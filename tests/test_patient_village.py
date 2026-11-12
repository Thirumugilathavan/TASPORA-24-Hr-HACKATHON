from datetime import date, timedelta
from uuid import UUID, uuid4
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.patient import Patient
from app.models.user import User
from app.models.village import Village
from app.schemas.patient_village import VillageIn
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
# 1. Village Listing & Registry Tests
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
    assert first["is_synthetic"] is True


@pytest.mark.asyncio
async def test_village_coordinate_validation():
    """Verifies Village model rejects coordinates outside valid geographic boundaries."""
    # Valid coordinates
    v_valid = Village(
        name="Valid Village",
        district="Sitapur",
        latitude=27.5684,
        longitude=80.6791,
        is_synthetic=True,
    )
    assert v_valid.latitude == 27.5684
    assert v_valid.longitude == 80.6791

    # Invalid latitude > 90
    with pytest.raises(ValueError, match="Latitude must be between -90.0 and 90.0"):
        Village(name="Bad Lat", district="Test", latitude=95.0, longitude=80.0)

    # Invalid latitude < -90
    with pytest.raises(ValueError, match="Latitude must be between -90.0 and 90.0"):
        Village(name="Bad Lat", district="Test", latitude=-91.5, longitude=80.0)

    # Invalid longitude > 180
    with pytest.raises(ValueError, match="Longitude must be between -180.0 and 180.0"):
        Village(name="Bad Lon", district="Test", latitude=20.0, longitude=185.0)

    # Empty name or district
    with pytest.raises(ValueError, match="name cannot be empty"):
        Village(name="  ", district="Test", latitude=20.0, longitude=80.0)


# ---------------------------------------------------------------------------
# 2. Patient Creation & Demographics Tests
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
async def test_patient_creation_tamil_and_english_languages(client: AsyncClient, db_session: AsyncSession):
    """Verifies support for Tamil and English preferred languages without forcing Hindi."""
    await VillageService.seed_synthetic_villages(db_session)
    villages = await VillageService.list_villages(db_session)
    village_id = str(villages.items[0].id)

    # Tamil language support
    user_ta = await create_user_helper(db_session, "Kavitha Murugan", "9876543250")
    res_ta = await client.post(
        "/api/patients",
        json={
            "village_id": village_id,
            "date_of_birth": "1992-04-10",
            "preferred_language": "ta",
            "consent_given": True,
        },
        headers=auth_header(user_ta),
    )
    assert res_ta.status_code == 201
    assert res_ta.json()["preferred_language"] == "ta"

    # English language support
    user_en = await create_user_helper(db_session, "John Peter", "9876543251")
    res_en = await client.post(
        "/api/patients",
        json={
            "village_id": village_id,
            "date_of_birth": "1988-11-25",
            "preferred_language": "en",
            "consent_given": True,
        },
        headers=auth_header(user_en),
    )
    assert res_en.status_code == 201
    assert res_en.json()["preferred_language"] == "en"


@pytest.mark.asyncio
async def test_patient_creation_consent_not_silently_assumed(client: AsyncClient, db_session: AsyncSession):
    """PRIVACY REQUIREMENT: Consent must not be silently assumed to be True if omitted."""
    await VillageService.seed_synthetic_villages(db_session)
    villages = await VillageService.list_villages(db_session)
    village_id = str(villages.items[0].id)

    user = await create_user_helper(db_session, "No Consent Provided", "9876543252")
    # Payload omits consent_given
    payload = {
        "village_id": village_id,
        "date_of_birth": "1990-01-01",
        "preferred_language": "ta",
    }
    response = await client.post("/api/patients", json=payload, headers=auth_header(user))
    assert response.status_code == 201
    data = response.json()
    # Must NOT be assumed True
    assert data["consent_given"] is False


