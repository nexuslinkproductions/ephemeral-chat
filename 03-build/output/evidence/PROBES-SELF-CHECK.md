# PROBES lane self-check, W14 retarget to the final V2 artifact

RUN: w14-ephemeral-probes-retarget-20261127
SCOPE: `03-build/output/probes/`, `03-build/output/evidence/`.
STATUS: complete. Seven red cases retargeted, six media cases added, mutation-all
unblocked and green, full 20 case suite green on the final artifact.

## Artifact under test

```
path   03-build/output/ephemeral-chat-v2.html
sha256 6c8c1283047f6ce7d3b926e6fd190d3c46b345926aa0142e02827cf2dc02558d
bytes  165202
```

Every evidence JSON below records that hash. No snapshot was taken and no app
file was edited by this lane.

## Command form

Run from `04_PROJECTS/EPHEMERAL`:

```
python3 03-build/output/probes/gate.py <case> --app 03-build/output/ephemeral-chat-v2.html
```

Exit 0 PASS, 1 FAIL, 2 the case could not run. Cover takes the relay flag:

```
python3 03-build/output/probes/gate.py cover --app 03-build/output/ephemeral-chat-v2.html --relay-host turn:127.0.0.1:5349
```

## Part 1, the seven retargeted cases

Each retarget keeps the card's failure-mode invariant and records the card row.
A case that cannot reach its invariant exits 2; none of the seven does.

| Card | Case | Retarget, and the invariant it still proves | Raw last line | Evidence |
|---|---|---|---|---|
| R2-02 | envelope | The unknown `k` frame is produced by the app's own compress-then-encrypt path: a one shot shim transform rewrites the envelope plaintext before the worker seals it. The receiver decrypts a valid frame with an unknown `k`. Proves: visible line naming the value, no crash, no silent return, unknown `v` visible with no content render, malformed JSON counted, three unknown frames in 10 s runs Kill. Plaintext injection is no longer used because V2 rejects it before the router. | `PASS envelope` | `envelope-20261127-021702.json` |
| R2-03 | ratchet | `exportKey` is allowed on public keys only. The case scans every `exportKey` call (must carry `.publicKey`, never `privateKey`), asserts key generation is inside the Worker, scans every worker-to-main and main-to-worker `postMessage` argument for `rk`, `ckS`, `ckR`, `.priv`, `mkBytes`, `file.key`, `privateKey`, and asserts chain key state is not declared in the main thread. Behaviorally: two identical sends produce different sealed binary frames, no plaintext marker appears in any frame, five more sends are five distinct frames. | `PASS ratchet` | `ratchet-20261127-021712.json` |
| R2-05 | file | The first transfer proves the binary wire shape: start (type 1), chunk (type 2), end (type 1). Completeness is tested by riding the app's sealed send path with the declared size raised 64 KiB and one extra chunk: the sender streams the real bytes, the receiver reaches `f.received !== f.size`, and no Save anchor or blob exists. Digest is tested by sealing a complete transfer with a wrong digest: no anchor, no blob. A literal replay of the captured binary frames with the file-end tail dropped is the last step and must also produce no anchor and no blob. | `PASS file` | `file-20261127-021732.json` |
| R2-06 | budget | A bad file-start is now a valid sealed frame with `size = -1`, so it reaches the real refusal branch and the next valid transfer must still complete (F-04). A8 is tested with 45 frames the app seals itself in one burst, not plaintext noise, so every frame reaches the counter; the receiver must end and the ended text must name `A8` or `frame rate`. Static pins `MAX_ROWS = 2000`, the trim loop, `frameTimes.length > 40`, and the 2 MiB byte rule. | `PASS budget` | `budget-20261127-021749.json` |
| R2-08 | lifecycle | A received image URL is created first, then the draft and a synthetic URL. `pagehide` must clear all five text fields, the file input, the transcript, the gallery and about panels; every app blob URL except the Worker script URL and the case's synthetic URL must be revoked, the received media URL must be in the revoked set, the last revoke must see zero live DOM nodes, and no channel may stay open. `?idle=5` is still refused. | `PASS lifecycle` | `lifecycle-20261127-021813.json` |
| R2-09 | kill | The harness installs a CDP `Page.javascriptDialogOpening` handler that accepts the native confirm out of band, so `#wipe` no longer blocks the renderer. A copied invite code is required for the clipboard branch; the shim records `Clipboard.prototype.writeText` calls instead of touching the OS clipboard. Proves: wipe enabled before connect, double Escape kills, DOM cleared before revoke, an empty clipboard write on the kill path, and an exact `about:blank` navigation. | `PASS kill` | `kill-20261127-021830.json` |
| R2-11 | migrate | After the channel count check the case reads the new 60 digit SAS on both peers, asserts it differs from the pre-migration SAS (fresh keyset) and matches across peers, asserts content is locked again, confirms the new SAS on both sides, then asserts content flows on the migrated channel. A second migration with a shim-tampered `fp` in the sealed M1 offer must not commit and must report a migration failure. | `PASS migrate` | `migrate-20261127-021901.json` |

