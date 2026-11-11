"""
Phase 5 Verification Tests:
- Redis-backed rate limiting (Login 5/min/IP, Registration 3/hr/IP, Password Reset 3/hr/IP)
- HTTP 429 Too Many Requests + Retry-After and X-RateLimit-* headers
- Graceful fallback to in-memory rate limiting when Redis connection fails
- Security headers (X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Cache-Control)
- Google OAuth 2.0 / OIDC placeholder:
  - Honest 503 Unavailable status when credentials are not configured
  - Cryptographic state generation, signature verification, replay protection, and redirect_uri validation
  - ID token signature, issuer, audience, and expiration verification
  - Secure account linking & default VIEWER role provisioning
"""

import time
import uuid
import jwt
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.app import app
from backend.core.config import settings
from backend.database.seed import seed_database
from backend.database.session import SessionLocal
from backend.middleware.rate_limit import rate_limiter_store, reset_rate_limits
from backend.services.google_oauth_service import (
    create_oauth_state,
    link_or_create_google_user,
    validate_redirect_uri,
    verify_and_consume_oauth_state,
    verify_google_id_token,
)


def _ensure_seeded() -> None:
    with SessionLocal() as session:
        seed_database(session)


def test_login_rate_limiting_and_retry_after_headers():
    _ensure_seeded()
    reset_rate_limits()
    client = TestClient(app)

    # Login limit is 5 requests / minute / IP
    for attempt in range(1, 6):
        resp = client.post(
            "/api/v1/auth/login",
            headers={"X-Forwarded-For": "203.0.113.10"},
            json={"email": "admin@parallaxai.io", "password": "wrong-password"},
        )
        assert resp.status_code == 401
        assert resp.headers.get("X-RateLimit-Limit") == "5"
        assert resp.headers.get("X-RateLimit-Remaining") == str(5 - attempt)

    # 6th request within the same minute must return 429 Too Many Requests + Retry-After
    blocked = client.post(
        "/api/v1/auth/login",
        headers={"X-Forwarded-For": "203.0.113.10"},
        json={"email": "admin@parallaxai.io", "password": "admin123"},
    )
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers
    assert int(blocked.headers["Retry-After"]) >= 1
    body = blocked.json()
    assert body["error"] == "too_many_requests"
    assert body["limit"] == 5


def test_registration_and_password_reset_rate_limiting():
    _ensure_seeded()
    reset_rate_limits()
    client = TestClient(app)

    # Registration limit is 3 requests / hour / IP
    for i in range(3):
        email = f"rl_reg_{i}_{uuid.uuid4().hex[:6]}@parallaxai.io"
        resp = client.post(
            "/api/v1/auth/register",
            headers={"X-Forwarded-For": "203.0.113.25"},
            json={
                "full_name": f"Rate Limit User {i}",
                "email": email,
                "password": "SafePassword!123",
                "accept_terms": True,
            },
        )
        assert resp.status_code == 201

    # 4th registration from the same IP is rate-limited (429)
    resp_4th = client.post(
        "/api/v1/auth/register",
        headers={"X-Forwarded-For": "203.0.113.25"},
        json={
            "full_name": "Rate Limit User 4",
            "email": f"rl_reg_4_{uuid.uuid4().hex[:6]}@parallaxai.io",
            "password": "SafePassword!123",
            "accept_terms": True,
        },
    )
    assert resp_4th.status_code == 429
    assert "Retry-After" in resp_4th.headers

    # Password reset limit is 3 requests / hour / IP
    for _ in range(3):
        pw_resp = client.post(
            "/api/v1/auth/forgot-password",
            headers={"X-Forwarded-For": "203.0.113.50"},
            json={"email": "admin@parallaxai.io"},
        )
        assert pw_resp.status_code == 200

    pw_4th = client.post(
        "/api/v1/auth/forgot-password",
        headers={"X-Forwarded-For": "203.0.113.50"},
        json={"email": "admin@parallaxai.io"},
    )
    assert pw_4th.status_code == 429


def test_graceful_fallback_when_redis_unavailable(monkeypatch):
    """Verify rate limiting continues working safely via in-memory fallback if Redis is unreachable."""
    reset_rate_limits()
    monkeypatch.setattr(rate_limiter_store, "_get_redis", lambda: None)

    allowed_1, count_1, rem_1, _ = rate_limiter_store.increment_and_check(
        "fallback_test_ip", limit=2, window_seconds=60
    )
    assert allowed_1 is True
    assert count_1 == 1
    assert rem_1 == 1

    allowed_2, count_2, rem_2, _ = rate_limiter_store.increment_and_check(
        "fallback_test_ip", limit=2, window_seconds=60
    )
    assert allowed_2 is True
    assert count_2 == 2
    assert rem_2 == 0

    allowed_3, count_3, rem_3, retry_after = rate_limiter_store.increment_and_check(
        "fallback_test_ip", limit=2, window_seconds=60
    )
    assert allowed_3 is False
    assert count_3 == 3
    assert rem_3 == 0
    assert retry_after >= 1


