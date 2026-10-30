# syntax=docker/dockerfile:1
#
# FastAPI backend image (#427).
#
# Multi-stage: build the virtualenv with uv, then copy just the venv and app into
# a clean runtime layer. uv is not present at runtime.
#
# pyproject.toml requires >=3.13.

# The one place the base image is named, by tag and by digest (#818). The tag
# alone floats: each build took whatever it pointed at that day. Dependabot's
# docker entry moves the digest, as a pull request the image scan runs on. It
# reads a literal FROM line only; with the tag in a build argument it found no
# dependency here at all.
FROM python:3.13-slim@sha256:57b29a7c050c4e679e4bea572e14b3965cf4b5839de2da49d55e49ffc4024f39 AS base

# uv, by version and digest (#819). `:latest` was whatever was newest on the day
# of the build. A stage of its own, so that it is named in a FROM line like the
# base image and Dependabot's docker entry moves it the same way.
#
# Docker Hub's copy, not ghcr.io's. They are the same image (this digest is the
# digest of both), but Dependabot can hold a new release back for the cooldown
# only where the registry tells it when a tag was published. Measured: for
# ghcr.io it reports "Cooldown was not applied" and carries on.
FROM astral/uv:0.13.1@sha256:4a1f3666816dafadd20ceb71eac9a7d56d7ef30279f7d64048519ab901ada336 AS uv

# ---- build: resolve from uv.lock only
FROM base AS build
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

# Dependencies first, without the project, so this layer survives app-code edits.
COPY pyproject.toml uv.lock ./
# --frozen fails rather than silently re-resolving if uv.lock is stale, so the
# image can only ever install what uv.lock pins (#439). Since #534 deleted the
# generated requirements.txt export, uv.lock is the only dependency source there is.
# No --extra test: the test extra exists to keep production installs lean.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ---- runtime
FROM base AS runtime
WORKDIR /app

# The runtime runs the virtualenv built above and installs nothing, so the base
# image's own pip goes (#818). pip carries its own copies of urllib3, msgpack
# and setuptools, which is what an image scan finds, and a package manager is
# the first thing an intruder would reach for.
RUN python -m pip uninstall --yes pip

# Non-root. python:slim has no unprivileged user of its own, so create one.
RUN useradd --create-home --uid 1000 appuser

COPY --from=build --chown=appuser:appuser /app/.venv /app/.venv
COPY --from=build --chown=appuser:appuser /app/app /app/app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER appuser
EXPOSE 8000

# The commit this image was built from: the Sentry release (#808). Last, so a
# new commit invalidates no layer above it.
ARG GIT_SHA=""
ENV GIT_SHA=${GIT_SHA}

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
