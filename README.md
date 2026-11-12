# CareBridge – AI-Powered Rural Healthcare Accessibility & Coordination Platform

> **Tagline:** *No Wasted Trips. Better Access. Continuous Care.*

CareBridge is an AI-powered rural healthcare accessibility and coordination platform designed specifically for patients and frontline health workers (such as ASHA workers) in rural and underserved communities.

Rural patients frequently travel tens of kilometres to health centres only to discover the required doctor is absent or prescribed medicines are out of stock. CareBridge addresses this challenge by evaluating facility capabilities, doctor attendance schedules, and probabilistic medicine stock availability to compute **loss-minimized recommendations** before the patient sets out.

---

## Architecture Overview

CareBridge is built on **FastAPI**, **SQLAlchemy (Async)**, and **Alembic**, modularised into four core integrated pillars:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             CareBridge Platform                             │
├──────────────────────┬──────────────────────┬───────────────────────────────┤
│ Core Healthcare &    │ Facilities & Stock   │ Patient & Village Management  │
│ Recommendation       │ Intelligence         │                               │
├──────────────────────┼──────────────────────┼───────────────────────────────┤
│ • Healthcare Requests│ • Facility Registry  │ • Village Directory & GPS     │
│ • Loss Minimization  │ • Doctor Scheduling  │ • Patient Demographic Profile │
│ • Appointment Booking│ • Stock Ledger       │ • Multi-role Access Control   │
│ • Concurrency Locks  │ • Belief States (P)  │ • ASHA Coordination           │
└──────────────────────┴──────────────────────┴───────────────────────────────┘
```

### 1. Authentication & Security
- **Role-Based Authorization:** Strict roles: `PATIENT`, `ASHA`, `STAFF`, `DOCTOR`, `ADMIN`.
- **Public Registration:** Self-registration strictly creates `PATIENT` accounts. Client-supplied administrative roles are ignored.
- **JWT Authentication:** Stateless HMAC-SHA256 JWT bearer tokens.
- **Ownership Scoping:** Patients can only access and manipulate their own requests, profiles, and bookings. Frontline staff (`ASHA`, `STAFF`, `DOCTOR`, `ADMIN`) have administrative and delegated privileges.

### 2. Patient & Village Module
- **Villages Directory:** Registry with GPS coordinates (`latitude`, `longitude`), district, and state. Synthetic villages explicitly identify as demo geography (`is_synthetic: true`).
- **Patient Profiles:** One-to-one demographic linkage to User and home Village. Strict consent defaults to `false`; clinical staff cannot access demographic profiles without explicit consent (`HTTP 403 CONSENT_REQUIRED`).

### 3. Facility, Doctor & Medicine Stock Intelligence
- **Facility Catalogue:** Multi-criteria filtering by village, facility type (`PHC`, `CHC`, `HOSPITAL`, `PHARMACY`), and offered services.
- **Doctor Attendance & Ownership:** 
  - Explicit database linkage: `Doctor.user_id` references `users.id` with a 1-to-1 unique constraint (`uq_doctors_user_id`).
  - Attendance self-verification is strictly restricted to the doctor's own explicitly linked user account (`doc.user_id == current_user.id`).
  - Unlinked legacy doctor profiles fail closed with `HTTP 403 FORBIDDEN` until linked by `STAFF` or `ADMIN`.
  - Shifts distinguish planned (`EXPECTED`) from physically verified (`PRESENT` / `ABSENT`) attendance.
- **Probabilistic Stock State:** Append-only ledger recording evidence from `STAFF` (weight 1.0) and `ASHA` (weight 0.8). **Patient feedback never modifies medicine stock probability directly.**
- **Availability Belief States:** Calculates probability $P(\text{available})$ and confidence metric $c \in [0.0, 1.0]$, mapped to agreed contract labels (`LIKELY`, `UNCERTAIN`, `UNLIKELY`).

### 4. Recommendation Engine & Appointment Scheduling
- **Expected Trip Loss Formula:**
  $$\text{Expected Loss} = \text{round\_half\_up}(\text{Failure Probability} \times \text{Travel Cost})$$
- **Loss Minimization:** Facilities are ranked in strictly ascending order of expected journey loss.
- **Double-Booking Protection:** Partial database unique indexes prevent concurrency conflicts:
  - Doctor slot: `(doctor_id, appointment_date, appointment_time)` where `doctor_id IS NOT NULL AND status != 'CANCELLED'`.
  - Walk-in slot: `(facility_id, appointment_date, appointment_time)` where `doctor_id IS NULL AND status != 'CANCELLED'`.
- **Slot Release on Cancellation:** Cancelling an appointment frees the slot for other patients.

### 5. Voice Access & Button Phone IVR
- **Zero Smartphone / Internet Dependency:** Ordinary keypad / feature phones access CareBridge services entirely over cellular voice networks via DTMF button tones.
- **Bilingual Interface:** Spoken audio prompts in Tamil (`ta`) and English (`en`).
- **Public & Protected Workflows:** Public directory of nearby facilities, verified doctor schedules, and medicine availability. Protected actions (healthcare request creation, appointment booking, status checks/cancellations) require 4-digit PIN verification.
- **Security & Lockout:** 3 failed PIN attempts trigger a 15-minute brute-force lockout. Dedicated `X-API-Key` protects carrier webhooks. Predictable phone-derived PINs are strictly demo-only and disabled in production.
- **Emergency Bypass:** Key `7` triggers immediate 108 ambulance dispatch advice and emergency hospital routing without authentication barriers.
- **Provider Agnostic:** Pluggable adapter architecture supporting Mock (JSON / CLI simulator) and Twilio (TwiML XML).

---

## Disclosures & Safety Notices

1. **Straight-Line Distance:** Distance calculations use approximate straight-line geographical distance (Haversine formula), not road network travel distance or real-world transit time.
2. **Simulated Data:** Facility availability, stock probabilities, and attendance schedules operate in evaluation/demonstration mode for hackathon validation.
3. **Clinical Judgment Disclaimer:** CareBridge assists with administrative routing and access coordination. It does not replace clinical triage or emergency care.

---

## Getting Started

### Prerequisites
- Python 3.11+
- Virtual environment (`venv` or `conda`)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Thirumugilathavan/TASPORA-24-Hr-HACKATHON.git
   cd TASPORA-24-Hr-HACKATHON
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   # On Windows:
   .\.venv\Scripts\activate
   # On Linux / macOS:
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment configuration:**
   Copy `.env.example` to `.env` (or configure environment variables):
   ```bash
   DATABASE_URL=sqlite+aiosqlite:///./carebridge.db
   SECRET_KEY=carebridge-production-secret-key-change-in-prod
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=1440
   ```

5. **Run Database Migrations:**
   ```bash
   alembic upgrade head
   ```

6. **Start the Development Server:**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

7. **Explore Interactive API Documentation:**
   - Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
   - ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## Running the Automated Test Suite

CareBridge includes a comprehensive automated test suite covering unit, property, security, and end-to-end integration workflows.

Run all tests:
```bash
pytest -v
```

Run specific test modules:
```bash
# End-to-End full lifecycle test
pytest -v tests/test_e2e_integration.py

