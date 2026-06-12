from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import text
from app.database import AsyncSessionLocal
from app.utils.security import decode_token

class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Attempt to extract tenant_id from JWT token in header or cookie
        tenant_id = None
        token = None
        
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            
        if not token:
            token = request.cookies.get("access_token")
            
        if token:
            payload = decode_token(token)
            if payload and payload.get("type") == "access":
                tenant_id = payload.get("tenant_id")

        request.state.tenant_id = tenant_id

        import uuid
        from app.utils.context import tenant_id_var
        try:
            tenant_id_var.set(uuid.UUID(str(tenant_id)) if tenant_id else None)
        except Exception:
            tenant_id_var.set(None)

        # 2. Bind the database session to the request lifecycle
        async with AsyncSessionLocal() as session:
            request.state.db = session
            try:
                if tenant_id:
                    # Enforce tenant context in the connection session
                    await session.execute(
                        text("SELECT set_tenant_id(:tenant_id)"),
                        {"tenant_id": tenant_id}
                    )
                else:
                    # Reset the tenant context for safety
                    await session.execute(text("SELECT set_tenant_id(NULL)"))
            except Exception:
                # Ignore errors during startup/migrations when the database schema/function isn't ready
                pass
                
            response = await call_next(request)
            return response
