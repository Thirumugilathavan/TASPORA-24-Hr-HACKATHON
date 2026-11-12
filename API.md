# CareBridge API contract v1

Workflow: register -> request -> check availability -> recommend -> book -> fulfil.
Adding a field is safe. Renaming or removing one needs everyone's agreement.
FastAPI's `/docs` page is the live source of truth. All data is simulated.

## Conventions
- Base path `/api`, JSON only, UUID string IDs, UTC ISO-8601 times
- `p_available`, `confidence`, `failure_probability`: numbers 0 to 1
- Money in whole rupees, distance in km (Haversine straight-line distance)
- Auth: `Authorization: Bearer <jwt>`. IVR uses header `X-API-Key` instead.
- Lists: `{"items": [...], "total": n}`
- Errors: `{"error": {"code": "NOT_FOUND", "message": "..."}}` with HTTP 400/401/403/404/409/422
- `source_type` for stock reports is set by the server from the caller's role, never by the client.

## Enums (uppercase strings)
- role: PATIENT, ASHA, DOCTOR, STAFF, ADMIN
- facility_type: PHC, CHC, HOSPITAL, PHARMACY
- availability_status: IN_STOCK, LOW, OUT, UNKNOWN
- source_type: STAFF, ASHA, PATIENT
- request_type: CONSULTATION, REFILL, CHECKUP, DIAGNOSTIC
- urgency: NORMAL, PRIORITY, URGENT
- appointment_status: BOOKED, CONFIRMED, CANCELLED, COMPLETED
- attendance_status: EXPECTED, PRESENT, ABSENT, UNKNOWN (EXPECTED = planned shift, not confirmed)
- availability_label: LIKELY (p >= 0.65), UNCERTAIN (0.35 < p < 0.65), UNLIKELY (p <= 0.35)

---

## 1. Auth and Patients (Person 1)
| Method | Path | Body or query | Notes |
|---|---|---|---|
| POST | /api/auth/register | name, phone, password, role | Enforces PATIENT role for self-registration |
| POST | /api/auth/login | phone, password | -> access_token, role, user_id |
| GET | /api/villages | None | -> items: id, name, district, latitude, longitude, is_synthetic |
| POST | /api/patients | village_id, date_of_birth, preferred_language, consent_given, emergency_contact_phone | Creates patient profile bound 1-to-1 with caller |
| GET | /api/patients/{id} | id (Patient UUID or User UUID) | Demographic detail with nested village |

### Patient & Village Security Rules
1. **Consent Behavior:** `consent_given` defaults to `false`. Consent is never silently assumed. Clinical roles (`ASHA`, `DOCTOR`, `STAFF`) require explicit patient consent (`consent_given=true`) to view complete demographic records; without consent, access returns `HTTP 403 CONSENT_REQUIRED`.
2. **Self Access Guarantee:** A `PATIENT` role user can always access their own profile regardless of consent state (`HTTP 200`). Cross-patient access returns `HTTP 403 ACCESS_DENIED`.
3. **Language Support:** First-class support for Tamil (`ta`, `tamil`) and English (`en`, `english`), along with `hi`, `te`, `bn`. Does not force Hindi as the default for the Tamil Nadu platform context.
4. **Emergency Contact Privacy:** `emergency_contact_phone` is strictly optional and validated as a 10-digit Indian mobile. Exposed only to the patient themselves, system admins, or consented clinical staff.
5. **Synthetic Village Disclosure:** Simulated test villages explicitly return `is_synthetic: true` to prevent mistaking demonstration coordinates for verified healthcare geography.
6. **Deletion Safety:** Removing a village never cascade-deletes patient records (RESTRICT foreign key policy).

---

## 2. Facilities and Doctors (Person 2)
| Method | Path | Notes |
|---|---|---|
| GET | /api/facilities | query: village_id, facility_type, service |
| GET | /api/facilities/{id} | includes services[] and doctors[] |
| POST | /api/facilities | Restricted to STAFF and ADMIN |
| GET | /api/doctors | query: facility_id |
| GET | /api/doctors/{id}/schedule | query: date. Returns attendance_status, last_verified_at. Unscheduled dates return UNKNOWN |
| POST | /api/doctors | body: facility_id, name, specialization, qualification, contact_phone, user_id (optional). Restricted to STAFF and ADMIN |
| POST | /api/doctors/{id}/link-user | body: user_id. Restricted to STAFF and ADMIN. Links doctor profile to user account. Rejects duplicates (409) and non-DOCTOR roles (400) |
| POST | /api/doctors/{id}/schedule | Restricted to STAFF and ADMIN |
| POST | /api/doctors/{id}/verify-attendance | query: date, attendance_status. Restricted to STAFF, ADMIN, DOCTOR |

