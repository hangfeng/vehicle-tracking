import pytest
import uuid
from datetime import datetime
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.gate_event import GateEvent, Direction, ReviewStatus
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
