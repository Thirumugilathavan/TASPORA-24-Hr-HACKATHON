# NALAM AI Voice Access (IVR) — Setup & Developer Guide

This guide explains how to configure, run, and test the NALAM AI Voice Access (IVR) module both locally (using the mock provider and interactive CLI simulator) and in production with real telephony carriers (Twilio Programmable Voice or Exotel).

---

## 1. Telecom Provider Feasibility & Rationale

| Provider | Evaluation & Indian Number Availability | Webhook & Protocol Support | Decision |
|---|---|---|---|
| **Twilio Programmable Voice** | Supports Indian virtual numbers (+91) and toll-free numbers (1800) subject to standard TRAI / DoT enterprise KYC documentation. Offers global testing sandbox, developer CLI, and rich TwiML verbs (`<Gather>`, `<Say language="ta-IN">`, `<Dial>`, `<Hangup>`). | Standard HTTP POST form-urlencoded webhooks with robust HMAC-SHA1 cryptographic signature verification (`X-Twilio-Signature`). | **Primary Selected Provider** |
| **Exotel Voice API** | Strong domestic presence in India with local virtual numbers (080, 011, etc.). Requires commercial Indian business registration and DoT compliance onboarding. | Proprietary REST and passthrough applet webhooks. | **Supported via TelephonyProvider Abstraction** |
| **Mock Telephony Adapter** | Zero external dependencies or network credentials. Enables deterministic CI/CD, headless automated testing, and local development. | In-memory and JSON serialization simulating phone keypad clicks. | **Default Development Adapter** |

---

## 2. Environment Configuration

Add the following environment variables to your `.env` file:

```ini
# IVR & Voice Access Settings
IVR_API_KEY="dev-ivr-secret-key-carebridge-2026"
IVR_PROVIDER="twilio"                      # 'twilio' for real calls, 'mock' for local simulation
IVR_SESSION_TIMEOUT_MINUTES=10
IVR_MAX_AUTH_ATTEMPTS=3
IVR_AUTH_LOCKOUT_MINUTES=15
IVR_DEFAULT_LANGUAGE="ta"
IVR_AUDIO_BASE_URL=""
IVR_EMERGENCY_NUMBER="108"
IVR_ALLOW_DEMO_PHONE_PIN=true              # Set to 'false' in production environments
IVR_ENABLE_OUTBOUND_CALLBACKS=true
IVR_ENABLE_CALL_TRANSFER=true
IVR_TRANSFER_PHONE_NUMBER="+919876500999"  # Live healthcare support desk destination
IVR_ENABLE_CALL_RECORDING=false

# Real-Time Telephony Provider Configuration (Twilio)
TELEPHONY_PROVIDER="twilio"
TELEPHONY_ENABLED=true
TELEPHONY_ACCOUNT_SID="ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
TELEPHONY_AUTH_TOKEN="your_twilio_auth_token_here"
TELEPHONY_PHONE_NUMBER="+919876500000"     # Your purchased Twilio Indian voice number
TELEPHONY_WEBHOOK_BASE_URL="https://your-subdomain.ngrok-free.app"
TELEPHONY_WEBHOOK_SECRET="your_twilio_auth_token_here"
TELEPHONY_CALL_TIMEOUT=30
TELEPHONY_MAX_CALL_DURATION=600            # Safe call limit in seconds (10 minutes)
```

---

## 3. Production Twilio Number Provisioning & Webhook Setup

### Step 1: Provision an Indian Voice-Capable Number
1. Sign up or log in to the **Twilio Console** (`https://console.twilio.com`).
2. Go to **Phone Numbers** $\to$ **Manage** $\to$ **Buy a Number**.
3. Select **India (+91)** with capabilities **Voice** checked.
4. *Regulatory Note:* Indian Department of Telecommunications (DoT) and TRAI regulations require submitting business registration documents and address verification (KYC) for active Indian virtual numbers.
5. In development or hackathon evaluation, you may alternatively use a US/UK virtual number for inbound voice testing while awaiting regulatory clearance.

### Step 2: Expose NALAM AI Backend via Public HTTPS
Twilio requires a public HTTPS webhook endpoint. For local development or evaluation:
```bash
# Using ngrok
ngrok http 8000

# Or using Cloudflare Tunnel
cloudflared tunnel --url http://127.0.0.1:8000
```
Note the assigned HTTPS URL, e.g.:  
`https://carebridge-telecom.ngrok-free.app`

### Step 3: Configure Twilio Phone Number Console
1. Navigate to **Phone Numbers** $\to$ **Active Numbers** $\to$ Click your provisioned number.
2. Scroll to the **Voice Configuration** section:
   - **A CALL COMES IN:** Webhook
   - **URL:** `https://carebridge-telecom.ngrok-free.app/api/ivr/webhooks/incoming`
   - **HTTP METHOD:** `HTTP POST`
