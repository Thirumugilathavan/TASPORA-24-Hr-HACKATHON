from datetime import date, time
import uuid
import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.appointment import Appointment
from app.models.request import HealthcareRequest
from app.models.user import User
from app.schemas.shared import AppointmentStatus, RequestType, Role


@pytest.mark.asyncio
async def test_create_appointment_success(client: AsyncClient, db_session):
    """Verify booking an appointment for a patient."""
    patient = User(name="Geeta Patel", phone="9876543501", password_hash="h", role=Role.PATIENT.value)
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)

    token = create_access_token({"sub": str(patient.id), "role": patient.role})
    headers = {"Authorization": f"Bearer {token}"}

    req = HealthcareRequest(patient_id=patient.id, request_type=RequestType.CONSULTATION)
    db_session.add(req)
    await db_session.commit()
    await db_session.refresh(req)

    facility_id = uuid.uuid4()
    doctor_id = uuid.uuid4()
    appt_date = date(2026, 11, 20)
    appt_time = "10:30:00"

    payload = {
        "patient_id": str(patient.id),
        "facility_id": str(facility_id),
        "doctor_id": str(doctor_id),
        "request_id": str(req.id),
        "appointment_date": appt_date.isoformat(),
        "appointment_time": appt_time,
    }

    res = await client.post("/api/appointments", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert "id" in data
    assert data["status"] == "BOOKED"


@pytest.mark.asyncio
async def test_appointment_double_booking_doctor_conflict_returns_409(client: AsyncClient, db_session):
    """CONCURRENCY / CONFLICT TEST: Verify HTTP 409 when double-booking same doctor and time."""
    p1 = User(name="Patient A", phone="9876543502", password_hash="h", role=Role.PATIENT.value)
    p2 = User(name="Patient B", phone="9876543503", password_hash="h", role=Role.PATIENT.value)
    db_session.add_all([p1, p2])
    await db_session.commit()
    await db_session.refresh(p1)
    await db_session.refresh(p2)

    token1 = create_access_token({"sub": str(p1.id), "role": p1.role})
    token2 = create_access_token({"sub": str(p2.id), "role": p2.role})

    facility_id = uuid.uuid4()
    doctor_id = uuid.uuid4()
    target_date = "2026-11-25"
    target_time = "14:00:00"

    # Patient 1 books the slot
    payload1 = {
        "patient_id": str(p1.id),
        "facility_id": str(facility_id),
        "doctor_id": str(doctor_id),
        "appointment_date": target_date,
        "appointment_time": target_time,
    }
    res1 = await client.post("/api/appointments", json=payload1, headers={"Authorization": f"Bearer {token1}"})
    assert res1.status_code == 201

    # Patient 2 attempts to book the EXACT SAME doctor, date, and time
    payload2 = {
        "patient_id": str(p2.id),
        "facility_id": str(facility_id),
        "doctor_id": str(doctor_id),
        "appointment_date": target_date,
        "appointment_time": target_time,
    }
    res2 = await client.post("/api/appointments", json=payload2, headers={"Authorization": f"Bearer {token2}"})
    assert res2.status_code == 409
    err = res2.json()
    assert err["error"]["code"] == "SLOT_TAKEN"
    assert "already booked" in err["error"]["message"].lower()


@pytest.mark.asyncio
async def test_appointment_unassigned_facility_conflict_returns_409(client: AsyncClient, db_session):
    """CONFLICT TEST: Verify HTTP 409 when booking same unassigned facility walk-in slot."""
    p1 = User(name="Patient C", phone="9876543504", password_hash="h", role=Role.PATIENT.value)
    p2 = User(name="Patient D", phone="9876543505", password_hash="h", role=Role.PATIENT.value)
    db_session.add_all([p1, p2])
    await db_session.commit()
    await db_session.refresh(p1)
    await db_session.refresh(p2)

    token1 = create_access_token({"sub": str(p1.id), "role": p1.role})
    token2 = create_access_token({"sub": str(p2.id), "role": p2.role})

    facility_id = uuid.uuid4()
    target_date = "2026-11-26"
    target_time = "11:00:00"

    payload1 = {
        "patient_id": str(p1.id),
        "facility_id": str(facility_id),
        "doctor_id": None,
        "appointment_date": target_date,
        "appointment_time": target_time,
    }
    res1 = await client.post("/api/appointments", json=payload1, headers={"Authorization": f"Bearer {token1}"})
    assert res1.status_code == 201

    payload2 = {
        "patient_id": str(p2.id),
        "facility_id": str(facility_id),
        "doctor_id": None,
        "appointment_date": target_date,
        "appointment_time": target_time,
    }
    res2 = await client.post("/api/appointments", json=payload2, headers={"Authorization": f"Bearer {token2}"})
    assert res2.status_code == 409
    assert res2.json()["error"]["code"] == "SLOT_TAKEN"


@pytest.mark.asyncio
async def test_appointment_cancellation_releases_slot(client: AsyncClient, db_session):
    """LIFECYCLE TEST: Verify that cancelling an appointment releases the slot for re-booking."""
    p1 = User(name="Patient E", phone="9876543506", password_hash="h", role=Role.PATIENT.value)
    p2 = User(name="Patient F", phone="9876543507", password_hash="h", role=Role.PATIENT.value)
    db_session.add_all([p1, p2])
    await db_session.commit()
    await db_session.refresh(p1)
    await db_session.refresh(p2)

    token1 = create_access_token({"sub": str(p1.id), "role": p1.role})
    token2 = create_access_token({"sub": str(p2.id), "role": p2.role})

    facility_id = uuid.uuid4()
    doctor_id = uuid.uuid4()
    target_date = "2026-11-27"
    target_time = "09:00:00"

    # 1. Patient 1 books
    res1 = await client.post(
        "/api/appointments",
        json={
            "patient_id": str(p1.id),
            "facility_id": str(facility_id),
            "doctor_id": str(doctor_id),
            "appointment_date": target_date,
            "appointment_time": target_time,
        },
        headers={"Authorization": f"Bearer {token1}"},
    )
    appt_id = res1.json()["id"]

    # 2. Patient 1 cancels
    cancel_res = await client.patch(f"/api/appointments/{appt_id}/cancel", headers={"Authorization": f"Bearer {token1}"})
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELLED"

    # 3. Repeated cancellation is idempotent
    repeat_cancel = await client.patch(f"/api/appointments/{appt_id}/cancel", headers={"Authorization": f"Bearer {token1}"})
    assert repeat_cancel.status_code == 200
    assert repeat_cancel.json()["status"] == "CANCELLED"

    # 4. Patient 2 can now book the exact same slot because active conflict is released!
    res2 = await client.post(
        "/api/appointments",
        json={
            "patient_id": str(p2.id),
            "facility_id": str(facility_id),
            "doctor_id": str(doctor_id),
            "appointment_date": target_date,
            "appointment_time": target_time,
        },
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert res2.status_code == 201
    assert res2.json()["status"] == "BOOKED"


@pytest.mark.asyncio
async def test_get_appointment_by_id_and_ownership(client: AsyncClient, db_session):
    """SECURITY TEST: Verify retrieving appointment and patient authorization."""
    p1 = User(name="P1", phone="9876543508", password_hash="h", role=Role.PATIENT.value)
    p2 = User(name="P2", phone="9876543509", password_hash="h", role=Role.PATIENT.value)
    db_session.add_all([p1, p2])
    await db_session.commit()
    await db_session.refresh(p1)
    await db_session.refresh(p2)

    token1 = create_access_token({"sub": str(p1.id), "role": p1.role})
    token2 = create_access_token({"sub": str(p2.id), "role": p2.role})

    # Book for P1
    create_res = await client.post(
        "/api/appointments",
        json={
            "patient_id": str(p1.id),
            "facility_id": str(uuid.uuid4()),
            "appointment_date": "2026-11-28",
            "appointment_time": "15:00:00",
        },
        headers={"Authorization": f"Bearer {token1}"},
    )
    appt_id = create_res.json()["id"]

    # P1 reads own appointment -> 200
    get_res = await client.get(f"/api/appointments/{appt_id}", headers={"Authorization": f"Bearer {token1}"})
    assert get_res.status_code == 200
    assert get_res.json()["id"] == appt_id
    assert get_res.json()["status"] == "BOOKED"

    # P2 attempts to read P1's appointment -> 403 Forbidden
    forbidden_res = await client.get(f"/api/appointments/{appt_id}", headers={"Authorization": f"Bearer {token2}"})
    assert forbidden_res.status_code == 403
    assert forbidden_res.json()["error"]["code"] == "FORBIDDEN"

    # P2 attempts to cancel P1's appointment -> 403 Forbidden
    cancel_forbidden = await client.patch(f"/api/appointments/{appt_id}/cancel", headers={"Authorization": f"Bearer {token2}"})
    assert cancel_forbidden.status_code == 403
