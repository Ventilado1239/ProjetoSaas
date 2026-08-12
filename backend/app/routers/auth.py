from datetime import datetime, timezone, timedelta
import uuid
from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.database import get_db
from app.models.models import Usuario, TokenBlacklist, Tenant
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from app.utils.security import (
    DUMMY_PASSWORD_HASH,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token
)
from app.config import settings
from app.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
async def me(current_user: Usuario = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "nome": current_user.nome,
        "email": current_user.email,
        "perfil": current_user.perfil,
        "tenant_id": current_user.tenant_id,
    }

@router.post("/login")
async def login(
    login_data: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    # 1. Fetch user by email
    await db.execute(text("SET LOCAL app.bypass_rls = 'true'"))
    normalized_email = str(login_data.email).strip().lower()
    stmt = select(Usuario).where(func.lower(Usuario.email) == normalized_email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    # Always run bcrypt to reduce account-enumeration timing differences.
    password_valid = verify_password(login_data.password, user.senha_hash if user else DUMMY_PASSWORD_HASH)
    if not user or not user.ativo or not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas."
        )

    # 3. Generate tokens
    access_token_data = {
        "sub": str(user.id),
        "tenant_id": str(user.tenant_id),
        "perfil": user.perfil,
        "scope": "tenant",
        "ver": user.token_version,
    }
    refresh_token_data = {
        "sub": str(user.id),
        "tenant_id": str(user.tenant_id),
        "scope": "tenant",
        "ver": user.token_version,
    }
    
    access_token = create_access_token(access_token_data)
    refresh_token = create_refresh_token(refresh_token_data)
    
    # 4. Set httpOnly cookies
    is_prod = settings.ENVIRONMENT == "production"
    
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=is_prod,
        samesite="strict",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )
    
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=is_prod,
        samesite="strict",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        path="/auth"
    )
    
    # Return user details
    return {
        "message": "Login realizado com sucesso",
        "user": {
            "id": user.id,
            "nome": user.nome,
            "email": user.email,
            "perfil": user.perfil,
            "tenant_id": user.tenant_id
        }
    }

@router.post("/refresh")
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    # 1. Get refresh token from cookies
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de atualização ausente."
        )
        
    # 2. Decode and validate refresh token
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de atualização inválido ou expirado."
        )
        
    jti = payload.get("jti")
    user_id_str = payload.get("sub")

    if not jti or payload.get("scope", "tenant") != "tenant":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de atualização inválido.")
    
    # 3. Check blacklist
    stmt = select(TokenBlacklist).where(TokenBlacklist.token == jti)
    result = await db.execute(stmt)
    blacklisted = result.scalar_one_or_none()
    if blacklisted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de atualização revogado."
        )
        
    # Fetch the user to ensure they still exist
    await db.execute(text("SET LOCAL app.bypass_rls = 'true'"))
    try:
        user_id = uuid.UUID(str(user_id_str))
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de atualizacao invalido.")
    user_result = await db.execute(select(Usuario).where(Usuario.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user or not user.ativo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado."
        )
    if payload.get("ver") != user.token_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessao revogada.")

    # 4. Invalidate old refresh token (add to blacklist)
    exp_timestamp = payload.get("exp")
    exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
    
    blacklist_entry = TokenBlacklist(
        token=jti,
        expira_em=exp_datetime
    )
    db.add(blacklist_entry)
    
    # 5. Generate new pair (Token Rotation)
    access_token_data = {
        "sub": user_id_str,
        "tenant_id": str(user.tenant_id),
        "perfil": user.perfil,
        "scope": "tenant",
        "ver": user.token_version,
    }
    refresh_token_data = {
        "sub": user_id_str,
        "tenant_id": str(user.tenant_id),
        "scope": "tenant",
        "ver": user.token_version,
    }
    
    new_access_token = create_access_token(access_token_data)
    new_refresh_token = create_refresh_token(refresh_token_data)
    
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de atualizacao ja utilizado.")
    
    # 6. Set new cookies
    is_prod = settings.ENVIRONMENT == "production"
    
    response.set_cookie(
        key="access_token",
        value=new_access_token,
        httponly=True,
        secure=is_prod,
        samesite="strict",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )
    
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=is_prod,
        samesite="strict",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        path="/auth"
    )
    
    return {"message": "Tokens atualizados com sucesso"}

@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        payload = decode_token(refresh_token)
        if payload and payload.get("type") == "refresh":
            jti = payload.get("jti")
            exp_timestamp = payload.get("exp")
            exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            
            # Check if already blacklisted to avoid unique key errors
            stmt = select(TokenBlacklist).where(TokenBlacklist.token == jti)
            res = await db.execute(stmt)
            if not res.scalar_one_or_none():
                blacklist_entry = TokenBlacklist(
                    token=jti,
                    expira_em=exp_datetime
                )
                db.add(blacklist_entry)
                await db.commit()
                
    # Delete cookies on client side
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/auth")
    
    return {"message": "Logout realizado com sucesso"}
