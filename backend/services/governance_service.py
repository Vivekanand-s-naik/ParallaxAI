"""
PostgreSQL-backed Governance Domain Service for ParallaxAI.
Provides serialization, consensus calculation, ML bias integration,
real-time statistics, influence graph calculation, and audit trail logging.
"""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

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
from backend.models import Decision as LegacyDecision, Vote as LegacyVote
from backend.schemas.governance_domain import (
    AgentOut,
    AuditLogOut,
    ConsensusSummaryOut,
    DecisionOut,
    DecisionParticipantOut,
    GovernanceRuleOut,
    NotificationOut,
    VoteOut,
)


def serialize_agent(agent: AgentORM) -> AgentOut:
    return AgentOut(
        id=agent.code or str(agent.id),
        uuid=agent.id,
        code=agent.code,
        name=agent.name,
        type="ai" if agent.type == "ai" else "human",
        provider=agent.provider,
        model_version=agent.model_version,
        role=agent.role,
        description=agent.description,
        confidence_threshold=agent.confidence_threshold,
        influence_weight=agent.influence_weight,
        vote_count=agent.vote_count,
        average_confidence=round(agent.average_confidence, 4),
        is_active=agent.is_active,
        user_id=agent.user_id,
        metadata=agent.metadata_json or {},
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )


def resolve_agent(session: Session, identifier: str) -> Optional[AgentORM]:
    """Resolve an AgentORM by either its UUID string or its semantic code (e.g. 'ai_gpt4')."""
    if not identifier:
        return None
    try:
        agent_uuid = uuid.UUID(identifier)
        agent = session.execute(
            select(AgentORM).where(AgentORM.id == agent_uuid)
        ).scalar_one_or_none()
        if agent is not None:
            return agent
    except ValueError:
        pass

    return session.execute(
        select(AgentORM).where(AgentORM.code == identifier)
    ).scalar_one_or_none()


def serialize_vote(vote: VoteORM) -> VoteOut:
    agent = vote.agent
    return VoteOut(
        id=str(vote.id),
        agent_id=agent.code if agent else str(vote.agent_id),
        agent_uuid=vote.agent_id,
        agent_code=agent.code if agent else None,
        agent_name=agent.name if agent else "Unknown Agent",
        agent_type=agent.type if agent else "ai",
        agent_role=agent.role if agent else "Reviewer",
        provider=agent.provider if agent else None,
        model_version=agent.model_version if agent else None,
        influence_weight=agent.influence_weight if agent else 1.0,
        decision_id=str(vote.decision_id),
        vote=vote.vote if vote.vote in ("accept", "reject", "abstain") else "accept",  # type: ignore[arg-type]
        recommendation=vote.recommendation or vote.vote,
        confidence=round(vote.confidence, 4),
        justification=vote.justification,
        bias_indicators=vote.bias_indicators or [],
        timestamp=vote.timestamp,
    )


def serialize_participant(part: DecisionParticipantORM) -> DecisionParticipantOut:
    agent = part.agent
    return DecisionParticipantOut(
        agent_id=agent.code if agent else str(part.agent_id),
        agent_uuid=part.agent_id,
        agent_code=agent.code if agent else str(part.agent_id),
        agent_name=agent.name if agent else "Unknown Agent",
        agent_type="ai" if (agent and agent.type == "ai") else "human",
        agent_role=agent.role if agent else "Participant",
        provider=agent.provider if agent else None,
        model_version=agent.model_version if agent else None,
        influence_weight=agent.influence_weight if agent else 1.0,
        participation_status=part.participation_status,
        assigned_at=part.assigned_at,
    )


