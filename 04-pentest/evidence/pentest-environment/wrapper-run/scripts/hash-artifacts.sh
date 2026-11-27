#!/bin/sh
# BC-W7: build SHA256SUMS for a directory of release artifacts.
# Sorted with LC_ALL=C so the file is reproducible, and never includes itself.
# Usage: sh scripts/hash-artifacts.sh <artifact-dir> [output-file]
set -eu

dir=${1:?usage: hash-artifacts.sh <artifact-dir> [output-file]}
out=${2:-}

[ -d "$dir" ] || { echo "not a directory: $dir" >&2; exit 2; }
[ -n "$out" ] || out="$dir/SHA256SUMS"
out_abs=$(CDPATH= cd -- "$(dirname -- "$out")" && pwd)/$(basename -- "$out")

(
  cd "$dir"
  find . -maxdepth 1 -type f ! -name 'SHA256SUMS' ! -name 'SHA256SUMS.minisig' -print |
    sed 's|^\./||' |
    LC_ALL=C sort |
    while IFS= read -r file; do
      if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$file"
      else
        shasum -a 256 "$file"
      fi
    done
) > "$out_abs"

echo "wrote $out_abs"
