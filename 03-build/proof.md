# W15 build review proof, whole R2

Run: w15-ephemeral-buildreview-20261127
Reviewer: independent haiku-review lane (claude-haiku-5-5). Not the builder.
Brief: 03-build/briefs/W15-BUILDREVIEW.md. Only write: this file.

## Identity and method

- Repo: 04_PROJECTS/EPHEMERAL, branch Development, HEAD 1c6fd4a.
- The brief names 4a5d553 as the artifact commit. The artifact is identical at both commits: `git diff --stat 4a5d553 HEAD -- 03-build/output` touches only the lead log and 22 evidence JSON files. Not a finding.
- Artifact: 03-build/output/ephemeral-chat-v2.html, 165,202 bytes, sha256 6c8c1283047f6ce7d3b926e6fd190d3c46b345926aa0142e02827cf2dc02558d. Matches the brief, CORE-SELFCHECK and the lead log. Measured.
- Working tree was clean before and after the review (`git status --porcelain` empty). Measured.
- Scratch copy: `git archive HEAD 03-build` extracted to /Users/marcelspatz/.hermes/cache/scratch/w15-review-20261127. gate.py and swift write into the tree (gate.py writes evidence JSON beside the artifact; swift writes .build, which is tracked). Copies of the artifact, gate.py, Package.swift and main.cjs were checked byte-identical to the working tree with cmp. Scratch logs: scratch/w15-review-20261127/logs/.
- The wrapper selfcheck was run in place. It only reads files; repo status was unchanged afterwards.

## Part 1. Artifact form and hygiene (measured)

