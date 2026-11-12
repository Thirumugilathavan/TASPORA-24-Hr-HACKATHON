from datetime import date
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from app.core.math_utils import round_expected_loss
from app.models.request import HealthcareRequest
from app.schemas.shared import (
    AttendanceStatus,
    AvailabilityLabel,
    RecommendationItem,
    RequestType,
)
from app.services.distance_service import haversine_km
from app.services.stubs import (
    distance_km,
    get_availability,
    get_doctor_status,
    list_candidate_facilities,
)

# Reference simulated facilities used if teammate facility-service returns an empty list
DEFAULT_CANDIDATE_FACILITIES = [
    {
        "id": UUID("11111111-1111-1111-1111-111111111111"),
        "name": "Taluk Community Health Centre",
        "facility_type": "CHC",
        "services": ["General Medicine", "Pediatrics", "Pharmacy Refill", "General Checkup", "Diagnostics"],
        "base_cost": 25,
        "cost_per_km": 3,
        "_simulated": True,
    },
    {
        "id": UUID("22222222-2222-2222-2222-222222222222"),
        "name": "Gram Panchayat Primary Health Centre",
        "facility_type": "PHC",
        "services": ["General Medicine", "Pharmacy Refill", "General Checkup"],
        "base_cost": 15,
        "cost_per_km": 2,
        "_simulated": True,
    },
    {
        "id": UUID("33333333-3333-3333-3333-333333333333"),
        "name": "District Sub-Divisional Hospital",
        "facility_type": "HOSPITAL",
        "services": ["General Medicine", "Specialist Consultation", "Pharmacy Refill", "General Checkup", "Diagnostics"],
        "base_cost": 40,
        "cost_per_km": 4,
        "_simulated": True,
    },
    {
        "id": UUID("44444444-4444-4444-4444-444444444444"),
        "name": "Jan Aushadhi Kendra Pharmacy",
        "facility_type": "PHARMACY",
        "services": ["Pharmacy Refill"],
        "base_cost": 10,
        "cost_per_km": 2,
        "_simulated": True,
    },
]


def map_request_to_service(request_type: RequestType) -> str:
    """Map patient request type to required healthcare service capability."""
    mapping = {
        RequestType.CONSULTATION: "General Medicine",
        RequestType.REFILL: "Pharmacy Refill",
        RequestType.CHECKUP: "General Checkup",
        RequestType.DIAGNOSTIC: "Diagnostics",
    }
    return mapping.get(request_type, "General Medicine")


def evaluate_facility_suitability(
    facility: Dict[str, Any],
    service: str,
    request_type: RequestType
) -> float:
    """Evaluate suitability of facility for the requested service (0.0 to 1.0).

    Medical Safety Rule:
    Does NOT provide clinical suitability or medical judgment; only verifies
    administrative capability and service offerings.
    """
    services = facility.get("services", [])
    facility_type = facility.get("facility_type", "PHC")

    # If facility doesn't list the service, suitability drops significantly
    has_service = service in services or len(services) == 0

    if request_type == RequestType.REFILL:
        if facility_type == "PHARMACY":
            return 0.98 if has_service else 0.40
        return 0.85 if has_service else 0.30

    if request_type == RequestType.DIAGNOSTIC:
        if facility_type in ("HOSPITAL", "CHC"):
            return 0.92 if has_service else 0.20
        return 0.40 if has_service else 0.10

    if request_type in (RequestType.CONSULTATION, RequestType.CHECKUP):
        if facility_type == "PHARMACY":
            return 0.10  # Pharmacies cannot conduct clinical consultations
        if facility_type == "HOSPITAL":
            return 0.95
        if facility_type == "CHC":
            return 0.90
        return 0.85

    return 0.70 if has_service else 0.20


