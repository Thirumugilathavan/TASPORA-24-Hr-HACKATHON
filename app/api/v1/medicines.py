from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.medicine import MedicineCreate, MedicineResponse
from app.schemas.shared import Page
from app.services.medicine_service import MedicineServiceHandler

router = APIRouter(prefix="/medicines", tags=["Medicines"])


@router.get("", response_model=Page[MedicineResponse])
async def get_medicines(
    q: Optional[str] = Query(None, description="Search query matching brand or generic name"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Search medicine catalogue.

    IMPORTANT MEDICAL SAFETY:
    This endpoint provides catalogue information only.
    It does NOT provide prescriptions, medical diagnosis, or dosage recommendations.
    """
    handler = MedicineServiceHandler(db)
    items, total = await handler.search_medicines(query_text=q, skip=skip, limit=limit)
    return Page(items=items, total=total)


@router.post("", response_model=MedicineResponse, status_code=status.HTTP_201_CREATED)
async def create_medicine(
    payload: MedicineCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add a medicine entry to the catalogue."""
    handler = MedicineServiceHandler(db)
    return await handler.create_medicine(payload)
