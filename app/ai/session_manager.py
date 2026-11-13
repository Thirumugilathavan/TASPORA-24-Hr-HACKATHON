"""In-Memory Multi-Turn Conversation Session Manager for NALAM AI Assistant.

Maintains conversational continuity across turns:
- Active search location (e.g. Coimbatore, Salem, Tiruchengode)
- Active intent (FACILITY_SEARCH, DOCTOR_AVAILABILITY, etc.)
- Active facility or doctor selected
- Active medicine queried
- History of recent conversational turns
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid


@dataclass
class ConversationTurn:
    turn_id: str
    user_message: str
    detected_language: str
    intent: str
    extracted_location: Optional[str]
    tools_called: List[str]
    assistant_response: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ConversationSession:
    conversation_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    active_location: Optional[str] = None
    active_intent: Optional[str] = None
    active_facility_id: Optional[str] = None
    active_facility_name: Optional[str] = None
    active_doctor_name: Optional[str] = None
    active_medicine: Optional[str] = None
    turns: List[ConversationTurn] = field(default_factory=list)

    def add_turn(
        self,
        user_message: str,
        detected_language: str,
        intent: str,
        extracted_location: Optional[str],
        tools_called: List[str],
        assistant_response: str,
    ) -> None:
        self.turns.append(
            ConversationTurn(
                turn_id=str(uuid.uuid4()),
                user_message=user_message,
                detected_language=detected_language,
                intent=intent,
                extracted_location=extracted_location,
                tools_called=tools_called,
                assistant_response=assistant_response,
            )
        )
        self.last_updated_at = datetime.now(timezone.utc)
        if extracted_location:
            self.active_location = extracted_location
        if intent not in ["GENERAL_CONVERSATION", "UNKNOWN_INTENT"]:
            self.active_intent = intent

    def get_last_turn(self) -> Optional[ConversationTurn]:
        return self.turns[-1] if self.turns else None


class SessionManager:
    """Thread-safe in-memory session manager for AI conversations."""

    def __init__(self, max_sessions: int = 5000):
        self._sessions: Dict[str, ConversationSession] = {}
        self.max_sessions = max_sessions

    def get_or_create(self, conversation_id: Optional[str] = None) -> ConversationSession:
        cid = conversation_id.strip() if conversation_id and conversation_id.strip() else str(uuid.uuid4())
        if cid not in self._sessions:
            # Evict oldest session if threshold reached
            if len(self._sessions) >= self.max_sessions:
                oldest_key = min(self._sessions.keys(), key=lambda k: self._sessions[k].last_updated_at)
                del self._sessions[oldest_key]
            self._sessions[cid] = ConversationSession(conversation_id=cid)
        return self._sessions[cid]

    def clear(self, conversation_id: str) -> None:
        if conversation_id in self._sessions:
            del self._sessions[conversation_id]

    def count(self) -> int:
        return len(self._sessions)


# Global session manager instance
session_manager = SessionManager()
