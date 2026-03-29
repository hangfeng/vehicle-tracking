# 厂区车辆进出管理系统 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个基于摄像头车牌识别的厂区车辆进出管理系统，支持实时看板、出入记录查询、报警管理，三级角色权限。

**Architecture:** FastAPI 后端 + React 前端 + 独立 PaddleOCR AI 识别服务。所有表含 factory_id 支持多厂区扩展。Redis 缓存实时车辆状态，WebSocket 推送看板数据。

**Tech Stack:** Python 3.11 + FastAPI + SQLAlchemy 2 + Alembic + PostgreSQL 15 + Redis 7 + React 18 + Vite + TypeScript + Ant Design 5 + PaddleOCR + Docker Compose

---

## 文件结构

```
vehicle-tracking/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/versions/
│   ├── app/
│   │   ├── main.py              # FastAPI app, router registration
│   │   ├── config.py            # Settings from env vars
│   │   ├── database.py          # SQLAlchemy engine + session
│   │   ├── deps.py              # FastAPI dependencies (get_db, get_current_user)
│   │   ├── models/
│   │   │   ├── factory.py       # Factory model
│   │   │   ├── user.py          # User model + role enum
│   │   │   ├── vehicle.py       # Vehicle model + status enum
│   │   │   ├── location.py      # Gate/location model
│   │   │   ├── gate_event.py    # GateEvent model + review_status enum
│   │   │   └── alert.py         # Alert model + type enum
│   │   ├── schemas/
│   │   │   ├── auth.py          # LoginRequest, TokenResponse, UserOut
│   │   │   ├── vehicle.py       # VehicleCreate, VehicleOut, VehicleUpdate
│   │   │   ├── gate_event.py    # GateEventCreate, GateEventOut, ReviewRequest
│   │   │   ├── alert.py         # AlertOut, ResolveRequest
│   │   │   └── dashboard.py     # DashboardStats, RecentEvent
│   │   ├── routers/
│   │   │   ├── auth.py          # POST /auth/login, GET /auth/me
│   │   │   ├── vehicles.py      # CRUD /vehicles
│   │   │   ├── gate_events.py   # GET/POST /gate-events, PATCH review
│   │   │   ├── alerts.py        # GET /alerts, PATCH resolve
│   │   │   ├── dashboard.py     # GET /dashboard/stats
│   │   │   └── settings.py      # GET/PUT /settings/alert-rules
│   │   ├── services/
│   │   │   ├── auth.py          # JWT create/verify, password hash
│   │   │   ├── vehicle_status.py # Update vehicle status in Redis
│   │   │   └── alert_engine.py  # Check long_stay, create alerts
│   │   └── ws/
│   │       └── manager.py       # WebSocket connection manager
│   └── tests/
│       ├── conftest.py
│       ├── test_auth.py
│       ├── test_vehicles.py
│       ├── test_gate_events.py
│       └── test_alerts.py
├── ai-service/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                  # FastAPI app exposing /recognize
│   ├── recognizer.py            # PaddleOCR wrapper
│   └── tests/
│       └── test_recognizer.py
└── frontend/
    ├── package.json
    ├── vite.config.ts
    ├── src/
    │   ├── main.tsx
    │   ├── App.tsx              # Routes + auth guard
    │   ├── api/
    │   │   ├── client.ts        # Axios instance + interceptors
    │   │   ├── auth.ts
    │   │   ├── vehicles.ts
    │   │   ├── gateEvents.ts
    │   │   └── alerts.ts
    │   ├── store/
    │   │   ├── auth.ts          # Zustand auth store
    │   │   └── realtime.ts      # WebSocket + live stats
    │   ├── pages/
    │   │   ├── Login.tsx
    │   │   ├── Dashboard.tsx
    │   │   ├── GateEvents.tsx
    │   │   ├── Vehicles.tsx
    │   │   ├── Alerts.tsx
    │   │   └── Settings.tsx
    │   ├── components/
    │   │   ├── AppLayout.tsx    # Left sidebar + top bar
    │   │   ├── StatsCards.tsx
    │   │   ├── EventTable.tsx
    │   │   └── ReviewModal.tsx
    │   └── types/
    │       └── index.ts         # Shared TypeScript types
    └── tests/
```

---

## Task 1: 项目基础设施（Docker Compose + 环境变量）

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `backend/requirements.txt`
- Create: `ai-service/requirements.txt`

- [ ] **Step 1: 创建 .env.example**

```bash
# .env.example
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/vehicle_tracking
REDIS_URL=redis://redis:6379/0
SECRET_KEY=change-this-to-a-random-secret-key-in-production
AI_SERVICE_URL=http://ai-service:8001
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=gate-captures
AI_CONFIDENCE_THRESHOLD=0.85
LONG_STAY_HOURS=8
```

- [ ] **Step 2: 创建 docker-compose.yml**

```yaml
version: "3.9"

services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: vehicle_tracking
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    volumes:
      - minio_data:/data
    ports:
      - "9000:9000"
      - "9001:9001"

  backend:
    build: ./backend
    env_file: .env
    ports:
      - "8000:8000"
    depends_on:
      - db
      - redis
      - minio
    volumes:
      - ./backend:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  ai-service:
    build: ./ai-service
    ports:
      - "8001:8001"
    volumes:
      - ./ai-service:/app
    command: uvicorn main:app --host 0.0.0.0 --port 8001 --reload

  frontend:
    image: node:20-alpine
    working_dir: /app
    volumes:
      - ./frontend:/app
    ports:
      - "5173:5173"
    command: sh -c "npm install && npm run dev -- --host"
    depends_on:
      - backend

volumes:
  postgres_data:
  minio_data:
```

- [ ] **Step 3: 创建 backend/requirements.txt**

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
sqlalchemy[asyncio]==2.0.30
asyncpg==0.29.0
alembic==1.13.1
pydantic[email]==2.7.1
pydantic-settings==2.2.1
passlib[bcrypt]==1.7.4
python-jose[cryptography]==3.3.0
python-multipart==0.0.9
redis[hiredis]==5.0.4
httpx==0.27.0
boto3==1.34.0
pytest==8.2.0
pytest-asyncio==0.23.6
httpx==0.27.0
```

- [ ] **Step 4: 创建 ai-service/requirements.txt**

```
fastapi==0.111.0
uvicorn==0.29.0
paddlepaddle==2.6.1
paddleocr==2.7.3
opencv-python-headless==4.9.0.80
numpy==1.26.4
httpx==0.27.0
pytest==8.2.0
```

- [ ] **Step 5: 复制 .env**

```bash
cp .env.example .env
```

- [ ] **Step 6: 启动基础服务验证**

```bash
docker compose up db redis minio -d
docker compose ps
```

Expected: 三个容器 running 状态

- [ ] **Step 7: Commit**

```bash
git add docker-compose.yml .env.example backend/requirements.txt ai-service/requirements.txt
git commit -m "feat: add project infrastructure (docker-compose, deps)"
```

---

## Task 2: 后端基础框架（config, database, main）

**Files:**
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`
- Create: `backend/app/main.py`
- Create: `backend/Dockerfile`

- [ ] **Step 1: 创建 backend/Dockerfile**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
```

- [ ] **Step 2: 创建 backend/app/config.py**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str
    secret_key: str
    ai_service_url: str
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str = "gate-captures"
    ai_confidence_threshold: float = 0.85
    long_stay_hours: int = 8
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    class Config:
        env_file = ".env"

settings = Settings()
```

