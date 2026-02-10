"""
JWT e hashing de senhas para autenticação stateless.
Usa bcrypt diretamente para evitar limite de 72 bytes do passlib em alguns ambientes.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt
from jose import JWTError, jwt

from app.config import get_settings

# Bcrypt aceita no máximo 72 bytes; truncar para evitar ValueError em qualquer ambiente
_BCRYPT_MAX_PASSWORD_BYTES = 72
# Rounds alvo para re-hash progressivo no login (hashes antigos com rounds > este são atualizados)
_BCRYPT_TARGET_ROUNDS = 8


def _truncate_password_bytes(raw: str) -> bytes:
    """Trunca senha a 72 bytes (limite do bcrypt)."""
    return raw.encode("utf-8")[: _BCRYPT_MAX_PASSWORD_BYTES]


def get_bcrypt_rounds_from_hash(hashed_password: str) -> int:
    """Extrai o cost factor (rounds) do hash bcrypt. Formato: $2b$10$..."""
    if not hashed_password or not isinstance(hashed_password, str):
        return 0
    parts = hashed_password.strip().split("$")
    if len(parts) >= 3:
        try:
            return int(parts[2])
        except (ValueError, IndexError):
            pass
    return 0


def verify_password(plain_password: str, hashed_password: str) -> bool:
    pwd_bytes = _truncate_password_bytes(plain_password or "")
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode("utf-8")
    return bcrypt.checkpw(pwd_bytes, hashed_password)


def get_password_hash(password: str, rounds: Optional[int] = None) -> str:
    settings = get_settings()
    pwd_bytes = _truncate_password_bytes(password or "")
    r = rounds if rounds is not None else settings.bcrypt_rounds
    r = max(4, min(31, r))
    salt = bcrypt.gensalt(rounds=r)
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def create_access_token(
    subject: str | int,
    extra_claims: Optional[dict[str, Any]] = None,
) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "type": "access",
    }
    if extra_claims:
        to_encode.update(extra_claims)
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str | int) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> Optional[dict[str, Any]]:
    settings = get_settings()
    try:
        return jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError:
        return None
