"""
Risk Scoring Engine
-------------------
Scores users and events based on behavioral signals.
Week 4 will enhance this with proper ML anomaly detection.
For now: rule-based scoring that's transparent and explainable.
"""

from typing import Optional
from app.models.events import UserProfile, AuthEvent, RiskLevel


class RiskEngine:
    """
    Rule-based risk scoring engine.
    
    Each rule contributes a weighted score (0-100 total).
    Rules are designed to be transparent — every score comes
    with a human-readable explanation (important for demos).
    """

    def score_user(
        self,
        user: Optional[UserProfile],
        recent_events: list[AuthEvent],
    ) -> tuple[float, list[str]]:
        """
        Score a user based on their profile and recent activity.
        
        Returns:
            (score: float 0-100, factors: list of human-readable reasons)
        """
        score = 0.0
        factors = []

        if not user:
            return 50.0, ["User profile unavailable"]

        # --- MFA enrollment (biggest signal) ---
        if not user.mfa_enrolled:
            score += 35
            factors.append("No MFA enrolled — high risk baseline")
        elif len(user.mfa_factors) == 1:
            score += 5
            factors.append("Only one MFA factor enrolled")

        # --- Failed login analysis ---
        failed = [e for e in recent_events if e.outcome == "FAILURE"]
        if len(failed) >= 5:
            score += 30
            factors.append(f"{len(failed)} failed logins in 24h — possible brute force")
        elif len(failed) >= 3:
            score += 20
            factors.append(f"{len(failed)} failed logins in 24h")
        elif len(failed) >= 1:
            score += 10
            factors.append(f"{len(failed)} failed login attempt(s)")

        # --- Unusual login times ---
        odd_hour_logins = []
        for e in recent_events:
            if e.outcome == "SUCCESS" and e.published:
                hour = e.published.hour
                if hour < 6 or hour > 22:
                    odd_hour_logins.append(e)
        if odd_hour_logins:
            score += 15
            factors.append(f"Login at unusual hour ({odd_hour_logins[0].published.hour}:00 UTC)")

        # --- Multiple IP addresses ---
        ips = {e.ip_address for e in recent_events if e.ip_address}
        if len(ips) > 3:
            score += 15
            factors.append(f"Activity from {len(ips)} different IPs in 24h")
        elif len(ips) > 1:
            score += 5
            factors.append(f"Activity from {len(ips)} IPs")

        # --- Multiple countries ---
        countries = {
            e.geolocation.country for e in recent_events
            if e.geolocation and e.geolocation.country
        }
        if len(countries) > 1:
            score += 25
            factors.append(f"Logins from multiple countries: {', '.join(countries)}")

        # --- Severity signals from events ---
        high_sev = [e for e in recent_events if e.severity in ("WARN", "ERROR")]
        if high_sev:
            score += 10
            factors.append(f"{len(high_sev)} WARN/ERROR severity events")

        # --- Account status ---
        if user.status != "ACTIVE":
            score += 20
            factors.append(f"Account status: {user.status}")

        # Cap at 100
        score = min(100.0, score)

        if not factors:
            factors.append("No risk signals detected")

        return round(score, 1), factors

    def score_to_level(self, score: float) -> RiskLevel:
        """Convert numeric score to risk level enum"""
        if score >= 75:
            return RiskLevel.CRITICAL
        elif score >= 50:
            return RiskLevel.HIGH
        elif score >= 25:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def score_event(self, event: AuthEvent) -> tuple[float, list[str]]:
        """Score an individual event (used for real-time event hooks in Week 3)"""
        score = 0.0
        factors = []

        if event.outcome == "FAILURE":
            score += 30
            factors.append(f"Failed authentication: {event.outcome_reason or 'unknown reason'}")

        if event.severity == "ERROR":
            score += 25
            factors.append("ERROR severity event")
        elif event.severity == "WARN":
            score += 15
            factors.append("WARN severity event")

        if event.published:
            hour = event.published.hour
            if hour < 6 or hour > 22:
                score += 20
                factors.append(f"Occurred at unusual hour ({hour}:00 UTC)")

        return min(100.0, score), factors
