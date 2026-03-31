import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.checkpoint import CheckPoint, IdentificationMethod
from app.models.department import Department
from app.models.user import User, UserRole
from app.services.auth import create_access_token, hash_password


async def get_token(user: User) -> str:
    return create_access_token(str(user.id), user.role.value)


@pytest.mark.asyncio
async def test_create_checkpoint_event_as_manager(
    client: AsyncClient,
    manager_user: User,
    db_session: AsyncSession,
):
    department = Department(id=uuid.uuid4(), factory_id=manager_user.factory_id, name="安保部")
    checkpoint = CheckPoint(
        id=uuid.uuid4(),
        factory_id=manager_user.factory_id,
        department_id=department.id,
        name="北门",
        identification_method=IdentificationMethod.manual,
        is_gate=True,
    )
    db_session.add_all([department, checkpoint])
    await db_session.commit()

    token = await get_token(manager_user)
    resp = await client.post(
        "/checkpoint-events",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "checkpoint_id": str(checkpoint.id),
            "plate_number": "沪A66666",
            "direction": "entry",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["checkpoint_id"] == str(checkpoint.id)
    assert resp.json()["plate_number"] == "沪A66666"
    assert resp.json()["entered_by_user_name"] == manager_user.name


@pytest.mark.asyncio
async def test_create_checkpoint_event_requires_document_number_for_delivery(
    client: AsyncClient,
    manager_user: User,
    db_session: AsyncSession,
):
    department = Department(id=uuid.uuid4(), factory_id=manager_user.factory_id, name="安保部")
    checkpoint = CheckPoint(
        id=uuid.uuid4(),
        factory_id=manager_user.factory_id,
        department_id=department.id,
        name="北门",
        identification_method=IdentificationMethod.manual,
        is_gate=True,
    )
    db_session.add_all([department, checkpoint])
    await db_session.commit()

    token = await get_token(manager_user)
    resp = await client.post(
        "/checkpoint-events",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "checkpoint_id": str(checkpoint.id),
            "plate_number": "沪A77777",
            "direction": "entry",
            "business_type": "delivery",
        },
    )
    assert resp.status_code == 400
    assert "单号" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_list_checkpoint_events_filters_operator_by_department(
    client: AsyncClient,
    operator_user: User,
    db_session: AsyncSession,
):
    own_department = Department(id=uuid.uuid4(), factory_id=operator_user.factory_id, name="收货部")
    other_department = Department(id=uuid.uuid4(), factory_id=operator_user.factory_id, name="仓储部")
    operator_user.department_id = own_department.id

    own_checkpoint = CheckPoint(
        id=uuid.uuid4(),
        factory_id=operator_user.factory_id,
        department_id=own_department.id,
        name="收货口",
        identification_method=IdentificationMethod.manual,
        is_gate=False,
    )
    other_checkpoint = CheckPoint(
        id=uuid.uuid4(),
        factory_id=operator_user.factory_id,
        department_id=other_department.id,
        name="仓储口",
        identification_method=IdentificationMethod.manual,
        is_gate=False,
    )
    db_session.add_all([own_department, other_department, own_checkpoint, other_checkpoint])
    manager_user = User(
        id=uuid.uuid4(),
        factory_id=operator_user.factory_id,
        department_id=other_department.id,
        name="厂区管理员",
        phone="13800009999",
        password_hash=hash_password("password123"),
        role=UserRole.factory_manager,
    )
    db_session.add(manager_user)
    await db_session.commit()

    operator_token = await get_token(operator_user)
    await client.post(
        "/checkpoint-events",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={
            "checkpoint_id": str(own_checkpoint.id),
            "plate_number": "沪A11111",
            "direction": "entry",
        },
    )

    manager_token = await get_token(manager_user)
    await client.post(
        "/checkpoint-events",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={
            "checkpoint_id": str(other_checkpoint.id),
            "plate_number": "沪A22222",
            "direction": "entry",
        },
    )

    resp = await client.get(
        "/checkpoint-events",
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert resp.status_code == 200
    assert [item["plate_number"] for item in resp.json()] == ["沪A11111"]
    assert resp.json()[0]["entered_by_user_name"] == operator_user.name


@pytest.mark.asyncio
async def test_create_checkpoint_event_rejects_duplicate_entry_on_same_checkpoint(
    client: AsyncClient,
    manager_user: User,
    db_session: AsyncSession,
):
    department = Department(id=uuid.uuid4(), factory_id=manager_user.factory_id, name="安保部")
    checkpoint = CheckPoint(
        id=uuid.uuid4(),
        factory_id=manager_user.factory_id,
        department_id=department.id,
        name="北门",
        identification_method=IdentificationMethod.manual,
        is_gate=True,
    )
    db_session.add_all([department, checkpoint])
    await db_session.commit()

    token = await get_token(manager_user)
    first_resp = await client.post(
        "/checkpoint-events",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "checkpoint_id": str(checkpoint.id),
            "plate_number": "沪A33333",
            "direction": "entry",
        },
    )
    assert first_resp.status_code == 201

    second_resp = await client.post(
        "/checkpoint-events",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "checkpoint_id": str(checkpoint.id),
            "plate_number": "沪A33333",
            "direction": "entry",
        },
    )
    assert second_resp.status_code == 400
    assert "不能连续入场" in second_resp.json()["detail"]
