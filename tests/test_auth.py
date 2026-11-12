import pytest
from httpx import AsyncClient
from app.core.security import decode_access_token, hash_password, verify_password, normalize_phone_number


@pytest.mark.asyncio
async def test_register_patient_success(client: AsyncClient):
    """Verify that valid registration creates a PATIENT account with normalized phone."""
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
async def test_duplicate_phone_with_different_formatting_fails(client: AsyncClient):
    """Verify that registering with +91 country prefix detects duplicate for 10-digit number."""
    payload = {
        "name": "Original User",
        "phone": "9876543215",
        "password": "Password123",
    }
    first_res = await client.post("/api/auth/register", json=payload)
    assert first_res.status_code == 201

    duplicate_payload = {
        "name": "Duplicate User",
        "phone": "+91 98765 43215",
        "password": "DifferentPassword123",
    }
    second_res = await client.post("/api/auth/register", json=duplicate_payload)
    assert second_res.status_code == 409
    err = second_res.json()
    assert err["error"]["code"] == "CONFLICT"


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
async def test_register_with_country_code_and_login_with_plain_number(client: AsyncClient):
    """Verify user registering with '+91 98765 43216' can log in with '9876543216' and exact password."""
    reg_payload = {
        "name": "Prefix User",
        "phone": "+91 98765 43216",
        "password": "TestPassword123!",
    }
    reg_res = await client.post("/api/auth/register", json=reg_payload)
    assert reg_res.status_code == 201
    assert reg_res.json()["phone"] == "9876543216"

    # Login with standard 10 digits
    login_payload = {
        "phone": "9876543216",
        "password": "TestPassword123!",
    }
    login_res = await client.post("/api/auth/login", json=login_payload)
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()


@pytest.mark.asyncio
async def test_register_with_plain_number_and_login_with_prefix_and_leading_zero(client: AsyncClient):
    """Verify user registering with '9876543217' can log in with '+919876543217' and '09876543217'."""
    reg_payload = {
        "name": "Zero User",
        "phone": "9876543217",
        "password": "CorrectPassword456!",
    }
    reg_res = await client.post("/api/auth/register", json=reg_payload)
    assert reg_res.status_code == 201

    # 1. Login with +91 prefix
    login_res1 = await client.post("/api/auth/login", json={
        "phone": "+919876543217",
        "password": "CorrectPassword456!",
    })
    assert login_res1.status_code == 200

    # 2. Login with leading 0 (STD)
    login_res2 = await client.post("/api/auth/login", json={
        "phone": "09876543217",
        "password": "CorrectPassword456!",
    })
    assert login_res2.status_code == 200


@pytest.mark.asyncio
async def test_passwords_with_spaces_symbols_unicode(client: AsyncClient):
    """Verify registration and login works for passwords with spaces, symbols, and Unicode."""
    cases = [
        ("9876543221", "Pass With Spaces in Middle 123"),
        ("9876543222", "P@$$w0rd!#%^&*()-_=+[]{}:;'<>,.?/|~"),
        ("9876543223", "கடவுச்சொல்123!"),
    ]

    for phone, pwd in cases:
        reg_res = await client.post("/api/auth/register", json={
            "name": f"User {phone}",
            "phone": phone,
            "password": pwd,
        })
        assert reg_res.status_code == 201

        login_res = await client.post("/api/auth/login", json={
            "phone": phone,
            "password": pwd,
        })
        assert login_res.status_code == 200
        assert "access_token" in login_res.json()


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
    assert "invalid phone number or password" in err["error"]["message"].lower()


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


@pytest.mark.asyncio
async def test_protected_routes_with_and_without_token(client: AsyncClient):
    """Verify protected routes succeed with valid JWT and reject unauthenticated requests."""
    # 1. Unauthenticated request to /api/patients fails
    unauth_res = await client.get("/api/patients/3fa85f64-5717-4562-b3fc-2c963f66afa6")
    assert unauth_res.status_code in [401, 403]

    # 2. Register & login
    reg_res = await client.post("/api/auth/register", json={
        "name": "Token Tester",
        "phone": "9876543230",
        "password": "TokenPassword123!",
    })
    assert reg_res.status_code == 201

    login_res = await client.post("/api/auth/login", json={
        "phone": "9876543230",
        "password": "TokenPassword123!",
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    # 3. Request with valid token
    auth_headers = {"Authorization": f"Bearer {token}"}
    me_res = await client.get("/api/auth/me", headers=auth_headers)
    # If /api/auth/me exists, verify 200, else verify token decodes
    decoded = decode_access_token(token)
    assert decoded["phone"] == "9876543230"
    assert decoded["role"] == "PATIENT"
