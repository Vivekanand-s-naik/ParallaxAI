"""
Users Administration & Profile API Router (/api/v1/users).
Enforces RBAC permissions (users:read, users:manage, roles:manage) and ownership checks.
"""

import math
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from backend.auth import get_current_user_orm
from backend.core.permissions import (
    assert_owner_or_permission,
    require_permissions,
)
from backend.database.models import (
    AuditLogORM,
    RoleORM,
    UserORM,
    UserRoleORM,
    VoteORM,
    utc_now,
)
from backend.database.session import get_db
from backend.schemas.users_roles import (
    PaginatedUsersOut,
    UserAdminOut,
    UserProfileUpdateRequest,
    UserRolesUpdateRequest,
    UserStatusUpdateRequest,
)
from backend.services.auth_service import get_user_permissions, set_user_active_status
from backend.services.governance_service import (
    record_audit_log,
    serialize_audit_log,
    serialize_vote,
)

router = APIRouter(prefix="/api/v1/users", tags=["Users"])


def _to_user_admin_out(user: UserORM) -> UserAdminOut:
    return UserAdminOut(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        auth_provider=user.auth_provider,
        primary_role=user.primary_role,
        roles=user.role_names,
        permissions=get_user_permissions(user),
        preferences=user.preferences or {},
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.get("", response_model=PaginatedUsersOut)
async def list_users(
    search: Optional[str] = Query(default=None),
    role: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: UserORM = Depends(require_permissions("users:read")),
    session: Session = Depends(get_db),
) -> PaginatedUsersOut:
    """List users with search, role, and account status filtering."""
    stmt = select(UserORM).order_by(UserORM.created_at.desc())
    if is_active is not None:
        stmt = stmt.where(UserORM.is_active == is_active)
    if search:
        q = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(UserORM.email).like(q),
                func.lower(UserORM.full_name).like(q),
                func.lower(func.coalesce(UserORM.username, "")).like(q),
            )
        )

    users = list(session.execute(stmt).scalars().all())
    if role:
        role_upper = role.strip().upper()
        users = [u for u in users if role_upper in {r.upper() for r in u.role_names}]

    total = len(users)
    total_pages = max(1, math.ceil(total / page_size))
    start = (page - 1) * page_size
    sliced = users[start : start + page_size]

    return PaginatedUsersOut(
        items=[_to_user_admin_out(u) for u in sliced],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/me", response_model=UserAdminOut)
async def get_my_profile(
    current_user: UserORM = Depends(get_current_user_orm),
) -> UserAdminOut:
    """Return the current authenticated user's profile and preferences."""
    return _to_user_admin_out(current_user)


@router.patch("/me", response_model=UserAdminOut)
async def update_my_profile(
    payload: UserProfileUpdateRequest,
    current_user: UserORM = Depends(get_current_user_orm),
    session: Session = Depends(get_db),
) -> UserAdminOut:
    """Update the current user's own profile name and preferences."""
    if payload.full_name is not None:
        current_user.full_name = payload.full_name.strip()
    if payload.preferences is not None:
        merged = dict(current_user.preferences or {})
        merged.update(payload.preferences)
        current_user.preferences = merged
    current_user.updated_at = utc_now()
    session.commit()
    session.refresh(current_user)
    return _to_user_admin_out(current_user)


@router.get("/{user_id}", response_model=UserAdminOut)
async def get_user_by_id(
    user_id: uuid.UUID,
    current_user: UserORM = Depends(get_current_user_orm),
    session: Session = Depends(get_db),
) -> UserAdminOut:
    """Retrieve a user profile (allowed for the user themselves or holders of users:read)."""
    assert_owner_or_permission(current_user, user_id, "users:read")
    target = session.execute(
        select(UserORM).where(UserORM.id == user_id)
    ).scalar_one_or_none()
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return _to_user_admin_out(target)


@router.patch("/{user_id}/status", response_model=UserAdminOut)
async def update_user_status(
    user_id: uuid.UUID,
    payload: UserStatusUpdateRequest,
    current_user: UserORM = Depends(require_permissions("users:manage")),
    session: Session = Depends(get_db),
) -> UserAdminOut:
    """Activate or deactivate a user account. Deactivating revokes all active sessions."""
    if user_id == current_user.id and not payload.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account",
        )

    target = session.execute(
        select(UserORM).where(UserORM.id == user_id)
    ).scalar_one_or_none()
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if (
        "SUPER_ADMIN" in {r.upper() for r in target.role_names}
        and "SUPER_ADMIN" not in {r.upper() for r in current_user.role_names}
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a SUPER_ADMIN may modify another SUPER_ADMIN account",
        )

    prev_state = "active" if target.is_active else "inactive"
    new_state = "active" if payload.is_active else "inactive"
    updated_user = set_user_active_status(session, user_id, payload.is_active)

    record_audit_log(
        session=session,
        action=(
            f"User account {updated_user.email} status changed from {prev_state} to {new_state}"
            + (f" — Reason: {payload.reason}" if payload.reason else "")
        ),
        event_type="user_status_updated",
        actor_user=current_user,
        actor_type="user",
        previous_status=prev_state,
        new_status=new_state,
        metadata={"target_user_id": str(user_id), "is_active": payload.is_active},
    )
    session.commit()
    session.refresh(updated_user)
    return _to_user_admin_out(updated_user)


