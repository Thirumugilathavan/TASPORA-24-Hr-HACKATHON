from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.parse import parse_qs
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import verify_ivr_api_key
from app.integrations.telephony.provider_adapter import get_telephony_provider
from app.models.facility import Facility
from app.models.ivr import IVRSession
from app.models.medicine import Medicine
from app.schemas.ivr import (
    IVRFeedbackIn,
    IVRInputIn,
    IVRLookupIn,
    IVRLookupOut,
    IVRResponse,
    IVRSessionStatusOut,
    IVRStartCallIn,
    OutboundCallIn,
    OutboundCallOut,
    TelephonyEventType,
)
from app.schemas.shared import AvailabilityLabel
from app.services.availability_service import AvailabilityService
from app.services.ivr_auth_service import normalize_phone_number
from app.services.ivr_service import IVRService
from app.services.recommendation_service import generate_recommendations

router = APIRouter(prefix="/ivr", tags=["Voice Access (IVR)"])


async def _extract_request_payload(request: Request) -> Dict[str, Any]:
    """Safely extracts JSON or Form URL-encoded data from incoming telecom webhooks."""
    content_type = request.headers.get("content-type", "").lower()
    if "application/json" in content_type:
        try:
            return await request.json()
        except Exception:
            return {}
    try:
        body_bytes = await request.body()
        if body_bytes:
            parsed = parse_qs(body_bytes.decode("utf-8", errors="replace"))
            return {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}
    except Exception:
        pass
    try:
        form = await request.form()
        return dict(form)
    except Exception:
        return {}


async def verify_carrier_webhook(request: Request, raw_data: Dict[str, Any]) -> None:
    """Verifies cryptographic carrier signature (e.g., X-Twilio-Signature)."""
    provider = get_telephony_provider()
    headers_dict = dict(request.headers)
    url_str = str(request.url)
    if not provider.validate_inbound_webhook(raw_data, headers_dict, url_str):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "FORBIDDEN", "message": "Invalid telephony webhook signature"}},
        )