def generate_recommendations(
    request: HealthcareRequest,
    village_id: Optional[UUID] = None,
    candidate_facilities: Optional[List[Dict[str, Any]]] = None,
    village_coords: Optional[Tuple[float, float]] = None,
) -> List[RecommendationItem]:
    """Generate loss-minimized healthcare facility recommendations.

    Implements API.md expected loss formula:
    expected_loss = failure_probability * travel_cost

    Sorted ascending by expected_loss.
    """
    service = map_request_to_service(request.request_type)
    target_village_id = village_id or uuid4()
    today = date.today()

    # Retrieve candidate facilities via argument, shared contract, or default fallback
    if candidate_facilities:
        candidates = candidate_facilities
    else:
        candidates = list_candidate_facilities(target_village_id, service)
        if not candidates:
            candidates = DEFAULT_CANDIDATE_FACILITIES

    evaluated_items: List[RecommendationItem] = []

    for fac in candidates:
        fac_id = fac.get("id") if isinstance(fac.get("id"), UUID) else UUID(str(fac.get("id")))
        fac_name = fac.get("name", "Healthcare Facility")

        # 1. Facility Service Suitability
        suitability = evaluate_facility_suitability(fac, service, request.request_type)

        # 2. Doctor Availability via live data or shared contract
        if "doctor_status" in fac and fac["doctor_status"] is not None:
            doc_status = fac["doctor_status"]
            if not isinstance(doc_status, AttendanceStatus):
                doc_status = AttendanceStatus(doc_status)
        else:
            doc_status = get_doctor_status(fac_id, today)

        # Doctor failure probability
        if doc_status == AttendanceStatus.PRESENT:
            p_doc_fail = 0.05
        elif doc_status == AttendanceStatus.EXPECTED:
            # EXPECTED means planned, not physically confirmed
            p_doc_fail = 0.35
        elif doc_status == AttendanceStatus.UNKNOWN:
            p_doc_fail = 0.55
        else:  # ABSENT
            p_doc_fail = 0.95

        # 3. Medicine Availability via live data or shared contract
        med_confidence = 0.80
        p_stock_fail = 0.20
        stock_label = AvailabilityLabel.UNCERTAIN

        if "medicine_belief" in fac and fac["medicine_belief"] is not None:
            stock_res = fac["medicine_belief"]
            p_avail = float(stock_res.get("p", 0.5))
            conf = float(stock_res.get("conf", 0.5))
            stock_label = stock_res.get("label", AvailabilityLabel.UNCERTAIN)
            if not isinstance(stock_label, AvailabilityLabel):
                stock_label = AvailabilityLabel(stock_label)
            med_confidence = conf

            if p_avail > 0.0:
                p_stock_fail = max(0.0, 1.0 - (p_avail * conf))
            else:
                p_stock_fail = 1.0
        elif request.medicine_id is not None or request.request_type == RequestType.REFILL:
            med_id = request.medicine_id or uuid4()
            stock_res = get_availability(fac_id, med_id)
            p_avail = float(stock_res.get("p", 0.5))
            conf = float(stock_res.get("conf", 0.5))
            stock_label = stock_res.get("label", AvailabilityLabel.UNCERTAIN)
            med_confidence = conf

            if p_avail > 0.0:
                p_stock_fail = max(0.0, 1.0 - (p_avail * conf))
            else:
                p_stock_fail = 1.0

        # 4. Straight-line Distance (Approximate Haversine km)
        if village_coords and "latitude" in fac and "longitude" in fac:
            dist = round(haversine_km(village_coords[0], village_coords[1], fac["latitude"], fac["longitude"]))
        else:
            dist = distance_km(target_village_id, fac_id)

        if dist <= 0:
            # Deterministic synthetic distance for demo facilities if stub returns 0
            fac_hash = abs(hash(str(fac_id))) % 25
            dist = max(3, fac_hash)

        # 5. Whole Rupee Travel Cost
        base_cost = fac.get("base_cost", 20)
        cost_per_km = fac.get("cost_per_km", 3)
        travel_cost = int(base_cost + (cost_per_km * dist))

        # 6. Failure Probability Calculation
        if request.request_type == RequestType.REFILL:
            # For refill, failure is driven by stock confidence and facility suitability
            p_success = suitability * (1.0 - p_stock_fail)
        elif request.request_type in (RequestType.CONSULTATION, RequestType.CHECKUP):
            # For consultation, failure is driven by doctor availability and suitability
            p_success = suitability * (1.0 - p_doc_fail)
        else:
            # Diagnostic / General
            p_success = suitability * (1.0 - (0.5 * p_doc_fail + 0.5 * p_stock_fail))

        failure_probability = round(min(1.0, max(0.05, 1.0 - p_success)), 4)

        # 7. Expected Loss (Strict Decimal ROUND_HALF_UP)
        expected_loss = round_expected_loss(failure_probability, travel_cost)

        # 8. Rationale / Explanation Generation
        doc_note = (
            "Doctor verified PRESENT on duty."
            if doc_status == AttendanceStatus.PRESENT
            else "Doctor schedule is EXPECTED (planned, not confirmed)."
            if doc_status == AttendanceStatus.EXPECTED
            else "Doctor attendance UNKNOWN."
            if doc_status == AttendanceStatus.UNKNOWN
            else "Doctor reported ABSENT."
        )

        stock_note = (
            f"Medicine stock likelihood: {stock_label.value} (confidence: {int(med_confidence * 100)}%)."
            if request.request_type == RequestType.REFILL or request.medicine_id
            else "Standard clinical consultation services available."
        )

        explanation = (
            f"{fac_name} matches {service}. {doc_note} {stock_note} "
            f"Estimated travel distance: ~{dist} km (straight-line approx). "
            f"Expected trip loss calculated at Rs {expected_loss} (failure risk: {int(failure_probability * 100)}%). "
            f"[Simulated Facility]"
        )

        item = RecommendationItem(
            rank=0,  # Will be assigned after sorting
            facility_id=fac_id,
            facility_name=fac_name,
            suitability_score=round(suitability, 2),
            medicine_confidence=round(med_confidence, 2),
            travel_distance_km=dist,
            travel_cost=travel_cost,
            failure_probability=failure_probability,
            expected_loss=expected_loss,
            doctor_status=doc_status,
            explanation=explanation,
        )
        evaluated_items.append(item)

    # Sort strictly ascending by expected_loss
    evaluated_items.sort(key=lambda x: (x.expected_loss, x.failure_probability, x.travel_distance_km))

    # Assign 1-based ranks
    for index, item in enumerate(evaluated_items, start=1):
        item.rank = index

    return evaluated_items
