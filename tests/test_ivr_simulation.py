import pytest
from httpx import AsyncClient
from app.services.pincode_service import PincodeService


@pytest.mark.asyncio
async def test_pincode_resolution_service_valid():
    """Verify exact and regional postal PIN code resolution across India."""
    # 1. Exact match for Tiruchengode, Tamil Nadu
    res = PincodeService.resolve_pincode("637211")
    assert res["pincode"] == "637211"
    assert "Namakkal" in res["district"]
    assert res["state"] == "Tamil Nadu"
    assert res["is_approximate"] is True
    assert res["confidence"] == "EXACT"
    assert abs(res["latitude"] - 11.3800) < 0.01

    # 2. Exact match for Chennai GPO
    res_chn = PincodeService.resolve_pincode("600001")
    assert res_chn["pincode"] == "600001"
    assert res_chn["district"] == "Chennai"
    assert res_chn["state"] == "Tamil Nadu"
    assert res_chn["confidence"] == "EXACT"

    # 3. Regional postal circle prefix match for a valid unlisted PIN code
    res_circle = PincodeService.resolve_pincode("637001")
    assert res_circle["pincode"] == "637001"
    assert res_circle["state"] == "Tamil Nadu"
    assert res_circle["confidence"] == "POSTAL_CIRCLE"
    assert res_circle["is_approximate"] is True


@pytest.mark.asyncio
async def test_pincode_resolution_service_invalid():
    """Verify validation and rejection of malformed or invalid PIN codes."""
    from fastapi import HTTPException

    # 1. Starts with 0 (invalid Indian postal zone)
    with pytest.raises(HTTPException) as exc:
        PincodeService.resolve_pincode("012345")
    assert exc.value.status_code == 400
    assert exc.value.detail["error"]["code"] == "INVALID_PINCODE_FORMAT"

    # 2. Too short
    with pytest.raises(HTTPException) as exc:
        PincodeService.resolve_pincode("1234")
    assert exc.value.status_code == 400

    # 3. Non-numeric
    with pytest.raises(HTTPException) as exc:
        PincodeService.resolve_pincode("63721A")
    assert exc.value.status_code == 400

    # 4. Unknown postal zone
    with pytest.raises(HTTPException) as exc:
        PincodeService.resolve_pincode("999999")
    assert exc.value.status_code == 404
    assert exc.value.detail["error"]["code"] == "PINCODE_NOT_FOUND"


