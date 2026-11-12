"""
Pytest suite for Statewide Tamil Nadu Health Camp & Follow-up Discovery.
Tests canonical district registry, deduplication, collectors, spatial proximity sorting,
coverage analytics, API endpoints, and notification dispatch.
"""

from datetime import datetime, timezone, timedelta
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.health_camp import HealthCamp, HealthCampSource, UserCampPreference
from app.models.user import User
from app.services.tn_districts import (
    get_all_districts,
    normalize_tn_district,
    get_district_metadata,
    TN_DISTRICTS,
)
from app.services.camp_collector_service import (
    CampCollectorService,
    generate_camp_dedup_hash,
)
from app.services.camp_service import (
    CampService,
    calculate_haversine_distance_km,
)


def test_canonical_districts_registry():
    """Verify all 38 revenue districts of Tamil Nadu are mapped with metadata."""
    districts = get_all_districts()
    assert len(districts) == 38
    assert len(TN_DISTRICTS) == 38

    # Verify key districts exist
    sample_districts = ["Chennai", "Coimbatore", "Madurai", "Salem", "Tiruchirappalli", "Nilgiris", "Kanniyakumari"]
    for d in sample_districts:
        meta = get_district_metadata(d)
        assert meta is not None
        assert "latitude" in meta
        assert "longitude" in meta
        assert "portal_url" in meta
        assert "name_ta" in meta


def test_district_alias_normalization():
    """Test standardizing misspelled, historic, or colloquial district names."""
    test_cases = [
        ("Trichy", "Tiruchirappalli"),
        ("Tiruchchirappli", "Tiruchirappalli"),
        ("Tiruchi", "Tiruchirappalli"),
        ("Tuticorin", "Thoothukudi"),
        ("Thootukudi", "Thoothukudi"),
        ("Kovai", "Coimbatore"),
        ("Madras", "Chennai"),
        ("Ooty", "Nilgiris"),
        ("The Nilgiris", "Nilgiris"),
        ("Ramnad", "Ramanathapuram"),
        ("Villupuram", "Viluppuram"),
        ("Kanyakumari", "Kanniyakumari"),
        ("Tirupattur", "Tirupathur"),
        ("Dharampuri", "Dharmapuri"),
    ]
    for raw, expected in test_cases:
        assert normalize_tn_district(raw) == expected, f"Failed for {raw}"


def test_camp_dedup_hash():
    """Verify deterministic deduplication hash generation."""
    date1 = datetime(2026, 11, 20, 9, 0, tzinfo=timezone.utc)
    h1 = generate_camp_dedup_hash("Salem", "Mobile Medical Outreach Camp", date1, "Panchayat Community Hall")
    h2 = generate_camp_dedup_hash("salem", "Mobile Medical Outreach Camp", date1, "Panchayat Community Hall")
    h3 = generate_camp_dedup_hash("Salem", "Mobile Medical Outreach Camp", date1, "Different Venue")

    assert h1 == h2, "Hash must be case and whitespace invariant for district"
    assert h1 != h3, "Different venue must yield distinct hash"


def test_haversine_distance():
    """Verify great circle distance calculation."""
    # Salem (11.6643, 78.1460) to Erode (11.3410, 77.7172) is approx 58-62 km
    dist = calculate_haversine_distance_km(11.6643, 78.1460, 11.3410, 77.7172)
    assert 55.0 <= dist <= 65.0

    # Same location is 0.0
    dist_zero = calculate_haversine_distance_km(11.6643, 78.1460, 11.6643, 78.1460)
    assert dist_zero == 0.0


@pytest.mark.asyncio
async def test_camps_api_list_and_coverage(client: AsyncClient, db_session: AsyncSession):
    """Test GET /api/camps and GET /api/camps/coverage endpoints."""
    # Seed default sources in in-memory test db
    await CampCollectorService.initialize_default_sources(db_session)

    # 1. Test Coverage Endpoint
    cov_resp = await client.get("/api/camps/coverage")
    assert cov_resp.status_code == 200
    cov_data = cov_resp.json()
    assert cov_data["total_districts"] == 38
    assert "districts" in cov_data
    assert len(cov_data["districts"]) == 38

    # 2. Test Districts List Endpoint
    dist_resp = await client.get("/api/camps/districts")
    assert dist_resp.status_code == 200
    dist_list = dist_resp.json()
    assert len(dist_list) == 38

    # 3. Test Sources Endpoint
    src_resp = await client.get("/api/camps/sources")
    assert src_resp.status_code == 200
    sources = src_resp.json()
    assert len(sources) >= 1

    # 4. Test Camps List Endpoint
    camps_resp = await client.get("/api/camps")
    assert camps_resp.status_code == 200
    camps_data = camps_resp.json()
    assert "items" in camps_data
    assert "total" in camps_data


