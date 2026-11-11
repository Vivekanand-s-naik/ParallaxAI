from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
import json
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
import uvicorn

from backend.models import *
from backend.websocket_manager import WebSocketManager
from backend.ml_bias_detector import MLBiasDetector
from backend.ai_integration import AIIntegration
from backend.data_store import DataStore
from backend.auth import (
    authenticate_user, create_token, get_current_user,
    require_admin, optional_auth, USERS
)
from backend.api.v1.auth import router as auth_v1_router
from backend.database.session import get_db
from backend.services.auth_service import authenticate_user_db, issue_token_pair
from sqlalchemy.orm import Session

app = FastAPI(title="ParallaxAI API", version="2.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount v1 routers
app.include_router(auth_v1_router)

# Initialize components
websocket_manager = WebSocketManager()
ml_bias_detector = MLBiasDetector()
ai_integration = AIIntegration()
data_store = DataStore()

# Initialize sample data
data_store.initialize_sample_data()

# ───────────────────────────────────────────
# Public endpoints (no auth required)
# ───────────────────────────────────────────

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


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
# WebSocket endpoint (auth optional via query param)
# ───────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            await websocket_manager.handle_message(websocket, message)
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)


# ───────────────────────────────────────────
# Decision endpoints (auth required)
# ───────────────────────────────────────────

@app.get("/api/decisions", response_model=List[Decision])
async def get_decisions(current_user: dict = Depends(get_current_user)):
    return list(data_store.decisions.values())


@app.get("/api/decisions/{decision_id}", response_model=Decision)
async def get_decision(decision_id: str, current_user: dict = Depends(get_current_user)):
    if decision_id not in data_store.decisions:
        raise HTTPException(status_code=404, detail="Decision not found")
    return data_store.decisions[decision_id]


