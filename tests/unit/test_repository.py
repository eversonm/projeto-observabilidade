import pytest

from app.products import repository
from app.products.schemas import ProductCreate


@pytest.mark.asyncio
async def test_repository_creates_and_reads_product(test_session_factory):
    async with test_session_factory() as session:
        created = await repository.create_product(
            session,
            ProductCreate(
                name="Produto unitário",
                description="Desc",
                link="https://example.org",
            ),
        )
        found = await repository.get_product(session, created.id)
        rows, total = await repository.list_products(session, 10, 0)
    assert found is not None
    assert found.name == "Produto unitário"
    assert total == 1
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_repository_deletes_product(test_session_factory):
    async with test_session_factory() as session:
        created = await repository.create_product(
            session, ProductCreate(name="X", description="Y", link="Z")
        )
        await repository.delete_product(session, created)
        assert await repository.get_product(session, created.id) is None


@pytest.mark.asyncio
async def test_repository_updates_product(test_session_factory):
    async with test_session_factory() as session:
        created = await repository.create_product(
            session, ProductCreate(name="Antes", description="Y", link="Z")
        )
        updated = await repository.update_product(
            session,
            created,
            ProductCreate(name="Depois", description="Y2", link="Z2"),
        )
        assert updated.name == "Depois"
        assert updated.description == "Y2"
        assert updated.link == "Z2"

