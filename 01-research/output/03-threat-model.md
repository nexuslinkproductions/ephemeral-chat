# 03. Threat model: Ephemeral chat V1

**Run:** w1-ephemeral-hardening-20261126
**Lane:** 3 of 7
**Status:** complete
**Subject:** `input/ephemeral-chat-v1.html`, 1154 lines, 35,598 bytes, SHA-256 `23be3a0b6f53587e50c97c1767fa745980788288145dc79d3dba42095b150337`.
**Product sheet:** `input/ephemeral-chat-overview.pdf`, one page.

## 0. Scope, method, scoring

This is an architecture-level threat model of V1 as shipped. It grades the app against nine attacker classes. For each class it states the attacker's capabilities, what V1 withstands today with source evidence, the gaps, and ranked hardening options. Section 11 ranks the residual risks by likelihood times impact.

Evidence convention:

- `ephemeral-chat-v1.html:NNN` is a line in the app source. All line numbers refer to that file. A bare `:NNN` is shorthand for `ephemeral-chat-v1.html:NNN`.
- "grep, zero matches" means I searched the whole file for the token and found no occurrence. The exact commands are in section 12.
- External claims carry a source URL. Anything I could not verify is marked UNVERIFIED.
- "Inferred" means the mechanism follows from the code or the protocol but I did not run an exploit.

Scoring:

- Likelihood 1 to 5: 1 requires rare access, 3 is opportunistic, 5 is present in most sessions.
- Impact 1 to 5: 1 is a nuisance, 3 is a session DoS or partial metadata, 5 is full plaintext, impersonation, or persistent compromise.
- Risk score = likelihood times impact. The table shows the reasoning, not just the number.

Grade rubric:

- A: withstands the class with no material residual.
- B: core confidentiality holds; the residual is metadata or availability.
- C: core holds only partially; a material gap needs a compensating control.
- D: the class wins against most app controls; only fragmentation and manual steps help.
- F: no effective defense in V1; the class wins by design.

## 0.1 The architectural fact that sets the ceiling