@pytest.mark.asyncio
async def test_public_pincode_api_endpoint(client: AsyncClient):
    """Verify GET /api/pincodes/resolve is publicly accessible without authentication."""
    resp = await client.get("/api/pincodes/resolve", params={"pincode": "637211"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["pincode"] == "637211"
    assert data["state"] == "Tamil Nadu"
    assert data["is_approximate"] is True


@pytest.mark.asyncio
async def test_simulated_ivr_start_call(client: AsyncClient):
    """Verify public simulated IVR start returns language selection prompt."""
    resp = await client.post("/api/ivr/simulation/start", json={"language": "ta"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "IN_PROGRESS"
    assert data["current_menu"] == "LANGUAGE_SELECT"
    assert "NALAM AI" in data["speak_text"]
    assert data["gather_dtmf"] is True
    assert len(data["options"]) == 2


@pytest.mark.asyncio
async def test_simulated_ivr_language_and_main_menu(client: AsyncClient):
    """Verify language selection transitions to main menu in chosen language."""
    # Start
    start_res = (await client.post("/api/ivr/simulation/start")).json()
    call_sid = start_res["call_sid"]

    # Select 2 for English
    input_res = await client.post(
        "/api/ivr/simulation/input",
        json={"call_sid": call_sid, "digits": "2", "current_menu": "LANGUAGE_SELECT", "language": "en"},
    )
    assert input_res.status_code == 200
    data = input_res.json()
    assert data["current_menu"] == "MAIN_MENU"
    assert data["language"] == "en"
    assert "Main Menu" in data["speak_text"]
    assert "Press 1 to find nearby healthcare facilities" in data["speak_text"]

    # Select 1 for Tamil
    input_ta = await client.post(
        "/api/ivr/simulation/input",
        json={"call_sid": call_sid, "digits": "1", "current_menu": "LANGUAGE_SELECT", "language": "ta"},
    )
    assert input_ta.status_code == 200
    assert input_ta.json()["current_menu"] == "MAIN_MENU"
    assert input_ta.json()["language"] == "ta"
    assert "முதன்மை மெனு" in input_ta.json()["speak_text"]


@pytest.mark.asyncio
async def test_simulated_ivr_services_and_assistance_options(client: AsyncClient):
    """Verify Option 2 (Services), Option 3 (Assistance), Repeat (9), and Return to Menu (0)."""
    call_sid = "sim-test-services"

    # Press 2: Healthcare services
    s2 = await client.post(
        "/api/ivr/simulation/input",
        json={"call_sid": call_sid, "digits": "2", "current_menu": "MAIN_MENU", "language": "en"},
    )
    assert s2.status_code == 200
    assert s2.json()["current_menu"] == "SERVICES_INFO"
    assert "Primary Health Centres" in s2.json()["speak_text"]

    # Press 9: Repeat services
    s9 = await client.post(
        "/api/ivr/simulation/input",
        json={"call_sid": call_sid, "digits": "9", "current_menu": "SERVICES_INFO", "language": "en"},
    )
    assert s9.status_code == 200
    assert s9.json()["current_menu"] == "SERVICES_INFO"

    # Press 0: Return to Main Menu
    s0 = await client.post(
        "/api/ivr/simulation/input",
        json={"call_sid": call_sid, "digits": "0", "current_menu": "SERVICES_INFO", "language": "en"},
    )
    assert s0.status_code == 200
    assert s0.json()["current_menu"] == "MAIN_MENU"

    # Press 3: Emergency assistance and contacts
    s3 = await client.post(
        "/api/ivr/simulation/input",
        json={"call_sid": call_sid, "digits": "3", "current_menu": "MAIN_MENU", "language": "en"},
    )
    assert s3.status_code == 200
    assert s3.json()["current_menu"] == "ASSISTANCE_INFO"
    assert "112" in s3.json()["speak_text"]
    assert "108" in s3.json()["speak_text"]


@pytest.mark.asyncio
async def test_simulated_ivr_invalid_inputs_and_repeat(client: AsyncClient):
    """Verify handling of invalid keypad options gracefully."""
    call_sid = "sim-test-invalid"

    # Invalid digit 8 from MAIN_MENU
    inv = await client.post(
        "/api/ivr/simulation/input",
        json={"call_sid": call_sid, "digits": "8", "current_menu": "MAIN_MENU", "language": "en"},
    )
    assert inv.status_code == 200
    data = inv.json()
    assert data["current_menu"] == "MAIN_MENU"
    assert "Invalid option" in data["speak_text"]


@pytest.mark.asyncio
async def test_simulated_ivr_facilities_via_pincode_and_distance_order(client: AsyncClient, seed_data: dict):
    """Verify Option 1 with PIN code input queries real database and returns ascending distance order."""
    call_sid = "sim-test-facilities"

    # 1. Option 1 from Main Menu
    opt1 = await client.post(
        "/api/ivr/simulation/input",
        json={"call_sid": call_sid, "digits": "1", "current_menu": "MAIN_MENU", "language": "en"},
    )
    assert opt1.status_code == 200
    assert opt1.json()["current_menu"] == "LOCATION_INPUT"

    # 2. Enter 6-digit PIN code "560001#" (Bengaluru Postal area, matching seeded test facilities)
    pin_input = await client.post(
        "/api/ivr/simulation/input",
        json={"call_sid": call_sid, "digits": "560001#", "current_menu": "LOCATION_INPUT", "language": "en"},
    )
    assert pin_input.status_code == 200
    data = pin_input.json()
    assert data["current_menu"] == "FACILITIES_RESULTS"
    assert data["is_approximate"] is True
    assert "facilities" in data
    assert len(data["facilities"]) > 0

    # Verify facilities are ordered by strictly ascending distance
    distances = [f["distance_km"] for f in data["facilities"]]
    assert distances == sorted(distances), f"Distances must be in ascending order: {distances}"
    assert distances[0] >= 0.0

    # Verify spoken text contains facility details and approximate notice
    assert "approximate postal area" in data["speak_text"]
    assert data["facilities"][0]["name"] in data["speak_text"]


@pytest.mark.asyncio
async def test_simulated_ivr_facilities_via_gps_coordinates(client: AsyncClient, seed_data: dict):
    """Verify Option 1 with GPS coordinate payload queries database directly."""
    call_sid = "sim-test-gps"

    gps_input = await client.post(
        "/api/ivr/simulation/input",
        json={
            "call_sid": call_sid,
            "digits": "*",
            "current_menu": "LOCATION_INPUT",
            "language": "ta",
            "location_data": {"latitude": 12.9720, "longitude": 77.5940, "name": "ராம்பூர்"},
        },
    )
    assert gps_input.status_code == 200
    data = gps_input.json()
    assert data["current_menu"] == "FACILITIES_RESULTS"
    assert len(data["facilities"]) > 0
    # First facility must be closest
    assert data["facilities"][0]["distance_km"] <= data["facilities"][-1]["distance_km"]


@pytest.mark.asyncio
async def test_simulated_ivr_empty_facilities_radius(client: AsyncClient, seed_data: dict):
    """Verify graceful handling when no facilities exist in search area."""
    call_sid = "sim-test-empty"

    # Coords in the middle of the Indian Ocean
    empty_input = await client.post(
        "/api/ivr/simulation/input",
        json={
            "call_sid": call_sid,
            "digits": "*",
            "current_menu": "LOCATION_INPUT",
            "language": "en",
            "location_data": {"latitude": 5.0, "longitude": 80.0, "name": "Remote Ocean Area"},
        },
    )
    assert empty_input.status_code == 200
    data = empty_input.json()
    assert data["current_menu"] == "LOCATION_INPUT"
    assert "No healthcare facilities found" in data["speak_text"]


@pytest.mark.asyncio
async def test_simulated_ivr_village_option_switch(client: AsyncClient):
    """Verify pressing 4 in LOCATION_INPUT guides user to village locality search."""
    call_sid = "sim-test-vswitch"

    resp = await client.post(
        "/api/ivr/simulation/input",
        json={"call_sid": call_sid, "digits": "4", "current_menu": "LOCATION_INPUT", "language": "en"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_menu"] == "VILLAGE_SEARCH_INPUT"
    assert "village search input" in data["speak_text"]
