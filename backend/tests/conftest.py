import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.main import app
from app.database import Base, get_db
from app.models.user import User, UserRole
from app.models import factory, vehicle, location, gate_event, alert, checkpoint, path_template, vehicle_journey, department, checkpoint_event  # noqa: F401
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
