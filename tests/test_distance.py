import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.distance_service import DistanceService, haversine_km


def test_haversine_known_coordinates():
    """Test Haversine distance calculation between Bangalore and Mysore."""
    dist = haversine_km(12.9716, 77.5946, 12.2958, 76.6394)
    assert 125 <= round(dist) <= 130


@pytest.mark.asyncio
async def test_distance_service_with_seeded_data(db_session: AsyncSession, seed_data: dict):
    """Test DistanceService calculation between Rampur village and CHC Sitapur (~12 km)."""
    service = DistanceService(db_session)
    v1 = seed_data["villages"][0]
    f2 = seed_data["facilities"][1]

    dist = await service.calculate_distance(v1.id, f2.id)
    assert isinstance(dist, int)
    assert 10 <= dist <= 14


@pytest.mark.asyncio
async def test_distance_missing_village_or_facility(db_session: AsyncSession, seed_data: dict):
    """Verify ValueError when village or facility does not exist."""
    service = DistanceService(db_session)
    v1 = seed_data["villages"][0]
    f1 = seed_data["facilities"][0]

    with pytest.raises(ValueError, match="not found"):
        await service.calculate_distance(uuid.uuid4(), f1.id)

    with pytest.raises(ValueError, match="not found"):
        await service.calculate_distance(v1.id, uuid.uuid4())
