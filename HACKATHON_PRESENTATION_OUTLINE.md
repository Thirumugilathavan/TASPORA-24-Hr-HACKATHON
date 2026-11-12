# CareBridge — Hackathon Presentation Outline

**Project Name:** CareBridge  
**Tagline:** *No Wasted Trips. Better Access. Continuous Care.*  
**Track:** Healthcare Accessibility, AI Systems & Rural Public Infrastructure  

---

## 1. Problem Statement: The Rural Healthcare Reality
- **The Wasted Trip Dilemma:** Millions of rural residents travel 20–50 km on infrequent rural buses to reach Primary Health Centres (PHCs) or Community Health Centres (CHCs).
- **The Double Failure:**
  1. Arriving at the clinic only to find the doctor is absent or called away on emergency duty.
  2. Seeing a doctor only to find prescribed essential medicines (insulin, antibiotics, anti-hypertensives) are completely out of stock.
- **The Human Cost:** Lost daily wages, delayed treatment, worsening chronic complications, and deep distrust in public healthcare infrastructure.

---

## 2. Target Users
1. **Rural Patients & Families:** Often with limited literacy, non-English speaking, with basic feature phones or shared smartphones.
2. **Frontline ASHA Workers:** Community health activists coordinating maternal care, immunization, and elderly follow-ups across villages.
3. **Primary Health Centre Staff & Doctors:** Medical Officers requiring simple verification tools for physical attendance and stock replenishment.

---

## 3. Our Solution: CareBridge
An AI-powered, bilingual healthcare coordination platform accessible via **both Web (Vite/React)** and **Ordinary Button Phones (Voice/IVR)** that minimizes wasted trips by reasoning over uncertainty.

---

## 4. System Architecture & Pillars

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Access Channels (Dual Modality)                       │
│  [ Web App: Tamil / English ]           [ Keypad Feature Phone: Voice IVR ] │
└──────────────────────┬──────────────────────────────────────┬───────────────┘
                       │                                      │
┌──────────────────────▼──────────────────────────────────────▼───────────────┐
│                          FastAPI Application Gateway                        │
│  • Role-Based Security: PATIENT, ASHA, STAFF, DOCTOR, ADMIN                 │
│  • Privacy Layer: Explicit Consent Default (False), Ownership Scoping       │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                         Core Intelligence Engines                           │
├──────────────────────┬──────────────────────┬───────────────────────────────┤
│ Facility & Doctor    │ Stock Belief Engine  │ Uncertainty-Aware             │
│ Scheduling           │ (Bayesian Ledger)    │ Recommendation Engine         │
│ • Doctor.user_id     │ • Staff (wt 1.0)     │ • Straight-Line Distance      │
│   verification       │ • ASHA (wt 0.8)      │ • Failure Probability         │
│ • PRESENT vs EXPECTED│ • P(available) &     │ • Expected Trip Loss          │
│ • Double-booking lock│   Confidence metric  │   Minimization Formula        │
└──────────────────────┴──────────────────────┴───────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                    Persistence & Migrations (Alembic)                       │
│      17 Unified Tables (Async SQLAlchemy Engine + Partial Unique Indexes)    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Technology Stack
- **Backend:** FastAPI, Python 3.11+, Pydantic v2, SQLAlchemy 2.0 (AsyncIO), Alembic.
- **Frontend:** React 18, TypeScript, Tailwind CSS, Lucide Icons, Vite.
- **Telephony & Voice:** Pluggable Telephony Adapter (Mock CLI Simulator + Twilio Voice TwiML).
- **Security:** Passlib (bcrypt), Python-Jose (JWT), Constant-time secret digest comparison, HMAC-SHA1 webhook signature check.
- **Testing:** Pytest (134 automated unit, security, integration, and E2E tests).

---

## 6. The Breakthrough Innovation: Uncertainty-Aware Trip Routing
Existing appointment apps assume binary availability ($1$ or $0$). CareBridge treats rural healthcare as a **decision under uncertainty**:
- **Probabilistic Beliefs:** Continuous belief state $P(\text{available}) \in [0.0, 1.0]$ and confidence $c \in [0.0, 1.0]$.
- **Expected Trip Loss:**
  $$\text{Expected Loss} = \text{round\_half\_up}(\text{Failure Probability} \times \text{Travel Cost})$$
- If the nearest PHC is 2 km away but has an 80% chance of being out of critical insulin, CareBridge directs the patient to a CHC 5 km away with 95% confirmed stock, saving the patient a wasted trip.

---

## 7. Demonstration Sequence
1. **Tamil-First Web Interface:** Instant toggle between தமிழ் and English.
2. **Patient Registration & Privacy:** Shows explicit consent default (`False`).
3. **Facility & Attendance Integrity:** Doctor marked `PRESENT` only upon actual login.
4. **Stock Confidence:** Medicine stock labeled `LIKELY`, `UNCERTAIN`, or `UNLIKELY`.
5. **Smart Recommendation:** Shows how expected trip loss re-ranks facilities.
6. **Confirmed Booking:** Double-booking prevention via partial database unique indexes.
7. **Voice IVR Keypad Access:** Full DTMF dialling via CLI simulator for button-phone users.

---

## 8. Security & Ethical Boundaries
- **Strictly Non-Diagnostic:** CareBridge coordinates access; it does **not** diagnose or prescribe.
- **Zero-Trust Roles:** Self-registration strictly creates `PATIENT` role.
- **No Spoofed Attendance:** Doctors can only verify their own explicitly linked user profile.
- **PIN Lockout:** 3 incorrect attempts lock the caller out for 15 minutes.

---

## 9. Current Limitations & Roadmap
- **ASHA Village Scoping:** ASHA worker queries will be scoped to revenue village hierarchies in Phase 2.
- **Road Distance:** Upgrading from straight-line Haversine distance to OpenStreetMap road transit graph.
- **Telecom Deployment:** Connecting live carrier SIP trunking for state-wide telephone pilot.

---

## 10. Expected Social Impact
- **70%+ reduction in wasted patient trips.**
- **Improved chronic disease adherence** for rural elderly patients through reliable medicine stock transparency.
- **Equal access for non-smartphone owners** via native button-phone voice navigation.
