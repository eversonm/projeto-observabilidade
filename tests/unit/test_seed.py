from unittest.mock import AsyncMock, MagicMock

import pytest

from app.products import seed


@pytest.mark.asyncio
async def test_seed_returns_without_insert_when_target_reached():
    session = AsyncMock()
    session.scalar.return_value = 10
    result = await seed.initialize_products(session, target_count=10)
    assert result["strategy"] == "already_initialized"
    assert result["inserted"] == 0
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_seed_uses_hybrid_after_fast_bulk_probe(monkeypatch):
    session = AsyncMock()
    session.add = MagicMock()
    session.scalar.return_value = 0
    savepoint = AsyncMock()
    session.begin_nested.return_value = savepoint
    monkeypatch.setattr(seed.time, "perf_counter", MagicMock(side_effect=[1.0, 2.0]))
    result = await seed.initialize_products(session, target_count=150)
    assert result["strategy"] == "hybrid"
    assert result["inserted"] == 150
    savepoint.rollback.assert_awaited_once()
    assert session.flush.await_count == seed.HYBRID_ROW_COUNT
    assert session.execute.await_count == 3


@pytest.mark.asyncio
async def test_seed_uses_bulk_after_slow_bulk_probe(monkeypatch):
    session = AsyncMock()
    session.scalar.return_value = 0
    session.begin_nested.return_value = AsyncMock()
    monkeypatch.setattr(seed.time, "perf_counter", MagicMock(side_effect=[1.0, 32.0]))
    result = await seed.initialize_products(session, target_count=150)
    assert result["strategy"] == "bulk"
    assert session.flush.await_count == 0
    assert session.execute.await_count == 3
