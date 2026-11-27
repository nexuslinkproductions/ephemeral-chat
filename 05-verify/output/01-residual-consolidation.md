# 01 Residual consolidation, blueprint rows 1 to 25 and the pentest additions

RUN: w26-ephemeral-verify-20261127, lane 3, residuals.
DATE WRITTEN: 2026-11-27.
ARTIFACT: `03-build/output/ephemeral-chat-v2.html`, sha256 `2092e0e9e8e3418ba167e22b99623094e0f5d05ea876014874be1e3c4b53b87b`, 169,810 bytes.
SOURCES READ IN FULL: `02-plan/output/blueprint-v2.md` section 5 rows 1 to 25; `04-pentest/output/00-register-summary.md` sections 1 to 6, including the round 3 closure; `04-pentest/output/03-environment-matrix.md`; `05-verify/CONTEXT.md`; `05-verify/briefs/W26-VERIFY-WAVE.md`.
METHOD: consolidate what the registers and the build record already state. This file re-executes nothing and overrides no register. Where a register label is round 2 and section 6 of the register supersedes it, this file follows section 6. Every row names its source and its current state. Nothing is dropped.

ASCII only. No em or en dashes.

## 1. Disposition vocabulary

| Word | Meaning |
|---|---|
| carried | Open, stated, and unchanged in the shipped shape under test. The source and the decision changer are named. |
| fixed | A landed change exists and the named evidence supports it. A live proof that is still missing is named in the row. |
| owner decision | The remaining step is a product or release choice only the owner can make. The options and the default are named. |

A row is not "fixed" because code was read. It is fixed when a landed change plus the named measurement or read supports the claim. Where the only support is a read, the row says READ. Where the only support is a measurement, it says MEASURED.

Counts are in section 8: 25 blueprint rows, 25 pentest and release-shape rows, 3 platform gap rows, 30 named-limit rows (15 exit 2 plus 15 other limits, 2 now closed), 7 owner decisions.

## 2. Blueprint rows 1 to 25

Source column is the blueprint row and its supporting research. Current state is the shipped artifact at 2092e0e9 unless another file is named.

