from datetime import date
import uuid
import pytest
from httpx import AsyncClient

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
    doc_1 = seed_data["doctors"][0]  # Dr. Anita Sharma
    doc_2 = seed_data["doctors"][1]  # Dr. Rajesh Kumar

    # Create user for Doctor 1 and explicitly link to doc_1
    doc_user_1 = User(
        name="Dr. Anita Sharma",
        phone="9876543220",
        password_hash="fakehash",
        role="DOCTOR",
        is_active=True,
    )
    db_session.add(doc_user_1)
    await db_session.flush()

    # Explicitly link doc_1 to doc_user_1
    doc_1.user_id = doc_user_1.id
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
async def test_unlinked_doctor_cannot_self_verify(client: AsyncClient, db_session, seed_data: dict):
    """SECURITY TEST: An unlinked legacy doctor profile cannot self-verify (fail-closed).

    Even if the User account has matching name and phone, without explicit user_id linkage,
    the attendance verification is rejected with HTTP 403 FORBIDDEN.
    """
    doc_1 = seed_data["doctors"][0]
    assert doc_1.user_id is None  # Legacy unlinked profile

    # Create doctor user with identical name and phone
    matching_user = User(
        name=doc_1.name,
        phone=doc_1.contact_phone,
        password_hash="fakehash",
        role="DOCTOR",
        is_active=True,
    )
    db_session.add(matching_user)
    await db_session.commit()

    token = create_access_token({"sub": str(matching_user.id), "role": "DOCTOR"})
    headers = {"Authorization": f"Bearer {token}"}
    today = date.today().isoformat()

    # Should FAIL CLOSED with 403 because user_id is not explicitly linked
    res = await client.post(
        f"/api/doctors/{doc_1.id}/verify-attendance?date={today}&attendance_status=PRESENT",
        headers=headers,
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_staff_links_doctor_to_user_and_then_doctor_verifies(client: AsyncClient, db_session, seed_data: dict):
    """SECURITY TEST: Trusted STAFF process explicitly links doctor to user, enabling self-verification."""
    doc_2 = seed_data["doctors"][1]
    staff_headers = seed_data["headers"]["staff"]

    # Create doctor user
    doc_user_2 = User(
        name="Dr. Rajesh Kumar",
        phone="9876543299",
        password_hash="fakehash",
        role="DOCTOR",
        is_active=True,
    )
    db_session.add(doc_user_2)
    await db_session.commit()

    # STAFF links doctor profile to user account
    link_res = await client.post(
        f"/api/doctors/{doc_2.id}/link-user",
        json={"user_id": str(doc_user_2.id)},
        headers=staff_headers,
    )
    assert link_res.status_code == 200
    assert link_res.json()["user_id"] == str(doc_user_2.id)

    # Doctor 2 can now verify attendance
    token_doc_2 = create_access_token({"sub": str(doc_user_2.id), "role": "DOCTOR"})
    headers_doc_2 = {"Authorization": f"Bearer {token_doc_2}"}
    today = date.today().isoformat()

    verify_res = await client.post(
        f"/api/doctors/{doc_2.id}/verify-attendance?date={today}&attendance_status=PRESENT",
        headers=headers_doc_2,
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["attendance_status"] == "PRESENT"


@pytest.mark.asyncio
async def test_link_doctor_duplicate_user_rejected(client: AsyncClient, db_session, seed_data: dict):
    """SECURITY TEST: Duplicate doctor-user associations are rejected (409 Conflict)."""
    doc_1 = seed_data["doctors"][0]
    doc_2 = seed_data["doctors"][1]
    staff_headers = seed_data["headers"]["staff"]

    doc_user = User(
        name="Dr. Unique",
        phone="9876543298",
        password_hash="fakehash",
        role="DOCTOR",
        is_active=True,
    )
    db_session.add(doc_user)
    await db_session.commit()

    # Link to doc_1 -> Success
    res1 = await client.post(
        f"/api/doctors/{doc_1.id}/link-user",
        json={"user_id": str(doc_user.id)},
        headers=staff_headers,
    )
    assert res1.status_code == 200

    # Attempt to link same user to doc_2 -> 409 Conflict
    res2 = await client.post(
        f"/api/doctors/{doc_2.id}/link-user",
        json={"user_id": str(doc_user.id)},
        headers=staff_headers,
    )
    assert res2.status_code == 409
    assert res2.json()["error"]["code"] == "CONFLICT"


@pytest.mark.asyncio
async def test_link_doctor_non_doctor_role_rejected(client: AsyncClient, seed_data: dict):
    """SECURITY TEST: Linking a user who is not a DOCTOR (e.g. PATIENT) is rejected (400 Bad Request)."""
    doc_1 = seed_data["doctors"][0]
    staff_headers = seed_data["headers"]["staff"]
    patient_user = seed_data["users"]["patient"]

    res = await client.post(
        f"/api/doctors/{doc_1.id}/link-user",
        json={"user_id": str(patient_user.id)},
        headers=staff_headers,
    )
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "BAD_REQUEST"


@pytest.mark.asyncio
async def test_patient_cannot_link_doctor_user(client: AsyncClient, seed_data: dict):
    """SECURITY TEST: PATIENT role cannot invoke administrative link-user endpoint (403 Forbidden)."""
    doc_1 = seed_data["doctors"][0]
    patient_headers = seed_data["headers"]["patient"]

    res = await client.post(
        f"/api/doctors/{doc_1.id}/link-user",
        json={"user_id": str(uuid.uuid4())},
        headers=patient_headers,
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_verify_attendance_nonexistent_doctor_returns_404(client: AsyncClient, seed_data: dict):
    """SECURITY TEST: Attendance verification for non-existent doctor ID safely returns 404."""
    staff_headers = seed_data["headers"]["staff"]
    random_id = uuid.uuid4()
    today = date.today().isoformat()

    res = await client.post(
        f"/api/doctors/{random_id}/verify-attendance?date={today}&attendance_status=PRESENT",
        headers=staff_headers,
    )
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_create_doctor_with_explicit_user_id(client: AsyncClient, db_session, seed_data: dict):
    """Verify creating a doctor with explicit user_id succeeds and establishes link."""
    staff_headers = seed_data["headers"]["staff"]
    fac_1 = seed_data["facilities"][0]

    doc_user = User(
        name="Dr. Direct Link",
        phone="9876543297",
        password_hash="fakehash",
        role="DOCTOR",
        is_active=True,
    )
    db_session.add(doc_user)
    await db_session.commit()

    payload = {
        "facility_id": str(fac_1.id),
        "name": "Dr. Direct Link",
        "specialization": "Orthopedics",
        "user_id": str(doc_user.id),
    }
    res = await client.post("/api/doctors", json=payload, headers=staff_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["user_id"] == str(doc_user.id)
    assert data["name"] == "Dr. Direct Link"
