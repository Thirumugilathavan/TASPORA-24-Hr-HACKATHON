import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_medicines(client: AsyncClient, seed_data: dict):
    """Verify standard list format: {'items': [...], 'total': n}."""
    response = await client.get("/api/medicines")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] == 3
    assert len(data["items"]) == 3


@pytest.mark.asyncio
async def test_search_medicine_by_name(client: AsyncClient, seed_data: dict):
    """Verify search by brand name."""
    response = await client.get("/api/medicines?q=para")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Paracetamol"


@pytest.mark.asyncio
async def test_search_medicine_by_generic_name(client: AsyncClient, seed_data: dict):
    """Verify search by generic name."""
    response = await client.get("/api/medicines?q=Acetaminophen")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Paracetamol"
    assert data["items"][0]["generic_name"] == "Acetaminophen"


@pytest.mark.asyncio
async def test_search_medicine_empty_result(client: AsyncClient, seed_data: dict):
    """Verify search with no matches returns empty items list."""
    response = await client.get("/api/medicines?q=NonExistentDrugXYZ")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_catalogue_metadata_only(client: AsyncClient, seed_data: dict):
    """Verify medicine returns only catalogue metadata, not dosage or prescription advice."""
    response = await client.get("/api/medicines?q=Amoxicillin")
    assert response.status_code == 200
    data = response.json()
    med = data["items"][0]
    assert "strength" in med
    assert "dosage_form" in med
    assert "prescription" not in med
    assert "dosage_recommendation" not in med


@pytest.mark.asyncio
async def test_create_medicine(client: AsyncClient, seed_data: dict):
    """Verify creating a catalogue entry by authorized staff."""
    staff_headers = seed_data["headers"]["staff"]
    payload = {
        "name": "Ibuprofen",
        "generic_name": "Ibuprofen",
        "strength": "400 mg",
        "dosage_form": "Tablet",
    }
    response = await client.post("/api/medicines", json=payload, headers=staff_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Ibuprofen"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_medicine_patient_forbidden(client: AsyncClient, seed_data: dict):
    """Verify patients cannot add medicines to catalogue (HTTP 403 Forbidden)."""
    patient_headers = seed_data["headers"]["patient"]
    payload = {
        "name": "Unauthorized Medicine",
        "generic_name": "Compound X",
    }
    response = await client.post("/api/medicines", json=payload, headers=patient_headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_create_medicine_empty_name_fails(client: AsyncClient, seed_data: dict):
    """Verify empty medicine name fails with 422 Unprocessable Entity."""
    staff_headers = seed_data["headers"]["staff"]
    payload = {
        "name": "   ",
        "generic_name": "Blank",
    }
    response = await client.post("/api/medicines", json=payload, headers=staff_headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_duplicate_medicine_safe_handling(client: AsyncClient, seed_data: dict):
    """Verify duplicate medicine entry is safely handled idempotently."""
    staff_headers = seed_data["headers"]["staff"]
    payload = {
        "name": "Cetirizine 10mg",
        "generic_name": "Cetirizine",
        "strength": "10 mg",
        "dosage_form": "Tablet",
    }
    r1 = await client.post("/api/medicines", json=payload, headers=staff_headers)
    assert r1.status_code == 201
    id1 = r1.json()["id"]

    r2 = await client.post("/api/medicines", json=payload, headers=staff_headers)
    assert r2.status_code == 201
    id2 = r2.json()["id"]
    assert id1 == id2
