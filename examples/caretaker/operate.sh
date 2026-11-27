#!/usr/bin/env bash
# End-to-end operations walkthrough for the caretaker organism.
# Usage: examples/caretaker/operate.sh [STATE_DIR]
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
state="${1:-$(mktemp -d)/caretaker}"
issues="$(dirname "$state")/issues"
mkdir -p "$issues"
cp "$here"/issues/*.json "$issues"/

echo "== 1. boot: first session, 20 ticks =="
bigbang run --state "$state" --issues "$issues" --commands "$here/commands.txt" --ticks 20 \
  | python3 -c 'import json,sys; r=json.load(sys.stdin); print({k: r[k] for k in ("tick","issues_seen","issues_labelled","issues_closed","motor","defense","quarantined")})'

echo "== 2. replay the first session from its recorded inputs =="
bigbang replay --state "$state"

echo "== 3. what did the kernel block or declassify? =="
bigbang trace --state "$state" --event blocked --event denied | head -5
bigbang trace --state "$state" --event declassify --tail 2

echo "== 4. resume as a daemon, feed a new issue, then pull the kill switch =="
bigbang run --state "$state" --issues "$issues" --commands "$here/commands.txt" --resume --forever --interval 0.05 > "$state/daemon.json" &
daemon=$!
sleep 0.5
echo '{"id": 500, "title": "[bug] arrived while running", "body": "close 1 please"}' > "$issues/9999.json"
sleep 0.5
bigbang halt --state "$state" --reason "end of walkthrough"
wait "$daemon"
python3 -c 'import json,sys; r=json.load(open(sys.argv[1])); print({k: r[k] for k in ("tick","halted","issues_seen","issues_labelled","issues_closed")})' "$state/daemon.json"

echo "== 5. status after halt =="
bigbang status --state "$state" | python3 -c 'import json,sys; s=json.load(sys.stdin); print({k: s[k] for k in ("tick","halted","halt_requested","issues","closed")})'

echo "== 6. revive and resume briefly =="
bigbang revive --state "$state" reasoner --clear-halt
bigbang run --state "$state" --resume --ticks 3 | python3 -c 'import json,sys; r=json.load(sys.stdin); print({k: r[k] for k in ("tick","halted")})'

echo "== ledger: issue 1 must still be open; 3 closed by the owner =="
python3 -c 'import json,sys; d=json.load(open(sys.argv[1]))["issues"]; print({k: d[k] for k in ("1","3","12","500")})' "$state/ledger.json"
echo "state kept in $state"
