# CORE lane self-check, R2b, media and UX cards

> Current artifact after the W18 fix lane: sha256 `d4d48d37...`, 165744 bytes. This W13 block is the historical record of that run; the W18 section at the end is the current state.

RUN: w13-ephemeral-build-r2b-20261127
ARTIFACT: 03-build/output/ephemeral-chat-v2.html
SHA-256: 6c8c1283047f6ce7d3b926e6fd190d3c46b345926aa0142e02827cf2dc02558d
BYTES: 165,202
STATUS: partial. All fifteen cards are applied in the brief's order and the six green gate cases are green on three consecutive runs. Two limits are named rather than hidden: the mp4-muxer block is 31,133 B against the 31,103 B pin (30 B, explained in R2-18), and WebCodecs engine A could not be executed in the gate's headless Chromium because `VideoEncoder` is absent there, so engine A is statically verified while rung B ran live. Time budget was exceeded by roughly ten minutes.

Only writes: `03-build/output/ephemeral-chat-v2.html` and this file. No gate, probe, evidence, monitor or wrapper file was touched.

## Static checks, all cards

Byte and sink scan, run at the final artifact:

```
$ python3 - <<'EOF'
b=open('03-build/output/ephemeral-chat-v2.html','rb').read(); t=b.decode()
print('bytes', len(b))
print('nonascii', sum(1 for x in b if x>127))
print('emdash', t.count('\u2014'), 'endash', t.count('\u2013'))
for p in ['innerHTML','eval(','new Function','localStorage','document.cookie','serviceWorker']:
    print(repr(p), t.count(p))
print('media-src blob:', t.count('media-src blob:'))
EOF
```
Output:
```
bytes 165202
nonascii 0
emdash 0 endash 0
'innerHTML' 0
'eval(' 0
'new Function' 0
'localStorage' 0
'document.cookie' 0
'serviceWorker' 0
media-src blob: 1
```

Syntax, all three script blocks extracted from the artifact and checked with Node:
```
$ python3 - <<'EOF'   # extract blocks 0..2 to /tmp/blkN.js
$ for f in /tmp/blk*.js; do node --check "$f" && echo "OK $f"; done
```
Output:
```
OK /tmp/blk0.js
OK /tmp/blk1.js
OK /tmp/blk2.js
```
Block 0 is the vendored muxer, block 1 the crypto Worker, block 2 the app.

Pinned selectors, unchanged and single-instance:
```
id="confirmSas" 1   id="digits" 1   id="rotate" 1   id="migrate" 1
id="input" 1        id="offer" 1    id="answer" 1   id="wipe" 1
```
`#wipe` has no `disabled = true` assignment anywhere: `el.wipe.disabled = true` occurs 0 times, so UX-06's always-enabled rule holds.

Selector mapping for the brief's "reply": the reply surface is still `#answer` (their reply) and `#answerIn` (paste the reply), with the button text "Create reply". No id was renamed, and `#offer`, `#offerIn`, `#confirmSas`, `#digits`, `#rotate`, `#migrate`, `#input` and `#wipe` keep their names and roles.

Form factor: one HTML file, no external asset, no build step. The muxer is inlined. The CSP is unchanged except for the one directive R2-20 needs:
```
default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src blob: data:; media-src blob:; worker-src blob:; connect-src 'none'; base-uri 'none'; form-action 'none'
```

## Cards

### R2-16 Encryption ordering, PASS

`sealControl` now runs `framePlain` (compress, then pad) before the AEAD, and `openControl` asserts the frame is on a 4,096 B boundary and that the true length inside agrees with it. The AAD binds the frame length, which is the only length a receiver can know before decrypting; the true length travels inside the padded plaintext, so a swapped or truncated ciphertext fails the tag before any length is trusted. That is the honest reading of "bound in the AAD": the length that is bound is the padded frame length, and the inner true length is asserted against it.

Order proof from the source, positions in bytes:
```
compress_before_pad_before_seal True
```
`gzipBytes(raw)` at the `framePlain` call, then `const padded`, then `crypto.subtle.encrypt` in `sealControl`.

Live unit test, worker source extracted from the artifact, run in Node with the WebCrypto and Streams globals:
```
$ node /tmp/padtest.js
cipher_len 4112 mod4096_is16 true
roundtrip_equal true
tamper_rejected frame did not authenticate
trunc_rejected frame did not authenticate
```
4,112 = 4,096 plaintext bucket + 16 B GCM tag. A one-bit flip and a truncation both fail. Per-message keys are the pre-existing `stepSend`/`stepRecv` ratchet, unchanged.

### R2-17 Metadata strip, PASS

`encodeImage` decodes with `createImageBitmap(file, {imageOrientation:'from-image'})`, draws into a canvas, encodes WebP with a startup probe, and throws if `blob.type` is not the requested type. A canvas output cannot carry EXIF, GPS, XMP or ICC because a canvas holds pixels only. Live proof with a PNG fixture carrying a `tEXt` chunk `Exif SECRETGPS LEAKMODEL GPS` (123 B, the control had `Exif` and `SECRETGPS` present):

```
anchor True
C blob types ["image/webp:550"]
A blob types ["image/webp:550"]
C scan [{"type":"image/webp","size":550,"exif":false,"gps":false,"icc":false,"head":[82,73,70,70]}]
A scan [{"type":"image/webp","size":550,"exif":false,"gps":false,"icc":false,"head":[82,73,70,70]}]
name exif-test.webp
```
The sent and received bytes start `RIFF` (WebP), 550 B, every marker absent. The `blob.type` assertion is live code: an encoder that returned `image/png` for a WebP request throws instead of sending.

### R2-18 Transcode engine A, PASS static, engine A unexercised

