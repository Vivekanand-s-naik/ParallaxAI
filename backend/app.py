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

app = FastAPI(title="ParallaxAI API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
websocket_manager = WebSocketManager()
ml_bias_detector = MLBiasDetector()
ai_integration = AIIntegration()
data_store = DataStore()

# Initialize sample data
data_store.initialize_sample_data()

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# WebSocket endpoint
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

# Decision endpoints
@app.get("/api/decisions", response_model=List[Decision])
async def get_decisions():
    return list(data_store.decisions.values())

@app.get("/api/decisions/{decision_id}", response_model=Decision)
async def get_decision(decision_id: str):
    if decision_id not in data_store.decisions:
        raise HTTPException(status_code=404, detail="Decision not found")
    return data_store.decisions[decision_id]

@app.post("/api/decisions", response_model=Decision)
async def create_decision(decision_data: dict):
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
    
    # Notify all connected clients
    await websocket_manager.broadcast({
        "type": "decision_created",
        "data": decision.dict()
    })
    
    return decision

@app.put("/api/decisions/{decision_id}/status")
async def update_decision_status(decision_id: str, status_data: dict):
    if decision_id not in data_store.decisions:
        raise HTTPException(status_code=404, detail="Decision not found")
    
    decision = data_store.decisions[decision_id]
    decision.status = status_data.get("status", decision.status)
    decision.updated_at = datetime.now()
    
    # Create audit log entry
    audit_entry = AuditLog(
        id=str(uuid.uuid4()),
        decision_id=decision_id,
        action=f"Status updated to {decision.status}",
        timestamp=datetime.now(),
        agent_actions=[f"System: Status changed to {decision.status}"],
        rules_applied=["status_update_rule"],
        compliance_status="compliant",
        audit_hash=f"hash_{decision_id}_{datetime.now().timestamp()}"
    )
    data_store.audit_logs[audit_entry.id] = audit_entry
    
    # Notify all connected clients
    await websocket_manager.broadcast({
        "type": "decision_updated",
        "data": decision.dict()
    })
    
    return decision

# Agent endpoints
@app.get("/api/agents", response_model=List[Agent])
async def get_agents():
    return list(data_store.agents.values())

@app.get("/api/agents/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str):
    if agent_id not in data_store.agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    return data_store.agents[agent_id]

# Vote endpoints
@app.get("/api/votes", response_model=List[Vote])
async def get_votes(decision_id: Optional[str] = None):
    votes = list(data_store.votes.values())
    if decision_id:
        votes = [vote for vote in votes if vote.decision_id == decision_id]
    return votes

@app.post("/api/votes", response_model=Vote)
async def create_vote(vote_data: dict):
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
    
    # Update decision bias score using ML
    if vote.decision_id in data_store.decisions:
        decision = data_store.decisions[vote.decision_id]
        decision_votes = [v for v in data_store.votes.values() if v.decision_id == vote.decision_id]
        bias_score = ml_bias_detector.calculate_bias_score(decision, decision_votes)
        decision.bias_score = bias_score
        decision.updated_at = datetime.now()
    
    # Notify all connected clients
    await websocket_manager.broadcast({
        "type": "vote_created",
        "data": vote.dict()
    })
    
    return vote

# Governance rules endpoints
@app.get("/api/governance-rules", response_model=List[GovernanceRule])
async def get_governance_rules():
    return list(data_store.governance_rules.values())

@app.post("/api/governance-rules", response_model=GovernanceRule)
async def create_governance_rule(rule_data: dict):
    rule = GovernanceRule(
        id=str(uuid.uuid4()),
        name=rule_data.get("name"),
        description=rule_data.get("description"),
        context=rule_data.get("context", "general"),
        rule_definition=rule_data.get("rule_definition", ""),
        is_active=rule_data.get("is_active", True),
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    data_store.governance_rules[rule.id] = rule
    
    # Notify all connected clients
    await websocket_manager.broadcast({
        "type": "governance_rule_created",
        "data": rule.dict()
    })
    
    return rule

@app.put("/api/governance-rules/{rule_id}")
async def update_governance_rule(rule_id: str, rule_data: dict):
    if rule_id not in data_store.governance_rules:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    rule = data_store.governance_rules[rule_id]
    rule.name = rule_data.get("name", rule.name)
    rule.description = rule_data.get("description", rule.description)
    rule.context = rule_data.get("context", rule.context)
    rule.rule_definition = rule_data.get("rule_definition", rule.rule_definition)
    rule.is_active = rule_data.get("is_active", rule.is_active)
    rule.updated_at = datetime.now()
    
    # Notify all connected clients
    await websocket_manager.broadcast({
        "type": "governance_rule_updated",
        "data": rule.dict()
    })
    
    return rule

# Audit log endpoints
@app.get("/api/audit-logs", response_model=List[AuditLog])
async def get_audit_logs():
    return sorted(data_store.audit_logs.values(), key=lambda x: x.timestamp, reverse=True)

@app.get("/api/audit-logs/{decision_id}")
async def get_audit_logs_for_decision(decision_id: str):
    logs = [log for log in data_store.audit_logs.values() if log.decision_id == decision_id]
    return sorted(logs, key=lambda x: x.timestamp, reverse=True)

# Notification endpoints
@app.get("/api/notifications", response_model=List[Notification])
async def get_notifications():
    return sorted(data_store.notifications.values(), key=lambda x: x.timestamp, reverse=True)

@app.post("/api/notifications", response_model=Notification)
async def create_notification(notification_data: dict):
    notification = Notification(
        id=str(uuid.uuid4()),
        type=notification_data.get("type"),
        title=notification_data.get("title"),
        message=notification_data.get("message"),
        is_read=False,
        timestamp=datetime.now()
    )
    
    data_store.notifications[notification.id] = notification
    
    # Notify all connected clients
    await websocket_manager.broadcast({
        "type": "notification_created",
        "data": notification.dict()
    })
    
    return notification

@app.put("/api/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str):
    if notification_id not in data_store.notifications:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification = data_store.notifications[notification_id]
    notification.is_read = True
    
    # Notify all connected clients
    await websocket_manager.broadcast({
        "type": "notification_updated",
        "data": notification.dict()
    })
    
    return notification

# Statistics endpoint
@app.get("/api/stats")
async def get_stats():
    decisions = list(data_store.decisions.values())
    agents = list(data_store.agents.values())
    votes = list(data_store.votes.values())
    notifications = list(data_store.notifications.values())
    
    total_decisions = len(decisions)
    ai_accuracy = 0.85  # Calculate from actual votes
    override_rate = 0.12  # Calculate from human overrides
    bias_incidents = len([n for n in notifications if n.type == "bias_alert"])
    
    # Calculate agent metrics
    ai_agents = [a for a in agents if a.type == "ai"]
    human_agents = [a for a in agents if a.type == "human"]
    
    # Calculate consensus rate
    completed_decisions = [d for d in decisions if d.status in ["approved", "rejected"]]
    consensus_decisions = len(completed_decisions)  # Simplified calculation
    consensus_rate = consensus_decisions / max(total_decisions, 1)
    
    return {
        "total_decisions": total_decisions,
        "ai_accuracy": ai_accuracy,
        "override_rate": override_rate,
        "bias_incidents": bias_incidents,
        "total_agents": len(agents),
        "ai_agents": len(ai_agents),
        "human_agents": len(human_agents),
        "consensus_rate": consensus_rate,
        "unread_notifications": len([n for n in notifications if not n.is_read])
    }

# AI Integration endpoints
@app.post("/api/ai/analyze-decision")
async def analyze_decision_with_ai(analysis_data: dict):
    decision_id = analysis_data.get("decision_id")
    if decision_id not in data_store.decisions:
        raise HTTPException(status_code=404, detail="Decision not found")
    
    decision = data_store.decisions[decision_id]
    
    # Use AI integration to analyze decision
    analysis = await ai_integration.analyze_decision(decision)
    
    return analysis

@app.post("/api/ai/detect-bias")
async def detect_bias_with_ai(bias_data: dict):
    decision_id = bias_data.get("decision_id")
    if decision_id not in data_store.decisions:
        raise HTTPException(status_code=404, detail="Decision not found")
    
    decision = data_store.decisions[decision_id]
    decision_votes = [v for v in data_store.votes.values() if v.decision_id == decision_id]
    
    # Use ML bias detector
    bias_analysis = ml_bias_detector.detect_bias(decision, decision_votes)
    
    return bias_analysis

# Bias scanning endpoint
@app.post("/api/bias/trigger-review")
async def trigger_bias_review():
    # Create a bias review notification
    notification = Notification(
        id=str(uuid.uuid4()),
        type="bias_alert",
        title="Bias Review Triggered",
        message="A manual bias review has been initiated by user request.",
        is_read=False,
        timestamp=datetime.now()
    )
    
    data_store.notifications[notification.id] = notification
    
    # Notify all connected clients
    await websocket_manager.broadcast({
        "type": "bias_review_triggered",
        "data": notification.dict()
    })
    
    return {"message": "Bias review triggered successfully"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