@pytest.mark.asyncio
async def test_emergency_contact_phone_validation(client: AsyncClient, db_session: AsyncSession):
    """Verifies that emergency contact phone is optional, but strictly validated when provided."""
    await VillageService.seed_synthetic_villages(db_session)
    villages = await VillageService.list_villages(db_session)
    village_id = str(villages.items[0].id)

    user = await create_user_helper(db_session, "Invalid Contact User", "9876543253")

    # Invalid phone format: too short
    res_short = await client.post(
        "/api/patients",
        json={"village_id": village_id, "date_of_birth": "1990-01-01", "emergency_contact_phone": "12345"},
        headers=auth_header(user),
    )
    assert res_short.status_code == 422

    # Invalid phone format: non-numeric
    res_alpha = await client.post(
        "/api/patients",
        json={"village_id": village_id, "date_of_birth": "1990-01-01", "emergency_contact_phone": "98765abcde"},
        headers=auth_header(user),
    )
    assert res_alpha.status_code == 422


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
# 3. Patient Retrieval & Identity Resolution Tests
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
        preferred_language="ta",
        consent_given=True,
        emergency_contact_phone="9876543299",
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
    assert data["preferred_language"] == "ta"
    assert data["emergency_contact_phone"] == "9876543299"

    # Verify nested village relationship attributes
    village_data = data["village"]
    assert village_data["id"] == str(village.id)
    assert village_data["name"] == village.name
    assert village_data["district"] == village.district
    assert village_data["latitude"] == village.latitude
    assert village_data["longitude"] == village.longitude


@pytest.mark.asyncio
async def test_patient_retrieval_by_user_id(client: AsyncClient, db_session: AsyncSession):
    """IDENTITY RESOLUTION: Verifies resolution when caller looks up using User.id instead of Patient.id."""
    await VillageService.seed_synthetic_villages(db_session)
    villages = await VillageService.list_villages(db_session)
    village = villages.items[0]

    user = await create_user_helper(db_session, "User ID Query Patient", "9876543254")
    patient = Patient(
        user_id=user.id,
        village_id=village.id,
        date_of_birth=date(1993, 7, 14),
        preferred_language="ta",
        consent_given=True,
    )
    db_session.add(patient)
    await db_session.commit()

    # Call GET /api/patients/{user.id} instead of patient.id
    response = await client.get(f"/api/patients/{user.id}", headers=auth_header(user))
    assert response.status_code == 200
    assert response.json()["id"] == str(patient.id)
    assert response.json()["user_id"] == str(user.id)


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


# ---------------------------------------------------------------------------
# 4. Authorization & Consent Controls
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_access_to_another_patients_record_forbidden(client: AsyncClient, db_session: AsyncSession):
    """SECURITY TEST: Verifies that Patient B is forbidden (403) from accessing Patient A's record."""
    await VillageService.seed_synthetic_villages(db_session)
    villages = await VillageService.list_villages(db_session)
    village_id = villages.items[0].id

    user_a = await create_user_helper(db_session, "Patient A", "9876543227")
    user_b = await create_user_helper(db_session, "Patient B", "9876543228")

    patient_a = Patient(
        user_id=user_a.id,
        village_id=village_id,
        date_of_birth=date(1991, 10, 20),
        preferred_language="ta",
        consent_given=True,
    )
    db_session.add(patient_a)
    await db_session.commit()

    # Patient B attempts to retrieve Patient A's record
    headers_b = auth_header(user_b)
    response = await client.get(f"/api/patients/{patient_a.id}", headers=headers_b)
    assert response.status_code == 403
    err = response.json().get("error", {})
    assert err.get("code") == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_clinical_roles_can_access_consented_patient(client: AsyncClient, db_session: AsyncSession):
    """LEAST PRIVILEGE: Verifies that clinical roles (DOCTOR, ASHA) can access patient profile when consent is granted."""
    await VillageService.seed_synthetic_villages(db_session)
    villages = await VillageService.list_villages(db_session)
    village_id = villages.items[0].id

    patient_user = await create_user_helper(db_session, "Patient Consented", "9876543229")
    doctor_user = await create_user_helper(db_session, "Dr. Rao", "9876543230", role="DOCTOR")
    asha_user = await create_user_helper(db_session, "Sunita ASHA", "9876543231", role="ASHA")

    patient = Patient(
        user_id=patient_user.id,
        village_id=village_id,
        date_of_birth=date(1985, 4, 10),
        preferred_language="ta",
        consent_given=True,
        emergency_contact_phone="9876543288",
    )
    db_session.add(patient)
    await db_session.commit()

    # Doctor access
    doc_res = await client.get(f"/api/patients/{patient.id}", headers=auth_header(doctor_user))
    assert doc_res.status_code == 200
    assert doc_res.json()["id"] == str(patient.id)
    assert doc_res.json()["emergency_contact_phone"] == "9876543288"

    # ASHA access
    asha_res = await client.get(f"/api/patients/{patient.id}", headers=auth_header(asha_user))
    assert asha_res.status_code == 200
    assert asha_res.json()["id"] == str(patient.id)
    assert asha_res.json()["emergency_contact_phone"] == "9876543288"


