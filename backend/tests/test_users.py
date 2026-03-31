import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User, UserRole
from app.models.factory import Factory
from app.services.auth import create_access_token, hash_password
import uuid

async def get_token(user: User) -> str:
    return create_access_token(str(user.id), user.role.value)

@pytest.mark.asyncio
async def test_admin_can_list_all_users(client: AsyncClient, admin_user: User, manager_user: User):
    token = await get_token(admin_user)
    resp = await client.get("/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    ids = [u["id"] for u in resp.json()]
    assert str(admin_user.id) in ids
    assert str(manager_user.id) in ids

@pytest.mark.asyncio
async def test_manager_only_sees_own_factory(client: AsyncClient, manager_user: User, operator_user: User):
    token = await get_token(manager_user)
    resp = await client.get("/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    ids = [u["id"] for u in resp.json()]
    # manager and operator_user are in different factories, so operator_user should not appear
    assert str(operator_user.id) not in ids

@pytest.mark.asyncio
async def test_operator_cannot_list_users(client: AsyncClient, operator_user: User):
    token = await get_token(operator_user)
    resp = await client.get("/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403

@pytest.mark.asyncio
async def test_admin_can_create_manager(client: AsyncClient, admin_user: User, db_session: AsyncSession):
    token = await get_token(admin_user)
    factory_id = uuid.uuid4()
    fac = Factory(id=factory_id, name="测试厂", timezone="Asia/Shanghai")
    db_session.add(fac)
    await db_session.commit()

    resp = await client.post("/users", headers={"Authorization": f"Bearer {token}"}, json={
        "phone": "13900099001",
        "name": "新管理员",
        "password": "test123456",
        "role": "factory_manager",
        "factory_id": str(factory_id),
    })
    assert resp.status_code == 201
    assert resp.json()["role"] == "factory_manager"
    assert resp.json()["serial_no"].startswith("USR")

@pytest.mark.asyncio
async def test_manager_cannot_create_admin(client: AsyncClient, manager_user: User):
    token = await get_token(manager_user)
    resp = await client.post("/users", headers={"Authorization": f"Bearer {token}"}, json={
        "phone": "13900099002",
        "name": "越权",
        "password": "test123456",
        "role": "group_admin",
        "factory_id": None,
    })
    assert resp.status_code == 403

@pytest.mark.asyncio
async def test_batch_status_update(client: AsyncClient, admin_user: User, operator_user: User):
    token = await get_token(admin_user)
    resp = await client.post("/users/batch-status", headers={"Authorization": f"Bearer {token}"}, json={
        "ids": [str(operator_user.id)],
        "is_active": False,
    })
    assert resp.status_code == 200
    assert resp.json()["updated"] == 1
