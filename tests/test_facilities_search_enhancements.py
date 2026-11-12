import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_facility_search_with_ownership_and_distance(client: AsyncClient, seed_data: dict):
    # Search around Rampur seed coordinates (12.9716, 77.5946)
    res = await client.get(
        "/api/facilities/nearby",
        params={
            "latitude": 12.9716,
            "longitude": 77.5946,
            "radius_km": 25.0,
            "ownership": "Government",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] > 0
    # Strict ascending distance check
    distances = [item["distance_km"] for item in data["items"]]
    assert distances == sorted(distances)

    # Check facility details
    for item in data["items"]:
        assert "name" in item
        assert "facility_type" in item
        assert "distance_km" in item
        assert "directions_url" in item


@pytest.mark.asyncio
async def test_facility_search_auto_expansion(client: AsyncClient, seed_data: dict):
    # Coordinates where CHC Sitapur is ~12.2 km away. With radius 0.5km, auto_expand should expand to 25km.
    res = await client.get(
        "/api/facilities/nearby",
        params={
            "latitude": 13.0000,
            "longitude": 77.5000,
            "radius_km": 0.5,
            "auto_expand": "true",
        },
    )
    assert res.status_code == 200
    data = res.json()
    # If expanded, is_expanded should be True and total > 0
    assert data["resolved_location"]["is_expanded"] is True
    assert data["radius_km"] > 0.5
    assert data["total"] > 0
