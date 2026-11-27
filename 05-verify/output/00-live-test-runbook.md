# 00 Live peer test runbook, two people, two Chromium desktops

RUN: w26-ephemeral-verify-20261127, lane 3, runbook.
DATE WRITTEN: 2026-11-27.
OWNER GATE: the live peer test. Its result is recorded in this file with the date and a pass or fail per step. The machine gates are separate, in 05-verify/proof.md and 05-verify/output/02-release-shape-proof.md.
ARTIFACT UNDER TEST: `03-build/output/ephemeral-chat-v2.html`, sha256 `2092e0e9e8e3418ba167e22b99623094e0f5d05ea876014874be1e3c4b53b87b`, 169,810 bytes. Checked at write time.
SHAPE: the browser artifact opened as a local file in Chromium desktop on two machines. Lane 2 has landed the packaged macOS shell (`02-release-shape-proof.md`, PASS), and the same steps repeat inside the app; the shell-only limits are named in section 16.

ASCII only. No em or en dashes. Every step names what proves it and what to screenshot or note.

## 1. Roles and rules

| Role | Machine | Does |
|---|---|---|
| Owner | A | Creates the invite, drives the session, wipes at the end |
| Second person | B | Reads the safety number over voice, creates the reply, confirms, receives files |

Rules that make the result usable:

1. Both machines run the same artifact, checked by hash before the first step. A mismatch is a stop, not a note.
2. Both browsers are Chromium class. Chrome 158.0.8127.38 was the measured build in the pentest environment. Use a dedicated profile with zero extensions. An extension can read the page and is a disclosed residual; a profile with extensions makes the session result uninterpretable.
3. The safety number is compared over a channel the code does not travel over: a phone call, a video call on a different device, or in person. Reading it through the app, a chat, or the same machine defeats the check.
4. Never retype a code. Copy and paste. A retyped code that fails is a test error, not a product result.
5. Record exact text seen. Copy the sender log lines, do not paraphrase them. Screenshot every proof named below.
6. A step that fails is a result. Stop, screenshot, note the exact message and the time, and continue only if the next step still has a live session. Do not retry more than once without recording the first failure.
7. Evidence folder: `05-verify/output/evidence/live-<YYYYMMDD>/`. Name files `<step>-<machine>-<what>.png`, for example `05-B-received-card.png`. The owner creates the folder before step 1.

Time budget for the full protocol: 45 to 60 minutes, including one video transcode and one reload. The video step is the slow one.

## 2. Prerequisites

| Item | Where | Note |
|---|---|---|
| Artifact file | both machines | Copy by USB, local share or a download the owner controls. No server is required. |
| Chromium desktop | both machines | Chrome, Chromium, Edge or Brave in Chromium mode. Safari and iOS are not gates. |
| Voice channel | owner and second person | Phone or a second device. Not the app. |
| DevTools | both machines | F12 or Cmd+Option+I. Needed for the storage check in step 12. |
| `python3` with PIL | machine A | Only for the trace image. `python3 -c "import PIL"` must exit 0. |
| `ffmpeg` and `ffprobe` | machine A | Only if the 63 MB fixture is not available. |
| `tcpdump` and `tshark` | machine A, optional | Step 6 needs admin rights. If unavailable, record the step as NOT RUN with the reason. |
| 63.3 MiB video fixture | `04-pentest/evidence/pentest-environment/fixtures/over45.mp4` | 66,345,189 bytes, 1920x1080, 20 s, h264 plus aac. Copy it to A. Rebuild with the command in section 17 if absent. |
| Plain files for step 8 | machine A | `setup.lnk` and `invoice.pdf.app`, created by the command in section 10. |

## 3. Step 1, pin the artifact and open it

On each machine, in a terminal in the folder that holds the file. macOS:

```sh
shasum -a 256 ephemeral-chat-v2.html
wc -c ephemeral-chat-v2.html
```

Linux: `sha256sum ephemeral-chat-v2.html` and `wc -c ephemeral-chat-v2.html`. Windows PowerShell: `Get-FileHash ephemeral-chat-v2.html -Algorithm SHA256` and `(Get-Item ephemeral-chat-v2.html).Length`.

Expected on both: `2092e0e9e8e3418ba167e22b99623094e0f5d05ea876014874be1e3c4b53b87b` and `169810`.

Then open the file in Chromium, both machines, one window each.

Expected: the pairing screen, heading `One session. Nothing kept.`, the two panels `Start a session` and `Join a session`, and the fine print that names the peer IP in the code, the extension exposure, the STUN use and the no-storage claim. The `Wipe` button is visible even before any connection.

