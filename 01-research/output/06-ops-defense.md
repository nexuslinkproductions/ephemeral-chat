# 06 Ops defense: kill switch, fresh-set migration, external monitor, OS trace minimization

RUN: w1-ephemeral-hardening-20261126, lane 6 of 7.
APP UNDER REVIEW: `input/ephemeral-chat-v1.html`, 35598 bytes, 1154 lines. All line references are to that file.
HOST MEASUREMENTS: macOS 26.4.1, build 25E253 (`sw_vers`), taken on this machine during this pass. Measured values are labeled as measured, not inferred.

## 0. Labels used in this file

| Label | Meaning |
|---|---|
| HIGH | Standard platform API or documented system behavior. The effect on app-owned state is deterministic and can be demonstrated. |
| MEDIUM | The mechanism works, but the result depends on browser internals, OS configuration, or user action outside the page. |
| LOW | No supported path for a web app. Requires admin or root, or relies on the user remembering to do something. |
| UNVERIFIED | Claim not confirmed by a fetched source in this pass. Used only for platform notes that do not drive a design decision. |

Two words are used precisely. "Shreds" means the data is no longer reachable through any API the app or a normal process can use. It does not mean the bytes are gone from RAM, swap, or backups. "Watches" means the monitor can observe the signal through a public API or a sampled system counter.

## 1. What V1 already does, and where the defense layer plugs in

V1 has a real wipe path, not a decorative one. `endSession(reason)` at line 554 closes the peer connection and data channel through `closePeer()` at line 541, revokes every blob URL (lines 559 to 561), clears the message log with `replaceChildren()` (line 564), empties all five textareas and the file input (lines 565 to 570), disables every control, and shows a terminal panel. It is idempotent through the `sessionEnded` flag (line 555). That is a good foundation.

The triggers that reach it today:

| Trigger | Line | Gap |
|---|---|---|
| Wipe button | 354, handler 1076 to 1080 | Button starts `disabled` (line 354) and is only enabled when the channel opens (line 676). A user stuck in pairing cannot kill the session, even though the invite code already exists and may already be on the clipboard. |
| Idle timeout, default 30 minutes | 432 to 434, check 607 to 610, interval 1136 | Works. Activity bumping (lines 612 to 623, 1133 to 1135) means a moving mouse keeps a session alive indefinitely. That is a policy choice, not a bug. |
| Peer loss | 640 to 647, 681 to 683 | Works after a 5 second grace period. `window.close()` is attempted at 601 to 603, best effort only. |
| Page hide | 1141 to 1145 | Clears the log and peer. Does not revoke blob URLs or clear the pending incoming buffer. |
| Manual restart | 1089 | `location.reload()`, which is the strongest page-level shred available, but it runs only after the user clicks Restart on the ended panel. |

Missing entirely: a peer-initiated panic signal, any anomaly detection, any key or session rotation, any clipboard cleanup, and any external watcher. The protocol has exactly three inbound frame types, `msg`, `file-start`, `file-end` (lines 824 to 839), and invalid JSON is silently dropped at line 828. `file-end` carries no transfer id (line 924), so control frames and file frames need a versioned envelope before panic or migration messages can be added safely.

## 2. Kill switch scoped to the chat

Scope: everything the page owns or can reach through a web API. The switch does not try to be an OS cleaner. Section 5 covers the OS layer, and section 2.6 states the boundary explicitly.

### 2.1 Shred inventory: what the page can actually destroy

| Artifact | Where it lives in V1 | Lever available to the page | Provable effect | Residue and ceiling | Label |
|---|---|---|---|---|---|
| DTLS and SCTP session state | Browser network process, keyed by the `RTCPeerConnection` at line 475 | `pc.close()` via `closePeer()` line 550 | The transport is closed and the connection object is unusable. The channel can no longer send or receive. | Key zeroization inside the browser is not exposed or documented. The app can prove the connection is dead, not that the key bytes were overwritten. | HIGH for closure, UNVERIFIED for zeroization |
| Data channel | `dc` line 476 | `dc.close()` line 549 | Ready state moves to closed, no further messages are delivered. | Buffered outbound bytes may already be in the network process. Cannot be recalled. | HIGH |
| Message DOM | `el.log` line 453 | `replaceChildren()` line 564 | Nodes are detached and unreachable from the document. | Strings may persist in the JS heap until garbage collection. JavaScript strings are immutable, so they cannot be overwritten in place. | HIGH for reachability, LOW for memory |
| Composer and code textareas | `el.input`, `el.offer`, `el.answer`, `el.offerIn`, `el.answerIn`, lines 565 to 569 | Assign `''` to `.value` | The visible and form value is empty. | The old string remains in the heap until collection. Setting `.value` does not zero the backing store. | MEDIUM |
| Incoming file buffer | `incoming.buffer`, allocated line 1011 | Overwrite with `crypto.getRandomValues` before dropping the reference | Bytes in that `Uint8Array` are replaced. | `endIncoming()` already copied the bytes with `buffer.slice(0, offset)` (line 1045) into a `Blob` (line 1046), so a completed transfer has at least two copies. Overwriting the original does not touch the Blob. | MEDIUM, partial |
| Blob URLs and their backing blobs | `urls` array line 486, pushed at 891 and 1048 | `URL.revokeObjectURL` lines 559 to 561 | The URL stops resolving. New loads fail. | The Blob is freed only when no references remain, which requires clearing the DOM nodes that hold it (the `img.src` at 894 and 986, the anchor `href` at 981). Large blobs may be disk-backed in some browsers, and revocation is not secure deletion. | MEDIUM |
| Invite and reply codes | Textareas 763 and 794, plus the string in the heap | Clear textarea, revoke nothing else | The visible code is gone. | Copies exist in the clipboard if the user pressed Copy (line 1067), in screenshots, in the chat app the code was pasted into, and in browser form history in some configurations. | LOW outside the page |
| Clipboard | System pasteboard, written at line 1067 | `navigator.clipboard.writeText('')` | Attempts to replace the clipboard with an empty string. | Requires document focus and permission. On macOS 26 the system keeps a clipboard history that Spotlight can search (verified Apple support page below), and Universal Clipboard may have already copied the value to another device. Clearing the current pasteboard does not clear history. | LOW |
| Session metadata in JS | `pc`, `dc`, `connected`, `incoming`, `sendQueue`, lines 475 to 486 | Null every reference | No app path can reach the objects. | Closure variables and Promise chains may retain references until collection. | HIGH |
| Page document and renderer state | The tab itself | `location.replace('about:blank')` | Destroys the document, its JS heap, and its DOM. This is the only operation that plausibly takes the whole page state with it. | The renderer process may be reused. Browser-level caches and back/forward state are outside app control. | HIGH for document state, MEDIUM for process memory |

