# Setup Guide

## Step 1 — Okta Developer Account (free)

1. Go to **https://developer.okta.com/signup/**
2. Sign up for a free developer account
3. Verify your email and log into your Okta admin console
4. Your Okta domain will look like: `https://dev-1234567.okta.com`
   - Copy this — it's your `OKTA_DOMAIN` in `.env`

---

## Step 2 — Create an API Token

API tokens let your backend authenticate with Okta's REST APIs.

1. In your Okta admin console, go to **Security → API → Tokens**
2. Click **Create Token**
3. Name it `zero-trust-dashboard-dev`
4. Copy the token value immediately — Okta only shows it once
5. Add it to your `.env` as `OKTA_API_TOKEN`

> ⚠️ Never commit your API token to GitHub. The `.env` file is in `.gitignore`.

---

## Step 3 — Create an Okta Application (for OAuth)

This is used later for the frontend login flow.

1. Go to **Applications → Applications → Create App Integration**
2. Choose **OIDC - OpenID Connect** → **Single-Page Application**
3. Name it `Zero Trust Dashboard`
4. Sign-in redirect URI: `http://localhost:3000/login/callback`
5. Sign-out redirect URI: `http://localhost:3000`
6. Copy the **Client ID** → `OKTA_CLIENT_ID` in `.env`

---

## Step 4 — Generate Test Data

Your developer account starts empty. Create some auth events:

```bash
# Option 1: Log in/out of your Okta dashboard a few times
# Option 2: Create test users
# In your Okta console: Directory → People → Add Person

# Option 3: Use the Okta CLI
brew install --cask oktactl
okta login
okta apps create
```

**Useful test scenarios to create:**
- Normal login (creates `user.session.start`)
- Wrong password (creates `user.authentication.auth_via_mfa` FAILURE)
- MFA enrollment (creates `user.mfa.factor.activate`)
- New device login (creates `policy.evaluate_sign_on`)

---

## Step 5 — Local Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Mac/Linux
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your Okta domain and API token

# Verify your Okta connection
python test_okta_connection.py

# Start the API server (Week 2+)
uvicorn app.main:app --reload --port 8000
```

---

## Step 6 — AWS Setup (Week 2)

```bash
# Install AWS CLI
brew install awscli

# Configure credentials
aws configure
# Enter: Access Key ID, Secret Access Key, Region (us-east-1), Output (json)

# Verify
aws sts get-caller-identity
```

---

## Environment Variables Reference

| Variable | Where to find it | Required |
|---|---|---|
| `OKTA_DOMAIN` | Your Okta admin console URL | ✓ |
| `OKTA_API_TOKEN` | Security → API → Tokens | ✓ |
| `OKTA_CLIENT_ID` | Applications → Your App | Week 5+ |
| `OKTA_CLIENT_SECRET` | Applications → Your App | Week 5+ |
| `AWS_REGION` | Your preferred AWS region | Week 2+ |
| `AWS_ACCESS_KEY_ID` | IAM → Users → Security credentials | Week 2+ |
| `AWS_SECRET_ACCESS_KEY` | IAM → Users → Security credentials | Week 2+ |

---

## Troubleshooting

**`401 Unauthorized` from Okta API**
- Check your `OKTA_API_TOKEN` is correct and not expired
- Tokens expire after 30 days of inactivity — create a new one if needed

**`Your token must be a valid API token`**
- Make sure there's no extra whitespace around the token in `.env`
- Format should be: `OKTA_API_TOKEN=00abc123...` (no quotes)

**No events returned**
- Normal for a fresh dev account — log in/out a few times to generate events
- Check `since` datetime — make sure you're not filtering too far back

**`ModuleNotFoundError`**
- Make sure your virtual environment is activated: `source venv/bin/activate`
- Re-run: `pip install -r requirements.txt`