Proves: both people test the same bytes, and the disclosure copy is present before pairing starts.

Record: screenshot of the heading plus the `Wipe` button on each machine, and the two command outputs. Note the browser version on each machine (`chrome://version`).

## 4. Step 2, pair and compare the safety number

Order matters. A is the offerer, B is the answerer.

1. A clicks `Create invite`. The invite code appears in the `Invite code` box. The line under it shows the time left, starting near 120 seconds.
2. A notes the character count of the invite code, without copying the code into the notes. This is the residual 24 measurement: the QR ceiling was set from an inferred envelope length, and this is the real length.
3. A sends the code to B over a channel that reaches only B: a direct message to the one person, a local share, or in person. The code channel is not trusted; the safety number comparison in the next step is the authentication. Do not put the code in a group chat or a synced note, because it is a bearer token until it expires.
4. B pastes the invite into `Join a session` and clicks `Create reply`. The reply code appears in `Your reply`. B sends it back to A.
5. A pastes the reply into `Their reply` and clicks `Connect`.
6. Both screens move to the chat view and show `Safety number` with 60 digits in 12 groups of 5, plus a suite label next to it.
7. Both people read the digits aloud in groups over the voice channel. Compare all 60 digits. A mismatch is a FAIL and a product event; click `It does not match` and record the ended panel text.

Expected: both numbers are identical, the suite label is identical, and the message box plus the `Send` and `+` controls are disabled until both people confirm.

Proves: the invite and reply envelope works over the zero-infrastructure path, the safety number is bound to the session keys and identical on both sides, the code TTL is visible and counted down, and content is gated on the human check.

Record: screenshot of both safety number panels, side by side if possible. Note the invite code character count, the observed TTL countdown, the elapsed time from `Create invite` to `Connect`, and both suite labels. If the code expires during the handoff, note the elapsed time: that is the owner decision on the 120 second TTL.

## 5. Step 3, confirm and prove the gate

Both people click `It matches`. Expected, in this order: a system line `Safety number confirmed on both sides. Content is unlocked.`, the verification chip reads `verified`, and the composer becomes usable on both sides.

Negative check, do this before confirming on one side: try to type in the message box and click `Send`. Both are disabled, so no message is sent and nothing appears in the log. This proves the gate is not cosmetic.

Proves: the pre-confirm router drops content frames, and the composer unlocks only after both local and peer confirmation.

Record: screenshot before the click (locked composer with the toast if captured), screenshot after (system line and `verified`), and the exact chip text on both.

## 6. Step 4, text both ways

Send a unique marker from A to B, then a second unique marker from B to A:

```
EPHEMERAL_W26_A2B_20261127
EPHEMERAL_W26_B2A_20261127
```

Expected: one bubble on each side per message, in order, no duplicate, no console error. The log is the only place the text exists.

Proves: the `msg` frame path works in both directions through the ratchet and AEAD, and the marker is available for the wire check in step 6.

Record: screenshot of both logs with the markers, and the send and receive times.

## 7. Step 5, image send with the trace check

Build a trace image on A. The control markers are in the file before sending. The canvas re-encode must drop all of them.

```sh
cd <evidence folder>
python3 - <<'PY'
from PIL import Image, PngImagePlugin
im = Image.new('RGB', (1600, 1200), (40, 90, 160))
meta = PngImagePlugin.PngInfo()
meta.add_text('Exif', 'SECRETGPS LEAKMODEL GPS')
meta.add_text('Comment', 'EPHEMERAL_TRACE_W26')
im.save('trace.png', pnginfo=meta)
PY
python3 -c "d=open('trace.png','rb').read(); print('control', b'SECRETGPS' in d, b'LEAKMODEL' in d, b'EPHEMERAL_TRACE_W26' in d)"
```

Expected control output: `control True True True`.

1. A clicks `+`, selects `trace.png`. The image is re-encoded and sent immediately, with no draft and no Send button. The sender card should show the re-encoded name `trace.webp` and the size.
2. B receives a file card, state `verified`, with an image preview and a `Save` anchor.
3. B clicks `Save` and saves to the evidence folder. Do not open the file.
4. Check the saved bytes on B:

```sh
ls -l trace.webp
file trace.webp
python3 -c "d=open('trace.webp','rb').read(); print(d[:4], [m in d for m in (b'Exif', b'SECRETGPS', b'LEAKMODEL', b'EPHEMERAL_TRACE_W26')])"
```

