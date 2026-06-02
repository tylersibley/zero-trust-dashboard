"""
Users API
---------
GET /api/v1/users           - All active users with security metrics
GET /api/v1/users/{id}      - Single user profile
GET /api/v1/users/at-risk   - Users with high risk scores or no MFA
"""

from fastapi import APIRouter, Path, Query, HTTPException
from app.services.okta_client import OktaClient
from app.services.cache import cached
from app.models.events import UserProfile

router = APIRouter()


@router.get("/users", response_model=list[UserProfile])
@cached(ttl_seconds=120)
async def get_users(
    limit: int = Query(default=100, ge=1, le=500),
    status: str = Query(default="ACTIVE", description="ACTIVE, SUSPENDED, DEPROVISIONED"),
):
    """
    Fetch all users with MFA enrollment status.
    MFA adoption rate is a key Zero Trust compliance metric.
    """
    client = OktaClient()
    users = await client.get_users(limit=limit)
    if status != "ALL":
        users = [u for u in users if u.status == status]
    return users


@router.get("/users/at-risk", response_model=list[UserProfile])
@cached(ttl_seconds=120)
async def get_at_risk_users():
    """
    Users flagged as security risks:
    - No MFA enrolled (biggest risk factor)
    - Haven't logged in for 30+ days (stale accounts)
    - High failed login count
    """
    client = OktaClient()
    users = await client.get_users(limit=200)

    from datetime import datetime, timedelta, timezone
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

    at_risk = []
    for user in users:
        risk_factors = []
        if not user.mfa_enrolled:
            risk_factors.append("No MFA enrolled")
        if user.last_login and user.last_login < thirty_days_ago:
            risk_factors.append("Inactive 30+ days")
        if user.failed_login_count > 3:
            risk_factors.append(f"{user.failed_login_count} failed logins")
        if risk_factors:
            at_risk.append(user)

    return at_risk


@router.get("/users/{user_id}", response_model=UserProfile)
async def get_user(
    user_id: str = Path(description="Okta user ID (00u...) or login email"),
):
    """Get a single user profile with MFA and security details."""
    client = OktaClient()
    user = await client.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")
    return user
