import pytest
from pydantic import ValidationError

from app.config import Settings
from app.routers.master import MasterTenantCreate, ResetPasswordRequest
from app.services.backup_service import decrypt_backup_content, encrypt_backup_content
from app.utils.security import create_access_token, decode_token, validate_password_strength


def _settings_payload(**overrides):
    payload = {
        "DATABASE_URL": "postgresql+asyncpg://user:password@localhost/database",
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_ANON_KEY": "anon",
        "SUPABASE_SERVICE_ROLE_KEY": "service",
        "JWT_SECRET": "development-secret",
    }
    payload.update(overrides)
    return payload


def test_password_policy_rejects_weak_passwords():
    with pytest.raises(ValueError):
        validate_password_strength("master123")
    validate_password_strength("UmaSenhaForte2026")


def test_master_payload_does_not_accept_invalid_business_values():
    base = {
        "nome": "Clinica Segura",
        "whatsapp_numero": "5511999999999",
        "admin_email": "dono@example.com",
        "admin_password": "UmaSenhaForte2026",
    }
    with pytest.raises(ValueError):
        MasterTenantCreate(**base, plano="ilimitado")
    with pytest.raises(ValueError):
        ResetPasswordRequest(new_password="fraca")


def test_jwt_has_expected_issuer_audience_and_scope():
    token = create_access_token({
        "sub": "00000000-0000-0000-0000-000000000001",
        "tenant_id": "00000000-0000-0000-0000-000000000002",
        "scope": "tenant",
    })
    payload = decode_token(token)
    assert payload is not None
    assert payload["scope"] == "tenant"
    assert payload["jti"]


def test_backup_encryption_is_authenticated_and_not_plaintext():
    plaintext = b"nome,whatsapp\nPaciente,5511999999999\n"
    encrypted = encrypt_backup_content(plaintext, "backup-key-with-at-least-32-characters")
    assert encrypted != plaintext
    assert b"Paciente" not in encrypted
    assert decrypt_backup_content(encrypted, "backup-key-with-at-least-32-characters") == plaintext


def test_environment_name_cannot_bypass_production_guards():
    with pytest.raises(ValidationError):
        Settings(**_settings_payload(ENVIRONMENT="prodution"), _env_file=None)


def test_production_refuses_mock_whatsapp_configuration():
    with pytest.raises(ValidationError, match="EVOLUTION_API_URL"):
        Settings(**_settings_payload(
            ENVIRONMENT="production",
            JWT_SECRET="jwt-secret-with-at-least-32-random-characters",
            DATA_ENCRYPTION_KEY="data-key-with-at-least-32-random-characters",
            CORS_ORIGINS="https://app.example.com",
            ALLOWED_HOSTS="api.example.com",
            ASAAS_WEBHOOK_SECRET="asaas-webhook-secret-with-32-characters",
            EVOLUTION_WEBHOOK_SECRET="evolution-webhook-secret-with-32-chars",
            BACKUP_DIR="C:\\persistent\\backups",
            BACKUP_ENCRYPTION_KEY="backup-key-with-at-least-32-characters",
        ), _env_file=None)
