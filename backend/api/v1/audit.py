"""
Audit & Explainability API Router (/api/v1/audit).
Provides immutable, read-only access to the governance audit log with search,
filtering, pagination, and decision explainability trace.
"""

import math
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.core.permissions import require_permissions
from backend.database.models import (
    AuditLogORM,
    DecisionORM,
    UserORM,
    VoteORM,
)
from backend.database.session import get_db
from backend.schemas.governance_domain import (
    AuditLogOut,
    PaginatedAuditLogsOut,
)
from backend.services.governance_service import (
    compute_decision_consensus,
    serialize_audit_log,
    serialize_decision,
    serialize_vote,
)

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("", response_model=PaginatedAuditLogsOut)
async def list_audit_logs(
    search: Optional[str] = Query(default=None),
    compliance_status: Optional[str] = Query(default=None),
    actor_type: Optional[str] = Query(default=None),
    event_type: Optional[str] = Query(default=None),
    decision_id: Optional[uuid.UUID] = Query(default=None),
    date_from: Optional[datetime] = Query(default=None),
    date_to: Optional[datetime] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    current_user: UserORM = Depends(require_permissions("audit:read")),
    db: Session = Depends(get_db),
) -> PaginatedAuditLogsOut:
    stmt = select(AuditLogORM)

    if search and search.strip():
        q = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                AuditLogORM.action.ilike(q),
                AuditLogORM.actor_name.ilike(q),
                AuditLogORM.audit_hash.ilike(q),
                AuditLogORM.event_type.ilike(q),
            )
        )

    if compliance_status:
        stmt = stmt.where(AuditLogORM.compliance_status == compliance_status)
    if actor_type:
        stmt = stmt.where(AuditLogORM.actor_type == actor_type)
    if event_type:
        stmt = stmt.where(AuditLogORM.event_type == event_type)
    if decision_id is not None:
        stmt = stmt.where(AuditLogORM.decision_id == decision_id)
    if date_from is not None:
        stmt = stmt.where(AuditLogORM.timestamp >= date_from)
    if date_to is not None:
        stmt = stmt.where(AuditLogORM.timestamp <= date_to)

    total = (
        db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        or 0
    )

    stmt = (
        stmt.order_by(AuditLogORM.timestamp.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = list(db.execute(stmt).scalars().all())

    decision_titles = {
        d.id: d.title
        for d in db.execute(select(DecisionORM.id, DecisionORM.title)).all()
    }

    items = [
        serialize_audit_log(
            row, decision_title=decision_titles.get(row.decision_id) if row.decision_id else None
        )
        for row in rows
    ]
    total_pages = max(1, math.ceil(total / page_size))

    return PaginatedAuditLogsOut(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/decision/{decision_id}")
async def get_decision_explainability_and_audit(
    decision_id: uuid.UUID,
    current_user: UserORM = Depends(require_permissions("audit:read")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    decision = db.execute(
        select(DecisionORM).where(DecisionORM.id == decision_id)
    ).scalar_one_or_none()
    if decision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found"
        )

    logs = list(
        db.execute(
            select(AuditLogORM)
            .where(AuditLogORM.decision_id == decision.id)
            .order_by(AuditLogORM.timestamp.desc())
        )
        .scalars()
        .all()
    )
    votes = list(
        db.execute(
            select(VoteORM)
            .where(VoteORM.decision_id == decision.id)
            .order_by(VoteORM.timestamp.asc())
        )
        .scalars()
        .all()
    )
    consensus = compute_decision_consensus(decision)

    return {
        "decision": serialize_decision(db, decision).model_dump(mode="json"),
        "consensus": consensus.model_dump(mode="json"),
        "votes": [serialize_vote(v).model_dump(mode="json") for v in votes],
        "audit_trail": [
            serialize_audit_log(log, decision_title=decision.title).model_dump(mode="json")
            for log in logs
        ],
    }

