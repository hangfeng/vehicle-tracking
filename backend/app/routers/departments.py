import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.department import Department
from app.models.user import User, UserRole
from app.schemas.department import DepartmentCreate, DepartmentOut, DepartmentUpdate
from app.deps import get_current_user, require_roles

router = APIRouter(prefix="/departments", tags=["departments"])


def _resolve_factory_id(user: User, provided: uuid.UUID | None) -> uuid.UUID:
    if user.role in (UserRole.system_admin, UserRole.group_admin):
        if not provided:
            raise HTTPException(status_code=400, detail="需指定 factory_id")
        return provided
    if user.factory_id is None:
        raise HTTPException(status_code=400, detail="当前用户未绑定厂区")
    return user.factory_id


@router.get("", response_model=list[DepartmentOut])
async def list_departments(
    factory_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(Department)
    if user.role in (UserRole.system_admin, UserRole.group_admin):
        if factory_id is not None:
            query = query.where(Department.factory_id == factory_id)
    else:
        query = query.where(Department.factory_id == user.factory_id)
    result = await db.execute(query.order_by(Department.created_at))
    return result.scalars().all()


@router.post("", response_model=DepartmentOut, status_code=201)
async def create_department(
    body: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.group_admin, UserRole.factory_manager)),
):
    department = Department(
        factory_id=_resolve_factory_id(user, body.factory_id),
        name=body.name,
    )
    db.add(department)
    await db.commit()
    await db.refresh(department)
    return department


@router.patch("/{department_id}", response_model=DepartmentOut)
async def update_department(
    department_id: uuid.UUID,
    body: DepartmentUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.group_admin, UserRole.factory_manager)),
):
    query = select(Department).where(Department.id == department_id)
    if user.role not in (UserRole.system_admin, UserRole.group_admin):
        query = query.where(Department.factory_id == user.factory_id)
    result = await db.execute(query)
    department = result.scalar_one_or_none()
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")
    for key, value in body.model_dump(exclude_none=True).items():
        setattr(department, key, value)
    await db.commit()
    await db.refresh(department)
    return department
