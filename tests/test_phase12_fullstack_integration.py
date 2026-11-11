"""
Phase 12 — Full-Stack End-to-End Integration Test Suite.
Verifies all 11 /api/v1/* routers, frontend-backend contract schemas,
7-section Decision Workspace, ML Bias & Fairness Scanner, YAML Policy Engine,
Cryptographic Audit Trail, Notification Center, and Real-Time WebSocket (/ws).
"""

from fastapi.testclient import TestClient

from backend.app import app


def _login(client: TestClient, identifier: str, password: str) -> dict:
    resp = client.post(
        "/api/v1/auth/login",
        json={"identifier": identifier, "password": password, "remember_me": False},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "access_token" in data
    assert "user" in data
    return data


def test_system_health_stats_and_settings_contracts():
    """Verify Command Center /system/health, /system/stats, and /system/settings contracts."""
    with TestClient(app) as client:
        admin_auth = _login(client, "admin@parallaxai.io", "admin123")
        headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

        # 1. /api/v1/system/health
        health_resp = client.get("/api/v1/system/health")
        assert health_resp.status_code == 200
        health = health_resp.json()
        assert health["status"] == "healthy"
        assert health["services"]["postgresql"]["connected"] is True
        assert "redis" in health["services"]
        assert "websocket" in health["services"]
        assert "ml_bias_engine" in health["services"]
        assert "ai_providers" in health["services"]

        # 2. /api/v1/system/stats
        stats_resp = client.get("/api/v1/system/stats", headers=headers)
        assert stats_resp.status_code == 200
        stats = stats_resp.json()
        for key in (
            "kpis",
            "decision_activity",
            "category_distribution",
            "agent_activity",
            "recent_decisions",
            "recent_audit_logs",
            "recent_notifications",
        ):
            assert key in stats, f"Missing key {key} in /api/v1/system/stats"

        # 3. /api/v1/system/settings
        settings_resp = client.get("/api/v1/system/settings", headers=headers)
        assert settings_resp.status_code == 200
        sys_settings = settings_resp.json()
        for section in (
            "platform",
            "infrastructure",
            "ai_providers",
            "authentication",
            "rate_limits",
        ):
            assert section in sys_settings

        # 4. /api/v1/auth/sessions
        sessions_resp = client.get("/api/v1/auth/sessions", headers=headers)
        assert sessions_resp.status_code == 200
        assert isinstance(sessions_resp.json(), list)
        assert len(sessions_resp.json()) >= 1


def test_end_to_end_decision_workspace_voting_bias_governance_and_audit_flow():
    """
    Execute the complete Human-AI Co-Governance lifecycle:
    Create Decision -> AI & Fairness Scan -> 7-Section Workspace -> Cast Vote ->
    Trigger Bias Review -> YAML Policy Lifecycle -> Approve Decision -> Verify Audit & Notifications -> Cleanup.
    """
    with TestClient(app) as client:
        gov_auth = _login(client, "sarah.chen@parallaxai.io", "governance123")
        gov_headers = {"Authorization": f"Bearer {gov_auth['access_token']}"}

        admin_auth = _login(client, "admin@parallaxai.io", "admin123")
        admin_headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

        # 1. Create a new decision case
        create_resp = client.post(
            "/api/v1/decisions",
            headers=gov_headers,
            json={
                "title": "Integration Test — Autonomous Diagnostic Triage #901",
                "description": "End-to-end integration test decision",
                "context": "Evaluate multi-agent clinical triage priority for rural emergency telemetry.",
                "application_type": "medical_diagnosis",
                "priority": "high",
                "applicant_data": {
                    "facility_tier": "rural_critical_access",
                    "urgency_index": 0.88,
                },
            },
        )
        assert create_resp.status_code == 201, create_resp.text
        created_decision = create_resp.json()
        decision_id = created_decision["id"]

        try:
            # 2. Run AI & ML Bias Evaluation
            analyze_resp = client.post(
                f"/api/v1/decisions/{decision_id}/analyze",
                headers=gov_headers,
            )
            assert analyze_resp.status_code == 200, analyze_resp.text
            analyze_data = analyze_resp.json()
            assert analyze_data["decision_id"] == decision_id
            assert "ai_analysis" in analyze_data
            assert "bias_analysis" in analyze_data

            # 3. Inspect 7-Section Decision Workspace
            ws_resp = client.get(
                f"/api/v1/decisions/{decision_id}/workspace",
                headers=gov_headers,
            )
            assert ws_resp.status_code == 200, ws_resp.text
            workspace = ws_resp.json()
            for section in (
                "decision",
                "participants",
                "votes",
                "ai_opinions",
                "human_reviews",
                "consensus",
                "bias_analysis",
                "governance_rules",
                "audit_trail",
            ):
                assert section in workspace, f"Missing workspace section: {section}"

            # 4. Submit a Human Co-Governance Vote
            vote_resp = client.post(
                "/api/v1/votes",
                headers=gov_headers,
                json={
                    "decision_id": decision_id,
                    "vote": "accept",
                    "recommendation": "accept",
                    "confidence": 0.93,
                    "justification": "Clinical telemetry and rural equity checks verified.",
                    "bias_indicators": ["geographic_access"],
                },
            )
            assert vote_resp.status_code == 201, vote_resp.text

            # Verify voting summary endpoint
            summary_resp = client.get(
                f"/api/v1/votes/decision/{decision_id}/summary",
                headers=gov_headers,
            )
            assert summary_resp.status_code == 200
            summary_data = summary_resp.json()
            assert summary_data["decision_id"] == decision_id
            assert summary_data["consensus"]["votes_cast"] >= 1

            # 5. Verify Bias & Fairness Scanner endpoints
            bias_overview_resp = client.get(
                "/api/v1/bias/overview",
                headers=gov_headers,
            )
            assert bias_overview_resp.status_code == 200
            bias_overview = bias_overview_resp.json()
            assert "summary" in bias_overview
            assert "fairness_metrics" in bias_overview
            assert "category_breakdown" in bias_overview

            trigger_resp = client.post(
                "/api/v1/bias/trigger-review",
                headers=gov_headers,
                json={
                    "decision_id": decision_id,
                    "reason": "Integration test fairness review verification",
                },
            )
            assert trigger_resp.status_code == 201, trigger_resp.text
            notif_id = trigger_resp.json()["notification"]["id"]

            # 6. Validate YAML & Governance Rule lifecycle
            yaml_resp = client.post(
                "/api/v1/governance/validate-yaml",
                headers=gov_headers,
                json={
                    "rule_definition": "max_bias_score: 0.45\nrequire_human_signoff: true"
                },
            )
            assert yaml_resp.status_code == 200
            assert yaml_resp.json()["valid"] is True

            rule_create_resp = client.post(
                "/api/v1/governance/rules",
                headers=gov_headers,
                json={
                    "name": "Integration Test Clinical Equity Rule",
                    "description": "Temporary integration test rule",
                    "context": "medical_diagnosis",
                    "policy_type": "threshold",
                    "rule_definition": "max_bias_score: 0.45\nmin_consensus: 0.75",
                    "approval_threshold": 0.75,
                    "require_human_review": True,
                    "is_active": True,
                    "priority": 2,
                },
            )
            assert rule_create_resp.status_code == 201
            rule_id = rule_create_resp.json()["id"]

            rule_del_resp = client.delete(
                f"/api/v1/governance/rules/{rule_id}",
                headers=gov_headers,
            )
            assert rule_del_resp.status_code == 200

            # 7. Execute Governance Action (Approve)
            gov_action_resp = client.post(
                f"/api/v1/decisions/{decision_id}/governance-action",
                headers=gov_headers,
                json={
                    "action": "approve",
                    "justification": "Approved following clinical fairness verification and consensus.",
                },
            )
            assert gov_action_resp.status_code == 200
            assert gov_action_resp.json()["status"] == "approved"

            # 8. Verify Cryptographic Audit Explainability
            audit_dec_resp = client.get(
                f"/api/v1/audit/decision/{decision_id}",
                headers=gov_headers,
            )
            assert audit_dec_resp.status_code == 200
            audit_dec = audit_dec_resp.json()
            assert len(audit_dec["audit_trail"]) >= 2
            assert all(
                item["audit_hash"].startswith("sha256_")
                and len(item["audit_hash"]) >= 32
                for item in audit_dec["audit_trail"]
            )

            # Verify Agent Influence Graph contract
            graph_resp = client.get(
                "/api/v1/agents/influence-graph",
                headers=gov_headers,
            )
            assert graph_resp.status_code == 200
            graph_data = graph_resp.json()
            assert "nodes" in graph_data
            assert "edges" in graph_data
            assert "metrics" in graph_data
            assert "active_agents" in graph_data["metrics"]
            assert "average_agreement_rate" in graph_data["metrics"]
            assert "highest_influence_agent" in graph_data["metrics"]

            # 9. Mark notification read & delete notification
            mark_read_resp = client.put(
                f"/api/v1/notifications/{notif_id}/read",
                headers=gov_headers,
            )
            assert mark_read_resp.status_code == 200
            assert mark_read_resp.json()["is_read"] is True

            client.delete(
                f"/api/v1/notifications/{notif_id}",
                headers=gov_headers,
            )
        finally:
            # Clean up the integration test decision
            del_resp = client.delete(
                f"/api/v1/decisions/{decision_id}",
                headers=admin_headers,
            )
            assert del_resp.status_code == 200


def test_websocket_realtime_connection_and_ping_pong():
    """Verify WebSocket (/ws) connection establishment and bidirectional ping/pong."""
    with TestClient(app) as client:
        admin_auth = _login(client, "admin@parallaxai.io", "admin123")
        token = admin_auth["access_token"]

        with client.websocket_connect(f"/ws?token={token}") as ws:
            welcome = ws.receive_json()
            assert welcome["type"] == "connection_established"

            ws.send_json({"type": "ping"})
            reply = ws.receive_json()
            assert reply["type"] == "pong"

