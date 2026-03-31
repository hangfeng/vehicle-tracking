import pytest
import uuid
from httpx import AsyncClient
from app.models.checkpoint import CheckPoint, IdentificationMethod
from app.models.path_template import PathTemplate, PathTemplateStep, StepDirection
from app.models.user import User
from app.services.auth import create_access_token

async def get_token(user: User) -> str:
    return create_access_token(str(user.id), user.role.value)

@pytest.mark.asyncio
async def test_create_checkpoint(client: AsyncClient, manager_user: User):
    token = await get_token(manager_user)
    resp = await client.post("/checkpoints", headers={"Authorization": f"Bearer {token}"}, json={
        "name": "北门",
        "identification_method": "camera",
        "is_gate": True,
        "camera_config": {"rtsp_url": "rtsp://cam1", "confidence_threshold": 0.85},
    })
    assert resp.status_code == 201
    assert resp.json()["name"] == "北门"
    assert resp.json()["is_gate"] is True

@pytest.mark.asyncio
async def test_list_checkpoints(client: AsyncClient, manager_user: User):
    token = await get_token(manager_user)
    await client.post("/checkpoints", headers={"Authorization": f"Bearer {token}"}, json={
        "name": "仓库A", "identification_method": "manual", "is_gate": False,
    })
    resp = await client.get("/checkpoints", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

@pytest.mark.asyncio
async def test_update_checkpoint(client: AsyncClient, manager_user: User):
    token = await get_token(manager_user)
    create_resp = await client.post("/checkpoints", headers={"Authorization": f"Bearer {token}"}, json={
        "name": "旧名", "identification_method": "manual", "is_gate": False,
    })
    cp_id = create_resp.json()["id"]
    patch_resp = await client.patch(f"/checkpoints/{cp_id}", headers={"Authorization": f"Bearer {token}"}, json={"name": "新名"})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["name"] == "新名"

@pytest.mark.asyncio
async def test_delete_checkpoint(client: AsyncClient, manager_user: User):
    token = await get_token(manager_user)
    create_resp = await client.post("/checkpoints", headers={"Authorization": f"Bearer {token}"}, json={
        "name": "临时节点", "identification_method": "manual", "is_gate": False,
    })
    cp_id = create_resp.json()["id"]
    del_resp = await client.delete(f"/checkpoints/{cp_id}", headers={"Authorization": f"Bearer {token}"})
    assert del_resp.status_code == 204

@pytest.mark.asyncio
async def test_operator_cannot_create_checkpoint(client: AsyncClient, operator_user: User):
    token = await get_token(operator_user)
    resp = await client.post("/checkpoints", headers={"Authorization": f"Bearer {token}"}, json={
        "name": "越权节点", "identification_method": "manual", "is_gate": False,
    })
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_group_admin_can_list_all_checkpoints_without_factory_filter(
    client: AsyncClient,
    admin_user: User,
    db_session,
):
    checkpoint = CheckPoint(
        id=uuid.uuid4(),
        factory_id=uuid.uuid4(),
        name="老节点",
        identification_method=IdentificationMethod.manual,
        is_gate=False,
    )
    db_session.add(checkpoint)
    await db_session.commit()

    token = await get_token(admin_user)
    resp = await client.get("/checkpoints", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert any(item["id"] == str(checkpoint.id) for item in resp.json())


@pytest.mark.asyncio
async def test_group_admin_can_list_all_path_templates_without_factory_filter(
    client: AsyncClient,
    admin_user: User,
    db_session,
):
    checkpoint = CheckPoint(
        id=uuid.uuid4(),
        factory_id=uuid.uuid4(),
        name="模板节点",
        identification_method=IdentificationMethod.manual,
        is_gate=False,
    )
    template = PathTemplate(
        id=uuid.uuid4(),
        factory_id=checkpoint.factory_id,
        name="老模板",
    )
    step = PathTemplateStep(
        id=uuid.uuid4(),
        template_id=template.id,
        checkpoint_id=checkpoint.id,
        step_order=1,
        direction=StepDirection.any,
    )
    db_session.add_all([checkpoint, template, step])
    await db_session.commit()

    token = await get_token(admin_user)
    resp = await client.get("/path-templates", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert any(item["id"] == str(template.id) for item in resp.json())
