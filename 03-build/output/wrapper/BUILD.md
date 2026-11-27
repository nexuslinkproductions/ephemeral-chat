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
| `scripts/selfcheck.sh` | Every check this lane claims, in one rerunnable script. |
| `SELF-CHECK.md` | Per card PASS or FAIL with the command and its raw output. |

`core/ephemeral-chat-v2.html` is not in this tree. The CORE lane owns that file at
`03-build/output/ephemeral-chat-v2.html`; the packaging step copies it to `core/` inside the
asar. No packaging step runs this round.

## Card map, BC-W1 to BC-W8

| Card | Where it is | How it is checked |
|---|---|---|
| BC-W1 | `main.cjs`: `app.enableSandbox()` before ready, and every window option closed: `nodeIntegration`, `nodeIntegrationInWorker`, `nodeIntegrationInSubFrames`, `contextIsolation`, `sandbox`, `webviewTag`, `webSecurity` | `scripts/selfcheck.sh` section 7 static scan. The runtime `process` and `require` assertion belongs to `gate.py shell` once a binary exists. |
| BC-W2 | `preload.cjs` exposes one frozen `shell` object with `wipe()` and `badge(on)`. `main.cjs` `assertSender` checks `event.senderFrame.origin` against `app://core` and the sender id against the one window, rejects null frames, counts rejections, and validates `badge` as a boolean | `scripts/selfcheck.sh` section 8: one `exposeInMainWorld`, two invoke verbs, no `ipcRenderer` exposure. R3-W2 is the live probe. |
| BC-W3 | `main.cjs` `hardenContents`: `will-navigate`, `will-frame-navigate` and `will-attach-webview` all denied, `setWindowOpenHandler` returns deny, every permission denied by both handlers | `scripts/selfcheck.sh` section 7. R3-W3 is the live probe. |
| BC-W4 | `main.cjs`: `protocol.registerSchemesAsPrivileged` for `app` before ready, `protocol.handle('app')` serving only the verified buffer at `app://core/index.html` with a CSP response header. No `file://` anywhere in the tree | `scripts/selfcheck.sh` section 7 (banned `loadFile(` and `file://`) plus section 14 (64 hex pin). `scripts/pin-core.sh` gates the build order. |
| BC-W5 | `fuses.json` plus `scripts/fuses.sh write` and `read` | `scripts/selfcheck.sh` section 6: nine fuses at the BC-W5 positions. The release gate is `npx @electron/fuses read --app <installed app>`, output attached to release evidence. |
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
no check then load window. The constant is all zeros this round because the pin is committed
at integration, after the CORE lane's `ephemeral-chat-v2.html` is final, and an unset pin
fails closed: no window, exit 1, with the expected and actual hash in stderr and a native
dialog. `scripts/pin-core.sh` prints the line to paste and exits 1 until the constant matches.

Build order, from `11-packaging-executable.md` section 10: build the core, hash it, commit
the constant, then build the shell. A hash computed after packaging proves nothing.

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
