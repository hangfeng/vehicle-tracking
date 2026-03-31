import pytest
import uuid
from app.models.factory import Factory
from app.models.user import User
from app.services.auth import create_access_token


async def get_token(user: User) -> str:
    return create_access_token(str(user.id), user.role.value)

@pytest.mark.asyncio
async def test_create_gate_event_high_confidence(client, operator_user):
    resp = await client.post("/gate-events", json={
        "factory_id": str(operator_user.factory_id),
        "plate_number": "沪A12345",
        "direction": "entry",
        "confidence_score": 0.95,
    })
    assert resp.status_code == 200
    assert resp.json()["review_status"] == "auto_confirmed"

@pytest.mark.asyncio
async def test_create_gate_event_low_confidence(client, operator_user):
    resp = await client.post("/gate-events", json={
        "factory_id": str(operator_user.factory_id),
        "plate_number": "粤B00000",
        "direction": "entry",
        "confidence_score": 0.60,
    })
    assert resp.status_code == 200
    assert resp.json()["review_status"] == "pending_review"

@pytest.mark.asyncio
async def test_review_event_confirm(client, operator_user):
    create = await client.post("/gate-events", json={
        "factory_id": str(operator_user.factory_id),
        "plate_number": "京C11111",
        "direction": "exit",
        "confidence_score": 0.50,
    })
    event_id = create.json()["id"]
    login = await client.post("/auth/login", json={"phone": "13800000001", "password": "password123"})
    token = login.json()["access_token"]
    resp = await client.patch(
        f"/gate-events/{event_id}/review",
        json={"plate_number": "京C11111", "action": "confirm"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["review_status"] == "manually_confirmed"

@pytest.mark.asyncio
async def test_list_gate_events(client, operator_user):
    await client.post("/gate-events", json={
        "factory_id": str(operator_user.factory_id),
        "plate_number": "沪A99999",
        "direction": "entry",
        "confidence_score": 0.90,
    })
    login = await client.post("/auth/login", json={"phone": "13800000001", "password": "password123"})
    token = login.json()["access_token"]
    resp = await client.get("/gate-events", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1

@pytest.mark.asyncio
async def test_export_gate_events_returns_xlsx(client, operator_user):
    # Create an event first
    await client.post("/gate-events", json={
        "factory_id": str(operator_user.factory_id),
        "plate_number": "浙D12345",
        "direction": "entry",
        "confidence_score": 0.90,
    })
    login = await client.post("/auth/login", json={"phone": "13800000001", "password": "password123"})
    token = login.json()["access_token"]
    resp = await client.get("/gate-events/export", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@pytest.mark.asyncio
async def test_group_admin_can_list_gate_events_without_factory_filter(client, admin_user, db_session):
    factory_id = uuid.uuid4()
    db_session.add(Factory(id=factory_id, name="测试厂区", timezone="Asia/Shanghai"))
    await db_session.commit()

    await client.post("/gate-events", json={
        "factory_id": str(factory_id),
        "plate_number": "沪A10001",
        "direction": "entry",
        "confidence_score": 0.90,
    })

    token = await get_token(admin_user)
    resp = await client.get("/gate-events", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1
