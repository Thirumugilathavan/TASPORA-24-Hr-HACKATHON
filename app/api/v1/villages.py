from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.patient_village import VillageListOut
from app.services.village_service import VillageService

router = APIRouter(prefix="/villages", tags=["Villages"])


@router.get(
    "",
    response_model=VillageListOut,
    summary="List all registered villages",
    description="Returns a list of villages with GPS coordinates and total count.",
)
async def list_villages(db: AsyncSession = Depends(get_db)) -> VillageListOut:
    return await VillageService.list_villages(db)
