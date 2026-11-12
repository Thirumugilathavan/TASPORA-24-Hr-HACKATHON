from dataclasses import dataclass
from datetime import datetime, timezone
import math
from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock import FacilityMedicineBelief, StockReport
from app.schemas.shared import AvailabilityLabel, AvailabilityStatus, SourceType


@dataclass
class StockAlgorithmConfig:
    """Configurable parameters for the Stock Intelligence belief state algorithm."""
    weight_staff: float = 1.0
    weight_asha: float = 0.8
    # Rule 2: Patient feedback must never directly modify medicine stock probability
    weight_patient: float = 0.0
    weight_admin: float = 1.0

    half_life_hours: float = 36.0
    max_evidence_age_days: float = 14.0

    prior_probability: float = 0.5
    prior_weight: float = 0.5

    threshold_likely: float = 0.65
    threshold_unlikely: float = 0.35

    volume_k: float = 0.8
    min_confidence_definitive: float = 0.20


DEFAULT_ALGO_CONFIG = StockAlgorithmConfig()


class AvailabilityService:
    def __init__(self, db: AsyncSession, config: Optional[StockAlgorithmConfig] = None):
        self.db = db
        self.config = config or DEFAULT_ALGO_CONFIG

    def get_source_weight(self, source_type: str) -> float:
        """Rule 1 & 2: STAFF and ASHA carry stronger weight; PATIENT weight is strictly 0.0."""
        st = source_type.upper() if isinstance(source_type, str) else source_type.value
        if st == SourceType.STAFF.value:
            return self.config.weight_staff
        elif st == SourceType.ASHA.value:
            return self.config.weight_asha
        elif st == SourceType.PATIENT.value:
            return self.config.weight_patient
        elif st == "ADMIN":
            return self.config.weight_admin
        return 0.0

    def get_status_score(self, status: str) -> Optional[float]:
        """Rule 3: UNKNOWN reports must not be interpreted as IN_STOCK or OUT."""
        st = status.upper() if isinstance(status, str) else status.value
        if st == AvailabilityStatus.IN_STOCK.value:
            return 1.0
        elif st == AvailabilityStatus.LOW.value:
            return 0.4
        elif st == AvailabilityStatus.OUT.value:
            return 0.0
        elif st == AvailabilityStatus.UNKNOWN.value:
            return None
        return None

    async def calculate_belief(
        self,
        facility_id: UUID,
        medicine_id: UUID,
        as_of: Optional[datetime] = None,
    ) -> Tuple[float, float, AvailabilityLabel, int, Optional[datetime]]:
        """Compute probabilistic availability belief and confidence from the append-only ledger.

        Returns:
            (p_available, confidence, label, evidence_count, last_report_at)
        """
        now = as_of or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        stmt = (
            select(StockReport)
            .where(
                StockReport.facility_id == facility_id,
                StockReport.medicine_id == medicine_id,
            )
            .order_by(StockReport.reported_at.desc())
        )
        res = await self.db.execute(stmt)
        reports: List[StockReport] = list(res.scalars().all())

        evidence_count = len(reports)
        if evidence_count == 0:
            return (
                self.config.prior_probability,
                0.0,
                AvailabilityLabel.UNCERTAIN,
                0,
                None,
            )

        last_report_at = reports[0].reported_at
        if last_report_at.tzinfo is None:
            last_report_at = last_report_at.replace(tzinfo=timezone.utc)

        weighted_sum = 0.0
        total_avail_weight = 0.0
        total_unknown_weight = 0.0
        scores: List[Tuple[float, float]] = []

        max_age_hours = self.config.max_evidence_age_days * 24.0
        half_life_hours = self.config.half_life_hours

        for rep in reports:
            rep_time = rep.reported_at
            if rep_time.tzinfo is None:
                rep_time = rep_time.replace(tzinfo=timezone.utc)

            age_hours = max(0.0, (now - rep_time).total_seconds() / 3600.0)
            if age_hours > max_age_hours:
                continue

            decay = math.pow(2.0, -age_hours / half_life_hours)
            src_weight = self.get_source_weight(rep.source_type)
            effective_weight = src_weight * decay

            score = self.get_status_score(rep.availability_status)
            if score is None:
                # UNKNOWN report: adds to uncertainty without modifying stock probability
                total_unknown_weight += effective_weight
            else:
                if effective_weight > 0.0:
                    weighted_sum += effective_weight * score
                    total_avail_weight += effective_weight
                    scores.append((score, effective_weight))

        p_prior = self.config.prior_probability
        w_prior = self.config.prior_weight

        if total_avail_weight <= 0.0:
            p_available = p_prior
        else:
            p_available = (p_prior * w_prior + weighted_sum) / (w_prior + total_avail_weight)

        # Clamping guarantees
        p_available = max(0.0, min(1.0, float(p_available)))

        # Confidence calculation
        vol_factor = 1.0 - math.exp(-self.config.volume_k * total_avail_weight)

        if len(scores) > 1 and total_avail_weight > 0.0:
            mean_score = weighted_sum / total_avail_weight
            variance = sum(w * ((s - mean_score) ** 2) for s, w in scores) / total_avail_weight
            std_dev = math.sqrt(max(0.0, variance))
            conflict_penalty = max(0.1, 1.0 - 1.8 * std_dev)
        else:
            conflict_penalty = 1.0

        if total_unknown_weight > 0.0:
            unknown_factor = (total_avail_weight + 1.0) / (total_avail_weight + total_unknown_weight + 1.0)
        else:
            unknown_factor = 1.0

        latest_age_hours = max(0.0, (now - last_report_at).total_seconds() / 3600.0)
        if latest_age_hours > 48.0:
            freshness_factor = math.pow(2.0, -(latest_age_hours - 48.0) / half_life_hours)
        else:
            freshness_factor = 1.0

        confidence = vol_factor * conflict_penalty * unknown_factor * freshness_factor
        confidence = max(0.0, min(1.0, float(confidence)))

        if confidence < self.config.min_confidence_definitive or total_avail_weight <= 0.0:
            label = AvailabilityLabel.UNCERTAIN
        elif p_available >= self.config.threshold_likely:
            label = AvailabilityLabel.LIKELY
        elif p_available <= self.config.threshold_unlikely:
            label = AvailabilityLabel.UNLIKELY
        else:
            label = AvailabilityLabel.UNCERTAIN

        return (
            round(p_available, 4),
            round(confidence, 4),
            label,
            evidence_count,
            last_report_at,
        )

    async def update_belief_state(
        self,
        facility_id: UUID,
        medicine_id: UUID,
    ) -> FacilityMedicineBelief:
        """Recalculate belief state and persist/update into facility_medicine_beliefs table."""
        p_avail, conf, label, count, last_rep = await self.calculate_belief(facility_id, medicine_id)

        stmt = select(FacilityMedicineBelief).where(
            FacilityMedicineBelief.facility_id == facility_id,
            FacilityMedicineBelief.medicine_id == medicine_id,
        )
        res = await self.db.execute(stmt)
        belief = res.scalar_one_or_none()

        label_str = label.value if hasattr(label, "value") else str(label)

        if not belief:
            belief = FacilityMedicineBelief(
                facility_id=facility_id,
                medicine_id=medicine_id,
                p_available=p_avail,
                confidence=conf,
                label=label_str,
                evidence_count=count,
                last_report_at=last_rep,
            )
            self.db.add(belief)
        else:
            belief.p_available = p_avail
            belief.confidence = conf
            belief.label = label_str
            belief.evidence_count = count
            belief.last_report_at = last_rep

        await self.db.commit()
        await self.db.refresh(belief)
        return belief
