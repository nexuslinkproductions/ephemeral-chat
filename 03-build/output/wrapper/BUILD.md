# Wrapper build notes, EXEC-ONLY shell

Scope: `03-build/output/wrapper/`. Owner: WRAPPER lane. Static files only in this round.
No `npm install`, no `electron-builder` run, no binary produced. Every card below is
implemented in a file a reviewer can read and a command a reviewer can rerun.

Sources: blueprint v2 sections 6.1, 6.3, 6.4 and 6.6; `11-packaging-executable.md` sections
3.2, 4.1, 4.2, 6.1, 6.2, 9.2 to 9.4; `13-platform-ux.md` sections 2.4, 3.1 to 3.4, 5;
`15-cve-packaging-native.md` section 2.

## Files

| File | Role |
|---|---|
| `package.json` | Exact Electron pin, exact fuses tool pin, scripts. No runtime dependency. |
| `main.cjs` | Window, `app://` protocol, the SHA-256 pin, navigation and permission denies, kill path, badge, About. |
| `preload.cjs` | The one bridge object, two verbs. |
| `menu.cjs` | UX-09 menu template and accelerators. No Reload, no Preferences, no zoom. |
| `qr.cjs` | UX-10 host contract: 997 byte ceiling, version 25 target, opt in scan, paste fallback. |
| `fuses.json` | BC-W5 fuse table, one row per fuse, with the conflict resolution recorded. |
| `scripts/fuses.sh` | Emits and runs the `@electron/fuses` write and read commands from `fuses.json`. |
| `scripts/hash-artifacts.sh` | BC-W7 `SHA256SUMS`, sorted and reproducible. |
| `scripts/sign-hashes.sh` | BC-W7 detached signature over the hash list, minisign or cosign. |
| `scripts/verify-artifacts.sh` | BC-W7 and BC-W8 independent verifier. No network, no download code. |
| `scripts/pin-core.sh` | BC-W4 layer 3 build input. Prints the core hash and fails on a stale constant. |
| `scripts/build-gate.sh` | P-02 and P-09 release gate. Refuses an unset or malformed build hash, a loose fuse table, a stale core pin, or a binary whose three node entry point fuses are not Disabled. |
| `scripts/e2e-core-load.sh` | P-01 live proof. Stages the wrapper beside the pinned core, runs the stock Electron binary, and requires the served byte count, the `app://core` URL, the S0 boot and one IPC round trip. |
| `scripts/selfcheck.sh` | Every check this lane claims, in one rerunnable script. |
| `SELF-CHECK.md` | Per card PASS or FAIL with the command and its raw output. |

`core/ephemeral-chat-v2.html` is not in this tree. The CORE lane owns that file at
`03-build/output/ephemeral-chat-v2.html`; the packaging step copies it to `core/` inside the
asar. No packaging step runs this round.

## Card map, BC-W1 to BC-W8