## Part 2, the six media cases

| Card | Case | Invariant proven | Raw last line | Evidence |
|---|---|---|---|---|
| R2-16 | media-order | `framePlain` compresses then pads to a 4096 byte bucket, `sealControl` frames before the AEAD call and binds `plain.length + 16` in the AAD, `openControl` asserts the length and zero padding, and `sendChunk` has no gzip pass. Behaviorally: every sealed control frame is a 4096 multiple and the media chunk frame is exactly the encoded bytes plus the GCM tag. Alias `media` maps to the same case. | `PASS media-order` | `media-order-20261127-022130.json` |
| R2-17 | exif | A real PNG carrying `tEXt` and `eXIf` markers is sent through the picker. The received blob must be WebP or JPEG, carry none of `Exif`, `GPS`, `XMP`, `iCCP`, `eXIf`, `Comment`, and the displayed name must match the encoded extension. Static: `encodeImage` has one call site inside `acceptFile`, and the picker, drop and paste all route through `acceptFile`. | `PASS exif` | `exif-20261127-022139.json` |
| R2-19 | bitrate | `VIDEO_CAP = 47185920`, the budget is `floor(VIDEO_CAP * 0.90)`, the retry is `bitrate * (VIDEO_CAP / size) * 0.95`, and the refusal names the reached size. `planBitrate` is extracted and executed with the artifact's own cap: projected budget, ten second bitrate, 1080/720/480 ladders, 600 s ceiling, zero duration. Engine A structural: `decoderConfig` asserted before `muxer.finalize()`, `frame.close()` present, `encodeQueueSize > 8` cap, rung B fallback. | `PASS bitrate` | `bitrate-20261127-022146.json` |
| R2-20 | playback | CSP carries `media-src blob:`. A 0.7 s video is generated in the page with MediaRecorder and dropped through the real drop handler, so this is live rung B. The received video must have no error, `readyState >= 1`, non-zero width and duration. Wipe must revoke the video URL after its node is gone and navigate to about:blank. | `PASS playback` | `playback-20261127-022147.json` |
| R2-21 | imagecap | `IMAGE_MAX_PX = 60000000`, the pixel gate precedes the destination canvas allocation, and `bitmap.close()` is in a `finally`. A fake `createImageBitmap` reports 20000 x 10000 px, so the gate refuses without allocating the image; the fake bitmap must be closed exactly once and no wire frame may leave. A real 2000 x 10 PNG must arrive with its long edge capped at 1600. | `PASS imagecap` | `imagecap-20261127-022200.json` |
| R2-22 | paste | `acceptFile` is the only entry point: `queueFiles` and `sendFile` both call it, and the picker, drop and paste callers route through those. A text-only paste is not prevented. Two unnamed pasted images arrive as `paste-1` and `paste-2`, so the name is counter based, not a timestamp. The single transcode guard is present. | `PASS paste` | `paste-20261127-022208.json` |

R2-18 transcode has no seventh case by design. Its failure mode is covered
structurally in `bitrate` (decoderConfig before finalize, frame close, queue cap)
and behaviorally through rung B in `playback`. Engine A cannot execute here:
`VideoEncoder` is undefined under the harness's headless `--disable-gpu`
Chromium, so engine A is static-only in this environment. Headed engine A
execution is named R4 work, along with a real >45 MiB clip for the retry path.

## Part 3, full suite on the final artifact

All 20 cases, one run each, artifact hash `6c8c1283...`, 165202 bytes.

