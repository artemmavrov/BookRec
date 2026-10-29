FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.13 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
RUN uv sync --frozen --no-dev --no-editable


FROM python:3.12-slim

RUN useradd --system --no-create-home app

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1

USER app

EXPOSE 8000

CMD ["uvicorn", "bookrec.main:app", "--host", "0.0.0.0", "--port", "8000"]