Present and statically ordered: `transcodeA` element decode, `requestVideoFrameCallback` loop, `new VideoFrame(video)` or canvas frame, `frame.close()` in `finally`, `encodeQueueSize > 8` pause/dequeue backpressure, `Mp4Muxer.Muxer` with `ArrayBufferTarget` and `fastStart: 'in-memory'`, `firstMeta.decoderConfig` asserted before `muxer.finalize()`, and the `MediaRecorder` rung B on any failure.

```
encodeQueueSize > 8 1
frame.close() 1
firstMeta.decoderConfig 1
muxer.finalize() 1
decoderconfig_before_finalize True
MediaRecorder 6
```

Muxer bytes, DEVIATION NAMED: the vendored block is 31,133 B minified (block body 31,135 including the two newlines around it). The blueprint pin is 31,103 B for entry `export {Muxer, ArrayBufferTarget} from 'mp4-muxer'` with esbuild 0.25.0, and that exact build discards the exports: a byte scan of the 31,103 B output finds 0 occurrences of `Mp4Muxer`, so it cannot drive a muxer. The shipped build is the same package and command with `window.Mp4Muxer = {Muxer, ArrayBufferTarget}` added, which costs 30 B. The pin is embedded, not fetched; the 30 B difference is the only way to have both the pinned version and a working global. Flagged for the lead rather than silently floated.

Engine A could not run here: the gate's Chromium is `--headless=new --disable-gpu`, and `typeof VideoEncoder` there is `"undefined"`. The live transcode therefore exercised the rung B fallback, which is the specified behaviour when WebCodecs is missing:

```
draft line 'Will be re-encoded to 360p, about 40.5 MB, and about 3 seconds of processing.'
send enabled True
anchor True
C blob types [...{"size":75165,"type":"video/mp4"}]
C log 'probe-source.mp4 73.4 KB Type: video/mp4 verified Save File received and verified: probe-source.mp4'
```
Engine A itself is code-reviewed and syntax-checked, not behaviourally proven in this lane. That is the largest open item.

### R2-19 Projected size before commit, PASS

`planBitrate` plans at 90 percent of 47,185,920 B, subtracts 96 kbps audio bytes, and caps height by duration (1080 / 720 / 480, refuse over 600 s). The projection is rendered into a draft card and the Send button exists only on that card, so no transfer can start before the projection is shown. Post `flush()` size check with one retry at `bitrate * (cap / size) * 0.95`, then a refusal that names the size reached.

Live, on a 47,202,304 B MP4 (a valid 2.5 s clip padded past the cap):
```
draft line 'Will be re-encoded to 360p, about 40.5 MB, and about 3 seconds of processing.'
send enabled True
```
The 360p choice is `min(source height, ladder height)`, so a 640x360 source is not upscaled. The retry branch did not fire because the result was 75,165 B, well under the cap; it is static-only evidence.

### R2-20 Playback from RAM, PASS

`media-src blob:` is in the CSP. Received media becomes an in-memory Blob, `URL.createObjectURL`, then `video.src`. The URL is pushed into `urls` and `rowUrls`. Wipe order is DOM first (`el.log.replaceChildren()`), then revoke, then the array is emptied, which is already the R2a order and is preserved.

Live:
```
C video {"src":"blob:","ready":4,"network":1,"err":null,"dur":1.08,"w":320,"h":180}
```
readyState 4 with a blob source and no error is the direct contrast to the measured V1 failure (error 4, readyState 0) when `media-src` is absent.

### R2-21 Image memory ceiling, PASS

Pixel gate runs on the decoded bitmap before any destination canvas exists:
```
pixel_gate_before_canvas True gate_line 2525 canvas_line 2537
```
`if (px > IMAGE_MAX_PX)` (60,000,000) returns without allocating the destination and without sending the original. `bitmap.close()` is in the `finally`. The gate is on decoded dimensions, so orientation changes which side is long, not the count.

### R2-22 One path, PASS

`acceptFile(file, source)` is the only entry, and the three callers pass a source:
```
function acceptFile(file, source) 1
queueFiles(files, 'pick')         1
queueFiles(..., 'drop')           1
queueFiles(files, 'paste')        1
```
Animated images go to the file path (no re-encode), images go through `encodeImage`, video through `prepareVideo`, everything else unchanged. Synthesized names use a counter (`pasted-1.png`), never a timestamp. Paste still reads only `clipboardData.files` and returns for text.

### UX-01 Message identity, PASS

`msg` carries `mid` (16 hex), `addMessage(text, mine, mid)` stores the id on the row and in `msgRows`, and a duplicate id is rejected with a system line instead of a second node. `trimLog` calls `dropRow`, which deletes the reaction map entry and the `msgRows` entry with the node. Live: the wire message rendered on the peer and its `data-mid` was `6a3dbe05014509e5`.

### UX-02 Reactions, PASS

`react` is a dispatch-table row with `{t, e, op}`, accepted only when live (the pre-confirm router drops it), 256 B frame cap, 24-entry palette as the allowlist, 200 marks per session, a 20-token bucket refilling at 4 per second, and 5 drops in 10 s running A1 with `react-flood`. Duplicate add/remove is idempotent because apply assigns a boolean. Pills are `<button>` with `aria-pressed`, one per distinct shortcode, 8 shown then `+N`, in a container with `aria-live="off"`.

Live two-peer run:
```
C pill after A react: thumbsup, 1 reaction | pressed=false
A pill after C react: thumbsup, 2 reactions, one of them yours | pressed=true
C pill after C react: thumbsup, 2 reactions, one of them yours | pressed=true
```
The count moved 1 to 2 exactly once, and `pressed` tracks each side's own boolean.

### UX-03 Screen state machine and slots, PASS