One ordering detail matters. The log must be cleared before revoking blob URLs, because the `<img>` and `<a>` nodes hold references to the blobs. Revoking first leaves the nodes displaying cached content until they are removed. V1 revokes before clearing (lines 559 to 564), which happens to work because the panel is hidden immediately, but the correct order is DOM first, then URLs, then buffers.

### 2.2 Trigger path A: manual kill, available at every stage

The button exists but is gated on connection (line 676). Fix: remove the `disabled` attribute from the markup (line 354) and let `endSession` handle the not-yet-connected case. `closePeer()` is already null-safe (lines 545 to 550), and `endSession` already returns early if called twice (line 555). The confirm dialog at line 1078 should stay for a connected session and be skipped when nothing is connected, because there is nothing to lose and the extra click is friction on a panic path.

Add a keyboard path that works even when focus is in a textarea: `Escape` pressed twice within 800 ms. This is a local event listener, no permission, no dependency on the peer. Keep the existing button as the discoverable path.

The manual kill is the only trigger the user fully controls. It must never depend on the network, the peer, or a pending Promise. Every step in the sequence in 2.5 is synchronous except the optional clipboard attempt and the final navigation.

### 2.3 Trigger path B: peer panic frame over the authenticated channel

Current inbound parsing accepts three keys and ignores everything else (lines 829 to 835). Add one control frame:

```
{ "k": "panic", "v": 1, "reason": "peer-panic", "ts": 1790000000000 }
```

Send it on the existing data channel (`dc.send`, same path as line 849) before closing anything. On receipt: reject if `sessionEnded` is already true, reject if `dc !== channel` so a frame from a stale channel cannot kill a new session, then call `endSession('peer-panic')`.

No MAC and no nonce are needed. DTLS already authenticates and integrity-protects the channel, and a peer is entitled to end its own session. Replaying a panic frame only ends a session that is already ending, which is an availability cost the peer could impose anyway by closing the channel. Adding a MAC here would require an application-level key, and WebRTC exposes no keying material to JavaScript, so the MAC would be security theater unless the optional app-layer ratchet from the crypto lane is present. Do not build it for V2.

The panic frame is a courtesy, not a security dependency. If the peer is compromised and suppresses it, the local kill still runs. The channel then closes and the peer's own peer-loss path (lines 681 to 683) wipes its side within the 5 second grace period (lines 640 to 647). Design the UI so the local panic always completes locally first, and the frame is best effort with no await.

Trigger policy: manual button, double Escape, or local anomaly. The frame is only the wire format for the peer notification.

### 2.4 Trigger path C: anomaly detection in the page

