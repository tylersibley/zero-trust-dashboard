from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
from enum import Enum


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class GeoLocation(BaseModel):
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None


class DeviceInfo(BaseModel):
    os: Optional[str] = None
    browser: Optional[str] = None
    device_type: Optional[str] = None
    is_managed: Optional[bool] = None


class AuthEvent(BaseModel):
    """Normalized Okta System Log event"""
    event_id: str
    event_type: str                          # e.g. user.session.start
    display_message: str
    severity: str                            # DEBUG, INFO, WARN, ERROR
    published: datetime
    actor_id: Optional[str] = None
    actor_name: Optional[str] = None
    actor_type: Optional[str] = None
    target_id: Optional[str] = None
    target_name: Optional[str] = None
    outcome: Optional[str] = None           # SUCCESS, FAILURE, SKIPPED
    outcome_reason: Optional[str] = None
    ip_address: Optional[str] = None
    geolocation: Optional[GeoLocation] = None
    device: Optional[DeviceInfo] = None
    user_agent: Optional[str] = None
    raw: Optional[dict[str, Any]] = None    # Full raw event for debugging

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class RiskScore(BaseModel):
    """Risk assessment for an auth event"""
    event_id: str
    user_id: str
    score: float = Field(ge=0, le=100)
    level: RiskLevel
    factors: list[str] = []                 # Human-readable risk factors
    timestamp: datetime

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class UserProfile(BaseModel):
    """Okta user with computed security metrics"""
    user_id: str
    login: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    status: str                             # ACTIVE, SUSPENDED, etc.
    created: Optional[datetime] = None
    last_login: Optional[datetime] = None
    mfa_enrolled: bool = False
    mfa_factors: list[str] = []
    current_risk_score: float = 0.0
    risk_level: RiskLevel = RiskLevel.LOW
    recent_event_count: int = 0
    failed_login_count: int = 0

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class DashboardSummary(BaseModel):
    """Top-level metrics for the dashboard header"""
    total_events_24h: int
    high_risk_events_24h: int
    active_users: int
    mfa_adoption_rate: float               # 0.0 - 1.0
    failed_login_rate: float               # 0.0 - 1.0
    top_event_types: list[dict[str, Any]]
    risk_distribution: dict[str, int]      # {"low": 120, "medium": 15, "high": 3}