@pytest.mark.asyncio
async def test_clinical_roles_cannot_access_unconsented_patient(client: AsyncClient, db_session: AsyncSession):
    """PRIVACY REQUIREMENT: Clinical roles (ASHA, DOCTOR, STAFF) are blocked (403) from accessing records without patient consent."""
    await VillageService.seed_synthetic_villages(db_session)
    villages = await VillageService.list_villages(db_session)
    village_id = villages.items[0].id

    patient_user = await create_user_helper(db_session, "Patient Unconsented", "9876543255")
    doctor_user = await create_user_helper(db_session, "Dr. Blocked", "9876543256", role="DOCTOR")
    asha_user = await create_user_helper(db_session, "ASHA Blocked", "9876543257", role="ASHA")
    staff_user = await create_user_helper(db_session, "Staff Blocked", "9876543258", role="STAFF")

    # Patient explicitly did NOT give consent (consent_given=False)
    patient = Patient(
        user_id=patient_user.id,
        village_id=village_id,
        date_of_birth=date(1994, 2, 20),
        preferred_language="ta",
        consent_given=False,
    )
    db_session.add(patient)
    await db_session.commit()

    # Doctor attempt without consent -> 403 CONSENT_REQUIRED
    doc_res = await client.get(f"/api/patients/{patient.id}", headers=auth_header(doctor_user))
    assert doc_res.status_code == 403
    assert doc_res.json()["error"]["code"] == "CONSENT_REQUIRED"

    # ASHA attempt without consent -> 403 CONSENT_REQUIRED
    asha_res = await client.get(f"/api/patients/{patient.id}", headers=auth_header(asha_user))
    assert asha_res.status_code == 403
    assert asha_res.json()["error"]["code"] == "CONSENT_REQUIRED"

    # Staff attempt without consent -> 403 CONSENT_REQUIRED
    staff_res = await client.get(f"/api/patients/{patient.id}", headers=auth_header(staff_user))
    assert staff_res.status_code == 403
    assert staff_res.json()["error"]["code"] == "CONSENT_REQUIRED"

    # Patient can still access their own record even if consent_given is False
    self_res = await client.get(f"/api/patients/{patient.id}", headers=auth_header(patient_user))
    assert self_res.status_code == 200
    assert self_res.json()["id"] == str(patient.id)


@pytest.mark.asyncio
async def test_admin_and_staff_permissions(client: AsyncClient, db_session: AsyncSession):
    """Verifies ADMIN has audit access and STAFF has consented access."""
    await VillageService.seed_synthetic_villages(db_session)
    villages = await VillageService.list_villages(db_session)
    village_id = villages.items[0].id

    patient_user = await create_user_helper(db_session, "Patient Consent Staff", "9876543259")
    admin_user = await create_user_helper(db_session, "Admin User", "9876543260", role="ADMIN")
    staff_user = await create_user_helper(db_session, "Staff User", "9876543261", role="STAFF")

    patient = Patient(
        user_id=patient_user.id,
        village_id=village_id,
        date_of_birth=date(1990, 8, 15),
        preferred_language="en",
        consent_given=True,
    )
    db_session.add(patient)
    await db_session.commit()

    # Staff access with consent
    staff_res = await client.get(f"/api/patients/{patient.id}", headers=auth_header(staff_user))
    assert staff_res.status_code == 200

    # Admin audit access
    admin_res = await client.get(f"/api/patients/{patient.id}", headers=auth_header(admin_user))
    assert admin_res.status_code == 200
    assert admin_res.json()["id"] == str(patient.id)
