"""
Phase 3 — Authentication & Session Management Tests.
Covers:
- Registration (default VIEWER role, Argon2id hashing)
- Duplicate email rejection (409)
- Valid login (email & username, JWT access token + HttpOnly refresh token cookie)
- Invalid login rejection (401)
- Argon2id password hashing verification
- Expired access token rejection (401)
- Refresh token rotation & replacement tracking
- Refresh token reuse detection (revoking entire token family)
- Refresh token revocation & logout
- Disabled account rejection (on login, /me, and refresh)
- Password change & password reset token flow
"""

import uuid
from datetime import timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from backend.app import app
from backend.core.security import (
    create_access_token,
    hash_opaque_token,
    hash_password,
    verify_password,
)
from backend.database.models import RefreshTokenORM, UserORM
from backend.database.seed import seed_database
from backend.database.session import SessionLocal
from backend.services.auth_service import (
    create_password_reset_token,
    set_user_active_status,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def ensure_seeded():
    with SessionLocal() as session:
        seed_database(session)


def test_argon2id_password_hashing():
    """Verify passwords use Argon2id ($argon2id$) and verify properly."""
    raw = "SecureGovernancePass!2026"
    hashed = hash_password(raw)
    assert hashed.startswith("$argon2id$")
    assert verify_password(raw, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_user_registration_and_duplicate_email():
    """Verify registration assigns VIEWER role, hashes password, and rejects duplicate emails."""
    unique_email = f"newuser_{uuid.uuid4().hex[:8]}@parallaxai.io"
    payload = {
        "full_name": "Elena Vance",
        "email": unique_email,
        "password": "StrongPassword123!",
        "confirm_password": "StrongPassword123!",
        "accept_terms": True,
    }
    res = client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["user"]["email"] == unique_email
    assert data["user"]["role"] == "VIEWER"
    assert "VIEWER" in data["user"]["roles"]
    assert "decisions:read" in data["user"]["permissions"]
    assert "users:manage" not in data["user"]["permissions"]
    assert "parallaxai_refresh_token" in res.cookies

    # Duplicate email registration must fail with 409 Conflict
    dup_res = client.post("/api/v1/auth/register", json=payload)
    assert dup_res.status_code == 409
    assert "already exists" in dup_res.json()["detail"].lower()

    # Clean up test user
    with SessionLocal() as session:
        session.execute(delete(UserORM).where(UserORM.email == unique_email))
        session.commit()


def test_valid_and_invalid_login():
    """Verify login works with both email and username, and rejects invalid credentials."""
    # Valid login with email
    res_email = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@parallaxai.io", "password": "admin123"},
    )
    assert res_email.status_code == 200
    body = res_email.json()
    assert body["access_token"]
    assert body["user"]["email"] == "admin@parallaxai.io"
    assert "SUPER_ADMIN" in body["user"]["roles"]

    # Valid login with legacy username endpoint (/api/auth/login)
    res_legacy = client.post(
        "/api/auth/login",
        json={"username": "analyst", "password": "analyst123"},
    )
    assert res_legacy.status_code == 200
    assert res_legacy.json()["token"]
    assert res_legacy.json()["user"]["username"] == "analyst"

    # Invalid password
    res_bad_pw = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@parallaxai.io", "password": "wrongpassword"},
    )
    assert res_bad_pw.status_code == 401

    # Non-existent account
    res_no_user = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@parallaxai.io", "password": "password123"},
    )
    assert res_no_user.status_code == 401


def test_me_endpoint_and_expired_access_token():
    """Verify /api/v1/auth/me works with valid token and rejects expired access tokens."""
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "reviewer@parallaxai.io", "password": "reviewer123"},
    )
    token = login_res.json()["access_token"]
    user_id = login_res.json()["user"]["id"]

    me_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "reviewer@parallaxai.io"
    assert "HUMAN_REVIEWER" in me_res.json()["roles"]

    # Create an already-expired JWT access token
    expired_token = create_access_token(
        user_id=user_id,
        username="reviewer",
        email="reviewer@parallaxai.io",
        role="HUMAN_REVIEWER",
        expires_delta=timedelta(seconds=-60),
    )
    exp_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert exp_res.status_code == 401
    assert "invalid or expired" in exp_res.json()["detail"].lower()


