import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import get_password_hash
from app.db.session import Base, get_db
from app.main import app
from app.models.models import Permission, RolePermission, User
from app.services.user_service import UserService

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db() -> AsyncGenerator[AsyncSession, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db: AsyncSession) -> User:
    service = UserService(db)
    await service.ensure_core_groups()
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpassword123"),
        full_name="Test User",
        is_active=True,
        is_approved=True,
    )
    db.add(user)
    await db.flush()
    user = await service.assign_groups(user, {"helfende"})
    await db.commit()
    return user


@pytest_asyncio.fixture
async def superuser(db: AsyncSession) -> User:
    service = UserService(db)
    await service.ensure_core_groups()
    user = User(
        email="admin@example.com",
        hashed_password=get_password_hash("adminpassword123"),
        full_name="Admin User",
        is_active=True,
        is_approved=True,
        is_superuser=True,
    )
    db.add(user)
    await db.flush()
    user = await service.assign_groups(user, {"helfende", "admin"})
    await db.commit()
    return user


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, test_user: User) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "testpassword123"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_headers(client: AsyncClient, superuser: User) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "adminpassword123"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def schirrmeister_headers(client: AsyncClient, db: AsyncSession) -> dict[str, str]:
    service = UserService(db)
    await service.ensure_core_groups()
    user = User(
        email="schirr@example.com",
        hashed_password=get_password_hash("schirrpassword123"),
        full_name="Schirrmeister User",
        is_active=True,
        is_approved=True,
    )
    db.add(user)
    await db.flush()
    await service.assign_groups(user, {"helfende", "schirrmeister"})

    # Ensure the schirrmeister group has the close_ticket permission
    from sqlalchemy import select
    schirr_group = await service.get_group_by_name("schirrmeister")
    assert schirr_group is not None
    perm_result = await db.execute(select(Permission).where(Permission.codename == "close_ticket"))
    perm = perm_result.scalar_one_or_none()
    if perm is None:
        perm = Permission(codename="close_ticket", description="Can close tickets")
        db.add(perm)
        await db.flush()
    existing_rp = await db.execute(
        select(RolePermission).where(
            RolePermission.role_id == schirr_group.id,
            RolePermission.permission_id == perm.id,
        )
    )
    if existing_rp.scalar_one_or_none() is None:
        db.add(RolePermission(role_id=schirr_group.id, permission_id=perm.id))
        await db.flush()

    await db.commit()

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "schirr@example.com", "password": "schirrpassword123"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
