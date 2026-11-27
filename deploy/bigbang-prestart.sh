#!/usr/bin/env bash
# bigbang-prestart.sh - Pre-start hook for systemd bigbang.service
set -euo pipefail

CONF_FILE="/etc/bigbang/bigbang.conf"
if [[ -f "$CONF_FILE" ]]; then
  # shellcheck source=/dev/null
  source "$CONF_FILE"
fi

STATE_DIR="${BIGBANG_STATE_DIR:-/var/lib/bigbang/state}"
ISSUES_DIR="${BIGBANG_ISSUES_DIR:-/var/lib/bigbang/issues}"
COMMANDS_FILE="${BIGBANG_COMMANDS_FILE:-/var/lib/bigbang/commands.txt}"

mkdir -p "$STATE_DIR" "$ISSUES_DIR" "$(dirname "$COMMANDS_FILE")"
touch "$COMMANDS_FILE"

# If stopped gracefully by systemd in a previous run, clear the halt lock
HALT_FILE="$STATE_DIR/HALT"
SNAPSHOT_FILE="$STATE_DIR/snapshot.json"

if [[ -f "$HALT_FILE" ]]; then
  REASON=$(cat "$HALT_FILE" 2>/dev/null || true)
  if [[ "$REASON" =~ "systemd stop" || "$REASON" =~ "service restart" ]]; then
    rm -f "$HALT_FILE"
    # Reset halted flag in snapshot if present so resume executes immediately
    if [[ -f "$SNAPSHOT_FILE" ]]; then
      python3 -c "
import json
try:
    with open('$SNAPSHOT_FILE', 'r+') as f:
        data = json.load(f)
        if data.get('halted'):
            data['halted'] = False
            f.seek(0)
            json.dump(data, f, indent=2)
            f.truncate()
except Exception:
    pass
"
    fi
  fi
fi

# If state directory has no organism snapshot yet, bootstrap first tick
if [[ ! -f "$SNAPSHOT_FILE" ]]; then
  /opt/bigbang/venv/bin/python -m bigbang run \
    --state "$STATE_DIR" \
    --issues "$ISSUES_DIR" \
    --commands "$COMMANDS_FILE" \
    --brain "${BIGBANG_BRAIN:-rule}" \
    --organism "${BIGBANG_ORGANISM:-body}" \
    --role "${BIGBANG_ROLE:-general}" \
    --ticks 1 >/dev/null 2>&1 || true
fi