- [ ] **Step 3: 创建 backend/app/database.py**

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
```

- [ ] **Step 4: 创建 backend/app/main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Vehicle Tracking API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 5: 启动后端验证**

```bash
docker compose up backend -d
curl http://localhost:8000/health
```

Expected: `{"status":"ok"}`

- [ ] **Step 6: Commit**

```bash
git add backend/
git commit -m "feat: add backend base (config, database, fastapi app)"
```

---

## Task 3: 数据库模型（models）

**Files:**
- Create: `backend/app/models/factory.py`
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/vehicle.py`
- Create: `backend/app/models/location.py`
- Create: `backend/app/models/gate_event.py`
- Create: `backend/app/models/alert.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`

- [ ] **Step 1: 创建 backend/app/models/factory.py**

```python
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class Factory(Base):
    __tablename__ = "factories"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100))
    address: Mapped[str | None] = mapped_column(String(500))
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Shanghai")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [ ] **Step 2: 创建 backend/app/models/user.py**

```python
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, ForeignKey, Enum as SAEnum, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
import enum

class UserRole(str, enum.Enum):
    group_admin = "group_admin"
    factory_manager = "factory_manager"
    operator = "operator"

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    factory_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("factories.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [ ] **Step 3: 创建 backend/app/models/vehicle.py**

```python
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Enum as SAEnum, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
import enum

class VehicleStatus(str, enum.Enum):
    in_factory = "in_factory"
    out = "out"
    unknown = "unknown"

class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    factory_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("factories.id"))
    plate_number: Mapped[str] = mapped_column(String(20), index=True)
    vehicle_type: Mapped[str] = mapped_column(String(50), default="truck")
    company: Mapped[str | None] = mapped_column(String(100))
    contact_name: Mapped[str | None] = mapped_column(String(50))
    contact_phone: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[VehicleStatus] = mapped_column(SAEnum(VehicleStatus), default=VehicleStatus.unknown)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [ ] **Step 4: 创建 backend/app/models/location.py**

```python
import uuid
from sqlalchemy import String, Boolean, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
import enum

class LocationType(str, enum.Enum):
    gate = "gate"
    checkpoint = "checkpoint"

class Location(Base):
    __tablename__ = "locations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    factory_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("factories.id"))
    name: Mapped[str] = mapped_column(String(100))
    type: Mapped[LocationType] = mapped_column(SAEnum(LocationType), default=LocationType.gate)
    camera_ip: Mapped[str | None] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
```

- [ ] **Step 5: 创建 backend/app/models/gate_event.py**

```python
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Float, Boolean, ForeignKey, Enum as SAEnum, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
import enum

class ReviewStatus(str, enum.Enum):
    auto_confirmed = "auto_confirmed"
    pending_review = "pending_review"
    manually_confirmed = "manually_confirmed"
    rejected = "rejected"

class Direction(str, enum.Enum):
    entry = "entry"
    exit = "exit"

class GateEvent(Base):
    __tablename__ = "gate_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    factory_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("factories.id"))
    gate_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("locations.id"), nullable=True)
    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    plate_number: Mapped[str] = mapped_column(String(20), index=True)
    direction: Mapped[Direction] = mapped_column(SAEnum(Direction))
    captured_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    image_url: Mapped[str | None] = mapped_column(String(500))
    confidence_score: Mapped[float | None] = mapped_column(Float)
    review_status: Mapped[ReviewStatus] = mapped_column(SAEnum(ReviewStatus), default=ReviewStatus.pending_review)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_manual: Mapped[bool] = mapped_column(Boolean, default=False)
```

- [ ] **Step 6: 创建 backend/app/models/alert.py**

```python
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, ForeignKey, Enum as SAEnum, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
import enum

class AlertType(str, enum.Enum):
    long_stay = "long_stay"
    pending_review = "pending_review"

class AlertSeverity(str, enum.Enum):
    info = "info"
    warning = "warning"
    critical = "critical"

class AlertStatus(str, enum.Enum):
    active = "active"
    resolved = "resolved"

class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    factory_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("factories.id"))
    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    type: Mapped[AlertType] = mapped_column(SAEnum(AlertType))
    message: Mapped[str] = mapped_column(Text)
    severity: Mapped[AlertSeverity] = mapped_column(SAEnum(AlertSeverity), default=AlertSeverity.warning)
    status: Mapped[AlertStatus] = mapped_column(SAEnum(AlertStatus), default=AlertStatus.active)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    note: Mapped[str | None] = mapped_column(Text)
```

- [ ] **Step 7: 初始化 Alembic**

```bash
cd backend
docker compose run --rm backend alembic init alembic
```

- [ ] **Step 8: 配置 alembic/env.py — 替换 target_metadata 段**

在 `alembic/env.py` 中找到 `target_metadata = None`，替换为：

```python
from app.models.factory import Factory
from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.location import Location
from app.models.gate_event import GateEvent
from app.models.alert import Alert
from app.database import Base
target_metadata = Base.metadata
```

同时将 `run_migrations_offline` 中的 `url = config.get_main_option("sqlalchemy.url")` 替换为：

```python
from app.config import settings
url = settings.database_url.replace("+asyncpg", "")  # alembic uses sync driver
```

对 `run_migrations_online` 做同样的 URL 替换，并用同步 engine：

```python
from sqlalchemy import engine_from_config, pool
from app.config import settings

configuration = config.get_section(config.config_ini_section, {})
configuration["sqlalchemy.url"] = settings.database_url.replace("+asyncpg", "+psycopg2")
connectable = engine_from_config(configuration, prefix="sqlalchemy.", poolclass=pool.NullPool)
```

- [ ] **Step 9: 生成并执行迁移**

```bash
docker compose run --rm backend alembic revision --autogenerate -m "initial schema"
docker compose run --rm backend alembic upgrade head
```

Expected: 6张表创建成功，无报错

- [ ] **Step 10: Commit**

```bash
git add backend/app/models/ backend/alembic/ backend/alembic.ini
git commit -m "feat: add database models and initial migration"
```

---

## Task 4: 认证服务（JWT + 依赖注入）

**Files:**
- Create: `backend/app/services/auth.py`
- Create: `backend/app/deps.py`
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/routers/auth.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_auth.py`

- [ ] **Step 1: 创建 backend/app/services/auth.py**

```python
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(user_id: str, role: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": user_id, "role": role, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except JWTError:
        raise ValueError("Invalid token")
```

- [ ] **Step 2: 创建 backend/app/schemas/auth.py**

```python
import uuid
from pydantic import BaseModel
from app.models.user import UserRole

class LoginRequest(BaseModel):
    phone: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserOut(BaseModel):
    id: uuid.UUID
    name: str
    phone: str
    role: UserRole
    factory_id: uuid.UUID | None

    model_config = {"from_attributes": True}
```

- [ ] **Step 3: 创建 backend/app/deps.py**

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User, UserRole
from app.services.auth import decode_token

bearer = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_token(credentials.credentials)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    result = await db.execute(select(User).where(User.id == uuid.UUID(payload["sub"]), User.is_active == True))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

def require_roles(*roles: UserRole):
    async def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user
    return checker
```

- [ ] **Step 4: 创建 backend/app/routers/auth.py**

```python
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserOut
from app.services.auth import verify_password, create_access_token
from app.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.phone == body.phone, User.is_active == True))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    user.last_login = datetime.utcnow()
    await db.commit()
    return TokenResponse(access_token=create_access_token(str(user.id), user.role.value))

@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user
```

- [ ] **Step 5: 注册路由到 main.py**

在 `backend/app/main.py` 中添加：

```python
from app.routers import auth

