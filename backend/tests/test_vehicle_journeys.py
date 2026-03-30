import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.vehicle import Vehicle, VehicleStatus
from app.models.checkpoint import CheckPoint, IdentificationMethod
from app.models.vehicle_journey import VehicleJourney, JourneyStatus
from app.services.auth import create_access_token

async def get_token(user: User) -> str:
    return create_access_token(str(user.id), user.role.value)

@pytest.mark.asyncio
async def test_start_journey(client: AsyncClient, operator_user: User, db_session: AsyncSession):
    token = await get_token(operator_user)
    vehicle = Vehicle(
        id=uuid.uuid4(),
        factory_id=operator_user.factory_id,
        plate_number="粤B00001",
        status=VehicleStatus.in_factory,
    )
    db_session.add(vehicle)
    await db_session.commit()

    resp = await client.post("/vehicle-journeys", headers={"Authorization": f"Bearer {token}"}, json={
        "vehicle_id": str(vehicle.id),
        "factory_id": str(operator_user.factory_id),
        "template_id": None,
    })
    assert resp.status_code == 201
    assert resp.json()["status"] == "active"

@pytest.mark.asyncio
async def test_record_journey_event_no_deviation(client: AsyncClient, operator_user: User, db_session: AsyncSession):
    token = await get_token(operator_user)
    vehicle = Vehicle(
        id=uuid.uuid4(),
        factory_id=operator_user.factory_id,
        plate_number="粤B00002",
        status=VehicleStatus.in_factory,
    )
    checkpoint = CheckPoint(
        id=uuid.uuid4(),
        factory_id=operator_user.factory_id,
        name="仓库A",
        identification_method=IdentificationMethod.manual,
        is_gate=False,
    )
    db_session.add(vehicle)
    db_session.add(checkpoint)
    await db_session.commit()

    journey_resp = await client.post("/vehicle-journeys", headers={"Authorization": f"Bearer {token}"}, json={
        "vehicle_id": str(vehicle.id),
        "factory_id": str(operator_user.factory_id),
        "template_id": None,
    })
    journey_id = journey_resp.json()["id"]

    event_resp = await client.post("/journey-events", headers={"Authorization": f"Bearer {token}"}, json={
        "journey_id": journey_id,
        "checkpoint_id": str(checkpoint.id),
        "direction": "entry",
        "license_plate": "粤B00002",
        "confidence": None,
        "image_url": None,
        "notes": None,
    })
    assert event_resp.status_code == 201
    assert event_resp.json()["is_deviation"] is False

@pytest.mark.asyncio
async def test_deviation_detected(client: AsyncClient, operator_user: User, db_session: AsyncSession):
    """Template expects checkpoint A first, but event at checkpoint B → deviation."""
    token = await get_token(operator_user)
    from app.models.path_template import PathTemplate, PathTemplateStep, StepDirection
    cpA = CheckPoint(id=uuid.uuid4(), factory_id=operator_user.factory_id, name="A", identification_method=IdentificationMethod.manual, is_gate=False)
    cpB = CheckPoint(id=uuid.uuid4(), factory_id=operator_user.factory_id, name="B", identification_method=IdentificationMethod.manual, is_gate=False)
    vehicle = Vehicle(id=uuid.uuid4(), factory_id=operator_user.factory_id, plate_number="粤B00003", status=VehicleStatus.in_factory)
    tmpl = PathTemplate(id=uuid.uuid4(), factory_id=operator_user.factory_id, name="Test Template")
    db_session.add_all([cpA, cpB, vehicle, tmpl])
    await db_session.flush()
    step = PathTemplateStep(template_id=tmpl.id, checkpoint_id=cpA.id, step_order=1, direction=StepDirection.entry)
    db_session.add(step)
    await db_session.commit()

    journey_resp = await client.post("/vehicle-journeys", headers={"Authorization": f"Bearer {token}"}, json={
        "vehicle_id": str(vehicle.id),
        "factory_id": str(operator_user.factory_id),
        "template_id": str(tmpl.id),
    })
    journey_id = journey_resp.json()["id"]

    # Record event at cpB (wrong — template expects cpA)
    event_resp = await client.post("/journey-events", headers={"Authorization": f"Bearer {token}"}, json={
        "journey_id": journey_id,
        "checkpoint_id": str(cpB.id),
        "direction": "entry",
        "license_plate": "粤B00003",
        "confidence": None,
        "image_url": None,
        "notes": None,
    })
    assert event_resp.status_code == 201
    assert event_resp.json()["is_deviation"] is True

@pytest.mark.asyncio
async def test_get_active_journey(client: AsyncClient, operator_user: User, db_session: AsyncSession):
    token = await get_token(operator_user)
    vehicle = Vehicle(id=uuid.uuid4(), factory_id=operator_user.factory_id, plate_number="粤B00004", status=VehicleStatus.in_factory)
    db_session.add(vehicle)
    await db_session.commit()

    await client.post("/vehicle-journeys", headers={"Authorization": f"Bearer {token}"}, json={
        "vehicle_id": str(vehicle.id),
        "factory_id": str(operator_user.factory_id),
        "template_id": None,
    })

    resp = await client.get(f"/vehicles/{vehicle.id}/journey", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"
