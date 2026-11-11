"""
Database-backed Authentication & Session Management Service for ParallaxAI.
Implements registration, login, Argon2id verification, short-lived JWT access tokens,
hashed refresh token rotation with reuse detection, session revocation, and password reset.
"""

import hashlib
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.security import (
    create_access_token,
    generate_opaque_token,
    hash_opaque_token,
    hash_password,
    needs_rehash,
    verify_password,
)
from backend.database.models import (
    AuditLogORM,
    PasswordResetTokenORM,
    RefreshTokenORM,
    RoleORM,
    UserORM,
    UserRoleORM,
    utc_now,
)
from backend.schemas.auth import RegisterRequest, UserAuthOut


def get_user_permissions(user: UserORM) -> List[str]:
    """Collect unique permission names across all roles assigned to the user."""
    perms = set()
    for role in user.roles:
        for perm in role.permissions:
            perms.add(perm.name)
    return sorted(perms)


def build_user_auth_out(user: UserORM) -> UserAuthOut:
    """Serialize a UserORM instance with roles and permissions into UserAuthOut."""
    roles = user.role_names
    if not roles:
        roles = ["VIEWER"]
    primary = user.primary_role
    return UserAuthOut(
        id=user.id,
        username=user.username or user.email.split("@")[0],
        email=user.email,
        full_name=user.full_name,
        role=primary,
        roles=roles,
        permissions=get_user_permissions(user),
        is_active=user.is_active,
        is_verified=user.is_verified,
        auth_provider=user.auth_provider,
        preferences=user.preferences or {},
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


def _derive_unique_username(session: Session, email: str, requested_username: Optional[str]) -> str:
    if requested_username:
        candidate = requested_username.strip().lower()
        existing = session.execute(
            select(UserORM).where(func.lower(UserORM.username) == candidate)
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username is already taken",
            )
        return candidate

    base = re.sub(r"[^a-z0-9._-]", "", email.split("@")[0].lower()) or "user"
    candidate = base[:48]
    suffix = 1
    while (
        session.execute(
            select(UserORM).where(func.lower(UserORM.username) == candidate)
        ).scalar_one_or_none()
        is not None
    ):
        candidate = f"{base[:40]}_{suffix}"
        suffix += 1
    return candidate


def register_user(
    session: Session,
    data: RegisterRequest,
    ip_address: Optional[str] = None,
) -> UserORM:
    """
    Register a new user account with Argon2id password hashing and safe default VIEWER role.
    Prevents duplicate emails and self-assigned privileged roles.
    """
    normalized_email = data.email.strip().lower()

    existing_email = session.execute(
        select(UserORM).where(func.lower(UserORM.email) == normalized_email)
    ).scalar_one_or_none()
    if existing_email is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists",
        )

    username = _derive_unique_username(session, normalized_email, data.username)
    now = utc_now()

    user = UserORM(
        id=uuid.uuid4(),
        username=username,
        email=normalized_email,
        full_name=data.full_name.strip(),
        password_hash=hash_password(data.password),
        is_active=True,
        is_verified=False,
        auth_provider="local",
        preferences={},
        created_at=now,
        updated_at=now,
    )
    session.add(user)
    session.flush()

    # Assign safe default role: VIEWER
    viewer_role = session.execute(
        select(RoleORM).where(RoleORM.name == "VIEWER")
    ).scalar_one_or_none()
    if viewer_role is None:
        viewer_role = RoleORM(
            id=uuid.uuid4(),
            name="VIEWER",
            description="Read-only observer with visibility into decisions, voting, governance, and fairness metrics",
            is_system=True,
            created_at=now,
            updated_at=now,
        )
        session.add(viewer_role)
        session.flush()

    session.add(
        UserRoleORM(
            id=uuid.uuid4(),
            user_id=user.id,
            role_id=viewer_role.id,
            assigned_at=now,
        )
    )

    # Record audit log
    audit_hash = hashlib.sha256(f"register:{user.id}:{now.isoformat()}".encode()).hexdigest()
    session.add(
        AuditLogORM(
            id=uuid.uuid4(),
            actor_user_id=user.id,
            actor_name=user.full_name,
            actor_type="user",
            event_type="user_registered",
            action=f"New user registered: {user.email} (assigned role: VIEWER)",
            agent_actions=[],
            rules_applied=[],
            compliance_status="compliant",
            audit_hash=f"sha256_{audit_hash[:32]}",
            metadata_json={"ip_address": ip_address or "unknown", "default_role": "VIEWER"},
            timestamp=now,
        )
    )

    session.commit()
    session.refresh(user)
    return user


def authenticate_user_db(
    session: Session,
    identifier: str,
    password: str,
) -> UserORM:
    """
    Authenticate a user by email or username against PostgreSQL using Argon2id.
    Enforces account activation status.
    """
    ident_clean = identifier.strip().lower()
    user = session.execute(
        select(UserORM).where(
            or_(
                func.lower(UserORM.email) == ident_clean,
                func.lower(UserORM.username) == ident_clean,
            )
        )
    ).scalar_one_or_none()

    if user is None or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email/username or password",
        )

    if not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email/username or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Please contact an administrator.",
        )

    now = utc_now()
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    user.last_login_at = now
    user.updated_at = now
    session.commit()
    session.refresh(user)
    return user


