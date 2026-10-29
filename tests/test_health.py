import httpx
import pytest
from structlog.testing import capture_logs

from bookrec.api.v1.health import check_postgres
from bookrec.config import get_settings
from tests.conftest import FakePool


async def test_health_ok(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    postgres = payload["components"]["postgres"]
    assert postgres["status"] == "ok"
    assert postgres["version"] == "16.0"
    assert postgres["response_time_ms"] >= 0
    assert postgres["error"] is None


async def test_health_returns_503_when_database_is_down(
    client: httpx.AsyncClient, pool: FakePool
) -> None:
    pool.error = OSError("connection refused")

    response = await client.get("/api/v1/health")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "error"
    postgres = payload["components"]["postgres"]
    assert postgres["status"] == "error"
    assert postgres["error"] == "OSError"
    assert postgres["version"] is None


async def test_health_returns_503_on_timeout(
    client: httpx.AsyncClient, pool: FakePool, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("BOOKREC_HEALTH_CHECK_TIMEOUT", "0.05")
    get_settings.cache_clear()
    pool.delay = 1.0

    response = await client.get("/api/v1/health")

    assert response.status_code == 503
    postgres = response.json()["components"]["postgres"]
    assert postgres["status"] == "error"
    assert postgres["error"] == "TimeoutError"
    assert postgres["response_time_ms"] < 1000


async def test_health_does_not_leak_error_details(
    client: httpx.AsyncClient, pool: FakePool
) -> None:
    pool.error = RuntimeError("password authentication failed for user secret")

    response = await client.get("/api/v1/health")

    assert response.status_code == 503
    assert "secret" not in response.text
    assert response.json()["components"]["postgres"]["error"] == "RuntimeError"


async def test_health_failure_is_logged_without_secrets(
    client: httpx.AsyncClient, pool: FakePool
) -> None:
    pool.error = RuntimeError("password authentication failed for user secret")

    with capture_logs() as logs:
        await client.get("/api/v1/health")

    (entry,) = [log for log in logs if log["event"] == "health_check_failed"]
    assert entry["log_level"] == "warning"
    assert entry["component"] == "postgres"
    assert entry["error"] == "RuntimeError"
    assert entry["response_time_ms"] >= 0
    assert "secret" not in str(logs)


async def test_health_success_is_not_logged_as_failure(client: httpx.AsyncClient) -> None:
    with capture_logs() as logs:
        await client.get("/api/v1/health")

    assert not [log for log in logs if log["event"] == "health_check_failed"]


async def test_check_postgres_measures_response_time(pool: FakePool) -> None:
    pool.delay = 0.05

    result = await check_postgres(pool, timeout_seconds=1.0)

    assert result.status == "ok"
    assert result.response_time_ms >= 40


async def test_check_postgres_reports_error_with_elapsed_time(pool: FakePool) -> None:
    pool.error = ConnectionError("boom")

    result = await check_postgres(pool, timeout_seconds=1.0)

    assert result.status == "error"
    assert result.error == "ConnectionError"
    assert result.version is None
    assert result.response_time_ms >= 0
