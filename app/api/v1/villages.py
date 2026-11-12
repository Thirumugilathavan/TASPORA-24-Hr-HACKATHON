from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.patient_village import VillageListOut
from app.services.village_service import VillageService

router = APIRouter(prefix="/villages", tags=["Villages"])


@router.get(
    "/search",
    response_model=VillageListOut,
    summary="Search Indian villages, towns, and cities",
    description="Intelligent search across official Indian settlements with prefix, substring, and typo tolerance.",
)
async def search_villages(
    q: str = Query(..., min_length=1, description="Location search query (village, town, or city)"),
    state: Optional[str] = Query(None, description="Optional state filter"),
    district: Optional[str] = Query(None, description="Optional district filter"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of suggestions to return"),
    db: AsyncSession = Depends(get_db),
) -> VillageListOut:
    return await VillageService.search_villages(
        db=db,
        query=q,
        state=state,
        district=district,
        limit=limit,
    )


@router.get(
    "",
    response_model=VillageListOut,
    summary="List all registered villages",
    description="Returns a list of villages with GPS coordinates and total count.",
)
async def list_villages(
    skip: int = Query(0, ge=0, description="Records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Records limit"),
    db: AsyncSession = Depends(get_db),
) -> VillageListOut:
    return await VillageService.list_villages(db, skip=skip, limit=limit)
