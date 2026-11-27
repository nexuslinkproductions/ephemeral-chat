# Wrapper lane self-check, run w21-ephemeral-repair-20261127, lane C

Scope: `03-build/output/wrapper/` only. Static files, plus one live run on the stock Electron
45.5.0 framework at
`/Users/marcelspatz/.hermes/cache/scratch/w5-electron/node_modules/electron/dist/Electron.app`.
No install, no packaged binary, no git command. All output below is copied from the commands
shown.

## Repair results

| Item | Result | What changed | Evidence |
|---|---|---|---|
| P-01 | PASS, measured live | `protocol.handle('app')` moved to `session.fromPartition('core')`; `url.origin` compare replaced by `isCoreUrl` (scheme, host, path); the IPC sender check uses the same predicate | live run below: `served=165744 bytes`, `href app://core/index.html`, `screen S0`, `badge ok` |
| P-02 | PASS, stock framework refused by the gate | `fuses.json` gains `requiredOff`; new `scripts/build-gate.sh` asserts the three fuses off and reads the binary; BUILD.md names fused binaries as the only shipped form and the in-code loop as defense in depth | gate run below: stock 45.5.0 reads RunAsNode Enabled, NodeOptions Enabled, NodeCliInspect Enabled, gate REFUSED |
| P-08 | PASS, measured | `hash-artifacts.sh` now walks every regular file at any depth, so an `.app` bundle is covered beside the dmg | bundle beside dmg test below, tamper detected |
| P-09 | PASS, measured refusal | `main.cjs` refuses to start when `EPHEMERAL_BUILD_HASH` is unset or not 64 lowercase hex; a dev hatch is unpackaged only; About reports `UNVERIFIED (development run, not a release build)`; build gate refuses both | refusal transcript below, exit 1 both ways |
| P-12 | PASS, code and static check | `will-download` on the core session, fixed extension allowlist, `path.basename` plus character allowlist, save under `<downloads>/ephemeral` with a non clobbering name | selfcheck section 15 |
| P-13 | PASS | one `COMMANDS` source in `menu.cjs`, preload forwards shape only; clipboard clear gated on window focus; `will-navigate` allows only exact `about:blank`; `sign-hashes.sh` comment fixed; BUILD.md pin text fixed | selfcheck sections 15 and 16 |

The headline P-01 live run, against the pinned wave-start artifact (sha `d4d48d37...`, 165,744
bytes), on the stock 45.5.0 framework:

```
ephemeral-e2e: served=165744 bytes electron=45.5.0 {"href":"app://core/index.html","title":"Ephemeral chat","screen":"S0","elements":112,"pageBytes":165813,"shell":"object","badge":"ok"}

RESULT: PASS, app://core served 165744 bytes from the pinned core and the page booted to S0
```

That line is measured inside the app: `servedBytes` is incremented in `serveCore` for the
response actually returned, `did-finish-load` proves the navigation completed, `screen S0` is
the core's own boot state, and `badge ok` is a real `shell.badge(true)` IPC round trip through
the new sender check.

P-02 gate run, with the frozen artifact as `--core` and the stock framework as `--app`:

```
== 1. build hash shape
build hash: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
== 2. fuse table
runAsNode, nodeOptions and nodeCliInspect are required off and are off in fuses.json
table ok
== 3. core pin
bytes:   165744
sha256:  d4d48d3711acc8a32ba1fca97faa02e2690bc2ef6ff3487434aba36c5c618742
in code: d4d48d3711acc8a32ba1fca97faa02e2690bc2ef6ff3487434aba36c5c618742
pin matches
== 4. fuse read on the shipped binary
Analyzing app: Electron.app
Fuse Version: v1
  RunAsNode is Enabled
  EnableCookieEncryption is Disabled
  EnableNodeOptionsEnvironmentVariable is Enabled
  EnableNodeCliInspectArguments is Enabled
  EnableEmbeddedAsarIntegrityValidation is Disabled
  OnlyLoadAppFromAsar is Disabled
  LoadBrowserProcessSpecificV8Snapshot is Disabled
  GrantFileProtocolExtraPrivileges is Enabled
  WasmTrapHandlers is Enabled
REFUSED: RunAsNode is not Disabled on .../Electron.app. This binary cannot ship.
EXIT=1
```

P-08 bundle beside dmg:

```
520f24e876ac721b8afeb937bc51a716c9f7f5762fa42f9b982c0c6efd4af68c  ephemeral.app/Contents/MacOS/ephemeral
54cf25904acf2628db2a19df10603f844fd80d775ee228b382a58a968648c56f  ephemeral.app/Contents/Resources/Electron Helper (GPU).txt
f19e67cc530964a7bb352c065ad84f22e44bd163aa1bbab198872535873aad59  ephemeral.dmg
ephemeral.app/Contents/MacOS/ephemeral: OK
ephemeral.app/Contents/Resources/Electron Helper (GPU).txt: OK
ephemeral.dmg: OK
tamper detected, verify exit nonzero
```

P-09 start refusal:

```
--- unset ---
ephemeral: refusing to start: EPHEMERAL_BUILD_HASH must be 64 hex characters
EXIT=1
--- malformed ---
ephemeral: refusing to start: EPHEMERAL_BUILD_HASH must be 64 hex characters
EXIT=1
```

## Cards

