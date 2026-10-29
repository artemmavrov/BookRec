import asyncio
import json
import logging
from collections.abc import AsyncIterator, Iterator
from typing import Any

import httpx
import pytest
import structlog

from bookrec.config import get_settings
from bookrec.main import app


class FakePool:
    def __init__(
        self,
        version: str = "16.0",
        error: Exception | None = None,
        delay: float = 0.0,
    ) -> None:
        self.version = version
        self.error = error
        self.delay = delay
        self.closed = False

    async def fetchval(self, query: str) -> str:
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.error:
            raise self.error
        return self.version

    async def close(self) -> None:
        self.closed = True


@pytest.fixture(autouse=True)
def settings_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("BOOKREC_DATABASE_DSN", "postgresql://user:secret@localhost:5432/test")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def isolate_logging() -> Iterator[None]:
    root = logging.getLogger()
    handlers = list(root.handlers)
    level = root.level
    yield
    root.handlers = handlers
    root.setLevel(level)
    structlog.reset_defaults()
    structlog.contextvars.clear_contextvars()


def read_logs(capsys: pytest.CaptureFixture[str]) -> list[dict[str, Any]]:
    lines = capsys.readouterr().out.splitlines()
    return [json.loads(line) for line in lines if line.strip()]


@pytest.fixture
def pool() -> FakePool:
    return FakePool()


@pytest.fixture
async def client(pool: FakePool) -> AsyncIterator[httpx.AsyncClient]:
    app.state.pool = pool
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