- One HTML file. Three inline script blocks: vendored muxer, text/worker cryptoWorker, app. No external references: zero matches for src or href to http(s) or protocol-relative URLs, url(http, @import, fetch(, import(, https:// and http://.
- ASCII: 0 non-ASCII bytes. U+2014 count 0. U+2013 count 0. No CR, no tabs.
- Tree-wide: 199 git-tracked text files under 03-build, excluding .build. Zero dash characters U+2012 to U+2015 and zero non-ASCII bytes.
- Muxer block: the first script body is 31,135 bytes, which includes three surrounding newline bytes. Minified content is 31,132 bytes. The lead's 31,133 counts one newline. One-byte accounting difference, no effect.
- Muxer explanation, checked in code (read): the vendored block ends with `window.Mp4Muxer={Muxer:it,ArrayBufferTarget:Oe};` at byte 52558. The app's engine A reads that global: `typeof Mp4Muxer === 'undefined'` at line 2718 and `new Mp4Muxer.Muxer` / `new Mp4Muxer.ArrayBufferTarget()` at lines 2732 to 2733. A classic script cannot bind ESM exports, so a global is the only route. The stated reason for the 30 B global holds. Without it, the typeof check silently takes the rung B fallback.
- Not verified: the pinned 31,103 B build was not rebuilt (no esbuild run, no pinned output in the repo). The 30 B delta is also not reproduced by arithmetic. The inserted statement is 48 bytes, so it is not a plain 30 B insertion. Non-blocking, see F4.

## Part 2. Gates (my runs, scratch copy of HEAD)

Each row is one invocation, run by me. Exit codes are real (run-all.sh writes rc per case). All 20 cases exit 0.

| Case | My run | Lead first loop | Lead addendum | Agrees |
|---|---|---|---|---|
| selftest | PASS rc 0 | PASS 0 | - | yes |
| envelope | PASS rc 0 | PASS 0 | - | yes |
| ratchet | PASS rc 0 | PASS 0 | - | yes |
| sas | PASS rc 0 | PASS 0 | - | yes |
| file | PASS rc 0 | PASS 0 | - | yes |
| budget | PASS rc 0 | PASS 0 | - | yes |
| code | PASS rc 0 | PASS 0 | - | yes |
| lifecycle | PASS rc 0 | PASS 0 | - | yes |
| kill | PASS rc 0 | PASS 0 | - | yes |
| rotate | PASS rc 0 | PASS 0 | - | yes |
| migrate | PASS rc 0 | PASS 0 | - | yes |
| stun | PASS rc 0 | PASS 0 | - | yes |
| cover (--relay-host turn:127.0.0.1:5349, gate usage form) | PASS rc 0 | not run | - | yes |
| cover (--relay-host turns:127.0.0.1:5349, blueprint R2-13 form) | PASS rc 0 | SKIP rc 2 (flag omitted, lead error) | PASS 0 | yes, with addendum |
| media-order | PASS rc 0 | PASS 0 | - | yes |
| exif | PASS rc 0 | PASS 0 | - | yes |
| bitrate | PASS rc 0 | PASS 0 | - | yes |
| playback | PASS rc 0 | PASS 0 | - | yes |
| imagecap | PASS rc 0 | PASS 0 | - | yes |
| paste | PASS rc 0 | PASS 0 | - | yes |
| mutation-all | PASS rc 0 | FAIL rc 1 (kill mutant got SKIP rc 2, devtools socket closed) | PASS 0 | yes, with addendum |

- Lead first loop: 18 pass, 2 fail (SUMMARY pass=18 fail=2 of 20). Both failures are explained in the addendum. The cover one is a missing flag. The mutation-all one is a harness flake inside the kill-nav mutant subrun. My mutation-all run was clean on the first try, so I did not reproduce the flake. Known flake, see F5.
- Relay host spelling: blueprint R2-13 says turns:, the gate usage line and the CannotRun message say turn:. case_cover accepts any non-empty host string, so both spellings run. See F9.

## Part 3. Invariant integrity, anti fake green (seven retargets)

Method: diffed gate.py b985061..4a5d553 (786 insertions, 88 deletions). Read each retargeted case body. Compared against the failure mode in blueprint section 4.2. Ran mutants on scratch copies of the artifact.

| Retarget (card) | What the old case did | What the new case does | Invariant still holds? | Mutant evidence |
|---|---|---|---|---|
| envelope (R2-02) | Sent plaintext frames. The artifact rejects plaintext before the router, so the unknown-k and version checks never reached the router. Vacuous. | Mutates the app's own sealed envelope via the shim. Asserts a visible system line for unknown k, visible version state, a visible malformed-JSON line, and that three unknown frames run Kill. | Yes. Unknown frames give visible state or kill. Strengthened. | Not mutated. |
| ratchet (R2-03) | Banned exportKey artifact-wide. | exportKey allowed only on .publicKey and banned in the main thread. Scans postMessage sites in worker and main for key tokens. Checks identical plaintext gives distinct ciphertext on the wire. | Yes. Artifact has exactly two exportKey calls, both `exportKey('raw', kp.publicKey)` at line 685 in the worker. None in main. | Worker postMessage carrying ckS: FAIL "Worker postMessage carries key material" (my run). |
| file (R2-05) | Replayed plaintext string frames. V2 sends none, so the case was empty by design. | Sealed truncated-size mutation and sealed bad-digest mutation through the app path, plus a binary truncated replay. Each asserts no new Save anchor, no new blob, and a visible failure. | Yes. Truncated transfer produces no Save anchor. | mutation-all completeness guard (received !== size forced to false): FAIL on mutant, PASS in my run. |
| budget (R2-06) | 200 plaintext frames, rejected before the counter. Vacuous. | 45 sealed valid frames. Kill must name A8. Row cap pinned by MAX_ROWS = 2000 and the mutation-all row-cap guard. | Yes. A8 trips. | frameTimes > 400 (static pin still matches): FAIL "45 valid frames in a burst did not trip the A8 rate rule" (my run). |
| lifecycle (R2-08) | Blob count difference only. | Per-URL live check, DOM-before-revoke check, channels closed, draft, codes, log, gallery and about cleared, and ?idle=5 not honored. | Yes. pagehide still wipes. Verified by reading the artifact handler at lines 3792 to 3822. | Not mutated. |
| kill (R2-09) | No clipboard assertion. Confirm dialog unhandled, so the case SKIPped. | CDP dialog accepted, double Escape, DOM-before-revoke, clipboard clear, and about:blank via wait_blank (raises on timeout). | Yes on the focused path. See F3 for the unfocused path. | Clipboard clear removed: FAIL "the kill path did not clear the copied code from the clipboard" (my run). |
| migrate (R2-11) | Plaintext tampered offer, rejected before the router. Vacuous. | Sealed tampered fp through the app path. The session must end with the Migration failed text. New 60-digit SAS must differ and match on both peers. Composer stays locked until confirm. | Yes. Fingerprint checks at artifact lines 3254 to 3255 and 3369. | Not mutated. |

Also: budget's candidate cap moved from a weak `\b32\b` pin to `CAND_MAX = 32`, and the 40-candidate refusal is checked behaviorally. Strengthened.

Result: no retarget weakened its guard. Mutant or behavioral evidence for ratchet, budget, kill, and the file completeness guard (mutation-all). Read-only evidence for envelope, lifecycle and migrate.

## Part 4. Satellites

- swift test (scratch copy, clean .build): "Executed 21 tests, with 0 failures (0 unexpected)", exit 0. Run on the scratch copy because the command writes into the tracked .build.
- scripts/selfcheck.sh (in place): RESULT PASS, exit 0. Step 14 checks only the shape of CORE_SHA256 and passes in both states. It does not test fail-closed behavior. See F11.
- Zero CORE_SHA256 placeholder fails closed. Measured with a stubbed electron module (no Electron binary, no npm). Harness: scratch fc/harness.cjs.
  - Shipped placeholder: "Core pin is not set" dialog, app.exit(1), no protocol.handle, no BrowserWindow, process exit 1.
  - Control, pin set to the artifact sha256 in the scratch copy: protocol.handle app, new BrowserWindow(), exit 0. The harness is not vacuous.
  - Wrong pin: "Core hash mismatch" dialog, app.exit(1), no window, process exit 1.
  - Limit: the stub models only the pin-check ordering. It is not an Electron runtime run.

## Part 5. Blueprint coverage spot check (six cards)

All six named scopes exist in the artifact (read and grep, line numbers in the artifact).

- R2-03 crypto in the Worker: present. Worker script id="cryptoWorker" starts at byte 52624. genPair at 682. Public-only export at 685. AES-GCM and hkdf inside the worker. Main thread has no generateKey and no exportKey (ratchet static scan).
- R2-09 kill switch: present. Wipe button id="wipe" at 521. function wipe at 1071. endSession at 1729. Clipboard clear at 1818 to 1819. location.replace('about:blank') at 1850.
- R2-16 encryption ordering: present. framePlain at 833 calls gzipBytes(raw) at 835, then const padded at 841. sealControl at 855 calls crypto.subtle.encrypt at 865. openControl at 878 checks frame bounds. Order is compress, pad, seal.
- R2-18 engine A: scope present. transcodeA at 2677. VideoFrame at 2795. encodeQueueSize > 8 at 2808. requestVideoFrameCallback at 2814. decoderConfig asserted at 2821, before muxer.finalize() at 2822. MediaRecorder rung B at 2836. Engine A was not executed here or by the lead (no VideoEncoder in headless Chromium). The named case `transcode` is not registered in gate.py. See F1.
- UX-02 reactions: present. REACT_FRAME_MAX 256 at 1151. REACT_SESSION_MAX 200 at 1152. REACT_BURST 20 and REACT_REFILL_MS 250 at 1153 to 1154. PALETTE with 24 entries at 1160. PALETTE_MAP allowlist at 1170. applyReact at 1518 with the PALETTE_MAP.has guard at 1519. aria-pressed at 417. Named case `react` is not registered. See F1.
- UX-03 screen machine: present. showScreen at 3521 sets document.body.dataset.screen at 3522. slots.active and slots.pending at 1806 to 1807 and later. Migration strip at 3299. adopt at 3389. Named case `nav` is not registered. The "only visibility writer" claim was not checked; 40 other .hidden assignments exist for other panels. See F1.

## Findings ledger

Severity: H high, M medium, L low, I info. None of these blocks the brief's criteria. All are listed, none repaired (read-only review).

| ID | Sev | Location | Evidence | Fix |
|---|---|---|---|---|
| F1 | M | probes/gate.py CASES, lines 2058 to 2080 | Nine R2b named cases are not registered: transcode (R2-18), mid (UX-01), react (UX-02), nav (UX-03), sas-ui (UX-04), pair (UX-05), panic (UX-06), gallery (UX-07), a11y (UX-08). Code read, not executed. | Register the nine cases, or record the gap in the acceptance record before R2b is accepted. R2-18 and UX-01 to UX-08 are live-probed only. |
| F2 | M | git ls-files 03-build/output/monitor/.build | 2,587 tracked files, about 244 MB on disk, including .lock, object files and a test binary. No .gitignore covers it. Measured. | git rm -r --cached that path, add .build/ to a .gitignore. |
| F3 | L-M | ephemeral-chat-v2.html line 1818 | Clipboard clear runs only if copiedCode is set and document.hasFocus() is true. Blueprint line 294 specifies this. An unfocused kill (timeout, peer left) leaves the copied bearer code on the OS clipboard. Design ceiling, not a retarget weakening. | Confirm the ceiling in the ops doc, or add a clear on next focus. |
| F4 | L | CORE-SELFCHECK R2-18, blueprint 6.2 | 30 B delta not reproduced. Explanation holds in code (see Part 1). Inserted statement is 48 B. | Record the pinned build output and hash next to the pin, or correct the figure. |
| F5 | L | probes/gate.py kill subrun inside mutation-all | Kill case can return SKIP rc 2 (devtools websocket closed), which fails mutation-all by design. Seen in the lead's first loop. Not reproduced here. | Retry once on devtools close, or report as a known harness flake. |
| F6 | L | gate.py case_budget, `frameTimes.length > 40` pin | Static pin not end-anchored, so `> 400` passes the static half. Behavioral half catches it (my mutant run). | Anchor the pin with a terminator. |
| F7 | L | gate.py case_ratchet postMessage scan | Scans 160 characters after each self.postMessage(. A key posted under a name outside the token list passes the static half. | Pin the payload shapes of worker postMessage calls. |
| F8 | L | gate.py case_lifecycle | Does not check the F-09 drop guard from the R2-08 card. The old case did not either, so this is not a weakening. Blob exemption covers only type text/javascript. | Add a drop-guard assertion. |
| F9 | L | blueprint R2-13 vs gate.py usage line and case_cover message | Spelling turns: vs turn:. Both PASS. | Align the three places. |
| F10 | I | brief and prompt | Brief says artifact commit 4a5d553, prompt says 1c6fd4a. HEAD is 1c6fd4a. Artifact identical at both. | None. |
| F11 | I | wrapper/scripts/selfcheck.sh step 14 | Passes in both placeholder and pinned state. Fail-closed is not tested by the script. Verified separately (Part 4). | Add a placeholder-behavior assertion. |
| F12 | I | CORE-SELFCHECK header | "partial" status with a 45 minute budget overrun by about ten minutes. Consistent with F1 and F4. | None. |

## Limits and deviations

- Budget: about 30 minutes was the target. I ran over.
- Gate and swift ran on a scratch copy of HEAD, not in the working tree (reason in Identity and method).
- Engine A and the nine R2b named cases were not executed (F1, Part 5).
- The electron check uses a stub, not an Electron runtime (Part 4).
- The pinned 31,103 B muxer build was not rebuilt (Part 1, F4).
- Evidence JSON from my gate runs was written into the scratch copy, not into the repo.

## Verdict basis

- Gate runs match the recorded runs: 20 of 20 pass, agreeing with the lead's addendum result.
- No retarget weakened its invariant. Seven of seven read against the card table. Mutant or behavioral evidence for four of them.
- Satellites pass: swift 21 of 21, wrapper selfcheck PASS, placeholder fails closed.
- Spot checks: six of six named scopes exist in the artifact.
- The brief's criteria hold. The findings above stay listed, not repaired. F1 is the item the parent should look at first.

READY