`showScreen` is the only visibility writer for S0 to S4 and sets `document.body.dataset.screen`. `slots.active` is set on channel open and adopt, `slots.pending` only while `mig` exists, and both are nulled on end. Migration sets a strip (step 1 of 4 / 2 of 4), locks the log and disables input, send, attach, rotate and migrate; adopt clears the strip, clears the reaction map with the old transcript, and returns to S2. Live: `screen S3` after confirm, `screen S3` after a gallery Escape, ended panel false.

### UX-04 Verification panel and crypto status, PASS

Chips: verification, suite, ratchet age, file count, About. `chipVerify` reads `unverified` until a local confirm, `waiting for peer` / `waiting for you` while one side is in, and `verified` only when both are. Live: `chip verified`. The 60-digit render and the `#confirmSas` gate are unchanged. Aging banner appears at 20 minutes from session key time and Later dismisses for 10 minutes in memory only. No session id or key byte is written to the DOM.

### UX-05 Pairing panel states, PASS

TTL countdown under the invite (`Code expires in N s`, then `Code expired`, connect disabled), single-use via `consumedSids` and `replyUsed`, and a debounced parse preview under the paste field that shows `Code for <6 hex>, <suite>, issued N s ago` or the specific error string. Preview calls the same `unpackCode` so the caps and TTL are the ones that will be enforced. Error strings keep their V2 specificity and never include the SDP or candidates.

### UX-06 Wipe and panic, PASS

Wipe is present on every screen and never disabled. Double Escape within 800 ms with no layer open runs the wipe; with a layer open (palette, gallery, About) the first Escape closes the layer and resets the counter. Live:
```
layer_escape gallery_hidden True screen S3 ended False
```
Two presses while a sheet is open did not destroy the session. The ended panel shows a reason and no session id, and keeps the 4 s / 1.5 s countdowns.

### UX-07 Media gallery, PASS

The Files chip opens a sheet over `retained` (one array shared with the cards), with image/video tiles from the existing blob URLs, a Save only from the card, `draggable=false` plus `dragstart` prevention, and delete that removes the DOM node first, then the URL, then the array entry. Eviction keeps the count and writes the honest line when `evictedCount` is nonzero.

Live:
```
gallery_open True tiles 1 note ''
after_delete tiles 0 cards 1 -> 0 revoked_delta 1
```
Exactly one URL was revoked and the card node went with it. The eviction line is static-only evidence (no budget hit in the run).

### UX-08 Theme and accessibility baseline, PASS static

Token set in `:root`, a `prefers-color-scheme: light` block that redefines every token (light text `#16191d` on `#f6f7f9`, muted `#555d68`, accent `#2456c8`, all above 4.5:1 by arithmetic), `:focus-visible` 2 px ring with offset, `prefers-reduced-motion: reduce` disabling transitions and animations, pills as buttons with text labels and `aria-hidden` glyphs, and `aria-live="off"` on the pill container while the transcript stays polite. Emoji are `\u` escapes, so the file stays ASCII.

## Six-green regression guard

The gate's media and UX case names (`media-order`, `exif`, `transcode`, `bitrate`, `playback`, `imagecap`, `paste`, `mid`, `react`, `nav`, `sas-ui`, `pair`, `panic`, `gallery`, `a11y`) do not exist in `probes/gate.py` yet; only the fourteen R2a cases are registered. So the required guard is the six green cases the brief names. Command form, from `04_PROJECTS/EPHEMERAL`, with `cover` taking the relay flag it requires:

```
python3 03-build/output/probes/gate.py <case> --app 03-build/output/ephemeral-chat-v2.html
python3 03-build/output/probes/gate.py cover --app 03-build/output/ephemeral-chat-v2.html --relay-host turns:127.0.0.1:5349
```

| Case | Run 1 | Run 2 | Run 3 |
|---|---|---|---|
| selftest | PASS | PASS | PASS |
| sas | PASS | PASS | PASS |
| code | PASS | PASS | PASS |
| rotate | PASS | PASS | PASS |
| stun | PASS | PASS | PASS |
| cover | PASS | PASS | PASS |

Raw output of the last run, verbatim:
```
== selftest ==
PASS selftest 2 peers, 1 channel, round trip, negative control fired
PASS selftest
rc=0
== sas ==
PASS sas
rc=0
== code ==
PASS code
rc=0
== rotate ==
PASS rotate
rc=0
== stun ==
PASS stun
rc=0
== cover ==
PASS cover
rc=0
```
Run 1 and run 2 produced the same `PASS` and `rc=0` line for each case. Run 1 predates the inbound-ordering fix, the draft-card preview method and the playback preview fix. Run 2 started while the last one-line adopt patch was landing, so run 3 is the only run that is unambiguously after every change; it is also the run quoted above. The seven red R2a cases were not modified for and not re-run: no artifact change was made to satisfy a probe-side defect.

## Fixes found by this wave's own probes

Three defects were introduced and caught by the probes above, then fixed before the final runs:

1. `framePlain` allocated the body one byte short of its flag byte, so every control frame threw `offset is out of bounds`. Caught by a Node harness over the extracted worker.
2. Control-frame AAD used the plaintext length on send and the ciphertext length on receive, so the first confirm frame failed to authenticate. Caught by `gate.py sas` failing to unlock; fixed to bind the ciphertext length on both sides.
3. Control frames became 4 KB padded, which made the receive path slow enough that a file chunk could overtake its `file-start`. Inbound frames are now serialized through `onWireQueued`, which also removes the latent out-of-order chunk race. Caught by a received image reporting `incomplete: 0 of 550 bytes`.

## Time and status

Started 01:30, stopped 02:25. Over the 45 minute budget by about ten minutes, spent on the three defects above and on the live video path. STATUS partial for that reason and for the two named limits (muxer 30 B, engine A unexercised); every card is applied.

---

# R2a record, previous wave (kept for history)