| Card | Where it is | How it is checked |
|---|---|---|
| BC-W1 | `main.cjs`: `app.enableSandbox()` before ready, and every window option closed: `nodeIntegration`, `nodeIntegrationInWorker`, `nodeIntegrationInSubFrames`, `contextIsolation`, `sandbox`, `webviewTag`, `webSecurity` | `scripts/selfcheck.sh` section 7 static scan. The runtime `process` and `require` assertion belongs to `gate.py shell` once a binary exists. |
| BC-W2 | `preload.cjs` exposes one frozen `shell` object with `wipe()` and `badge(on)`. `main.cjs` `assertSender` checks `event.senderFrame.url` with the same `app://core/index.html` predicate the server uses, checks the sender id against the one window, rejects null frames, counts rejections, and validates `badge` as a boolean. `menu.cjs` `COMMANDS` is the only command list; the preload validates shape only | `scripts/selfcheck.sh` section 8: one `exposeInMainWorld`, two invoke verbs, no `ipcRenderer` exposure, no second command list. R3-W2 is the live probe. |
| BC-W3 | `main.cjs` `hardenContents`: `will-navigate` allows only the exact `about:blank` eviction and denies every other URL, `will-frame-navigate` and `will-attach-webview` are denied, `setWindowOpenHandler` returns deny, every permission denied by both handlers | `scripts/selfcheck.sh` sections 7 and 15. R3-W3 is the live probe. |
| BC-W4 | `main.cjs`: `protocol.registerSchemesAsPrivileged` for `app` before ready, `session.fromPartition('core').protocol.handle('app')` serving only the verified buffer at `app://core/index.html` with a CSP response header, and a scheme, host and path check because `new URL().origin` is `null` for this custom scheme. No `file://` anywhere in the tree | `scripts/selfcheck.sh` sections 7, 14 and 15, `scripts/pin-core.sh` gates the build order, `scripts/e2e-core-load.sh` proves the live load. |
| BC-W5 | `fuses.json` plus `scripts/fuses.sh write` and `read`, and `scripts/build-gate.sh` which refuses a binary unless `runAsNode`, `nodeOptions` and `nodeCliInspect` read back Disabled | `scripts/selfcheck.sh` section 6 and 16. A stock Electron framework fails this gate: all three are Enabled (F-ENV-3). The release gate is `sh scripts/build-gate.sh --app <installed app>`, output attached to release evidence. |
| BC-W6 | `package.json` pins `electron` to `45.5.0` and `@electron/fuses` to `2.1.3` exactly. `main.cjs` About shows Electron, Chromium, build hash, core hash, build date and the verify commands, and warns past 90 days | `node -e "require('./package.json')"` and the About string in `main.cjs`. SLA text below. |
| BC-W7 | `scripts/hash-artifacts.sh`, `scripts/sign-hashes.sh`, `scripts/verify-artifacts.sh` | `scripts/selfcheck.sh` section 12 proves the verifier calls only minisign and the system hash tool. Release evidence carries both channel URLs and a verification transcript. |
| BC-W8 | No updater symbol anywhere: no `autoUpdater`, no `setFeedURL`, no `checkForUpdates`. Policy below and in `UPDATE-POLICY.md` | `scripts/selfcheck.sh` section 11. R3-W5 is the release gate. |

BC-W9 to BC-W13 are release engineering, not wrapper configuration. They are named in
`UPDATE-POLICY.md` as release gates and have no code in this tree.
BC-W14 is implemented in `main.cjs`: single instance lock, payload shape cap, no debugger
switch accepted, no listening socket, DevTools behind `EPHEMERAL_DEVTOOLS=1` and never in a
packaged build.

## The pin

Blueprint 6.1 pins Electron to one supported major and does not name a number. The number
here is `45.5.0`, the version whose framework archives `11-packaging-executable.md` section
7.1 measured (`electron-v45.5.0-<arch>.zip`). `npm view electron version` returned `45.5.0`
on 2026-11-27, so the pin is also the current release at build time. The upgrade rule is
blueprint 6.1: quarterly, or on a Chromium critical.

The core pin is 64 hex characters in `main.cjs`, compared with `crypto.timingSafeEqual`
against the bytes read from the asar. The served response is that same Buffer, so there is
no check then load window. The constant currently holds
`d4d48d3711acc8a32ba1fca97faa02e2690bc2ef6ff3487434aba36c5c618742`, the reviewed V2 artifact
at 165,744 bytes. A release build reruns `scripts/pin-core.sh` through `scripts/build-gate.sh`
after the core is final, and the constant is updated to that final hash before packaging. An
all zero constant fails closed: no window, exit 1, with the expected and actual hash in stderr
and a native dialog. A real constant that no longer matches fails the same way. The build gate
refuses both.

Build order, from `11-packaging-executable.md` section 10: build the core, hash it, commit
the constant, then build the shell. A hash computed after packaging proves nothing.

## Build gate and the fuse posture

`scripts/build-gate.sh` is the one command a release run must pass before packaging:

```
EPHEMERAL_BUILD_HASH=<64 hex> sh scripts/build-gate.sh --core <final core> --app <built app>
```

It refuses when the hash is unset or not 64 lowercase hex characters, when `fuses.json` does
not require `runAsNode`, `nodeOptions` and `nodeCliInspect` off, when `main.cjs` does not carry
the current core hash, and when the actual binary does not read back all three as Disabled.

