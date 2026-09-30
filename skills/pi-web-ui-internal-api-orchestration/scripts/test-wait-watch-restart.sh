#!/usr/bin/env bash
# Scripted check: wait-watch.sh detects a Pi Web UI restart via MainPID.
#
# Behaviour under test: when the service unit's MainPID changes between loop
# iterations, the watcher prints a "reconnecting" message and re-snapshots the
# PID. The unit comes from PI_WEB_UI_SERVICE (default pi-web-ui.service). A fake
# `systemctl` is placed first on PATH so no real service is touched, and a
# bound-but-unserved Unix socket stands in for the Internal API (the long poll
# fails, the loop advances, and the restart branch runs).
#
# Exit codes: 0 = the restart message was observed, 1 = it was not (RED), 3 =
# the check could not run (missing python3, for example).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WATCHER="$SCRIPT_DIR/wait-watch.sh"

if ! command -v python3 >/dev/null 2>&1; then
  echo "SKIP: python3 is required to create the stand-in socket" >&2
  exit 3
fi

TMP="$(mktemp -d)"
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT

# Fake systemctl: the first MainPID read returns 111, every later one returns 222.
mkdir -p "$TMP/bin"
COUNTER="$TMP/systemctl-count"
echo 0 > "$COUNTER"
cat > "$TMP/bin/systemctl" <<FAKE
#!/usr/bin/env bash
if [ "\${1:-}" = "show" ]; then
  n=\$(cat "$COUNTER"); n=\$((n + 1)); echo "\$n" > "$COUNTER"
  if [ "\$n" -le 1 ]; then echo 111; else echo 222; fi
  exit 0
fi
exit 1
FAKE
chmod +x "$TMP/bin/systemctl"

# A real Unix socket file, but nothing listening on it.
SOCKET="$TMP/internal-api.sock"
python3 - "$SOCKET" <<'PY'
import socket
import sys

sock = socket.socket(socket.AF_UNIX)
sock.bind(sys.argv[1])
PY
TOKEN="$TMP/token"
echo test-token > "$TOKEN"

set +e
PATH="$TMP/bin:$PATH" \
PI_WEB_UI_SERVICE=pi-web-ui.service \
PI_WEB_UI_SOCKET="$SOCKET" \
PI_WEB_UI_TOKEN_PATH="$TOKEN" \
PI_WEB_UI_API_BASE="http://localhost/api/v1" \
timeout 20 bash "$WATCHER" watch-restart-check 3 1000 > "$TMP/out.log" 2>&1
RUN_EXIT=$?
set -e

if grep -q 'reconnecting' "$TMP/out.log"; then
  echo "PASS: restart detected (run exit $RUN_EXIT)"
  echo "--- watcher output ---"
  cat "$TMP/out.log"
  exit 0
fi

echo "FAIL: no restart-detection message; watcher output:" >&2
cat "$TMP/out.log" >&2
exit 1
