import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.path_template import PathTemplate, PathTemplateStep
from app.models.user import User, UserRole
from app.schemas.path_template import PathTemplateCreate, PathTemplateUpdate, PathTemplateOut
from app.deps import get_current_user, require_roles

router = APIRouter(prefix="/path-templates", tags=["path-templates"])

@router.get("", response_model=list[PathTemplateOut])
async def list_templates(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PathTemplate)
        .where(PathTemplate.factory_id == user.factory_id)
        .options(selectinload(PathTemplate.steps))
    )
    return result.scalars().all()

@router.post("", response_model=PathTemplateOut, status_code=201)
async def create_template(
    body: PathTemplateCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.factory_manager, UserRole.group_admin)),
):
    tmpl = PathTemplate(name=body.name, factory_id=user.factory_id)
    db.add(tmpl)
    await db.flush()
    for s in body.steps:
        step = PathTemplateStep(template_id=tmpl.id, **s.model_dump())
        db.add(step)
    await db.commit()
    result = await db.execute(
        select(PathTemplate).where(PathTemplate.id == tmpl.id).options(selectinload(PathTemplate.steps))
    )
    return result.scalar_one()

@router.get("/{tmpl_id}", response_model=PathTemplateOut)
async def get_template(
    tmpl_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PathTemplate)
        .where(PathTemplate.id == tmpl_id, PathTemplate.factory_id == user.factory_id)
        .options(selectinload(PathTemplate.steps))
    )
    tmpl = result.scalar_one_or_none()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return tmpl

@router.patch("/{tmpl_id}", response_model=PathTemplateOut)
async def update_template(
    tmpl_id: uuid.UUID,
    body: PathTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.factory_manager, UserRole.group_admin)),
):
    result = await db.execute(
        select(PathTemplate).where(PathTemplate.id == tmpl_id, PathTemplate.factory_id == user.factory_id)
    )
    tmpl = result.scalar_one_or_none()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    if body.name is not None:
        tmpl.name = body.name
    if body.is_active is not None:
        tmpl.is_active = body.is_active
    if body.steps is not None:
        await db.execute(delete(PathTemplateStep).where(PathTemplateStep.template_id == tmpl_id))
        for s in body.steps:
            db.add(PathTemplateStep(template_id=tmpl_id, **s.model_dump()))
    await db.commit()
    result = await db.execute(
        select(PathTemplate).where(PathTemplate.id == tmpl_id).options(selectinload(PathTemplate.steps))
    )
    return result.scalar_one()

@router.delete("/{tmpl_id}", status_code=204)
async def delete_template(
    tmpl_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.factory_manager, UserRole.group_admin)),
):
    result = await db.execute(
        select(PathTemplate).where(PathTemplate.id == tmpl_id, PathTemplate.factory_id == user.factory_id)
    )
    tmpl = result.scalar_one_or_none()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    await db.execute(delete(PathTemplateStep).where(PathTemplateStep.template_id == tmpl_id))
    await db.delete(tmpl)
    await db.commit()
