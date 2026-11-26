# 02 Audit findings, ephemeral chat V1

Run: w1-ephemeral-hardening-20261126. Lane 2 of 7.
Target: `/Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/input/ephemeral-chat-v1.html`, 35598 bytes, V1, 26 Nov 2026. Product claims: `input/ephemeral-chat-overview.pdf`.
Doctrine: trust boundaries first, reachability from a real entry point, exploit shape or fail-closed proof. Findings only, no fixes.
Status legend: CONFIRMED means the mechanism is visible in the source and the call path is complete. INFERRED means part of the impact depends on browser or runtime semantics that were reasoned from spec, not observed live. UNVERIFIED appears only where noted.

## Method and entry points

Every finding below traces to one of these six real entry points. Anything that did not trace was cut.

| Id | Entry point | Source line |
|---|---|---|
| E1 | Data channel `message` handler, text and binary | 684, dispatches to `onMessage` 824 |
| E2 | Drop handler on `document` | 1110 |
| E3 | Paste handler on `document` | 1124 |
| E4 | Invite parser, `#join` click | 1083, `joinSession` 777, `unpack` 732 |
| E5 | Reply parser, `#connect` click | 1084, `acceptAnswer` 807, `unpack` 732 |
| E6 | Unload and wipe paths, `pagehide` and `endSession` | 1141, 554 |

