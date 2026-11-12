import uuid
from typing import List, Optional
from uuid import UUID
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.notification import Notification
from app.schemas.notification import NotificationCreateIn, NotificationListOut, NotificationOut


class NotificationService:
    @staticmethod
    async def get_user_notifications(
        db: AsyncSession,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> NotificationListOut:
        """Retrieve user's notifications. Seeds realistic initial alerts if user has none."""
        # Check existing count
        count_stmt = select(func.count(Notification.id)).where(Notification.user_id == user_id)
        existing_count = (await db.execute(count_stmt)).scalar_one()

        if existing_count == 0:
            # Seed authentic initial healthcare & system notices for this user
            initial_notices = [
                Notification(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    title="Welcome to NALAM AI Healthcare",
                    message="Your patient account and village profile are securely active. Explore nearby healthcare facilities, doctor consultations, and medicine supplies.",
                    type="info",
                    is_read=False,
                    link="/facilities",
                ),
                Notification(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    title="MOHFW Facility Registry Connected",
                    message="Verified Government Primary Health Centres (PHC), Sub-Centres (SCE), and District Hospitals are ranked dynamically from your location.",
                    type="info",
                    is_read=False,
                    link="/facilities",
                ),
                Notification(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    title="24/7 Telephone IVR Helpline",
                    message="Access healthcare discovery and appointment guidance without mobile internet by calling toll-free 1800-419-6252 or using the IVR simulation.",
                    type="appointment",
                    is_read=False,
                    link="/ivr",
                ),
                Notification(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    title="Community Health Bulletin",
                    message="Routine immunization, diagnostic checkups, and generic medicines under Jan Aushadhi are accessible at your local health center.",
                    type="alert",
                    is_read=False,
                    link="/facilities",
                ),
            ]
            for n in initial_notices:
                db.add(n)
            await db.commit()

        # Query paginated notifications
        stmt = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        notifications = list(result.scalars().all())

        total_stmt = select(func.count(Notification.id)).where(Notification.user_id == user_id)
        total = (await db.execute(total_stmt)).scalar_one()

        unread_stmt = (
            select(func.count(Notification.id))
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        )
        unread_count = (await db.execute(unread_stmt)).scalar_one()

        items = [NotificationOut.model_validate(n) for n in notifications]
        return NotificationListOut(items=items, total=total, unread_count=unread_count)

    @staticmethod
    async def mark_as_read(
        db: AsyncSession,
        user_id: UUID,
        notification_id: UUID,
    ) -> Optional[NotificationOut]:
        """Mark single notification as read."""
        stmt = select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
        res = await db.execute(stmt)
        notification = res.scalar_one_or_none()
        if not notification:
            return None

        notification.is_read = True
        await db.commit()
        await db.refresh(notification)
        return NotificationOut.model_validate(notification)

    @staticmethod
    async def mark_all_as_read(
        db: AsyncSession,
        user_id: UUID,
    ) -> int:
        """Mark all unread notifications for a user as read."""
        stmt = (
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
            .values(is_read=True)
        )
        res = await db.execute(stmt)
        await db.commit()
        return res.rowcount

    @staticmethod
    async def create_notification(
        db: AsyncSession,
        user_id: UUID,
        data: NotificationCreateIn,
    ) -> NotificationOut:
        """Create a new notification for a user."""
        notification = Notification(
            id=uuid.uuid4(),
            user_id=user_id,
            title=data.title,
            message=data.message,
            type=data.type or "info",
            is_read=False,
            link=data.link,
        )
        db.add(notification)
        await db.commit()
        await db.refresh(notification)
        return NotificationOut.model_validate(notification)

    @staticmethod
    async def create_camp_notifications(
        db: AsyncSession,
        camp_title: str,
        district: str,
        start_date_str: str,
        venue: str,
        camp_id: UUID,
        category: str = "GENERAL_HEALTH_CAMP",
    ) -> int:
        """Create camp notification for patients registered in matching district without duplicate alerts."""
        from app.models.patient import Patient
        from app.models.village import Village
        from app.models.health_camp import UserCampPreference
        from app.services.tn_districts import normalize_tn_district

        canon_dist = normalize_tn_district(district) or district

        # Query users whose patient profile is in this district
        stmt = (
            select(Patient.user_id)
            .join(Village, Patient.village_id == Village.id)
            .where(func.lower(Village.district) == canon_dist.lower())
        )
        res = await db.execute(stmt)
        user_ids = set(res.scalars().all())

        # Also find users whose preferred_districts includes this district
        pref_stmt = select(UserCampPreference).where(UserCampPreference.opt_in == True)
        pref_res = await db.execute(pref_stmt)
        for pref in pref_res.scalars().all():
            if pref.preferred_districts:
                norm_prefs = [normalize_tn_district(d) for d in pref.preferred_districts]
                if canon_dist in norm_prefs:
                    user_ids.add(pref.user_id)

        notified_count = 0
        camp_link = f"/camps?camp_id={camp_id}"

        for u_id in user_ids:
            # Check if user opted out
            opt_stmt = select(UserCampPreference.opt_in).where(UserCampPreference.user_id == u_id)
            opt_res = await db.execute(opt_stmt)
            opt_in = opt_res.scalar_one_or_none()
            if opt_in is False:
                continue

            # Duplicate suppression: check if user already received notification for this camp
            dup_stmt = select(func.count(Notification.id)).where(
                Notification.user_id == u_id,
                Notification.link == camp_link
            )
            already_notified = (await db.execute(dup_stmt)).scalar_one() > 0
            if not already_notified:
                notif = Notification(
                    id=uuid.uuid4(),
                    user_id=u_id,
                    title=f"Health Camp in {canon_dist}: {camp_title[:50]}",
                    message=f"Government outreach event scheduled on {start_date_str} at {venue}. Free screening, checkups, and medicine dispensing.",
                    type="alert",
                    is_read=False,
                    link=camp_link,
                )
                db.add(notif)
                notified_count += 1

        if notified_count > 0:
            await db.commit()
        return notified_count

