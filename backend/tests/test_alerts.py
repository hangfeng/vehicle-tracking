import pytest

@pytest.mark.asyncio
async def test_low_confidence_creates_alert(client, operator_user):
    await client.post("/gate-events", json={
        "factory_id": str(operator_user.factory_id),
        "plate_number": "粤B99999",
        "direction": "entry",
        "confidence_score": 0.50,
    })
    login = await client.post("/auth/login", json={"phone": "13800000001", "password": "password123"})
    token = login.json()["access_token"]
    resp = await client.get("/alerts?status=active", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    alerts = resp.json()
    assert len(alerts) == 1
    assert alerts[0]["type"] == "pending_review"

@pytest.mark.asyncio
async def test_resolve_alert(client, operator_user):
    await client.post("/gate-events", json={
        "factory_id": str(operator_user.factory_id),
        "plate_number": "苏C55555",
        "direction": "entry",
        "confidence_score": 0.40,
    })
    login = await client.post("/auth/login", json={"phone": "13800000001", "password": "password123"})
    token = login.json()["access_token"]
    alerts_resp = await client.get("/alerts?status=active", headers={"Authorization": f"Bearer {token}"})
    alert_id = alerts_resp.json()[0]["id"]
    resp = await client.patch(
        f"/alerts/{alert_id}/resolve",
        json={"note": "已人工确认"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"
