from fastapi import APIRouter, Query, status
from app.schemas.pincode import PincodeResolutionOut
from app.services.pincode_service import PincodeService

router = APIRouter(prefix="/pincodes", tags=["Postal PIN Codes"])


@router.get(
    "/resolve",
    response_model=PincodeResolutionOut,
    summary="Resolve 6-digit Indian PIN code",
    description="Resolves an Indian postal PIN code to approximate geographic coordinates and administrative district.",
)
async def resolve_pincode(
    pincode: str = Query(..., min_length=6, max_length=6, description="6-digit Indian PIN code (e.g. 637211)"),
) -> PincodeResolutionOut:
    """Resolve Indian PIN code to postal centroid coordinates and district boundaries."""
    res = PincodeService.resolve_pincode(pincode)
    return PincodeResolutionOut(**res)
