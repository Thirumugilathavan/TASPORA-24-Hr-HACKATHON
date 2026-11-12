import pytest
from httpx import AsyncClient
import uuid


@pytest.mark.asyncio
async def test_get_facilities_list_format(client: AsyncClient, seed_data: dict):
    """Verify standard list format: {'items': [...], 'total': n}."""
    response = await client.get("/api/facilities")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] == 3
    assert len(data["items"]) == 3
    first = data["items"][0]
    assert "id" in first
    assert "name" in first
    assert "facility_type" in first
    assert "village_id" in first
    assert "latitude" in first
    assert "longitude" in first


@pytest.mark.asyncio
async def test_filter_facilities_by_village(client: AsyncClient, seed_data: dict):
    """Verify filtering facilities by village_id."""
    v1_id = seed_data["villages"][0].id
    response = await client.get(f"/api/facilities?village_id={v1_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    for item in data["items"]:
        assert item["village_id"] == str(v1_id)


@pytest.mark.asyncio
async def test_filter_facilities_by_type(client: AsyncClient, seed_data: dict):
    """Verify filtering facilities by facility_type."""
    response = await client.get("/api/facilities?facility_type=CHC")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "CHC Sitapur"


@pytest.mark.asyncio
async def test_filter_facilities_by_service(client: AsyncClient, seed_data: dict):
    """Verify filtering facilities by offered service name."""
    response = await client.get("/api/facilities?service=Immunization")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2

    response_surg = await client.get("/api/facilities?service=Surgery")
    assert response_surg.status_code == 200
    data_surg = response_surg.json()
    assert data_surg["total"] == 1
    assert data_surg["items"][0]["name"] == "City General Hospital"


@pytest.mark.asyncio
async def test_get_facility_detail_with_services_and_doctors(client: AsyncClient, seed_data: dict):
    """Verify detailed response includes services[] and doctors[]."""
    fac_1 = seed_data["facilities"][0]
    response = await client.get(f"/api/facilities/{fac_1.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(fac_1.id)
    assert data["name"] == "PHC Rampur"
    assert "services" in data
    assert "doctors" in data
    assert len(data["services"]) == 2
    service_names = [s["service_name"] for s in data["services"]]
    assert "Maternal Care" in service_names
    assert "Immunization" in service_names
    assert len(data["doctors"]) == 1
    assert data["doctors"][0]["name"] == "Dr. Anita Sharma"


@pytest.mark.asyncio
async def test_get_facility_not_found(client: AsyncClient, seed_data: dict):
    """Verify 404 error follows standard format: {'error': {'code': '...', 'message': '...'}}."""
    random_id = uuid.uuid4()
    response = await client.get(f"/api/facilities/{random_id}")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_create_facility(client: AsyncClient, seed_data: dict):
    """Verify facility creation by authorized staff."""
    staff_headers = seed_data["headers"]["staff"]
    payload = {
        "name": "Sub-Centre Anandpur",
        "facility_type": "PHC",
        "address": "Village Square, Anandpur",
        "village_id": str(seed_data["villages"][0].id),
        "latitude": 12.9900,
        "longitude": 77.6100,
        "contact_details": {"phone": "9998887776"},
        "services": ["First Aid", "Blood Pressure Check"],
    }
    response = await client.post("/api/facilities", json=payload, headers=staff_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Sub-Centre Anandpur"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_facility_patient_forbidden(client: AsyncClient, seed_data: dict):
    """Verify patients cannot create facilities (HTTP 403 Forbidden)."""
    patient_headers = seed_data["headers"]["patient"]
    payload = {
        "name": "Unauthorized Clinic",
        "facility_type": "PHC",
        "address": "Some Street",
        "village_id": str(seed_data["villages"][0].id),
        "latitude": 12.9900,
        "longitude": 77.6100,
    }
    response = await client.post("/api/facilities", json=payload, headers=patient_headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_create_facility_validation_invalid_coordinates(client: AsyncClient, seed_data: dict):
    """Verify invalid coordinates (>90 lat) fail with 422."""
    staff_headers = seed_data["headers"]["staff"]
    payload = {
        "name": "Invalid Coords PHC",
        "facility_type": "PHC",
        "address": "Some Street",
        "village_id": str(seed_data["villages"][0].id),
        "latitude": 95.0,  # Invalid latitude
        "longitude": 77.6100,
    }
    response = await client.post("/api/facilities", json=payload, headers=staff_headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_facility_validation_invalid_type(client: AsyncClient, seed_data: dict):
    """Verify invalid facility type fails with 422."""
    staff_headers = seed_data["headers"]["staff"]
    payload = {
        "name": "Invalid Type Facility",
        "facility_type": "SUPERMARKET",  # Invalid type
        "address": "Some Street",
        "village_id": str(seed_data["villages"][0].id),
        "latitude": 12.9900,
        "longitude": 77.6100,
    }
    response = await client.post("/api/facilities", json=payload, headers=staff_headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_facility_nonexistent_village_returns_404(client: AsyncClient, seed_data: dict):
    """Verify 404 when referencing a non-existent village."""
    staff_headers = seed_data["headers"]["staff"]
    payload = {
        "name": "Missing Village PHC",
        "facility_type": "PHC",
        "address": "Some Street",
        "village_id": str(uuid.uuid4()),
        "latitude": 12.9900,
        "longitude": 77.6100,
    }
    response = await client.post("/api/facilities", json=payload, headers=staff_headers)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
