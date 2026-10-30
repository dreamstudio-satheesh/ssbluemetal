#!/usr/bin/env bash
# Publish the API through Cloudflare.
#
#   API_PORT=8000 TUNNEL_NAME=ssm-api ./webapp/tunnel.sh     # named tunnel (stable domain)
#   API_PORT=8000 TUNNEL_TOKEN=eyJ... ./webapp/tunnel.sh     # dashboard token tunnel
#   ./webapp/tunnel.sh                                        # quick tunnel (random URL)
set -euo pipefail
cd "$(dirname "$0")/.."

PORT="${API_PORT:-8000}"
command -v cloudflared >/dev/null || { echo "cloudflared not installed"; exit 1; }

curl -sf -m 3 "http://127.0.0.1:$PORT/api/health" >/dev/null \
  || { echo "API is not running on 127.0.0.1:$PORT — start it first: ./webapi.sh"; exit 1; }

if [ -n "${TUNNEL_TOKEN:-}" ]; then
  echo "Token tunnel -> http://127.0.0.1:$PORT"
  exec cloudflared tunnel --no-autoupdate run --token "$TUNNEL_TOKEN"
fi

if [ -n "${TUNNEL_NAME:-}" ]; then
  echo "Named tunnel '$TUNNEL_NAME' -> http://127.0.0.1:$PORT"
  exec cloudflared tunnel --no-autoupdate run "$TUNNEL_NAME"
fi

echo "Quick tunnel -> http://127.0.0.1:$PORT  (URL changes on every restart)"
exec cloudflared tunnel --no-autoupdate --url "http://127.0.0.1:$PORT"