3. Scroll to **CALL STATUS CHANGES**:
   - **STATUS CALLBACK URL:** `https://carebridge-telecom.ngrok-free.app/api/ivr/webhooks/status`
   - **HTTP METHOD:** `HTTP POST`
4. Save the configuration.

---

## 4. Making Your First Real Telephone Call

1. **Start the NALAM AI Backend:**
   ```powershell
   Set-Location C:\Users\prabu\.gemini\antigravity\scratch\TASPORA-24-Hr-HACKATHON
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

2. **Verify Public Tunnel:**
   Ensure `ngrok` or your public ingress proxy is active and forwarding traffic to `127.0.0.1:8000`.

3. **Dial from Any Phone:**
   From an ordinary mobile phone, landline, or feature phone, dial your Twilio telephone number.

4. **Experience the Live IVR:**
   - **Welcome:** Hear the bilingual greeting: *"NALAM AI-க்கு நல்வரவு. தமிழில் தொடர 1-ஐ அழுத்தவும். For English, press 2."*
   - **Language:** Press `1` for Tamil or `2` for English.
   - **Main Menu:** The system recites the Main Menu:
     - Press `1` to discover nearby PHCs and CHCs (straight-line distance announced).
     - Press `2` to check doctor attendance (clearly distinguishes `PRESENT` from `EXPECTED`).
     - Press `3` to check medicine availability (Bayesian probability and confidence recited).
     - Press `4` to create a healthcare request or request an ASHA worker callback (requires 4-digit PIN).
     - Press `5` to inspect active appointments and confirm cancellations.
     - Press `6` to book an appointment slot.
     - Press `7` for immediate 108 emergency guidance.
     - Press `0` to transfer to a live healthcare representative.
     - Press `8` to repeat menu.
     - Press `9` to end call safely.

---

## 5. Initiating Outbound Calls & ASHA Callbacks

To dispatch an automated outbound callback to a rural patient:

```bash
curl -X POST http://127.0.0.1:8000/api/ivr/callbacks/initiate \
  -H "X-API-Key: dev-ivr-secret-key-carebridge-2026" \
  -H "Content-Type: application/json" \
  -d '{
    "to_phone": "9876543203",
    "purpose": "ASHA_CALLBACK"
  }'
```

*Note on Calling Hours:* Outbound calls are permitted only between **08:00 and 20:00 Indian Standard Time (IST)**. Any request dispatched outside these hours is rejected with `400 Bad Request` unless `IS_SIMULATED=True`.

---

## 6. Interactive Local CLI Simulator (Zero Telecom Credits)

If real carrier credentials or numbers are unprovisioned, test all call flows via the built-in terminal simulator:

```bash
python -m app.tools.ivr_simulator --phone 9876543203 --lang ta
```

### Simulator Commands:
- Single-digit navigation: `1`, `2`, `3`, `4`, `5`, `6`, `7`
- 4-digit PIN: `3203#`
- Return to Main Menu: `0` or `*`
- Repeat Audio Menu: `8`
- Disconnect: `9` or `q`

---

## 7. Running the Automated IVR Test Suite

Run all IVR unit, security, integration, and telephony tests:

```powershell
# Run dedicated telephony tests
pytest tests/test_ivr_live_telephony.py -v

# Run complete IVR test suite
pytest tests/test_ivr_*.py -v

# Run entire repository test suite (139 tests)
pytest
```

---

## 8. Troubleshooting & Common Gotchas

1. **`403 Forbidden` on Webhook:**
   - Cause: Twilio HMAC-SHA1 signature verification mismatch.
   - Solution: Ensure `TELEPHONY_AUTH_TOKEN` in `.env` matches your Twilio account auth token exactly, and `TELEPHONY_WEBHOOK_BASE_URL` matches the public HTTPS host. For local development bypass, leave `TELEPHONY_AUTH_TOKEN` empty.

2. **No DTMF Detected from Button Phone:**
   - Cause: Phone keypad sends out-of-band RFC 2833 tones or in-band audio tones.
   - Solution: Twilio automatically decodes dual-tone multi-frequency signals when `<Gather>` is active. Ensure `<Gather action="/api/ivr/webhooks/continue" method="POST">` is active.

3. **Tamil Pronunciation Quality:**
   - Twilio uses Amazon Polly neural voices for Indian languages (`ta-IN` for Tamil, `en-IN` for Indian English). Ensure prompt text contains natural, colloquial Tamil phrasing rather than complex Sanskritized terminology.
