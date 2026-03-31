import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.user_mgmt import UserCreate, UserUpdate, UserOut, BatchStatusRequest, BatchStatusResponse
from app.deps import get_current_user, require_roles
from app.services.auth import hash_password
from app.services.serial_numbers import generate_serial_no

router = APIRouter(prefix="/users", tags=["users"])

def _can_manage_role(actor: User, target_role: UserRole) -> bool:
    """group_admin can manage any role; factory_manager can only manage operator."""
    if actor.role == UserRole.group_admin:
        return True
    if actor.role == UserRole.factory_manager:
        return target_role == UserRole.operator
    return False


def _validate_role_factory_assignment(role: UserRole, factory_id: uuid.UUID | None) -> None:
    if role == UserRole.group_admin and factory_id is not None:
        raise HTTPException(status_code=400, detail="集团管理员不能绑定所属厂区")
    if role in (UserRole.factory_manager, UserRole.operator) and factory_id is None:
        raise HTTPException(status_code=400, detail="厂区管理员和操作员必须选择所属厂区")


def _validate_role_department_assignment(
    role: UserRole,
    department_id: uuid.UUID | None,
) -> None:
    if role == UserRole.group_admin and department_id is not None:
        raise HTTPException(status_code=400, detail="集团管理员不能绑定所属部门")

@router.get("", response_model=list[UserOut])
async def list_users(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.group_admin, UserRole.factory_manager)),
):
    if user.role == UserRole.group_admin:
        result = await db.execute(select(User))
    else:
        result = await db.execute(
            select(User).where(
                User.factory_id == user.factory_id,
                User.role == UserRole.operator,
            )
        )
    return result.scalars().all()

@router.post("", response_model=UserOut, status_code=201)
async def create_user(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.group_admin, UserRole.factory_manager)),
):
    if not _can_manage_role(actor, body.role):
        raise HTTPException(status_code=403, detail="Cannot create user with this role")
    _validate_role_factory_assignment(body.role, body.factory_id)
    _validate_role_department_assignment(body.role, body.department_id)
    if actor.role == UserRole.factory_manager and body.factory_id != actor.factory_id:
        raise HTTPException(status_code=403, detail="Can only create users in your own factory")
    existing = await db.execute(select(User).where(User.phone == body.phone))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Phone already exists")
    new_user = User(
        serial_no=await generate_serial_no(
            db,
            model=User,
            serial_column=User.serial_no,
            module_prefix="USR",
        ),
        phone=body.phone,
        name=body.name,
        password_hash=hash_password(body.password),
        role=body.role,
        factory_id=body.factory_id,
        department_id=body.department_id,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.group_admin, UserRole.factory_manager)),
):
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if actor.role == UserRole.factory_manager and target.factory_id != actor.factory_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return target

@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.group_admin, UserRole.factory_manager)),
):
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if not _can_manage_role(actor, target.role):
        raise HTTPException(status_code=403, detail="Cannot modify user with this role")
    if actor.role == UserRole.factory_manager and target.factory_id != actor.factory_id:
        raise HTTPException(status_code=403, detail="Access denied")
    # Check new role assignment is also permitted (prevent privilege escalation)
    if body.role is not None and not _can_manage_role(actor, body.role):
        raise HTTPException(status_code=403, detail="Cannot assign this role")
    next_role = body.role if body.role is not None else target.role
    next_factory_id = body.factory_id if body.factory_id is not None else target.factory_id
    next_department_id = body.department_id if body.department_id is not None else target.department_id
    _validate_role_factory_assignment(next_role, next_factory_id)
    _validate_role_department_assignment(next_role, next_department_id)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(target, k, v)
    await db.commit()
    await db.refresh(target)
    return target

@router.post("/batch-status", response_model=BatchStatusResponse)
async def batch_update_status(
    body: BatchStatusRequest,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.group_admin, UserRole.factory_manager)),
):
    result = await db.execute(select(User).where(User.id.in_(body.ids)))
    targets = result.scalars().all()
    updated = 0
    for target in targets:
        if not _can_manage_role(actor, target.role):
            continue
        if actor.role == UserRole.factory_manager and target.factory_id != actor.factory_id:
            continue
        target.is_active = body.is_active
        updated += 1
    await db.commit()
    return BatchStatusResponse(updated=updated)
