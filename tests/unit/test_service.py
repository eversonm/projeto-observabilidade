from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.products import service
from app.products.models import Product
from app.products.schemas import ProductCreate


@pytest.mark.asyncio
async def test_list_products_delegates_to_repository(monkeypatch):
    expected = ([Product(id=1, name="A", description="B", link="C")], 1)
    list_products = AsyncMock(return_value=expected)
    monkeypatch.setattr(service.repository, "list_products", list_products)
    result = await service.list_products(AsyncMock(), limit=10, offset=0)
    assert result == expected
    list_products.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_product_delegates_to_repository(monkeypatch):
    product = Product(id=1, name="A", description="B", link="C")
    create_product = AsyncMock(return_value=product)
    monkeypatch.setattr(service.repository, "create_product", create_product)
    data = ProductCreate(name="A", description="B", link="C")
    assert await service.create_product(AsyncMock(), data) is product
    create_product.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_product_returns_repository_result(monkeypatch):
    product = Product(id=1, name="A", description="B", link="C")
    get_product = AsyncMock(return_value=product)
    monkeypatch.setattr(service.repository, "get_product", get_product)
    assert await service.get_product(AsyncMock(), 1) is product


@pytest.mark.asyncio
async def test_update_product_loads_then_updates(monkeypatch):
    product = Product(id=1, name="A", description="B", link="C")
    get_product = AsyncMock(return_value=product)
    update_product = AsyncMock(return_value=product)
    monkeypatch.setattr(service.repository, "get_product", get_product)
    monkeypatch.setattr(service.repository, "update_product", update_product)
    data = ProductCreate(name="A2", description="B2", link="C2")
    assert await service.update_product(AsyncMock(), 1, data) is product
    update_product.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_product_loads_then_deletes(monkeypatch):
    product = Product(id=1, name="A", description="B", link="C")
    get_product = AsyncMock(return_value=product)
    delete_product = AsyncMock()
    monkeypatch.setattr(service.repository, "get_product", get_product)
    monkeypatch.setattr(service.repository, "delete_product", delete_product)
    await service.delete_product(AsyncMock(), 1)
    delete_product.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_missing_product_returns_404(monkeypatch):
    get_product = AsyncMock(return_value=None)
    monkeypatch.setattr(service.repository, "get_product", get_product)
    with pytest.raises(HTTPException) as error:
        await service.get_product(AsyncMock(), 999)
    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_missing_product_does_not_call_repository_delete(monkeypatch):
    get_product = AsyncMock(return_value=None)
    delete_product = AsyncMock()
    monkeypatch.setattr(service.repository, "get_product", get_product)
    monkeypatch.setattr(service.repository, "delete_product", delete_product)
    with pytest.raises(HTTPException):
        await service.delete_product(AsyncMock(), 999)
    delete_product.assert_not_awaited()
