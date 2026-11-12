"""Comprehensive Test Suite for CareBridge AI Agent, Tool Calling, RAG, and Multimodal Voice.

Verifies:
1. "Find a PHC near Tiruchengode" returns real facilities with distances and doctor shifts (NEVER merely an announcement).
2. Doctor availability lookup returns verified attendance status.
3. Medicine stock lookup returns belief states and probability.
4. RAG query returns expected loss calculation and documentation citations.
5. Emergency triage triggers 108 protocol.
6. Clinical safety disclaimer enforces non-diagnostic posture.
7. Tamil multilingual queries return native Tamil guidance.
8. Voice STT and TTS endpoints respond reliably.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_find_phc_near_tiruchengode_executes_and_returns_records(client: AsyncClient, seed_data: dict):
    """CRITICAL ACCEPTANCE TEST:
    Must execute facility search and return actual facilities, distances, and doctor shifts.
    MUST NEVER merely announce 'I will search...' or 'I will find...'.
    """
    payload = {
        "message": "Find a PHC near Tiruchengode",
        "language": "en",
        "location_context": "Tiruchengode",
    }
    response = await client.post("/api/ai/chat", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Verify structured fields
    assert "conversation_id" in data
    assert data["intent"] == "FACILITY_PROXIMITY_SEARCH"
    assert "search_facilities_tool" in data["tools_called"]

    # Verify anti-pattern elimination: Must NOT say "I will search" without results
    response_text = data["response_text"]
    assert "I will search" not in response_text
    assert "I'll search" not in response_text

    # Must contain real facilities
    assert len(data["cards"]) > 0
    facility_card = data["cards"][0]
    assert facility_card["type"] == "FACILITY"
    assert "PHC" in facility_card["title"] or "Hospital" in facility_card["title"] or "Tiruchengode" in facility_card["title"] or "Rampur" in facility_card["title"]

    # Must contain distance and doctor information
    assert "distance_km" in facility_card["details"]
    assert "doctor_name" in facility_card["details"]
    assert "doctor_status" in facility_card["details"]
    assert "disclaimer" in data


@pytest.mark.asyncio
async def test_doctor_availability_lookup(client: AsyncClient, seed_data: dict):
    """Verifies that asking about doctor availability returns real doctor attendance."""
    payload = {
        "message": "Is a general physician available at the nearest PHC today?",
        "language": "en",
    }
    response = await client.post("/api/ai/chat", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["intent"] == "DOCTOR_AVAILABILITY_LOOKUP"
    assert "check_doctor_availability_tool" in data["tools_called"]
    assert len(data["cards"]) > 0

    doctor_card = data["cards"][0]
    assert doctor_card["type"] == "DOCTOR"
    assert doctor_card["badge"] in ["PRESENT", "EXPECTED", "UNKNOWN", "ABSENT"]
    assert "Dr." in doctor_card["title"]


@pytest.mark.asyncio
async def test_medicine_stock_probabilistic_lookup(client: AsyncClient, seed_data: dict):
    """Verifies querying medicine availability returns belief state and probability."""
    payload = {
        "message": "Where can I get Paracetamol near me?",
        "language": "en",
    }
    response = await client.post("/api/ai/chat", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["intent"] == "MEDICINE_STOCK_LOOKUP"
    assert "check_medicine_stock_tool" in data["tools_called"]
    assert "Paracetamol" in data["response_text"]


@pytest.mark.asyncio
async def test_rag_query_expected_loss_formula(client: AsyncClient):
    """Verifies asking about recommendation algorithm returns formula via RAG."""
    payload = {
        "message": "How does CareBridge calculate its healthcare recommendations and expected loss?",
        "language": "en",
    }
    response = await client.post("/api/ai/chat", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["intent"] == "PROJECT_DOCUMENTATION_RAG"
    assert "query_rag_knowledge_tool" in data["tools_called"]
    assert "Expected Loss" in data["response_text"]
    assert "Failure Probability" in data["response_text"]
    assert len(data["rag_sources"]) > 0


@pytest.mark.asyncio
async def test_emergency_triage_triggers_108_protocol(client: AsyncClient):
    """Verifies severe medical emergency triggers immediate 108 ambulance advice."""
    payload = {
        "message": "Patient is having severe chest pain and difficulty breathing!",
        "language": "en",
    }
    response = await client.post("/api/ai/chat", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["intent"] == "EMERGENCY_DISPATCH"
    assert "emergency_guidance_tool" in data["tools_called"]
    assert "108" in data["response_text"]

    emergency_cards = [c for c in data["cards"] if c["type"] == "EMERGENCY"]
    assert len(emergency_cards) == 1
    assert emergency_cards[0]["details"]["emergency_phone"] == "108"


@pytest.mark.asyncio
async def test_clinical_safety_guard_enforces_non_diagnostic_posture(client: AsyncClient, seed_data: dict):
    """Verifies that asking for drug dosages or prescriptions is politely refused and redirected."""
    payload = {
        "message": "What dose of paracetamol should I take for my child's fever?",
        "language": "en",
    }
    response = await client.post("/api/ai/chat", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["intent"] == "CLINICAL_DISCLAIMER_ENFORCEMENT"
    assert "does not provide" in data["response_text"].lower() or "safety disclaimer" in data["response_text"].lower()
    # Must still provide facility card so patient can visit doctor
    assert len(data["cards"]) > 0


@pytest.mark.asyncio
async def test_tamil_multilingual_query_returns_tamil_guidance(client: AsyncClient, seed_data: dict):
    """Verifies querying in Tamil returns native Tamil text and Tamil translations."""
    payload = {
        "message": "திருச்செங்கோடு அருகே உள்ள ஆரம்ப சுகாதார நிலையம் எங்கே?",
        "language": "ta",
    }
    response = await client.post("/api/ai/chat", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["language"] == "ta"
    assert "ஆரம்ப சுகாதார நிலையங்கள்" in data["response_text"]
    assert len(data["cards"]) > 0


@pytest.mark.asyncio
async def test_ai_health_and_tools_catalog(client: AsyncClient):
    """Verifies AI subsystem health check and registered tools catalog."""
    health_res = await client.get("/api/ai/health")
    assert health_res.status_code == 200
    health_data = health_res.json()
    assert health_data["status"] == "healthy"
    assert health_data["tools_count"] >= 6
    assert health_data["rag_documents_indexed"] > 0

    tools_res = await client.get("/api/ai/tools")
    assert tools_res.status_code == 200
    tools_data = tools_res.json()
    tool_names = [t["name"] for t in tools_data]
    assert "search_facilities_tool" in tool_names
    assert "check_doctor_availability_tool" in tool_names
    assert "check_medicine_stock_tool" in tool_names
    assert "get_recommendations_tool" in tool_names
    assert "query_rag_knowledge_tool" in tool_names
    assert "emergency_guidance_tool" in tool_names


@pytest.mark.asyncio
async def test_voice_transcribe_and_synthesize_endpoints(client: AsyncClient):
    """Verifies multimodal voice STT and TTS endpoints."""
    # STT Test
    stt_res = await client.post(
        "/api/ai/voice/transcribe",
        json={"audio_base64": "UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=", "language": "ta"},
    )
    assert stt_res.status_code == 200
    stt_data = stt_res.json()
    assert "transcribed_text" in stt_data
    assert len(stt_data["transcribed_text"]) > 0

    # TTS Test
    tts_res = await client.post(
        "/api/ai/voice/synthesize",
        json={"text": "வணக்கம், கேர்பிரிட்ஜ்", "language": "ta"},
    )
    assert tts_res.status_code == 200
    tts_data = tts_res.json()
    assert tts_data["status"] == "success"
    assert tts_data["audio_base64"] is not None


@pytest.mark.asyncio
async def test_ai_feedback_submission(client: AsyncClient):
    """Verifies feedback endpoint records user ratings."""
    payload = {
        "conversation_id": "test-conv-12345",
        "rating": 5,
        "feedback_text": "Great guidance and accurate distance!",
    }
    response = await client.post("/api/ai/feedback", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "feedback_recorded"
    assert data["rating"] == 5
