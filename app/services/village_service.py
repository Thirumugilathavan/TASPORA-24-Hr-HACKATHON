import json
from pathlib import Path
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.village import Village
from app.schemas.patient_village import VillageListOut, VillageOut


class VillageService:
    @staticmethod
    async def list_villages(db: AsyncSession) -> VillageListOut:
        """Returns all registered villages ordered by district and name."""
        stmt = select(Village).order_by(Village.district.asc(), Village.name.asc())
        result = await db.execute(stmt)
        villages = result.scalars().all()
        items = [VillageOut.model_validate(v) for v in villages]
        return VillageListOut(items=items, total=len(items))

    @staticmethod
    async def seed_synthetic_villages(db: AsyncSession, json_path: Optional[str] = None) -> List[Village]:
        """Seeds synthetic village records into the database, marking is_synthetic=True."""
        if json_path is None:
            base_dir = Path(__file__).resolve().parent.parent.parent
            json_path = str(base_dir / "seed_data" / "villages.json")

        path = Path(json_path)
        if not path.exists():
            return []

        with open(path, "r", encoding="utf-8") as f:
            records = json.load(f)

        seeded: List[Village] = []
        for rec in records:
            vid = UUID(rec["id"]) if isinstance(rec["id"], str) else rec["id"]
            stmt = select(Village).where(Village.id == vid)
            existing = (await db.execute(stmt)).scalar_one_or_none()
            if not existing:
                village = Village(
                    id=vid,
                    name=rec["name"],
                    district=rec["district"],
                    latitude=float(rec["latitude"]),
                    longitude=float(rec["longitude"]),
                    is_synthetic=bool(rec.get("is_synthetic", True)),
                )
                db.add(village)
                seeded.append(village)

        if seeded:
            await db.commit()
            for v in seeded:
                await db.refresh(v)
        return seeded
