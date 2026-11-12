import uuid
import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.user import User
from app.schemas.shared import RequestType, Role, Urgency


@pytest.mark.asyncio
async def test_create_healthcare_request_success(client: AsyncClient, db_session):
    """Verify successful healthcare request creation by a patient for their own account."""
    # 1. Create patient user
    patient = User(
        name="Sunita Devi",
        phone="9876543301",
        password_hash="fakehash",
        role=Role.PATIENT.value,
        is_active=True,
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)

    token = create_access_token({"sub": str(patient.id), "role": patient.role, "phone": patient.phone})
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "patient_id": str(patient.id),
        "request_type": "CONSULTATION",
        "medicine_id": None,
        "description": "Fever and severe cough for 3 days",
        "urgency": "NORMAL",
    }

    res = await client.post("/api/requests", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert "id" in data
    assert data["status"] == "PENDING"
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_request_patient_forbidden_for_other_patient(client: AsyncClient, db_session):
    """SECURITY TEST: Verify that a patient cannot create a request under another patient's ID."""
    patient1 = User(name="User 1", phone="9876543302", password_hash="h1", role=Role.PATIENT.value)
    patient2 = User(name="User 2", phone="9876543303", password_hash="h2", role=Role.PATIENT.value)
    db_session.add_all([patient1, patient2])
    await db_session.commit()
    await db_session.refresh(patient1)
    await db_session.refresh(patient2)

    token1 = create_access_token({"sub": str(patient1.id), "role": patient1.role})
    headers = {"Authorization": f"Bearer {token1}"}

    payload = {
        "patient_id": str(patient2.id),  # Attempting to forge request for patient 2
        "request_type": "CHECKUP",
        "description": "Routine checkup",
        "urgency": "NORMAL",
    }

    res = await client.post("/api/requests", json=payload, headers=headers)
    assert res.status_code == 403
    err = res.json()
    assert err["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_asha_worker_can_create_request_for_patient(client: AsyncClient, db_session):
    """Verify that an ASHA worker can create a request on behalf of a rural patient."""
    asha = User(name="ASHA Worker 1", phone="9876543304", password_hash="hash", role=Role.ASHA.value)
    patient = User(name="Rural Patient", phone="9876543305", password_hash="hash", role=Role.PATIENT.value)
    db_session.add_all([asha, patient])
    await db_session.commit()
    await db_session.refresh(asha)
    await db_session.refresh(patient)

    token = create_access_token({"sub": str(asha.id), "role": asha.role})
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "patient_id": str(patient.id),
        "request_type": "REFILL",
        "medicine_id": str(uuid.uuid4()),
        "description": "Hypertension medicine refill needed",
        "urgency": "PRIORITY",
    }

    res = await client.post("/api/requests", json=payload, headers=headers)
    assert res.status_code == 201
    assert res.json()["status"] == "PENDING"


@pytest.mark.asyncio
async def test_create_request_invalid_type_fails(client: AsyncClient, db_session):
    """Verify validation rejection for invalid request_type."""
    user = User(name="Test User", phone="9876543306", password_hash="h", role=Role.PATIENT.value)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token({"sub": str(user.id), "role": user.role})
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "patient_id": str(user.id),
        "request_type": "INVALID_TYPE",
        "description": "test",
    }

    res = await client.post("/api/requests", json=payload, headers=headers)
    assert res.status_code == 422
    assert "error" in res.json()


@pytest.mark.asyncio
async def test_create_request_invalid_urgency_fails(client: AsyncClient, db_session):
    """Verify validation rejection for invalid urgency."""
    user = User(name="Test User 2", phone="9876543307", password_hash="h", role=Role.PATIENT.value)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token({"sub": str(user.id), "role": user.role})
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "patient_id": str(user.id),
        "request_type": "CONSULTATION",
        "urgency": "CRITICAL_CODE_RED",  # Invalid urgency
    }

    res = await client.post("/api/requests", json=payload, headers=headers)
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_get_request_by_id_success(client: AsyncClient, db_session):
    """Verify retrieving existing request details by ID."""
    patient = User(name="Ramesh Kumar", phone="9876543308", password_hash="h", role=Role.PATIENT.value)
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)

    token = create_access_token({"sub": str(patient.id), "role": patient.role})
    headers = {"Authorization": f"Bearer {token}"}

    # Create request
    create_res = await client.post(
        "/api/requests",
        json={"patient_id": str(patient.id), "request_type": "DIAGNOSTIC", "description": "Blood sugar test"},
        headers=headers,
    )
    req_id = create_res.json()["id"]

    # Fetch request
    get_res = await client.get(f"/api/requests/{req_id}", headers=headers)
    assert get_res.status_code == 200
    detail = get_res.json()
    assert detail["id"] == req_id
    assert detail["request_type"] == "DIAGNOSTIC"
    assert detail["status"] == "PENDING"
    assert detail["description"] == "Blood sugar test"


@pytest.mark.asyncio
async def test_get_request_unknown_id_returns_404(client: AsyncClient, db_session):
    """Verify 404 response when request ID does not exist."""
    user = User(name="User", phone="9876543309", password_hash="h", role=Role.PATIENT.value)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token({"sub": str(user.id), "role": user.role})
    headers = {"Authorization": f"Bearer {token}"}

    fake_id = uuid.uuid4()
    res = await client.get(f"/api/requests/{fake_id}", headers=headers)
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_get_request_patient_forbidden_for_other_patient(client: AsyncClient, db_session):
    """SECURITY TEST: Verify that a patient cannot read another patient's request."""
    user1 = User(name="U1", phone="9876543310", password_hash="h", role=Role.PATIENT.value)
    user2 = User(name="U2", phone="9876543311", password_hash="h", role=Role.PATIENT.value)
    db_session.add_all([user1, user2])
    await db_session.commit()
    await db_session.refresh(user1)
    await db_session.refresh(user2)

    token1 = create_access_token({"sub": str(user1.id), "role": user1.role})
    token2 = create_access_token({"sub": str(user2.id), "role": user2.role})

    # User 1 creates request
    create_res = await client.post(
        "/api/requests",
        json={"patient_id": str(user1.id), "request_type": "CONSULTATION"},
        headers={"Authorization": f"Bearer {token1}"},
    )
    req_id = create_res.json()["id"]

    # User 2 attempts to read User 1's request
    res = await client.get(f"/api/requests/{req_id}", headers={"Authorization": f"Bearer {token2}"})
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"
