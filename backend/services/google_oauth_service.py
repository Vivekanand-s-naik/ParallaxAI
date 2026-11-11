"""
Google OAuth 2.0 / OpenID Connect Integration Service for ParallaxAI.
Implements:
- OAuth state generation, HMAC-SHA256 signing, and one-time replay protection
- Redirect URI allowlist validation
- OpenID Connect ID token signature, issuer, audience, and expiration validation
- Secure account linking and safe default VIEWER role assignment
- Honest unavailable status (503 Service Unavailable) until GOOGLE_CLIENT_ID
  and GOOGLE_CLIENT_SECRET are configured. Never simulates a Google login.
"""

import base64
import hashlib
import hmac
import json
import secrets
import time
import urllib.parse
import uuid
from typing import Any, Dict, Optional, Set
import jwt
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.database.models import RoleORM, UserORM, UserRoleORM, utc_now

GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_VALID_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}
OAUTH_STATE_TTL_SECONDS = 600

# One-time state store for CSRF / replay protection
_active_oauth_states: Dict[str, int] = {}


def assert_google_oauth_configured() -> None:
    """
    Raise HTTP 503 Service Unavailable if Google OAuth credentials are not configured.
    Never simulate a successful Google login.
    """
    if not settings.is_google_oauth_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Google Sign-In is currently unavailable. Configure GOOGLE_CLIENT_ID, "
                "GOOGLE_CLIENT_SECRET, and GOOGLE_REDIRECT_URI in the environment to enable Google OAuth 2.0."
            ),
        )


def validate_redirect_uri(redirect_uri: Optional[str]) -> str:
    """
    Validate that the requested redirect_uri matches the configured GOOGLE_REDIRECT_URI
    or an allowed frontend origin in BACKEND_CORS_ORIGINS.
    """
    configured_redirect = settings.GOOGLE_REDIRECT_URI.strip()
    if not redirect_uri:
        return configured_redirect

    candidate = redirect_uri.strip()
    if candidate == configured_redirect:
        return candidate

    parsed = urllib.parse.urlparse(candidate)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth redirect_uri format",
        )

    origin = f"{parsed.scheme}://{parsed.netloc}"
    allowed_origins: Set[str] = set(settings.BACKEND_CORS_ORIGINS or [])
    if origin not in allowed_origins:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Disallowed OAuth redirect_uri origin",
        )
    return candidate


def create_oauth_state(redirect_uri: Optional[str] = None) -> str:
    """
    Create a cryptographically signed, time-bounded, single-use OAuth 2.0 state parameter.
    """
    validated_redirect = validate_redirect_uri(redirect_uri)
    nonce = secrets.token_urlsafe(24)
    issued_at = int(time.time())
    payload = {
        "nonce": nonce,
        "iat": issued_at,
        "exp": issued_at + OAUTH_STATE_TTL_SECONDS,
        "redirect_uri": validated_redirect,
    }
    raw_json = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    b64_payload = base64.urlsafe_b64encode(raw_json).decode("ascii").rstrip("=")
    signature = hmac.new(
        settings.JWT_SECRET_KEY.encode("utf-8"),
        b64_payload.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()

    # Prune expired nonces and store current nonce for single-use verification
    now = int(time.time())
    expired = [k for k, exp in _active_oauth_states.items() if exp <= now]
    for k in expired:
        _active_oauth_states.pop(k, None)
    _active_oauth_states[nonce] = issued_at + OAUTH_STATE_TTL_SECONDS

    return f"{b64_payload}.{signature}"


def verify_and_consume_oauth_state(state: str) -> Dict[str, Any]:
    """
    Validate HMAC signature, expiration, redirect_uri, and single-use nonce of an OAuth state token.
    """
    if not state or "." not in state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth state parameter",
        )

    b64_payload, provided_sig = state.rsplit(".", 1)
    expected_sig = hmac.new(
        settings.JWT_SECRET_KEY.encode("utf-8"),
        b64_payload.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(provided_sig, expected_sig):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth state signature verification failed",
        )

    padding = "=" * (-len(b64_payload) % 4)
    try:
        raw_bytes = base64.urlsafe_b64decode(b64_payload + padding)
        payload = json.loads(raw_bytes.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed OAuth state payload",
        ) from exc

    now = int(time.time())
    if int(payload.get("exp", 0)) <= now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth state has expired",
        )

    nonce = payload.get("nonce")
    if not nonce or nonce not in _active_oauth_states:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth state has already been used or is unrecognized",
        )
    # Consume nonce so state cannot be replayed
    _active_oauth_states.pop(nonce, None)

    validate_redirect_uri(payload.get("redirect_uri"))
    return payload


