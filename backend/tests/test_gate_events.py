import pytest
import uuid
from sqlalchemy import select
from app.models.factory import Factory
from app.models.location import Location, LocationType
from app.models.checkpoint import CheckPoint, IdentificationMethod
from app.models.checkpoint_event import CheckpointEvent
from app.models.vehicle import Vehicle, VehicleStatus
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


@pytest.mark.asyncio
async def test_create_gate_event_creates_vehicle_when_missing(client, operator_user, db_session):
    resp = await client.post("/gate-events", json={
        "factory_id": str(operator_user.factory_id),
        "plate_number": "沪A88888",
        "direction": "entry",
        "confidence_score": 0.90,
    })

    assert resp.status_code == 200

    result = await db_session.execute(
        select(Vehicle).where(
            Vehicle.factory_id == operator_user.factory_id,
            Vehicle.plate_number == "沪A88888",
        )
    )
    vehicle = result.scalar_one_or_none()
    assert vehicle is not None
    assert vehicle.status == VehicleStatus.in_factory
    assert vehicle.last_seen_at is not None


@pytest.mark.asyncio
async def test_create_gate_event_syncs_checkpoint_event_for_matching_gate_checkpoint(client, operator_user, db_session):
    gate = Location(
        id=uuid.uuid4(),
        factory_id=operator_user.factory_id,
        name="厂区北门",
        type=LocationType.gate,
        is_active=True,
    )
    checkpoint = CheckPoint(
        id=uuid.uuid4(),
        factory_id=operator_user.factory_id,
        name="厂区北门",
        identification_method=IdentificationMethod.camera,
        is_gate=True,
    )
    db_session.add_all([gate, checkpoint])
    await db_session.commit()

    resp = await client.post("/gate-events", json={
        "factory_id": str(operator_user.factory_id),
        "gate_id": str(gate.id),
        "plate_number": "沪A55555",
        "direction": "entry",
        "confidence_score": 0.90,
    })

    assert resp.status_code == 200

    event_result = await db_session.execute(
        select(CheckpointEvent).where(
            CheckpointEvent.factory_id == operator_user.factory_id,
            CheckpointEvent.plate_number == "沪A55555",
        )
    )
    checkpoint_event = event_result.scalar_one_or_none()
    assert checkpoint_event is not None
    assert checkpoint_event.checkpoint_id == checkpoint.id
    assert checkpoint_event.source.value == "ai"