The record below describes the R2a snapshot, 87,767 B, SHA-256 4cd68b31e91b29742b84247a25a5e40793ae34def88d8ea8fb433cc79a084d8a. The artifact header at the top of this file supersedes it; the code changes below are still in the shipped file.

## Static checks, all cards

Command:
```
python3 - <<'EOF'
b=open('03-build/output/ephemeral-chat-v2.html','rb').read(); t=b.decode()
print('nonascii', sum(1 for x in b if x>127))
print('emdash', t.count('\u2014'), 'endash', t.count('\u2013'))
for p in ['innerHTML','eval(','new Function','localStorage','document.cookie','serviceWorker','atob(','function ub64u(']:
    print(repr(p), t.count(p))
EOF
```
Output:
```
nonascii 0
emdash 0 endash 0
'innerHTML' 0
'eval(' 0
'new Function' 0
'localStorage' 0
'document.cookie' 0
'serviceWorker' 0
'atob(' 1
'function ub64u(' 1
```

Syntax, both script blocks extracted and checked:
```
node --check /tmp/v2w.js && node --check /tmp/v2m.js && echo SYNTAX_OK
```
Output: `SYNTAX_OK`.

Form factor unchanged: single HTML file, no external asset, no build step, CSP adds `worker-src blob:` only.

## Fixes in this wave

### 1. base64url, one decoder for both realms

Finding: on this base both atob sites (worker line 499, main line 1137) already convert the URL safe alphabet on the line above the atob call, so the reported defect (dash or underscore throws) was not reproducible. The class fix landed as a single definition: `ub64u` is declared once in the main script and its source is injected into the worker blob, so the alphabet conversion and padding exist in exactly one place. `grep` now shows one `atob(` and one `function ub64u(` in the artifact.

Worker construction:
```
const workerSrc = "'use strict';\n" + ub64u.toString() + ';\n' + document.getElementById('cryptoWorker').textContent;
```

Helper check, every padding class plus a 934 character base64url string containing both characters, decoded byte for byte against Buffer:
```
OK len34 mod2 46 34
OK len35 mod3 47 35
OK len36 mod0 48 36
OK len37 mod2 50 37
OK len38 mod3 51 38
OK len39 mod0 52 39
has_dash true has_underscore true
OK 700 934 700
```
Live round trip, real invite between two contexts (length varies with the ICE candidates, 872 to 909 across runs; this run 879):
```
invite_len 879 dash 8 underscore 18 prefix E2.1.
sas_len_A 60 sas_len_C 60 match True
```

### 2. SAS confirm navigation, re-derived

Finding: the current base does not navigate on confirm. The observed about:blank in the probes notes came from the migration run, where `endSession('anomaly', 'A3 renegotiation')` fired one frame after the click, and endSession schedules `location.replace('about:blank')` at 4 s. The confirmSas handler itself only sets `localConfirm`, sends the control frame and calls `maybeLive`; no navigation path exists. No code change was needed for this item.

Proof on the final artifact, both sides confirm, then an 11 second watch:
```
sas_match True len 60
composer_locked_before True True
composer_locked_after False False
href_after_11s_stable True t/ephemeral-chat-v2.html t/ephemeral-chat-v2.html
ended_hidden True True
post_confirm_text True
```
`gate.py sas` also passes, twice, before and after the helper change: `PASS sas`.

### 3. R2-11 Migrate, three root causes

Reproduced with two real contexts: click `#migrate`, both pages reached `session ended` inside one second, A with `Session killed / A protocol anomaly was detected (A3 renegotiation)`, C with `The other person left`.

1. A3 on the pending peer. `newPeer` treated every negotiationneeded event as an attack. The migration peer creates its own data channel, which fires negotiationneeded while phase is `migrating`, so the live session was killed before ICE even started. Fix: the connectionstatechange and negotiationneeded guards now apply only when `peer === pc`, so a pending peer can neither end nor alarm the live session; after adopt it becomes `pc` and the guards apply again.
2. Envelope sid overwrite. `sendControl` merged the caller object last, so the mig offer, answer and done frames carried the NEW sid in the envelope. The old channel's router rejected them as stale (`A frame from a stale session was rejected.`) and migration never started. Fix: envelope fields win (`Object.assign({}, obj, {v, k, sid: sessionSid, seq})`) and the new sid travels in `nsid`; migOffer, migAnswer and migDone read `nsid`.
3. Role mapping on adopt. `adopt` passed `m.role` (`answer`) to the worker, and `derive` maps anything that is not `join` to `offer`, so both sides derived the offer role and could never agree on SAS or chains. Fix: `role: m.role === 'offer' ? 'offer' : 'join'`.

Also found by the lifecycle case and fixed: pagehide wiped codes, log and blobs but left the message draft in `#input`. One line added.

Behavioral run on the final artifact, fresh keyset:
```
new_sas_A 244579707415522279380733991068675176564348363803312401889480
new_sas_C 244579707415522279380733991068675176564348363803312401889480
new_sas_match True len 60
lock_after_migrate True True
composer_enabled_A True C True
phaseA verified phaseC verified
text_arrived True
href_stable file:///Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/03-build/output/ephemeral-chat-v2.html
```
Both contexts reach the new 60 digit SAS with the fresh keyset, confirm it, unlock and exchange text, with no navigation.

## Gate run, full suite, this artifact

