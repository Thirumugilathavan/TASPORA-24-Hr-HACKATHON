from typing import Any, Dict
import uuid
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
