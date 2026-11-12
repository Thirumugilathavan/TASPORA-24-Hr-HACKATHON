from typing import Optional
from app.core.config import settings
from app.integrations.telephony.base import TelephonyProvider
from app.integrations.telephony.mock_provider import MockTelephonyProvider
from app.integrations.telephony.twilio_provider import TwilioTelephonyProvider


def get_telephony_provider(name: Optional[str] = None) -> TelephonyProvider:
    """Factory retrieving active telephony provider based on configuration."""
    provider_name = (name or getattr(settings, "IVR_PROVIDER", "mock")).lower()
    if provider_name == "twilio":
        return TwilioTelephonyProvider()
    return MockTelephonyProvider()
