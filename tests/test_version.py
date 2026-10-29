import tomllib
from importlib.metadata import version
from pathlib import Path

import httpx

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


async def test_version_returns_string(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/version")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"version"}
    assert isinstance(payload["version"], str)
    assert payload["version"]


async def test_version_matches_installed_package(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/version")

    assert response.json()["version"] == version("bookrec")


async def test_version_matches_pyproject(client: httpx.AsyncClient) -> None:
    declared = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]["version"]

    response = await client.get("/api/v1/version")

    assert response.json()["version"] == declared


async def test_version_is_not_available_without_prefix(client: httpx.AsyncClient) -> None:
    response = await client.get("/version")

    assert response.status_code == 404