Absence claims were re-grepped, not assumed. `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, `eval`, `new Function`, `DOMParser`, `srcdoc`, `createContextualFragment`: zero hits. `localStorage`, `sessionStorage`, `indexedDB`, `document.cookie`, `serviceWorker`, `caches`: zero hits. `fetch`, `XMLHttpRequest`, `WebSocket`, `sendBeacon`, `EventSource`, `console.`: zero hits. The only network reach is the fixed STUN list at 442 to 445.

---

## F-01 Silent MITM whenever the out-of-band code channel is writable

**Severity: High**
**file:line:** 722-746 (`pack`/`unpack`), 761, 783-786, 792, 812-815, 748-822
**call_path:** `#create` click (1082) -> `createInvite` (748) -> `pack(pc.localDescription.sdp)` (761) -> code in `#offer` -> user transports the code over "any channel you trust" (product sheet line 19) -> attacker with write access to that channel replaces `a=fingerprint`, `a=ice-ufrag`, `a=ice-pwd` and `a=candidate` lines, keeping the SDP structurally valid -> victim pastes into `#offerIn` and clicks `#join` (1083) -> `joinSession` (777) -> `unpack` (783) -> `setRemoteDescription({type:'offer', sdp})` (786) -> victim returns the reply code -> attacker completes DTLS with the certificate matching the substituted fingerprint.
**exploit_or_proof:** The SDP is the only trust anchor and it is transported as opaque text with no integrity tag, no version, no session id, no expiry, and no second factor. Substitution is not detectable by the app and there is no fingerprint or SAS comparison in the UI to detect it out of band. RFC 8827 section 7 requires the security characteristics of a peer connection to include "some mechanism to allow an out-of-band verification of the peer, such as a certificate fingerprint or a Short Authentication String (SAS)" (https://www.rfc-editor.org/rfc/rfc8827.txt). V1 has the transport for such a check, the fingerprint is inside the code, but it never asks either user to compare it. The attacker becomes the DTLS endpoint and reads all "encrypted" content, or relays it to keep both users unaware. An attacker who is only on path, without write access to the code channel, is still stopped by DTLS fingerprint verification, so this is specifically the compromised out-of-band channel case.
**checklist_item:** auth, pairing, MITM when the out-of-band channel is compromised, key material in the code
**status:** CONFIRMED (mechanism and reachability). The live MITM is an exploit shape, not executed.

---

## F-02 Truncated transfer is zero padded and the Save link stays live

**Severity: High**
**file:line:** 1044-1051, 1023-1026, 976-985, 998-1016
**call_path:** `onMessage` (824) -> `beginIncoming` (831, 998) with `size: 50000000` -> a few binary chunks (838, 1019) -> `{"k":"file-end"}` (833) -> `endIncoming` (1038).
**exploit_or_proof:** `const bytes = bad ? buffer.slice(0, offset) : buffer;` (1045). On a short transfer `bad` is false and `offset < meta.size`, so `bytes` is the entire preallocated 50 MB `Uint8Array`, not the received prefix. `new Blob([bytes])` (1046) therefore has 50 MB of content with roughly 49,999,000 zero bytes appended. `card.done(url, preview)` runs first (1050) and sets `save.href` and `save.hidden = false` (981-983). Only afterwards does `card.error('incomplete')` (1051) replace the state text; it never removes the link or the blob. The user gets a normal looking Save control on a corrupt file, and the only signal is the word "incomplete" in the same footer row.
The same sequence is also an amplification primitive: about 1 KB of attacker traffic causes one 50 MB typed array plus one 50 MB blob snapshot, repeatable after each `file-end`.
**checklist_item:** deserialization and framing, chunk reassembly, data loss, oversized Blob
**status:** CONFIRMED

---

## F-03 Unbounded retained blob memory, no session byte or file count budget

**Severity: Medium**
**file:line:** 486, 890-891, 1046-1048, 559-561
**call_path:** repeated cycles of `file-start` / chunks / `file-end` (E1) -> `endIncoming` (1038) -> `URL.createObjectURL(blob)` (1047) -> `urls.push(url)` (1048). The only revocation is inside `endSession` (559-561).
**exploit_or_proof:** Every received file pins a blob in the blob URL store and a URL string in `urls` for the life of the session. There is no cap on file count or total bytes anywhere: `MAX_FILE` (427) is per file and `beginIncoming` validates only one file at a time (1001). Twenty files of 50 MB retain about 1 GB, and the tab is killed by the renderer long before `endSession` runs. The sender side has the same accumulation for local previews (890-891). Nothing trims the array, and a peer can drive it without any user action on the receiver.
**checklist_item:** DoS, unbounded buffers, oversized Blob, message rate
**status:** CONFIRMED (code path). The memory retention is INFERRED from blob URL store semantics: a blob URL keeps its blob alive until revoked or the document unloads.

---

## F-04 One invalid file-start disables all later file receive, silently

**Severity: Medium**
**file:line:** 998-1005, 999, 1020, 1038-1043
**call_path:** `onMessage` (824) -> `beginIncoming` (998) with `size` of 0, negative, above `MAX_FILE`, or non-numeric -> `incoming = { reject: true }` (1002). Every later `file-start` returns at `if (incoming) return;` (999). Every later binary frame returns at `if (!incoming || incoming.reject) return;` (1020). Only `file-end` clears the stub (1040-1043).
**exploit_or_proof:** Send `{"k":"file-start","size":60000000}` and never send `file-end`. The stub is never cleared, so for the rest of the session every legitimate file the peer sends is dropped with no UI feedback and no system message. The sender sees its own cards reach "sent" because `sendFile` completes into `dc.send` (924-925); the receiver sees nothing. Recovery requires ending the session, which the receiver has no reason to do because nothing was shown. The "too large" system message at 1003 fires once, then the feature is dead.
**checklist_item:** DoS, gate integrity keyed on a flag that never resets, file framing
**status:** CONFIRMED

---

## F-05 Gzip decompression bomb in the invite and reply parser

**Severity: Medium**
**file:line:** 732-746, 783, 812
**call_path:** paste a code into `#offerIn` -> `#join` click (1083) -> `joinSession` (777) -> `unpack(el.offerIn.value)` (783) -> `DecompressionStream('gzip')` (740) -> `new Response(stream).arrayBuffer()` (741) with no output limit. The same path exists for the reply at 812.
**exploit_or_proof:** `arrayBuffer()` buffers the entire decompressed output in memory before `setRemoteDescription` is ever reached (786). The format marker is fully attacker chosen and there is no cap on decompressed size. Measured locally with zlib level 9: zero filled input compresses at 1025.9 to 1 (10 MB to 10221 bytes, 1 MB to 1051 bytes). A 1 MB code string decodes to roughly 750 KB of gzip and expands to about 769 MB; a 5 MB paste expands to about 3847 MB. The resulting OOM kills the renderer, and because the allocation happens before any SDP validation, the invite is never even examined. This is reachable in the normal flow, since the invitee is expected to paste a code supplied by the other party.
**checklist_item:** DoS, deserialization, parser input bounds, oversized allocation
**status:** CONFIRMED (mechanism and measured compression ratio). The exact browser OOM threshold was not measured.

---

## F-06 Unbounded transcript DOM, no message or card cap, no rate limit

**Severity: Medium**
**file:line:** 528-539, 928-969, 824-839, 398
**call_path:** `onMessage` (824) -> `addMessage` (830, 528) or `beginIncoming` -> `createFileCard` (1008, 928). Each call appends a new subtree to `#log` and nothing ever removes one except `endSession`.
**exploit_or_proof:** A peer sends 20,000 character messages, the maximum `MAX_TEXT` allows (429, 830), in a tight loop. Each becomes a `div.msg > div.bubble` with its own text node, retained for the session. 50,000 messages retain about 1 GB of text plus layout boxes, and every append also forces a scroll measurement (511-517). File cards are cheaper per node and equally unbounded. There is no message counter, no byte budget, no time window, and no backpressure feedback to the sender. The log is also `aria-live="polite"` (398), so a screen reader queues the same flood.
**checklist_item:** DoS, message rate, unbounded buffers, main thread blocking
**status:** CONFIRMED

---

## F-07 Attacker chosen ICE candidates make the browser send UDP to arbitrary endpoints

**Severity: Medium**
**file:line:** 783-790, 786, 442-445, 6
**call_path:** `joinSession` (777) -> `unpack` (783) -> `setRemoteDescription({type:'offer', sdp})` (786) with an SDP containing `a=candidate` lines for arbitrary addresses -> `createAnswer` and `setLocalDescription` (788-789) -> ICE checklist -> STUN connectivity checks to every remote candidate.
**exploit_or_proof:** The pasted invite is not just an offer, it is the peer's entire candidate set. RFC 8445 section 2.2 describes the mechanism: "The agent works through the checklist by sending a STUN request for the next candidate pair on the list periodically" (https://www.rfc-editor.org/rfc/rfc8445.txt). An invite carrying candidates for `192.168.1.1:445`, `10.0.0.5:22` and an external host causes the victim's browser to emit STUN binding requests to those addresses as soon as the reply is generated. The app's fixed `ICE` list at 442 is irrelevant here, because these are remote candidates. The `connect-src 'none'` policy at line 6 does not stop it: CSP3 scopes `connect-src` to fetch, XHR, EventSource, Beacon, `ping` and WebSocket, and defines a separate RTC pre-connect gate (https://www.w3.org/TR/CSP3). Impact is a UDP probe of internal hosts from the victim's browser plus the victim's source address reaching an arbitrary endpoint. Requires the victim to paste the invite and click Create reply, which is the normal join flow.
**checklist_item:** auth, ICE candidate injection, CSP posture, network egress
**status:** CONFIRMED (protocol behavior per RFC 8445 and the source path). No live packet capture was performed.

---

## F-08 pagehide is a partial wipe and diverges from endSession

**Severity: Low**
**file:line:** 1141-1145, 554-605, 1147-1150
**call_path:** tab hidden or navigated away -> `pagehide` listener (1141) -> `closePeer`, `incoming = null`, `el.log.replaceChildren()`. It does not call `endSession`.
**exploit_or_proof:** Compare the two wipe sets. `endSession` clears `#offer`, `#answer`, `#offerIn`, `#answerIn`, `#input`, revokes every blob URL (559-561), resets `sendQueue`, and disables the controls. `pagehide` clears only the log. The pairing codes (which contain the DTLS fingerprint, ICE ufrag, ICE pwd and candidate addresses), any unsent composer text, and every live blob URL survive the handler. In a BFCache freeze the frozen document keeps them in memory until `pageshow`, where `event.persisted` triggers a reload (1147-1149), so the restore path is clean. No disk write was demonstrated, and the product sheet already discloses OS level traces such as swap and crash dumps (line 27). The defect is that the wipe is not the same operation on both paths, so any future path that snapshots the document (session restore, page state serialization) inherits the codes.
**checklist_item:** secrets, codes in memory and DOM, wipe completeness, gate integrity
**status:** CONFIRMED (mechanism). Retention beyond process lifetime is INFERRED and not demonstrated.

---

## F-09 Passive listener turns the expiry preventDefault into a no-op, then the drop guard skips cancel

**Severity: Low**
**file:line:** 1134, 612-623, 1110-1121
**call_path:** idle limit already reached -> user drops a file on the page -> window capture `bump` (1134) -> `event.preventDefault()` (618) is ignored because the listener is registered `passive: true` -> `endSession('timeout')` (619) -> the bubble phase `drop` listener on `document` sees `connected === false` and returns at 1112 without cancelling -> the browser default drop action runs.
**exploit_or_proof:** A passive listener cannot cancel an event; `preventDefault()` has no effect and the browser logs a warning. Because the guard at 1112 returns before `event.preventDefault()` at 1113, the default action for a dropped file, navigating the tab to that file, proceeds after the session has already been wiped. The result is that a dropped HTML file replaces the ended screen and is rendered by the browser from a local file origin. It cannot read the app origin, and the session data is already gone, so this is a UX and posture defect rather than a data leak.
**checklist_item:** drop handler, event gate integrity, wipe behavior
**status:** CONFIRMED

---

## F-10 Production `?idle=` override lets a link shorten the session to 5 seconds

**Severity: Low**
**file:line:** 430-441, 435
**call_path:** victim opens the app with `?idle=5` -> `params.get('idle')` (431) -> `IDLE_MS = 5000` (432-434) -> `checkIdle` ends the session 5 seconds after the last activity (607-610).
**exploit_or_proof:** A link can force the minimum idle limit on any session the victim starts from it. The UI does disclose the value in the intro copy (441), so it is not silent, and the victim still has to pair. The impact is a link driven session kill, or a much shorter window than the advertised 30 minutes. The comment at 436 presents this as a documented test override, and there is no production gate around it.
**checklist_item:** gate integrity, config surface, DoS
**status:** CONFIRMED

---

## F-11 CSP delivered in a meta tag cannot frame-guard, and connect-src excludes the app's own transport

**Severity: Low**
**file:line:** 6
**call_path:** page load -> meta CSP applies -> the policy contains no and cannot contain `frame-ancestors`; `connect-src 'none'` does not govern `RTCPeerConnection`.
**exploit_or_proof:** `frame-ancestors` is not supported in a `<meta>` element (https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/frame-ancestors), so an HTTPS deployment of this page can be framed and the Wipe and restart controls clickjacked. No privileged action is exposed, the clipboard write needs a gesture and cannot be read back, so impact is a forced session end. Separately, CSP3 scopes `connect-src` to fetch, XHR, EventSource, Beacon, `ping` and WebSocket, and gives RTC its own pre-connect gate (https://www.w3.org/TR/CSP3). The app proves this itself: it reaches the STUN servers at 442-445 while `connect-src 'none'` is in force. Any hardening that treats `connect-src 'none'` as an exfiltration control for the data channel or ICE is relying on a directive that does not cover either.
**checklist_item:** hardening gap, CSP posture, clickjacking, exfiltration assumptions
**status:** CONFIRMED

---

## F-12 File id is generated and never validated, reassembly is positional

**Severity: Low**
**file:line:** 898-904, 999, 1019-1036, 1038-1053
**call_path:** `sendFile` emits `{k:'file-start', id: uid(), ...}` (898-904). `beginIncoming` never reads `id` (998-1016). `addChunk` appends positionally with no correlation (1019). `endIncoming` closes whatever is current with no id check (1038).
**exploit_or_proof:** Adversarial sequence: `file-start` A with size 100, then `file-start` B with size 50000000, which is silently dropped at 999, then chunks belonging to B, which land in A's buffer and trip the overflow branch (1023-1026), then `file-end`, which finalizes A as 100 bytes and marks it bad. The receiver cannot distinguish a crossed, replayed, or misattributed sequence from a correct one. Today the sender serializes sends through `sendQueue` (872-881), so a well behaved peer cannot trigger it and a malicious peer only corrupts its own transfer. The finding is gate integrity: a correlation field exists and is dead, so any future concurrent or resumed transfer inherits silent misattribution with no validation to catch it.
**checklist_item:** framing, adversarial chunk sequences, gate integrity keyed on a name that drifted, deserialization
**status:** CONFIRMED

---

## F-13 Peer controls the saved filename including bidi controls, with no untrusted file warning

**Severity: Low**
**file:line:** 938-939, 981-983, 1046-1050
**call_path:** `file-start` supplies `name` and `type` (898-904) -> `beginIncoming` truncates to 200 and 120 characters (1006-1007) -> `createFileCard` sets `title.textContent` and `title.title` (938-939) -> `card.done` sets `save.download = title.textContent` (982).
**exploit_or_proof:** Both the displayed name and the download name are peer supplied, and `textContent` preserves Unicode bidi control characters such as U+202E, so a name ending in an executable extension can render with a reversed tail and appear to be an image or document. The blob MIME is also peer supplied (1007, 1046), so saving an HTML payload named `.html` and opening it runs it from a local file origin. There is no warning that a received file is untrusted, and the card presents Save as the normal completion action. Exploitation needs the receiver to click Save and then open the file, so this is user action gated.
**checklist_item:** file metadata to DOM, attribute values, blob URL abuse, social engineering
**status:** CONFIRMED (mechanism). Real world success depends on the receiver opening the saved file, which was not tested.

---

## Auth math, entropy and replay

The code contains no shared secret and no verifier, so there is no offline or online guessing attack to size. The connection gate is possession of the private key matching the certificate fingerprint carried in the SDP; that fingerprint is a SHA-256 hash and the certificate is ephemeral per `RTCPeerConnection`. Brute force is not the viable path, substitution through the code channel is (F-01). The ICE ufrag and pwd in the code authorize connectivity checks but are not an auth gate: an attacker holding them still cannot complete DTLS without the matching key.

Replay is possible because the code format has no nonce, session id, version, or expiry (735-745). Re-pasting a recorded invite produces a reply for a session whose PeerConnection is long gone, so the practical result is a failed connection rather than an auth bypass. Beyond that self denial, no replay impact was demonstrated. UNVERIFIED for any cross-session confusion.

---

## What V1 does right, with fail-closed proofs

**S-1 No HTML injection sink.** Zero hits for `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, `eval`, `new Function`, `DOMParser`, `srcdoc`, `createContextualFragment`. Every peer controlled string reaches the DOM through `textContent`: system text (522), messages (534), file name (938), size (942), file state (992). Attribute values are assigned as properties, not parsed markup: `title.title` (939), `save.href` and `save.download` (981-982), `img.src` (986). Attribute injection and DOM XSS are not reachable from any peer input.

**S-2 No persistence APIs.** Zero hits for localStorage, sessionStorage, indexedDB, document.cookie, serviceWorker, caches. No fetch, XHR, WebSocket, beacon, EventSource, or console logging. `endSession` revokes every blob URL, replaces the log, clears all five textareas and the file input, and disables the controls (559-582). The wipe is idempotent through the `sessionEnded` flag (555-556).

**S-3 Receiver caps size before allocating.** `beginIncoming` rejects non-finite, zero, negative, and above `MAX_FILE` sizes before `new Uint8Array(size)` (1000-1005), so one file cannot exceed 50 MB. Name and type are truncated (1006-1007). `addChunk` clamps by `room` and never writes past the buffer (1022-1029).

**S-4 Framing fails closed on stray frames.** A binary frame with no active transfer is dropped (1020). `file-end` with no transfer is a no-op (1039). A rejected transfer is cleared on `file-end` (1040-1043). Unknown or malformed code formats throw and close the peer through `fail` (735, 745, 626-631). Extra bytes past the declared size set `bad` and are not written (1023-1026).

**S-5 On-path-only MITM is blocked.** DTLS verifies the peer certificate against the fingerprint in the SDP, so an attacker who can observe but not rewrite the code cannot terminate the channel. Liveness is also transport level: ICE consent expires after 30 seconds per RFC 7675 (https://www.rfc-editor.org/rfc/rfc7675.txt), and `connectionstatechange` maps disconnect and failure to `endSession('peer')` (635-651), so a vanished peer is detected without an application heartbeat.

**S-6 Capability reduction in the policy.** `default-src 'none'`, `img-src blob: data:`, `base-uri 'none'`, `form-action 'none'`, `referrer no-referrer` (6-7). No third-party code, fonts, analytics, or assets. The only fixed network reach is two Google STUN servers (442-445). Note the `connect-src` limit recorded in F-11.

**S-7 Idle wipe is local and peer independent.** `checkIdle` runs on an interval (1136) plus `visibilitychange` (1137-1139) and `pageshow` (1147-1150), compares against `lastActivity` (607-610), and the passive activity listeners refresh it (1133-1135). A silent peer cannot keep the session alive past the limit.

**S-8 Message size is bounded on both ends.** `MAX_TEXT` truncates on send (849-850) and again on receive (830), so one message cannot be unbounded even if the other side ignores the limit.

---

## Counts

| Severity | Count | Findings |
|---|---|---|
| High | 2 | F-01, F-02 |
| Medium | 5 | F-03, F-04, F-05, F-06, F-07 |
| Low | 6 | F-08, F-09, F-10, F-11, F-12, F-13 |
| Total | 13 | |

## Top three risks

1. **F-01, silent MITM when the code channel is writable.** The product's entire confidentiality claim rests on the out-of-band channel being authentic, and nothing in the UI lets either user check. This is the highest impact because it converts the headline feature into a false sense of security, and it is the one item the engagement brief names explicitly.
2. **F-02, corrupt file exported as a completed save.** A truncated transfer becomes a zero padded blob with a live Save link, and the same path is a 50 MB amplification primitive from about 1 KB of traffic. Data loss plus memory DoS in one sequence.
3. **The inbound budget class, F-03, F-04, F-06.** Retained blobs, the stuck reject stub, and the unbounded transcript all share one missing control: no session level byte, count, or rate budget on inbound data. Any one of them can end the session for a receiver who does nothing wrong, and the stuck stub does it with a single message.

---

## SELF-CHECK

Re-read the file at the end of the run, re-ran every mechanical check, and re-verified each cited source line against the app.

| # | Acceptance item | Result | Evidence |
|---|---|---|---|
| 1 | Output at `/Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/01-research/output/02-audit-findings.md` | PASS | `write_file` verified true; file is 23846 chars, 214 lines before this section. |
| 2 | One block per finding with title, severity, file:line, call_path, exploit_or_proof, checklist_item, status | PASS | Script check: 13 `F-` headings, and `file:line:`, `call_path:`, `exploit_or_proof:`, `checklist_item:`, `status:` present in all 13; no missing field reported. |
| 3 | Call path from a real entry point, or cut or marked unverified | PASS | All 13 map to E1 to E6 in the entry point table: F-01 E4/E5, F-02 E1, F-03 E1, F-04 E1, F-05 E4/E5, F-06 E1/E3, F-07 E4, F-08 E6, F-09 E2, F-10 load path, F-11 load path, F-12 E1, F-13 E1. Nothing in the report lacks a path. The replay note is explicitly UNVERIFIED and is not counted as a finding. |
| 4 | Counts by severity and top three risks | PASS | Counts section: High 2, Medium 5, Low 6, total 13, matching the per-block severities in the script check. Top three section names F-01, F-02, F-03/F-04/F-06. |
| 5 | Severity by real impact, not by bug class | PASS | Data loss and auth bypass are High. DoS and the network primitive are Medium. Posture and user action gated items are Low. F-02 is High because it produces a saveable corrupt file, not merely because it allocates. |
| 6 | Checklist coverage | PASS | Injection and DOM: S-1 plus F-13. Deserialization and framing: F-02, F-05, F-12, S-4. DoS, chunk flooding, rate, oversized blob, main thread: F-03, F-04, F-05, F-06, F-02. Auth, entropy, brute force, replay, MITM, ICE injection: F-01, F-07, and the Auth math section. Secrets in memory, DOM, console, clipboard: F-08, S-2, S-8 note on no console output, `copyText` 1060-1074 is gesture gated. Gate integrity on flags and names: F-04 (`reject`), F-09 (`connected` and passive), F-12 (dead `id`), F-10 (URL flag). |
| 7 | What V1 does right, with fail-closed proofs | PASS | S-1 through S-8, each tied to file:line or to a re-run grep whose result is stated. |
| 8 | English, no em dashes or en dashes | PASS | U+2014 count 0, U+2013 count 0. The whole file is ASCII, non-ASCII set empty. |
| 9 | App claims carry file:line, external claims carry a verified URL | PASS | Every app assertion cites a line range. External claims: RFC 8827 section 7 text verified at https://www.rfc-editor.org/rfc/rfc8827.txt; RFC 8445 section 2.2 verified at https://www.rfc-editor.org/rfc/rfc8445.txt; RFC 7675 30 second consent expiry verified at https://www.rfc-editor.org/rfc/rfc7675.txt; CSP3 connect-src scope and the RTC pre-connect gate verified at https://www.w3.org/TR/CSP3; frame-ancestors meta restriction verified at https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/frame-ancestors. |
| 10 | Findings only, no fixes | PASS | No remediation section and no patch. F-11 names the directive scope as analysis, not as a change. |
| 11 | No writes outside the output file | PASS | Only this file was written. The compression ratio and typed array checks ran in the scratch directory with no repo writes, and `input/` was read only. |
| 12 | Numbers are measured or labelled | PASS | Gzip ratio 1025.9 to 1 measured with zlib level 9 on 10 MB of zeros (10221 bytes), 1 MB measured at 1051 bytes. The 769 MB and 3847 MB expansions are arithmetic on that measured ratio and are stated as such. No OOM threshold is claimed. |

Claims deliberately not made: no XSS in the app origin, no RCE in the app origin, no disk write from `pagehide`, no successful live MITM, no packet capture for F-07, no cross-session replay impact. Each of those is either excluded by S-1 and S-2 or labelled INFERRED/UNVERIFIED in the block where it appears.

Stage level note: the stage acceptance also runs `ls output/0*.md | wc -l` expecting 7. At the time this lane finished the directory held 6 files (02, 03, 04, 05, 06, 07), with this lane's file present and the remaining lane still landing. The dash grep over `output/` and the `grep -L SELF-CHECK` check were run against this file and pass; the full directory verdict belongs to the lead after all seven land.


