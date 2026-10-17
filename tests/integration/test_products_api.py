from unittest.mock import AsyncMock

import pytest


@pytest.mark.asyncio
async def test_product_crud_and_pagination(client, product_payload):
    created = await client.post("/api/v1/products", json=product_payload)
    assert created.status_code == 201
    product = created.json()
    assert product["name"] == "Caderno"
    product_id = product["id"]
    assert product["created_at"]
    assert product["updated_at"]

    fetched = await client.get(f"/api/v1/products/{product_id}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == product_id

    listed = await client.get("/api/v1/products?limit=1&offset=0")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert len(listed.json()["items"]) == 1

    updated_payload = {**product_payload, "name": "Caderno atualizado"}
    updated = await client.put(f"/api/v1/products/{product_id}", json=updated_payload)
    assert updated.status_code == 200
    assert updated.json()["name"] == "Caderno atualizado"

    deleted = await client.delete(f"/api/v1/products/{product_id}")
    assert deleted.status_code == 204
    missing = await client.get(f"/api/v1/products/{product_id}")
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_product_field_limits_are_enforced(client, product_payload):
    too_long = {**product_payload, "description": "x" * 1001}
    response = await client.post("/api/v1/products", json=too_long)
    assert response.status_code == 422

    too_long_name = {**product_payload, "name": "x" * 257}
    response = await client.post("/api/v1/products", json=too_long_name)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_invalid_pagination_returns_validation_error(client):
    response = await client.get("/api/v1/products?limit=0")
    assert response.status_code == 422
    assert response.json()["detail"][0]["field"] == "query.limit"


@pytest.mark.asyncio
async def test_init_route_requires_admin_role(client):
    response = await client.post("/api/v1/products/init")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_init_route_returns_seed_result_for_admin(client, monkeypatch):
    from app.auth import Principal, require_admin
    from app.products import seed

    async def admin() -> Principal:
        return Principal("admin", "admin", frozenset({"products-admin"}))

    initialize = AsyncMock(
        return_value={
            "inserted": 10,
            "total": 10,
            "strategy": "bulk",
            "benchmark_seconds": 0.2,
        }
    )
    monkeypatch.setattr(seed, "initialize_products", initialize)
    from app.main import app

    app.dependency_overrides[require_admin] = admin
    response = await client.post("/api/v1/products/init")
    assert response.status_code == 201
    assert response.json()["inserted"] == 10
    initialize.assert_awaited_once()


@pytest.mark.asyncio
async def test_repeated_init_returns_ok_when_no_rows_are_added(client, monkeypatch):
    from app.auth import Principal, require_admin
    from app.main import app
    from app.products import seed

    async def admin() -> Principal:
        return Principal("admin", "admin", frozenset({"products-admin"}))

    initialize = AsyncMock(
        return_value={
            "inserted": 0,
            "total": 2_000_000,
            "strategy": "already_initialized",
            "benchmark_seconds": 0.0,
        }
    )
    monkeypatch.setattr(seed, "initialize_products", initialize)
    app.dependency_overrides[require_admin] = admin
    response = await client.post("/api/v1/products/init")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_alertmanager_webhook_records_firing_and_resolution(client):
    alert = {
        "fingerprint": "fingerprint-1",
        "status": "firing",
        "labels": {"alertname": "TestAlert"},
        "startsAt": "2026-10-16T12:00:00Z",
        "endsAt": "0001-01-01T00:00:00Z",
    }
    fired = await client.post("/internal/alertmanager", json={"alerts": [alert]})
    assert fired.status_code == 202
    assert fired.json()["processed"] == 1

    resolved = {**alert, "status": "resolved", "endsAt": "2026-10-16T12:02:00Z"}
    response = await client.post("/internal/alertmanager", json={"alerts": [resolved]})
    assert response.status_code == 202
    assert response.json()["processed"] == 1


@pytest.mark.asyncio
async def test_health_liveness_is_available_without_auth(client):
    response = await client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
