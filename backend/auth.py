"""
Authentication & Authorization dependencies for ParallaxAI.
Validates JWT access tokens (and legacy HMAC tokens for backwards compatibility)
against PostgreSQL, enforcing live account status and database role/permission lookups.
"""

import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.security import (
    create_access_token,
    decode_access_token,
    verify_password,
)
from backend.database.models import UserORM
from backend.database.session import SessionLocal, get_db
from backend.services.auth_service import build_user_auth_out, get_user_permissions

SECRET_KEY = os.getenv("SESSION_SECRET", settings.SESSION_SECRET)

security = HTTPBearer(auto_error=False)

# Legacy fallback dictionary retained for backwards-compatible imports
USERS: Dict[str, Dict[str, Any]] = {
    "admin": {
        "username": "admin",
        "password_hash": hashlib.sha256(b"admin123").hexdigest(),
        "role": "admin",
        "full_name": "System Administrator",
        "email": "admin@parallaxai.io",
    },
    "analyst": {
        "username": "analyst",
        "password_hash": hashlib.sha256(b"analyst123").hexdigest(),
        "role": "analyst",
        "full_name": "Data Analyst",
        "email": "analyst@parallaxai.io",
    },
    "reviewer": {
        "username": "reviewer",
        "password_hash": hashlib.sha256(b"reviewer123").hexdigest(),
        "role": "reviewer",
        "full_name": "Human Reviewer",
        "email": "reviewer@parallaxai.io",
    },
}


def _sign(payload: str) -> str:
    return hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()


def create_token(
    username: str,
    role: str,
    ttl_seconds: int = 900,
    user_id: Optional[str] = None,
    email: Optional[str] = None,
) -> str:
    """Create a signed JWT access token."""
    from datetime import timedelta

    return create_access_token(
        user_id=user_id or username,
        username=username,
        email=email or f"{username}@parallaxai.io",
        role=role,
        expires_delta=timedelta(seconds=ttl_seconds),
    )


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify a JWT access token (or legacy HMAC token).
    Returns decoded payload dict or None.
    """
    jwt_payload = decode_access_token(token)
    if jwt_payload is not None:
        return jwt_payload

    # Legacy HMAC fallback
    try:
        parts = token.rsplit(".", 1)
        if len(parts) != 2:
            return None
        encoded, signature = parts
        expected = _sign(encoded)
        if not hmac.compare_digest(signature, expected):
            return None
        payload = json.loads(base64.urlsafe_b64decode(encoded + "==").decode())
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Authenticate against PostgreSQL using Argon2id.
    Returns user dictionary if valid and active, else None.
    """
    ident = username.strip().lower()
    with SessionLocal() as session:
        user = session.execute(
            select(UserORM).where(
                or_(
                    func.lower(UserORM.username) == ident,
                    func.lower(UserORM.email) == ident,
                )
            )
        ).scalar_one_or_none()
        if user is not None and user.password_hash:
            if not verify_password(password, user.password_hash):
                return None
            if not user.is_active:
                return None
            out = build_user_auth_out(user)
            return {
                "id": str(user.id),
                "username": out.username,
                "role": out.role,
                "roles": out.roles,
                "permissions": out.permissions,
                "full_name": out.full_name,
                "email": out.email,
                "is_active": out.is_active,
            }
    return None


def _resolve_user_from_payload(
    session: Session, payload: Dict[str, Any]
) -> Optional[UserORM]:
    """Resolve a live UserORM from a token payload."""
    sub = str(payload.get("sub", ""))
    user: Optional[UserORM] = None
    try:
        sub_uuid = uuid.UUID(sub)
        user = session.execute(
            select(UserORM).where(UserORM.id == sub_uuid)
        ).scalar_one_or_none()
    except ValueError:
        pass

    if user is None and sub:
        user = session.execute(
            select(UserORM).where(
                or_(
                    func.lower(UserORM.username) == sub.lower(),
                    func.lower(UserORM.email) == sub.lower(),
                )
            )
        ).scalar_one_or_none()

    return user


def get_current_user_orm(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
    session: Session = Depends(get_db),
) -> UserORM:
    """
    FastAPI dependency: validates Bearer token AND verifies the user exists and is active in PostgreSQL.
    Do not trust role claims in a long-lived token as the sole authorization source.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
        )
    payload = verify_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )

    user = _resolve_user_from_payload(session, payload)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )
    return user


def get_current_user(
    user: UserORM = Depends(get_current_user_orm),
) -> Dict[str, Any]:
    """
    FastAPI dependency: returns a dictionary with live database user info, roles, and permissions.
    Compatible with both existing endpoints and v1 endpoints.
    """
    perms = get_user_permissions(user)
    primary_role = user.primary_role
    return {
        "id": str(user.id),
        "sub": user.username or user.email,
        "username": user.username or user.email.split("@")[0],
        "email": user.email,
        "full_name": user.full_name,
        "role": primary_role.lower() if primary_role in ("ADMIN", "ANALYST") else primary_role,
        "primary_role": primary_role,
        "roles": user.role_names,
        "permissions": perms,
        "is_active": user.is_active,
    }


def require_admin(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Dependency: require ADMIN or SUPER_ADMIN role from live database roles."""
    roles_upper = {r.upper() for r in current_user.get("roles", [])}
    role_single = str(current_user.get("role", "")).upper()
    if not ({"SUPER_ADMIN", "ADMIN"} & (roles_upper | {role_single})):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


def optional_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
    session: Session = Depends(get_db),
) -> Optional[Dict[str, Any]]:
    """Dependency: try to authenticate against DB, returning None if unauthenticated or invalid."""
    if credentials is None or not credentials.credentials:
        return None
    payload = verify_token(credentials.credentials)
    if payload is None:
        return None
    user = _resolve_user_from_payload(session, payload)
    if user is None or not user.is_active:
        return None
    perms = get_user_permissions(user)
    return {
        "id": str(user.id),
        "sub": user.username or user.email,
        "username": user.username or user.email.split("@")[0],
        "email": user.email,
        "full_name": user.full_name,
        "role": user.primary_role,
        "roles": user.role_names,
        "permissions": perms,
        "is_active": user.is_active,
    }
