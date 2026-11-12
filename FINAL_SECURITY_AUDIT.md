# NALAM AI — Final Security Audit & Privacy Review

**Audit Date:** 2026-11-12  
**Assessor:** Lead Security & Integration Engineer  
**Scope:** NALAM AI FastAPI Backend, React Web Frontend, IVR Voice Access Engine, Database Schemas & Migrations.  
**Repository:** `https://github.com/Thirumugilathavan/TASPORA-24-Hr-HACKATHON`  
**Target Branch:** `integration/carebridge-backend`  

---

## 1. Executive Summary

A comprehensive security review was conducted across the unified NALAM AI platform. 
The system enforces strict zero-trust boundaries between patient self-service and healthcare operational functions:
- **Public Registration:** Strictly restricted to creating `PATIENT` role accounts.
- **Patient Privacy:** Consent defaults to `false`. Clinical staff cannot access demographic data without explicit consent (`HTTP 403 CONSENT_REQUIRED`).
- **Doctor Attendance Integrity:** Doctor attendance self-verification is strictly locked to explicitly linked user accounts (`doc.user_id == current_user.id`).
- **Voice Access Security:** Predictable phone-derived PINs are strictly disabled in production. Brute-force protection enforces a 15-minute lockout after 3 consecutive failures. HMAC-SHA1 signature verification is implemented for Twilio webhooks.

---

## 2. Security Findings & Remediations

### Finding SEC-01: Twilio Webhook Missing Signature Verification
- **Severity:** High
- **Affected Component:** `app/api/v1/ivr.py` / `app/integrations/telephony/twilio_provider.py`
- **Description:** Previously, telephony webhooks relied exclusively on `X-API-Key`. While appropriate for carrier proxies, direct live Twilio webhooks transmit request signatures via `X-Twilio-Signature` rather than custom secret headers. Exposing a webhook publicly without signature validation risks request forgery or unauthorized DTMF injection.
- **Fix Implemented:** Implemented standard HMAC-SHA1 signature validation method `TwilioTelephonyProvider.validate_signature(url, params, signature, auth_token)` using constant-time digest comparison (`hmac.compare_digest`). Added `TWILIO_AUTH_TOKEN` to `Settings`.
- **Test Evidence:** `tests/test_ivr_security.py::test_ivr_twilio_signature_verification` PASSED. Verified that forged signatures, altered payload parameters, and blank tokens are rejected.
- **Remaining Risk:** In development/demo mode, `X-API-Key` remains available for the local CLI simulator and testing tools.
- **Deployment Blocker:** **No longer blocks deployment** if `TWILIO_AUTH_TOKEN` is configured on live gateways.

---

### Finding SEC-02: Predictable Phone-Derived PINs in Voice Access
- **Severity:** High
- **Affected Component:** `app/services/ivr_auth_service.py`
- **Description:** An early convenience feature permitted callers to authenticate using the last 4 digits of their phone number. If enabled in production, an attacker could easily spoof or dial a victim's phone number and access appointment records and healthcare requests.
- **Fix Implemented:** Strict production boundary enforced:
  ```python
  is_production = getattr(settings, "ENVIRONMENT", "").lower() == "production"
  allow_demo_pin = getattr(settings, "IVR_ALLOW_DEMO_PHONE_PIN", False) and not is_production
  ```
  In production, authentication strictly verifies securely provisioned bcrypt password hashes (`verify_password(clean_pin, user.password_hash)`).
- **Test Evidence:** `tests/test_ivr_security.py::test_ivr_production_prevents_predictable_phone_derived_pin` PASSED. Confirmed that in `ENVIRONMENT=production`, phone-derived PINs fail immediately with `INVALID_PIN`.
- **Remaining Risk:** None. Production default enforces password hashes.
- **Deployment Blocker:** **Resolved.**

---

### Finding SEC-03: Brute-Force PIN Enumeration on IVR Endpoints
- **Severity:** Medium
- **Affected Component:** `app/services/ivr_auth_service.py` / `ivr_auth_attempts` table
- **Description:** 4-digit PINs have a limited keyspace (10,000 combinations). Without rate limiting, an automated caller could iterate through PIN combinations.
- **Fix Implemented:** Dedicated tracking table `ivr_auth_attempts` tracks consecutive failed attempts per normalized phone number. Upon reaching `IVR_MAX_AUTH_ATTEMPTS` (3 failures), the account is locked for `IVR_AUTH_LOCKOUT_MINUTES` (15 minutes).
- **Test Evidence:** `tests/test_ivr_security.py::test_ivr_brute_force_pin_lockout_via_api` PASSED.
- **Remaining Risk:** Negligible. 3 attempts against a 10,000 keyspace yields a $0.03\%$ probability of random success.
- **Deployment Blocker:** **Resolved.**

---

