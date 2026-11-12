import difflib
import json
import re
import uuid
from pathlib import Path
from typing import List, Optional
from uuid import UUID
from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.village import Village
from app.schemas.patient_village import CustomVillageCreateIn, VillageListOut, VillageOut
from app.services.pincode_service import PincodeService


class VillageService:
    @staticmethod
    async def list_villages(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
    ) -> VillageListOut:
        """Returns registered villages ordered by district and name."""
        stmt = select(Village).order_by(Village.district.asc(), Village.name.asc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        villages = result.scalars().all()
        
        count_stmt = select(func.count(Village.id))
        total_count = (await db.execute(count_stmt)).scalar_one_or_none() or len(villages)
        
        items = [VillageOut.model_validate(v) for v in villages]
        return VillageListOut(items=items, total=total_count)

    @staticmethod
    async def search_villages(
        db: AsyncSession,
        query: str,
        state: Optional[str] = None,
        district: Optional[str] = None,
        limit: int = 20,
    ) -> VillageListOut:
        """
        Intelligent location search supporting villages, towns, and cities across India.
        - Exact name match (highest priority)
        - Prefix name match
        - Subdistrict/District prefix match
        - Substring match
        - PIN code search and auto-resolution
        - Typo & spelling tolerance (fuzzy search for minor typing variations)
        - Distinguishes identically named locations via administrative hierarchy (subdistrict, district, state).
        """
        clean_q = query.strip()
        if not clean_q:
            return VillageListOut(items=[], total=0)

        records: List[Village] = []
        seen_ids = set()

        # 1. Check if query is or contains a 6-digit Indian PIN code
        pin_match = re.search(r"\b([1-9]\d{5})\b", clean_q)
        if pin_match:
            pin_code = pin_match.group(1)
            try:
                pin_info = PincodeService.resolve_pincode(pin_code)
                pin_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"pincode:{pin_code}")
                p_stmt = select(Village).where(Village.id == pin_uuid)
                p_res = (await db.execute(p_stmt)).scalar_one_or_none()
                if not p_res:
                    p_res = Village(
                        id=pin_uuid,
                        name=f"PIN {pin_code} - {pin_info.get('locality', 'Postal Area')}",
                        district=pin_info["district"],
                        state=pin_info.get("state", "Tamil Nadu"),
                        subdistrict=pin_info.get("locality", pin_info["district"]),
                        latitude=float(pin_info["latitude"]),
                        longitude=float(pin_info["longitude"]),
                        is_synthetic=True,
                    )
                    db.add(p_res)
                    await db.commit()
                    await db.refresh(p_res)
                records.append(p_res)
                seen_ids.add(p_res.id)
            except Exception:
                pass

        prefix_term = f"{clean_q}%"
        filter_clauses = [
            Village.name.ilike(prefix_term),
            Village.subdistrict.ilike(prefix_term),
            Village.district.ilike(prefix_term),
        ]

        relevance = case(
            (func.lower(Village.name) == func.lower(clean_q), 1),
            (Village.name.ilike(prefix_term), 2),
            (Village.subdistrict.ilike(prefix_term), 3),
            (Village.district.ilike(prefix_term), 4),
            else_=5,
        )

        stmt = select(Village).where(or_(*filter_clauses))
        if state and state.strip():
            stmt = stmt.where(Village.state.ilike(f"%{state.strip()}%"))
        if district and district.strip():
            stmt = stmt.where(Village.district.ilike(f"%{district.strip()}%"))

        stmt = stmt.order_by(relevance, func.length(Village.name).asc(), Village.name.asc()).limit(limit)

        result = await db.execute(stmt)
        for v in result.scalars().all():
            if v.id not in seen_ids and len(records) < limit:
                records.append(v)
                seen_ids.add(v.id)

        # If fewer than limit, check substring matches
        if len(records) < limit:
            remaining = limit - len(records)
            substr_term = f"%{clean_q}%"
            sub_stmt = select(Village).where(
                or_(
                    Village.name.ilike(substr_term),
                    Village.subdistrict.ilike(substr_term),
                    Village.district.ilike(substr_term),
                )
            )
            if state and state.strip():
                sub_stmt = sub_stmt.where(Village.state.ilike(f"%{state.strip()}%"))
            if district and district.strip():
                sub_stmt = sub_stmt.where(Village.district.ilike(f"%{district.strip()}%"))

            sub_stmt = sub_stmt.order_by(func.length(Village.name).asc(), Village.name.asc()).limit(remaining * 2)
            sub_res = (await db.execute(sub_stmt)).scalars().all()
            for v in sub_res:
                if v.id not in seen_ids and len(records) < limit:
                    records.append(v)
                    seen_ids.add(v.id)

        # If still 0 results and query is at least 3 chars, attempt spelling correction / fuzzy match
        if not records and len(clean_q) >= 3:
            cand_prefixes = [f"{clean_q[:3]}%", f"{clean_q[:2]}%"]
            candidates: List[str] = []
            for pfx in cand_prefixes:
                c_stmt = select(Village.name).where(Village.name.ilike(pfx)).distinct().limit(100)
                if state and state.strip():
                    c_stmt = c_stmt.where(Village.state.ilike(f"%{state.strip()}%"))
                c_res = (await db.execute(c_stmt)).scalars().all()
                if c_res:
                    candidates = list(c_res)
                    break

            if candidates:
                close_matches = difflib.get_close_matches(clean_q, candidates, n=5, cutoff=0.55)
                if close_matches:
                    fuzz_stmt = select(Village).where(Village.name.in_(close_matches))
                    if state and state.strip():
                        fuzz_stmt = fuzz_stmt.where(Village.state.ilike(f"%{state.strip()}%"))
                    fuzz_stmt = fuzz_stmt.limit(limit)
                    fuzz_res = (await db.execute(fuzz_stmt)).scalars().all()
                    for v in fuzz_res:
                        if v.id not in seen_ids and len(records) < limit:
                            records.append(v)
                            seen_ids.add(v.id)

        items = [VillageOut.model_validate(v) for v in records]
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
                    state=rec.get("state", "Uttar Pradesh"),
                    subdistrict=rec.get("subdistrict", rec["district"]),
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

    @staticmethod
    async def create_custom_village(
        db: AsyncSession,
        data: CustomVillageCreateIn,
    ) -> VillageOut:
        """Creates and stores a verified custom/fallback locality record."""
        lat = data.latitude
        lon = data.longitude

        # 1. Attempt PIN code resolution if coordinates not provided
        if (lat is None or lon is None) and data.pincode:
            try:
                pin_res = PincodeService.resolve_pincode(data.pincode)
                lat = float(pin_res["latitude"])
                lon = float(pin_res["longitude"])
                if not data.district and pin_res.get("district"):
                    data.district = pin_res["district"]
                if not data.state and pin_res.get("state"):
                    data.state = pin_res["state"]
            except Exception:
                pass

        # 2. Fallback to district average coordinates
        if lat is None or lon is None:
            stmt = select(func.avg(Village.latitude), func.avg(Village.longitude)).where(
                Village.district.ilike(f"%{data.district.strip()}%")
            )
            d_res = await db.execute(stmt)
            row = d_res.first()
            if row and row[0] is not None and row[1] is not None:
                lat = float(row[0])
                lon = float(row[1])
            else:
                lat = 11.1271  # Tamil Nadu centroid
                lon = 78.6569

        clean_name = data.name.strip()
        clean_district = data.district.strip()
        clean_state = data.state.strip() if data.state else "Tamil Nadu"
        clean_sub = data.subdistrict.strip() if data.subdistrict else clean_district

        # Check if an identical village already exists
        exist_stmt = select(Village).where(
            func.lower(Village.name) == func.lower(clean_name),
            func.lower(Village.district) == func.lower(clean_district),
        )
        existing_v = (await db.execute(exist_stmt)).scalar_one_or_none()
        if existing_v:
            return VillageOut.model_validate(existing_v)

        new_village = Village(
            id=uuid.uuid4(),
            name=clean_name,
            district=clean_district,
            state=clean_state,
            subdistrict=clean_sub,
            latitude=round(float(lat), 6),
            longitude=round(float(lon), 6),
            is_synthetic=True,
        )
        db.add(new_village)
        await db.commit()
        await db.refresh(new_village)
        return VillageOut.model_validate(new_village)
