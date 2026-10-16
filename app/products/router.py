import logging

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import Principal, require_admin, require_products_user
from app.database import get_session
from app.products import service
from app.products.schemas import ProductCreate, ProductPage, ProductRead

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/products", tags=["products"])


@router.get("", response_model=ProductPage)
async def list_products(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_products_user),
) -> ProductPage:
    items, total = await service.list_products(session, limit, offset)
    return ProductPage(items=items, total=total, limit=limit, offset=offset)


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreate,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_products_user),
) -> ProductRead:
    product = await service.create_product(session, data)
    logger.info(
        "product_created",
        extra={"actor": principal.username, "product_id": product.id},
    )
    return ProductRead.model_validate(product)


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(
    product_id: int,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_products_user),
) -> ProductRead:
    return ProductRead.model_validate(await service.get_product(session, product_id))


@router.put("/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: int,
    data: ProductCreate,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_products_user),
) -> ProductRead:
    product = await service.update_product(session, product_id, data)
    logger.info(
        "product_updated",
        extra={"actor": principal.username, "product_id": product.id},
    )
    return ProductRead.model_validate(product)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_products_user),
) -> Response:
    await service.delete_product(session, product_id)
    logger.info(
        "product_deleted",
        extra={"actor": principal.username, "product_id": product_id},
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/init")
async def init_products(
    response: Response,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_admin),
) -> dict[str, int | float | str]:
    from app.products.seed import initialize_products

    result = await initialize_products(session)
    response.status_code = (
        status.HTTP_201_CREATED if result["inserted"] else status.HTTP_200_OK
    )
    logger.warning(
        "product_seed_finished",
        extra={"actor": principal.username, **result},
    )
    return result

