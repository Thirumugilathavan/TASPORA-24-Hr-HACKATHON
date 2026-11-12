from datetime import date
import uuid
from app.schemas.shared import AttendanceStatus, AvailabilityLabel
from app.services.stubs import (
    distance_km,
    get_availability,
    get_doctor_status,
    list_candidate_facilities,
)


def test_get_availability_stub_preserves_contract_keys():
    """Verify get_availability returns {p, conf, label} per API.md Section 8."""
    facility_id = uuid.uuid4()
    medicine_id = uuid.uuid4()

    result = get_availability(facility_id, medicine_id)

    # API.md contract keys
    assert "p" in result
    assert "conf" in result
    assert "label" in result
    assert isinstance(result["p"], (float, int))
    assert isinstance(result["conf"], (float, int))
    assert isinstance(result["label"], AvailabilityLabel)

    # Verification of simulation flag
    assert result.get("_simulated") is True


def test_list_candidate_facilities_stub():
    """Verify list_candidate_facilities returns a list."""
    village_id = uuid.uuid4()
    service = "General Medicine"

    facilities = list_candidate_facilities(village_id, service)
    assert isinstance(facilities, list)


def test_get_doctor_status_stub():
    """Verify get_doctor_status returns an AttendanceStatus enum."""
    facility_id = uuid.uuid4()
    today = date.today()

    status = get_doctor_status(facility_id, today)
    assert isinstance(status, AttendanceStatus)


def test_distance_km_stub():
    """Verify distance_km returns an integer whole kilometre."""
    village_id = uuid.uuid4()
    facility_id = uuid.uuid4()

    km = distance_km(village_id, facility_id)
    assert isinstance(km, int)
