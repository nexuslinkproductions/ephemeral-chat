#!/bin/sh
# BC-W4 layer 3 build input. Prints the SHA-256 of the reviewed core and fails when main.cjs
# holds a different constant. Build order is the rule: build the core, hash it, commit the
# constant, then build the shell. A hash computed after packaging is self referential.
# Usage: sh scripts/pin-core.sh <core html>
set -eu

core=${1:?usage: pin-core.sh <core html>}
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
main="$here/../main.cjs"

[ -f "$core" ] || { echo "missing core: $core" >&2; exit 2; }
[ -f "$main" ] || { echo "missing main.cjs" >&2; exit 2; }

if command -v sha256sum >/dev/null 2>&1; then
  hash=$(sha256sum "$core" | cut -d' ' -f1)
else
  hash=$(shasum -a 256 "$core" | cut -d' ' -f1)
fi
current=$(sed -n "s/^const CORE_SHA256 = '\([0-9a-f]*\)';.*/\1/p" "$main")

echo "core:    $core"
echo "bytes:   $(wc -c < "$core" | tr -d ' ')"
echo "sha256:  $hash"
echo "in code: $current"

if [ "$hash" != "$current" ]; then
  echo "MISMATCH: set CORE_SHA256 = '$hash' in main.cjs, then rebuild the shell." >&2
  exit 1
fi
echo "pin matches"
