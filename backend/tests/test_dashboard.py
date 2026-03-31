import pytest
import uuid
from datetime import datetime, timedelta

from app.models.checkpoint import CheckPoint, IdentificationMethod
from app.models.checkpoint_event import CheckpointEvent, CheckpointEventBusinessType, CheckpointEventSource
from app.models.gate_event import Direction
from app.models.factory import Factory
from app.models.user import User
from app.services.auth import create_access_token


async def get_token(user: User) -> str:
    return create_access_token(str(user.id), user.role.value)


@pytest.mark.asyncio
async def test_group_admin_dashboard_stats_without_factory_filter(client, admin_user, db_session):
    factory_id = uuid.uuid4()
    db_session.add(Factory(id=factory_id, name="测试厂区", timezone="Asia/Shanghai"))
    await db_session.commit()

    await client.post("/gate-events", json={
        "factory_id": str(factory_id),
        "plate_number": "沪A30003",
        "direction": "entry",
        "confidence_score": 0.40,
    })

    token = await get_token(admin_user)
    resp = await client.get("/dashboard/stats", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["entries_today"] >= 1
    assert data["active_alerts_count"] >= 1


@pytest.mark.asyncio
async def test_dashboard_recent_access_records_group_single_visit(client, manager_user, db_session):
    factory = Factory(id=manager_user.factory_id, name="测试厂区", timezone="Asia/Shanghai")
    gate_checkpoint = CheckPoint(
        id=uuid.uuid4(),
        factory_id=manager_user.factory_id,
        name="厂区大门",
        identification_method=IdentificationMethod.manual,
        is_gate=True,
    )
    warehouse_checkpoint = CheckPoint(
        id=uuid.uuid4(),
        factory_id=manager_user.factory_id,
        name="1号仓库",
        identification_method=IdentificationMethod.manual,
        is_gate=False,
    )
    entry_time = datetime(2026, 3, 31, 8, 0, 0)
    warehouse_time = entry_time + timedelta(minutes=40)
    exit_time = entry_time + timedelta(hours=2, minutes=30)
    db_session.add_all([
        factory,
        gate_checkpoint,
        warehouse_checkpoint,
        CheckpointEvent(
            id=uuid.uuid4(),
            factory_id=manager_user.factory_id,
            checkpoint_id=gate_checkpoint.id,
            department_id=None,
            vehicle_id=None,
            plate_number="沪A88888",
            direction=Direction.entry,
            event_time=entry_time,
            serial_no="IO20260331080000001",
            source=CheckpointEventSource.manual,
            business_type=CheckpointEventBusinessType.other,
            document_no=None,
            entered_by_user_id=manager_user.id,
            note=None,
            gate_event_id=None,
        ),
        CheckpointEvent(
            id=uuid.uuid4(),
            factory_id=manager_user.factory_id,
            checkpoint_id=warehouse_checkpoint.id,
            department_id=None,
            vehicle_id=None,
            plate_number="沪A88888",
            direction=Direction.entry,
            event_time=warehouse_time,
            serial_no="IO20260331084000001",
            source=CheckpointEventSource.manual,
            business_type=CheckpointEventBusinessType.other,
            document_no=None,
            entered_by_user_id=manager_user.id,
            note=None,
            gate_event_id=None,
        ),
        CheckpointEvent(
            id=uuid.uuid4(),
            factory_id=manager_user.factory_id,
            checkpoint_id=gate_checkpoint.id,
            department_id=None,
            vehicle_id=None,
            plate_number="沪A88888",
            direction=Direction.exit,
            event_time=exit_time,
            serial_no="IO20260331103000001",
            source=CheckpointEventSource.manual,
            business_type=CheckpointEventBusinessType.other,
            document_no=None,
            entered_by_user_id=manager_user.id,
            note=None,
            gate_event_id=None,
        ),
    ])
    await db_session.commit()

    token = await get_token(manager_user)
    resp = await client.get("/dashboard/recent-access-records", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["plate_number"] == "沪A88888"
    assert data[0]["entry_time"] == "2026-03-31T08:00:00"
    assert data[0]["exit_time"] == "2026-03-31T10:30:00"
    assert data[0]["stay_duration_minutes"] == 150
    assert data[0]["status"] == "completed"
    assert data[0]["record_no"] == "IO20260331080000001"
    assert data[0]["path_nodes"] == [
        {"checkpoint_id": str(gate_checkpoint.id), "checkpoint_name": "厂区大门", "event_time": "2026-03-31T08:00:00"},
        {"checkpoint_id": str(warehouse_checkpoint.id), "checkpoint_name": "1号仓库", "event_time": "2026-03-31T08:40:00"},
        {"checkpoint_id": str(gate_checkpoint.id), "checkpoint_name": "厂区大门", "event_time": "2026-03-31T10:30:00"},
    ]
