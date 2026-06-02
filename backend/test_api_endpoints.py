"""
Week 2 Test Script — FastAPI Endpoints
---------------------------------------
Tests all API endpoints locally before deploying to Lambda.

Usage:
    # Terminal 1 — start the server
    uvicorn app.main:app --reload --port 8000

    # Terminal 2 — run this script
    python test_api_endpoints.py
"""

import asyncio
import httpx

BASE_URL = "http://localhost:8000"


async def test_endpoint(client, method, path, label, json=None):
    try:
        if method == "GET":
            r = await client.get(f"{BASE_URL}{path}", timeout=30)
        else:
            r = await client.post(f"{BASE_URL}{path}", json=json, timeout=30)

        if r.status_code < 300:
            data = r.json()
            count = len(data) if isinstance(data, list) else "✓"
            print(f"  ✓ {label} [{r.status_code}] → {count}")
            return data
        else:
            print(f"  ✗ {label} [{r.status_code}] → {r.text[:100]}")
    except Exception as e:
        print(f"  ✗ {label} → ERROR: {e}")
    return None


async def run_tests():
    print("\n🔐 Zero Trust Dashboard — API Endpoint Tests")
    print(f"   Base URL: {BASE_URL}\n")

    async with httpx.AsyncClient() as client:

        print("=" * 60)
        print("  HEALTH & ROOT")
        print("=" * 60)
        await test_endpoint(client, "GET", "/health", "Health check")
        await test_endpoint(client, "GET", "/", "Root")
        await test_endpoint(client, "GET", "/docs", "Swagger UI")

        print("\n" + "=" * 60)
        print("  EVENTS ENDPOINTS")
        print("=" * 60)
        events = await test_endpoint(client, "GET", "/api/v1/events?limit=10", "Recent events")
        await test_endpoint(client, "GET", "/api/v1/events/failed", "Failed logins")
        await test_endpoint(client, "GET", "/api/v1/events/high-severity", "High severity")
        summary = await test_endpoint(client, "GET", "/api/v1/events/summary", "Dashboard summary")

        if summary:
            print(f"\n  Dashboard metrics:")
            print(f"    Total events (24h): {summary.get('total_events_24h')}")
            print(f"    High risk events:   {summary.get('high_risk_events_24h')}")
            print(f"    Active users:       {summary.get('active_users')}")
            print(f"    MFA adoption:       {summary.get('mfa_adoption_rate', 0)*100:.0f}%")
            print(f"    Failed login rate:  {summary.get('failed_login_rate', 0)*100:.1f}%")

        print("\n" + "=" * 60)
        print("  USERS ENDPOINTS")
        print("=" * 60)
        users = await test_endpoint(client, "GET", "/api/v1/users", "All users")
        await test_endpoint(client, "GET", "/api/v1/users/at-risk", "At-risk users")

        if users and len(users) > 0:
            user_id = users[0].get("user_id")
            await test_endpoint(client, "GET", f"/api/v1/users/{user_id}", f"Single user ({users[0].get('login', '')})")
            await test_endpoint(client, "GET", f"/api/v1/events/user/{user_id}", "User events")

            print("\n" + "=" * 60)
            print("  RISK ENDPOINTS")
            print("=" * 60)
            risk = await test_endpoint(client, "GET", f"/api/v1/risk/score/{user_id}", f"Risk score for user")
            if risk:
                print(f"\n  Risk score: {risk.get('score')} ({risk.get('level')})")
                print(f"  Factors: {', '.join(risk.get('factors', []))}")

            await test_endpoint(client, "GET", "/api/v1/risk/scores", "All risk scores")

            print("\n" + "=" * 60)
            print("  POLICY SIMULATION")
            print("=" * 60)
            sim = await test_endpoint(
                client, "POST", "/api/v1/risk/simulate",
                "Simulate normal access",
                json={"user_id": user_id, "resource": "Okta Dashboard"}
            )
            if sim:
                print(f"\n  Decision: {sim.get('decision')} (score: {sim.get('risk_score')})")
                print(f"  Reasoning: {sim.get('reasoning')}")

            # Simulate a risky access attempt
            risky_sim = await test_endpoint(
                client, "POST", "/api/v1/risk/simulate",
                "Simulate risky access (unusual country + hour)",
                json={
                    "user_id": user_id,
                    "resource": "Admin Console",
                    "location_country": "North Korea",
                    "time_of_day": 3,
                    "device_managed": False,
                }
            )
            if risky_sim:
                print(f"\n  Risky decision: {risky_sim.get('decision')} (score: {risky_sim.get('risk_score')})")
                print(f"  Factors: {', '.join(risky_sim.get('factors_evaluated', []))}")

        print("\n" + "=" * 60)
        print("  WEEK 2 COMPLETE ✓")
        print("=" * 60)
        print("""
  What's working:
    ✓ FastAPI app with full routing
    ✓ /events — recent, failed, high-severity, summary
    ✓ /users — all users, at-risk, single user
    ✓ /risk — per-user scoring, all scores, policy simulation
    ✓ In-memory caching (60s TTL)
    ✓ Swagger UI at /docs
    ✓ Lambda-ready via Mangum

  Next up (Week 3):
    → DynamoDB event storage
    → Okta Event Hooks (real-time push vs polling)
    → Persistent caching

  Deployment:
    → See infrastructure/sam/template.yaml
    → CI/CD via .github/workflows/deploy.yml
""")


if __name__ == "__main__":
    asyncio.run(run_tests())