Expected: a WebP file, first bytes `b'RIFF'`, and `[False, False, False, False]`. On macOS or Linux, `file trace.webp` also prints a WebP description; on Windows use the Python line alone. A `.png` name, a JPEG, or any True marker is a FAIL of the metadata strip.

Proves: the single `acceptFile` path re-encodes every image through a canvas, the EXIF and text markers do not survive, the digest and completeness gate run before the Save anchor appears, and the saved file is the verified plaintext span only.

Record: screenshot of the sender card and the receiver card, the three command outputs, the saved file path, and the exact file size in bytes.

## 8. Step 6, wire trace, no plaintext and no HTTPS

This is the blueprint R4 packet check. Run it while repeating one text marker and one small file. It needs admin rights.

```sh
IF=$(route -n get default | awk '/interface:/{print $2}')
# Linux: IF=$(ip route get 1.1.1.1 | awk '{print $5; exit}')
sudo tcpdump -i "$IF" -n -s 0 -w live-w26.pcap 'udp or tcp'
# during the capture: send EPHEMERAL_W26_WIRE_20261127 as text, then send a small file
# containing the same marker in its bytes, then stop the capture with Ctrl+C
tshark -r live-w26.pcap -Y 'frame contains "EPHEMERAL_W26"' | wc -l
tshark -r live-w26.pcap -Y 'tcp.port == 443' | wc -l
tshark -r live-w26.pcap -Y 'dns' -T fields -e dns.qry.name | sort -u
```

Expected: `0` for the marker count, `0` for TCP 443, and only the configured STUN hostnames in the DNS list. The address table should contain only the two peer addresses and the STUN endpoints; any other host is a FAIL. The peer address is expected in default mode and is a stated residual.

Proves: no plaintext marker crosses the wire, there is no HTTPS or third-party call, and the default path uses only the configured STUN providers.

Record: the pcap path, all three outputs, the interface name, and the capture start and stop times. If `tshark` is absent, note NOT RUN and the reason; do not substitute a claim.

## 9. Step 7, video over the 45 MB path

Fixture: `over45.mp4`, 66,345,189 bytes, 1920x1080, 20 s. It is over the 45 MiB cap (47,185,920 bytes) by about 19 MB, so it must be transcoded before it can be sent.

1. A clicks `+`, selects `over45.mp4`. Expected draft card: `Will be re-encoded to 1080p, about ... MB, and about ... seconds of processing.` with a `Send video` button. Record the exact projected size and seconds. The Send control must not start a transfer before the projection is shown.
2. A clicks `Send video`. Progress shows `encoding N%`.
3. Record the exact sender system lines. Expected on this build: `sending X MB (webcodecs)`. Engine A was fixed and verified headed on Chrome 158 (`03-environment-matrix.md` section 8.3). A line reading `WebCodecs could not encode this clip (...). Falling back to MediaRecorder.` is a regression against that fix: record it and continue if the transfer completes. The 45 MB path can still PASS on the transfer and digest, but the engine line is a separate fail against F-ENV-1.
4. B receives the card. Expected: state `verified`, size under 47,185,920 bytes, a `Save` anchor, and a playable preview. Play it: 1920x1080, duration about 20 seconds, `readyState` reaches 4, current time advances.
5. If the first encode is over the cap, expect `The first encode reached X MB, over the 45 MB cap. Retrying once at a lower bitrate.` and then either a verified result under the cap or the named refusal `the result is still X MB after one retry, so it was not sent`. A silent stop or a Save anchor over the cap is a FAIL.

Proves: the projected size is shown before commit, the over-cap transcode path runs, the bulk chunk traffic survives the A8 frame guard while a transfer is active, the digest verifies, playback is from memory, and the cap is enforced after one retry.

Record: screenshot of the draft projection, screenshot of every sender system line, the receiver card with its size and `verified` state, the video metadata screenshot, and the elapsed encoding and transfer times.

## 10. Step 8, dangerous extension warning

Create two harmless files with dangerous names on A:

```sh
printf 'W26 harmless test payload, do not open\n' > setup.lnk
printf 'W26 harmless test payload, do not open\n' > invoice.pdf.app
```

Send both, one at a time. On B, each card must show the banner `This type can run code when opened. Only save it if you trust the sender.` The `Save` anchor is still present after verification, because the final click is the user's. Do not open either file.

Proves: the dangerous type list covers shortcut and desktop entries and the app bundle suffix, the warning is driven by the displayed name and the real type, and the warning does not block a deliberate save.

