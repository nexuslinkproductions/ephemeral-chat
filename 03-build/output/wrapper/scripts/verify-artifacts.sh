#!/bin/sh
# BC-W7 and BC-W8: the manual replacement verifier. It shares no code with the downloader,
# performs no network access, and is the only thing a user has to run. Signature first, then
# the per artifact hash. If the signature fails, no hash is trusted and the script stops.
# Usage: sh scripts/verify-artifacts.sh <SHA256SUMS> <SHA256SUMS.minisig> <minisign.pub> [artifact-dir]
set -eu

sums=${1:-}
sig=${2:-}
pub=${3:-}
dir=${4:-}

if [ -z "$sums" ] || [ -z "$sig" ] || [ -z "$pub" ]; then
  echo "usage: verify-artifacts.sh <SHA256SUMS> <SHA256SUMS.minisig> <minisign.pub> [artifact-dir]" >&2
  exit 2
fi
[ -n "$dir" ] || dir=$(dirname -- "$sums")

for file in "$sums" "$sig" "$pub"; do
  [ -f "$file" ] || { echo "missing $file" >&2; exit 2; }
done
[ -d "$dir" ] || { echo "missing artifact directory: $dir" >&2; exit 2; }

sums_abs=$(CDPATH= cd -- "$(dirname -- "$sums")" && pwd)/$(basename -- "$sums")

echo "step 1: detached signature over the hash list"
minisign -Vm "$sums_abs" -x "$sig" -p "$pub"

echo "step 2: per artifact SHA-256"
cd "$dir"
if command -v sha256sum >/dev/null 2>&1; then
  sha256sum -c "$sums_abs"
else
  shasum -a 256 -c "$sums_abs"
fi

echo "step 3: reminder, not a check"
echo "the hash proves the file is the reviewed one; it does not prove who built it"
