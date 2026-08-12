import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from app.config import settings
from app.middleware.tenant import TenantMiddleware
from app.middleware.security import SecurityAndRateLimitMiddleware
from app.routers import auth, whatsapp, webhooks, dashboard, master
from app.tasks.scheduler import start_scheduler, shutdown_scheduler
import app.middleware.auditoria


# Configure structlog for JSON logs (useful for auditing and LGPD compliance)
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    shutdown_scheduler()
    from app.services.whatsapp_service import close_http_client
    await close_http_client()
    from app.services.asaas_service import close_http_client as close_asaas_http_client
    await close_asaas_http_client()

app = FastAPI(
    title="SaaS de Gestão via WhatsApp",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
    lifespan=lifespan
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers
        )
    if isinstance(exc, RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors()}
        )

    logger.exception("Erro interno não tratado", path=request.url.path)

    if settings.ENVIRONMENT != "development":
        return JSONResponse(
            status_code=500,
            content={"detail": "Erro interno do servidor."}
        )
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)}
    )

# Middleware is registered inner-to-outer by Starlette.
app.add_middleware(TenantMiddleware)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Webhook-Secret", "asaas-access-token"],
)

# Rate limiting and origin validation run before opening a database session.
app.add_middleware(SecurityAndRateLimitMiddleware)

# Reject forged Host headers at the outermost edge.
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts_list)

# Register routers
app.include_router(auth.router)
app.include_router(master.router)
app.include_router(whatsapp.router)
app.include_router(webhooks.router)
app.include_router(dashboard.router)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=True)