| # | Residual | Source | Current state | Disposition |
|---|---|---|---|---|
| 1 | The SAS is a human check | blueprint 5 row 1; 04-crypto-design 1.2, 5.1 | Both sides must confirm before content unlocks, and the runbook steps 2 and 3 exercise it. A user who clicks through without comparing digits gets no protection, and the number proves shared keys, not personhood. No code change can close this. | carried |
| 2 | The code channel remains the root of trust | row 2; 03-threat-model class 3, 10 | The invite and reply codes still travel over a channel outside the app. The SAS catches substitution only when the digits are compared over a separate channel. Runbook step 2 makes that the protocol. | carried |
| 3 | Default mode exposes peer IPs and is detectable | row 3; 05-transport-hardening 1.1, 1.3, 2.5 | Default mode is unchanged: direct candidates, peer address in the code, WebRTC classifiable and blockable. The R3-BS-10 third-host case completes at Info (section 3, PA-21), which is a path-visibility fact, not a fix. Cover mode narrows the exposure only when configured. | carried |
| 4 | No TURN in default mode | row 4; 03-threat-model classes 2, 5 | Cover mode now has a consumer: `relayConfig` at artifact:1173-1199, relay-only ICE at :1950, fail closed at :1673-1674, and `gate.py cover` PASS on 2092e0e9. The default artifact still has no relay and fails closed on symmetric NAT or blocked UDP. | carried |
| 5 | Clipboard history and cross-device clipboard | row 5; 03 risk 2, 06-ops-defense 2.6 | The code textareas clear 30 s after a copy with a Show button, the clipboard is cleared on kill only when a code was copied and the page still has focus, and the shell clears the clipboard in `hardKill` (main.cjs:317). OS history, Universal Clipboard and clipboard managers remain outside. | carried |
| 6 | Platform adversary | row 6; 03 class 7, 04 6 | The browser artifact is fully exposed to a malicious extension or a compromised browser. The packaged macOS shape now passes the fuse read, the gate and the core-load e2e (`02-release-shape-proof.md` sections 5 to 9), so the extension model is removed by the shell. A compromised OS and a stolen signing key remain, and the live test in this file still runs the browser artifact. | carried, narrowed by the packaged shape |
| 7 | No provable key erasure | row 7; 04 7.1, 06 2.6 | Worker termination, `.fill(0)` and dropping references remain best effort. DTLS keys live in the browser network process. No native memory control exists in either shape. | carried |
| 8 | Swap, hibernation, crash dumps, screenshots | row 8; 04 6, 06 5 | Outside the page. The product copy and the OS checklist are the only controls. No change in this wave. | carried |
| 9 | No supply-chain verification in the product | row 9; 03 class 9 | A packaged macOS build now exists. Its About code shows the core SHA-256, the build hash and the build date (main.cjs:170, 477, READ). The build is ad-hoc signed, not Developer ID, and no hash is published in two channels yet. The browser artifact shows no hash. R3-BS-02 is ACCEPTED: a same-length substituted file boots and pairs, with no in-page provenance. | carried, narrowed but not closed by the packaged shape |
| 10 | A saved malicious file can still be opened | row 10; 03 risk 10, 02 F-13 | The warning list now covers `lnk`, `desktop`, `url`, `hta`, `docm`, `xlsm`, `reg` and `scf` at artifact:1746, and P-11 measured all eight names true with `invoice.pdf` false. Save is still allowed after verification and the OS handler is outside the app. | carried |
| 11 | Anomaly detection is blind to a normal-behaving peer | row 11; 06 2.4 | A1, A2 and A8 see protocol abuse and rate, not intent. Accepted by design. | carried, accepted |
| 12 | Monitor limits | row 12; 06 4.1, 4.6, 5.3 | The monitor suite runs 21 tests, 0 failures, arm64 macOS. It is macOS only, same-user can kill it, root can hide from it, and no live app-to-monitor alert was run. Not part of the live peer test. | carried |
| 13 | Deniability is narrow | row 13; 04 5.3 | No long-term identity keys and no signatures. Deniability still fails against a saved copy, a screenshot or a compromised peer. | carried |
| 14 | No post-quantum protection | row 14; 04 3.3 | The ratchet is classical. ML-KEM remains a V3 separate build. | carried |
| 15 | SPAKE2 is not in the default artifact | row 15; 04 1.3, 8.1 | The default artifact ships SAS only. SPAKE2 needs P-256 point arithmetic and a prebuilt optional file, and the owner has not allowed that file. | owner decision |
| 16 | CSP limits | row 16; 02 F-11, 07 3.6 | `frame-ancestors` cannot be set from a meta tag, and `script-src 'unsafe-inline'` stays because a hash needs a build step the owner ruling forbids and S-1 leaves no injection sink. No change. | carried |
| 17 | No revocation in a serverless design | row 17; 03 class 3, 06 3.5 | Codes carry a 120 s TTL and single use on the page (`TTL_MS` at artifact:1144, consumed sid check at :1732). A leaked code is valid for its window; there is no directory to revoke against. | carried, narrowed by the TTL |
| 18 | The undetectable transport target is only partly met | row 18; 05 1.3, 2.2, 3.6 | Default mode is classifiable WebRTC and blockable with one rule. Cover mode looks like TLS to one relay host and hides peer addresses from each other, but the relay stays a visible endpoint and a metadata holder. | carried |
| 19 | Linux has no asar integrity layer | row 19; 11 3.2-3.4, 15 L-02, L-03, U-10 | No Linux build exists in this wave, so the missing layer 2 is not yet shipped. When a Linux build is made, only the published hash and the package manager remain. | carried, also section 4 |
| 20 | The pinned engine accumulates CVEs between releases | row 20; 11 5.2, 8.3; 14 3.2; 15 E-14 | No updater and no version check, by design. The compensating control is implemented: About shows the build date and warns past 90 days (main.cjs:466-480). The packaged build is dated 2026-11-27; no public release exists yet to age. | carried by design |
| 21 | Windows cannot keep the profile off disk while running | row 21; 11 4.1, 4.2 | No Windows build exists. The platform limitation is unchanged: a launch-scoped `userData` directory is real files for the life of the process. | carried, also section 4 |
| 22 | libwebrtc has no advisory channel | row 22; 14 4.1, 4.3, 6.2 | R3-BS-08, the SDP and ICE fuzz case, is exit 2 with a named limit: no corpus generator and no CPU budget. The SDP parser reached through the reply code is still the only libwebrtc code a party with an invite reaches with zero authentication. | carried, verification limit |
| 23 | The muxer `finalize()` failure was unexplained | row 23; 12 2.7, 10 | Root cause measured: `EncodedVideoChunk.duration` is null on Chrome 158, the muxer throws on chunk 1, `decoderConfig` stays null, and `finalize()` throws on `colorSpace` (F-ENV-1). P-03 landed a finite duration fallback and a retry that falls to engine B at artifact:2795-2801 and :2969-2975. Lane 1 re-ran it headed: engine A encoded the 20 s over-45-MiB clip end to end, 35,929,778 B, verified, playback readyState 4, and the forced over-cap retry fell back to rung B and delivered (`03-environment-matrix.md` section 8.3 and 8.4, PASS). | fixed |
| 24 | The QR ceiling rests on an inferred code length | row 24; 13 2.4 | QR is EXEC-ONLY. `wrapper/qr.cjs` implements the host contract: version 25, a 997 byte ceiling, and a scan permission flow that requires a paste fallback. No encoder is vendored, so no QR render path ships. The envelope length is still unmeasured in the registers. Runbook step 2 records the real invite code character count for the measurement. | carried |
| 25 | An older signed build can be reinstalled | row 25; 11 5.2, 5.5, blueprint 6.1 step 4 | No version counter and no signed metadata, so a hash and signature check cannot tell new from old. R3-W5 accepts the older signed case and names the About build date warning as the compensating control. | carried, V3 owner decision |

