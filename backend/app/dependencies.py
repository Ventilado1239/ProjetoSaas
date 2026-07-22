import uuid
from typing import Callable, Optional
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.models import Tenant, Usuario
from app.utils.security import decode_token

async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> Usuario:
    """
    Extracts the authenticated user from the JWT token.
    Supports both Authorization header (Bearer token) and access_token cookie.
    """
    token = None
    
    # 1. Try to get token from Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        
    # 2. Try to get token from cookie
    if not token:
        token = request.cookies.get("access_token")
        
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autorizado. Token ausente.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    payload = decode_token(token)
    if not payload or payload.get("type") != "access" or payload.get("scope", "tenant") != "tenant":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido. Campo 'sub' ausente.",
        )
        
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido. 'sub' não é um UUID válido.",
        )
        
    # Fetch user from database
    result = await db.execute(select(Usuario).where(Usuario.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado.",
        )
    if not user.ativo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário desativado.")

    if str(user.tenant_id) != str(payload.get("tenant_id")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token nao pertence ao usuario.")
    if payload.get("ver") != user.token_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessao revogada.")

    tenant = await db.get(Tenant, user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Conta nao encontrada.")
    if not tenant.sistema_ativo and user.perfil != "dono":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Conta temporariamente desativada.")
        
    from app.utils.context import current_user_var
    current_user_var.set(user)
    return user

async def get_tenant_id(current_user: Usuario = Depends(get_current_user)) -> uuid.UUID:
    """
    Returns the tenant ID of the currently authenticated user.
    """
    return current_user.tenant_id


def require_roles(*allowed_roles: str) -> Callable:
    """FastAPI dependency enforcing server-side role authorization."""
    async def role_checker(current_user: Usuario = Depends(get_current_user)) -> Usuario:
        if current_user.perfil not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Voce nao tem permissao para executar esta acao.",
            )
        return current_user
    return role_checker
