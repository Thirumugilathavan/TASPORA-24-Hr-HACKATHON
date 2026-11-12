from datetime import date, time, timedelta
import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.user import User
from app.models.village import Village
from app.schemas.shared import AppointmentStatus, AttendanceStatus, Role, Urgency


@pytest.mark.asyncio
async def test_full_carebridge_e2e_workflow(client: AsyncClient, db_session):
    """End-to-End Integration Test covering the complete NALAM AI rural healthcare lifecycle.

    Step 1: Patient registration
    Step 2: Authentication & JWT login
    Step 3: Village lookup & Patient profile creation
    Step 4: Village directory query
    Step 5: Facility creation & Service discovery
    Step 6: Doctor registration, scheduling & Attendance verification
    Step 7: Medicine catalogue, Stock reporting & Belief state retrieval
    Step 8: Healthcare request creation
    Step 9: Smart loss-minimized recommendation generation
    Step 10: Stored recommendation retrieval
    Step 11: Appointment booking & Conflict protection check
    Step 12: Appointment retrieval & Cancellation (slot release)
    """
    # -------------------------------------------------------------------------
    # STEP 1: Register a new patient account
    # -------------------------------------------------------------------------
    register_payload = {
        "name": "Sunita Devi",
        "phone": "9876500001",
        "password": "SecurePassword123!",
    }
    reg_res = await client.post("/api/auth/register", json=register_payload)
    assert reg_res.status_code == 201, f"Registration failed: {reg_res.text}"
    patient_user_data = reg_res.json()
    assert patient_user_data["phone"] == "9876500001"
    assert patient_user_data["role"] == "PATIENT"
    patient_user_id = patient_user_data["id"]

    # -------------------------------------------------------------------------
    # STEP 2: Authenticate and obtain JWT bearer token
    # -------------------------------------------------------------------------
    login_payload = {
        "phone": "9876500001",
        "password": "SecurePassword123!",
    }
    login_res = await client.post("/api/auth/login", json=login_payload)
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token_data = login_res.json()
    assert "access_token" in token_data
    patient_token = token_data["access_token"]
    patient_headers = {"Authorization": f"Bearer {patient_token}"}

    # Staff/Admin token for administrative actions (doctor/facility creation)
    staff_user = User(
        name="Staff Admin",
        phone="9876500099",
        password_hash="fakehash",
        role=Role.STAFF.value,
    )
    db_session.add(staff_user)
    await db_session.commit()
    await db_session.refresh(staff_user)
    staff_token = create_access_token({"sub": str(staff_user.id), "role": Role.STAFF.value})
    staff_headers = {"Authorization": f"Bearer {staff_token}"}

    # -------------------------------------------------------------------------
    # STEP 3: Seed Village & Create Patient Demographic Profile
    # -------------------------------------------------------------------------
    village = Village(
        name="Rampur Kalan",
        district="Varanasi",
        state="Uttar Pradesh",
        latitude=25.3176,
        longitude=82.9739,
        is_synthetic=False,
    )
    db_session.add(village)
    await db_session.commit()
    await db_session.refresh(village)

    patient_profile_payload = {
        "village_id": str(village.id),
        "date_of_birth": "1990-05-15",
        "preferred_language": "hi",
        "emergency_contact_phone": "9876500002",
        "consent_given": True,
    }
    profile_res = await client.post("/api/patients", json=patient_profile_payload, headers=patient_headers)
    assert profile_res.status_code == 201, f"Patient profile creation failed: {profile_res.text}"
    patient_profile = profile_res.json()
    assert patient_profile["village_id"] == str(village.id)
    assert patient_profile["user_id"] == patient_user_id
    patient_profile_id = patient_profile["id"]

    # -------------------------------------------------------------------------
    # STEP 4: List Villages
    # -------------------------------------------------------------------------
    villages_res = await client.get("/api/villages", headers=patient_headers)
    assert villages_res.status_code == 200
    villages_list = villages_res.json()["items"]
    assert any(v["name"] == "Rampur Kalan" for v in villages_list)

    # -------------------------------------------------------------------------
    # STEP 5: Create Healthcare Facility & Query Facilities
    # -------------------------------------------------------------------------
    facility_payload = {
        "name": "Rampur Community Health Centre",
        "facility_type": "CHC",
        "address": "Main Road, Rampur Sector 2",
        "village_id": str(village.id),
        "latitude": 25.3250,
        "longitude": 82.9800,
        "services": ["General Medicine", "Pharmacy Refill"],
    }
    fac_res = await client.post("/api/facilities", json=facility_payload, headers=staff_headers)
    assert fac_res.status_code == 201, f"Facility creation failed: {fac_res.text}"
    facility_data = fac_res.json()
    facility_id = facility_data["id"]

    # Query facilities offering General Medicine near the village
    query_fac_res = await client.get(
        f"/api/facilities?village_id={village.id}&service=General Medicine",
        headers=patient_headers,
    )
    assert query_fac_res.status_code == 200
    fac_results = query_fac_res.json()["items"]
    assert len(fac_results) >= 1
    assert any(f["id"] == facility_id for f in fac_results)

    # -------------------------------------------------------------------------
    # STEP 6: Register Doctor, Schedule & Verify Attendance
    # -------------------------------------------------------------------------
    doctor_payload = {
        "facility_id": facility_id,
        "name": "Dr. Ramesh Verma",
        "specialization": "General Physician",
        "qualification": "MBBS, MD",
        "contact_phone": "9876500003",
    }
    doc_res = await client.post("/api/doctors", json=doctor_payload, headers=staff_headers)
    assert doc_res.status_code == 201, f"Doctor creation failed: {doc_res.text}"
    doctor_data = doc_res.json()
    doctor_id = doctor_data["id"]

    today = date.today()
    schedule_payload = {
        "doctor_id": doctor_id,
        "facility_id": facility_id,
        "schedule_date": today.isoformat(),
        "start_time": "09:00:00",
        "end_time": "14:00:00",
        "attendance_status": "EXPECTED",
        "notes": "Morning OPD shift",
    }
    sched_res = await client.post(f"/api/doctors/{doctor_id}/schedule", json=schedule_payload, headers=staff_headers)
    assert sched_res.status_code == 201, f"Doctor schedule creation failed: {sched_res.text}"

    # Verify doctor attendance is logged
    doc_sched_res = await client.get(
        f"/api/doctors/{doctor_id}/schedule?date={today.isoformat()}",
        headers=patient_headers,
    )
    assert doc_sched_res.status_code == 200
    sched_info = doc_sched_res.json()
    assert sched_info["attendance_status"] == AttendanceStatus.EXPECTED.value

    # -------------------------------------------------------------------------
    # STEP 7: Catalogue Medicine, Submit Stock Report & Check Stock Availability
    # -------------------------------------------------------------------------
    medicine_payload = {
        "name": "Paracetamol 500mg",
        "generic_name": "Paracetamol",
        "strength": "500mg",
        "dosage_form": "Tablet",
    }
    med_res = await client.post("/api/medicines", json=medicine_payload, headers=staff_headers)
    assert med_res.status_code == 201, f"Medicine creation failed: {med_res.text}"
    med_data = med_res.json()
    medicine_id = med_data["id"]

    # Submit verified stock report from staff
    stock_payload = {
        "facility_id": facility_id,
        "medicine_id": medicine_id,
        "availability_status": "IN_STOCK",
    }
    stock_res = await client.post("/api/stock/report", json=stock_payload, headers=staff_headers)
    assert stock_res.status_code == 201, f"Stock report submission failed: {stock_res.text}"

    # Check belief state availability
    stock_check_res = await client.get(
        f"/api/stock/availability?medicine_id={medicine_id}&facility_ids={facility_id}",
        headers=patient_headers,
    )
    assert stock_check_res.status_code == 200
    avail_info = stock_check_res.json()
    assert len(avail_info["items"]) >= 1
    first_item = avail_info["items"][0]
    assert first_item["label"] in ("LIKELY", "UNCERTAIN", "UNLIKELY")
    assert first_item["confidence"] > 0.0

    # -------------------------------------------------------------------------
    # STEP 8: Create Patient Healthcare Request
    # -------------------------------------------------------------------------
    request_payload = {
        "patient_id": patient_user_id,
        "request_type": "CONSULTATION",
        "description": "Severe fever and body pain for two days",
        "urgency": "PRIORITY",
    }
    req_res = await client.post("/api/requests", json=request_payload, headers=patient_headers)
    assert req_res.status_code == 201, f"Healthcare request creation failed: {req_res.text}"
    request_data = req_res.json()
    request_id = request_data["id"]

    # Verify request details via GET
    get_req_res = await client.get(f"/api/requests/{request_id}", headers=patient_headers)
    assert get_req_res.status_code == 200
    assert get_req_res.json()["urgency"] == Urgency.PRIORITY.value

    # -------------------------------------------------------------------------
    # STEP 9: Generate Loss-Minimized Smart Recommendations
    # -------------------------------------------------------------------------
    rec_payload = {"request_id": request_id}
    rec_res = await client.post("/api/recommendations", json=rec_payload, headers=patient_headers)
    assert rec_res.status_code == 200, f"Recommendation generation failed: {rec_res.text}"
    rec_data = rec_res.json()
    items = rec_data["items"]
    assert len(items) > 0

    # Verify ascending expected_loss ordering
    for i in range(len(items) - 1):
        assert items[i]["expected_loss"] <= items[i + 1]["expected_loss"]
        assert items[i]["rank"] == i + 1

    recommended_facility_id = items[0]["facility_id"]

    # -------------------------------------------------------------------------
    # STEP 10: Retrieve Stored Recommendations
    # -------------------------------------------------------------------------
    stored_rec_res = await client.get(f"/api/recommendations/{request_id}", headers=patient_headers)
    assert stored_rec_res.status_code == 200
    assert len(stored_rec_res.json()["items"]) == len(items)

    # -------------------------------------------------------------------------
    # STEP 11: Book Appointment & Verify Slot Conflict Prevention
    # -------------------------------------------------------------------------
    tomorrow = today + timedelta(days=1)
    appointment_payload = {
        "patient_id": patient_user_id,
        "facility_id": recommended_facility_id,
        "doctor_id": doctor_id,
        "request_id": request_id,
        "appointment_date": tomorrow.isoformat(),
        "appointment_time": "10:00:00",
    }
    appt_res = await client.post("/api/appointments", json=appointment_payload, headers=patient_headers)
    assert appt_res.status_code == 201, f"Appointment booking failed: {appt_res.text}"
    appt_data = appt_res.json()
    appointment_id = appt_data["id"]
    assert appt_data["status"] == AppointmentStatus.BOOKED.value

    # Test conflict prevention: Attempt to double-book the same slot
    conflict_payload = {
        "patient_id": str(staff_user.id),  # Different patient
        "facility_id": recommended_facility_id,
        "doctor_id": doctor_id,
        "appointment_date": tomorrow.isoformat(),
        "appointment_time": "10:00:00",
    }
    conflict_res = await client.post("/api/appointments", json=conflict_payload, headers=staff_headers)
    assert conflict_res.status_code == 409, "Double booking should return HTTP 409 Conflict"

    # -------------------------------------------------------------------------
    # STEP 12: Retrieve Appointment & Cancel Appointment (Slot Release)
    # -------------------------------------------------------------------------
    get_appt_res = await client.get(f"/api/appointments/{appointment_id}", headers=patient_headers)
    assert get_appt_res.status_code == 200
    assert get_appt_res.json()["status"] == AppointmentStatus.BOOKED.value

    # Cancel the appointment
    cancel_res = await client.patch(f"/api/appointments/{appointment_id}/cancel", headers=patient_headers)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == AppointmentStatus.CANCELLED.value

    # Verify slot is released: Re-booking the slot now succeeds
    rebook_res = await client.post("/api/appointments", json=conflict_payload, headers=staff_headers)
    assert rebook_res.status_code == 201, "Re-booking after cancellation should succeed"
