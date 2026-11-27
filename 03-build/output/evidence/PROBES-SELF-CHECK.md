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
