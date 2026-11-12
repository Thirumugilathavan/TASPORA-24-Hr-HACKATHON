from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete

from app.models.stock import StockReport
from app.schemas.shared import AvailabilityLabel, AvailabilityStatus, SourceType
from app.services.availability_service import AvailabilityService


@pytest.mark.asyncio
async def test_patient_report_never_modifies_stock_probability(db_session: AsyncSession, seed_data: dict):
    """Mandatory Rule 2: Patient feedback must never directly modify medicine stock probability.
    Initial state: prior p = 0.5.
    Patient submits OUT report: p must remain 0.5!
    Patient submits IN_STOCK report: p must remain 0.5!
    """
    fac = seed_data["facilities"][0]
    med = seed_data["medicines"][0]
    service = AvailabilityService(db_session)

    # 1. Baseline: No reports
    p_init, conf_init, label_init, count_init, _ = await service.calculate_belief(fac.id, med.id)
    assert p_init == 0.5
    assert conf_init == 0.0
    assert label_init == AvailabilityLabel.UNCERTAIN

    # 2. Patient reports OUT
    r1 = StockReport(
        facility_id=fac.id,
        medicine_id=med.id,
        reporter_id=seed_data["users"]["patient"].id,
        source_type=SourceType.PATIENT.value,
        availability_status=AvailabilityStatus.OUT.value,
    )
    db_session.add(r1)
    await db_session.commit()

    p_after_patient, _, _, count_patient, _ = await service.calculate_belief(fac.id, med.id)
    assert p_after_patient == 0.5
    assert count_patient == 1

    # 3. Another patient reports IN_STOCK
    r2 = StockReport(
        facility_id=fac.id,
        medicine_id=med.id,
        reporter_id=seed_data["users"]["patient"].id,
        source_type=SourceType.PATIENT.value,
        availability_status=AvailabilityStatus.IN_STOCK.value,
    )
    db_session.add(r2)
    await db_session.commit()

    p_after_second, _, _, count_second, _ = await service.calculate_belief(fac.id, med.id)
    assert p_after_second == 0.5
    assert count_second == 2


@pytest.mark.asyncio
async def test_staff_and_asha_stronger_evidence_than_patient(db_session: AsyncSession, seed_data: dict):
    """Mandatory Rule 1: STAFF and ASHA reports must carry stronger evidence weight than PATIENT."""
    fac = seed_data["facilities"][0]
    med = seed_data["medicines"][0]
    service = AvailabilityService(db_session)

    assert service.get_source_weight(SourceType.STAFF.value) == 1.0
    assert service.get_source_weight(SourceType.ASHA.value) == 0.8
    assert service.get_source_weight(SourceType.PATIENT.value) == 0.0

    r_staff = StockReport(
        facility_id=fac.id,
        medicine_id=med.id,
        reporter_id=seed_data["users"]["staff"].id,
        source_type=SourceType.STAFF.value,
        availability_status=AvailabilityStatus.IN_STOCK.value,
    )
    db_session.add(r_staff)
    await db_session.commit()

    p_staff, conf_staff, label_staff, _, _ = await service.calculate_belief(fac.id, med.id)
    assert p_staff >= 0.65
    assert label_staff == AvailabilityLabel.LIKELY
    assert conf_staff > 0.0


@pytest.mark.asyncio
async def test_unknown_report_handling(db_session: AsyncSession, seed_data: dict):
    """Mandatory Rule 3: UNKNOWN reports must not be interpreted as IN_STOCK or OUT."""
    fac = seed_data["facilities"][0]
    med = seed_data["medicines"][0]
    service = AvailabilityService(db_session)

    r_unknown = StockReport(
        facility_id=fac.id,
        medicine_id=med.id,
        reporter_id=seed_data["users"]["staff"].id,
        source_type=SourceType.STAFF.value,
        availability_status=AvailabilityStatus.UNKNOWN.value,
    )
    db_session.add(r_unknown)
    await db_session.commit()

    p, conf, label, count, _ = await service.calculate_belief(fac.id, med.id)
    assert p == 0.5
    assert label == AvailabilityLabel.UNCERTAIN


