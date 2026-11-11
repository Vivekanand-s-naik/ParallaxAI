"""
Idempotent database seed script for ParallaxAI.
Preserves all sample data from the original DataStore and Auth modules
using deterministic UUIDv5 identifiers and conflict-safe upserts so repeated
executions never create duplicate records.
"""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple

from argon2 import PasswordHasher
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.models import (
    AgentORM,
    AuditLogORM,
    DecisionORM,
    DecisionParticipantORM,
    GovernanceRuleORM,
    NotificationORM,
    PermissionORM,
    RoleORM,
    RolePermissionORM,
    UserORM,
    UserRoleORM,
    VoteORM,
)
from backend.database.session import SessionLocal

SEED_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
ph = PasswordHasher()


def seed_uuid(entity_type: str, key: str) -> uuid.UUID:
    """Generate a deterministic UUIDv5 for seeded records."""
    return uuid.uuid5(SEED_NAMESPACE, f"parallaxai.{entity_type}.{key}")


PERMISSIONS_DEF: List[Tuple[str, str, str]] = [
    ("decisions:read", "decisions", "View decisions and decision details"),
    ("decisions:create", "decisions", "Create new decisions for evaluation"),
    ("decisions:update", "decisions", "Update decision metadata and context"),
    ("decisions:approve", "decisions", "Approve decisions under governance policy"),
    ("decisions:reject", "decisions", "Reject decisions under governance policy"),
    ("decisions:escalate", "decisions", "Escalate decisions for senior or committee review"),
    ("agents:read", "agents", "View AI and human agents in the registry"),
    ("agents:manage", "agents", "Register, update, activate/deactivate agents and weights"),
    ("voting:read", "voting", "View multi-agent votes and consensus status"),
    ("voting:participate", "voting", "Submit human review votes and justifications"),
    ("governance:read", "governance", "View governance rules and policy definitions"),
    ("governance:manage", "governance", "Create, update, enable, or disable governance policies"),
    ("bias:read", "bias", "View bias scanner metrics, fairness analysis, and alerts"),
    ("audit:read", "audit", "View audit trail and compliance logs"),
    ("notifications:read", "notifications", "View and manage system and governance notifications"),
    ("users:read", "users", "View user accounts and assigned roles"),
    ("users:manage", "users", "Activate, deactivate, and manage user accounts"),
    ("roles:manage", "roles", "Assign roles and manage role permissions"),
    ("system:configure", "system", "View and configure platform settings and health"),
]

ALL_PERMISSION_NAMES = [p[0] for p in PERMISSIONS_DEF]

ROLES_DEF: Dict[str, Tuple[str, List[str]]] = {
    "SUPER_ADMIN": (
        "Full unrestricted platform administration and governance authority",
        ALL_PERMISSION_NAMES,
    ),
    "ADMIN": (
        "Platform administrator with user, agent, governance, and decision management privileges",
        [p for p in ALL_PERMISSION_NAMES if p != "roles:manage"],
    ),
    "GOVERNANCE_OFFICER": (
        "Governance officer responsible for policy management, compliance, escalations, and approvals",
        [
            "decisions:read",
            "decisions:create",
            "decisions:update",
            "decisions:approve",
            "decisions:reject",
            "decisions:escalate",
            "agents:read",
            "voting:read",
            "voting:participate",
            "governance:read",
            "governance:manage",
            "bias:read",
            "audit:read",
            "notifications:read",
        ],
    ),
    "HUMAN_REVIEWER": (
        "Authorized human participant who evaluates decisions, submits votes, and escalates risks",
        [
            "decisions:read",
            "decisions:escalate",
            "agents:read",
            "voting:read",
            "voting:participate",
            "governance:read",
            "bias:read",
            "audit:read",
            "notifications:read",
        ],
    ),
    "ANALYST": (
        "Data and fairness analyst monitoring bias metrics, influence graphs, and audit trails",
        [
            "decisions:read",
            "decisions:create",
            "decisions:update",
            "agents:read",
            "voting:read",
            "governance:read",
            "bias:read",
            "audit:read",
            "notifications:read",
        ],
    ),
    "VIEWER": (
        "Read-only observer with visibility into decisions, voting, governance, and fairness metrics",
        [
            "decisions:read",
            "agents:read",
            "voting:read",
            "governance:read",
            "bias:read",
            "notifications:read",
        ],
    ),
}


