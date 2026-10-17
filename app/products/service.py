from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.products import repository
from app.products.models import Product
from app.products.schemas import ProductCreate


async def list_products(
    session: AsyncSession, limit: int, offset: int
) -> tuple[list[Product], int]:
    return await repository.list_products(session, limit, offset)


async def get_product(session: AsyncSession, product_id: int) -> Product:
    product = await repository.get_product(session, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado",
        )
    return product


async def create_product(session: AsyncSession, data: ProductCreate) -> Product:
    return await repository.create_product(session, data)


async def update_product(
    session: AsyncSession, product_id: int, data: ProductCreate
) -> Product:
    product = await get_product(session, product_id)
    return await repository.update_product(session, product, data)


async def delete_product(session: AsyncSession, product_id: int) -> None:
    product = await get_product(session, product_id)
    await repository.delete_product(session, product)
