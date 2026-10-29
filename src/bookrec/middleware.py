import logging
import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from fastapi import Request, Response

log = structlog.get_logger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"
QUIET_PATHS = frozenset({"/healthz"})


def elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 2)


async def request_logging(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    request_id = request.headers.get(REQUEST_ID_HEADER, "")[:128] or uuid.uuid4().hex
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        request_id=request_id, method=request.method, path=request.url.path
    )
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        log.exception("request_failed", duration_ms=elapsed_ms(started))
        structlog.contextvars.clear_contextvars()
        raise

    response.headers[REQUEST_ID_HEADER] = request_id
    level = logging.DEBUG if request.url.path in QUIET_PATHS else logging.INFO
    log.log(
        level,
        "request_completed",
        status_code=response.status_code,
        duration_ms=elapsed_ms(started),
    )
    structlog.contextvars.clear_contextvars()
    return response