### Finding SEC-04: Unauthorized Doctor Attendance Spoofing
- **Severity:** High
- **Affected Component:** `app/api/v1/doctors.py` (`POST /api/doctors/{id}/verify-attendance`)
- **Description:** Earlier iterations permitted any authenticated user with `DOCTOR` role to verify attendance for any doctor profile across any facility.
- **Fix Implemented:** 
  1. Added explicit `Doctor.user_id` foreign key referencing `users.id` with a 1-to-1 unique constraint (`uq_doctors_user_id`).
  2. Restricted `DOCTOR` role self-verification to the doctor's own linked profile (`doc.user_id == current_user.id`).
  3. Unlinked doctor profiles fail closed with `HTTP 403 FORBIDDEN` until linked by `STAFF` or `ADMIN`.
- **Test Evidence:** `tests/test_doctors.py` (21 tests passed, including `test_doctor_cannot_verify_another_doctor_attendance`, `test_unlinked_doctor_cannot_self_verify`, and `test_staff_links_doctor_to_user_and_then_doctor_verifies`).
- **Remaining Risk:** None. Strict ownership enforced.
- **Deployment Blocker:** **Resolved.**

---

### Finding SEC-05: Patient Clinical Consent Default & Boundary Enforcement
- **Severity:** High
- **Affected Component:** `app/models/patient.py` / `app/services/patient_service.py`
- **Description:** Healthcare regulations and rural medical privacy require patient consent to be opt-in, never assumed.
- **Fix Implemented:**
  - `consent_given` defaults strictly to `False` in SQLAlchemy models and Pydantic schemas.
  - Frontline staff (`ASHA`, `DOCTOR`, `STAFF`) attempting to retrieve unconsented patient demographic details are rejected with `HTTP 403 CONSENT_REQUIRED`.
  - Patients can only retrieve and modify their own records (`check_patient_ownership`).
- **Test Evidence:** `tests/test_patient_village.py::test_clinical_roles_cannot_access_unconsented_patient` PASSED.
- **Remaining Risk:** None.
- **Deployment Blocker:** **Resolved.**

---

### Finding SEC-06: ASHA Cross-Village Access Boundary (Known Limitation)
- **Severity:** Medium
- **Affected Component:** `app/services/patient_service.py`
- **Description:** Currently, an authenticated ASHA worker can look up any patient who has given consent, regardless of the patient's home village. In real rural administration, ASHAs are assigned to specific sub-centres or revenue villages.
- **Investigation & Assessment:** Introducing village-level filtering during the final hackathon integration without an administrative "ASHA Village Assignment" table risks breaking valid multi-village coordination and hackathon demo scenarios.
- **Remediation Plan:** Documented as a known limitation. A future administrative module will map `asha_village_assignments (user_id, village_id)` to restrict ASHA queries strictly to assigned villages.
- **Remaining Risk:** Low for evaluation/hackathon. ASHA access is still gated by valid JWT authentication and explicit patient consent.
- **Deployment Blocker:** **Permissible for Hackathon Demo; requires organizational mapping table before state-wide health system rollout.**

---

### Finding SEC-07: Clinical Decision Boundary & Medical Safety
- **Severity:** Medium
- **Affected Component:** Platform Documentation, UI Labels, and Algorithm Specifications
- **Description:** Risk of patients or evaluators mistaking routing recommendations for medical diagnosis, triage, or prescription substitution.
- **Fix Implemented:**
  - Explicit disclaimers added to `README.md`, `STOCK_ALGORITHM.md`, and frontend banners: NALAM AI is an access and coordination platform, **NOT** an AI diagnostic or prescription tool.
  - Stock probabilities are explicitly labeled with confidence metrics (`LIKELY`, `UNCERTAIN`, `UNLIKELY`).
  - Distance metrics explicitly state straight-line Haversine computation, not road transit time.
- **Remaining Risk:** None. Strict non-diagnostic posture maintained.
- **Deployment Blocker:** **Resolved.**

---

## 3. Public Deployment Readiness Matrix

| Area | Status | Hackathon Demo | Production Deployment |
|---|---|---|---|
| JWT Authentication | Robust | Approved | Approved |
| Role-Based Authorization | Robust | Approved | Approved |
| Patient Consent Default (False) | Robust | Approved | Approved |
| Doctor Ownership Linkage | Robust | Approved | Approved |
| Stock Ledger Role-Weighting | Robust | Approved | Approved |
| IVR Brute-Force Lockout | Robust | Approved | Approved |
| Twilio Webhook Signature Check | Implemented | Approved (Local Simulator) | Approved (with Live Secret) |
| ASHA Village Assignment Scoping | Pending Hierarchy Table | Approved (Demo Mode) | **Requires Village Assignment Module** |
| Real Telecom Cellular Line | Blocked (Requires SIP) | Approved (CLI Simulator) | **Requires Twilio Paid Account** |

**Recommendation:** NALAM AI is **fully approved for live hackathon demonstration**. For production deployment, implement ASHA village-assignment scoping and configure a funded Twilio account.
