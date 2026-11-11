"""
Multi-Agent Voting API Router (/api/v1/votes).
Supports listing votes, decision consensus summaries, and submitting/updating votes
with permission checks, agent resolution, consensus & bias recalculation, audit logging, and WebSocket broadcast.
"""

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.permissions import require_permissions, user_has_permission
from backend.database.models import (
    AgentORM,
    DecisionORM,
    DecisionParticipantORM,
    NotificationORM,
    UserORM,
    VoteORM,
    utc_now,
)
from backend.database.session import get_db
from backend.schemas.governance_domain import (
    ConsensusSummaryOut,
    VoteCreateRequest,
    VoteOut,
)
from backend.services.governance_service import (
    compute_decision_consensus,
    record_audit_log,
    resolve_agent,
    serialize_vote,
    to_legacy_decision_and_votes,
)
from backend.services.runtime import ml_bias_detector, websocket_manager

router = APIRouter(prefix="/api/v1/votes", tags=["votes"])


@router.get("", response_model=List[VoteOut])
async def list_votes(
    decision_id: Optional[uuid.UUID] = Query(default=None),
    agent_id: Optional[str] = Query(default=None),
    vote: Optional[str] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
    current_user: UserORM = Depends(require_permissions("voting:read")),
    db: Session = Depends(get_db),
) -> List[VoteOut]:
    stmt = select(VoteORM)
    if decision_id is not None:
        stmt = stmt.where(VoteORM.decision_id == decision_id)
    if agent_id:
        agent = resolve_agent(db, agent_id)
        if agent is None:
            return []
        stmt = stmt.where(VoteORM.agent_id == agent.id)
    if vote:
        stmt = stmt.where(VoteORM.vote == vote.lower())

    stmt = stmt.order_by(VoteORM.timestamp.desc()).limit(limit)
    votes = list(db.execute(stmt).scalars().all())
    return [serialize_vote(v) for v in votes]


@router.get("/decision/{decision_id}/summary")
async def get_decision_voting_summary(
    decision_id: uuid.UUID,
    current_user: UserORM = Depends(require_permissions("voting:read")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    decision = db.execute(
        select(DecisionORM).where(DecisionORM.id == decision_id)
    ).scalar_one_or_none()
    if decision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found"
        )

    votes = list(
        db.execute(
            select(VoteORM)
            .where(VoteORM.decision_id == decision_id)
            .order_by(VoteORM.timestamp.asc())
        )
        .scalars()
        .all()
    )
    consensus: ConsensusSummaryOut = compute_decision_consensus(decision)
    return {
        "decision_id": str(decision.id),
        "decision_title": decision.title,
        "decision_status": decision.status,
        "bias_score": round(decision.bias_score, 3),
        "risk_level": decision.risk_level,
        "consensus": consensus.model_dump(mode="json"),
        "votes": [serialize_vote(v).model_dump(mode="json") for v in votes],
    }


def _resolve_voting_agent(
    db: Session, current_user: UserORM, requested_agent_id: Optional[str]
) -> AgentORM:
    """
    Resolve which AgentORM is casting a vote:
    - If requested_agent_id is given, look up by UUID or code.
      Prevent non-admin users from impersonating another human user's linked agent.
    - Otherwise, look up a human AgentORM linked to current_user.id, or create/match one by name.
    """
    if requested_agent_id:
        agent = resolve_agent(db, requested_agent_id)
        if agent is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Voting agent '{requested_agent_id}' not found",
            )
        if (
            agent.user_id is not None
            and agent.user_id != current_user.id
            and not user_has_permission(current_user, "agents:manage")
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot submit a vote on behalf of another human operator's agent",
            )
        return agent

    # Look for an existing agent linked to current_user
    linked = db.execute(
        select(AgentORM).where(AgentORM.user_id == current_user.id)
    ).scalar_one_or_none()
    if linked is not None:
        return linked

    # Fallback: match human agent by name or use first active human reviewer agent
    by_name = db.execute(
        select(AgentORM).where(
            AgentORM.type == "human", AgentORM.name == current_user.full_name
        )
    ).scalar_one_or_none()
    if by_name is not None:
        return by_name

    # Auto-register a dedicated human reviewer agent for this authenticated operator
    safe_code = f"human_{current_user.username.lower()[:40]}"
    existing_code = db.execute(
        select(AgentORM).where(AgentORM.code == safe_code)
    ).scalar_one_or_none()
    if existing_code is not None:
        return existing_code

    new_human_agent = AgentORM(
        id=uuid.uuid4(),
        code=safe_code,
        name=f"{current_user.full_name} (Human Reviewer)",
        type="human",
        provider="human",
        role="Human Governance Reviewer",
        description=f"Authenticated human reviewer ({current_user.email})",
        confidence_threshold=0.6,
        influence_weight=1.3,
        vote_count=0,
        average_confidence=0.85,
        is_active=True,
        user_id=current_user.id,
        metadata_json={"auto_created": True},
    )
    db.add(new_human_agent)
    db.flush()
    return new_human_agent


