# Setting Up Okta Event Hooks

Event Hooks let Okta push auth events to your API in real time
instead of you polling every few seconds.

## The Problem Event Hooks Solve

Without hooks:
```
Browser → User logs in → Okta records event
Dashboard polls Okta every 60s → Gets event (up to 60s delay)
```

With hooks:
```
Browser → User logs in → Okta records event
Okta immediately POSTs to your API → Stored in DynamoDB instantly
```

---

## Step 1 — Expose Your Local Server to the Internet

Okta needs a public URL to POST to. During development, use ngrok
to tunnel your local port 8000 to a public URL.

```bash
# Install ngrok (one time)
# Download from https://ngrok.com/download

# Start tunnel (every time you develop)
ngrok http 8000
```

ngrok gives you a URL like: `https://abc123.ngrok.io`
Your Event Hook URL will be: `https://abc123.ngrok.io/api/v1/webhooks/okta/events`

---

## Step 2 — Register the Event Hook in Okta

1. Go to your Okta admin console
2. Navigate to **Workflow → Event Hooks**
3. Click **Create Event Hook**
4. Fill in:
   - **Name:** `Zero Trust Dashboard`
   - **URL:** `https://YOUR_NGROK_URL/api/v1/webhooks/okta/events`
   - **Authentication:** leave blank for now (add HMAC signing later)

5. Under **Subscribe to events**, add:
   - `user.session.start` — every login attempt
   - `user.authentication.auth_via_mfa` — MFA events
   - `user.account.lock` — locked accounts
   - `policy.evaluate_sign_on` — policy evaluations
   - `user.session.end` — logouts

6. Click **Save**

---

## Step 3 — Verify the Hook

After saving, Okta shows a **Verify** button.

1. Make sure your server is running and ngrok is active
2. Click **Verify**
3. Okta sends a GET request with `x-okta-verification-challenge` header
4. Your API echoes it back → Okta marks the hook as **Verified**

---

## Step 4 — Test It

1. Open an incognito window
2. Go to `https://integrator-1985580.okta.com`
3. Try logging in (success or failure)
4. Watch your server logs — you should see the event arrive instantly
5. Check DynamoDB — the event should be stored

---

## Production Deployment

When deployed to AWS Lambda, replace the ngrok URL with your
API Gateway URL from the SAM deployment output.

The Event Hook endpoint is already wired up and ready —
just update the URL in your Okta console.