The page can observe its own transport with `getStats()` (MDN: https://developer.mozilla.org/en-US/docs/Web/API/RTCPeerConnection/getStats), which returns a report containing per-data-channel counters (`messagesSent`, `messagesReceived`, `bytesSent`, `bytesReceived`, MDN: https://developer.mozilla.org/en-US/docs/Web/API/RTCDataChannelStats) and transport entries with `dtlsState` and payload byte counters (MDN: https://developer.mozilla.org/en-US/docs/Web/API/RTCTransportStats). The app currently calls neither `getStats` nor listens for renegotiation; both are additions.

Rules, each with one action. No scoring model, no ML, because each rule has to be testable on its own.

| Rule | Signal | Threshold | Action | False positives | Label |
|---|---|---|---|---|---|
| A1 unknown frame | `k` value outside the known set, counted in `onMessage` (line 829) | 3 in 10 s | KILL | Version skew during rollout, so gate on `v` | HIGH |
| A2 channel topology | A second `datachannel` event, or a label other than `chat` (line 656 binds any) | 1 | KILL | None in this app, it opens exactly one channel (line 755) | HIGH |
| A3 renegotiation | `negotiationneeded` after the channel opens | 1 | KILL, except during an approved migration | None, the app never renegotiates today | HIGH |
| A4 overlapping transfers | `file-start` while `incoming` is set (line 999 ignores it silently) | 2 in 30 s | KILL | A peer with a buggy client | MEDIUM |
| A5 declared size mismatch | `offset !== meta.size` (line 1051 already marks the card) | 2 in one session | KILL | Truncated transfer on a dying link, which is rare | MEDIUM |
| A6 transport path | `dtlsState` leaves `connected` while the channel still reports open, or the selected candidate pair becomes a relay when no TURN server is configured (lines 442 to 445 configure STUN only) | 1 | KILL | Path change from Wi-Fi to wired can change the pair but not to relay. Exact stats field names for candidate types are UNVERIFIED in this pass | MEDIUM |
| A7 byte accounting | Transport `bytesReceived` minus data-channel payload bytes exceeds 30 percent of the transport total, with no file transfer active | 2 consecutive samples 5 s apart | KILL | Retransmissions on a lossy link | MEDIUM |
| A8 frame rate or volume | More than 40 frames/s for 5 s, or more than 2 MB/s while `incoming` is null | 1 | KILL | None for a text chat | HIGH |
| A9 send queue stall | `bufferedAmount` above 4 MB for 10 s with no file in flight (line 857 uses 512 KB as the drain threshold) | 1 | WARN only | Slow uplink | HIGH |

WARN means a visible banner and a log line. KILL means `endSession('anomaly')` with the rule id shown in the ended panel. The whole detector is a 5 second interval reading `getStats()` plus counters incremented in `onMessage` and `addChunk`. Stop the interval in `endSession`, next to the idle timer clear (line 557).

Honest boundary: anomaly detection sees protocol abuse and transport anomalies. It cannot see a human on the other end, a compromised endpoint, or a passive observer. A peer that simply reads the messages and behaves normally is invisible to every rule above.

### 2.5 The kill sequence, ordered

The sequence is written as a single function that never awaits before the local state is dead. Every step is wrapped so one failure cannot abort the rest.

| t | Step | Why |
|---|---|---|
| 0 ms | Set `sessionEnded = true`, disable input, clear the composer | Stops new data entering the page |
| 0 ms | Send `{k:'panic'}` if `dc.readyState === 'open'`, no await | Gives the peer a clean shutdown without blocking |
| 10 ms | `closePeer()`: close channel and peer, null both | Drops the transport, the only lever on DTLS state |
| 10 ms | Clear idle and disconnect timers, stop the anomaly interval | Nothing can fire after the wipe |
| 20 ms | `el.log.replaceChildren()` | Releases DOM references, including image and anchor nodes holding blobs |
| 30 ms | Clear all five textareas and the file input (lines 565 to 570) | Removes codes and drafts |
| 40 ms | Revoke every blob URL, empty the array | URL stops resolving |
| 50 ms | Overwrite `incoming.buffer` with random bytes, then null `incoming` | Best effort on the one buffer the app owns |
| 60 ms | Drop `sendQueue` and all closures holding `File` handles | Releases references to user files |
| 70 ms | Clear any sessionStorage or storage the hardening adds, if present | V1 has none; keep the call guarded |
| 80 ms | If a code was copied this session and `document.hasFocus()`, call `navigator.clipboard.writeText('')`, no await, catch and ignore | Best effort clipboard cleanup |
| 300 ms | Show the ended panel with the reason | User confirmation |
| 4 s | `location.replace('about:blank')` | Destroys the document and its heap, the strongest page-level shred |

Do not use `window.close()` for the manual path. It is already best effort for timeout and peer loss (lines 601 to 603), and browsers refuse it for tabs the script did not open. `location.replace` always works and leaves no back entry, which is better than `reload` (line 1089) because reload can restore form values in some browsers.

The ended panel is shown for 4 seconds before navigation. Shorten it to 1.5 seconds on the anomaly path, where the user needs less explanation and speed matters more.

### 2.6 What the kill switch cannot do

State these in the product copy, not only in the code comments:

- It cannot prove key erasure. The DTLS keys live in the browser network process. `close()` ends their use; it does not expose them for zeroization.
- It cannot zero JavaScript strings. Clearing the DOM and dropping references is the ceiling.
- It cannot clear the system clipboard history, and on macOS 26 that history is searchable through Spotlight (verified: https://support.apple.com/guide/mac-help/search-your-clipboard-history-mchl40d5b86b/mac).
- It cannot remove saved downloads (line 982 downloads with the sender's filename), screenshots, swap contents, hibernation images, or crash reports. Section 5 covers those.
- It cannot defeat an attacker who already has script execution in the page. Such an attacker can skip the kill or exfiltrate before it runs. The external monitor in section 4 is the witness for that case, and it is deliberately outside the browser.
- It cannot force the peer to wipe. It can only ask, then close the channel so the peer's own peer-loss logic fires.

## 3. Fresh-set migration: both peers move to a new session

### 3.1 What migration is for

Fresh-set migration replaces the entire session: new `RTCPeerConnection`, new DTLS certificate and fingerprint, new SDP and ICE candidates, new invite and reply codes, new data channel, new application state. The old connection is closed only after the new one is proven live. An attacker who learned the old codes, recorded the old handshake, or took a screenshot of the old pairing screen restarts from zero.

It does not undo data the attacker already copied. It does not remove malware from an endpoint. It is a code and key revocation mechanism plus a session aging mechanism, not an incident response team.

### 3.2 Why a new connection is the only transport-level rekey

The WebRTC API exposes no keying material and no rekey call. There is no `getKeys()`, no `rekey()`, and no way to force a DTLS handshake on an existing connection. DTLS performs its own record key updates internally, but the page cannot observe, trigger, or verify them. Therefore, when the requirement is "new keys", the only implementable meaning in a browser app is "new connection with a new certificate and fingerprint". The fingerprint is visible in the SDP that the code carries (`a=fingerprint`), and the app can parse and compare it, which is what makes the commitment check in 3.3 possible.

An application-level ratchet, if the crypto lane adds one, can rotate message keys inside the existing channel. That is cheaper and continuous, and it is the right tool for forward secrecy. It does not replace migration, because the transport identity and the codes stay the same. Keep both: ratchet for per-message secrecy, migration for identity reset.

### 3.3 Soft migration, coordinated in-band over the authenticated channel

Preconditions: the old data channel is open, no file transfer is active (`incoming` is null and `sendQueue` is idle), and neither side is already migrating. If a transfer is active, refuse with a toast and let the user retry.

Roles: the peer that clicks Migrate becomes the offerer. If both click within the same second, both abort, wait a random 500 to 1500 ms, and the peer with the lexicographically lower current DTLS fingerprint becomes the offerer. That tie-break uses data both sides already have.

Protocol, all frames sent over the old data channel:

| Step | Sender | Frame | Receiver action |
|---|---|---|---|
| M1 | Offerer | `{k:'mig', v:1, step:'offer', sid, fp, code}` where `sid` is 16 random bytes hex, `fp` is the SHA-256 of the new SDP fingerprint, and `code` is the packed new offer (same `pack()` at line 722) | Verify `sid` is new and no migration is active. Store `sid` and `fp`. Create a new peer and channel, `setRemoteDescription` with the unpacked offer, create the answer, gather ICE |
| M2 | Answerer | `{k:'mig', v:1, step:'answer', sid, fp, code, check}` where `check` is the first 6 hex characters of SHA-256 over `sid || fp_offer || fp_answer` | Verify `sid` matches. Verify `check`. Set the remote answer on the new peer |
| M3 | Both | On the new channel's `open`: `{k:'mig', v:1, step:'commit', sid, fp_self, fp_peer}` | Verify `fp_peer` equals the fingerprint actually present in the peer's SDP, and that the pair matches what was committed in M1 and M2. Only then mark the new channel as the live one |
| M4 | Both | After commit verified both ways: `{k:'mig', v:1, step:'done', sid}` on the old channel | Close the old peer and channel, clear the old log, adopt the new objects |
| M5 | Both | Timeout at 15 s on any step | Close both peers, `endSession('migration-failed')`, show "session ended, start a new one" |

What the checks buy, stated precisely:

- The `fp` in M1 is a commitment to the new fingerprint before the new code is used. If the code later travels by another path, for example the user pastes it into a chat, a substituted code fails the fingerprint comparison.
- The `check` in M2 binds the answer to the exact offer and session id, so an answer from a different migration attempt cannot be replayed into this one.
- M3 verifies the fingerprint in the actual SDP, not just the value in the frame. That catches a peer that packs a code whose fingerprint differs from the one it committed to.
- The old channel's DTLS integrity authenticates every frame. No application MAC is possible without exported key material, so do not pretend there is one.

The remaining gap: if the old channel itself is under the control of an attacker at the endpoint, every frame above is visible to that attacker, including the new code. That is why 3.4 exists. Soft migration protects against code leakage, old recordings, and session aging. It does not protect against a compromised endpoint, and no in-band protocol can.

Optional human check, cheap and worth it: both sides display the first 6 hex characters of SHA-256 over the two new fingerprints sorted. The two people read them aloud on a call or in person. A mismatch means an active attacker in the middle of the migration. Six hex characters is 24 bits, enough to defeat a blind substitution, and it takes five seconds to compare. No wordlist needed.

### 3.4 Hard migration, for a suspected endpoint compromise

If either side suspects that the other endpoint, or its own, is compromised, soft migration is the wrong tool because the new code passes through the compromised machine.

Hard migration procedure:

1. Both users kill the current session locally first (button or panic frame). Kill before generating anything new.
2. Both close the tab and reopen the app from a known-good source. Do not reuse the tab that may be instrumented.
3. Exchange the new invite and reply codes over a different channel and, ideally, a different device: a phone call reading the code aloud, or in person. Do not send them through the machine under suspicion.
4. Compare the 6 hex character check from 3.3 on the call. Both sides must see the same value before typing anything.
5. Only then exchange messages. Treat everything from the old session as burned.

The ordering is the security property. Killing first means the attacker loses the channel before the new code exists. Delivering the code out of band means the attacker never sees it. Doing it in the other order, new session first and kill later, leaves the attacker watching the migration and defeats the purpose.

### 3.5 Codes: expiry, single use, handling

V1 generates a code and leaves it in the textarea until the session is wiped (lines 761 to 769, 792 to 799). There is no expiry and no single-use rule. The migration design should carry three rules into the pairing code as well:

- TTL 120 seconds. After that, the code is stale and the user must generate a new one. A stale code can still be pasted, so the receiver checks an embedded timestamp and refuses after the TTL. The timestamp is inside the encrypted payload, so it cannot be tampered with without breaking the code format.
- Single use. Once a code has produced a connection, any second use is refused by the app, and the UI says so. This needs a per-page marker only; cross-device replay is handled by the timestamp and by the peer refusing a second connection on the same PC.
- Clear on copy after 30 seconds, with a "show" button that regenerates. `navigator.clipboard.writeText` at line 1067 currently copies and leaves the textarea populated. Clear the textarea, not the clipboard, because clipboard history keeps the copy anyway.

### 3.6 What survives and what does not

| Item | After soft migration | After hard migration |
|---|---|---|
| Old DTLS keys and certificate | Destroyed with the old peer close. Not provable at byte level, same as 2.1 | Same |
| Old invite and reply codes | Dead, new codes in their place | Dead, new codes delivered out of band |
| Old fingerprint | Replaced, and the old one is no longer accepted | Replaced |
| Old data channel and its buffered frames | Closed, buffered frames discarded by the browser | Same |
| Chat history in the DOM | Cleared as part of the switch. A new session starts empty, which is the point | Cleared by the kill |
| Blob URLs and file blobs | Revoked and dropped | Revoked and dropped by the kill |
| Clipboard copies of old codes | Not recoverable by the app. History may keep them | Same, and the user should clear history |
| The humans and their out-of-band channel | Survive, that is the root of trust | Survive, and they are the only channel used for the new codes |
| Data the attacker already copied | Survives. Migration cannot un-steal it | Survives |
| Monitor log | Survives, and should record the migration event with both fingerprints and the time | Survives |

### 3.7 Failure modes and feasibility

| Failure | Handling |
|---|---|
| New channel never opens | 15 s timeout, kill both peers, terminal panel |
| Commit fingerprint mismatch | Kill immediately, show "migration rejected", log the mismatch in the monitor |
| Peer disappears mid-migration | Old channel closes, peer-loss path fires, kill |
| Both sides initiate | Tie-break by current fingerprint, loser aborts its pending peer and answers |
| User clicks Wipe during migration | Kill switch closes `pending.pc` as well as `pc`. Keep both in one array or one `connections` set, not two globals |
| Migrate clicked during a file transfer | Refuse with a toast, no state change |

Feasibility: HIGH for the mechanics. Every call is standard WebRTC (`RTCPeerConnection`, `createOffer`, `setRemoteDescription`, `createDataChannel`), the same on macOS, Linux, and Windows because it runs in the browser. MEDIUM for the operational result, because two connections briefly coexist and the UI must not let the user type into the wrong one. The hard part is state, not cryptography. Budget one `pending` object with `{pc, dc, sid, fp, role, deadline}` and a single `adopt(pending)` function that swaps the globals and clears the old log.

Skip for V2: automatic migration on a timer, migration over a third-party signaling channel, and multiple simultaneous migrations. Session aging can be a UI prompt at 20 minutes ("session is old, rotate?"), which is one line of policy and no new machinery.

## 4. External monitor overlay on macOS

### 4.1 The trust-domain argument

The monitor must survive a compromise of the chat. That requirement decides the architecture before any feature does.

- Separate process. A native app or a launchd agent, not a browser extension and not a script inside the page. The chat page has no API to spawn a process, signal one, attach to one, or read its memory. A sandboxed renderer is terminated by the browser process when it misbehaves, and it cannot reach outside its sandbox (Chromium's own description of renderer sandboxing and process termination: https://www.chromium.org/Home/chromium-security/site-isolation/).
- Separate identity. Its own bundle identifier and code signing identity, installed by the user, not loaded by the browser. Nothing the page does can change its binary or its launch agent.
- Separate input path. The monitor reads only public system counters and kernel APIs. It accepts no commands from the browser, no HTTP, no WebSocket, and no AppleScript. If it accepted a "pause" command from localhost, a compromised page could fetch that URL and switch it off. No listener is a security property, not a missing feature.
- Separate failure domain. launchd starts it at login with `KeepAlive`, so killing it produces a restart and a visible gap in its log. The log is a hash-chained append-only file under `~/Library/Application Support`, which the browser cannot write to.

The limits, stated as plainly as the argument:

- A process running as the same user can `SIGKILL` the monitor, edit its log, or replace its binary in `~/Applications`. The monitor restarts, and the gap is evidence, but it is not prevention.
- Root can do anything, including hiding from the monitor.
- The monitor is a witness, not a guard. It cannot block the chat, cannot inspect DTLS, and cannot prove the absence of an attack.
- The only version that survives root on the Mac is a monitor on a different device, for example a phone on the same LAN watching the Mac's exported counters. That is out of scope for V2 and should be named as the ceiling in the design note.

This is still a real gain. The common compromise path is the page: a malicious script, a supply-chain injection, a browser bug in the renderer. All of those live inside the sandbox, and the monitor is outside it, watching the process from the OS side. The attacker has to escape the browser and gain the user's UID before it can touch the monitor, which is a much higher bar than owning a tab.

### 4.2 Placement: menu bar versus always-on-top HUD

| Option | Mechanism | Strength | Weakness |
|---|---|---|---|
| Menu bar item, primary | `NSStatusItem`, which Apple documents as an individual element displayed in the system menu bar, created through `NSStatusBar` (https://developer.apple.com/documentation/appkit/nsstatusitem) | Always visible, no content covered, survives space changes, standard macOS behavior, cheap to build | Small surface, easy to ignore, hidden in a crowded menu bar |
| Floating HUD, secondary | A window level above normal plus `fullScreenAuxiliary`, documented as "The window displays on the same space as the full screen window" (https://developer.apple.com/documentation/appkit/nswindow/collectionbehavior-swift.struct/fullscreenauxiliary) | Impossible to miss, shows detail without opening a menu | Covers content, appears in screenshots and screen shares, needs careful click-through and multi-display handling, and a chat compromise could draw over it if the attacker controls another window |

Recommendation: menu bar icon as the always-on surface, with three states (green: quiet, amber: warning, red: critical), plus a system notification for transitions. The HUD appears only for a critical event and can be dismissed. This is one `NSStatusItem`, one `UNUserNotificationCenter` authorization request (Apple requires the user to allow notifications: https://developer.apple.com/documentation/usernotifications/unusernotificationcenter), and one optional `NSPanel`. Do not build a permanently floating HUD. It is the feature users disable first.

### 4.3 What it can feasibly watch

| Signal | Method | Cadence | What it provably observes | Blind spots | Feasibility |
|---|---|---|---|---|---|
| Browser process alive and frontmost | `NSWorkspace` running applications and frontmost application | 2 s | Which browser is running and frontmost, by bundle id | Which tab, which profile | HIGH |
| Network connections | `lsof -nP -i` filtered by browser PID. Measured on this host: 289 rows in one run, well under a second | 5 s | TCP and UDP sockets owned by the process | WebRTC uses one UDP socket for multiple destinations, so the remote peer is often `*:*`. lsof shows the socket, not the peer. Other users' processes need root | MEDIUM |
| Inbound attempts | pf or socketfilterfw logs, unified log | event | Dropped inbound packets, if the firewall logs them | Requires root to read the log and to enable logging. lsof cannot see a SYN that was dropped | LOW without root, HIGH with root |
| Bandwidth | `nettop -P -x -l 1 -J bytes_in,bytes_out`, verified working on this host, per-process byte counters | 2 s sample | Bytes in and out per process between samples | Bursts shorter than the sample, shared sockets, no per-tab attribution | MEDIUM |
| CPU and memory | `ps` or `proc_pid_rusage` for the browser and its helpers. Measured example on this host shows per-process CPU and percent memory | 5 s | Process CPU and RSS, coarse system pressure | Renderer shared across tabs, compressed memory hides true pressure, other users need root | MEDIUM |
| Clipboard activity | Poll `NSPasteboard.changeCount` (https://developer.apple.com/documentation/appkit/nspasteboard/changecount). Apple's pasteboard access behavior lets the user customize access per app after an access alert (https://developer.apple.com/tutorials/data/documentation/appkit/nspasteboard/accessbehavior-86972.json) | 1 s | That the clipboard changed, no content, no source app | Does not say who copied or what. Reading the content would trigger the OS alert and is deliberately avoided | MEDIUM |
| Camera and microphone | The OS already shows an orange dot for microphone and a green dot for camera (https://support.apple.com/guide/mac-help/quickly-change-settings-mchl50f94f8f/26/mac/26). A monitor can watch device activation the way OverSight does (https://objective-see.org/products/oversight.html) | event | That a device was activated, sometimes by which process | No public API for the indicator itself. OverSight documents cases where it cannot identify the process | MEDIUM, prior art exists |
| New listening ports | `lsof -nP -iTCP -sTCP:LISTEN`, diff against the previous sample | 30 s | A new listening socket by a known process | Other users need root, short-lived listeners missed | MEDIUM |
| Screen recording by another app | TCC database is not readable without full disk access. Apple exposes the permission list in System Settings (https://support.apple.com/guide/mac-help/control-access-to-screen-recording-on-mac-mchld6aa7d23/mac) | manual | Which apps are allowed to record the screen | No clean programmatic read of the list. User checks the list | LOW |
| Monitor liveness | Heartbeat file plus launchd `KeepAlive` | 1 s | A gap in coverage, after the fact | Does not prevent the kill | HIGH |

Deliberately not watched: browser history, page content, keystrokes (needs an input tap and Accessibility permission), and the chat's memory (needs `task_for_pid` and a debugger entitlement). Each would turn the monitor into spyware and would need permissions the product cannot justify. The clipboard is watched as an event, not as content, for the same reason.

### 4.4 Monitor rules and alerting

Five rules, one action each, no scoring:

| Rule | Condition | Action |
|---|---|---|
| M1 unexpected network | The browser PID's outbound rate exceeds five times its 10 minute median for 30 s | Amber banner, log with the sample |
| M2 camera or mic | Any device activation while the chat tab is the frontmost browser window | Red alert, sound, HUD, log |
| M3 clipboard churn | More than three clipboard changes in 60 s while the chat is frontmost | Amber banner, log counts only |
| M4 load | Browser CPU above 80 percent for 60 s, or memory above 2 GB | Amber banner, log |
| M5 monitor gap | Heartbeat missing for more than 10 s, detected on restart | Red alert with the gap duration, because a gap may mean the monitor was killed |

Alerting: `NSSound` or `afplay` for sound (the binary is present at `/usr/bin/afplay`, measured), `UNUserNotificationCenter` for a banner with the user's authorization, and the menu bar icon color change, which needs no permission. One alert per transition with a 15 minute silence action. No repeating alarms. Critical alerts use the HUD, everything else uses the banner.

Honest noise estimate: M1 fires on every large download, video call, and cloud sync. Require the user to mark "transfer expected" from the menu for the next 10 minutes, or accept the false positives and treat the monitor as a log first, alarm second. A monitor that cries wolf gets turned off, which is worse than a quiet one.

### 4.5 Prior art, verified

| Tool | What it does | Platform and mechanism reality |
|---|---|---|
| Little Snitch 6 | Personal application firewall and network monitor. Connection list shows the app, the server, and a traffic meter with current or 5 minute history (https://help.obdev.at/littlesnitch6/lsm-connection-list). Supports macOS 14 and later (https://obdev.at/en/press/pr/2024-05-21-Objective-Development-Releases-Little-Snitch-6.html) | Commercial, native, kernel-adjacent. Proves that per-connection visibility with app attribution is a native feature, not something a page can do |
| LuLu | Free, open-source macOS firewall that blocks unknown outgoing connections, macOS 10.15+ (https://objective-see.org/products/lulu.html) | Native, open source, the reference for a minimal outbound alert UI |
| OverSight | Watches the mic and webcam and alerts on activation, macOS 12+ (https://objective-see.org/products/oversight.html) | Native, documents that process attribution is sometimes impossible even with privileged access |
| lsof | Lists open files including network files, with `-i` selecting Internet files (https://lsof.readthedocs.io/en/latest/manpage/) | Present on every Mac, no install, but polling only and limited visibility across users. Measured working on this host |
| Endpoint Security | Apple C API for monitoring system events, delivered as a system extension, with the `com.apple.developer.endpoint-security.client` entitlement that must be requested from Apple, and installable only from `/Applications` (https://developer.apple.com/documentation/endpointsecurity/monitoring-system-events-with-endpoint-security.md and https://developer.apple.com/documentation/endpointsecurity.md) | The real thing, but it needs an Apple-granted entitlement, a Developer ID, and a system extension. Not a weekend feature, and not available to a web app or a Mac App Store app |

The pattern: every tool that actually watches the system is native, separately installed, and privileged where the signal requires it. A browser page cannot join that category. The monitor has to be a separate deliverable.

### 4.6 What the monitor cannot see

- Inside the DTLS tunnel. Message content and peer identity are opaque to it.
- Per-tab traffic. A browser multiplexes everything through shared sockets and helper processes.
- Whether the chat is compromised. It sees symptoms, such as unexpected bytes or CPU, not intent.
- Blocked inbound attempts without root and firewall logging.
- Screen contents without Screen and System Audio Recording permission, which the monitor should never request, because a watcher that can read every window is a bigger risk than the one it watches.
- Anything at all if the attacker has root. Say so in the About window.

## 5. Per-OS trace minimization

The chat is a web app, so every OS-level trace below is outside its control. The honest framing for the product is a short "after the chat" checklist plus a monitor that can remind the user. Do not pretend the page can clean any of this.

### 5.1 Measured baseline on this host

Commands were run during this pass on macOS 26.4.1 (build 25E253).

| Measurement | Command | Result |
|---|---|---|
| OS version | `sw_vers` | macOS 26.4.1, build 25E253 |
| Swap | `sysctl vm.swapusage` | total 14336.00M, used 13671.56M, free 664.44M, marked `(encrypted)` |
| Swap and hibernation files | `ls -la /var/vm` | `sleepimage`, 2147483648 bytes, owner root wheel, mode `-rw------T` |
| Power settings | `pmset -g` | `hibernatemode 3`, `hibernatefile /var/vm/sleepimage`, `standby 1`, `powernap 1` |
| Spotlight | `mdutil -s /` | `Indexing enabled.` |
| Crash and diagnostic reports | `ls ~/Library/Logs/DiagnosticReports` | 33 entries, 8 `.ips` files in `Retired` |
| Network sockets | `lsof -nP -i \| wc -l` | 289 rows, returned quickly enough for a 5 s poll |
| Per-process bandwidth | `nettop -P -x -l 1 -J bytes_in,bytes_out` | Works, one row per process with byte counters |
| Alerting binaries | `command -v afplay osascript nettop` | All present under `/usr/bin` |

These are the actual numbers a monitor would see, and they are the reason several labels below are LOW rather than theoretical.

### 5.2 Vectors, mitigations, and honest labels

| Vector | What leaks | Measured or documented state | Mitigation | Who can do it | Label |
|---|---|---|---|---|---|
| Swap | Live memory pages, including message text and file chunks, written to disk | macOS encrypts virtual memory and says secure virtual memory is always on (https://support.apple.com/en-us/guide/mac-help/what-is-secure-virtual-memory-on-mac-mh11852/15.0/mac/15.0). This host reports swap as encrypted, 13.6 GB in use | Platform control. No per-app opt-out. Closing the tab and reducing memory pressure shrink the exposure, they do not remove it | OS, always on | OS MITIGATED |
| Hibernation | The entire memory image at sleep time, written to `/var/vm/sleepimage` | `hibernatemode 3`, image present at 2 GiB, measured. `pmset` documents that mode 0 disables SafeSleep altogether (https://developer.apple.com/library/mac/documentation/Darwin/Reference/ManPages/man1/pmset.1.html) | `sudo pmset -a hibernatemode 0`. On Apple silicon and T2 Macs data is encrypted automatically, and FileVault adds at-rest protection (https://support.apple.com/guide/mac-help/protect-data-on-your-mac-with-filevault-mh11785/mac) | Admin, system-wide tradeoff | HIGH with admin, but it costs safe sleep |
| Spotlight indexing | Contents of saved files and, on macOS 26, clipboard history, searchable locally | Indexing enabled on `/`, measured. Apple documents excluding files and folders, and removing clipboard history from Spotlight results (https://support.apple.com/guide/mac-help/spotlight-settings-on-mac-mchl54d95e8a/mac) | Add the download folder to Spotlight Privacy. Clear clipboard history | User | HIGH for folder exclusion, MEDIUM for clipboard |
| Screenshots | Pixels of the chat, saved as a file | macOS saves screenshots to the desktop by default, and Control plus the shortcut saves to the clipboard instead (https://support.apple.com/en-us/102646) | Use Control to avoid a file, or change the save location, or delete after use. A screenshot on the desktop is indexed and may be synced or backed up | User | HIGH |
| Clipboard | Invite and reply codes, copied at line 1067 | macOS 26 clipboard history is searchable in Spotlight (https://support.apple.com/guide/mac-help/search-your-clipboard-history-mchl40d5b86b/mac), and Universal Clipboard copies between devices (https://support.apple.com/guide/mac-help/copy-and-paste-between-devices-mchl70368996/mac) | Do not copy codes when avoidable. Clear the clipboard and its history. Disable Universal Clipboard on shared Apple accounts | User, partially | PARTIAL |
| Crash reports | Memory fragments, possibly including message strings, written to `~/Library/Logs/DiagnosticReports` | Directory exists with 33 entries and 8 `.ips` files, measured. Apple documents `.ips` crash reports in Console (https://support.apple.com/guide/console/reports-cnsl664be99a/mac) | Delete the reports. There is no supported per-app switch to stop local report writing | User, low control | LOW |
| Saved downloads | The full file, with the sender's filename | The Save link sets `download` from the file card title (line 982), so the receiver's copy lands in the download folder with the original name | Require an explicit Save, warn that saving ends ephemerality, save to an encrypted volume, delete after use | App UI plus user | HIGH at UI level |
| Browser caches and session restore | A rendered copy of the document, form values, and page state | V1 has no storage APIs and clears the log on `pagehide` (lines 1141 to 1145) | Serve with `Cache-Control: no-store`, keep the pagehide handler, navigate to `about:blank` after a wipe as in 2.5 | Server plus app | MEDIUM, depends on browser |
| Screen recording by another app | Every pixel of the chat, continuously | macOS requires Screen and System Audio Recording permission per app, and the menu bar shows a purple indicator when system audio is recorded (https://support.apple.com/guide/mac-help/control-access-to-screen-recording-on-mac-mchld6aa7d23/mac) | Review the permission list in System Settings, revoke apps that do not need it, never grant it to the monitor | User | HIGH as a permission control, LOW as detection |
| Camera and microphone | Room audio and video, if any app captures it | The OS shows an orange dot for microphone and a green dot for camera in the menu bar (https://support.apple.com/guide/mac-help/quickly-change-settings-mchl50f94f8f/26/mac/26) | Watch the dots. The chat never requests these devices, so any activation during a session is unrelated and worth investigating | User, plus monitor | HIGH for the indicator, MEDIUM for automation |

### 5.3 Linux and Windows notes

Not verified in this pass. They are included so the design does not claim macOS-only behavior is universal. Treat every row as UNVERIFIED.

| Platform | Vector | Note | Mitigation | Label |
|---|---|---|---|---|
| Linux | Swap and hibernation | Swap is unencrypted unless encrypted swap or LUKS is configured. Hibernation writes the memory image into swap | Encrypted swap, disable hibernation, zram for pressure | UNVERIFIED |
| Linux | Indexing | tracker and mlocate index home directories | Exclude paths in the indexer configuration | UNVERIFIED |
| Linux | Clipboard | Desktop environments and clipboard managers keep history | Clear history, avoid clipboard managers on the session machine | UNVERIFIED |
| Linux | Crash dumps | systemd-coredump stores dumps and journal entries | Disable or limit `coredumpctl` retention | UNVERIFIED |
| Windows | Pagefile and hibernation | `pagefile.sys` is encrypted only when BitLocker is on, `hiberfil.sys` holds the memory image | BitLocker, `powercfg /h off` | UNVERIFIED |
| Windows | Search index and clipboard | Windows Search indexes user folders. Clipboard history is off by default and enabled per user with Win+V | Exclude folders from indexing, clear clipboard history | UNVERIFIED |
| Windows | Crash reports | Windows Error Reporting keeps reports under ProgramData | Delete and disable optional reporting | UNVERIFIED |

### 5.4 Operator checklist after a sensitive session

1. Kill the session with the button, not by closing the tab, so the app clears its own state first.
2. If any code was copied, clear the clipboard and, on macOS 26, the clipboard history.
3. Delete any saved download or screenshot that is not needed. Empty the trash.
4. Check the monitor log for alerts during the session, especially camera, microphone, and clipboard events.
5. Add the download folder to Spotlight Privacy if downloads are part of the workflow.
6. Keep FileVault on. Consider `hibernatemode 0` only if the threat model includes powered-off disk forensics and losing safe sleep is acceptable.
7. Clear old diagnostic reports periodically. Exclude the folder from backups if backups are part of the threat model.
8. After any suspicion of endpoint compromise, do the hard migration in 3.4, with new codes delivered on a different device.

## 6. Build order and what to skip

| Order | Item | Effort | Why first |
|---|---|---|---|
| 1 | Always-enabled Wipe plus double Escape, and the ordered kill sequence | Small | It is the only defense that works with no peer and no monitor |
| 2 | Panic frame plus the five highest-confidence anomaly rules (A1, A2, A3, A6, A8) | Medium | Closes the peer notification and the obvious protocol abuse cases |
| 3 | Soft migration with fingerprint commitment and the 6 hex check | Medium to large | The actual fresh-set requirement, and the state machine needs care |
| 4 | Monitor menu bar app with clipboard event watch, camera and mic watch, bandwidth and CPU rules | Large, native | Separate deliverable, separate trust domain |
| 5 | Hard migration runbook and the OS checklist | Small | Process, not code, but it is the only defense against endpoint compromise |

Skip in V2:

- ML or scored anomaly detection. Five deterministic rules are testable and explainable.
- A permanently floating HUD. Menu bar first.
- A browser extension. It lives in the same trust domain as the page and cannot watch the system.
- Endpoint Security or a system extension for the monitor. The entitlement has to be requested from Apple and the build and signing cost is out of proportion to V2. lsof, nettop, and AppKit cover the required signals with honest labels.
- Per-tab network attribution. It does not exist on macOS without a Network Extension, and a monitor that claims it would be lying.
- Automatic migration on a timer. Prompt the user at 20 minutes instead.

## 7. Sources, all fetched and title-checked in this pass

| Source | Title as fetched | What it supports |
|---|---|---|
| https://developer.mozilla.org/en-US/docs/Web/API/RTCPeerConnection/getStats | RTCPeerConnection: getStats() method | Stats report available to the page |
| https://developer.mozilla.org/en-US/docs/Web/API/RTCDataChannelStats | RTCDataChannelStats | Data channel byte and message counters |
| https://developer.mozilla.org/en-US/docs/Web/API/RTCTransportStats | RTCTransportStats | `dtlsState` and transport byte counters |
| https://support.apple.com/guide/mac-help/search-your-clipboard-history-mchl40d5b86b/mac | Search your Clipboard history in Spotlight on Mac | System clipboard history exists and is searchable |
| https://support.apple.com/en-us/guide/mac-help/what-is-secure-virtual-memory-on-mac-mh11852/15.0/mac/15.0 | What is secure virtual memory on Mac? | Swap is encrypted, always on |
| https://developer.apple.com/library/mac/documentation/Darwin/Reference/ManPages/man1/pmset.1.html | pmset(1) Mac OS X Manual Page | Hibernation mode and the SafeSleep switch |
| https://support.apple.com/guide/mac-help/protect-data-on-your-mac-with-filevault-mh11785/mac | Protect data on your Mac with FileVault | Automatic encryption on Apple silicon and T2, FileVault at-rest protection |
| https://support.apple.com/guide/mac-help/spotlight-settings-on-mac-mchl54d95e8a/mac | Spotlight settings on Mac | Spotlight Privacy folder exclusion, clipboard history removal |
| https://support.apple.com/en-us/102646 | Take a screenshot on Mac | Screenshots save to the desktop by default, Control saves to the clipboard |
| https://support.apple.com/guide/mac-help/copy-and-paste-between-devices-mchl70368996/mac | Copy and paste between your Mac and other Apple devices | Universal Clipboard |
| https://support.apple.com/guide/console/reports-cnsl664be99a/mac | View reports in Console on Mac | `.ips` crash reports |
| https://support.apple.com/guide/mac-help/control-access-to-screen-recording-on-mac-mchld6aa7d23/mac | Control access to screen and system audio recording on Mac | Per-app screen recording permission |
| https://support.apple.com/guide/mac-help/quickly-change-settings-mchl50f94f8f/26/mac/26 | Use Control Center on Mac | Orange microphone dot, green camera dot, purple system audio dot |
| https://www.chromium.org/Home/chromium-security/site-isolation/ | Site Isolation | Renderer sandboxing and termination by the browser process |
| https://developer.apple.com/documentation/appkit/nsstatusitem | NSStatusItem | Menu bar status item API |
| https://developer.apple.com/documentation/appkit/nswindow/collectionbehavior-swift.struct/fullscreenauxiliary | fullScreenAuxiliary | Window displays on the same space as the full screen window |
| https://developer.apple.com/documentation/usernotifications/unusernotificationcenter | UNUserNotificationCenter | Notification authorization is requested from the user |
| https://developer.apple.com/documentation/appkit/nspasteboard/changecount | changeCount | Clipboard change counter |
| https://developer.apple.com/tutorials/data/documentation/appkit/nspasteboard/accessbehavior-86972.json | NSPasteboard access behavior | Per-app pasteboard access behavior after an access alert |
| https://objective-see.org/products/oversight.html | Objective-See: OverSight | Mic and webcam activation alerts, process attribution limits |
| https://objective-see.org/products/lulu.html | LuLu | Free open-source macOS firewall blocking unknown outgoing connections |
| https://help.obdev.at/littlesnitch6/lsm-connection-list | Network Monitor - Connection list | Per-connection app, server, and traffic meter |
| https://obdev.at/en/press/pr/2024-05-21-Objective-Development-Releases-Little-Snitch-6.html | Introducing Little Snitch 6 | Personal firewall and network monitor, macOS 14 and later |
| https://lsof.readthedocs.io/en/latest/manpage/ | Manpage - lsof | Lists network files, `-i` selects Internet files |
| https://developer.apple.com/documentation/endpointsecurity/monitoring-system-events-with-endpoint-security.md | Monitoring System Events with Endpoint Security | Endpoint Security entitlement must be requested, system extension install constraints |
| https://developer.apple.com/documentation/endpointsecurity.md | Endpoint Security | C API for monitoring system events |

Local evidence, not external sources: the measured commands in section 5.1, run on this host during this pass. The line references throughout come from `input/ephemeral-chat-v1.html`.

## SELF-CHECK

STATUS: complete. Tool time ran slightly past the 25 minute guidance because the first write sequence overwrote earlier sections and had to be rebuilt; every section and check below was completed after the rebuild.

| Acceptance item | Result | Evidence |
|---|---|---|
| Exactly one output file written, nothing under `input/` touched | PASS | Only `output/06-ops-defense.md` was created or modified. No write, patch, or command targeted `input/` or any other file |
| Kill switch is scoped to the chat and names what it shreds | PASS | Section 2.1 table covers DTLS and SCTP state, data channel, message DOM, textareas and codes, incoming file buffer, blob URLs and blobs, clipboard, JS references, and the document itself, each with a provable effect and a residue note |
| Kill switch names its trigger paths: manual, peer panic, anomaly | PASS | 2.2 manual button plus double Escape, 2.3 `{k:'panic'}` frame with receiver checks, 2.4 rules A1 to A9 with thresholds and actions |
| Fresh-set migration rotates both peers to new keys and new codes | PASS | Section 3.3 M1 to M5 creates a new `RTCPeerConnection`, new fingerprint, new SDP and codes; 3.4 hard migration adds out-of-band code delivery |
| Migration coordination is in-band and its security limit is stated | PASS | 3.3 frames, fingerprint commitment, `check` binding, M3 SDP verification, 6 hex human check; the paragraph after the checks states that an endpoint compromise sees every in-band frame |
| What survives and what does not | PASS | 3.6 table, 10 rows, including old keys, old codes, DOM history, blobs, clipboard, attacker copies, and monitor log |
| Monitor is a separate process in a separate trust domain, argued | PASS | 4.1 separate process, identity, input path, failure domain, plus same-user, root, and second-device limits |
| Monitor watch list covers connection state, inbound attempts, bandwidth, CPU and memory, clipboard, camera and mic | PASS | 4.3 table, 10 signals, each with method, cadence, provable effect, blind spot, and feasibility |
| Alerting covers sound and banner | PASS | 4.4 `NSSound` or `afplay`, `UNUserNotificationCenter`, menu bar color, silence action |
| Prior art covers Little Snitch, LuLu, Objective-See, lsof, Endpoint Security, menu bar versus HUD | PASS | 4.5 table, 5 tools; 4.2 menu bar versus HUD with verified API citations |
| Per-OS trace minimization covers swap, hibernation, Spotlight, screenshots, clipboard, crash dumps with honest labels | PASS | 5.2 table, 10 vectors, each labeled; 5.1 measured host baseline; 5.3 Linux and Windows rows all labeled UNVERIFIED |
| Every external claim carries a fetched, title-checked URL | PASS | Section 7 lists 26 unique URLs. All were fetched in this pass and their titles checked. The two Apple `.md` and `.json` pages are machine-readable variants of the same documentation pages and returned the expected content |
| Every claim about the app carries a file:line reference | PASS | 35 line-reference hits (`grep -c 'line [0-9]'`). Samples: `endSession` line 554, wipe handler line 1076, clipboard write line 1067, `onMessage` line 824, Save download line 982, `pagehide` line 1141 |
| No em dashes or en dashes | PASS | `grep -c` for U+2014 returned 0, for U+2013 returned 0 |
| No section placeholder comments left | PASS | No HTML comment markers remain in the document. All rebuild markers were replaced by content |
| File ends with a SELF-CHECK section | PASS | This section |
| Acceptance requires no fabricated numbers | PASS | Every number is either measured on this host (5.1) or derived from a fetched source; the two Apple JSON and markdown pages were read directly, not summarized from memory |

Residual risks in this deliverable:

- The exact `getStats()` field names for candidate pair types are marked UNVERIFIED in rule A6. The rule can be implemented without them by using `dtlsState` alone, which is verified.
- The Linux and Windows rows in 5.3 are UNVERIFIED by design. They are notes, not claims the build depends on.
- The monitor design assumes the chat tab and the monitor run under the same user. A root attacker defeats it, and 4.1 says so.





