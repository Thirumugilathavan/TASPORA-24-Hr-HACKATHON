import base64
import hashlib
import hmac
import html
import logging
from typing import Any, Dict, Optional
import httpx

from app.core.config import settings
from app.integrations.telephony.base import TelephonyProvider
from app.schemas.ivr import IVRResponse, TelephonyCallEvent, TelephonyEventType

logger = logging.getLogger(__name__)


class TwilioTelephonyProvider(TelephonyProvider):
    """Twilio-compatible telephony adapter producing standard TwiML XML and handling carrier webhooks."""

    def validate_inbound_webhook(
        self,
        request_data: Dict[str, Any],
        headers: Dict[str, str],
        url: str,
    ) -> bool:
        """Validate cryptographic signature (X-Twilio-Signature) via HMAC-SHA1.

        Twilio Signature Algorithm:
        1. Take the full webhook URL.
        2. Sort POST parameter keys alphabetically.
        3. Append key and value to URL string.
        4. Compute HMAC-SHA1 digest using Twilio Auth Token.
        5. Base64 encode and compare using constant-time comparison.
        """
        auth_token = settings.TELEPHONY_AUTH_TOKEN or settings.TELEPHONY_WEBHOOK_SECRET
        if not auth_token:
            # If no auth token is configured (e.g. development/testing mode), permit request
            return True

        # Header keys in HTTP headers may be lowercase or capitalized
        twilio_signature = headers.get("x-twilio-signature") or headers.get("X-Twilio-Signature")
        if not twilio_signature:
            logger.warning("Missing X-Twilio-Signature header on inbound webhook")
            return False

        # Construct target URL (prefer configured base URL if behind proxy/ngrok)
        target_url = url
        if settings.TELEPHONY_WEBHOOK_BASE_URL:
            # Reconstruct with configured base URL if path matches
            from urllib.parse import urlparse
            parsed_base = urlparse(settings.TELEPHONY_WEBHOOK_BASE_URL)
            parsed_req = urlparse(url)
            target_url = f"{parsed_base.scheme}://{parsed_base.netloc}{parsed_req.path}"
            if parsed_req.query:
                target_url += f"?{parsed_req.query}"

        # Sort POST data by keys
        data_string = target_url
        for k in sorted(request_data.keys()):
            val = request_data[k]
            if isinstance(val, (list, tuple)):
                val = val[0] if val else ""
            data_string += f"{k}{val}"

        mac = hmac.new(auth_token.encode("utf-8"), data_string.encode("utf-8"), hashlib.sha1)
        expected_signature = base64.b64encode(mac.digest()).decode("utf-8")

        is_valid = hmac.compare_digest(twilio_signature.strip(), expected_signature.strip())
        if not is_valid:
            logger.warning(
                f"Twilio webhook signature mismatch. Target URL: {target_url}, "
                f"Received: {twilio_signature[:10]}..., Expected: {expected_signature[:10]}..."
            )
        return is_valid

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
        """Formats IVRResponse into standard TwiML XML string with language-specific TTS."""
        escaped_text = html.escape(ivr_response.speak_text)
        lang_code = "ta-IN" if ivr_response.language == "ta" else "en-IN"

        # Optional audio URL playback
        play_tag = f'<Play>{html.escape(ivr_response.audio_url)}</Play>\n    ' if ivr_response.audio_url else ""

        # Case 1: Call Transfer to Human Support
        if ivr_response.transfer_number:
            escaped_number = html.escape(ivr_response.transfer_number)
            return (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                f'<Response>\n'
                f'  <Say language="{lang_code}">{escaped_text}</Say>\n'
                f'  <Dial timeout="25">{escaped_number}</Dial>\n'
                f'  <Say language="{lang_code}">The representative was unavailable. Returning to main menu.</Say>\n'
                f'</Response>'
            )

        # Case 2: Hangup / Call Termination
        if ivr_response.hangup:
            return (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                f'<Response>\n'
                f'  {play_tag}<Say language="{lang_code}">{escaped_text}</Say>\n'
                f'  <Hangup/>\n'
                f'</Response>'
            )

        # Case 3: DTMF Digit Gather
        if ivr_response.gather_dtmf:
            num_digits = ivr_response.num_digits
            timeout = ivr_response.timeout_seconds
            finish_key = ivr_response.finish_on_key
            action_attr = f' action="{html.escape(ivr_response.action_url)}"' if ivr_response.action_url else ""
            method_attr = ' method="POST"' if ivr_response.action_url else ""

            return (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                f'<Response>\n'
                f'  <Gather numDigits="{num_digits}" timeout="{timeout}" finishOnKey="{finish_key}"{action_attr}{method_attr}>\n'
                f'    {play_tag}<Say language="{lang_code}">{escaped_text}</Say>\n'
                f'  </Gather>\n'
                f'  <Say language="{lang_code}">No input detected.</Say>\n'
                f'</Response>'
            )

        # Case 4: Informational Speak
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<Response>\n'
            f'  {play_tag}<Say language="{lang_code}">{escaped_text}</Say>\n'
            f'</Response>'
        )

    async def initiate_outbound_call(
        self,
        to_phone: str,
        from_phone: str,
        callback_url: str,
    ) -> Dict[str, Any]:
        """Dispatch an outbound telephone call via Twilio Programmable Voice REST API."""
        account_sid = settings.TELEPHONY_ACCOUNT_SID
        auth_token = settings.TELEPHONY_AUTH_TOKEN
        caller_id = from_phone or settings.TELEPHONY_PHONE_NUMBER

        # If credentials are not configured, simulate queued outbound call
        if not account_sid or not auth_token or account_sid.startswith("mock") or account_sid.startswith("your_"):
            import uuid
            from datetime import datetime, timezone
            call_sid = f"CA_sim_{uuid.uuid4().hex[:16]}"
            logger.info(
                f"[SIMULATED OUTBOUND] Telephony credentials unprovisioned. "
                f"Simulating call from {caller_id} to {to_phone} with callback {callback_url}"
            )
            return {
                "call_sid": call_sid,
                "to_phone": to_phone,
                "from_phone": caller_id,
                "status": "queued",
                "provider": "twilio_simulated",
                "callback_url": callback_url,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

        # Real Twilio REST API dispatch
        api_url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Calls.json"
        data = {
            "To": to_phone,
            "From": caller_id,
            "Url": callback_url,
            "Timeout": str(settings.TELEPHONY_CALL_TIMEOUT),
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                res = await client.post(
                    api_url,
                    data=data,
                    auth=(account_sid, auth_token),
                )
                res.raise_for_status()
                res_data = res.json()
                return {
                    "call_sid": res_data.get("sid"),
                    "to_phone": res_data.get("to"),
                    "from_phone": res_data.get("from"),
                    "status": res_data.get("status"),
                    "provider": "twilio",
                    "created_at": res_data.get("date_created"),
                }
            except Exception as e:
                logger.error(f"Failed to initiate Twilio outbound call: {e}")
                raise

    def transfer_call(self, call_sid: str, destination_phone: str) -> str:
        """Generate TwiML XML to dial destination phone."""
        escaped_number = html.escape(destination_phone)
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<Response>\n'
            f'  <Say language="ta-IN">உங்கள் அழைப்பு இணைக்கப்படுகிறது.</Say>\n'
            f'  <Dial timeout="25">{escaped_number}</Dial>\n'
            f'</Response>'
        )

    def terminate_call(self, call_sid: str) -> str:
        """Generate TwiML XML to hangup."""
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<Response><Hangup/></Response>'
        )

    async def get_call_status(self, call_sid: str) -> Dict[str, Any]:
        """Fetch live call status from Twilio REST API."""
        account_sid = settings.TELEPHONY_ACCOUNT_SID
        auth_token = settings.TELEPHONY_AUTH_TOKEN
        if not account_sid or not auth_token:
            return {"call_sid": call_sid, "status": "completed", "provider": "twilio_simulated"}

        api_url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Calls/{call_sid}.json"
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(api_url, auth=(account_sid, auth_token))
            res.raise_for_status()
            res_data = res.json()
            return {
                "call_sid": res_data.get("sid"),
                "status": res_data.get("status"),
                "duration": res_data.get("duration"),
                "from_phone": res_data.get("from"),
                "to_phone": res_data.get("to"),
                "provider": "twilio",
            }
