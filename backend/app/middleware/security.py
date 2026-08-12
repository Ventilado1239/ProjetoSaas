import time
import asyncio
from collections import defaultdict
from typing import Dict, List
import json
from app.config import settings

class SecurityAndRateLimitMiddleware:
    def __init__(self, app):
        self.app = app
        self.ip_limits: Dict[str, List[float]] = defaultdict(list)
        self.tenant_limits: Dict[str, List[float]] = defaultdict(list)
        self.login_limits: Dict[str, List[float]] = defaultdict(list)
        self.cleanup_counter = 0

    def _clean_expired(self, now: float):
        for ip, times in list(self.ip_limits.items()):
            valid_times = [t for t in times if now - t < 60.0]
            if not valid_times:
                self.ip_limits.pop(ip, None)
            else:
                self.ip_limits[ip] = valid_times

        for tenant, times in list(self.tenant_limits.items()):
            valid_times = [t for t in times if now - t < 60.0]
            if not valid_times:
                self.tenant_limits.pop(tenant, None)
            else:
                self.tenant_limits[tenant] = valid_times

        for ip, times in list(self.login_limits.items()):
            valid_times = [t for t in times if now - t < 300.0]
            if not valid_times:
                self.login_limits.pop(ip, None)
            else:
                self.login_limits[ip] = valid_times

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers_dict = dict(scope.get("headers", []))

        # Browsers always send Origin on cross-origin unsafe requests. Rejecting
        # unknown origins prevents credentialed CSRF even before CORS handling.
        method = scope.get("method", "GET").upper()
        origin = headers_dict.get(b"origin", b"").decode("utf-8")
        if method in {"POST", "PUT", "PATCH", "DELETE"} and origin and origin not in settings.cors_origins_list:
            await self._send_error(send, 403, "Origem nao permitida.")
            return
        
        # 1. Get client IP
        client = scope.get("client")
        ip = client[0] if client else "unknown"
        
        # 2. Get tenant_id from authorization header or cookies
        auth_header = headers_dict.get(b"authorization", b"").decode("utf-8")
        token = None
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            
        if not token:
            cookie_header = headers_dict.get(b"cookie", b"").decode("utf-8")
            if cookie_header:
                cookies = {}
                for cookie in cookie_header.split(";"):
                    parts = cookie.split("=")
                    if len(parts) == 2:
                        cookies[parts[0].strip()] = parts[1].strip()
                token = cookies.get("access_token")

        tenant_id = None
        if token:
            try:
                from app.utils.security import decode_token
                payload = decode_token(token)
                if payload and payload.get("type") == "access":
                    tenant_id = payload.get("tenant_id")
            except Exception:
                pass

        now = time.time()
        self.cleanup_counter += 1
        if self.cleanup_counter >= 100:
            self.cleanup_counter = 0
            self._clean_expired(now)

        path = scope.get("path", "")
        if method == "POST" and path in {"/auth/login", "/master/auth/login"}:
            attempts = [timestamp for timestamp in self.login_limits[ip] if now - timestamp < 300.0]
            self.login_limits[ip] = attempts
            if len(attempts) >= 20:
                await self._send_error(send, 429, "Muitas tentativas de login. Tente novamente mais tarde.")
                return
            self.login_limits[ip].append(now)

        # Check IP Limit (100 req/min)
        ip_times = self.ip_limits[ip]
        ip_times = [t for t in ip_times if now - t < 60.0]
        self.ip_limits[ip] = ip_times
        if len(ip_times) >= 100:
            await self._send_error(send, 429, "Rate limit exceeded. Máximo de 100 requisições por minuto por IP.")
            return

        # Check Tenant Limit (1000 req/min)
        if tenant_id:
            tenant_str = str(tenant_id)
            tenant_times = self.tenant_limits[tenant_str]
            tenant_times = [t for t in tenant_times if now - t < 60.0]
            self.tenant_limits[tenant_str] = tenant_times
            if len(tenant_times) >= 1000:
                await self._send_error(send, 429, "Rate limit exceeded. Máximo de 1000 requisições por minuto por tenant.")
                return

        # Record request timestamp
        self.ip_limits[ip].append(now)
        if tenant_id:
            self.tenant_limits[str(tenant_id)].append(now)

        # 3. HTTPS Redirect in production
        if settings.ENVIRONMENT != "development":
            proto = headers_dict.get(b"x-forwarded-proto", b"").decode("utf-8")
            if proto == "http":
                host = headers_dict.get(b"host", b"localhost").decode("utf-8")
                path = scope.get("path", "")
                query = scope.get("query_string", b"").decode("utf-8")
                url = f"https://{host}{path}"
                if query:
                    url += f"?{query}"
                await self._send_redirect(send, url)
                return

        # 4. Inject Security Headers in Response
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                sec_headers = {
                    b"strict-transport-security": b"max-age=63072000; includeSubDomains; preload",
                    b"x-content-type-options": b"nosniff",
                    b"x-frame-options": b"DENY",
                    b"content-security-policy": b"default-src 'none'; frame-ancestors 'none'; base-uri 'none';",
                    b"referrer-policy": b"no-referrer",
                    b"permissions-policy": b"camera=(), microphone=(), geolocation=()",
                }
                if path.startswith("/auth") or path.startswith("/master"):
                    sec_headers[b"cache-control"] = b"no-store"
                # Overwrite standard headers with security values
                headers = [h for h in headers if h[0].lower() not in sec_headers]
                for k, v in sec_headers.items():
                    headers.append((k, v))
                message["headers"] = headers

            await send(message)

        await self.app(scope, receive, send_wrapper)

    async def _send_error(self, send, status_code: int, message: str):
        content = json.dumps({"detail": message}).encode("utf-8")
        await send({
            "type": "http.response.start",
            "status": status_code,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(content)).encode("utf-8")),
            ],
        })
        await send({
            "type": "http.response.body",
            "body": content,
        })

    async def _send_redirect(self, send, url: str):
        await send({
            "type": "http.response.start",
            "status": 301,
            "headers": [
                (b"location", url.encode("utf-8")),
            ],
        })
        await send({
            "type": "http.response.body",
            "body": b"",
        })