@pytest.mark.asyncio
async def test_camps_spatial_proximity_query(client: AsyncClient, db_session: AsyncSession):
    """Test querying camps with spatial user_lat and user_lng coordinates."""
    # Seed a camp directly in db_session
    now = datetime.now(timezone.utc)
    camp1 = HealthCamp(
        title="Test Camp Near Salem",
        description="Test description",
        category="GENERAL_HEALTH_CAMP",
        organizing_dept="DPH Salem",
        start_date=now + timedelta(days=2),
        venue_name="Salem Venue",
        full_address="Salem",
        district="Salem",
        latitude=11.6650,
        longitude=78.1470,
        services_offered=["General Checkup"],
        source_org="NHM TN",
        source_url="https://nhm.tn.gov.in",
        discovered_at=now,
        last_checked_at=now,
        verification_status="VERIFIED",
        event_status="UPCOMING",
        provenance={"test": True},
        dedup_hash="test_salem_hash_1",
    )
    camp2 = HealthCamp(
        title="Test Camp In Madurai",
        description="Test description",
        category="GENERAL_HEALTH_CAMP",
        organizing_dept="DPH Madurai",
        start_date=now + timedelta(days=2),
        venue_name="Madurai Venue",
        full_address="Madurai",
        district="Madurai",
        latitude=9.9252,
        longitude=78.1198,
        services_offered=["General Checkup"],
        source_org="NHM TN",
        source_url="https://nhm.tn.gov.in",
        discovered_at=now,
        last_checked_at=now,
        verification_status="VERIFIED",
        event_status="UPCOMING",
        provenance={"test": True},
        dedup_hash="test_madurai_hash_2",
    )
    db_session.add(camp1)
    db_session.add(camp2)
    await db_session.commit()

    # Salem coordinates: camp1 should be ~0.1 km, camp2 should be ~190 km
    resp = await client.get("/api/camps?user_lat=11.6643&user_lng=78.1460&limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) >= 2
    assert data["items"][0]["district"] == "Salem"
    assert data["items"][0]["distance_km"] < data["items"][1]["distance_km"]


@pytest.mark.asyncio
async def test_camp_single_detail_and_404(client: AsyncClient, db_session: AsyncSession):
    """Test retrieving a single camp and 404 behavior."""
    # Invalid UUID
    random_id = uuid.uuid4()
    resp = await client.get(f"/api/camps/{random_id}")
    assert resp.status_code == 404

    now = datetime.now(timezone.utc)
    camp = HealthCamp(
        title="Test Detail Camp",
        description="Detailed description for testing",
        category="NCD_SCREENING",
        organizing_dept="NHM TN",
        start_date=now + timedelta(days=1),
        venue_name="Test PHC",
        full_address="Erode District",
        district="Erode",
        latitude=11.3410,
        longitude=77.7172,
        services_offered=["Blood Pressure", "Blood Glucose"],
        source_org="NHM Tamil Nadu",
        source_url="https://nhm.tn.gov.in/test",
        discovered_at=now,
        last_checked_at=now,
        verification_status="VERIFIED",
        event_status="UPCOMING",
        provenance={"official_notice": "Ref 2026/DHS/01"},
        dedup_hash="test_detail_hash_erode",
    )
    db_session.add(camp)
    await db_session.commit()
    await db_session.refresh(camp)

    detail_resp = await client.get(f"/api/camps/{camp.id}")
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()
    assert detail_data["id"] == str(camp.id)
    assert detail_data["title"] == "Test Detail Camp"
    assert "Blood Pressure" in detail_data["services_offered"]
    assert detail_data["provenance"]["official_notice"] == "Ref 2026/DHS/01"
