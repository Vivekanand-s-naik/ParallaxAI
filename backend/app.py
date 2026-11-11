from contextlib import asynccontextmanager
from datetime import datetime
import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session
import uvicorn

from backend.api.v1.agents import router as agents_v1_router
from backend.api.v1.audit import router as audit_v1_router
from backend.api.v1.auth import router as auth_v1_router
from backend.api.v1.bias import router as bias_v1_router
from backend.api.v1.decisions import router as decisions_v1_router
from backend.api.v1.governance import router as governance_v1_router
from backend.api.v1.notifications import router as notifications_v1_router
from backend.api.v1.roles import router as roles_v1_router
from backend.api.v1.system import router as system_v1_router
from backend.api.v1.users import router as users_v1_router
from backend.api.v1.votes import router as votes_v1_router
from backend.auth import (
    USERS,
    authenticate_user,
    create_token,
    get_current_user,
    get_current_user_orm,
    optional_auth,
    require_admin,
)
from backend.core.config import settings
from backend.core.permissions import require_permissions, user_has_permission
from backend.core.security import decode_access_token
from backend.data_store import DataStore
from backend.middleware.rate_limit import RateLimitMiddleware
from backend.middleware.security import (
    SecurityHeadersMiddleware,
    register_exception_handlers,
)
from backend.database.models import (
    AgentORM,
    AuditLogORM,
    DecisionORM,
    DecisionParticipantORM,
    GovernanceRuleORM,
    NotificationORM,
    UserORM,
    VoteORM,
    utc_now,
)
from backend.database.seed import run_seed
from backend.database.session import check_db_connection, get_db
from backend.models import *
from backend.services.auth_service import authenticate_user_db, issue_token_pair
from backend.services.governance_service import (
    compute_decision_consensus,
    compute_platform_stats,
    record_audit_log,
    resolve_agent,
    serialize_agent,
    serialize_audit_log,
    serialize_decision,
    serialize_governance_rule,
    serialize_notification,
    serialize_vote,
    to_legacy_decision_and_votes,
)
from backend.services.runtime import ai_integration, ml_bias_detector, websocket_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    if check_db_connection():
        try:
            run_seed()
        except Exception:
            pass
    yield


app = FastAPI(
    title="ParallaxAI Governance Command Center API",
    version="2.0.0",
    lifespan=lifespan,
)

