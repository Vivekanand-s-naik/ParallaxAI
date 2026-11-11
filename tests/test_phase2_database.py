"""
Phase 2 — Database Foundation, Migrations, Constraints, Transactions, and Idempotent Seeding Tests.
Executes against the dedicated ParallaxAI PostgreSQL instance.
"""

import uuid
import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext

from backend.database.session import (
    SessionLocal,
    AsyncSessionLocal,
    sync_engine,
    check_db_connection,
    check_async_db_connection,
)
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
from backend.database.seed import seed_database


def test_sync_db_connection():
    """Verify synchronous PostgreSQL connection check returns True."""
    assert check_db_connection() is True


@pytest.mark.asyncio
async def test_async_db_connection():
    """Verify asynchronous (asyncpg) PostgreSQL connection check returns True."""
    assert await check_async_db_connection() is True
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT current_database()"))
        db_name = result.scalar_one()
        assert db_name == "parallaxai_db"


def test_alembic_migration_is_at_head():
    """Verify the database schema is migrated to the latest Alembic head revision."""
    alembic_cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(alembic_cfg)
    head_rev = script.get_current_head()

    with sync_engine.connect() as conn:
        context = MigrationContext.configure(conn)
        current_rev = context.get_current_revision()

    assert current_rev == head_rev
    assert current_rev == "0001_initial_schema"


def test_all_expected_tables_exist():
    """Verify all 14 required tables exist in PostgreSQL."""
    inspector = inspect(sync_engine)
    table_names = set(inspector.get_table_names())
    expected_tables = {
        "users",
        "roles",
        "permissions",
        "user_roles",
        "role_permissions",
        "refresh_tokens",
        "password_reset_tokens",
        "agents",
        "decisions",
        "decision_participants",
        "votes",
        "governance_rules",
        "audit_logs",
        "notifications",
        "alembic_version",
    }
    assert expected_tables.issubset(table_names)


def test_idempotent_seeding():
    """Verify running seed_database multiple times preserves exact counts without duplicates."""
    with SessionLocal() as session:
        first_counts = seed_database(session)
        second_counts = seed_database(session)

    assert first_counts == second_counts
    assert first_counts["permissions"] == 19
    assert first_counts["roles"] == 6
    assert first_counts["users"] >= 4
    assert first_counts["agents"] >= 6
    assert first_counts["governance_rules"] >= 3
    assert first_counts["decisions"] >= 5
    assert first_counts["votes"] >= 15
    assert first_counts["audit_logs"] >= 2
    assert first_counts["notifications"] >= 5


def test_crud_and_relationships():
    """Verify CRUD operations and foreign key relationships across Decisions, Agents, Votes, and Users."""
    with SessionLocal() as session:
        # Query seeded admin user and check RBAC relationships
        admin = session.execute(
            select(UserORM).where(UserORM.username == "admin")
        ).scalar_one()
        assert admin.email == "admin@parallaxai.io"
        assert "SUPER_ADMIN" in admin.role_names
        assert "ADMIN" in admin.role_names
        assert admin.primary_role == "SUPER_ADMIN"

        super_admin_role = next(r for r in admin.roles if r.name == "SUPER_ADMIN")
        perm_names = {p.name for p in super_admin_role.permissions}
        assert "decisions:approve" in perm_names
        assert "roles:manage" in perm_names
        assert len(perm_names) == 19

        # Create a temporary decision, participant, and vote, then clean up
        agent = session.execute(
            select(AgentORM).where(AgentORM.code == "ai_gpt4")
        ).scalar_one()

        temp_decision = DecisionORM(
            title="Test CRUD Decision",
            description="Testing ORM relationships and cascade delete",
            context="Test Context",
            application_type="lending",
            priority="high",
            status="under_review",
            applicant_data={"income": 90000},
            created_by_id=admin.id,
        )
        session.add(temp_decision)
        session.flush()

        participant = DecisionParticipantORM(
            decision_id=temp_decision.id,
            agent_id=agent.id,
            participation_status="voted",
        )
        vote = VoteORM(
            decision_id=temp_decision.id,
            agent_id=agent.id,
            submitted_by_user_id=admin.id,
            vote="accept",
            recommendation="accept",
            confidence=0.92,
            justification="Strong financial profile",
            bias_indicators=[],
        )
        session.add_all([participant, vote])
        session.commit()

        # Verify relationships load properly
        session.refresh(temp_decision)
        assert len(temp_decision.participants) == 1
        assert len(temp_decision.votes) == 1
        assert temp_decision.votes[0].agent.code == "ai_gpt4"

        # Verify CASCADE delete removes participant and vote
        dec_id = temp_decision.id
        session.delete(temp_decision)
        session.commit()

        remaining_votes = session.execute(
            select(VoteORM).where(VoteORM.decision_id == dec_id)
        ).scalars().all()
        assert len(remaining_votes) == 0


def test_unique_constraints_and_transaction_rollback():
    """Verify unique constraints raise IntegrityError and rollback leaves session clean."""
    with SessionLocal() as session:
        # Attempt to insert a duplicate email in users
        dup_user = UserORM(
            username="dup_admin_test",
            email="admin@parallaxai.io",  # already exists
            full_name="Duplicate Admin",
            is_active=True,
        )
        session.add(dup_user)
        with pytest.raises(IntegrityError):
            session.flush()

        # Rollback and verify session can still query cleanly
        session.rollback()
        count = len(session.execute(select(UserORM)).scalars().all())
        assert count >= 4

    with SessionLocal() as session:
        # Attempt duplicate vote by the same agent on the same decision
        decision = session.execute(select(DecisionORM)).scalars().first()
        existing_vote = decision.votes[0]

        dup_vote = VoteORM(
            id=uuid.uuid4(),
            decision_id=decision.id,
            agent_id=existing_vote.agent_id,
            vote="reject",
            confidence=0.5,
            justification="Duplicate vote test",
        )
        session.add(dup_vote)
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

