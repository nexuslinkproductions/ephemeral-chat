# 01 Trust Map: Ephemeral Chat V1

Run: `w1-ephemeral-hardening-20261126`, lane 1 of 7.
Source: `input/ephemeral-chat-v1.html`, 1154 lines, 35,598 bytes, sha256 `23be3a0b6f53587e50c97c1767fa745980788288145dc79d3dba42095b150337`.
Scope: static trust map of the shipped V1. No live run in this lane, so unmeasured runtime claims are labelled UNVERIFIED. Defect severity and remediation belong to the audit and design lanes.

Evidence key: `file:line` means a line in `input/ephemeral-chat-v1.html`. "sheet" means page 1 of `input/ephemeral-chat-overview.pdf`. External platform claims carry a source URL that was fetched and title-checked for this file.

## INVENTORY

| Block | Lines | Purpose |
|---|---|---|
| Document head, CSP, cache and referrer meta | 1-9 | Charset, viewport, CSP, no-referrer, cache hint, title. |
| Stylesheet | 10-348 | All layout, bubbles, file cards, drag overlay, ended screen, responsive rules. |
| Header bar | 351-355 | Brand, status pill, Wipe button. |
| Pairing screen | 357-395 | Two panels, create and join flows, four code textareas, copy buttons. |
| Chat log | 397-401 | Transcript container with `role=log`, `aria-live`, empty state. |
| Ended screen | 403-410 | Post-wipe notice and restart button. |
| Composer | 413-418 | Attach button, hidden file input, message textarea, Send button. |
| Toast | 420 | Transient status message. |
| Script bootstrap and constants | 422-445 | Strict IIFE, `$` helper, size and text limits, idle parsing, STUN list. |
| Element cache | 447-473 | Maps DOM ids to `el.*` references. |
| Mutable session state | 475-486 | Peer, channel, flags, incoming file, send queue, timers, activity, object URL list. |
| `uid` | 488-490 | Random file id with a timestamp fallback. |
| `setStatus`, `toast` | 492-503 | Header status text and transient toast. |
| `formatSize`, `scrollDown`, `atBottom` | 505-517 | Byte formatting and scroll position helpers. |
| `addSystem`, `addMessage` | 519-539 | Safe DOM text writers for system lines and chat lines. |
| `closePeer` | 541-552 | Clears disconnect timer, closes channel and peer, drops references. |
| `endSession` | 554-605 | One-shot wipe, UI teardown, reason text, optional close attempt. |
| `checkIdle`, `bump` | 607-623 | Idle deadline check and throttled activity recording. |
| `fail` | 625-631 | Closes peer, sets error status, toasts the error. |
| `newPeer` | 633-658 | Creates the RTCPeerConnection, wires state changes and inbound channels. |
| `bindChannel` | 660-685 | Wires one data channel, enables the composer on open, ends session on close. |
| `iceDone` | 687-704 | Waits for ICE gathering complete with a 4.5 s cap and 150 ms settle. |
| `toBase64`, `fromBase64` | 706-720 | Byte to base64 and back, whitespace tolerant on decode. |
| `pack`, `unpack` | 722-746 | SDP to `GZ1` or `RAW1` code and back. |
| `createInvite` | 748-775 | Host flow: offer, ICE gather, pack, display invite code. |
| `joinSession` | 777-805 | Joiner flow: unpack invite, answer, pack reply code. |
| `acceptAnswer` | 807-822 | Host flow: unpack reply, set remote answer. |
| `onMessage` | 824-839 | Routes text control frames and binary chunks. |
| `sendText` | 841-854 | Enter and Send path: trim, cap, send, local echo. |
| `drain` | 856-870 | Send buffer backpressure wait with a 10 s cap. |
| `queueFiles` | 872-881 | Serializes file sends and catches per-file errors. |
| `sendFile` | 883-926 | Validates, previews, sends file-start, chunks, file-end. |
| `createFileCard` | 928-996 | Builds the file card DOM and exposes progress, done, error. |
| `beginIncoming` | 998-1017 | Validates file-start, allocates the buffer, creates the card. |
| `addChunk` | 1019-1036 | Copies binary chunks into the preallocated buffer. |
| `endIncoming` | 1038-1053 | Builds Blob and object URL, shows preview and Save, checks length. |
| `autoSize` | 1055-1058 | Grows the message box up to 120 px. |
| `copyText` | 1060-1074 | Clipboard write with a manual-select fallback. |
| `wipe` | 1076-1080 | Confirms and ends the session. |
| Primary event wiring | 1082-1090 | Create, join, connect, copy, send, wipe, restart, attach. |
| Input and file listeners | 1092-1104 | Auto-size, Enter to send, file picker change. |
| Code textarea focus | 1106-1108 | Select all on focus. |
| Drag and drop | 1110-1122 | Document-level drop to send, drag overlay state. |
| Paste | 1124-1131 | Clipboard files to send. |
| Activity and idle wiring | 1133-1139 | Passive activity bump, interval, visibility check. |
| Page lifecycle | 1141-1150 | `pagehide` cleanup, `pageshow` reload or idle check. |
| Script close | 1151-1152 | Ends the IIFE and the inline script. |

## SESSION LIFECYCLE

Two roles, no room, no directory. The host creates an invite, the joiner creates a reply, the host accepts the reply. Everything is one `RTCPeerConnection` and one data channel.

### What each code contains

Both codes are the complete SDP string, compressed or raw, then base64 encoded, with a `GZ1.` or `RAW1.` prefix. `pack` encodes `pc.localDescription.sdp` (722-730). The app never parses or rewrites the SDP. It only wraps it.

- Invite code: `GZ1.` plus base64 of gzip of the host offer SDP, built at 761. If `CompressionStream` is missing, `RAW1.` plus base64 of the raw SDP bytes, built at 729.
- Reply code: the same format over the joiner answer SDP, built at 792.
- The SDP itself carries the fields the browser generated: ICE ufrag and password, ICE candidates, the `a=fingerprint` hash of the DTLS certificate, the DTLS setup role, the `m=application ... UDP/DTLS/SCTP webrtc-datachannel` line, and the SCTP port. The app adds no session id, no room id, no expiry, no MAC, no checksum, no version negotiation beyond `GZ1` and `RAW1` (734-745).
- The fingerprint is the only cryptographic identity material in the code. It is a public hash, not a key. There is no shared secret and no password in either code.

The app source contains no `fingerprint` string, and no SDP parser. The attribute exists only inside the opaque `pc.localDescription.sdp` that `pack` compresses. Its presence is a property of the browser's SDP, not of app code.

