import asyncio
import time
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select
from app.models.village import Village
from app.services.facility_service import FacilityServiceHandler

DB_URL = "sqlite+aiosqlite:///carebridge.db"

async def test_live():
    engine = create_async_engine(DB_URL)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with async_session() as session:
        # Find a real village (e.g., in Tamil Nadu, Alangulam or Tirunelveli or similar)
        stmt = select(Village).where(Village.name.ilike("%Alangulam%")).limit(1)
        res = await session.execute(stmt)
        village = res.scalar_one_or_none()
        if not village:
            stmt = select(Village).limit(1)
            res = await session.execute(stmt)
            village = res.scalar_one_or_none()

        print(f"Testing with Village: {village.name}, District: {village.district}, State: {village.state}")
        print(f"Coordinates: lat={village.latitude}, lon={village.longitude}")

        handler = FacilityServiceHandler(session)

        # 1. Test distance sorting by village_id
        t0 = time.time()
        result = await handler.get_nearby_facilities(village_id=village.id, radius_km=15.0, limit=10)
        elapsed = time.time() - t0

        print(f"\n--- Nearby Facilities within 15 km (Found {result.total} facilities in {elapsed*1000:.2f} ms) ---")
        print(f"Resolved Location: {result.resolved_location['label']}")
        for idx, item in enumerate(result.items):
            print(f"#{idx+1}: [{item.distance_km:.2f} km] {item.name} ({item.facility_type}) - {item.address}")
            assert item.directions_url is not None
            assert item.unverified_availability is True

        # Verify strict ascending order
        distances = [item.distance_km for item in result.items]
        assert distances == sorted(distances), "Facilities must be strictly sorted by ascending distance!"
        print("\nSUCCESS: All returned facilities are strictly sorted nearest-first!")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_live())
