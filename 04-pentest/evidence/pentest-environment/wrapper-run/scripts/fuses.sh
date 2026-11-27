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

flags=$(python3 - "$config" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="ascii") as handle:
    data = json.load(handle)
pairs = []
for name, value in data["fuses"].items():
    pairs.append("%s=%s" % (name, "on" if value else "off"))
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