Record: screenshot of each card with the banner and the file name, and note the type row shown on the card. A missing banner on either name is a FAIL.

## 11. Step 9, fresh keyset, Rotate then New session

This step covers both key-changing actions. `Rotate keys` changes the keys inside the live channel and keeps the identity. `New session` changes the identity and the codes. Run both, in that order.

1. With the session live and no transfer running, A clicks `Rotate keys`.
2. Expected lines: on A, `Rotating session keys under a fresh DH output.` then `Key rotation acknowledged and verified. Both chains were reset.` On B, `Peer rotated the session keys.` On A the ratchet chip reads `rotated 0 min ago`. The safety number stays the same, because the identity did not change, and text still flows after the rotation.
3. A clicks `New session`.
4. Both sides show the strip `Preparing a new session, step N of 4.` The log is locked and the composer and attach controls are disabled.
5. Within 15 seconds both sides reach a new `Safety number` panel with the line `New identity. Compare the new safety number.`
6. Compare the new 60 digits over voice again. They must differ from the step 2 number and match between A and B. Confirm on both.
7. Expected: the old log is cleared, the new session is live, and the old invite and reply codes point at a closed peer. B's old chat content is gone.

Proves: Rotate resets the root and both chains under a fresh DH output with a verified MAC and leaves the safety number unchanged, and Migrate completes M1 to M5 with a new DTLS certificate and new ephemeral and static keys, a different safety number, a closed old channel and old codes that cannot reach a live peer.

Record: screenshots of the old and new safety numbers side by side, the rotation system lines, the strip text, the elapsed time from click to new number, and the system lines. Note any `The migration attempt limit for this session was reached` or timeout text.

Negative check, optional: start a 45 MB send and click `New session` during it. Expected toast `Finish the transfer first` and no migration. Record it if run.

## 12. Step 10, wipe

1. On A, click `Wipe`. A native confirm dialog reads `End this session and wipe everything from memory? The other person will be disconnected.` Accept it.
2. Expected on A, in order: the composer disappears, the ended panel reads `Session wiped` and `Everything was erased.`, and the page navigates to `about:blank` about 4 seconds later.
3. Expected on B, in order: the ended panel reads `Session ended` and `The other person left. Everything was erased.`, then `about:blank` about 4 seconds later.
4. Optional check before starting: on the pairing screen with no session, the `Wipe` button wipes with no confirm dialog, because there is nothing to lose. Note whether that matches the owner's expectation.

Proves: the panic frame is best effort, the local wipe runs first and does not wait for the network, the peer wipes on loss, and the page leaves the document.

Record: screenshots of both ended panels, the confirm dialog text if captured, the timestamps of the click, the panel and the blank page on both machines.

## 13. Step 11, kill switch

Repeat a short pairing and confirm the safety number, or use a fresh session after step 10.

1. Put the cursor inside the message box and press Escape twice within 800 milliseconds. Expected: the same ended panel and `about:blank` after about 4 seconds. A single Escape must do nothing.
2. Optional, the harder case: start the 45 MB transfer and press the double Escape on A while it runs. Expected: the transfer aborts, B gets no `Save` anchor, the session ends and both pages go blank. Record B's card state and the absence of the anchor.
3. Optional, shell shape only: if the packaged app is being tested, use the shell wipe menu item and confirm the renderer wipes before the process is destroyed. That row belongs to the release shape proof, not to this browser run.

Proves: the kill path works from inside a textarea, does not depend on the button, and a kill during a transfer does not leave a savable partial file.

Record: screenshots and timestamps on both machines, and the exact ended text.

## 14. Step 12, reload proving zero storage

Pair a fresh session and confirm the safety number. Open DevTools Console on both machines and run this before the reload:

```js
[Object.keys(localStorage).length,
 Object.keys(sessionStorage).length,
 document.cookie,
 (await indexedDB.databases()).length,
 (await caches.keys()).length]
```

Expected: `[0, 0, "", 0, 0]`. Then reload A with Cmd+R on macOS, or Ctrl+R or F5 on Windows and Linux. Expected: the pairing screen, no transcript, no code, no session. Run the same line again; expected `[0, 0, "", 0, 0]`. B sees the peer leave and wipes, which is the expected peer-loss behavior, not a failure.

Also open DevTools, Application, Storage and screenshot the tree: Local Storage, Session Storage, IndexedDB, Cookies, Cache Storage must all show zero entries. The Application panel must be opened after the reload for the screenshot; the console line is the primary proof because it reads the live page.

