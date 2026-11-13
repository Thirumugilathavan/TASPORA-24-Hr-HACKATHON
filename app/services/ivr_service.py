from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.appointment import Appointment
from app.models.doctor import Doctor, DoctorSchedule
from app.models.facility import Facility
from app.models.ivr import IVRSession
from app.models.medicine import Medicine
from app.models.patient import Patient
from app.models.request import HealthcareRequest
from app.models.user import User
from app.schemas.ivr import IVRResponse
from app.schemas.shared import AppointmentStatus, AttendanceStatus, AvailabilityLabel, RequestType, Urgency
from app.services.availability_service import AvailabilityService
from app.services.distance_service import DistanceService
from app.services.doctor_service import DoctorServiceHandler
from app.services.facility_service import FacilityServiceHandler
from app.services.ivr_auth_service import IVRAuthService
from app.services.ivr_prompt_service import IVRPromptService
from app.services.ivr_session_service import IVRSessionService
from app.services.medicine_service import MedicineServiceHandler
from app.services.recommendation_service import generate_recommendations


class IVRService:
    """Core orchestration engine for telephone keypad interactions."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.session_service = IVRSessionService(db)
        self.auth_service = IVRAuthService(db)
        self.prompt_service = IVRPromptService()

    async def start_call(self, call_sid: str, caller_phone: str, language: Optional[str] = None) -> IVRResponse:
        """Handle incoming call event and initiate language selection or main menu."""
        session = await self.session_service.get_or_create_session(
            call_sid=call_sid,
            caller_phone=caller_phone,
            default_language="ta",
        )

        # Pre-identify caller to link user/patient if known
        user, patient = await self.auth_service.lookup_caller(caller_phone)
        if user:
            session.user_id = user.id
            if patient:
                session.patient_id = patient.id
            await self.db.commit()

        # Every new inbound call must begin with bilingual language selection
        session.current_menu = "LANGUAGE_SELECT"
        session.retry_count = 0
        menu_state = dict(session.menu_state or {})
        menu_state["language_confirmed"] = False
        menu_state["is_fallback_language"] = False
        menu_state["language_selection_timestamp"] = None
        session.menu_state = menu_state
        await self.db.commit()

        # Welcome prompt offering Tamil (1) or English (2)
        welcome_text = self.prompt_service.get_language_select_prompt()
        await self.session_service.record_interaction(
            session_id=session.id,
            menu_name="LANGUAGE_SELECT",
            prompt_played=welcome_text,
            action_taken="CALL_INITIATED_LANGUAGE_SELECT",
        )

        return IVRResponse(
            call_sid=session.call_sid,
            speak_text=welcome_text,
            gather_dtmf=True,
            num_digits=1,
            timeout_seconds=6,
            current_menu="LANGUAGE_SELECT",
            language="ta",
            is_verified=session.is_verified,
        )

    async def process_dtmf(self, call_sid: str, digits: str) -> IVRResponse:
        """Route keypad DTMF digits through the menu state machine."""
        return await self.process_input(call_sid=call_sid, digits=digits, speech_text=None)

    async def process_input(
        self,
        call_sid: str,
        digits: Optional[str] = None,
        speech_text: Optional[str] = None,
    ) -> IVRResponse:
        """Route keypad DTMF digits or spoken speech input through menu state machine."""
        clean_digits = (digits or "").strip()
        clean_speech = (speech_text or "").strip()

        # Retrieve active session
        stmt = select(IVRSession).where(IVRSession.call_sid == call_sid)
        res = await self.db.execute(stmt)
        session = res.scalar_one_or_none()

        if not session or session.status != "IN_PROGRESS":
            goodbye_text = self.prompt_service.get_goodbye("ta")
            return IVRResponse(
                call_sid=call_sid,
                speak_text=goodbye_text,
                hangup=True,
                session_status="COMPLETED",
            )

        lang = session.language or "ta"
        menu = session.current_menu
        state = dict(session.menu_state or {})

        # Check session duration / timeout limit
        max_duration = getattr(settings, "TELEPHONY_MAX_CALL_DURATION", 600)
        if session.started_at:
            now_utc = datetime.now(timezone.utc)
            started = session.started_at if session.started_at.tzinfo else session.started_at.replace(tzinfo=timezone.utc)
            if (now_utc - started).total_seconds() > max_duration:
                goodbye = self.prompt_service.get_goodbye(lang)
                await self.session_service.end_session(session, "TIMEOUT")
                return IVRResponse(
                    call_sid=call_sid,
                    speak_text=goodbye,
                    hangup=True,
                    session_status="COMPLETED",
                    language=lang,
                )

        # Check language change requests from speech or keypad
        if clean_speech and any(kw in clean_speech.lower() for kw in [
            "change language", "switch language", "change to english", "change to tamil",
            "மொழியை மாற்ற", "மொழி மாற்றம்", "மொழியை மாற்ற வேண்டும்"
        ]):
            return await self._show_language_switch_menu(session)

        # '*' from MAIN_MENU offers language change:
        if clean_digits == "*" and menu == "MAIN_MENU":
            return await self._show_language_switch_menu(session)

        # Universal Key Controls:
        # '9': Hangup safely
        if clean_digits == "9" and menu != "AUTH_PIN":
            goodbye_text = self.prompt_service.get_goodbye(lang)
            await self.session_service.end_session(session, "COMPLETED")
            await self.session_service.record_interaction(session.id, menu, goodbye_text, clean_digits, "HANGUP")
            return IVRResponse(
                call_sid=call_sid,
                speak_text=goodbye_text,
                hangup=True,
                session_status="COMPLETED",
                language=lang,
            )

        # '0': From Main Menu -> Support Transfer / Health Desk; from other menus -> Return to Main Menu
        if clean_digits == "0":
            if menu == "MAIN_MENU":
                return await self._handle_call_transfer(session, lang)
            elif menu not in ("LANGUAGE_SELECT", "AUTH_PIN"):
                return await self._show_main_menu(session, lang)

        if clean_digits == "*" and menu not in ("LANGUAGE_SELECT", "AUTH_PIN"):
            return await self._show_main_menu(session, lang)

        # '8': Repeat current menu
        if clean_digits == "8" and menu != "AUTH_PIN":
            return await self._repeat_current_menu(session, lang)

        # Route by menu state
        if menu == "LANGUAGE_SELECT":
            return await self._handle_language_select(session, clean_digits, clean_speech)
        elif menu == "MAIN_MENU":
            # If conversational speech was provided, execute AI Assistant
            if clean_speech and not clean_digits:
                return await self._handle_conversational_ai(session, clean_speech, lang, state)
            return await self._handle_main_menu(session, clean_digits, lang)
        elif menu == "AUTH_PIN":
            return await self._handle_auth_pin(session, clean_digits, lang, state)
        elif menu == "FACILITIES_LIST":
            return await self._handle_facilities_list(session, clean_digits, lang)
        elif menu == "MEDICINE_SELECT":
            return await self._handle_medicine_select(session, clean_digits, lang)
        elif menu == "DOCTOR_CHECK":
            return await self._handle_doctor_check(session, clean_digits, lang)
        elif menu == "REQUEST_TYPE_SELECT":
            return await self._handle_request_type(session, clean_digits, lang, state)
        elif menu == "REQUEST_URGENCY_SELECT":
            return await self._handle_request_urgency(session, clean_digits, lang, state)
        elif menu == "REQUEST_CONFIRMED":
            return await self._handle_request_confirmed(session, clean_digits, lang, state)
        elif menu == "RECOMMENDATIONS":
            return await self._handle_recommendations(session, clean_digits, lang, state)
        elif menu == "APPOINTMENT_SLOT_SELECT":
            return await self._handle_appointment_slot(session, clean_digits, lang, state)
        elif menu == "STATUS_MENU":
            return await self._handle_status_menu(session, clean_digits, lang, state)
        elif menu == "CANCEL_CONFIRM":
            return await self._handle_cancel_confirm(session, clean_digits, lang, state)
        else:
            return await self._show_main_menu(session, lang)

    # -------------------------------------------------------------------------
    # State Handlers
    # -------------------------------------------------------------------------

    async def _show_language_switch_menu(self, session: IVRSession) -> IVRResponse:
        """Prompts caller to change language while preserving conversation history."""
        session.current_menu = "LANGUAGE_SELECT"
        session.retry_count = 0
        menu_state = dict(session.menu_state or {})
        menu_state["previous_language"] = session.language
        session.menu_state = menu_state
        await self.db.commit()

        switch_prompt = self.prompt_service.get_language_switch_prompt()
        await self.session_service.record_interaction(
            session_id=session.id,
            menu_name="LANGUAGE_SELECT",
            prompt_played=switch_prompt,
            action_taken="CHANGE_LANGUAGE_REQUESTED",
        )

        return IVRResponse(
            call_sid=session.call_sid,
            speak_text=switch_prompt,
            gather_dtmf=True,
            num_digits=1,
            timeout_seconds=6,
            current_menu="LANGUAGE_SELECT",
            language=session.language or "ta",
            is_verified=session.is_verified,
        )

    async def _handle_language_select(
        self,
        session: IVRSession,
        digits: Optional[str] = None,
        speech_text: Optional[str] = None,
    ) -> IVRResponse:
        """Select Tamil (1) or English (2) via DTMF or speech."""
        clean_digits = (digits or "").strip()
        clean_speech = (speech_text or "").strip().lower()

        selected_lang = None
        if clean_digits == "1" or any(w in clean_speech for w in ["tamil", "தமிழ்", "ஒன்று", "one"]):
            selected_lang = "ta"
        elif clean_digits == "2" or any(w in clean_speech for w in ["english", "ஆங்கிலம்", "இரண்டு", "two"]):
            selected_lang = "en"

        max_retries = getattr(settings, "IVR_LANGUAGE_MAX_RETRIES", 3)

        if selected_lang:
            session.language = selected_lang
            session.current_menu = "MAIN_MENU"
            session.retry_count = 0
            menu_state = dict(session.menu_state or {})
            menu_state["selected_language"] = selected_lang
            menu_state["language_confirmed"] = True
            menu_state["language_selection_timestamp"] = datetime.now(timezone.utc).isoformat()
            menu_state["is_fallback_language"] = False
            session.menu_state = menu_state
            await self.db.commit()

            # Record interaction
            action = f"LANGUAGE_SELECTED_{selected_lang.upper()}"
            await self.session_service.record_interaction(
                session.id, "LANGUAGE_SELECT", f"Selected {selected_lang}", clean_digits or clean_speech, action
            )

            welcome_msg = self.prompt_service.get_language_welcome_message(selected_lang)
            return await self._show_main_menu(session, selected_lang, prefix_welcome=welcome_msg)

        # No input (empty digits and empty speech)
        if not clean_digits and not clean_speech:
            session.retry_count += 1
            if session.retry_count < max_retries:
                retry_msg = self.prompt_service.get_language_timeout_prompt()
                await self.session_service.record_interaction(session.id, "LANGUAGE_SELECT", retry_msg, "", "RETRY_NO_INPUT")
                await self.db.commit()
                return IVRResponse(
                    call_sid=session.call_sid,
                    speak_text=retry_msg,
                    gather_dtmf=True,
                    num_digits=1,
                    current_menu="LANGUAGE_SELECT",
                    language=session.language or "ta",
                )
            else:
                # Documented Fallback to Tamil
                return await self._apply_language_fallback(session)

        # Invalid input entered
        session.retry_count += 1
        if session.retry_count < max_retries:
            retry_msg = self.prompt_service.get_language_invalid_prompt()
            await self.session_service.record_interaction(session.id, "LANGUAGE_SELECT", retry_msg, clean_digits or clean_speech, "RETRY_INVALID_INPUT")
            await self.db.commit()
            return IVRResponse(
                call_sid=session.call_sid,
                speak_text=retry_msg,
                gather_dtmf=True,
                num_digits=1,
                current_menu="LANGUAGE_SELECT",
                language=session.language or "ta",
            )
        else:
            # Documented Fallback to Tamil
            return await self._apply_language_fallback(session)

    async def _apply_language_fallback(self, session: IVRSession) -> IVRResponse:
        """Apply documented fallback after retries exhausted without misclassifying caller."""
        fallback_lang = getattr(settings, "IVR_LANGUAGE_FALLBACK", "ta")
        session.language = fallback_lang
        session.current_menu = "MAIN_MENU"
        session.retry_count = 0
        menu_state = dict(session.menu_state or {})
        menu_state["selected_language"] = fallback_lang
        menu_state["language_confirmed"] = False  # Caller did not explicitly select it
        menu_state["is_fallback_language"] = True
        menu_state["fallback_reason"] = "MAX_RETRIES_EXCEEDED"
        menu_state["language_selection_timestamp"] = datetime.now(timezone.utc).isoformat()
        session.menu_state = menu_state
        await self.db.commit()

        fallback_announcement = self.prompt_service.get_language_fallback_announcement(fallback_lang)
        await self.session_service.record_interaction(
            session.id, "LANGUAGE_SELECT", fallback_announcement, None, "FALLBACK_DEFAULT_LANGUAGE"
        )
        return await self._show_main_menu(session, fallback_lang, prefix_welcome=fallback_announcement)

    async def _handle_conversational_ai(
        self,
        session: IVRSession,
        speech_text: str,
        lang: str,
        state: Dict[str, Any],
    ) -> IVRResponse:
        """Executes closed-loop AI turn with caller's explicit language preference."""
        from app.ai.agent import NalamAIAgent
        from app.ai.schemas import AIChatRequest

        agent = NalamAIAgent()
        ai_req = AIChatRequest(
            message=speech_text,
            language=lang,  # Explicitly pass selected language
            conversation_id=str(session.id),
            location_context=state.get("resolved_location") or "Namakkal",
        )
        ai_resp = await agent.execute_turn(ai_req, self.db)
        await self.session_service.record_interaction(
            session.id, "MAIN_MENU", ai_resp.response_text, speech_text, "AI_CONVERSATION_TURN"
        )
        return IVRResponse(
            call_sid=session.call_sid,
            speak_text=ai_resp.response_text,
            gather_dtmf=True,
            num_digits=1,
            timeout_seconds=8,
            current_menu="MAIN_MENU",
            language=lang,
            is_verified=session.is_verified,
        )

    async def _show_main_menu(self, session: IVRSession, lang: str, prefix_welcome: Optional[str] = None) -> IVRResponse:
        """Display and read the top-level Main Menu."""
        session.current_menu = "MAIN_MENU"
        session.retry_count = 0
        await self.db.commit()

        menu_text = self.prompt_service.get_main_menu(lang)
        full_text = f"{prefix_welcome} {menu_text}" if prefix_welcome else menu_text
        await self.session_service.record_interaction(session.id, "MAIN_MENU", full_text, None, "MENU_SHOWN")

        return IVRResponse(
            call_sid=session.call_sid,
            speak_text=full_text,
            gather_dtmf=True,
            num_digits=1,
            timeout_seconds=8,
            current_menu="MAIN_MENU",
            language=lang,
            is_verified=session.is_verified,
        )

    async def _handle_main_menu(self, session: IVRSession, digits: str, lang: str) -> IVRResponse:
        """Route main menu options 1 to 7."""
        if digits == "1":
            # 1: Find nearby healthcare facilities
            return await self._show_facilities(session, lang)
        elif digits == "2":
            # 2: Check doctor availability
            return await self._show_doctor_check(session, lang)
        elif digits == "3":
            # 3: Check medicine stock
            return await self._show_medicine_catalog(session, lang)
        elif digits == "4":
            # 4: Create healthcare request (requires authentication)
            if not session.is_verified:
                return await self._prompt_pin(session, lang, target_menu="REQUEST_TYPE_SELECT")
            return await self._show_request_type_menu(session, lang)
        elif digits == "5":
            # 5: Check existing request and appointment status (requires authentication)
            if not session.is_verified:
                return await self._prompt_pin(session, lang, target_menu="STATUS_MENU")
            return await self._show_status_menu(session, lang)
        elif digits == "6":
            # 6: Book an appointment (requires authentication)
            if not session.is_verified:
                return await self._prompt_pin(session, lang, target_menu="APPOINTMENT_SLOT_SELECT")
            return await self._show_appointment_flow(session, lang)
        elif digits == "7":
            # 7: Emergency guidance (immediate, unauthenticated)
            emergency_text = self.prompt_service.get_emergency_message(lang)
            await self.session_service.record_interaction(session.id, "EMERGENCY_GUIDANCE", emergency_text, digits, "EMERGENCY_SERVED")
            return IVRResponse(
                call_sid=session.call_sid,
                speak_text=emergency_text,
                gather_dtmf=True,
                num_digits=1,
                current_menu="MAIN_MENU",
                language=lang,
                is_verified=session.is_verified,
            )
        elif digits == "0":
            # 0: Support transfer / Health Desk operator
            return await self._handle_call_transfer(session, lang)
        else:
            # Invalid input on main menu
            session.retry_count += 1
            if session.retry_count >= 3:
                goodbye = self.prompt_service.get_goodbye(lang)
                await self.session_service.end_session(session, "FAILED")
                return IVRResponse(call_sid=session.call_sid, speak_text=goodbye, hangup=True)

            inv_text = f"{self.prompt_service.get_invalid_input(lang)} {self.prompt_service.get_main_menu(lang)}"
            return IVRResponse(
                call_sid=session.call_sid,
                speak_text=inv_text,
                gather_dtmf=True,
                num_digits=1,
                current_menu="MAIN_MENU",
                language=lang,
                is_verified=session.is_verified,
            )

    async def _handle_call_transfer(self, session: IVRSession, lang: str) -> IVRResponse:
        """Transfer call to configured human health worker desk or play unavailable message."""
        if settings.IVR_ENABLE_CALL_TRANSFER and settings.IVR_TRANSFER_PHONE_NUMBER:
            transfer_text = self.prompt_service.get_call_transfer_prompt(lang)
            await self.session_service.record_interaction(session.id, "CALL_TRANSFER", transfer_text, "0", "TRANSFER_INITIATED")
            return IVRResponse(
                call_sid=session.call_sid,
                speak_text=transfer_text,
                gather_dtmf=False,
                transfer_number=settings.IVR_TRANSFER_PHONE_NUMBER,
                current_menu="CALL_TRANSFER",
                language=lang,
                is_verified=session.is_verified,
            )
        else:
            unavail_text = self.prompt_service.get_call_transfer_unavailable(lang)
            await self.session_service.record_interaction(session.id, "CALL_TRANSFER", unavail_text, "0", "TRANSFER_UNAVAILABLE")
            return IVRResponse(
                call_sid=session.call_sid,
                speak_text=unavail_text,
                gather_dtmf=True,
                num_digits=1,
                current_menu="MAIN_MENU",
                language=lang,
                is_verified=session.is_verified,
            )

    # -------------------------------------------------------------------------
    # Sub-Flow: Security PIN Verification
    # -------------------------------------------------------------------------

    async def _prompt_pin(self, session: IVRSession, lang: str, target_menu: str) -> IVRResponse:
        """Request 4-digit PIN before proceeding to protected menus."""
        session.current_menu = "AUTH_PIN"
        session.menu_state = {**dict(session.menu_state or {}), "target_menu": target_menu}
        session.retry_count = 0
        await self.db.commit()

        pin_text = self.prompt_service.get_pin_prompt(lang)
        await self.session_service.record_interaction(session.id, "AUTH_PIN", pin_text, None, "PIN_REQUESTED")

        return IVRResponse(
            call_sid=session.call_sid,
            speak_text=pin_text,
            gather_dtmf=True,
            num_digits=4,
            finish_on_key="#",
            timeout_seconds=10,
            current_menu="AUTH_PIN",
            language=lang,
            is_verified=False,
        )

    async def _handle_auth_pin(self, session: IVRSession, digits: str, lang: str, state: Dict[str, Any]) -> IVRResponse:
        """Verify entered PIN."""
        if digits in ("0", "*"):
            return await self._show_main_menu(session, lang)

        is_valid, err_code = await self.auth_service.verify_pin(session.caller_phone, digits)

        if is_valid:
            session.is_verified = True
            session.retry_count = 0
            user, patient = await self.auth_service.lookup_caller(session.caller_phone)
            if user:
                session.user_id = user.id
            if patient:
                session.patient_id = patient.id
            await self.db.commit()

            target_menu = state.get("target_menu", "MAIN_MENU")
            if target_menu == "REQUEST_TYPE_SELECT":
                return await self._show_request_type_menu(session, lang)
            elif target_menu == "STATUS_MENU":
                return await self._show_status_menu(session, lang)
            elif target_menu == "APPOINTMENT_SLOT_SELECT":
                return await self._show_appointment_flow(session, lang)
            else:
                return await self._show_main_menu(session, lang)
        else:
            if err_code == "LOCKED":
                lock_text = self.prompt_service.get_pin_locked(lang)
                await self.session_service.end_session(session, "FAILED")
                return IVRResponse(call_sid=session.call_sid, speak_text=lock_text, hangup=True, is_verified=False)

            session.retry_count += 1
            remaining = max(0, settings.IVR_MAX_AUTH_ATTEMPTS - session.retry_count)
            if session.retry_count >= settings.IVR_MAX_AUTH_ATTEMPTS:
                lock_text = self.prompt_service.get_pin_locked(lang)
                await self.session_service.end_session(session, "FAILED")
                return IVRResponse(call_sid=session.call_sid, speak_text=lock_text, hangup=True, is_verified=False)

            fail_text = self.prompt_service.get_pin_invalid(remaining, lang)
            return IVRResponse(
                call_sid=session.call_sid,
                speak_text=fail_text,
                gather_dtmf=True,
                num_digits=4,
                finish_on_key="#",
                timeout_seconds=10,
                current_menu="AUTH_PIN",
                language=lang,
                is_verified=False,
            )

    # -------------------------------------------------------------------------
    # Sub-Flow: Facilities Discovery
    # -------------------------------------------------------------------------

    async def _show_facilities(self, session: IVRSession, lang: str) -> IVRResponse:
        """Fetch nearby facilities and read them out."""
        handler = FacilityServiceHandler(self.db)
        # Use patient's village if available
        village_id = None
        if session.patient_id:
            p_stmt = select(Patient).where(Patient.id == session.patient_id)
            p_res = await self.db.execute(p_stmt)
            p = p_res.scalar_one_or_none()
            if p:
                village_id = p.village_id

        facilities, _ = await handler.list_facilities(village_id=village_id, limit=3)
        if not facilities and village_id:
            # Fallback to general list if no facilities in that exact village
            facilities, _ = await handler.list_facilities(limit=3)

        fac_dicts = []
        dist_service = DistanceService(self.db)
        for f in facilities:
            dist = None
            if village_id:
                try:
                    dist = await dist_service.calculate_distance(village_id, f.id)
                except Exception:
                    dist = None

            fac_dicts.append({
                "id": str(f.id),
                "name": f.name,
                "facility_type": f.facility_type,
                "distance_km": dist,
            })

        session.current_menu = "FACILITIES_LIST"
        session.menu_state = {**dict(session.menu_state or {}), "facilities": fac_dicts}
        await self.db.commit()

        prompt_text = self.prompt_service.get_facilities_prompt(fac_dicts, lang)
        await self.session_service.record_interaction(session.id, "FACILITIES_LIST", prompt_text, "1", "FACILITIES_READ")

        return IVRResponse(
            call_sid=session.call_sid,
            speak_text=prompt_text,
            gather_dtmf=True,
            num_digits=1,
            timeout_seconds=10,
            current_menu="FACILITIES_LIST",
            language=lang,
            is_verified=session.is_verified,
        )

    async def _handle_facilities_list(self, session: IVRSession, digits: str, lang: str) -> IVRResponse:
        return await self._show_main_menu(session, lang)

    # -------------------------------------------------------------------------
    # Sub-Flow: Doctor Availability
    # -------------------------------------------------------------------------

    async def _show_doctor_check(self, session: IVRSession, lang: str) -> IVRResponse:
        """Check doctor availability today at the primary or first facility."""
        doc_stmt = select(Doctor).options(selectinload(Doctor.facility))
        doc_res = await self.db.execute(doc_stmt)
        doctor = doc_res.scalars().first()

        today = date.today()
        today_str = "இன்று" if lang == "ta" else "today"

        if not doctor:
            msg = (
                "மருத்துவர் விவரங்கள் எதுவும் கிடைக்கவில்லை. முதன்மை மெனுவிற்கு செல்ல 0-ஐ அழுத்தவும்."
                if lang == "ta"
                else "No doctor records found. Press 0 for main menu."
            )
            return IVRResponse(call_sid=session.call_sid, speak_text=msg, gather_dtmf=True, num_digits=1)

        doc_handler = DoctorServiceHandler(self.db)
        sched = await doc_handler.get_doctor_schedule(doctor.id, today)
        status = sched.attendance_status if sched else AttendanceStatus.UNKNOWN

        fac_name = doctor.facility.name if doctor.facility else "Primary Clinic"
        prompt_text = self.prompt_service.get_doctor_status_prompt(doctor.name, fac_name, status, today_str, lang)

        session.current_menu = "DOCTOR_CHECK"
        await self.db.commit()
        await self.session_service.record_interaction(session.id, "DOCTOR_CHECK", prompt_text, "2", "DOCTOR_STATUS_ANNOUNCED")

        return IVRResponse(
            call_sid=session.call_sid,
            speak_text=prompt_text,
            gather_dtmf=True,
            num_digits=1,
            timeout_seconds=10,
            current_menu="DOCTOR_CHECK",
            language=lang,
            is_verified=session.is_verified,
        )

    async def _handle_doctor_check(self, session: IVRSession, digits: str, lang: str) -> IVRResponse:
        return await self._show_main_menu(session, lang)

    # -------------------------------------------------------------------------
    # Sub-Flow: Medicine Stock Intelligence
    # -------------------------------------------------------------------------

    async def _show_medicine_catalog(self, session: IVRSession, lang: str) -> IVRResponse:
        """Show list of common medicines to check availability."""
        med_stmt = select(Medicine).limit(4)
        med_res = await self.db.execute(med_stmt)
        medicines = list(med_res.scalars().all())

        med_dicts = [{"id": str(m.id), "name": m.name} for m in medicines]
        session.current_menu = "MEDICINE_SELECT"
        session.menu_state = {**dict(session.menu_state or {}), "medicines": med_dicts}
        await self.db.commit()

        prompt_text = self.prompt_service.get_medicine_select_prompt(med_dicts, lang)
        await self.session_service.record_interaction(session.id, "MEDICINE_SELECT", prompt_text, "3", "CATALOGUE_READ")

        return IVRResponse(
            call_sid=session.call_sid,
            speak_text=prompt_text,
            gather_dtmf=True,
            num_digits=1,
            timeout_seconds=8,
            current_menu="MEDICINE_SELECT",
            language=lang,
            is_verified=session.is_verified,
        )

    async def _handle_medicine_select(self, session: IVRSession, digits: str, lang: str) -> IVRResponse:
        state = dict(session.menu_state or {})
        meds = state.get("medicines", [])

        try:
            choice_idx = int(digits) - 1
            if 0 <= choice_idx < len(meds):
                selected_med = meds[choice_idx]
                med_id = UUID(selected_med["id"])
                med_name = selected_med["name"]

                # Get first available facility
                f_stmt = select(Facility).limit(1)
                f_res = await self.db.execute(f_stmt)
                fac = f_res.scalar_one_or_none()

                if fac:
                    fac_name = fac.name
                    fac_id = fac.id
                else:
                    fac_name = "அருகிலுள்ள மருந்தகம்" if lang == "ta" else "Nearest Pharmacy"
                    fac_id = uuid4()

                # Calculate probabilistic belief
                service = AvailabilityService(self.db)
                p_avail, conf, label, _, _ = await service.calculate_belief(fac_id, med_id)

                result_text = self.prompt_service.get_medicine_stock_result(
                    med_name, fac_name, label, p_avail, conf, lang
                )
                session.current_menu = "MAIN_MENU"
                await self.db.commit()
                await self.session_service.record_interaction(session.id, "MEDICINE_RESULT", result_text, digits, "STOCK_ANNOUNCED")

                return IVRResponse(
                    call_sid=session.call_sid,
                    speak_text=result_text,
                    gather_dtmf=True,
                    num_digits=1,
                    timeout_seconds=10,
                    current_menu="MAIN_MENU",
                    language=lang,
                    is_verified=session.is_verified,
                )
        except Exception:
            pass

        return await self._show_main_menu(session, lang)

    # -------------------------------------------------------------------------
    # Sub-Flow: Create Healthcare Request
    # -------------------------------------------------------------------------

    async def _show_request_type_menu(self, session: IVRSession, lang: str) -> IVRResponse:
        session.current_menu = "REQUEST_TYPE_SELECT"
        await self.db.commit()

        prompt_text = self.prompt_service.get_request_type_menu(lang)
        await self.session_service.record_interaction(session.id, "REQUEST_TYPE_SELECT", prompt_text, None, "REQUEST_TYPES_READ")

        return IVRResponse(
            call_sid=session.call_sid,
            speak_text=prompt_text,
            gather_dtmf=True,
            num_digits=1,
            timeout_seconds=8,
            current_menu="REQUEST_TYPE_SELECT",
            language=lang,
            is_verified=session.is_verified,
        )

    async def _handle_request_type(self, session: IVRSession, digits: str, lang: str, state: Dict[str, Any]) -> IVRResponse:
        type_mapping = {
            "1": (RequestType.CONSULTATION, "மருத்துவ ஆலோசனை" if lang == "ta" else "Consultation", False),
            "2": (RequestType.REFILL, "மருந்து மறு நிரப்பல்" if lang == "ta" else "Medicine Refill", False),
            "3": (RequestType.CHECKUP, "பொது பரிசோதனை" if lang == "ta" else "General Checkup", False),
            "4": (RequestType.DIAGNOSTIC, "ஆய்வக பரிசோதனை" if lang == "ta" else "Diagnostics", False),
            "5": (RequestType.CONSULTATION, "ஆஷா பணியாளர் உதவி" if lang == "ta" else "ASHA Worker Callback", True),
        }

        if digits not in type_mapping:
            return await self._show_request_type_menu(session, lang)

        req_type, type_name, is_asha = type_mapping[digits]
        session.current_menu = "REQUEST_URGENCY_SELECT"
        session.menu_state = {
            **state,
            "selected_request_type": req_type.value,
            "request_type_name": type_name,
            "is_asha_request": is_asha,
        }
        await self.db.commit()

        prompt_text = self.prompt_service.get_request_urgency_menu(type_name, lang)
        return IVRResponse(
            call_sid=session.call_sid,
            speak_text=prompt_text,
            gather_dtmf=True,
            num_digits=1,
            timeout_seconds=8,
            current_menu="REQUEST_URGENCY_SELECT",
            language=lang,
            is_verified=session.is_verified,
        )

    async def _handle_request_urgency(self, session: IVRSession, digits: str, lang: str, state: Dict[str, Any]) -> IVRResponse:
        urgency = Urgency.PRIORITY if digits == "2" else Urgency.NORMAL
        req_type_str = state.get("selected_request_type", "CONSULTATION")
        req_type = RequestType(req_type_str)
        is_asha = state.get("is_asha_request", False)

        # Resolve patient ID
        patient_id = session.patient_id or session.user_id
        if not patient_id:
            # Self-healing fallback if user ID was not attached
            user, patient = await self.auth_service.lookup_caller(session.caller_phone)
            patient_id = patient.id if patient else (user.id if user else uuid4())
            session.patient_id = patient_id

        # Create healthcare request
        desc = (
            f"IVR phone request: Patient requested ASHA worker callback assistance ({lang})"
            if is_asha
            else f"IVR phone request ({lang})"
        )
        req = HealthcareRequest(
            patient_id=patient_id,
            request_type=req_type,
            urgency=urgency,
            description=desc,
            status="PENDING",
        )
        self.db.add(req)
        await self.db.commit()
        await self.db.refresh(req)

        session.current_menu = "REQUEST_CONFIRMED"
        session.menu_state = {**state, "created_request_id": str(req.id)}
        await self.db.commit()

        if is_asha:
            prompt_text = self.prompt_service.get_asha_callback_prompt(lang)
            await self.session_service.record_interaction(session.id, "ASHA_CALLBACK_CONFIRMED", prompt_text, digits, "ASHA_REQUEST_CREATED")
        else:
            prompt_text = self.prompt_service.get_request_created(str(req.id), lang)
            await self.session_service.record_interaction(session.id, "REQUEST_CONFIRMED", prompt_text, digits, "REQUEST_CREATED")

        return IVRResponse(
            call_sid=session.call_sid,
            speak_text=prompt_text,
            gather_dtmf=True,
            num_digits=1,
            timeout_seconds=8,
            current_menu="REQUEST_CONFIRMED",
            language=lang,
            is_verified=session.is_verified,
        )

    async def _handle_request_confirmed(self, session: IVRSession, digits: str, lang: str, state: Dict[str, Any]) -> IVRResponse:
        if digits == "1":
            # Offer recommendations
            return await self._show_recommendations(session, lang, state)
        return await self._show_main_menu(session, lang)

    # -------------------------------------------------------------------------
    # Sub-Flow: Recommendations
    # -------------------------------------------------------------------------

    async def _show_recommendations(self, session: IVRSession, lang: str, state: Dict[str, Any]) -> IVRResponse:
        req_id_str = state.get("created_request_id")
        if not req_id_str:
            return await self._show_main_menu(session, lang)

        req_stmt = select(HealthcareRequest).where(HealthcareRequest.id == UUID(req_id_str))
        req_res = await self.db.execute(req_stmt)
        req = req_res.scalar_one_or_none()

        if not req:
            return await self._show_main_menu(session, lang)

        # Generate recommendations using recommendation engine
        # Eager load live facilities
        f_stmt = select(Facility).options(selectinload(Facility.services))
        f_res = await self.db.execute(f_stmt)
        db_facs = list(f_res.scalars().all())

        cand_dicts = []
        for f in db_facs:
            cand_dicts.append({
                "id": f.id,
                "name": f.name,
                "facility_type": f.facility_type,
                "services": [s.service_name for s in f.services],
                "base_cost": 25 if f.facility_type == "CHC" else 15,
                "cost_per_km": 3,
                "latitude": f.latitude,
                "longitude": f.longitude,
            })

        recs = generate_recommendations(req, candidate_facilities=cand_dicts if cand_dicts else None)
        rec_items = [r.model_dump(mode="json") for r in recs]

        session.current_menu = "RECOMMENDATIONS"
        session.menu_state = {**state, "recommendations": rec_items}
        await self.db.commit()

        prompt_text = self.prompt_service.get_recommendation_readout(rec_items, lang)
        await self.session_service.record_interaction(session.id, "RECOMMENDATIONS", prompt_text, "1", "RECOMMENDATIONS_READ")

        return IVRResponse(
            call_sid=session.call_sid,
            speak_text=prompt_text,
            gather_dtmf=True,
            num_digits=1,
            timeout_seconds=10,
            current_menu="RECOMMENDATIONS",
            language=lang,
            is_verified=session.is_verified,
        )

    async def _handle_recommendations(self, session: IVRSession, digits: str, lang: str, state: Dict[str, Any]) -> IVRResponse:
        if digits == "1":
            # Book appointment at recommended facility
            recs = state.get("recommendations", [])
            if recs:
                top_fac = recs[0]
                session.menu_state = {
                    **state,
                    "target_facility_id": top_fac.get("facility_id"),
                    "target_facility_name": top_fac.get("facility_name"),
                }
                await self.db.commit()
                return await self._show_appointment_slot_menu(session, lang, top_fac.get("facility_name", "Clinic"))
        return await self._show_main_menu(session, lang)

    # -------------------------------------------------------------------------
    # Sub-Flow: Appointment Booking & Conflict Handling
    # -------------------------------------------------------------------------

    async def _show_appointment_flow(self, session: IVRSession, lang: str) -> IVRResponse:
        f_stmt = select(Facility).limit(1)
        f_res = await self.db.execute(f_stmt)
        fac = f_res.scalar_one_or_none()

        fac_id = str(fac.id) if fac else str(uuid4())
        fac_name = fac.name if fac else ("கிராமப்புற மருத்துவ மையம்" if lang == "ta" else "Rural Health Centre")

        session.menu_state = {
            **dict(session.menu_state or {}),
            "target_facility_id": fac_id,
            "target_facility_name": fac_name,
        }
        await self.db.commit()
        return await self._show_appointment_slot_menu(session, lang, fac_name)

    async def _show_appointment_slot_menu(self, session: IVRSession, lang: str, fac_name: str) -> IVRResponse:
        session.current_menu = "APPOINTMENT_SLOT_SELECT"
        await self.db.commit()

        prompt_text = self.prompt_service.get_slot_selection_menu(fac_name, lang)
        await self.session_service.record_interaction(session.id, "APPOINTMENT_SLOT_SELECT", prompt_text, None, "SLOTS_SHOWN")

        return IVRResponse(
            call_sid=session.call_sid,
            speak_text=prompt_text,
            gather_dtmf=True,
            num_digits=1,
            timeout_seconds=8,
            current_menu="APPOINTMENT_SLOT_SELECT",
            language=lang,
            is_verified=session.is_verified,
        )

    async def _handle_appointment_slot(self, session: IVRSession, digits: str, lang: str, state: Dict[str, Any]) -> IVRResponse:
        time_mapping = {
            "1": (time(10, 0), "10:00 AM"),
            "2": (time(12, 0), "12:00 PM"),
            "3": (time(14, 0), "02:00 PM"),
        }

        if digits not in time_mapping:
            return await self._show_main_menu(session, lang)

        appt_time, time_label = time_mapping[digits]
        tomorrow = date.today() + timedelta(days=1)
        fac_id_str = state.get("target_facility_id")
        fac_name = state.get("target_facility_name", "Clinic")
        facility_id = UUID(fac_id_str) if fac_id_str else uuid4()
        patient_id = session.patient_id or session.user_id

        # Check for slot conflict (double booking)
        conflict_stmt = select(Appointment).where(
            Appointment.facility_id == facility_id,
            Appointment.appointment_date == tomorrow,
            Appointment.appointment_time == appt_time,
            Appointment.status != AppointmentStatus.CANCELLED,
        )
        c_res = await self.db.execute(conflict_stmt)
        if c_res.scalar_one_or_none():
            conflict_msg = self.prompt_service.get_slot_conflict_message(lang)
            return IVRResponse(
                call_sid=session.call_sid,
                speak_text=conflict_msg,
                gather_dtmf=True,
                num_digits=1,
                current_menu="APPOINTMENT_SLOT_SELECT",
                language=lang,
                is_verified=session.is_verified,
            )

        # Attempt to insert appointment
        appt = Appointment(
            patient_id=patient_id,
            facility_id=facility_id,
            doctor_id=None,
            request_id=UUID(state.get("created_request_id")) if state.get("created_request_id") else None,
            appointment_date=tomorrow,
            appointment_time=appt_time,
            status=AppointmentStatus.BOOKED,
        )
        self.db.add(appt)
        try:
            await self.db.commit()
            await self.db.refresh(appt)
        except IntegrityError:
            await self.db.rollback()
            conflict_msg = self.prompt_service.get_slot_conflict_message(lang)
            return IVRResponse(
                call_sid=session.call_sid,
                speak_text=conflict_msg,
                gather_dtmf=True,
                num_digits=1,
                current_menu="APPOINTMENT_SLOT_SELECT",
                language=lang,
                is_verified=session.is_verified,
            )

        session.current_menu = "MAIN_MENU"
        await self.db.commit()

        confirmed_text = self.prompt_service.get_appointment_booked(
            str(appt.id), fac_name, time_label, tomorrow.isoformat(), lang
        )
        await self.session_service.record_interaction(session.id, "APPOINTMENT_CONFIRMED", confirmed_text, digits, "APPOINTMENT_BOOKED")

        return IVRResponse(
            call_sid=session.call_sid,
            speak_text=confirmed_text,
            gather_dtmf=True,
            num_digits=1,
            timeout_seconds=8,
            current_menu="MAIN_MENU",
            language=lang,
            is_verified=session.is_verified,
        )

    # -------------------------------------------------------------------------
    # Sub-Flow: Request and Appointment Status & Cancellation
    # -------------------------------------------------------------------------

    async def _show_status_menu(self, session: IVRSession, lang: str) -> IVRResponse:
        patient_id = session.patient_id or session.user_id

        # Query requests
        r_stmt = select(HealthcareRequest).where(HealthcareRequest.patient_id == patient_id)
        r_res = await self.db.execute(r_stmt)
        requests = list(r_res.scalars().all())

        # Query appointments
        a_stmt = select(Appointment).where(
            Appointment.patient_id == patient_id,
            Appointment.status != AppointmentStatus.CANCELLED,
        )
        a_res = await self.db.execute(a_stmt)
        appointments = list(a_res.scalars().all())

        latest_appt_dict = None
        if appointments:
            latest = appointments[-1]
            f_stmt = select(Facility).where(Facility.id == latest.facility_id)
            f_res = await self.db.execute(f_stmt)
            fac = f_res.scalar_one_or_none()
            fac_name = fac.name if fac else "Clinic"

            latest_appt_dict = {
                "id": str(latest.id),
                "facility_name": fac_name,
                "date": latest.appointment_date.isoformat(),
                "time": str(latest.appointment_time),
            }

        session.current_menu = "STATUS_MENU"
        session.menu_state = {
            **dict(session.menu_state or {}),
            "latest_appointment": latest_appt_dict,
        }
        await self.db.commit()

        status_text = self.prompt_service.get_status_overview(len(requests), len(appointments), latest_appt_dict, lang)
        await self.session_service.record_interaction(session.id, "STATUS_MENU", status_text, "5", "STATUS_ANNOUNCED")

        return IVRResponse(
            call_sid=session.call_sid,
            speak_text=status_text,
            gather_dtmf=True,
            num_digits=1,
            timeout_seconds=8,
            current_menu="STATUS_MENU",
            language=lang,
            is_verified=session.is_verified,
        )

    async def _handle_status_menu(self, session: IVRSession, digits: str, lang: str, state: Dict[str, Any]) -> IVRResponse:
        if digits == "1" and state.get("latest_appointment"):
            # Prompt explicit confirmation before cancellation
            session.current_menu = "CANCEL_CONFIRM"
            await self.db.commit()

            confirm_text = self.prompt_service.get_cancel_confirm_prompt(lang)
            return IVRResponse(
                call_sid=session.call_sid,
                speak_text=confirm_text,
                gather_dtmf=True,
                num_digits=1,
                timeout_seconds=8,
                current_menu="CANCEL_CONFIRM",
                language=lang,
                is_verified=session.is_verified,
            )

        return await self._show_main_menu(session, lang)

    async def _handle_cancel_confirm(self, session: IVRSession, digits: str, lang: str, state: Dict[str, Any]) -> IVRResponse:
        if digits == "1":
            # Cancel appointment
            latest_appt = state.get("latest_appointment")
            if latest_appt:
                appt_id = UUID(latest_appt["id"])
                stmt = select(Appointment).where(Appointment.id == appt_id)
                res = await self.db.execute(stmt)
                appt = res.scalar_one_or_none()
                if appt:
                    appt.status = AppointmentStatus.CANCELLED
                    await self.db.commit()

            session.current_menu = "MAIN_MENU"
            await self.db.commit()

            success_text = self.prompt_service.get_cancel_success(lang)
            await self.session_service.record_interaction(session.id, "APPOINTMENT_CANCELLED", success_text, digits, "APPOINTMENT_CANCELLED")
            return IVRResponse(
                call_sid=session.call_sid,
                speak_text=success_text,
                gather_dtmf=True,
                num_digits=1,
                current_menu="MAIN_MENU",
                language=lang,
                is_verified=session.is_verified,
            )

        return await self._show_main_menu(session, lang)

    async def _repeat_current_menu(self, session: IVRSession, lang: str) -> IVRResponse:
        """Repeat current menu prompt."""
        if session.current_menu == "MAIN_MENU":
            return await self._show_main_menu(session, lang)
        elif session.current_menu == "FACILITIES_LIST":
            return await self._show_facilities(session, lang)
        elif session.current_menu == "DOCTOR_CHECK":
            return await self._show_doctor_check(session, lang)
        elif session.current_menu == "MEDICINE_SELECT":
            return await self._show_medicine_catalog(session, lang)
        elif session.current_menu == "REQUEST_TYPE_SELECT":
            return await self._show_request_type_menu(session, lang)
        elif session.current_menu == "STATUS_MENU":
            return await self._show_status_menu(session, lang)
        else:
            return await self._show_main_menu(session, lang)
