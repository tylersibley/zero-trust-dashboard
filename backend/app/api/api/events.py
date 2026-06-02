"""
Events API
----------
Endpoints for fetching and filtering Okta authentication events.

GET /api/v1/events              - Recent events (last 24h, paginated)
GET /api/v1/events/failed       - Failed login attempts
GET /api/v1/events/high-risk    - High severity events
GET /api/v1/events/summary      - Dashboard summary metrics
GET /api/v1/events/user/{id}    - Events for a specific user
"""

from fastapi import APIRouter, Query, Path
from typing import Optional
from datetime import datetime, timedelta, timezone

from app.services.okta_client import OktaClient
from app.services.cache import cached
from app.models.events import AuthEvent, DashboardSummary

router = APIRouter()


@router.get("/events", response_model=list[AuthEvent])
@cached(ttl_seconds=60)
async def get_events(
    hours: int = Query(default=24, ge=1, le=168, description="Hours to look back"),
    limit: int = Query(default=50, ge=1, le=200, description="Max events to return"),
    event_type: Optional[str] = Query(default=None, description="Filter by event type e.g. 'user.session.start'"),
    outcome: Optional[str] = Query(default=None, description="Filter by outcome: SUCCESS, FAILURE, CHALLENGE"),
):
    """
    Fetch recent authentication events from Okta System Log.
    
    Results are cached for 60 seconds to avoid hammering the Okta API.
    """
    client = OktaClient()
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    filter_parts = []
    if event_type:
        filter_parts.append(f'eventType eq "{event_type}"')
    if outcome:
        filter_parts.append(f'outcome.result eq "{outcome.upper()}"')

    filter_str = " and ".join(filter_parts) if filter_parts else None
    return await client.get_system_log_events(since=since, filter_str=filter_str, limit=limit)


@router.get("/events/failed", response_model=list[AuthEvent])
@cached(ttl_seconds=60)
async def get_failed_logins(
    hours: int = Query(default=24, ge=1, le=168),
    limit: int = Query(default=50, ge=1, le=200),
):
    """Get all failed authentication attempts — key input for risk scoring."""
    client = OktaClient()
    return await client.get_failed_logins(hours=hours)


@router.get("/events/high-severity", response_model=list[AuthEvent])
@cached(ttl_seconds=60)
async def get_high_severity_events(
    hours: int = Query(default=48, ge=1, le=168),
):
    """Get WARN and ERROR severity events — these always warrant attention."""
    client = OktaClient()
    return await client.get_high_severity_events(hours=hours)


@router.get("/events/summary", response_model=DashboardSummary)
@cached(ttl_seconds=120)
async def get_dashboard_summary():
    """
    Aggregate metrics for the dashboard header cards.
    
    Returns: total events, high-risk count, active users, MFA rate,
             failed login rate, top event types, risk distribution.
    """
    client = OktaClient()

    # Fetch in parallel would be ideal — keeping sequential for clarity
    all_events = await client.get_system_log_events(limit=200)
    failed_events = await client.get_failed_logins(hours=24)
    users = await client.get_users(limit=200)

    # Compute metrics
    total = len(all_events)
    failed_count = len(failed_events)
    active_users = len([u for u in users if u.status == "ACTIVE"])
    mfa_enrolled = len([u for u in users if u.mfa_enrolled])
    mfa_rate = mfa_enrolled / len(users) if users else 0.0
    failed_rate = failed_count / total if total else 0.0

    # Event type frequency
    type_counts: dict[str, int] = {}
    for e in all_events:
        type_counts[e.event_type] = type_counts.get(e.event_type, 0) + 1
    top_types = sorted(
        [{"event_type": k, "count": v} for k, v in type_counts.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:5]

    # Risk distribution (basic — will be enhanced in Week 4)
    high_risk = len([e for e in all_events if e.severity in ("WARN", "ERROR") and e.outcome == "FAILURE"])
    medium_risk = len([e for e in all_events if e.severity == "WARN"])
    low_risk = total - high_risk - medium_risk

    return DashboardSummary(
        total_events_24h=total,
        high_risk_events_24h=high_risk,
        active_users=active_users,
        mfa_adoption_rate=round(mfa_rate, 3),
        failed_login_rate=round(failed_rate, 3),
        top_event_types=top_types,
        risk_distribution={
            "low": max(0, low_risk),
            "medium": max(0, medium_risk),
            "high": max(0, high_risk),
        },
    )


@router.get("/events/user/{user_id}", response_model=list[AuthEvent])
async def get_user_events(
    user_id: str = Path(description="Okta user ID or login email"),
    hours: int = Query(default=24, ge=1, le=168),
):
    """Get all auth events for a specific user — used in user detail view."""
    client = OktaClient()
    return await client.get_events_by_user(user_id=user_id, hours=hours)
