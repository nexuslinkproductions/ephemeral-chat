#!/bin/sh
# Build gate. A release build must pass every check here before it is packaged, and the
# release evidence records the output. It refuses, it does not warn.
#
#   1. P-09, WB-08: EPHEMERAL_BUILD_HASH is 64 lowercase hex characters.
#   2. P-02, BC-W5: fuses.json keeps runAsNode, nodeOptions and nodeCliInspect off, and with
#      --app the actual binary reports all three Disabled through @electron/fuses read.
#   3. BC-W4: main.cjs carries the SHA-256 of the current core file.
#
# The in-code debug switch loop in main.cjs is defense in depth, not the control. A stock
# Electron framework reports all three fuses enabled, so this gate refuses it (F-ENV-3).
#
# Usage: sh scripts/build-gate.sh [--core <core html>] [--app <packaged app, framework or electron binary>]
set -eu

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
app=""
core="$here/../../ephemeral-chat-v2.html"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --app)
      shift
      app=${1:-}
      ;;
    --core)
      shift
      core=${1:-}
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 2
      ;;
  esac
  shift
done

refuse() {
  echo "REFUSED: $1" >&2
  exit 1
}

echo "== 1. build hash shape"
build_hash=${EPHEMERAL_BUILD_HASH:-}
if [ -z "$build_hash" ]; then
  refuse "EPHEMERAL_BUILD_HASH is unset. A release build carries its 64 hex character hash."
fi
if ! printf '%s' "$build_hash" | grep -Eq '^[0-9a-f]{64}$'; then
  refuse "EPHEMERAL_BUILD_HASH is not 64 lowercase hex characters."
fi
echo "build hash: $build_hash"

echo "== 2. fuse table"
if python3 - "$here/../fuses.json" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="ascii") as handle:
    data = json.load(handle)
required = data.get("requiredOff", [])
got = data.get("fuses", {})
want = ["runAsNode", "nodeOptions", "nodeCliInspect"]
missing = [name for name in want if name not in required]
wrong = [name for name in want if got.get(name) is not False]
if missing or wrong:
    print("requiredOff missing=%s fuses not off=%s" % (missing, wrong))
    sys.exit(1)
print("runAsNode, nodeOptions and nodeCliInspect are required off and are off in fuses.json")
PY
then
  echo "table ok"
else
  refuse "fuses.json does not require the three node entry points off."
fi

echo "== 3. core pin"
if [ -z "$core" ]; then
  refuse "--core is empty."
fi
if ! sh "$here/pin-core.sh" "$core"; then
  refuse "main.cjs does not carry the current core hash."
fi

if [ -n "$app" ]; then
  echo "== 4. fuse read on the shipped binary"
  [ -e "$app" ] || refuse "no such app: $app"
  read_out=$(sh "$here/fuses.sh" read --app "$app" 2>&1) || {
    printf '%s\n' "$read_out" >&2
    refuse "the fuse reader failed on $app."
  }
  printf '%s\n' "$read_out"
  for name in RunAsNode EnableNodeOptionsEnvironmentVariable EnableNodeCliInspectArguments; do
    printf '%s\n' "$read_out" | grep -q "$name is Disabled" || {
      refuse "$name is not Disabled on $app. This binary cannot ship."
    }
  done
  echo "all three node entry point fuses are Disabled on the shipped binary"
else
  echo "== 4. fuse read skipped (no --app), static table only"
fi

echo
echo "RESULT: PASS"