## 3. Pentest and release-shape additions

Each row is a finding or an accepted test result from `04-pentest/output/00-register-summary.md` section 6 unless another source is named. Duplicates are marked, not deleted.

| ID | Item | Source | Current state | Disposition |
|---|---|---|---|---|
| PA-01 | F-ENV-1, engine A cannot encode | register 6.1; environment matrix section 8 | Fixed and verified headed on 2092e0e9. Engine A encoded the 20 s over-45-MiB clip end to end, 35,929,778 B in 20.5 s with no fallback; receiver verified and playback ran 1080p, 20.00 s, readyState 4. The forced over-cap retry fell back to rung B and delivered 37.3 MB (environment matrix 8.3 and 8.4, PASS). Named limit: engine A on the packaged shell's Chromium was not driven. | fixed |
| PA-02 | F-ENV-2, shell cannot load its own core | register 5 and 6; environment matrix F-ENV-2; release proof section 8 | P-01 closed at code level: handler registered on the `core` partition and the origin compare replaced. Stock Electron 45.5.0 live run PASS, served 169,810 bytes, screen S0. The packaged app now proves the same: `e2e-core-load.sh` served 169,810 bytes from the asar and booted to S0 (`02-release-shape-proof.md` section 8, PASS). | fixed |
| PA-03 | F-ENV-3, the debug refusal is not a control | register 6.1; environment matrix F-ENV-3; release proof sections 5, 9 and 10 | P-02 closed and the accept side run on the packaged macOS binary: `RunAsNode`, `EnableNodeOptionsEnvironmentVariable` and `EnableNodeCliInspectArguments` all read Disabled, and with `ELECTRON_RUN_AS_NODE=1` the stock binary runs node code while the packaged binary does not (`02-release-shape-proof.md` sections 5 and 9, PASS). Fixed on macOS. Named limit: no fused Windows or Linux binary, so the fuse is unverified there (section 4). | fixed on macOS, carried on Windows and Linux |
| PA-04 | F-ENV-4, received-file warning misses shortcut types | register 6.1; environment matrix F-ENV-4 | Fixed by P-11: artifact:1746 covers `lnk`, `desktop`, `url`, `hta`, `docm`, `xlsm`, `reg`, `scf`; all eight measured true, `invoice.pdf` false. | fixed |
| PA-05 | F-ADV-01, a stalled file-start holds receive and migration | register 6.1 | P-04 closed (READ): first-chunk deadline discards the hold; results index 17 records held at 1 s, migrate refused, hold discarded. Ceiling kept: bulk chunk frames stay exempt from the A8 byte counters while a transfer is active. | fixed for the hold, carried ceiling |
| PA-06 | F-ADV-02, repeated migration offers leak pending peers | register 6.1 | P-05 closed: results index 18 records 8 offers, 6 accepted, 2 attempt-limit refusals, 5 closed peers, screen S3, channel open. Ceiling kept: a sixth migration can be left connecting and its 15 s timer can still end the session (INFERRED, not waited out). | fixed, carried ceiling |
| PA-07 | F-ADV-03, SAS digits stay in the DOM after S4 | register 6.1 | P-10 closed: results index 13 records digits 60 to 0, digits in DOM 0, clipboard written then cleared, focus true. Limit kept: the unfocused clipboard branch is EX-ADV-01, not run. | fixed, verification limit |
| PA-08 | F-ADV-04, cover mode had no consumer | register 6.1 and 6.3 | Resolved by P-06: the artifact reads `?relay=` (turn or turns only), forces relay-only ICE, and fails closed with no relay candidate; `gate.py cover` PASS. Ceilings kept: relay user and credential travel in the URL query, up to 128 characters each, and the artifact enforces no credential TTL. `EPHEMERAL_RELAY_*` build inputs are still not consumed. | fixed as ledgered, owner decision on the ceilings |
| PA-09 | WB-01, preload bridge has no consumer and shell kill sends no panic | register 6.1 | P-07 closed (READ): one COMMANDS source, the dead preload relay removed or given a consumer, and the shell kill path goes through the wipe contract (main.cjs:345-354, menu.cjs:16, preload.cjs:11-14, artifact:3784-3790). L-5, shell kill to core wipe, was not run; `event.source` identity is INFERRED. | fixed, verification limit |
| PA-10 | WB-02, command whitelist drift by `wipe` | register 5 | P-13 closed: single COMMANDS source across menu.cjs and preload.cjs. | fixed |
| PA-11 | WB-03, unconditional shell clipboard clear | register 5 | P-13 closed: one clipboard policy, shell clear gated by the same rule as the renderer. | fixed |
| PA-12 | WB-04, blanket `will-navigate` deny cancels about:blank and reload | register 5 | P-13 closed: predicate allows about:blank. The runtime effect in a live shell is INFERRED, not run. | fixed, verification limit |
| PA-13 | WB-05, warning list misses eight names | register 5 | Duplicate of F-ENV-4, fixed by P-11 at artifact:1746. | fixed, duplicate |
| PA-14 | WB-06, no download sink confinement | register 5 and 6.1 | P-12 closed: `will-download` with a type allowlist and `setSavePath` under `~/Downloads/ephemeral` (main.cjs:398-429, READ). The live download was not run (L-6). Saved files leave the session and the wipe does not remove them; see section 5. | fixed, owner decision on the export wording |
| PA-15 | WB-07, hash script omits directory artifacts | register 5 | P-08 closed: `hash-artifacts.sh:28` hashes the bundle as well as the dmg; a tampered bundle exits 1 (MEASURED, scratch). | fixed |
| PA-16 | WB-08, `BUILD_HASH` fallback is not fail closed | register 5 | P-09 closed: `main.cjs:34-37, 87-90, 175-177` refuse an unset or malformed hash; no-hash start exits 1 and the build gate refuses (MEASURED). | fixed |
| PA-17 | WB-09, About claims a minisign key it does not show | register 5 | P-13 closed: the `sign-hashes.sh` comment was corrected. The About panel does not display a key fingerprint; the published hash remains an ops control. | fixed as a documentation defect |
| PA-18 | WB-10, BUILD.md pin drift | register 5 | RP-2 closed: BUILD.md names 2092e0e9 at 169,810 bytes, matching main.cjs:26 (READ, size MEASURED). | fixed |
| PA-19 | WB-11, clipboard ceiling accepted as designed | register 5 | Info, not a defect. The F3 focus gate is intentional and matches blueprint row 5. It is carried there. | carried, duplicate of row 5 |
| PA-20 | WB-12, S5 naming drift | register 5 | P-13 closed: artifact:3602 reads S0 to S4; no S5 string remains. | fixed |
| PA-21 | R3-BS-10, a third-host candidate completes | register 6.1 and 6.2; blueprint 6.5 R3-BS-10 | Confirmed at Info by the planner call. Re-run on 2092e0e9: the session completes with its only declared candidate dead, channel open, 9,075 ms (MEASURED). Blueprint-v2.md:769 requires "fails or completes only through it"; that condition was not met. The selected-pair identity comes from the d4d48d37 dump and was not re-dumped on 2092e0e9 (L-7). | carried, accepted at Info |
| PA-22 | REL-L1, `scripts/fuses.sh write` cannot flip any fuse | release proof sections 4 and 10 | The script emits lowerCamel names from `fuses.json`; `@electron/fuses` 2.1.3 accepts only enum names, so the write exits 1 with `Invalid fuse name runAsNode`. A scratch copy with a one block mapping table wrote the fuses. The project script was not edited by lane 2. | carried, fix named but not applied |
| PA-23 | REL-L2, the browser V8 snapshot fuse cannot be enabled on the stock framework | release proof sections 4a and 10 | `fuses.json` sets `loadBrowserProcessSpecificV8Snapshot: true`, but the stock Electron 45.5.0 darwin-arm64 framework ships no `browser_v8_context_snapshot.bin`; the app aborted with `Error loading V8 startup snapshot file`. The packaged binary has the fuse off; `fuses.json` still says true. | carried, fix named but not applied |
| PA-24 | REL-L3, a fuse write invalidates the code signature | release proof sections 4b and 10 | Rewriting the executable with the fuse tool invalidates the signature; macOS killed the first launch with `Killed: 9`. Release order is package, fuse, codesign. The proof used an ad-hoc signature. Developer ID signing and notarization are absent. | carried |
| PA-25 | REL-L4, distribution shape is not produced | release proof section 10 | The app is ad-hoc signed, 252 MB, and no dmg was produced. Not a defect for the shape proof; distribution packaging is a later release card. | carried |

