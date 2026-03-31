import pytest
from httpx import AsyncClient
from app.models.user import User
from app.services.auth import create_access_token


async def get_token(user: User) -> str:
    return create_access_token(str(user.id), user.role.value)


@pytest.mark.asyncio
async def test_group_admin_can_list_inferred_factories_when_factory_table_is_empty(
    client: AsyncClient,
    admin_user: User,
    operator_user: User,
):
    token = await get_token(admin_user)
    resp = await client.get("/factories", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    ids = {item["id"] for item in resp.json()}
    assert str(operator_user.factory_id) in ids
