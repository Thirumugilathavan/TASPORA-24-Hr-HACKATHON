# CareBridge Voice Access (IVR) — API Specification

The CareBridge Voice Access module exposes a set of REST and Webhook endpoints enabling telephony carriers (e.g., Twilio, Exotel) and simulation tools to drive DTMF-based button-phone healthcare access.

---

## Authentication & Security

All IVR endpoints require API key authentication using the `X-API-Key` HTTP request header:

```http
X-API-Key: <IVR_API_KEY>
```

- If `X-API-Key` header is missing, the API returns `401 Unauthorized`.
- If `X-API-Key` is invalid, the API returns `403 Forbidden`.
- Constant-time string comparison (`secrets.compare_digest`) prevents timing side-channel attacks.

Standard CareBridge error envelope is returned on failure:
```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Missing or invalid IVR API key"
  }
}
```

---

## Endpoint Overview

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/ivr/webhook` | Unified carrier webhook (Twilio TwiML / Mock JSON) |
| `POST` | `/api/ivr/call/start` | Programmatically initiate an IVR session (Simulator / Outbound) |
| `POST` | `/api/ivr/call/input` | Submit DTMF button keypresses to active session |
| `GET`  | `/api/ivr/session/{id}` | Inspect live diagnostic and interaction state |
| `POST` | `/api/ivr/call/hangup` | Gracefully end an active IVR call session |
| `POST` | `/api/ivr/lookup` | Per API.md Section 9: Simplified medicine availability lookup |
| `POST` | `/api/ivr/feedback` | Per API.md Section 9: Simplified patient stock feedback |

---

## 1. Carrier Telephony Webhook

### `POST /api/ivr/webhook`
Consumes carrier events (Call start, DTMF gather callbacks, Hangup). Accepts both `application/x-www-form-urlencoded` (Twilio standard) and `application/json` (Mock provider).

#### Twilio Form Request Example
```http
POST /api/ivr/webhook HTTP/1.1
Host: api.carebridge.org
X-API-Key: dev-ivr-secret-key-carebridge-2026
Content-Type: application/x-www-form-urlencoded

CallSid=CA12345678abcdef&From=%2B919876543201&Digits=1
```

#### Twilio TwiML XML Response Example
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather numDigits="1" finishOnKey="#" timeout="8" action="/api/ivr/webhook" method="POST">
        <Say language="ta-IN">முதன்மை மெனு: அருகிலுள்ள மருத்துவமனைகளை அறிய 1-ஐ அழுத்தவும்...</Say>
    </Gather>
</Response>
```

---

## 2. Initiate Call Session

### `POST /api/ivr/call/start`
Starts a voice access session for a caller phone number.

#### Request Body
```json
{
  "caller_phone": "+91 98765-43203",
  "call_sid": "call-custom-sid-1001",
  "language": "ta"
}
```

#### Response (`201 Created`)
```json
{
  "call_sid": "call-custom-sid-1001",
  "speak_text": "CareBridge-க்கு நல்வரவு. தமிழில் தொடர 1-ஐ அழுத்தவும். For English, press 2.",
  "audio_url": null,
  "gather_dtmf": true,
  "num_digits": 1,
  "finish_on_key": "#",
  "timeout_seconds": 6,
  "hangup": false,
  "session_status": "IN_PROGRESS",
  "current_menu": "LANGUAGE_SELECT",
  "language": "ta",
  "is_verified": false,
  "error": null
}
```

---

## 3. Submit DTMF Keypad Input

### `POST /api/ivr/call/input`
Submits DTMF digits entered by the caller.

#### Request Body
```json
{
  "call_sid": "call-custom-sid-1001",
  "digits": "1"
}
```

#### Response (`200 OK`)
```json
{
  "call_sid": "call-custom-sid-1001",
  "speak_text": "முதன்மை மெனு: அருகிலுள்ள மருத்துவமனைகளை அறிய 1-ஐ அழுத்தவும். மருத்துவர் வருகை விவரம் அறிய 2-ஐ அழுத்தவும்...",
  "gather_dtmf": true,
  "num_digits": 1,
  "finish_on_key": "#",
  "timeout_seconds": 8,
  "hangup": false,
  "session_status": "IN_PROGRESS",
  "current_menu": "MAIN_MENU",
  "language": "ta",
  "is_verified": false,
  "error": null
}
```

---

## 4. Get Session Status

### `GET /api/ivr/session/{session_id}`
Returns diagnostic details of an IVR session by UUID.

#### Response (`200 OK`)
```json
{
  "id": "e3b0c442-98fc-1c14-9afc-432039876001",
  "call_sid": "call-custom-sid-1001",
  "caller_phone": "9876543203",
  "language": "ta",
  "current_menu": "MAIN_MENU",
  "is_verified": true,
  "status": "IN_PROGRESS",
  "retry_count": 0,
  "started_at": "2026-11-12T13:00:00Z",
  "last_interaction_at": "2026-11-12T13:02:15Z",
  "ended_at": null
}
```

---

## 5. Graceful Call Hangup

### `POST /api/ivr/call/hangup`
Terminates an active session and plays the polite goodbye prompt.

#### Request Body
```json
{
  "call_sid": "call-custom-sid-1001",
  "digits": ""
}
```

#### Response (`200 OK`)
```json
{
  "call_sid": "call-custom-sid-1001",
  "speak_text": "CareBridge-ஐ பயன்படுத்தியதற்கு நன்றி. நலம் பெறுங்கள்.",
  "gather_dtmf": false,
  "hangup": true,
  "session_status": "COMPLETED",
  "language": "ta",
  "is_verified": true,
  "error": null
}
```

---

## 6. Medicine Lookup (API.md Section 9)

### `POST /api/ivr/lookup`
Simplified voice lookup providing plain spoken availability statements for rural button-phone users.

#### Request Body
```json
{
  "phone": "9876543203",
  "medicine_code": "paracetamol"
}
```

#### Response (`200 OK`)
```json
{
  "speak_text": "PHC Rampur-ல் paracetamol மருந்து இருப்பு நிலை: LIKELY. மதிப்பிடப்பட்ட கிடைக்கும் வாய்ப்பு: 85 சதவீதம். இது மருத்துவ பரிந்துரை அல்ல.",
  "facility_id": "fac-uuid-1001",
  "p_available": 0.85,
  "options": []
}
```

---

## 7. Patient Feedback (API.md Section 9)

### `POST /api/ivr/feedback`
Simplified patient stock feedback recorded for health worker follow-up. Stored as `PATIENT` feedback and never directly alters probabilistic stock inventory models.

#### Request Body
```json
{
  "phone": "9876543203",
  "facility_id": "fac-uuid-1001",
  "medicine_code": "paracetamol",
  "got_it": true
}
```

#### Response (`200 OK`)
```json
{
  "status": "RECORDED",
  "message": "Thank you for your feedback. Recorded for health worker follow-up."
}
```
