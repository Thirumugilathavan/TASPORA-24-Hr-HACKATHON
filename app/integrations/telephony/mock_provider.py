from typing import Any, Dict, Optional
import uuid
from datetime import datetime, timezone
from app.integrations.telephony.base import TelephonyProvider
from app.schemas.ivr import IVRResponse, TelephonyCallEvent, TelephonyEventType


class MockTelephonyProvider(TelephonyProvider):
    """Mock provider simulating telecom interactions via structured JSON."""

    def parse_webhook(
        self,
        request_data: Dict[str, Any],
        headers: Dict[str, str],
    ) -> TelephonyCallEvent:
        call_sid = request_data.get("call_sid") or f"mock-call-{uuid.uuid4().hex[:8]}"
        caller_phone = request_data.get("caller_phone") or request_data.get("phone") or "9876500001"
        digits = request_data.get("digits")

        event_type_str = request_data.get("event_type", "call_start" if digits is None else "gather")
        try:
            event_type = TelephonyEventType(event_type_str)
        except ValueError:
            event_type = TelephonyEventType.GATHER if digits else TelephonyEventType.CALL_START

        return TelephonyCallEvent(
            call_sid=call_sid,
            caller_phone=caller_phone,
            digits=digits,
            event_type=event_type,
            provider="mock",
            raw_payload=request_data,
        )

    def format_response(self, ivr_response: IVRResponse) -> Dict[str, Any]:
        """Returns JSON response for simulated feature phone client."""
        return ivr_response.model_dump(mode="json")

    def validate_inbound_webhook(
        self,
        request_data: Dict[str, Any],
        headers: Dict[str, str],
        url: str,
    ) -> bool:
        """Mock provider webhook is always valid for local tests and simulators."""
        return True

    async def initiate_outbound_call(
        self,
        to_phone: str,
        from_phone: str,
        callback_url: str,
    ) -> Dict[str, Any]:
        """Simulate dispatch of outbound call."""
        call_sid = f"mock-out-{uuid.uuid4().hex[:12]}"
        return {
            "call_sid": call_sid,
            "to_phone": to_phone,
            "from_phone": from_phone or "9876500000",
            "status": "queued",
            "provider": "mock",
            "callback_url": callback_url,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    def transfer_call(self, call_sid: str, destination_phone: str) -> Dict[str, Any]:
        """Simulate call transfer to human health worker."""
        return {
            "call_sid": call_sid,
            "action": "TRANSFER",
            "destination_phone": destination_phone,
            "status": "in-progress",
        }

    def terminate_call(self, call_sid: str) -> Dict[str, Any]:
        """Simulate call termination."""
        return {
            "call_sid": call_sid,
            "action": "HANGUP",
            "status": "completed",
        }

    async def get_call_status(self, call_sid: str) -> Dict[str, Any]:
        """Return simulated call status."""
        return {
            "call_sid": call_sid,
            "status": "completed",
            "duration": 45,
            "provider": "mock",
        }
