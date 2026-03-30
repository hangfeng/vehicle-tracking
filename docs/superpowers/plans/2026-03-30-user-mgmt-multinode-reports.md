# 用户管理 + 多节点追踪 + 批量操作 + 报表中心 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有厂区车辆管理系统上新增用户管理、多节点车辆路径追踪、批量操作和报表导出四个功能模块。

**Architecture:** 后端新增 5 张表（checkpoints, path_templates, path_template_steps, vehicle_journeys, journey_events），vehicles 表新增 current_checkpoint_id 字段，alerts 枚举新增 path_deviation 类型。通过 Alembic 迁移应用变更，不删除现有表。前端新增用户管理和报表页面，扩展出入记录和车辆页面支持批量操作。

**Tech Stack:** Python 3.11 + FastAPI + SQLAlchemy 2 async + Alembic + PostgreSQL 15 + React 19 + TypeScript + Ant Design 6 + recharts + openpyxl

---

## 文件结构

**后端新增文件：**
- `backend/app/models/checkpoint.py` — CheckPoint 模型
- `backend/app/models/path_template.py` — PathTemplate + PathTemplateStep 模型
- `backend/app/models/vehicle_journey.py` — VehicleJourney + JourneyEvent 模型
- `backend/app/schemas/user_mgmt.py` — UserCreate, UserUpdate, UserOut
- `backend/app/schemas/checkpoint.py` — CheckPointCreate, CheckPointOut
- `backend/app/schemas/path_template.py` — PathTemplateCreate, PathTemplateOut
- `backend/app/schemas/vehicle_journey.py` — VehicleJourneyCreate, JourneyEventCreate, JourneyOut
- `backend/app/schemas/report.py` — TrafficReport, VehicleReport, AlertReport
- `backend/app/routers/users.py` — 用户管理 API
- `backend/app/routers/checkpoints.py` — 节点管理 API
- `backend/app/routers/path_templates.py` — 路径模板 API
- `backend/app/routers/vehicle_journeys.py` — 行程 API
- `backend/app/routers/reports.py` — 报表 API
- `backend/alembic/versions/002_add_multinode_tables.py` — Alembic 迁移
- `backend/tests/test_users.py`
- `backend/tests/test_checkpoints.py`
- `backend/tests/test_vehicle_journeys.py`
- `backend/tests/test_reports.py`

**后端修改文件：**
- `backend/app/main.py` — 注册新 router，导入新模型
- `backend/app/models/vehicle.py` — 新增 current_checkpoint_id
- `backend/app/models/alert.py` — 新增 path_deviation 枚举值
- `backend/app/routers/gate_events.py` — 新增批量审核端点
- `backend/app/routers/vehicles.py` — 新增 Excel 导入端点
- `backend/tests/conftest.py` — 导入新模型，新增 group_admin fixture
- `backend/requirements.txt` — 新增 reportlab, pandas

**前端新增文件：**
- `frontend/src/pages/Users.tsx`
- `frontend/src/pages/Reports.tsx`
- `frontend/src/pages/Settings.tsx`

**前端修改文件：**
- `frontend/src/types/index.ts` — 新增类型
- `frontend/src/App.tsx` — 新增路由
- `frontend/src/components/AppLayout.tsx` — 新增导航项
- `frontend/src/pages/GateEvents.tsx` — 批量审核
- `frontend/src/pages/Vehicles.tsx` — Excel 导入

---

## Task 1: 新增后端模型 + Alembic 迁移

**Files:**
- Create: `backend/app/models/checkpoint.py`
- Create: `backend/app/models/path_template.py`
- Create: `backend/app/models/vehicle_journey.py`
- Modify: `backend/app/models/vehicle.py`
- Modify: `backend/app/models/alert.py`
- Create: `backend/alembic/versions/002_add_multinode_tables.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/conftest.py`

- [ ] **Step 1: 创建 CheckPoint 模型**

```python
# backend/app/models/checkpoint.py
import uuid
import enum
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Enum as SAEnum, JSON, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class IdentificationMethod(str, enum.Enum):
    camera = "camera"
    manual = "manual"

class CheckPoint(Base):
    __tablename__ = "checkpoints"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    factory_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("factories.id"))
    name: Mapped[str] = mapped_column(String(100))
    identification_method: Mapped[IdentificationMethod] = mapped_column(SAEnum(IdentificationMethod))
    is_gate: Mapped[bool] = mapped_column(Boolean, default=False)
    camera_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [ ] **Step 2: 创建 PathTemplate + PathTemplateStep 模型**

```python
# backend/app/models/path_template.py
import uuid
import enum
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey, Enum as SAEnum, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class StepDirection(str, enum.Enum):
    entry = "entry"
    exit = "exit"
    any = "any"

class PathTemplate(Base):
    __tablename__ = "path_templates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    factory_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("factories.id"))
    name: Mapped[str] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class PathTemplateStep(Base):
    __tablename__ = "path_template_steps"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("path_templates.id"))
    checkpoint_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("checkpoints.id"))
    step_order: Mapped[int] = mapped_column(Integer)
    direction: Mapped[StepDirection] = mapped_column(SAEnum(StepDirection))
```

- [ ] **Step 3: 创建 VehicleJourney + JourneyEvent 模型**

```python
# backend/app/models/vehicle_journey.py
import uuid
import enum
from datetime import datetime
from sqlalchemy import Text, Boolean, DateTime, ForeignKey, Enum as SAEnum, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class JourneyStatus(str, enum.Enum):
    active = "active"
    completed = "completed"
    deviated = "deviated"

class JourneyDirection(str, enum.Enum):
    entry = "entry"
    exit = "exit"

class VehicleJourney(Base):
    __tablename__ = "vehicle_journeys"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vehicles.id"))
    factory_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("factories.id"))
    template_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("path_templates.id"), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[JourneyStatus] = mapped_column(SAEnum(JourneyStatus), default=JourneyStatus.active)

class JourneyEvent(Base):
    __tablename__ = "journey_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    journey_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vehicle_journeys.id"))
    gate_event_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("gate_events.id"), nullable=True)
    checkpoint_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("checkpoints.id"))
    direction: Mapped[JourneyDirection] = mapped_column(SAEnum(JourneyDirection))
    occurred_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    is_deviation: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
```

- [ ] **Step 4: 更新 Vehicle 模型，新增 current_checkpoint_id**

在 `backend/app/models/vehicle.py` 末尾，`note` 字段后添加：

```python
    current_checkpoint_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("checkpoints.id"), nullable=True)
```

- [ ] **Step 5: 更新 Alert 模型，新增 path_deviation 枚举值**

修改 `backend/app/models/alert.py` 中的 `AlertType`：

```python
class AlertType(str, enum.Enum):
    long_stay = "long_stay"
    pending_review = "pending_review"
    path_deviation = "path_deviation"
```

- [ ] **Step 6: 更新 main.py 导入新模型**

修改 `backend/app/main.py` 第 4 行：

```python
from app.models import factory, user, vehicle, location, gate_event, alert, checkpoint, path_template, vehicle_journey  # noqa: F401
```

- [ ] **Step 7: 更新 conftest.py 导入新模型并添加 group_admin fixture**

修改 `backend/tests/conftest.py`：

```python
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.main import app
from app.database import Base, get_db
from app.models.user import User, UserRole
from app.models import factory, vehicle, location, gate_event, alert, checkpoint, path_template, vehicle_journey  # noqa: F401
from app.services.auth import hash_password
import uuid

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def operator_user(db_session):
    factory_id = uuid.uuid4()
    user = User(
        id=uuid.uuid4(),
        factory_id=factory_id,
        name="测试操作员",
        phone="13800000001",
        password_hash=hash_password("password123"),
        role=UserRole.operator,
    )
    db_session.add(user)
    await db_session.commit()
    return user

@pytest_asyncio.fixture
async def manager_user(db_session):
    factory_id = uuid.uuid4()
    user = User(
        id=uuid.uuid4(),
        factory_id=factory_id,
        name="测试管理员",
        phone="13800000002",
        password_hash=hash_password("password123"),
        role=UserRole.factory_manager,
    )
    db_session.add(user)
    await db_session.commit()
    return user

@pytest_asyncio.fixture
async def admin_user(db_session):
    user = User(
        id=uuid.uuid4(),
        factory_id=None,
        name="集团管理员",
        phone="13800000003",
        password_hash=hash_password("password123"),
        role=UserRole.group_admin,
    )
    db_session.add(user)
    await db_session.commit()
    return user
