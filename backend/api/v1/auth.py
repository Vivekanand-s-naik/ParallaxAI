"""
Authentication API Router (/api/v1/auth).
Supports registration, login, logout, short-lived JWT access tokens,
HttpOnly refresh token cookies + rotation + reuse detection, session management,
password change, and honest password-reset / Google OAuth status reporting.
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from backend.auth import get_current_user_orm
from backend.core.config import settings
from backend.database.models import UserORM
from backend.database.session import get_db
from backend.schemas.auth import (
    AuthProvidersStatusOut,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    RegisterRequest,
    ResetPasswordRequest,
    SessionInfoOut,
    TokenResponse,
    UserAuthOut,
)
from backend.services.auth_service import (
    authenticate_user_db,
    build_user_auth_out,
    change_user_password,
    create_password_reset_token,
    get_user_active_sessions,
    is_email_provider_configured,
    issue_token_pair,
    register_user,
    reset_password_with_token,
    revoke_all_user_sessions,
    revoke_refresh_token,
    revoke_session_by_id,
    rotate_refresh_token,
)

REFRESH_COOKIE_NAME = "parallaxai_refresh_token"

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


def _set_refresh_cookie(
    response: Response, raw_refresh_token: str, remember_me: bool = False
) -> None:
    days = 30 if remember_me else settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
    max_age = days * 86400
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=raw_refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,  # type: ignore[arg-type]
        max_age=max_age,
        path="/",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,  # type: ignore[arg-type]
        path="/",
    )


@router.get("/providers", response_model=AuthProvidersStatusOut)
async def get_auth_providers_status() -> AuthProvidersStatusOut:
    """Return honest configuration status for Google OAuth and email password reset."""
    google_ready = settings.is_google_oauth_configured
    email_ready = is_email_provider_configured()
    return AuthProvidersStatusOut(
        local_enabled=True,
        google_oauth_enabled=google_ready,
        google_oauth_message=(
            "Google OAuth 2.0 is active."
            if google_ready
            else "Google Sign-In is currently unavailable: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GOOGLE_REDIRECT_URI are not configured."
        ),
        password_reset_email_enabled=email_ready,
        password_reset_message=(
            "Password reset email delivery is active."
            if email_ready
            else "Outbound email provider (SMTP) is not configured. Password reset tokens are generated in the database, or an administrator can reset your credentials."
        ),
    )


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    session: Session = Depends(get_db),
) -> TokenResponse:
    """Register a new user account (defaulting to VIEWER role) and issue session tokens."""
    ip_addr = _client_ip(request)
    user_agent = request.headers.get("user-agent")
    user = register_user(session, payload, ip_address=ip_addr)
    access_token, raw_refresh, _ = issue_token_pair(
        session,
        user=user,
        user_agent=user_agent,
        ip_address=ip_addr,
        remember_me=False,
    )
    _set_refresh_cookie(response, raw_refresh, remember_me=False)
    return TokenResponse(
        token=access_token,
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=build_user_auth_out(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate user with email or username and return short-lived access token + refresh cookie."""
    ip_addr = _client_ip(request)
    user_agent = request.headers.get("user-agent")
    user = authenticate_user_db(session, payload.identifier, payload.password)
    access_token, raw_refresh, _ = issue_token_pair(
        session,
        user=user,
        user_agent=user_agent,
        ip_address=ip_addr,
        remember_me=payload.remember_me,
    )
    _set_refresh_cookie(response, raw_refresh, remember_me=payload.remember_me)
    return TokenResponse(
        token=access_token,
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=build_user_auth_out(user),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_session_token(
    request: Request,
    response: Response,
    payload: Optional[RefreshTokenRequest] = None,
    cookie_token: Optional[str] = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    session: Session = Depends(get_db),
) -> TokenResponse:
    """Rotate refresh token and issue a fresh JWT access token."""
    raw_token = (payload.refresh_token if payload and payload.refresh_token else None) or cookie_token
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not provided",
        )
    user, new_access_token, new_refresh_token = rotate_refresh_token(
        session,
        raw_refresh_token=raw_token,
        user_agent=request.headers.get("user-agent"),
        ip_address=_client_ip(request),
    )
    _set_refresh_cookie(response, new_refresh_token)
    return TokenResponse(
        token=new_access_token,
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=build_user_auth_out(user),
    )


