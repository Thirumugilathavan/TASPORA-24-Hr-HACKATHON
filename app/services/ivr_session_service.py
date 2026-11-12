from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.ivr import IVRInteraction, IVRSession
from app.services.ivr_auth_service import normalize_phone_number


class IVRSessionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_session(
        self,
        call_sid: str,
        caller_phone: str,
        default_language: Optional[str] = None,
    ) -> IVRSession:
        """Retrieve existing active session by call_sid or create a new one."""
        norm_phone = normalize_phone_number(caller_phone)
        now = datetime.now(timezone.utc)

        stmt = select(IVRSession).where(IVRSession.call_sid == call_sid)
        res = await self.db.execute(stmt)
        session = res.scalar_one_or_none()

        timeout_delta = timedelta(minutes=settings.IVR_SESSION_TIMEOUT_MINUTES)

        if session:
            # Check for inactivity timeout
            last_at = session.last_interaction_at
            if last_at.tzinfo is None:
                last_at = last_at.replace(tzinfo=timezone.utc)

            if now - last_at > timeout_delta and session.status == "IN_PROGRESS":
                session.status = "TIMEOUT"
                session.ended_at = now
                await self.db.commit()

                # Start fresh session for the new call
                session = IVRSession(
                    call_sid=call_sid,
                    caller_phone=norm_phone,
                    language=default_language or settings.IVR_DEFAULT_LANGUAGE,
                    current_menu="LANGUAGE_SELECT",
                    menu_state={},
                    is_verified=False,
                    retry_count=0,
                    status="IN_PROGRESS",
                    started_at=now,
                    last_interaction_at=now,
                )
                self.db.add(session)
                await self.db.commit()
                await self.db.refresh(session)
            else:
                session.last_interaction_at = now
                await self.db.commit()
        else:
            session = IVRSession(
                call_sid=call_sid,
                caller_phone=norm_phone,
                language=default_language or settings.IVR_DEFAULT_LANGUAGE,
                current_menu="LANGUAGE_SELECT",
                menu_state={},
                is_verified=False,
                retry_count=0,
                status="IN_PROGRESS",
                started_at=now,
                last_interaction_at=now,
            )
            self.db.add(session)
            await self.db.commit()
            await self.db.refresh(session)

        return session

    async def get_session_by_id(self, session_id: UUID) -> Optional[IVRSession]:
        stmt = select(IVRSession).where(IVRSession.id == session_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def update_session_state(
        self,
        session: IVRSession,
        current_menu: Optional[str] = None,
        language: Optional[str] = None,
        is_verified: Optional[bool] = None,
        user_id: Optional[UUID] = None,
        patient_id: Optional[UUID] = None,
        menu_state_update: Optional[Dict[str, Any]] = None,
        reset_retry: bool = False,
        increment_retry: bool = False,
    ) -> IVRSession:
        """Update session parameters and persist state."""
        now = datetime.now(timezone.utc)
        session.last_interaction_at = now

        if current_menu is not None:
            session.current_menu = current_menu
        if language is not None:
            session.language = language
        if is_verified is not None:
            session.is_verified = is_verified
        if user_id is not None:
            session.user_id = user_id
        if patient_id is not None:
            session.patient_id = patient_id

        if menu_state_update is not None:
            current_state = dict(session.menu_state or {})
            current_state.update(menu_state_update)
            session.menu_state = current_state

        if reset_retry:
            session.retry_count = 0
        elif increment_retry:
            session.retry_count += 1

        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def record_interaction(
        self,
        session_id: UUID,
        menu_name: str,
        prompt_played: str,
        dtmf_input: Optional[str] = None,
        action_taken: Optional[str] = None,
    ) -> IVRInteraction:
        """Log an interaction step to the audit trail."""
        interaction = IVRInteraction(
            session_id=session_id,
            menu_name=menu_name,
            prompt_played=prompt_played,
            dtmf_input=dtmf_input,
            action_taken=action_taken,
        )
        self.db.add(interaction)
        await self.db.commit()
        await self.db.refresh(interaction)
        return interaction

    async def end_session(self, session: IVRSession, final_status: str = "COMPLETED") -> IVRSession:
        """Terminate call session."""
        now = datetime.now(timezone.utc)
        session.status = final_status
        session.ended_at = now
        session.last_interaction_at = now
        await self.db.commit()
        await self.db.refresh(session)
        return session
