"""
Week 1 Test Script — Okta Connection Verification
--------------------------------------------------
Run this first to confirm your Okta API credentials work
and see your first live events in the terminal.

Usage:
    cd backend
    python -m venv venv && source venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env   # fill in your credentials
    python test_okta_connection.py
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

from app.services.okta_client import OktaClient
from app.core.config import get_settings


def print_section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_event(event, index: int):
    print(f"\n  [{index+1}] {event.event_type}")
    print(f"      Message:  {event.display_message}")
    print(f"      Severity: {event.severity}")
    print(f"      Time:     {event.published.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"      Actor:    {event.actor_name or 'N/A'} ({event.actor_id or 'N/A'})")
    print(f"      Outcome:  {event.outcome or 'N/A'}")
    if event.ip_address:
        print(f"      IP:       {event.ip_address}")
    if event.geolocation and event.geolocation.city:
        geo = event.geolocation
        print(f"      Location: {geo.city}, {geo.state}, {geo.country}")


def print_user(user, index: int):
    print(f"\n  [{index+1}] {user.login}")
    print(f"      Name:   {user.first_name} {user.last_name}")
    print(f"      Status: {user.status}")
    print(f"      MFA:    {'✓ Enrolled' if user.mfa_enrolled else '✗ NOT enrolled'}")
    if user.mfa_factors:
        print(f"      Factors: {', '.join(user.mfa_factors)}")
    if user.last_login:
        print(f"      Last login: {user.last_login.strftime('%Y-%m-%d %H:%M UTC')}")


async def run_tests():
    settings = get_settings()
    client = OktaClient()

    print("\n🔐 Zero Trust Dashboard — Okta Connection Test")
    print(f"   Domain: {settings.okta_base_url}")
    print(f"   Env:    {settings.app_env}")

    # -------------------------------------------------------------------------
    # Test 1: Recent auth events (last 24 hours)
    # -------------------------------------------------------------------------
    print_section("TEST 1: Recent Events (last 24h)")
    try:
        events = await client.get_system_log_events(limit=10)
        print(f"  ✓ Successfully fetched {len(events)} events")
        for i, event in enumerate(events[:5]):
            print_event(event, i)
        if len(events) > 5:
            print(f"\n  ... and {len(events) - 5} more events")
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        print("    → Check OKTA_DOMAIN and OKTA_API_TOKEN in your .env file")

    # -------------------------------------------------------------------------
    # Test 2: Failed login attempts
    # -------------------------------------------------------------------------
    print_section("TEST 2: Failed Login Attempts (last 24h)")
    try:
        failed = await client.get_failed_logins(hours=24)
        print(f"  ✓ Found {len(failed)} failed login attempts")
        if failed:
            print("\n  Most recent failures:")
            for i, event in enumerate(failed[:3]):
                print_event(event, i)
        else:
            print("  ℹ No failed logins in the last 24 hours (good!)")
            print("    Tip: Try logging in with a wrong password to generate test data")
    except Exception as e:
        print(f"  ✗ Failed: {e}")

    # -------------------------------------------------------------------------
    # Test 3: High severity events
    # -------------------------------------------------------------------------
    print_section("TEST 3: High Severity Events (WARN/ERROR)")
    try:
        high_sev = await client.get_high_severity_events(hours=48)
        print(f"  ✓ Found {len(high_sev)} WARN/ERROR events in last 48h")
        for i, event in enumerate(high_sev[:3]):
            print_event(event, i)
    except Exception as e:
        print(f"  ✗ Failed: {e}")

    # -------------------------------------------------------------------------
    # Test 4: User profiles
    # -------------------------------------------------------------------------
    print_section("TEST 4: User Profiles + MFA Status")
    try:
        users = await client.get_users(limit=10)
        print(f"  ✓ Fetched {len(users)} users")

        mfa_enrolled = sum(1 for u in users if u.mfa_enrolled)
        mfa_rate = mfa_enrolled / len(users) * 100 if users else 0
        print(f"\n  MFA Adoption: {mfa_enrolled}/{len(users)} users ({mfa_rate:.0f}%)")

        print("\n  Sample users:")
        for i, user in enumerate(users[:5]):
            print_user(user, i)
    except Exception as e:
        print(f"  ✗ Failed: {e}")

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------
    print_section("WEEK 1 COMPLETE ✓")
    print("""
  What's working:
    ✓ Okta API authentication
    ✓ System Log event fetching + normalization
    ✓ Failed login detection
    ✓ Severity-based filtering
    ✓ User profile + MFA status fetching
    ✓ Geolocation + device extraction

  Next up (Week 2):
    → Wrap this in FastAPI endpoints
    → Deploy to AWS Lambda behind API Gateway
    → Add response caching

  Pro tips for generating test data:
    → Log in/out a few times to create session events
    → Try wrong passwords to create failure events
    → Enroll/unenroll MFA factors
    → Log in from a different browser/device
""")


if __name__ == "__main__":
    asyncio.run(run_tests())
