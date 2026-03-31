import pytest
import uuid
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
