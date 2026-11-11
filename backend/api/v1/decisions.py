"""
Decisions Management & Collaborative Workspace API Router (/api/v1/decisions).
Enforces granular RBAC permissions (decisions:read, decisions:create, decisions:update,
decisions:approve, decisions:reject, decisions:escalate) and ownership checks.
"""

import math
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.auth import get_current_user_orm
from backend.core.permissions import (
    assert_owner_or_permission,
    require_permissions,
    require_roles,
    user_has_permission,
)
from backend.database.models import (
    AgentORM,
    AuditLogORM,
    DecisionORM,
    DecisionParticipantORM,
    GovernanceRuleORM,
    NotificationORM,
    UserORM,
    utc_now,
)
from backend.database.session import get_db
from backend.schemas.governance_domain import (
    DecisionCreateRequest,
    DecisionGovernanceActionRequest,
    DecisionOut,
    DecisionUpdateRequest,
    PaginatedDecisionsOut,
)
from backend.services.governance_service import (
    compute_decision_consensus,
    record_audit_log,
    resolve_agent,
    serialize_audit_log,
    serialize_decision,
    serialize_governance_rule,
    serialize_participant,
    serialize_vote,
    to_legacy_decision_and_votes,
)
from backend.services.runtime import ai_integration, ml_bias_detector, websocket_manager

router = APIRouter(prefix="/api/v1/decisions", tags=["Decisions"])


@router.get("", response_model=PaginatedDecisionsOut)
async def list_decisions(
    search: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    priority: Optional[str] = Query(default=None),
    application_type: Optional[str] = Query(default=None),
    risk_level: Optional[str] = Query(default=None),
    date_from: Optional[datetime] = Query(default=None),
    date_to: Optional[datetime] = Query(default=None),
    sort_by: str = Query(default="updated_at"),
    sort_order: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: UserORM = Depends(require_permissions("decisions:read")),
    session: Session = Depends(get_db),
) -> PaginatedDecisionsOut:
    """List decisions with search, filtering, sorting, and pagination."""
    stmt = select(DecisionORM)

    if status_filter:
        stmt = stmt.where(DecisionORM.status == status_filter.strip().lower())
    if priority:
        stmt = stmt.where(DecisionORM.priority == priority.strip().lower())
    if application_type:
        stmt = stmt.where(DecisionORM.application_type == application_type.strip().lower())
    if risk_level:
        stmt = stmt.where(DecisionORM.risk_level == risk_level.strip().lower())
    if date_from:
        stmt = stmt.where(DecisionORM.created_at >= date_from)
    if date_to:
        stmt = stmt.where(DecisionORM.created_at <= date_to)
    if search:
        q = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(DecisionORM.title).like(q),
                func.lower(DecisionORM.context).like(q),
                func.lower(func.coalesce(DecisionORM.description, "")).like(q),
                func.lower(DecisionORM.application_type).like(q),
            )
        )

    sort_col = {
        "created_at": DecisionORM.created_at,
        "updated_at": DecisionORM.updated_at,
        "bias_score": DecisionORM.bias_score,
        "priority": DecisionORM.priority,
        "status": DecisionORM.status,
        "title": DecisionORM.title,
    }.get(sort_by, DecisionORM.updated_at)

    if sort_order.lower() == "asc":
        stmt = stmt.order_by(sort_col.asc())
    else:
        stmt = stmt.order_by(sort_col.desc())

    decisions = list(session.execute(stmt).scalars().all())
    total = len(decisions)
    total_pages = max(1, math.ceil(total / page_size))
    start = (page - 1) * page_size
    sliced = decisions[start : start + page_size]

    return PaginatedDecisionsOut(
        items=[serialize_decision(session, d) for d in sliced],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{decision_id}", response_model=DecisionOut)
async def get_decision_by_id(
    decision_id: uuid.UUID,
    current_user: UserORM = Depends(require_permissions("decisions:read")),
    session: Session = Depends(get_db),
) -> DecisionOut:
    """Get a single decision by UUID."""
    decision = session.execute(
        select(DecisionORM).where(DecisionORM.id == decision_id)
    ).scalar_one_or_none()
    if decision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found"
        )
    return serialize_decision(session, decision)


