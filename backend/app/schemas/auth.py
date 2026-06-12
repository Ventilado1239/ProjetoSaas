import uuid
from pydantic import BaseModel, EmailStr

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: uuid.UUID
    nome: str
    email: str
    perfil: str
    tenant_id: uuid.UUID

    class Config:
        from_attributes = True
