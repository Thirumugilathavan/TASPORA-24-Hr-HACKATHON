import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_notifications_crud_and_read_status(client: AsyncClient, seed_data: dict):
    headers = seed_data["headers"]["patient"]

    # 1. Fetch notifications for user (should auto-seed 4 notices)
    res = await client.get("/api/notifications", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 4
    assert data["unread_count"] >= 4
    assert len(data["items"]) >= 4

    # Check notification fields
    first_notif = data["items"][0]
    assert "id" in first_notif
    assert "title" in first_notif
    assert "message" in first_notif
    assert "type" in first_notif
    assert first_notif["is_read"] is False

    # 2. Mark single notification as read
    notif_id = first_notif["id"]
    patch_res = await client.patch(f"/api/notifications/{notif_id}/read", headers=headers)
    assert patch_res.status_code == 200
    assert patch_res.json()["is_read"] is True

    # Check that unread count decreased
    res2 = await client.get("/api/notifications", headers=headers)
    assert res2.json()["unread_count"] == data["unread_count"] - 1

    # 3. Mark all as read
    read_all_res = await client.post("/api/notifications/read-all", headers=headers)
    assert read_all_res.status_code == 200
    assert read_all_res.json()["status"] == "success"

    # Verify 0 unread remaining
    res3 = await client.get("/api/notifications", headers=headers)
    assert res3.json()["unread_count"] == 0

    # 4. Create new notification
    create_res = await client.post(
        "/api/notifications",
        headers=headers,
        json={
            "title": "Lab Results Ready",
            "message": "Your routine blood glucose test results are available.",
            "type": "info",
            "link": "/appointments",
        },
    )
    assert create_res.status_code == 201
    created_item = create_res.json()
    assert created_item["title"] == "Lab Results Ready"
    assert created_item["is_read"] is False

    # Verify unread is now 1
    res4 = await client.get("/api/notifications", headers=headers)
    assert res4.json()["unread_count"] == 1