```

- [ ] **Step 8: 生成 Alembic 迁移文件**

在 backend 容器内运行（或 venv 中）：

```bash
cd backend
docker compose exec backend alembic revision --autogenerate -m "add multinode tables"
```

然后手动检查生成的迁移文件，确保包含：
- `checkpoints` 表创建
- `path_templates` 表创建
- `path_template_steps` 表创建
- `vehicle_journeys` 表创建
- `journey_events` 表创建
- `vehicles.current_checkpoint_id` 列新增

在 upgrade() 函数最开始添加（PostgreSQL 15 支持事务内 ADD VALUE）：

```python
op.execute(sa.text("ALTER TYPE alerttype ADD VALUE IF NOT EXISTS 'path_deviation'"))
```

在 downgrade() 中，PostgreSQL 不支持删除枚举值，留空注释：
```python
# NOTE: PostgreSQL does not support removing enum values
```

- [ ] **Step 9: 应用迁移**

```bash
docker compose exec backend alembic upgrade head
```

Expected output: 迁移成功，无错误

- [ ] **Step 10: 验证表已创建**

```bash
docker compose exec db psql -U postgres vehicle_tracking -c "\dt"
```

Expected: 输出中包含 checkpoints, path_templates, path_template_steps, vehicle_journeys, journey_events

- [ ] **Step 11: Commit**

```bash
git add backend/app/models/checkpoint.py backend/app/models/path_template.py backend/app/models/vehicle_journey.py
git add backend/app/models/vehicle.py backend/app/models/alert.py backend/app/main.py
git add backend/tests/conftest.py backend/alembic/versions/
git commit -m "feat: add checkpoint, path_template, vehicle_journey models and migration"
```

---

## Task 2: 用户管理 API

**Files:**
- Create: `backend/app/schemas/user_mgmt.py`
- Create: `backend/app/routers/users.py`
- Create: `backend/tests/test_users.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_users.py
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User, UserRole
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
    # manager can only see users in same factory; operator_user is in different factory
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
    # create a factory first
    from app.models.factory import Factory
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
```

- [ ] **Step 2: 运行测试验证失败**

```bash
docker compose exec backend pytest tests/test_users.py -v
```

Expected: FAIL — ImportError or 404

- [ ] **Step 3: 创建 schemas/user_mgmt.py**

```python
# backend/app/schemas/user_mgmt.py
import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.user import UserRole

class UserCreate(BaseModel):
    phone: str
    name: str
    password: str
    role: UserRole
    factory_id: uuid.UUID | None = None

class UserUpdate(BaseModel):
    name: str | None = None
    role: UserRole | None = None
    factory_id: uuid.UUID | None = None
    is_active: bool | None = None

class UserOut(BaseModel):
    id: uuid.UUID
    phone: str
    name: str
    role: UserRole
    factory_id: uuid.UUID | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}

class BatchStatusRequest(BaseModel):
    ids: list[uuid.UUID]
    is_active: bool

class BatchStatusResponse(BaseModel):
    updated: int
```

- [ ] **Step 4: 创建 routers/users.py**

```python
# backend/app/routers/users.py
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.user_mgmt import UserCreate, UserUpdate, UserOut, BatchStatusRequest, BatchStatusResponse
from app.deps import get_current_user, require_roles
from app.services.auth import hash_password

router = APIRouter(prefix="/users", tags=["users"])

def _can_manage_role(actor: User, target_role: UserRole) -> bool:
    """group_admin can manage any role; factory_manager can only manage operator."""
    if actor.role == UserRole.group_admin:
        return True
    if actor.role == UserRole.factory_manager:
        return target_role == UserRole.operator
    return False

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
    if actor.role == UserRole.factory_manager and body.factory_id != actor.factory_id:
        raise HTTPException(status_code=403, detail="Can only create users in your own factory")
    existing = await db.execute(select(User).where(User.phone == body.phone))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Phone already exists")
    new_user = User(
        phone=body.phone,
        name=body.name,
        password_hash=hash_password(body.password),
        role=body.role,
        factory_id=body.factory_id,
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
```

- [ ] **Step 5: 注册 router 到 main.py**

在 `backend/app/main.py` 中添加：

```python
from app.routers import auth, vehicles, gate_events, alerts, dashboard, users

# ...
app.include_router(users.router)
```

- [ ] **Step 6: 运行测试验证通过**

```bash
docker compose exec backend pytest tests/test_users.py -v
```

Expected: 全部 PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/user_mgmt.py backend/app/routers/users.py backend/tests/test_users.py backend/app/main.py
git commit -m "feat: add user management API with role-based access control"
```

---

## Task 3: 节点管理 API (Checkpoint)

**Files:**
- Create: `backend/app/schemas/checkpoint.py`
- Create: `backend/app/routers/checkpoints.py`
- Create: `backend/tests/test_checkpoints.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_checkpoints.py
import pytest
from httpx import AsyncClient
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
```

- [ ] **Step 2: 运行测试验证失败**

```bash
docker compose exec backend pytest tests/test_checkpoints.py -v
```

Expected: FAIL

- [ ] **Step 3: 创建 schemas/checkpoint.py**

```python
# backend/app/schemas/checkpoint.py
import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.checkpoint import IdentificationMethod

class CheckPointCreate(BaseModel):
    name: str
    identification_method: IdentificationMethod
    is_gate: bool = False
    camera_config: dict | None = None

class CheckPointUpdate(BaseModel):
    name: str | None = None
    identification_method: IdentificationMethod | None = None
    is_gate: bool | None = None
    camera_config: dict | None = None
    is_active: bool | None = None

class CheckPointOut(BaseModel):
    id: uuid.UUID
    factory_id: uuid.UUID
    name: str
    identification_method: IdentificationMethod
    is_gate: bool
    camera_config: dict | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 4: 创建 routers/checkpoints.py**

```python
# backend/app/routers/checkpoints.py
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.checkpoint import CheckPoint
from app.models.user import User, UserRole
from app.schemas.checkpoint import CheckPointCreate, CheckPointUpdate, CheckPointOut
from app.deps import get_current_user, require_roles

router = APIRouter(prefix="/checkpoints", tags=["checkpoints"])

@router.get("", response_model=list[CheckPointOut])
async def list_checkpoints(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(CheckPoint).where(CheckPoint.factory_id == user.factory_id)
    )
    return result.scalars().all()

@router.post("", response_model=CheckPointOut, status_code=201)
async def create_checkpoint(
    body: CheckPointCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.factory_manager, UserRole.group_admin)),
):
    cp = CheckPoint(**body.model_dump(), factory_id=user.factory_id)
    db.add(cp)
    await db.commit()
    await db.refresh(cp)
    return cp

@router.patch("/{cp_id}", response_model=CheckPointOut)
async def update_checkpoint(
    cp_id: uuid.UUID,
    body: CheckPointUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.factory_manager, UserRole.group_admin)),
):
    result = await db.execute(
        select(CheckPoint).where(CheckPoint.id == cp_id, CheckPoint.factory_id == user.factory_id)
    )
    cp = result.scalar_one_or_none()
    if not cp:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(cp, k, v)
    await db.commit()
    await db.refresh(cp)
    return cp

@router.delete("/{cp_id}", status_code=204)
async def delete_checkpoint(
    cp_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.factory_manager, UserRole.group_admin)),
):
    result = await db.execute(
        select(CheckPoint).where(CheckPoint.id == cp_id, CheckPoint.factory_id == user.factory_id)
    )
    cp = result.scalar_one_or_none()
    if not cp:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    await db.delete(cp)
    await db.commit()
```

- [ ] **Step 5: 注册 router 到 main.py**

```python
from app.routers import auth, vehicles, gate_events, alerts, dashboard, users, checkpoints

app.include_router(checkpoints.router)
```

- [ ] **Step 6: 运行测试验证通过**

```bash
docker compose exec backend pytest tests/test_checkpoints.py -v
```

Expected: 全部 PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/checkpoint.py backend/app/routers/checkpoints.py backend/tests/test_checkpoints.py backend/app/main.py
git commit -m "feat: add checkpoint management API"
```

---

## Task 4: 路径模板 API

**Files:**
- Create: `backend/app/schemas/path_template.py`
- Create: `backend/app/routers/path_templates.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: 创建 schemas/path_template.py**

```python
# backend/app/schemas/path_template.py
import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.path_template import StepDirection

class PathTemplateStepCreate(BaseModel):
    checkpoint_id: uuid.UUID
    step_order: int
    direction: StepDirection

class PathTemplateStepOut(BaseModel):
    id: uuid.UUID
    checkpoint_id: uuid.UUID
    step_order: int
    direction: StepDirection

    model_config = {"from_attributes": True}

class PathTemplateCreate(BaseModel):
    name: str
    steps: list[PathTemplateStepCreate]

class PathTemplateUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None
    steps: list[PathTemplateStepCreate] | None = None

class PathTemplateOut(BaseModel):
    id: uuid.UUID
    factory_id: uuid.UUID
    name: str
    is_active: bool
    created_at: datetime
    steps: list[PathTemplateStepOut] = []

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: 创建 routers/path_templates.py**

```python
# backend/app/routers/path_templates.py
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
```

PathTemplate 模型需要添加 `steps` relationship。在 `backend/app/models/path_template.py` 中 PathTemplate 类内添加：

```python
from sqlalchemy.orm import relationship
# 在 PathTemplate 类中：
    steps: Mapped[list["PathTemplateStep"]] = relationship("PathTemplateStep", lazy="select")
```

- [ ] **Step 3: 注册 router 到 main.py**

```python
from app.routers import auth, vehicles, gate_events, alerts, dashboard, users, checkpoints, path_templates

app.include_router(path_templates.router)
```

- [ ] **Step 4: 运行现有测试确认不破坏**

```bash
docker compose exec backend pytest tests/ -v --ignore=tests/test_users.py --ignore=tests/test_checkpoints.py
```

