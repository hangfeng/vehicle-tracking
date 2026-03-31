import pytest
import uuid
from sqlalchemy import select
from app.models.gate_event import GateEvent, Direction, ReviewStatus
from app.models.vehicle import Vehicle, VehicleStatus
from app.services.vehicle_backfill import backfill_vehicles_from_gate_events

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
    assert resp.json()["serial_no"].startswith("VEH")

@pytest.mark.asyncio
async def test_list_vehicles_empty(client, operator_user):
    login = await client.post("/auth/login", json={"phone": "13800000001", "password": "password123"})
    token = login.json()["access_token"]
    resp = await client.get("/vehicles", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_in_factory_candidates(client, manager_user, db_session):
    db_session.add_all([
        Vehicle(
            id=uuid.uuid4(),
            factory_id=manager_user.factory_id,
            plate_number="沪A12345",
            status=VehicleStatus.in_factory,
        ),
        Vehicle(
            id=uuid.uuid4(),
            factory_id=manager_user.factory_id,
            plate_number="沪A54321",
            status=VehicleStatus.out,
        ),
    ])
    await db_session.commit()

    login = await client.post("/auth/login", json={"phone": "13800000002", "password": "password123"})
    token = login.json()["access_token"]
    resp = await client.get("/vehicles/in-factory-candidates", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert [item["plate_number"] for item in resp.json()] == ["沪A12345"]


@pytest.mark.asyncio
async def test_backfill_vehicles_from_gate_events_creates_missing_vehicle(db_session, operator_user):
    db_session.add(GateEvent(
        id=uuid.uuid4(),
        factory_id=operator_user.factory_id,
        plate_number="沪A88888",
        direction=Direction.entry,
        review_status=ReviewStatus.auto_confirmed,
    ))
    await db_session.commit()

    created = await backfill_vehicles_from_gate_events(db_session)

    assert created == 1

    result = await db_session.execute(
        select(Vehicle).where(
            Vehicle.factory_id == operator_user.factory_id,
            Vehicle.plate_number == "沪A88888",
        )
    )
    vehicle = result.scalar_one_or_none()
    assert vehicle is not None
    assert vehicle.status == VehicleStatus.in_factory
