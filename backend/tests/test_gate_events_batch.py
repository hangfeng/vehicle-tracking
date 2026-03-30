import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.gate_event import GateEvent, Direction, ReviewStatus
from app.services.auth import create_access_token

async def get_token(user: User) -> str:
    return create_access_token(str(user.id), user.role.value)

@pytest.mark.asyncio
async def test_batch_review_confirm(client: AsyncClient, operator_user: User, db_session: AsyncSession):
    token = await get_token(operator_user)
    e1 = GateEvent(id=uuid.uuid4(), factory_id=operator_user.factory_id, plate_number="粤A11111", direction=Direction.entry, review_status=ReviewStatus.pending_review)
    e2 = GateEvent(id=uuid.uuid4(), factory_id=operator_user.factory_id, plate_number="粤A22222", direction=Direction.entry, review_status=ReviewStatus.pending_review)
    db_session.add_all([e1, e2])
    await db_session.commit()

    resp = await client.post("/gate-events/batch-review", headers={"Authorization": f"Bearer {token}"}, json={
        "ids": [str(e1.id), str(e2.id)],
        "action": "confirm",
    })
    assert resp.status_code == 200
    assert resp.json()["updated"] == 2

@pytest.mark.asyncio
async def test_batch_review_only_pending(client: AsyncClient, operator_user: User, db_session: AsyncSession):
    """Already-confirmed events should not be updated."""
    token = await get_token(operator_user)
    e_confirmed = GateEvent(id=uuid.uuid4(), factory_id=operator_user.factory_id, plate_number="粤A33333", direction=Direction.entry, review_status=ReviewStatus.auto_confirmed)
    e_pending = GateEvent(id=uuid.uuid4(), factory_id=operator_user.factory_id, plate_number="粤A44444", direction=Direction.entry, review_status=ReviewStatus.pending_review)
    db_session.add_all([e_confirmed, e_pending])
    await db_session.commit()

    resp = await client.post("/gate-events/batch-review", headers={"Authorization": f"Bearer {token}"}, json={
        "ids": [str(e_confirmed.id), str(e_pending.id)],
        "action": "confirm",
    })
    assert resp.status_code == 200
    assert resp.json()["updated"] == 1  # Only pending one updated