The code format is checked only for a prefix and base64 validity. `unpack` splits at the first dot (734), requires at least one character before it (735), strips whitespace from the body (716), inflates `GZ1` (738-743), decodes `RAW1` (744), and rejects anything else (745). There is no length cap before base64 decode, so a pasted multi-megabyte string is decoded in memory.

### Pairing mechanics and who validates what

Host, `createInvite` (748-775):

1. `closePeer()` first, so any prior peer is discarded (751).
2. `pc = newPeer()` (754), which builds an `RTCPeerConnection` with the two Google STUN servers (634, 442-445).
3. `bindChannel(pc.createDataChannel('chat', { ordered: true }))` (755). One reliable ordered channel, no `maxRetransmits`, no `maxPacketLifeTime`.
4. `createOffer`, `setLocalDescription` (756-757), then `iceDone(pc)` (758), which waits for gathering complete or 4500 ms plus 150 ms (687-704).
5. `pack(pc.localDescription.sdp)` (761), display in `#offer` (763), enable Copy and Connect (764-765).

Joiner, `joinSession` (777-805):

1. `unpack(el.offerIn.value)` (783).
2. `pc = newPeer()` (785), `setRemoteDescription({ type: 'offer', sdp })` (786).
3. `createAnswer`, `setLocalDescription` (788-789), `iceDone` (790), `pack` (792), display in `#answer` (794), enable Copy (795).

Host, `acceptAnswer` (807-822):

1. Require `pc` (811, checked again at 814).
2. `unpack(el.answerIn.value)` (812).
3. `setRemoteDescription({ type: 'answer', sdp })` (815).
4. Status becomes connecting (816), then ICE checks, DTLS handshake, SCTP association, and the channel open event.

Who validates what:

| Check | Where | What it proves |
|---|---|---|
| Code prefix and base64 | App, `unpack` 734-745 | The string is one of the two formats and decodes. Nothing about the sender. |
| SDP grammar and state | Browser, `setRemoteDescription` 786, 815 | The SDP is syntactically usable as an offer or answer for this peer. |
| ICE credentials and candidates | Browser, ICE stack | The answer matches the offer's ufrag and pwd, and a path exists. |
| DTLS certificate hash | Browser, DTLS stack, against `a=fingerprint` in the remote SDP | The peer holds the private key for the certificate named in the code it sent. This authenticates the code channel, not the human. |
| That the peer is the intended person | Nothing | No fingerprint display, no SAS, no identity binding. |
| That the code has not been used before | Nothing | No nonce, no one-time flag, no replay cache. |
| That the code belongs to this session | Nothing | No session id. A code is valid for any `RTCPeerConnection` that can consume it. |

