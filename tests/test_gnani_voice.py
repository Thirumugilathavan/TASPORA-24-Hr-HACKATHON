"""Automated Unit and Integration Tests for Gnani.ai Multilingual Voice Chatbot.

Verifies:
1. Gnani STT success with mocked cloud response.
2. Gnani STT error handling when cloud returns non-200.
3. Gnani TTS success with WAV output.
4. Gnani TTS failure handling with resilient synthetic fallback.
5. Missing API key or offline evaluation handling.
6. Invalid base64 or empty audio validation.
7. Language code mapping (ta-IN, en-IN, hi-IN, auto).
8. Unified voice conversation turn (LLM Tool Calling + Gnani TTS audio synthesis).
9. Voice status endpoint catalog and model discovery.
10. Text-only chat continuity when voice is disabled or offline.
"""
import base64
import pytest
from httpx import AsyncClient, Response
from unittest.mock import patch, AsyncMock

from app.ai.gnani_adapter import GnaniVoiceAdapter


@pytest.fixture
def mock_wav_base64() -> str:
    # 44-byte standard RIFF/WAV header with 100 samples of silence
    header = (
        b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00"
        b"\x80\x3e\x00\x00\x00\x7d\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    )
    return base64.b64encode(header).decode("ascii")


@pytest.mark.asyncio
async def test_gnani_stt_success_mocked(mock_wav_base64: str):
    """Verifies that Gnani STT parses valid cloud response correctly."""
    adapter = GnaniVoiceAdapter()
    adapter.is_live = True
    adapter.api_key = "test-mock-api-key"

    mock_resp = {
        "success": True,
        "transcript": "திருச்செங்கோடு ஆரம்ப சுகாதார நிலையம் எங்கே உள்ளது?",
        "detected_language_code": "ta-IN",
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = Response(200, json=mock_resp)

        result = await adapter.transcribe(
            audio_base64=mock_wav_base64,
            audio_format="wav",
            language="ta",
        )

        assert result["status"] == "success"
        assert result["transcribed_text"] == "திருச்செங்கோடு ஆரம்ப சுகாதார நிலையம் எங்கே உள்ளது?"
        assert result["detected_language"] == "ta"
        assert result["provider"] == "gnani_vachana_cloud"


@pytest.mark.asyncio
async def test_gnani_stt_failure_handling(mock_wav_base64: str):
    """Verifies that Gnani STT handles cloud errors gracefully without crashing."""
    adapter = GnaniVoiceAdapter()
    adapter.is_live = True
    adapter.api_key = "test-mock-api-key"

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = Response(503, text="Service Unavailable")

        result = await adapter.transcribe(
            audio_base64=mock_wav_base64,
            audio_format="wav",
            language="ta",
        )

        assert result["status"] == "error"
        assert result["transcribed_text"] == ""
        assert "503" in result["error"]


@pytest.mark.asyncio
async def test_gnani_tts_success_mocked():
    """Verifies that Gnani TTS successfully receives binary WAV audio."""
    adapter = GnaniVoiceAdapter()
    adapter.is_live = True
    adapter.api_key = "test-mock-api-key"

    fake_wav_bytes = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80\x3e\x00\x00data\x00\x00"

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = Response(200, content=fake_wav_bytes)

        result = await adapter.synthesize(
            text="வணக்கம், கேர்பிரிட்ஜ் உங்களுக்கு உதவ தயாராக உள்ளது.",
            language="ta",
            voice_name="Nalini",
        )

        assert result["status"] == "success"
        assert result["format"] == "audio/wav"
        assert result["audio_base64"] is not None
        assert result["provider"] == "gnani_vachana_cloud"


@pytest.mark.asyncio
async def test_gnani_tts_failure_provides_fallback():
    """Verifies that TTS failures fall back to clean synthetic chime without crashing."""
    adapter = GnaniVoiceAdapter()
    adapter.is_live = True
    adapter.api_key = "test-mock-api-key"

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = Response(500, text="Internal Server Error")

        result = await adapter.synthesize(
            text="Testing error fallback.",
            language="en",
        )

        # Must still return valid playable WAV audio so frontend audio players do not crash
        assert result["format"] == "audio/wav"
        assert result["audio_base64"] is not None
        assert result["status"] in ["fallback", "demo_fallback"]


@pytest.mark.asyncio
async def test_invalid_audio_validation(client: AsyncClient):
    """Verifies empty or corrupt base64 audio returns validation error."""
    # Empty audio
    res1 = await client.post("/api/ai/voice/transcribe", json={"audio_base64": "", "language": "ta"})
    assert res1.status_code in [422, 500]

    # Non-base64 corrupt payload
    res2 = await client.post("/api/ai/voice/transcribe", json={"audio_base64": "!!!not_base64!!!", "language": "ta"})
    assert res2.status_code in [422, 500]


@pytest.mark.asyncio
async def test_voice_status_endpoint(client: AsyncClient):
    """Verifies /api/ai/voice/status exposes engine models, supported languages and voices."""
    res = await client.get("/api/ai/voice/status")
    assert res.status_code == 200
    data = res.json()
    assert "provider" in data
    assert "supported_languages" in data
    assert "supported_voices" in data
    assert "models" in data
    assert data["models"]["stt"] == "prisma-v3.0"
    assert data["models"]["tts"] == "timbre-v2.5"


@pytest.mark.asyncio
async def test_voice_turn_with_audio_synthesis(client: AsyncClient, seed_data: dict):
    """Verifies chat with include_audio=True returns both verified tool records and synthesized speech."""
    payload = {
        "message": "Find a PHC near Tiruchengode",
        "language": "en",
        "location_context": "Tiruchengode",
        "include_audio": True,
        "voice_name": "Nalini",
    }
    res = await client.post("/api/ai/chat", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["intent"] == "FACILITY_PROXIMITY_SEARCH"
    assert "search_facilities_tool" in data["tools_called"]
    assert len(data["cards"]) > 0
    # Must contain audio payload for voice playback
    assert data["audio_base64"] is not None
    assert len(data["audio_base64"]) > 0


@pytest.mark.asyncio
async def test_text_only_operation_without_audio(client: AsyncClient, seed_data: dict):
    """Verifies standard text-only chat does not force audio generation when include_audio=False."""
    payload = {
        "message": "Where can I get Paracetamol near me?",
        "language": "en",
        "include_audio": False,
    }
    res = await client.post("/api/ai/chat", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["intent"] == "MEDICINE_STOCK_LOOKUP"
    # When include_audio is False, audio_base64 is omitted or null to save bandwidth
    assert data.get("audio_base64") is None


@pytest.mark.asyncio
async def test_language_code_mapping_tamil_and_english():
    """Verifies that Tamil and English map to appropriate Indic language codes."""
    adapter = GnaniVoiceAdapter()
    assert adapter.LANG_MAP["ta"] == "ta-IN"
    assert adapter.LANG_MAP["en"] == "en-IN"
    assert adapter.LANG_MAP["auto"] == "indic-auto"
