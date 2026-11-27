#!/bin/sh
# BC-W7 and P-08: build SHA256SUMS for a directory of release artifacts.
# Every regular file at any depth is listed, so an .app bundle is covered file by file next
# to the dmg. Sorted with LC_ALL=C so the file is reproducible, and never includes itself.
# Symlinks inside a bundle are not hashed: they are metadata, and the target file is listed.
# Usage: sh scripts/hash-artifacts.sh <artifact-dir> [output-file]
set -eu

dir=${1:?usage: hash-artifacts.sh <artifact-dir> [output-file]}
out=${2:-}

[ -d "$dir" ] || { echo "not a directory: $dir" >&2; exit 2; }
[ -n "$out" ] || out="$dir/SHA256SUMS"
out_abs=$(CDPATH= cd -- "$(dirname -- "$out")" && pwd)/$(basename -- "$out")
tmp="${TMPDIR:-/tmp}/sha256sums.$$"
trap 'rm -f "$tmp"' EXIT INT TERM

hash_file() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1"
  else
    shasum -a 256 "$1"
  fi
}

(
  cd "$dir"
  find . -type f ! -name 'SHA256SUMS' ! -name 'SHA256SUMS.minisig' -print |
    sed 's|^\./||' |
    LC_ALL=C sort |
    while IFS= read -r file; do
      hash_file "$file"
    done
) > "$tmp"

mv "$tmp" "$out_abs"
trap - EXIT INT TERM
echo "wrote $out_abs"
