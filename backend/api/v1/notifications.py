"""
Notification Center API Router (/api/v1/notifications).
Supports listing notifications with filters, marking single or all notifications as read,
creating notifications, and deleting notifications in PostgreSQL.
"""

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.core.permissions import require_permissions, user_has_any_permission
from backend.database.models import NotificationORM, UserORM, utc_now
from backend.database.session import get_db
from backend.schemas.governance_domain import (
    NotificationCreateRequest,
    NotificationOut,
)
from backend.services.governance_service import serialize_notification
from backend.services.runtime import websocket_manager

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(
    is_read: Optional[bool] = Query(default=None),
    type: Optional[str] = Query(default=None),
    priority: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=300),
    current_user: UserORM = Depends(require_permissions("notifications:read")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    stmt = select(NotificationORM)
    if is_read is not None:
        stmt = stmt.where(NotificationORM.is_read.is_(is_read))
    if type:
        stmt = stmt.where(NotificationORM.type == type)
    if priority:
        stmt = stmt.where(NotificationORM.priority == priority.lower())

    stmt = stmt.order_by(NotificationORM.timestamp.desc()).limit(limit)
    rows = list(db.execute(stmt).scalars().all())

    unread_count = (
        db.execute(
            select(func.count())
            .select_from(NotificationORM)
            .where(NotificationORM.is_read.is_(False))
        ).scalar_one()
        or 0
    )

    return {
        "items": [serialize_notification(n).model_dump(mode="json") for n in rows],
        "unread_count": unread_count,
        "total": len(rows),
    }


@router.post("", response_model=NotificationOut, status_code=status.HTTP_201_CREATED)
async def create_notification(
    payload: NotificationCreateRequest,
    current_user: UserORM = Depends(require_permissions("notifications:read")),
    db: Session = Depends(get_db),
) -> NotificationOut:
    if not user_has_any_permission(
        current_user, ["governance:manage", "system:configure", "decisions:escalate"]
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to create governance notifications",
        )

    notif = NotificationORM(
        id=uuid.uuid4(),
        type=payload.type,
        title=payload.title.strip(),
        message=payload.message.strip(),
        priority=payload.priority,
        is_read=False,
        related_decision_id=payload.related_decision_id,
        metadata_json=payload.metadata or {},
        timestamp=utc_now(),
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)

    serialized = serialize_notification(notif)
    await websocket_manager.broadcast(
        {
            "type": "notification_created",
            "data": serialized.model_dump(mode="json"),
        }
    )
    return serialized


@router.put("/{notification_id}/read", response_model=NotificationOut)
async def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: UserORM = Depends(require_permissions("notifications:read")),
    db: Session = Depends(get_db),
) -> NotificationOut:
    notif = db.execute(
        select(NotificationORM).where(NotificationORM.id == notification_id)
    ).scalar_one_or_none()
    if notif is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
        )

    notif.is_read = True
    notif.read_at = utc_now()
    db.commit()
    db.refresh(notif)

    serialized = serialize_notification(notif)
    await websocket_manager.broadcast(
        {
            "type": "notification_updated",
            "data": serialized.model_dump(mode="json"),
        }
    )
    return serialized


@router.post("/mark-all-read")
async def mark_all_notifications_read(
    current_user: UserORM = Depends(require_permissions("notifications:read")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    unread = list(
        db.execute(
            select(NotificationORM).where(NotificationORM.is_read.is_(False))
        )
        .scalars()
        .all()
    )
    now = utc_now()
    for n in unread:
        n.is_read = True
        n.read_at = now
    db.commit()

    await websocket_manager.broadcast(
        {
            "type": "notifications_marked_all_read",
            "data": {"updated_count": len(unread)},
        }
    )
    return {"message": "All notifications marked as read", "updated_count": len(unread)}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: uuid.UUID,
    current_user: UserORM = Depends(require_permissions("notifications:read")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    notif = db.execute(
        select(NotificationORM).where(NotificationORM.id == notification_id)
    ).scalar_one_or_none()
    if notif is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
        )

    db.delete(notif)
    db.commit()
    return {"message": "Notification deleted", "id": str(notification_id)}