@router.put("/{user_id}/roles", response_model=UserAdminOut)
async def update_user_roles(
    user_id: uuid.UUID,
    payload: UserRolesUpdateRequest,
    current_user: UserORM = Depends(
        require_permissions("users:manage", "roles:manage", require_all=False)
    ),
    session: Session = Depends(get_db),
) -> UserAdminOut:
    """Assign roles to a user account with privilege escalation protection and audit logging."""
    target = session.execute(
        select(UserORM).where(UserORM.id == user_id)
    ).scalar_one_or_none()
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    requested_names = sorted({r.strip().upper() for r in payload.roles if r.strip()})
    if not requested_names:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one valid role must be specified",
        )

    actor_is_super = "SUPER_ADMIN" in {r.upper() for r in current_user.role_names}
    target_was_super = "SUPER_ADMIN" in {r.upper() for r in target.role_names}

    if ("SUPER_ADMIN" in requested_names or target_was_super) and not actor_is_super:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a SUPER_ADMIN can assign or modify the SUPER_ADMIN role",
        )

    if user_id == current_user.id and target_was_super and "SUPER_ADMIN" not in requested_names:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot remove the SUPER_ADMIN role from your own account",
        )

    role_objs: List[RoleORM] = []
    for r_name in requested_names:
        r_obj = session.execute(
            select(RoleORM).where(func.upper(RoleORM.name) == r_name)
        ).scalar_one_or_none()
        if r_obj is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role '{r_name}' does not exist",
            )
        role_objs.append(r_obj)

    previous_roles = target.role_names
    session.execute(delete(UserRoleORM).where(UserRoleORM.user_id == target.id))
    session.flush()

    now = utc_now()
    for r_obj in role_objs:
        session.add(
            UserRoleORM(
                id=uuid.uuid4(),
                user_id=target.id,
                role_id=r_obj.id,
                assigned_by_id=current_user.id,
                assigned_at=now,
            )
        )
    target.updated_at = now

    record_audit_log(
        session=session,
        action=(
            f"Updated roles for {target.email}: {previous_roles} -> {requested_names}"
            + (f" ({payload.reason})" if payload.reason else "")
        ),
        event_type="user_roles_updated",
        actor_user=current_user,
        actor_type="user",
        previous_status=",".join(previous_roles),
        new_status=",".join(requested_names),
        metadata={
            "target_user_id": str(target.id),
            "previous_roles": previous_roles,
            "new_roles": requested_names,
        },
    )
    session.commit()
    session.expire(target, ["user_roles"])
    session.refresh(target)
    return _to_user_admin_out(target)


@router.get("/{user_id}/activity")
async def get_user_activity(
    user_id: uuid.UUID,
    current_user: UserORM = Depends(get_current_user_orm),
    session: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Return audit trail and submitted votes for a user (owner or users:read)."""
    assert_owner_or_permission(current_user, user_id, "users:read")
    target = session.execute(
        select(UserORM).where(UserORM.id == user_id)
    ).scalar_one_or_none()
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    logs = list(
        session.execute(
            select(AuditLogORM)
            .where(AuditLogORM.actor_user_id == user_id)
            .order_by(AuditLogORM.timestamp.desc())
            .limit(50)
        ).scalars()
    )
    votes = list(
        session.execute(
            select(VoteORM)
            .where(VoteORM.submitted_by_user_id == user_id)
            .order_by(VoteORM.timestamp.desc())
            .limit(50)
        ).scalars()
    )

    return {
        "user": _to_user_admin_out(target),
        "audit_logs": [serialize_audit_log(log) for log in logs],
        "votes": [serialize_vote(v) for v in votes],
    }

