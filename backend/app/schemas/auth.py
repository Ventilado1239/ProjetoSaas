import uuid
from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)

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


class OperatorCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    nome: str = Field(min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(min_length=12, max_length=72)
    perfil: Literal["recepcionista", "medico", "funcionario"]

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).lower()


class OperatorResponse(BaseModel):
    id: uuid.UUID
    nome: str
    email: str
    perfil: str
    ativo: bool

    model_config = ConfigDict(from_attributes=True)
