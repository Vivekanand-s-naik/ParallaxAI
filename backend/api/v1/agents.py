"""
Agent Registry & Influence Graph API Router (/api/v1/agents).
Enforces granular RBAC permissions (agents:read, agents:manage).
"""

import re
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.core.permissions import require_permissions
from backend.database.models import AgentORM, AuditLogORM, UserORM, VoteORM, utc_now
from backend.database.session import get_db
from backend.schemas.governance_domain import (
    AgentCreateRequest,
    AgentOut,
    AgentUpdateRequest,
)
from backend.services.governance_service import (
    compute_influence_graph,
    record_audit_log,
    resolve_agent,
    serialize_agent,
    serialize_audit_log,
    serialize_vote,
)

router = APIRouter(prefix="/api/v1/agents", tags=["Agents & Influence"])


@router.get("", response_model=List[AgentOut])
async def list_agents(
    agent_type: Optional[str] = Query(default=None, alias="type"),
    is_active: Optional[bool] = Query(default=None),
    search: Optional[str] = Query(default=None),
    current_user: UserORM = Depends(require_permissions("agents:read")),
    session: Session = Depends(get_db),
) -> List[AgentOut]:
    """List AI and human agents in the registry."""
    stmt = select(AgentORM).order_by(AgentORM.type, AgentORM.influence_weight.desc())
    if agent_type:
        stmt = stmt.where(AgentORM.type == agent_type.strip().lower())
    if is_active is not None:
        stmt = stmt.where(AgentORM.is_active == is_active)
    if search:
        q = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            func.lower(AgentORM.name).like(q) | func.lower(AgentORM.role).like(q)
        )

    agents = list(session.execute(stmt).scalars().all())
    return [serialize_agent(a) for a in agents]


@router.get("/influence-graph")
async def get_influence_graph(
    current_user: UserORM = Depends(require_permissions("agents:read")),
    session: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Return the interactive React Flow influence graph nodes, edges, agreement pairs, and metrics."""
    return compute_influence_graph(session)


@router.get("/{agent_id}")
async def get_agent_details(
    agent_id: str,
    current_user: UserORM = Depends(require_permissions("agents:read")),
    session: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve agent profile, historical participation, voting statistics, and recent activity."""
    agent = resolve_agent(session, agent_id)
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found"
        )

    votes = list(
        session.execute(
            select(VoteORM)
            .where(VoteORM.agent_id == agent.id)
            .order_by(VoteORM.timestamp.desc())
            .limit(50)
        ).scalars()
    )
    accept_count = sum(1 for v in votes if v.vote == "accept")
    reject_count = sum(1 for v in votes if v.vote == "reject")
    abstain_count = sum(1 for v in votes if v.vote == "abstain")

    logs = list(
        session.execute(
            select(AuditLogORM)
            .where(AuditLogORM.actor_agent_id == agent.id)
            .order_by(AuditLogORM.timestamp.desc())
            .limit(25)
        ).scalars()
    )

    return {
        "agent": serialize_agent(agent),
        "voting_statistics": {
            "recorded_votes": len(votes),
            "historical_vote_count": agent.vote_count,
            "accept_votes": accept_count,
            "reject_votes": reject_count,
            "abstain_votes": abstain_count,
            "accept_rate": round(accept_count / max(len(votes), 1), 3),
            "average_confidence": round(agent.average_confidence, 3),
        },
        "recent_votes": [serialize_vote(v) for v in votes],
        "recent_activities": [serialize_audit_log(log) for log in logs],
    }


@router.post("", response_model=AgentOut, status_code=status.HTTP_201_CREATED)
async def register_agent(
    payload: AgentCreateRequest,
    current_user: UserORM = Depends(require_permissions("agents:manage")),
    session: Session = Depends(get_db),
) -> AgentOut:
    """Register a new AI or human agent in the governance registry."""
    existing_name = session.execute(
        select(AgentORM).where(func.lower(AgentORM.name) == payload.name.strip().lower())
    ).scalar_one_or_none()
    if existing_name is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An agent with this name already exists",
        )

    slug = re.sub(r"[^a-z0-9_]", "_", payload.name.strip().lower()).strip("_")
    code = (payload.code or f"{payload.type}_{slug}")[:64]
    if not code.startswith(f"{payload.type}_"):
        code = f"{payload.type}_{code}"[:64]

    if session.execute(select(AgentORM).where(AgentORM.code == code)).scalar_one_or_none():
        code = f"{code[:54]}_{uuid.uuid4().hex[:6]}"

    now = utc_now()
    agent = AgentORM(
        id=uuid.uuid4(),
        code=code,
        name=payload.name.strip(),
        type=payload.type,
        provider=payload.provider or ("human" if payload.type == "human" else "custom"),
        model_version=payload.model_version,
        role=payload.role.strip(),
        description=payload.description,
        confidence_threshold=payload.confidence_threshold,
        influence_weight=payload.influence_weight,
        vote_count=0,
        average_confidence=0.0,
        is_active=payload.is_active,
        user_id=payload.user_id,
        metadata_json=payload.metadata or {},
        created_at=now,
        updated_at=now,
    )
    session.add(agent)
    session.flush()

    record_audit_log(
        session=session,
        actor_user=current_user,
        actor_agent=agent,
        actor_type="user",
        event_type="agent_registered",
        action=f"Registered {agent.type.upper()} agent '{agent.name}' (weight={agent.influence_weight})",
        metadata={"agent_code": agent.code, "type": agent.type, "role": agent.role},
    )
    session.commit()
    session.refresh(agent)
    return serialize_agent(agent)


@router.patch("/{agent_id}", response_model=AgentOut)
async def update_agent(
    agent_id: str,
    payload: AgentUpdateRequest,
    current_user: UserORM = Depends(require_permissions("agents:manage")),
    session: Session = Depends(get_db),
) -> AgentOut:
    """Update an agent's configuration, status, or influence weight."""
    agent = resolve_agent(session, agent_id)
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found"
        )

    changes = []
    if payload.name is not None and payload.name.strip() != agent.name:
        changes.append(f"name: {agent.name} -> {payload.name.strip()}")
        agent.name = payload.name.strip()
    if payload.provider is not None:
        agent.provider = payload.provider
    if payload.model_version is not None:
        agent.model_version = payload.model_version
    if payload.role is not None:
        agent.role = payload.role.strip()
    if payload.description is not None:
        agent.description = payload.description
    if payload.confidence_threshold is not None:
        agent.confidence_threshold = payload.confidence_threshold
    if payload.influence_weight is not None and payload.influence_weight != agent.influence_weight:
        changes.append(f"influence_weight: {agent.influence_weight} -> {payload.influence_weight}")
        agent.influence_weight = payload.influence_weight
    if payload.is_active is not None and payload.is_active != agent.is_active:
        changes.append(f"is_active: {agent.is_active} -> {payload.is_active}")
        agent.is_active = payload.is_active
    if payload.metadata is not None:
        agent.metadata_json = payload.metadata

    agent.updated_at = utc_now()
    record_audit_log(
        session=session,
        actor_user=current_user,
        actor_agent=agent,
        actor_type="user",
        event_type="agent_updated",
        action=f"Updated agent '{agent.name}': {', '.join(changes) or 'configuration updated'}",
        metadata={"agent_code": agent.code, "changes": changes},
    )
    session.commit()
    session.refresh(agent)
    return serialize_agent(agent)

