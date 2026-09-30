#!/usr/bin/env bash
# wait-watch.sh — Persistent zero-token watcher for Pi Web UI Internal API watches.
#
# Audience: Authored for the Antigravity CLI/IDE parent orchestrator.
# Also usable from any CLI harness on this host.
#
# Restart detection: snapshots the MainPID of the service unit named by
# PI_WEB_UI_SERVICE (default: pi-web-ui.service) and prints a "reconnecting"
# message when it changes, because a server restart reloads watches `detached`.
# When `systemctl` is unavailable, or the unit is unknown, the check is a
# documented no-op — the schedule backstop still covers a hung wait.
#
# Usage:
#   wait-watch.sh <watchId> [max_iterations] [request_timeout_ms]
#
# Example (Antigravity background task invocation):
#   run_command(
#     CommandLine: "./scripts/wait-watch.sh watch-<watch-id>",
#     WaitMsBeforeAsync: 1000
#   )
#
# Exit Codes:
#   0 = Watch fired successfully (turn settled or condition met)
#   1 = Timed out after max iterations
#   3 = Configuration error (missing socket or token)

set -euo pipefail

WATCH_ID="${1:-}"
if [ -z "$WATCH_ID" ]; then
  echo "Usage: $0 <watchId> [max_iterations] [request_timeout_ms]" >&2
  exit 3
fi

MAX_ITERATIONS="${2:-120}"        # 120 * 30s = 60 minutes default
REQUEST_TIMEOUT_MS="${3:-30000}"   # 30s per held request

SOCKET="${PI_WEB_UI_SOCKET:-$HOME/.pi-web-ui/internal-api.sock}"
TOKEN_PATH="${PI_WEB_UI_TOKEN_PATH:-$HOME/.pi-web-ui/internal-api-token}"
API_BASE="${PI_WEB_UI_API_BASE:-http://localhost/api/v1}"

if [ ! -S "$SOCKET" ]; then
  echo "Error: Pi Web UI Unix socket not found at $SOCKET" >&2
  exit 3
fi

if [ ! -f "$TOKEN_PATH" ]; then
  echo "Error: Pi Web UI token not found at $TOKEN_PATH" >&2
  exit 3
fi

TOKEN="$(cat "$TOKEN_PATH")"

# Restart detection (generic): the unit is configurable, and the whole check is
# a no-op when systemctl is unavailable or reports no MainPID.
SERVICE="${PI_WEB_UI_SERVICE:-pi-web-ui.service}"
BASE_PID=""
if command -v systemctl >/dev/null 2>&1; then
  BASE_PID="$(systemctl show -p MainPID --value "$SERVICE" 2>/dev/null || true)"
fi

echo "[wait-watch] Monitoring watch '$WATCH_ID' via $SOCKET (max ${MAX_ITERATIONS} iterations)..."
if [ -n "$BASE_PID" ]; then
  echo "[wait-watch] Restart detection: service '$SERVICE' MainPID $BASE_PID"
fi

ITER=0
CURSOR=""

while [ "$ITER" -lt "$MAX_ITERATIONS" ]; do
  ITER=$((ITER + 1))

  # A restart reloads watches detached; surface it instead of hanging silently.
  if [ -n "$BASE_PID" ]; then
    CUR_PID="$(systemctl show -p MainPID --value "$SERVICE" 2>/dev/null || true)"
    if [ -n "$CUR_PID" ] && [ "$CUR_PID" != "$BASE_PID" ]; then
      echo "[wait-watch] Pi Web UI service '$SERVICE' restarted (MainPID $BASE_PID -> $CUR_PID); reconnecting..."
      BASE_PID="$CUR_PID"
    fi
  fi

  URL="$API_BASE/watches/wait?ids=$WATCH_ID&timeout=$REQUEST_TIMEOUT_MS"
  if [ -n "$CURSOR" ]; then
    URL="$URL&cursor=$CURSOR"
  fi

  RESP="$(curl --silent --unix-socket "$SOCKET" -H "Authorization: Bearer $TOKEN" "$URL")" || true

  if [ -z "$RESP" ]; then
    sleep 2
    continue
  fi

  FIRED="$(echo "$RESP" | jq -r '.fired // false' 2>/dev/null || echo "false")"
  NEXT_CURSOR="$(echo "$RESP" | jq -r '.nextCursor // empty' 2>/dev/null || true)"
  if [ -n "$NEXT_CURSOR" ]; then
    CURSOR="$NEXT_CURSOR"
  fi

  if [ "$FIRED" = "true" ]; then
    echo "[wait-watch] Watch '$WATCH_ID' FIRED at $(date -u +%Y-%m-%dT%H:%M:%SZ) (iteration $ITER):"
    echo "$RESP" | jq . 2>/dev/null || echo "$RESP"
    exit 0
  fi
done

echo "[wait-watch] Timeout: watch '$WATCH_ID' did not fire within $MAX_ITERATIONS iterations." >&2
exit 1