def build_google_authorization_url(redirect_uri: Optional[str] = None) -> Dict[str, str]:
    """
    Construct the Google OAuth 2.0 / OpenID Connect authorization URL and state.
    Requires Google OAuth credentials to be configured.
    """
    assert_google_oauth_configured()
    validated_redirect = validate_redirect_uri(redirect_uri)
    state = create_oauth_state(validated_redirect)

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID.strip(),
        "redirect_uri": validated_redirect,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    }
    url = f"{GOOGLE_AUTH_ENDPOINT}?{urllib.parse.urlencode(params)}"
    return {"authorization_url": url, "state": state, "redirect_uri": validated_redirect}


def verify_google_id_token(
    id_token: str,
    signing_key: str,
    expected_client_id: Optional[str] = None,
    algorithms: Optional[list[str]] = None,
) -> Dict[str, Any]:
    """
    Validate a Google OpenID Connect ID token's cryptographic signature,
    issuer ('accounts.google.com' or 'https://accounts.google.com'),
    audience (GOOGLE_CLIENT_ID), expiration, and subject/email claims.
    """
    audience = (expected_client_id or settings.GOOGLE_CLIENT_ID).strip()
    if not audience:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GOOGLE_CLIENT_ID is not configured for ID token verification",
        )

    try:
        claims = jwt.decode(
            id_token,
            signing_key,
            algorithms=algorithms or ["RS256", "HS256"],
            audience=audience,
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google ID token has expired",
        ) from exc
    except jwt.InvalidAudienceError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google ID token audience mismatch",
        ) from exc
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google ID token signature or claims",
        ) from exc

    issuer = claims.get("iss")
    if issuer not in GOOGLE_VALID_ISSUERS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google ID token issuer",
        )

    if not claims.get("email") or not claims.get("email_verified", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google account email must be verified",
        )

    return claims


def link_or_create_google_user(
    session: Session, google_claims: Dict[str, Any]
) -> UserORM:
    """
    Securely link a verified Google identity ('sub' + 'email') to an existing active UserORM
    or provision a new UserORM with the default VIEWER role.
    """
    google_sub = str(google_claims["sub"]).strip()
    email = str(google_claims["email"]).strip().lower()
    full_name = str(google_claims.get("name") or email.split("@")[0]).strip()

    # 1. Match by google_sub
    user = session.execute(
        select(UserORM).where(UserORM.google_sub == google_sub)
    ).scalar_one_or_none()

    # 2. Match by verified email (account linking)
    if user is None:
        user = session.execute(
            select(UserORM).where(func.lower(UserORM.email) == email)
        ).scalar_one_or_none()
        if user is not None:
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Account is deactivated. Contact a governance administrator.",
                )
            user.google_sub = google_sub
            user.is_verified = True
            if user.auth_provider == "local":
                user.auth_provider = "local+google"

    # 3. Provision a new account with safe VIEWER role
    if user is None:
        base_username = email.split("@")[0][:48]
        username = base_username
        if session.execute(
            select(UserORM).where(func.lower(UserORM.username) == username)
        ).scalar_one_or_none():
            username = f"{base_username}_{uuid.uuid4().hex[:6]}"

        user = UserORM(
            id=uuid.uuid4(),
            username=username,
            email=email,
            full_name=full_name,
            password_hash=None,
            is_active=True,
            is_verified=True,
            auth_provider="google",
            google_sub=google_sub,
            preferences={"theme": "dark", "notifications_enabled": True},
        )
        session.add(user)
        session.flush()

        viewer_role = session.execute(
            select(RoleORM).where(RoleORM.name == "VIEWER")
        ).scalar_one_or_none()
        if viewer_role is not None:
            session.add(
                UserRoleORM(
                    id=uuid.uuid4(),
                    user_id=user.id,
                    role_id=viewer_role.id,
                )
            )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact a governance administrator.",
        )

    user.last_login_at = utc_now()
    session.commit()
    session.refresh(user)
    return user

