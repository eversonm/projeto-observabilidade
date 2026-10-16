import time
from pathlib import Path

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.products.models import Product

SEED_SQL = Path(__file__).resolve().parents[2] / "sql" / "init_products.sql"
HYBRID_ROW_COUNT = 100
BULK_THRESHOLD_SECONDS = 30.0
ADVISORY_LOCK_KEY = 8_173_011


async def initialize_products(
    session: AsyncSession, target_count: int | None = None
) -> dict[str, int | float | str]:
    target = target_count if target_count is not None else settings.seed_target_count
    await session.execute(
        text("SELECT pg_advisory_xact_lock(:key)"),
        {"key": ADVISORY_LOCK_KEY},
    )
    current = int(await session.scalar(select(func.count()).select_from(Product)) or 0)
    missing = max(target - current, 0)
    if missing == 0:
        await session.commit()
        return {
            "inserted": 0,
            "total": current,
            "strategy": "already_initialized",
            "benchmark_seconds": 0.0,
        }

    sql = text(SEED_SQL.read_text(encoding="utf-8"))
    savepoint = await session.begin_nested()
    started = time.perf_counter()
    await session.execute(sql, {"row_count": missing})
    benchmark_seconds = time.perf_counter() - started
    await savepoint.rollback()

    if benchmark_seconds < BULK_THRESHOLD_SECONDS and missing > HYBRID_ROW_COUNT:
        for index in range(HYBRID_ROW_COUNT):
            session.add(
                Product(
                    name=f"Produto sintético individual {current + index + 1}",
                    description=(
                        "Registro sintético inserido individualmente para benchmark."
                    ),
                    link=f"https://example.com/products/{current + index + 1}",
                )
            )
            await session.flush()
        bulk_count = missing - HYBRID_ROW_COUNT
        await session.execute(sql, {"row_count": bulk_count})
        strategy = "hybrid"
    else:
        await session.execute(sql, {"row_count": missing})
        strategy = "bulk"

    await session.commit()
    return {
        "inserted": missing,
        "total": current + missing,
        "strategy": strategy,
        "benchmark_seconds": round(benchmark_seconds, 3),
    }

