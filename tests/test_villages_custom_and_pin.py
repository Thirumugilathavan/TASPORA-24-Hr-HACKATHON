import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_custom_village_creation(client: AsyncClient):
    payload = {
        "name": "Chitlapakkam South",
        "district": "Chengalpattu",
        "state": "Tamil Nadu",
        "pincode": "600064",
    }
    res = await client.post("/api/villages/custom", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Chitlapakkam South"
    assert data["district"] == "Chengalpattu"
    assert data["latitude"] is not None
    assert data["longitude"] is not None
    assert data["is_synthetic"] is True


@pytest.mark.asyncio
async def test_pin_code_search_resolution(client: AsyncClient):
    res = await client.get("/api/villages/search?q=637211")
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) > 0
    assert any("637211" in v["name"] or "Tiruchengode" in v["name"] for v in data["items"])