def seed_database(session: Session) -> Dict[str, int]:
    """
    Idempotently seed all RBAC and governance sample data into PostgreSQL.
    Returns counts of total records in each seeded table after completion.
    """
    now = datetime.now(timezone.utc)

    # 1. Seed Permissions
    perm_map: Dict[str, PermissionORM] = {}
    for perm_name, module, description in PERMISSIONS_DEF:
        existing = session.execute(
            select(PermissionORM).where(PermissionORM.name == perm_name)
        ).scalar_one_or_none()
        if not existing:
            existing = PermissionORM(
                id=seed_uuid("permission", perm_name),
                name=perm_name,
                module=module,
                description=description,
                created_at=now,
            )
            session.add(existing)
        perm_map[perm_name] = existing
    session.flush()

    # 2. Seed Roles & Role-Permissions
    role_map: Dict[str, RoleORM] = {}
    for role_name, (role_desc, perm_names) in ROLES_DEF.items():
        role = session.execute(
            select(RoleORM).where(RoleORM.name == role_name)
        ).scalar_one_or_none()
        if not role:
            role = RoleORM(
                id=seed_uuid("role", role_name),
                name=role_name,
                description=role_desc,
                is_system=True,
                created_at=now,
                updated_at=now,
            )
            session.add(role)
            session.flush()
        role_map[role_name] = role

        existing_rp_ids = {
            rp.permission_id
            for rp in session.execute(
                select(RolePermissionORM).where(RolePermissionORM.role_id == role.id)
            ).scalars()
        }
        for p_name in perm_names:
            perm_obj = perm_map[p_name]
            if perm_obj.id not in existing_rp_ids:
                session.add(
                    RolePermissionORM(
                        id=seed_uuid("role_perm", f"{role_name}:{p_name}"),
                        role_id=role.id,
                        permission_id=perm_obj.id,
                        created_at=now,
                    )
                )
    session.flush()

    # 3. Seed Users (preserving admin, analyst, reviewer + governance officer)
    seed_users = [
        {
            "username": "admin",
            "email": "admin@parallaxai.io",
            "full_name": "System Administrator",
            "password": "admin123",
            "roles": ["SUPER_ADMIN", "ADMIN"],
        },
        {
            "username": "analyst",
            "email": "analyst@parallaxai.io",
            "full_name": "Data Analyst",
            "password": "analyst123",
            "roles": ["ANALYST"],
        },
        {
            "username": "reviewer",
            "email": "reviewer@parallaxai.io",
            "full_name": "Human Reviewer",
            "password": "reviewer123",
            "roles": ["HUMAN_REVIEWER"],
        },
        {
            "username": "sarah.chen",
            "email": "sarah.chen@parallaxai.io",
            "full_name": "Sarah Chen",
            "password": "governance123",
            "roles": ["GOVERNANCE_OFFICER", "HUMAN_REVIEWER"],
        },
    ]

    user_map: Dict[str, UserORM] = {}
    for u_data in seed_users:
        user = session.execute(
            select(UserORM).where(UserORM.email == u_data["email"])
        ).scalar_one_or_none()
        if not user:
            user = UserORM(
                id=seed_uuid("user", u_data["username"]),
                username=u_data["username"],
                email=u_data["email"],
                full_name=u_data["full_name"],
                password_hash=ph.hash(u_data["password"]),
                is_active=True,
                is_verified=True,
                auth_provider="local",
                created_at=now - timedelta(days=30),
                updated_at=now,
            )
            session.add(user)
            session.flush()
        user_map[u_data["username"]] = user

        existing_ur_role_ids = {
            ur.role_id
            for ur in session.execute(
                select(UserRoleORM).where(UserRoleORM.user_id == user.id)
            ).scalars()
        }
        for r_name in u_data["roles"]:
            role_obj = role_map[r_name]
            if role_obj.id not in existing_ur_role_ids:
                session.add(
                    UserRoleORM(
                        id=seed_uuid("user_role", f"{u_data['username']}:{r_name}"),
                        user_id=user.id,
                        role_id=role_obj.id,
                        assigned_at=now,
                    )
                )
    session.flush()

    # 4. Seed Agents (exact 6 agents from original DataStore)
    sample_agents = [
        {
            "code": "ai_gpt4",
            "name": "GPT-4",
            "type": "ai",
            "provider": "openai",
            "model_version": "gpt-4o",
            "role": "Primary AI Reviewer",
            "description": "OpenAI GPT-4o multi-domain governance and risk evaluation agent",
            "influence_weight": 1.2,
            "vote_count": 150,
            "average_confidence": 0.87,
        },
        {
            "code": "ai_claude",
            "name": "Claude-4",
            "type": "ai",
            "provider": "anthropic",
            "model_version": "claude-sonnet-4-5",
            "role": "Secondary AI Reviewer",
            "description": "Anthropic Claude Sonnet 4.5 ethical reasoning and fairness reviewer",
            "influence_weight": 1.1,
            "vote_count": 140,
            "average_confidence": 0.82,
        },
        {
            "code": "ai_bert",
            "name": "BERT-Legal",
            "type": "ai",
            "provider": "local_ml",
            "model_version": "bert-large-legal",
            "role": "Specialized Legal AI",
            "description": "Domain-tuned legal and regulatory compliance classification model",
            "influence_weight": 0.9,
            "vote_count": 120,
            "average_confidence": 0.78,
        },
        {
            "code": "human_sarah",
            "name": "Sarah Chen",
            "type": "human",
            "provider": "human",
            "model_version": None,
            "role": "Senior Compliance Officer",
            "description": "Lead human governance officer overseeing high-risk escalations",
            "influence_weight": 1.5,
            "vote_count": 95,
            "average_confidence": 0.91,
            "linked_username": "sarah.chen",
        },
        {
            "code": "human_mike",
            "name": "Mike Rodriguez",
            "type": "human",
            "provider": "human",
            "model_version": None,
            "role": "Risk Assessment Specialist",
            "description": "Financial and operational risk evaluation specialist",
            "influence_weight": 1.3,
            "vote_count": 88,
            "average_confidence": 0.85,
            "linked_username": "reviewer",
        },
        {
            "code": "human_alex",
            "name": "Alex Kim",
            "type": "human",
            "provider": "human",
            "model_version": None,
            "role": "Bias Review Expert",
            "description": "Algorithmic fairness and demographic parity auditor",
            "influence_weight": 1.4,
            "vote_count": 72,
            "average_confidence": 0.89,
            "linked_username": "analyst",
        },
    ]

    agent_list: List[AgentORM] = []
    for a_data in sample_agents:
        agent = session.execute(
            select(AgentORM).where(AgentORM.code == a_data["code"])
        ).scalar_one_or_none()
        if not agent:
            linked_user = user_map.get(a_data.get("linked_username", ""))
            agent = AgentORM(
                id=seed_uuid("agent", a_data["code"]),
                code=a_data["code"],
                name=a_data["name"],
                type=a_data["type"],
                provider=a_data["provider"],
                model_version=a_data["model_version"],
                role=a_data["role"],
                description=a_data["description"],
                confidence_threshold=0.5,
                influence_weight=a_data["influence_weight"],
                vote_count=a_data["vote_count"],
                average_confidence=a_data["average_confidence"],
                is_active=True,
                user_id=linked_user.id if linked_user else None,
                created_at=now - timedelta(days=30),
                updated_at=now,
            )
            session.add(agent)
            session.flush()
        agent_list.append(agent)

    # 5. Seed Governance Rules (exact 3 rules from original DataStore)
    sample_rules = [
        {
            "key": "high_value_decision_review",
            "name": "High Value Decision Review",
            "description": "Require human review for decisions involving high-value transactions",
            "context": "financial",
            "policy_type": "threshold",
            "approval_threshold": 0.8,
            "require_human_review": True,
            "escalation_target": "senior_reviewer",
            "priority": 1,
            "applied_count": 4,
            "rule_definition": (
                "conditions:\n"
                "  - transaction_amount > 100000\n"
                "actions:\n"
                "  - require_human_review: true\n"
                "  - escalate_to: senior_reviewer\n"
                "priority: 1\n"
            ),
        },
        {
            "key": "bias_detection_threshold",
            "name": "Bias Detection Threshold",
            "description": "Trigger bias review when bias score exceeds threshold",
            "context": "general",
            "policy_type": "fairness",
            "approval_threshold": 0.7,
            "require_human_review": True,
            "escalation_target": "bias_review_committee",
            "priority": 2,
            "applied_count": 6,
            "rule_definition": (
                "conditions:\n"
                "  - bias_score > 0.7\n"
                "actions:\n"
                "  - trigger_bias_review: true\n"
                "  - notify: bias_review_committee\n"
                "priority: 2\n"
            ),
        },
        {
            "key": "ai_consensus_requirement",
            "name": "AI Consensus Requirement",
            "description": "Require consensus among AI agents for approval",
            "context": "general",
            "policy_type": "consensus",
            "approval_threshold": 0.8,
            "require_human_review": True,
            "escalation_target": "human_reviewer",
            "priority": 3,
            "applied_count": 5,
            "rule_definition": (
                "conditions:\n"
                "  - ai_consensus_rate < 0.8\n"
                "actions:\n"
                "  - require_additional_review: true\n"
                "  - escalate_to: human_reviewer\n"
                "priority: 3\n"
            ),
        },
    ]

    rule_map: Dict[str, GovernanceRuleORM] = {}
    for r_data in sample_rules:
        rule = session.execute(
            select(GovernanceRuleORM).where(GovernanceRuleORM.name == r_data["name"])
        ).scalar_one_or_none()
        if not rule:
            rule = GovernanceRuleORM(
                id=seed_uuid("rule", r_data["key"]),
                name=r_data["name"],
                description=r_data["description"],
                context=r_data["context"],
                policy_type=r_data["policy_type"],
                rule_definition=r_data["rule_definition"],
                approval_threshold=r_data["approval_threshold"],
                require_human_review=r_data["require_human_review"],
                escalation_target=r_data["escalation_target"],
                is_active=True,
                priority=r_data["priority"],
                applied_count=r_data["applied_count"],
                created_by_id=user_map["admin"].id,
                created_at=now - timedelta(days=15),
                updated_at=now,
            )
            session.add(rule)
            session.flush()
        rule_map[r_data["key"]] = rule

    # 6. Seed Decisions (exact 5 sample decisions from original DataStore)
    sample_decisions = [
        {
            "key": "decision_1_lending",
            "title": "Loan Application Review for Business Expansion",
            "description": "Commercial credit line evaluation for an urban technology SMB seeking $150,000 expansion capital.",
            "context": "Loan Application Review for Business Expansion",
            "application_type": "lending",
            "priority": "medium",
            "status": "approved",
            "bias_score": 0.15,
            "ai_recommendation": "accept",
            "consensus_status": "consensus_reached",
            "consensus_score": 0.78,
            "applicant_data": {
                "age": 35,
                "gender": "female",
                "race": "asian",
                "location": "urban",
                "income": 85000,
                "credit_score": 720,
                "business_type": "technology",
            },
            "rule_key": "high_value_decision_review",
        },
        {
            "key": "decision_2_hiring",
            "title": "Hiring Decision for Software Engineer Position",
            "description": "Candidate evaluation for Senior Backend Software Engineer role with cross-agent technical and fairness review.",
            "context": "Hiring Decision for Software Engineer Position",
            "application_type": "hiring",
            "priority": "high",
            "status": "under_review",
            "bias_score": 0.65,
            "ai_recommendation": "accept",
            "consensus_status": "divided",
            "consensus_score": 0.60,
            "applicant_data": {
                "age": 28,
                "gender": "male",
                "race": "hispanic",
                "location": "suburban",
                "education": "bachelors",
                "experience_years": 5,
            },
            "rule_key": "ai_consensus_requirement",
        },
        {
            "key": "decision_3_insurance",
            "title": "Insurance Risk Assessment for Property Coverage",
            "description": "Underwriting risk evaluation for rural residential property coverage policy renewal.",
            "context": "Insurance Risk Assessment for Property Coverage",
            "application_type": "risk_assessment",
            "priority": "medium",
            "status": "rejected",
            "bias_score": 0.32,
            "ai_recommendation": "reject",
            "consensus_status": "consensus_reached",
            "consensus_score": 0.72,
            "applicant_data": {
                "age": 45,
                "gender": "male",
                "race": "black",
                "location": "rural",
                "property_value": 250000,
                "claim_history": 2,
            },
            "rule_key": "ai_consensus_requirement",
        },
        {
            "key": "decision_4_healthcare",
            "title": "Medical Treatment Authorization",
            "description": "Prior authorization review for specialized chronic care treatment regimen.",
            "context": "Medical Treatment Authorization",
            "application_type": "healthcare",
            "priority": "critical",
            "status": "escalated",
            "bias_score": 0.78,
            "ai_recommendation": "escalate",
            "consensus_status": "escalated_for_review",
            "consensus_score": 0.45,
            "applicant_data": {
                "age": 67,
                "gender": "female",
                "race": "white",
                "location": "urban",
                "condition": "chronic",
                "treatment_cost": 50000,
            },
            "rule_key": "bias_detection_threshold",
        },
        {
            "key": "decision_5_legal",
            "title": "Legal Case Priority Assessment",
            "description": "Civil docket prioritization and compliance triage assessment.",
            "context": "Legal Case Priority Assessment",
            "application_type": "legal",
            "priority": "low",
            "status": "approved",
            "bias_score": 0.22,
            "ai_recommendation": "accept",
            "consensus_status": "consensus_reached",
            "consensus_score": 0.88,
            "applicant_data": {
                "age": 42,
                "gender": "other",
                "race": "asian",
                "location": "urban",
                "case_type": "civil",
                "complexity": "medium",
            },
            "rule_key": "ai_consensus_requirement",
        },
    ]

    decision_list: List[DecisionORM] = []
    for idx, d_data in enumerate(sample_decisions):
        dec_id = seed_uuid("decision", d_data["key"])
        decision = session.execute(
            select(DecisionORM).where(DecisionORM.id == dec_id)
        ).scalar_one_or_none()
        if not decision:
            risk_lvl = (
                "high"
                if d_data["bias_score"] > 0.7
                else "medium"
                if d_data["bias_score"] > 0.4
                else "low"
            )
            decision = DecisionORM(
                id=dec_id,
                title=d_data["title"],
                description=d_data["description"],
                context=d_data["context"],
                application_type=d_data["application_type"],
                priority=d_data["priority"],
                status=d_data["status"],
                applicant_data=d_data["applicant_data"],
                metadata_json={"created_by": "system", "priority": d_data["priority"]},
                bias_score=d_data["bias_score"],
                risk_level=risk_lvl,
                ai_recommendation=d_data["ai_recommendation"],
                consensus_status=d_data["consensus_status"],
                consensus_score=d_data["consensus_score"],
                created_by_id=user_map["admin"].id,
                governance_rule_id=rule_map[d_data["rule_key"]].id,
                created_at=now - timedelta(hours=24 - idx * 3, minutes=30),
                updated_at=now - timedelta(minutes=15 + idx * 5),
            )
            session.add(decision)
            session.flush()
        decision_list.append(decision)

    # 7. Seed Decision Participants & Sample Votes (preserving exact vote patterns)
    vote_patterns = [
        ("accept", 0.85),
        ("accept", 0.82),
        ("reject", 0.75),  # AI votes
        ("accept", 0.90),
        ("reject", 0.88),  # Human votes
    ]

    for dec_idx, decision in enumerate(decision_list):
        for agent_idx, agent in enumerate(agent_list):
            has_voted = dec_idx < 3 and agent_idx < len(vote_patterns)
            part_id = seed_uuid("participant", f"{decision.id}:{agent.code}")
            existing_part = session.execute(
                select(DecisionParticipantORM).where(
                    DecisionParticipantORM.decision_id == decision.id,
                    DecisionParticipantORM.agent_id == agent.id,
                )
            ).scalar_one_or_none()
            if not existing_part:
                session.add(
                    DecisionParticipantORM(
                        id=part_id,
                        decision_id=decision.id,
                        agent_id=agent.id,
                        participation_status="voted" if has_voted else "assigned",
                        assigned_at=decision.created_at,
                    )
                )

            if has_voted:
                vote_decision, confidence = vote_patterns[agent_idx]
                existing_vote = session.execute(
                    select(VoteORM).where(
                        VoteORM.decision_id == decision.id,
                        VoteORM.agent_id == agent.id,
                    )
                ).scalar_one_or_none()
                if not existing_vote:
                    vote_time = now - timedelta(minutes=45 - agent_idx * 5)
                    session.add(
                        VoteORM(
                            id=seed_uuid("vote", f"{decision.id}:{agent.code}"),
                            decision_id=decision.id,
                            agent_id=agent.id,
                            vote=vote_decision,
                            recommendation=vote_decision,
                            confidence=confidence,
                            justification=(
                                f"Based on analysis of criteria and risk factors. "
                                f"Confidence: {confidence * 100:.1f}%"
                            ),
                            bias_indicators=(
                                ["demographic_disparity"]
                                if vote_decision == "reject" and confidence < 0.8
                                else []
                            ),
                            timestamp=vote_time,
                            updated_at=vote_time,
                        )
                    )
    session.flush()

    # 8. Seed Sample Audit Logs
    for idx, decision in enumerate(decision_list[:2]):
        audit_id = seed_uuid("audit", f"initial_audit_{decision.id}")
        existing_audit = session.execute(
            select(AuditLogORM).where(AuditLogORM.id == audit_id)
        ).scalar_one_or_none()
        if not existing_audit:
            ts = now - timedelta(minutes=20 - idx * 5)
            hash_input = f"{decision.id}:{decision.status}:{ts.isoformat()}"
            audit_hash = hashlib.sha256(hash_input.encode()).hexdigest()
            session.add(
                AuditLogORM(
                    id=audit_id,
                    decision_id=decision.id,
                    actor_user_id=user_map["admin"].id,
                    actor_name="System Governance Engine",
                    actor_type="system",
                    event_type="decision_processed",
                    action=f"Decision processed and {decision.status}",
                    previous_status="pending",
                    new_status=decision.status,
                    agent_actions=[
                        "AI-GPT-4: Analyzed application data",
                        "AI-Claude: Reviewed risk factors",
                        "Human-Sarah: Final approval review",
                        "System: Applied governance rules",
                    ],
                    rules_applied=[
                        "High Value Decision Review",
                        "Bias Detection Threshold",
                    ],
                    compliance_status="compliant",
                    audit_hash=f"sha256_{audit_hash[:32]}",
                    metadata_json={
                        "processor": "automated_system",
                        "review_time_minutes": 25,
                    },
                    timestamp=ts,
                )
            )
    session.flush()

    # 9. Seed Sample Notifications (exact 5 sample notifications from original DataStore)
    sample_notifications = [
        {
            "key": "notif_1_bias_alert",
            "type": "bias_alert",
            "title": "High Bias Score Detected",
            "message": f"Decision '{decision_list[3].title}' has a bias score of 0.78, requiring immediate review.",
            "priority": "high",
            "is_read": False,
            "decision": decision_list[3],
        },
        {
            "key": "notif_2_human_override",
            "type": "human_override",
            "title": "Human Override Applied",
            "message": "Sarah Chen overrode AI recommendation for lending decision.",
            "priority": "medium",
            "is_read": False,
            "decision": decision_list[0],
        },
        {
            "key": "notif_3_decision_approved",
            "type": "decision_approved",
            "title": "Decision Approved",
            "message": "Loan Application Review for Business Expansion has been approved.",
            "priority": "low",
            "is_read": True,
            "decision": decision_list[0],
        },
        {
            "key": "notif_4_rule_violation",
            "type": "rule_violation",
            "title": "Governance Rule Violation",
            "message": "High Value Decision Review rule threshold triggered in recent transaction.",
            "priority": "high",
            "is_read": False,
            "decision": decision_list[3],
        },
        {
            "key": "notif_5_system_alert",
            "type": "system_alert",
            "title": "System Maintenance Scheduled",
            "message": "ParallaxAI system maintenance scheduled for tonight at 2 AM UTC.",
            "priority": "medium",
            "is_read": True,
            "decision": None,
        },
    ]

    for idx, n_data in enumerate(sample_notifications):
        notif_id = seed_uuid("notification", n_data["key"])
        existing_notif = session.execute(
            select(NotificationORM).where(NotificationORM.id == notif_id)
        ).scalar_one_or_none()
        if not existing_notif:
            session.add(
                NotificationORM(
                    id=notif_id,
                    type=n_data["type"],
                    title=n_data["title"],
                    message=n_data["message"],
                    priority=n_data["priority"],
                    is_read=n_data["is_read"],
                    related_decision_id=(
                        n_data["decision"].id if n_data["decision"] else None
                    ),
                    metadata_json={"source": "system", "category": "governance"},
                    timestamp=now - timedelta(hours=2, minutes=30 - idx * 10),
                )
            )

    session.commit()

    return {
        "permissions": len(session.execute(select(PermissionORM)).scalars().all()),
        "roles": len(session.execute(select(RoleORM)).scalars().all()),
        "users": len(session.execute(select(UserORM)).scalars().all()),
        "agents": len(session.execute(select(AgentORM)).scalars().all()),
        "governance_rules": len(
            session.execute(select(GovernanceRuleORM)).scalars().all()
        ),
        "decisions": len(session.execute(select(DecisionORM)).scalars().all()),
        "decision_participants": len(
            session.execute(select(DecisionParticipantORM)).scalars().all()
        ),
        "votes": len(session.execute(select(VoteORM)).scalars().all()),
        "audit_logs": len(session.execute(select(AuditLogORM)).scalars().all()),
        "notifications": len(session.execute(select(NotificationORM)).scalars().all()),
    }


def run_seed() -> Dict[str, int]:
    """Run the idempotent database seed using a managed synchronous session."""
    with SessionLocal() as session:
        return seed_database(session)


if __name__ == "__main__":
    counts = run_seed()
    print("Database seed completed successfully:", counts)

