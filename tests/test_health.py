import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check_endpoint(client: AsyncClient):
    """Verify health endpoint returns status, simulated disclosure, and database status."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["project"] == "NALAM AI"
    assert data["simulated_mode"] is True
    assert "disclosure" in data
    assert "synthetic" in data["disclosure"].lower()
    assert data["database"] == "connected"


@pytest.mark.asyncio
async def test_api_root_endpoint(client: AsyncClient):
    """Verify base /api endpoint returns HTTP 200 directly without redirect."""
    response = await client.get("/api")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["project"] == "CareBridge"
