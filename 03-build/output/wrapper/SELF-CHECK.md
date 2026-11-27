# Wrapper lane self-check, run w11-ephemeral-build-r2a-20261127

Scope: `03-build/output/wrapper/` and `03-build/output/cover/`. Static files only. No install,
no binary build, no `electron-builder` run. All output below is copied from the commands shown.

One naming note: the brief calls the entry file `main.js`. The file here is `main.cjs`, the name
blueprint 6.1 (and `11-packaging-executable.md` 7.2 and 9.3) uses for the shell's trusted
computing base: `main.cjs`, `preload.cjs`, the core HTML. `package.json` `main` points at it.

## Card results

| Card | Result | Command | Raw output |
|---|---|---|---|
| BC-W1 closed window options, `enableSandbox` before ready | PASS | `node --check main.cjs` plus selfcheck section 7 | `18 required options present, 0 banned constructs` |
| BC-W2 one bridge, primitive arguments, sender check | PASS | selfcheck section 8 | `one bridge object, two invoke verbs, no raw transport exposure` |
| BC-W3 deny navigation, frames, webviews, window creation | PASS | selfcheck section 7 plus grep of the handlers | `will-navigate`, `will-frame-navigate`, `will-attach-webview`, `setWindowOpenHandler` all present and denying; `0 banned constructs` |
| BC-W4 `app://` serving the pinned buffer, no `file://` | PASS (pin unset, fails closed) | selfcheck sections 7 and 14, plus `scripts/pin-core.sh` | `CORE_SHA256 present, 64 hex characters, placeholder state: unset`; `MISMATCH: set CORE_SHA256 = '23be3a0b...' in main.cjs` exit 1 |
| BC-W5 every production fuse | PASS (table and command), binary read blocked this round | `sh scripts/fuses.sh flags --app /tmp/none` | `runAsNode=off nodeOptions=off nodeCliInspect=off onlyLoadAppFromAsar=on embeddedAsarIntegrityValidation=on grantFileProtocolExtraPrivileges=off loadBrowserProcessSpecificV8Snapshot=on cookieEncryption=off wasmTrapHandlers=on` |
| BC-W6 exact pin, About string, SLA | PASS | `node -p "require('./package.json').devDependencies.electron"` | `45.5.0` |
| BC-W7 detached signature and hash path | PASS for the script path, release evidence deferred | `scripts/hash-artifacts.sh` roundtrip plus selfcheck section 12 | `a.txt: OK`, `b.txt: OK`; `verifier calls minisign and the system hash tool only` |
| BC-W8 no updater, manual replacement policy | PASS | selfcheck section 11 plus `UPDATE-POLICY.md` | `no auto updater symbol and no relay host in any runtime file` |
| BC-W14 single instance, no debugger switch, DevTools flag | PASS | static scan of `main.cjs` | `requestSingleInstanceLock()`, four refused switches, `DEVTOOLS` false when packaged |
| UX-09 menu, shortcuts, badge | PASS | selfcheck section 10 | `no reload, no zoom, wipe without accelerator, devtools behind the build flag only` |
| UX-10 QR ceiling and scan contract | PASS | selfcheck section 9 | `997 accepted, 998 refused, scan requires user intent and a paste fallback` |
| R2-13 cover config, no relay in the default tree | PASS | selfcheck section 11 plus `cover/relay.env.example` | `no auto updater symbol and no relay host in any runtime file` |

Two honest gaps, both by round scope rather than by defect:

1. `CORE_SHA256` is the all zero placeholder because the pin is a build input committed at
   integration, after the CORE lane's `ephemeral-chat-v2.html` is final (`11-packaging-executable.md`
   section 10 build order). The constant fails closed: `readAndVerifyCore` refuses to
   serve anything and exits 1 with both hashes. `scripts/pin-core.sh` prints the exact line
   and exits 1 until the constant matches the file. No binary is built this round, so no
   runtime launch was attempted or claimed.
2. BC-W5 `read` and the BC-W7 signing transcript need an installed artifact and a signing
   key. Neither exists in this round. The table, the flipper and the verifier are here so the
   release run is a command, not a design decision.

## Full self-check transcript

