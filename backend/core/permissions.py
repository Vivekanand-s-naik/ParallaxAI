"""
Granular Role-Based Access Control (RBAC) dependencies for FastAPI.
Evaluates permissions dynamically against PostgreSQL on every request.
"""

import uuid
from typing import Callable, Sequence, Set

from fastapi import Depends, HTTPException, status

from backend.auth import get_current_user_orm
from backend.database.models import UserORM
from backend.services.auth_service import get_user_permissions


def user_has_permission(user: UserORM, permission: str) -> bool:
    """Check whether a UserORM instance holds a specific permission (or SUPER_ADMIN)."""
    if not user.is_active:
        return False
    role_names = {r.upper() for r in user.role_names}
    if "SUPER_ADMIN" in role_names:
        return True
    perms = set(get_user_permissions(user))
    return permission in perms


def user_has_any_permission(user: UserORM, permissions: Sequence[str]) -> bool:
    """Check whether a UserORM instance holds at least one of the given permissions."""
    if not user.is_active:
        return False
    role_names = {r.upper() for r in user.role_names}
    if "SUPER_ADMIN" in role_names:
        return True
    perms = set(get_user_permissions(user))
    return bool(perms.intersection(permissions))


def require_permissions(
    *required_permissions: str, require_all: bool = True
) -> Callable[[UserORM], UserORM]:
    """
    FastAPI dependency factory requiring the authenticated user to hold the specified
    granular permissions in PostgreSQL.
    """

    def dependency(current_user: UserORM = Depends(get_current_user_orm)) -> UserORM:
        role_names = {r.upper() for r in current_user.role_names}
        if "SUPER_ADMIN" in role_names:
            return current_user

        user_perms: Set[str] = set(get_user_permissions(current_user))
        if require_all:
            missing = [p for p in required_permissions if p not in user_perms]
            if missing:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required: {', '.join(missing)}",
                )
        else:
            if not any(p in user_perms for p in required_permissions):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Requires at least one of: {', '.join(required_permissions)}",
                )
        return current_user

    return dependency


def require_roles(*allowed_roles: str) -> Callable[[UserORM], UserORM]:
    """
    FastAPI dependency factory requiring the authenticated user to hold at least one
    of the specified role names in PostgreSQL.
    """
    normalized_allowed = {r.upper() for r in allowed_roles}

    def dependency(current_user: UserORM = Depends(get_current_user_orm)) -> UserORM:
        user_roles = {r.upper() for r in current_user.role_names}
        if "SUPER_ADMIN" in user_roles:
            return current_user
        if not user_roles.intersection(normalized_allowed):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role not assigned. Allowed roles: {', '.join(sorted(normalized_allowed))}",
            )
        return current_user

    return dependency


def assert_owner_or_permission(
    current_user: UserORM,
    owner_user_id: uuid.UUID | None,
    fallback_permission: str,
) -> None:
    """
    Verify that `current_user` is either the resource owner (`owner_user_id == current_user.id`)
    or holds `fallback_permission` (or `SUPER_ADMIN`).
    """
    if owner_user_id is not None and current_user.id == owner_user_id:
        return
    if user_has_permission(current_user, fallback_permission):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Ownership or '{fallback_permission}' permission required",
    )