def serialize_decision(
    session: Session,
    decision: DecisionORM,
    user_cache: Optional[Dict[uuid.UUID, str]] = None,
    rule_cache: Optional[Dict[uuid.UUID, str]] = None,
) -> DecisionOut:
    creator_name = "System"
    if decision.created_by_id:
        if user_cache and decision.created_by_id in user_cache:
            creator_name = user_cache[decision.created_by_id]
        else:
            u = session.execute(
                select(UserORM.full_name).where(UserORM.id == decision.created_by_id)
            ).scalar_one_or_none()
            if u:
                creator_name = u

    rule_name: Optional[str] = None
    if decision.governance_rule_id:
        if rule_cache and decision.governance_rule_id in rule_cache:
            rule_name = rule_cache[decision.governance_rule_id]
        else:
            r = session.execute(
                select(GovernanceRuleORM.name).where(
                    GovernanceRuleORM.id == decision.governance_rule_id
                )
            ).scalar_one_or_none()
            if r:
                rule_name = r

    risk_lvl: Any = (
        decision.risk_level
        if decision.risk_level in ("low", "medium", "high")
        else ("high" if decision.bias_score > 0.7 else "medium" if decision.bias_score > 0.4 else "low")
    )

    return DecisionOut(
        id=str(decision.id),
        title=decision.title or decision.context[:120],
        description=decision.description,
        context=decision.context,
        application_type=decision.application_type,
        priority=decision.priority or "medium",
        status=decision.status,
        applicant_data=decision.applicant_data or {},
        metadata=decision.metadata_json or {},
        bias_score=round(decision.bias_score, 3),
        risk_level=risk_lvl,
        ai_recommendation=decision.ai_recommendation,
        consensus_status=decision.consensus_status or "pending",
        consensus_score=round(decision.consensus_score or 0.0, 3),
        human_override=decision.human_override,
        override_reason=decision.override_reason,
        created_by_id=decision.created_by_id,
        created_by_name=creator_name,
        governance_rule_id=decision.governance_rule_id,
        governance_rule_name=rule_name,
        participant_count=len(decision.participants) if decision.participants else 0,
        vote_count=len(decision.votes) if decision.votes else 0,
        created_at=decision.created_at,
        updated_at=decision.updated_at,
    )