Command: `sh scripts/selfcheck.sh` in `03-build/output/wrapper`.

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
PASS BC-W3 named in 4 files
PASS BC-W4 named in 4 files
PASS BC-W5 named in 5 files
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
PASS sh -n fuses.sh
PASS sh -n hash-artifacts.sh
PASS sh -n pin-core.sh
PASS sh -n selfcheck.sh
PASS sh -n sign-hashes.sh
PASS sh -n verify-artifacts.sh
== 14. core pin shape
CORE_SHA256 present, 64 hex characters, placeholder state: unset
PASS BC-W4 pin shape

RESULT: PASS
```

Exit code: `EXIT=0`.

## Byte scans of the lane's own files

ASCII and dash scan, command `python3` walk over every file in the tree, printed from
selfcheck section 4:

```
non ascii bytes: 0, dash chars: 0, curly chars: 0
```

Codepoints checked: U+2012, U+2013, U+2014, U+2015, U+2212, plus U+2018, U+2019, U+201C,
U+201D and U+2026. Zero of each. Zero bytes above 0x7F.

## Script behaviour, run by hand

Fuse flag emission, from `fuses.json`:

```
$ sh scripts/fuses.sh flags --app /tmp/none
runAsNode=off nodeOptions=off nodeCliInspect=off onlyLoadAppFromAsar=on embeddedAsarIntegrityValidation=on grantFileProtocolExtraPrivileges=off loadBrowserProcessSpecificV8Snapshot=on cookieEncryption=off wasmTrapHandlers=on
```

Missing `--app` on the same script exits 2 with a usage line, so a release run cannot flip a
fuse on the wrong target silently:

```
$ sh scripts/fuses.sh read
usage: fuses.sh <read|write|flags> --app <path>
```

Hash roundtrip on two scratch files:

```
$ sh scripts/hash-artifacts.sh /Users/marcelspatz/.hermes/cache/scratch/w11-hash-test
wrote /Users/marcelspatz/.hermes/cache/scratch/w11-hash-test/SHA256SUMS
$ cat .../SHA256SUMS
b6a98d9ce9a2d9149288fa3df42d377c3e42737afdcdaf714e33c0a100b51060  a.txt
f2c82decdd7181cf98945929a62598db7e6b477e11f6e0eb0ae97020eff151ad  b.txt
$ shasum -a 256 -c SHA256SUMS
a.txt: OK
b.txt: OK
```

Pin gate against the read only V1 source, proving the mismatch path is live:

```
$ sh scripts/pin-core.sh ../../../input/ephemeral-chat-v1.html
core:    ../../../input/ephemeral-chat-v1.html
bytes:   35598
sha256:  23be3a0b6f53587e50c97c1767fa745980788288145dc79d3dba42095b150337
in code: 0000000000000000000000000000000000000000000000000000000000000000
MISMATCH: set CORE_SHA256 = '23be3a0b6f53587e50c97c1767fa745980788288145dc79d3dba42095b150337' in main.cjs, then rebuild the shell.
EXIT=1
```

That hash is the V1 core, not the V2 core. It is used only to prove the gate fails when the
constant is stale. The integration run uses `../ephemeral-chat-v2.html` once the CORE lane's
file is final.

Verifier usage guard:

```
$ sh scripts/verify-artifacts.sh /tmp/x
usage: verify-artifacts.sh <SHA256SUMS> <SHA256SUMS.minisig> <minisign.pub> [artifact-dir]
EXIT=2
```

## Files written

`03-build/output/wrapper/`: `package.json`, `main.cjs`, `preload.cjs`, `menu.cjs`, `qr.cjs`,
`fuses.json`, `BUILD.md`, `UPDATE-POLICY.md`, `SELF-CHECK.md`,
`scripts/fuses.sh`, `scripts/hash-artifacts.sh`, `scripts/sign-hashes.sh`,
`scripts/verify-artifacts.sh`, `scripts/pin-core.sh`, `scripts/selfcheck.sh`.

`03-build/output/cover/`: `relay.env.example`.

Nothing outside `wrapper/` and `cover/` was written. `input/`, `01-research/`, `02-plan/` and
`_config/` were read only, as the lane scope rule requires.