# Doctor ownership and schedule verification tests
pytest -v tests/test_doctors.py

# Patient privacy and village validation tests
pytest -v tests/test_patient_village.py

# Probabilistic stock intelligence algorithm tests
pytest -v tests/test_algorithm.py

# Appointment conflict & double booking tests
pytest -v tests/test_appointments.py

# Recommendation engine loss-minimization tests
pytest -v tests/test_recommendations.py

# Voice Access / IVR test suite (Unit, Security, Integration, E2E)
pytest -v tests/test_ivr_unit.py tests/test_ivr_security.py tests/test_ivr_integration.py tests/test_ivr_e2e.py
```

---

## API Summary

| Method | Endpoint | Description | Role Required |
|---|---|---|---|
| `POST` | `/api/auth/register` | Register new user account | Public (enforces `PATIENT`) |
| `POST` | `/api/auth/login` | Login and obtain JWT token | Public |
| `GET` | `/api/villages` | List villages with GPS coordinates | Authenticated |
| `POST` | `/api/patients` | Create patient profile | `PATIENT`, `ASHA`, `STAFF`, `ADMIN` |
| `GET` | `/api/patients/{id}` | Retrieve patient profile | Scoped / Clinical (requires consent) |
| `GET` | `/api/facilities` | List & filter facilities | Authenticated |
| `POST` | `/api/facilities` | Register healthcare facility | `STAFF`, `ADMIN` |
| `GET` | `/api/facilities/{id}` | Facility details with doctors & services | Authenticated |
| `GET` | `/api/doctors` | List doctors by facility | Authenticated |
| `POST` | `/api/doctors` | Register doctor (optional `user_id`) | `STAFF`, `ADMIN` |
| `POST` | `/api/doctors/{id}/link-user` | Explicitly associate doctor profile to user account | `STAFF`, `ADMIN` |
| `GET` | `/api/doctors/{id}/schedule` | Doctor schedule & attendance | Authenticated |
| `POST` | `/api/doctors/{id}/schedule` | Set planned doctor schedule | `STAFF`, `ADMIN` |
| `POST` | `/api/doctors/{id}/verify-attendance` | Log verified attendance (`PRESENT`/`ABSENT`) | `STAFF`, `ADMIN`, `DOCTOR` (own profile) |
| `GET` | `/api/medicines` | Search medicine catalogue | Authenticated |
| `POST` | `/api/medicines` | Add medicine to catalogue | `STAFF`, `ADMIN` |
| `POST` | `/api/stock/report` | Submit medicine stock report | Authenticated (server derives role) |
| `GET` | `/api/stock/availability` | Query probabilistic stock belief | Authenticated |
| `POST` | `/api/requests` | Initiate healthcare request | Scoped `PATIENT` / `ASHA` / `STAFF` |
| `GET` | `/api/requests/{id}` | Retrieve healthcare request | Scoped / Clinical |
| `POST` | `/api/recommendations` | Generate loss-minimized recommendations | Scoped / Clinical |
| `GET` | `/api/recommendations/{request_id}` | Retrieve stored recommendations | Scoped / Clinical |
| `POST` | `/api/appointments` | Book appointment with conflict protection | Scoped / Clinical |
| `GET` | `/api/appointments/{id}` | Get appointment details | Scoped / Clinical |
| `PATCH` | `/api/appointments/{id}/cancel` | Cancel appointment and release slot | Scoped / Clinical |
| `POST` | `/api/ivr/webhook` | Carrier webhook (Twilio TwiML / Mock JSON) | `X-API-Key` |
| `POST` | `/api/ivr/call/start` | Initiate IVR voice access call session | `X-API-Key` |
| `POST` | `/api/ivr/call/input` | Process button-phone DTMF keypad input | `X-API-Key` |
| `GET` | `/api/ivr/session/{id}` | Retrieve live session diagnostic state | `X-API-Key` |
| `POST` | `/api/ivr/call/hangup` | Gracefully end an active voice call | `X-API-Key` |
| `POST` | `/api/ivr/lookup` | Spoken medicine availability summary | `X-API-Key` |
| `POST` | `/api/ivr/feedback` | Record caller stock feedback | `X-API-Key` |
| `GET` | `/api/health` | Service health status | Public |
