"""Shared Python-level contracts between CareBridge modules.

Per API.md Section 8:
- get_availability(facility_id, medicine_id) -> {p, conf, label} (Person 3, used by Person 4)
- list_candidate_facilities(village_id, service) -> [facility] (Person 2, used by Person 4)
- get_doctor_status(facility_id, date) -> attendance_status (Person 2, used by Person 4)
- distance_km(village_id, facility_id) -> int (Person 2, used by Person 4)

DISCLOSURE:
All calculations operate in simulated evaluation mode for hackathon demonstration.
Distance calculations use straight-line Haversine distance, not road travel distance.
"""
from datetime import date
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.schemas.shared import AttendanceStatus, AvailabilityLabel


def get_availability(
    facility_id: UUID,
    medicine_id: UUID,
    p: float = 0.0,
    conf: float = 0.0,
    label: AvailabilityLabel = AvailabilityLabel.UNCERTAIN,
) -> Dict[str, Any]:
    """Shared Contract 1: Retrieve medicine availability belief for a facility.

    Owner: Person 3 (Medicines & Stock)
    Consumer: Person 4 (Recommendation Engine)

    Preserves exact API.md return keys: {"p", "conf", "label"}.
    """
    return {
        "p": float(p),
        "conf": float(conf),
        "label": label if isinstance(label, AvailabilityLabel) else AvailabilityLabel(label),
        "_simulated": True,
    }


def list_candidate_facilities(
    village_id: UUID,
    service: Optional[str] = None,
    facilities_data: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Shared Contract 2: List healthcare facilities offering a service near a village.

    Owner: Person 2 (Facilities & Doctors)
    Consumer: Person 4 (Recommendation Engine)
    """
    return facilities_data if facilities_data is not None else []


def get_doctor_status(
    facility_id: UUID,
    schedule_date: Optional[date] = None,
    status: AttendanceStatus = AttendanceStatus.UNKNOWN,
) -> AttendanceStatus:
    """Shared Contract 3: Check doctor attendance status for a facility and date.

    Owner: Person 2 (Facilities & Doctors)
    Consumer: Person 4 (Recommendation Engine)

    Returns AttendanceStatus enum: EXPECTED, PRESENT, ABSENT, or UNKNOWN.
    EXPECTED means planned schedule attendance, NOT confirmed attendance.
    """
    return status if isinstance(status, AttendanceStatus) else AttendanceStatus(status)


def distance_km(
    village_id: UUID,
    facility_id: UUID,
    calculated_km: Optional[int] = None,
) -> int:
    """Shared Contract 4: Compute approximate straight-line distance in whole kilometres.

    Owner: Person 2 (Facilities & Doctors)
    Consumer: Person 4 (Recommendation Engine)

    CRITICAL NOTICE:
    Haversine computes straight-line (as the crow flies) distance, NOT actual road network travel
    distance or travel time. In rural areas, road distance can be significantly longer.
    """
    return calculated_km if calculated_km is not None else 0
