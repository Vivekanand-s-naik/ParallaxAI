"""
Governance Console & Policy Engine API Router (/api/v1/governance).
Supports listing, creating, updating, deleting, and validating YAML-based governance rules.
"""

import uuid
from typing import Any, Dict, List, Optional
import yaml

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.permissions import require_permissions, user_has_any_permission
from backend.database.models import GovernanceRuleORM, UserORM, utc_now
from backend.database.session import get_db
from backend.schemas.governance_domain import (
    GovernanceRuleCreateRequest,
    GovernanceRuleOut,
    GovernanceRuleUpdateRequest,
)
from backend.services.governance_service import (
    record_audit_log,
    serialize_governance_rule,
)
from backend.services.runtime import websocket_manager

router = APIRouter(prefix="/api/v1/governance", tags=["governance"])


@router.get("/rules", response_model=List[GovernanceRuleOut])
async def list_governance_rules(
    context: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
    current_user: UserORM = Depends(require_permissions("governance:read")),
    db: Session = Depends(get_db),
) -> List[GovernanceRuleOut]:
    stmt = select(GovernanceRuleORM)
    if context:
        stmt = stmt.where(GovernanceRuleORM.context == context)
    if is_active is not None:
        stmt = stmt.where(GovernanceRuleORM.is_active.is_(is_active))
    stmt = stmt.order_by(GovernanceRuleORM.priority.asc(), GovernanceRuleORM.name.asc())
    rules = list(db.execute(stmt).scalars().all())
    return [serialize_governance_rule(r) for r in rules]


@router.get("/rules/{rule_id}", response_model=GovernanceRuleOut)
async def get_governance_rule(
    rule_id: uuid.UUID,
    current_user: UserORM = Depends(require_permissions("governance:read")),
    db: Session = Depends(get_db),
) -> GovernanceRuleOut:
    rule = db.execute(
        select(GovernanceRuleORM).where(GovernanceRuleORM.id == rule_id)
    ).scalar_one_or_none()
    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Governance rule not found"
        )
    return serialize_governance_rule(rule)


@router.post("/validate-yaml")
async def validate_governance_yaml(
    rule_definition: str = Body(..., embed=True),
    current_user: UserORM = Depends(require_permissions("governance:read")),
) -> Dict[str, Any]:
    try:
        parsed = yaml.safe_load(rule_definition)
        if not isinstance(parsed, dict):
            return {
                "valid": False,
                "error": "YAML policy definition must be a top-level mapping/object",
                "parsed": None,
            }
        return {
            "valid": True,
            "error": None,
            "parsed": parsed,
            "keys": list(parsed.keys()),
        }
    except yaml.YAMLError as exc:
        return {
            "valid": False,
            "error": str(exc),
            "parsed": None,
        }


@router.post(
    "/rules", response_model=GovernanceRuleOut, status_code=status.HTTP_201_CREATED
)
async def create_governance_rule(
    payload: GovernanceRuleCreateRequest,
    current_user: UserORM = Depends(require_permissions("governance:manage")),
    db: Session = Depends(get_db),
) -> GovernanceRuleOut:
    now = utc_now()
    rule = GovernanceRuleORM(
        id=uuid.uuid4(),
        name=payload.name.strip(),
        description=payload.description.strip(),
        context=payload.context.strip(),
        policy_type=payload.policy_type.strip(),
        rule_definition=payload.rule_definition,
        approval_threshold=payload.approval_threshold,
        require_human_review=payload.require_human_review,
        escalation_target=payload.escalation_target,
        is_active=payload.is_active,
        priority=payload.priority,
        applied_count=0,
        created_at=now,
        updated_at=now,
    )
    db.add(rule)

    record_audit_log(
        session=db,
        action=f"Created governance rule '{rule.name}' (context={rule.context}, priority={rule.priority})",
        event_type="governance_rule_created",
        actor_user=current_user,
        actor_type="user",
        rules_applied=[rule.name],
        compliance_status="compliant",
        metadata={"rule_id": str(rule.id), "context": rule.context},
    )

    db.commit()
    db.refresh(rule)
    serialized = serialize_governance_rule(rule)

    await websocket_manager.broadcast(
        {
            "type": "governance_rule_created",
            "data": serialized.model_dump(mode="json"),
        }
    )
    return serialized


@router.put("/rules/{rule_id}", response_model=GovernanceRuleOut)
async def update_governance_rule(
    rule_id: uuid.UUID,
    payload: GovernanceRuleUpdateRequest,
    current_user: UserORM = Depends(require_permissions("governance:manage")),
    db: Session = Depends(get_db),
) -> GovernanceRuleOut:
    rule = db.execute(
        select(GovernanceRuleORM).where(GovernanceRuleORM.id == rule_id)
    ).scalar_one_or_none()
    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Governance rule not found"
        )

    if payload.name is not None:
        rule.name = payload.name.strip()
    if payload.description is not None:
        rule.description = payload.description.strip()
    if payload.context is not None:
        rule.context = payload.context.strip()
    if payload.policy_type is not None:
        rule.policy_type = payload.policy_type.strip()
    if payload.rule_definition is not None:
        rule.rule_definition = payload.rule_definition
    if payload.approval_threshold is not None:
        rule.approval_threshold = payload.approval_threshold
    if payload.require_human_review is not None:
        rule.require_human_review = payload.require_human_review
    if payload.escalation_target is not None:
        rule.escalation_target = payload.escalation_target
    if payload.is_active is not None:
        rule.is_active = payload.is_active
    if payload.priority is not None:
        rule.priority = payload.priority

    rule.updated_at = utc_now()

    record_audit_log(
        session=db,
        action=f"Updated governance rule '{rule.name}' (is_active={rule.is_active})",
        event_type="governance_rule_updated",
        actor_user=current_user,
        actor_type="user",
        rules_applied=[rule.name],
        compliance_status="compliant",
        metadata={"rule_id": str(rule.id), "is_active": rule.is_active},
    )

    db.commit()
    db.refresh(rule)
    serialized = serialize_governance_rule(rule)

    await websocket_manager.broadcast(
        {
            "type": "governance_rule_updated",
            "data": serialized.model_dump(mode="json"),
        }
    )
    return serialized


@router.delete("/rules/{rule_id}")
async def delete_governance_rule(
    rule_id: uuid.UUID,
    current_user: UserORM = Depends(require_permissions("governance:manage")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    rule = db.execute(
        select(GovernanceRuleORM).where(GovernanceRuleORM.id == rule_id)
    ).scalar_one_or_none()
    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Governance rule not found"
        )

    rule_name = rule.name
    db.delete(rule)

    record_audit_log(
        session=db,
        action=f"Deleted governance rule '{rule_name}'",
        event_type="governance_rule_deleted",
        actor_user=current_user,
        actor_type="user",
        rules_applied=[rule_name],
        compliance_status="compliant",
        metadata={"rule_id": str(rule_id)},
    )
    db.commit()

    await websocket_manager.broadcast(
        {"type": "governance_rule_deleted", "data": {"id": str(rule_id)}}
    )
    return {"message": f"Governance rule '{rule_name}' deleted", "id": str(rule_id)}

