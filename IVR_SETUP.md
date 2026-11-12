# CareBridge Voice Access (IVR) — Setup & Developer Guide

This guide explains how to configure, run, and test the CareBridge Voice Access (IVR) module both locally using the interactive CLI simulator and in production using Twilio (or any telecom carrier).

---

## 1. Environment Configuration

Add the following environment variables to your `.env` file or cloud configuration:

| Variable | Default Value | Description |
|---|---|---|
| `IVR_API_KEY` | `dev-ivr-secret-key-carebridge-2026` | Shared secret key required in `X-API-Key` HTTP header for all IVR endpoints. |
| `IVR_PROVIDER` | `mock` | Telephony adapter (`mock` for JSON testing, `twilio` for TwiML XML). |
| `IVR_SESSION_TIMEOUT_MINUTES` | `10` | Inactivity threshold before an abandoned call session expires. |
| `IVR_MAX_AUTH_ATTEMPTS` | `3` | Maximum incorrect PIN attempts permitted before brute-force account lockout. |
| `IVR_AUTH_LOCKOUT_MINUTES` | `15` | Lockout duration following 3 consecutive failed PIN attempts. |
| `IVR_DEFAULT_LANGUAGE` | `ta` | Default spoken language fallback (`ta` for Tamil, `en` for English). |
| `IVR_EMERGENCY_NUMBER` | `108` | National emergency ambulance telephone number announced in prompts. |

---

## 2. Interactive Local CLI Simulator

Developers can test the full IVR call flow, DTMF keypad navigation, PIN authentication, request creation, and appointment booking locally without connecting a telephony carrier or spending telecom credits.

### Running the Simulator
From the repository root:
```bash
python -m app.tools.ivr_simulator
```

### Options
```bash
python -m app.tools.ivr_simulator --help

Usage: python -m app.tools.ivr_simulator [OPTIONS]

Options:
  --phone TEXT     Caller phone number to simulate (default: 9876543203)
  --url TEXT       CareBridge backend base URL (default: http://127.0.0.1:8000)
  --api-key TEXT   IVR API Key (default: dev-ivr-secret-key-carebridge-2026)
  --lang [ta|en]   Initial preferred language (default: ta)
```

### Simulator Commands During Call
- Enter single or multi-digit numbers: `1`, `2`, `3`, `4`, `5`, `6`, `7`
- Enter 4-digit PIN: e.g. `3203#`
- Return to Main Menu: `0` or `*`
- Repeat Audio Menu: `8`
- Hangup / Disconnect: `9` or `q` or `exit`

---

## 3. Production Twilio Webhook Setup

CareBridge can receive live inbound telephone calls from ordinary button phones via Twilio Voice.

### Step 1: Set Telephony Provider in Environment
In `.env`:
```env
IVR_PROVIDER=twilio
IVR_API_KEY=your-secure-production-api-key
```

### Step 2: Expose Local or Production Backend
If testing locally with a live phone, expose your local port 8000 using ngrok or Cloudflare Tunnel:
```bash
ngrok http 8000
```
This produces a public HTTPS forwarding URL, e.g.:
`https://carebridge-telecom.ngrok-free.app`

### Step 3: Configure Twilio Phone Number Console
1. Navigate to your **Twilio Console** $\to$ **Phone Numbers** $\to$ **Active Numbers**.
2. Select your provisioned Indian or local phone number.
3. Under **Voice & Fax** $\to$ **A Call Comes In**:
   - Set to: **Webhook**
   - URL: `https://carebridge-telecom.ngrok-free.app/api/ivr/webhook`
   - HTTP Method: **HTTP POST**
4. If your carrier does not support adding custom headers directly on the initial webhook, configure Twilio Studio or a TwiML Bin with an HTTP header widget passing:
   - Header: `X-API-Key`
   - Value: `<your-secure-production-api-key>`

### Step 4: Verification
Call the phone number from any feature phone or smartphone keypad. You will immediately hear:
> *"CareBridge-க்கு நல்வரவு. தமிழில் தொடர 1-ஐ அழுத்தவும். For English, press 2."*

Press `1` for Tamil or `2` for English, and navigate using the physical phone keypad.

---

## 4. Database Migrations

The IVR module introduces three tables:
- `ivr_sessions`: Live and historical telephone call sessions.
- `ivr_interactions`: Step-by-step audit log of prompts played and keys pressed.
- `ivr_auth_attempts`: Rate-limiting and brute-force lockout tracking per phone number.

To apply migrations on any environment:
```bash
alembic upgrade head
```

To rollback:
```bash
alembic downgrade -1
```
