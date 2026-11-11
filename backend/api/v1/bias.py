"""
Bias & Fairness Scanner API Router (/api/v1/bias).
Provides platform-wide fairness metrics, category bias breakdowns, ML-based decision bias analysis,
and human review escalation triggers backed by PostgreSQL and MLBiasDetector.
"""

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.permissions import require_permissions
from backend.database.models import (
    DecisionORM,
    NotificationORM,
    UserORM,
    VoteORM,
    utc_now,
)
from backend.database.session import get_db
from backend.services.governance_service import (
    record_audit_log,
    serialize_decision,
    serialize_notification,
    to_legacy_decision_and_votes,
)
from backend.services.runtime import ml_bias_detector, websocket_manager

router = APIRouter(prefix="/api/v1/bias", tags=["bias"])


@router.get("/overview")
async def get_bias_fairness_overview(
    current_user: UserORM = Depends(require_permissions("bias:read")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    decisions = list(
        db.execute(select(DecisionORM).order_by(DecisionORM.updated_at.desc()))
        .scalars()
        .all()
    )
    votes = list(db.execute(select(VoteORM)).scalars().all())
    bias_notifications = list(
        db.execute(
            select(NotificationORM)
            .where(NotificationORM.type.in_(["bias_alert", "rule_violation"]))
            .order_by(NotificationORM.timestamp.desc())
            .limit(20)
        )
        .scalars()
        .all()
    )

    votes_by_decision: Dict[uuid.UUID, List[VoteORM]] = {}
    for v in votes:
        votes_by_decision.setdefault(v.decision_id, []).append(v)

    category_Accumulator: Dict[str, List[float]] = {
        "demographic": [],
        "geographic": [],
        "economic": [],
        "experiential": [],
        "procedural": [],
    }
    demographic_parity_scores: List[float] = []
    equal_opportunity_scores: List[float] = []
    equalized_odds_scores: List[float] = []
    overall_fairness_scores: List[float] = []

    decision_analyses: List[Dict[str, Any]] = []
    anomaly_count = 0

    for d in decisions:
        d_votes = votes_by_decision.get(d.id, [])
        legacy_dec, legacy_votes = to_legacy_decision_and_votes(d, d_votes)
        report = ml_bias_detector.detect_bias(legacy_dec, legacy_votes)

        fairness = report.get("fairness_metrics", {})
        demographic_parity_scores.append(
            float(fairness.get("demographic_parity", 0.75))
        )
        equal_opportunity_scores.append(float(fairness.get("equal_opportunity", 0.75)))
        equalized_odds_scores.append(float(fairness.get("equalized_odds", 0.75)))
        overall_fairness_scores.append(float(fairness.get("overall_fairness", 0.75)))

        cat_scores = report.get("category_scores", {})
        for cat_key in category_Accumulator:
            if cat_key in cat_scores:
                category_Accumulator[cat_key].append(float(cat_scores[cat_key]))

        is_anomaly = bool(
            report.get("ml_detection", {}).get("is_anomalous", False)
            or d.bias_score > 0.7
        )
        if is_anomaly:
            anomaly_count += 1

        decision_analyses.append(
            {
                "decision_id": str(d.id),
                "title": d.title,
                "application_type": d.application_type,
                "status": d.status,
                "bias_score": round(d.bias_score, 3),
                "risk_level": d.risk_level,
                "is_anomalous": is_anomaly,
                "fairness_metrics": fairness,
                "category_scores": cat_scores,
                "bias_indicators": report.get("bias_indicators", []),
                "recommendations": report.get("recommendations", []),
                "vote_count": len(d_votes),
                "created_at": d.created_at.isoformat(),
            }
        )

    def _avg(values: List[float], default: float = 0.0) -> float:
        return round(sum(values) / len(values), 3) if values else default

    category_breakdown = [
        {
            "category": cat.capitalize(),
            "key": cat,
            "average_score": _avg(scores, 0.0),
            "max_score": round(max(scores), 3) if scores else 0.0,
            "flagged_count": sum(1 for s in scores if s > 0.5),
        }
        for cat, scores in category_Accumulator.items()
    ]

    flagged_decisions = [
        item
        for item in decision_analyses
        if item["bias_score"] > 0.4 or item["is_anomalous"]
    ]

    return {
        "summary": {
            "total_evaluated_decisions": len(decisions),
            "high_bias_count": sum(1 for d in decisions if d.bias_score > 0.7),
            "medium_bias_count": sum(
                1 for d in decisions if 0.4 < d.bias_score <= 0.7
            ),
            "low_bias_count": sum(1 for d in decisions if d.bias_score <= 0.4),
            "anomaly_count": anomaly_count,
            "average_bias_score": _avg([d.bias_score for d in decisions], 0.0),
            "ml_models_trained": bool(ml_bias_detector.is_trained),
        },
        "fairness_metrics": {
            "demographic_parity": _avg(demographic_parity_scores, 0.8),
            "equal_opportunity": _avg(equal_opportunity_scores, 0.8),
            "equalized_odds": _avg(equalized_odds_scores, 0.8),
            "overall_fairness": _avg(overall_fairness_scores, 0.8),
        },
        "category_breakdown": category_breakdown,
        "flagged_decisions": flagged_decisions,
        "all_decision_analyses": decision_analyses,
        "recent_bias_alerts": [
            serialize_notification(n).model_dump(mode="json")
            for n in bias_notifications
        ],
    }


@router.post("/analyze/{decision_id}")
async def analyze_decision_bias_endpoint(
    decision_id: uuid.UUID,
    current_user: UserORM = Depends(require_permissions("bias:read")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    decision = db.execute(
        select(DecisionORM).where(DecisionORM.id == decision_id)
    ).scalar_one_or_none()
    if decision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found"
        )

    votes = list(
        db.execute(select(VoteORM).where(VoteORM.decision_id == decision.id))
        .scalars()
        .all()
    )
    legacy_dec, legacy_votes = to_legacy_decision_and_votes(decision, votes)
    report = ml_bias_detector.detect_bias(legacy_dec, legacy_votes)

    # Sync updated bias score if different
    computed_score = float(report.get("overall_bias_score", decision.bias_score))
    decision.bias_score = round(computed_score, 3)
    decision.risk_level = (
        "high"
        if decision.bias_score > 0.7
        else "medium"
        if decision.bias_score > 0.4
        else "low"
    )
    decision.updated_at = utc_now()
    db.commit()
    db.refresh(decision)

    return {
        "decision": serialize_decision(db, decision).model_dump(mode="json"),
        "bias_analysis": report,
    }


@router.post("/trigger-review", status_code=status.HTTP_201_CREATED)
async def trigger_bias_human_review(
    decision_id: uuid.UUID = Body(..., embed=True),
    reason: str = Body(
        default="Flagged in Bias & Fairness Scanner for human governance review",
        embed=True,
    ),
    current_user: UserORM = Depends(require_permissions("bias:read")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    decision = db.execute(
        select(DecisionORM).where(DecisionORM.id == decision_id)
    ).scalar_one_or_none()
    if decision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found"
        )

    prev_status = decision.status
    if decision.status == "pending":
        decision.status = "under_review"
    decision.updated_at = utc_now()

    notif = NotificationORM(
        id=uuid.uuid4(),
        type="bias_alert",
        title=f"Bias Review Requested: {decision.title[:80]}",
        message=f"{current_user.full_name} triggered a fairness & bias review: {reason}",
        priority="high" if decision.bias_score > 0.7 else "medium",
        is_read=False,
        related_decision_id=decision.id,
        timestamp=utc_now(),
    )
    db.add(notif)

    audit_entry = record_audit_log(
        session=db,
        action=f"Triggered bias & fairness review: {reason}",
        event_type="bias_review_triggered",
        decision_id=decision.id,
        actor_user=current_user,
        actor_type="user",
        previous_status=prev_status,
        new_status=decision.status,
        compliance_status="under_review",
        metadata={"bias_score": decision.bias_score, "reason": reason},
    )

    db.commit()
    db.refresh(notif)

    serialized_notif = serialize_notification(notif)
    await websocket_manager.broadcast(
        {
            "type": "bias_review_triggered",
            "data": {
                "decision_id": str(decision.id),
                "notification": serialized_notif.model_dump(mode="json"),
                "audit_id": str(audit_entry.id),
            },
        }
    )

    return {
        "message": "Bias review triggered and notification created",
        "decision_id": str(decision.id),
        "notification": serialized_notif.model_dump(mode="json"),
    }