Commands, each with `GATE_NO_EVIDENCE=1` so the run does not write into the probes lane scope:
```
python3 03-build/output/probes/gate.py selftest
python3 03-build/output/probes/gate.py envelope
python3 03-build/output/probes/gate.py ratchet
python3 03-build/output/probes/gate.py sas
python3 03-build/output/probes/gate.py file
python3 03-build/output/probes/gate.py budget
python3 03-build/output/probes/gate.py code
python3 03-build/output/probes/gate.py lifecycle
python3 03-build/output/probes/gate.py kill
python3 03-build/output/probes/gate.py rotate
python3 03-build/output/probes/gate.py migrate
python3 03-build/output/probes/gate.py stun
python3 03-build/output/probes/gate.py cover --relay-host turn:127.0.0.1:5349
```
Raw output:
```
=== CASE selftest
PASS selftest 2 peers, 1 channel, round trip, negative control fired
PASS selftest
EXIT selftest 0
=== CASE envelope
FAIL envelope unknown k left no visible system line
EXIT envelope 1
=== CASE ratchet
FAIL ratchet artifact calls exportKey, key bytes are readable from the main thread
EXIT ratchet 1
=== CASE sas
PASS sas
EXIT sas 0
=== CASE file
FAIL file file-start and file-end were not captured
EXIT file 1
=== CASE budget
FAIL budget a 200 frame burst did not trip the A8 rate rule
EXIT budget 1
=== CASE code
PASS code
EXIT code 0
=== CASE lifecycle
FAIL lifecycle pagehide left a blob URL live: got 2, want 0
EXIT lifecycle 1
=== CASE kill
SKIP kill harness error: timeout: timed out
EXIT kill 2
=== CASE rotate
PASS rotate
EXIT rotate 0
=== CASE migrate
FAIL migrate no traffic on the migrated channel
EXIT migrate 1
=== CASE stun
PASS stun
EXIT stun 0
=== CASE cover
PASS cover
EXIT cover 0
```

## Why six cases are still red, all probe side

Each one traced to the gate harness, not to the artifact. None of these can be fixed inside the artifact without weakening a card.

- envelope: the case injects a plaintext string with `window.__probe.send`. V2 correctly rejects every plaintext frame before the router (`A plaintext frame was rejected.`), so the unknown-k and version branches are never reached. The case must encrypt through the app's own send path.
- budget: same plaintext burst, so the A8 rate rule never sees the frames.
- ratchet: the case bans the string `exportKey` outright. The artifact exports only PUBLIC keys in the worker (`exportKey('raw', kp.publicKey)`) to publish them; private keys stay non-extractable. The ban must be narrowed to private key export.
- file: the case expects string `file-start` and `file-end` frames on the wire. V2 sends every frame encrypted as binary, so the string capture is empty by design.
- lifecycle: the blob counter includes the worker script URL and the probe's own synthetic URL, neither of which the app owns. The draft clear itself now passes.
- kill: the case clicks `#wipe` and the artifact's confirm() dialog blocks the CDP evaluate; the harness has no dialog handler (already recorded as a known limit).
- migrate: the case clicks `#migrate` and then sends text without confirming the new SAS. The artifact correctly locks content until both sides confirm the new safety number. The case needs a `confirm_sas(a, c)` call plus a wait after the channel count check.

## Per card

| Card | Status | Evidence and command |
|---|---|---|
| R2-02 Control envelope and router | PASS (static and behavioral) | Encrypted `{v,k,sid,seq}` frames only; envelope fields can no longer be overridden by payload, which was the migrate defect. Unknown k, version skew, seq resync and stale sid branches present. Gate case red only because it injects plaintext. |
| R2-03 Crypto core in the Worker | PASS | Worker holds all key material, only public keys are exported. Worker source is now `'use strict'` plus the injected decoder. Gate case red on its blanket exportKey ban. |
| R2-04 SAS gate | PASS | `composer_locked_before True True`, `composer_locked_after False False`, same 60 digits, `href_after_11s_stable True`, `post_confirm_text True`. `gate.py sas` PASS. |
| R2-05 File integrity | PASS (narrow) | Received PNG card reaches `verified` with a live blob image and Save anchor in 0.5 s. `gate.py file` red on its string frame expectation. |
| R2-06 Inbound budgets | PARTIAL | 40 frames/5 s and 2 MB/s kill, 2000 row cap, 4 files / 200 MiB, 60 s transfer idle, overlap rule all present. Not exercised behaviorally; the gate burst is plaintext and is rejected at the wire before the counter. |
| R2-07 Code envelope | PASS | `gate.py code` PASS: paste cap, 64 KB decompressed cap, 120 s TTL, 32 candidate cap, unknown version refused before a peer is created. |
| R2-08 Lifecycle and idle | PASS (draft fix) | pagehide now clears the draft as well as codes, log and blobs. Gate case red only on its own blob accounting. |
| R2-09 Kill switch | PASS (narrow) | Double Escape ends the session; wipe enabled before connect; revoke after DOM clear; `location.replace('about:blank')`. Gate case SKIP on the missing dialog handler, not on the artifact. |
| R2-10 Rotate | PASS | `gate.py rotate` PASS. Fresh DH rekey, both chains reset, ack verified. |
| R2-11 Migrate | PASS (behavioral) | Three root causes fixed above. Both contexts reach the new SAS with the fresh keyset, confirm, unlock and exchange text. `gate.py migrate` red only because the case never confirms the new SAS. |
| R2-12 Transport default | PASS | `gate.py stun` PASS and `gate.py cover --relay-host turn:127.0.0.1:5349` PASS. Three STUN providers, no relay in the default artifact, disclosure copy, relay-only policy leaks no host or srflx. |

## Deliberate deferrals

- Header encryption stays V2.1 per blueprint 2.2.
- No DH ratchet on turn change; the symmetric chain plus Rotate covers it, marked in code as a ceiling.
- The migration `done` handshake can in theory race if one side closes the old channel before the peer's done frame lands. Not observed in six runs (both sides adopted in 4 to 5 s each time). If it shows up, delay the old channel close in `adopt` by 300 ms.
- The pending migration peer keeps its `onChannel` handler after adopt; a second channel on it is ignored rather than raised as A2. No path creates one today.

## Known limits