## 4. Fused Windows and Linux builds not yet made

The macOS packaged shape has landed: all four accept criteria PASS (`02-release-shape-proof.md`). Windows and Linux have no build, no fuse read, no signature and no package in the tree. This section records what is still absent on each platform.

| Platform | What exists | What is absent | Disposition |
|---|---|---|---|
| macOS, arm64 host | A packaged `ephemeral.app` in `.agent-runs/`, fused, ad-hoc signed; fuses read Disabled for all three required entries; build-gate PASS where the stock framework is REFUSED; 266 of 266 bundle files hashed; e2e served 169,810 bytes and booted to S0 (`02-release-shape-proof.md` sections 5 to 9) | Developer ID signature, notarization, stapled ticket, dmg. The wrapper's own `fuses.sh write` is still broken (PA-22), the snapshot fuse row is still true in `fuses.json` (PA-23), and the fuse write still needs a re-sign step (PA-24). An x64 artifact is a separate acceptance item. | carried for distribution signing and the wrapper fixes; shape accepted |
| Windows x64 | Core artifact and the wrapper source only | A fused Windows build, Authenticode over every exe and dll, the NSIS per-user installer, the portable zip, `signtool verify /pa /all`, the R3-W8 trust cases, the Windows ASAR integrity resource | carried, owner decision on release scope (section 7, OD-1) |
| Arch, Omarchy and other Linux | Core artifact and the wrapper source only | A fused Linux build, AppImage with an embedded gpg signature, `PKGBUILD` with `sha256sums`, `desktop-file-validate`, the R3-W9 launch cases. Layer 2, ASAR integrity, does not exist on Linux at all (blueprint row 19). | carried, owner decision on release scope (section 7, OD-1) |

