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
    """Verify creating a catalogue entry."""
    payload = {
        "name": "Ibuprofen",
        "generic_name": "Ibuprofen",
        "strength": "400 mg",
        "dosage_form": "Tablet",
    }
    response = await client.post("/api/medicines", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Ibuprofen"
    assert "id" in data
