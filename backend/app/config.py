import os
from typing import List, Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    DATABASE_APP_ROLE: Optional[str] = "saas_app_user"
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    
    JWT_SECRET: str
    DATA_ENCRYPTION_KEY: Optional[str] = None
    JWT_ALGORITHM: str = "HS256"
    JWT_ISSUER: str = "projeto-saas-api"
    JWT_AUDIENCE: str = "projeto-saas-web"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"
    ALLOWED_HOSTS: str = "localhost,127.0.0.1,testserver"
    ENVIRONMENT: str = "development"
    PORT: int = 8000
    
    EVOLUTION_API_URL: Optional[str] = None
    EVOLUTION_API_KEY: Optional[str] = None
    EVOLUTION_WEBHOOK_SECRET: Optional[str] = None
    ASAAS_WEBHOOK_TOKEN: Optional[str] = None
    ASAAS_WEBHOOK_SECRET: Optional[str] = None
    ASAAS_API_URL: str = "https://api-sandbox.asaas.com/v3"
    ASAAS_API_KEY: Optional[str] = None
    ASAAS_BILLING_ENABLED: bool = False
    BACKUP_DIR: Optional[str] = None
    BACKUP_ENCRYPTION_KEY: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def allowed_hosts_list(self) -> List[str]:
        return [host.strip() for host in self.ALLOWED_HOSTS.split(",") if host.strip()]

    @property
    def data_encryption_key(self) -> str:
        return self.DATA_ENCRYPTION_KEY or self.JWT_SECRET

    @model_validator(mode="after")
    def validate_security_configuration(self):
        environment = self.ENVIRONMENT.lower().strip()
        if environment not in {"development", "test", "production"}:
            raise ValueError("ENVIRONMENT deve ser development, test ou production.")
        self.ENVIRONMENT = environment
        if self.JWT_ALGORITHM != "HS256":
            raise ValueError("JWT_ALGORITHM deve ser HS256.")

        if environment == "production":
            weak_secrets = {
                "super-secret-key-change-in-production",
                "secret",
                "changeme",
            }
            if len(self.JWT_SECRET) < 32 or self.JWT_SECRET.lower() in weak_secrets:
                raise ValueError("JWT_SECRET de producao deve ter pelo menos 32 caracteres aleatorios.")
            if not self.DATA_ENCRYPTION_KEY or len(self.DATA_ENCRYPTION_KEY) < 32:
                raise ValueError("DATA_ENCRYPTION_KEY de producao deve ter pelo menos 32 caracteres aleatorios.")
            if self.DATA_ENCRYPTION_KEY == self.JWT_SECRET:
                raise ValueError("DATA_ENCRYPTION_KEY deve ser diferente de JWT_SECRET.")
            if not self.cors_origins_list or any("localhost" in origin or "127.0.0.1" in origin for origin in self.cors_origins_list):
                raise ValueError("CORS_ORIGINS de producao deve conter apenas origens HTTPS reais.")
            if any(not origin.startswith("https://") for origin in self.cors_origins_list):
                raise ValueError("Todas as CORS_ORIGINS de producao devem usar HTTPS.")
            if not self.allowed_hosts_list or "*" in self.allowed_hosts_list:
                raise ValueError("ALLOWED_HOSTS de producao deve listar hosts explicitos.")
            if not (self.ASAAS_WEBHOOK_TOKEN or self.ASAAS_WEBHOOK_SECRET):
                raise ValueError("Configure ASAAS_WEBHOOK_SECRET em producao.")
            if len(self.ASAAS_WEBHOOK_TOKEN or self.ASAAS_WEBHOOK_SECRET or "") < 32:
                raise ValueError("O token do webhook Asaas deve ter pelo menos 32 caracteres.")
            if self.ASAAS_BILLING_ENABLED:
                if not self.ASAAS_API_KEY:
                    raise ValueError("Configure ASAAS_API_KEY quando a cobranca automatica estiver habilitada.")
                if not self.ASAAS_API_URL.startswith("https://"):
                    raise ValueError("ASAAS_API_URL deve usar HTTPS em producao.")
            if not self.EVOLUTION_WEBHOOK_SECRET:
                raise ValueError("Configure EVOLUTION_WEBHOOK_SECRET em producao.")
            if len(self.EVOLUTION_WEBHOOK_SECRET) < 32:
                raise ValueError("EVOLUTION_WEBHOOK_SECRET deve ter pelo menos 32 caracteres.")
            if not self.EVOLUTION_API_URL or not self.EVOLUTION_API_URL.startswith("https://"):
                raise ValueError("Configure EVOLUTION_API_URL com HTTPS em producao.")
            if not self.EVOLUTION_API_KEY:
                raise ValueError("Configure EVOLUTION_API_KEY em producao.")
            if not self.BACKUP_DIR or not os.path.isabs(self.BACKUP_DIR):
                raise ValueError("BACKUP_DIR de producao deve ser um caminho absoluto em volume persistente.")
            if not self.BACKUP_ENCRYPTION_KEY or len(self.BACKUP_ENCRYPTION_KEY) < 32:
                raise ValueError("BACKUP_ENCRYPTION_KEY de producao deve ter pelo menos 32 caracteres aleatorios.")
        return self

# Determine correct .env path if setting env_file relative to this file
# This file is backend/app/config.py
# parent of this file is backend/app/
# parent of parent is backend/ (where .env is)
settings_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(settings_path):
    settings = Settings(_env_file=settings_path)
else:
    settings = Settings()