def issue_token_pair(
    session: Session,
    user: UserORM,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
    remember_me: bool = False,
    family_id: Optional[uuid.UUID] = None,
) -> Tuple[str, str, RefreshTokenORM]:
    """
    Issue a short-lived JWT access token and a hashed database-backed refresh token.
    Returns (access_token, raw_refresh_token, refresh_token_orm).
    """
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated.",
        )

    access_token = create_access_token(
        user_id=user.id,
        username=user.username,
        email=user.email,
        role=user.primary_role,
    )

    raw_refresh = generate_opaque_token(48)
    refresh_hash = hash_opaque_token(raw_refresh)
    now = utc_now()
    refresh_days = 30 if remember_me else settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS

    refresh_record = RefreshTokenORM(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=refresh_hash,
        family_id=family_id or uuid.uuid4(),
        is_revoked=False,
        expires_at=now + timedelta(days=refresh_days),
        user_agent=(user_agent or "")[:500] if user_agent else None,
        ip_address=(ip_address or "")[:64] if ip_address else None,
        created_at=now,
    )
    session.add(refresh_record)
    session.commit()
    session.refresh(refresh_record)
    return access_token, raw_refresh, refresh_record


def rotate_refresh_token(
    session: Session,
    raw_refresh_token: str,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> Tuple[UserORM, str, str]:
    """
    Validate and rotate a refresh token.
    - If the token is already revoked (token reuse detected), revokes the entire token family.
    - If expired, marks revoked and rejects.
    - If user is disabled, revokes all user sessions and rejects.
    - Otherwise marks current token revoked, links replaced_by_id, and issues a new token pair.
    """
    if not raw_refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is missing",
        )

    token_hash = hash_opaque_token(raw_refresh_token)
    token_record = session.execute(
        select(RefreshTokenORM).where(RefreshTokenORM.token_hash == token_hash)
    ).scalar_one_or_none()

    if token_record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    now = utc_now()

    # Reuse detection: if an already-revoked refresh token is presented, revoke the entire family
    if token_record.is_revoked:
        session.execute(
            update(RefreshTokenORM)
            .where(RefreshTokenORM.family_id == token_record.family_id)
            .values(is_revoked=True, revoked_at=now)
        )
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has already been revoked; session family invalidated",
        )

    expires_at = token_record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= now:
        token_record.is_revoked = True
        token_record.revoked_at = now
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired",
        )

    user = session.execute(
        select(UserORM).where(UserORM.id == token_record.user_id)
    ).scalar_one_or_none()

    if user is None or not user.is_active:
        session.execute(
            update(RefreshTokenORM)
            .where(RefreshTokenORM.user_id == token_record.user_id)
            .values(is_revoked=True, revoked_at=now)
        )
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated or no longer exists",
        )

    # Mark old token as revoked and issue replacement in the same family
    token_record.is_revoked = True
    token_record.revoked_at = now

    raw_new_refresh = generate_opaque_token(48)
    new_refresh_hash = hash_opaque_token(raw_new_refresh)
    new_record = RefreshTokenORM(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=new_refresh_hash,
        family_id=token_record.family_id,
        is_revoked=False,
        expires_at=now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        user_agent=(user_agent or "")[:500] if user_agent else token_record.user_agent,
        ip_address=(ip_address or "")[:64] if ip_address else token_record.ip_address,
        created_at=now,
    )
    session.add(new_record)
    session.flush()
    token_record.replaced_by_id = new_record.id

    access_token = create_access_token(
        user_id=user.id,
        username=user.username,
        email=user.email,
        role=user.primary_role,
    )

    session.commit()
    session.refresh(user)
    return user, access_token, raw_new_refresh


def revoke_refresh_token(
    session: Session,
    raw_refresh_token: Optional[str],
    user_id: Optional[uuid.UUID] = None,
) -> bool:
    """Revoke a specific refresh token by its raw value."""
    if not raw_refresh_token:
        return False

    token_hash = hash_opaque_token(raw_refresh_token)
    stmt = select(RefreshTokenORM).where(RefreshTokenORM.token_hash == token_hash)
    if user_id is not None:
        stmt = stmt.where(RefreshTokenORM.user_id == user_id)

    token_record = session.execute(stmt).scalar_one_or_none()
    if token_record is None:
        return False

    if not token_record.is_revoked:
        token_record.is_revoked = True
        token_record.revoked_at = utc_now()
        session.commit()
    return True


def revoke_all_user_sessions(session: Session, user_id: uuid.UUID) -> int:
    """Revoke all active refresh tokens for a user."""
    now = utc_now()
    result = session.execute(
        update(RefreshTokenORM)
        .where(
            RefreshTokenORM.user_id == user_id,
            RefreshTokenORM.is_revoked == False,  # noqa: E712
        )
        .values(is_revoked=True, revoked_at=now)
    )
    session.commit()
    return int(result.rowcount or 0)


