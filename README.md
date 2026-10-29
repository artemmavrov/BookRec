# BookRec

Async web service built with FastAPI and asyncpg, backed by PostgreSQL.

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| GET | `/healthz` | Liveness probe. Does not touch the database and lives outside `/api/v1`, since it is meant for the orchestrator, not for API clients |
| GET | `/api/v1/version` | Application version taken from the installed package metadata |
| GET | `/api/v1/health` | End-to-end check: version and response time of every third-party component. Returns `503` if any component is down |

## Configuration

Copy the example and adjust it if needed:

```
cp .env.example .env
```

| Variable | Default | Description |
| --- | --- | --- |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | required | Credentials used by the `db` service in docker-compose |
| `BOOKREC_DATABASE_DSN` | required | PostgreSQL DSN used by the application |
| `BOOKREC_LOG_LEVEL` | `INFO` | Log level |
| `BOOKREC_LOG_JSON` | `true` | JSON logs when `true`, console format when `false` |
| `BOOKREC_HEALTH_CHECK_TIMEOUT` | `2.0` | Timeout in seconds for a single component check |

## Run with Docker

```
docker compose up --build
```

The application is available at `http://localhost:8000`. PostgreSQL is published only on `127.0.0.1:5433`.

## Run locally

Requires [uv](https://docs.astral.sh/uv/) and a running PostgreSQL (for example `docker compose up -d db`).

```
uv sync
uv run uvicorn bookrec.main:app --reload
```

## Development

```
uv run ruff check .
uv run ruff format .
uv run pytest --cov
```

Tests do not need a database: the connection pool is replaced with a fake one. Coverage below 90% fails the run.

## CD

The image is published to GitHub Container Registry: `ghcr.io/artemmavrov/bookrec`.

### Triggers

| Event | Result |
| --- | --- |
| Pull request | CI only, nothing is published |
| Push to `main` | CI gate, then image tagged `edge` and `sha-<short>` |
| Push of tag `vX.Y.Z` | CI gate, then image tagged `X.Y.Z`, `X.Y`, `X` |
| Manual run | Same as a push to the selected ref |

The image is built only after the CI workflow (lint, format, tests with coverage, docker build) succeeds.

### Versioning

- The application version lives in `pyproject.toml` and is served by `GET /api/v1/version`.
- A release is a git tag `vX.Y.Z`. The pipeline fails if the tag differs from the `pyproject.toml` version, so the registry tag and the version reported by the app can never diverge.
- `sha-<short>` identifies the exact commit of any image, `edge` always points to the latest `main`.

### Release

```
git tag v0.1.0
git push origin v0.1.0
```

### Pull

```
docker pull ghcr.io/artemmavrov/bookrec:edge
docker pull ghcr.io/artemmavrov/bookrec:0.1.0
```
