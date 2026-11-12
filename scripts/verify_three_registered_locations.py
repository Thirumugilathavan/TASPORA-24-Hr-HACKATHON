import asyncio
import time
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select
from app.models.village import Village
from app.services.facility_service import FacilityServiceHandler

DB_URL = "sqlite+aiosqlite:///carebridge.db"

LOCATIONS_TO_TEST = [
    {"name": "Muthupilli Alangulam", "state": "Tamil Nadu"},
    {"name": "Srirangam", "state": "Andhra Pradesh"},
    {"name": "Sidhauli", "state": "Uttar Pradesh"},
]

async def verify():
    engine = create_async_engine(DB_URL)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    results_per_location = {}

    async with async_session() as session:
        handler = FacilityServiceHandler(session)

        for loc in LOCATIONS_TO_TEST:
            print(f"\n==================================================================")
            print(f"TESTING LOCATION: {loc['name']} ({loc['state']})")
            print(f"==================================================================")

            # 1. Resolve registered location coordinates from database
            stmt = select(Village).where(
                Village.name.ilike(f"%{loc['name']}%"),
                Village.state.ilike(f"%{loc['state']}%")
            ).limit(1)
            res = await session.execute(stmt)
            village = res.scalar_one_or_none()

            assert village is not None, f"Village {loc['name']} not found in database!"
            assert village.latitude is not None and village.longitude is not None
            assert -90.0 <= village.latitude <= 90.0
            assert -180.0 <= village.longitude <= 180.0

            print(f"1. Coordinate Resolution:")
            print(f"   - Name:     {village.name}")
            print(f"   - District: {village.district}")
            print(f"   - State:    {village.state}")
            print(f"   - Lat/Lon:  {village.latitude:.4f}, {village.longitude:.4f}")

            # 2. Query nearby facilities using GeoJSON dataset
            t0 = time.time()
            nearby = await handler.get_nearby_facilities(
                village_id=village.id,
                radius_km=25.0,
                limit=10,
            )
            query_ms = (time.time() - t0) * 1000

            print(f"\n2. GeoJSON Dataset Query (took {query_ms:.2f} ms):")
            print(f"   - Total Matching Facilities within 25 km: {nearby.total}")
            print(f"   - Top {len(nearby.items)} Facilities Returned:")

            assert len(nearby.items) > 0, f"Expected nearby facilities for {village.name} within 25 km!"

            facilities_list = []
            distances = []
            types_found = set()

            for idx, f in enumerate(nearby.items):
                print(f"     #{idx+1}: [{f.distance_km:.2f} km] {f.name} ({f.facility_type}) - {f.address}")
                distances.append(f.distance_km)
                types_found.add(f.facility_type)
                facilities_list.append(f.name)
                # Verify directions URL
                assert f.directions_url is not None
                assert str(f.latitude) in f.directions_url
                assert str(f.longitude) in f.directions_url
                # Verify unverified_availability flag
                assert f.unverified_availability is True
                # Verify distance is within radius
                assert f.distance_km <= 25.0

            # 3. Confirm strictly sorted ascending (nearest first)
            print(f"\n3. Distance Sorting Verification:")
            assert distances == sorted(distances), "Facilities MUST be sorted strictly nearest-first!"
            print(f"   - Strictly sorted: {distances[0]} km <= ... <= {distances[-1]} km [PASSED]")

            # 4. Confirm variety of facility types (not restricted to a fixed CHC list)
            print(f"\n4. Facility Types in Results: {types_found}")
            # Ensure it is not just CHCs
            assert not (len(types_found) == 1 and "CHC" in types_found), "Must not return only CHCs!"

            results_per_location[loc["name"]] = {
                "village": f"{village.name}, {village.state}",
                "facilities": facilities_list,
                "first_dist": distances[0],
                "types": list(types_found),
            }

        # 5. Confirm changing registered location changes results completely
        print(f"\n==================================================================")
        print(f"5. LOCATION SENSITIVITY & INDEPENDENCE CHECK")
        print(f"==================================================================")
        names = list(results_per_location.keys())
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                loc_a = names[i]
                loc_b = names[j]
                facs_a = set(results_per_location[loc_a]["facilities"])
                facs_b = set(results_per_location[loc_b]["facilities"])
                overlap = facs_a.intersection(facs_b)
                print(f"Comparing {loc_a} vs {loc_b}: overlap = {len(overlap)} facilities")
                assert len(overlap) == 0, f"Different locations should return distinct nearby facilities! Overlap: {overlap}"
        print("CONFIRMED: Results are 100% geographically unique to each registered location! [PASSED]")

        # 6. Test edge cases: invalid coordinates, missing location, empty radius
        print(f"\n==================================================================")
        print(f"6. EDGE CASE & ERROR HANDLING CHECKS")
        print(f"==================================================================")
        # Missing all params
        try:
            await handler.get_nearby_facilities()
            assert False, "Should raise ValueError when no location provided"
        except ValueError as e:
            print(f"Missing location handled gracefully: {e} [PASSED]")

        # Invalid coordinates
        try:
            await handler.get_nearby_facilities(lat=95.0, lon=78.0)
            assert False, "Should raise ValueError for invalid lat"
        except ValueError as e:
            print(f"Invalid coordinate handled gracefully: {e} [PASSED]")

        # Out-of-bounds radius
        try:
            await handler.get_nearby_facilities(lat=10.0, lon=78.0, radius_km=-5.0)
            assert False, "Should raise ValueError for negative radius"
        except ValueError as e:
            print(f"Negative radius handled gracefully: {e} [PASSED]")

        # Small radius in ocean / empty area
        empty_res = await handler.get_nearby_facilities(lat=5.0, lon=75.0, radius_km=5.0)
        assert empty_res.total == 0
        assert len(empty_res.items) == 0
        print(f"Empty results handled gracefully (total=0, items=[]) [PASSED]")

    await engine.dispose()
    print(f"\nALL 3-LOCATION VERIFICATIONS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(verify())
