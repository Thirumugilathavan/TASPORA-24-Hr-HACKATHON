import pytest
from httpx import AsyncClient
from app.core.security import decode_access_token


@pytest.mark.asyncio
async def test_register_patient_success(client: AsyncClient):
    """Verify that valid registration creates a PATIENT account."""
    payload = {
        "name": "Arun Kumar",
        "phone": "9876543210",
        "password": "SecurePassword123",
        "role": "PATIENT",
    }
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Arun Kumar"
    assert data["phone"] == "9876543210"
    assert data["role"] == "PATIENT"
    assert "id" in data
    assert "password" not in data
    assert "password_hash" not in data


@pytest.mark.asyncio
async def test_register_enforces_patient_role_and_ignores_client_role(client: AsyncClient):
    """SECURITY TEST: Verify that public registration ignores client-supplied privileged role
    and strictly enforces PATIENT role.
    """
    payload = {
        "name": "Malicious Actor",
        "phone": "9876543211",
        "password": "AdminPassword123",
        "role": "ADMIN",  # Attempting to elevate to ADMIN during public registration
    }
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    # Must NOT be ADMIN, must strictly be PATIENT
    assert data["role"] == "PATIENT"


@pytest.mark.asyncio
async def test_register_duplicate_phone_fails(client: AsyncClient):
    """Verify that registering with an already existing phone number returns HTTP 409 CONFLICT."""
    payload = {
        "name": "First User",
        "phone": "9876543212",
        "password": "Password123",
    }
    first_res = await client.post("/api/auth/register", json=payload)
    assert first_res.status_code == 201

    duplicate_payload = {
        "name": "Duplicate User",
        "phone": "9876543212",
        "password": "DifferentPassword123",
    }
    second_res = await client.post("/api/auth/register", json=duplicate_payload)
    assert second_res.status_code == 409
    err = second_res.json()
    assert "error" in err
    assert err["error"]["code"] == "CONFLICT"
    assert "already registered" in err["error"]["message"].lower()


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """Verify that valid login returns a Bearer JWT token with user_id and role."""
    reg_payload = {
        "name": "Login Test User",
        "phone": "9876543213",
        "password": "MySecretPassword",
    }
    await client.post("/api/auth/register", json=reg_payload)

    login_payload = {
        "phone": "9876543213",
        "password": "MySecretPassword",
    }
    login_res = await client.post("/api/auth/login", json=login_payload)
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    assert token_data["role"] == "PATIENT"
    assert "user_id" in token_data

    # Verify token payload contents
    payload = decode_access_token(token_data["access_token"])
    assert payload is not None
    assert payload["sub"] == token_data["user_id"]
    assert payload["role"] == "PATIENT"


@pytest.mark.asyncio
async def test_login_invalid_password_fails(client: AsyncClient):
    """Verify that an incorrect password returns HTTP 401 UNAUTHORIZED."""
    reg_payload = {
        "name": "Wrong Pwd User",
        "phone": "9876543214",
        "password": "CorrectPassword",
    }
    await client.post("/api/auth/register", json=reg_payload)

    login_payload = {
        "phone": "9876543214",
        "password": "WrongPassword",
    }
    login_res = await client.post("/api/auth/login", json=login_payload)
    assert login_res.status_code == 401
    err = login_res.json()
    assert "error" in err
    assert err["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_nonexistent_phone_fails(client: AsyncClient):
    """Verify that an unregistered phone returns HTTP 401 UNAUTHORIZED."""
    login_payload = {
        "phone": "9999999999",
        "password": "AnyPassword",
    }
    login_res = await client.post("/api/auth/login", json=login_payload)
    assert login_res.status_code == 401
    err = login_res.json()
    assert "error" in err
    assert err["error"]["code"] == "INVALID_CREDENTIALS"