| # | Card | Case | Exit | Raw last line | Evidence |
|---|---|---|---|---|---|
| 1 | R2-01 | selftest | 0 | `PASS selftest 2 peers, 1 channel, round trip, negative control fired` | `selftest-20261127-021658.json` |
| 2 | R2-02 | envelope | 0 | `PASS envelope` | `envelope-20261127-021702.json` |
| 3 | R2-03 | ratchet | 0 | `PASS ratchet` | `ratchet-20261127-021712.json` |
| 4 | R2-04 | sas | 0 | `PASS sas` | `sas-20261127-021723.json` |
| 5 | R2-05 | file | 0 | `PASS file` | `file-20261127-021732.json` |
| 6 | R2-06 | budget | 0 | `PASS budget` | `budget-20261127-021749.json` |
| 7 | R2-07 | code | 0 | `PASS code` | `code-20261127-021758.json` |
| 8 | R2-08 | lifecycle | 0 | `PASS lifecycle` | `lifecycle-20261127-021813.json` |
| 9 | R2-09 | kill | 0 | `PASS kill` | `kill-20261127-021830.json` |
| 10 | R2-10 | rotate | 0 | `PASS rotate` | `rotate-20261127-021849.json` |
| 11 | R2-11 | migrate | 0 | `PASS migrate` | `migrate-20261127-021901.json` |
| 12 | R2-12 | stun | 0 | `PASS stun` | `stun-20261127-021920.json` |
| 13 | R2-13 | cover | 0 | `PASS cover` | `cover-20261127-021926.json` |
| 14 | R2-15 | mutation-all | 0 | `PASS mutation-all` | `mutation-all-20261127-021932.json` |
| 15 | R2-16 | media-order | 0 | `PASS media-order` | `media-order-20261127-022130.json` |
| 16 | R2-17 | exif | 0 | `PASS exif` | `exif-20261127-022139.json` |
| 17 | R2-19 | bitrate | 0 | `PASS bitrate` | `bitrate-20261127-022146.json` |
| 18 | R2-20 | playback | 0 | `PASS playback` | `playback-20261127-022147.json` |
| 19 | R2-21 | imagecap | 0 | `PASS imagecap` | `imagecap-20261127-022200.json` |
| 20 | R2-22 | paste | 0 | `PASS paste` | `paste-20261127-022208.json` |

The six previously green cases stayed green: selftest, sas, code, rotate, stun,
cover, all exit 0 on the final artifact.

## Mutation sweep

`mutation-all` baselines every guarded case and then reverts each guard on a
scratch copy. Each revert must make its matching case exit 1 with a reason
different from the unmutated baseline. Seven guards:

```
code-cap      CODE_MAX = 16 * 1024 -> 1000000000        case code
preparse-cap  text.length > 65536 -> 1000000000         case code
ttl           TTL_MS = 120000 -> 1000000000             case code
row-cap       MAX_ROWS = 2000 -> 20                     case budget
kill-nav      about:blank -> about:log                  case kill
sas-lock      three disabled flags -> enabled           case sas
completeness  f.received !== f.size -> false            case file
```

Guard patterns are pinned to the constant or expression they guard, not to a
bare number, so a revert cannot land on an unrelated site. `kill-nav` is
detected by an exact `about:blank` href check, because Chrome reports
`about:blank#blocked` for an invalid `about:` target and a prefix check would
have passed it.

```
python3 03-build/output/probes/gate.py mutation-all --app 03-build/output/ephemeral-chat-v2.html
PASS mutation-all
rc=0
```

## Environment limits recorded, not hidden

- `VideoEncoder` is undefined in the harness Chromium (`--disable-gpu`). Engine
  A is asserted structurally. Rung B runs live in `playback`. Headed engine A
  execution and a real retry-path clip are R4 work.
- Ciphertext replay of an old control frame fails AEAD and ends the session, so
  it cannot reach the completeness branch. The completeness and digest branches
  are reached by mutating one plaintext field on the app's own sealed send path.
  The literal replay is still run last and must leave no Save anchor.
- The 200 MP image gate is exercised with a fake `createImageBitmap`, so no
  multi-hundred-megabyte allocation is needed; the close counter proves the
  `finally`.
- Video playback uses the live MediaRecorder rung, 0.7 s, in-page generated.

