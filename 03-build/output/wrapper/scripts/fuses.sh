#!/bin/sh
# BC-W5 fuse flipper and reader. The static table lives in ../fuses.json so the decision is
# readable without running anything.
# Usage: sh scripts/fuses.sh <read|write|flags> --app <installed app or electron binary>
set -eu

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
config="$here/../fuses.json"
mode=${1:-}
shift || true

app=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --app)
      shift
      app=${1:-}
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 2
      ;;
  esac
  shift
done

usage() {
  echo "usage: fuses.sh <read|write|flags> --app <path>" >&2
  exit 2
}

[ -n "$mode" ] || usage
[ -f "$config" ] || { echo "missing config: $config" >&2; exit 2; }

# fuses.json uses lowerCamel keys for readability. @electron/fuses 2.1.3 accepts only the
# enum names below, and an unmapped name is a hard error there, so map every row and refuse
# an unknown key here instead of shipping a write that cannot flip anything (REL-L1).
flags=$(python3 - "$config" <<'PY'
import json
import sys

NAMES = {
    "runAsNode": "RunAsNode",
    "nodeOptions": "EnableNodeOptionsEnvironmentVariable",
    "nodeCliInspect": "EnableNodeCliInspectArguments",
    "onlyLoadAppFromAsar": "OnlyLoadAppFromAsar",
    "embeddedAsarIntegrityValidation": "EnableEmbeddedAsarIntegrityValidation",
    "grantFileProtocolExtraPrivileges": "GrantFileProtocolExtraPrivileges",
    "loadBrowserProcessSpecificV8Snapshot": "LoadBrowserProcessSpecificV8Snapshot",
    "cookieEncryption": "EnableCookieEncryption",
    "wasmTrapHandlers": "WasmTrapHandlers",
}

with open(sys.argv[1], "r", encoding="ascii") as handle:
    data = json.load(handle)
unknown = [key for key in data["fuses"] if key not in NAMES]
if unknown:
    raise SystemExit("unmapped fuse name(s): %s" % ", ".join(unknown))
pairs = []
for name, value in data["fuses"].items():
    pairs.append("%s=%s" % (NAMES[name], "on" if value else "off"))
print(" ".join(pairs))
PY
)

case "$mode" in
  read)
    [ -n "$app" ] || usage
    exec npx --yes @electron/fuses@2.1.3 read --app "$app"
    ;;
  write)
    [ -n "$app" ] || usage
    # Word splitting on $flags is intended: it is a list of Name=on flags built above.
    # shellcheck disable=SC2086
    exec npx --yes @electron/fuses@2.1.3 write --app "$app" $flags
    ;;
  flags)
    echo "$flags"
    ;;
  *)
    echo "unknown mode: $mode (read, write, flags)" >&2
    exit 2
    ;;
esac
