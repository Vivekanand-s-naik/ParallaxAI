"""
Authentication utilities for ParallaxAI
Uses HMAC-SHA256 tokens signed with SESSION_SECRET
"""

import os
import hmac
import hashlib
import json
import time
from typing import Optional, Dict, Any
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Secret key from environment
SECRET_KEY = os.getenv("SESSION_SECRET", "parallaxai-default-secret-change-in-production")

security = HTTPBearer(auto_error=False)

# -------------------------------------------------------------------
# Pre-defined users  (in production, use a database)
# Passwords are SHA-256 hashed: hashlib.sha256(b"password").hexdigest()
# -------------------------------------------------------------------
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
    """Create an HMAC-SHA256 signature."""
    return hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()


def create_token(username: str, role: str, ttl_seconds: int = 86400) -> str:
    """Create a signed token: base64-json.signature"""
    expires_at = int(time.time()) + ttl_seconds
    payload = json.dumps({"sub": username, "role": role, "exp": expires_at}, separators=(",", ":"))
    import base64
    encoded = base64.urlsafe_b64encode(payload.encode()).decode()
    signature = _sign(encoded)
    return f"{encoded}.{signature}"


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify token signature and expiry. Returns payload dict or None."""
    try:
        import base64
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
    """Check credentials. Returns user dict or None."""
    user = USERS.get(username)
    if not user:
        return None
    if user["password_hash"] != hashlib.sha256(password.encode()).hexdigest():
        return None
    return user


# -------------------------------------------------------------------
# FastAPI dependencies
# -------------------------------------------------------------------

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
) -> Dict[str, Any]:
    """Dependency: require a valid token. Returns payload."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    payload = verify_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload


def require_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Dependency: require admin role."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user


def optional_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
) -> Optional[Dict[str, Any]]:
    """Dependency: try to authenticate but don't fail if no token."""
    if credentials is None:
        return None
    return verify_token(credentials.credentials)
