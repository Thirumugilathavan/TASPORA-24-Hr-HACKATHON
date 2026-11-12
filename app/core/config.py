import json
from typing import List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "CareBridge"
    API_V1_PREFIX: str = "/api"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Security
    SECRET_KEY: str = "carebridge-dev-secret-key-at-least-32-chars-long"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./carebridge.db"

    # CORS
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # Delivery Methods (Configurable, unhardcoded)
    SUPPORTED_DELIVERY_METHODS: Union[List[str], str] = [
        "COMMUNITY_HEALTH_WORKER",
        "VOLUNTEER",
        "LOCAL_COURIER",
    ]

    # Simulation Transparency Flag
    IS_SIMULATED: bool = True

    # IVR & Voice Access Settings
    IVR_API_KEY: str = "carebridge-ivr-secret-api-key"
    IVR_PROVIDER: str = "mock"
    IVR_SESSION_TIMEOUT_MINUTES: int = 10
    IVR_MAX_AUTH_ATTEMPTS: int = 3
    IVR_AUTH_LOCKOUT_MINUTES: int = 15
    IVR_DEFAULT_LANGUAGE: str = "ta"
    IVR_AUDIO_BASE_URL: str = ""
    IVR_EMERGENCY_NUMBER: str = "108"
    IVR_ALLOW_DEMO_PHONE_PIN: bool = True
    TWILIO_AUTH_TOKEN: Optional[str] = None

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return []

    @field_validator("SUPPORTED_DELIVERY_METHODS", mode="before")
    @classmethod
    def assemble_delivery_methods(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return []

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