# Security headers, rate limiting, and CORS middleware
register_exception_handlers(app)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS or ["http://localhost:5173", "http://localhost:5000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all /api/v1 routers
app.include_router(auth_v1_router)
app.include_router(users_v1_router)
app.include_router(roles_v1_router)
app.include_router(decisions_v1_router)
app.include_router(agents_v1_router)
app.include_router(votes_v1_router)
app.include_router(governance_v1_router)
app.include_router(bias_v1_router)
app.include_router(audit_v1_router)
app.include_router(notifications_v1_router)
app.include_router(system_v1_router)

# Retain DataStore instance for legacy fallback reference
data_store = DataStore()
data_store.initialize_sample_data()


# ───────────────────────────────────────────
# Public endpoints (no auth required)
# ───────────────────────────────────────────

@app.get("/health")
async def health_check():
    db_ok = check_db_connection()
    return {
        "status": "healthy" if db_ok else "degraded",
        "database_connected": db_ok,
        "timestamp": utc_now().isoformat(),
    }


# ───────────────────────────────────────────
# Legacy Auth endpoints (compatibility aliases backed by PostgreSQL)
# ───────────────────────────────────────────

@app.post("/api/auth/login")
async def login(credentials: dict, session: Session = Depends(get_db)):
    """Authenticate against PostgreSQL and return a signed JWT token."""
    identifier = credentials.get("email") or credentials.get("username", "")
    password = credentials.get("password", "")

    user_orm = authenticate_user_db(session, identifier, password)
    access_token, raw_refresh, _ = issue_token_pair(session, user=user_orm)
    legacy_role = (
        user_orm.primary_role.lower()
        if user_orm.primary_role in ("ADMIN", "ANALYST")
        else ("admin" if user_orm.primary_role == "SUPER_ADMIN" else "reviewer")
    )
    return {
        "token": access_token,
        "access_token": access_token,
        "refresh_token": raw_refresh,
        "user": {
            "id": str(user_orm.id),
            "username": user_orm.username or user_orm.email,
            "role": legacy_role,
            "primary_role": user_orm.primary_role,
            "roles": user_orm.role_names,
            "permissions": user_orm.permissions,
            "full_name": user_orm.full_name,
            "email": user_orm.email,
        },
    }


@app.get("/api/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Return info about the currently authenticated user from PostgreSQL."""
    return {
        "id": current_user.get("id"),
        "username": current_user.get("username"),
        "role": current_user.get("role"),
        "primary_role": current_user.get("primary_role"),
        "roles": current_user.get("roles", []),
        "permissions": current_user.get("permissions", []),
        "full_name": current_user.get("full_name"),
        "email": current_user.get("email"),
    }


@app.post("/api/auth/refresh")
async def refresh_token(current_user: dict = Depends(get_current_user)):
    """Issue a fresh JWT access token for an already-authenticated user."""
    token = create_token(
        username=current_user["username"],
        role=current_user["primary_role"],
        user_id=current_user["id"],
        email=current_user["email"],
    )
    return {"token": token, "access_token": token}


# ───────────────────────────────────────────
# WebSocket endpoint (supports optional JWT token via query param)
# ───────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(default=None),
):
    metadata: Dict[str, Any] = {}
    if token:
        try:
            payload = decode_access_token(token)
            metadata = {
                "user_id": payload.get("uid") or payload.get("sub"),
                "email": payload.get("email"),
                "role": payload.get("role"),
                "authenticated": True,
            }
        except Exception:
            metadata = {"authenticated": False}
    await websocket_manager.connect(websocket, metadata=metadata)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            await websocket_manager.handle_message(websocket, message)
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
    except Exception:
        websocket_manager.disconnect(websocket)


# ───────────────────────────────────────────
# Legacy /api/decisions endpoints (PostgreSQL + RBAC backed)
# ───────────────────────────────────────────

@app.get("/api/decisions")
async def get_decisions(
    current_user: UserORM = Depends(require_permissions("decisions:read")),
    db: Session = Depends(get_db),
):
    rows = list(
        db.execute(select(DecisionORM).order_by(DecisionORM.created_at.desc()))
        .scalars()
        .all()
    )
    return [serialize_decision(db, d).model_dump(mode="json") for d in rows]


@app.get("/api/decisions/{decision_id}")
async def get_decision(
    decision_id: str,
    current_user: UserORM = Depends(require_permissions("decisions:read")),
    db: Session = Depends(get_db),
):
    try:
        dec_uuid = uuid.UUID(decision_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Decision not found") from exc

    d = db.execute(select(DecisionORM).where(DecisionORM.id == dec_uuid)).scalar_one_or_none()
    if d is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    return serialize_decision(db, d).model_dump(mode="json")


@app.post("/api/decisions")
async def create_decision(
    decision_data: dict,
    current_user: UserORM = Depends(require_permissions("decisions:create")),
    db: Session = Depends(get_db),
):
    context = str(decision_data.get("context", "")).strip()
    if not context:
        raise HTTPException(status_code=400, detail="Decision context is required")

    title = str(decision_data.get("title") or context[:120]).strip()
    now = utc_now()
    decision = DecisionORM(
        id=uuid.uuid4(),
        title=title,
        description=decision_data.get("description") or context,
        context=context,
        application_type=decision_data.get("application_type", "general"),
        priority=decision_data.get("priority", "medium"),
        applicant_data=decision_data.get("applicant_data", {}),
        metadata_json=decision_data.get("metadata", {}),
        status="under_review",
        bias_score=0.0,
        risk_level="low",
        consensus_status="awaiting_votes",
        consensus_score=0.0,
        created_by_id=current_user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(decision)
    db.flush()

    active_agents = list(
        db.execute(select(AgentORM).where(AgentORM.is_active.is_(True))).scalars().all()
    )
    for agent in active_agents:
        db.add(
            DecisionParticipantORM(
                id=uuid.uuid4(),
                decision_id=decision.id,
                agent_id=agent.id,
                participation_status="assigned",
                assigned_at=now,
            )
        )

    record_audit_log(
        session=db,
        action=f"Decision created by {current_user.full_name}",
        event_type="decision_created",
        decision_id=decision.id,
        actor_user=current_user,
        actor_type="user",
        previous_status=None,
        new_status="under_review",
        compliance_status="compliant",
    )
    db.commit()
    db.refresh(decision)

    serialized = serialize_decision(db, decision).model_dump(mode="json")
    await websocket_manager.broadcast({"type": "decision_created", "data": serialized})
    return serialized


@app.put("/api/decisions/{decision_id}/status")
async def update_decision_status(
    decision_id: str,
    status_data: dict,
    current_user: UserORM = Depends(get_current_user_orm),
    db: Session = Depends(get_db),
):
    try:
        dec_uuid = uuid.UUID(decision_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Decision not found") from exc

    decision = db.execute(
        select(DecisionORM).where(DecisionORM.id == dec_uuid)
    ).scalar_one_or_none()
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")

    new_status = status_data.get("status", decision.status)
    justification = status_data.get("justification") or f"Status updated to {new_status}"

    # Enforce action-specific permissions
    perm_map = {
        "approved": "decisions:approve",
        "rejected": "decisions:reject",
        "escalated": "decisions:escalate",
        "under_review": "decisions:update",
        "pending": "decisions:update",
    }
    req_perm = perm_map.get(new_status, "decisions:update")
    if not user_has_permission(current_user, req_perm):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing required permission: {req_perm}",
        )

    prev_status = decision.status
    decision.status = new_status
    decision.updated_at = utc_now()

    record_audit_log(
        session=db,
        action=f"Status updated from '{prev_status}' to '{new_status}' by {current_user.full_name}: {justification}",
        event_type="decision_status_updated",
        decision_id=decision.id,
        actor_user=current_user,
        actor_type="user",
        previous_status=prev_status,
        new_status=new_status,
        agent_actions=[f"Status changed to {new_status}"],
        rules_applied=["status_update_rule"],
        compliance_status="compliant",
    )
    db.commit()
    db.refresh(decision)

    serialized = serialize_decision(db, decision).model_dump(mode="json")
    await websocket_manager.broadcast({"type": "decision_updated", "data": serialized})
    return serialized


@app.delete("/api/decisions/{decision_id}")
async def delete_decision(
    decision_id: str,
    current_user: UserORM = Depends(require_permissions("decisions:manage")),
    db: Session = Depends(get_db),
):
    try:
        dec_uuid = uuid.UUID(decision_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Decision not found") from exc

    decision = db.execute(
        select(DecisionORM).where(DecisionORM.id == dec_uuid)
    ).scalar_one_or_none()
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")

    db.delete(decision)
    db.commit()
    await websocket_manager.broadcast({"type": "decision_deleted", "data": {"id": decision_id}})
    return {"message": "Decision deleted"}


# ───────────────────────────────────────────
# Legacy /api/agents endpoints (PostgreSQL + RBAC backed)
# ───────────────────────────────────────────

@app.get("/api/agents")
async def get_agents(
    current_user: UserORM = Depends(require_permissions("agents:read")),
    db: Session = Depends(get_db),
):
    agents = list(
        db.execute(select(AgentORM).order_by(AgentORM.type, AgentORM.name))
        .scalars()
        .all()
    )
    return [serialize_agent(a).model_dump(mode="json") for a in agents]


@app.get("/api/agents/{agent_id}")
async def get_agent(
    agent_id: str,
    current_user: UserORM = Depends(require_permissions("agents:read")),
    db: Session = Depends(get_db),
):
    agent = resolve_agent(db, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return serialize_agent(agent).model_dump(mode="json")


# ───────────────────────────────────────────
# Legacy /api/votes endpoints (PostgreSQL + RBAC backed)
# ───────────────────────────────────────────

@app.get("/api/votes")
async def get_votes(
    decision_id: Optional[str] = None,
    current_user: UserORM = Depends(require_permissions("voting:read")),
    db: Session = Depends(get_db),
):
    stmt = select(VoteORM)
    if decision_id:
        try:
            dec_uuid = uuid.UUID(decision_id)
            stmt = stmt.where(VoteORM.decision_id == dec_uuid)
        except ValueError:
            return []
    rows = list(db.execute(stmt.order_by(VoteORM.timestamp.desc())).scalars().all())
    return [serialize_vote(v).model_dump(mode="json") for v in rows]


@app.post("/api/votes")
async def create_vote(
    vote_data: dict,
    current_user: UserORM = Depends(require_permissions("voting:participate")),
    db: Session = Depends(get_db),
):
    from backend.api.v1.votes import create_or_update_vote
    from backend.schemas.governance_domain import VoteCreateRequest

    req = VoteCreateRequest(
        decision_id=str(vote_data.get("decision_id", "")),
        agent_id=vote_data.get("agent_id"),
        vote=vote_data.get("vote", "accept"),
        confidence=float(vote_data.get("confidence", 0.85)),
        justification=str(vote_data.get("justification") or "Submitted via ParallaxAI"),
        bias_indicators=vote_data.get("bias_indicators") or [],
    )
    out = await create_or_update_vote(payload=req, current_user=current_user, db=db)
    return out.model_dump(mode="json")


# ───────────────────────────────────────────
# Legacy /api/governance-rules endpoints (PostgreSQL + RBAC backed)
# ───────────────────────────────────────────

@app.get("/api/governance-rules")
async def get_governance_rules(
    current_user: UserORM = Depends(require_permissions("governance:read")),
    db: Session = Depends(get_db),
):
    rules = list(
        db.execute(
            select(GovernanceRuleORM).order_by(
                GovernanceRuleORM.priority.asc(), GovernanceRuleORM.name.asc()
            )
        )
        .scalars()
        .all()
    )
    return [serialize_governance_rule(r).model_dump(mode="json") for r in rules]


@app.post("/api/governance-rules")
async def create_governance_rule(
    rule_data: dict,
    current_user: UserORM = Depends(require_permissions("governance:manage")),
    db: Session = Depends(get_db),
):
    now = utc_now()
    rule = GovernanceRuleORM(
        id=uuid.uuid4(),
        name=str(rule_data.get("name", "Untitled Rule")),
        description=str(rule_data.get("description", "")),
        context=str(rule_data.get("context", "general")),
        policy_type=str(rule_data.get("policy_type", "threshold")),
        rule_definition=str(rule_data.get("rule_definition", "threshold: 0.7")),
        is_active=bool(rule_data.get("is_active", True)),
        priority=int(rule_data.get("priority", 1)),
        created_at=now,
        updated_at=now,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    serialized = serialize_governance_rule(rule).model_dump(mode="json")
    await websocket_manager.broadcast({"type": "governance_rule_created", "data": serialized})
    return serialized


@app.put("/api/governance-rules/{rule_id}")
async def update_governance_rule(
    rule_id: str,
    rule_data: dict,
    current_user: UserORM = Depends(require_permissions("governance:manage")),
    db: Session = Depends(get_db),
):
    try:
        r_uuid = uuid.UUID(rule_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Rule not found") from exc

    rule = db.execute(
        select(GovernanceRuleORM).where(GovernanceRuleORM.id == r_uuid)
    ).scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")

    if "name" in rule_data:
        rule.name = str(rule_data["name"])
    if "description" in rule_data:
        rule.description = str(rule_data["description"])
    if "context" in rule_data:
        rule.context = str(rule_data["context"])
    if "rule_definition" in rule_data:
        rule.rule_definition = str(rule_data["rule_definition"])
    if "priority" in rule_data:
        rule.priority = int(rule_data["priority"])
    if "is_active" in rule_data:
        rule.is_active = bool(rule_data["is_active"])

    rule.updated_at = utc_now()
    db.commit()
    db.refresh(rule)
    serialized = serialize_governance_rule(rule).model_dump(mode="json")
    await websocket_manager.broadcast({"type": "governance_rule_updated", "data": serialized})
    return serialized


@app.delete("/api/governance-rules/{rule_id}")
async def delete_governance_rule(
    rule_id: str,
    current_user: UserORM = Depends(require_permissions("governance:manage")),
    db: Session = Depends(get_db),
):
    try:
        r_uuid = uuid.UUID(rule_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Rule not found") from exc

    rule = db.execute(
        select(GovernanceRuleORM).where(GovernanceRuleORM.id == r_uuid)
    ).scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")

    db.delete(rule)
    db.commit()
    await websocket_manager.broadcast({"type": "governance_rule_deleted", "data": {"id": rule_id}})
    return {"message": "Rule deleted"}


# ───────────────────────────────────────────
# Legacy /api/audit-logs endpoints (PostgreSQL + RBAC backed)
# ───────────────────────────────────────────

@app.get("/api/audit-logs")
async def get_audit_logs(
    current_user: UserORM = Depends(require_permissions("audit:read")),
    db: Session = Depends(get_db),
):
    rows = list(
        db.execute(select(AuditLogORM).order_by(AuditLogORM.timestamp.desc()))
        .scalars()
        .all()
    )
    return [serialize_audit_log(r).model_dump(mode="json") for r in rows]


@app.get("/api/audit-logs/{decision_id}")
async def get_audit_logs_for_decision(
    decision_id: str,
    current_user: UserORM = Depends(require_permissions("audit:read")),
    db: Session = Depends(get_db),
):
    try:
        dec_uuid = uuid.UUID(decision_id)
    except ValueError:
        return []
    rows = list(
        db.execute(
            select(AuditLogORM)
            .where(AuditLogORM.decision_id == dec_uuid)
            .order_by(AuditLogORM.timestamp.desc())
        )
        .scalars()
        .all()
    )
    return [serialize_audit_log(r).model_dump(mode="json") for r in rows]


# ───────────────────────────────────────────
# Legacy /api/notifications endpoints (PostgreSQL + RBAC backed)
# ───────────────────────────────────────────

@app.get("/api/notifications")
async def get_notifications(
    current_user: UserORM = Depends(require_permissions("notifications:read")),
    db: Session = Depends(get_db),
):
    rows = list(
        db.execute(select(NotificationORM).order_by(NotificationORM.timestamp.desc()))
        .scalars()
        .all()
    )
    return [serialize_notification(n).model_dump(mode="json") for n in rows]


@app.post("/api/notifications")
async def create_notification(
    notification_data: dict,
    current_user: UserORM = Depends(require_permissions("notifications:read")),
    db: Session = Depends(get_db),
):
    notif = NotificationORM(
        id=uuid.uuid4(),
        type=str(notification_data.get("type", "system_alert")),
        title=str(notification_data.get("title", "Notification")),
        message=str(notification_data.get("message", "")),
        priority=str(notification_data.get("priority", "medium")),
        is_read=False,
        timestamp=utc_now(),
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    serialized = serialize_notification(notif).model_dump(mode="json")
    await websocket_manager.broadcast({"type": "notification_created", "data": serialized})
    return serialized


@app.put("/api/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: UserORM = Depends(require_permissions("notifications:read")),
    db: Session = Depends(get_db),
):
    try:
        n_uuid = uuid.UUID(notification_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Notification not found") from exc

    notif = db.execute(
        select(NotificationORM).where(NotificationORM.id == n_uuid)
    ).scalar_one_or_none()
    if notif is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True
    notif.read_at = utc_now()
    db.commit()
    db.refresh(notif)
    serialized = serialize_notification(notif).model_dump(mode="json")
    await websocket_manager.broadcast({"type": "notification_updated", "data": serialized})
    return serialized


@app.delete("/api/notifications/{notification_id}")
async def delete_notification(
    notification_id: str,
    current_user: UserORM = Depends(require_permissions("notifications:read")),
    db: Session = Depends(get_db),
):
    try:
        n_uuid = uuid.UUID(notification_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Notification not found") from exc

    notif = db.execute(
        select(NotificationORM).where(NotificationORM.id == n_uuid)
    ).scalar_one_or_none()
    if notif is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    db.delete(notif)
    db.commit()
    return {"message": "Notification deleted"}


# ───────────────────────────────────────────
# Legacy /api/stats & AI Integration endpoints (PostgreSQL + RBAC backed)
# ───────────────────────────────────────────

@app.get("/api/stats")
async def get_stats(
    current_user: UserORM = Depends(require_permissions("decisions:read")),
    db: Session = Depends(get_db),
):
    return compute_platform_stats(db)


@app.post("/api/ai/analyze-decision")
async def analyze_decision_with_ai(
    analysis_data: dict,
    current_user: UserORM = Depends(require_permissions("decisions:read")),
    db: Session = Depends(get_db),
):
    decision_id = analysis_data.get("decision_id", "")
    try:
        dec_uuid = uuid.UUID(str(decision_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Decision not found") from exc

    decision = db.execute(
        select(DecisionORM).where(DecisionORM.id == dec_uuid)
    ).scalar_one_or_none()
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")

    votes = list(
        db.execute(select(VoteORM).where(VoteORM.decision_id == decision.id))
        .scalars()
        .all()
    )
    legacy_dec, _ = to_legacy_decision_and_votes(decision, votes)
    analysis = await ai_integration.analyze_decision(legacy_dec)
    return analysis


@app.post("/api/ai/detect-bias")
async def detect_bias_with_ai(
    bias_data: dict,
    current_user: UserORM = Depends(require_permissions("bias:read")),
    db: Session = Depends(get_db),
):
    decision_id = bias_data.get("decision_id", "")
    try:
        dec_uuid = uuid.UUID(str(decision_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Decision not found") from exc

    decision = db.execute(
        select(DecisionORM).where(DecisionORM.id == dec_uuid)
    ).scalar_one_or_none()
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")

    votes = list(
        db.execute(select(VoteORM).where(VoteORM.decision_id == decision.id))
        .scalars()
        .all()
    )
    legacy_dec, legacy_votes = to_legacy_decision_and_votes(decision, votes)
    return ml_bias_detector.detect_bias(legacy_dec, legacy_votes)


@app.post("/api/bias/trigger-review")
async def trigger_bias_review(
    current_user: UserORM = Depends(require_permissions("bias:read")),
    db: Session = Depends(get_db),
):
    notif = NotificationORM(
        id=uuid.uuid4(),
        type="bias_alert",
        title="Bias Review Triggered",
        message=f"Manual bias review initiated by {current_user.full_name}.",
        priority="high",
        is_read=False,
        timestamp=utc_now(),
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    serialized = serialize_notification(notif).model_dump(mode="json")
    await websocket_manager.broadcast({"type": "bias_review_triggered", "data": serialized})
    return {"message": "Bias review triggered successfully", "notification": serialized}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
