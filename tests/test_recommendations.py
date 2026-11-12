import uuid
import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.request import HealthcareRequest
from app.models.user import User
from app.schemas.shared import RequestType, Role, Urgency


@pytest.mark.asyncio
async def test_generate_and_retrieve_recommendations(client: AsyncClient, db_session):
    """Verify recommendation generation, loss-minimization ordering, and retrieval."""
    patient = User(name="Kavita Singh", phone="9876543401", password_hash="h", role=Role.PATIENT.value)
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)

    token = create_access_token({"sub": str(patient.id), "role": patient.role})
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Consultation Request
    req = HealthcareRequest(
        patient_id=patient.id,
        request_type=RequestType.CONSULTATION,
        description="Fever and body pain",
        urgency=Urgency.NORMAL,
        status="PENDING",
    )
    db_session.add(req)
    await db_session.commit()
    await db_session.refresh(req)

    # 2. Generate Recommendations
    rec_res = await client.post(
        "/api/recommendations",
        json={"request_id": str(req.id)},
        headers=headers,
    )
    assert rec_res.status_code == 200
    data = rec_res.json()
    assert data["request_id"] == str(req.id)
    items = data["items"]
    assert len(items) > 0

    # 3. Verify ascending expected_loss order
    for i in range(len(items) - 1):
        assert items[i]["expected_loss"] <= items[i + 1]["expected_loss"]
        assert items[i]["rank"] == i + 1

    # 4. Verify fields & types
    first_item = items[0]
    assert "facility_id" in first_item
    assert "facility_name" in first_item
    assert "suitability_score" in first_item
    assert 0.0 <= first_item["suitability_score"] <= 1.0
    assert 0.0 <= first_item["failure_probability"] <= 1.0
    assert isinstance(first_item["expected_loss"], int)
    assert isinstance(first_item["travel_distance_km"], int)
    assert isinstance(first_item["travel_cost"], int)
    assert "explanation" in first_item
    assert "simulated" in first_item["explanation"].lower()

    # 5. Retrieve via GET endpoint
    get_res = await client.get(f"/api/recommendations/{req.id}", headers=headers)
    assert get_res.status_code == 200
    retrieved_data = get_res.json()
    assert retrieved_data["request_id"] == str(req.id)
    assert len(retrieved_data["items"]) == len(items)
    assert retrieved_data["items"][0]["facility_id"] == first_item["facility_id"]


@pytest.mark.asyncio
async def test_recommendations_refill_medicine_confidence(client: AsyncClient, db_session):
    """Verify medicine stock handling for refill requests."""
    patient = User(name="Patient Refill", phone="9876543402", password_hash="h", role=Role.PATIENT.value)
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)

    token = create_access_token({"sub": str(patient.id), "role": patient.role})
    headers = {"Authorization": f"Bearer {token}"}

    med_id = uuid.uuid4()
    req = HealthcareRequest(
        patient_id=patient.id,
        request_type=RequestType.REFILL,
        medicine_id=med_id,
        description="Paracetamol and ORS refill",
        urgency=Urgency.PRIORITY,
        status="PENDING",
    )
    db_session.add(req)
    await db_session.commit()
    await db_session.refresh(req)

    rec_res = await client.post(
        "/api/recommendations",
        json={"request_id": str(req.id)},
        headers=headers,
    )
    assert rec_res.status_code == 200
    items = rec_res.json()["items"]
    assert len(items) > 0
    # For refill requests, pharmacies or CHC/PHCs with stock are evaluated
    for item in items:
        assert 0.0 <= item["medicine_confidence"] <= 1.0
        assert "stock" in item["explanation"].lower() or "medicine" in item["explanation"].lower()


@pytest.mark.asyncio
async def test_recommendations_nonexistent_request_returns_404(client: AsyncClient, db_session):
    """Verify 404 response when request_id does not exist."""
    user = User(name="User", phone="9876543403", password_hash="h", role=Role.PATIENT.value)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token({"sub": str(user.id), "role": user.role})
    headers = {"Authorization": f"Bearer {token}"}

    fake_id = uuid.uuid4()
    res = await client.post(
        "/api/recommendations",
        json={"request_id": str(fake_id)},
        headers=headers,
    )
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_recommendations_patient_forbidden_for_other_request(client: AsyncClient, db_session):
    """SECURITY TEST: Verify that a patient cannot generate recommendations for another patient's request."""
    u1 = User(name="U1", phone="9876543404", password_hash="h", role=Role.PATIENT.value)
    u2 = User(name="U2", phone="9876543405", password_hash="h", role=Role.PATIENT.value)
    db_session.add_all([u1, u2])
    await db_session.commit()
    await db_session.refresh(u1)
    await db_session.refresh(u2)

    token2 = create_access_token({"sub": str(u2.id), "role": u2.role})

    # Create request for User 1
    req = HealthcareRequest(patient_id=u1.id, request_type=RequestType.CONSULTATION)
    db_session.add(req)
    await db_session.commit()
    await db_session.refresh(req)

    # User 2 attempts to generate recommendations for User 1's request
    res = await client.post(
        "/api/recommendations",
        json={"request_id": str(req.id)},
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"
