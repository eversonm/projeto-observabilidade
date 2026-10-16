from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.products.models import Product
from app.products.schemas import ProductCreate


async def list_products(
    session: AsyncSession, limit: int, offset: int
) -> tuple[list[Product], int]:
    rows = await session.scalars(
        select(Product).order_by(Product.id).limit(limit).offset(offset)
    )
    total = await session.scalar(select(func.count()).select_from(Product))
    return list(rows), int(total or 0)


async def get_product(session: AsyncSession, product_id: int) -> Product | None:
    return await session.get(Product, product_id)


async def create_product(session: AsyncSession, data: ProductCreate) -> Product:
    product = Product(**data.model_dump())
    session.add(product)
    await session.commit()
    await session.refresh(product)
    return product


async def update_product(
    session: AsyncSession, product: Product, data: ProductCreate
) -> Product:
    for field, value in data.model_dump().items():
        setattr(product, field, value)
    await session.commit()
    await session.refresh(product)
    return product


async def delete_product(session: AsyncSession, product: Product) -> None:
    await session.delete(product)
    await session.commit()