@pytest.mark.asyncio
async def test_conflicting_stock_reports_handling(db_session: AsyncSession, seed_data: dict):
    """Mandatory Rule 8: Handle conflicting reports without silently discarding evidence."""
    fac = seed_data["facilities"][0]
    med = seed_data["medicines"][0]
    service = AvailabilityService(db_session)

    now = datetime.now(timezone.utc)
    r1 = StockReport(
        facility_id=fac.id,
        medicine_id=med.id,
        reporter_id=seed_data["users"]["staff"].id,
        source_type=SourceType.STAFF.value,
        availability_status=AvailabilityStatus.IN_STOCK.value,
        reported_at=now,
    )
    r2 = StockReport(
        facility_id=fac.id,
        medicine_id=med.id,
        reporter_id=seed_data["users"]["staff"].id,
        source_type=SourceType.STAFF.value,
        availability_status=AvailabilityStatus.OUT.value,
        reported_at=now,
    )
    db_session.add_all([r1, r2])
    await db_session.commit()

    p, conf, label, count, _ = await service.calculate_belief(fac.id, med.id)
    assert count == 2
    assert 0.45 <= p <= 0.55
    assert label == AvailabilityLabel.UNCERTAIN
    assert conf < 0.3


@pytest.mark.asyncio
async def test_confidence_and_probability_boundaries(db_session: AsyncSession, seed_data: dict):
    """Verify all probability and confidence values strictly remain in [0.0, 1.0]."""
    fac = seed_data["facilities"][0]
    med = seed_data["medicines"][0]
    service = AvailabilityService(db_session)

    for i in range(15):
        db_session.add(StockReport(
            facility_id=fac.id,
            medicine_id=med.id,
            reporter_id=seed_data["users"]["staff"].id,
            source_type=SourceType.STAFF.value,
            availability_status=AvailabilityStatus.IN_STOCK.value,
        ))
    await db_session.commit()

    p, conf, label, count, _ = await service.calculate_belief(fac.id, med.id)
    assert 0.0 <= p <= 1.0
    assert 0.0 <= conf <= 1.0
    assert p >= 0.65
    assert label == AvailabilityLabel.LIKELY


@pytest.mark.asyncio
async def test_availability_labels_thresholds(db_session: AsyncSession, seed_data: dict):
    """Verify label boundaries:
    - LIKELY when p_available >= 0.65
    - UNLIKELY when p_available <= 0.35
    - UNCERTAIN when between 0.35 and 0.65
    """
    fac = seed_data["facilities"][0]
    med = seed_data["medicines"][0]
    service = AvailabilityService(db_session)

    # Test OUT report producing UNLIKELY
    r_out = StockReport(
        facility_id=fac.id,
        medicine_id=med.id,
        reporter_id=seed_data["users"]["staff"].id,
        source_type=SourceType.STAFF.value,
        availability_status=AvailabilityStatus.OUT.value,
    )
    db_session.add(r_out)
    await db_session.commit()

    p_out, conf_out, label_out, _, _ = await service.calculate_belief(fac.id, med.id)
    assert p_out <= 0.35
    assert label_out == AvailabilityLabel.UNLIKELY

    # Clear and test LOW report producing UNCERTAIN
    await db_session.execute(delete(StockReport))
    await db_session.commit()

    r_low = StockReport(
        facility_id=fac.id,
        medicine_id=med.id,
        reporter_id=seed_data["users"]["staff"].id,
        source_type=SourceType.STAFF.value,
        availability_status=AvailabilityStatus.LOW.value,
    )
    db_session.add(r_low)
    await db_session.commit()

    p_low, _, label_low, _, _ = await service.calculate_belief(fac.id, med.id)
    assert 0.35 < p_low < 0.65
    assert label_low == AvailabilityLabel.UNCERTAIN