V1 has one authentication step: a person copies an SDP blob to another person over some other channel. The blob contains the DTLS fingerprint ([RFC 8827](https://www.rfc-editor.org/rfc/rfc8827)) and the ICE candidates ([RFC 8828](https://www.rfc-editor.org/rfc/rfc8828)). The DTLS handshake then proves that the party at the other end holds the private key for that fingerprint. It does not prove that the party is the person you meant to talk to.

The app never closes that gap. It has no fingerprint display, no short authentication string, and no binding between the code and an identity. The strings "fingerprint", "SAS", "verify", and "safety" do not occur in the file (grep, zero matches). The UI shows only the opaque code (`ephemeral-chat-v1.html:372`, `:391`). The code is compression plus base64 (`:722-730`), which is encoding, not authentication. Anyone who sees it can decode it.

Consequence: the confidentiality of every session is capped by the integrity of the out-of-band channel that carried the code. A network attacker who cannot see the code cannot break DTLS. An attacker who can read and write the code does not need to break DTLS. They supply their own fingerprint and become the peer. Every class below is a variation on this sentence.

## 0.2 Class summary

| # | Attacker class | Grade | Core residual |
|---|---|---|---|
| 1 | Passive network observer | B | Metadata: IPs, timing, volume |
| 2 | Active MITM on the network path | B | DoS; total if the page is served over HTTP |
| 3 | Compromised out-of-band channel | F | Attacker becomes the peer; no SAS |
| 4 | Rogue or malicious peer | C | Resource exhaustion; saved-file execution |
| 5 | Swarm or flood against ICE and WebRTC | C | No inbound rate limits; no TURN |
| 6 | Local forensics on a seized or shared device | D | Swap, screenshots, clipboard, memory |
| 7 | Platform adversary | F | Browser is the TCB; extensions read the DOM |
| 8 | Public STUN operator | B | Metadata and availability; no content |
| 9 | Supply chain, swapped HTML | C | No hash or signature in the product |

## 1. Passive network observer

Covers an ISP, a cafe or hotel wifi operator, a corporate network tap, and any on-path device that can read packets but does not modify them.

### Capabilities

- Read packet headers on the path: source and destination IP, port, protocol, timing, size, DNS queries, and TLS SNI if any.
- Correlate the session with other traffic from the same device, including the out-of-band channel if it is on the same path.
- Distinguish a text chat from a file transfer by volume, and estimate duration and activity periods.
- Cannot modify, drop, or inject. That is class 2.

### What V1 withstands today

- **Content confidentiality.** Every application payload crosses the data channel: `dc.send` at `ephemeral-chat-v1.html:849`, `:898`, `:915`, and `:924`. The data channel is SCTP over DTLS, which RFC 8831 describes as providing "confidentiality, source authentication, and integrity-protected transfers" ([RFC 8831](https://www.rfc-editor.org/rfc/rfc8831)). A passive observer sees ciphertext.
- **No HTTP content channel.** The file contains zero `fetch`, `XMLHttpRequest`, `WebSocket`, and `sendBeacon` calls (grep, zero matches). The only runtime network destination is the STUN server configured at `ephemeral-chat-v1.html:442-445`.
- **No third-party assets.** The markup contains no external `<script src>`, `<link href>`, or remote `<img src>` (grep, zero matches). The CSP at `:6` allows only inline script and style, plus `blob:` and `data:` images. There is no analytics, font, or CDN request to observe.
- **The app does not transmit the pairing codes.** The invite and reply codes are placed in textareas at `:763` and `:794`, and copied by a user action at `:1067`. The app itself never sends them anywhere. If the user sends them over a separate channel, that channel's exposure is not the app's traffic.
- **Files are not written to disk by the app.** `URL.createObjectURL` at `:890` and `:1047` creates memory-backed blob URLs. A received file is saved only if the receiver clicks the Save link (`:981-983`).
- **The page fetch is protected if the page is served over HTTPS.** The app cannot enforce HTTPS, but the documented deployment includes an HTTPS URL (product sheet, "HOW A SESSION STARTS", line 19). A `file://` load has no page fetch at all.

### Gaps

- **Metadata is fully exposed.** The observer sees both IPs, the UDP ports, the start and end time, the message cadence, and the volume. The product sheet concedes "Each peer sees the other's IP" and that a public STUN server sees a route request (product sheet, "THE PRIVACY MODEL", line 27). The same data is visible to the network.
- **DNS leaks the STUN dependency.** The lookup of `stun.l.google.com` at `ephemeral-chat-v1.html:443` tells the DNS resolver, often the ISP, that the device is using WebRTC. This happens before any DTLS handshake.
- **The out-of-band channel can escalate the class.** If the code is sent over plaintext SMS, email, or a chat on the same network, the passive observer sees it and becomes class 3. The app does not require or check an authenticated channel.
- **No traffic padding.** Text messages and file chunks have distinguishable sizes. A 50 MB file is obvious from the byte count. The observer can infer when a transfer starts and ends.
- **The idle wipe does not hide the live session.** The 30-minute default at `:431-435` limits duration, not visibility. An observer watching a live session sees it for as long as it runs.
- **HTTP delivery is a thin boundary.** If the page is served over HTTP, the passive observer becomes an active attacker who can swap the file. That is class 9, but the transition costs nothing for the attacker.

### Hardening options, ranked

1. **Require an authenticated out-of-band channel in the product text.** Signal, in person, or a password-manager share. Zero code, and it closes the escalation path to class 3. This is the highest value per unit of effort.
2. **Pad or bucket data channel frames.** Fixed-size frames, or padding to a small set of buckets, so text and file chunks are less distinguishable. Medium effort, some overhead. This directly serves the "undetectable to network observers" target.
3. **Offer a TURN over TLS 443 relay mode.** It looks like HTTPS, hides the peer IPs from each other, and survives UDP blocking. High effort and cost. It also addresses class 8 and the no-TURN availability gap.
4. **Publish a signed file and a hash.** Makes HTTP delivery irrelevant because the user can verify the file. Ops, low effort.
5. **Add a metadata note to the pairing screen.** Next to the existing STUN sentence at `:362`, list what the network sees: public IP, timing, and volume, not content. Zero risk, better informed consent.

**Grade: B.** Content is protected by DTLS. Metadata is not protected at all, and the out-of-band escalation is real.

## 2. Active MITM on the network path

Covers an attacker who can inject, drop, delay, or spoof packets on the path, including a hostile wifi portal, a rogue router, a compromised ISP middlebox, and a DNS hijacker.

### Capabilities

- Modify or drop packets in flight; spoof DNS responses; spoof or drop STUN responses; block UDP.
- Attempt to terminate DTLS with their own certificate.
- Serve a modified HTML file if the page is fetched over HTTP.
- Cannot forge the DTLS handshake without the private key for the fingerprint that is inside the code.

### What V1 withstands today

- **DTLS authenticates the peer against the fingerprint in the SDP.** RFC 8827 describes the signaling message as carrying "a 'fingerprint' attribute binding the communication to a key pair" ([RFC 8827](https://www.rfc-editor.org/rfc/rfc8827)). The app packs the whole local SDP at `ephemeral-chat-v1.html:761` and `:792`. If the attacker terminates DTLS with a different certificate, the fingerprint does not match and the handshake fails. The fingerprint travels in the out-of-band code, not on the network path.
- **There is no signaling endpoint to hijack after the code exchange.** The app does not fetch a session description, a room, or a key from a server. The only network traffic is STUN (`:442-445`) and the DTLS/UDP flow. An attacker cannot redirect a later signaling request because none exists.
- **No external script to inject.** The markup has no external references (grep, zero matches), and the CSP at `:6` is `default-src 'none'`. An on-path attacker cannot add a script tag to the page without changing the HTML itself.
- **`connect-src 'none'` blocks the common page-script egress APIs.** The CSP at `:6` blocks `fetch`, `XMLHttpRequest`, `WebSocket`, `EventSource`, `sendBeacon`, and the `ping` attribute (MDN lists these as the APIs controlled by `connect-src`; it does not list `RTCPeerConnection`) ([MDN connect-src](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/connect-src)). This is a mitigation, not a boundary, because a swapped file can omit the CSP.
- **No TURN means no relay credential to steal.** The ICE configuration at `:442-445` contains only STUN URLs. There is no TURN username, password, or relay allocation for an attacker to hijack.

### Gaps

- **Denial of service is trivial.** Drop the STUN responses or the UDP flow and the connection fails. There is no TURN fallback, so a UDP-blocking network is a hard stop. The app reports "connection failed" at `:645-651`, but it cannot distinguish censorship from a peer problem.
- **STUN responses are not authenticated.** The ICE configuration at `:442-445` has no STUN credential, and RFC 5389 defines the Binding exchange as a simple request and response ([RFC 5389](https://www.rfc-editor.org/rfc/rfc5389)). An on-path attacker can spoof a reflexive address or drop the response. The result is a wrong candidate or a failure, not a confidentiality break, because DTLS still checks the fingerprint.
- **HTTP delivery is a total break.** If the page is loaded over HTTP, the attacker can replace the HTML and the CSP goes with it. This is the only path from class 2 to full compromise, and it is an ops failure, not a crypto failure.
- **No path-quality signal.** A relayed, delayed, or throttled path is invisible. The status line at `:353` shows connected or not, not how. A user cannot tell a degraded path from a normal one.
- **DNS for the STUN host can be hijacked.** The app has no DNS pinning and no alternate resolver. A malicious STUN server can misdirect candidates, but it cannot decrypt the DTLS channel without the fingerprint private key.
- **No page integrity check.** If the page is served from a compromised HTTPS origin, the attacker is the origin, not an on-path MITM. That is class 9, and TLS does not help.

### Hardening options, ranked

1. **Serve only over HTTPS with HSTS, and publish the file hash.** Ops. This removes the HTTP swap path, which is the only total break in this class.
2. **Add a TURN over TLS 443 fallback.** It survives UDP blocking and makes the flow look like HTTPS. Medium to high effort. It also gives the app a relay mode for IP privacy.
3. **Show the selected candidate pair type and a round-trip estimate once connected.** Host, server-reflexive, or relay, plus a latency number. This does not stop an attacker, but it makes a relay or a degraded path visible. Low effort.
4. **Add a second STUN provider and a user-configurable STUN/TURN URL.** Low effort, improves resilience and lets a user avoid a blocked or untrusted operator.
5. **Separate network failure from peer loss in the UI.** Treat ICE gathering failure and `connectionState === 'failed'` before any connection as "network blocked", distinct from the peer-left path at `:590-592`. Low effort, reduces misdiagnosis.

**Grade: B.** Confidentiality holds against a network-only attacker. Availability and HTTP delivery are the gaps. If the page is served over HTTP, the grade for this class is F.

## 3. Compromised out-of-band channel

Covers an attacker who can read the invite or reply code from the channel that carries it (email, chat, SMS, a clipboard, a support ticket), and an attacker who can also write to that channel and substitute a code.

### Capabilities

- Read the code, decode it, and learn the offerer's ICE candidates and DTLS fingerprint.
- Write a different code: substitute an SDP with their own fingerprint and ICE candidates.
- Race the legitimate peer to answer an invite, or send a malicious invite to the joiner.
- Replay an old code while the original tab is still open.
- Send a gzip bomb as a code.
- If the channel is only readable, the attacker learns IPs and the fingerprint but cannot inject an answer. If it is writable, the attacker becomes the peer.

### What V1 withstands today

- **Nothing cryptographic.** The app treats any well-formed SDP as valid. `acceptAnswer` calls `setRemoteDescription` with the pasted answer at `ephemeral-chat-v1.html:815`. `joinSession` calls the same with the pasted offer at `:786`. There is no expected fingerprint, no allowlist, no signature, and no comparison step.
- **The code is not encrypted.** `pack` uses `CompressionStream('gzip')` and base64 (`:722-730`), with a raw base64 fallback when compression is unavailable. That is compression and encoding, not confidentiality. Anyone who sees the code can decode the SDP with standard tools.
- **Post-session cleanup is good.** `endSession` clears all four code textareas (`:565-570`) and the transcript (`:564`). That limits later recovery. It does not stop live substitution.
- **There is no inbound signaling listener.** The app has no server, room, or discovery endpoint. An attacker cannot initiate a session without a code. This is a real structural strength: unsolicited inbound traffic has no path to an answer. The target principle "unkeyed inbound traffic never gets an answer" is already true at the signaling layer. The gap is that a code is a bearer token, not a key.

### Gaps

- **No fingerprint display and no short authentication string.** The strings "fingerprint", "SAS", "verify", and "safety" are absent (grep, zero matches). The user has nothing to compare. The only thing shown is the whole code, which is opaque.
- **The invite leaks IP addresses.** The offer is packed after ICE gathering completes (`:758-761`), so it contains the offerer's candidates. RFC 8828 notes that ICE can reveal private addresses and, with a split-tunnel VPN, additional public addresses ([RFC 8828](https://www.rfc-editor.org/rfc/rfc8828)). Anyone who sees the code learns them.
- **No expiry.** The SDP has a session id and version, but the app does not check age. An invite can be answered while the tab is open, which may be hours. There is no timestamp or nonce in the code envelope.
- **No one-time use.** The app does not consume the invite after a successful answer. The same code can be pasted again. A second attempt calls `setRemoteDescription` on the existing connection (`:815`) or fails into `fail` (`:817-821`); the app does not mark the code as used either way.
- **No binding to the intended peer.** The app cannot tell the intended peer from anyone else who has the code. The DTLS handshake authenticates the holder of the fingerprint private key, which is exactly the attacker if they supplied the code.
- **The decompressor has no output cap.** `unpack` pipes the decoded body through `DecompressionStream('gzip')` and buffers the whole result with `new Response(stream).arrayBuffer()` (`:740-742`). A small gzip bomb can expand to a large buffer and crash the tab. This is reachable from the exact input the attacker controls. Impact is a tab DoS, not code execution.
- **The app gives no sensitivity warning.** Nothing tells the user that the code is the session secret and should travel over an authenticated channel.

### Hardening options, ranked

1. **Add a short authentication string derived from both DTLS fingerprints.** Parse the `a=fingerprint` line from the local and remote SDP, sort the two values, hash them, and display the same 6-word or 6-digit value on both sides. Require both users to confirm before the composer unlocks. This is the single highest-value change in the whole model. It turns the out-of-band channel from "trusted" into "tamper-evident", and it defeats a substituted answer and an active signaling MITM. Use `crypto.subtle.digest` where available; if it is unavailable, fall back to displaying both full fingerprints for manual comparison. Medium effort, no new dependency.
2. **Cap the code and the decompressed SDP.** Reject a code over a fixed size (for example, 16 KB) and a decompressed SDP over a fixed size (for example, 64 KB) before `setRemoteDescription`. One guard in `unpack` (`:732-746`). This closes the gzip bomb and the oversized-SDP path.
3. **Add an expiry and a one-time flag to the code envelope.** Include a timestamp and a random nonce, reject codes older than the ICE lifetime (a few minutes), and disable the join path after a successful answer. Low to medium effort, changes the code format.
4. **Warn that the code is a secret.** Put a line next to the invite and reply fields: send this over a channel you trust, and read it aloud if you can. Zero code. Pair it with the SAS from option 1 so the warning has a check behind it.
5. **Make the code single-use in the UI.** After a successful `setRemoteDescription`, clear the input, disable the connect or join button, and show "paired". The app already has the state transitions; this is a small UI change.

**Grade: F.** The class wins by design. The app's only authentication is possession of a bearer code, and it never verifies the bearer.

## 4. Rogue or malicious peer

Covers the person or process that holds a valid code and becomes the peer. The peer is authenticated as "whoever has the code", not as a known person.

### Capabilities

- Send arbitrary text, JSON, binary chunks, and file metadata over the data channel.
- Open additional data channels.
- Lie about file size, type, and name.
- Flood the channel with messages or chunks.
- Send an SDP answer with arbitrary ICE candidates.
- Deliver a malicious file and persuade the user to save and open it.
- Read everything the user sends, by definition.

### What V1 withstands today

- **No HTML injection.** Every message is inserted with `textContent` at `ephemeral-chat-v1.html:534`. The file contains zero `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, `eval`, and `new Function` (grep, zero matches). A message like `<img src=x onerror=alert(1)>` renders as text.
- **No scripted image preview.** The preview regex accepts only `image/png`, `image/jpeg`, `image/gif`, `image/webp`, and `image/avif` (`:893`, `:1049`). SVG is excluded, so an SVG with script is not loaded into the `<img>`.
- **File size is capped and checked.** `beginIncoming` rejects a size that is not finite, not positive, or over 50 MB (`:1000-1005`). The receiver allocates exactly that size (`:1011`). Overflow is truncated and marked bad (`:1023-1030`), and an incomplete transfer is flagged (`:1051`).
- **Only one incoming file at a time.** `beginIncoming` returns early if `incoming` is set (`:999`). Chunks without a `file-start` are dropped (`:1020`).
- **Filenames are text.** The name is inserted with `textContent` (`:938`) and sliced to 200 characters (`:1006`). The `download` attribute at `:982` is a user action, not automatic execution.
- **No automatic save or open.** The Save link is hidden until the transfer completes (`:961`, `:983`). The receiver must click it.

### Gaps

- **No transcript cap.** `addMessage` appends a new node for every message (`:528-539`), and nothing removes old nodes except `endSession` (`:564`). A peer can send messages until the tab runs out of memory.
- **No inbound message size cap before `JSON.parse`.** `onMessage` parses any string it receives at `:828`. The browser's SCTP receive limit is the only bound. The app does not check the string length or reject oversized messages.
- **No rate limit.** A peer can send a continuous stream of 20 KB text messages (`:830`) or binary chunks. There is no per-second or per-session budget.
- **Every data channel is bound.** The `datachannel` handler at `:656` calls `bindChannel` for every channel the peer opens, and `dc` is overwritten each time. Old channels keep their `message` listeners, so traffic can multiply across channels.
- **A malicious answerer can inject ICE candidates.** `setRemoteDescription` at `:815` accepts an answer with arbitrary `a=candidate` lines. The browser will send STUN connectivity checks to those addresses. This can generate UDP traffic to localhost or LAN hosts and trip intrusion detection. The attacker does not receive the results, so the intelligence value is limited, but the victim's browser is used as a probe. This is inferred from ICE behavior, not demonstrated in V1.
- **File type is attacker-controlled.** The Blob is created with `meta.type` at `:1046`. If the user saves an HTML, SVG, or executable file and opens it, it runs with the user's privileges. The app cannot prevent that, but it can warn and show the real type.
- **The download name is attacker-controlled.** `save.download` is set from the displayed name at `:982`. Browsers normally strip path separators, but a name like `invoice.pdf.html` is still deceptive. The UI shows the name, not the resolved type.
- **No integrity check beyond length.** DTLS protects the bytes in transit, so a network attacker cannot alter them. The peer itself can send anything. `endIncoming` only checks that the byte count matches (`:1051`).
- **The peer sees the user's IP by design.** There is no relay option. RFC 8828 describes the address exposure as a WebRTC property ([RFC 8828](https://www.rfc-editor.org/rfc/rfc8828)), and the product sheet concedes it.

### Hardening options, ranked

1. **Cap the transcript and the inbound rate.** A maximum node count or byte count, dropping the oldest messages, plus a per-session rate limit. One guard in `addMessage` and `onMessage`. Cheap, and it closes the easiest DoS.
2. **Reject oversized messages before `JSON.parse`.** A fixed cap for text messages (for example, 64 KB) and a cap for binary messages (the expected chunk size plus a margin). One guard in `onMessage` (`:824-839`). This also reduces the value of the multi-channel trick.
3. **Bind only the expected channel.** Accept the first channel with the label `chat`, and close or ignore additional channels. One guard in the `datachannel` handler (`:656`).
4. **Show the real type and warn before saving executable types.** Keep the raster-only preview. Add a warning on the file card for `text/html`, `image/svg+xml`, and executable types. UI change, no new dependency.
5. **Add a one-click block.** The Wipe button at `:1076-1080` requires a confirm dialog. Under an active flood, a block that closes the channel and wipes immediately is better. Low effort.
6. **Offer a relay mode to hide IPs from the peer.** This overlaps class 1 and class 8, and it is the only way to remove the by-design address exposure.

**Grade: C.** Injection and file preview are handled well. Resource exhaustion and local file execution are not.

## 5. Swarm or flood against ICE and WebRTC

Covers many hosts sending packets at the STUN service or the peer's UDP port, and a paired peer flooding the data channel. There is no application server, so the classic "flood the signaling service" attack has no target. The remaining surfaces are the public STUN dependency, the endpoint's UDP stack, and the data channel.

### Capabilities

- Flood or block the public STUN service, or flood the peer's UDP port with ICE connectivity checks.
- Send a code with a very large number of ICE candidates.
- Once paired, flood the data channel with messages, chunks, or new channels.
- Force repeated connection attempts by social engineering the user to paste codes.
- Cannot flood an application endpoint because none exists.

### What V1 withstands today

- **No signaling server, no room ID, no discovery.** A connection exists only after a user creates or joins a session (`ephemeral-chat-v1.html:748`, `:777`). There is no endpoint to enumerate, no directory to scrape, and no server-side queue to fill. This is the strongest structural property in the class.
- **ICE gathering is bounded.** `iceDone` resolves when `iceGatheringState === 'complete'` or after 4500 ms (`:687-704`). A slow or hostile STUN server cannot make gathering run forever.
- **The STUN list is fixed and small.** The ICE array at `:442-445` contains two Google hostnames. There is no remote configuration that can add arbitrary STUN or TURN servers.
- **The data channel is DTLS-protected and flow-controlled on the send side.** The sender waits when `bufferedAmount` is high (`:856-870`), and `bufferedAmountLowThreshold` is set at `:663`. This protects the sender's buffer, not the receiver's DOM.
- **The receiver caps one file at 50 MB and one at a time.** `:1001` and `:999`.

### Gaps

- **No inbound rate limit or transcript cap.** The same gap as class 4. A single paired peer can freeze the tab.
- **No cap on remote ICE candidates.** A malicious code can list thousands of candidates. The browser will send checks to each. This is a local resource and network-noise attack, not a content breach. It is inferred, not demonstrated.
- **No TURN and no relay.** There is no infrastructure that can absorb or filter a flood. The app is entirely endpoint to endpoint.
- **Both STUN hosts are Google.** A block or a flood of that service denies connectivity. There is no second operator and no fallback (`:443-444`).
- **No connection-attempt debounce.** A user can paste codes repeatedly, and each attempt creates a new `RTCPeerConnection` at `:754` or `:785`. This is user-driven, not remote, but it is unbounded.
- **No `maxMessageSize` check and no application framing.** The app relies on browser defaults for the largest message it will accept.
- **Incoming traffic does not reset the idle timer.** `bump` is attached only to local UI events (`:612-623`, `:1133-1135`), and `onMessage` never calls it. A long receive-only transfer can hit the 30-minute idle wipe (`:607-610`) while data is still arriving. This is a liveness and data-loss gap, not a confidentiality gap. It matters on slow links where a 50 MB transfer takes more than 30 minutes.
- **No heartbeat or path-quality signal.** The app relies on `connectionState` changes at `:635-655` and a 5-second disconnect timer at `:640-644`. That is adequate for peer loss, but it does not distinguish a flood from a bad path.

### Hardening options, ranked

1. **Implement the inbound rate limit, message size cap, and transcript cap from class 4.** One implementation covers both classes. Highest value.
2. **Reject remote SDP over a fixed size or with more than a fixed number of candidates.** Do it before `setRemoteDescription` at `:786` and `:815`. One guard. This bounds the ICE amplification surface.
3. **Add a second STUN operator and a TURN fallback.** Medium effort. This also improves availability on restrictive networks.
4. **Treat incoming traffic as activity for the idle timer, or pause the timer during an active transfer.** Small change in `onMessage` and `checkIdle`. This prevents a mid-transfer wipe.
5. **Debounce the Connect and Join buttons.** Ignore repeated clicks while a peer connection is being created. Low effort.

**Grade: C.** No server to flood is a genuine structural advantage. Endpoint resource limits are missing, and the public STUN dependency is a single point of failure.

## 6. Local forensics on a seized or shared device

Covers an attacker who has the device after the session, or who shares the device during it: disk forensics, browser profile inspection, swap and hibernation files, crash dumps, screenshots, screen recording, clipboard history, and a person looking over the shoulder.

### Capabilities

- Read the disk, the browser profile, swap, hibernation, crash dumps, and backup snapshots.
- Read clipboard history and clipboard manager databases.
- Read screenshots, screen recordings, and recent-files lists.
- Look at the live screen on a shared or unlocked device.
- If the device is captured during the session, read process memory, including plaintext and DTLS keys.
- Cannot read a session that ended and was wiped, unless a copy survived in swap, a dump, a screenshot, or the clipboard.

### What V1 withstands today

- **No persistence APIs.** The file makes zero calls to `localStorage`, `sessionStorage`, `indexedDB`, `serviceWorker`, and the Cache API. The only occurrences of "local storage", "IndexedDB", and "cookies" are the UI copy at `ephemeral-chat-v1.html:362`, which says nothing is written to them. A grep for `localStorage` and `sessionStorage` returns zero matches; `indexedDB` returns one, in that sentence.
- **No cookies.** The app never touches `document.cookie` (grep, zero matches).
- **The transcript is removed on end.** `endSession` calls `el.log.replaceChildren()` at `:564`, clears all four code textareas at `:565-570`, clears the file input at `:570`, and revokes every object URL at `:559-561`.
- **A normal navigation clears the page.** `pagehide` closes the peer and clears the log at `:1141-1145`. `pageshow` with `event.persisted` forces a reload at `:1147-1150`, so a bfcache restore does not show stale plaintext.
- **No automatic downloads.** The Save link is a user action (`:958-983`), and the product sheet states that a file exists on disk only if the receiver saves it (product sheet, line 47).
- **No third-party cache entries.** There are no external assets, so there is no CDN or font cache to inspect.

### Gaps

- **The `no-store` meta tag is not a cache control.** `Cache-Control: no-store` is set with `<meta http-equiv>` at `:8`. MDN lists the supported `http-equiv` values as content-language, content-type, content-security-policy, default-style, refresh, and set-cookie ([MDN meta http-equiv](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/meta/http-equiv)). Cache-Control is not one of them. If the page is served over HTTP, the browser may cache the HTML according to the server's response headers. The impact is low because the HTML contains no session data, but the app's "no-store" claim is not enforced by the app.
- **Memory is not zeroed.** `el.input.value = ''`, `replaceChildren()`, and `URL.revokeObjectURL` drop references. JavaScript strings are immutable, and buffers are garbage-collected; the app drops references but does not zero the underlying memory. The plaintext can remain in the heap, in swapped pages, or in a crash dump until the allocator reuses it. The app cannot call `memset` on a JavaScript string.
- **`pagehide` does not run on a crash, a forced kill, or a power loss.** `endSession` does not run either. The last transcript and codes can survive in memory or in a browser session restore.
- **Textareas are form controls.** Browser session restore may preserve their values across a crash or a restart. The app clears them only when `endSession` runs. This is browser-dependent and UNVERIFIED. I did not test session restore for this file. Treat it as a residual risk, not a confirmed leak.
- **Screenshots and screen recording are outside the app.** The product sheet admits "screenshots" and "clipboard" in the OS-level traces (product sheet, line 27). There is no blur-on-blur, no screenshot detection, and no way for a page to block the OS capture path.
- **Clipboard is a durable leak.** The Copy buttons write the full invite or reply code to the system clipboard at `:1067`, called from `:1085-1086`. macOS Universal Clipboard syncs it to other devices signed into the same account, and it remains there briefly ([Apple support](https://support.apple.com/en-us/102430)). Windows clipboard history keeps items until restart, except pinned items ([Microsoft support](https://support.microsoft.com/en-us/windows/apps/using-the-clipboard)). Clipboard managers persist to disk. The code is the session's only secret.
- **A shared device sees the live transcript.** There is no lock-on-blur. The transcript is visible until the 30-minute idle wipe (`:607-610`) or a manual Wipe (`:1076-1080`).
- **The original file remains on the sender's disk.** The app reads it for sending at `:914` and never deletes it. It cannot.
- **Browser history records the page.** The app cannot remove its own history entry or the `?idle=` parameter from the URL. `referrer` is `no-referrer` at `:7`, which helps against referrer leaks but not local history.
- **A saved received file is on disk by design.** The app cannot revoke it. The Save link is the only path, but the user may click it.
- **The idle window can be extended.** `?idle=` accepts any value of 5 or more (`:431-435`). A user can set a 24-hour session. This is a user choice, but the UI does not show the resulting exposure.

### Hardening options, ranked

1. **Blur or hide the transcript when the window loses focus or the screen locks, with a click-to-reveal.** This is the best cheap defense against shoulder surfing and casual shared-device access. It does not stop screenshots or a determined observer.
2. **Clear the clipboard after a short delay after copying a code.** For example, 30 seconds, best effort, with a warning that clipboard managers may keep it. Add a "read it aloud" option. Low effort, high value.
3. **Do not write the full code to the clipboard by default.** Show it, select it, and require a deliberate copy with a warning. Or shorten the code so it can be spoken or typed. Product decision.
4. **Add a "wipe on hide" option and a keyboard panic wipe.** Low effort. The Wipe path already exists at `:1076-1080`.
5. **Set a real `Cache-Control: no-store` response header at the server.** The meta tag at `:8` is decorative. Ops fix. Document that the app cannot set response headers.
6. **Document the OS-level residual.** Put the product sheet's own caveat (line 27) in the first-run text: swap, hibernation, crash dumps, screenshots, and clipboard are outside the app. Recommend full-disk encryption, a locked screen, and a dedicated browser profile.
7. **For high assurance, ship a native build that can zero memory and avoid the browser cache.** Long term. Changes the product.

**Grade: D.** The app minimizes its own artifacts well. The class includes the operating system, and the app's clipboard behavior adds a durable artifact that the app itself creates.

## 7. Platform adversary

Covers a malicious browser extension, a compromised browser, a compromised OS, and platform telemetry or endpoint agents that capture memory, screens, keys, or network traffic.

### Capabilities

- A malicious extension with host permission can read and modify the page DOM. Chrome content scripts run in an isolated world but "share access to the page's DOM" ([Chrome content scripts](https://developer.chrome.com/docs/extensions/develop/concepts/content-scripts)). An extension with the right permissions can also inject into the page's main world and hook APIs.
- A compromised browser or OS can read process memory, hook `RTCPeerConnection`, `RTCDataChannel.send`, `navigator.clipboard.writeText`, and `crypto`, capture the screen, and log keys.
- OS telemetry, crash reporters, endpoint agents, and backup tools may capture memory or files.
- An extension can read the pairing codes from the textareas, every message from the DOM, and every file card.
- The attacker does not need to break DTLS. They read the plaintext before or after it is encrypted.

### What V1 withstands today

- **Almost nothing, by definition.** The app's controls are the CSP at `ephemeral-chat-v1.html:6`, `textContent` at `:534`, and the absence of storage APIs. RFC 8827 states the assumption directly: "The basic assumption of this architecture is that network resources exist in a hierarchy of trust, rooted in the browser, which serves as the user's Trusted Computing Base (TCB). ... if the browser is compromised, then no security guarantees are possible" ([RFC 8827](https://www.rfc-editor.org/rfc/rfc8827)). This is the correct framing for the class.
- **CSP limits page-script egress, not extensions.** `connect-src 'none'` at `:6` blocks `fetch`, `XMLHttpRequest`, `WebSocket`, `EventSource`, and `sendBeacon` for a script running under the page's CSP. Content scripts run under the extension's CSP in an isolated world ([Chrome content scripts](https://developer.chrome.com/docs/extensions/develop/concepts/content-scripts)), so the page's CSP is not a boundary against them.
- **No injection sink.** `textContent` at `:534` and `:938`, and zero `innerHTML`, `eval`, or `document.write` (grep, zero matches). This removes DOM XSS as a pivot. It does not stop an extension, which reads the DOM directly.
- **No stored history.** Zero persistence APIs means an extension installed after the session cannot read a stored transcript. It must capture live. This reduces the blast radius of a late-installed extension.
- **`referrer` is `no-referrer` at `:7`.** The page does not leak its URL to third parties. An extension reads the URL directly.

### Gaps

- **Any extension with access to the page can read every message, the codes, and the file cards.** The app cannot detect or block it.
- **A main-world injection can replace `RTCPeerConnection` or `dc.send` and copy plaintext to an attacker.** The app has no integrity check on its own globals. It cannot tell that its APIs were wrapped.
- **A compromised browser or OS can read the heap and the DTLS keys.** The app cannot zero memory or attest the platform.
- **The CSP is a meta tag inside the file.** A malicious extension does not need to change it, because it runs outside the page's CSP. A swapped file can omit it. Neither path is stopped by it.
- **`script-src 'unsafe-inline'` is required by the single-file design.** There is no injection sink today, but any HTML injection would execute. This is a latent weakness, not an active hole.
- **No user-presence check.** The app cannot distinguish a human from an extension-driven DOM. The only human action is the initial click and the optional confirm on Wipe.
- **OS telemetry and crash reporting are outside the app.** The product sheet admits OS-level traces (line 27), but the app does not tell the user which platform features to disable.
- **The monitor overlay target is not a defense against this class.** A page-level overlay can watch the app's own signals, but a compromised browser can hide or alter the overlay. The overlay is a usability and transparency feature, not a security boundary.

### Hardening options, ranked

1. **State the platform assumption in the first-run UI.** Use a dedicated browser profile with no extensions, or a private window, and close other tabs. This is the only honest mitigation in a browser. Zero code.
2. **Offer a packaged desktop build with code signing and no extension model.** Tauri or Electron. High effort, changes distribution, but it is the only way to raise platform assurance.
3. **Add a "what this cannot protect" screen.** Extensions, screen capture, OS telemetry, and a compromised browser. Transparency, not prevention.
4. **Keep the CSP and the no-injection discipline.** Do not add `innerHTML`, `eval`, or third-party scripts. This preserves the property that a message cannot become code.
5. **If a native build is not possible, consider a Web Worker for message handling.** This makes casual DOM scraping harder. It is obfuscation, not a security boundary. Skip unless the product needs it.

**Grade: F.** The class is outside the app's trust boundary. The correct response is to state the assumption and offer a native option, not to pretend a web page can win.

## 8. Public STUN operator

Covers Google as the operator of `stun.l.google.com` and `stun1.l.google.com`, and any future operator the app might use.

### Capabilities

- See the source IP and port of every STUN binding request, plus timing and volume.
- Log, retain, and correlate requests from both peers.
- Return a bogus reflexive address, drop requests, or delay responses.
- Be compelled to disclose logs, or be breached.
- Cannot see the SDP, the pairing codes, the DTLS keys, or the content. STUN is not a relay in this app.

### What V1 withstands today

- **Content never transits the STUN server.** The only STUN use is ICE candidate gathering, configured at `ephemeral-chat-v1.html:442-445` and consumed by `new RTCPeerConnection` at `:634`. RFC 5389 defines STUN as a tool for an endpoint to discover its mapped address and check connectivity, not as a media or data relay ([RFC 5389](https://www.rfc-editor.org/rfc/rfc5389)).
- **The DTLS keys are negotiated end to end.** STUN is not in the key path. A malicious STUN response can misdirect candidates, but it cannot decrypt the channel without the fingerprint private key.
- **The pairing codes are never sent to the STUN server.** They are local textarea values at `:763` and `:794` until the user copies them.
- **No TURN means no relay operator receives the content.** The trade-off is that the peers' IPs are exposed to each other and to the network.
- **Two hostnames provide DNS-level redundancy.** `:443-444` lists two Google hosts. They are the same operator, so this is redundancy against a single host failure, not against the operator.

### Gaps

- **Metadata correlation.** The operator sees both peers' public IPs and the timing of their queries. It can infer that two IPs are likely in a call, even without the code. At scale, it can build a graph of who talks to whom.
- **Single operator dependency.** Both STUN hosts are Google. A block, a flood, or a policy change at that operator denies connectivity. There is no second operator and no TURN fallback.
- **A malicious operator can redirect the DTLS handshake.** It can return a reflexive address pointing at a host it controls. The handshake fails the fingerprint check, so confidentiality holds, but it enables a DoS and traffic redirection.
- **DNS leaks the dependency.** Resolving `stun.l.google.com` at `:443` tells the DNS resolver, often the ISP or a corporate resolver, that the device is using WebRTC. That is a second metadata observer.
- **No user-configurable STUN or TURN.** A privacy-conscious user cannot opt out of Google. The ICE array is hard-coded at `:442-445`.
- **The product copy is easy to misread.** "No message or file content passes through it" at `:362` is true. A reader may infer "no metadata". The sentence should say what the operator does see.

### Hardening options, ranked

1. **Allow a user-supplied STUN and TURN URL, and document a self-hosted option.** Medium effort, one configuration path. This is the only way a user can avoid a public operator.
2. **Use two or three STUN providers from different operators, or a self-hosted STUN as the first entry.** Cheap. This improves availability and reduces single-operator correlation.
3. **Add TURN over TLS 443.** It gives a relay path, hides peer IPs, and makes the flow look like HTTPS. Higher effort and cost. It also addresses class 1 and class 2.
4. **Document exactly what the STUN operator sees, next to the existing sentence at `:362`.** Public IP, timing, and volume, not content. Zero risk.
5. **For a global-adversary threat model, do not use a public STUN at all.** Use a STUN or TURN service in the same trust domain, or a relay the user controls. Product decision.

**Grade: B.** No content exposure. The metadata and availability dependency is real and is not disclosed precisely.

## 9. Supply chain: swapped or backdoored HTML

Covers an attacker who serves a modified copy of the HTML file, or who compromises the host, DNS, TLS certificate, or download path that delivers it.

### Capabilities

- Serve any JavaScript. Remove the CSP, add exfiltration, change the UI, and impersonate the peer.
- Compromise a static host, a DNS record, a TLS certificate, or a download mirror.
- Persuade the user to load a file from a link, an email, a chat, or a USB stick.
- If the user loads the modified file, the attacker has the same access as the app itself, plus network egress because the CSP can be omitted.

### What V1 withstands today

- **No third-party dependencies.** `ephemeral-chat-v1.html` contains no external `<script src>`, `<link href>`, or remote `<img src>` (grep, zero matches). There is no CDN, package manager, analytics, font, or remote configuration to compromise. This is the strongest supply-chain property in the app.
- **The whole app is one small file.** 35,598 bytes, 1154 lines. A determined reviewer can audit it. The product sheet calls this the "auditable surface" and says "Read the whole thing before you trust it" (product sheet, "WHAT IT DOES", line 17). That is a real property, though not a control most users will exercise.
- **No dynamic code loading.** Zero `eval`, `new Function`, `document.write`, `innerHTML`, and `importScripts` (grep, zero matches). A modified file must change the source itself, not inject a string at runtime.
- **CSP `default-src 'none'`.** The policy at `ephemeral-chat-v1.html:6` blocks external script, style, image, and connect sources. It limits a page-level injection that respects the CSP. It does not survive a modified file, because the policy is part of the file.
- **`referrer` is `no-referrer` at `:7`.** The page does not leak its URL to third parties. This is a small privacy gain, not an integrity control.

### Gaps

- **No signature, no published hash, no version display, no build provenance.** A user cannot tell a genuine copy from a modified one.
- **The CSP is a meta tag inside the file.** A modified copy can omit or weaken it at `:6`. There is no server header to enforce it.
- **SRI does not apply to the top-level document.** It works on `<script>` and `<link>` subresources, not on the HTML page itself ([MDN SRI](https://developer.mozilla.org/en-US/docs/Web/Security/Defenses/Subresource_Integrity)). There is no browser mechanism to pin the whole file.
- **HTTP delivery is a total break.** An active network attacker can swap the file in transit. This is class 2, but the impact belongs here.
- **A compromised HTTPS origin is a total break.** TLS proves the origin, not the content. If the origin is malicious or compromised, the user gets the malicious file over a valid certificate.
- **The download path is the trust path.** Email, chat, USB, and cloud drives are all in scope. The app does not verify where it came from.
- **No auto-update.** This avoids an update-channel hijack, but it also lets users keep an old vulnerable copy indefinitely. The trade-off should be explicit.
- **The "auditable surface" claim is not a control.** Most users will not read 1154 lines. A hash check is the usable substitute.
- **A modified copy can look identical.** It can keep the same UI and add one `fetch` to an attacker. The CSP would not be there to stop it, and all other classes become moot.

### Hardening options, ranked

1. **Publish a SHA-256 for every release in at least two independent channels.** For V1, the hash of the reviewed file is `23be3a0b6f53587e50c97c1767fa745980788288145dc79d3dba42095b150337`, measured with `shasum -a 256 ephemeral-chat-v1.html`. Put the expected value in the repository, the release page, and the documentation.
2. **Sign releases with minisign or cosign and publish the public key out of band.** A user can verify with one command. This is stronger than a hash on the same site, because the site can be compromised.
3. **Serve only over HTTPS with HSTS, from a static host with hardware-key account security and no third-party scripts.** Ops. This removes the HTTP swap path and reduces host compromise.
4. **Display the build hash in the UI footer, generated at build time.** A modified copy can change it, but a user who compares it to the published value can detect a casual swap. Low effort, useful with option 1.
5. **Put the verification command in the first-run UI, not only in the repository.** "Before you use this file, run `shasum -a 256 ephemeral-chat-v1.html` and compare to the published value." Zero code.
6. **For high assurance, distribute a signed native app or a signed archive with a verifier script.** Higher effort, changes distribution.

**Grade: C.** The no-dependency design is excellent. The app provides no way to verify that the file is the one that was reviewed. A swapped file is an F.

## 10. Cross-class observations

- **The pairing code is the root of trust.** Classes 1, 2, 3, and 9 all reduce to who has the code and what they can do with it. The code is a bearer token, not a key. It is not bound to a person, a device, or a time window.
- **The cryptography is not the weak part.** DTLS over SCTP is sound, and the app uses it correctly. The weak parts are authentication, resource limits, and platform trust. Do not spend the hardening budget on a new cipher before adding a SAS.
- **The product's own privacy model already concedes classes 6, 7, and 8.** The product sheet lists "Swap, hibernation, crash dumps, screenshots, clipboard" as OS-level traces and says "The app writes nothing; the OS can" (line 27). It also concedes that each peer sees the other's IP and that a public STUN server sees a route request. The threat model should treat these as documented residuals, not surprises. The gap is that the in-app text does not repeat them.
- **"No persistence" is true at the API level, false at the memory and OS level.** The app calls no storage API. The plaintext still lives in the DOM, the heap, swap, and any screenshot or clipboard capture. State the distinction precisely; do not let the marketing line stand in for the property.
- **V1 has no application-level key rotation or ratchet.** It relies on the DTLS session keys. There is no per-message rekey, no post-compromise migration, and no kill switch that moves both peers to a fresh keyset. The engagement's "transformers" target is a V2 design item. The current Wipe path (`:1076-1080`) ends the session locally; it does not coordinate a new keyset with the peer.
- **V1 has no identity layer.** There are no accounts, contact discovery, or room IDs. That is a privacy feature and an authentication limitation. The manual code is the only identity, and it authenticates possession, not personhood.
- **The idle wipe is a duration control, not a confidentiality control.** It limits how long a forgotten session stays open. It does not help against a live observer, a screenshot, a clipboard capture, or a memory dump. The default is 30 minutes (`:431-435`); the user can shorten it to 5 seconds or lengthen it without bound.
- **The design has one genuinely strong structural property.** There is no signaling server and no inbound listener. Unsolicited traffic has no path to an answer. Any hardening should preserve that property. Do not add a rendezvous service without a keyed admission check.

## 11. Top 10 risks

Ranked by likelihood times impact. The score is a sorting device, not a measurement. The reasoning column is the actual judgment.

| Rank | Risk | Class | L | I | Score | Reasoning |
|---|---|---|---|---|---|---|
| 1 | Pairing code is read or substituted on the out-of-band channel, so the attacker becomes the peer | 3 | 3 | 5 | 15 | The app's only authentication is possession of the code. Account compromise, a wrong recipient, or a helpdesk-style social engineering is plausible. The attacker who can write the code supplies their own fingerprint, becomes the peer, and the victim sees a normal "connected" state. No fingerprint display or SAS exists to detect it. |
| 2 | Pairing code persists in the OS clipboard or clipboard history | 3, 6 | 3 | 5 | 15 | Copy is a first-class button (`:1085-1086`) that writes the full code to the clipboard (`:1067`). macOS Universal Clipboard syncs it to other devices, Windows clipboard history keeps it until restart, and clipboard managers persist it. The exploit window is limited to the offerer's open tab and the ICE candidate lifetime, but a shared or seized device at the right time gets the same full compromise as rank 1. The app creates this artifact itself. |
| 3 | A swapped or backdoored HTML file is loaded | 9 | 3 | 5 | 15 | The file is the app. A modified copy can remove the CSP and exfiltrate everything. L3 covers HTTP delivery, a malicious mirror, or a phishing link; L2 applies only if every user loads from a pinned HTTPS origin. No hash or signature is published, so the user cannot tell. The impact is total and voids every other class. |
| 4 | Screenshot or shoulder surfing captures the transcript | 6 | 4 | 3 | 12 | Shared devices, screen sharing, and OS screenshot tools are common. The app has no blur when the window loses focus and no capture detection. The impact is what is on screen at that moment, not the whole session or the keys, so the impact is 3. |
| 5 | A malicious extension or a compromised browser reads the session | 7 | 2 | 5 | 10 | Extensions with broad host permissions are common; a malicious or compromised one is a targeted condition. A compromised browser or OS is rarer. The impact is total: DOM, plaintext, codes, and the ability to hook APIs. RFC 8827 says the browser is the TCB and no guarantees are possible if it is compromised. |
| 6 | Disk, swap, hibernation, or a crash dump contains plaintext after the session | 6 | 2 | 5 | 10 | Requires device seizure, forensic access, or a crash with a memory dump. Full-disk encryption reduces but does not remove the risk, because swap and hibernation can be captured while mounted. The app does not zero memory, so a memory image can contain the full transcript and keys. |
| 7 | The public STUN operator correlates the session or is blocked | 8 | 5 | 2 | 10 | Every session uses Google STUN (`:442-445`). The operator sees both public IPs and the timing, and can correlate them. It sees no content, so the impact is 2. Blocking is an availability issue. Likelihood is 5 because the dependency is unconditional. |
| 8 | A passive network observer profiles the session | 1 | 5 | 2 | 10 | Any ISP, cafe wifi, or corporate tap is on the path. The observer sees IPs, timing, and volume, but not content. It can infer a WebRTC call and its size. Likelihood is 5 because it is present on every network path. |
| 9 | A malicious peer floods the data channel and exhausts the tab | 4, 5 | 3 | 3 | 9 | The peer is authenticated by possession of the code, so a malicious peer is a realistic class. The flood is trivial: unlimited messages, no transcript cap, and no rate limit. The impact is a tab crash or freeze, which ends the session but does not expose more than the peer already sees. Availability only. |
| 10 | The user saves and opens a malicious file from the peer | 4 | 2 | 4 | 8 | The user must click Save and then open the file. The preview excludes SVG and shows only raster images, but the Save link writes any type. Opening an HTML or executable file runs it with the user's privileges. The app can warn, but cannot prevent it. |

Below the top 10, for completeness. The no-TURN row scores 8, the same as rank 10, but it is an availability risk with no confidentiality impact, so it is kept out of the top 10.

| Risk | Class | L | I | Score | Why it is below the line |
|---|---|---|---|---|---|
| An active network attacker blocks UDP or spoofs STUN, causing a failed connection | 2 | 3 | 2 | 6 | Availability only. DTLS and the fingerprint hold, so there is no content exposure. |
| Browser session restore keeps textarea codes after a crash | 6 | 2 | 3 | 6 | UNVERIFIED. The codes are in form controls, but I did not test the browser's restore behavior. The window is a crash or forced restart, not a normal close. |
| A gzip bomb in a pasted code crashes the tab | 3 | 2 | 2 | 4 | The attacker must get the user to paste the code. The outcome is a tab DoS, not code execution. |
| A malicious answer injects ICE candidates and probes the local network | 4 | 2 | 2 | 4 | The browser sends STUN checks, but the attacker does not get the results. Noise and local reconnaissance, not a content breach. |
| No TURN, so symmetric NAT or UDP blocking prevents a connection | 2, 5 | 4 | 2 | 8 | An availability risk, not a confidentiality risk. It is tracked by the transport lane. |

### Why this order

The top three all score 15 and all reduce to the two roots of trust: the code and the file. Rank 1 is the design (a bearer code with no verification). Rank 2 is an app feature that creates a durable copy of the code (the Copy button and the clipboard). Rank 3 is distribution (no way to verify the file). They are separated by how directly the app creates the exposure, not by severity. All three are total compromise when they land.

The middle band is the platform and the operating system. The app cannot fix a malicious extension, a memory dump, or a passive network tap. It can disclose them, reduce the clipboard and screenshot surface, and avoid adding new artifacts. That is the honest scope of a web app.

The bottom band is endpoint DoS and user action. These are cheaper to fix and lower impact, but they are the ones a peer or a bad code can trigger without any platform compromise. The inbound rate limit and the message size cap are one small guard each and should ship with the first hardening round.

The shape of the grades matches the shape of the risks. Classes 1, 2, and 8 get a B because DTLS does the work. Classes 3 and 7 get an F because the app has no control over the channel or the platform. Class 9 gets a C because the no-dependency design is strong but there is no verification step. Classes 4 and 5 get a C because the injection surface is clean but the resource limits are missing. Class 6 gets a D because the app minimizes its own artifacts but cannot control the OS, and it adds a clipboard artifact of its own.

### External sources

All sources below were fetched during this run, and the title was checked against the claim.

| Source | Title | URL |
|---|---|---|
| RFC 8831 | WebRTC Data Channels | https://www.rfc-editor.org/rfc/rfc8831 |
| RFC 8827 | WebRTC Security Architecture | https://www.rfc-editor.org/rfc/rfc8827 |
| RFC 8828 | WebRTC IP Address Handling Requirements | https://www.rfc-editor.org/rfc/rfc8828 |
| RFC 5389 | Session Traversal Utilities for NAT (STUN) | https://www.rfc-editor.org/rfc/rfc5389 |
| MDN | Content-Security-Policy: connect-src directive | https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/connect-src |
| MDN | `<meta http-equiv>` HTML attribute | https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/meta/http-equiv |
| MDN | Subresource Integrity | https://developer.mozilla.org/en-US/docs/Web/Security/Defenses/Subresource_Integrity |
| Chrome | Content scripts | https://developer.chrome.com/docs/extensions/develop/concepts/content-scripts |
| Apple | Use Universal Clipboard to copy and paste between your Apple devices | https://support.apple.com/en-us/102430 |
| Microsoft | Using the clipboard | https://support.microsoft.com/en-us/windows/apps/using-the-clipboard |

## 12. SELF-CHECK

### Lane acceptance

| Acceptance item | Result | Evidence |
|---|---|---|
| Every attacker class covered | PASS | Sections 1 to 9: passive observer, active MITM, out-of-band channel, malicious peer, swarm or flood, local forensics, platform adversary, STUN operator, supply chain. |
| Each class has capabilities, what V1 withstands, gaps, and ranked hardening | PASS | All nine sections contain the four `###` subsections. The final structural check printed `fields=True` for all nine. |
| Every withstands claim cites the source file | PASS | Each withstands block has at least one full `ephemeral-chat-v1.html:NNN` reference (counts 1 to 2), and every other line uses the `:NNN` shorthand defined at line 15. |
| TOP 10 table ranked by likelihood times impact with reasoning | PASS | Section 11 has exactly 10 ranked rows. Scores are 15, 15, 15, 12, 10, 10, 10, 10, 9, 8, and the sequence is non-increasing. Each row has L, I, score, and a reasoning cell. |
| English output | PASS | The file is English. |
| No em dashes or en dashes | PASS | Final scan: em 0, en 0, horizontal bar 0, minus sign 0. The stage-wide `grep -rl` also prints nothing. |
| External claims carry a URL or are marked UNVERIFIED | PASS | The external sources table at the end of section 11 lists 10 fetched sources. The session-restore claim is marked UNVERIFIED in section 6 and in the below-the-line table. The ICE candidate injection claim is marked inferred. |
| No edits outside the output file | PASS | Only `output/03-threat-model.md` was written. The input HTML and PDF were read only. |
| Time budget | PASS | The run started at 22:35 and the final check was at 22:48, about 13 minutes, under the 25-minute budget. |

### Stage-level checks

These are shared across the seven lanes. They were run after all seven files landed.

| Check | Result | Output |
|---|---|---|
| Seven output files exist | PASS | 7 |
| Every output file has a SELF-CHECK section | PASS | No file is listed by `grep -L`. |
| No em dashes in any output file | PASS | No file is listed by the em dash grep. |
| No en dashes in any output file | PASS | No file is listed by the en dash grep. |

Per-file claim discipline for the other six files is the lead's review item. This lane verifies its own file.

### Verification commands

```sh
cd /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL
shasum -a 256 input/ephemeral-chat-v1.html
# 23be3a0b6f53587e50c97c1767fa745980788288145dc79d3dba42095b150337
ls 01-research/output/0*.md | wc -l
# 7
grep -L "SELF-CHECK" 01-research/output/0*.md
# no output
grep -rl $'\u2014' 01-research/output/
grep -rl $'\u2013' 01-research/output/
# no output
```

### Source grep results used in the report

| Token | Matches | Where |
|---|---|---|
| `fingerprint`, `SAS`, `verify`, `safety` | 0 each | No verification UI or logic. |
| `localStorage`, `sessionStorage`, `serviceWorker` | 0 each | No persistence calls. |
| `indexedDB` | 1 | UI copy at `ephemeral-chat-v1.html:362` only. |
| `document.cookie` | 0 | No cookie access. |
| `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, `eval`, `new Function` | 0 each | No DOM or code injection sink. |
| `fetch`, `XMLHttpRequest`, `WebSocket`, `sendBeacon` | 0 each | No HTTP or socket egress. |
| `turn:`, `iceTransportPolicy` | 0 each | STUN only, no relay. |
| `crypto.subtle` | 0 | No application-layer crypto. |

### Known limits of this review

- I did not run the app, a browser, or an exploit. The claims are from source reading and protocol documents.
- Browser session-restore behavior for textarea values is UNVERIFIED.
- The ICE candidate injection impact is inferred from ICE behavior, not demonstrated.
- A naive scanner on this report will match the words `new Function` and `document.write` in the sentences that say the app has zero occurrences. Those are prose, not code.

