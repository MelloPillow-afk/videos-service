#!/bin/sh
set -eu
if [ "${1:-}" = api ]; then
    shift
    exec uvicorn src.app:create_app --factory --host 0.0.0.0 --port "${PORT:-8080}" "$@"
fi
exec "$@"