@router.post("", response_model=VoteOut, status_code=status.HTTP_201_CREATED)
async def create_or_update_vote(
    payload: VoteCreateRequest,
    current_user: UserORM = Depends(require_permissions("voting:participate")),
    db: Session = Depends(get_db),
) -> VoteOut:
    try:
        dec_uuid = uuid.UUID(payload.decision_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid decision_id UUID",
        ) from exc

    decision = db.execute(
        select(DecisionORM).where(DecisionORM.id == dec_uuid)
    ).scalar_one_or_none()
    if decision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found"
        )

    agent = _resolve_voting_agent(db, current_user, payload.agent_id)
    if not agent.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Agent '{agent.name}' is currently inactive and cannot vote",
        )

    # Check if this agent already voted on this decision (idempotent update or new vote)
    existing_vote = db.execute(
        select(VoteORM).where(
            VoteORM.decision_id == decision.id,
            VoteORM.agent_id == agent.id,
        )
    ).scalar_one_or_none()

    now = utc_now()
    if existing_vote is not None:
        existing_vote.vote = payload.vote
        existing_vote.recommendation = payload.recommendation or payload.vote
        existing_vote.confidence = payload.confidence
        existing_vote.justification = payload.justification
        existing_vote.bias_indicators = payload.bias_indicators or []
        existing_vote.timestamp = now
        vote_row = existing_vote
        action_verb = "Updated vote"
    else:
        vote_row = VoteORM(
            id=uuid.uuid4(),
            decision_id=decision.id,
            agent_id=agent.id,
            vote=payload.vote,
            recommendation=payload.recommendation or payload.vote,
            confidence=payload.confidence,
            justification=payload.justification,
            bias_indicators=payload.bias_indicators or [],
            timestamp=now,
        )
        db.add(vote_row)
        action_verb = "Submitted vote"

    # Ensure DecisionParticipantORM exists and is marked "voted"
    participant = db.execute(
        select(DecisionParticipantORM).where(
            DecisionParticipantORM.decision_id == decision.id,
            DecisionParticipantORM.agent_id == agent.id,
        )
    ).scalar_one_or_none()
    if participant is None:
        db.add(
            DecisionParticipantORM(
                id=uuid.uuid4(),
                decision_id=decision.id,
                agent_id=agent.id,
                participation_status="voted",
                assigned_at=now,
            )
        )
    else:
        participant.participation_status = "voted"

    db.flush()
    db.refresh(decision)

    # Recalculate agent statistics from actual votes
    agent_votes = list(
        db.execute(select(VoteORM).where(VoteORM.agent_id == agent.id)).scalars().all()
    )
    agent.vote_count = len(agent_votes)
    if agent_votes:
        agent.average_confidence = round(
            sum(v.confidence for v in agent_votes) / len(agent_votes), 4
        )
    agent.updated_at = now

    # Recalculate decision bias score & risk level via MLBiasDetector
    decision_votes = list(
        db.execute(select(VoteORM).where(VoteORM.decision_id == decision.id))
        .scalars()
        .all()
    )
    legacy_dec, legacy_votes = to_legacy_decision_and_votes(decision, decision_votes)
    new_bias_score = ml_bias_detector.calculate_bias_score(legacy_dec, legacy_votes)
    decision.bias_score = round(float(new_bias_score), 3)
    decision.risk_level = (
        "high"
        if decision.bias_score > 0.7
        else "medium"
        if decision.bias_score > 0.4
        else "low"
    )

    # Recalculate consensus
    consensus = compute_decision_consensus(decision)
    decision.consensus_status = consensus.consensus_status
    decision.consensus_score = consensus.consensus_score
    decision.updated_at = now

    # Record audit log
    record_audit_log(
        session=db,
        action=f"{action_verb} '{payload.vote}' on decision ({agent.name}, confidence={payload.confidence:.2f})",
        event_type="vote_submitted",
        decision_id=decision.id,
        actor_user=current_user,
        actor_agent=agent,
        actor_name=agent.name,
        actor_type=agent.type,
        previous_status=decision.status,
        new_status=decision.status,
        agent_actions=[f"{agent.code}:{payload.vote}"],
        compliance_status="under_review" if decision.bias_score > 0.7 else "compliant",
        metadata={
            "vote_id": str(vote_row.id),
            "vote": payload.vote,
            "confidence": payload.confidence,
            "consensus_score": consensus.consensus_score,
            "bias_score": decision.bias_score,
        },
    )

    # Create high-bias alert notification if bias_score > 0.7
    if decision.bias_score > 0.7:
        notif = NotificationORM(
            id=uuid.uuid4(),
            type="bias_alert",
            title="High Bias Risk Detected During Voting",
            message=(
                f"Decision '{decision.title}' reached bias score {decision.bias_score:.2f} "
                f"following vote by {agent.name}."
            ),
            priority="high",
            is_read=False,
            related_decision_id=decision.id,
            timestamp=now,
        )
        db.add(notif)

    db.commit()
    db.refresh(vote_row)
    serialized = serialize_vote(vote_row)

    await websocket_manager.broadcast(
        {
            "type": "vote_created",
            "data": serialized.model_dump(mode="json"),
            "consensus": consensus.model_dump(mode="json"),
        }
    )
    return serialized