@app.post("/api/decisions", response_model=Decision)
async def create_decision(decision_data: dict, current_user: dict = Depends(get_current_user)):
    decision = Decision(
        id=str(uuid.uuid4()),
        context=decision_data.get("context", ""),
        application_type=decision_data.get("application_type", "general"),
        metadata=decision_data.get("metadata", {}),
        status="under_review",
        bias_score=0.0,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    data_store.decisions[decision.id] = decision
    await websocket_manager.broadcast({"type": "decision_created", "data": decision.dict()})
    return decision


@app.put("/api/decisions/{decision_id}/status")
async def update_decision_status(
    decision_id: str, status_data: dict,
    current_user: dict = Depends(get_current_user)
):
    if decision_id not in data_store.decisions:
        raise HTTPException(status_code=404, detail="Decision not found")

    decision = data_store.decisions[decision_id]
    decision.status = status_data.get("status", decision.status)
    decision.updated_at = datetime.now()

    audit_entry = AuditLog(
        id=str(uuid.uuid4()),
        decision_id=decision_id,
        action=f"Status updated to {decision.status} by {current_user.get('sub', 'unknown')}",
        timestamp=datetime.now(),
        agent_actions=[f"System: Status changed to {decision.status}"],
        rules_applied=["status_update_rule"],
        compliance_status="compliant",
        audit_hash=f"hash_{decision_id}_{datetime.now().timestamp()}"
    )
    data_store.audit_logs[audit_entry.id] = audit_entry

    await websocket_manager.broadcast({"type": "decision_updated", "data": decision.dict()})
    return decision


@app.delete("/api/decisions/{decision_id}")
async def delete_decision(
    decision_id: str,
    current_user: dict = Depends(require_admin)
):
    if decision_id not in data_store.decisions:
        raise HTTPException(status_code=404, detail="Decision not found")
    del data_store.decisions[decision_id]
    await websocket_manager.broadcast({"type": "decision_deleted", "data": {"id": decision_id}})
    return {"message": "Decision deleted"}


# ───────────────────────────────────────────
# Agent endpoints (auth required)
# ───────────────────────────────────────────

@app.get("/api/agents", response_model=List[Agent])
async def get_agents(current_user: dict = Depends(get_current_user)):
    return list(data_store.agents.values())


@app.get("/api/agents/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str, current_user: dict = Depends(get_current_user)):
    if agent_id not in data_store.agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    return data_store.agents[agent_id]


# ───────────────────────────────────────────
# Vote endpoints (auth required)
# ───────────────────────────────────────────

@app.get("/api/votes", response_model=List[Vote])
async def get_votes(
    decision_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    votes = list(data_store.votes.values())
    if decision_id:
        votes = [vote for vote in votes if vote.decision_id == decision_id]
    return votes


@app.post("/api/votes", response_model=Vote)
async def create_vote(vote_data: dict, current_user: dict = Depends(get_current_user)):
    vote = Vote(
        id=str(uuid.uuid4()),
        agent_id=vote_data.get("agent_id"),
        decision_id=vote_data.get("decision_id"),
        vote=vote_data.get("vote"),
        confidence=vote_data.get("confidence", 0.5),
        justification=vote_data.get("justification", ""),
        timestamp=datetime.now()
    )
    data_store.votes[vote.id] = vote

    if vote.decision_id in data_store.decisions:
        decision = data_store.decisions[vote.decision_id]
        decision_votes = [v for v in data_store.votes.values() if v.decision_id == vote.decision_id]
        bias_score = ml_bias_detector.calculate_bias_score(decision, decision_votes)
        decision.bias_score = bias_score
        decision.updated_at = datetime.now()

    await websocket_manager.broadcast({"type": "vote_created", "data": vote.dict()})
    return vote


# ───────────────────────────────────────────
# Governance rules endpoints (auth required; delete admin-only)
# ───────────────────────────────────────────

@app.get("/api/governance-rules", response_model=List[GovernanceRule])
async def get_governance_rules(current_user: dict = Depends(get_current_user)):
    return list(data_store.governance_rules.values())


@app.post("/api/governance-rules", response_model=GovernanceRule)
async def create_governance_rule(rule_data: dict, current_user: dict = Depends(require_admin)):
    rule = GovernanceRule(
        id=str(uuid.uuid4()),
        name=rule_data.get("name"),
        description=rule_data.get("description"),
        context=rule_data.get("context", "general"),
        rule_definition=rule_data.get("rule_definition", ""),
        is_active=rule_data.get("is_active", True),
        priority=rule_data.get("priority", 1),
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    data_store.governance_rules[rule.id] = rule
    await websocket_manager.broadcast({"type": "governance_rule_created", "data": rule.dict()})
    return rule


@app.put("/api/governance-rules/{rule_id}")
async def update_governance_rule(
    rule_id: str, rule_data: dict,
    current_user: dict = Depends(get_current_user)
):
    if rule_id not in data_store.governance_rules:
        raise HTTPException(status_code=404, detail="Rule not found")

    # Only admin can update name/description; analysts can toggle active
    role = current_user.get("role")
    rule = data_store.governance_rules[rule_id]

    if role == "admin":
        rule.name = rule_data.get("name", rule.name)
        rule.description = rule_data.get("description", rule.description)
        rule.context = rule_data.get("context", rule.context)
        rule.rule_definition = rule_data.get("rule_definition", rule.rule_definition)
        rule.priority = rule_data.get("priority", rule.priority)

    # All authenticated users can toggle active status
    if "is_active" in rule_data:
        rule.is_active = rule_data["is_active"]

    rule.updated_at = datetime.now()
    await websocket_manager.broadcast({"type": "governance_rule_updated", "data": rule.dict()})
    return rule


@app.delete("/api/governance-rules/{rule_id}")
async def delete_governance_rule(
    rule_id: str,
    current_user: dict = Depends(require_admin)
):
    if rule_id not in data_store.governance_rules:
        raise HTTPException(status_code=404, detail="Rule not found")
    del data_store.governance_rules[rule_id]
    await websocket_manager.broadcast({"type": "governance_rule_deleted", "data": {"id": rule_id}})
    return {"message": "Rule deleted"}


# ───────────────────────────────────────────
# Audit log endpoints (auth required)
# ───────────────────────────────────────────

@app.get("/api/audit-logs", response_model=List[AuditLog])
async def get_audit_logs(current_user: dict = Depends(get_current_user)):
    return sorted(data_store.audit_logs.values(), key=lambda x: x.timestamp, reverse=True)


@app.get("/api/audit-logs/{decision_id}")
async def get_audit_logs_for_decision(decision_id: str, current_user: dict = Depends(get_current_user)):
    logs = [log for log in data_store.audit_logs.values() if log.decision_id == decision_id]
    return sorted(logs, key=lambda x: x.timestamp, reverse=True)


# ───────────────────────────────────────────
# Notification endpoints (auth required)
# ───────────────────────────────────────────

@app.get("/api/notifications", response_model=List[Notification])
async def get_notifications(current_user: dict = Depends(get_current_user)):
    return sorted(data_store.notifications.values(), key=lambda x: x.timestamp, reverse=True)


@app.post("/api/notifications", response_model=Notification)
async def create_notification(notification_data: dict, current_user: dict = Depends(get_current_user)):
    notification = Notification(
        id=str(uuid.uuid4()),
        type=notification_data.get("type"),
        title=notification_data.get("title"),
        message=notification_data.get("message"),
        is_read=False,
        timestamp=datetime.now()
    )
    data_store.notifications[notification.id] = notification
    await websocket_manager.broadcast({"type": "notification_created", "data": notification.dict()})
    return notification


@app.put("/api/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, current_user: dict = Depends(get_current_user)):
    if notification_id not in data_store.notifications:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification = data_store.notifications[notification_id]
    notification.is_read = True
    await websocket_manager.broadcast({"type": "notification_updated", "data": notification.dict()})
    return notification


@app.delete("/api/notifications/{notification_id}")
async def delete_notification(notification_id: str, current_user: dict = Depends(get_current_user)):
    if notification_id not in data_store.notifications:
        raise HTTPException(status_code=404, detail="Notification not found")
    del data_store.notifications[notification_id]
    return {"message": "Notification deleted"}


# ───────────────────────────────────────────
# Statistics endpoint (auth required)
# ───────────────────────────────────────────

@app.get("/api/stats")
async def get_stats(current_user: dict = Depends(get_current_user)):
    return data_store.get_stats()


# ───────────────────────────────────────────
# AI Integration endpoints (auth required)
# ───────────────────────────────────────────

@app.post("/api/ai/analyze-decision")
async def analyze_decision_with_ai(analysis_data: dict, current_user: dict = Depends(get_current_user)):
    decision_id = analysis_data.get("decision_id")
    if decision_id not in data_store.decisions:
        raise HTTPException(status_code=404, detail="Decision not found")
    decision = data_store.decisions[decision_id]
    analysis = await ai_integration.analyze_decision(decision)
    return analysis


@app.post("/api/ai/detect-bias")
async def detect_bias_with_ai(bias_data: dict, current_user: dict = Depends(get_current_user)):
    decision_id = bias_data.get("decision_id")
    if decision_id not in data_store.decisions:
        raise HTTPException(status_code=404, detail="Decision not found")
    decision = data_store.decisions[decision_id]
    decision_votes = [v for v in data_store.votes.values() if v.decision_id == decision_id]
    bias_analysis = ml_bias_detector.detect_bias(decision, decision_votes)
    return bias_analysis


@app.post("/api/bias/trigger-review")
async def trigger_bias_review(current_user: dict = Depends(get_current_user)):
    notification = Notification(
        id=str(uuid.uuid4()),
        type="bias_alert",
        title="Bias Review Triggered",
        message=f"Manual bias review initiated by {current_user.get('sub', 'unknown')}.",
        is_read=False,
        timestamp=datetime.now()
    )
    data_store.notifications[notification.id] = notification
    await websocket_manager.broadcast({
        "type": "bias_review_triggered",
        "data": notification.dict()
    })
    return {"message": "Bias review triggered successfully"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