Expected: 全部 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/path_template.py backend/app/routers/path_templates.py backend/app/models/path_template.py backend/app/main.py
git commit -m "feat: add path template API"
```

---

## Task 5: 车辆行程 API + 路径偏离检测

**Files:**
- Create: `backend/app/schemas/vehicle_journey.py`
- Create: `backend/app/routers/vehicle_journeys.py`
- Create: `backend/tests/test_vehicle_journeys.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_vehicle_journeys.py
import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.vehicle import Vehicle, VehicleStatus
from app.models.checkpoint import CheckPoint, IdentificationMethod
from app.models.vehicle_journey import VehicleJourney, JourneyStatus
from app.services.auth import create_access_token

async def get_token(user: User) -> str:
    return create_access_token(str(user.id), user.role.value)

@pytest.mark.asyncio
async def test_start_journey(client: AsyncClient, operator_user: User, db_session: AsyncSession):
    token = await get_token(operator_user)
    vehicle = Vehicle(
        id=uuid.uuid4(),
        factory_id=operator_user.factory_id,
        plate_number="粤B00001",
        status=VehicleStatus.in_factory,
    )
    db_session.add(vehicle)
    await db_session.commit()

    resp = await client.post("/vehicle-journeys", headers={"Authorization": f"Bearer {token}"}, json={
        "vehicle_id": str(vehicle.id),
        "factory_id": str(operator_user.factory_id),
        "template_id": None,
    })
    assert resp.status_code == 201
    assert resp.json()["status"] == "active"

@pytest.mark.asyncio
async def test_record_journey_event(client: AsyncClient, operator_user: User, db_session: AsyncSession):
    token = await get_token(operator_user)
    vehicle = Vehicle(
        id=uuid.uuid4(),
        factory_id=operator_user.factory_id,
        plate_number="粤B00002",
        status=VehicleStatus.in_factory,
    )
    checkpoint = CheckPoint(
        id=uuid.uuid4(),
        factory_id=operator_user.factory_id,
        name="仓库A",
        identification_method=IdentificationMethod.manual,
        is_gate=False,
    )
    db_session.add(vehicle)
    db_session.add(checkpoint)
    await db_session.commit()

    journey_resp = await client.post("/vehicle-journeys", headers={"Authorization": f"Bearer {token}"}, json={
        "vehicle_id": str(vehicle.id),
        "factory_id": str(operator_user.factory_id),
        "template_id": None,
    })
    journey_id = journey_resp.json()["id"]

    event_resp = await client.post("/journey-events", headers={"Authorization": f"Bearer {token}"}, json={
        "journey_id": journey_id,
        "checkpoint_id": str(checkpoint.id),
        "direction": "entry",
        "license_plate": "粤B00002",
        "confidence": None,
        "image_url": None,
        "notes": None,
    })
    assert event_resp.status_code == 201
    assert event_resp.json()["is_deviation"] is False

@pytest.mark.asyncio
async def test_deviation_detected(client: AsyncClient, operator_user: User, db_session: AsyncSession):
    """If template has step1=checkpointA but event is at checkpointB, deviation=True."""
    token = await get_token(operator_user)
    from app.models.path_template import PathTemplate, PathTemplateStep, StepDirection
    cpA = CheckPoint(id=uuid.uuid4(), factory_id=operator_user.factory_id, name="A", identification_method=IdentificationMethod.manual, is_gate=False)
    cpB = CheckPoint(id=uuid.uuid4(), factory_id=operator_user.factory_id, name="B", identification_method=IdentificationMethod.manual, is_gate=False)
    vehicle = Vehicle(id=uuid.uuid4(), factory_id=operator_user.factory_id, plate_number="粤B00003", status=VehicleStatus.in_factory)
    tmpl = PathTemplate(id=uuid.uuid4(), factory_id=operator_user.factory_id, name="Test Template")
    db_session.add_all([cpA, cpB, vehicle, tmpl])
    await db_session.flush()
    step = PathTemplateStep(template_id=tmpl.id, checkpoint_id=cpA.id, step_order=1, direction=StepDirection.entry)
    db_session.add(step)
    await db_session.commit()

    journey_resp = await client.post("/vehicle-journeys", headers={"Authorization": f"Bearer {token}"}, json={
        "vehicle_id": str(vehicle.id),
        "factory_id": str(operator_user.factory_id),
        "template_id": str(tmpl.id),
    })
    journey_id = journey_resp.json()["id"]

    # Record event at cpB (wrong checkpoint, should be cpA)
    event_resp = await client.post("/journey-events", headers={"Authorization": f"Bearer {token}"}, json={
        "journey_id": journey_id,
        "checkpoint_id": str(cpB.id),
        "direction": "entry",
        "license_plate": "粤B00003",
        "confidence": None,
        "image_url": None,
        "notes": None,
    })
    assert event_resp.status_code == 201
    assert event_resp.json()["is_deviation"] is True
```

- [ ] **Step 2: 运行测试验证失败**

```bash
docker compose exec backend pytest tests/test_vehicle_journeys.py -v
```

Expected: FAIL

- [ ] **Step 3: 创建 schemas/vehicle_journey.py**

```python
# backend/app/schemas/vehicle_journey.py
import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.vehicle_journey import JourneyStatus, JourneyDirection

class VehicleJourneyCreate(BaseModel):
    vehicle_id: uuid.UUID
    factory_id: uuid.UUID
    template_id: uuid.UUID | None = None

class JourneyEventCreate(BaseModel):
    journey_id: uuid.UUID
    checkpoint_id: uuid.UUID
    direction: JourneyDirection
    license_plate: str | None = None
    confidence: float | None = None
    image_url: str | None = None
    notes: str | None = None

class JourneyEventOut(BaseModel):
    id: uuid.UUID
    journey_id: uuid.UUID
    checkpoint_id: uuid.UUID
    direction: JourneyDirection
    occurred_at: datetime
    is_deviation: bool
    notes: str | None

    model_config = {"from_attributes": True}

class VehicleJourneyOut(BaseModel):
    id: uuid.UUID
    vehicle_id: uuid.UUID
    factory_id: uuid.UUID
    template_id: uuid.UUID | None
    started_at: datetime
    completed_at: datetime | None
    status: JourneyStatus

    model_config = {"from_attributes": True}
```

- [ ] **Step 4: 创建 routers/vehicle_journeys.py**

```python
# backend/app/routers/vehicle_journeys.py
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.vehicle_journey import VehicleJourney, JourneyEvent, JourneyStatus
from app.models.path_template import PathTemplateStep
from app.models.vehicle import Vehicle
from app.models.alert import Alert, AlertType, AlertSeverity, AlertStatus
from app.models.user import User
from app.schemas.vehicle_journey import VehicleJourneyCreate, JourneyEventCreate, VehicleJourneyOut, JourneyEventOut
from app.deps import get_current_user

router = APIRouter(tags=["vehicle-journeys"])