## Byte scan

```
probes/gate.py                     bytes=90531 non_ascii=0 en=0 em=0
evidence/PROBES-SELF-CHECK.md      bytes=12449 non_ascii=0 en=0 em=0
```

The scan counts bytes above 127 and the UTF-8 sequences `e2 80 93` and
`e2 80 94` in both files.

## W17 nine case registration

RUN: w17-ephemeral-ninecases2-20261127
STATUS: complete. Nine cases registered and green, 29 case suite green.

Artifact under test, unchanged by this lane:

```
path   03-build/output/ephemeral-chat-v2.html
sha256 6c8c1283047f6ce7d3b926e6fd190d3c46b345926aa0142e02827cf2dc02558d
bytes  165202
```

Command form, run from `04_PROJECTS/EPHEMERAL`:

```
python3 03-build/output/probes/gate.py <case> --app 03-build/output/ephemeral-chat-v2.html
```

Exit 0 PASS, 1 FAIL, 2 the case could not run. The new cases are appended to
`CASES` and `CARD_ORDER`; the 20 existing cases are unchanged.

### The nine cases

| Card | Case | Invariant the case proves | Raw last line | Evidence |
|---|---|---|---|---|
| UX-06 | panic | The wipe control is enabled at S0 and at S2, markup and code never disable it. One Escape closes the gallery and the about sheet without ending the session; a dismissed native confirm keeps the channel open; two Escapes inside 800 ms wipe, clear the copied code from the clipboard, empty the log, hide the verify panel, and leave no session id or 32 hex string in the ended DOM. | `PASS panic` | `panic-20261127-091706.json` |
| UX-02 | react | Caps pinned at frame 256, session 200, burst 20, refill 250 ms; palette is 24 word coded entries with 8 shown. A sealed react frame that arrives before SAS confirm is dropped with a visible line. Two identical adds for one mid render a count of 1 and both frames reach the wire. A react for an absent mid creates no row. An unknown shortcode renders no pill. A synchronous flood spends the bucket and the fifth drop kills with `react-flood`, with 0 to 20 frames on the wire. | `PASS react` | `react-20261127-091714.json` |
| UX-01 | mid | Every msg frame carries `mid`, 8 random bytes validated as 16 hex. Both peers show the same mid per message and two messages never share one. A reaction addressed by mid lands on that row only. A duplicate mid is rejected with a named line, keeps the first text, and leaves one row. `trimLog` calls `dropRow` before removing the node, and `dropRow` deletes the mid and reaction map entries. | `PASS mid` | `mid-20261127-091732.json` |
| UX-03 | nav | S0 to S4 each render one section with the documented focus move; no history entry is written across pairing, migration, or re-pairing. A migration raises the strip, locks the composer, attach and log, keeps the pending slot out of `slots.active`, then adopts on S2 with exactly one open channel and requires a fresh SAS confirm before S3. | `PASS nav` | `nav-20261127-091742.json` |
| UX-07 | gallery | No local storage, IndexedDB, cache, or file picker. The gallery is a view over `retained` blob URLs. Delete detaches the message card row before `revokeObjectURL` (`logLive` 0 at revoke), removes the Save anchor, the row, the tile, and the chip count. A dragstart on a tile is prevented and `draggable` is false. A bad digest produces no Save anchor and no tile. Eviction code is pinned statically (row first, `evictedCount`, gallery note). | `PASS gallery` | `gallery-20261127-091756.json` |
| UX-05 | pair | TTL starts at 110 to 120 s and counts down. A damaged code, a reused code, and a stale code each fail with an error and an empty reply field; none of the three error texts contains `v=0`, a candidate, a fingerprint, a ufrag, or an sdp. The consuming page refuses its own code on reuse. A fresh invite reaches a live pair that unlocks only after both confirms. | `PASS pair` | `pair-20261127-091806.json` |
| UX-04 | sas-ui | The panel renders twelve five digit cells, 60 digits, equal on both peers. The suite chip matches the panel and is not a placeholder. The composer and the `verified` chip stay locked through zero and one confirm; one confirm reads `waiting for peer`. Only both confirms produce `verified`, tone ok, S3, and a flowing message. The rendered DOM (scripts and textarea values excluded) carries no session id, no `eph_pk` or `stat_pk` value, no 64 hex string, and no SDP line. A mismatch ends on S4 titled `Verification failed` with no content. | `PASS sas-ui` | `sas-ui-20261127-091820.json` |
| UX-08 | a11y | Both theme blocks clear 4.5:1 for text, muted, faint, accent, danger, ok and wait (minimum 5.24:1, dark faint). The 2 px accent focus ring with a 2 px offset is present. Under an emulated reduced motion preference the one animated rule computes to 0 s, animation none, scroll behavior auto. Light and dark tokens apply to computed body colors. Transcript role log with aria-live polite, ended role alert, status roles, no `role="button"`, no inline click. Pills are buttons, aria-pressed, with a word label, inside an `aria-live="off"` container; a reaction leaves the log live setting at polite. | `PASS a11y` | `a11y-20261127-091837.json` |
| R2-18 | transcode | Engine A asserts a non null `decoderConfig` on the first chunk before `muxer.finalize()`, creates two `VideoFrame` sites, closes the frame in a finally, caps `encodeQueueSize` at 8 and pauses and resumes the decoder on dequeue, and probes `isConfigSupported`. `transcodeAndSend` tries A first, names the fallback, and records the engine. Live: a 14 s 720p clip over 45 MB reaches the draft card, engine A is forced unavailable, the fallback line appears, rung B constructs a MediaRecorder, the output is delivered, and the receiver plays a 1280x720 video with a finite duration. | `PASS transcode` | `transcode-20261127-091845.json` |