### Doctor Attendance & Security Rules
1. **Explicit Doctor-to-User Ownership:** The `Doctor` entity includes an explicit nullable `user_id` foreign key referencing `users.id` with a 1-to-1 uniqueness constraint (`uq_doctors_user_id`).
2. **Strict Verification Enforcement:** A `DOCTOR` role caller may only verify attendance for their own explicitly linked doctor profile (`Doctor.user_id == current_user.id`). Cross-doctor verification attempts return `HTTP 403 FORBIDDEN`. `PATIENT` and `ASHA` roles cannot verify attendance (`HTTP 403 FORBIDDEN`).
3. **Fail-Closed Authorization (No Name/Phone Fallback):** Unlinked legacy doctor profiles (`user_id is None`) cannot self-verify attendance and return `HTTP 403 FORBIDDEN`. Heuristic fallback to name or phone matching is strictly prohibited to eliminate impersonation risks.
4. **Administrative Association Process:** Associating a doctor profile with a user account requires an explicit administrative action by `STAFF` or `ADMIN` via `POST /api/doctors/{id}/link-user` or at doctor creation time via `POST /api/doctors`.
5. **Database Migration & Data Preservation:** Migration `c14696c8596b` adds `user_id` as a nullable column referencing `users.id` (`ON DELETE SET NULL`), preserving all legacy doctor profiles and duty schedules intact without data loss.
6. **No Phantom Attendance:** Shifts without recorded schedule return `UNKNOWN` attendance rather than inferred presence. `EXPECTED` denotes planned duty; `PRESENT` / `ABSENT` denotes verified status.
7. **Geodesic Distance Limitations:** All calculated distances represent Haversine straight-line geodesic distance in km, serving as an idealized lower bound for actual rural transit.

---

## 3. Medicines and Stock Intelligence (Person 3)
| Method | Path | Notes |
|---|---|---|
| GET | /api/medicines | query: q (name or generic_name search) |
| POST | /api/medicines | Restricted to STAFF and ADMIN |
| POST | /api/stock/report | body: facility_id, medicine_id, availability_status |
| GET | /api/stock/availability | query: medicine_id, facility_ids (comma list) |

Report response: `{"report_id", "verification_status": "PENDING", "updated": {"p_available", "confidence"}}`
Availability item: `{"facility_id", "p_available", "confidence", "label", "evidence_count", "last_report_at"}`

### Stock Algorithm & Evidence Rules
1. **Source Credibility & Patient Protection:** `source_type` is derived server-side from the authenticated user. Patient reports carry $0.0$ weight in probability calculation and never modify availability probability.
2. **Anti-Inflation Dampening:** Repeated reports from the same reporter suffer exponential decay ($0.5^k$) and are capped at $1.5 \times W_{\text{source}}$.
3. **UNKNOWN Neutrality:** `UNKNOWN` reports penalize confidence without asserting stockout (`OUT`).
4. **Conflict Penalization:** Conflicting reports between reporters increase variance and decrease confidence score.
5. **Categorical Triage Labels:**
   - **`LIKELY`:** $p_{\text{available}} \ge 0.65$
   - **`UNCERTAIN`:** $0.35 < p_{\text{available}} < 0.65$ (or confidence $= 0.0$ due to stale/missing evidence)
   - **`UNLIKELY`:** $p_{\text{available}} \le 0.35$
6. **Heuristic Disclosure:** Stock availability probabilities and confidence scores are heuristic risk-mitigation engineering models; they are not claimed to be clinically or statistically calibrated.

---

## 4. Requests, Recommendations, Appointments (Person 4)
| Method | Path | Notes |
|---|---|---|
| POST | /api/requests | patient_id, request_type, medicine_id, description, urgency -> id, status PENDING |
| GET | /api/requests/{id} | Patient-isolated |
| POST | /api/recommendations | body: request_id. Generates and stores ranked facilities |
| GET | /api/recommendations/{request_id} | stored result |
| POST | /api/appointments | patient_id, facility_id, doctor_id (nullable), request_id, appointment_date, appointment_time. 409 if slot taken |
| GET | /api/appointments/{id} | Patient-isolated |
| PATCH | /api/appointments/{id}/cancel | Releases slot for concurrency |

Recommendation item: `{"rank", "facility_id", "facility_name", "suitability_score", "medicine_confidence", "travel_distance_km", "travel_cost", "failure_probability", "expected_loss", "doctor_status", "explanation"}`

### Expected Loss Formula
$$\text{expected\_loss} = \text{failure\_probability} \times \text{travel\_cost}$$
Items are sorted in ascending order of `expected_loss` to direct rural patients to facilities that minimize travel burden and avoid futile journeys.

---

## 5. Medical Safety
No diagnosis and no dose advice in any response, voice prompt, or recommendation. CareBridge is a healthcare accessibility and logistics coordination platform, not a diagnostic engine.
