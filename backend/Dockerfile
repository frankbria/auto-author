# syntax=docker/dockerfile:1
#
# FastAPI backend image (#427).
#
# Multi-stage: build the virtualenv with uv, then copy just the venv and app into
# a clean runtime layer. uv is not present at runtime.
#
# pyproject.toml requires >=3.13.

ARG PYTHON_VERSION=3.13-slim

# ---- build: resolve from uv.lock only
FROM python:${PYTHON_VERSION} AS build
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

# Dependencies first, without the project, so this layer survives app-code edits.
COPY pyproject.toml uv.lock ./
# --frozen fails rather than silently re-resolving if uv.lock is stale, which is
# the same guarantee the requirements.txt drift check gives in CI (#439).
# No --extra test: the test extra exists to keep production installs lean.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ---- runtime
FROM python:${PYTHON_VERSION} AS runtime
WORKDIR /app

# Non-root. python:slim has no unprivileged user of its own, so create one.
RUN useradd --create-home --uid 1000 appuser

COPY --from=build --chown=appuser:appuser /app/.venv /app/.venv
COPY --from=build --chown=appuser:appuser /app/app /app/app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER appuser
EXPOSE 8000

# app.main:app — note backend/main.py is an unrelated stub (`print("Hello from
# backend!")`), not the server entrypoint.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