### Suite, 29 cases, one run each

Artifact hash `6c8c1283...`, 165202 bytes. Raw log `W17-suite-raw.log`,
machine summary `W17-suite.json`.

| # | Card | Case | Exit | Raw last line | Evidence |
|---|---|---|---|---|---|
| 1 | R2-01 | selftest | 0 | `PASS selftest` | `selftest-20261127-091201.json` |
| 2 | R2-02 | envelope | 0 | `PASS envelope` | `envelope-20261127-091205.json` |
| 3 | R2-03 | ratchet | 0 | `PASS ratchet` | `ratchet-20261127-091215.json` |
| 4 | R2-04 | sas | 0 | `PASS sas` | `sas-20261127-091226.json` |
| 5 | R2-05 | file | 0 | `PASS file` | `file-20261127-091235.json` |
| 6 | R2-06 | budget | 0 | `PASS budget` | `budget-20261127-091248.json` |
| 7 | R2-07 | code | 0 | `PASS code` | `code-20261127-091257.json` |
| 8 | R2-08 | lifecycle | 0 | `PASS lifecycle` | `lifecycle-20261127-091312.json` |
| 9 | R2-09 | kill | 0 | `PASS kill` | `kill-20261127-091330.json` |
| 10 | R2-10 | rotate | 0 | `PASS rotate` | `rotate-20261127-091343.json` |
| 11 | R2-11 | migrate | 0 | `PASS migrate` | `migrate-20261127-091355.json` |
| 12 | R2-12 | stun | 0 | `PASS stun` | `stun-20261127-091414.json` |
| 13 | R2-13 | cover | 0 | `PASS cover` | `cover-20261127-091420.json` |
| 14 | R2-15 | mutation-all | 0 | `PASS mutation-all` | `mutation-all-20261127-091426.json` |
| 15 | R2-16 | media-order | 0 | `PASS media-order` | `media-order-20261127-091619.json` |
| 16 | R2-17 | exif | 0 | `PASS exif` | `exif-20261127-091627.json` |
| 17 | R2-19 | bitrate | 0 | `PASS bitrate` | `bitrate-20261127-091635.json` |
| 18 | R2-20 | playback | 0 | `PASS playback` | `playback-20261127-091636.json` |
| 19 | R2-21 | imagecap | 0 | `PASS imagecap` | `imagecap-20261127-091649.json` |
| 20 | R2-22 | paste | 0 | `PASS paste` | `paste-20261127-091657.json` |
| 21 | UX-06 | panic | 0 | `PASS panic` | `panic-20261127-091706.json` |
| 22 | UX-02 | react | 0 | `PASS react` | `react-20261127-091714.json` |
| 23 | UX-01 | mid | 0 | `PASS mid` | `mid-20261127-091732.json` |
| 24 | UX-03 | nav | 0 | `PASS nav` | `nav-20261127-091742.json` |
| 25 | UX-07 | gallery | 0 | `PASS gallery` | `gallery-20261127-091756.json` |
| 26 | UX-05 | pair | 0 | `PASS pair` | `pair-20261127-091806.json` |
| 27 | UX-04 | sas-ui | 0 | `PASS sas-ui` | `sas-ui-20261127-091820.json` |
| 28 | UX-08 | a11y | 0 | `PASS a11y` | `a11y-20261127-091837.json` |
| 29 | R2-18 | transcode | 0 | `PASS transcode` | `transcode-20261127-091845.json` |

