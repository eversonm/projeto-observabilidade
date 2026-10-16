import pytest

from app.auth import require_products_user
from app.main import app


@pytest.mark.asyncio
async def test_metrics_endpoint_is_exposed(client):
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert "products_http_requests_total" in response.text


@pytest.mark.asyncio
async def test_products_require_authentication(client):
    app.dependency_overrides.pop(require_products_user)
    response = await client.get("/api/v1/products")
    assert response.status_code == 401