def revoke_session_by_id(
    session: Session, session_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    """Revoke a specific refresh token session by its ID for a given user."""
    token_record = session.execute(
        select(RefreshTokenORM).where(
            RefreshTokenORM.id == session_id,
            RefreshTokenORM.user_id == user_id,
        )
    ).scalar_one_or_none()
    if token_record is None:
        return False
    token_record.is_revoked = True
    token_record.revoked_at = utc_now()
    session.commit()
    return True


def get_user_active_sessions(
    session: Session, user_id: uuid.UUID
) -> List[RefreshTokenORM]:
    """List active (non-revoked, non-expired) refresh token sessions for a user."""
    now = utc_now()
    return list(
        session.execute(
            select(RefreshTokenORM)
            .where(
                RefreshTokenORM.user_id == user_id,
                RefreshTokenORM.is_revoked == False,  # noqa: E712
                RefreshTokenORM.expires_at > now,
            )
            .order_by(RefreshTokenORM.created_at.desc())
        ).scalars()
    )


def set_user_active_status(
    session: Session,
    target_user_id: uuid.UUID,
    is_active: bool,
) -> UserORM:
    """Activate or deactivate a user account; revokes all sessions when deactivating."""
    user = session.execute(
        select(UserORM).where(UserORM.id == target_user_id)
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    user.is_active = is_active
    user.updated_at = utc_now()
    if not is_active:
        session.execute(
            update(RefreshTokenORM)
            .where(
                RefreshTokenORM.user_id == target_user_id,
                RefreshTokenORM.is_revoked == False,  # noqa: E712
            )
            .values(is_revoked=True, revoked_at=utc_now())
        )
    session.commit()
    session.refresh(user)
    return user


def change_user_password(
    session: Session,
    user: UserORM,
    current_password: str,
    new_password: str,
) -> None:
    """Verify current password, update with Argon2id hash, and revoke existing refresh tokens."""
    if not user.password_hash or not verify_password(current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    now = utc_now()
    user.password_hash = hash_password(new_password)
    user.updated_at = now
    session.execute(
        update(RefreshTokenORM)
        .where(
            RefreshTokenORM.user_id == user.id,
            RefreshTokenORM.is_revoked == False,  # noqa: E712
        )
        .values(is_revoked=True, revoked_at=now)
    )
    session.commit()


def is_email_provider_configured() -> bool:
    """Check whether an SMTP/email delivery service is configured."""
    return bool(os.getenv("SMTP_HOST", "").strip() and os.getenv("SMTP_FROM_EMAIL", "").strip())


def create_password_reset_token(
    session: Session,
    email: str,
    ip_address: Optional[str] = None,
) -> Tuple[Optional[str], bool]:
    """
    Create a hashed password reset token in PostgreSQL if the user exists and is active.
    Returns (raw_token_or_none, email_provider_configured).
    Never pretends that an email was sent when no email provider is configured.
    """
    email_configured = is_email_provider_configured()
    normalized_email = email.strip().lower()
    user = session.execute(
        select(UserORM).where(func.lower(UserORM.email) == normalized_email)
    ).scalar_one_or_none()

    if user is None or not user.is_active:
        return None, email_configured

    raw_token = generate_opaque_token(36)
    token_hash = hash_opaque_token(raw_token)
    now = utc_now()

    reset_entry = PasswordResetTokenORM(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=token_hash,
        expires_at=now + timedelta(hours=1),
        ip_address=(ip_address or "")[:64] if ip_address else None,
        created_at=now,
    )
    session.add(reset_entry)
    session.commit()
    return raw_token, email_configured


def reset_password_with_token(
    session: Session,
    raw_token: str,
    new_password: str,
) -> UserORM:
    """Validate a password reset token, update the user's password, and revoke active sessions."""
    token_hash = hash_opaque_token(raw_token)
    reset_entry = session.execute(
        select(PasswordResetTokenORM).where(
            PasswordResetTokenORM.token_hash == token_hash
        )
    ).scalar_one_or_none()

    now = utc_now()
    if reset_entry is None or reset_entry.used_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or already used password reset token",
        )

    expires_at = reset_entry.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset token has expired",
        )

    user = session.execute(
        select(UserORM).where(UserORM.id == reset_entry.user_id)
    ).scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated or does not exist",
        )

    reset_entry.used_at = now
    user.password_hash = hash_password(new_password)
    user.updated_at = now

    # Revoke all active refresh tokens upon password reset
    session.execute(
        update(RefreshTokenORM)
        .where(
            RefreshTokenORM.user_id == user.id,
            RefreshTokenORM.is_revoked == False,  # noqa: E712
        )
        .values(is_revoked=True, revoked_at=now)
    )
    session.commit()
    session.refresh(user)
    return user