Consequence while this gap is open: the fuse is verified on macOS by the packaged read and the `ELECTRON_RUN_AS_NODE` behavior test, and unverified on Windows and Linux until a fused binary on each platform is built and R3-W1 is re-run there. The in-code refusal of `--inspect`, `--remote-debugging-port` and a bad build hash is defense in depth, not the control. A fuse that is only declared in a JSON file has not been read from a binary.

## 5. Received file export directory

Source: register 6.4, item L-6; main.cjs:71-75 and 398-429.

Current state: a Save in the packaged shell writes to `~/Downloads/ephemeral` through `will-download` and `setSavePath`, with a type allowlist. The kill path removes `DATA_DIR` only, so a saved export survives the wipe. In the browser artifact the file goes wherever the browser's download setting points, which is the Downloads folder unless Ask where to save is on, and that is also outside the wipe. The product copy does not say that a saved file leaves the session.

This is correct behavior for a user-requested export. Deleting a file the user deliberately saved would be data loss. The gap is the wording, not the sink.

| Option | What it costs | Assessment |
|---|---|---|
| A. Keep the directory, state in About and first-run copy that Save writes a file outside the session and the wipe does not remove it | One copy change, no code change | Recommended default. Honest and it preserves the user's file. |
| B. Save into a per-session folder and delete that folder on kill where the OS allows | Kill can fail on open handles; a user who wanted the file loses it; Windows file locking makes it unreliable | Not recommended. |
| C. Remove Save entirely | The only export path is gone; received files can never leave the page | Rejected for V2. |

