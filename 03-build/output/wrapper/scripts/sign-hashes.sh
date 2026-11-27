#!/bin/sh
# BC-W7: detached signature over SHA256SUMS. minisign by default, cosign with SIGNER=cosign.
# The private key never lives in the repository. The public key ships in the repo and in the
# About panel, so a verifier needs nothing from the release page.
# Usage: sh scripts/sign-hashes.sh <SHA256SUMS> [secret-key]
set -eu

sums=${1:?usage: sign-hashes.sh <SHA256SUMS> [secret-key]}
key=${2:-${MINISIGN_KEY:-}}

[ -f "$sums" ] || { echo "missing $sums" >&2; exit 2; }

if [ "${SIGNER:-minisign}" = "cosign" ]; then
  cosign sign-blob --yes ${key:+--key "$key"} --bundle "$sums.cosign.bundle" "$sums"
  echo "wrote $sums.cosign.bundle"
  exit 0
fi

[ -n "$key" ] || { echo "missing minisign secret key (arg 2 or MINISIGN_KEY)" >&2; exit 2; }
rm -f "$sums.minisig"
minisign -Sm "$sums" -s "$key"
echo "wrote $sums.minisig"
