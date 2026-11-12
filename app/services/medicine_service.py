from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.medicine import Medicine
from app.schemas.medicine import MedicineCreate


class MedicineServiceHandler:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def search_medicines(
        self,
        query_text: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Medicine], int]:
        """Search medicine catalogue by brand or generic name.

        CRITICAL: Catalogue information only.
        Prescription, diagnosis or dosage recommendations are prohibited.
        """
        stmt = select(Medicine)

        if query_text and query_text.strip():
            pattern = f"%{query_text.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Medicine.name).like(pattern),
                    func.lower(Medicine.generic_name).like(pattern),
                )
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_res = await self.db.execute(count_stmt)
        total = count_res.scalar_one()

        items_stmt = stmt.order_by(Medicine.name.asc()).offset(skip).limit(limit)
        items_res = await self.db.execute(items_stmt)
        items = list(items_res.scalars().all())

        return items, total

    async def get_medicine(self, medicine_id: UUID) -> Optional[Medicine]:
        stmt = select(Medicine).where(Medicine.id == medicine_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def create_medicine(self, data: MedicineCreate) -> Medicine:
        med = Medicine(
            name=data.name,
            generic_name=data.generic_name,
            strength=data.strength,
            dosage_form=data.dosage_form,
        )
        self.db.add(med)
        await self.db.commit()
        await self.db.refresh(med)
        return med
