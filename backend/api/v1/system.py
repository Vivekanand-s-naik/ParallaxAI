"""
System Statistics, Health, and Settings API Router (/api/v1/system).
Provides real-time Command Center metrics, time-series activity from PostgreSQL,
and safe service health/configuration inspection without exposing secrets.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import redis
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.auth import get_current_user_orm
from backend.core.config import settings
from backend.core.permissions import require_permissions
from backend.database.models import (
    AgentORM,
    AuditLogORM,
    DecisionORM,
    NotificationORM,
    UserORM,
    VoteORM,
    utc_now,
)
from backend.database.session import check_db_connection, get_db
from backend.services.governance_service import (
    compute_platform_stats,
    serialize_agent,
    serialize_audit_log,
    serialize_decision,
    serialize_notification,
)
from backend.services.runtime import ai_integration, ml_bias_detector, websocket_manager

router = APIRouter(prefix="/api/v1/system", tags=["system"])


def _check_redis_status() -> Dict[str, Any]:
    try:
        client = redis.Redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=1.5,
            socket_timeout=1.5,
            decode_responses=True,
        )
        pong = bool(client.ping())
        client.close()
        return {"connected": pong, "status": "healthy" if pong else "degraded"}
    except Exception:
        return {"connected": False, "status": "unavailable"}


@router.get("/health")
async def get_system_health() -> Dict[str, Any]:
    db_ok = check_db_connection()
    redis_info = _check_redis_status()
    ws_stats = websocket_manager.get_connection_stats()
    ai_status = ai_integration.get_service_status()

    return {
        "status": "healthy" if db_ok else "degraded",
        "timestamp": utc_now().isoformat(),
        "environment": settings.ENVIRONMENT,
        "services": {
            "backend_api": {"status": "healthy", "version": "2.0.0"},
            "postgresql": {
                "status": "healthy" if db_ok else "unavailable",
                "connected": db_ok,
            },
            "redis": redis_info,
            "websocket": {
                "status": "healthy",
                "active_connections": ws_stats.get("active_connections", 0),
                "total_messages_sent": ws_stats.get("total_messages_sent", 0),
            },
            "ml_bias_engine": {
                "status": "healthy" if ml_bias_detector.is_trained else "fallback",
                "models_trained": bool(ml_bias_detector.is_trained),
            },
            "ai_providers": {
                "openai_configured": bool(ai_status.get("openai_available", False)),
                "anthropic_configured": bool(ai_status.get("anthropic_available", False)),
                "gemini_configured": bool(ai_status.get("gemini_available", False)),
                "fallback_active": bool(ai_status.get("fallback_enabled", True)),
            },
        },
    }


@router.get("/stats")
async def get_command_center_stats(
    current_user: UserORM = Depends(require_permissions("decisions:read")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    stats = compute_platform_stats(db)

    decisions = list(
        db.execute(select(DecisionORM).order_by(DecisionORM.created_at.desc()))
        .scalars()
        .all()
    )
    agents = list(
        db.execute(select(AgentORM).order_by(AgentORM.type, AgentORM.name))
        .scalars()
        .all()
    )
    votes = list(
        db.execute(select(VoteORM).order_by(VoteORM.timestamp.desc())).scalars().all()
    )
    recent_logs = list(
        db.execute(select(AuditLogORM).order_by(AuditLogORM.timestamp.desc()).limit(15))
        .scalars()
        .all()
    )
    recent_notifications = list(
        db.execute(
            select(NotificationORM).order_by(NotificationORM.timestamp.desc()).limit(10)
        )
        .scalars()
        .all()
    )

    # Build time-series decision activity buckets from actual decision timestamps (last 7 days)
    now = utc_now()
    daily_buckets: Dict[str, Dict[str, Any]] = {}
    for offset in range(6, -1, -1):
        day_dt = now - timedelta(days=offset)
        day_key = day_dt.strftime("%Y-%m-%d")
        daily_buckets[day_key] = {
            "date": day_key,
            "label": day_dt.strftime("%b %d"),
            "total": 0,
            "approved": 0,
            "rejected": 0,
            "pending": 0,
            "escalated": 0,
        }

    for d in decisions:
        d_key = d.created_at.strftime("%Y-%m-%d")
        if d_key not in daily_buckets:
            # Group older seeded decisions into their actual date bucket or earliest bucket
            daily_buckets.setdefault(
                d_key,
                {
                    "date": d_key,
                    "label": d.created_at.strftime("%b %d"),
                    "total": 0,
                    "approved": 0,
                    "rejected": 0,
                    "pending": 0,
                    "escalated": 0,
                },
            )
        bucket = daily_buckets[d_key]
        bucket["total"] += 1
        if d.status == "approved":
            bucket["approved"] += 1
        elif d.status == "rejected":
            bucket["rejected"] += 1
        elif d.status == "escalated":
            bucket["escalated"] += 1
        else:
            bucket["pending"] += 1

    decision_activity_series = [
        daily_buckets[k] for k in sorted(daily_buckets.keys())[-7:]
    ]

    # Build per-agent activity summary from real votes
    agent_activity: List[Dict[str, Any]] = []
    for a in agents:
        a_votes = [v for v in votes if v.agent_id == a.id]
        accept_cnt = sum(1 for v in a_votes if v.vote == "accept")
        reject_cnt = sum(1 for v in a_votes if v.vote == "reject")
        abstain_cnt = sum(1 for v in a_votes if v.vote == "abstain")
        avg_conf = (
            sum(v.confidence for v in a_votes) / len(a_votes)
            if a_votes
            else a.average_confidence
        )
        agent_activity.append(
            {
                "agent_id": a.code,
                "name": a.name,
                "type": a.type,
                "role": a.role,
                "provider": a.provider,
                "influence_weight": a.influence_weight,
                "is_active": a.is_active,
                "vote_count": max(a.vote_count, len(a_votes)),
                "accept_votes": accept_cnt,
                "reject_votes": reject_cnt,
                "abstain_votes": abstain_cnt,
                "average_confidence": round(avg_conf, 3),
            }
        )

    # Category distribution of decisions
    category_counts: Dict[str, int] = {}
    for d in decisions:
        category_counts[d.application_type] = (
            category_counts.get(d.application_type, 0) + 1
        )

    return {
        "kpis": stats,
        "decision_activity": decision_activity_series,
        "category_distribution": [
            {"category": k, "count": v} for k, v in category_counts.items()
        ],
        "agent_activity": agent_activity,
        "recent_decisions": [
            serialize_decision(db, d).model_dump(mode="json") for d in decisions[:8]
        ],
        "recent_audit_logs": [
            serialize_audit_log(log).model_dump(mode="json") for log in recent_logs
        ],
        "recent_notifications": [
            serialize_notification(n).model_dump(mode="json")
            for n in recent_notifications
        ],
    }


@router.get("/settings")
async def get_system_settings(
    current_user: UserORM = Depends(get_current_user_orm),
) -> Dict[str, Any]:
    db_ok = check_db_connection()
    redis_info = _check_redis_status()
    ws_stats = websocket_manager.get_connection_stats()
    ai_status = ai_integration.get_service_status()

    return {
        "platform": {
            "app_name": settings.APP_NAME,
            "environment": settings.ENVIRONMENT,
            "default_registration_role": settings.DEFAULT_REGISTRATION_ROLE,
            "access_token_expire_minutes": settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            "refresh_token_expire_days": settings.REFRESH_TOKEN_EXPIRE_DAYS,
        },
        "infrastructure": {
            "database": {
                "engine": "PostgreSQL 16 (SQLAlchemy 2.0 + Alembic)",
                "connected": db_ok,
                "status": "healthy" if db_ok else "unavailable",
            },
            "redis": {
                "engine": "Redis 7",
                "connected": redis_info["connected"],
                "status": redis_info["status"],
                "rate_limiting_enabled": settings.RATE_LIMIT_ENABLED,
            },
            "websocket": {
                "endpoint": "/ws",
                "active_connections": ws_stats.get("active_connections", 0),
                "total_messages_sent": ws_stats.get("total_messages_sent", 0),
            },
        },
        "ai_providers": {
            "openai": {
                "provider": "OpenAI",
                "model": "gpt-4o",
                "configured": bool(ai_status.get("openai_available", False)),
                "status": "ready"
                if ai_status.get("openai_available")
                else "fallback_mode",
            },
            "anthropic": {
                "provider": "Anthropic",
                "model": "claude-3-5-sonnet-20241022",
                "configured": bool(ai_status.get("anthropic_available", False)),
                "status": "ready"
                if ai_status.get("anthropic_available")
                else "fallback_mode",
            },
            "gemini": {
                "provider": "Google Gemini",
                "model": "gemini-2.5-pro",
                "configured": bool(ai_status.get("gemini_available", False)),
                "status": "ready"
                if ai_status.get("gemini_available")
                else "fallback_mode",
            },
            "ml_bias_detector": {
                "engine": "Scikit-learn IsolationForest + RandomForest",
                "trained": bool(ml_bias_detector.is_trained),
                "status": "ready" if ml_bias_detector.is_trained else "rule_based_fallback",
            },
        },
        "authentication": {
            "password_hashing": "Argon2id (argon2-cffi)",
            "session_strategy": "JWT Access Token + HttpOnly Refresh Cookie Rotation",
            "google_oauth_enabled": settings.google_oauth_enabled,
            "email_reset_configured": settings.email_provider_configured,
        },
        "rate_limits": {
            "login_per_minute": settings.RATE_LIMIT_LOGIN_PER_MINUTE,
            "register_per_hour": settings.RATE_LIMIT_REGISTER_PER_HOUR,
            "password_reset_per_hour": settings.RATE_LIMIT_PASSWORD_RESET_PER_HOUR,
            "general_api_per_minute": settings.RATE_LIMIT_GENERAL_PER_MINUTE,
            "ai_inference_per_minute": settings.RATE_LIMIT_AI_PER_MINUTE,
            "upload_per_hour": settings.RATE_LIMIT_UPLOAD_PER_HOUR,
        },
    }

