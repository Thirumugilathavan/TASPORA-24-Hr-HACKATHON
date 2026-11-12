from abc import ABC, abstractmethod
from typing import Any, Dict
from app.schemas.ivr import IVRResponse, TelephonyCallEvent


class TelephonyProvider(ABC):
    """Abstract base class for telephony providers (Mock, Twilio, Exotel, etc.)."""

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
