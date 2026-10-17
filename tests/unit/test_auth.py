import pytest
from fastapi import HTTPException

from app.auth import (
    Principal,
    get_current_principal,
    require_admin,
    require_products_user,
)


@pytest.mark.asyncio
async def test_missing_bearer_token_returns_401():
    with pytest.raises(HTTPException) as error:
        await get_current_principal(None)
    assert error.value.status_code == 401


@pytest.mark.asyncio
async def test_non_admin_cannot_run_admin_action():
    with pytest.raises(HTTPException) as error:
        await require_admin(Principal("u", "user", frozenset({"products-user"})))
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_token_without_product_role_is_forbidden():
    with pytest.raises(HTTPException) as error:
        await require_products_user(Principal("u", "user", frozenset()))
    assert error.value.status_code == 403
