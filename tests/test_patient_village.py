from datetime import date, timedelta
from uuid import UUID, uuid4
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.patient import Patient
from app.models.user import User
from app.models.village import Village
from app.services.village_service import VillageService


async def create_user_helper(db: AsyncSession, name: str, phone: str, role: str = "PATIENT") -> User:
    """Helper creating a user directly in the database."""
    user = User(
        name=name,
        phone=phone,
        password_hash=hash_password("SecurePassword123"),
        role=role,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def auth_header(user: User) -> dict:
    """Generates an Authorization Bearer header for a given user."""
    token = create_access_token(data={"sub": str(user.id), "role": user.role})
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# 1. Village Listing Tests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_village_listing(client: AsyncClient, db_session: AsyncSession):
    """Verifies GET /api/villages returns items and total per API contract."""
    await VillageService.seed_synthetic_villages(db_session)

    response = await client.get("/api/villages")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1
    assert isinstance(data["items"], list)

    first = data["items"][0]
    assert "id" in first
    assert "name" in first
    assert "district" in first
    assert "latitude" in first
    assert "longitude" in first


# ---------------------------------------------------------------------------
# 2. Patient Creation Tests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_successful_patient_creation(client: AsyncClient, db_session: AsyncSession):
    """Verifies POST /api/patients creates a patient profile bound to the authenticated user."""
    await VillageService.seed_synthetic_villages(db_session)
    villages = await VillageService.list_villages(db_session)
    village_id = str(villages.items[0].id)

    user = await create_user_helper(db_session, "Sunita Devi", "9876543220")
    headers = auth_header(user)

    payload = {
        "village_id": village_id,
        "date_of_birth": "1995-06-20",
        "preferred_language": "hi",
        "consent_given": True,
        "emergency_contact_phone": "9876543229",
    }
    response = await client.post("/api/patients", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["user_id"] == str(user.id)
    assert data["village_id"] == village_id
    assert data["date_of_birth"] == "1995-06-20"
    assert data["preferred_language"] == "hi"
    assert data["consent_given"] is True


@pytest.mark.asyncio
async def test_patient_creation_invalid_village_id(client: AsyncClient, db_session: AsyncSession):
    """Verifies POST /api/patients returns 404 when referencing a non-existent village."""
    user = await create_user_helper(db_session, "Ramesh Test", "9876543221")
    headers = auth_header(user)

    payload = {
        "village_id": str(uuid4()),
        "date_of_birth": "1990-01-01",
        "preferred_language": "hi",
    }
    response = await client.post("/api/patients", json=payload, headers=headers)
    assert response.status_code == 404
    err = response.json().get("error", {})
    assert err.get("code") == "VILLAGE_NOT_FOUND"


@pytest.mark.asyncio
async def test_patient_creation_missing_required_fields(client: AsyncClient, db_session: AsyncSession):
    """Verifies POST /api/patients returns 422 when required fields are missing."""
    user = await create_user_helper(db_session, "Missing Fields User", "9876543222")
    headers = auth_header(user)

    payload = {"preferred_language": "hi"}
    response = await client.post("/api/patients", json=payload, headers=headers)
    assert response.status_code == 422
    err = response.json().get("error", {})
    assert err.get("code") == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_patient_creation_invalid_dob_future(client: AsyncClient, db_session: AsyncSession):
    """Verifies POST /api/patients returns 422 when date_of_birth is in the future."""
    await VillageService.seed_synthetic_villages(db_session)
    villages = await VillageService.list_villages(db_session)
    village_id = str(villages.items[0].id)

    user = await create_user_helper(db_session, "Future DOB User", "9876543223")
    headers = auth_header(user)
    future_date = (date.today() + timedelta(days=5)).isoformat()

    payload = {
        "village_id": village_id,
        "date_of_birth": future_date,
        "preferred_language": "hi",
    }
    response = await client.post("/api/patients", json=payload, headers=headers)
    assert response.status_code == 422
    err = response.json().get("error", {})
    assert err.get("code") == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_duplicate_patient_registration(client: AsyncClient, db_session: AsyncSession):
    """Verifies POST /api/patients rejects creating a second profile for the same user with 409 Conflict."""
    await VillageService.seed_synthetic_villages(db_session)
    villages = await VillageService.list_villages(db_session)
    village_id = str(villages.items[0].id)

    user = await create_user_helper(db_session, "Duplicate Patient User", "9876543224")
    headers = auth_header(user)

    payload = {
        "village_id": village_id,
        "date_of_birth": "1992-03-15",
        "preferred_language": "hi",
    }
    res1 = await client.post("/api/patients", json=payload, headers=headers)
    assert res1.status_code == 201

    # Second registration attempt for the same user
    res2 = await client.post("/api/patients", json=payload, headers=headers)
    assert res2.status_code == 409
    err = res2.json().get("error", {})
    assert err.get("code") == "PATIENT_ALREADY_EXISTS"


# ---------------------------------------------------------------------------
# 3. Patient Retrieval & Authorization Tests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_patient_retrieval_success(client: AsyncClient, db_session: AsyncSession):
    """Verifies GET /api/patients/{id} returns profile with nested village details."""
    await VillageService.seed_synthetic_villages(db_session)
    villages = await VillageService.list_villages(db_session)
    village = villages.items[0]

    user = await create_user_helper(db_session, "Retrieve Patient User", "9876543225")
    patient = Patient(
        user_id=user.id,
        village_id=village.id,
        date_of_birth=date(1988, 5, 12),
        preferred_language="hi",
        consent_given=True,
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)

    headers = auth_header(user)
    response = await client.get(f"/api/patients/{patient.id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(patient.id)
    assert data["user_id"] == str(user.id)
    assert data["name"] == user.name
    assert data["phone"] == user.phone
    assert data["date_of_birth"] == "1988-05-12"
    assert data["preferred_language"] == "hi"

    # Verify nested village relationship attributes
    village_data = data["village"]
    assert village_data["id"] == str(village.id)
    assert village_data["name"] == village.name
    assert village_data["district"] == village.district
    assert village_data["latitude"] == village.latitude
    assert village_data["longitude"] == village.longitude


@pytest.mark.asyncio
async def test_patient_retrieval_unknown_patient(client: AsyncClient, db_session: AsyncSession):
    """Verifies GET /api/patients/{id} returns 404 for a non-existent patient UUID."""
    user = await create_user_helper(db_session, "Unknown Patient Caller", "9876543226")
    headers = auth_header(user)
    random_id = str(uuid4())

    response = await client.get(f"/api/patients/{random_id}", headers=headers)
    assert response.status_code == 404
    err = response.json().get("error", {})
    assert err.get("code") == "PATIENT_NOT_FOUND"


@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient, db_session: AsyncSession):
    """Verifies endpoints reject unauthenticated requests with 401 Unauthorized."""
    # POST /api/patients without auth header
    res_post = await client.post(
        "/api/patients",
        json={"village_id": str(uuid4()), "date_of_birth": "1990-01-01", "preferred_language": "hi"},
    )
    assert res_post.status_code == 401
    assert res_post.json()["error"]["code"] == "UNAUTHORIZED"

    # GET /api/patients/{id} without auth header
    res_get = await client.get(f"/api/patients/{uuid4()}")
    assert res_get.status_code == 401
    assert res_get.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_access_to_another_patients_record_forbidden(client: AsyncClient, db_session: AsyncSession):
    """Verifies that Patient B is forbidden (403) from accessing Patient A's record."""
    await VillageService.seed_synthetic_villages(db_session)
    villages = await VillageService.list_villages(db_session)
    village_id = villages.items[0].id

    user_a = await create_user_helper(db_session, "Patient A", "9876543227")
    user_b = await create_user_helper(db_session, "Patient B", "9876543228")

    patient_a = Patient(
        user_id=user_a.id,
        village_id=village_id,
        date_of_birth=date(1991, 10, 20),
        preferred_language="hi",
    )
    db_session.add(patient_a)
    await db_session.commit()
    await db_session.refresh(patient_a)

    # Patient B attempts to retrieve Patient A's record
    headers_b = auth_header(user_b)
    response = await client.get(f"/api/patients/{patient_a.id}", headers=headers_b)
    assert response.status_code == 403
    err = response.json().get("error", {})
    assert err.get("code") == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_clinical_roles_can_access_patient(client: AsyncClient, db_session: AsyncSession):
    """Verifies that clinical/operational roles (DOCTOR, ASHA) can access patient profiles."""
    await VillageService.seed_synthetic_villages(db_session)
    villages = await VillageService.list_villages(db_session)
    village_id = villages.items[0].id

    patient_user = await create_user_helper(db_session, "Patient User", "9876543229")
    doctor_user = await create_user_helper(db_session, "Dr. Rao", "9876543230", role="DOCTOR")
    asha_user = await create_user_helper(db_session, "Sunita ASHA", "9876543231", role="ASHA")

    patient = Patient(
        user_id=patient_user.id,
        village_id=village_id,
        date_of_birth=date(1985, 4, 10),
        preferred_language="hi",
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)

    # Doctor access
    doc_res = await client.get(f"/api/patients/{patient.id}", headers=auth_header(doctor_user))
    assert doc_res.status_code == 200
    assert doc_res.json()["id"] == str(patient.id)

    # ASHA access
    asha_res = await client.get(f"/api/patients/{patient.id}", headers=auth_header(asha_user))
    assert asha_res.status_code == 200
    assert asha_res.json()["id"] == str(patient.id)
