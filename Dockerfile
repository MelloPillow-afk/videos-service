# Two images from one build: `--target worker` adds FFmpeg for the Cloud Run job;
# the default `api` target serves HTTP without it.
FROM python:3.13-slim AS base
COPY --from=ghcr.io/astral-sh/uv:0.12.4 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"
WORKDIR /app
# Runtime dependencies only; their layer is reused until the lockfile changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-default-groups --no-install-project
COPY yoyo.ini ./
COPY migrations ./migrations
COPY src ./src
RUN uv sync --locked --no-default-groups && useradd --system --no-create-home app
USER app

FROM base AS worker
USER root
RUN apt-get update \
    && apt-get install --yes --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
USER app
ENTRYPOINT ["python", "-m", "src.workers.media"]

FROM base AS api
# Cloud Run supplies PORT.
CMD exec uvicorn src.app:create_app --factory --host 0.0.0.0 --port "${PORT:-8080}"
