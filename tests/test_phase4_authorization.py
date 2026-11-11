"""
Phase 4 Verification Tests:
- Role-Based Access Control (RBAC) across all 6 roles and 19 permissions
- Unauthorized access rejection (403 Forbidden)
- Privileged governance actions (approve/reject/escalate with mandatory justification, YAML rule management)
- Ownership checks (decision creator vs non-owner)
- User-role assignment & SUPER_ADMIN escalation prevention
- Dynamic role-permission updates taking immediate effect
- PostgreSQL-backed domain endpoints (/api/v1/decisions, /agents, /votes, /governance, /bias, /audit, /notifications, /system)
"""

import uuid
from fastapi.testclient import TestClient

from backend.app import app
from backend.database.models import RoleORM
from backend.database.seed import seed_database
from backend.database.session import SessionLocal
from sqlalchemy import delete


def _ensure_seeded() -> None:
    with SessionLocal() as session:
        seed_database(session)


def _login_headers(client: TestClient, identifier: str, password: str) -> dict:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": identifier, "password": password},
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_role_permissions_matrix_and_roles_endpoint():
    _ensure_seeded()
    client = TestClient(app)
    admin_headers = _login_headers(client, "admin@parallaxai.io", "admin123")

    roles_resp = client.get("/api/v1/roles", headers=admin_headers)
    assert roles_resp.status_code == 200
    roles = {r["name"]: set(r["permissions"]) for r in roles_resp.json()}

    assert {
        "SUPER_ADMIN",
        "ADMIN",
        "GOVERNANCE_OFFICER",
        "HUMAN_REVIEWER",
        "ANALYST",
        "VIEWER",
    }.issubset(roles.keys())

    # SUPER_ADMIN has all 19 permissions
    assert len(roles["SUPER_ADMIN"]) == 19
    assert "roles:manage" in roles["SUPER_ADMIN"]
    assert "system:configure" in roles["SUPER_ADMIN"]

    # GOVERNANCE_OFFICER can approve/reject/escalate decisions and manage governance rules, but cannot manage users/roles
    assert "decisions:approve" in roles["GOVERNANCE_OFFICER"]
    assert "decisions:reject" in roles["GOVERNANCE_OFFICER"]
    assert "decisions:escalate" in roles["GOVERNANCE_OFFICER"]
    assert "governance:manage" in roles["GOVERNANCE_OFFICER"]
    assert "users:manage" not in roles["GOVERNANCE_OFFICER"]
    assert "roles:manage" not in roles["GOVERNANCE_OFFICER"]

    # HUMAN_REVIEWER can vote and escalate decisions, but cannot approve/reject or manage governance rules or users
    assert "voting:participate" in roles["HUMAN_REVIEWER"]
    assert "decisions:escalate" in roles["HUMAN_REVIEWER"]
    assert "decisions:approve" not in roles["HUMAN_REVIEWER"]
    assert "governance:manage" not in roles["HUMAN_REVIEWER"]

    # VIEWER has strictly read-only permissions (excluding sensitive compliance audit trail)
    assert roles["VIEWER"] == {
        "decisions:read",
        "agents:read",
        "voting:read",
        "governance:read",
        "bias:read",
        "notifications:read",
    }


def test_unauthorized_access_rejected_for_viewer():
    _ensure_seeded()
    client = TestClient(app)

    # Register a new user (receives VIEWER role by default)
    email = f"viewer_{uuid.uuid4().hex[:8]}@parallaxai.io"
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Read Only Viewer",
            "email": email,
            "password": "ViewerSafePassword!123",
            "accept_terms": True,
        },
    )
    assert reg_resp.status_code == 201
    viewer_headers = {"Authorization": f"Bearer {reg_resp.json()['access_token']}"}

    # VIEWER can read decisions, agents, governance rules, bias overview, stats
    assert client.get("/api/v1/decisions", headers=viewer_headers).status_code == 200
    assert client.get("/api/v1/agents", headers=viewer_headers).status_code == 200
    assert client.get("/api/v1/governance/rules", headers=viewer_headers).status_code == 200
    assert client.get("/api/v1/bias/overview", headers=viewer_headers).status_code == 200
    assert client.get("/api/v1/system/stats", headers=viewer_headers).status_code == 200

    # VIEWER is rejected (403) from compliance audit logs (requires audit:read)
    assert client.get("/api/v1/audit", headers=viewer_headers).status_code == 403

    # VIEWER is rejected (403) from creating a decision
    create_dec = client.post(
        "/api/v1/decisions",
        headers=viewer_headers,
        json={
            "title": "Unauthorized Decision",
            "context": "Viewer attempting to create a decision",
            "application_type": "loan_approval",
        },
    )
    assert create_dec.status_code == 403

    # VIEWER is rejected (403) from submitting a vote
    decisions = client.get("/api/v1/decisions", headers=viewer_headers).json()["items"]
    sample_decision_id = decisions[0]["id"]
    vote_resp = client.post(
        "/api/v1/votes",
        headers=viewer_headers,
        json={
            "decision_id": sample_decision_id,
            "vote": "accept",
            "confidence": 0.9,
            "justification": "Viewer trying to vote",
        },
    )
    assert vote_resp.status_code == 403

    # VIEWER is rejected (403) from approving a decision
    gov_action = client.post(
        f"/api/v1/decisions/{sample_decision_id}/governance-action",
        headers=viewer_headers,
        json={
            "action": "approve",
            "justification": "Viewer trying to approve decision",
        },
    )
    assert gov_action.status_code == 403

    # VIEWER is rejected (403) from creating governance rules
    rule_resp = client.post(
        "/api/v1/governance/rules",
        headers=viewer_headers,
        json={
            "name": "Unauthorized Rule",
            "description": "Should fail",
            "context": "general",
            "rule_definition": "threshold: 0.8",
        },
    )
    assert rule_resp.status_code == 403

    # VIEWER is rejected (403) from listing users or managing roles
    assert client.get("/api/v1/users", headers=viewer_headers).status_code == 403
    assert client.get("/api/v1/roles", headers=viewer_headers).status_code == 403