@router.post("/logout")
async def logout(
    response: Response,
    payload: Optional[LogoutRequest] = None,
    cookie_token: Optional[str] = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    session: Session = Depends(get_db),
):
    """Revoke the current refresh token in PostgreSQL and clear the HttpOnly refresh cookie."""
    raw_token = (payload.refresh_token if payload and payload.refresh_token else None) or cookie_token
    if raw_token:
        revoke_refresh_token(session, raw_refresh_token=raw_token)
    _clear_refresh_cookie(response)
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserAuthOut)
async def get_me(
    current_user: UserORM = Depends(get_current_user_orm),
) -> UserAuthOut:
    """Return the authenticated user's profile, roles, and granular permissions from PostgreSQL."""
    return build_user_auth_out(current_user)


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    response: Response,
    current_user: UserORM = Depends(get_current_user_orm),
    session: Session = Depends(get_db),
):
    """Change the current user's password and revoke older refresh token sessions."""
    change_user_password(
        session,
        user=current_user,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
    _clear_refresh_cookie(response)
    return {"message": "Password updated successfully. Please sign in again with your new password."}


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    session: Session = Depends(get_db),
) -> ForgotPasswordResponse:
    """
    Generate a password reset token in the database.
    Honestly reports if no email provider is configured instead of simulating email delivery.
    """
    _, email_configured = create_password_reset_token(
        session, email=payload.email, ip_address=_client_ip(request)
    )
    if not email_configured:
        return ForgotPasswordResponse(
            status="email_provider_not_configured",
            email_provider_configured=False,
            message=(
                "Password reset architecture is active, but an outbound email provider (SMTP) "
                "has not been configured in this environment. No email was sent. "
                "Please configure SMTP settings or contact a system administrator."
            ),
        )
    return ForgotPasswordResponse(
        status="reset_initiated",
        email_provider_configured=True,
        message="If an active account matches that email address, password reset instructions have been dispatched.",
    )


@router.post("/reset-password")
async def reset_password(
    payload: ResetPasswordRequest,
    session: Session = Depends(get_db),
):
    """Reset a user's password using a valid, non-expired password reset token."""
    reset_password_with_token(
        session, raw_token=payload.token, new_password=payload.new_password
    )
    return {"message": "Password has been reset successfully. You may now sign in."}


@router.get("/sessions", response_model=List[SessionInfoOut])
async def list_active_sessions(
    current_user: UserORM = Depends(get_current_user_orm),
    session: Session = Depends(get_db),
) -> List[SessionInfoOut]:
    """List all active refresh token sessions for the current user."""
    records = get_user_active_sessions(session, current_user.id)
    return [
        SessionInfoOut(
            id=r.id,
            family_id=r.family_id,
            user_agent=r.user_agent,
            ip_address=r.ip_address,
            is_revoked=r.is_revoked,
            expires_at=r.expires_at,
            created_at=r.created_at,
        )
        for r in records
    ]


@router.post("/sessions/revoke-all")
async def revoke_all_sessions(
    response: Response,
    current_user: UserORM = Depends(get_current_user_orm),
    session: Session = Depends(get_db),
):
    """Revoke all active refresh tokens for the current user across all devices."""
    revoked_count = revoke_all_user_sessions(session, current_user.id)
    _clear_refresh_cookie(response)
    return {"message": "All active sessions revoked", "revoked_count": revoked_count}


@router.delete("/sessions/{session_id}")
async def revoke_single_session(
    session_id: uuid.UUID,
    current_user: UserORM = Depends(get_current_user_orm),
    session: Session = Depends(get_db),
):
    """Revoke a specific session by ID for the current user."""
    ok = revoke_session_by_id(session, session_id=session_id, user_id=current_user.id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    return {"message": "Session revoked"}

