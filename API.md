# CareBridge API contract v1

Workflow: register -> request -> check availability -> recommend -> book -> fulfil.
Adding a field is safe. Renaming or removing one needs everyone's agreement.
FastAPI's `/docs` page is the live source of truth. All data is simulated.

## Conventions
- Base path `/api`, JSON only, UUID string IDs, UTC ISO-8601 times
- `p_available`, `confidence`, `failure_probability`: numbers 0 to 1
- Money in whole rupees, distance in km
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
- attendance_status: EXPECTED, PRESENT, ABSENT, UNKNOWN (EXPECTED = planned, not confirmed)
- availability_label: LIKELY (p >= 0.65), UNCERTAIN, UNLIKELY (p <= 0.35)

## 1. Auth and patients (Person 1)
| Method | Path | Body or query |
|---|---|---|
| POST | /api/auth/register | name, phone, password, role |
| POST | /api/auth/login | phone, password -> access_token, role, user_id |
| GET | /api/villages | -> items: id, name, district, latitude, longitude |
| POST | /api/patients | village_id, date_of_birth, preferred_language |
| GET | /api/patients/{id} | |

## 2. Facilities and doctors (Person 2)
| Method | Path | Notes |
|---|---|---|
| GET | /api/facilities | query: village_id, facility_type, service |
| GET | /api/facilities/{id} | includes services[] and doctors[] |
| GET | /api/doctors | query: facility_id |
| GET | /api/doctors/{id}/schedule | query: date. Returns attendance_status, last_verified_at |

## 3. Medicines and stock (Person 3)
| Method | Path | Notes |
|---|---|---|
| GET | /api/medicines | query: q |
| POST | /api/stock/report | body: facility_id, medicine_id, availability_status |
| GET | /api/stock/availability | query: medicine_id, facility_ids (comma list) |

Report response: `{"report_id", "verification_status": "PENDING", "updated": {"p_available", "confidence"}}`

Availability item: `{"facility_id", "p_available", "confidence", "label", "evidence_count", "last_report_at"}`

Feedback never changes stock. Only STAFF and ASHA reports carry strong weight.

## 4. Requests, recommendations, appointments (Person 4)
| Method | Path | Notes |
|---|---|---|
| POST | /api/requests | patient_id, request_type, medicine_id, description, urgency -> id, status PENDING |
| GET | /api/requests/{id} | |
| POST | /api/recommendations | body: request_id. Generates and stores |
| GET | /api/recommendations/{request_id} | stored result |
| POST | /api/appointments | patient_id, facility_id, doctor_id (nullable), request_id, appointment_date, appointment_time. 409 if slot taken |
| GET | /api/appointments/{id} | |
| PATCH | /api/appointments/{id}/cancel | |

Recommendation item: `{"rank", "facility_id", "facility_name", "suitability_score", "medicine_confidence", "travel_distance_km", "travel_cost", "failure_probability", "expected_loss", "doctor_status", "explanation"}`

`expected_loss = failure_probability x travel_cost`. Items are sorted ascending by expected_loss.

## 5. Feedback and delivery (Person 6)
| Method | Path | Notes |
|---|---|---|
| POST | /api/feedback | patient_id, facility_id, medicine_id, request_id, rating, comments |
| POST | /api/delivery | patient_id, facility_id, medicine_id, quantity, delivery_method, delivery_address |
| GET | /api/delivery/{id} | status: REQUESTED, APPROVED, DISPATCHED, DELIVERED, CANCELLED |

Delivery is simulated and must reference a valid request or prescription flag.

## 6. Phase 2 (Person 5)
/api/schemes, /api/camps, /api/camps/{id}/register, /api/referrals, /api/notifications

## 7. Channel endpoints (IVR and dashboard)
| Method | Path | Notes |
|---|---|---|
| POST | /api/ivr/lookup | phone, medicine_code -> speak_text, facility_id, p_available, options[] |
| POST | /api/ivr/feedback | phone, facility_id, medicine_code, got_it |
| GET | /api/dashboard/summary | -> grid[], alerts[], refills_due[], recent_reports[] |

The patient is identified by phone number. No login on a basic phone.

## 8. Python-level contracts between modules
Each owner ships a stub returning fixed values in hour 1.
- `get_availability(facility_id, medicine_id) -> {p, conf, label}` (Person 3, used by Person 4)
- `list_candidate_facilities(village_id, service) -> [facility]` (Person 2, used by Person 4)
- `get_doctor_status(facility_id, date) -> attendance_status` (Person 2, used by Person 4)
- `distance_km(village_id, facility_id) -> int` (Person 2, used by Person 4)

## 9. Medical safety
No diagnosis and no dose advice in any response or voice prompt.