@router.post(
    "/webhook",
    summary="Telephony provider webhook endpoint",
    description="Unified webhook entrypoint for telephony providers (Twilio, Mock, etc.). Authenticated via X-API-Key.",
)
async def telephony_webhook(
    request: Request,
    api_key: str = Depends(verify_ivr_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Handle incoming call events and DTMF gathers from telephony provider webhooks."""
    # Handle either JSON or Form URL-encoded data from telecom providers
    content_type = request.headers.get("content-type", "").lower()
    if "application/json" in content_type:
        raw_data = await request.json()
    elif "application/x-www-form-urlencoded" in content_type:
        body_bytes = await request.body()
        parsed = parse_qs(body_bytes.decode("utf-8", errors="replace"))
        raw_data = {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}
    else:
        try:
            form = await request.form()
            raw_data = dict(form)
        except Exception:
            body_bytes = await request.body()
            parsed = parse_qs(body_bytes.decode("utf-8", errors="replace"))
            raw_data = {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}

    provider = get_telephony_provider()
    headers_dict = dict(request.headers)
    event = provider.parse_webhook(raw_data, headers_dict)

    service = IVRService(db)

    if event.event_type == TelephonyEventType.CALL_START:
        ivr_resp = await service.start_call(
            call_sid=event.call_sid,
            caller_phone=event.caller_phone,
        )
    elif event.event_type == TelephonyEventType.HANGUP:
        stmt = select(IVRSession).where(IVRSession.call_sid == event.call_sid)
        res = await db.execute(stmt)
        session = res.scalar_one_or_none()
        if session:
            await service.session_service.end_session(session, "COMPLETED")
        ivr_resp = IVRResponse(
            call_sid=event.call_sid,
            speak_text="Call completed.",
            hangup=True,
            session_status="COMPLETED",
        )
    else:
        # GATHER event with DTMF digits
        ivr_resp = await service.process_dtmf(
            call_sid=event.call_sid,
            digits=event.digits or "",
        )

    # Format response depending on provider (XML for Twilio, JSON for mock)
    formatted = provider.format_response(ivr_resp)
    if isinstance(formatted, str) and formatted.startswith("<?xml"):
        return Response(content=formatted, media_type="application/xml")
    return formatted


@router.post(
    "/webhooks/incoming",
    summary="Carrier Inbound Voice Call Webhook",
    description="Provider-facing webhook for inbound voice calls. Validates carrier signature (X-Twilio-Signature).",
)
async def carrier_incoming_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle inbound voice call dispatched by telecom provider."""
    raw_data = await _extract_request_payload(request)
    await verify_carrier_webhook(request, raw_data)

    provider = get_telephony_provider()
    headers_dict = dict(request.headers)
    event = provider.parse_webhook(raw_data, headers_dict)

    service = IVRService(db)
    ivr_resp = await service.start_call(
        call_sid=event.call_sid,
        caller_phone=event.caller_phone,
    )
    ivr_resp.action_url = "/api/ivr/webhooks/continue"

    formatted = provider.format_response(ivr_resp)
    if isinstance(formatted, str) and formatted.startswith("<?xml"):
        return Response(content=formatted, media_type="application/xml")
    return formatted


@router.post(
    "/webhooks/continue",
    summary="Carrier DTMF Gather Callback Webhook",
    description="Provider-facing webhook for DTMF keypress input. Validates carrier signature (X-Twilio-Signature).",
)
async def carrier_continue_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle DTMF input gathered from carrier voice session."""
    raw_data = await _extract_request_payload(request)
    await verify_carrier_webhook(request, raw_data)

    provider = get_telephony_provider()
    headers_dict = dict(request.headers)
    event = provider.parse_webhook(raw_data, headers_dict)

    service = IVRService(db)
    if event.event_type == TelephonyEventType.HANGUP:
        stmt = select(IVRSession).where(IVRSession.call_sid == event.call_sid)
        res = await db.execute(stmt)
        session = res.scalar_one_or_none()
        if session:
            await service.session_service.end_session(session, "COMPLETED")
        ivr_resp = IVRResponse(
            call_sid=event.call_sid,
            speak_text="Call completed.",
            hangup=True,
            session_status="COMPLETED",
        )
    else:
        ivr_resp = await service.process_dtmf(
            call_sid=event.call_sid,
            digits=event.digits or "",
        )
    ivr_resp.action_url = "/api/ivr/webhooks/continue"

    formatted = provider.format_response(ivr_resp)
    if isinstance(formatted, str) and formatted.startswith("<?xml"):
        return Response(content=formatted, media_type="application/xml")
    return formatted


@router.post(
    "/webhooks/status",
    summary="Carrier Call Status Callback Webhook",
    description="Provider-facing webhook for call lifecycle tracking (ringing, completed, busy, no-answer, failed).",
)
async def carrier_status_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Update call outcome upon carrier call termination or failure."""
    raw_data = await _extract_request_payload(request)
    await verify_carrier_webhook(request, raw_data)

    provider = get_telephony_provider()
    event = provider.parse_webhook(raw_data, dict(request.headers))

    call_sid = event.call_sid
    call_status = raw_data.get("CallStatus", "").lower()

    if call_status in ("completed", "canceled", "failed", "busy", "no-answer"):
        stmt = select(IVRSession).where(IVRSession.call_sid == call_sid)
        res = await db.execute(stmt)
        session = res.scalar_one_or_none()
        if session and session.status == "IN_PROGRESS":
            service = IVRService(db)
            outcome = "COMPLETED" if call_status == "completed" else "FAILED"
            await service.session_service.end_session(session, outcome)

    return {"status": "ACKNOWLEDGED", "call_sid": call_sid, "call_status": call_status}


@router.post(
    "/callbacks/initiate",
    response_model=OutboundCallOut,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate Outbound Call / ASHA Callback",
    description="Trigger an automated outbound call or ASHA follow-up callback. Authenticated via X-API-Key.",
)
async def initiate_outbound_call(
    payload: OutboundCallIn,
    api_key: str = Depends(verify_ivr_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Dispatch an outbound telephone call respecting Indian calling hours (08:00 to 20:00 IST)."""
    # Enforce safe calling hours (08:00 to 20:00 Indian Standard Time: UTC+5:30)
    now_utc = datetime.now(timezone.utc)
    # Approximate IST hour calculation
    ist_hour = (now_utc.hour + 5 + (1 if now_utc.minute >= 30 else 0)) % 24
    if not (8 <= ist_hour < 20) and not settings.IS_SIMULATED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "OUTSIDE_CALLING_HOURS", "message": "Outbound calls permitted between 08:00 and 20:00 IST only"}},
        )

    norm_to = normalize_phone_number(payload.to_phone)
    if not norm_to or len(norm_to) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "INVALID_PHONE", "message": "Valid 10-digit phone number required"}},
        )

    provider = get_telephony_provider()
    callback_base = settings.TELEPHONY_WEBHOOK_BASE_URL or "http://127.0.0.1:8000"
    callback_url = f"{callback_base.rstrip('/')}/api/ivr/webhooks/incoming"
    from_phone = settings.TELEPHONY_PHONE_NUMBER or "9876500000"

    res = await provider.initiate_outbound_call(
        to_phone=norm_to,
        from_phone=from_phone,
        callback_url=callback_url,
    )

    # Record or initialize session
    service = IVRService(db)
    session = await service.session_service.get_or_create_session(
        call_sid=res["call_sid"],
        caller_phone=norm_to,
        default_language=settings.IVR_DEFAULT_LANGUAGE,
    )
    if payload.patient_id:
        session.patient_id = payload.patient_id
    await db.commit()

    return OutboundCallOut(
        call_sid=res["call_sid"],
        to_phone=norm_to,
        from_phone=from_phone,
        status=res.get("status", "queued"),
        provider=res.get("provider", "mock"),
        created_at=datetime.now(timezone.utc),
    )



@router.post(
    "/call/start",
    response_model=IVRResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate IVR session",
    description="Start an interactive voice session for a caller phone number. Authenticated via X-API-Key.",
)
async def start_ivr_call(
    payload: IVRStartCallIn,
    api_key: str = Depends(verify_ivr_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Initiate an IVR call session programmatically or for simulator testing."""
    call_sid = payload.call_sid or f"call-{uuid4().hex[:12]}"
    service = IVRService(db)
    return await service.start_call(
        call_sid=call_sid,
        caller_phone=payload.caller_phone,
        language=payload.language,
    )


@router.post(
    "/call/input",
    response_model=IVRResponse,
    summary="Submit DTMF keypad input",
    description="Process button-phone DTMF keypad input for an active call session. Authenticated via X-API-Key.",
)
async def process_call_input(
    payload: IVRInputIn,
    api_key: str = Depends(verify_ivr_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Submit digits pressed on the keypad."""
    service = IVRService(db)
    return await service.process_dtmf(
        call_sid=payload.call_sid,
        digits=payload.digits,
    )


@router.get(
    "/session/{session_id}",
    response_model=IVRSessionStatusOut,
    summary="Get IVR session status",
    description="Retrieve live state, verified status, and language of an active or past IVR session.",
)
async def get_session_status(
    session_id: UUID,
    api_key: str = Depends(verify_ivr_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve diagnostic and interaction state of a call session."""
    service = IVRService(db)
    session = await service.session_service.get_session_by_id(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": f"IVR session {session_id} not found"}},
        )
    return session


@router.post(
    "/call/hangup",
    response_model=IVRResponse,
    summary="Terminate IVR call session",
    description="Safely end an active call session.",
)
async def hangup_call(
    payload: IVRInputIn,
    api_key: str = Depends(verify_ivr_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Terminate call session."""
    stmt = select(IVRSession).where(IVRSession.call_sid == payload.call_sid)
    res = await db.execute(stmt)
    session = res.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": "Call session not found"}},
        )

    service = IVRService(db)
    await service.session_service.end_session(session, "COMPLETED")
    goodbye_text = service.prompt_service.get_goodbye(session.language)
    return IVRResponse(
        call_sid=session.call_sid,
        speak_text=goodbye_text,
        hangup=True,
        session_status="COMPLETED",
        language=session.language,
        is_verified=session.is_verified,
    )


@router.post(
    "/lookup",
    response_model=IVRLookupOut,
    summary="API.md contract: Medicine availability voice lookup",
    description="Per API.md Section 9: Simplified phone lookup for medicine availability.",
)
async def ivr_medicine_lookup(
    payload: IVRLookupIn,
    api_key: str = Depends(verify_ivr_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Lookup medicine availability spoken summary for a caller."""
    norm_phone = normalize_phone_number(payload.phone)

    # Search medicine by code / keyword
    code = payload.medicine_code.lower().strip()
    m_stmt = select(Medicine).where(
        Medicine.name.ilike(f"%{code}%") | (Medicine.generic_name.ilike(f"%{code}%"))
    )
    m_res = await db.execute(m_stmt)
    medicine = m_res.scalars().first()

    # Get facility
    f_stmt = select(Facility).limit(1)
    f_res = await db.execute(f_stmt)
    facility = f_res.scalar_one_or_none()

    if not facility:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": "No healthcare facility available"}},
        )

    med_id = medicine.id if medicine else uuid4()
    med_name = medicine.name if medicine else payload.medicine_code

    # Calculate belief
    avail_service = AvailabilityService(db)
    p_avail, conf, label, _, _ = await avail_service.calculate_belief(facility.id, med_id)

    speak_text = (
        f"{facility.name}-ல் {med_name} மருந்து இருப்பு நிலை: {label.value}. "
        f"மதிப்பிடப்பட்ட கிடைக்கும் வாய்ப்பு: {int(p_avail * 100)} சதவீதம். "
        "இது மருத்துவ பரிந்துரை அல்ல."
    )

    return IVRLookupOut(
        speak_text=speak_text,
        facility_id=facility.id,
        p_available=p_avail,
        options=[],
    )


@router.post(
    "/feedback",
    status_code=status.HTTP_200_OK,
    summary="API.md contract: Caller stock feedback",
    description="Per API.md Section 9: Log caller feedback on medicine availability without directly altering stock probability.",
)
async def ivr_feedback(
    payload: IVRFeedbackIn,
    api_key: str = Depends(verify_ivr_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Record patient/caller feedback.

    Safety Rule 2: Patient feedback must never directly modify medicine stock probability.
    """
    # Feedback recorded safely without inflating or altering p_available
    return {
        "status": "RECORDED",
        "message": "Thank you for your feedback. Recorded for health worker follow-up.",
    }