Disposition: owner decision on the wording (OD-3). The code is not changed by this file.

## 6. Verification limits carried with the registers

These are not product residuals. They are evidence gaps that bound what the stage can claim, stated here so the verdict does not read wider than the record.

### 6.1 The fifteen R3 exit 2 rows

| Row | Named limit | Consequence |
|---|---|---|
| R3-BS-03 | Was exit 2 with no packaged engine installed; a packaged 45.5.0 app now exists (`02-release-shape-proof.md`), but no renderer exploit was run against it | No renderer exploit run against the product build |
| R3-BS-04 | No syscall tracing or seatbelt dump on this host | Sandbox profile unproved beyond the code |
| R3-BS-05 | Was exit 2 with no packaged build installed; the packaged 45.5.0 app now exists, but its Chromium was not compared to stable or to KEV rows added since the build | Patch state of the packaged engine still unproved |
| R3-BS-08 | No fuzz corpus generator and no CPU budget in lane 1 | The SDP and ICE parser fuzz claim has no result |
| R3-BS-09 | No complete ICE responder built in the lane budget | Malformed STUN handling unproved |
| R3-BS-11 | No privileged capture and no NAT simulator | STUN reflection unproved |
| R3-BS-12 | No DTLS endpoint in the Python stdlib | DTLS handshake abuse unproved |
| R3-BS-13 | Same DTLS stack limit | DTLS record abuse unproved |
| R3-BS-18 | Nonce produced inside the crypto worker | 10,000-frame nonce log not carried |
| R3-BS-19 | Counter is a closure variable inside the worker | Nonce wrap not forced |
| R3-BS-21 | Tag compare is inside AES-GCM in the browser | No timing measurement of a JS compare |
| R3-BS-23 | Crafted image corpus not built | Image decoder abuse unproved |
| R3-BS-24 | Decompression bomb fixture not built | Decode memory ceiling unproved |
| R3-BS-25 | No `VideoDecoder` constructed by the artifact | Container abuse unproved |
| R3-BS-27 | Ten 45 MB fixtures outside the lane | Repeated decoder memory reclamation unproved |

