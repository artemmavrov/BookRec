import json
import os
import subprocess
import sys
from importlib.metadata import version

import asyncpg
import pytest
from structlog.testing import capture_logs

from bookrec.db import create_pool
from bookrec.main import app, lifespan
from tests.conftest import FakePool


async def test_lifespan_creates_and_closes_pool(
    monkeypatch: pytest.MonkeyPatch, pool: FakePool
) -> None:
    received = {}

    async def fake_create_pool(dsn: str) -> FakePool:
        received["dsn"] = dsn
        return pool

    monkeypatch.setattr("bookrec.main.create_pool", fake_create_pool)

    async with lifespan(app):
        assert app.state.pool is pool
        assert not pool.closed

    assert pool.closed
    assert received["dsn"] == "postgresql://user:secret@localhost:5432/test"


async def test_lifespan_logs_lifecycle(monkeypatch: pytest.MonkeyPatch, pool: FakePool) -> None:
    async def fake_create_pool(dsn: str) -> FakePool:
        return pool

    monkeypatch.setattr("bookrec.main.create_pool", fake_create_pool)

    with capture_logs() as logs:
        async with lifespan(app):
            pass

    events = [log["event"] for log in logs]
    assert events == ["app_starting", "db_pool_created", "app_stopping", "db_pool_closed"]
    assert logs[0]["version"] == version("bookrec")
    assert "secret" not in str(logs)


async def test_create_pool_is_lazy_and_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    received = {}

    async def fake_asyncpg_create_pool(dsn: str, **kwargs: int) -> str:
        received["dsn"] = dsn
        received.update(kwargs)
        return "pool"

    monkeypatch.setattr(asyncpg, "create_pool", fake_asyncpg_create_pool)

    result = await create_pool("postgresql://u:p@h:5432/d")

    assert result == "pool"
    assert received == {"dsn": "postgresql://u:p@h:5432/d", "min_size": 0, "max_size": 5}


def test_logging_is_configured_on_import() -> None:
    code = (
        "import logging; import bookrec.main; "
        "logging.getLogger('uvicorn.error').info('Started server process')"
    )
    env = {**os.environ, "BOOKREC_DATABASE_DSN": "postgresql://u:p@h:5432/d"}

    result = subprocess.run(
        [sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True
    )

    entry = json.loads(result.stdout.strip().splitlines()[-1])
    assert entry["message"] == "Started server process"
    assert entry["logger"] == "uvicorn.error"
