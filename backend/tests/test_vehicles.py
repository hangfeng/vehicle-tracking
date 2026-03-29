import pytest

@pytest.mark.asyncio
async def test_list_vehicles_requires_auth(client):
    resp = await client.get("/vehicles")
    assert resp.status_code in (401, 403)

@pytest.mark.asyncio
async def test_create_vehicle_requires_manager(client, operator_user):
    login = await client.post("/auth/login", json={"phone": "13800000001", "password": "password123"})
    token = login.json()["access_token"]
    resp = await client.post(
        "/vehicles",
        json={"plate_number": "沪A12345"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403

@pytest.mark.asyncio
async def test_create_vehicle_as_manager(client, manager_user):
    login = await client.post("/auth/login", json={"phone": "13800000002", "password": "password123"})
    token = login.json()["access_token"]
    resp = await client.post(
        "/vehicles",
        json={"plate_number": "沪A12345", "company": "顺丰物流"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["plate_number"] == "沪A12345"

@pytest.mark.asyncio
async def test_list_vehicles_empty(client, operator_user):
    login = await client.post("/auth/login", json={"phone": "13800000001", "password": "password123"})
    token = login.json()["access_token"]
    resp = await client.get("/vehicles", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == []
