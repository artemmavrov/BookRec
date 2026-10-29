import httpx
import pytest
import structlog
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware

from bookrec.logging import configure_logging
from bookrec.middleware import REQUEST_ID_HEADER, request_logging
from tests.conftest import read_logs


async def test_request_is_logged_with_request_context(
    client: httpx.AsyncClient, capsys: pytest.CaptureFixture[str]
) -> None:
    configure_logging("INFO")

    response = await client.get("/api/v1/version")

    (entry,) = [e for e in read_logs(capsys) if e["message"] == "request_completed"]
    assert entry["method"] == "GET"
    assert entry["path"] == "/api/v1/version"
    assert entry["status_code"] == 200
    assert entry["duration_ms"] >= 0
    assert entry["request_id"] == response.headers[REQUEST_ID_HEADER]


async def test_request_id_is_generated_per_request(client: httpx.AsyncClient) -> None:
    first = await client.get("/api/v1/version")
    second = await client.get("/api/v1/version")

    assert first.headers[REQUEST_ID_HEADER]
    assert first.headers[REQUEST_ID_HEADER] != second.headers[REQUEST_ID_HEADER]


async def test_incoming_request_id_is_propagated(
    client: httpx.AsyncClient, capsys: pytest.CaptureFixture[str]
) -> None:
    configure_logging("INFO")

    response = await client.get("/api/v1/version", headers={REQUEST_ID_HEADER: "trace-123"})

    assert response.headers[REQUEST_ID_HEADER] == "trace-123"
    entries = [e for e in read_logs(capsys) if e["message"] == "request_completed"]
    assert entries[0]["request_id"] == "trace-123"


async def test_request_id_is_not_leaked_between_requests(
    client: httpx.AsyncClient, capsys: pytest.CaptureFixture[str]
) -> None:
    configure_logging("INFO")

    await client.get("/api/v1/version", headers={REQUEST_ID_HEADER: "trace-123"})
    capsys.readouterr()
    structlog.get_logger("bookrec.test").info("outside_request")

    (entry,) = read_logs(capsys)
    assert "request_id" not in entry


async def test_healthz_is_logged_only_at_debug_level(
    client: httpx.AsyncClient, capsys: pytest.CaptureFixture[str]
) -> None:
    configure_logging("INFO")
    await client.get("/healthz")
    assert [e for e in read_logs(capsys) if e["logger"] == "bookrec.middleware"] == []

    configure_logging("DEBUG")
    await client.get("/healthz")
    (entry,) = [e for e in read_logs(capsys) if e["logger"] == "bookrec.middleware"]
    assert entry["message"] == "request_completed"
    assert entry["level"] == "debug"


async def test_unhandled_exception_is_logged_with_traceback(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_logging("INFO")
    broken = FastAPI()
    broken.add_middleware(BaseHTTPMiddleware, dispatch=request_logging)

    @broken.get("/boom")
    async def boom() -> None:
        raise RuntimeError("unexpected failure")

    transport = httpx.ASGITransport(app=broken, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http_client:
        response = await http_client.get("/boom")

    assert response.status_code == 500
    (entry,) = [e for e in read_logs(capsys) if e["message"] == "request_failed"]
    assert entry["level"] == "error"
    assert entry["path"] == "/boom"
    assert "RuntimeError: unexpected failure" in entry["exception"]
