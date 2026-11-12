import uuid
import pytest
from httpx import AsyncClient
from app.models.patient import Patient
from datetime import date


@pytest.mark.asyncio
async def test_nearby_facilities_distance_sorting(client: AsyncClient, seed_data: dict):
    """Verify that facilities are strictly sorted nearest-first (ascending geographic distance)."""
    # Coordinates of Rampur village center (12.9716, 77.5946)
    lat, lon = 12.9716, 77.5946
    response = await client.get(f"/api/facilities/nearby?latitude={lat}&longitude={lon}&radius_km=25")
    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert "total" in data
    assert "resolved_location" in data
    assert data["radius_km"] == 25.0

    items = data["items"]
    assert len(items) == 3

    # Closest facility must be PHC Rampur, followed by City General Hospital, then CHC Sitapur
    assert items[0]["name"] == "PHC Rampur"
    assert items[1]["name"] == "City General Hospital"
    assert items[2]["name"] == "CHC Sitapur"

    # Strictly ascending distance
    distances = [item["distance_km"] for item in items]
    assert distances == sorted(distances)
    assert distances[0] < distances[1] < distances[2]

    # Directions URL and availability flag
    for item in items:
        assert item["unverified_availability"] is True
        assert item["directions_url"].startswith("https://www.google.com/maps/dir/?api=1&destination=")


@pytest.mark.asyncio
async def test_nearby_facilities_radius_filtering(client: AsyncClient, seed_data: dict):
    """Verify that facilities beyond radius_km are strictly excluded."""
    # Rampur coordinates: CHC Sitapur is ~12.2 km away, PHC Rampur is ~0.06 km, Hospital is ~1.1 km
    lat, lon = 12.9716, 77.5946
    response = await client.get(f"/api/facilities/nearby?latitude={lat}&longitude={lon}&radius_km=5.0")
    assert response.status_code == 200
    data = response.json()

    items = data["items"]
    assert len(items) == 2
    for item in items:
        assert item["distance_km"] <= 5.0
        assert item["name"] in ["PHC Rampur", "City General Hospital"]

    # CHC Sitapur must not be in results
    names = [item["name"] for item in items]
    assert "CHC Sitapur" not in names


@pytest.mark.asyncio
async def test_nearby_facilities_resolution_by_village_id(client: AsyncClient, seed_data: dict):
    """Verify location resolution via village_id."""
    v1 = seed_data["villages"][0]
    response = await client.get(f"/api/facilities/nearby?village_id={v1.id}&radius_km=25")
    assert response.status_code == 200
    data = response.json()

    assert data["resolved_location"]["source"] == "village"
    assert data["resolved_location"]["village_id"] == str(v1.id)
    assert len(data["items"]) == 3
    assert data["items"][0]["name"] == "PHC Rampur"


@pytest.mark.asyncio
async def test_nearby_facilities_resolution_by_patient_id(
    client: AsyncClient, seed_data: dict, db_session
):
    """Verify location resolution via patient profile and village linkage."""
    v1 = seed_data["villages"][0]
    p_user = seed_data["users"]["patient"]

    patient = Patient(
        id=uuid.uuid4(),
        user_id=p_user.id,
        village_id=v1.id,
        date_of_birth=date(1990, 1, 1),
        preferred_language="en",
    )
    db_session.add(patient)
    await db_session.flush()

    response = await client.get(f"/api/facilities/nearby?patient_id={patient.id}&radius_km=25")
    assert response.status_code == 200
    data = response.json()

    assert data["resolved_location"]["source"] == "patient_village"
    assert data["items"][0]["name"] == "PHC Rampur"


@pytest.mark.asyncio
async def test_nearby_facilities_authenticated_resolution(
    client: AsyncClient, seed_data: dict, db_session
):
    """Verify authenticated patient resolves location automatically without query params."""
    v1 = seed_data["villages"][0]
    p_user = seed_data["users"]["patient"]
    token = seed_data["tokens"]["patient"]

    patient = Patient(
        id=uuid.uuid4(),
        user_id=p_user.id,
        village_id=v1.id,
        date_of_birth=date(1990, 1, 1),
        preferred_language="en",
    )
    db_session.add(patient)
    await db_session.flush()

    response = await client.get(
        "/api/facilities/nearby?radius_km=20",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["resolved_location"]["source"] == "patient_village"
    assert len(data["items"]) == 3


@pytest.mark.asyncio
async def test_nearby_facilities_type_filter(client: AsyncClient, seed_data: dict):
    """Verify filtering nearby results by facility_type."""
    lat, lon = 12.9716, 77.5946
    # Filter for CHC only
    response = await client.get(f"/api/facilities/nearby?latitude={lat}&longitude={lon}&radius_km=25&facility_type=CHC")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["facility_type"] == "CHC"
    assert data["items"][0]["name"] == "CHC Sitapur"

    # Filter for HOSPITAL only
    h_res = await client.get(f"/api/facilities/nearby?latitude={lat}&longitude={lon}&radius_km=25&facility_type=HOSPITAL")
    assert h_res.status_code == 200
    h_data = h_res.json()
    assert len(h_data["items"]) == 1
    assert h_data["items"][0]["facility_type"] == "HOSPITAL"
    assert h_data["items"][0]["name"] == "City General Hospital"


@pytest.mark.asyncio
async def test_nearby_facilities_validation_errors(client: AsyncClient):
    """Verify HTTP error codes on invalid query parameters."""
    # 1. Missing all location parameters unauthenticated -> 400
    r1 = await client.get("/api/facilities/nearby")
    assert r1.status_code == 400
    assert r1.json()["error"]["code"] == "LOCATION_REQUIRED"

    # 2. Invalid latitude > 90 -> 422
    r2 = await client.get("/api/facilities/nearby?latitude=95.0&longitude=77.0")
    assert r2.status_code == 422

    # 3. Invalid longitude > 180 -> 422
    r3 = await client.get("/api/facilities/nearby?latitude=12.0&longitude=190.0")
    assert r3.status_code == 422

    # 4. Invalid radius <= 0 -> 422
    r4 = await client.get("/api/facilities/nearby?latitude=12.0&longitude=77.0&radius_km=-5")
    assert r4.status_code == 422

    # 5. Non-existent village_id -> 404
    non_existent = uuid.uuid4()
    r5 = await client.get(f"/api/facilities/nearby?village_id={non_existent}")
    assert r5.status_code == 404


@pytest.mark.asyncio
async def test_healthcare_facilities_alias_endpoint(client: AsyncClient, seed_data: dict):
    """Verify that the /api/healthcare-facilities/nearby alias operates identically."""
    lat, lon = 12.9716, 77.5946
    response = await client.get(f"/api/healthcare-facilities/nearby?latitude={lat}&longitude={lon}&radius_km=25")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 3
    assert data["items"][0]["name"] == "PHC Rampur"
