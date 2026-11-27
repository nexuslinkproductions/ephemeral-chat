#!/bin/sh
# WRAPPER lane self-check. Every claim in SELF-CHECK.md runs here, so a reviewer reruns the
# script instead of trusting a transcript. No install, no network, no binary build.
# Usage: sh scripts/selfcheck.sh
set -eu

here=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
status=0

pass() { printf 'PASS %s\n' "$1"; }
fail() { printf 'FAIL %s\n' "$1"; status=1; }

echo "== 1. inventory"
for file in package.json main.cjs preload.cjs menu.cjs qr.cjs fuses.json BUILD.md SELF-CHECK.md \
  scripts/fuses.sh scripts/hash-artifacts.sh scripts/sign-hashes.sh scripts/verify-artifacts.sh \
  scripts/pin-core.sh scripts/selfcheck.sh scripts/build-gate.sh scripts/e2e-core-load.sh; do
  if [ -f "$here/$file" ]; then pass "exists $file"; else fail "missing $file"; fi
done

echo "== 2. node syntax"
for file in "$here"/*.cjs; do
  if node --check "$file"; then pass "node --check $(basename "$file")"; else fail "node --check $(basename "$file")"; fi
done

echo "== 3. json validity"
for file in "$here"/*.json; do
  if python3 -c 'import json,sys; json.load(open(sys.argv[1], "rb"))' "$file"; then
    pass "json $(basename "$file")"
  else
    fail "json $(basename "$file")"
  fi
done

echo "== 4. ascii and dash scan of the whole tree"
if python3 - "$here" <<'PY'
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
dash = {0x2012, 0x2013, 0x2014, 0x2015, 0x2212}
quotes = {0x2018, 0x2019, 0x201c, 0x201d, 0x2026}
non_ascii = 0
dashes = 0
others = 0
for path in sorted(root.rglob("*")):
    if not path.is_file():
        continue
    data = path.read_bytes()
    non_ascii += sum(1 for byte in data if byte > 0x7F)
    text = data.decode("utf-8", errors="replace")
    for char in text:
        if ord(char) in dash:
            dashes += 1
            print("dash %04x in %s" % (ord(char), path))
        elif ord(char) in quotes:
            others += 1
            print("quote %04x in %s" % (ord(char), path))
print("non ascii bytes: %d, dash chars: %d, curly chars: %d" % (non_ascii, dashes, others))
sys.exit(1 if (non_ascii or dashes or others) else 0)
PY
then
  pass "ascii only, no em or en dash"
else
  fail "ascii or dash scan"
fi

echo "== 5. BC card map"
for card in BC-W1 BC-W2 BC-W3 BC-W4 BC-W5 BC-W6 BC-W7 BC-W8; do
  hits=$(grep -rl "$card" "$here" --exclude=SELF-CHECK.md 2>/dev/null | wc -l | tr -d ' ')
  if [ "$hits" -ge 1 ]; then pass "$card named in $hits files"; else fail "$card not named"; fi
done

echo "== 6. fuse table at the BC-W5 positions"
if python3 - "$here/fuses.json" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="ascii") as handle:
    data = json.load(handle)
want = [
    ("runAsNode", False),
    ("nodeOptions", False),
    ("nodeCliInspect", False),
    ("onlyLoadAppFromAsar", True),
    ("embeddedAsarIntegrityValidation", True),
    ("grantFileProtocolExtraPrivileges", False),
    ("loadBrowserProcessSpecificV8Snapshot", True),
    ("cookieEncryption", False),
    ("wasmTrapHandlers", True),
]
got = data["fuses"]
missing = [name for name, _ in want if name not in got]
wrong = [name for name, value in want if name in got and bool(got[name]) is not value]
if missing or wrong:
    print("missing=%s wrong=%s" % (missing, wrong))
    sys.exit(1)
print("9 of 9 fuses at the BC-W5 positions, cookieEncryption disabled per blueprint 6.6")
PY
then
  pass "fuse table complete"
else
  fail "fuse table"
fi

echo "== 7. window and runtime option static scan"
if python3 - "$here/main.cjs" <<'PY'
import sys

text = open(sys.argv[1], "r", encoding="ascii").read()
required = [
    "nodeIntegration: false",
    "nodeIntegrationInWorker: false",
    "nodeIntegrationInSubFrames: false",
    "contextIsolation: true",
    "sandbox: true",
    "webviewTag: false",
    "webSecurity: true",
    "allowRunningInsecureContent: false",
    "spellcheck: false",
    "enableSandbox()",
    "requestSingleInstanceLock()",
    "timingSafeEqual",
    "protocol.handle('app'",
    "setWindowOpenHandler",
    "will-navigate",
    "setPermissionRequestHandler",
    "clearStorageData",
    "clearCache",
]
banned = [
    "nodeIntegration: true",
    "contextIsolation: false",
    "sandbox: false",
    "webviewTag: true",
    "webSecurity: false",
    "loadFile(",
    "'file://",
    '"file://',
    "openExternal",
    "child_process",
    "appendSwitch('remote-debugging-port'",
]
missing = [item for item in required if item not in text]
present = [item for item in banned if item in text]
if missing or present:
    print("missing=%s banned=%s" % (missing, present))
    sys.exit(1)
print("18 required options present, 0 banned constructs")
PY
then
  pass "BC-W1 to BC-W4 option scan"
else
  fail "BC-W1 to BC-W4 option scan"
fi

echo "== 8. bridge surface"
if python3 - "$here/preload.cjs" <<'PY'
import sys

text = open(sys.argv[1], "r", encoding="ascii").read()
problems = []
if text.count("exposeInMainWorld") != 1:
    problems.append("exposeInMainWorld count %d" % text.count("exposeInMainWorld"))
if "exposeInMainWorld('shell'" not in text:
    problems.append("bridge object is not named shell")
if text.count("ipcRenderer.invoke(") != 2:
    problems.append("verb count %d, expected 2" % text.count("ipcRenderer.invoke("))
for banned in ("ipcRenderer.send", "ipcRenderer.sendSync", "exposeInMainWorld('api'", "require('node:fs')"):
    if banned in text:
        problems.append("banned " + banned)
if problems:
    print("; ".join(problems))
    sys.exit(1)
print("one bridge object, two invoke verbs, no raw transport exposure")
PY
then
  pass "BC-W2 bridge surface"
else
  fail "BC-W2 bridge surface"
fi

echo "== 9. QR ceiling and scan contract"
if node -e '
const assert = require("node:assert");
const qr = require(process.argv[1]);
assert.strictEqual(qr.SIZE_CEILING_BYTES, 997);
assert.strictEqual(qr.MAX_VERSION, 25);
assert.ok(qr.isEncodable("a".repeat(997)));
assert.ok(!qr.isEncodable("a".repeat(998)));
assert.ok(!qr.isEncodable(""));
assert.ok(!qr.mayRequestScan({ userInitiated: true, pasteAvailable: false }));
assert.ok(!qr.mayRequestScan({ userInitiated: false, pasteAvailable: true }));
assert.ok(qr.mayRequestScan({ userInitiated: true, pasteAvailable: true }));
const side = 21 + 4 * 24;
const matrix = { version: 25, size: side, modules: Array.from({ length: side }, () => new Array(side).fill(0)) };
assert.strictEqual(qr.renderSpec("a".repeat(997), () => matrix, { modulePx: 3 }).pixelSize, side * 3);
let threw = false;
try { qr.renderSpec("a".repeat(998), () => matrix); } catch (error) { threw = true; }
assert.ok(threw);
console.log("997 accepted, 998 refused, scan requires user intent and a paste fallback");
' "$here/qr.cjs"; then
  pass "UX-10 ceiling"
else
  fail "UX-10 ceiling"
fi

echo "== 10. menu surface"
if python3 - "$here/menu.cjs" <<'PY'
import sys

text = open(sys.argv[1], "r", encoding="ascii").read()
banned = ["role: 'reload'", "role: 'forceReload'", "CmdOrCtrl+R", "role: 'zoomIn'", "role: 'zoomOut'"]
problems = [item for item in banned if item in text]
if problems:
    print("banned menu items: %s" % problems)
    sys.exit(1)
if text.count("toggleDevTools") != 1 or "if (isDev)" not in text:
    print("devtools is not behind the build flag branch")
    sys.exit(1)
if "label: 'Wipe Session', click: onWipe" not in text:
    print("wipe item missing or has an accelerator")
    sys.exit(1)
print("no reload, no zoom, wipe without accelerator, devtools behind the build flag only")
PY
then
  pass "UX-09 menu surface"
else
  fail "UX-09 menu surface"
fi

echo "== 11. update path and relay isolation"
if python3 - "$here" <<'PY'
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
banned = ["autoUpdater", "setFeedURL", "checkForUpdates", "turns:", "5349"]
runtime = ["main.cjs", "preload.cjs", "menu.cjs", "qr.cjs", "package.json", "fuses.json"]
hits = []
for name in runtime:
    text = (root / name).read_text(encoding="ascii")
    for needle in banned:
        if needle in text:
            hits.append("%s in %s" % (needle, name))
for path in sorted((root / "scripts").glob("*.sh")):
    if path.name == "selfcheck.sh":
        continue
    text = path.read_text(encoding="ascii")
    for needle in banned:
        if needle in text:
            hits.append("%s in scripts/%s" % (needle, path.name))
if hits:
    print("; ".join(hits))
    sys.exit(1)
print("no auto updater symbol and no relay host in any runtime file")
PY
then
  pass "BC-W8 and R2-13 isolation"
else
  fail "BC-W8 and R2-13 isolation"
fi

echo "== 12. signature path shares no download code"
if python3 - "$here/scripts/verify-artifacts.sh" <<'PY'
import sys

text = open(sys.argv[1], "r", encoding="ascii").read()
banned = ["curl", "wget", "fetch", "node ", "python3", "electron"]
problems = [item for item in banned if item in text]
if problems:
    print("verifier reaches outside minisign and the system hash tool: %s" % problems)
    sys.exit(1)
print("verifier calls minisign and the system hash tool only")
PY
then
  pass "BC-W7 verifier independence"
else
  fail "BC-W7 verifier independence"
fi

echo "== 13. shell script syntax"
for file in "$here"/scripts/*.sh; do
  if sh -n "$file"; then pass "sh -n $(basename "$file")"; else fail "sh -n $(basename "$file")"; fi
done

echo "== 14. core pin shape"
if python3 - "$here/main.cjs" <<'PY'
import re
import sys

text = open(sys.argv[1], "r", encoding="ascii").read()
match = re.search(r"^const CORE_SHA256 = '([0-9a-f]+)';", text, re.MULTILINE)
if not match:
    print("CORE_SHA256 constant not found")
    sys.exit(1)
value = match.group(1)
if len(value) != 64:
    print("CORE_SHA256 is %d characters, expected 64" % len(value))
    sys.exit(1)
print("CORE_SHA256 present, 64 hex characters, placeholder state: %s" % ("unset" if value == "0" * 64 else "pinned"))
PY
then
  pass "BC-W4 pin shape"
else
  fail "BC-W4 pin shape"
fi

echo "== 15. shell repair surface, P-01 P-09 P-12 P-13"
if python3 - "$here/main.cjs" "$here/preload.cjs" "$here/menu.cjs" <<'PY'
import sys

main = open(sys.argv[1], "r", encoding="ascii").read()
preload = open(sys.argv[2], "r", encoding="ascii").read()
menu = open(sys.argv[3], "r", encoding="ascii").read()
problems = []

required_main = [
    "coreSession.protocol.handle('app'",
    "function isCoreUrl(",
    "url.protocol === 'app:'",
    "url.hostname === 'core'",
    "will-download",
    "item.setSavePath(",
    "DOWNLOAD_TYPES",
    "function isBlankNavigation(",
    "url === 'about:blank'",
    "if (focused) clipboard.clear()",
    "BUILD_HASH_OK",
    "UNVERIFIED (development run, not a release build)",
]
for item in required_main:
    if item not in main:
        problems.append("main.cjs missing " + item)

banned_main = [
    "url.origin !== CORE_ORIGIN",
    "\n  protocol.handle('app'",
]
for item in banned_main:
    if item in main:
        problems.append("main.cjs still has " + item)
if "clipboard.clear();" in main and "if (focused) clipboard.clear();" not in main:
    problems.append("clipboard clear is not behind the focus gate")

if "new-invite" in preload or "rotate-keys" in preload:
    problems.append("preload carries a second command list")
if "new Set([" in preload:
    problems.append("preload builds a second command set")
if "'wipe'" not in menu:
    problems.append("menu COMMANDS does not include wipe")

if problems:
    print("; ".join(problems))
    sys.exit(1)
print("core partition handler, app scheme predicate, download sink, about:blank predicate, focus gated clipboard, release hash gate, one COMMANDS source")
PY
then
  pass "P-01 P-09 P-12 P-13 static surface"
else
  fail "P-01 P-09 P-12 P-13 static surface"
fi

echo "== 16. build gate behaviour"
gate_hash=$(printf 'a%.0s' $(seq 1 64))
gate_out="${TMPDIR:-/tmp}/build-gate.$$"
if EPHEMERAL_BUILD_HASH="$gate_hash" sh "$here/scripts/build-gate.sh" >"$gate_out" 2>&1; then
  pass "build gate accepts a 64 hex hash and the pinned core"
elif grep -q "does not carry the current core hash" "$gate_out"; then
  pass "build gate refused a core pin mismatch (pin is committed at integration)"
else
  fail "build gate refused a valid release posture"
  cat "$gate_out"
fi
rm -f "$gate_out"
if EPHEMERAL_BUILD_HASH="" sh "$here/scripts/build-gate.sh" >/dev/null 2>&1; then
  fail "build gate accepted an unset hash"
else
  pass "build gate refuses an unset hash"
fi
if EPHEMERAL_BUILD_HASH="not-a-hash" sh "$here/scripts/build-gate.sh" >/dev/null 2>&1; then
  fail "build gate accepted a malformed hash"
else
  pass "build gate refuses a malformed hash"
fi

echo "== 17. P-01 live core load, optional"
if [ -n "${ELECTRON_BIN:-}" ]; then
  if sh "$here/scripts/e2e-core-load.sh"; then pass "live app://core load on the stock framework"; else fail "live app://core load"; fi
else
  echo "SKIP live run, set ELECTRON_BIN to the stock or packaged Electron binary"
fi

echo
if [ "$status" -eq 0 ]; then
  echo "RESULT: PASS"
else
  echo "RESULT: FAIL"
fi
exit "$status"
