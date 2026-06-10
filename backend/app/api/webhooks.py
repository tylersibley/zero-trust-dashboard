"""
Okta Event Hooks API
--------------------
Okta pushes auth events to this endpoint in real-time.

How it works:
1. You register this endpoint URL in your Okta admin console
2. Okta sends a one-time verification request (GET with challenge)
3. After verification, Okta POSTs every auth event as it happens
4. We store it in DynamoDB and score it immediately

Okta Event Hook docs:
https://developer.okta.com/docs/concepts/event-hooks/
"""

from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import JSONResponse
from typing import Optional
import logging
import hmac
import hashlib

from app.core.config import get_settings
from app.services.dynamodb_service import DynamoDBService
from app.services.risk_engine import RiskEngine
from app.models.events import AuthEvent, GeoLocation, DeviceInfo
from datetime import datetime

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()


def normalize_hook_event(raw: dict) -> Optional[AuthEvent]:
    """Convert Okta Event Hook payload format to our AuthEvent model."""
    try:
        actor = raw.get("actor", {})
        targets = raw.get("target", [])
        target = targets[0] if targets else {}
        outcome = raw.get("outcome", {})
        client_info = raw.get("client", {})
        geo = client_info.get("geographicalContext", {})

        geolocation = None
        if geo:
            geolocation = GeoLocation(
                city=geo.get("city"),
                state=geo.get("state"),
                country=geo.get("country"),
            )

        ua = client_info.get("userAgent", {})
        device = DeviceInfo(
            os=ua.get("os"),
            browser=ua.get("browser"),
        )

        return AuthEvent(
            event_id=raw["uuid"],
            event_type=raw.get("eventType", "unknown"),
            display_message=raw.get("displayMessage", ""),
            severity=raw.get("severity", "INFO"),
            published=datetime.fromisoformat(
                raw["published"].replace("Z", "+00:00")
            ),
            actor_id=actor.get("id"),
            actor_name=actor.get("displayName") or actor.get("alternateId"),
            target_id=target.get("id"),
            target_name=target.get("displayName"),
            outcome=outcome.get("result"),
            outcome_reason=outcome.get("reason"),
            ip_address=client_info.get("ipAddress"),
            geolocation=geolocation,
            device=device,
        )
    except Exception as e:
        logger.warning(f"Failed to normalize hook event: {e}")
        return None


@router.get("/webhooks/okta/events")
async def verify_event_hook(x_okta_verification_challenge: Optional[str] = Header(None)):
    """
    Step 1: Okta verification handshake.

    When you register this endpoint in Okta, it sends a GET request
    with a verification challenge header. We echo it back to prove
    we own this endpoint.

    Okta docs: https://developer.okta.com/docs/concepts/event-hooks/#one-time-verification-request
    """
    if x_okta_verification_challenge:
        logger.info("Okta Event Hook verification request received")
        return JSONResponse(
            content={"verification": x_okta_verification_challenge}
        )
    return {"status": "Event Hook endpoint active"}


@router.post("/webhooks/okta/events")
async def receive_event_hook(request: Request):
    """
    Step 2: Receive real-time auth events from Okta.

    Okta POSTs a batch of events every time auth activity occurs.
    We store each event in DynamoDB and score high-risk ones immediately.
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Okta wraps events in a 'data.events' array
    raw_events = payload.get("data", {}).get("events", [])

    if not raw_events:
        logger.warning("Received empty event hook payload")
        return {"processed": 0}

    db = DynamoDBService()
    engine = RiskEngine()
    processed = 0
    high_risk_count = 0

    for raw in raw_events:
        event = normalize_hook_event(raw)
        if not event:
            continue

        # Store in DynamoDB
        stored = await db.store_event(event)
        if stored:
            processed += 1

        # Score the event immediately
        score, factors = engine.score_event(event)
        if score >= settings.risk_threshold_high:
            high_risk_count += 1
            logger.warning(
                f"HIGH RISK EVENT: {event.event_type} "
                f"actor={event.actor_name} "
                f"score={score} "
                f"factors={factors}"
            )

    logger.info(
        f"Event Hook: processed={processed} "
        f"high_risk={high_risk_count} "
        f"total_received={len(raw_events)}"
    )

    # Okta expects a 200 response — anything else triggers retry
    return {"processed": processed, "high_risk_flagged": high_risk_count}
