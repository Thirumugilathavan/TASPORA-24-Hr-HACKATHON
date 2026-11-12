from typing import Optional
from app.core.config import settings
from app.integrations.telephony.base import TelephonyProvider
from app.integrations.telephony.mock_provider import MockTelephonyProvider
from app.integrations.telephony.twilio_provider import TwilioTelephonyProvider


def get_telephony_provider(name: Optional[str] = None) -> TelephonyProvider:
    """Factory retrieving active telephony provider based on configuration."""
    if name:
        provider_name = name
    elif getattr(settings, "TELEPHONY_PROVIDER", "mock").lower() == "twilio":
        provider_name = "twilio"
    elif getattr(settings, "IVR_PROVIDER", "mock").lower() == "twilio":
        provider_name = "twilio"
    else:
        provider_name = getattr(settings, "TELEPHONY_PROVIDER", getattr(settings, "IVR_PROVIDER", "mock"))

    if str(provider_name).lower() == "twilio":
        return TwilioTelephonyProvider()
    return MockTelephonyProvider()