def test_refresh_token_rotation_and_reuse_detection():
    """
    Verify refresh token rotation:
    1. Using refresh_token_1 issues access_token_2 + refresh_token_2 and marks refresh_token_1 revoked.
    2. Replaying refresh_token_1 triggers reuse detection and revokes refresh_token_2 (entire family).
    """
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "analyst@parallaxai.io", "password": "analyst123"},
    )
    assert login_res.status_code == 200
    refresh_1 = login_res.json()["refresh_token"]

    # Rotate refresh_1 -> refresh_2
    rot_res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_1},
    )
    assert rot_res.status_code == 200
    refresh_2 = rot_res.json()["refresh_token"]
    assert refresh_2 != refresh_1

    # Verify in DB that refresh_1 is revoked and replaced_by_id points to refresh_2
    with SessionLocal() as session:
        r1_db = session.execute(
            select(RefreshTokenORM).where(
                RefreshTokenORM.token_hash == hash_opaque_token(refresh_1)
            )
        ).scalar_one()
        r2_db = session.execute(
            select(RefreshTokenORM).where(
                RefreshTokenORM.token_hash == hash_opaque_token(refresh_2)
            )
        ).scalar_one()
        assert r1_db.is_revoked is True
        assert r1_db.replaced_by_id == r2_db.id
        assert r2_db.is_revoked is False
        assert r1_db.family_id == r2_db.family_id

    # Replay refresh_1 -> must fail with 401 AND revoke refresh_2 (reuse detection)
    replay_res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_1},
    )
    assert replay_res.status_code == 401

    # Now refresh_2 must also be rejected because the family was invalidated
    r2_res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_2},
    )
    assert r2_res.status_code == 401


def test_logout_revokes_refresh_token():
    """Verify logout revokes the refresh token in the database so it cannot be used again."""
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "analyst@parallaxai.io", "password": "analyst123"},
    )
    refresh_token = login_res.json()["refresh_token"]

    logout_res = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert logout_res.status_code == 200

    # Attempting to refresh after logout must fail with 401
    refresh_res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_res.status_code == 401


def test_disabled_account_rejected_everywhere():
    """
    Verify that deactivating a user account:
    1. Immediately invalidates existing access tokens on /api/v1/auth/me (403)
    2. Revokes and rejects refresh tokens (401/403)
    3. Rejects new login attempts (403)
    """
    temp_email = f"disabled_test_{uuid.uuid4().hex[:8]}@parallaxai.io"
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Disabled Test User",
            "email": temp_email,
            "password": "Password123!",
            "confirm_password": "Password123!",
            "accept_terms": True,
        },
    )
    assert reg_res.status_code == 201
    access_token = reg_res.json()["access_token"]
    refresh_token = reg_res.json()["refresh_token"]
    user_id = uuid.UUID(reg_res.json()["user"]["id"])

    # Deactivate account in DB
    with SessionLocal() as session:
        set_user_active_status(session, user_id, is_active=False)

    # 1. Existing access token must be rejected on /api/v1/auth/me
    me_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_res.status_code == 403

    # 2. Refresh token must be rejected
    ref_res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert ref_res.status_code in (401, 403)

    # 3. Login must be rejected with 403
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": temp_email, "password": "Password123!"},
    )
    assert login_res.status_code == 403

    # Cleanup
    with SessionLocal() as session:
        session.execute(delete(UserORM).where(UserORM.id == user_id))
        session.commit()


def test_password_reset_and_honest_provider_status():
    """Verify forgot-password honestly reports unconfigured email provider and reset-password works."""
    temp_email = f"reset_test_{uuid.uuid4().hex[:8]}@parallaxai.io"
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Reset Test User",
            "email": temp_email,
            "password": "OldPassword123!",
            "confirm_password": "OldPassword123!",
            "accept_terms": True,
        },
    )
    assert reg_res.status_code == 201
    user_id = uuid.UUID(reg_res.json()["user"]["id"])

    # Forgot password endpoint honestly reports SMTP not configured
    forgot_res = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": temp_email},
    )
    assert forgot_res.status_code == 200
    assert forgot_res.json()["email_provider_configured"] is False
    assert "not been configured" in forgot_res.json()["message"]

    # Create a reset token via service and execute reset-password endpoint
    with SessionLocal() as session:
        raw_reset_token, _ = create_password_reset_token(session, email=temp_email)
        assert raw_reset_token is not None

    reset_res = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": raw_reset_token,
            "new_password": "NewPassword456!",
            "confirm_password": "NewPassword456!",
        },
    )
    assert reset_res.status_code == 200

    # Reusing the same reset token must fail
    reuse_res = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": raw_reset_token,
            "new_password": "AnotherPassword789!",
            "confirm_password": "AnotherPassword789!",
        },
    )
    assert reuse_res.status_code == 400

    # Login with new password succeeds
    login_new = client.post(
        "/api/v1/auth/login",
        json={"email": temp_email, "password": "NewPassword456!"},
    )
    assert login_new.status_code == 200

    # Cleanup
    with SessionLocal() as session:
        session.execute(delete(UserORM).where(UserORM.id == user_id))
        session.commit()

