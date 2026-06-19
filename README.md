# Zero Trust Security Dashboard

A full-stack security operations dashboard built on Okta's identity platform, demonstrating Zero Trust architecture principles through real-time threat detection, behavioral analytics, and ML-powered anomaly detection.

**Live data from a real Okta org** — not mocked or simulated.

---

## What It Does

Traditional security models trust users by default once inside the network. Zero Trust assumes breach: every access request is verified continuously, not just at login.

This dashboard operationalizes that model by pulling identity telemetry from Okta's APIs, scoring user risk in real time, and surfacing anomalies using machine learning — the same architecture used in enterprise SIEM and UEBA tools.

---

## Features

### Overview
- Org-wide risk gauge derived from live event distribution
- 24-hour event volume and high-risk event count
- MFA adoption rate with compliance threshold alerting
- At-risk user table with one-click investigation

### User Drilldown
- Per-user behavioral baseline (typical login hour, known IPs, failure rate)
- Risk score and risk level from ML scoring engine
- MFA enrollment status and enrolled factors
- Identity metadata pulled directly from Okta Users API

### Live Feed
- Real-time Okta System Log event stream
- Severity classification by event type (HIGH / MED / LOW)
- Auto-refreshes every 30 seconds
- Color-coded by risk level

---

## Architecture

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│   React Frontend │────▶│   FastAPI Backend     │────▶│   Okta APIs     │
│   (Vite)        │     │   (AWS Lambda)        │     │   System Log    │
│                 │     │                       │     │   Users API     │
│  - Overview     │     │  - Risk Scoring       │     │   Event Hooks   │
│  - Drilldown    │     │  - ML Anomaly Det.    │     └─────────────────┘
│  - Live Feed    │     │  - Policy Simulator   │
└─────────────────┘     │                       │     ┌─────────────────┐
                        │                       │────▶│   AWS DynamoDB  │
                        └──────────────────────┘     │   Event Storage │
                                                      └─────────────────┘
```

**Backend:** Python / FastAPI / Mangum (AWS Lambda adapter)  
**ML:** scikit-learn Isolation Forest for unsupervised anomaly detection  
**Storage:** AWS DynamoDB for event persistence  
**Identity:** Okta System Log API, Users API, Event Hooks (real-time webhooks)  
**Frontend:** React / Vite / recharts / react-router-dom  

---

## ML Anomaly Detection

The Isolation Forest model builds a behavioral baseline per user from historical Okta events:

- **Login hour distribution** — flags logins outside typical window
- **IP reputation** — surfaces new or unknown source IPs
- **Failure rate** — tracks authentication failure patterns over time
- **Event frequency** — detects spikes inconsistent with baseline behavior

Anomaly scores feed directly into the risk scoring engine, which classifies users as LOW / MEDIUM / HIGH / CRITICAL.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/events/summary` | 24h event counts, MFA adoption, risk distribution |
| GET | `/api/v1/events` | Paginated Okta system log events |
| GET | `/api/v1/users/at-risk` | Users with elevated risk scores |
| GET | `/api/v1/ml/baseline/{user_id}` | Behavioral baseline for a specific user |
| POST | `/api/v1/risk/simulate` | Simulate a Zero Trust policy decision |
| GET | `/api/v1/users` | All users with risk scores |

Full Swagger UI available at `/docs` when running locally.

---

## Running Locally

**Prerequisites:** Python 3.9+, Node 18+, Okta Developer account, AWS account

```bash
# Backend
cd backend
python -m venv venv
source venv/Scripts/activate  # Windows: . .\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Add your credentials to .env
cp .env.example .env

uvicorn app.main:app --reload --port 8000
```

```bash
# Frontend
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`

---

## Build Log

| Week | Deliverable |
|------|-------------|
| 1 | Okta API client, System Log ingestion, user profiles, MFA detection |
| 2 | FastAPI backend, 11 REST endpoints, risk scoring engine, Zero Trust policy simulator |
| 3 | DynamoDB event storage, Okta Event Hooks for real-time webhook ingestion |
| 4 | scikit-learn Isolation Forest ML model, per-user behavioral baselines |
| 5 | React frontend — Overview, User Drilldown, Live Feed — wired to live API |

---

## About

Built by [Tyler Sibley](https://tylersibley.dev) — IT student at Florida State University, Okta Certified Professional, AWS Cloud Practitioner.

This project was built to develop hands-on depth in identity security and Zero Trust architecture — the technical foundation of modern enterprise security programs.
