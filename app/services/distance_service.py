import math
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.facility import Facility
from app.models.village import Village


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points using the Haversine formula.

    CRITICAL NOTICE:
    This computes straight-line (as the crow flies) distance, NOT actual road network travel
    distance. In rural terrains, travel distance and time may be significantly higher due to
    terrain, unpaved roads, and geographical detours.
    """
    r = 6371.0  # Earth radius in kilometers

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


class DistanceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def calculate_distance(self, village_id: UUID, facility_id: UUID) -> int:
        """Calculates straight-line distance in whole kilometres between a village and facility."""
        # Lookup facility
        f_stmt = select(Facility).where(Facility.id == facility_id)
        f_res = await self.db.execute(f_stmt)
        facility = f_res.scalar_one_or_none()
        if not facility:
            raise ValueError(f"Facility with id {facility_id} not found")

        # Lookup village
        v_stmt = select(Village).where(Village.id == village_id)
        v_res = await self.db.execute(v_stmt)
        village = v_res.scalar_one_or_none()
        if not village:
            raise ValueError(f"Village with id {village_id} not found")

        dist = haversine_km(village.latitude, village.longitude, facility.latitude, facility.longitude)
        return round(dist)
