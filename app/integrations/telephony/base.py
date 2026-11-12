from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from app.schemas.ivr import IVRResponse, TelephonyCallEvent


class TelephonyProvider(ABC):
    """Abstract base class for telecom providers (Mock, Twilio, Exotel, etc.).

    Provides provider-independent telecom interface for:
    - Inbound call parsing and webhook signature verification
    - DTMF gather and response formatting (JSON, TwiML XML)
    - Call transfer and graceful termination
    - Outbound calling and callback initiation
    - Call status queries
    """

    @abstractmethod
    def parse_webhook(
        self,
        request_data: Dict[str, Any],
        headers: Dict[str, str],
    ) -> TelephonyCallEvent:
        """Parse provider-specific incoming webhook request into a unified TelephonyCallEvent."""
        pass

    @abstractmethod
    def format_response(self, ivr_response: IVRResponse) -> Any:
        """Format an IVRResponse into the provider's expected payload (e.g. JSON, TwiML XML)."""
        pass

    def generate_voice_response(self, ivr_response: IVRResponse) -> Any:
        """Alias for format_response for telecom provider independence."""
        return self.format_response(ivr_response)

    @abstractmethod
    def validate_inbound_webhook(
        self,
        request_data: Dict[str, Any],
        headers: Dict[str, str],
        url: str,
    ) -> bool:
        """Validate cryptographic webhook signature from provider (e.g., X-Twilio-Signature)."""
        pass

    @abstractmethod
    async def initiate_outbound_call(
        self,
        to_phone: str,
        from_phone: str,
        callback_url: str,
    ) -> Dict[str, Any]:
        """Dispatch an outbound telephone call via provider REST API."""
        pass

    @abstractmethod
    def transfer_call(self, call_sid: str, destination_phone: str) -> Any:
        """Generate response or invoke carrier API to transfer call to another number."""
        pass

    @abstractmethod
    def terminate_call(self, call_sid: str) -> Any:
        """Instruct the telephony provider to hang up the call."""
        pass

    @abstractmethod
    async def get_call_status(self, call_sid: str) -> Dict[str, Any]:
        """Retrieve real-time status of a call from the carrier."""
        pass