Shipped binaries are fused binaries, only. The fuse write in `scripts/fuses.sh` is a build
step, not a suggestion, and the read in the same gate is the evidence. The in-code switch loop
in `main.cjs` is defense in depth: it catches `--inspect` and `--inspect-brk` on the normal
entry path, but `NODE_OPTIONS` and `ELECTRON_RUN_AS_NODE` run code outside `main.cjs` entirely
(F-ENV-3). Only the fuses close that path, which is why the gate treats a stock framework as
unshippable.

Measured 2026-11-27 with `@electron/fuses` 2.1.3 read on the stock Electron 45.5.0 framework:
RunAsNode Enabled, EnableNodeOptionsEnvironmentVariable Enabled, EnableNodeCliInspectArguments
Enabled. The same gate command refused it. No fused release binary exists in this round, so the
passing side of the read is the named limit.

`EPHEMERAL_ALLOW_UNVERIFIED=1` is a development hatch, ignored when `app.isPackaged`. With it,
a start without a valid hash is allowed only unpackaged, and About says
`Build hash: UNVERIFIED (development run, not a release build)`. Without it, both build and
start refuse.

## Downloads and clipboard

P-12: `session.fromPartition('core').on('will-download')` is the only download sink. It takes
the page's proposed name, reduces it with `path.basename` and a character allowlist, refuses
any extension outside the fixed list (pdf, txt, md, csv, png, jpg, jpeg, gif, webp, avif, mp4,
webm, mp3, wav, ogg, m4a, docx, xlsx, pptx), and writes under `<downloads>/ephemeral` with a
non clobbering name. Nothing else can choose a path. A refused download is cancelled and
logged to stderr.

P-13 clipboard policy: a kill clears the OS clipboard only when the shell window is focused,
matching the core gate at artifact:1818 (`document.hasFocus()`). A background wipe does not
touch another application's clipboard.

## Live proof

`scripts/e2e-core-load.sh` stages the wrapper beside the pinned core, runs it on a real
Electron binary and asserts the probe line from `main.cjs`. `EPHEMERAL_E2E=1` is the only thing
that turns the probe on, so a normal run never takes that path. Measured on the stock 45.5.0
framework: `served=165744 bytes`, `app://core/index.html`, `screen S0`, `shell object`,
`badge ok`.

## Bridge

| Direction | Transport | Payload | Validation |
|---|---|---|---|
| Page to main | `contextBridge` `shell.wipe()` | none | sender origin and sender id in `assertSender` |
| Page to main | `contextBridge` `shell.badge(on)` | one boolean | same, plus `on === true || on === false` |
| Main to page | `webContents.send('shell:command', id)` then `window.postMessage` | one id from a fixed set | the set is enforced in `menu.cjs` and again in `preload.cjs`; the page gets a plain message event |

No third verb exists. `11-packaging-executable.md` section 9.3 allows exactly `wipe()` and
`badge(on)` in the preload, and a third capability needs a line in that table first.

## Deliberate cuts

- No `shell.openExternal` anywhere. BC-W3 names an external link path behind a confirmation,
  but section 9.3 forbids `shell.openExternal` in `main.cjs` and the core has no links, so
  the confirmation branch has no caller. If a link ever exists, it needs both a table line
  and a fixed `https:` allowlist, not a general opener.
- No updater. Not a stub, not a disabled flag: no symbol at all.
- No QR encoder vendored. `qr.cjs` is the host contract and the ceiling; the encoder was
  priced at a few hundred lines in `13-platform-ux.md` section 2.4 and is a later card.
- No session restore, no window state file, no crash reporter, no tray, no protocol handler.
- macOS `userData` is on the boot volume while the process runs. An `hdiutil` RAM disk would
  close that window and leaves a mount to clean up (`11-packaging-executable.md` 4.2). The
  directory is deleted on every exit path, including the kill.

## Verify commands in About

`shasum -a 256` on macOS, `sha256sum` on Linux, `certutil -hashfile <file> SHA256` on
Windows. The About panel shows both hashes so the comparison has both sides.
