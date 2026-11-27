#!/bin/sh
# P-01 live proof on the stock Electron framework. Stages the wrapper beside the pinned core,
# runs it, and requires that the app:// handler serves the core and the page boots to S0.
# The probe is inert unless EPHEMERAL_E2E=1, so this measures the shipped main.cjs.
#
# Usage: ELECTRON_BIN=/path/to/Electron sh scripts/e2e-core-load.sh [core html]
# The core defaults to the sibling artifact. Point EPHEMERAL_CORE or the argument at a frozen
# copy of the artifact the pin was committed for when the live file is mid edit.
set -eu

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
electron=${ELECTRON_BIN:-${1:-}}
core=${EPHEMERAL_CORE:-${2:-$here/../../ephemeral-chat-v2.html}}

[ -n "$electron" ] || { echo "usage: ELECTRON_BIN=/path/to/Electron sh scripts/e2e-core-load.sh" >&2; exit 2; }
[ -x "$electron" ] || { echo "not executable: $electron" >&2; exit 2; }
[ -f "$core" ] || { echo "missing core: $core" >&2; exit 2; }

if command -v sha256sum >/dev/null 2>&1; then
  core_hash=$(sha256sum "$core" | cut -d' ' -f1)
else
  core_hash=$(shasum -a 256 "$core" | cut -d' ' -f1)
fi
core_bytes=$(wc -c < "$core" | tr -d ' ')

stage=$(mktemp -d "${TMPDIR:-/tmp}/ephemeral-e2e.XXXXXX")
cleanup() { rm -rf "$stage"; }
trap cleanup EXIT INT TERM

mkdir -p "$stage/app/core"
cp "$here/../main.cjs" "$here/../preload.cjs" "$here/../menu.cjs" "$here/../qr.cjs" \
  "$here/../package.json" "$stage/app/"
cp "$core" "$stage/app/core/ephemeral-chat-v2.html"

log="$stage/out.log"
EPHEMERAL_BUILD_HASH="$core_hash" EPHEMERAL_E2E=1 "$electron" "$stage/app" >"$log" 2>&1 &
pid=$!
ticks=0
while kill -0 "$pid" 2>/dev/null; do
  ticks=$((ticks + 1))
  if [ "$ticks" -gt 120 ]; then
    kill "$pid" 2>/dev/null || true
    echo "e2e: timed out after 60 s" >&2
    cat "$log" >&2
    exit 1
  fi
  sleep 0.5
done

if ! wait "$pid"; then
  echo "e2e: electron exited non zero" >&2
  cat "$log" >&2
  exit 1
fi

cat "$log"

line=$(grep '^ephemeral-e2e: served=' "$log" | tail -1 || true)
[ -n "$line" ] || { echo "e2e: no probe line from the app" >&2; exit 1; }
printf '%s\n' "$line" | grep -q "served=$core_bytes bytes" || {
  echo "e2e: served bytes do not match the core size ($core_bytes)" >&2
  exit 1
}
printf '%s\n' "$line" | grep -q '"href":"app://core/index.html"' || {
  echo "e2e: the document URL is not app://core/index.html" >&2
  exit 1
}
printf '%s\n' "$line" | grep -q '"screen":"S0"' || {
  echo "e2e: the core did not boot to S0" >&2
  exit 1
}
printf '%s\n' "$line" | grep -q '"shell":"object"' || {
  echo "e2e: the preload bridge is missing" >&2
  exit 1
}
printf '%s\n' "$line" | grep -q '"badge":"ok"' || {
  echo "e2e: the IPC sender check rejected the pinned frame" >&2
  exit 1
}

echo
echo "RESULT: PASS, app://core served $core_bytes bytes from the pinned core and the page booted to S0"