The binding chain is therefore: code channel authenticates the fingerprint, fingerprint authenticates the DTLS certificate, DTLS encrypts the channel. RFC 5763 describes the mechanism as a fingerprint in SDP that identifies the key presented during the DTLS handshake (https://www.rfc-editor.org/rfc/rfc5763, abstract). RFC 8827 states that the fingerprint attribute binds the communication to a key pair and that this level of security comes from having the fingerprint in a message received securely (https://www.rfc-editor.org/rfc/rfc8827, section 4.1). The app never shows the fingerprint or a derived short code, so the human cannot perform the comparison RFC 8827 calls for as an out-of-band verification mechanism (same RFC, section 6, security characteristics, which requires a certificate fingerprint or SAS for out-of-band verification). Whoever supplies a valid code is the peer.

### Failure paths

- Missing or malformed code: no dot, dot at position 0, or bad base64. `unpack` throws "That code is not valid" (735) or the browser throws on base64. `fail` closes the peer, sets status error, and toasts for five seconds (625-631). The pairing UI stays usable, so the user can retry.
- Unknown prefix: "Unknown code format" (745). Same `fail` path.
- `GZ1` on a browser without `DecompressionStream`: "This browser cannot read that code" (739). Same path. There is no automatic retry as `RAW1`.
- Corrupt gzip: `DecompressionStream` rejects, `fail` runs.
- SDP rejected: wrong type, malformed m-line, missing ICE credentials, or an answer that does not match the offer. `setRemoteDescription` rejects, `fail` runs.
- Wrong code pasted into the wrong box: the app forces `type: 'offer'` at 786 and `type: 'answer'` at 815. A reply pasted as an invite usually fails SDP validation or ICE matching. There is no friendly role check.
- ICE gathering stalls: after 4500 ms the code is packed with whatever candidates exist (687-704). Host candidates may still connect on a LAN. On the public internet a code with no server-reflexive candidate usually fails later.
- Connection fails before open: `connectionState` becomes `failed` while `connected` is false. The handler sets status "connection failed" and toasts a retry suggestion (648-651). It does not close `pc` and does not wipe. A later Create invite calls `closePeer` (751), so the stale peer is discarded then.
- Connected then disconnected: a five second grace timer starts (638-644). If the state is still `disconnected` or `failed` at expiry, `endSession('peer')` runs (642). A recovery to `connected` clears the timer (653).
- Connected then `failed` or `closed`: immediate `endSession('peer')` (645-647).
- Data channel closes: immediate `endSession('peer')` if `connected` (681-683).
- Channel never opens but ICE succeeds: there is no open timeout. The UI stays at "connecting..." (816) until the idle wipe or the user closes the tab. This is a real hang path.
- Second Connect click before open: `#connect` is disabled only for the duration of the call (809, 820). A second click with a different answer can reject and run `fail`, which calls `closePeer` and drops the pending peer. The user must start over with Create invite.
- `endSession` during an async step: each stage rechecks `sessionEnded` after awaits (759, 762, 784, 787, 791, 793, 813). An in-flight invite or join stops before writing codes back to the DOM.
- Peer opens a second data channel: `newPeer` binds every inbound channel (656), and `bindChannel` overwrites `dc` without closing the previous one (661). A malicious peer can replace the channel object at any time. The old channel stays open until the peer closes it or the session ends.

## DATA FLOW

### Text message path, Enter key to peer DOM

1. Keydown listener on `#input` (1093-1098). Enter without Shift calls `preventDefault` and `sendText`. Shift+Enter is not intercepted, so it inserts a newline. The Send button calls the same function (1087).
2. `sendText` (841-854) exits if the session ended. It strips trailing whitespace with `replace(/\s+$/, '')` (843), so trailing newlines and spaces are not sent. It rejects an empty or whitespace-only message (844).
3. It requires `connected`, a non-null `dc`, and `dc.readyState === 'open'` (845-848). Otherwise it toasts "Not connected" and returns. There is no queue and no retry.
4. It sends one text frame: `JSON.stringify({ k: 'msg', text: text.slice(0, MAX_TEXT) })` (849). `MAX_TEXT` is 20000 UTF-16 code units (429). The frame has no id, sequence number, timestamp, length prefix outside JSON, or authentication tag.
5. It immediately renders the same text locally with `addMessage(..., true)` (850), then clears the input, resizes it, and refocuses (851-853). The local echo happens after `dc.send` returns, but `send` only enqueues into the SCTP buffer. A message can appear on screen and never reach the peer if the path dies immediately after.
6. On the receiver, `dc.onmessage` is `onMessage` (684). String data is parsed with `JSON.parse` inside a try/catch (826-828). Malformed JSON is dropped silently, with no system line and no counter.
7. The handler accepts only `k === 'msg'` with a string `text` (829). It slices to `MAX_TEXT` again (830) and calls `addMessage(text, false)`. Unknown keys and non-string text are ignored. There is no schema version and no forward compatibility path.
8. `addMessage` (528-539) creates a `div.msg`, a `div.bubble`, assigns `bubble.textContent = text` (534), appends, hides the empty state, and scrolls only if the user was already near the bottom (529, 538). `textContent` means no HTML parsing, no linkification, no markdown, and no script execution. Control characters, bidi overrides, zero-width characters, and very long unbroken strings pass through. CSS `white-space: pre-wrap` and `overflow-wrap: anywhere` (220-221) preserve newlines and force wrapping.
9. There is no delivery acknowledgement, read receipt, edit, delete, or resend. The sender's copy and the receiver's copy are independent DOM nodes. A wipe on one side does not remove the other side's nodes.

Wire shape, text:

```
A keydown -> sendText -> dc.send('{"k":"msg","text":"..."}')
  -> SCTP ordered reliable -> DTLS record(s) -> UDP
  -> B dtls -> sctp -> onmessage(string) -> JSON.parse -> addMessage -> textContent
```

### File and image path

Triggers:

- Attach button clicks the hidden `#file` input (1090, 414-415).
- File input change bumps activity, calls `queueFiles(el.file.files)`, then clears the input value (1100-1104).
- Document-level `drop` when connected prevents default, removes the overlay, and queues `event.dataTransfer.files` (1110-1121). Because the listener is on `document`, a drop anywhere in the window sends.
- Document-level `paste` when connected reads `event.clipboardData.files` and queues them (1124-1131). Pasting text is not intercepted, so it goes into the focused field normally.

Send path:

1. `queueFiles` (872-881) folds every file into one promise chain: `sendQueue = sendQueue.then(() => sendFile(file)).catch(...)`. Files are sent one at a time per sender. The catch toasts the error and resolves, so the next file still runs (877-879).
2. `sendFile` (883-926) requires an open channel (885), rejects a zero-byte file (886), and rejects a file over `MAX_FILE` (887). `MAX_FILE` is `50 * 1024 * 1024` = 52,428,800 bytes, which is 50 MiB, not 50 MB decimal (427).
3. It derives `type = file.type || 'application/octet-stream'` (889). It creates a local object URL from the `File` (890), stores it in `urls` (891), and builds a card with `mine = true` (892). If the MIME type matches `/^image\/(png|jpe?g|gif|webp|avif)$/i`, it sets the card image to the local object URL and unhides it (893-896). This preview comes from the sender's own file, not from the wire.
4. It sends a control frame: `{ k: 'file-start', id: uid(), name: file.name.slice(0, 200), size: file.size, type: type.slice(0, 120) }` (898-904). The `id` is generated but never sent again, never checked by the receiver, and never correlated with chunks.
5. Chunk loop (906-923). `CHUNK` is 16,384 bytes (428). For each step it checks the channel is still open, else marks the card "connection lost" and throws (909-912). It slices `file.slice(offset, end).arrayBuffer()` (913-914), sends the ArrayBuffer (915), advances the offset, updates the progress bar when the integer percent changes (917-921), and awaits `drain()` (922). A 50 MiB file is exactly 3200 chunks.
6. `drain` (856-870) returns immediately while `dc.bufferedAmount < 512 * 1024` (857). Otherwise it waits for `bufferedamountlow` (threshold set to 128 KiB at 663) or a 10 second timeout (867). The timeout resolves anyway, so the loop can keep enqueuing while the buffer is still above the threshold. `dc.send` on a full SCTP buffer can throw; `sendFile` has no try/catch around the send, so the throw reaches `queueFiles`, which toasts and leaves the card at its last progress value.
7. After the loop it sends `{ k: 'file-end' }` (924) and marks the card sent with the local URL (925). The local card never gets a Save link.

Receive path:

1. `onMessage` sends any non-string payload to `addChunk` (838). `binaryType` is `arraybuffer` (662), so chunks arrive as ArrayBuffer.
2. `file-start` calls `beginIncoming` (831-832). If a file is already in progress, the new start is dropped silently (999). A peer that opens a file and never ends it therefore blocks all later files for the session.
3. `beginIncoming` validates `Number(message.size)`: finite, greater than zero, at most `MAX_FILE` (1000-1004). Invalid size sets `incoming = { reject: true }` and adds a system line. It coerces `name` and `type` to strings and slices to 200 and 120 characters (1006-1007). It creates the receiver card (1008) and allocates `new Uint8Array(size)` immediately (1011), before any byte arrives. A single small control frame can force a 50 MiB allocation.
4. `addChunk` (1019-1036) ignores data when there is no incoming file or the file is rejected. It views the ArrayBuffer as `Uint8Array`, computes remaining room, and either copies and advances, or copies only the room, sets offset to the end, and marks `bad` (1023-1026). There is no chunk header, index, sequence, or hash. Correctness depends entirely on SCTP ordered reliable delivery and on the declared size.
5. `file-end` calls `endIncoming` (833-834, 1038-1053). A rejected file is cleared with no card. Otherwise it takes `bytes = bad ? buffer.slice(0, offset) : buffer` (1045). Since `bad` sets `offset` to the full buffer length, and a clean short file leaves `offset` below the length, the Blob is in both cases the full declared size. Missing bytes are zeros, not absent. It builds `new Blob([bytes], { type: meta.type })` (1046), a second full-size copy, creates an object URL (1047), stores it in `urls` (1048), tests the image MIME allowlist (1049), and calls `card.done(url, preview)` (1050).
6. `card.done` for a receiver sets `save.href = url`, `save.download = name`, and unhides Save (980-984). It also sets the preview image if the type matched (985-988). Only after that does `endIncoming` check `offset !== meta.size || bad` and call `card.error('incomplete')` (1051). The Save link is already live, so a truncated, zero-filled, or overlong file can be saved under the original name with only a small "incomplete" label in the card footer.
7. The Save link is a normal anchor with `download` and `rel=noopener` (958-962). Clicking it is the only write to disk in the app. The browser reads the Blob through the object URL. The saved file is plaintext and persists after the session.
8. Object URLs live until `endSession` revokes them (559-561) or the document unloads. `pagehide` does not revoke them (1141-1145). Every sent or received file adds one URL and, for images, one DOM `img` node. There is no cap on file count, so a long session accumulates Blob memory until wipe.

Wire shape, file:

```
sender: File -> 16 KiB slices -> dc.send(ArrayBuffer) x N
        plus one file-start JSON, one file-end JSON
receiver: file-start -> Uint8Array(size) -> copy chunks -> Blob -> object URL
          -> img.src (if image) and a.download (Save)
```

Peak receiver memory per file is at least the declared size for the `Uint8Array` plus the same size again for the Blob, so about 100 MiB for a 50 MiB file, before browser-internal copies. The sender keeps the original file plus one 16 KiB slice at a time. None of this is streamed to disk.

Integrity and identity properties of the file path:

- No hash, checksum, or signature over the file. Length mismatch is the only corruption signal, and it is checked after the Save link appears.
- No binding between `file-start` and `file-end` or between chunks beyond the ordered channel. The `id` field is unused.
- The receiver trusts the peer's declared size, name, and MIME type. The name is only length-limited. The type is only allowlisted for preview, not for storage.
- A malicious peer can send `file-start` with 50 MiB, no chunks, and `file-end`, producing a 50 MiB zero-filled Blob and a Save link, with "incomplete" as the only warning.
- Files are encrypted only in transit by DTLS. In the tab they are plaintext `Uint8Array` and Blob memory. On disk, if saved, they are plaintext.

## TRUST BOUNDARIES

| Boundary | What crosses | Guard today | Gap |
|---|---|---|---|
| Local user input to DOM | Typed text, pasted text, dropped files, file names, file bytes | `textContent` only (534, 522, 938, 992), no `innerHTML` anywhere (grep 0 hits), `MAX_TEXT` (849, 830), `MAX_FILE` (887, 1001), name and type length caps (901-903, 1006-1007), image MIME allowlist (893, 1049) | Bidi and control characters are not filtered. File names are only length-limited (901, 1006). No clickjacking guard. Image decode is browser attack surface. |
| App to peer network | SDP codes before pairing, then text, file metadata, file bytes | DTLS with the certificate hash from the remote SDP, SCTP ordered reliable, one stream | No fingerprint display or SAS. No message authentication or sequence numbers. No file hash. Codes are bearer tokens. |
| Peer to app parser | JSON control frames and binary chunks | `typeof` checks (826, 829), size caps (1000-1004), one file at a time (999), `textContent` render | No schema version, no rate limit, no chunk framing, no `file-start` to `file-end` correlation, no validation that a `file-start` is plausible before allocating up to 50 MiB (1011). Unknown keys ignored. |
| App to Google STUN | Source IP, source port, ICE username fragments, timing of binding and consent checks | None. STUN is the only third party (442-445) | CSP `connect-src 'none'` (6) does not govern WebRTC, so the policy does not stop or scope STUN or any peer connection. |
| App to static host | HTTPS GET of the HTML, source IP, user agent, headers, timing. The host can modify the file | `referrer` meta `no-referrer` (7). No SRI or hash pin because the script is inline | No integrity pin. A compromised or malicious host serves a backdoored page. `Cache-Control` meta (8) is not an effective header. |
| App to browser storage | Nothing through app APIs. Zero hits for localStorage, sessionStorage, IndexedDB, document.cookie, serviceWorker | Absence of APIs is the guard | The HTTP cache may store the HTML. bfcache may snapshot the page. `Cache-Control` meta is not a supported `http-equiv` value, so `no-store` is not reliably honored. |
| App to OS memory and disk | Plaintext messages in DOM, file bytes in `Uint8Array` and Blob, SDP and codes in JS strings and textareas | `pc.close()` and reference drops at 541-552. `URL.revokeObjectURL` at 559-561 | No zeroization. GC timing is not controlled. Swap, hibernation, crash dumps, screenshots are outside the app. |
| App to clipboard | Invite and reply SDP copied by user action (1067). Pasted files read from clipboard (1126) | User gesture only. No auto-copy, no auto-paste | Clipboard history and other apps can read the codes. No clear after copy. |
| App to URL parameter | `idle` in seconds from `location.search` (430-434) | Minimum of 5 seconds (432). Non-finite values fall back to 30 minutes | A crafted link can force a 5-second wipe. There is no upper bound, no warning, and no signature on the parameter. |
| Embedding page to app | Clicks and keystrokes through an iframe | None. CSP cannot set `frame-ancestors` from a meta tag, and no `X-Frame-Options` exists | Any site can frame the app and clickjack Connect, Create invite, or Wipe. `default-src 'none'` does not prevent embedding. |
| Browser extension or DevTools to app | Full DOM, JS heap, network events | None | Any extension with host permission reads the transcript and the file bytes. Private browsing does not remove this exposure. |
| Receiver Save to disk | Full file bytes and filename | Explicit click on the Save anchor (958-962, 980-984), `download` attribute, `rel=noopener` | The file is plaintext and persists. The browser may keep a download history entry. The app cannot delete it later. |

Guard notes with sources:

- CSP is delivered in a meta tag (6). It blocks scripts from external origins, styles from external origins, frames, objects, forms, and base changes. `script-src 'unsafe-inline'` is required because the whole app is inline. There is no injection sink in the app, so this mainly limits blast radius if one is added later.
- `connect-src 'none'` does not cover WebRTC. Chrome's own guidance states that CSP "does not govern speculative or non-Fetch network channels such as ... WebRTC" (https://developer.chrome.com/docs/modern-web-guidance/guides/security/restrict-outbound-connections, fetched, title "Restrict outbound network connections with Connection Allowlists"). MDN's `connect-src` page lists the governed APIs as ping, fetch, fetchLater, XMLHttpRequest, WebSocket, EventSource, and sendBeacon, with no RTCPeerConnection (https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/connect-src). The STUN traffic at 442-445 is therefore outside the CSP.
- `frame-ancestors` is not supported in a meta element, and a policy with `default-src 'none'` still allows the page to be embedded by anyone (https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/frame-ancestors, fetched, title "Content-Security-Policy: frame-ancestors directive"). The app has no server headers, so it cannot close this in the single-file form.
- `Cache-Control` in a meta tag is not a supported `http-equiv` value. MDN lists the supported values and warns not to set other security headers through `http-equiv` because unrecognized values are ignored and behavior varies (https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/meta/http-equiv, fetched, title "<meta http-equiv> HTML attribute"). The page's `no-store` intent at line 8 depends on the host sending a real header.
- There is no TURN server (442-445). This is good for trust, because no relay sees content, and bad for reachability, because symmetric NAT pairs fail closed. It also means the "direct channel" claim is true by construction, not by policy.

## WIPE PATHS

There are four triggers and one ordinary navigation path. `endSession` is the only function that performs the full wipe, and it is one-shot: a second call returns immediately (555-556).

| Trigger | Code path | What it provably clears | What it does not clear |
|---|---|---|---|
| Wipe button | `wipe` 1076-1080, `confirm` 1078, `endSession('wipe')` 1079 | Everything in the `endSession` inventory below. The peer loses the channel and runs its own peer-loss wipe. | Clipboard, browser cache, history, saved files, OS traces, peer's copy. No `window.close` attempt for this reason (600-604 only covers timeout and peer). |
| Idle timer | `checkIdle` 607-610 on an interval (1136), `bump` 612-623, `endSession('timeout')` 609 or 619 | The same full inventory. Then a `window.close` attempt 400 ms later (600-604). | The same residuals. The close attempt usually fails for a normal tab because the page was not opened by script (https://developer.mozilla.org/en-US/docs/Web/API/Window/close, fetched, title "Window: close() method"). |
| Peer loss | `connectionstatechange` 635-655, five second grace 638-644, immediate on `failed` or `closed` 645-647, channel `close` 681-683, `endSession('peer')` | The same full inventory, plus a `window.close` attempt (600-604). | The same residuals. If the failure happens before `connected`, there is no wipe at all: only status text and a toast (648-651). |
| Tab close or navigation | `pagehide` 1141-1145: `closePeer`, `incoming = null`, `log.replaceChildren` | The log DOM and the peer/channel references. The browser then tears down the document. | Codes in the four textareas, an unsent draft in `#input`, and object URLs are not cleared by this handler. Whether the browser frees or snapshots them is outside the app. |
| bfcache restore | `pageshow` 1147-1149: if `event.persisted`, `location.reload()` | On restore, the page reloads, so live JS state is rebuilt. | The bfcache snapshot itself may exist before the restore, and `pagehide` did not clear the code textareas or the draft. Whether that snapshot reaches disk is browser and platform dependent, UNVERIFIED here. |

### What `endSession` clears, line by line

- Stops the idle interval (557). `closePeer` also clears the disconnect timer (542).
- Sets `connected = false`, nulls `dc` and `pc`, closes both inside try/catch, nulls `incoming` (541-552).
- Revokes every object URL in `urls` and empties the array (559-561). This releases the Blob URL mappings. It does not overwrite the Blob bytes; the Blob becomes unreachable and is freed by GC.
- Nulls `incoming` again (562), which drops the only reference to the receive buffer. The `Uint8Array` is not zeroed.
- Resets `sendQueue` to a resolved promise (563). A file send in flight notices the closed channel on its next loop iteration and throws; its `File` reference and card remain until the promise settles.
- Removes every child of `#log` (564). All text bubbles, file cards, preview `img` nodes, and Save anchors are detached. Detached nodes are freed by GC, not zeroed.
- Empties the message input and all four code textareas (565-569). This sets `.value = ''`, which removes the current value but does not remove the elements or necessarily clear the browser's text control undo history. The textareas remain in the hidden pairing section.
- Empties the file input (570). This does not delete the user's original file.
- Hides the toast (571), hides pairing, chat, and composer (572-574), disables the input, Send, Attach, Wipe, Create, Join, Connect, Copy invite, and Copy reply (575-584), and hides the Wipe button (579).
- Sets status to "session ended" with the error color (585), writes the reason-specific title and body (587-596), shows the ended screen (597), and focuses Restart (598).

Provable outcomes: the live peer connection is closed, the transcript DOM is empty, the code fields are empty, the file input is empty, all visible controls except Restart are disabled, and the object URL table is empty. Not provable from the app: that any byte was overwritten in memory, that the clipboard is clean, that the browser cache is clean, or that the peer did the same.

### What no wipe path clears

- The HTML file itself, on the host or on local disk, and any HTTP cache copy. The `Cache-Control` meta at line 8 is not a reliable no-store directive (see TRUST BOUNDARIES).
- The browser history entry and the current URL, including any `?idle=` parameter.
- The system clipboard, if either code was copied, and clipboard history if the OS keeps one.
- Any file the receiver saved through the Save link. The app has no handle to delete it.
- The peer's transcript, peer's file blobs, and peer's codes. A wipe is local. The peer's own `endSession('peer')` clears that side, but only after the channel closes and only if the peer's page is still alive.
- Swap, hibernation files, crash dumps, screenshots, screen recordings, and OS-level telemetry.
- Browser extensions, DevTools sessions, and any instrumentation attached to the tab.
- Network captures. They hold ciphertext and metadata, not plaintext, but the metadata includes IPs, timing, and transfer sizes.
- The DNS cache entry for `stun.l.google.com`, and any STUN server logs.
- `lastActivity`, `lastBump`, and `sessionEnded` in JS memory. They are not sensitive, but they are not reset. Restart is a full `location.reload()` (1089), which rebuilds everything.

## CRYPTO REALITY

### What actually encrypts

One DTLS association per `RTCPeerConnection`, with SCTP inside it and one ordered data channel on top. The app contains no cryptography: no `crypto.subtle`, no library, no key derivation, no MAC, no signature. The only `crypto` call is `crypto.randomUUID` for the unused file id (488-490). All confidentiality, integrity, and peer authentication are delegated to the browser's WebRTC stack.

- Transport: DTLS 1.2 or 1.3 as negotiated by the browser, AEAD cipher, ECDHE key exchange. SCTP and the data channel ride inside DTLS, so text, control JSON, and file chunks share the same protection.
- Authentication: the `a=fingerprint` attribute in the remote SDP is the expected hash of the peer's DTLS certificate. The browser checks the certificate presented in the handshake against that hash. RFC 5763 describes the fingerprint as identifying the key presented during the DTLS handshake (https://www.rfc-editor.org/rfc/rfc5763, abstract). A mismatch fails the handshake, so the channel never opens.
- Trust anchor: the code channel. The fingerprint is only as trustworthy as the path that delivered it. RFC 8827 says the fingerprint binds the communication to a key pair and that the resulting security comes from having the fingerprint in a message received securely (https://www.rfc-editor.org/rfc/rfc8827, section 4.1).
- No application-layer encryption. If DTLS is terminated, the app has nothing underneath. There is no double encryption, no message-level seal, no sealed sender.

### Which keys exist, and where

| Material | Where it lives | Reachable from JS | Notes |
|---|---|---|---|
| DTLS certificate key pair | Browser network stack, generated by the browser, often per peer connection | No | Self-signed, not anchored to a CA. The fingerprint in the SDP is the only identity. |
| ECDHE session secret | Browser network stack | No | Ephemeral. Never written to the DOM or the codes. |
| DTLS record keys | Browser network stack | No | Derived from the ECDHE secret. Freed when the peer connection closes. |
| DTLS fingerprint | SDP string in `pc.localDescription` and `pc.remoteDescription`, in the four textareas, and in local `code` and `sdp` variables | Yes | Public hash. Not a secret. |
| ICE ufrag and password | Same SDP locations | Yes | Bearer credentials for ICE connectivity checks, not encryption keys. Anyone with the invite can use them to answer. |
| Message plaintext | DOM text nodes, the JSON string passed to `dc.send`, the parsed object in `onMessage` | Yes | Visible to DevTools and extensions. |
| File bytes, sender | The `File` handle and one 16 KiB `ArrayBuffer` slice at a time (913-915) | Yes | The original file stays on disk. |
| File bytes, receiver | `incoming.buffer` `Uint8Array` (1011) and the Blob built at 1046 | Yes | Plaintext, full file size, until GC. |
| App keys, passwords, ratchets | None | Not applicable | The app has no key material of its own. |

The codes are not keys. They are SDP envelopes carrying public fingerprints, ICE credentials, and candidates. Possession of a code grants the ability to participate in pairing, not the ability to decrypt a recorded session.

### Forward secrecy status

Forward secrecy is present at the DTLS layer, provided by ECDHE, and absent at the application layer because there is no application layer key schedule.

- RFC 8827 requires DTLS 1.2 with `TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256` and the P-256 curve, and requires implementations to favor cipher suites with forward secrecy over those without (https://www.rfc-editor.org/rfc/rfc8827, section 6, DTLS handshake text). ECDHE means the session keys are derived from ephemeral secrets that are not in the codes.
- The DTLS certificate is self-signed and typically generated per peer connection. There is no long-term identity key to steal and use against recorded traffic.
- Consequence: an attacker who records the ciphertext and later obtains both codes still cannot decrypt the session, assuming the endpoints were not compromised while it was live. The codes contain no ECDHE secret. This is the one strong property the design gets for free from WebRTC.
- Limit: there is no post-compromise security inside a session. If the endpoint is compromised while the session is live, the attacker reads the DOM, the JS heap, the receive buffer, and the Blob. Closing the peer connection ends the DTLS keys, but nothing rekeys on a schedule, and the app never rotates or confirms keys.
- Limit: DTLS may rekey internally, but the app has no visibility into it and no way to force it. The engagement idea of keys that constantly change is not implemented in V1. It would have to be built above or beside DTLS, and the current code has no hook for it.

### If the out-of-band channel leaks the codes

The severity depends on which code leaks and when.

- Invite code leaks before the host connects: the attacker has the host's offer, including ICE credentials and fingerprint. The attacker can create a valid answer and send it to the host. The host pastes it, DTLS succeeds against the attacker's fingerprint, and the attacker is the peer. The host sees "connected" and has no way to tell that the intended person never joined. This is the highest-severity leak.
- Reply code leaks before the host accepts it: the attacker has the joiner's answer, including the joiner's fingerprint and candidates. To use it, the attacker must complete DTLS with the host at the joiner's advertised address and port. An off-path attacker usually cannot claim that path. An attacker who can bind the address, race the real joiner, or sit on the path can. Lower severity than an invite leak, but not zero.
- Both codes leak after the session ends: no retroactive decryption. ECDHE secrets were never in the codes. The attacker learns IP addresses, candidates, and fingerprints, which are metadata, not content.
- Both codes leak during a live session: the attacker still cannot decrypt the existing DTLS association. They can impersonate one side only if they can get the other side to pair again with a substituted code, which requires an active channel, not a passive leak.
- Active man-in-the-middle on the code channel: the attacker replaces the host's offer with their own offer to the joiner and the joiner's answer with their own answer to the host. Each victim runs DTLS with the attacker and sees a fingerprint that matches the code it received. The attacker relays plaintext between the two DTLS legs. Nothing in the app detects this, because neither side ever displays or compares a fingerprint or a short authentication string. RFC 8827 calls for exactly that comparison as the out-of-band verification mechanism (section 6, security characteristics, certificate fingerprint or SAS).
- Passive observer of the code channel: can read the codes and race to answer an invite, but cannot decrypt a session it did not join. The invite is a bearer token with no expiry and no one-time enforcement before the host accepts an answer.
- Code reuse: there is no nonce, session id, or used flag. The host's `pc` is closed only by `closePeer`, `endSession`, or a new invite. Before an answer is accepted, the invite is valid for anyone who can reach the host's candidates. After the answer is set, a second answer is rejected by the SDP state machine, so the practical race window is between invite creation and Connect.

### What DTLS does not hide

- Peer IP addresses. Each side learns the other's candidates and source addresses. The STUN server learns the client's address.
- Traffic size and timing. A 50 MiB transfer is a large, long UDP flow. Chunk pacing and message cadence are observable. DTLS does not pad.
- The fact that a WebRTC session exists, between which addresses, and for how long.
- Endpoint state. The plaintext is in the tab by design. Any extension, DevTools session, or process with access to the renderer can read it.

## CLAIMS VERSUS CODE

The seven headline claims from the sheet are covered first. Verdicts are about what the code does, not about intent.

| # | Claim, sheet p.1 | Verdict | Code evidence | Why |
|---|---|---|---|---|
| 1 | "No persistence. No localStorage, IndexedDB, cookies, service worker, analytics, or external assets." | TRUE at the app API level, with an HTTP cache caveat | 0 grep hits for `localStorage`, `sessionStorage`, `indexedDB`, `document.cookie`, `serviceWorker`, `fetch`, `XMLHttpRequest`, `WebSocket`, `sendBeacon`; CSP at 6; no external script or link tags | The app never calls a persistence API. The caveat is outside the JS: the browser may cache the HTML, and the `Cache-Control` meta at 8 is not a supported `http-equiv` value, so `no-store` is not reliable. |
| 2 | "No server" and "no application server, relay, account, or directory" | PARTLY TRUE | ICE list 442-445; `RTCPeerConnection` 634; no TURN, no fetch, no signaling server | There is no application backend and no relay. But the page still comes from a static host or local disk, and Google STUN is contacted at 443-444. "No server" is true for content and signaling, false for delivery and NAT discovery. |
| 3 | "Direct encrypted channel" / "direct WebRTC session" | TRUE | One `RTCPeerConnection` 634, one data channel 755, STUN only 442-445, no TURN | Media and data go peer to peer over ICE-selected candidates. If a direct path cannot be found, the session fails rather than relay. DTLS provides the encryption. |
| 4 | "Manual pairing. A short invite and reply, exchanged out of band." | TRUE | `createInvite` 748-775, `joinSession` 777-805, `acceptAnswer` 807-822, `copyText` 1060-1074 | The app never transmits either code. The user copies and pastes them through a channel of their choice. The codes are SDP blobs, not short numeric codes, but they are manually exchanged. |
| 5 | "Up to 50 MB per file in 16 KB chunks" | TRUE with a units and memory caveat | `MAX_FILE` 427, sender check 887, receiver check 1001, `CHUNK` 428, loop 906-923 | The cap is 50 MiB (52,428,800 bytes), enforced on both ends. Chunks are 16 KiB. The receiver allocates the full size up front (1011) and then a second full copy for the Blob (1046), so a 50 MiB file costs about 100 MiB of tab memory. Nothing streams to disk. |
| 6 | "Erases itself. Close the tab, idle for 30 minutes, lose the peer, or press Wipe. Everything goes." | TRUE BY DEFAULT for idle, peer, and Wipe; NOT PROVEN for tab close | Idle default 431-434, interval 1136, `checkIdle` 607-610, `bump` 612-623, peer loss 635-655 and 681-683, Wipe 1076-1080, `endSession` 554-605, `pagehide` 1141-1145 | Idle, peer loss, and Wipe call `endSession`, which clears the DOM, codes, peer, and object URLs. The 30 minutes is only a default: `?idle=` accepts any value of 5 seconds or more (432-434), and only local activity resets it, so received traffic does not (1133-1135). Tab close runs a smaller cleanup that does not clear the code textareas or an unsent draft. "Everything" excludes clipboard, cache, saved files, peer copies, and OS traces. |
| 7 | "Auditable surface. One file, inline CSS and JS, no external assets. Read the whole thing before you trust it." | TRUE for the app file, with a stack caveat | 1154 lines, one file, inline style 10-348, inline script 422-1152, 0 external script or link tags, 0 `http://` or `https://` strings | The entire app logic is readable in one file with no minification and no dependencies. The security-critical part, DTLS, SCTP, ICE, and the browser's SDP handling, is not in this file and cannot be audited here. |

Secondary claims:

| # | Claim, sheet p.1 | Verdict | Code evidence | Why |
|---|---|---|---|---|
| 8 | "Files and images" and "16 KB chunks" | TRUE | 883-926, 428, 1019-1053 | File and image transfer share the data channel. Chunk size is 16 KiB. |
| 9 | "Images preview" | TRUE | 893-896, 1049-1050 | Preview only for `image/png`, `image/jpeg`, `image/gif`, `image/webp`, `image/avif`, on both sender and receiver. |
| 10 | "Drag, drop, paste. Drop files onto the window or paste a screenshot from the clipboard." | TRUE, with a connected-only condition | 1110-1121, 1124-1131 | The handlers return early unless `connected` is true. Drop is document-wide. Paste only handles files, not text. |
| 11 | "The receiver saves on request" | TRUE, with an ordering defect | Save anchor 958-962, enable on receive 980-984, incomplete check after 1051 | The Save link appears only on the receiver and only after `file-end`. It is enabled before the length check, so an incomplete file is still downloadable. |
| 12 | "One file, any OS. A browser page on Windows, macOS, and Linux. No install, build step, or dependency." | TRUE, subject to browser support | 1-9, 422-1152, `CompressionStream` fallback 722-730 | One HTML file, no build. It needs a browser with WebRTC and either `CompressionStream` or the `RAW1` fallback. No OS-specific code. |
| 13 | "No third-party code, fonts, or analytics" and "no external assets" | TRUE | 0 external `<script>`, `<link>`, font, or http(s) asset references; system font stack 34; inline CSS 10-348 | Nothing is loaded from another origin. STUN is a network service, not an asset. |
| 14 | "No accounts, contact discovery, or room IDs" | TRUE | No account, login, directory, or room code anywhere; pairing is the only entry 357-395 | Identity is whoever holds a code. There is no user database and no discovery. |
| 15 | "Messages and files exist only while the tab is open" and "no history" | MOSTLY TRUE, with browser-level caveats | DOM render 528-539, Blob 1046, `endSession` 554-605 | In-app data lives in DOM and memory. The browser may keep the page in HTTP cache or bfcache, and the OS may swap or dump it. A receiver-saved file outlives the tab by design. |
| 16 | "gzip SDP, about 650 chars" | UNVERIFIED in this lane | `pack` 722-730, `unpack` 732-746 | The mechanism is confirmed. The exact length depends on candidates and browser SDP and was not measured here. The run brief records about 650 chars as a prior verified fact. |
| 17 | "Tab close is a browser rule. A normal tab cannot be script-closed; the app wipes to an ended screen. A popup can close itself." | PARTLY TRUE and honestly worded | `endSession` ended screen 587-598, `window.close` 600-604, `pagehide` 1141-1145 | The ended screen appears for idle, peer, and Wipe. On tab close the app does not show an ended screen, because the page is going away; it runs `pagehide` cleanup. `window.close` is only attempted for timeout and peer, and normal tabs ignore it, which the sheet itself acknowledges. |
| 18 | "Verified in Chromium: two-way text, 2 MB binary, image preview, 60-message scroll, idle expiry, peer wipe, zero storage." | UNVERIFIED | No test artifacts in the project tree; mechanisms at 841-854, 883-926, 893-896, 511-517, 607-623, 554-605 | The code supports each mechanism. This lane did not run the app, and no test log or harness exists in `04_PROJECTS/EPHEMERAL` to confirm the test result. |
| 19 | "No message or file content passes through STUN." | TRUE | ICE list 442-445, DTLS data channel 634, 660-685 | STUN is used for binding discovery and connectivity checks. Content goes over the DTLS association to the peer. STUN sees addresses, ports, and ICE usernames, not text or files. |
| 20 | "The app writes nothing. A file exists on disk only if the receiver chooses to save it." | TRUE for app-initiated writes, with host and browser caveats | No storage APIs, no download call except the Save anchor 958-962/980-984 | The app itself writes no file and no storage entry. The browser writes cache, history, and downloads; the OS writes swap and dumps. The receiver's Save click is the only file write the app offers. |

### Keys, codes, blobs, DOM, the four categories the wipe claim depends on

- Keys: the app owns none. The DTLS certificate and ECDHE secrets are in the browser's network stack. `pc.close()` inside `closePeer` (549-550) tears down the association, and the app drops its only reference (547-548). The app cannot prove the browser zeroized the memory, and it never had access to the private key. No key is ever written to the DOM, the codes, or a textarea.
- Codes: `endSession` writes an empty string into `#offer`, `#answer`, `#offerIn`, and `#answerIn` (565-569). This clears the displayed and submitted values. The local variables `code` and `sdp` in `createInvite`, `joinSession`, and `acceptAnswer` are not nulled; they become unreachable when the async function returns and are freed by GC. The clipboard copy made by `copyText` (1067) is untouched, and the browser's text control undo history is not cleared.
- Blobs: every object URL in `urls` is revoked and the array is emptied (559-561). `incoming` is nulled (562), dropping the receive `Uint8Array`. The Blob built at 1046 has no reference after the DOM removal and the URL revocation, so it is freed by GC. Its bytes are not overwritten. Detached `img` nodes and Save anchors are removed by `replaceChildren` (564).
- DOM: `#log` is emptied (564), the composer and message input are hidden and the input value is cleared (565), the pairing screen is hidden with all four code fields cleared (566-569, 572), and all visible controls except Restart are disabled (575-584). The document itself, the CSS, the script, and the hidden element tree remain. No `document.write`, no `location.replace`, no history rewrite.

## CONSEQUENCES FOR HARDENING

1. Authenticate the human, not only the endpoint. The code binds a fingerprint to a certificate, but neither side ever displays the fingerprint or a short authentication string. An active out-of-band man-in-the-middle is undetectable. A SAS over the established channel, or a fingerprint display that both users compare, closes this. Evidence: codes at 761 and 792, no display anywhere, RFC 8827 section 6 calls for the comparison.
2. Make the codes single-use, expiring, and session-bound. Today an invite is a bearer token with no nonce, no expiry, and no binding to the intended peer. A race to answer is possible until Connect. Evidence: 734-745, 761, 807-815.
3. Treat all peer-supplied file metadata as hostile. Add a per-file hash, use the unused `id` to correlate `file-start` with chunks and `file-end`, frame each chunk, and check integrity before allocating or enabling Save. Evidence: `id` at 900 is never checked, allocation at 1011, Save before the check at 1050-1051.
4. Make the wipe as forensic as JavaScript allows, and be honest about the rest. Zero the receive buffer and Blob-sized arrays, clear the clipboard, clear the code fields on `pagehide` as well as `endSession`, and serve the page with real `Cache-Control: no-store` and `frame-ancestors` headers. Evidence: 559-570, 1141-1145, meta CSP and cache at 6-8.
5. Make idle expiry count session activity, not only local input. Received messages and file progress do not call `bump`, so a long silent transfer can be wiped mid-flight. Remove or gate the `?idle=` override, which currently allows a crafted link to force a 5-second wipe. Evidence: 431-435, 607-623, 1133-1136.

## SELF-CHECK

STATUS: complete. Completed in one pass, inside the lane budget.

| Acceptance item | Result | Evidence |
|---|---|---|
| Output file exists at the required path and is non-empty | PASS | `01-research/output/01-trust-map.md`, about 400 lines and 55 KB, written section by section. |
| INVENTORY covers every functional block with a line range and a one-line purpose | PASS | 47-row table from line 1 to line 1152, including head, CSS, each UI section, every JS function, event wiring, and page lifecycle. |
| SESSION LIFECYCLE explains invite and reply contents, fingerprint binding, validators, and failure paths | PASS | Code format and SDP contents at 722-746, 761, 792; validator table; 15 failure paths with line references. |
| DATA FLOW covers the text path from Enter to peer DOM | PASS | Nine ordered steps from 1093-1098 through 841-854, 824-839, 528-539, plus the wire shape. |
| DATA FLOW covers file and image chunking, reassembly, Blob, preview, and Save | PASS | Send path 872-926, receive path 998-1053, 16 KiB math, 3200 chunks, Blob at 1046, preview 1049-1050, Save 980-984. |
| TRUST BOUNDARIES table lists boundary, what crosses, and guard or nothing | PASS | 12-row table, including the no-guard rows for STUN, iframe embedding, extensions, and OS memory, with fetched sources for the CSP, frame, and cache claims. |
| WIPE PATHS covers tab close, idle, peer loss, and Wipe, including keys, codes, blobs, and DOM | PASS | Five-row trigger table, line-by-line `endSession` inventory at 554-605, plus the explicit keys, codes, blobs, DOM subsection and the residual list. |
| CRYPTO REALITY covers what encrypts, key locations, forward secrecy, and OOB code leaks | PASS | DTLS-only section, key location table, RFC 8827 forward secrecy quote with URL, seven leak scenarios. |
| Claims table covers no storage | PASS | Row 1, with grep evidence and the HTTP cache caveat. |
| Claims table covers no server | PASS | Row 2, verdict PARTLY TRUE, evidence 442-445 and 634. |
| Claims table covers direct channel | PASS | Row 3, evidence 634, 755, 442-445. |
| Claims table covers out-of-band codes | PASS | Row 4, evidence 748-822 and 1060-1074. |
| Claims table covers 50 MB files | PASS | Row 5, evidence 427, 887, 1001, 906-923, with the MiB correction. |
| Claims table covers 30-minute wipe | PASS | Row 6, evidence 431-434, 607-623, 554-605, 1141-1145, with the override and local-activity caveats. |
| Claims table covers auditable surface | PASS | Row 7, evidence one file, inline style and script, 0 external assets, with the browser-stack caveat. |
| Every app claim carries file:line evidence | PASS | Spot check: limits 427-429, idle 431-434, pairing 761/786/815, file 1011/1046/1051, wipe 559-569. Platform claims carry fetched URLs. |
| External claims carry a verified source URL | PASS | Seven URLs fetched and title-checked: RFC 5763, RFC 8827, MDN connect-src, MDN frame-ancestors, MDN meta http-equiv, MDN window.close, and Chrome's WebRTC and CSP guidance. |
| Unmeasured values are labelled | PASS | gzip code length row 16 and Chromium test row 18 are UNVERIFIED; bfcache disk retention is UNVERIFIED. |
| No em dashes or en dashes | PASS | A file scan for code points U+2014 and U+2013 returns 0 matches. |
| English output | PASS | Entire file is English. |
| No writes outside the one output file, no edits under `input/`, no git, no installs, no servers | PASS | Only `mkdir` of `output/` and writes to this file. Inputs opened read-only. |









