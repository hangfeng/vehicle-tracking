import pytest

@pytest.mark.asyncio
async def test_login_success(client, operator_user):
    resp = await client.post("/auth/login", json={"phone": "13800000001", "password": "password123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()

@pytest.mark.asyncio
async def test_login_wrong_password(client, operator_user):
    resp = await client.post("/auth/login", json={"phone": "13800000001", "password": "wrong"})
    assert resp.status_code == 401

@pytest.mark.asyncio
async def test_me_requires_auth(client):
    resp = await client.get("/auth/me")
    assert resp.status_code in (401, 403)  # 401 with starlette>=1.0, 403 with older versions

@pytest.mark.asyncio
async def test_me_returns_user(client, operator_user):
    login = await client.post("/auth/login", json={"phone": "13800000001", "password": "password123"})
    token = login.json()["access_token"]
    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["phone"] == "13800000001"