The 15 rows keep d4d48d37 stamps; they were not re-run on 2092e0e9. That is L-7 and it is not closed by this wave.

### 6.2 The other named limits

| Limit | What it means | Disposition |
|---|---|---|
| L-1, fused accept side | Closed on macOS: the packaged binary reads all three required fuses Disabled, the gate PASSes and the e2e serves 169,810 bytes to S0 (`02-release-shape-proof.md` sections 5 to 9). No Windows or Linux binary | closed on macOS, open on Windows and Linux |
| L-2, headed engine A after P-03 | Closed: lane 1 ran engine A headed on 2092e0e9 end to end over 45 MiB and forced the retry fallback (`03-environment-matrix.md` section 8.3 and 8.4, PASS) | closed |
| L-3, build gate without `--app` | Prints `RESULT: PASS` on the static table only | BUILD.md should say it is not a release PASS |
| L-4, runtime injection not re-run on 2092e0e9 | W23 re-ran P-04, P-05 and P-10 (results indices 13, 17, 18); the producer and the round 3 auditor did not | the W23 records stand as the evidence |
| L-5, shell kill to core wipe | Read only; `event.source` identity is INFERRED | open until a live shell kill |
| L-6, received file export directory | `~/Downloads/ephemeral` by design; kill removes only `DATA_DIR` | owner decision, section 5 |
| L-7, sha scope | The 15 exit 2 rows and the selected-pair dump are on d4d48d37; the whitebox and environment registers were not re-run on 2092e0e9 | next wave |
| R3-BS-22 zero-salt HKDF wording | NOT CHECKED | open, text-level |
| EX-ADV-01 | The unfocused clipboard branch was never exercised | open, low |
| EX-ADV-02 to EX-ADV-05 | TURN consumer, migration replay and react injection, wire fuzzing, nonce wrap | exit 2, named limits in the register |
| FC-05 | 256 KiB and 1 MiB sends owned by R3-BS-17 | run there, not a separate gap |
| TB-W5 and TB-W6 | TB-W5 is closed on macOS: a fused binary exists, reads correctly and passes the gate. TB-W6 is open: no Developer ID signature, no notarization, no Authenticode, no AppImage signature, no install tree | TB-W5 closed on macOS; TB-W6 release engineering |
| A8 byte rate, 2 MB/s without a transfer | The shim cannot seal frames, so a synthetic flood hits A1 or A8 frame rate first | open, environment limit |
| Monitor live alert | 21 unit tests pass; no end-to-end alert from a live app | open, not part of this stage gate |
| QR envelope length | Never measured; `qr.cjs` enforces 997 bytes by design; runbook step 2 records the real length | open, measurement |

Stage record, not a verification limit: RP-1, the register labels and final-record pointers, has the class fix applied at 98f8733. The scoped round 4 re-check returned BLOCKED on two text-only sites: the legend verdict at line 232 and the pre-repair records at lines 445 to 446. No disposition changed. `proof.md` round 4 carries the detail.

## 7. Owner decisions

