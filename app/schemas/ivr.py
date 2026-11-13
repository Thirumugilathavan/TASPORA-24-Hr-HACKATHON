from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.shared import RecommendationItem


class IVRLanguage(str, Enum):
    TAMIL = "ta"
    ENGLISH = "en"


class TelephonyEventType(str, Enum):
    CALL_START = "call_start"
    GATHER = "gather"
    HANGUP = "hangup"


class TelephonyCallEvent(BaseModel):
    """Normalized telephony event from any provider webhook."""
    call_sid: str
    caller_phone: str
    digits: Optional[str] = None
    speech_result: Optional[str] = None
    event_type: TelephonyEventType = TelephonyEventType.CALL_START
    provider: str = "mock"
    raw_payload: Optional[Dict[str, Any]] = None


class IVRResponse(BaseModel):
    """Standardized response instructions returned to telephony provider."""
    call_sid: str
    speak_text: str
    audio_url: Optional[str] = None
    gather_dtmf: bool = True
    num_digits: int = 1
    finish_on_key: str = "#"
    timeout_seconds: int = 5
    hangup: bool = False
    transfer_number: Optional[str] = None
    action_url: Optional[str] = None
    session_status: str = "IN_PROGRESS"
    current_menu: str = "LANGUAGE_SELECT"
    language: str = "ta"
    is_verified: bool = False
    error: Optional[str] = None


class IVRStartCallIn(BaseModel):
    """Payload to initiate an IVR session (used by simulator or webhook)."""
    caller_phone: str
    call_sid: Optional[str] = None
    language: Optional[str] = None


class IVRInputIn(BaseModel):
    """Payload when sending DTMF keypresses or speech to an active call session."""
    call_sid: str
    digits: Optional[str] = None
    speech_text: Optional[str] = None


class IVRSessionStatusOut(BaseModel):
    """Diagnostic and administrative status of an IVR session."""
    id: UUID
    call_sid: str
    caller_phone: str
    language: str
    current_menu: str
    is_verified: bool
    status: str
    retry_count: int
    started_at: datetime
    last_interaction_at: datetime
    ended_at: Optional[datetime] = None
    selected_language: Optional[str] = None
    language_selection_timestamp: Optional[datetime] = None
    is_fallback_language: Optional[bool] = False

    model_config = ConfigDict(from_attributes=True)


class IVRLookupIn(BaseModel):
    """Per API.md Section 9: Simplified phone lookup for medicine availability."""
    phone: str
    medicine_code: str  # e.g., "bp", "diabetes", "paracetamol", "ors"


class IVRLookupOut(BaseModel):
    """Per API.md Section 9: Plaintext speakable response for medicine availability."""
    speak_text: str
    facility_id: UUID
    p_available: float = Field(ge=0, le=1)
    options: List[RecommendationItem]


class IVRFeedbackIn(BaseModel):
    """Per API.md Section 9: Simplified caller feedback."""
    phone: str
    facility_id: UUID
    medicine_code: str
    got_it: bool


class OutboundCallIn(BaseModel):
    """Payload to trigger an outbound call or callback."""
    to_phone: str
    patient_id: Optional[UUID] = None
    purpose: str = "ASHA_CALLBACK"  # "ASHA_CALLBACK", "APPOINTMENT_REMINDER", etc.


class OutboundCallOut(BaseModel):
    """Result of an outbound call dispatch."""
    call_sid: str
    to_phone: str
    from_phone: str
    status: str
    provider: str
    created_at: datetime