@router.get("/{decision_id}/workspace")
async def get_decision_workspace(
    decision_id: uuid.UUID,
    current_user: UserORM = Depends(require_permissions("decisions:read")),
    session: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Comprehensive Decision Workspace payload combining:
    1. Decision Context
    2. Assigned AI & Human Participants
    3. Submitted AI Agent Opinions & Human Review Votes
    4. Consensus & Weighted Voting Summary
    5. Live ML Bias & Fairness Analysis
    6. Applicable Governance Rules
    7. Decision Audit Trail
    """
    decision = session.execute(
        select(DecisionORM).where(DecisionORM.id == decision_id)
    ).scalar_one_or_none()
    if decision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found"
        )

    active_agents = list(
        session.execute(
            select(AgentORM)
            .where(AgentORM.is_active == True)  # noqa: E712
            .order_by(AgentORM.type, AgentORM.name)
        ).scalars()
    )

    votes_out = [serialize_vote(v) for v in decision.votes]
    participants_out = [serialize_participant(p) for p in decision.participants]

    # Build per-agent opinion cards (separating AI agents and human participants)
    vote_by_agent_uuid = {v.agent_id: v for v in decision.votes}
    ai_opinions = []
    human_reviews = []
    for agent in active_agents:
        v_orm = vote_by_agent_uuid.get(agent.id)
        card = {
            "agent_id": agent.code,
            "agent_uuid": str(agent.id),
            "agent_name": agent.name,
            "agent_type": agent.type,
            "role": agent.role,
            "provider": agent.provider,
            "model_version": agent.model_version,
            "influence_weight": agent.influence_weight,
            "participation_status": "voted" if v_orm else "pending",
            "vote": v_orm.vote if v_orm else None,
            "recommendation": (v_orm.recommendation or v_orm.vote) if v_orm else None,
            "confidence": round(v_orm.confidence, 4) if v_orm else None,
            "justification": v_orm.justification if v_orm else None,
            "bias_indicators": (v_orm.bias_indicators or []) if v_orm else [],
            "voted_at": v_orm.timestamp.isoformat() if v_orm else None,
        }
        if agent.type == "ai":
            ai_opinions.append(card)
        else:
            human_reviews.append(card)

    consensus = compute_decision_consensus(
        decision, total_active_agents=max(len(active_agents), 1)
    )

    # Run live ML bias detector on this decision and its votes
    legacy_dec, legacy_votes = to_legacy_decision_and_votes(
        decision, list(decision.votes)
    )
    bias_analysis = ml_bias_detector.detect_bias(legacy_dec, legacy_votes)
    if bias_analysis.get("overall_bias_score", 0.0) == 0.0 and decision.bias_score > 0:
        bias_analysis["overall_bias_score"] = round(decision.bias_score, 3)

    # Applicable governance rules
    rules = list(
        session.execute(
            select(GovernanceRuleORM)
            .where(
                GovernanceRuleORM.is_active == True,  # noqa: E712
                or_(
                    GovernanceRuleORM.context == "general",
                    GovernanceRuleORM.context == decision.application_type,
                    GovernanceRuleORM.id == decision.governance_rule_id,
                ),
            )
            .order_by(GovernanceRuleORM.priority.asc())
        ).scalars()
    )

    # Audit logs for this decision
    audit_logs = list(
        session.execute(
            select(AuditLogORM)
            .where(AuditLogORM.decision_id == decision.id)
            .order_by(AuditLogORM.timestamp.desc())
        ).scalars()
    )

    return {
        "decision": serialize_decision(session, decision),
        "participants": participants_out,
        "votes": votes_out,
        "ai_opinions": ai_opinions,
        "human_reviews": human_reviews,
        "consensus": consensus,
        "bias_analysis": bias_analysis,
        "governance_rules": [serialize_governance_rule(r) for r in rules],
        "audit_trail": [
            serialize_audit_log(log, decision_title=decision.title)
            for log in audit_logs
        ],
    }


@router.post("", response_model=DecisionOut, status_code=status.HTTP_201_CREATED)
async def create_decision(
    payload: DecisionCreateRequest,
    current_user: UserORM = Depends(require_permissions("decisions:create")),
    session: Session = Depends(get_db),
) -> DecisionOut:
    """Create a new decision, assign active participants, and record an audit trail entry."""
    now = utc_now()
    derived_title = (payload.title or payload.context).strip()[:255]

    decision = DecisionORM(
        id=uuid.uuid4(),
        title=derived_title,
        description=payload.description,
        context=payload.context.strip(),
        application_type=payload.application_type.strip().lower(),
        priority=payload.priority,
        status="under_review",
        applicant_data=payload.applicant_data or {},
        metadata_json={
            **(payload.metadata or {}),
            "created_by": current_user.username or current_user.email,
            "priority": payload.priority,
        },
        bias_score=0.0,
        risk_level="low",
        consensus_status="awaiting_votes",
        consensus_score=0.0,
        created_by_id=current_user.id,
        governance_rule_id=payload.governance_rule_id,
        created_at=now,
        updated_at=now,
    )
    session.add(decision)
    session.flush()

    # Assign requested participants or all active agents
    if payload.participant_agent_ids:
        assigned_agents: List[AgentORM] = []
        for aid in payload.participant_agent_ids:
            ag = resolve_agent(session, aid)
            if ag and ag.is_active:
                assigned_agents.append(ag)
    else:
        assigned_agents = list(
            session.execute(
                select(AgentORM).where(AgentORM.is_active == True)  # noqa: E712
            ).scalars()
        )

    for ag in assigned_agents:
        session.add(
            DecisionParticipantORM(
                id=uuid.uuid4(),
                decision_id=decision.id,
                agent_id=ag.id,
                participation_status="assigned",
                assigned_at=now,
            )
        )

    record_audit_log(
        session=session,
        decision_id=decision.id,
        actor_user=current_user,
        actor_type="user",
        event_type="decision_created",
        action=f"Decision '{decision.title}' created for multi-agent evaluation",
        previous_status=None,
        new_status="under_review",
        agent_actions=[f"Assigned {len(assigned_agents)} active agents"],
        rules_applied=[],
        compliance_status="compliant",
        metadata={"application_type": decision.application_type, "priority": decision.priority},
    )
    session.commit()
    session.refresh(decision)

    out = serialize_decision(session, decision)
    await websocket_manager.broadcast(
        {"type": "decision_created", "data": out.model_dump(mode="json")}
    )
    return out


@router.patch("/{decision_id}", response_model=DecisionOut)
async def update_decision(
    decision_id: uuid.UUID,
    payload: DecisionUpdateRequest,
    current_user: UserORM = Depends(get_current_user_orm),
    session: Session = Depends(get_db),
) -> DecisionOut:
    """Update a decision (allowed for decision creator or holders of decisions:update)."""
    decision = session.execute(
        select(DecisionORM).where(DecisionORM.id == decision_id)
    ).scalar_one_or_none()
    if decision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found"
        )

    assert_owner_or_permission(current_user, decision.created_by_id, "decisions:update")

    if payload.title is not None:
        decision.title = payload.title.strip()
    if payload.description is not None:
        decision.description = payload.description
    if payload.context is not None:
        decision.context = payload.context.strip()
    if payload.application_type is not None:
        decision.application_type = payload.application_type.strip().lower()
    if payload.priority is not None:
        decision.priority = payload.priority
    if payload.applicant_data is not None:
        decision.applicant_data = payload.applicant_data
    if payload.metadata is not None:
        decision.metadata_json = payload.metadata
    if payload.governance_rule_id is not None:
        decision.governance_rule_id = payload.governance_rule_id

    decision.updated_at = utc_now()
    record_audit_log(
        session=session,
        decision_id=decision.id,
        actor_user=current_user,
        actor_type="user",
        event_type="decision_updated",
        action=f"Decision '{decision.title}' updated by {current_user.full_name}",
        previous_status=decision.status,
        new_status=decision.status,
    )
    session.commit()
    session.refresh(decision)

    out = serialize_decision(session, decision)
    await websocket_manager.broadcast(
        {"type": "decision_updated", "data": out.model_dump(mode="json")}
    )
    return out


@router.post("/{decision_id}/governance-action", response_model=DecisionOut)
async def execute_governance_action(
    decision_id: uuid.UUID,
    payload: DecisionGovernanceActionRequest,
    current_user: UserORM = Depends(get_current_user_orm),
    session: Session = Depends(get_db),
) -> DecisionOut:
    """
    Execute a sensitive governance control action (approve, reject, escalate, request_review).
    Enforces granular action-specific permissions and requires a justification.
    """
    perm_map = {
        "approve": "decisions:approve",
        "reject": "decisions:reject",
        "escalate": "decisions:escalate",
        "request_review": "decisions:escalate",
    }
    required_perm = perm_map[payload.action]
    if payload.action == "request_review":
        if not (
            user_has_permission(current_user, "decisions:escalate")
            or user_has_permission(current_user, "decisions:update")
            or user_has_permission(current_user, "decisions:approve")
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to request review",
            )
    elif not user_has_permission(current_user, required_perm):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions. Required: {required_perm}",
        )

    decision = session.execute(
        select(DecisionORM).where(DecisionORM.id == decision_id)
    ).scalar_one_or_none()
    if decision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found"
        )

    status_map = {
        "approve": "approved",
        "reject": "rejected",
        "escalate": "escalated",
        "request_review": "under_review",
    }
    prev_status = decision.status
    new_status = status_map[payload.action]
    now = utc_now()

    decision.status = new_status
    decision.reviewed_by_id = current_user.id
    decision.updated_at = now

    # Detect human override if AI recommended something different
    if (
        decision.ai_recommendation in ("accept", "reject")
        and payload.action in ("approve", "reject")
    ):
        ai_mapped = "approve" if decision.ai_recommendation == "accept" else "reject"
        if ai_mapped != payload.action:
            decision.human_override = True
            decision.override_reason = payload.justification

    consensus = compute_decision_consensus(decision)
    decision.consensus_status = consensus.consensus_status
    decision.consensus_score = consensus.consensus_score

    record_audit_log(
        session=session,
        decision_id=decision.id,
        actor_user=current_user,
        actor_type="user",
        event_type=f"decision_{new_status}",
        action=(
            f"Governance action '{payload.action.upper()}' executed by {current_user.full_name} "
            f"({prev_status} -> {new_status}). Justification: {payload.justification}"
        ),
        previous_status=prev_status,
        new_status=new_status,
        agent_actions=[f"{current_user.full_name}: {payload.action} ({payload.justification})"],
        rules_applied=["Governance Control Enforcement"],
        compliance_status="under_review" if new_status == "escalated" else "compliant",
        metadata={
            "governance_action": payload.action,
            "justification": payload.justification,
            "human_override": decision.human_override,
        },
    )

    notif_type = (
        "human_override"
        if decision.human_override
        else "decision_approved"
        if new_status == "approved"
        else "system_alert"
    )
    notif = NotificationORM(
        id=uuid.uuid4(),
        type=notif_type,
        title=f"Decision {new_status.replace('_', ' ').title()}: {decision.title[:60]}",
        message=f"{current_user.full_name} set status to '{new_status}'. Justification: {payload.justification}",
        priority="high" if new_status == "escalated" or decision.human_override else "medium",
        is_read=False,
        related_decision_id=decision.id,
        metadata_json={"action": payload.action, "actor": current_user.full_name},
        timestamp=now,
    )
    session.add(notif)
    session.commit()
    session.refresh(decision)

    out = serialize_decision(session, decision)
    await websocket_manager.broadcast(
        {"type": "decision_updated", "data": out.model_dump(mode="json")}
    )
    return out


@router.post("/{decision_id}/analyze")
async def run_ai_decision_analysis(
    decision_id: uuid.UUID,
    current_user: UserORM = Depends(require_permissions("decisions:read")),
    session: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Run multi-provider AI analysis and ML bias evaluation on a decision."""
    decision = session.execute(
        select(DecisionORM).where(DecisionORM.id == decision_id)
    ).scalar_one_or_none()
    if decision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found"
        )

    legacy_dec, legacy_votes = to_legacy_decision_and_votes(
        decision, list(decision.votes)
    )
    ai_result = await ai_integration.analyze_decision(legacy_dec)
    bias_result = ml_bias_detector.detect_bias(legacy_dec, legacy_votes)
    return {
        "decision_id": str(decision.id),
        "ai_analysis": ai_result,
        "bias_analysis": bias_result,
    }


@router.delete("/{decision_id}")
async def delete_decision(
    decision_id: uuid.UUID,
    current_user: UserORM = Depends(require_roles("SUPER_ADMIN", "ADMIN")),
    session: Session = Depends(get_db),
):
    """Delete a decision (ADMIN or SUPER_ADMIN only) and log the deletion."""
    decision = session.execute(
        select(DecisionORM).where(DecisionORM.id == decision_id)
    ).scalar_one_or_none()
    if decision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found"
        )

    title = decision.title
    record_audit_log(
        session=session,
        decision_id=None,
        actor_user=current_user,
        actor_type="user",
        event_type="decision_deleted",
        action=f"Decision '{title}' ({decision_id}) deleted by {current_user.full_name}",
        previous_status=decision.status,
        new_status="deleted",
        metadata={"deleted_decision_id": str(decision_id), "title": title},
    )
    session.delete(decision)
    session.commit()

    await websocket_manager.broadcast(
        {"type": "decision_deleted", "data": {"id": str(decision_id)}}
    )
    return {"message": "Decision deleted"}

