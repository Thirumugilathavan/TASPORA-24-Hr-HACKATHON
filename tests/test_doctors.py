from datetime import date
import uuid
import pytest
from httpx import AsyncClient


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


@pytest.mark.asyncio
async def test_doctor_schedule_unscheduled_date_returns_unknown(client: AsyncClient, seed_data: dict):
    """Do not invent doctor attendance.
    If no schedule is logged for the requested date, returns UNKNOWN.
    """
    doc_1 = seed_data["doctors"][0]
    future_date = "2026-12-25"
    response = await client.get(f"/api/doctors/{doc_1.id}/schedule?date={future_date}")
    assert response.status_code == 200
    data = response.json()
    assert data["attendance_status"] == "UNKNOWN"
    assert data["schedule"] is None


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
