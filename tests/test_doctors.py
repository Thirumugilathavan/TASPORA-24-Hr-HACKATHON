from datetime import date
import uuid
import pytest
from httpx import AsyncClient
from app.core.security import create_access_token
from app.models.user import User

from app.core.security import create_access_token
from app.models.user import User


@pytest.mark.asyncio
async def test_get_doctors_list(client: AsyncClient, seed_data: dict):
    """Verify listing doctors with standard format."""
    response = await client.get("/api/doctors")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] == 2


@pytest.mark.asyncio
async def test_filter_doctors_by_facility(client: AsyncClient, seed_data: dict):
    """Verify filtering doctors by facility_id."""
    fac_1 = seed_data["facilities"][0]
    response = await client.get(f"/api/doctors?facility_id={fac_1.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Dr. Anita Sharma"


@pytest.mark.asyncio
async def test_doctor_schedule_expected_vs_present(client: AsyncClient, seed_data: dict):
    """Verify doctor schedule retrieval and attendance distinction.

    EXPECTED means planned attendance, not confirmed.
    PRESENT means confirmed attendance.
    """
    doc_1 = seed_data["doctors"][0]
    doc_2 = seed_data["doctors"][1]
    today = date.today().isoformat()

    # Doctor 1: Scheduled with EXPECTED attendance
    resp_1 = await client.get(f"/api/doctors/{doc_1.id}/schedule?date={today}")
    assert resp_1.status_code == 200
    data_1 = resp_1.json()
    assert data_1["attendance_status"] == "EXPECTED"
    assert data_1["doctor_name"] == "Dr. Anita Sharma"
    assert data_1["schedule"] is not None
    assert data_1["schedule"]["attendance_status"] == "EXPECTED"

    # Doctor 2: Verified PRESENT
    resp_2 = await client.get(f"/api/doctors/{doc_2.id}/schedule?date={today}")
    assert resp_2.status_code == 200
    data_2 = resp_2.json()
    assert data_2["attendance_status"] == "PRESENT"
    assert data_2["doctor_name"] == "Dr. Rajesh Kumar"
    assert data_2["schedule"] is not None
    assert data_2["schedule"]["attendance_status"] == "PRESENT"
    assert data_2["last_verified_at"] is not None


@pytest.mark.asyncio
async def test_doctor_schedule_unscheduled_date_returns_unknown(client: AsyncClient, seed_data: dict):
    """Verify unscheduled date returns UNKNOWN rather than phantom attendance."""
    doc_1 = seed_data["doctors"][0]
    unscheduled = "2026-12-25"
    response = await client.get(f"/api/doctors/{doc_1.id}/schedule?date={unscheduled}")
    assert response.status_code == 200
    data = response.json()
    assert data["attendance_status"] == "UNKNOWN"
    assert data["schedule"] is None
    assert data["last_verified_at"] is None


@pytest.mark.asyncio
async def test_doctor_schedule_not_found(client: AsyncClient, seed_data: dict):
    """Verify 404 for invalid doctor ID."""
    random_id = uuid.uuid4()
    response = await client.get(f"/api/doctors/{random_id}/schedule")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_verify_attendance_updates_status(client: AsyncClient, seed_data: dict):
    """Verify attendance verification logs last_verified_at."""
    doc_1 = seed_data["doctors"][0]
    today = date.today().isoformat()
    staff_headers = seed_data["headers"]["staff"]

    verify_resp = await client.post(
        f"/api/doctors/{doc_1.id}/verify-attendance?date={today}&attendance_status=PRESENT",
        headers=staff_headers,
    )
    assert verify_resp.status_code == 200
    data = verify_resp.json()
    assert data["attendance_status"] == "PRESENT"
    assert data["last_verified_at"] is not None

    # Check via schedule endpoint
    check_resp = await client.get(f"/api/doctors/{doc_1.id}/schedule?date={today}")
    assert check_resp.status_code == 200
    check_data = check_resp.json()
    assert check_data["attendance_status"] == "PRESENT"
    assert check_data["last_verified_at"] is not None


@pytest.mark.asyncio
async def test_verify_attendance_patient_forbidden(client: AsyncClient, seed_data: dict):
    """Verify patients cannot verify doctor attendance (HTTP 403 Forbidden)."""
    doc_1 = seed_data["doctors"][0]
    today = date.today().isoformat()
    patient_headers = seed_data["headers"]["patient"]

    response = await client.post(
        f"/api/doctors/{doc_1.id}/verify-attendance?date={today}&attendance_status=PRESENT",
        headers=patient_headers,
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_create_doctor_patient_forbidden(client: AsyncClient, seed_data: dict):
    """Verify patients cannot register doctors (HTTP 403 Forbidden)."""
    patient_headers = seed_data["headers"]["patient"]
    fac_1 = seed_data["facilities"][0]
    payload = {
        "facility_id": str(fac_1.id),
        "name": "Dr. Unauthorized",
        "specialization": "Cardiology",
    }
    response = await client.post("/api/doctors", json=payload, headers=patient_headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_create_doctor_missing_facility_returns_404(client: AsyncClient, seed_data: dict):
    """Verify 404 when registering doctor to non-existent facility."""
    staff_headers = seed_data["headers"]["staff"]
    payload = {
        "facility_id": str(uuid.uuid4()),
        "name": "Dr. Missing Fac",
        "specialization": "General",
    }
    response = await client.post("/api/doctors", json=payload, headers=staff_headers)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_create_doctor_schedule_invalid_time_range(client: AsyncClient, seed_data: dict):
    """Verify schedule creation with invalid time range (start >= end) fails with 422."""
    staff_headers = seed_data["headers"]["staff"]
    doc_1 = seed_data["doctors"][0]
    payload = {
        "doctor_id": str(doc_1.id),
        "facility_id": str(doc_1.facility_id),
        "schedule_date": "2026-11-20",
        "start_time": "14:00:00",
        "end_time": "10:00:00",  # Invalid: start_time >= end_time
    }
    response = await client.post(f"/api/doctors/{doc_1.id}/schedule", json=payload, headers=staff_headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_doctor_cannot_verify_another_doctor_attendance(client: AsyncClient, db_session, seed_data: dict):
    """SECURITY TEST: A DOCTOR role caller cannot verify attendance for another doctor."""
    doc_1 = seed_data["doctors"][0]  # Dr. Anita Sharma, phone 9876543220
    doc_2 = seed_data["doctors"][1]  # Dr. Rajesh Kumar, phone 9876543221

    # Create user for Doctor 1
    doc_user_1 = User(
        name="Dr. Anita Sharma",
        phone="9876543220",
        password_hash="fakehash",
        role="DOCTOR",
        is_active=True,
    )
    db_session.add(doc_user_1)
    await db_session.commit()

    token_doc_1 = create_access_token({"sub": str(doc_user_1.id), "role": "DOCTOR"})
    headers_doc_1 = {"Authorization": f"Bearer {token_doc_1}"}
    today = date.today().isoformat()

    # Doctor 1 tries to verify Doctor 2's attendance -> Forbidden (403)
    res_forbidden = await client.post(
        f"/api/doctors/{doc_2.id}/verify-attendance?date={today}&attendance_status=PRESENT",
        headers=headers_doc_1,
    )
    assert res_forbidden.status_code == 403
    assert res_forbidden.json()["error"]["code"] == "FORBIDDEN"

    # Doctor 1 can verify their OWN attendance -> Success (200)
    res_own = await client.post(
        f"/api/doctors/{doc_1.id}/verify-attendance?date={today}&attendance_status=PRESENT",
        headers=headers_doc_1,
    )
    assert res_own.status_code == 200
    assert res_own.json()["attendance_status"] == "PRESENT"


@pytest.mark.asyncio
async def test_create_doctor_authorization(client: AsyncClient, seed_data: dict):
    """Anonymous and PATIENT callers cannot create doctors (401/403); STAFF and ADMIN can (201)."""
    fac = seed_data["facilities"][0]
    payload = {
        "facility_id": str(fac.id),
        "name": "Dr. Sunita Rao",
        "specialization": "Pediatrics",
        "qualification": "MBBS, DCH",
    }

    # Anonymous -> 401
    anon_res = await client.post("/api/doctors", json=payload)
    assert anon_res.status_code == 401

    # PATIENT -> 403
    pat_res = await client.post("/api/doctors", json=payload, headers=seed_data["headers"]["patient"])
    assert pat_res.status_code == 403

    # STAFF -> 201
    staff_res = await client.post("/api/doctors", json=payload, headers=seed_data["headers"]["staff"])
    assert staff_res.status_code == 201

    # ADMIN -> 201
    payload["name"] = "Dr. Admin Appointed"
    admin_res = await client.post("/api/doctors", json=payload, headers=seed_data["headers"]["admin"])
    assert admin_res.status_code == 201


@pytest.mark.asyncio
async def test_create_doctor_schedule_authorization(client: AsyncClient, seed_data: dict):
    """Anonymous and PATIENT callers cannot schedule shifts (401/403); STAFF and ADMIN can (201)."""
    doc = seed_data["doctors"][0]
    fac = seed_data["facilities"][0]
    payload = {
        "doctor_id": str(doc.id),
        "facility_id": str(fac.id),
        "schedule_date": "2026-11-20",
        "start_time": "09:00:00",
        "end_time": "13:00:00",
        "attendance_status": "EXPECTED",
    }

    # Anonymous -> 401
    anon_res = await client.post(f"/api/doctors/{doc.id}/schedule", json=payload)
    assert anon_res.status_code == 401

    # PATIENT -> 403
    pat_res = await client.post(f"/api/doctors/{doc.id}/schedule", json=payload, headers=seed_data["headers"]["patient"])
    assert pat_res.status_code == 403

    # STAFF -> 201
    staff_res = await client.post(f"/api/doctors/{doc.id}/schedule", json=payload, headers=seed_data["headers"]["staff"])
    assert staff_res.status_code == 201

    # ADMIN -> 201
    payload["schedule_date"] = "2026-11-21"
    admin_res = await client.post(f"/api/doctors/{doc.id}/schedule", json=payload, headers=seed_data["headers"]["admin"])
    assert admin_res.status_code == 201


@pytest.mark.asyncio
async def test_verify_attendance_role_restrictions(client: AsyncClient, seed_data: dict, db_session):
    """PATIENT and ASHA cannot verify attendance (403); STAFF, ADMIN and DOCTOR can (200)."""
    doc = seed_data["doctors"][0]
    today = date.today().isoformat()

    # Anonymous -> 401
    anon_res = await client.post(f"/api/doctors/{doc.id}/verify-attendance?date={today}&attendance_status=PRESENT")
    assert anon_res.status_code == 401

    # PATIENT -> 403
    pat_res = await client.post(
        f"/api/doctors/{doc.id}/verify-attendance?date={today}&attendance_status=PRESENT",
        headers=seed_data["headers"]["patient"],
    )
    assert pat_res.status_code == 403

    # ASHA -> 403
    asha_res = await client.post(
        f"/api/doctors/{doc.id}/verify-attendance?date={today}&attendance_status=PRESENT",
        headers=seed_data["headers"]["asha"],
    )
    assert asha_res.status_code == 403

    # STAFF -> 200
    staff_res = await client.post(
        f"/api/doctors/{doc.id}/verify-attendance?date={today}&attendance_status=PRESENT",
        headers=seed_data["headers"]["staff"],
    )
    assert staff_res.status_code == 200

    # ADMIN -> 200
    admin_res = await client.post(
        f"/api/doctors/{doc.id}/verify-attendance?date={today}&attendance_status=ABSENT",
        headers=seed_data["headers"]["admin"],
    )
    assert admin_res.status_code == 200
    assert admin_res.json()["attendance_status"] == "ABSENT"

    # DOCTOR (linked doctor profile) -> 200
    doc_user = User(
        id=uuid.uuid4(),
        name="Dr. Anita Sharma",
        phone="9876543220",
        password_hash="fakehash",
        role="DOCTOR",
        is_active=True,
    )
    db_session.add(doc_user)
    await db_session.commit()
    doc_token = create_access_token({"sub": str(doc_user.id), "role": "DOCTOR"})
    doc_headers = {"Authorization": f"Bearer {doc_token}"}

    doc_res = await client.post(
        f"/api/doctors/{doc.id}/verify-attendance?date={today}&attendance_status=PRESENT",
        headers=doc_headers,
    )
    assert doc_res.status_code == 200
    assert doc_res.json()["attendance_status"] == "PRESENT"