app.include_router(auth.router)
```

- [ ] **Step 6: 创建 backend/tests/conftest.py**

```python
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.main import app
from app.database import Base, get_db
from app.models.user import User, UserRole
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
```

- [ ] **Step 7: 创建 backend/tests/test_auth.py**

```python
import pytest

@pytest.mark.asyncio
async def test_login_success(client, operator_user):
    resp = await client.post("/auth/login", json={"phone": "13800000001", "password": "password123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()

@pytest.mark.asyncio
async def test_login_wrong_password(client, operator_user):
    resp = await client.post("/auth/login", json={"phone": "13800000001", "password": "wrong"})
    assert resp.status_code == 401

@pytest.mark.asyncio
async def test_me_requires_auth(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 403

@pytest.mark.asyncio
async def test_me_returns_user(client, operator_user):
    login = await client.post("/auth/login", json={"phone": "13800000001", "password": "password123"})
    token = login.json()["access_token"]
    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["phone"] == "13800000001"
```

- [ ] **Step 8: 运行测试**

```bash
docker compose run --rm backend pytest tests/test_auth.py -v
```

Expected: 4 passed

- [ ] **Step 9: 插入初始管理员账号**

```bash
docker compose run --rm backend python -c "
import asyncio
from app.database import AsyncSessionLocal
from app.models.user import User, UserRole
from app.services.auth import hash_password
import uuid

async def create_admin():
    async with AsyncSessionLocal() as db:
        user = User(
            id=uuid.uuid4(),
            name='超级管理员',
            phone='13900000000',
            password_hash=hash_password('admin123456'),
            role=UserRole.group_admin,
        )
        db.add(user)
        await db.commit()
        print('Admin created: 13900000000 / admin123456')

asyncio.run(create_admin())
"
```

- [ ] **Step 10: Commit**

```bash
git add backend/app/services/ backend/app/schemas/ backend/app/routers/ backend/app/deps.py backend/tests/
git commit -m "feat: add JWT auth, login endpoint, role-based deps"
```

---

## Task 5: 车辆管理 API

**Files:**
- Create: `backend/app/schemas/vehicle.py`
- Create: `backend/app/routers/vehicles.py`
- Create: `backend/tests/test_vehicles.py`

- [ ] **Step 1: 创建 backend/app/schemas/vehicle.py**

```python
import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.vehicle import VehicleStatus

class VehicleCreate(BaseModel):
    plate_number: str
    vehicle_type: str = "truck"
    company: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    note: str | None = None

class VehicleUpdate(BaseModel):
    vehicle_type: str | None = None
    company: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    note: str | None = None

class VehicleOut(BaseModel):
    id: uuid.UUID
    factory_id: uuid.UUID
    plate_number: str
    vehicle_type: str
    company: str | None
    contact_name: str | None
    contact_phone: str | None
    status: VehicleStatus
    last_seen_at: datetime | None
    note: str | None

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: 创建 backend/app/routers/vehicles.py**

```python
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.vehicle import Vehicle
from app.models.user import User, UserRole
from app.schemas.vehicle import VehicleCreate, VehicleUpdate, VehicleOut
from app.deps import get_current_user, require_roles

router = APIRouter(prefix="/vehicles", tags=["vehicles"])

@router.get("", response_model=list[VehicleOut])
async def list_vehicles(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Vehicle).where(Vehicle.factory_id == user.factory_id))
    return result.scalars().all()

@router.post("", response_model=VehicleOut)
async def create_vehicle(
    body: VehicleCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.factory_manager, UserRole.group_admin)),
):
    vehicle = Vehicle(**body.model_dump(), factory_id=user.factory_id)
    db.add(vehicle)
    await db.commit()
    await db.refresh(vehicle)
    return vehicle

@router.patch("/{vehicle_id}", response_model=VehicleOut)
async def update_vehicle(
    vehicle_id: uuid.UUID,
    body: VehicleUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.factory_manager, UserRole.group_admin)),
):
    result = await db.execute(select(Vehicle).where(Vehicle.id == vehicle_id, Vehicle.factory_id == user.factory_id))
    vehicle = result.scalar_one_or_none()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(vehicle, k, v)
    await db.commit()
    await db.refresh(vehicle)
    return vehicle
```

- [ ] **Step 3: 注册路由到 main.py**

```python
from app.routers import auth, vehicles
app.include_router(vehicles.router)
```

- [ ] **Step 4: 创建 backend/tests/test_vehicles.py**

```python
import pytest

@pytest.mark.asyncio
async def test_list_vehicles_requires_auth(client):
    resp = await client.get("/vehicles")
    assert resp.status_code == 403

@pytest.mark.asyncio
async def test_create_vehicle_requires_manager(client, operator_user):
    login = await client.post("/auth/login", json={"phone": "13800000001", "password": "password123"})
    token = login.json()["access_token"]
    resp = await client.post("/vehicles", json={"plate_number": "沪A12345"}, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403

@pytest.mark.asyncio
async def test_list_vehicles_empty(client, operator_user):
    login = await client.post("/auth/login", json={"phone": "13800000001", "password": "password123"})
    token = login.json()["access_token"]
    resp = await client.get("/vehicles", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == []
```

- [ ] **Step 5: 运行测试**

```bash
docker compose run --rm backend pytest tests/test_vehicles.py -v
```

Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/vehicle.py backend/app/routers/vehicles.py backend/tests/test_vehicles.py
git commit -m "feat: add vehicles CRUD API"
```

---

## Task 6: 出入记录 API + 车辆状态更新

**Files:**
- Create: `backend/app/schemas/gate_event.py`
- Create: `backend/app/services/vehicle_status.py`
- Create: `backend/app/routers/gate_events.py`
- Create: `backend/tests/test_gate_events.py`

- [ ] **Step 1: 创建 backend/app/services/vehicle_status.py**

```python
import redis.asyncio as aioredis
from app.config import settings

_redis: aioredis.Redis | None = None

def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis

async def set_vehicle_status(factory_id: str, plate: str, status: str):
    r = get_redis()
    await r.hset(f"factory:{factory_id}:vehicles", plate, status)

async def get_all_vehicle_statuses(factory_id: str) -> dict:
    r = get_redis()
    return await r.hgetall(f"factory:{factory_id}:vehicles")
```

- [ ] **Step 2: 创建 backend/app/schemas/gate_event.py**

```python
import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.gate_event import Direction, ReviewStatus

class GateEventCreate(BaseModel):
    factory_id: uuid.UUID
    gate_id: uuid.UUID | None = None
    plate_number: str
    direction: Direction
    image_url: str | None = None
    confidence_score: float | None = None

class ReviewRequest(BaseModel):
    plate_number: str  # corrected plate if needed
    action: str  # "confirm" or "reject"

class GateEventOut(BaseModel):
    id: uuid.UUID
    factory_id: uuid.UUID
    plate_number: str
    direction: Direction
    captured_at: datetime
    image_url: str | None
    confidence_score: float | None
    review_status: ReviewStatus
    is_manual: bool

    model_config = {"from_attributes": True}
```

- [ ] **Step 3: 创建 backend/app/routers/gate_events.py**

```python
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database import get_db
from app.models.gate_event import GateEvent, ReviewStatus
from app.models.vehicle import Vehicle, VehicleStatus
from app.models.user import User, UserRole
from app.schemas.gate_event import GateEventCreate, GateEventOut, ReviewRequest
from app.services.vehicle_status import set_vehicle_status
from app.deps import get_current_user, require_roles
from app.config import settings

router = APIRouter(prefix="/gate-events", tags=["gate-events"])

@router.get("", response_model=list[GateEventOut])
async def list_gate_events(
    plate: str | None = Query(None),
    direction: str | None = Query(None),
    review_status: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(GateEvent).where(GateEvent.factory_id == user.factory_id)
    if plate:
        q = q.where(GateEvent.plate_number.ilike(f"%{plate}%"))
    if direction:
        q = q.where(GateEvent.direction == direction)
    if review_status:
        q = q.where(GateEvent.review_status == review_status)
    q = q.order_by(desc(GateEvent.captured_at)).offset(offset).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()

@router.post("", response_model=GateEventOut)
async def create_gate_event(
    body: GateEventCreate,
    db: AsyncSession = Depends(get_db),
):
    # Called by AI service — no auth required (internal network only)
    review_status = (
        ReviewStatus.auto_confirmed
        if (body.confidence_score or 0) >= settings.ai_confidence_threshold
        else ReviewStatus.pending_review
    )
    event = GateEvent(**body.model_dump(), review_status=review_status)

    # Link to vehicle if exists
    result = await db.execute(
        select(Vehicle).where(Vehicle.plate_number == body.plate_number, Vehicle.factory_id == body.factory_id)
    )
    vehicle = result.scalar_one_or_none()
    if vehicle:
        event.vehicle_id = vehicle.id
        new_status = VehicleStatus.in_factory if body.direction.value == "entry" else VehicleStatus.out
        vehicle.status = new_status
        vehicle.last_seen_at = datetime.utcnow()
        await set_vehicle_status(str(body.factory_id), body.plate_number, new_status.value)

    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event

@router.patch("/{event_id}/review", response_model=GateEventOut)
async def review_gate_event(
    event_id: uuid.UUID,
    body: ReviewRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.operator, UserRole.factory_manager, UserRole.group_admin)),
):
    result = await db.execute(select(GateEvent).where(GateEvent.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    event.plate_number = body.plate_number
    event.review_status = ReviewStatus.manually_confirmed if body.action == "confirm" else ReviewStatus.rejected
    event.reviewed_by = user.id
    event.reviewed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(event)
    return event
```

- [ ] **Step 4: 注册路由**

```python
from app.routers import auth, vehicles, gate_events
app.include_router(gate_events.router)
```

- [ ] **Step 5: 创建 backend/tests/test_gate_events.py**

```python
import pytest
import uuid

@pytest.mark.asyncio
async def test_create_gate_event_high_confidence(client, operator_user):
    resp = await client.post("/gate-events", json={
        "factory_id": str(operator_user.factory_id),
        "plate_number": "沪A12345",
        "direction": "entry",
        "confidence_score": 0.95,
    })
    assert resp.status_code == 200
    assert resp.json()["review_status"] == "auto_confirmed"

@pytest.mark.asyncio
async def test_create_gate_event_low_confidence(client, operator_user):
    resp = await client.post("/gate-events", json={
        "factory_id": str(operator_user.factory_id),
        "plate_number": "粤B00000",
        "direction": "entry",
        "confidence_score": 0.60,
    })
    assert resp.status_code == 200
    assert resp.json()["review_status"] == "pending_review"

@pytest.mark.asyncio
async def test_review_event(client, operator_user):
    create = await client.post("/gate-events", json={
        "factory_id": str(operator_user.factory_id),
        "plate_number": "京C11111",
        "direction": "exit",
        "confidence_score": 0.50,
    })
    event_id = create.json()["id"]
    login = await client.post("/auth/login", json={"phone": "13800000001", "password": "password123"})
    token = login.json()["access_token"]
    resp = await client.patch(f"/gate-events/{event_id}/review",
        json={"plate_number": "京C11111", "action": "confirm"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["review_status"] == "manually_confirmed"
```

- [ ] **Step 6: 运行测试**

```bash
docker compose run --rm backend pytest tests/test_gate_events.py -v
```

Expected: 3 passed

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/gate_event.py backend/app/services/vehicle_status.py backend/app/routers/gate_events.py backend/tests/test_gate_events.py
git commit -m "feat: add gate events API with vehicle status tracking"
```

---

## Task 7: 报警引擎 + 报警 API

**Files:**
- Create: `backend/app/schemas/alert.py`
- Create: `backend/app/services/alert_engine.py`
- Create: `backend/app/routers/alerts.py`
- Create: `backend/tests/test_alerts.py`

- [ ] **Step 1: 创建 backend/app/schemas/alert.py**

```python
import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.alert import AlertType, AlertSeverity, AlertStatus

class AlertOut(BaseModel):
    id: uuid.UUID
    factory_id: uuid.UUID
    vehicle_id: uuid.UUID | None
    type: AlertType
    message: str
    severity: AlertSeverity
    status: AlertStatus
    created_at: datetime
    resolved_at: datetime | None
    note: str | None

    model_config = {"from_attributes": True}

class ResolveRequest(BaseModel):
    note: str | None = None
```

- [ ] **Step 2: 创建 backend/app/services/alert_engine.py**

```python
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.vehicle import Vehicle, VehicleStatus
from app.models.alert import Alert, AlertType, AlertSeverity, AlertStatus
from app.models.gate_event import GateEvent, ReviewStatus
from app.config import settings

async def check_long_stay(db: AsyncSession, factory_id) -> list[Alert]:
    """Create long_stay alerts for vehicles in factory beyond threshold."""
    threshold = datetime.utcnow() - timedelta(hours=settings.long_stay_hours)
    result = await db.execute(
        select(Vehicle).where(
            Vehicle.factory_id == factory_id,
            Vehicle.status == VehicleStatus.in_factory,
            Vehicle.last_seen_at <= threshold,
        )
    )
    vehicles = result.scalars().all()
    new_alerts = []
    for v in vehicles:
        # Check no existing active alert for this vehicle
        existing = await db.execute(
            select(Alert).where(
                Alert.vehicle_id == v.id,
                Alert.type == AlertType.long_stay,
                Alert.status == AlertStatus.active,
            )
        )
        if existing.scalar_one_or_none():
            continue
        alert = Alert(
            factory_id=factory_id,
            vehicle_id=v.id,
            type=AlertType.long_stay,
            message=f"车辆 {v.plate_number} 已在厂超过 {settings.long_stay_hours} 小时",
            severity=AlertSeverity.warning,
        )
        db.add(alert)
        new_alerts.append(alert)
    if new_alerts:
        await db.commit()
    return new_alerts

async def create_pending_review_alert(db: AsyncSession, factory_id, plate_number: str, event_id) -> Alert:
    alert = Alert(
        factory_id=factory_id,
        type=AlertType.pending_review,
        message=f"车牌识别置信度不足，需人工审核：{plate_number}",
        severity=AlertSeverity.info,
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert
```

- [ ] **Step 3: 在 gate_events.py 中触发 pending_review 报警**

在 `create_gate_event` 函数中，`db.add(event)` 之后添加：

```python
from app.services.alert_engine import create_pending_review_alert

    if review_status == ReviewStatus.pending_review:
        await create_pending_review_alert(db, body.factory_id, body.plate_number, event.id)
```

- [ ] **Step 4: 创建 backend/app/routers/alerts.py**

```python
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database import get_db
from app.models.alert import Alert, AlertStatus
from app.models.user import User
from app.schemas.alert import AlertOut, ResolveRequest
from app.deps import get_current_user

router = APIRouter(prefix="/alerts", tags=["alerts"])

@router.get("", response_model=list[AlertOut])
async def list_alerts(
    status: str | None = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(Alert).where(Alert.factory_id == user.factory_id)
    if status:
        q = q.where(Alert.status == status)
    q = q.order_by(desc(Alert.created_at)).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()

@router.patch("/{alert_id}/resolve", response_model=AlertOut)
async def resolve_alert(
    alert_id: uuid.UUID,
    body: ResolveRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id, Alert.factory_id == user.factory_id))
    alert = result.scalar_one_or_none()
    if not alert:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.status = AlertStatus.resolved
    alert.resolved_by = user.id
    alert.resolved_at = datetime.utcnow()
    alert.note = body.note
    await db.commit()
    await db.refresh(alert)
    return alert
```

- [ ] **Step 5: 注册路由**

```python
from app.routers import auth, vehicles, gate_events, alerts
app.include_router(alerts.router)
```

- [ ] **Step 6: 创建 backend/tests/test_alerts.py**

```python
import pytest

@pytest.mark.asyncio
async def test_low_confidence_creates_alert(client, operator_user):
    await client.post("/gate-events", json={
        "factory_id": str(operator_user.factory_id),
        "plate_number": "粤B99999",
        "direction": "entry",
        "confidence_score": 0.50,
    })
    login = await client.post("/auth/login", json={"phone": "13800000001", "password": "password123"})
    token = login.json()["access_token"]
    resp = await client.get("/alerts?status=active", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    alerts = resp.json()
    assert len(alerts) == 1
    assert alerts[0]["type"] == "pending_review"

@pytest.mark.asyncio
async def test_resolve_alert(client, operator_user):
    await client.post("/gate-events", json={
        "factory_id": str(operator_user.factory_id),
        "plate_number": "苏C55555",
        "direction": "entry",
        "confidence_score": 0.40,
    })
    login = await client.post("/auth/login", json={"phone": "13800000001", "password": "password123"})
    token = login.json()["access_token"]
    alerts_resp = await client.get("/alerts?status=active", headers={"Authorization": f"Bearer {token}"})
    alert_id = alerts_resp.json()[0]["id"]
    resp = await client.patch(f"/alerts/{alert_id}/resolve",
        json={"note": "已人工确认"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"
```

- [ ] **Step 7: 运行全部测试**

```bash
docker compose run --rm backend pytest tests/ -v
```

Expected: 全部 passed

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas/alert.py backend/app/services/alert_engine.py backend/app/routers/alerts.py backend/tests/test_alerts.py
git commit -m "feat: add alert engine and alerts API"
```

---

## Task 8: Dashboard API + WebSocket

**Files:**
- Create: `backend/app/schemas/dashboard.py`
- Create: `backend/app/routers/dashboard.py`
- Create: `backend/app/ws/manager.py`

- [ ] **Step 1: 创建 backend/app/ws/manager.py**

```python
from fastapi import WebSocket
from collections import defaultdict
import json

class ConnectionManager:
    def __init__(self):
        self.connections: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, factory_id: str, ws: WebSocket):
        await ws.accept()
        self.connections[factory_id].append(ws)

    def disconnect(self, factory_id: str, ws: WebSocket):
        self.connections[factory_id].remove(ws)

    async def broadcast(self, factory_id: str, data: dict):
        message = json.dumps(data)
        dead = []
        for ws in self.connections[factory_id]:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.connections[factory_id].remove(ws)

manager = ConnectionManager()
```

- [ ] **Step 2: 创建 backend/app/schemas/dashboard.py**

```python
from pydantic import BaseModel

class DashboardStats(BaseModel):
    vehicles_in_factory: int
    entries_today: int
    exits_today: int
    pending_review_count: int
    active_alerts_count: int
```

- [ ] **Step 3: 创建 backend/app/routers/dashboard.py**

```python
from datetime import datetime, date
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.vehicle import Vehicle, VehicleStatus
from app.models.gate_event import GateEvent, ReviewStatus, Direction
from app.models.alert import Alert, AlertStatus
from app.models.user import User
from app.schemas.dashboard import DashboardStats
from app.deps import get_current_user
from app.ws.manager import manager

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/stats", response_model=DashboardStats)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    fid = user.factory_id
    today = datetime.combine(date.today(), datetime.min.time())

    in_factory = await db.scalar(select(func.count()).select_from(Vehicle).where(
        Vehicle.factory_id == fid, Vehicle.status == VehicleStatus.in_factory))

    entries = await db.scalar(select(func.count()).select_from(GateEvent).where(
        GateEvent.factory_id == fid, GateEvent.direction == Direction.entry, GateEvent.captured_at >= today))

    exits = await db.scalar(select(func.count()).select_from(GateEvent).where(
        GateEvent.factory_id == fid, GateEvent.direction == Direction.exit, GateEvent.captured_at >= today))

    pending = await db.scalar(select(func.count()).select_from(GateEvent).where(
        GateEvent.factory_id == fid, GateEvent.review_status == ReviewStatus.pending_review))

    active_alerts = await db.scalar(select(func.count()).select_from(Alert).where(
        Alert.factory_id == fid, Alert.status == AlertStatus.active))

    return DashboardStats(
        vehicles_in_factory=in_factory or 0,
        entries_today=entries or 0,
        exits_today=exits or 0,
        pending_review_count=pending or 0,
        active_alerts_count=active_alerts or 0,
    )

@router.websocket("/ws/{factory_id}")
async def websocket_endpoint(factory_id: str, websocket: WebSocket):
    await manager.connect(factory_id, websocket)
    try:
        while True:
            await websocket.receive_text()  # keep alive
    except WebSocketDisconnect:
        manager.disconnect(factory_id, websocket)
```

- [ ] **Step 4: 注册路由**

```python
from app.routers import auth, vehicles, gate_events, alerts, dashboard
app.include_router(dashboard.router)
```

- [ ] **Step 5: 在 gate_events.py 中广播 WebSocket 事件**

在 `create_gate_event` 的 `db.commit()` 之后添加：

```python
from app.ws.manager import manager
import asyncio

    asyncio.create_task(manager.broadcast(str(body.factory_id), {
        "type": "gate_event",
        "plate_number": body.plate_number,
        "direction": body.direction.value,
        "review_status": review_status.value,
    }))
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/dashboard.py backend/app/routers/dashboard.py backend/app/ws/
git commit -m "feat: add dashboard stats API and WebSocket live push"
```

---

## Task 9: AI 识别服务（PaddleOCR）

**Files:**
- Create: `ai-service/recognizer.py`
- Create: `ai-service/main.py`
- Create: `ai-service/Dockerfile`
- Create: `ai-service/tests/test_recognizer.py`

- [ ] **Step 1: 创建 ai-service/recognizer.py**

```python
import cv2
import numpy as np
from paddleocr import PaddleOCR

_ocr = None

def get_ocr() -> PaddleOCR:
    global _ocr
    if _ocr is None:
        _ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
    return _ocr

def recognize_plate(image_bytes: bytes) -> tuple[str, float]:
    """
    Returns (plate_number, confidence_score).
    plate_number is empty string if nothing detected.
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return "", 0.0

    ocr = get_ocr()
    result = ocr.ocr(img, cls=True)
    if not result or not result[0]:
        return "", 0.0

    # Collect all text lines, pick highest confidence
    best_text = ""
    best_score = 0.0
    for line in result[0]:
        text, score = line[1]
        if score > best_score:
            best_text = text
            best_score = score

    return best_text.replace(" ", ""), best_score
```

- [ ] **Step 2: 创建 ai-service/main.py**

```python
import httpx
import uuid
from fastapi import FastAPI, UploadFile, File, Form
from recognizer import recognize_plate
import os

app = FastAPI(title="AI Recognition Service")

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/recognize")
async def recognize(
    file: UploadFile = File(...),
    factory_id: str = Form(...),
    gate_id: str = Form(None),
    direction: str = Form(...),
):
    image_bytes = await file.read()
    plate, confidence = recognize_plate(image_bytes)

    if not plate:
        return {"plate_number": None, "confidence": 0.0, "event_id": None}

    # Save image to MinIO (simplified: skip in MVP, store URL as empty)
    image_url = None

    # Post to backend
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{BACKEND_URL}/gate-events", json={
            "factory_id": factory_id,
            "gate_id": gate_id,
            "plate_number": plate,
            "direction": direction,
            "image_url": image_url,
            "confidence_score": confidence,
        })
        event_id = resp.json().get("id") if resp.status_code == 200 else None

    return {"plate_number": plate, "confidence": confidence, "event_id": event_id}
```

- [ ] **Step 3: 创建 ai-service/Dockerfile**

```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
```

- [ ] **Step 4: 创建 ai-service/tests/test_recognizer.py**

```python
import pytest
from recognizer import recognize_plate
import numpy as np
import cv2

def make_blank_image() -> bytes:
    img = np.zeros((100, 300, 3), dtype=np.uint8)
    _, buf = cv2.imencode(".jpg", img)
    return buf.tobytes()

def test_blank_image_returns_empty():
    plate, score = recognize_plate(make_blank_image())
    assert plate == ""
    assert score == 0.0

def test_invalid_bytes_returns_empty():
    plate, score = recognize_plate(b"not an image")
    assert plate == ""
    assert score == 0.0
```

- [ ] **Step 5: 运行 AI 服务测试**

```bash
docker compose run --rm ai-service pytest tests/ -v
```

Expected: 2 passed

- [ ] **Step 6: 验证 AI 服务健康检查**

```bash
docker compose up ai-service -d
curl http://localhost:8001/health
```

Expected: `{"status":"ok"}`

- [ ] **Step 7: Commit**

```bash
git add ai-service/
git commit -m "feat: add AI plate recognition service (PaddleOCR)"
```

---

## Task 10: 前端基础框架

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/src/types/index.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/store/auth.ts`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/main.tsx`

- [ ] **Step 1: 初始化前端项目**

```bash
cd frontend
npm create vite@latest . -- --template react-ts
npm install antd @ant-design/icons axios zustand react-router-dom dayjs
```

- [ ] **Step 2: 创建 frontend/src/types/index.ts**

```typescript
export type UserRole = "group_admin" | "factory_manager" | "operator";

export interface User {
  id: string;
  name: string;
  phone: string;
  role: UserRole;
  factory_id: string | null;
}

export type Direction = "entry" | "exit";
export type ReviewStatus = "auto_confirmed" | "pending_review" | "manually_confirmed" | "rejected";
export type VehicleStatus = "in_factory" | "out" | "unknown";
export type AlertType = "long_stay" | "pending_review";
export type AlertStatus = "active" | "resolved";

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
```

- [ ] **Step 3: 创建 frontend/src/api/client.ts**

```typescript
import axios from "axios";

export const api = axios.create({
  baseURL: "http://localhost:8000",
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem("access_token");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);
```

- [ ] **Step 4: 创建 frontend/src/store/auth.ts**

```typescript
import { create } from "zustand";
import { User } from "../types";
import { api } from "../api/client";

interface AuthState {
  user: User | null;
  token: string | null;
  login: (phone: string, password: string) => Promise<void>;
  logout: () => void;
  fetchMe: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem("access_token"),

  login: async (phone, password) => {
    const resp = await api.post("/auth/login", { phone, password });
    const token = resp.data.access_token;
    localStorage.setItem("access_token", token);
    set({ token });
    const me = await api.get("/auth/me");
    set({ user: me.data });
  },

  logout: () => {
    localStorage.removeItem("access_token");
    set({ user: null, token: null });
  },

  fetchMe: async () => {
    try {
      const resp = await api.get("/auth/me");
      set({ user: resp.data });
    } catch {
      set({ user: null, token: null });
    }
  },
}));
```

- [ ] **Step 5: 创建 frontend/src/App.tsx**

```typescript
import { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Spin } from "antd";
import { useAuthStore } from "./store/auth";
import AppLayout from "./components/AppLayout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import GateEvents from "./pages/GateEvents";
import Vehicles from "./pages/Vehicles";
import Alerts from "./pages/Alerts";

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
        <Route path="/" element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
          <Route index element={<Dashboard />} />
          <Route path="gate-events" element={<GateEvents />} />
          <Route path="vehicles" element={<Vehicles />} />
          <Route path="alerts" element={<Alerts />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
```

- [ ] **Step 6: Commit**

```bash
git add frontend/
git commit -m "feat: add frontend base (Vite + React + Antd + Zustand + routing)"
```

---

## Task 11: 前端页面实现

**Files:**
- Create: `frontend/src/components/AppLayout.tsx`
- Create: `frontend/src/pages/Login.tsx`
- Create: `frontend/src/pages/Dashboard.tsx`
- Create: `frontend/src/pages/GateEvents.tsx`
- Create: `frontend/src/pages/Vehicles.tsx`
- Create: `frontend/src/pages/Alerts.tsx`

- [ ] **Step 1: 创建 frontend/src/components/AppLayout.tsx**

```typescript
import { Layout, Menu, Badge } from "antd";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import { DashboardOutlined, CarOutlined, AlertOutlined, SwapOutlined, LogoutOutlined } from "@ant-design/icons";
import { useAuthStore } from "../store/auth";

const { Sider, Content, Header } = Layout;

export default function AppLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuthStore();

  const menuItems = [
    { key: "/", icon: <DashboardOutlined />, label: "实时看板" },
    { key: "/gate-events", icon: <SwapOutlined />, label: "出入记录" },
    { key: "/vehicles", icon: <CarOutlined />, label: "车辆管理" },
    { key: "/alerts", icon: <AlertOutlined />, label: "报警中心" },
  ];

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider width={200} theme="dark">
        <div style={{ color: "#fff", padding: "16px", fontWeight: "bold", fontSize: 16 }}>
          🚛 车辆管理
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
        <Header style={{ background: "#fff", padding: "0 24px", display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid #f0f0f0" }}>
          <span style={{ color: "#475569" }}>{user?.name} · {user?.role}</span>
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

- [ ] **Step 2: 创建 frontend/src/pages/Login.tsx**

```typescript
import { Form, Input, Button, Card, message } from "antd";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/auth";

export default function Login() {
  const { login } = useAuthStore();
  const navigate = useNavigate();

  const onFinish = async (values: { phone: string; password: string }) => {
    try {
      await login(values.phone, values.password);
      navigate("/");
    } catch {
      message.error("手机号或密码错误");
    }
  };

  return (
    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh", background: "#f0f2f5" }}>
      <Card title="厂区车辆管理系统" style={{ width: 360 }}>
        <Form onFinish={onFinish} layout="vertical">
          <Form.Item name="phone" label="手机号" rules={[{ required: true }]}>
            <Input placeholder="请输入手机号" />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true }]}>
            <Input.Password placeholder="请输入密码" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block>登录</Button>
        </Form>
      </Card>
    </div>
  );
}
```

- [ ] **Step 3: 创建 frontend/src/pages/Dashboard.tsx**

```typescript
import { useEffect, useState } from "react";
import { Row, Col, Statistic, Card, Table, Tag } from "antd";
import { CarOutlined, ArrowUpOutlined, ArrowDownOutlined, AlertOutlined, ClockCircleOutlined } from "@ant-design/icons";
import { api } from "../api/client";
import { DashboardStats, GateEvent } from "../types";
import { useAuthStore } from "../store/auth";
import dayjs from "dayjs";

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentEvents, setRecentEvents] = useState<GateEvent[]>([]);
  const { user } = useAuthStore();

  const fetchData = async () => {
    const [statsRes, eventsRes] = await Promise.all([
      api.get("/dashboard/stats"),
      api.get("/gate-events?limit=10"),
    ]);
    setStats(statsRes.data);
    setRecentEvents(eventsRes.data);
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000);

    if (user?.factory_id) {
      const ws = new WebSocket(`ws://localhost:8000/dashboard/ws/${user.factory_id}`);
      ws.onmessage = () => fetchData();
      return () => { clearInterval(interval); ws.close(); };
    }
    return () => clearInterval(interval);
  }, [user]);

  const columns = [
    { title: "车牌", dataIndex: "plate_number", key: "plate_number" },
    { title: "方向", dataIndex: "direction", key: "direction", render: (d: string) =>
      <Tag color={d === "entry" ? "green" : "red"}>{d === "entry" ? "入场" : "出场"}</Tag> },
    { title: "时间", dataIndex: "captured_at", key: "captured_at", render: (t: string) => dayjs(t).format("HH:mm:ss") },
    { title: "状态", dataIndex: "review_status", key: "review_status", render: (s: string) =>
      s === "pending_review" ? <Tag color="orange">待审核</Tag> : <Tag color="blue">已确认</Tag> },
  ];

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={5}><Card><Statistic title="在厂车辆" value={stats?.vehicles_in_factory ?? "-"} prefix={<CarOutlined />} /></Card></Col>
        <Col span={5}><Card><Statistic title="今日入场" value={stats?.entries_today ?? "-"} prefix={<ArrowDownOutlined />} valueStyle={{ color: "#3f8600" }} /></Card></Col>
        <Col span={5}><Card><Statistic title="今日出场" value={stats?.exits_today ?? "-"} prefix={<ArrowUpOutlined />} valueStyle={{ color: "#cf1322" }} /></Card></Col>
        <Col span={5}><Card><Statistic title="待审核" value={stats?.pending_review_count ?? "-"} prefix={<ClockCircleOutlined />} valueStyle={{ color: "#fa8c16" }} /></Card></Col>
        <Col span={4}><Card><Statistic title="活跃报警" value={stats?.active_alerts_count ?? "-"} prefix={<AlertOutlined />} valueStyle={{ color: "#ff4d4f" }} /></Card></Col>
      </Row>
      <Card title="最近出入记录">
        <Table dataSource={recentEvents} columns={columns} rowKey="id" pagination={false} size="small" />
      </Card>
    </div>
  );
}
```

- [ ] **Step 4: 创建 frontend/src/pages/GateEvents.tsx**

```typescript
import { useEffect, useState } from "react";
import { Table, Tag, Button, Modal, Input, Select, Space, Image, Typography } from "antd";
import { api } from "../api/client";
import { GateEvent } from "../types";
import dayjs from "dayjs";

export default function GateEvents() {
  const [events, setEvents] = useState<GateEvent[]>([]);
  const [reviewing, setReviewing] = useState<GateEvent | null>(null);
  const [correctedPlate, setCorrectedPlate] = useState("");
  const [filterPlate, setFilterPlate] = useState("");
  const [filterStatus, setFilterStatus] = useState<string | undefined>();

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
    await api.patch(`/gate-events/${reviewing.id}/review`, { plate_number: correctedPlate, action });
    setReviewing(null);
    fetchEvents();
  };

  const columns = [
    { title: "车牌", dataIndex: "plate_number", key: "plate_number" },
    { title: "方向", dataIndex: "direction", key: "direction", render: (d: string) =>
      <Tag color={d === "entry" ? "green" : "red"}>{d === "entry" ? "入场" : "出场"}</Tag> },
    { title: "时间", dataIndex: "captured_at", key: "captured_at", render: (t: string) => dayjs(t).format("YYYY-MM-DD HH:mm:ss") },
    { title: "置信度", dataIndex: "confidence_score", key: "confidence_score", render: (s: number | null) =>
      s != null ? `${(s * 100).toFixed(1)}%` : "-" },
    { title: "状态", dataIndex: "review_status", key: "review_status", render: (s: string) => {
      const map: Record<string, [string, string]> = {
        auto_confirmed: ["已自动确认", "blue"],
        pending_review: ["待审核", "orange"],
        manually_confirmed: ["人工确认", "green"],
        rejected: ["已拒绝", "red"],
      };
      const [label, color] = map[s] || [s, "default"];
      return <Tag color={color}>{label}</Tag>;
    }},
    { title: "操作", key: "action", render: (_: unknown, record: GateEvent) =>
      record.review_status === "pending_review" ? (
        <Button size="small" type="link" onClick={() => { setReviewing(record); setCorrectedPlate(record.plate_number); }}>
          审核
        </Button>
      ) : null,
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Input.Search placeholder="车牌搜索" onSearch={setFilterPlate} allowClear style={{ width: 200 }} />
        <Select placeholder="审核状态" allowClear style={{ width: 160 }} onChange={setFilterStatus}>
          <Select.Option value="pending_review">待审核</Select.Option>
          <Select.Option value="auto_confirmed">自动确认</Select.Option>
          <Select.Option value="manually_confirmed">人工确认</Select.Option>
          <Select.Option value="rejected">已拒绝</Select.Option>
        </Select>
      </Space>
      <Table dataSource={events} columns={columns} rowKey="id" size="small"
        rowClassName={(r) => r.review_status === "pending_review" ? "ant-table-row-warning" : ""} />

      <Modal title="审核出入记录" open={!!reviewing} onCancel={() => setReviewing(null)}
        footer={[
          <Button key="reject" danger onClick={() => handleReview("reject")}>拒绝</Button>,
          <Button key="confirm" type="primary" onClick={() => handleReview("confirm")}>确认</Button>,
        ]}>
        {reviewing && (
          <div>
            <p>识别车牌：<Typography.Text code>{reviewing.plate_number}</Typography.Text></p>
            <p>置信度：{reviewing.confidence_score ? `${(reviewing.confidence_score * 100).toFixed(1)}%` : "-"}</p>
            <p>修正车牌：</p>
            <Input value={correctedPlate} onChange={(e) => setCorrectedPlate(e.target.value)} />
          </div>
        )}
      </Modal>
    </div>
  );
}
```

- [ ] **Step 5: 创建 frontend/src/pages/Vehicles.tsx**

```typescript
import { useEffect, useState } from "react";
import { Table, Tag, Button, Modal, Form, Input, message } from "antd";
import { api } from "../api/client";
import { Vehicle } from "../types";
import dayjs from "dayjs";

export default function Vehicles() {
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [adding, setAdding] = useState(false);
  const [form] = Form.useForm();

  const fetch = async () => {
    const resp = await api.get("/vehicles");
    setVehicles(resp.data);
  };
  useEffect(() => { fetch(); }, []);

  const handleAdd = async (values: Record<string, string>) => {
    await api.post("/vehicles", values);
    message.success("车辆已添加");
    setAdding(false);
    form.resetFields();
    fetch();
  };

  const statusMap: Record<string, [string, string]> = {
    in_factory: ["在厂", "green"],
    out: ["离厂", "default"],
    unknown: ["未知", "orange"],
  };

  const columns = [
    { title: "车牌", dataIndex: "plate_number", key: "plate_number" },
    { title: "类型", dataIndex: "vehicle_type", key: "vehicle_type" },
    { title: "所属公司", dataIndex: "company", key: "company", render: (v: string | null) => v || "-" },
    { title: "联系人", dataIndex: "contact_name", key: "contact_name", render: (v: string | null) => v || "-" },
    { title: "状态", dataIndex: "status", key: "status", render: (s: string) => {
      const [label, color] = statusMap[s] || [s, "default"];
      return <Tag color={color}>{label}</Tag>;
    }},
    { title: "最后记录", dataIndex: "last_seen_at", key: "last_seen_at",
      render: (t: string | null) => t ? dayjs(t).format("MM-DD HH:mm") : "-" },
  ];

  return (
    <div>
      <Button type="primary" style={{ marginBottom: 16 }} onClick={() => setAdding(true)}>添加车辆</Button>
      <Table dataSource={vehicles} columns={columns} rowKey="id" size="small" />
      <Modal title="添加车辆" open={adding} onCancel={() => setAdding(false)} onOk={() => form.submit()}>
        <Form form={form} onFinish={handleAdd} layout="vertical">
          <Form.Item name="plate_number" label="车牌号" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="vehicle_type" label="车辆类型"><Input placeholder="truck" /></Form.Item>
          <Form.Item name="company" label="所属公司"><Input /></Form.Item>
          <Form.Item name="contact_name" label="联系人"><Input /></Form.Item>
          <Form.Item name="contact_phone" label="联系电话"><Input /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
```

- [ ] **Step 6: 创建 frontend/src/pages/Alerts.tsx**

```typescript
import { useEffect, useState } from "react";
import { Table, Tag, Button, Modal, Input, message, Select, Space } from "antd";
import { api } from "../api/client";
import { Alert } from "../types";
import dayjs from "dayjs";

export default function Alerts() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [resolving, setResolving] = useState<Alert | null>(null);
  const [note, setNote] = useState("");
  const [statusFilter, setStatusFilter] = useState("active");

  const fetch = async () => {
    const resp = await api.get(`/alerts?status=${statusFilter}`);
    setAlerts(resp.data);
  };
  useEffect(() => { fetch(); }, [statusFilter]);

  const handleResolve = async () => {
    if (!resolving) return;
    await api.patch(`/alerts/${resolving.id}/resolve`, { note });
    message.success("已处理");
    setResolving(null);
    fetch();
  };

  const typeMap: Record<string, string> = { long_stay: "长时间未出场", pending_review: "需人工审核" };
  const severityColor: Record<string, string> = { info: "blue", warning: "orange", critical: "red" };

  const columns = [
    { title: "类型", dataIndex: "type", key: "type", render: (t: string) => typeMap[t] || t },
    { title: "内容", dataIndex: "message", key: "message" },
    { title: "级别", dataIndex: "severity", key: "severity", render: (s: string) => <Tag color={severityColor[s]}>{s}</Tag> },
    { title: "时间", dataIndex: "created_at", key: "created_at", render: (t: string) => dayjs(t).format("MM-DD HH:mm") },
    { title: "状态", dataIndex: "status", key: "status", render: (s: string) =>
      <Tag color={s === "active" ? "red" : "green"}>{s === "active" ? "待处理" : "已解决"}</Tag> },
    { title: "操作", key: "action", render: (_: unknown, record: Alert) =>
      record.status === "active" ? (
        <Button size="small" type="link" onClick={() => { setResolving(record); setNote(""); }}>处理</Button>
      ) : null },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Select value={statusFilter} onChange={setStatusFilter} style={{ width: 120 }}>
          <Select.Option value="active">待处理</Select.Option>
          <Select.Option value="resolved">已解决</Select.Option>
        </Select>
      </Space>
      <Table dataSource={alerts} columns={columns} rowKey="id" size="small" />
      <Modal title="处理报警" open={!!resolving} onCancel={() => setResolving(null)} onOk={handleResolve}>
        <p>{resolving?.message}</p>
        <Input.TextArea placeholder="处理备注（可选）" value={note} onChange={(e) => setNote(e.target.value)} rows={3} />
      </Modal>
    </div>
  );
}
```

- [ ] **Step 7: 添加后端 Excel 导出端点（backend/app/routers/gate_events.py 新增）**

先安装依赖，在 `backend/requirements.txt` 末尾追加：
```
openpyxl==3.1.2
```

在 `gate_events.py` 末尾添加：

```python
from fastapi.responses import StreamingResponse
import openpyxl
import io

@router.get("/export")
async def export_gate_events(
    plate: str | None = Query(None),
    direction: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(GateEvent).where(GateEvent.factory_id == user.factory_id)
    if plate:
        q = q.where(GateEvent.plate_number.ilike(f"%{plate}%"))
    if direction:
        q = q.where(GateEvent.direction == direction)
    q = q.order_by(desc(GateEvent.captured_at)).limit(10000)
    result = await db.execute(q)
    events = result.scalars().all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "出入记录"
    ws.append(["车牌", "方向", "出入口", "时间", "置信度", "审核状态"])
    for e in events:
        ws.append([
            e.plate_number,
            "入场" if e.direction.value == "entry" else "出场",
            str(e.gate_id) if e.gate_id else "",
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
        headers={"Content-Disposition": "attachment; filename=gate_events.xlsx"},
    )
```

在 `frontend/src/pages/GateEvents.tsx` 的 Space 组件里添加导出按钮：

```typescript
<Button onClick={() => window.open(`http://localhost:8000/gate-events/export?${new URLSearchParams({ ...(filterPlate ? { plate: filterPlate } : {}) }).toString()}`)}>
  导出 Excel
</Button>
```

- [ ] **Step 8: 启动前端验证**

```bash
docker compose up frontend -d
```

打开 http://localhost:5173，用 `13900000000 / admin123456` 登录，验证：
- 看板页面显示统计数字
- 导航栏可切换到各页面
- 出入记录页面可加载数据

- [ ] **Step 8: Commit**

```bash
git add frontend/src/
git commit -m "feat: add all frontend pages (dashboard, gate events, vehicles, alerts)"
```

---

## Task 12: 全系统验收测试

- [ ] **Step 1: 启动全部服务**

```bash
docker compose up -d
docker compose ps
```

Expected: 所有服务均为 running

- [ ] **Step 2: 运行后端全量测试**

```bash
docker compose run --rm backend pytest tests/ -v
```

Expected: 全部 passed

- [ ] **Step 3: 端到端手动验证**

1. 打开 http://localhost:5173，登录管理员账号
2. 看板页显示统计卡片（均为0）
3. 模拟 AI 服务上报一条高置信度入场记录：
```bash
curl -X POST http://localhost:8000/gate-events \
  -H "Content-Type: application/json" \
  -d '{"factory_id":"<your-factory-id>","plate_number":"沪A88888","direction":"entry","confidence_score":0.95}'
```
4. 看板自动刷新，在厂车辆数变为 1，今日入场 +1
5. 模拟一条低置信度记录：
```bash
curl -X POST http://localhost:8000/gate-events \
  -H "Content-Type: application/json" \
  -d '{"factory_id":"<your-factory-id>","plate_number":"粤X00000","direction":"entry","confidence_score":0.55}'
```
6. 出入记录页有一条橙色"待审核"记录，报警中心有一条 pending_review 报警
7. 点击"审核"确认车牌，状态变为 manually_confirmed
8. 报警中心处理报警，状态变为已解决

- [ ] **Step 4: 最终 Commit**

```bash
git add .
git commit -m "feat: vehicle tracking MVP complete — gate events, dashboard, alerts, AI service"
```
