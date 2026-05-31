"""
Okta API Service
----------------
Handles all communication with Okta's APIs:
  - System Log API  → auth event stream
  - Users API       → user profiles and MFA status
  - Event Hooks     → real-time event push (Week 3)

Okta API Docs:
  https://developer.okta.com/docs/reference/api/system-log/
  https://developer.okta.com/docs/reference/api/users/
"""

import httpx
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, AsyncGenerator
from app.core.config import get_settings
from app.models.events import AuthEvent, UserProfile, GeoLocation, DeviceInfo

logger = logging.getLogger(__name__)
settings = get_settings()


class OktaClient:
    """Async client for Okta's REST APIs using API token auth"""

    def __init__(self):
        self.base_url = settings.okta_base_url
        self.headers = {
            "Authorization": f"SSWS {settings.okta_api_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    # -------------------------------------------------------------------------
    # System Log API
    # -------------------------------------------------------------------------

    async def get_system_log_events(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        filter_str: Optional[str] = None,
        limit: int = 100,
    ) -> list[AuthEvent]:
        """
        Pull events from Okta's System Log API.

        Args:
            since:      Start datetime (defaults to 24 hours ago)
            until:      End datetime (defaults to now)
            filter_str: Okta filter expression e.g. 'eventType eq "user.session.start"'
            limit:      Max events to return (Okta max per page is 1000)

        Returns:
            List of normalized AuthEvent objects
        """
        if since is None:
            since = datetime.now(timezone.utc) - timedelta(hours=24)
        if until is None:
            until = datetime.now(timezone.utc)

        params = {
            "since": since.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "until": until.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "limit": min(limit, 1000),
            "sortOrder": "DESCENDING",
        }
        if filter_str:
            params["filter"] = filter_str

        url = f"{self.base_url}/api/v1/logs"
        events = []

        async with httpx.AsyncClient() as client:
            while url and len(events) < limit:
                try:
                    response = await client.get(
                        url, headers=self.headers, params=params, timeout=30.0
                    )
                    response.raise_for_status()
                    raw_events = response.json()

                    for raw in raw_events:
                        event = self._normalize_log_event(raw)
                        if event:
                            events.append(event)

                    # Okta uses Link header for pagination
                    link_header = response.headers.get("link", "")
                    url = self._extract_next_url(link_header)
                    params = {}  # Pagination URL already has params

                    if not raw_events:
                        break

                except httpx.HTTPStatusError as e:
                    logger.error(f"Okta API error {e.response.status_code}: {e.response.text}")
                    raise
                except httpx.RequestError as e:
                    logger.error(f"Network error calling Okta: {e}")
                    raise

        logger.info(f"Fetched {len(events)} events from Okta System Log")
        return events[:limit]

    async def get_events_by_user(
        self, user_id: str, hours: int = 24
    ) -> list[AuthEvent]:
        """Get all events for a specific user in the last N hours"""
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        filter_str = f'actor.id eq "{user_id}"'
        return await self.get_system_log_events(since=since, filter_str=filter_str)

    async def get_failed_logins(self, hours: int = 24) -> list[AuthEvent]:
        """Get all failed authentication events"""
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        filter_str = 'outcome.result eq "FAILURE" and eventType sw "user.session"'
        return await self.get_system_log_events(since=since, filter_str=filter_str)

    async def get_high_severity_events(self, hours: int = 24) -> list[AuthEvent]:
        """Get WARN and ERROR severity events"""
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        filter_str = 'severity eq "WARN" or severity eq "ERROR"'
        return await self.get_system_log_events(since=since, filter_str=filter_str)

    # -------------------------------------------------------------------------
    # Users API
    # -------------------------------------------------------------------------

    async def get_users(self, limit: int = 200) -> list[UserProfile]:
        """Get all active users with their MFA enrollment status"""
        url = f"{self.base_url}/api/v1/users"
        params = {"limit": min(limit, 200), "filter": 'status eq "ACTIVE"'}
        users = []

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url, headers=self.headers, params=params, timeout=30.0
                )
                response.raise_for_status()
                raw_users = response.json()

                for raw in raw_users:
                    # Fetch MFA factors for each user
                    factors = await self._get_user_factors(client, raw["id"])
                    user = self._normalize_user(raw, factors)
                    users.append(user)

            except httpx.HTTPStatusError as e:
                logger.error(f"Okta Users API error: {e.response.text}")
                raise

        logger.info(f"Fetched {len(users)} users from Okta")
        return users

    async def get_user(self, user_id: str) -> Optional[UserProfile]:
        """Get a single user by ID or login"""
        url = f"{self.base_url}/api/v1/users/{user_id}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=self.headers, timeout=15.0)
                response.raise_for_status()
                raw = response.json()
                factors = await self._get_user_factors(client, raw["id"])
                return self._normalize_user(raw, factors)
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return None
                raise

    async def _get_user_factors(
        self, client: httpx.AsyncClient, user_id: str
    ) -> list[dict]:
        """Get enrolled MFA factors for a user"""
        url = f"{self.base_url}/api/v1/users/{user_id}/factors"
        try:
            response = await client.get(url, headers=self.headers, timeout=15.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return []

    # -------------------------------------------------------------------------
    # Data normalization helpers
    # -------------------------------------------------------------------------

    def _normalize_log_event(self, raw: dict) -> Optional[AuthEvent]:
        """Transform raw Okta System Log event into our AuthEvent model"""
        try:
            # Extract actor info
            actor = raw.get("actor", {})
            actor_id = actor.get("id")
            actor_name = actor.get("displayName") or actor.get("alternateId")
            actor_type = actor.get("type")

            # Extract target (what was being accessed)
            targets = raw.get("target", [])
            target = targets[0] if targets else {}
            target_id = target.get("id")
            target_name = target.get("displayName") or target.get("alternateId")

            # Extract outcome
            outcome = raw.get("outcome", {})
            outcome_result = outcome.get("result")
            outcome_reason = outcome.get("reason")

            # Extract geolocation from client info
            client_info = raw.get("client", {})
            geo_context = raw.get("securityContext", {}) or client_info.get("geographicalContext", {})
            geolocation = None
            if geo_context:
                geolocation = GeoLocation(
                    city=geo_context.get("city"),
                    state=geo_context.get("state"),
                    country=geo_context.get("country"),
                    lat=geo_context.get("geolocation", {}).get("lat"),
                    lon=geo_context.get("geolocation", {}).get("lon"),
                )

            # Extract device info from user agent
            user_agent_raw = client_info.get("userAgent", {})
            device = DeviceInfo(
                os=user_agent_raw.get("os"),
                browser=user_agent_raw.get("browser"),
                device_type=client_info.get("device"),
            )

            return AuthEvent(
                event_id=raw["uuid"],
                event_type=raw.get("eventType", "unknown"),
                display_message=raw.get("displayMessage", ""),
                severity=raw.get("severity", "INFO"),
                published=datetime.fromisoformat(
                    raw["published"].replace("Z", "+00:00")
                ),
                actor_id=actor_id,
                actor_name=actor_name,
                actor_type=actor_type,
                target_id=target_id,
                target_name=target_name,
                outcome=outcome_result,
                outcome_reason=outcome_reason,
                ip_address=client_info.get("ipAddress"),
                geolocation=geolocation,
                device=device,
                user_agent=user_agent_raw.get("rawUserAgent"),
                raw=raw,
            )
        except Exception as e:
            logger.warning(f"Failed to normalize event {raw.get('uuid', 'unknown')}: {e}")
            return None

    def _normalize_user(self, raw: dict, factors: list[dict]) -> UserProfile:
        """Transform raw Okta user into our UserProfile model"""
        profile = raw.get("profile", {})

        # Determine MFA enrollment
        active_factors = [f for f in factors if f.get("status") == "ACTIVE"]
        factor_types = [f.get("factorType", "") for f in active_factors]

        # Parse dates safely
        def parse_date(s):
            if not s:
                return None
            try:
                return datetime.fromisoformat(s.replace("Z", "+00:00"))
            except Exception:
                return None

        return UserProfile(
            user_id=raw["id"],
            login=profile.get("login", ""),
            email=profile.get("email", ""),
            first_name=profile.get("firstName"),
            last_name=profile.get("lastName"),
            status=raw.get("status", "UNKNOWN"),
            created=parse_date(raw.get("created")),
            last_login=parse_date(raw.get("lastLogin")),
            mfa_enrolled=len(active_factors) > 0,
            mfa_factors=factor_types,
        )

    def _extract_next_url(self, link_header: str) -> Optional[str]:
        """Parse Okta's Link header to get the next page URL"""
        if not link_header:
            return None
        for part in link_header.split(","):
            if 'rel="next"' in part:
                url = part.split(";")[0].strip().strip("<>")
                return url
        return None