Defaults are what happens if the owner says nothing. None of these blocks the machine gates.

| ID | Decision | Options | Default |
|---|---|---|---|
| OD-1 | Release scope for this round | Ship macOS first and state Windows and Linux as not yet built, or wait for all three fused builds | Ship macOS, state the other two as named gaps (section 4) |
| OD-2 | Cover mode credentials | Wire `EPHEMERAL_RELAY_*` at build time and add a credential TTL, or keep the manual `?relay=` path and document it as INFRA | Document the manual path as INFRA for V2.1 and add a TTL when the build input is wired. The query-string credential is visible in browser history and the address bar; that ceiling is real. |
| OD-3 | Received file export wording | State that Save writes outside the session and the wipe does not remove it, or change the directory, or remove Save | State it in About and the first-run copy (section 5) |
| OD-4 | SPAKE2 optional prebuilt artifact | Allow a maintainer-built optional single HTML file, or defer to a paste-in curve implementation | Defer (blueprint row 15) |
| OD-5 | Code TTL of 120 s | Keep it, or raise it if the live test shows routine expiry | Keep 120 s unless runbook step 2 records expiry in normal use; then raise to the ICE lifetime and record the change |
| OD-6 | SAS mismatch override | No override, or a separate logged override action | No override (blueprint 2.1 rule 4) |
| OD-7 | Windows profile on disk | Accept the platform limitation with full volume encryption, or require a native client | Accept for a per-user install and document it (blueprint row 21) |

## 8. Counts and reconciliation

Counts computed from the tables, not asserted from memory:

- Blueprint rows: 25, numbered 1 to 25, one row each.
- Pentest and release-shape additions: 25, IDs PA-01 to PA-25.
- Platform gap rows: 3 (macOS shape accepted with signing absent, Windows absent, Linux absent).
- Named-limit rows: 15 exit 2 rows plus 15 other limits; L-1 and L-2 are now closed.
- Owner decisions: 7, OD-1 to OD-7.
- Duplicates marked: PA-13 equals PA-04 (WB-05 and F-ENV-4); PA-19 restates blueprint row 5 (WB-11).

One sentence summary, counted from the table: 23 blueprint rows are carried, 1 is fixed (row 23), and 1 is an owner decision (row 15). Of the 23 carried, 4 are narrowed by a landed change (rows 4, 6, 9, 17) and 19 are unchanged. Row 25 is carried with a V3 owner decision noted in its cell. Row 23 is the one fully fixed blueprint residual, on lane 1's headed re-run; row 9 stays carried because the published hash and the signed channel are still absent.

## 9. Self-check for this file

Commands run after the last edit, output quoted in the lane report:

```
python3 -c "d=open('05-verify/output/01-residual-consolidation.md','rb').read(); print('bytes', len(d)); print('em', d.count(b'\xe2\x80\x94'), 'en', d.count(b'\xe2\x80\x93'), 'nonascii', sum(1 for b in d if b > 127))"
grep -c '^| [0-9]' 05-verify/output/01-residual-consolidation.md
grep -c '^| PA-' 05-verify/output/01-residual-consolidation.md
grep -o '^| [0-9]* |' 05-verify/output/01-residual-consolidation.md | tr -d '| ' | sort -n | tr '\n' ' '
```

Expected: zero em, zero en, zero non-ASCII bytes; 25 numbered blueprint rows; 25 PA rows; the numbered row list reads 1 to 25 with no gap. The exact outputs are recorded in the lane report.

STATUS: complete. Every blueprint residual 1 to 25 and every pentest, release-shape or named limit that changes what the product can claim is represented, with a source, a current state and a disposition. F-ENV-1 is fixed and verified headed; the macOS packaged shape PASSes. The open set is the carried product residuals, the two wrapper script defects REL-L1 and REL-L2, Developer ID and notarization, the Windows and Linux builds, and the owner decisions with their defaults.
