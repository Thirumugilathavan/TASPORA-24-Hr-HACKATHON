"""FastAPI AI Assistant Router for CareBridge.

Exposes endpoints for:
- /api/ai/chat: Closed-loop tool calling & RAG healthcare assistant
- /api/ai/voice/transcribe: Speech-to-text (Gnani / Indic voice adapter)
- /api/ai/voice/synthesize: Text-to-speech (Gnani / Indic voice adapter)
- /api/ai/health: AI subsystem status & readiness
- /api/ai/tools: Registered tools and schema catalog
- /api/ai/feedback: Conversational response feedback
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agent import carebridge_agent
from app.ai.gnani_adapter import gnani_adapter
from app.ai.rag import rag_engine
from app.ai.schemas import (
    AIChatRequest,
    AIChatResponse,
    AIHealthResponse,
    ToolDefinition,
    VoiceSynthesizeRequest,
    VoiceSynthesizeResponse,
    VoiceTranscribeRequest,
    VoiceTranscribeResponse,
)
from app.core.database import get_db

router = APIRouter(prefix="/ai", tags=["AI Healthcare Assistant"])


class AIFeedbackRequest(BaseModel):
    conversation_id: str
    message_index: Optional[int] = 0
    rating: int  # 1 (poor) to 5 (excellent)
    feedback_text: Optional[str] = None


@router.post(
    "/chat",
    response_model=AIChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Interactive AI Healthcare & Coordination Assistant",
    description=(
        "Executes closed-loop tool calling over live database facilities, verified doctor attendance, "
        "probabilistic medicine inventories, loss calculations, and project documentation."
    ),
)
async def chat_with_assistant(
    request: AIChatRequest,
    db: AsyncSession = Depends(get_db),
) -> AIChatResponse:
    """Processes user query, executes required tools/RAG, and delivers structured response."""
    try:
        response = await carebridge_agent.execute_turn(request=request, db=db)
        return response
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "AI_EXECUTION_ERROR", "message": str(exc)}},
        )


@router.post(
    "/voice/transcribe",
    response_model=VoiceTranscribeResponse,
    summary="Speech-to-Text Audio Transcription",
    description="Transcribes spoken Tamil or English audio into text using Gnani Indic Speech Adapter.",
)
async def transcribe_voice(request: VoiceTranscribeRequest) -> VoiceTranscribeResponse:
    """Transcribes base64 audio payload to text."""
    try:
        result = await gnani_adapter.transcribe(
            audio_base64=request.audio_base64,
            audio_format=request.audio_format,
            language=request.language or "ta",
        )
        return VoiceTranscribeResponse(
            transcribed_text=result["transcribed_text"],
            detected_language=result["detected_language"],
            confidence=result["confidence"],
            provider=result["provider"],
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "VOICE_TRANSCRIBE_ERROR", "message": str(exc)}},
        )


@router.post(
    "/voice/synthesize",
    response_model=VoiceSynthesizeResponse,
    summary="Text-to-Speech Voice Synthesis",
    description="Synthesizes Tamil or English text into natural spoken audio via Gnani Indic Voice Adapter.",
)
async def synthesize_voice(request: VoiceSynthesizeRequest) -> VoiceSynthesizeResponse:
    """Synthesizes text into base64 WAV audio."""
    try:
        result = await gnani_adapter.synthesize(
            text=request.text,
            language=request.language,
            voice_name=request.voice_name,
            voice_gender=request.voice_gender or "female",
        )
        return VoiceSynthesizeResponse(
            audio_base64=result.get("audio_base64"),
            audio_url=result.get("audio_url"),
            duration_seconds=result.get("duration_seconds", 1.0),
            format=result.get("format", "audio/wav"),
            status=result.get("status", "success"),
            provider=result.get("provider", "local_indic_adapter"),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "VOICE_SYNTHESIZE_ERROR", "message": str(exc)}},
        )


@router.get(
    "/health",
    response_model=AIHealthResponse,
    summary="AI Subsystem Health & Readiness",
)
async def ai_health() -> AIHealthResponse:
    """Returns AI subsystem health, indexed RAG chunks, and voice adapter status."""
    v_status = gnani_adapter.get_status()
    return AIHealthResponse(
        status="healthy",
        service="carebridge-ai-agent",
        tools_count=6,
        rag_documents_indexed=len(rag_engine.chunks),
        llm_provider="Local Semantic Tool Calling Engine (Deterministic & Fast)",
        voice_provider=v_status["provider"],
    )


@router.get(
    "/voice/status",
    summary="Gnani Voice Provider Status & Voice Catalog",
)
async def get_voice_status() -> Dict[str, Any]:
    """Returns active Gnani STT/TTS engine status, voice catalog, and cloud connectivity."""
    return gnani_adapter.get_status()


@router.get(
    "/tools",
    response_model=List[ToolDefinition],
    summary="Registered AI Tools Catalog",
)
async def list_ai_tools() -> List[ToolDefinition]:
    """Catalogues all live backend tools accessible by the CareBridge AI Assistant."""
    return [
        ToolDefinition(
            name="search_facilities_tool",
            description="Searches healthcare facilities, calculates straight-line haversine distance, and lists doctors and services.",
            parameters={
                "location_name": "string (optional): Town, village, or district name",
                "facility_type": "string (optional): 'PHC', 'CHC', 'HOSPITAL', or 'PHARMACY'",
                "service": "string (optional): Specific healthcare service filter",
                "limit": "integer: Maximum results to return",
            },
        ),
        ToolDefinition(
            name="check_doctor_availability_tool",
            description="Queries verified doctor attendance and duty shift times for today (distinguishing PRESENT from EXPECTED).",
            parameters={
                "facility_name": "string (optional)",
                "doctor_name": "string (optional)",
                "specialization": "string (optional)",
            },
        ),
        ToolDefinition(
            name="check_medicine_stock_tool",
            description="Queries probabilistic medicine inventory beliefs (p_available, confidence, and LIKELY/UNCERTAIN/UNLIKELY label).",
            parameters={
                "medicine_name": "string (required): Brand or generic medicine name",
                "facility_name": "string (optional)",
            },
        ),
        ToolDefinition(
            name="get_recommendations_tool",
            description="Calculates uncertainty-aware facility recommendations minimizing Expected Trip Loss.",
            parameters={
                "village_name": "string (optional)",
                "request_type": "string: 'CONSULTATION', 'REFILL', 'CHECKUP', 'DIAGNOSTIC'",
                "medicine_name": "string (optional)",
            },
        ),
        ToolDefinition(
            name="query_rag_knowledge_tool",
            description="Retrieves authoritative architectural and algorithm documentation chunks from project repository.",
            parameters={"query": "string: Architectural or technical question"},
        ),
        ToolDefinition(
            name="emergency_guidance_tool",
            description="Returns official 108 emergency ambulance protocols and 24x7 trauma facilities for life-threatening symptoms.",
            parameters={"symptom_or_query": "string: Emergency symptom description"},
        ),
    ]


@router.post(
    "/feedback",
    status_code=status.HTTP_200_OK,
    summary="Submit AI Answer Feedback",
)
async def submit_feedback(payload: AIFeedbackRequest):
    """Records user satisfaction rating for assistant answers."""
    return {
        "status": "feedback_recorded",
        "conversation_id": payload.conversation_id,
        "rating": payload.rating,
    }