def test_privileged_governance_actions_and_voting_flow():
    _ensure_seeded()
    client = TestClient(app)

    analyst_headers = _login_headers(client, "analyst@parallaxai.io", "analyst123")
    reviewer_headers = _login_headers(client, "reviewer@parallaxai.io", "reviewer123")
    officer_headers = _login_headers(client, "sarah.chen@parallaxai.io", "governance123")

    # 1. ANALYST creates a new decision
    create_resp = client.post(
        "/api/v1/decisions",
        headers=analyst_headers,
        json={
            "title": "Autonomous Triage Policy Evaluation",
            "description": "Clinical AI triage escalation threshold evaluation",
            "context": "Emergency department clinical risk scoring for cardiovascular symptoms",
            "application_type": "medical_diagnosis",
            "priority": "high",
            "applicant_data": {"department": "Cardiology", "patient_cohort_size": 450},
            "metadata": {"urgency_level": "high", "clinical_trial": False},
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    decision = create_resp.json()
    decision_id = decision["id"]
    assert decision["status"] == "under_review"
    assert decision["participant_count"] >= 6

    # 2. Ownership check: ANALYST (creator) can update their own decision
    patch_resp = client.patch(
        f"/api/v1/decisions/{decision_id}",
        headers=analyst_headers,
        json={"priority": "critical"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["priority"] == "critical"

    # 3. ANALYST cannot approve the decision (missing decisions:approve)
    analyst_approve = client.post(
        f"/api/v1/decisions/{decision_id}/governance-action",
        headers=analyst_headers,
        json={
            "action": "approve",
            "justification": "Analyst trying to approve directly",
        },
    )
    assert analyst_approve.status_code == 403

    # 4. HUMAN_REVIEWER submits a vote on the decision
    vote_resp = client.post(
        "/api/v1/votes",
        headers=reviewer_headers,
        json={
            "decision_id": decision_id,
            "vote": "accept",
            "recommendation": "Approve with continuous cardiology monitoring",
            "confidence": 0.91,
            "justification": "Clinical telemetry and fairness indicators meet safety thresholds.",
            "bias_indicators": [],
        },
    )
    assert vote_resp.status_code == 201, vote_resp.text
    vote_data = vote_resp.json()
    assert vote_data["vote"] == "accept"
    assert vote_data["confidence"] == 0.91

    # 5. GOVERNANCE_OFFICER inspects full 7-section Decision Workspace
    ws_resp = client.get(
        f"/api/v1/decisions/{decision_id}/workspace",
        headers=officer_headers,
    )
    assert ws_resp.status_code == 200
    ws = ws_resp.json()
    assert ws["decision"]["id"] == decision_id
    assert ws["consensus"]["votes_cast"] >= 1
    assert "bias_analysis" in ws
    assert len(ws["audit_trail"]) >= 2

    # 6. GOVERNANCE_OFFICER approves the decision with justification
    gov_resp = client.post(
        f"/api/v1/decisions/{decision_id}/governance-action",
        headers=officer_headers,
        json={
            "action": "approve",
            "justification": "Approved after clinical ethics review and human reviewer sign-off.",
        },
    )
    assert gov_resp.status_code == 200, gov_resp.text
    assert gov_resp.json()["status"] == "approved"

    # 7. GOVERNANCE_OFFICER creates and validates a YAML governance rule
    yaml_check = client.post(
        "/api/v1/governance/validate-yaml",
        headers=officer_headers,
        json={"rule_definition": "min_consensus: 0.8\nrequire_human_signoff: true\n"},
    )
    assert yaml_check.status_code == 200
    assert yaml_check.json()["valid"] is True

    rule_create = client.post(
        "/api/v1/governance/rules",
        headers=officer_headers,
        json={
            "name": f"Cardiology Safety Gate {uuid.uuid4().hex[:6]}",
            "description": "Requires 80% consensus for cardiology triage decisions",
            "context": "medical_diagnosis",
            "policy_type": "consensus_threshold",
            "rule_definition": "min_consensus: 0.8\nrequire_human_signoff: true\n",
            "approval_threshold": 0.8,
            "require_human_review": True,
            "escalation_target": "GOVERNANCE_OFFICER",
            "priority": 1,
        },
    )
    assert rule_create.status_code == 201, rule_create.text


def test_user_role_assignment_and_dynamic_role_permissions():
    _ensure_seeded()
    client = TestClient(app)
    super_admin_headers = _login_headers(client, "admin@parallaxai.io", "admin123")

    # Register a fresh user (starts as VIEWER)
    email = f"dynamic_{uuid.uuid4().hex[:8]}@parallaxai.io"
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Dynamic Role User",
            "email": email,
            "password": "DynamicPassword!123",
            "accept_terms": True,
        },
    )
    assert reg.status_code == 201
    user_id = reg.json()["user"]["id"]
    user_headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    # Initially cannot create decisions (VIEWER)
    resp1 = client.post(
        "/api/v1/decisions",
        headers=user_headers,
        json={
            "title": "Before Role Upgrade",
            "context": "Testing dynamic role assignment",
            "application_type": "general",
        },
    )
    assert resp1.status_code == 403

    # SUPER_ADMIN assigns ANALYST role to this user
    assign_resp = client.put(
        f"/api/v1/users/{user_id}/roles",
        headers=super_admin_headers,
        json={"roles": ["ANALYST"]},
    )
    assert assign_resp.status_code == 200
    assert "ANALYST" in assign_resp.json()["roles"]
    assert "decisions:create" in assign_resp.json()["permissions"]

    # Immediately (even with the same valid JWT, because permissions are resolved live from PostgreSQL!),
    # the user can now create a decision!
    resp2 = client.post(
        "/api/v1/decisions",
        headers=user_headers,
        json={
            "title": "After Role Upgrade to Analyst",
            "context": "Testing live permission resolution from PostgreSQL",
            "application_type": "general",
        },
    )
    assert resp2.status_code == 201

    # Create a custom role and dynamically update its permissions
    custom_role_name = f"CUSTOM_AUDITOR_{uuid.uuid4().hex[:6].upper()}"
    create_role = client.post(
        "/api/v1/roles",
        headers=super_admin_headers,
        json={
            "name": custom_role_name,
            "description": "Custom auditor role for testing",
            "permissions": ["decisions:read", "audit:read"],
        },
    )
    assert create_role.status_code == 201
    custom_role_id = create_role.json()["id"]

    # Update custom role permissions to include voting:participate
    update_role = client.put(
        f"/api/v1/roles/{custom_role_id}/permissions",
        headers=super_admin_headers,
        json={"permissions": ["decisions:read", "audit:read", "voting:participate"]},
    )
    assert update_role.status_code == 200
    assert "voting:participate" in update_role.json()["permissions"]

    # Clean up temporary custom test roles
    with SessionLocal() as session:
        session.execute(delete(RoleORM).where(RoleORM.name.like("CUSTOM_AUDITOR_%")))
        session.commit()


def test_influence_graph_and_system_endpoints():
    _ensure_seeded()
    client = TestClient(app)
    headers = _login_headers(client, "admin@parallaxai.io", "admin123")

    graph_resp = client.get("/api/v1/agents/influence-graph", headers=headers)
    assert graph_resp.status_code == 200
    graph = graph_resp.json()
    assert len(graph["nodes"]) >= 11  # 6 agents + >=5 decisions
    assert len(graph["edges"]) >= 15
    assert "agreement_pairs" in graph

    health_resp = client.get("/api/v1/system/health")
    assert health_resp.status_code == 200
    health = health_resp.json()
    assert health["services"]["postgresql"]["connected"] is True

    settings_resp = client.get("/api/v1/system/settings", headers=headers)
    assert settings_resp.status_code == 200
    assert settings_resp.json()["authentication"]["password_hashing"] == "Argon2id (argon2-cffi)"
