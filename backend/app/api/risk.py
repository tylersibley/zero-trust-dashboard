"""
Risk API
--------
GET /api/v1/risk/score/{user_id}   - Risk score for a specific user
GET /api/v1/risk/scores            - Risk scores for all users
POST /api/v1/risk/simulate         - Simulate Zero Trust policy decision
"""

from fastapi import APIRouter, Path
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

from app.services.okta_client import OktaClient
from app.services.risk_engine import RiskEngine
from app.models.events import RiskScore, RiskLevel

router = APIRouter()


class PolicySimulationRequest(BaseModel):
    """Input for Zero Trust policy simulation"""
    user_id: str
    resource: str = "Okta Dashboard"
    ip_address: Optional[str] = None
    location_country: Optional[str] = None
    device_managed: Optional[bool] = None
    time_of_day: Optional[int] = None  # Hour 0-23


class PolicySimulationResult(BaseModel):
    """Result of Zero Trust policy evaluation"""
    decision: str           # ALLOW, CHALLENGE, DENY
    risk_score: float
    risk_level: RiskLevel
    factors_evaluated: list[str]
    reasoning: str
    recommended_action: str


@router.get("/risk/score/{user_id}", response_model=RiskScore)
async def get_user_risk_score(
    user_id: str = Path(description="Okta user ID"),
):
    """
    Calculate current risk score for a specific user based on:
    - Recent failed login attempts
    - MFA enrollment status
    - Login time anomalies
    - New device/location signals
    """
    client = OktaClient()
    engine = RiskEngine()

    user = await client.get_user(user_id)
    events = await client.get_events_by_user(user_id=user_id, hours=24)

    score, factors = engine.score_user(user, events)
    level = engine.score_to_level(score)

    return RiskScore(
        event_id=f"score_{user_id}",
        user_id=user_id,
        score=score,
        level=level,
        factors=factors,
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/risk/scores", response_model=list[RiskScore])
async def get_all_risk_scores():
    """Risk scores for all active users — used for the risk leaderboard."""
    client = OktaClient()
    engine = RiskEngine()
    users = await client.get_users(limit=100)

    scores = []
    for user in users:
        events = await client.get_events_by_user(user_id=user.user_id, hours=24)
        score, factors = engine.score_user(user, events)
        level = engine.score_to_level(score)
        scores.append(RiskScore(
            event_id=f"score_{user.user_id}",
            user_id=user.user_id,
            score=score,
            level=level,
            factors=factors,
            timestamp=datetime.now(timezone.utc),
        ))

    return sorted(scores, key=lambda x: x.score, reverse=True)


@router.post("/risk/simulate", response_model=PolicySimulationResult)
async def simulate_policy(request: PolicySimulationRequest):
    """
    Simulate a Zero Trust access decision.
    
    This is the showpiece feature — given a user + context,
    what would Okta's adaptive policy decide?
    """
    client = OktaClient()
    engine = RiskEngine()

    user = await client.get_user(request.user_id)
    events = await client.get_events_by_user(user_id=request.user_id, hours=24)

    base_score, user_factors = engine.score_user(user, events)
    context_factors = []
    context_score = 0.0

    # Evaluate contextual signals
    if request.ip_address:
        known_ips = {e.ip_address for e in events if e.ip_address and e.outcome == "SUCCESS"}
        if request.ip_address not in known_ips:
            context_score += 20
            context_factors.append(f"Unrecognized IP: {request.ip_address}")

    if request.location_country:
        known_countries = {
            e.geolocation.country for e in events
            if e.geolocation and e.geolocation.country and e.outcome == "SUCCESS"
        }
        if known_countries and request.location_country not in known_countries:
            context_score += 30
            context_factors.append(f"Unusual country: {request.location_country}")

    if request.device_managed is False:
        context_score += 15
        context_factors.append("Unmanaged device")

    if request.time_of_day is not None:
        if request.time_of_day < 6 or request.time_of_day > 22:
            context_score += 15
            context_factors.append(f"Unusual hour: {request.time_of_day}:00")

    total_score = min(100, base_score + context_score)
    level = engine.score_to_level(total_score)
    all_factors = user_factors + context_factors

    # Make policy decision
    if total_score >= 75:
        decision = "DENY"
        reasoning = "Risk score too high for access. Multiple anomalous signals detected."
        recommended_action = "Block access and alert security team. Require identity verification."
    elif total_score >= 40:
        decision = "CHALLENGE"
        reasoning = "Elevated risk detected. Step-up authentication required."
        recommended_action = "Require MFA re-verification before granting access."
    else:
        decision = "ALLOW"
        reasoning = "Risk within acceptable threshold. Normal authentication flow."
        recommended_action = "Grant access with standard session policies applied."

    return PolicySimulationResult(
        decision=decision,
        risk_score=round(total_score, 1),
        risk_level=level,
        factors_evaluated=all_factors,
        reasoning=reasoning,
        recommended_action=recommended_action,
    )