@router.post("/vehicle-journeys", response_model=VehicleJourneyOut, status_code=201)
async def start_journey(
    body: VehicleJourneyCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Close any existing active journey for this vehicle
    result = await db.execute(
        select(VehicleJourney).where(
            VehicleJourney.vehicle_id == body.vehicle_id,
            VehicleJourney.status == JourneyStatus.active,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        from datetime import datetime
        existing.status = JourneyStatus.completed
        existing.completed_at = datetime.utcnow()

    journey = VehicleJourney(
        vehicle_id=body.vehicle_id,
        factory_id=body.factory_id,
        template_id=body.template_id,
    )
    db.add(journey)
    await db.commit()
    await db.refresh(journey)
    return journey

@router.get("/vehicles/{vehicle_id}/journey", response_model=VehicleJourneyOut | None)
async def get_active_journey(
    vehicle_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(VehicleJourney).where(
            VehicleJourney.vehicle_id == vehicle_id,
            VehicleJourney.status == JourneyStatus.active,
        )
    )
    return result.scalar_one_or_none()

@router.get("/vehicles/{vehicle_id}/journeys", response_model=list[VehicleJourneyOut])
async def list_journeys(
    vehicle_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(VehicleJourney).where(VehicleJourney.vehicle_id == vehicle_id)
    )
    return result.scalars().all()

@router.post("/journey-events", response_model=JourneyEventOut, status_code=201)
async def record_journey_event(
    body: JourneyEventCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Load journey
    result = await db.execute(select(VehicleJourney).where(VehicleJourney.id == body.journey_id))
    journey = result.scalar_one_or_none()
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")

    is_deviation = False

    # Check deviation against template
    if journey.template_id:
        # Count existing events to determine expected step
        from sqlalchemy import func
        count_result = await db.execute(
            select(func.count()).where(JourneyEvent.journey_id == body.journey_id)
        )
        event_count = count_result.scalar()
        expected_order = event_count + 1

        step_result = await db.execute(
            select(PathTemplateStep).where(
                PathTemplateStep.template_id == journey.template_id,
                PathTemplateStep.step_order == expected_order,
            )
        )
        expected_step = step_result.scalar_one_or_none()

        if expected_step is None:
            # Extra event beyond template
            is_deviation = True
        elif expected_step.checkpoint_id != body.checkpoint_id:
            is_deviation = True
        elif expected_step.direction.value != "any" and expected_step.direction.value != body.direction.value:
            is_deviation = True

    event = JourneyEvent(
        journey_id=body.journey_id,
        checkpoint_id=body.checkpoint_id,
        direction=body.direction,
        is_deviation=is_deviation,
        notes=body.notes,
    )
    db.add(event)

    if is_deviation:
        journey.status = JourneyStatus.deviated
        # Create alert
        veh_result = await db.execute(select(Vehicle).where(Vehicle.id == journey.vehicle_id))
        vehicle = veh_result.scalar_one_or_none()
        alert = Alert(
            factory_id=journey.factory_id,
            vehicle_id=journey.vehicle_id,
            type=AlertType.path_deviation,
            message=f"车辆 {vehicle.plate_number if vehicle else '未知'} 偏离预定路径",
            severity=AlertSeverity.warning,
            status=AlertStatus.active,
        )
        db.add(alert)

    # Update vehicle current_checkpoint_id
    veh_result = await db.execute(select(Vehicle).where(Vehicle.id == journey.vehicle_id))
    vehicle = veh_result.scalar_one_or_none()
    if vehicle:
        vehicle.current_checkpoint_id = body.checkpoint_id

    await db.commit()
    await db.refresh(event)
    return event
```

- [ ] **Step 5: 注册 router 到 main.py**

```python
from app.routers import auth, vehicles, gate_events, alerts, dashboard, users, checkpoints, path_templates, vehicle_journeys

app.include_router(vehicle_journeys.router)
```

- [ ] **Step 6: 运行测试验证通过**

```bash
docker compose exec backend pytest tests/test_vehicle_journeys.py -v
```

Expected: 全部 PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/vehicle_journey.py backend/app/routers/vehicle_journeys.py backend/tests/test_vehicle_journeys.py backend/app/main.py
git commit -m "feat: add vehicle journey API with path deviation detection"
```

---

## Task 6: 批量操作 API

**Files:**
- Modify: `backend/app/routers/gate_events.py`
- Modify: `backend/app/routers/vehicles.py`
- Modify: `backend/requirements.txt`

- [ ] **Step 1: 更新 requirements.txt**

在 `backend/requirements.txt` 末尾不需要添加新依赖（openpyxl 已有，无需额外包）。此步骤可跳过，继续下一步。

- [ ] **Step 2: 在 gate_events.py 新增批量审核端点**

在 `backend/app/routers/gate_events.py` 中，在文件顶部的 import 区域添加 `from pydantic import BaseModel`，然后在文件末尾添加：

```python
class BatchReviewRequest(BaseModel):
    ids: list[uuid.UUID]
    action: str  # "confirm" or "reject"

class BatchReviewResponse(BaseModel):
    updated: int

@router.post("/batch-review", response_model=BatchReviewResponse)
async def batch_review_gate_events(
    body: BatchReviewRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.operator, UserRole.factory_manager, UserRole.group_admin)),
):
    result = await db.execute(
        select(GateEvent).where(
            GateEvent.id.in_(body.ids),
            GateEvent.factory_id == user.factory_id,
            GateEvent.review_status == ReviewStatus.pending_review,
        )
    )
    events = result.scalars().all()
    new_status = ReviewStatus.manually_confirmed if body.action == "confirm" else ReviewStatus.rejected
    for event in events:
        event.review_status = new_status
        event.reviewed_by = user.id
        event.reviewed_at = datetime.utcnow()
    await db.commit()
    return BatchReviewResponse(updated=len(events))
```

- [ ] **Step 3: 写批量审核测试**

```python
# 在 backend/tests/test_gate_events_batch.py
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
```

- [ ] **Step 4: 运行批量审核测试**

```bash
docker compose exec backend pytest tests/test_gate_events_batch.py -v
```

Expected: PASS

- [ ] **Step 5: 在 vehicles.py 新增 Excel 导入端点**

在 `backend/app/routers/vehicles.py` 中，在文件顶部的 import 区域添加：
```python
from fastapi import UploadFile, File
from pydantic import BaseModel
import openpyxl
import io
```

然后在文件末尾添加：

```python
class ImportResponse(BaseModel):
    created: int
    skipped: int
    errors: list[str]

@router.post("/import", response_model=ImportResponse)
async def import_vehicles(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.factory_manager, UserRole.group_admin)),
):
    content = await file.read()
    try:
        wb = openpyxl.load_workbook(io.BytesIO(content))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Excel file")

    ws = wb.active
    created = 0
    skipped = 0
    errors = []

    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if not row or not row[0]:
            continue
        plate = str(row[0]).strip()
        company = str(row[1]).strip() if len(row) > 1 and row[1] else None
        contact_name = str(row[2]).strip() if len(row) > 2 and row[2] else None
        contact_phone = str(row[3]).strip() if len(row) > 3 and row[3] else None

        if not plate:
            errors.append(f"Row {row_idx}: 车牌号不能为空")
            continue
        if not company:
            errors.append(f"Row {row_idx}: 所属公司不能为空")
            continue

        existing = await db.execute(
            select(Vehicle).where(Vehicle.plate_number == plate, Vehicle.factory_id == user.factory_id)
        )
        if existing.scalar_one_or_none():
            skipped += 1
            continue

        vehicle = Vehicle(
            plate_number=plate,
            company=company,
            contact_name=contact_name,
            contact_phone=contact_phone,
            factory_id=user.factory_id,
        )
        db.add(vehicle)
        created += 1

    await db.commit()
    return ImportResponse(created=created, skipped=skipped, errors=errors)
```

- [ ] **Step 6: 运行所有后端测试**

```bash
docker compose exec backend pytest tests/ -v
```

Expected: 全部 PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/gate_events.py backend/app/routers/vehicles.py backend/requirements.txt backend/tests/test_gate_events_batch.py
git commit -m "feat: add batch review and Excel vehicle import"
```

---

## Task 7: 报表 API

**Files:**
- Create: `backend/app/schemas/report.py`
- Create: `backend/app/routers/reports.py`
- Create: `backend/tests/test_reports.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_reports.py
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
async def test_report_export_excel(client: AsyncClient, operator_user: User):
    token = await get_token(operator_user)
    resp = await client.get(
        "/reports/export",
        headers={"Authorization": f"Bearer {token}"},
        params={"start_date": "2020-01-01", "end_date": "2099-12-31", "format": "excel"},
    )
    assert resp.status_code == 200
    assert "spreadsheet" in resp.headers["content-type"]
```

- [ ] **Step 2: 运行测试验证失败**

```bash
docker compose exec backend pytest tests/test_reports.py -v
```

Expected: FAIL

- [ ] **Step 3: 创建 schemas/report.py**

```python
# backend/app/schemas/report.py
from pydantic import BaseModel

class DailyTraffic(BaseModel):
    date: str
    entries: int
    exits: int

class CheckpointTraffic(BaseModel):
    checkpoint_id: str
    name: str
    entries: int
    exits: int

class TrafficReport(BaseModel):
    total_entries: int
    total_exits: int
    avg_stay_duration_minutes: float | None
    by_day: list[DailyTraffic]
    by_checkpoint: list[CheckpointTraffic]

class VehicleActivity(BaseModel):
    vehicle_id: str
    plate_number: str
    total_visits: int
    alert_count: int

class VehicleReport(BaseModel):
    vehicles: list[VehicleActivity]

class AlertSummaryItem(BaseModel):
    type: str
    count: int

class AlertReport(BaseModel):
    total_active: int
    total_resolved: int
    by_type: list[AlertSummaryItem]
```

- [ ] **Step 4: 创建 routers/reports.py**

```python
# backend/app/routers/reports.py
import io
import uuid
from datetime import datetime, date
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.database import get_db
from app.models.gate_event import GateEvent, Direction
from app.models.vehicle import Vehicle
from app.models.alert import Alert, AlertStatus
from app.models.user import User
from app.schemas.report import TrafficReport, DailyTraffic, CheckpointTraffic, VehicleReport, VehicleActivity, AlertReport, AlertSummaryItem
from app.deps import get_current_user
import openpyxl

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/traffic", response_model=TrafficReport)
async def traffic_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    granularity: str = Query("day"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    factory_id = user.factory_id
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    base_q = select(GateEvent).where(
        GateEvent.factory_id == factory_id,
        GateEvent.captured_at >= start_dt,
        GateEvent.captured_at <= end_dt,
    )

    result = await db.execute(base_q)
    events = result.scalars().all()

    total_entries = sum(1 for e in events if e.direction == Direction.entry)
    total_exits = sum(1 for e in events if e.direction == Direction.exit)

    # Group by day
    day_map: dict[str, dict] = {}
    for e in events:
        d = e.captured_at.strftime("%Y-%m-%d")
        if d not in day_map:
            day_map[d] = {"entries": 0, "exits": 0}
        if e.direction == Direction.entry:
            day_map[d]["entries"] += 1
        else:
            day_map[d]["exits"] += 1
    by_day = [DailyTraffic(date=d, **v) for d, v in sorted(day_map.items())]

    return TrafficReport(
        total_entries=total_entries,
        total_exits=total_exits,
        avg_stay_duration_minutes=None,
        by_day=by_day,
        by_checkpoint=[],
    )

@router.get("/vehicles", response_model=VehicleReport)
async def vehicle_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    factory_id = user.factory_id
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    result = await db.execute(
        select(GateEvent.vehicle_id, func.count().label("visits"))
        .where(
            GateEvent.factory_id == factory_id,
            GateEvent.captured_at >= start_dt,
            GateEvent.captured_at <= end_dt,
            GateEvent.vehicle_id.isnot(None),
        )
        .group_by(GateEvent.vehicle_id)
        .order_by(func.count().desc())
        .limit(50)
    )
    rows = result.all()

    activities = []
    for vehicle_id, visits in rows:
        veh_result = await db.execute(select(Vehicle).where(Vehicle.id == vehicle_id))
        vehicle = veh_result.scalar_one_or_none()
        alert_result = await db.execute(
            select(func.count()).where(
                Alert.vehicle_id == vehicle_id,
                Alert.created_at >= start_dt,
                Alert.created_at <= end_dt,
            )
        )
        alert_count = alert_result.scalar()
        if vehicle:
            activities.append(VehicleActivity(
                vehicle_id=str(vehicle_id),
                plate_number=vehicle.plate_number,
                total_visits=visits,
                alert_count=alert_count or 0,
            ))

    return VehicleReport(vehicles=activities)

@router.get("/alerts", response_model=AlertReport)
async def alert_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    factory_id = user.factory_id
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    result = await db.execute(
        select(Alert).where(
            Alert.factory_id == factory_id,
            Alert.created_at >= start_dt,
            Alert.created_at <= end_dt,
        )
    )
    alerts = result.scalars().all()

    total_active = sum(1 for a in alerts if a.status == AlertStatus.active)
    total_resolved = sum(1 for a in alerts if a.status == AlertStatus.resolved)

    type_map: dict[str, int] = {}
    for a in alerts:
        type_map[a.type.value] = type_map.get(a.type.value, 0) + 1
    by_type = [AlertSummaryItem(type=t, count=c) for t, c in type_map.items()]

    return AlertReport(total_active=total_active, total_resolved=total_resolved, by_type=by_type)

@router.get("/export")
async def export_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    format: str = Query("excel"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    factory_id = user.factory_id
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    result = await db.execute(
        select(GateEvent).where(
            GateEvent.factory_id == factory_id,
            GateEvent.captured_at >= start_dt,
            GateEvent.captured_at <= end_dt,
        ).order_by(GateEvent.captured_at)
    )
    events = result.scalars().all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "进出记录"
    ws.append(["车牌", "方向", "时间", "置信度", "审核状态"])
    for e in events:
        ws.append([
            e.plate_number,
            "入场" if e.direction == Direction.entry else "出场",
            e.captured_at.strftime("%Y-%m-%d %H:%M:%S"),
            f"{e.confidence_score:.2%}" if e.confidence_score else "",
            e.review_status.value,
        ])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=report_{start_date}_{end_date}.xlsx"},
    )
```

- [ ] **Step 5: 注册 router 到 main.py**

```python
from app.routers import auth, vehicles, gate_events, alerts, dashboard, users, checkpoints, path_templates, vehicle_journeys, reports

app.include_router(reports.router)
```

- [ ] **Step 6: 运行测试验证通过**

```bash
docker compose exec backend pytest tests/test_reports.py -v
```

Expected: 全部 PASS

- [ ] **Step 7: 运行所有后端测试**

```bash
docker compose exec backend pytest tests/ -v
```

Expected: 全部 PASS

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas/report.py backend/app/routers/reports.py backend/tests/test_reports.py backend/app/main.py
git commit -m "feat: add reports API with traffic, vehicle, and alert summaries"
```

---

## Task 8: 前端 - 类型 + 导航 + 用户管理页面

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/AppLayout.tsx`
- Create: `frontend/src/pages/Users.tsx`

- [ ] **Step 1: 安装 recharts**

```bash
docker compose exec frontend npm install recharts
```

- [ ] **Step 2: 更新 frontend/src/types/index.ts**

```typescript
export type UserRole = "group_admin" | "factory_manager" | "operator";

export interface User {
  id: string;
  name: string;
  phone: string;
  role: UserRole;
  factory_id: string | null;
  is_active: boolean;
  created_at: string;
}

export type Direction = "entry" | "exit";
export type ReviewStatus = "auto_confirmed" | "pending_review" | "manually_confirmed" | "rejected";
export type VehicleStatus = "in_factory" | "out" | "unknown";
export type AlertType = "long_stay" | "pending_review" | "path_deviation";
export type AlertStatus = "active" | "resolved";
export type IdentificationMethod = "camera" | "manual";
export type JourneyStatus = "active" | "completed" | "deviated";
export type JourneyDirection = "entry" | "exit";

export interface GateEvent {
  id: string;
  factory_id: string;
  plate_number: string;
  direction: Direction;
  captured_at: string;
  image_url: string | null;
  confidence_score: number | null;
  review_status: ReviewStatus;
  is_manual: boolean;
}

export interface Vehicle {
  id: string;
  factory_id: string;
  plate_number: string;
  vehicle_type: string;
  company: string | null;
  contact_name: string | null;
  contact_phone: string | null;
  status: VehicleStatus;
  last_seen_at: string | null;
  note: string | null;
  current_checkpoint_id: string | null;
}

export interface Alert {
  id: string;
  factory_id: string;
  vehicle_id: string | null;
  type: AlertType;
  message: string;
  severity: string;
  status: AlertStatus;
  created_at: string;
  resolved_at: string | null;
  note: string | null;
}

export interface DashboardStats {
  vehicles_in_factory: number;
  entries_today: number;
  exits_today: number;
  pending_review_count: number;
  active_alerts_count: number;
}

export interface CheckPoint {
  id: string;
  factory_id: string;
  name: string;
  identification_method: IdentificationMethod;
  is_gate: boolean;
  camera_config: Record<string, unknown> | null;
  is_active: boolean;
  created_at: string;
}

export interface PathTemplateStep {
  id: string;
  checkpoint_id: string;
  step_order: number;
  direction: "entry" | "exit" | "any";
}

export interface PathTemplate {
  id: string;
  factory_id: string;
  name: string;
  is_active: boolean;
  created_at: string;
  steps: PathTemplateStep[];
}

export interface VehicleJourney {
  id: string;
  vehicle_id: string;
  factory_id: string;
  template_id: string | null;
  started_at: string;
  completed_at: string | null;
  status: JourneyStatus;
}

export interface DailyTraffic {
  date: string;
  entries: number;
  exits: number;
}

export interface TrafficReport {
  total_entries: number;
  total_exits: number;
  avg_stay_duration_minutes: number | null;
  by_day: DailyTraffic[];
  by_checkpoint: Array<{ checkpoint_id: string; name: string; entries: number; exits: number }>;
}

export interface AlertReport {
  total_active: number;
  total_resolved: number;
  by_type: Array<{ type: string; count: number }>;
}
```

- [ ] **Step 3: 更新 AppLayout.tsx，新增导航项**

```typescript
// frontend/src/components/AppLayout.tsx
import { Layout, Menu } from "antd";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import {
  DashboardOutlined,
  CarOutlined,
  AlertOutlined,
  SwapOutlined,
  UserOutlined,
  BarChartOutlined,
  SettingOutlined,
  LogoutOutlined,
} from "@ant-design/icons";
import { useAuthStore } from "../store/auth";

const { Sider, Content, Header } = Layout;

export default function AppLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuthStore();

  const allItems = [
    { key: "/", icon: <DashboardOutlined />, label: "实时看板", roles: ["group_admin", "factory_manager", "operator"] },
    { key: "/gate-events", icon: <SwapOutlined />, label: "出入记录", roles: ["group_admin", "factory_manager", "operator"] },
    { key: "/vehicles", icon: <CarOutlined />, label: "车辆管理", roles: ["group_admin", "factory_manager", "operator"] },
    { key: "/alerts", icon: <AlertOutlined />, label: "报警中心", roles: ["group_admin", "factory_manager", "operator"] },
    { key: "/users", icon: <UserOutlined />, label: "用户管理", roles: ["group_admin", "factory_manager"] },
    { key: "/reports", icon: <BarChartOutlined />, label: "报表中心", roles: ["group_admin", "factory_manager", "operator"] },
    { key: "/settings", icon: <SettingOutlined />, label: "系统设置", roles: ["group_admin", "factory_manager"] },
  ];

  const menuItems = allItems
    .filter(item => !user || item.roles.includes(user.role))
    .map(({ key, icon, label }) => ({ key, icon, label }));

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider width={200} theme="dark">
        <div style={{ color: "#fff", padding: "16px", fontWeight: "bold", fontSize: 16 }}>
          车辆管理
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header style={{
          background: "#fff",
          padding: "0 24px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          borderBottom: "1px solid #f0f0f0",
        }}>
          <span style={{ color: "#475569" }}>
            {user?.name} · {user?.role}
          </span>
          <LogoutOutlined style={{ cursor: "pointer", color: "#6b7280" }} onClick={logout} />
        </Header>
        <Content style={{ margin: 24 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
```

- [ ] **Step 4: 创建用户管理页面 Users.tsx**

```typescript
// frontend/src/pages/Users.tsx
import { useEffect, useState } from "react";
import { Table, Button, Tag, Drawer, Form, Input, Select, Space, Popconfirm, Typography, message } from "antd";
import { PlusOutlined } from "@ant-design/icons";
import { api } from "../api/client";
import { useAuthStore } from "../store/auth";
import type { User, UserRole } from "../types";
import dayjs from "dayjs";

const roleLabels: Record<UserRole, string> = {
  group_admin: "集团管理员",
  factory_manager: "厂区管理员",
  operator: "操作员",
};
const roleColors: Record<UserRole, string> = {
  group_admin: "blue",
  factory_manager: "green",
  operator: "default",
};

export default function Users() {
  const { user: me } = useAuthStore();
  const [users, setUsers] = useState<User[]>([]);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [form] = Form.useForm();

  const fetchUsers = async () => {
    const resp = await api.get("/users");
    setUsers(resp.data);
  };

  useEffect(() => { fetchUsers(); }, []);

  const openCreate = () => {
    setEditingUser(null);
    form.resetFields();
    setDrawerOpen(true);
  };

  const openEdit = (u: User) => {
    setEditingUser(u);
    form.setFieldsValue({ name: u.name, role: u.role, factory_id: u.factory_id });
    setDrawerOpen(true);
  };

  const handleSubmit = async () => {
    const values = await form.validateFields();
    if (editingUser) {
      await api.patch(`/users/${editingUser.id}`, values);
      message.success("更新成功");
    } else {
      await api.post("/users", values);
      message.success("创建成功");
    }
    setDrawerOpen(false);
    fetchUsers();
  };

  const handleBatchStatus = async (is_active: boolean) => {
    const resp = await api.post("/users/batch-status", { ids: selectedIds, is_active });
    message.success(`已${is_active ? "启用" : "停用"} ${resp.data.updated} 个用户`);
    setSelectedIds([]);
    fetchUsers();
  };

  const availableRoles: UserRole[] = me?.role === "group_admin"
    ? ["group_admin", "factory_manager", "operator"]
    : ["operator"];

  const columns = [
    { title: "姓名", dataIndex: "name", key: "name" },
    { title: "手机号", dataIndex: "phone", key: "phone" },
    {
      title: "角色",
      dataIndex: "role",
      key: "role",
      render: (r: UserRole) => <Tag color={roleColors[r]}>{roleLabels[r]}</Tag>,
    },
    {
      title: "状态",
      dataIndex: "is_active",
      key: "is_active",
      render: (v: boolean) => <Tag color={v ? "green" : "red"}>{v ? "启用" : "停用"}</Tag>,
    },
    {
      title: "创建时间",
      dataIndex: "created_at",
      key: "created_at",
      render: (v: string) => dayjs(v).format("YYYY-MM-DD HH:mm"),
    },
    {
      title: "操作",
      key: "action",
      render: (_: unknown, record: User) => (
        <Button type="link" onClick={() => openEdit(record)}>编辑</Button>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>用户管理</Typography.Title>
        <Space>
          {selectedIds.length > 0 && (
            <>
              <Popconfirm title="确认启用选中用户？" onConfirm={() => handleBatchStatus(true)}>
                <Button>批量启用</Button>
              </Popconfirm>
              <Popconfirm title="确认停用选中用户？" onConfirm={() => handleBatchStatus(false)}>
                <Button danger>批量停用</Button>
              </Popconfirm>
            </>
          )}
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建用户</Button>
        </Space>
      </div>

      <Table
        dataSource={users}
        columns={columns}
        rowKey="id"
        rowSelection={{
          selectedRowKeys: selectedIds,
          onChange: (keys) => setSelectedIds(keys as string[]),
        }}
      />

      <Drawer
        title={editingUser ? "编辑用户" : "新建用户"}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        footer={
          <Button type="primary" onClick={handleSubmit} block>保存</Button>
        }
      >
        <Form form={form} layout="vertical">
          {!editingUser && (
            <>
              <Form.Item name="phone" label="手机号" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
              <Form.Item name="password" label="初始密码" rules={[{ required: true }]}>
                <Input.Password />
              </Form.Item>
            </>
          )}
          <Form.Item name="name" label="姓名" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          {!editingUser && (
            <Form.Item name="role" label="角色" rules={[{ required: true }]}>
              <Select options={availableRoles.map(r => ({ value: r, label: roleLabels[r] }))} />
            </Form.Item>
          )}
        </Form>
      </Drawer>
    </div>
  );
}
```

- [ ] **Step 5: 更新 App.tsx，注册新路由**

```typescript
// frontend/src/App.tsx
import { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useAuthStore } from "./store/auth";
import AppLayout from "./components/AppLayout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import GateEvents from "./pages/GateEvents";
import Vehicles from "./pages/Vehicles";
import Alerts from "./pages/Alerts";
import Users from "./pages/Users";
import Reports from "./pages/Reports";
import Settings from "./pages/Settings";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token);
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  const { token, fetchMe } = useAuthStore();

  useEffect(() => {
    if (token) fetchMe();
  }, []);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <AppLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="gate-events" element={<GateEvents />} />
          <Route path="vehicles" element={<Vehicles />} />
          <Route path="alerts" element={<Alerts />} />
          <Route path="users" element={<Users />} />
          <Route path="reports" element={<Reports />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
```

- [ ] **Step 6: 验证前端编译无错误**

```bash
docker compose exec frontend npm run build
```

Expected: Build successful, no TypeScript errors

- [ ] **Step 7: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/App.tsx frontend/src/components/AppLayout.tsx frontend/src/pages/Users.tsx
git commit -m "feat: add user management page and update navigation"
```

---

## Task 9: 前端 - 系统设置页面（节点 + 路径模板）

**Files:**
- Create: `frontend/src/pages/Settings.tsx`

- [ ] **Step 1: 创建 Settings.tsx**

```typescript
// frontend/src/pages/Settings.tsx
import { useEffect, useState } from "react";
import { Tabs, Table, Button, Modal, Form, Input, Select, Switch, Space, Tag, message, Typography } from "antd";
import { PlusOutlined, DeleteOutlined } from "@ant-design/icons";
import { api } from "../api/client";
import type { CheckPoint, PathTemplate } from "../types";

function CheckpointSettings() {
  const [checkpoints, setCheckpoints] = useState<CheckPoint[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<CheckPoint | null>(null);
  const [form] = Form.useForm();

  const fetch = async () => {
    const resp = await api.get("/checkpoints");
    setCheckpoints(resp.data);
  };

  useEffect(() => { fetch(); }, []);

  const openCreate = () => { setEditing(null); form.resetFields(); setModalOpen(true); };
  const openEdit = (cp: CheckPoint) => {
    setEditing(cp);
    form.setFieldsValue({ name: cp.name, identification_method: cp.identification_method, is_gate: cp.is_gate });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    const values = await form.validateFields();
    if (editing) {
      await api.patch(`/checkpoints/${editing.id}`, values);
      message.success("更新成功");
    } else {
      await api.post("/checkpoints", values);
      message.success("创建成功");
    }
    setModalOpen(false);
    fetch();
  };

  const handleDelete = async (id: string) => {
    await api.delete(`/checkpoints/${id}`);
    message.success("已删除");
    fetch();
  };

  const columns = [
    { title: "名称", dataIndex: "name" },
    {
      title: "识别方式",
      dataIndex: "identification_method",
      render: (v: string) => <Tag>{v === "camera" ? "摄像头" : "手动"}</Tag>,
    },
    {
      title: "类型",
      dataIndex: "is_gate",
      render: (v: boolean) => <Tag color={v ? "blue" : "default"}>{v ? "大门" : "内部节点"}</Tag>,
    },
    {
      title: "状态",
      dataIndex: "is_active",
      render: (v: boolean) => <Tag color={v ? "green" : "red"}>{v ? "启用" : "停用"}</Tag>,
    },
    {
      title: "操作",
      render: (_: unknown, r: CheckPoint) => (
        <Space>
          <Button type="link" onClick={() => openEdit(r)}>编辑</Button>
          <Button type="link" danger onClick={() => handleDelete(r.id)}>删除</Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 12 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增节点</Button>
      </div>
      <Table dataSource={checkpoints} columns={columns} rowKey="id" />
      <Modal title={editing ? "编辑节点" : "新增节点"} open={modalOpen} onOk={handleSubmit} onCancel={() => setModalOpen(false)}>
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="节点名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="identification_method" label="识别方式" rules={[{ required: true }]}>
            <Select options={[{ value: "camera", label: "摄像头" }, { value: "manual", label: "手动录入" }]} />
          </Form.Item>
          <Form.Item name="is_gate" label="是否大门节点" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

function TemplateSettings() {
  const [templates, setTemplates] = useState<PathTemplate[]>([]);
  const [checkpoints, setCheckpoints] = useState<CheckPoint[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();

  const fetch = async () => {
    const [tResp, cResp] = await Promise.all([api.get("/path-templates"), api.get("/checkpoints")]);
    setTemplates(tResp.data);
    setCheckpoints(cResp.data);
  };

  useEffect(() => { fetch(); }, []);

  const handleSubmit = async () => {
    const values = await form.validateFields();
    await api.post("/path-templates", values);
    message.success("创建成功");
    setModalOpen(false);
    fetch();
  };

  const handleDelete = async (id: string) => {
    await api.delete(`/path-templates/${id}`);
    message.success("已删除");
    fetch();
  };

  const cpOptions = checkpoints.map(cp => ({ value: cp.id, label: cp.name }));

  const columns = [
    { title: "模板名称", dataIndex: "name" },
    {
      title: "步骤数",
      dataIndex: "steps",
      render: (steps: PathTemplate["steps"]) => steps?.length ?? 0,
    },
    {
      title: "状态",
      dataIndex: "is_active",
      render: (v: boolean) => <Tag color={v ? "green" : "red"}>{v ? "启用" : "停用"}</Tag>,
    },
    {
      title: "操作",
      render: (_: unknown, r: PathTemplate) => (
        <Button type="link" danger icon={<DeleteOutlined />} onClick={() => handleDelete(r.id)}>删除</Button>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 12 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => { form.resetFields(); setModalOpen(true); }}>
          新建模板
        </Button>
      </div>
      <Table dataSource={templates} columns={columns} rowKey="id" />
      <Modal title="新建路径模板" open={modalOpen} onOk={handleSubmit} onCancel={() => setModalOpen(false)} width={600}>
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="模板名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.List name="steps">
            {(fields, { add, remove }) => (
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                  <span>步骤列表</span>
                  <Button size="small" onClick={() => add({ step_order: fields.length + 1, direction: "entry" })}>
                    + 添加步骤
                  </Button>
                </div>
                {fields.map((field, index) => (
                  <Space key={field.key} style={{ display: "flex", marginBottom: 8 }} align="start">
                    <Form.Item name={[field.name, "checkpoint_id"]} rules={[{ required: true }]} noStyle>
                      <Select placeholder="选择节点" style={{ width: 160 }} options={cpOptions} />
                    </Form.Item>
                    <Form.Item name={[field.name, "direction"]} rules={[{ required: true }]} noStyle>
                      <Select style={{ width: 100 }} options={[
                        { value: "entry", label: "进入" },
                        { value: "exit", label: "离开" },
                        { value: "any", label: "任意" },
                      ]} />
                    </Form.Item>
                    <Form.Item name={[field.name, "step_order"]} initialValue={index + 1} hidden>
                      <Input />
                    </Form.Item>
                    <Button danger onClick={() => remove(field.name)}>删除</Button>
                  </Space>
                ))}
              </div>
            )}
          </Form.List>
        </Form>
      </Modal>
    </div>
  );
}

export default function Settings() {
  return (
    <div>
      <Typography.Title level={4}>系统设置</Typography.Title>
      <Tabs
        items={[
          { key: "checkpoints", label: "节点管理", children: <CheckpointSettings /> },
          { key: "templates", label: "路径模板", children: <TemplateSettings /> },
        ]}
      />
    </div>
  );
}
```

- [ ] **Step 2: 验证编译**

```bash
docker compose exec frontend npm run build
```

Expected: Build successful

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Settings.tsx
git commit -m "feat: add settings page with checkpoint and path template management"
```

---

## Task 10: 前端 - 批量操作

**Files:**
- Modify: `frontend/src/pages/GateEvents.tsx`
- Modify: `frontend/src/pages/Vehicles.tsx`

- [ ] **Step 1: 更新 GateEvents.tsx 添加批量审核**

在现有 GateEvents.tsx 中，添加以下变更：

1. 在 state 部分新增：
```typescript
const [selectedIds, setSelectedIds] = useState<string[]>([]);
```

2. 新增批量审核函数：
```typescript
const handleBatchReview = async (action: "confirm" | "reject") => {
  if (selectedIds.length === 0) return;
  const resp = await api.post("/gate-events/batch-review", { ids: selectedIds, action });
  message.success(`已处理 ${resp.data.updated} 条记录`);
  setSelectedIds([]);
  fetchEvents();
};
```

3. 在 Table 组件上添加 `rowSelection` 和批量操作按钮：

在筛选区域下方，Table 上方添加：
```typescript
{selectedIds.length > 0 && (
  <Space style={{ marginBottom: 12 }}>
    <span>{selectedIds.length} 条已选中</span>
    <Popconfirm title="批量确认选中记录？" onConfirm={() => handleBatchReview("confirm")}>
      <Button type="primary" size="small">批量确认</Button>
    </Popconfirm>
    <Popconfirm title="批量拒绝选中记录？" onConfirm={() => handleBatchReview("reject")}>
      <Button danger size="small">批量拒绝</Button>
    </Popconfirm>
  </Space>
)}
```

在 Table 组件添加 rowSelection：
```typescript
rowSelection={{
  selectedRowKeys: selectedIds,
  onChange: (keys) => setSelectedIds(keys as string[]),
  getCheckboxProps: (record: GateEvent) => ({
    disabled: record.review_status !== "pending_review",
  }),
}}
```

完整更新后的 GateEvents.tsx：

```typescript
import { useEffect, useState } from "react";
import {
  Table, Tag, Button, Modal, Input, Select, Space, Typography, Popconfirm, message,
} from "antd";
import { api } from "../api/client";
import type { GateEvent } from "../types";
import dayjs from "dayjs";

export default function GateEvents() {
  const [events, setEvents] = useState<GateEvent[]>([]);
  const [reviewing, setReviewing] = useState<GateEvent | null>(null);
  const [correctedPlate, setCorrectedPlate] = useState("");
  const [filterPlate, setFilterPlate] = useState("");
  const [filterStatus, setFilterStatus] = useState<string | undefined>();
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const fetchEvents = async () => {
    const params: Record<string, string> = {};
    if (filterPlate) params.plate = filterPlate;
    if (filterStatus) params.review_status = filterStatus;
    const resp = await api.get("/gate-events", { params });
    setEvents(resp.data);
  };

  useEffect(() => { fetchEvents(); }, [filterPlate, filterStatus]);

  const handleReview = async (action: "confirm" | "reject") => {
    if (!reviewing) return;
    await api.patch(`/gate-events/${reviewing.id}/review`, {
      plate_number: correctedPlate,
      action,
    });
    setReviewing(null);
    fetchEvents();
  };

  const handleBatchReview = async (action: "confirm" | "reject") => {
    const resp = await api.post("/gate-events/batch-review", { ids: selectedIds, action });
    message.success(`已处理 ${resp.data.updated} 条记录`);
    setSelectedIds([]);
    fetchEvents();
  };

  const handleExport = () => {
    const params = new URLSearchParams();
    if (filterPlate) params.set("plate", filterPlate);
    window.open(`/api/gate-events/export?${params.toString()}`, "_blank");
  };

  const reviewStatusMap: Record<string, [string, string]> = {
    auto_confirmed: ["已自动确认", "blue"],
    pending_review: ["待审核", "orange"],
    manually_confirmed: ["人工确认", "green"],
    rejected: ["已拒绝", "red"],
  };

  const columns = [
    { title: "车牌", dataIndex: "plate_number", key: "plate_number" },
    {
      title: "方向",
      dataIndex: "direction",
      key: "direction",
      render: (d: string) => <Tag color={d === "entry" ? "green" : "red"}>{d === "entry" ? "入场" : "出场"}</Tag>,
    },
    {
      title: "时间",
      dataIndex: "captured_at",
      key: "captured_at",
      render: (v: string) => dayjs(v).format("YYYY-MM-DD HH:mm:ss"),
    },
    {
      title: "置信度",
      dataIndex: "confidence_score",
      key: "confidence_score",
      render: (v: number | null) => v != null ? `${(v * 100).toFixed(1)}%` : "-",
    },
    {
      title: "审核状态",
      dataIndex: "review_status",
      key: "review_status",
      render: (s: string) => {
        const [label, color] = reviewStatusMap[s] ?? [s, "default"];
        return <Tag color={color}>{label}</Tag>;
      },
    },
    {
      title: "操作",
      key: "action",
      render: (_: unknown, record: GateEvent) =>
        record.review_status === "pending_review" ? (
          <Button type="link" onClick={() => { setReviewing(record); setCorrectedPlate(record.plate_number); }}>
            审核
          </Button>
        ) : null,
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>出入记录</Typography.Title>
        <Button onClick={handleExport}>导出 Excel</Button>
      </div>

      <Space style={{ marginBottom: 12 }}>
        <Input.Search
          placeholder="搜索车牌"
          onSearch={setFilterPlate}
          allowClear
          style={{ width: 200 }}
        />
        <Select
          placeholder="审核状态"
          allowClear
          style={{ width: 160 }}
          onChange={setFilterStatus}
          options={[
            { value: "pending_review", label: "待审核" },
            { value: "auto_confirmed", label: "已自动确认" },
            { value: "manually_confirmed", label: "人工确认" },
            { value: "rejected", label: "已拒绝" },
          ]}
        />
      </Space>

      {selectedIds.length > 0 && (
        <Space style={{ marginBottom: 12 }}>
          <span style={{ color: "#6b7280" }}>{selectedIds.length} 条已选中</span>
          <Popconfirm title="批量确认选中记录？" onConfirm={() => handleBatchReview("confirm")}>
            <Button type="primary" size="small">批量确认</Button>
          </Popconfirm>
          <Popconfirm title="批量拒绝选中记录？" onConfirm={() => handleBatchReview("reject")}>
            <Button danger size="small">批量拒绝</Button>
          </Popconfirm>
        </Space>
      )}

      <Table
        dataSource={events}
        columns={columns}
        rowKey="id"
        rowSelection={{
          selectedRowKeys: selectedIds,
          onChange: (keys) => setSelectedIds(keys as string[]),
          getCheckboxProps: (record: GateEvent) => ({
            disabled: record.review_status !== "pending_review",
          }),
        }}
      />

      <Modal
        title="审核记录"
        open={!!reviewing}
        onCancel={() => setReviewing(null)}
        footer={
          <Space>
            <Button onClick={() => handleReview("reject")} danger>拒绝</Button>
            <Button type="primary" onClick={() => handleReview("confirm")}>确认</Button>
          </Space>
        }
      >
        <p>原始识别车牌：<strong>{reviewing?.plate_number}</strong></p>
        <Input
          value={correctedPlate}
          onChange={(e) => setCorrectedPlate(e.target.value)}
          placeholder="修正车牌（如无需修正保持原值）"
        />
      </Modal>
    </div>
  );
}
```

- [ ] **Step 2: 更新 Vehicles.tsx 添加 Excel 导入**

在现有 Vehicles.tsx 中新增 Excel 导入功能。在文件顶部 import 中添加：

```typescript
import { Upload, message } from "antd";
import { UploadOutlined } from "@ant-design/icons";
import type { UploadProps } from "antd";
```

在组件内添加导入处理函数：
```typescript
const uploadProps: UploadProps = {
  accept: ".xlsx,.xls",
  showUploadList: false,
  customRequest: async ({ file }) => {
    const formData = new FormData();
    formData.append("file", file as File);
    const resp = await api.post("/vehicles/import", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    const { created, skipped, errors } = resp.data;
    message.success(`导入完成：新增 ${created} 辆，跳过 ${skipped} 辆${errors.length ? `，${errors.length} 条错误` : ""}`);
    fetchVehicles();
  },
};
```

在页面顶部按钮区域添加：
```typescript
<Upload {...uploadProps}>
  <Button icon={<UploadOutlined />}>导入 Excel</Button>
</Upload>
```

- [ ] **Step 3: 验证编译**

```bash
docker compose exec frontend npm run build
```

Expected: Build successful

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/GateEvents.tsx frontend/src/pages/Vehicles.tsx
git commit -m "feat: add batch review to gate events and Excel import to vehicles"
```

---

## Task 11: 前端 - 报表中心页面

**Files:**
- Create: `frontend/src/pages/Reports.tsx`

- [ ] **Step 1: 创建 Reports.tsx**

```typescript
// frontend/src/pages/Reports.tsx
import { useState } from "react";
import { DatePicker, Select, Button, Card, Row, Col, Statistic, Table, Tabs, Space, Typography, message } from "antd";
import { DownloadOutlined } from "@ant-design/icons";
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { api } from "../api/client";
import type { TrafficReport, AlertReport } from "../types";
import dayjs, { type Dayjs } from "dayjs";

const { RangePicker } = DatePicker;

export default function Reports() {
  const [dateRange, setDateRange] = useState<[Dayjs, Dayjs]>([
    dayjs().subtract(7, "day"),
    dayjs(),
  ]);
  const [granularity, setGranularity] = useState("day");
  const [trafficData, setTrafficData] = useState<TrafficReport | null>(null);
  const [alertData, setAlertData] = useState<AlertReport | null>(null);
  const [loading, setLoading] = useState(false);

  const params = {
    start_date: dateRange[0].format("YYYY-MM-DD"),
    end_date: dateRange[1].format("YYYY-MM-DD"),
    granularity,
  };

  const fetchReports = async () => {
    setLoading(true);
    try {
      const [tResp, aResp] = await Promise.all([
        api.get("/reports/traffic", { params }),
        api.get("/reports/alerts", { params }),
      ]);
      setTrafficData(tResp.data);
      setAlertData(aResp.data);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = () => {
    const p = new URLSearchParams({ ...params, format: "excel" });
    window.open(`/api/reports/export?${p.toString()}`, "_blank");
  };

  const alertTypeLabels: Record<string, string> = {
    long_stay: "长时间在厂",
    pending_review: "低置信度待审",
    path_deviation: "路径偏离",
  };

  const alertColumns = [
    { title: "报警类型", dataIndex: "type", render: (t: string) => alertTypeLabels[t] ?? t },
    { title: "次数", dataIndex: "count" },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>报表中心</Typography.Title>
        <Button icon={<DownloadOutlined />} onClick={handleExport}>导出 Excel</Button>
      </div>

      <Space style={{ marginBottom: 16 }}>
        <RangePicker
          value={dateRange}
          onChange={(v) => v && setDateRange(v as [Dayjs, Dayjs])}
          presets={[
            { label: "今日", value: [dayjs(), dayjs()] },
            { label: "本周", value: [dayjs().startOf("week"), dayjs()] },
            { label: "本月", value: [dayjs().startOf("month"), dayjs()] },
          ]}
        />
        <Select
          value={granularity}
          onChange={setGranularity}
          options={[
            { value: "day", label: "按天" },
            { value: "week", label: "按周" },
            { value: "month", label: "按月" },
          ]}
          style={{ width: 100 }}
        />
        <Button type="primary" onClick={fetchReports} loading={loading}>查询</Button>
      </Space>

      {trafficData && (
        <Tabs
          items={[
            {
              key: "traffic",
              label: "进出流量",
              children: (
                <div>
                  <Row gutter={16} style={{ marginBottom: 24 }}>
                    <Col span={6}>
                      <Card>
                        <Statistic title="总进场次数" value={trafficData.total_entries} />
                      </Card>
                    </Col>
                    <Col span={6}>
                      <Card>
                        <Statistic title="总出场次数" value={trafficData.total_exits} />
                      </Card>
                    </Col>
                    <Col span={6}>
                      <Card>
                        <Statistic
                          title="平均在厂时长"
                          value={trafficData.avg_stay_duration_minutes ?? "N/A"}
                          suffix={trafficData.avg_stay_duration_minutes ? "分钟" : ""}
                        />
                      </Card>
                    </Col>
                    <Col span={6}>
                      <Card>
                        <Statistic
                          title="活跃报警"
                          value={alertData?.total_active ?? 0}
                          valueStyle={{ color: alertData && alertData.total_active > 0 ? "#cf1322" : undefined }}
                        />
                      </Card>
                    </Col>
                  </Row>

                  <Card title="进出趋势" style={{ marginBottom: 24 }}>
                    <ResponsiveContainer width="100%" height={300}>
                      <LineChart data={trafficData.by_day}>
                        <XAxis dataKey="date" />
                        <YAxis />
                        <Tooltip />
                        <Legend />
                        <Line type="monotone" dataKey="entries" name="进场" stroke="#52c41a" />
                        <Line type="monotone" dataKey="exits" name="出场" stroke="#f5222d" />
                      </LineChart>
                    </ResponsiveContainer>
                  </Card>
                </div>
              ),
            },
            {
              key: "alerts",
              label: "报警汇总",
              children: alertData ? (
                <div>
                  <Row gutter={16} style={{ marginBottom: 16 }}>
                    <Col span={6}>
                      <Card>
                        <Statistic title="待处理报警" value={alertData.total_active} valueStyle={{ color: "#cf1322" }} />
                      </Card>
                    </Col>
                    <Col span={6}>
                      <Card>
                        <Statistic title="已解决报警" value={alertData.total_resolved} valueStyle={{ color: "#52c41a" }} />
                      </Card>
                    </Col>
                  </Row>
                  <Card title="报警类型分布">
                    <Table
                      dataSource={alertData.by_type}
                      columns={alertColumns}
                      rowKey="type"
                      pagination={false}
                    />
                  </Card>
                </div>
              ) : null,
            },
          ]}
        />
      )}

      {!trafficData && !loading && (
        <div style={{ textAlign: "center", padding: "48px 0", color: "#9ca3af" }}>
          请选择时间范围并点击查询
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: 验证完整编译**

```bash
docker compose exec frontend npm run build
```

Expected: Build successful, no errors

- [ ] **Step 3: 重启前端容器**

```bash
docker compose restart frontend
```

- [ ] **Step 4: 端到端验证**

1. 打开 http://localhost:5173，使用 admin 账号 (13900000000/admin123456) 登录
2. 左侧菜单应显示：实时看板、出入记录、车辆管理、报警中心、用户管理、报表中心、系统设置
3. 访问 /users → 应显示用户列表，可新建用户
4. 访问 /settings → 应显示节点管理和路径模板标签
5. 访问 /reports → 选择日期范围，点击查询，应显示统计数据
6. 访问 /gate-events → 表格应有复选框，待审核记录可批量操作

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Reports.tsx
git commit -m "feat: add reports page with traffic trend chart and alert summary"
```

---

## 验收标准

- [ ] 所有后端测试通过：`docker compose exec backend pytest tests/ -v`
- [ ] 前端编译无错误：`docker compose exec frontend npm run build`
- [ ] 5 张新表已在 PostgreSQL 中创建
- [ ] 用户管理：group_admin 可管理所有用户，factory_manager 只能管本厂区操作员
- [ ] 节点管理：可创建 camera/manual 两种识别方式的节点
- [ ] 路径模板：可定义多步骤路径，路径偏离触发报警
- [ ] 批量审核：出入记录页支持多选批量确认/拒绝
- [ ] Excel 导入：车辆管理页支持 Excel 批量导入
- [ ] 报表中心：进出趋势折线图 + 报警汇总，支持 Excel 导出
