"""
Roles & Permissions RBAC API Router (/api/v1/roles).
Allows inspecting roles and granular permissions and managing role-permission mappings.
"""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from backend.core.permissions import require_permissions
from backend.database.models import (
    PermissionORM,
    RoleORM,
    RolePermissionORM,
    UserORM,
    UserRoleORM,
    utc_now,
)
from backend.database.session import get_db
from backend.schemas.users_roles import (
    PermissionOut,
    RoleCreateRequest,
    RoleOut,
    RolePermissionsUpdateRequest,
)
from backend.services.governance_service import record_audit_log

router = APIRouter(prefix="/api/v1/roles", tags=["Roles & Permissions"])


def _to_role_out(session: Session, role: RoleORM) -> RoleOut:
    user_count = session.execute(
        select(func.count(UserRoleORM.id)).where(UserRoleORM.role_id == role.id)
    ).scalar_one()
    perms = sorted({p.name for p in role.permissions})
    return RoleOut(
        id=role.id,
        name=role.name,
        description=role.description,
        is_system=role.is_system,
        permissions=perms,
        user_count=int(user_count or 0),
        created_at=role.created_at,
        updated_at=role.updated_at,
    )


@router.get("", response_model=List[RoleOut])
async def list_roles(
    current_user: UserORM = Depends(
        require_permissions("users:read", "roles:manage", require_all=False)
    ),
    session: Session = Depends(get_db),
) -> List[RoleOut]:
    """List all roles with their assigned permissions and user counts."""
    roles = list(
        session.execute(select(RoleORM).order_by(RoleORM.name)).scalars().all()
    )
    return [_to_role_out(session, r) for r in roles]


@router.get("/permissions", response_model=List[PermissionOut])
async def list_permissions(
    current_user: UserORM = Depends(
        require_permissions("users:read", "roles:manage", require_all=False)
    ),
    session: Session = Depends(get_db),
) -> List[PermissionOut]:
    """List all granular permissions defined in the platform."""
    perms = list(
        session.execute(
            select(PermissionORM).order_by(PermissionORM.module, PermissionORM.name)
        ).scalars()
    )
    return [
        PermissionOut(
            id=p.id,
            name=p.name,
            module=p.module,
            description=p.description,
        )
        for p in perms
    ]


@router.post("", response_model=RoleOut, status_code=status.HTTP_201_CREATED)
async def create_role(
    payload: RoleCreateRequest,
    current_user: UserORM = Depends(require_permissions("roles:manage")),
    session: Session = Depends(get_db),
) -> RoleOut:
    """Create a new custom role with specified granular permissions."""
    role_name = payload.name.strip().upper().replace(" ", "_")
    existing = session.execute(
        select(RoleORM).where(func.upper(RoleORM.name) == role_name)
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Role '{role_name}' already exists",
        )

    now = utc_now()
    role = RoleORM(
        id=uuid.uuid4(),
        name=role_name,
        description=payload.description.strip(),
        is_system=False,
        created_at=now,
        updated_at=now,
    )
    session.add(role)
    session.flush()

    for perm_name in sorted(set(payload.permissions)):
        perm = session.execute(
            select(PermissionORM).where(PermissionORM.name == perm_name)
        ).scalar_one_or_none()
        if perm is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown permission '{perm_name}'",
            )
        session.add(
            RolePermissionORM(
                id=uuid.uuid4(),
                role_id=role.id,
                permission_id=perm.id,
                created_at=now,
            )
        )

    record_audit_log(
        session=session,
        action=f"Created role '{role_name}' with {len(payload.permissions)} permissions",
        event_type="role_created",
        actor_user=current_user,
        actor_type="user",
        metadata={"role_name": role_name, "permissions": payload.permissions},
    )
    session.commit()
    session.refresh(role)
    return _to_role_out(session, role)


@router.put("/{role_id}/permissions", response_model=RoleOut)
async def update_role_permissions(
    role_id: uuid.UUID,
    payload: RolePermissionsUpdateRequest,
    current_user: UserORM = Depends(require_permissions("roles:manage")),
    session: Session = Depends(get_db),
) -> RoleOut:
    """Update the granular permissions assigned to a role."""
    role = session.execute(
        select(RoleORM).where(RoleORM.id == role_id)
    ).scalar_one_or_none()
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
        )

    if role.name == "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The SUPER_ADMIN role permissions cannot be restricted",
        )

    requested_perms = sorted(set(payload.permissions))
    perm_objs: List[PermissionORM] = []
    for p_name in requested_perms:
        p_obj = session.execute(
            select(PermissionORM).where(PermissionORM.name == p_name)
        ).scalar_one_or_none()
        if p_obj is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown permission '{p_name}'",
            )
        perm_objs.append(p_obj)

    old_perms = sorted({p.name for p in role.permissions})
    session.execute(
        delete(RolePermissionORM).where(RolePermissionORM.role_id == role.id)
    )
    session.flush()

    now = utc_now()
    for p_obj in perm_objs:
        session.add(
            RolePermissionORM(
                id=uuid.uuid4(),
                role_id=role.id,
                permission_id=p_obj.id,
                created_at=now,
            )
        )

    if payload.description is not None:
        role.description = payload.description.strip()
    role.updated_at = now

    record_audit_log(
        session=session,
        action=f"Updated permissions for role '{role.name}' ({len(old_perms)} -> {len(requested_perms)})",
        event_type="role_permissions_updated",
        actor_user=current_user,
        actor_type="user",
        metadata={
            "role_id": str(role.id),
            "role_name": role.name,
            "previous_permissions": old_perms,
            "new_permissions": requested_perms,
        },
    )
    session.commit()
    session.expire(role, ["role_permissions"])
    session.refresh(role)
    return _to_role_out(session, role)

