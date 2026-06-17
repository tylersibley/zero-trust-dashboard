"""
ML Anomaly Detection API
-------------------------
GET  /api/v1/ml/train/{user_id}     - Train model for a specific user
POST /api/v1/ml/train/all           - Train models for all users
POST /api/v1/ml/score               - Score a single event
GET  /api/v1/ml/baseline/{user_id}  - View a user's behavioral baseline
GET  /api/v1/ml/status              - Overall ML system status
"""

from fastapi import APIRouter, Path, HTTPException
from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime, timezone

from app.services.anomaly_detector import get_detector, AnomalyResult
from app.services.okta_client import OktaClient
from app.services.dynamodb_service import DynamoDBService

router = APIRouter()


class ScoreEventRequest(BaseModel):
    user_id: str
    event_id: Optional[str] = None
    hour: Optional[int] = None          # 0-23
    ip_address: Optional[str] = None
    country: Optional[str] = None
    outcome: Optional[str] = "SUCCESS"  # SUCCESS, FAILURE, CHALLENGE


class AnomalyResponse(BaseModel):
    user_id: str
    is_anomaly: bool
    anomaly_score: float
    confidence: float
    risk_level: str
    anomalous_features: list[str]
    baseline_comparison: dict[str, Any]
    scored_at: str


class TrainResponse(BaseModel):
    user_id: str
    success: bool
    events_used: int
    message: str


@router.post("/ml/train/{user_id}", response_model=TrainResponse)
@router.post("/ml/train/all")
async def train_user_model(
    user_id: str = Path(description="Okta user ID"),
):
    """
    Train an Isolation Forest model for a specific user.

    Fetches the user's last 7 days of events from Okta,
    builds a behavioral baseline, and trains the ML model.
    """
    detector = get_detector()
    client = OktaClient()

    # Fetch historical events
    events = await client.get_events_by_user(user_id=user_id, hours=168)  # 7 days

    if not events:
        raise HTTPException(
            status_code=404,
            detail=f"No events found for user {user_id}. Generate some activity first."
        )

    # Build baseline
    baseline = detector.build_baseline(user_id, events)

    if not baseline.has_enough_data():
        return TrainResponse(
            user_id=user_id,
            success=False,
            events_used=len(events),
            message=f"Only {len(events)} events found — need at least 3. Generate more activity."
        )

    # Train model
    success = detector.train_model(user_id, events)

    return TrainResponse(
        user_id=user_id,
        success=success,
        events_used=len(events),
        message=(
            f"Model trained on {len(events)} events. "
            f"Baseline: typical login hour {baseline.typical_hours[0]:.0f}:00 "
            f"(±{baseline.typical_hours[1]:.0f}h), "
            f"{baseline.known_ip_count} known IPs, "
            f"{baseline.failure_rate:.0%} historical failure rate."
        ) if success else "Training failed — check logs"
    )


@router.post("/ml/train-all")
async def train_all_models():
    """Train ML models for all active users. Run this after generating test data."""
    detector = get_detector()
    client = OktaClient()

    users = await client.get_users(limit=50)
    results = []

    for user in users:
        events = await client.get_events_by_user(user_id=user.user_id, hours=168)
        if not events:
            results.append({
                "user_id": user.user_id,
                "login": user.login,
                "success": False,
                "reason": "No events found"
            })
            continue

        baseline = detector.build_baseline(user.user_id, events)
        success = detector.train_model(user.user_id, events)

        results.append({
            "user_id": user.user_id,
            "login": user.login,
            "success": success,
            "events_used": len(events),
            "typical_hour": f"{baseline.typical_hours[0]:.0f}:00",
            "known_ips": baseline.known_ip_count,
            "failure_rate": f"{baseline.failure_rate:.0%}",
        })

    trained = sum(1 for r in results if r["success"])
    return {
        "trained": trained,
        "total_users": len(users),
        "results": results,
        "message": f"Successfully trained {trained}/{len(users)} models"
    }


@router.post("/ml/score", response_model=AnomalyResponse)
async def score_event(request: ScoreEventRequest):
    """
    Score an event against the user's ML model.

    If no model exists for the user, trains one first automatically.
    """
    detector = get_detector()
    client = OktaClient()

    # Auto-train if no model exists
    if request.user_id not in detector._models:
        events = await client.get_events_by_user(user_id=request.user_id, hours=168)
        if events:
            detector.build_baseline(request.user_id, events)
            detector.train_model(request.user_id, events)

    # Build a synthetic event dict from request params
    now = datetime.now(timezone.utc)
    if request.hour is not None:
        now = now.replace(hour=request.hour)

    event_dict = {
        "event_id": request.event_id or "manual-score",
        "published": now.isoformat(),
        "outcome": request.outcome or "SUCCESS",
        "ip_address": request.ip_address or "",
        "geo_country": request.country or "",
        "event_type": "user.session.start",
    }

    result: AnomalyResult = detector.score_event(event_dict, request.user_id)

    # Map anomaly score to risk level
    if result.anomaly_score >= 0.7:
        risk_level = "critical"
    elif result.anomaly_score >= 0.5:
        risk_level = "high"
    elif result.anomaly_score >= 0.3:
        risk_level = "medium"
    else:
        risk_level = "low"

    return AnomalyResponse(
        user_id=request.user_id,
        is_anomaly=result.is_anomaly,
        anomaly_score=result.anomaly_score,
        confidence=result.confidence,
        risk_level=risk_level,
        anomalous_features=result.anomalous_features,
        baseline_comparison=result.baseline_comparison,
        scored_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/ml/baseline/{user_id}")
async def get_user_baseline(
    user_id: str = Path(description="Okta user ID"),
):
    """View a user's behavioral baseline — what 'normal' looks like for them."""
    detector = get_detector()

    baseline = detector._baselines.get(user_id)
    if not baseline:
        # Try to build it
        client = OktaClient()
        events = await client.get_events_by_user(user_id=user_id, hours=168)
        if not events:
            raise HTTPException(status_code=404, detail="No events found for user")
        baseline = detector.build_baseline(user_id, events)

    mean_hour, std_hour = baseline.typical_hours
    return {
        "user_id": user_id,
        "total_events_analyzed": baseline.total_events,
        "model_trained": user_id in detector._models,
        "behavioral_profile": {
            "typical_login_hour": f"{mean_hour:.0f}:00 UTC",
            "login_hour_window": f"±{std_hour:.0f} hours",
            "known_ip_count": baseline.known_ip_count,
            "known_ips": list(baseline.ip_addresses)[:5],
            "known_countries": list(baseline.countries),
            "historical_failure_rate": f"{baseline.failure_rate:.1%}",
            "total_failures": baseline.failure_count,
        },
        "has_enough_data": baseline.has_enough_data(),
        "note": "More events = better anomaly detection accuracy"
    }


@router.get("/ml/status")
async def get_ml_status():
    """Overall ML system status — how many models are trained."""
    detector = get_detector()
    return {
        "models_trained": len(detector._models),
        "baselines_built": len(detector._baselines),
        "trained_users": list(detector._models.keys()),
        "status": "ready" if detector._models else "no_models_trained",
        "tip": "Call POST /api/v1/ml/train/all to train models for all users"
    }
