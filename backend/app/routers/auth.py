from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.models import Usuario, TokenBlacklist, Tenant
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from app.utils.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token
)
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login")
async def login(
    login_data: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    # 1. Fetch user by email
    await db.execute(text("SET LOCAL app.bypass_rls = 'true'"))
    stmt = select(Usuario).where(Usuario.email == login_data.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas."
        )
        
    # 2. Verify password
    if not verify_password(login_data.password, user.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas."
        )

    # 3. Generate tokens
    access_token_data = {
        "sub": str(user.id),
        "tenant_id": str(user.tenant_id),
        "perfil": user.perfil
    }
    refresh_token_data = {
        "sub": str(user.id),
        "tenant_id": str(user.tenant_id)
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
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )
    
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        path="/"
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
    tenant_id_str = payload.get("tenant_id")
    
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
    user_result = await db.execute(select(Usuario).where(Usuario.id == user_id_str))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado."
        )

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
        "tenant_id": tenant_id_str,
        "perfil": user.perfil
    }
    refresh_token_data = {
        "sub": user_id_str,
        "tenant_id": tenant_id_str
    }
    
    new_access_token = create_access_token(access_token_data)
    new_refresh_token = create_refresh_token(refresh_token_data)
    
    await db.commit()
    
    # 6. Set new cookies
    is_prod = settings.ENVIRONMENT == "production"
    
    response.set_cookie(
        key="access_token",
        value=new_access_token,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )
    
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        path="/"
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
    response.delete_cookie(key="refresh_token", path="/")
    
    return {"message": "Logout realizado com sucesso"}
