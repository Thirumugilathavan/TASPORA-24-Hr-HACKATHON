import pytest
from httpx import AsyncClient
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.village import Village


@pytest.fixture
async def search_test_villages(db_session: AsyncSession):
    """Seed test villages across multiple states and districts for isolated testing."""
    v1 = Village(
        name="Rampur",
        district="Sitapur",
        subdistrict="Laharpur",
        state="Uttar Pradesh",
        latitude=27.5684,
        longitude=80.6791,
        is_synthetic=True,
    )
    v2 = Village(
        name="Bilaspur",
        district="Bilaspur",
        subdistrict="Bilaspur",
        state="Chhattisgarh",
        latitude=22.0797,
        longitude=82.1409,
        is_synthetic=True,
    )
    v3 = Village(
        name="Bilaspur",
        district="Bilaspur",
        subdistrict="Sadar",
        state="Himachal Pradesh",
        latitude=31.3260,
        longitude=76.7600,
        is_synthetic=True,
    )
    v4 = Village(
        name="Tiruchirappalli",
        district="Tiruchirappalli",
        subdistrict="Tiruchirappalli",
        state="Tamil Nadu",
        latitude=10.7905,
        longitude=78.7047,
        is_synthetic=True,
    )
    db_session.add_all([v1, v2, v3, v4])
    await db_session.commit()
    return [v1, v2, v3, v4]


@pytest.mark.asyncio
async def test_search_villages_exact_and_prefix(client: AsyncClient, search_test_villages):
    """Test that search returns exact and prefix matches with ranking."""
    response = await client.get("/api/villages/search?q=Rampur&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) > 0
    assert data["items"][0]["name"] == "Rampur"
    assert data["items"][0]["district"] == "Sitapur"
    assert data["items"][0]["state"] == "Uttar Pradesh"


@pytest.mark.asyncio
async def test_search_villages_filters(client: AsyncClient, search_test_villages):
    """Test filtering by state and district."""
    response = await client.get("/api/villages/search?q=Bilaspur&state=Chhattisgarh&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["state"] == "Chhattisgarh"

    hp_response = await client.get("/api/villages/search?q=Bilaspur&state=Himachal Pradesh&limit=5")
    assert hp_response.status_code == 200
    hp_data = hp_response.json()
    assert len(hp_data["items"]) == 1
    assert hp_data["items"][0]["state"] == "Himachal Pradesh"


@pytest.mark.asyncio
async def test_search_villages_hierarchy_distinction(client: AsyncClient, search_test_villages):
    """Test that duplicate village names contain administrative hierarchy."""
    response = await client.get("/api/villages/search?q=Bilaspur&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 2
    states = {item["state"] for item in data["items"]}
    assert "Chhattisgarh" in states
    assert "Himachal Pradesh" in states


@pytest.mark.asyncio
async def test_search_villages_spelling_typo_tolerance(client: AsyncClient, search_test_villages):
    """Test that minor typing variations return relevant suggestions."""
    response = await client.get("/api/villages/search?q=Ramppur&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) > 0
    assert data["items"][0]["name"] == "Rampur"


@pytest.mark.asyncio
async def test_search_villages_empty_query_fails_validation(client: AsyncClient):
    """Test that empty query returns 422 Unprocessable Entity."""
    response = await client.get("/api/villages/search?q=")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_patient_with_searched_location(client: AsyncClient, search_test_villages):
    """Test full registration journey using a village selected from search."""
    search_res = await client.get("/api/villages/search?q=Tiruchirappalli&limit=1")
    assert search_res.status_code == 200
    village_id = search_res.json()["items"][0]["id"]

    phone = "9876543299"
    reg_payload = {
        "name": "Nationwide Test Patient",
        "phone": phone,
        "password": "SecurePassword123!",
        "role": "PATIENT",
    }
    auth_res = await client.post("/api/auth/register", json=reg_payload)
    assert auth_res.status_code == 201

    login_res = await client.post("/api/auth/login", json={"phone": phone, "password": "SecurePassword123!"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    pat_payload = {
        "village_id": village_id,
        "date_of_birth": "1992-05-15",
        "preferred_language": "ta",
        "consent_given": True,
        "emergency_contact_phone": "9876543211",
    }
    pat_res = await client.post("/api/patients", json=pat_payload, headers=headers)
    assert pat_res.status_code == 201
    pat_data = pat_res.json()
    assert pat_data["village_id"] == village_id
