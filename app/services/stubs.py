"""Shared Python-level contract placeholders between CareBridge modules.

Per API.md Section 8:
- get_availability(facility_id, medicine_id) -> {p, conf, label} (Person 3, used by Person 4)
- list_candidate_facilities(village_id, service) -> [facility] (Person 2, used by Person 4)
- get_doctor_status(facility_id, date) -> attendance_status (Person 2, used by Person 4)
- distance_km(village_id, facility_id) -> int (Person 2, used by Person 4)

DISCLOSURE:
All stubs in this module are deterministic placeholders for Phase 1 integration.
They return unverified placeholder structures and do NOT represent real hospital,
pharmacy, or government healthcare data.
"""
from datetime import date
from typing import Any, Dict, List
from uuid import UUID

from app.schemas.shared import AttendanceStatus, AvailabilityLabel


def get_availability(facility_id: UUID, medicine_id: UUID) -> Dict[str, Any]:
    """Shared Contract 1: Retrieve medicine availability belief for a facility.

    Owner: Person 3 (Medicines & Stock)
    Consumer: Person 4 (Recommendation Engine)

    Preserves exact API.md return keys: {"p", "conf", "label"}.
    Explicitly flagged as simulated placeholder.
    """
    return {
        "p": 0.0,
        "conf": 0.0,
        "label": AvailabilityLabel.UNCERTAIN,
        "_simulated": True,
        "_status": "PLACEHOLDER_UNIMPLEMENTED",
    }


def list_candidate_facilities(village_id: UUID, service: str) -> List[Dict[str, Any]]:
    """Shared Contract 2: List healthcare facilities offering a service near a village.

    Owner: Person 2 (Facilities & Doctors)
    Consumer: Person 4 (Recommendation Engine)

    Returns candidate facility records. Returns an empty list in Phase 1 stub.
    """
    # Deterministic empty list during Phase 1 foundation; no fabricated facilities.
    return []


def get_doctor_status(facility_id: UUID, schedule_date: date) -> AttendanceStatus:
    """Shared Contract 3: Check doctor attendance status for a facility and date.

    Owner: Person 2 (Facilities & Doctors)
    Consumer: Person 4 (Recommendation Engine)

    Returns AttendanceStatus enum. Returns UNKNOWN during Phase 1 placeholder state.
    """
    return AttendanceStatus.UNKNOWN


def distance_km(village_id: UUID, facility_id: UUID) -> int:
    """Shared Contract 4: Compute approximate straight-line distance in whole kilometres.

    Owner: Person 2 (Facilities & Doctors)
    Consumer: Person 4 (Recommendation Engine)

    NOTE: When implemented with coordinates, Haversine computes straight-line
    distance, NOT actual road network travel distance or travel time.
    Distances below 0.5 km round to 0 km (or 1 km if non-zero travel applies).
    Returns 0 in Phase 1 placeholder state.
    """
    return 0
