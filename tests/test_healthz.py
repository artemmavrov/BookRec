import httpx

from tests.conftest import FakePool


async def test_healthz_returns_ok(client: httpx.AsyncClient) -> None:
    response = await client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_healthz_does_not_depend_on_database(
    client: httpx.AsyncClient, pool: FakePool
) -> None:
    pool.error = OSError("database is down")

    response = await client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_healthz_is_not_under_api_prefix(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/healthz")

    assert response.status_code == 404
