"""
Seed and synchronize official Tamil Nadu health camp sources.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import AsyncSessionLocal
from app.services.camp_service import CampService
from app.services.camp_collector_service import CampCollectorService

async def main():
    async with AsyncSessionLocal() as session:
        print("1. Initializing official Tamil Nadu sources...")
        created = await CampCollectorService.initialize_default_sources(session)
        print(f"Default sources initialized (newly added: {created})")

        print("2. Executing collection sync across active official sources...")
        sync_result = await CampService.sync_all_sources(session)
        print("Sync completed!")
        print(f"Sources processed: {sync_result['sources_processed']}")
        print(f"Sources succeeded: {sync_result['sources_succeeded']}")
        print(f"Total new events: {sync_result['total_new_events']}")
        for d in sync_result['details']:
            print(f"  - {d['source']}: {d['status']} (new: {d['new_events']})")

        print("\n3. Querying statewide district coverage...")
        coverage = await CampService.get_district_coverage(session)
        print(f"Total Districts Monitored: {coverage.total_districts}")
        print(f"Districts with Events: {coverage.districts_with_events_count}")
        print(f"Total Verified Camps: {coverage.total_verified_camps}")
        print(f"Monitored Sources Count: {coverage.monitored_sources_count}")

        print("\n4. Sample Upcoming Camps:")
        camps = await CampService.get_camps(session=session, limit=5)
        for c in camps.items:
            print(f"  • [{c.district}] {c.title}")
            print(f"    Date: {c.start_date.strftime('%Y-%m-%d %H:%M')} | Category: {c.category} | Venue: {c.venue_name}")
            print(f"    Services: {', '.join(c.services_offered[:3])}...")
            print(f"    Source: {c.source_org} ({c.source_url})")

if __name__ == "__main__":
    asyncio.run(main())
