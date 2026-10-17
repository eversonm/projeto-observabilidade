from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth import Principal, require_admin, require_products_user
from app.database import get_session
from app.main import app
from app.products.models import Base


@pytest_asyncio.fixture
async def test_session_factory():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    yield factory
    await test_engine.dispose()


@pytest_asyncio.fixture
async def client(test_session_factory) -> AsyncGenerator[AsyncClient, None]:
    async def session_override() -> AsyncGenerator[AsyncSession, None]:
        async with test_session_factory() as session:
            yield session

    async def product_user() -> Principal:
        return Principal("user-123", "test-user", frozenset({"products-user"}))

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[require_products_user] = product_user
    app.dependency_overrides[require_admin] = product_user
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def product_payload() -> dict[str, str]:
    return {
        "name": "Caderno",
        "description": "Caderno universitário de 100 folhas",
        "link": "https://example.com/caderno",
    }
