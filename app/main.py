import json
import logging
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import make_asgi_app
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.database import engine
from app.observability.metrics import HTTP_DURATION, HTTP_REQUESTS
from app.observability.router import router as observability_router
from app.products.models import Base
from app.products.router import router as products_router


class JsonFormatter(logging.Formatter):
    fields = (
        "request_id",
        "trace_id",
        "method",
        "route",
        "status_code",
        "duration_seconds",
        "actor",
        "product_id",
        "alert_name",
        "recovery_seconds",
        "strategy",
        "inserted",
        "total",
        "benchmark_seconds",
    )

    def format(self, record: logging.LogRecord) -> str:
        event: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(
                record.created, timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        event.update(
            {
                field: getattr(record, field)
                for field in self.fields
                if hasattr(record, field)
            }
        )
        if record.exc_info:
            event["exception"] = self.formatException(record.exc_info)
        return json.dumps(event, ensure_ascii=False, default=str)


handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
logger = logging.getLogger("products_api")


def configure_tracing() -> None:
    resource = Resource.create({"service.name": "products-api"})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=settings.otel_exporter_otlp_endpoint,
                insecure=True,
            )
        )
    )
    trace.set_tracer_provider(provider)
    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
    HTTPXClientInstrumentor().instrument()


configure_tracing()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        await connection.execute(text("SELECT 1"))
    yield
    await engine.dispose()


app = FastAPI(
    title="Produtos API",
    version="1.0.0",
    lifespan=lifespan,
    swagger_ui_init_oauth={"clientId": settings.keycloak_client_id},
)
app.include_router(products_router)
app.include_router(observability_router)
app.mount("/metrics", make_asgi_app())
FastAPIInstrumentor.instrument_app(app)


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(
    _: Request, exc: RequestValidationError
) -> JSONResponse:
    details = [
        {
            "field": ".".join(str(part) for part in error["loc"]),
            "message": error["msg"],
        }
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": details})


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(
    _: Request, exc: SQLAlchemyError
) -> JSONResponse:
    logger.error("database_error", exc_info=(type(exc), exc, exc.__traceback__))
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno da aplicação"},
    )


@app.middleware("http")
async def request_observability(request: Request, call_next: Any) -> Any:
    started = time.perf_counter()
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))[:128]
    request.state.request_id = request_id
    try:
        response = await call_next(request)
    except Exception:
        elapsed = time.perf_counter() - started
        route = getattr(request.scope.get("route"), "path", "unmatched")
        HTTP_REQUESTS.labels(request.method, route, "5xx").inc()
        HTTP_DURATION.labels(request.method, route).observe(elapsed)
        logger.exception(
            "request_failed",
            extra={"request_id": request_id, "route": route},
        )
        raise
    elapsed = time.perf_counter() - started
    route = getattr(request.scope.get("route"), "path", "unmatched")
    status_class = f"{response.status_code // 100}xx"
    HTTP_REQUESTS.labels(request.method, route, status_class).inc()
    HTTP_DURATION.labels(request.method, route).observe(elapsed)
    response.headers["X-Request-ID"] = request_id
    span_context = trace.get_current_span().get_span_context()
    trace_id = f"{span_context.trace_id:032x}" if span_context.is_valid else ""
    logger.info(
        "http_request",
        extra={
            "request_id": request_id,
            "trace_id": trace_id,
            "method": request.method,
            "route": route,
            "status_code": response.status_code,
            "duration_seconds": round(elapsed, 6),
        },
    )
    return response


@app.get("/health/live", tags=["health"])
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
async def readiness() -> JSONResponse:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return JSONResponse({"status": "ready"})
    except Exception:
        logger.exception("readiness_check_failed")
        return JSONResponse({"status": "unavailable"}, status_code=503)


@app.exception_handler(Exception)
async def unexpected_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    logger.error(
        "unhandled_application_error",
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno da aplicação"},
        headers={
            "X-Request-ID": getattr(request.state, "request_id", ""),
        },
    )
