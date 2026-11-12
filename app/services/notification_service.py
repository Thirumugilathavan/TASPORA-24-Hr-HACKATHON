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