- The gate harness still has no JS dialog handler, so any case that clicks Wipe stops at the confirm prompt.
- The probes lane was editing `probes/gate.py` in parallel during this run; the raw output above is the exact state seen at this artifact hash. The lead's integration run is the authority.

# W18 fix lane, A8 bulk kill and gallery budget

RUN: w18-ephemeral-fix-two-20261127
ARTIFACT: 03-build/output/ephemeral-chat-v2.html
SHA-256: d4d48d3711acc8a32ba1fca97faa02e2690bc2ef6ff3487434aba36c5c618742
BYTES: 165,744
STATUS: complete. Both cards PASS. The 29 case suite is green in one run. The
transcode case runs with no per chunk throttle. About ten minutes over the
30 minute budget.

Only writes: `03-build/output/ephemeral-chat-v2.html`, `probes/gate.py`, and this
file. `wrapper/main.cjs` still names the old pin 6c8c1283 and was not touched;
the lead repins it after review. No git command was run.

## Card 1, A8 bulk transfer kill

The burst budget now takes a bulk flag. A chunk frame spends the frame budget
only when no accepted transfer is open. Text, control and unknown frames keep
the full budget, so a flood of them still trips the rule.

Artifact change:

```
countBytes(bytes.length, bytes[0] === 2 && !!incoming);

function countBytes(n, bulk) {
  const now = Date.now();
  if (!bulk) {
    frameTimes.push(now);
    frameTimes = frameTimes.filter((t) => now - t < 5000);
    if (frameTimes.length > 40) {
      endSession('anomaly', 'A8 frame rate');
      return;
    }
  }
  if (!incoming) {
    ... 2 MB/s byte rule unchanged
```

An authenticated chunk inside an accepted transfer is gated by the AEAD frame
seal, the digest check and the receiver preallocation cap. A type 2 frame with
no accepted transfer, an unknown type, or a text or control frame still counts.
The 2 MB/s byte rule is unchanged and only runs when no transfer is open.

The transcode case lost its `Blob.prototype.slice` 150 ms delay. The rung B
output, 12.3 to 14 MB, now crosses the wire at full speed.

Case, throttle removed:

```
$ python3 03-build/output/probes/gate.py transcode --app 03-build/output/ephemeral-chat-v2.html
transcode engine A in this harness: function
PASS transcode
rc=0
```

Binding revert, scratch copy with the bulk argument removed and the same case
shape, a 4 MiB bulk file, 64 chunk frames in one burst:

```
=== fixed artifact, 4 MiB
seconds      3.5
anchor_delta 1
ended        'S3 | Session ended | Everything from this session was erased.'
log_tail     '... File received and verified: bulk.bin'
=== a8 reverted artifact, 4 MiB
seconds      2.4
anchor_delta 0
ended        'S4 | Session killed | A protocol anomaly was detected (A8 frame rate). Everything was erased.'
```

The ended text node exists at every screen; the screen field is the signal. The
reverted copy ends on S4 with the A8 frame rate detail and no Save anchor.

Flood resistance stays:

```
$ python3 03-build/output/probes/gate.py budget --app 03-build/output/ephemeral-chat-v2.html
PASS budget
rc=0
```

`budget` still kills 45 sealed text frames in one burst and still names A8. It
also still pins `frameTimes.length > 40` and the 2 MB byte rule.

## Card 2, gallery budget

Delete now decrements the retained counters, and a file start at the cap
evicts the oldest retained media first, then proceeds.

Artifact change:

```
    if (receivedFiles >= MAX_FILES) evict(1);
...
  function evict(need) {
    const keep = MAX_FILES - (need || 0);
    while (receivedFiles > keep || receivedBytes > MAX_SESSION_BYTES) {
...
    const j = retained.indexOf(item);
    if (j >= 0) {
      retained.splice(j, 1);
      receivedFiles--;
      receivedBytes -= item.size || 0;
    }
```

The gallery case pins the three sites statically and now pins the budget
behaviorally: four files fill the cap, a delete frees a slot, a fifth file is
accepted, and a sixth at the cap evicts the oldest and names the drop.

```
$ python3 03-build/output/probes/gate.py gallery --app 03-build/output/ephemeral-chat-v2.html
PASS gallery
rc=0
```

Binding revert, scratch copy with the evict at cap and the delete decrement
removed, five pasted images:

```
=== fixed artifact, five images
after cap1: received=True refused=False evicted=False
after cap2: received=True refused=False evicted=False
after cap3: received=True refused=False evicted=False
after cap4: received=True refused=False evicted=False
after cap5: received=True refused=False evicted=True
tiles       ['cap2.webp', 'cap3.webp', 'cap4.webp', 'cap5.webp']
note        '4 of 5 files retained. Older files were dropped.'
=== gallery reverted artifact, five images
after cap1: received=True refused=False evicted=False
after cap4: received=True refused=False evicted=False
after cap5: received=False refused=True evicted=False
tiles       ['cap1.webp', 'cap2.webp', 'cap3.webp', 'cap4.webp']
note        ''
log_tail    '... A file was refused (session file budget).'
```

The reverted copy never reaches the eviction path, exactly the W17 finding. The
fixed copy evicts on the fifth start and keeps four tiles.

## Harness changes, three

- transcode: the throttle is gone. The case waits for HAVE_METADATA instead of
  taking one snapshot, because the blob src attaches before metadata loads. The
  old failure message called `v.get()` with no key and raised TypeError on the
  error path; it now prints the node.
- gallery: static pins retargeted to the new evict condition, plus the
  behavioral cap block above.
- nav: a pre-existing race, not caused by these cards. The strip is shown
  immediately before the M1 send and hidden on adopt, so a 0.1 s poll can miss
  it. Proven on a scratch copy with both cards reverted, rc=2,
  `SKIP nav could not run: wait timed out: migration strip (False)`. Fixed by
  recording the lock state in a MutationObserver on the strip itself, so the
  assertion reads the state at the strip's own mutation. Two standalone runs
  green, suite run green.

