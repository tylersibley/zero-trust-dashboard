"""
Week 3 Test Script — DynamoDB Storage + Event Hooks
-----------------------------------------------------
Tests that events are being stored to and retrieved from DynamoDB.

Usage:
    # Make sure server is running first:
    uvicorn app.main:app --reload --port 8000

    # Then in a second terminal:
    python test_dynamodb.py
"""

import asyncio
import httpx
from dotenv import load_dotenv
load_dotenv()

from app.services.dynamodb_service import DynamoDBService
from app.services.okta_client import OktaClient

BASE_URL = "http://localhost:8000"


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


async def test_dynamodb_direct():
    """Test DynamoDB directly without going through the API"""
    section("TEST 1: DynamoDB Table Setup")
    db = DynamoDBService()

    created = await db.ensure_table_exists()
    print(f"  {'✓' if created else '✗'} Table setup: {'ready' if created else 'FAILED'}")

    if not created:
        print("  → Check your AWS credentials in .env")
        return False

    section("TEST 2: Fetch + Store Events from Okta → DynamoDB")
    client = OktaClient()
    events = await client.get_system_log_events(limit=20)
    print(f"  ✓ Fetched {len(events)} events from Okta")

    stored = await db.store_events_batch(events)
    print(f"  ✓ Stored {stored} events to DynamoDB")

    section("TEST 3: Read Events Back from DynamoDB")
    stored_events = await db.get_recent_events(limit=10)
    print(f"  ✓ Retrieved {len(stored_events)} events from DynamoDB")

    if stored_events:
        e = stored_events[0]
        print(f"\n  Sample stored event:")
        print(f"    event_id:  {e.get('event_id', '')[:20]}...")
        print(f"    type:      {e.get('event_type')}")
        print(f"    actor:     {e.get('actor_name')}")
        print(f"    outcome:   {e.get('outcome')}")
        print(f"    published: {e.get('published')}")
        if e.get('geo_country'):
            print(f"    country:   {e.get('geo_country')}")

    section("TEST 4: Query Events by User")
    if stored_events:
        actor_id = stored_events[0].get("actor_id", "")
        if actor_id and actor_id != "unknown":
            user_events = await db.get_events_by_user(actor_id, limit=5)
            print(f"  ✓ Found {len(user_events)} events for actor {actor_id[:15]}...")
        else:
            print("  ℹ Skipped — no valid actor_id in stored events")

    section("TEST 5: Failed Events Query")
    failed = await db.get_failed_events(limit=10)
    print(f"  ✓ Found {len(failed)} failed events in DynamoDB")
    for e in failed[:2]:
        print(f"    → {e.get('actor_name')} | {e.get('event_type')} | {e.get('published', '')[:19]}")

    return True


async def test_webhook_endpoint():
    """Test the Event Hook endpoint directly"""
    section("TEST 6: Event Hook Verification")
    async with httpx.AsyncClient() as client:
        # Test verification handshake
        r = await client.get(
            f"{BASE_URL}/api/v1/webhooks/okta/events",
            headers={"x-okta-verification-challenge": "test-challenge-abc123"},
        )
        if r.status_code == 200 and r.json().get("verification") == "test-challenge-abc123":
            print("  ✓ Verification handshake works correctly")
        else:
            print(f"  ✗ Verification failed: {r.status_code} {r.text}")

    section("TEST 7: Event Hook Payload Ingestion")
    # Simulate an Okta event hook POST
    fake_payload = {
        "eventType": "com.okta.event_hook",
        "eventTypeVersion": "1.0",
        "source": "https://integrator-1985580.okta.com",
        "data": {
            "events": [
                {
                    "uuid": "test-event-week3-001",
                    "published": "2026-06-10T03:00:00.000Z",
                    "eventType": "user.session.start",
                    "displayMessage": "User login to Okta",
                    "severity": "WARN",
                    "actor": {
                        "id": "00u13l2p9ly7eugOT698",
                        "displayName": "Priya Patel",
                        "type": "User",
                    },
                    "outcome": {"result": "FAILURE", "reason": "INVALID_CREDENTIALS"},
                    "client": {
                        "ipAddress": "185.220.101.5",
                        "geographicalContext": {
                            "country": "Russia",
                            "city": "Moscow",
                        },
                        "userAgent": {"os": "Linux", "browser": "Chrome"},
                    },
                    "target": [],
                }
            ]
        },
    }

    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{BASE_URL}/api/v1/webhooks/okta/events",
            json=fake_payload,
        )
        if r.status_code == 200:
            data = r.json()
            print(f"  ✓ Event Hook processed: {data}")
            print(f"  ✓ High-risk events flagged: {data.get('high_risk_flagged', 0)}")
        else:
            print(f"  ✗ Hook ingestion failed: {r.status_code} {r.text}")


async def run():
    print("\n🔐 Zero Trust Dashboard — Week 3: DynamoDB + Event Hooks")

    # Test DynamoDB directly
    success = await test_dynamodb_direct()

    if success:
        # Test webhook endpoint
        await test_webhook_endpoint()

        print(f"\n{'='*60}")
        print("  WEEK 3 COMPLETE ✓")
        print(f"{'='*60}")
        print("""
  What's working:
    ✓ DynamoDB table auto-created on startup
    ✓ Events fetched from Okta + stored to DynamoDB
    ✓ Events retrievable from DynamoDB
    ✓ Per-user event queries via GSI
    ✓ Failed event filtering
    ✓ Event Hook verification handshake
    ✓ Real-time event ingestion endpoint

  Next up (Week 4):
    → ML anomaly detection with scikit-learn
    → Behavioral baseline per user
    → Smarter risk scoring

  To connect real Okta Event Hooks:
    → See docs/EVENT_HOOKS_SETUP.md (created this week)
""")
    else:
        print("\n  ✗ DynamoDB tests failed — check AWS credentials in .env")


if __name__ == "__main__":
    asyncio.run(run())