| Card | Result | Evidence |
|---|---|---|
| BC-W1 | PASS | selfcheck section 7: 18 required options, 0 banned constructs |
| BC-W2 | PASS | selfcheck section 8 plus the live `badge ok` round trip |
| BC-W3 | PASS | selfcheck sections 7 and 15; `about:blank` allowed by predicate, all else denied |
| BC-W4 | PASS, live | pin matches the wave-start artifact; live run serves 165,744 bytes at `app://core/index.html` |
| BC-W5 | PASS, table and gate; fused binary read is the named limit | selfcheck sections 6 and 16 |
| BC-W6 | PASS | `45.5.0` pin; About shows both hashes and the unverified state when applicable |
| BC-W7 | PASS for the script path | selfcheck section 12; verifier calls minisign and the system hash tool only |
| BC-W8 | PASS | selfcheck section 11; no updater symbol |
| BC-W14 | PASS | single instance lock, four refused switches, DevTools behind the flag; P-09 adds the hash refusal |
| UX-09 | PASS | selfcheck section 10 |
| UX-10 | PASS | selfcheck section 9 |
| R2-13 | PASS | no relay host in any runtime file |

## Full self-check transcript

Command: `ELECTRON_BIN=<stock Electron> EPHEMERAL_CORE=<frozen artifact> sh scripts/selfcheck.sh`
in `03-build/output/wrapper`.

```
== 1. inventory
PASS exists package.json
PASS exists main.cjs
PASS exists preload.cjs
PASS exists menu.cjs
PASS exists qr.cjs
PASS exists fuses.json
PASS exists BUILD.md
PASS exists SELF-CHECK.md
PASS exists scripts/fuses.sh
PASS exists scripts/hash-artifacts.sh
PASS exists scripts/sign-hashes.sh
PASS exists scripts/verify-artifacts.sh
PASS exists scripts/pin-core.sh
PASS exists scripts/selfcheck.sh
PASS exists scripts/build-gate.sh
PASS exists scripts/e2e-core-load.sh
== 2. node syntax
PASS node --check main.cjs
PASS node --check menu.cjs
PASS node --check preload.cjs
PASS node --check qr.cjs
== 3. json validity
PASS json fuses.json
PASS json package.json
== 4. ascii and dash scan of the whole tree
non ascii bytes: 0, dash chars: 0, curly chars: 0
PASS ascii only, no em or en dash
== 5. BC card map
PASS BC-W1 named in 4 files
PASS BC-W2 named in 4 files
PASS BC-W3 named in 3 files
PASS BC-W4 named in 5 files
PASS BC-W5 named in 6 files
PASS BC-W6 named in 3 files
PASS BC-W7 named in 5 files
PASS BC-W8 named in 4 files
== 6. fuse table at the BC-W5 positions
9 of 9 fuses at the BC-W5 positions, cookieEncryption disabled per blueprint 6.6
PASS fuse table complete
== 7. window and runtime option static scan
18 required options present, 0 banned constructs
PASS BC-W1 to BC-W4 option scan
== 8. bridge surface
one bridge object, two invoke verbs, no raw transport exposure
PASS BC-W2 bridge surface
== 9. QR ceiling and scan contract
997 accepted, 998 refused, scan requires user intent and a paste fallback
PASS UX-10 ceiling
== 10. menu surface
no reload, no zoom, wipe without accelerator, devtools behind the build flag only
PASS UX-09 menu surface
== 11. update path and relay isolation
no auto updater symbol and no relay host in any runtime file
PASS BC-W8 and R2-13 isolation
== 12. signature path shares no download code
verifier calls minisign and the system hash tool only
PASS BC-W7 verifier independence
== 13. shell script syntax
PASS sh -n build-gate.sh
PASS sh -n e2e-core-load.sh
PASS sh -n fuses.sh
PASS sh -n hash-artifacts.sh
PASS sh -n pin-core.sh
PASS sh -n selfcheck.sh
PASS sh -n sign-hashes.sh
PASS sh -n verify-artifacts.sh
== 14. core pin shape
CORE_SHA256 present, 64 hex characters, placeholder state: pinned
PASS BC-W4 pin shape
== 15. shell repair surface, P-01 P-09 P-12 P-13
core partition handler, app scheme predicate, download sink, about:blank predicate, focus gated clipboard, release hash gate, one COMMANDS source
PASS P-01 P-09 P-12 P-13 static surface
== 16. build gate behaviour
PASS build gate refused a core pin mismatch (pin is committed at integration)
PASS build gate refuses an unset hash
PASS build gate refuses a malformed hash
== 17. P-01 live core load, optional
ephemeral-e2e: served=165744 bytes electron=45.5.0 {"href":"app://core/index.html","title":"Ephemeral chat","screen":"S0","elements":112,"pageBytes":165813,"shell":"object","badge":"ok"}

RESULT: PASS, app://core served 165744 bytes from the pinned core and the page booted to S0
PASS live app://core load on the stock framework

RESULT: PASS
```

Exit code: `EXIT=0`.

## Named limits

- No fused release binary exists in this round, so the passing side of the `@electron/fuses`
  read is not exercised. The stock framework read runs and is refused, which proves the gate.
- P-12's download sink is static checked only. A runtime proof needs a live peer transfer to
  produce a save link; the receipt path is not exercised in this lane.
- The `about:blank` eviction allow (WB-04, P-13) is code checked only. Reaching it at runtime
  needs a completed peer session that calls `endSession`, which this lane did not run.
- The live P-01 run uses the frozen wave-start artifact (`d4d48d37...`, 165,744 bytes), the
  target under pentest. The live core file was mid edit by the CORE lane (169,810 bytes at
  check time), so it does not match the committed pin. The pin is updated at integration by
  `scripts/pin-core.sh`, and `build-gate.sh` refuses until it matches; selfcheck section 16
  records that refusal as the correct behaviour.
- The core pin in `main.cjs` is the reviewed V2 artifact, not the in flight repair. This is
  deliberate: pinning a file another lane is writing would ship a stale hash.