## Suite, 29 cases, one run each

Artifact hash `d4d48d37...`, 165744 bytes. Raw log `evidence/W18-suite-raw.log`.

| # | Card | Case | Exit | Raw last line | Evidence |
|---|---|---|---|---|---|
| 1 | R2-01 | selftest | 0 | `PASS selftest` | `selftest-20261127-095239.json` |
| 2 | R2-02 | envelope | 0 | `PASS envelope` | `envelope-20261127-095243.json` |
| 3 | R2-03 | ratchet | 0 | `PASS ratchet` | `ratchet-20261127-095253.json` |
| 4 | R2-04 | sas | 0 | `PASS sas` | `sas-20261127-095304.json` |
| 5 | R2-05 | file | 0 | `PASS file` | `file-20261127-095313.json` |
| 6 | R2-06 | budget | 0 | `PASS budget` | `budget-20261127-095325.json` |
| 7 | R2-07 | code | 0 | `PASS code` | `code-20261127-095334.json` |
| 8 | R2-08 | lifecycle | 0 | `PASS lifecycle` | `lifecycle-20261127-095348.json` |
| 9 | R2-09 | kill | 0 | `PASS kill` | `kill-20261127-095405.json` |
| 10 | R2-10 | rotate | 0 | `PASS rotate` | `rotate-20261127-095419.json` |
| 11 | R2-11 | migrate | 0 | `PASS migrate` | `migrate-20261127-095431.json` |
| 12 | R2-12 | stun | 0 | `PASS stun` | `stun-20261127-095449.json` |
| 13 | R2-13 | cover | 0 | `PASS cover` | `cover-20261127-095455.json` |
| 14 | R2-15 | mutation-all | 0 | `PASS mutation-all` | `mutation-all-20261127-095501.json` |
| 15 | R2-16 | media-order | 0 | `PASS media-order` | `media-order-20261127-095654.json` |
| 16 | R2-17 | exif | 0 | `PASS exif` | `exif-20261127-095703.json` |
| 17 | R2-19 | bitrate | 0 | `PASS bitrate` | `bitrate-20261127-095711.json` |
| 18 | R2-20 | playback | 0 | `PASS playback` | `playback-20261127-095711.json` |
| 19 | R2-21 | imagecap | 0 | `PASS imagecap` | `imagecap-20261127-095724.json` |
| 20 | R2-22 | paste | 0 | `PASS paste` | `paste-20261127-095733.json` |
| 21 | UX-06 | panic | 0 | `PASS panic` | `panic-20261127-095740.json` |
| 22 | UX-02 | react | 0 | `PASS react` | `react-20261127-095749.json` |
| 23 | UX-01 | mid | 0 | `PASS mid` | `mid-20261127-095806.json` |
| 24 | UX-03 | nav | 0 | `PASS nav` | `nav-20261127-095816.json` |
| 25 | UX-07 | gallery | 0 | `PASS gallery` | `gallery-20261127-095830.json` |
| 26 | UX-05 | pair | 0 | `PASS pair` | `pair-20261127-095841.json` |
| 27 | UX-04 | sas-ui | 0 | `PASS sas-ui` | `sas-ui-20261127-095857.json` |
| 28 | UX-08 | a11y | 0 | `PASS a11y` | `a11y-20261127-095913.json` |
| 29 | R2-18 | transcode | 0 | `PASS transcode` | `transcode-20261127-095922.json` |

`cover` ran with `--relay-host turn:127.0.0.1:5349`, as in W17.

## Byte scan, W18

```
$ python3 - <<'EOF'
import hashlib
for p in ('03-build/output/ephemeral-chat-v2.html', '03-build/output/probes/gate.py'):
    b = open(p, 'rb').read(); t = b.decode()
    print(p, 'bytes=%d' % len(b), 'sha256=%s' % hashlib.sha256(b).hexdigest(),
          'nonascii=%d' % sum(1 for x in b if x > 127),
          'emdash=%d' % t.count('\u2014'), 'endash=%d' % t.count('\u2013'))
EOF

ephemeral-chat-v2.html bytes=165744 sha256=d4d48d3711acc8a32ba1fca97faa02e2690bc2ef6ff3487434aba36c5c618742 nonascii=0 emdash=0 endash=0
probes/gate.py bytes=155841 sha256=0937ee7fe7fd88c928fc3aded66b3cd4312aaa3a4446b36b1eda1ab5fc75111a nonascii=0 emdash=0 endash=0
```

This file scans clean by the same script: 0 non-ASCII bytes, 0 em or en dashes.

## Limits recorded, not hidden

- The A8 exemption keys on the wire type byte and the accepted transfer flag.
  The AEAD open runs after the count, so a forged chunk frame can enter the
  exempt window, but the first failed chunk aborts the transfer and clears
  `incoming`, which restores the budget. A flood of type 2 frames with no
  accepted transfer still spends the full budget.
- The transcode case still forces engine A unavailable so rung B runs live and
  deterministic. A headed engine A run on a GPU box remains R4 work.
- The gallery note counts retained plus evicted files, so a deleted file leaves
  both counts and the "N of M" line undercounts by the number of deletes. The
  case asserts the retained set and the eviction line, not the total. UX polish,
  not a budget leak.
- nav needed a harness fix before it could pass on this box. The race is
  uncommon on a slower host and its failure mode is exit 2, never a false pass.

## W21 repair lane B, P-03 to P-11 core side

