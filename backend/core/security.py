"""
Cryptographic and token security utilities for ParallaxAI.
- Argon2id password hashing (via argon2-cffi)
- Short-lived JWT access tokens (via PyJWT)
- Opaque refresh/reset token generation and SHA-256 storage hashing
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from argon2 import PasswordHasher, Type
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

from backend.core.config import settings

# Explicitly configure Argon2id
password_hasher = PasswordHasher(
    time_cost=2,
    memory_cost=65536,
    parallelism=2,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return password_hasher.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a plaintext password against an Argon2id hash."""
    if not password_hash:
        return False
    try:
        return password_hasher.verify(password_hash, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    """Check if an existing Argon2id hash needs parameter upgrade."""
    try:
        return password_hasher.check_needs_rehash(password_hash)
    except Exception:
        return False


def create_access_token(
    user_id: uuid.UUID | str,
    username: Optional[str],
    email: str,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a short-lived signed JWT access token.
    Note: Role claims in the token are for convenience only; backend authorization
    always verifies active account status and permissions from PostgreSQL.
    """
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "username": username or email,
        "email": email,
        "role": role,
        "type": "access",
        "jti": str(uuid.uuid4()),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT access token. Returns payload dict or None."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["sub", "exp", "iat", "type"]},
        )
        if payload.get("type") != "access":
            return None
        return payload
    except jwt.PyJWTError:
        return None


def generate_opaque_token(nbytes: int = 48) -> str:
    """Generate a cryptographically strong URL-safe opaque token."""
    return secrets.token_urlsafe(nbytes)


def hash_opaque_token(raw_token: str) -> str:
    """Hash a refresh token or password-reset token with SHA-256 before database storage."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