Proves: no persistence API is used at any point, a reload loses the session, and there is no recoverable transcript in page storage.

Record: console output before and after the reload, the Application screenshot, and B's ended panel.

## 15. Result table, owner fills this in

Date: ____________  Artifact sha: `2092e0e9e8e3418ba167e22b99623094e0f5d05ea876014874be1e3c4b53b87b`

| Step | What it proves | A observed | B observed | Verdict | Evidence |
|---|---|---|---|---|---|
| 1 Pin and open | same bytes, disclosure present | | | PASS / FAIL | |
| 2 Pair and SAS | envelope, TTL, identical 60 digits | | | PASS / FAIL | |
| 3 Confirm | content gate | | | PASS / FAIL | |
| 4 Text both ways | msg path, AEAD | | | PASS / FAIL | |
| 5 Image trace | re-encode strips markers, Save gated | | | PASS / FAIL | |
| 6 Wire trace | no plaintext, no HTTPS, STUN only | | | PASS / FAIL / NOT RUN | |
| 7 Video over 45 MB | projection, transcode, cap, playback | | | PASS / FAIL | |
| 8 Dangerous extension | warning on lnk and app | | | PASS / FAIL | |
| 9 Rotate then New session | rekey keeps SAS, new session changes it, old channel closed | | | PASS / FAIL | |
| 10 Wipe | local wipe, peer loss, about:blank | | | PASS / FAIL | |
| 11 Kill switch | double Escape, transfer kill | | | PASS / FAIL | |
| 12 Reload | zero storage, no transcript | | | PASS / FAIL | |

Overall: PASS / FAIL. Owner signature and date: ____________________.

## 16. What this run does not prove

1. It does not prove the packaged or fused shell in this session. The `@electron/fuses` read, the code signature and the `app://` core load are proved in 05-verify/output/02-release-shape-proof.md. If the run uses the browser artifact, those rows are NOT RUN for this session.
2. It does not prove the absence of OS traces: swap, hibernation, crash dumps, screenshots and clipboard history stay outside the page. Blueprint rows 5, 7 and 8 carry them.
3. It does not prove an anonymity property. Default mode exposes the peer address and is classifiable as WebRTC. Cover mode, when configured, narrows that and does not remove the relay as a metadata holder.
4. The engine used is whatever the build reports in the sender log. Engine A was verified headed on Chrome 158 in `03-environment-matrix.md` section 8, and a fallback line in this run would be a regression, not a silent pass.
5. A user who clicks `It matches` without comparing digits gets no protection. That is blueprint row 1 and no test can close it.
6. A single run on one network is one sample. The packet result is not a general network claim.

## 17. Appendix, fixture and helper commands

Rebuild the over-cap video if the fixture is absent:

```sh
ffmpeg -y -f lavfi -i testsrc2=size=1920x1080:rate=30:duration=20 \
  -f lavfi -i sine=frequency=440:duration=20 \
  -c:v libx264 -preset veryfast -b:v 26M -maxrate 26M -bufsize 52M \
  -c:a aac -b:a 128k -movflags +faststart over45.mp4
wc -c over45.mp4
ffprobe -v error -show_entries format=duration,size -show_entries stream=width,height -of default=noprint_wrappers=1 over45.mp4
```

Requirement: the file is larger than 47,185,920 bytes and decodes as 1920x1080, about 20 seconds. The size does not need to match the measured 66,345,189 bytes; the encoder version changes it.

Trace image control and result checks are in step 5. Storage one-liner is in step 12. Capture commands are in step 6.

## 18. Self-check for this file

Commands run after the last edit, output quoted in the lane report:

```
python3 -c "d=open('05-verify/output/00-live-test-runbook.md','rb').read(); print('bytes', len(d)); print('em', d.count(b'\xe2\x80\x94'), 'en', d.count(b'\xe2\x80\x93'), 'nonascii', sum(1 for b in d if b > 127))"
grep -c '^## ' 05-verify/output/00-live-test-runbook.md
grep -c '^| [0-9].*PASS / FAIL' 05-verify/output/00-live-test-runbook.md
```

Expected: zero em, zero en, zero non-ASCII bytes, 18 section headings including this one, and 12 result rows carrying a PASS / FAIL cell. The exact counts are recorded in the lane report, not asserted here from memory.

STATUS: complete. The protocol is written. The live result is the owner's to fill in; this file does not claim any step passed.
