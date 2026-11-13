"""Schemas for CareBridge AI Agent, Tools, RAG, and Multimodal Voice Access."""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CardType(str, Enum):
    FACILITY = "FACILITY"
    DOCTOR = "DOCTOR"
    MEDICINE = "MEDICINE"
    RECOMMENDATION = "RECOMMENDATION"
    APPOINTMENT = "APPOINTMENT"
    EMERGENCY = "EMERGENCY"
    RAG_SOURCE = "RAG_SOURCE"
    DISCLAIMER = "DISCLAIMER"
    SCHEME = "SCHEME"


class AIChatCard(BaseModel):
    """Structured UI widget for rich frontend rendering."""
    type: CardType
    title: str
    subtitle: Optional[str] = None
    badge: Optional[str] = None
    badge_color: Optional[str] = None  # green, yellow, red, blue, purple
    details: Dict[str, Any] = Field(default_factory=dict)
    action: Optional[Dict[str, Any]] = None
    action_url: Optional[str] = None
    action_label: Optional[str] = None


class ChatMessage(BaseModel):
    role: str  # user, assistant, system
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    cards: Optional[List[AIChatCard]] = None


class AIChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="User query or voice transcript")
    conversation_id: Optional[str] = Field(None, description="Session conversation ID")
    language: Optional[str] = Field("auto", description="'ta', 'en', or 'auto' for automatic language detection")
    patient_id: Optional[UUID] = Field(None, description="Authenticated patient UUID if logged in")
    village_id: Optional[UUID] = Field(None, description="Patient's home village UUID")
    location_context: Optional[str] = Field(None, description="Location context e.g. Tiruchengode, Rampur")
    user_role: Optional[str] = Field("PATIENT", description="User role (PATIENT, ASHA, STAFF, ADMIN)")
    include_audio: Optional[bool] = Field(False, description="Whether to include synthesized audio response")
    voice_name: Optional[str] = Field(None, description="Optional voice name (e.g. Nalini, Deepak)")


class AIChatResponse(BaseModel):
    conversation_id: str
    response_text: str
    language: str  # 'ta' or 'en'
    intent: str
    tools_called: List[str] = Field(default_factory=list)
    cards: List[AIChatCard] = Field(default_factory=list)
    rag_sources: List[Dict[str, Any]] = Field(default_factory=list)
    action_taken: Optional[str] = None
    audio_base64: Optional[str] = Field(None, description="Base64 encoded WAV audio if synthesized")
    audio_duration: Optional[float] = Field(None, description="Audio duration in seconds")
    voice_provider: Optional[str] = Field(None, description="Voice provider name")
    disclaimer: str = (
        "NALAM provides accessibility and coordination information only. "
        "It does not provide clinical diagnosis, prescriptions, or dosage advice. "
        "For medical emergencies, call 108 immediately."
    )


class VoiceTranscribeRequest(BaseModel):
    audio_base64: str = Field(..., description="Base64 encoded audio payload")
    audio_format: str = Field("wav", description="Audio format (wav, mp3, ogg)")
    language: Optional[str] = Field("auto", description="Preferred language (ta, en, auto)")


class VoiceTranscribeResponse(BaseModel):
    transcribed_text: str
    detected_language: str
    confidence: float
    provider: str


class VoiceSynthesizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000)
    language: str = Field("ta", description="'ta' for Tamil or 'en' for English")
    voice_gender: Optional[str] = Field("female", description="female or male")
    voice_name: Optional[str] = Field(None, description="Optional voice name (Nalini, Bhavna, Deepak, etc.)")


class VoiceSynthesizeResponse(BaseModel):
    audio_base64: Optional[str] = None
    audio_url: Optional[str] = None
    duration_seconds: Optional[float] = None
    format: str = "audio/wav"
    status: str = "success"
    provider: str


class AIHealthResponse(BaseModel):
    status: str
    service: str = "carebridge-ai-agent"
    tools_count: int
    rag_documents_indexed: int
    llm_provider: str
    voice_provider: str


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]