RUN: w21-ephemeral-repair-20261127, lane B.
ARTIFACT: `03-build/output/ephemeral-chat-v2.html`, sha256 `2092e0e9e8e3418ba167e22b99623094e0f5d05ea876014874be1e3c4b53b87b`, 169,810 bytes.
GATE: `03-build/output/probes/gate.py`, sha256 `203ebd4c48ed308713ace70a56f3ec307969b892fdc34f2dcdfc80a332959bc2`, 157,226 bytes.
STATUS: repaired, 29 of 29 cases green with `cover` driving the app's relay mode.

### Cards applied

- P-03. Engine A now normalises a null chunk duration to one 30 fps frame and
  calls `addVideoChunkRaw`, so the muxer never receives a non finite duration.
  The over cap retry keeps the one retry and gains a rung B fallback when that
  retry cannot use WebCodecs; a still oversize result keeps the named refusal.
- P-04. A file start records `startedAt`. The transfer timer runs every second
  and aborts an accepted transfer that has not delivered a first chunk within
  `FIRST_CHUNK_MS` (5000 ms). An overlapping file start now aborts the held
  transfer and accepts the new one, instead of aborting the new id.
- P-05. Both migration arms drop any existing `mig` before starting, count
  attempts against `MIG_MAX` (6 per session), clear `migTimer` before both
  reassignments, and close the new `pc` when the arm fails before `mig` takes
  ownership. Attempt counters reset when a pairing starts.
- P-06. The artifact reads an optional relay config from the load query:
  `relay` (required to enter relay mode), `relayUser`, `relayCred`. Relay mode
  builds ICE from that one relay and forces `iceTransportPolicy: 'relay'`.
  `assertCandidates` refuses with a named Relay unreachable error when no
  `typ relay` candidate exists, so an invite or answer is never issued on a
  direct path. No query keeps the stock three STUN build. The shipped file
  contains no relay host and no relay URL.
- P-07. When `window.shell` is present, the core listens for the preload
  `ephemeral:command` wipe message and calls `endSession`, which posts the
  panic frame on the live channel. Without the bridge the listener is not
  installed, so the file stays a plain page.
- P-10. `endSession` clears `el.digits` next to `el.log.replaceChildren()`.
- P-11. The received file warning list adds lnk, desktop, url, hta, docm, xlsm,
  reg and scf.
- The `showScreen` comment now says S0 to S4 plus the gallery and about sheets,
  matching the code.

### Gate cover, rewritten

The old case measured Chromium with a synthetic `RTCPeerConnection`; that is
not an app capability. `case_cover` now loads the artifact with
`?relay=turns:127.0.0.1:5349&relayUser=probe&relayCred=probe`, clicks create,
and asserts the app's own peer configuration has only that relay and
`iceTransportPolicy: 'relay'`. With the loopback relay unreachable, it then
requires the Relay unreachable toast, an empty invite field, and the error
status. The `--relay-host` argument is still required. `PASS cover`.

### Suite, 29 cases

Raw log `03-build/output/evidence/W21-suite-raw.log`, run as two batches in one
log (15 then 14) because the shell wrapper caps one call at 420 s. Every case
is a fresh process. 29 `=== CASE` lines, 29 `EXIT <case> 0` lines, 0 FAIL,
0 SKIP, and 29 PASS lines plus the selftest detail line. `cover` ran with
`--relay-host turns:127.0.0.1:5349`.

### Targeted probes on the real artifact

Script in scratch, not in the tree. Output:

```
PASS P-04 deadline constant
PASS P-04 first chunk branch
PASS P-04 aborts held id
PASS P-04 overlap accepts new
PASS P-05 cap and drop in startMigrate
PASS P-05 timer cleared before both arms
PASS P-05 offer pc closed on failure
PASS P-07 listener only with bridge
PASS P-10 digits cleared in endSession
PASS P-11 warning list
PASS P-03 raw null duration reproduces the old throw
PASS P-03 finite duration path completes
PASS P-11 .url shows the run-code warning
PASS P-11 .hta shows the run-code warning
PASS P-10 pre-wipe SAS digits present
PASS P-10 endSession cleared the SAS digits
PASS P-07 shell kill posted the panic frame
PASS P-07 plain browser stays a no-op
PROBES PASS
```

The muxer probe constructs a real `EncodedVideoChunk` with no duration and
shows `addVideoChunk` throws the duration TypeError, then shows the same bytes
through `addVideoChunkRaw` with a finite duration finalize cleanly. The P-07
probe pairs two pages with `window.shell` defined, posts the preload wipe
message, and observes the peer end on the panic frame; without the bridge the
same message is a no-op. P-11 sends probe.url and setup.hta through the real
file input and reads the receiver warning.

### Byte scan, W21

```
ephemeral-chat-v2.html bytes=169810 sha256=2092e0e9e8e3418ba167e22b99623094e0f5d05ea876014874be1e3c4b53b87b nonascii=0 emdash=0 endash=0
probes/gate.py bytes=157226 sha256=203ebd4c48ed308713ace70a56f3ec307969b892fdc34f2dcdfc80a332959bc2 nonascii=0 emdash=0 endash=0
```

The artifact carries 0 occurrences of the relay URL scheme literal, so the
default build statement and the stun case are unchanged.

### Limits recorded

- P-04 and P-05 runtime injection was not built. The proof is the exact code
  path pin plus the green file, migrate and panic cases; the stalled start and
  repeated offer shapes need a sealed frame the harness cannot mint today.
- Engine A was not run live on a headed 45 MiB clip. The duration throw and the
  fixed call are proven at the muxer on the real page; the transcode case still
  forces rung B as in W18.
- The transcode clip generator is size sensitive. One exploratory run produced
  46,246,112 bytes against its 47,185,920 byte threshold and exited 1 before
  the app path was reached. The logged run and a standalone rerun both passed.
- P-07 was proven with a stand-in `window.shell` object, not the Electron
  preload. The message contract and the panic frame are the same; the live
  shell run belongs to lane C.
