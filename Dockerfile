FROM python:3.13-slim-trixie@sha256:8fb4cfa1a2616d7b8e0c2175cc6ad68f5729c34ea8488c0b360d2934b7be9024

COPY --from=ghcr.io/astral-sh/uv:0.12.4@sha256:0ff11fbfed5cb87a930fa471748f03bd78cbc15a4fc09f18b06a15e0ead32370 /uv /usr/local/bin/uv

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 videos \
    && useradd --uid 10001 --gid videos --no-create-home videos

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-default-groups --no-install-project --no-cache
COPY src/ ./src/
COPY migrations/ ./migrations/
COPY yoyo.ini docker-entrypoint.sh ./
RUN chmod 0555 /app/docker-entrypoint.sh

USER 10001:10001
EXPOSE 8080
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["api"]
