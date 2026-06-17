import asyncio
import httpx

BASE_URL = "http://localhost:8000"

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

async def run():
    print("\n🤖 Zero Trust Dashboard — Week 4: ML Anomaly Detection")

    async with httpx.AsyncClient(timeout=60.0) as client:

        section("TEST 1: ML System Status")
        r = await client.get(f"{BASE_URL}/api/v1/ml/status")
        status = r.json()
        print(f"  Models trained: {status['models_trained']}")

        section("TEST 2: Fetching Users")
        r = await client.get(f"{BASE_URL}/api/v1/users")
        users = r.json()
        print(f"  Found {len(users)} users")
        for u in users:
            print(f"    → {u['login']}")

        section("TEST 3: Training ML Models for All Users")
        r = await client.post(f"{BASE_URL}/api/v1/ml/train-all")
        train_results = r.json()
        print(f"  ✓ {train_results.get('message', 'Done')}")
        trained = [r for r in train_results.get('results', []) if r['success']]
        for result in train_results.get('results', []):
            icon = "✓" if result['success'] else "✗"
            print(f"    {icon} {result.get('login', '')} — {result.get('events_used', 0)} events, typical: {result.get('typical_hour', 'N/A')}, failure rate: {result.get('failure_rate', 'N/A')}")

        if not trained:
            print("\n  ✗ No models trained")
            return

        section("TEST 4: User Behavioral Baseline")
        user_id = trained[0]['user_id']
        login = trained[0]['login']
        r = await client.get(f"{BASE_URL}/api/v1/ml/baseline/{user_id}")
        baseline = r.json()
        profile = baseline.get('behavioral_profile', {})
        print(f"  User: {login}")
        print(f"  Events analyzed: {baseline['total_events_analyzed']}")
        print(f"  Typical login: {profile.get('typical_login_hour')} {profile.get('login_hour_window')}")
        print(f"  Known countries: {profile.get('known_countries')}")
        print(f"  Failure rate: {profile.get('historical_failure_rate')}")

        section("TEST 5: Score a NORMAL Event")
        r = await client.post(f"{BASE_URL}/api/v1/ml/score", json={"user_id": user_id, "hour": 14, "outcome": "SUCCESS"})
        result = r.json()
        print(f"  Score: {result['anomaly_score']} ({result['risk_level']}) — anomaly: {result['is_anomaly']}")

        section("TEST 6: Score a SUSPICIOUS Event")
        r = await client.post(f"{BASE_URL}/api/v1/ml/score", json={"user_id": user_id, "hour": 3, "ip_address": "185.220.101.5", "country": "Russia", "outcome": "FAILURE"})
        result = r.json()
        print(f"  Score: {result['anomaly_score']} ({result['risk_level']}) — anomaly: {result['is_anomaly']}")
        print(f"  Flags:")
        for f in result['anomalous_features']:
            print(f"    → {f}")

        section("TEST 7: Impossible Travel")
        r = await client.post(f"{BASE_URL}/api/v1/ml/score", json={"user_id": user_id, "hour": 2, "ip_address": "103.21.244.0", "country": "North Korea", "outcome": "SUCCESS"})
        result = r.json()
        print(f"  Score: {result['anomaly_score']} ({result['risk_level']}) — anomaly: {result['is_anomaly']}")
        for f in result['anomalous_features']:
            print(f"  → {f}")

        section("WEEK 4 COMPLETE ✓")

if __name__ == "__main__":
    asyncio.run(run())