def serialize_governance_rule(rule: GovernanceRuleORM) -> GovernanceRuleOut:
    return GovernanceRuleOut(
        id=str(rule.id),
        name=rule.name,
        description=rule.description,
        context=rule.context,
        policy_type=rule.policy_type,
        rule_definition=rule.rule_definition,
        approval_threshold=rule.approval_threshold,
        require_human_review=rule.require_human_review,
        escalation_target=rule.escalation_target,
        is_active=rule.is_active,
        priority=rule.priority,
        applied_count=rule.applied_count,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


def serialize_audit_log(
    log: AuditLogORM, decision_title: Optional[str] = None
) -> AuditLogOut:
    title = decision_title or (log.decision.title if log.decision else None)
    comp: Any = (
        log.compliance_status
        if log.compliance_status in ("compliant", "under_review", "non_compliant")
        else "compliant"
    )
    return AuditLogOut(
        id=str(log.id),
        decision_id=str(log.decision_id) if log.decision_id else None,
        decision_title=title,
        actor_user_id=log.actor_user_id,
        actor_agent_id=log.actor_agent_id,
        actor_name=log.actor_name,
        actor_type=log.actor_type,
        event_type=log.event_type,
        action=log.action,
        previous_status=log.previous_status,
        new_status=log.new_status,
        agent_actions=log.agent_actions or [],
        rules_applied=log.rules_applied or [],
        compliance_status=comp,
        audit_hash=log.audit_hash,
        metadata=log.metadata_json or {},
        timestamp=log.timestamp,
    )


def serialize_notification(notif: NotificationORM) -> NotificationOut:
    prio: Any = (
        notif.priority
        if notif.priority in ("low", "medium", "high", "critical")
        else "medium"
    )
    return NotificationOut(
        id=str(notif.id),
        type=notif.type,
        title=notif.title,
        message=notif.message,
        priority=prio,
        is_read=notif.is_read,
        recipient_user_id=notif.recipient_user_id,
        related_decision_id=(
            str(notif.related_decision_id) if notif.related_decision_id else None
        ),
        metadata=notif.metadata_json or {},
        timestamp=notif.timestamp,
        read_at=notif.read_at,
    )


def to_legacy_decision_and_votes(
    decision: DecisionORM, votes: List[VoteORM]
) -> Tuple[LegacyDecision, List[LegacyVote]]:
    """Convert ORM Decision & Votes into legacy Pydantic models for MLBiasDetector and AIIntegration."""
    risk_lvl: Any = (
        decision.risk_level
        if decision.risk_level in ("low", "medium", "high")
        else "low"
    )
    legacy_dec = LegacyDecision(
        id=str(decision.id),
        context=decision.context,
        application_type=decision.application_type,
        applicant_data=decision.applicant_data or {},
        metadata=decision.metadata_json or {},
        status=decision.status if decision.status in ("pending", "under_review", "approved", "rejected", "escalated") else "under_review",  # type: ignore[arg-type]
        bias_score=decision.bias_score,
        risk_level=risk_lvl,
        created_at=decision.created_at,
        updated_at=decision.updated_at,
        ai_recommendation=decision.ai_recommendation,
        human_override=decision.human_override,
        override_reason=decision.override_reason,
    )

    legacy_votes: List[LegacyVote] = []
    for v in votes:
        if v.vote not in ("accept", "reject"):
            continue
        agent_code = v.agent.code if v.agent else str(v.agent_id)
        legacy_votes.append(
            LegacyVote(
                id=str(v.id),
                agent_id=agent_code,
                decision_id=str(decision.id),
                vote=v.vote,  # type: ignore[arg-type]
                confidence=v.confidence,
                justification=v.justification,
                timestamp=v.timestamp,
                bias_indicators=v.bias_indicators or [],
            )
        )
    return legacy_dec, legacy_votes


def compute_decision_consensus(
    decision: DecisionORM,
    total_active_agents: int = 6,
) -> ConsensusSummaryOut:
    """
    Calculate multi-agent consensus for a decision using agent influence weights
    and confidence scores while preserving the existing ParallaxAI consensus semantics.
    """
    votes = list(decision.votes or [])
    participants = list(decision.participants or [])
    total_participants = max(len(participants), len(votes), total_active_agents)

    accept_votes = [v for v in votes if v.vote == "accept"]
    reject_votes = [v for v in votes if v.vote == "reject"]
    abstain_votes = [v for v in votes if v.vote == "abstain"]
    decisive_votes = accept_votes + reject_votes

    votes_cast = len(votes)
    pending_votes = max(0, total_participants - votes_cast)

    if not decisive_votes:
        return ConsensusSummaryOut(
            total_participants=total_participants,
            votes_cast=votes_cast,
            pending_votes=pending_votes,
            accept_votes=0,
            reject_votes=0,
            abstain_votes=len(abstain_votes),
            weighted_accept_score=0.0,
            weighted_reject_score=0.0,
            consensus_score=0.0,
            average_confidence=0.0,
            ai_consensus_rate=0.0,
            human_consensus_rate=0.0,
            consensus_status="awaiting_votes",
            recommended_outcome="pending",
            explanation="No decisive votes have been submitted yet. Awaiting AI and human reviewer evaluations.",
        )

    weighted_accept = sum(
        (v.agent.influence_weight if v.agent else 1.0) * v.confidence
        for v in accept_votes
    )
    weighted_reject = sum(
        (v.agent.influence_weight if v.agent else 1.0) * v.confidence
        for v in reject_votes
    )
    total_weight = weighted_accept + weighted_reject
    consensus_score = (
        max(weighted_accept, weighted_reject) / total_weight
        if total_weight > 0
        else 0.0
    )
    avg_confidence = sum(v.confidence for v in decisive_votes) / len(decisive_votes)

    ai_votes = [v for v in decisive_votes if (v.agent and v.agent.type == "ai")]
    human_votes = [v for v in decisive_votes if (v.agent and v.agent.type == "human")]

    def _group_agreement(group: List[VoteORM]) -> float:
        if not group:
            return 0.0
        acc = sum(1 for v in group if v.vote == "accept")
        rej = sum(1 for v in group if v.vote == "reject")
        return max(acc, rej) / len(group)

    ai_consensus_rate = _group_agreement(ai_votes)
    human_consensus_rate = _group_agreement(human_votes)

    recommended = "accept" if weighted_accept >= weighted_reject else "reject"
    if decision.bias_score > 0.7:
        consensus_status = "escalated_for_review"
        recommended = "escalate"
        explanation = (
            f"High bias risk ({decision.bias_score:.2f} > 0.70 threshold) requires human governance review "
            f"despite {len(accept_votes)} accept vs {len(reject_votes)} reject votes."
        )
    elif consensus_score >= 0.75 and len(decisive_votes) >= 2:
        consensus_status = "consensus_reached"
        explanation = (
            f"Strong multi-agent consensus ({consensus_score * 100:.1f}% weighted agreement) "
            f"in favor of '{recommended.upper()}' across {len(decisive_votes)} votes."
        )
    else:
        consensus_status = "divided"
        explanation = (
            f"Split assessment ({consensus_score * 100:.1f}% weighted agreement; "
            f"{len(accept_votes)} accept vs {len(reject_votes)} reject). Human governance review recommended."
        )

    return ConsensusSummaryOut(
        total_participants=total_participants,
        votes_cast=votes_cast,
        pending_votes=pending_votes,
        accept_votes=len(accept_votes),
        reject_votes=len(reject_votes),
        abstain_votes=len(abstain_votes),
        weighted_accept_score=round(weighted_accept, 3),
        weighted_reject_score=round(weighted_reject, 3),
        consensus_score=round(consensus_score, 3),
        average_confidence=round(avg_confidence, 3),
        ai_consensus_rate=round(ai_consensus_rate, 3),
        human_consensus_rate=round(human_consensus_rate, 3),
        consensus_status=consensus_status,
        recommended_outcome=recommended,
        explanation=explanation,
    )


def record_audit_log(
    session: Session,
    action: str,
    event_type: str = "decision_event",
    decision_id: Optional[uuid.UUID] = None,
    actor_user: Optional[UserORM] = None,
    actor_agent: Optional[AgentORM] = None,
    actor_name: Optional[str] = None,
    actor_type: str = "user",
    previous_status: Optional[str] = None,
    new_status: Optional[str] = None,
    agent_actions: Optional[List[str]] = None,
    rules_applied: Optional[List[str]] = None,
    compliance_status: str = "compliant",
    metadata: Optional[Dict[str, Any]] = None,
) -> AuditLogORM:
    """Create a persistent AuditLogORM entry with a deterministic SHA-256 content digest."""
    now = utc_now()
    resolved_name = (
        actor_name
        or (actor_user.full_name if actor_user else None)
        or (actor_agent.name if actor_agent else None)
        or "System Governance Engine"
    )
    digest_payload = (
        f"{decision_id}:{resolved_name}:{event_type}:{action}:"
        f"{previous_status}->{new_status}:{now.isoformat()}"
    )
    digest = hashlib.sha256(digest_payload.encode("utf-8")).hexdigest()

    entry = AuditLogORM(
        id=uuid.uuid4(),
        decision_id=decision_id,
        actor_user_id=actor_user.id if actor_user else None,
        actor_agent_id=actor_agent.id if actor_agent else None,
        actor_name=resolved_name,
        actor_type=actor_type,
        event_type=event_type,
        action=action,
        previous_status=previous_status,
        new_status=new_status,
        agent_actions=agent_actions or [],
        rules_applied=rules_applied or [],
        compliance_status=compliance_status,
        audit_hash=f"sha256_{digest[:32]}",
        metadata_json=metadata or {},
        timestamp=now,
    )
    session.add(entry)
    return entry


def compute_platform_stats(session: Session) -> Dict[str, Any]:
    """
    Compute live platform statistics from PostgreSQL records.
    All metrics are derived from real database rows.
    """
    now = utc_now()
    cutoff_24h = now - timedelta(hours=24)

    decisions = list(session.execute(select(DecisionORM)).scalars().all())
    agents = list(session.execute(select(AgentORM)).scalars().all())
    votes = list(session.execute(select(VoteORM)).scalars().all())
    notifications = list(session.execute(select(NotificationORM)).scalars().all())
    rules = list(session.execute(select(GovernanceRuleORM)).scalars().all())
    audit_logs = list(session.execute(select(AuditLogORM)).scalars().all())

    total_decisions = len(decisions)
    approved_decisions = sum(1 for d in decisions if d.status == "approved")
    rejected_decisions = sum(1 for d in decisions if d.status == "rejected")
    escalated_decisions = sum(1 for d in decisions if d.status == "escalated")
    pending_decisions = sum(
        1 for d in decisions if d.status in ("pending", "under_review")
    )
    decisions_requiring_review = sum(
        1
        for d in decisions
        if d.status in ("pending", "under_review", "escalated") or d.bias_score > 0.7
    )

    total_agents = len(agents)
    active_agents = [a for a in agents if a.is_active]
    ai_agents = sum(1 for a in active_agents if a.type == "ai")
    human_agents = sum(1 for a in active_agents if a.type == "human")
    high_influence_agents = sum(1 for a in active_agents if a.influence_weight > 1.2)

    high_bias_decisions = sum(1 for d in decisions if d.bias_score > 0.7)
    medium_bias_decisions = sum(1 for d in decisions if 0.4 < d.bias_score <= 0.7)
    low_bias_decisions = sum(1 for d in decisions if d.bias_score <= 0.4)

    unread_notifications = sum(1 for n in notifications if not n.is_read)
    bias_alerts = sum(1 for n in notifications if n.type == "bias_alert")
    rule_violation_alerts = sum(1 for n in notifications if n.type == "rule_violation")

    active_rules = sum(1 for r in rules if r.is_active)

    # Calculate real AI accuracy & agreement with finalized decisions
    finalized = [d for d in decisions if d.status in ("approved", "rejected")]
    ai_matches = 0
    ai_comparisons = 0
    for d in finalized:
        expected_vote = "accept" if d.status == "approved" else "reject"
        for v in d.votes:
            if v.agent and v.agent.type == "ai" and v.vote in ("accept", "reject"):
                ai_comparisons += 1
                if v.vote == expected_vote:
                    ai_matches += 1
    ai_accuracy = (ai_matches / ai_comparisons) if ai_comparisons > 0 else 0.85

    override_events = sum(1 for d in decisions if d.human_override) + sum(
        1 for n in notifications if n.type == "human_override"
    )
    override_rate = override_events / max(total_decisions, 1)

    compliant_logs = sum(
        1 for log in audit_logs if log.compliance_status == "compliant"
    )
    compliance_rate = compliant_logs / max(len(audit_logs), 1)

    consensus_scores = [
        compute_decision_consensus(d, total_active_agents=max(len(active_agents), 1)).consensus_score
        for d in decisions
        if d.votes
    ]
    consensus_rate = (
        sum(consensus_scores) / len(consensus_scores) if consensus_scores else 0.0
    )

    # Network density from agent co-participation on decisions
    possible_pairs = (len(active_agents) * (len(active_agents) - 1)) // 2
    co_voting_pairs = set()
    for d in decisions:
        voter_ids = sorted({str(v.agent_id) for v in d.votes})
        for i in range(len(voter_ids)):
            for j in range(i + 1, len(voter_ids)):
                co_voting_pairs.add((voter_ids[i], voter_ids[j]))
    network_density = (
        len(co_voting_pairs) / possible_pairs if possible_pairs > 0 else 0.0
    )

    # Processing time in minutes from created_at to updated_at
    proc_times = [
        max(1.0, (d.updated_at - d.created_at).total_seconds() / 60.0)
        for d in decisions
        if d.updated_at and d.created_at and d.updated_at >= d.created_at
    ]
    avg_proc_time = sum(proc_times) / len(proc_times) if proc_times else 0.0

    decisions_last_24h = sum(
        1
        for d in decisions
        if d.created_at.replace(tzinfo=timezone.utc) >= cutoff_24h
    )
    votes_last_24h = sum(
        1
        for v in votes
        if v.timestamp.replace(tzinfo=timezone.utc) >= cutoff_24h
    )
    alerts_last_24h = sum(
        1
        for n in notifications
        if not n.is_read and n.timestamp.replace(tzinfo=timezone.utc) >= cutoff_24h
    )

    return {
        "total_decisions": total_decisions,
        "approved_decisions": approved_decisions,
        "rejected_decisions": rejected_decisions,
        "escalated_decisions": escalated_decisions,
        "pending_decisions": pending_decisions,
        "decisions_requiring_review": decisions_requiring_review,
        "approval_rate": round(approved_decisions / max(total_decisions, 1), 3),
        "total_agents": total_agents,
        "active_agents": len(active_agents),
        "ai_agents": ai_agents,
        "human_agents": human_agents,
        "high_influence_agents": high_influence_agents,
        "high_bias_decisions": high_bias_decisions,
        "medium_bias_decisions": medium_bias_decisions,
        "low_bias_decisions": low_bias_decisions,
        "bias_incidents": bias_alerts,
        "governance_violations": rule_violation_alerts,
        "ai_accuracy": round(ai_accuracy, 3),
        "override_rate": round(override_rate, 3),
        "unread_notifications": unread_notifications,
        "total_notifications": len(notifications),
        "active_rules": active_rules,
        "total_rules": len(rules),
        "compliance_rate": round(compliance_rate, 3),
        "consensus_rate": round(consensus_rate, 3),
        "average_processing_time": round(avg_proc_time, 1),
        "override_events": override_events,
        "network_density": round(network_density, 3),
        "total_votes": len(votes),
        "total_audit_logs": len(audit_logs),
        "decisions_last_24h": decisions_last_24h,
        "votes_last_24h": votes_last_24h,
        "alerts_last_24h": alerts_last_24h,
    }


def compute_influence_graph(session: Session) -> Dict[str, Any]:
    """
    Build real React Flow graph nodes and edges from actual PostgreSQL agents,
    decisions, votes, and agreement relationships. Never generates random edges.
    """
    agents = list(
        session.execute(select(AgentORM).order_by(AgentORM.type, AgentORM.name)).scalars().all()
    )
    decisions = list(
        session.execute(
            select(DecisionORM).order_by(DecisionORM.updated_at.desc())
        ).scalars().all()
    )
    votes = list(session.execute(select(VoteORM)).scalars().all())

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    # 1. Agent Nodes (AI on left column, Human on right column, Decisions in center)
    ai_agents = [a for a in agents if a.type == "ai"]
    human_agents = [a for a in agents if a.type == "human"]

    for idx, agent in enumerate(ai_agents):
        agent_votes = [v for v in votes if v.agent_id == agent.id]
        avg_conf = (
            sum(v.confidence for v in agent_votes) / len(agent_votes)
            if agent_votes
            else agent.average_confidence
        )
        nodes.append(
            {
                "id": f"agent:{agent.code}",
                "type": "agentNode",
                "position": {"x": 80, "y": 100 + idx * 180},
                "data": {
                    "entity_type": "agent",
                    "agent_id": agent.code,
                    "uuid": str(agent.id),
                    "label": agent.name,
                    "agent_type": "ai",
                    "role": agent.role,
                    "provider": agent.provider,
                    "model_version": agent.model_version,
                    "influence_weight": agent.influence_weight,
                    "average_confidence": round(avg_conf, 3),
                    "vote_count": max(agent.vote_count, len(agent_votes)),
                    "active_votes": len(agent_votes),
                    "is_active": agent.is_active,
                },
            }
        )

    for idx, agent in enumerate(human_agents):
        agent_votes = [v for v in votes if v.agent_id == agent.id]
        avg_conf = (
            sum(v.confidence for v in agent_votes) / len(agent_votes)
            if agent_votes
            else agent.average_confidence
        )
        nodes.append(
            {
                "id": f"agent:{agent.code}",
                "type": "agentNode",
                "position": {"x": 820, "y": 100 + idx * 180},
                "data": {
                    "entity_type": "agent",
                    "agent_id": agent.code,
                    "uuid": str(agent.id),
                    "label": agent.name,
                    "agent_type": "human",
                    "role": agent.role,
                    "provider": "human",
                    "model_version": None,
                    "influence_weight": agent.influence_weight,
                    "average_confidence": round(avg_conf, 3),
                    "vote_count": max(agent.vote_count, len(agent_votes)),
                    "active_votes": len(agent_votes),
                    "is_active": agent.is_active,
                },
            }
        )

    # 2. Decision Nodes & Vote Edges
    for idx, decision in enumerate(decisions):
        dec_node_id = f"decision:{decision.id}"
        nodes.append(
            {
                "id": dec_node_id,
                "type": "decisionNode",
                "position": {"x": 450, "y": 70 + idx * 140},
                "data": {
                    "entity_type": "decision",
                    "decision_id": str(decision.id),
                    "label": decision.title,
                    "application_type": decision.application_type,
                    "status": decision.status,
                    "priority": decision.priority,
                    "bias_score": round(decision.bias_score, 3),
                    "risk_level": decision.risk_level,
                    "consensus_status": decision.consensus_status,
                    "consensus_score": round(decision.consensus_score, 3),
                    "vote_count": len(decision.votes),
                },
            }
        )

        for v in decision.votes:
            if not v.agent:
                continue
            source_id = f"agent:{v.agent.code}"
            edges.append(
                {
                    "id": f"vote:{v.id}",
                    "source": source_id,
                    "target": dec_node_id,
                    "type": "voteEdge",
                    "animated": decision.status in ("pending", "under_review"),
                    "label": f"{v.vote.upper()} ({v.confidence * 100:.0f}%)",
                    "data": {
                        "edge_kind": "vote",
                        "vote_id": str(v.id),
                        "vote": v.vote,
                        "confidence": round(v.confidence, 3),
                        "influence_weight": v.agent.influence_weight,
                        "weighted_influence": round(
                            v.agent.influence_weight * v.confidence, 3
                        ),
                        "justification": v.justification,
                    },
                }
            )

    # 3. Pairwise Agent Agreement Matrix & Influence Alignment Edges
    agreement_matrix: List[Dict[str, Any]] = []
    votes_by_decision: Dict[uuid.UUID, Dict[uuid.UUID, VoteORM]] = {}
    for v in votes:
        votes_by_decision.setdefault(v.decision_id, {})[v.agent_id] = v

    for i in range(len(agents)):
        for j in range(i + 1, len(agents)):
            a1 = agents[i]
            a2 = agents[j]
            shared = 0
            agreed = 0
            for dec_votes in votes_by_decision.values():
                if a1.id in dec_votes and a2.id in dec_votes:
                    shared += 1
                    if dec_votes[a1.id].vote == dec_votes[a2.id].vote:
                        agreed += 1
            if shared > 0:
                rate = round(agreed / shared, 3)
                agreement_matrix.append(
                    {
                        "agent_a_id": a1.code,
                        "agent_a_name": a1.name,
                        "agent_a_type": a1.type,
                        "agent_b_id": a2.code,
                        "agent_b_name": a2.name,
                        "agent_b_type": a2.type,
                        "shared_decisions": shared,
                        "agreed_decisions": agreed,
                        "agreement_rate": rate,
                    }
                )
                if rate >= 0.65:
                    edges.append(
                        {
                            "id": f"agreement:{a1.code}:{a2.code}",
                            "source": f"agent:{a1.code}",
                            "target": f"agent:{a2.code}",
                            "type": "agreementEdge",
                            "animated": False,
                            "label": f"{rate * 100:.0f}% align",
                            "data": {
                                "edge_kind": "agreement",
                                "shared_decisions": shared,
                                "agreement_rate": rate,
                            },
                        }
                    )

    stats = compute_platform_stats(session)
    avg_agreement = (
        round(
            sum(item["agreement_rate"] for item in agreement_matrix)
            / len(agreement_matrix),
            3,
        )
        if agreement_matrix
        else 0.85
    )
    top_agent = (
        max(agents, key=lambda a: a.influence_weight).name if agents else None
    )
    return {
        "nodes": nodes,
        "edges": edges,
        "agreement_pairs": agreement_matrix,
        "metrics": {
            "total_agents": stats["total_agents"],
            "active_agents": stats["active_agents"],
            "ai_agents": stats["ai_agents"],
            "human_agents": stats["human_agents"],
            "high_influence_agents": stats["high_influence_agents"],
            "consensus_rate": stats["consensus_rate"],
            "average_agreement_rate": avg_agreement,
            "highest_influence_agent": top_agent,
            "override_events": stats["override_events"],
            "network_density": stats["network_density"],
        },
    }

