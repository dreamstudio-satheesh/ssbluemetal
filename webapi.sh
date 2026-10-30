#!/usr/bin/env bash
# Local API server (no docker). Uses db/billing.db directly and loads webapp/.env.
set -euo pipefail
cd "$(dirname "$0")"

if [ -f webapp/.env ]; then
  set -a
  . ./webapp/.env
  set +a
fi

PY=.venv/bin/python
[ -x "$PY" ] || { echo "Missing .venv — run: uv venv .venv && uv pip install --python .venv/bin/python -r webapp/requirements-web.txt"; exit 1; }

HOST="${API_HOST:-127.0.0.1}"
PORT="${API_PORT:-8000}"
echo "API on http://$HOST:$PORT  (docs: /docs)"
exec "$PY" -m uvicorn webapp.main:app --host "$HOST" --port "$PORT"