@pytest.mark.asyncio
async def test_stale_evidence_handling(db_session: AsyncSession, seed_data: dict):
    """Rule 5 & 7: Stale evidence decays to prior and UNCERTAIN."""
    fac = seed_data["facilities"][0]
    med = seed_data["medicines"][0]
    service = AvailabilityService(db_session)

    old_date = datetime.now(timezone.utc) - timedelta(days=20)
    r_stale = StockReport(
        facility_id=fac.id,
        medicine_id=med.id,
        reporter_id=seed_data["users"]["staff"].id,
        source_type=SourceType.STAFF.value,
        availability_status=AvailabilityStatus.IN_STOCK.value,
        reported_at=old_date,
    )
    db_session.add(r_stale)
    await db_session.commit()

    p, conf, label, count, last_rep = await service.calculate_belief(fac.id, med.id)
    assert p == 0.5
    assert conf == 0.0
    assert label == AvailabilityLabel.UNCERTAIN
    assert count == 1
    assert last_rep is not None


@pytest.mark.asyncio
async def test_repeated_reports_dampened_and_capped(db_session: AsyncSession, seed_data: dict):
    """Verify repeated reports from a single reporter suffer diminishing returns and do not inflate confidence."""
    fac = seed_data["facilities"][0]
    med = seed_data["medicines"][0]
    service = AvailabilityService(db_session)
    staff_user = seed_data["users"]["staff"]

    # 1 report
    r1 = StockReport(
        facility_id=fac.id,
        medicine_id=med.id,
        reporter_id=staff_user.id,
        source_type=SourceType.STAFF.value,
        availability_status=AvailabilityStatus.IN_STOCK.value,
    )
    db_session.add(r1)
    await db_session.commit()
    _, conf_1, _, _, _ = await service.calculate_belief(fac.id, med.id)

    # Add 10 more reports from the same staff user
    for _ in range(10):
        db_session.add(StockReport(
            facility_id=fac.id,
            medicine_id=med.id,
            reporter_id=staff_user.id,
            source_type=SourceType.STAFF.value,
            availability_status=AvailabilityStatus.IN_STOCK.value,
        ))
    await db_session.commit()
    _, conf_11, _, count_11, _ = await service.calculate_belief(fac.id, med.id)

    assert count_11 == 11
    # Confidence must NOT reach near 1.0; capped at single-reporter maximum (~0.70)
    assert conf_11 < 0.75
    assert conf_11 >= conf_1


@pytest.mark.asyncio
async def test_independent_reporters_yield_higher_confidence_than_single(
    db_session: AsyncSession, seed_data: dict
):
    """Verify independent observers provide stronger evidentiary corroboration than a single repetitive reporter."""
    import uuid
    from app.models.user import User
    fac = seed_data["facilities"][0]
    med = seed_data["medicines"][0]
    service = AvailabilityService(db_session)

    # Facility with 10 reports from 1 reporter
    staff_1 = seed_data["users"]["staff"]
    for _ in range(10):
        db_session.add(StockReport(
            facility_id=fac.id,
            medicine_id=med.id,
            reporter_id=staff_1.id,
            source_type=SourceType.STAFF.value,
            availability_status=AvailabilityStatus.IN_STOCK.value,
        ))
    await db_session.commit()
    _, conf_single, _, _, _ = await service.calculate_belief(fac.id, med.id)

    # Second facility with 3 reports from 3 distinct staff members
    fac_2 = seed_data["facilities"][1]
    for i in range(3):
        distinct_staff = User(
            name=f"Staff Member {i+1}",
            phone=f"981112223{i}",
            password_hash="fake",
            role="STAFF",
        )
        db_session.add(distinct_staff)
        await db_session.flush()

        db_session.add(StockReport(
            facility_id=fac_2.id,
            medicine_id=med.id,
            reporter_id=distinct_staff.id,
            source_type=SourceType.STAFF.value,
            availability_status=AvailabilityStatus.IN_STOCK.value,
        ))
    await db_session.commit()
    _, conf_multi, _, _, _ = await service.calculate_belief(fac_2.id, med.id)

    # 3 distinct independent staff members yield higher confidence than 1 person repeating 10 times
    assert conf_multi > conf_single
