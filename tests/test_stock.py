import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.stock import StockReport


@pytest.mark.asyncio
async def test_create_stock_report_staff_success(client: AsyncClient, seed_data: dict):
    """Verify POST /api/stock/report:
    - report_id returned
    - verification_status = PENDING
    - updated: p_available, confidence returned
    """
    fac_1 = seed_data["facilities"][0]
    med_1 = seed_data["medicines"][0]
    staff_headers = seed_data["headers"]["staff"]

    payload = {
        "facility_id": str(fac_1.id),
        "medicine_id": str(med_1.id),
        "availability_status": "IN_STOCK",
    }

    response = await client.post(
        "/api/stock/report",
        json=payload,
        headers=staff_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert "report_id" in data
    assert data["verification_status"] == "PENDING"
    assert "updated" in data
    assert "p_available" in data["updated"]
    assert "confidence" in data["updated"]
    assert 0.0 <= data["updated"]["p_available"] <= 1.0
    assert 0.0 <= data["updated"]["confidence"] <= 1.0


@pytest.mark.asyncio
async def test_server_derived_source_type_never_trusts_client(
    client: AsyncClient, db_session: AsyncSession, seed_data: dict
):
    """The server must determine source_type strictly from the authenticated caller's role.
    Never trust a client-provided source_type.
    """
    fac_1 = seed_data["facilities"][0]
    med_1 = seed_data["medicines"][0]
    patient_headers = seed_data["headers"]["patient"]

    payload = {
        "facility_id": str(fac_1.id),
        "medicine_id": str(med_1.id),
        "availability_status": "IN_STOCK",
        "source_type": "STAFF",  # Spoof attempt in body
    }

    response = await client.post(
        "/api/stock/report",
        json=payload,
        headers=patient_headers,
    )
    assert response.status_code == 201
    rep_id = uuid.UUID(response.json()["report_id"])

    # Verify directly in the DB ledger that source_type was set to PATIENT
    stmt = select(StockReport).where(StockReport.id == rep_id)
    res = await db_session.execute(stmt)
    report_in_db = res.scalar_one_or_none()
    assert report_in_db is not None
    assert report_in_db.source_type == "PATIENT"


@pytest.mark.asyncio
async def test_stock_report_missing_facility_or_medicine_404(client: AsyncClient, seed_data: dict):
    """Verify 404 error when facility or medicine does not exist."""
    med_1 = seed_data["medicines"][0]
    fac_1 = seed_data["facilities"][0]
    staff_headers = seed_data["headers"]["staff"]

    bad_fac_payload = {
        "facility_id": str(uuid.uuid4()),
        "medicine_id": str(med_1.id),
        "availability_status": "IN_STOCK",
    }
    resp1 = await client.post("/api/stock/report", json=bad_fac_payload, headers=staff_headers)
    assert resp1.status_code == 404
    assert resp1.json()["error"]["code"] == "NOT_FOUND"

    bad_med_payload = {
        "facility_id": str(fac_1.id),
        "medicine_id": str(uuid.uuid4()),
        "availability_status": "IN_STOCK",
    }
    resp2 = await client.post("/api/stock/report", json=bad_med_payload, headers=staff_headers)
    assert resp2.status_code == 404
    assert resp2.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_get_stock_availability_single_and_multiple(client: AsyncClient, seed_data: dict):
    """Verify GET /api/stock/availability supports medicine_id and comma-separated facility_ids."""
    fac_1 = seed_data["facilities"][0]
    fac_2 = seed_data["facilities"][1]
    med_1 = seed_data["medicines"][0]
    staff_headers = seed_data["headers"]["staff"]

    # Submit staff report for fac_1
    await client.post(
        "/api/stock/report",
        json={"facility_id": str(fac_1.id), "medicine_id": str(med_1.id), "availability_status": "IN_STOCK"},
        headers=staff_headers,
    )

    # Single facility query
    resp_single = await client.get(f"/api/stock/availability?medicine_id={med_1.id}&facility_ids={fac_1.id}")
    assert resp_single.status_code == 200
    data_single = resp_single.json()
    assert data_single["medicine_id"] == str(med_1.id)
    assert len(data_single["items"]) == 1
    item = data_single["items"][0]
    assert item["facility_id"] == str(fac_1.id)
    assert item["label"] == "LIKELY"
    assert item["p_available"] >= 0.65
    assert item["evidence_count"] >= 1
    assert item["last_report_at"] is not None

    # Multiple facility query
    fac_ids = f"{fac_1.id},{fac_2.id}"
    resp_multi = await client.get(f"/api/stock/availability?medicine_id={med_1.id}&facility_ids={fac_ids}")
    assert resp_multi.status_code == 200
    data_multi = resp_multi.json()
    assert len(data_multi["items"]) == 2
    f_ids_ret = [it["facility_id"] for it in data_multi["items"]]
    assert str(fac_1.id) in f_ids_ret
    assert str(fac_2.id) in f_ids_ret


@pytest.mark.asyncio
async def test_get_stock_availability_missing_medicine_404(client: AsyncClient, seed_data: dict):
    """Verify 404 when querying availability for non-existent medicine."""
    random_id = uuid.uuid4()
    resp = await client.get(f"/api/stock/availability?medicine_id={random_id}")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"
