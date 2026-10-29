from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware

from bookrec.api import healthz
from bookrec.api.v1 import health, version
from bookrec.config import LoggingSettings, get_settings
from bookrec.db import create_pool
from bookrec.logging import configure_logging
from bookrec.middleware import request_logging

logging_settings = LoggingSettings()
configure_logging(logging_settings.log_level, logging_settings.log_json)

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    log.info("app_starting", version=version.APP_VERSION, log_level=settings.log_level)
    app.state.pool = await create_pool(settings.database_dsn)
    log.info("db_pool_created")
    yield
    log.info("app_stopping")
    await app.state.pool.close()
    log.info("db_pool_closed")


app = FastAPI(title="BookRec", lifespan=lifespan)
app.add_middleware(BaseHTTPMiddleware, dispatch=request_logging)
app.include_router(healthz.router)
app.include_router(version.router)
app.include_router(health.router)
