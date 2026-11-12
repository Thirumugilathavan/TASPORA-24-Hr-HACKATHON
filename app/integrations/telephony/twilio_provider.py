import html
from typing import Any, Dict
from app.integrations.telephony.base import TelephonyProvider
from app.schemas.ivr import IVRResponse, TelephonyCallEvent, TelephonyEventType


class TwilioTelephonyProvider(TelephonyProvider):
    """Twilio-compatible telephony adapter producing standard TwiML XML."""

    def parse_webhook(
        self,
        request_data: Dict[str, Any],
        headers: Dict[str, str],
    ) -> TelephonyCallEvent:
        call_sid = request_data.get("CallSid") or request_data.get("call_sid") or "twilio-unknown"
        caller_phone = request_data.get("From") or request_data.get("caller_phone") or ""
        digits = request_data.get("Digits") or request_data.get("digits")

        call_status = request_data.get("CallStatus", "").lower()
        if call_status in ("completed", "canceled", "failed", "busy", "no-answer"):
            event_type = TelephonyEventType.HANGUP
        elif digits is not None:
            event_type = TelephonyEventType.GATHER
        else:
            event_type = TelephonyEventType.CALL_START

        return TelephonyCallEvent(
            call_sid=call_sid,
            caller_phone=caller_phone,
            digits=digits,
            event_type=event_type,
            provider="twilio",
            raw_payload=request_data,
        )

    def format_response(self, ivr_response: IVRResponse) -> str:
        """Formats IVRResponse into standard TwiML XML string."""
        escaped_text = html.escape(ivr_response.speak_text)
        lang_code = "ta-IN" if ivr_response.language == "ta" else "en-IN"

        if ivr_response.hangup:
            return (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                f'<Response><Say language="{lang_code}">{escaped_text}</Say><Hangup/></Response>'
            )

        if ivr_response.gather_dtmf:
            num_digits = ivr_response.num_digits
            timeout = ivr_response.timeout_seconds
            finish_key = ivr_response.finish_on_key
            return (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                f'<Response>\n'
                f'  <Gather numDigits="{num_digits}" timeout="{timeout}" finishOnKey="{finish_key}">\n'
                f'    <Say language="{lang_code}">{escaped_text}</Say>\n'
                f'  </Gather>\n'
                f'  <Say language="{lang_code}">No input detected.</Say>\n'
                f'</Response>'
            )

        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<Response><Say language="{lang_code}">{escaped_text}</Say></Response>'
        )
