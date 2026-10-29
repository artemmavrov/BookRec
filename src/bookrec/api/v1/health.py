import asyncio
import time

import asyncpg
import structlog
from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel

from bookrec.config import get_settings

router = APIRouter(prefix="/api/v1")
log = structlog.get_logger(__name__)


class ComponentHealth(BaseModel):
    status: str
    response_time_ms: float
    version: str | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    status: str
    components: dict[str, ComponentHealth]


async def check_postgres(pool: asyncpg.Pool, timeout_seconds: float) -> ComponentHealth:
    started = time.perf_counter()
    try:
        async with asyncio.timeout(timeout_seconds):
            server_version = await pool.fetchval("SHOW server_version")
    except Exception as exc:
        elapsed = round((time.perf_counter() - started) * 1000, 2)
        log.warning(
            "health_check_failed",
            component="postgres",
            error=type(exc).__name__,
            response_time_ms=elapsed,
        )
        return ComponentHealth(
            status="error", response_time_ms=elapsed, version=None, error=type(exc).__name__
        )
    elapsed = round((time.perf_counter() - started) * 1000, 2)
    return ComponentHealth(status="ok", response_time_ms=elapsed, version=server_version)


@router.get("/health", response_model=HealthResponse)
async def get_health(request: Request, response: Response) -> HealthResponse:
    timeout = get_settings().health_check_timeout
    postgres = await check_postgres(request.app.state.pool, timeout)
    overall = "ok" if postgres.status == "ok" else "error"
    if overall != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(status=overall, components={"postgres": postgres})