### Binding proof, panic and react

Both reverts ran on scratch copies, never on the pinned artifact. The copies
differ in size (165155 and 165151 bytes) and hash, so the evidence JSON records
a mutated app, not the shipped one.

```
panic guard: if (palettePop || !el.gallery.hidden || !el.about.hidden) {  ->  if (false) {
python3 03-build/output/probes/gate.py panic --app .../panic-revert.html
FAIL panic one Escape did not close the gallery: got False, want True
rc=1

react guard: const control = k === 'sas-confirm' || k === 'sas-bad' || k === 'panic';  ->  const control = true;
python3 03-build/output/probes/gate.py react --app .../react-revert.html
FAIL react a react frame before SAS confirm left no drop line
rc=1

restore, pinned artifact:
python3 03-build/output/probes/gate.py panic --app 03-build/output/ephemeral-chat-v2.html
PASS panic
rc=0
python3 03-build/output/probes/gate.py react --app 03-build/output/ephemeral-chat-v2.html
PASS react
rc=0
```

The two FAIL records are `panic-20261127-091100.json` (165155 bytes) and
`react-20261127-091108.json` (165151 bytes). An earlier `react` record at
`react-20261127-084051.json` is a development run of the case itself before its
wire assertion was corrected to the bucket ceiling; it is not part of this
proof.

### Findings and limits, recorded not hidden

1. Gallery eviction is unreachable from the receive path. `onFileStart` refuses
   at `receivedFiles >= MAX_FILES` and `evict()` only runs when
   `receivedFiles > MAX_FILES`, so the fifth accepted transfer never starts.
   `deleteRetained` also does not decrement `receivedFiles`, so a delete does
   not free the budget. The case pins the evict code and the gallery note
   statically and proves the reachable cap refusal behavior; it does not claim
   a live eviction line. R4 fix: admit the over-cap file and let `evict` run,
   or decrement the counters on delete.
2. Gallery delete detaches the message card row before the revoke
   (`lastRevoke.logLive` is 0) but the gallery tile image is still attached at
   that instant (`tileLive` 1); `renderGallery()` removes it synchronously in
   the same task, so no frame paints a revoked image. The case asserts the
   message card ordering, which is the card failure mode; strict zero node
   ordering is proven on the wipe path by `lifecycle`.
3. Engine A exists in this Chromium (`typeof VideoEncoder` is function), so the
   transcode case forces it unavailable to run the fallback deterministically.
   A headed engine A run on a GPU box is R4 work.
4. A rung B output over about 2.6 MB trips the A8 frame rate rule on an
   unthrottled loopback, because every 64 KiB data chunk counts as a frame and
   the rule kills above 40 frames in 5 s. The transcode case models a real link
   by delaying `Blob.slice().arrayBuffer()` 150 ms per chunk; the delivery then
   completes and the receiver plays the video. R4 should exempt data chunks
   from the frame count or widen the window.
5. `showScreen` implements S0 to S4. The source comment and the card name say
   S0 to S5; no S5 state exists. Sheets are layers, not screens. The nav case
   asserts the five implemented states; the panic case asserts the layer rule.
6. A damaged gzip code surfaces the raw DecompressionStream message
   (`incorrect header check`) instead of a friendly string. It leaks no SDP or
   candidate and produces no reply, so the gate passes; it is UX polish, not a
   security gap.

### Byte scan, W17

```
probes/gate.py                     bytes=152475 non_ascii=0 en=0 em=0
evidence/PROBES-SELF-CHECK.md      bytes=23973 non_ascii=0 en=0 em=0
```

The W14 byte line earlier in this file is historical.
