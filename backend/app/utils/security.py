import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
import bcrypt
import jwt
from jwt import InvalidTokenError
from app.config import settings

# Used when an account does not exist so login timing does not reveal registered emails.
DUMMY_PASSWORD_HASH = bcrypt.hashpw(b"timing-defense-only", bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies that a plain text password matches its hash."""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    """Hashes a plain text password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def validate_password_strength(password: str) -> None:
    """Reject weak credentials used when provisioning or resetting accounts."""
    if len(password) < 12:
        raise ValueError("A senha deve ter pelo menos 12 caracteres.")
    if len(password.encode("utf-8")) > 72:
        raise ValueError("A senha deve ter no maximo 72 bytes.")
    if not any(char.isalpha() for char in password) or not any(char.isdigit() for char in password):
        raise ValueError("A senha deve conter letras e numeros.")
    if password.lower() in {"password1234", "admin12345678", "master123456"}:
        raise ValueError("Escolha uma senha menos previsivel.")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generates a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    now = datetime.now(timezone.utc)
    to_encode.update({
        "exp": expire,
        "iat": now,
        "jti": str(uuid.uuid4()),
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "type": "access",
    })
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generates a JWT refresh token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    # Generate a unique ID for this refresh token to support rotation and blacklist tracking
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
        "jti": str(uuid.uuid4()),
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
    })
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def decode_token(token: str) -> Optional[dict]:
    """Decodes a JWT token. Returns the payload or None if invalid."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
        )
        return payload
    except InvalidTokenError:
        return None
