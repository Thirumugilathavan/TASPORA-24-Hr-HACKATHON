from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db

router = APIRouter(tags=["Health"])


@router.get("/")
@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint providing platform status and simulated mode disclosure."""
    db_status = "connected"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "ok",
        "project": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "database": db_status,
        "simulated_mode": settings.IS_SIMULATED,
        "disclosure": (
            "CareBridge is operating in simulated evaluation mode. "
            "No live connection exists to real hospital systems, pharmacy inventories, "
            "or emergency services. All data is synthetic."
        ),
    }