def test_security_headers_present():
    client = TestClient(app)
    resp = client.get("/api/v1/auth/providers")
    assert resp.status_code == 200
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "no-store" in resp.headers.get("Cache-Control", "")


def test_google_oauth_honest_unavailable_state_and_security_validations():
    _ensure_seeded()
    client = TestClient(app)

    # 1. When GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET are unconfigured, /providers and /google/login honestly report unavailable
    prov = client.get("/api/v1/auth/providers").json()
    assert prov["google_oauth_enabled"] is False
    assert "GOOGLE_CLIENT_ID" in prov["google_oauth_message"]

    login_resp = client.get("/api/v1/auth/google/login")
    assert login_resp.status_code == 503
    assert "GOOGLE_CLIENT_ID" in login_resp.json()["detail"]

    callback_resp = client.get("/api/v1/auth/google/callback?code=fake&state=fake")
    assert callback_resp.status_code == 503

    # 2. Validate OAuth state HMAC signing, replay protection, and redirect_uri validation
    state_token = create_oauth_state("http://localhost:5173")
    verified = verify_and_consume_oauth_state(state_token)
    assert verified["redirect_uri"] == "http://localhost:5173"

    # Replaying the same state token must fail (400)
    with pytest.raises(HTTPException) as exc_replay:
        verify_and_consume_oauth_state(state_token)
    assert exc_replay.value.status_code == 400

    # Tampered signature must fail (400)
    tampered = state_token[:-4] + "0000"
    with pytest.raises(HTTPException) as exc_tamper:
        verify_and_consume_oauth_state(tampered)
    assert exc_tamper.value.status_code == 400

    # Disallowed redirect_uri origin must fail (400)
    with pytest.raises(HTTPException) as exc_redir:
        validate_redirect_uri("https://malicious-attacker.example.com/callback")
    assert exc_redir.value.status_code == 400

    # 3. Validate Google ID token claims verification (issuer, audience, expiration, signature)
    test_secret = "test-oidc-signing-secret-key-32-bytes"
    client_id = "parallaxai-test-client-id.apps.googleusercontent.com"
    now = int(time.time())

    valid_id_token = jwt.encode(
        {
            "iss": "https://accounts.google.com",
            "aud": client_id,
            "sub": f"google_sub_{uuid.uuid4().hex[:10]}",
            "email": f"oauth_user_{uuid.uuid4().hex[:6]}@parallaxai.io",
            "email_verified": True,
            "name": "Verified OAuth User",
            "iat": now,
            "exp": now + 3600,
        },
        test_secret,
        algorithm="HS256",
    )
    claims = verify_google_id_token(
        valid_id_token,
        signing_key=test_secret,
        expected_client_id=client_id,
        algorithms=["HS256"],
    )
    assert claims["email_verified"] is True

    # Wrong audience must be rejected (401)
    with pytest.raises(HTTPException) as exc_aud:
        verify_google_id_token(
            valid_id_token,
            signing_key=test_secret,
            expected_client_id="wrong-client-id",
            algorithms=["HS256"],
        )
    assert exc_aud.value.status_code == 401

    # Wrong issuer must be rejected (401)
    bad_issuer_token = jwt.encode(
        {
            "iss": "https://evil-issuer.example.com",
            "aud": client_id,
            "sub": "sub_123",
            "email": "user@parallaxai.io",
            "email_verified": True,
            "iat": now,
            "exp": now + 3600,
        },
        test_secret,
        algorithm="HS256",
    )
    with pytest.raises(HTTPException) as exc_iss:
        verify_google_id_token(
            bad_issuer_token,
            signing_key=test_secret,
            expected_client_id=client_id,
            algorithms=["HS256"],
        )
    assert exc_iss.value.status_code == 401

    # 4. Secure account linking assigns default VIEWER role to new Google OAuth user
    with SessionLocal() as session:
        linked_user = link_or_create_google_user(session, claims)
        assert linked_user.email == claims["email"]
        assert linked_user.google_sub == claims["sub"]
        assert linked_user.primary_role == "VIEWER"
        assert "VIEWER" in linked_user.role_names

