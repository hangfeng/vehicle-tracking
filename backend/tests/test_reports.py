import pytest
import uuid
from datetime import datetime
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.checkpoint import CheckPoint, IdentificationMethod
from app.models.checkpoint_event import CheckpointEvent, CheckpointEventBusinessType, CheckpointEventSource
from app.models.department import Department
from app.models.user import User
from app.models.factory import Factory
from app.models.gate_event import GateEvent, Direction, ReviewStatus
from app.models.vehicle import Vehicle, VehicleStatus
from app.services.auth import create_access_token

async def get_token(user: User) -> str:
    return create_access_token(str(user.id), user.role.value)

@pytest.mark.asyncio
async def test_traffic_report(client: AsyncClient, operator_user: User, db_session: AsyncSession):
    token = await get_token(operator_user)
    e = GateEvent(
        id=uuid.uuid4(),
        factory_id=operator_user.factory_id,
        plate_number="粤B99999",
        direction=Direction.entry,
        review_status=ReviewStatus.auto_confirmed,
    )
    db_session.add(e)
    await db_session.commit()

    resp = await client.get(
        "/reports/traffic",
        headers={"Authorization": f"Bearer {token}"},
        params={"start_date": "2020-01-01", "end_date": "2099-12-31", "granularity": "day"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_entries" in data
    assert data["total_entries"] >= 1


@pytest.mark.asyncio
async def test_traffic_report_supports_week_granularity(client: AsyncClient, operator_user: User, db_session: AsyncSession):
    token = await get_token(operator_user)
    db_session.add_all([
        GateEvent(
            id=uuid.uuid4(),
            factory_id=operator_user.factory_id,
            plate_number="粤B10001",
            direction=Direction.entry,
            review_status=ReviewStatus.auto_confirmed,
            captured_at=datetime(2026, 3, 30, 9, 0, 0),
        ),
        GateEvent(
            id=uuid.uuid4(),
            factory_id=operator_user.factory_id,
            plate_number="粤B10002",
            direction=Direction.exit,
            review_status=ReviewStatus.auto_confirmed,
            captured_at=datetime(2026, 4, 1, 9, 0, 0),
        ),
    ])
    await db_session.commit()

    resp = await client.get(
        "/reports/traffic",
        headers={"Authorization": f"Bearer {token}"},
        params={"start_date": "2026-03-29", "end_date": "2026-04-05", "granularity": "week"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["by_day"]) == 1
    assert data["by_day"][0]["entries"] == 1
    assert data["by_day"][0]["exits"] == 1

@pytest.mark.asyncio
async def test_alert_report(client: AsyncClient, operator_user: User, db_session: AsyncSession):
    token = await get_token(operator_user)
    resp = await client.get(
        "/reports/alerts",
        headers={"Authorization": f"Bearer {token}"},
        params={"start_date": "2020-01-01", "end_date": "2099-12-31"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_active" in data
    assert "total_resolved" in data

@pytest.mark.asyncio
async def test_report_export_excel(client: AsyncClient, operator_user: User):
    token = await get_token(operator_user)
    resp = await client.get(
        "/reports/export",
        headers={"Authorization": f"Bearer {token}"},
        params={"start_date": "2020-01-01", "end_date": "2099-12-31", "format": "excel"},
    )
    assert resp.status_code == 200
    assert "spreadsheet" in resp.headers["content-type"]


@pytest.mark.asyncio
async def test_group_admin_traffic_report_without_factory_filter(
    client: AsyncClient,
    admin_user: User,
    db_session: AsyncSession,
):
    token = await get_token(admin_user)
    factory_id = uuid.uuid4()
    db_session.add(Factory(id=factory_id, name="测试厂区", timezone="Asia/Shanghai"))
    db_session.add(GateEvent(
        id=uuid.uuid4(),
        factory_id=factory_id,
        plate_number="粤B88888",
        direction=Direction.entry,
        review_status=ReviewStatus.auto_confirmed,
        captured_at=datetime.utcnow(),
    ))
    await db_session.commit()

    resp = await client.get(
        "/reports/traffic",
        headers={"Authorization": f"Bearer {token}"},
        params={"start_date": "2020-01-01", "end_date": "2099-12-31", "granularity": "day"},
    )
    assert resp.status_code == 200
    assert resp.json()["total_entries"] >= 1


@pytest.mark.asyncio
async def test_access_detail_report(client: AsyncClient, manager_user: User, db_session: AsyncSession):
    department = Department(id=uuid.uuid4(), factory_id=manager_user.factory_id, name="收货部")
    checkpoint = CheckPoint(
        id=uuid.uuid4(),
        factory_id=manager_user.factory_id,
        department_id=department.id,
        name="北门",
        identification_method=IdentificationMethod.manual,
        is_gate=True,
    )
    event = CheckpointEvent(
        id=uuid.uuid4(),
        serial_no="IO20260331100000001",
        factory_id=manager_user.factory_id,
        checkpoint_id=checkpoint.id,
        department_id=department.id,
        vehicle_id=None,
        plate_number="沪A12345",
        direction=Direction.entry,
        event_time=datetime(2026, 3, 31, 10, 0, 0),
        source=CheckpointEventSource.manual,
        business_type=CheckpointEventBusinessType.delivery,
        document_no="DH-001",
        entered_by_user_id=manager_user.id,
        note="测试明细",
        gate_event_id=None,
    )
    db_session.add_all([department, checkpoint, event])
    await db_session.commit()

    token = await get_token(manager_user)
    resp = await client.get(
        "/reports/access-details",
        headers={"Authorization": f"Bearer {token}"},
        params={"start_date": "2026-03-01", "end_date": "2026-03-31"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["serial_no"] == "IO20260331100000001"
    assert data[0]["checkpoint_name"] == "北门"
    assert data[0]["department_name"] == "收货部"
    assert data[0]["entered_by_user_name"] == manager_user.name

    serial_resp = await client.get(
        "/reports/access-details",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "start_date": "2026-03-01",
            "end_date": "2026-03-31",
            "serial_no": "IO20260331100000001",
        },
    )
    assert serial_resp.status_code == 200
    assert len(serial_resp.json()) == 1


@pytest.mark.asyncio
async def test_access_detail_report_export_excel(client: AsyncClient, manager_user: User):
    token = await get_token(manager_user)
    resp = await client.get(
        "/reports/access-details/export",
        headers={"Authorization": f"Bearer {token}"},
        params={"start_date": "2020-01-01", "end_date": "2099-12-31"},
    )
    assert resp.status_code == 200
    assert "spreadsheet" in resp.headers["content-type"]


@pytest.mark.asyncio
async def test_vehicle_detail_report(client: AsyncClient, manager_user: User, db_session: AsyncSession):
    vehicle = Vehicle(
        id=uuid.uuid4(),
        serial_no="VEH20260402120000001",
        factory_id=manager_user.factory_id,
        plate_number="沪A54321",
        vehicle_type="truck",
        company="测试物流",
        contact_name="张三",
        contact_phone="13800001111",
        status=VehicleStatus.in_factory,
    )
    db_session.add(vehicle)
    await db_session.commit()

    token = await get_token(manager_user)
    resp = await client.get(
        "/reports/vehicle-details",
        headers={"Authorization": f"Bearer {token}"},
        params={"serial_no": "VEH20260402120000001"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["plate_number"] == "沪A54321"


@pytest.mark.asyncio
async def test_user_detail_report(client: AsyncClient, manager_user: User, db_session: AsyncSession):
    factory = Factory(id=manager_user.factory_id, name="测试厂区", timezone="Asia/Shanghai")
    department = Department(id=uuid.uuid4(), factory_id=manager_user.factory_id, name="调度部")
    manager_user.serial_no = "USR20260402121000001"
    manager_user.department_id = department.id
    db_session.add_all([factory, department])
    await db_session.commit()

    token = await get_token(manager_user)
    resp = await client.get(
        "/reports/user-details",
        headers={"Authorization": f"Bearer {token}"},
        params={"serial_no": "USR20260402121000001"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["name"] == manager_user.name
    assert resp.json()[0]["department_name"] == "调度部"
