# Zero Trust Security Dashboard

A full-stack security monitoring dashboard built on Okta's APIs, demonstrating Zero Trust architecture principles including real-time authentication event monitoring, risk scoring, anomaly detection, and adaptive access policy simulation.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        React Frontend                           │
│         (Dashboard UI, Charts, Risk Alerts, User Views)         │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AWS API Gateway                              │
└──────────┬──────────────────┬──────────────────┬───────────────┘
           │                  │                  │
           ▼                  ▼                  ▼
    ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
    │   /events   │   │   /users    │   │    /risk    │
    │   Lambda    │   │   Lambda    │   │   Lambda    │
    └──────┬──────┘   └──────┬──────┘   └──────┬──────┘
           │                  │                  │
           └──────────────────┼──────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │     DynamoDB      │
                    │  (Event Storage)  │
                    └─────────┬─────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │  Okta System │  │  Okta Users  │  │  Okta Event  │
    │   Log API    │  │     API      │  │    Hooks     │
    └──────────────┘  └──────────────┘  └──────────────┘
```

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React, Tailwind CSS, Recharts |
| Backend | Python, FastAPI, AWS Lambda |
| Database | AWS DynamoDB |
| Identity | Okta APIs (System Log, Users, Event Hooks) |
| Infrastructure | AWS API Gateway, S3, CloudFront, Terraform |
| CI/CD | GitHub Actions |
| ML | scikit-learn (anomaly detection) |

## Features

- **Real-time auth event monitoring** — Live stream of all Okta authentication events
- **Risk scoring engine** — ML-based anomaly detection flagging unusual login behavior
- **User security profiles** — Per-user auth history, risk trends, device/location tracking
- **Zero Trust policy simulator** — Simulate adaptive access decisions based on context
- **Compliance dashboard** — MFA adoption, inactive privileged accounts, policy violations
- **Slack alerting** — Real-time notifications for high-risk events *(stretch goal)*

## Project Structure

```
zero-trust-dashboard/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI route handlers
│   │   ├── core/         # Config, auth, utilities
│   │   ├── models/       # Pydantic data models
│   │   └── services/     # Okta API clients, DynamoDB, ML
│   └── tests/
├── frontend/
│   └── src/
│       ├── components/   # Reusable UI components
│       ├── pages/        # Dashboard, Users, Risk, Policy
│       ├── hooks/        # Custom React hooks
│       └── utils/        # API calls, formatters
├── infrastructure/
│   ├── terraform/        # AWS infrastructure as code
│   └── sam/              # AWS SAM for Lambda deployment
└── docs/                 # Architecture diagrams, writeups
```

## Getting Started

See [SETUP.md](docs/SETUP.md) for full setup instructions.

### Quick Start

```bash
# Clone the repo
git clone https://github.com/yourusername/zero-trust-dashboard

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Add your Okta credentials

# Run locally
uvicorn app.main:app --reload

# Frontend setup (separate terminal)
cd frontend
npm install
npm start
```

## Roadmap

- [x] Week 1: Okta API integration & event polling
- [ ] Week 2: FastAPI backend + AWS Lambda deployment
- [ ] Week 3: DynamoDB event storage + Event Hooks
- [ ] Week 4: Anomaly detection & risk scoring
- [ ] Week 5-6: React frontend + visualizations
- [ ] Week 7: Zero Trust policy simulator
- [ ] Week 8: CI/CD pipeline + production polish
- [ ] Week 9: Documentation + portfolio writeup
- [ ] Week 10: Stretch goals (Slack alerts, SageMaker)

## Portfolio Context

Built to demonstrate enterprise identity and security architecture skills relevant to TAM, Solutions Engineer, and Solutions Architect roles. Leverages hands-on Okta API experience gained during a Customer Success internship at Okta.
