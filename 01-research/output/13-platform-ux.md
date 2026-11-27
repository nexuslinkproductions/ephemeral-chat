# 13. Platform UX: reactions, navigation, session manager, shell, and the discipline cut list

RUN: w5-ephemeral-platform-20261126, platform UX lane. Brief: `01-research/briefs/W5-PLATFORM.md`.
TARGET: the platform addendum to `02-plan/output/blueprint-v2.md`, specifically section 2.4 (versioned control envelope), section 2.1 (pairing and verification), section 2.3 (resource budgets), and section 2.5 (kill, rotate, migrate).
FORM: design, not code. Every item names whether it lives in the single-file core or is EXEC-ONLY in the shell.

Sources cited by path throughout:

- `02-plan/output/blueprint-v2.md`, the plan this addendum extends.
- `01-research/output/02-audit-findings.md`, findings F-01 to F-13 and strengths S-1 to S-8.
- `01-research/output/03-threat-model.md`, nine attacker classes, section 10 cross-class observations, section 11 risk ranking.
- `01-research/output/04-crypto-design.md`, SAS, ratchet, key wipe semantics, zero trace table.
- `01-research/output/06-ops-defense.md`, kill sequence, M1 to M5 migration, anomaly rules A1 to A9, code TTL.
- `01-research/output/11-packaging-executable.md` and `01-research/output/12-media-pipeline.md`, peer platform lanes. This file states shell requirements, not wrapper internals, so it does not depend on their choices.

## 0. Interpretation, and the two hard rules

The owner ruling says the shell opens the chat "with full UI and navigation" (`_config/SETUP.md`, platform expansion paragraph). This file reads that as a complete application surface: pairing, verification, chat, session controls, media, diagnostics, menus, keyboard, and window behavior. It does not read it as a multi-conversation navigation model, because a conversation list requires message history and the product has none by design. Navigation here means screen navigation plus exactly one pending session slot. That is an interpretation, flagged as such, and section 2.1 argues it from the ephemeral core rather than from taste.

Two hard rules apply to every item below.

1. Both modes or EXEC-ONLY. Anything that needs the wrapper is tagged EXEC-ONLY with the reason. The core stays one HTML file with no build step, no external asset, and no new dependency, per blueprint owner ruling 3.
2. No new persistence. S-2 in `02-audit-findings.md` records zero hits for `localStorage`, `sessionStorage`, `indexedDB`, `document.cookie`, `serviceWorker` and `caches`, and blueprint section 3 keeps that as invariant I-3. Every UI state in this file lives in memory and dies with the page. Where a feature would need storage to be pleasant, the feature is cut, not the rule. Section 4 lists those cuts.

Numbers in this file come in three kinds, labelled where they appear: values quoted from the research files, values computed from a cited table with the arithmetic shown, and design defaults chosen here with the reason named. No measured bundle or memory figure is invented.

## 1. Reactions over the control envelope

### 1.1 Why this is a new frame type, not a field on `msg`

V1 messages have no identity. `addMessage` appends a node per message (`02-audit-findings.md` F-06, source lines 528 to 539) and nothing carries a message id. Reactions need a stable target, so the addendum adds `mid` to every `msg` frame and to nothing else. File cards keep their existing `id` from `file-start` and get no reactions; a file card already has Save, Delete and preview controls, and a second reaction namespace on the gallery would be two ways to address the same object.

The envelope already exists. Blueprint section 2.4 fixes `{ v: 1, k: "<type>", sid, seq, ... }` with a single dispatch table, known types `msg`, `file-start`, `chunk-meta`, `file-end`, `sas-confirm`, `sas-bad`, `panic`, `rekey`, `rekey-ok`, `mig`, and rule 2: an unknown `k` increments `unknownFrames` and is shown, never silently dropped. A reaction that rode inside `msg` as an optional field would fail the other way: an old peer would render the message without the reaction and no counter would move, which is the silent divergence the envelope was built to prevent. So reactions get `k: "react"` and a row in the dispatch table.

### 1.2 Frame

```
{ v: 1, k: "react", sid, seq,
  t:  "<target mid>",        // 16 hex chars, sender generated, unique per session
  e:  "<shortcode>",         // one of 24 fixed shortcodes, no raw emoji bytes
  op: "add" | "remove" }
```

| Field | Rule | Reason |
|---|---|---|
| `v` | must equal 1 | Envelope rule 2. A mismatch shows "peer is newer" or "peer is older" and refuses content. |
| `k` | literal `react` | One row in the dispatch table. |
| `sid` | must equal the pairing envelope `sid` | Envelope rule 5. A frame from a stale session is rejected before any handler runs. |
| `seq` | monotonic per direction, consumed like every frame | Envelope rule 4. Reactions get no private sequence and no private gap rule. |
| `t` | exactly 16 lowercase hex characters, must match a live `msg` `mid` in the current session | Prevents positional addressing, which is the F-12 defect in a new place. No target, no reaction. |
| `e` | must be a key in the shipped palette of 24 | The palette is the allowlist and the per-message cap. Unknown shortcode is a counted reject, never rendered. |
| `op` | exactly `add` or `remove` | Two operations, no toggle. A toggle is a lost-update bug waiting for a reordered frame. |

Frame size cap 256 bytes, checked after parse. A longer frame is rejected and counted. The global 64 KB pre-parse cap from blueprint section 2.3 still runs first.

No `rid`, no `from`, no `ts`, no `count`. Three of those omissions are load bearing:

- No actor field. The data channel authenticates the peer, so any `react` frame received is by definition the peer's reaction and any local click is mine. An actor field would be a peer-controlled claim about identity with no verification behind it, the same class of mistake as a peer-supplied filename.
- No count. Counts are derived from state. A peer-supplied count is an integer the UI would have to trust and could use to overflow a badge or a layout.
- No timestamp. Nothing in the UI orders by time, and a peer clock is not a trust input.

### 1.3 Router and apply rules, numbered for the build cards

1. Before SAS confirmation, `react` is not accepted. Blueprint section 2.1 rule 2 keeps the pre-confirm router down to `sas-confirm`, `sas-bad` and `panic`. A `react` in that state increments the pre-confirm drop counter and shows nothing.
2. A `react` whose `sid` does not match the live session is rejected before any handler runs (envelope rule 5).
3. A `react` whose `t` is not a live `mid` is a no-op with a counted event. It must not create a transcript row, resurrect a trimmed message, or move the scroll position. A peer that reacts to a message the log cap already trimmed must not be able to grow the log again, which is the F-06 unbounded DOM path through a side door. Five misses in 10 seconds runs the A1 machinery and kills with reason `react-miss`.
4. An `e` outside the palette increments `reactRejects`, shows nothing, and three in 10 seconds runs A1 and kills. This is the same threshold and the same counter family as unknown frames, not a second anomaly system.
5. A duplicate `add` is a no-op. A duplicate `remove` is a no-op. This is idempotency by state shape, not by a dedupe table (section 1.4).
6. A local click applies optimistically only if the message is live, the session is not ended, and the composer gate is open. It then sends one frame. There is no retry and no acknowledgement. If the channel is not open the click is disabled, not queued.
7. Nothing about a reaction is persisted, logged, or written to the URL.

### 1.4 State shape, and why the two sides cannot diverge

```
session.reactions : Map<mid, Map<shortcode, { me: bool, peer: bool }>>
```

The actor set in a one-to-one session has exactly two members, so a pair of booleans replaces a set of reactor ids. A group chat would need `Map<actor, bool>` and a membership list, which is one of the reasons section 4 cuts group chat.

Apply is an assignment, not a mutation of a count:

```
add:    slot[who] = true
remove: slot[who] = false
```

That is the whole convergence argument. Each side is the only writer of its own boolean, the operation is idempotent, and the channel is ordered and reliable (`04-crypto-design.md` section 2.2 records the ordered, reliable data channel as the reason the skipped-key window can be small), so a duplicate or a replayed frame converges to the same state and a loss while the channel is live cannot happen. There is no last-write-wins clock, no vector, no echo, and no server. An echo would be a second writer for the same boolean and would introduce exactly the conflict this shape avoids.

The renderer reads the pair: count is `me + peer`, the pressed state is `me`, and the pill exists when either is true. A reflected frame would land as the peer's own mark, which is indistinguishable from a genuine reaction and still bounded at one mark per side. The peer can set that mark anyway, so reflection gains it nothing.

Memory is bounded by the caps in 1.5. At 200 marks and a two-boolean leaf, the map is under 20 KB by arithmetic on the entry shape, labelled inference, not a measurement.

### 1.5 Caps and rate limits

Caps exist so reaction spam cannot become the F-06 DoS with a smaller frame. The important structural point comes first: the DOM cost of a reaction is one pill per distinct shortcode on a message, not one node per reaction. N repeats of the same shortcode cost zero extra nodes after the first, so the node count is bounded by the palette, not by the frame count. What remains unbounded is frame processing, and that is what the bucket covers.

| Cap | Value | Kind | Why this value |
|---|---|---|---|
| Palette size | 24 shortcodes | design default | Big enough for a quick row plus a picker, small enough to fit in the file as a table of 24 pairs and to render without an emoji picker dependency. |
| Distinct shortcodes per message | 24, equal to the palette | structural | The allowlist is the cap. No arrival-order race, no admission rule, no divergence. |
| Marks per shortcode per message | 2, one per side | structural | The actor set is two. |
| Session marks | 200 | design default | 200 leaves about 100 messages with one reaction each, or a handful of heavily reacted messages, and bounds the map to tens of KB. Over the cap, new targets are refused with one system line, not a kill. |
| Burst | 20 frames | design default | Two people toggling quickly do not reach 20. |
| Sustained | 4 frames per second | design default | Well above human tapping, far below the A8 kill threshold of 40 frames per second for 5 seconds (`06-ops-defense.md` section 2.4, rule A8). |
| Drop threshold | 5 dropped frames in 10 s runs A1 and kills with `react-flood` | design default | A normal user never drains the bucket. A flood drains it immediately. |
| Frame size | 256 bytes | design default | The largest legal frame is about 90 bytes. 256 leaves room for a future field without a renegotiation. |

Layering, stated so the build card can be graded: the bucket drops first and counts, A8 remains the backstop for total frame rate, and A1 remains the backstop for unknown values. There is no fourth mechanism. The session cap is a soft refusal, not a kill, because hitting 200 marks is a long conversation, not an attack.

Why 4 per second is enough and why a stricter number is not better: a user adding and removing the same reaction in frustration can legitimately produce 6 to 8 frames in a second. A limit that fires on that teaches the user that reactions are broken. The bucket absorbs it, and only sustained abuse drains 20 tokens.

### 1.6 Interface

Pills sit on the message bubble's bottom edge, in palette order, never in count or recency order. Stable order means the layout does not jump when the peer reacts, and it removes a timing signal about who reacted first.

- Pill: one `<button>` with the glyph as a text node from the shipped palette, the count as a text node, `aria-pressed` true when `me`, and an `aria-label` of the form "thumbs up, 2 reactions, one of them yours". Zero `innerHTML`, which keeps S-1 at zero sinks.
- Collapse: the first 8 pills render, the rest collapse into a "+N" button that expands the row. Collapse is a UI affordance, not protocol state, so the two sides may collapse differently without diverging.
- Hover row: appears after 150 ms on pointer hover, anchored above the bubble, 6 palette quick picks plus "More". It flips below when there are fewer than 40 px of headroom. It never covers the message text and never traps the pointer.
- Touch: long press 400 ms opens the same row. The shell is desktop Chromium, so this is a fallback, not the main path.
- Keyboard: with a message focused, `R` opens the row, arrow keys move, `Enter` toggles, `Escape` closes. Every pill is reachable by Tab without opening the row.
- Live region: the transcript is `aria-live="polite"` in V1 (source line 398, `02-audit-findings.md` F-06). Reaction changes must not re-announce a message. The pill container is `aria-live="off"`, and only a failed local action writes to the polite status line.
- Motion: 120 ms opacity at most, and none under `prefers-reduced-motion`.
- Empty state: no pills, no reserved space. The hover row is the discoverable path, and the composer hint line names `R` once per session.

### 1.7 Reactions die with the session

| Event | Reaction state | Mechanism |
|---|---|---|
| Reload | gone | No storage API. The map is a local variable in the page. |
| `pagehide` | gone | The pagehide path runs the same in-page wipe as Kill, minus navigation (blueprint section 2.5, wipe fix 1; `02-audit-findings.md` F-08). |
| Kill | gone | The log is cleared before blob URLs are revoked (`06-ops-defense.md` section 2.1 ordering note), and the map is dropped with the session object. |
| Rotate | kept | Rotate changes keys inside the same session and keeps the transcript (`04-crypto-design.md` section 7.3). Reactions are UI state about that transcript, so they stay. |
| Migrate M1 to M5 | gone | M4 clears the old log and adopts the new objects (blueprint section 2.5). A new session identity starts empty, and reactions are part of the old transcript. |
| Log trim at 2,000 rows | target gone | The reaction map entry for a trimmed `mid` is deleted in the same pass that removes the node, so the map cannot outgrow the DOM. |

The trim rule is the one that needs code. Trimming only the DOM would leave a map of 2,000-plus entries that a peer could target with `react` frames forever. The trim pass deletes the row and its map entry together, and a later `react` for that `mid` is the miss path in rule 3.

### 1.8 What is deliberately not built

- Custom emoji and image reactions. An image in a reaction is the file pipeline with a different label, and it would let a reaction carry a 45 MB payload past the reaction caps. Cut.
- Super reactions, bursts, and animations. They are engagement mechanics with no security value, and they add per-reaction DOM.
- Who-reacted lists. In a two-person chat the list is the pill. A list is a social graph artifact with no reader.
- Reaction notifications and badge counts. A reaction is not worth an OS event, and a per-reaction badge is a DoS amplifier on the badge path.
- Reactions on file cards. Section 1.1.
- Reaction search, filters, or summaries. There is no corpus to search.

## 2. Navigation for a one-to-one ephemeral chat

### 2.1 What navigation can mean when there is no history

Three things navigation normally does are impossible here, and each maps to a ruling already made.

| Normal navigation job | Why it cannot exist | Source |
|---|---|---|
| Move between conversations | A conversation list is a store of past sessions. There is no store, and reload loses everything. | `02-audit-findings.md` S-2, blueprint section 3 invariant I-3 |
| Return to a previous screen with state | Browser back and forward would restore form values and plaintext. The app navigates to `about:blank` on Kill for exactly this reason. | `06-ops-defense.md` section 2.5, `04-crypto-design.md` section 6 (bfcache row) |
| Deep link into a session | URL state is attacker-controlled configuration. F-10 is the proof: `?idle=5` shortened a session from a link. | `02-audit-findings.md` F-10 |

What is left is real and worth building: a screen state machine, one pending session slot, a menu, and keyboard paths. That is the "full UI and navigation" this file recommends, and the rest of section 2 specifies it.

### 2.2 Screen map

One document, one screen at a time, no router, no history entries. Transitions are function calls that replace the panel, not links.

| Screen | Entry | On screen | Deliberately absent |
|---|---|---|---|
| S0 Landing | Load, or after Wipe in the shell | Create invite, Join with code, idle limit, one line of what this does not protect, build hash | Recent sessions, account, settings |
| S1a Invite | Create invite | Code area, Copy, Show, TTL countdown, QR (EXEC-ONLY), "send this over a channel you trust" | A share sheet, an email button, a contact picker |
| S1b Join | Join | Paste field, paste-preview state, TTL and format errors, Create reply | A code history, a QR-only path |
| S2 Verify | Peer connected | 60 digit safety number in 12 groups of 5, suite label, Match and Does not match, peer confirmation state | A skip button, a remember-this-device checkbox |
| S3 Chat | Both sides confirmed | Header with status chips, transcript, composer, file tray, gallery entry, session menu | Search, message actions beyond reactions and delete, typing state |
| S4 Ended | Kill, peer loss, anomaly, migration failure, idle | Reason, countdown, one sentence about what was destroyed | A cancel button, a session id, a "reopen" that preserves state |
| Sheet About and diagnostics | Menu or footer link | What is not protected, build hash, transport candidate type, monitor state, ratchet counters | Any session content |

Rules that make the map safe:

1. S2 has no back. Once content is locked, leaving means Wipe, not a return to S1.
2. S0 to S3 is a one-way transition. There is no "home" button inside a session, because home is unauthenticated and the session state would still be in memory.
3. S4 never renders a session identifier. `04-crypto-design.md` section 7.3 item 5 says a session id is a correlation handle and must not be shown. The ended panel says what happened, not which session it was.
4. No screen writes to `location`, `history`, or the document title beyond a static title. The only navigation is the final `location.replace('about:blank')`.
5. Focus moves to the new panel's first heading on every transition, so a screen reader user is not left in a removed subtree.

### 2.3 Session manager: two slots, not a list

The blueprint's state discipline is one `pending` object and one `adopt(pending)` function (section 2.5, and `06-ops-defense.md` section 3.7). The session manager is the UI over exactly that shape.

| Slot | Type | Created | Destroyed | Shown as |
|---|---|---|---|---|
| `active` | `{pc, dc, sid, fp, role, log, reactions}` | Pairing success | Kill, peer loss, migration failure | The chat |
| `pending` | `{pc, dc, sid, fp, role, deadline}` | Migrate M1 | M4 adopt, M5 timeout, Kill | A progress strip over the chat |

There is no third slot, no array of sessions, and no "background session". A second incoming pair attempt is refused by the existing single-connection rule, and a second Migrate click is the tie-break case, not a second slot.

Mapping M1 to M5 onto the UI, so the strips and the failure text are specified rather than improvised:

| Step | Frame | UI | Composer | Timeout |
|---|---|---|---|---|
| M1 | offer sent | "Preparing a new session, step 1 of 4" | locked | 15 s |
| M2 | answer | "Step 2 of 4", old transcript visible and read-only | locked | 15 s |
| M3 | commit | "Verifying the new connection", fingerprint match shown as a check | locked | 15 s |
| M4 | done | old log cleared, new session toast, composer unlocked | unlocked | none |
| M5 | timeout | ended panel with reason `migration-failed`, no retry button | disabled | terminal |

The composer is locked from M1 to M4 by the UI, not only by the protocol. Blueprint section 2.5 refuses migration while a transfer is active, and the same reasoning applies to typing: a message sent on the old channel after M3 is ambiguous, and the new channel is not yet the live one. Two initiators within a second produce a 500 to 1500 ms random wait plus the fingerprint tie-break (`06-ops-defense.md` section 3.3), so the UI shows "two requests, resolving" and not an error.

Two named actions, never conflated, per blueprint section 2.5's naming note:

- Rotate keys: in-channel rekey, same session and codes, reaction state kept, transcript kept. Menu item and status surface update.
- New session: Migrate, new identity, new codes, log and reactions cleared.

"Start over" is not a third action. After a suspected endpoint compromise the runbook is Kill, close the window, reopen from a known-good copy, and exchange new codes out of band (`06-ops-defense.md` section 3.4). The ended panel therefore has no button that cancels the wipe. Reopening is a fresh launch, and in the shell that is a menu action, not a session restore.

### 2.4 Pairing: paste versus QR

The code is the root of trust and the clipboard is its worst carrier. Threat model rank 2 scores clipboard persistence at 15, equal to rank 1 (`03-threat-model.md` section 11). QR looks like the fix. The numbers say it is a partial one.

Size first, because size decides whether QR is even readable. `04-crypto-design.md` section 3.2 puts the V1 code at about 650 characters and the ML-KEM variant at roughly 1.7 KB. The V2 envelope adds a 32 hex session id, an issue timestamp, two 32 byte public keys and a suite id, which is roughly another 150 to 200 characters before compression; the real length must be measured when the envelope lands, and 800 bytes is the planning figure here, labelled inference. A base64url body contains lowercase letters, so the byte-mode column is the relevant one; the alphanumeric column is listed for comparison only. From the fetched capacity table:

| QR version | Error correction | Byte capacity | Module count | Fits an 800 byte code |
|---|---|---|---|---|
| 20 | M | 666 | 97 | No |
| 22 | M | 779 | 105 | No |
| 23 | M | 857 | 109 | Yes |
| 25 | M | 997 | 117 | Yes |
| 33 | M | 1628 | 149 | No for the 1.7 KB ML-KEM code |
| 35 | M | 1809 | 157 | Yes for the 1.7 KB ML-KEM code |

Module count is 21 plus 4 times the version minus 1, so version 23 is 109 by 109 modules. That is a comfortable on-screen QR at 3 px per module, roughly 330 px square. It is not comfortable for the ML-KEM variant at 157 modules, and a 1.7 KB code would need a larger canvas and a closer scan.

| Option | What it is | Adds or costs | Works in file mode | Verdict |
|---|---|---|---|---|
| Paste | The code travels as text through whatever channel the two people already trust | No new permission, no new bytes. Keeps the clipboard exposure that rank 2 scores 15, and keeps the "read it aloud" fallback | Yes | Default, and the only universal path |
| QR display | The app renders the code as a QR for the other person to photograph | Needs an encoder, roughly a few hundred lines or a paste-in library, and the code becomes a screen-capture target. Removes clipboard exposure in the invite direction only | Technically yes, with an encoder in the core | EXEC-ONLY by choice: display without a scan path adds a capture surface and no second direction, so it only pays off beside the scan below |
| QR scan | The app reads a QR with the camera | Adds a camera permission to a product whose pitch is no permissions, needs `BarcodeDetector` or a bundled decoder, and `BarcodeDetector` is documented as limited availability, not Baseline | No | EXEC-ONLY, never the only path |

The accessibility argument decides it. A QR cannot be read aloud, and the safety number flow already depends on a voice channel being available. A blind user or a user on a phone call needs the paste path, so paste can never be removed. A feature that must always exist beside the "better" one is not a replacement, and building both doubles the pairing surface that R3 has to attack (blueprint section 4.3 class 1 and 2).

Recommendation: paste is the default and the documented path. The shell may show a QR of the invite code (display only) when the measured code is under 997 bytes, with the paste field still on screen and still the primary control. Scanning is EXEC-ONLY and off by default, because it buys one direction of clipboard avoidance for a camera permission, and the reply code still has to travel back. The copy next to a displayed QR says a QR on screen can be photographed by anything in the room, so the room is the boundary, not the clipboard.

Pairing panel states, independent of QR:

1. Empty, with a format hint and the 16 KB pre-decode cap enforced on paste (`03-threat-model.md` class 3, blueprint section 2.1).
2. Parsing, then either a preview (peer fingerprint short form, suite, issue age) or a specific error: wrong prefix, wrong version, stale by more than 120 seconds, already consumed on this page, too many candidates.
3. Code shown, with a 120 second countdown ring and a Show button that regenerates after the textarea is cleared 30 seconds post-copy (`06-ops-defense.md` section 3.5).
4. Used. The code is consumed and the join path is disabled with "this code was already used on this page".
5. Expired. The countdown expires and the only action is Generate new code.

No state ever displays the decoded SDP, the candidates, or the raw fingerprint hex. The short form is a 6 hex prefix, enough to compare between the two screens and not enough to reconstruct anything.

### 2.5 Crypto status surface

The surface answers three questions at a glance: am I verified, what suite am I on, and how old is the key material. It reads from the Worker, never from the main thread's guess.

Worker status message, requested once per second while the document is visible and paused on blur:

```
{ t: "status", sasState, suite, rekeyCount, lastRekeyAt,
  dhStepCount, lastDhStepAt, msgsSent, msgsRecv, candidateType,
  monitorState }
```

No key material, no session id, no peer address string. `candidateType` is host, server-reflexive or relay, which is the honest path-quality signal `03-threat-model.md` class 2 recommends; it is diagnostics, not a header chip.

Header chips, left to right:

| Chip | States | Source of truth |
|---|---|---|
| Verification | Unverified (locked), Waiting for peer, Verified, Mismatch | Local SAS confirm plus the peer `sas-confirm` |
| Suite | X25519 or P-256 | Suite negotiated in the envelope, displayed next to the number per blueprint section 2.1 rule 5 |
| Ratchet | "rotated 3 min ago", amber at 20 min | `lastRekeyAt` and `lastDhStepAt` |
| Files | "Files 3" | Local retained-file count |

The verification gate is stricter than the wire rule, and the difference is deliberate. Blueprint section 2.1 locks the composer until each side records a local confirmation, and the router drops content frames before the local confirm. If I confirm first and type, the peer's router drops my message until they confirm, and my UI would have shown a sent message that never rendered. So the composer unlocks only when both my confirmation and the peer's `sas-confirm` are in. The router rule is unchanged; this is a UI tightening that prevents silent loss.

Safety number presentation:

- 60 digits in 12 groups of 5, monospace, grouped 4 per line for three lines. No copy button. It is public, but a copy button adds clipboard churn that the monitor rule M3 watches (`06-ops-defense.md` section 4.4).
- Match is one click and is final for the session. Does not match sends `sas-bad` and kills with a visible reason. There is no override, per blueprint section 2.1 rule 4.
- The suite label sits directly under the digits, so a P-256 downgrade changes both the label and the digits (`04-crypto-design.md` section 8.2).
- Before confirmation, the number is shown but the digits are not labelled "verified" anywhere. The word verified appears only after both confirms.
- After confirmation, the panel collapses to a chip; "View safety number" reopens it. Reopening does not re-run anything.

Ratchet age, defined precisely so the number is not decorative:

- `rekeyAge` is now minus `lastRekeyAt`, the last explicit Rotate. It survives DH steps.
- `dhAge` is now minus `lastDhStepAt`, the last double ratchet DH step, which happens on turn changes. It is seconds in an active chat and is shown only in diagnostics.
- The header shows `rekeyAge` and a rotation count. At 20 minutes the aging banner appears: "Session is old. Rotate keys?" with Rotate and Later, per blueprint invariant I-4 and `06-ops-defense.md` section 3.7. Later dismisses for 10 minutes and is not persisted.
- Amber is the maximum severity for age. Red is reserved for mismatch, anomaly and kill, so a long session does not look like an attack.

Never shown: the session id, raw key bytes, the peer IP as a string, message counters in the header, or a "secure" badge with no state behind it. The About panel repeats the honest limits from blueprint section 5: the number proves shared keys, not personhood, and the platform boundary is outside the app.

### 2.6 Wipe and panic affordances

V1 gates the Wipe button on connection (source line 354, enabled at line 676), so a user stuck in pairing cannot kill a session whose code may already be on the clipboard (`06-ops-defense.md` section 2.2). The addendum removes that gate in the core and keeps the button visible on every screen from S0 to S3.

| Affordance | Where | Behavior |
|---|---|---|
| Wipe button | Persistent, top right, every screen | Immediate when nothing is connected, one confirm when connected. Never disabled |
| Double Escape | Global keydown, works with focus in a textarea | Two presses within 800 ms run Kill. Always available |
| Session menu, Wipe Session | Shell menu | Same handler, no accelerator. Discoverability, not a second mechanism |
| Panic frame | Automatic on Kill | `{k:"panic"}` best effort, no await, never claimed as delivered |
| Ended panel | S4 | Reason line, 4 s countdown, 1.5 s on the anomaly path, then `about:blank` |

The Escape interaction with the reaction row needs one rule. A modal layer that consumes Escape clears the panic counter instead of feeding it. Without that rule, closing a reaction picker with two quick presses wipes the session, which trains users to fear the picker. With it, panic is still two presses away at all times, and a user in a hurry presses Escape once to close the layer and twice more to wipe. The trade is three presses in the rare layered case against accidental destruction in the common one. The gate asserts both halves: layer open, two presses do not wipe; layer closed, two presses do.

Ended panel copy, fixed strings, no interpolation of peer data:

- Title: "Session destroyed."
- Body: "This device cleared the transcript, the codes and the files. Nothing was saved."
- Reason line, one of: you ended it, peer left, network lost, idle timeout, anomaly rule, migration failed, safety number mismatch.
- No session id, no peer name, no message count, no "start over" that preserves anything.
- In the shell, a "New session" item in the File menu is the only next step. In the core, the user reopens the file.

The panel must not claim the peer wiped. The panic frame is best effort, and the peer's own wipe depends on its peer-loss path firing within the grace period (`06-ops-defense.md` section 2.3).

### 2.7 In-session media gallery, RAM-only

The gallery is a view over the session's `files` array, not a second store. Every thumbnail, poster frame and full image is a blob URL created from decrypted plaintext in memory, and nothing else.

| Element | Behavior | Bound |
|---|---|---|
| Entry | Header chip "Files N" opens a sheet | N is the retained count |
| Grid | Square thumbnails, name, size, type | Raster only for preview, same regex as V1 (`02-audit-findings.md`, source 893 and 1049) |
| Open | Full view in a modal, Escape closes | One at a time |
| Video | Poster frame generated in memory, controls shown only after a click, no autoplay | Whatever the media lane produces, 45 MB cap per the owner ruling |
| Save | Only after digest and completeness pass, and only from the file card | Blueprint section 2.3 rules 7 to 9 |
| Delete | Removes the node first, then revokes the URL | `06-ops-defense.md` section 2.1 ordering note |
| Drag out | Blocked. `draggable="false"`, no `DownloadURL`, dragstart prevented | A drag to Finder is a disk write the app did not ask for |
| Eviction | Oldest file is dropped when the 4 file or 200 MiB budget is hit | Blueprint section 2.3 budget table |

The gallery shows one line when eviction has happened: "3 of 5 files retained. Older files were dropped." That is the honest ephemerality the product sells, and it is better than a silent disappearance.

Deleting from the gallery deletes the message card's blob too, because there is one array. Two delete paths with two arrays would drift, and the DOM-first ordering exists precisely because image and anchor nodes hold blob references.

No gallery state survives the session. There is no thumbnail cache, no "recently viewed", no file list in the URL, no drag-and-drop target that writes to disk. A saved file is a file and leaves the app, which the Save warning says in one line.

## 3. Executable shell UX, EXEC-ONLY

Scope: the shell is a wrapper that opens the single-file core in a self-contained Chromium window. This section specifies what the user sees and what the wrapper must forbid. It does not choose the framework; `01-research/output/11-packaging-executable.md` owns that. Where an API is named, it is the existence proof for a requirement, not a dependency choice.

### 3.1 Window chrome

| Property | Value | Reason |
|---|---|---|
| Titlebar | Standard OS titlebar, no custom drag region, no transparency | A custom titlebar buys nothing and adds hit-testing bugs and a second place to spoof the window identity |
| Size | 980 by 720 default, 720 by 560 minimum, resizable | The chat column and the gallery sheet fit without a responsive cliff |
| Windows | Exactly one | A second window is a second session surface with no session manager to control it |
| Tabs, bookmarks, address bar | None | The core has no URL state and no navigation. An address bar invites a `?idle=` style parameter and a history entry |
| Always on top | Off, not configurable | It is a HUD, it appears in screen shares, and `06-ops-defense.md` section 4.2 already argues against a permanent HUD for the monitor |
| Window state restore | None | Restoring bounds is a state file. Fixed default size, no restore, no state directory |
| Devtools | Not built into the release menu, no keyboard role | Devtools on a live session is a plaintext inspector |
| Isolation | `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true` | The page is untrusted input by construction. Only one bridge channel, described in 3.4 |
| Title | Static "ephemeral" | A title that changes with peer or message data leaks to the window list and to screen recording |

The renderer loads the packaged HTML from the app bundle, never a remote URL, and the shell refuses to load any other origin. That is the one place the shell can beat the browser: no address bar, no extension model by default, no page fetch from a network origin. The About panel still says the shell cannot fix a compromised OS or a hook in the renderer, because that is true.

### 3.2 Application menu

| Menu | Items | Notes |
|---|---|---|
| ephemeral | About ephemeral, Quit (Cmd+Q) | About carries the build hash, the suite, and what this does not protect. No preferences item, because there are no persisted settings |
| File | New Invite (Cmd+N), New Session (Cmd+Shift+N), Close Window (Cmd+W) | New Invite is enabled only with no active session. New Session runs Migrate when a session is live |
| Edit | Undo, Redo, Cut, Copy, Paste, Select All | Required. Codes are pasted, and removing the standard edit roles breaks that |
| Session | Rotate Keys (Cmd+Shift+K), Wipe Session | Wipe has no accelerator. Double Escape is the panic chord, and a second menu accelerator would be a second path to test |
| View | Diagnostics (Cmd+Shift+D), Actual Size, Enter Full Screen | Diagnostics is the about sheet. No reload item, no zoom |
| Window | Minimize, Zoom, Bring All to Front | Standard |
| Help | What This Protects, Verify Build | Verify Build opens the hash and the command to compare it |

Three omissions are requirements:

1. No Reload. Cmd+R and Cmd+Shift+R are disabled at the wrapper level. In this product reload is a wipe with no confirmation, no panic frame, and no ended panel, so it must not be one keystroke away. If the user wants a new session, that is Kill then reopen.
2. No Preferences or Settings. Every setting in this file is either derived from the OS or fixed. A settings window would need storage to remember anything, and blueprint invariant I-3 forbids storage.
3. No History, Bookmarks, Downloads, or Developer items. Each is an artifact surface the product does not have.

Opening a second instance focuses the existing window. Dropping a file on the dock icon does nothing; the only file ingress is the in-session drop target, where the caps and the type checks run.

### 3.3 Shortcuts

| Keys | Action | Mode |
|---|---|---|
| Escape Escape, within 800 ms | Kill | Core and shell |
| Escape | Close the topmost layer (picker, gallery, diagnostics) | Core and shell |
| R, with a message focused | Open the reaction row | Core and shell |
| Tab, arrows, Enter | Move, select, toggle in the reaction row | Core and shell |
| Cmd+N | New invite, only with no session | Shell, menu |
| Cmd+Shift+N | New session (Migrate) | Shell, menu |
| Cmd+Shift+K | Rotate keys | Shell, menu |
| Cmd+W | Close window, which is a Kill by construction | Shell |
| Cmd+Q | Quit, which is a Kill by construction | Shell |
| Cmd+Shift+D | Diagnostics | Shell, menu |

No other global chord is added. Every chord is a surface that can collide with a browser default, an OS shortcut, or an input method, and the panic path already has two independent discoverable forms: the button and double Escape.

The wrapper must also disable these browser-level defaults, because each one writes state or leaks content: autofill and password save, spellcheck on the composer, session restore, crash reporter upload, and the back and forward gestures. Spellcheck is named explicitly because it can send typed words to a checker outside the page, and invariant I-2 says no plaintext leaves the page except STUN binding traffic. The composer sets `spellcheck="false"`, `autocomplete="off"`, `autocorrect="off"`, `autocapitalize="off"` in the core, so the rule holds in file mode too and does not depend on a browser setting the user may have enabled.

### 3.4 Dock badge on incoming

The badge is a dot, never a number.

| Event | Core attempt | Shell |
|---|---|---|
| Message arrives while the window is unfocused | `navigator.setAppBadge()` in a try and forget | Main process `dock.setBadge("•")` |
| Window focused | `navigator.clearAppBadge()` | `dock.setBadge("")` |
| Session ends or is wiped | Clear | Clear |
| Reaction arrives | No badge | No badge |

`navigator.setAppBadge` is documented as limited availability, not Baseline, and requires a secure context, so in `file://` it will usually no-op. That is acceptable: the core treats it as best effort, and the shell path is the reliable one. `dock.setBadge` is macOS only in Electron; Windows and Linux equivalents are platform-specific and marked UNVERIFIED here.

Why a dot and not a count: a count is a small unread model, and an unread model is the first half of a read receipt. It also forces a decision about whether a reaction or a file counts, which is a product surface nobody asked for. A dot says "something arrived" and nothing more.

Why no OS notification: a banner is an OS artifact outside the app's wipe path, and the app has no API to clear it (inference: no page or shell API reaches the notification centre's stored list). A banner with message text would put plaintext there, which is the class 6 artifact the whole wipe path exists to avoid. A banner without text is only a worse badge. The badge plus an optional `dock.bounce("informational")` covers the need without a notification permission. No permission is requested, so there is nothing to grant by accident.

### 3.5 Dark and light

The app follows the OS, in both modes, with no toggle and no stored preference.

- Core: CSS custom properties, `color-scheme: light dark`, one `@media (prefers-color-scheme: dark)` block overriding the token set. `prefers-color-scheme` is Baseline and has been available across browsers since January 2020, so this is the boring path.
- Shell: the same CSS, because the wrapper renders the same file. The shell sets `nativeTheme.themeSource = "system"` if it exposes the option at all. There is no in-app appearance setting.
- Contrast: body text at 4.5:1 or better and large text at 3:1, which is WCAG 2.2 success criterion 1.4.3 level AA. The dark palette is checked separately; inverting a light palette does not preserve ratios.
- Typography: system UI stack only, no bundled or remote font. The emoji glyphs use the platform emoji font through a font stack, and a platform without one falls back to the shortcode text, which is still readable and still selectable.
- Motion: 120 ms transitions, none under `prefers-reduced-motion`.
- Focus: a 2 px visible focus ring on every interactive element, including pills and the composer, with a 3:1 contrast against its adjacent colour.

A theme toggle is cut for the reason in section 4: remembering it needs storage. Following the OS is what a user already expects, and it is the only version that keeps zero persistence.

### 3.6 What the shell must not add

Each of these is a small convenience that would quietly undo a core property, so the wrapper's gate should assert the absence.

- No recent sessions, no reopen-last, no window state file, no crash recovery.
- No auto-update channel that phones home. Distribution and signing are ops (`03-threat-model.md` class 9); an updater is a network client with standing access to the app directory.
- No telemetry, no crash upload, no usage counters, no first-run analytics.
- No protocol handler or URL scheme. A link that opens the app is a deep link, and deep links are attacker-controlled input.
- No menu item that reveals a file in Finder, opens a download folder, or prints. Each writes or exposes plaintext outside the session.
- No extension support and no plugin directory. The shell's advantage over the browser is that it starts without an extension model; adding one gives that back.

## 4. Discipline: the temptations a platform invites, and where each is cut

A platform build invites features that make the product feel normal. Normal is the threat here. Each row names the temptation, the cut in one line, and the threat model ground it stands on. The cut is not a backlog item; it is a design decision that the addendum should record so a later round does not reopen it by accident.

| # | Temptation | The cut, in one line | Threat model ground |
|---|---|---|---|
| 1 | Accounts and sign-in | An account is a persistent identifier and a correlation handle, and the product's only identity is a per-session key with no directory, so there is nothing to sign in to | `03-threat-model.md` section 10: V1 has no identity layer and that is a privacy feature; class 9 adds a durable artifact |
| 2 | Contact discovery and a friend list | Discovery needs a directory or an address book upload, which is the signaling surface and the social graph the no-server design exists to avoid | `03-threat-model.md` class 5 and section 10: no signaling server and no inbound listener is the strongest structural property |
| 3 | Message history and scrollback | A history store is a persistence API and a forensics target, and a stored transcript turns deniability into evidence | `02-audit-findings.md` S-2, `03-threat-model.md` class 6, `04-crypto-design.md` section 5.3 |
| 4 | Read receipts and typing indicators | A receipt is a presence side channel that reveals attention and adds frames to the channel A8 already polices, and "seen at 14:02" is exactly the archaeology an ephemeral session removes | `03-threat-model.md` class 1 (metadata) and class 4 (unbounded frame rate); `06-ops-defense.md` rule A8 |
| 5 | Message editing and delete-for-everyone | Both need a durable message record and a shared clock, and with no store the only delete is the wipe, which deletes everything | `03-threat-model.md` class 6 (a retained record is a forensics artifact), `06-ops-defense.md` section 2.5, `02-audit-findings.md` S-2 |
| 6 | Search the conversation | Search needs an index, an index is persistence, and an in-memory plaintext index is a memory-dump target | `03-threat-model.md` class 6, `04-crypto-design.md` section 7.1 |
| 7 | Multi-device sync | Sync needs an account, a store and a relay that holds state, and each is a new trust domain the wipe cannot reach | `03-threat-model.md` classes 7 and 9 |
| 8 | Backup and export transcript | Export writes plaintext to disk, which is the one artifact the app cannot revoke, and it converts a deniable transcript into evidence | `03-threat-model.md` class 6, `04-crypto-design.md` sections 5.3 and 6 |
| 9 | Push notifications with content | A push service is a third party that sees metadata, and a banner is an OS artifact outside the app's wipe path, with no API for the app to clear it | `03-threat-model.md` class 6, `06-ops-defense.md` section 5.2 |
| 10 | Analytics, crash reporting, auto-update telemetry | Any of them is an egress channel that breaks I-2 and a supply-chain surface that the no-dependency design removed | Blueprint invariant I-2, `03-threat-model.md` class 9 |
| 11 | Custom emoji and image reactions | A peer-supplied image in a reaction is the file pipeline under a different name, with a 45 MB ceiling and no Save gate | `03-threat-model.md` class 4 (rogue peer resource exhaustion), `02-audit-findings.md` F-03 and F-13, blueprint section 2.3 |
| 12 | Reaction notifications and who-reacted lists | A per-person ledger is a social graph artifact, and a notification per reaction is a DoS amplifier on the badge path | `03-threat-model.md` class 4, `06-ops-defense.md` rule A8 |
| 13 | Deep links and URL state | URL state is attacker-controlled configuration, and F-10 is the proof that one parameter shortened a session | `03-threat-model.md` class 4 (any link can drive it), `02-audit-findings.md` F-10 |
| 14 | A settings panel and a theme toggle | Settings need storage to be meaningful, and storage is the invariant the product is built around | `03-threat-model.md` class 6 (a settings file is a disk artifact), `02-audit-findings.md` S-2, blueprint invariant I-3 |

The pattern is one sentence: every row converts an in-memory fact into a durable one, or converts a local decision into a network-visible one. The ephemeral core is not a feature list that happens to lack storage; it is a shape, and each temptation is a way to break the shape while keeping the marketing.

## 5. Recommended UI scope for the addendum cards

Ten cards, in dependency order. Each names its file scope, one gate command, and the failure mode the gate catches, in the same shape as blueprint section 4.2. A card whose scope names a `gate.py` case owns that case. Cards marked EXEC-ONLY have no core half and must not gate the default artifact.

| Card | Scope | Mode | Gate | Failure mode caught |
|---|---|---|---|---|
| UX-01 Message identity | `msg` frame gains `mid`, `addMessage`, log trim, `03-build/output/probes/gate.py` (case `mid`) | Core | `python3 03-build/output/probes/gate.py mid` | A reaction addresses the wrong message, or two messages share an id, which is F-12's positional bug with a new field |
| UX-02 Reactions | `react` frame, dispatch row, `applyReact`, reaction map, pill render, hover row, palette, bucket, `gate.py` (case `react`) | Core | `python3 03-build/output/probes/gate.py react` | A reaction before SAS confirm, a duplicate that double counts, an unknown shortcode that renders, a flood that fails to trip the bucket or A8, or a reaction that resurrects a trimmed row |
| UX-03 Screen state machine and session slots | Panel container, S0 to S4 transitions plus two sheets, `active` and `pending` slots, migration strip, focus moves, `gate.py` (case `nav`) | Core | `python3 03-build/output/probes/gate.py nav` | A back path into a live session, a composer that unlocks during migration, or two session slots that can both be live |
| UX-04 Verification panel and crypto status | SAS panel, 60 digit render, confirm and mismatch, peer confirm gate, status chips, ratchet age, aging banner, `gate.py` (case `sas-ui`) | Core | `python3 03-build/output/probes/gate.py sas-ui` | A composer that unlocks before the peer confirms, a "verified" label before both confirms, or a session id or key byte reaching the DOM |
| UX-05 Pairing panel states | Paste, parse, preview, TTL countdown, single use, error strings, show and regenerate, `gate.py` (case `pair`) | Core | `python3 03-build/output/probes/gate.py pair` | A stale or reused code that still pairs, or an error that leaks decoded SDP or candidates |
| UX-06 Wipe and panic | Always-enabled button, confirm rules, double Escape, layer rule, ended panel, countdowns, `gate.py` (case `panic`) | Core | `python3 03-build/output/probes/gate.py panic` | Wipe disabled before connect, Escape in a picker that wipes the session, or an ended panel that shows a session id |
| UX-07 Media gallery | Gallery sheet, grid, delete order, save gate, eviction line, drag block, `gate.py` (case `gallery`) | Core | `python3 03-build/output/probes/gate.py gallery` | A delete that revokes before removing the node, a save anchor before the digest, or a drag that writes plaintext to disk |
| UX-08 Theme and accessibility baseline | Token set, light and dark blocks, focus ring, reduced motion, emoji fallback, `gate.py` (case `a11y`) | Core | `python3 03-build/output/probes/gate.py a11y` | A dark palette below 4.5:1, a pill that is not a button, or a live region that re-announces a message on every reaction |
| UX-09 Shell window, menu, shortcuts, badge | Wrapper main process, menu template, disabled defaults, badge bridge, `gate.py` (case `shell`) | EXEC-ONLY | `python3 03-build/output/probes/gate.py shell --app 04-shell/output/ephemeral.app` | A reachable Reload, a second window, a badge with a count, an OS notification, or a renderer with `nodeIntegration` on |
| UX-10 QR display and scan | Encoder in the shell, size ceiling check, scan permission flow, paste fallback, `gate.py` (case `qr`) | EXEC-ONLY | `python3 03-build/output/probes/gate.py qr` | A QR rendered for a code above the version 25 ceiling, a scan path with no paste fallback, or a camera permission requested before the user asks to scan |

Order and dependency: UX-01 then UX-02, because reactions cannot be built or gated without message ids. UX-03 before UX-04 and UX-05, because both live inside the screen machine. UX-06 last in the core group, because it touches every panel's Escape and focus handling. UX-09 and UX-10 land after the core group and after `01-research/output/11-packaging-executable.md` picks the wrapper.

What the addendum should not include, stated so the scope stays closed:

- No group chat, no channels, no threads. Every reaction rule in section 1 assumes a two-member actor set, and a group version needs a membership list, a per-actor map, and a fan-out policy.
- No notification permission, no history, no settings, no accounts, no contact list. Section 4.
- No new dependency in the core. The palette is a table, the pills are CSS, the reaction logic is a map and two booleans.
- No shell-only feature that the core cannot degrade from. The QR card is additive and removable; the badge is best effort; the menu mirrors keyboard paths that exist in the core.

## 6. External sources

Every source below was fetched during this run and its title checked against the claim it supports. All other claims trace to the research files by path.

| Source | Title as fetched | What it supports |
|---|---|---|
| https://docs.discord.com/developers/resources/message | Message Resource | The reaction object carries a per-emoji `count` and a per-viewer `me` boolean, which is the pill shape in section 1.6 |
| https://www.thonky.com/qr-code-tutorial/character-capacities | Character Capacities by Version, Mode, and Error Correction | Byte-mode capacity per QR version and error correction level, used in the section 2.4 size table |
| https://www.qrcode.com/en/about/version.html | Information capacity and versions of QR Code QRcode.com | Version 1 is 21 by 21 modules and version 40 is 177 by 177, which backs the module count formula in section 2.4 |
| https://developer.mozilla.org/en-US/docs/Web/API/BarcodeDetector | BarcodeDetector - Web APIs MDN | BarcodeDetector is limited availability and not Baseline, which is why scanning is EXEC-ONLY |
| https://developer.mozilla.org/en-US/docs/Web/API/Navigator/setAppBadge | Navigator: setAppBadge() method | The core badge path and its secure context and limited availability constraints |
| https://www.electronjs.org/docs/latest/api/dock | Class: Dock Electron | `dock.setBadge` exists as the shell badge path on macOS |
| https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html | Understanding Success Criterion 1.4.3: Contrast (Minimum) WAI | The 4.5:1 body text and 3:1 large text thresholds in section 3.5 |
| https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/@media/prefers-color-scheme | prefers-color-scheme CSS media feature | OS-driven theming without JavaScript or storage, Baseline since January 2020 |

Claims from these sources are limited to what the fetched text states. The QR version to capacity mapping is read from the table, and the module count is the standard formula 21 plus 4 times version minus 1, which the table page states as 21 by 21 for version 1 up to 177 by 177 for version 40. The 800 byte code length is a planning figure derived from the 650 character V1 figure plus the envelope field sizes, and is labelled inference in section 2.4.

## SELF-CHECK

Re-read the file end to end after the last edit and ran the checks below. Results are from the commands quoted, not from memory.

### Lane acceptance

| # | Acceptance item | Result | Evidence |
|---|---|---|---|
| 1 | Output exists and is non-empty at `01-research/output/13-platform-ux.md` | PASS | `test -s` exited 0. `wc -l` reports 559 lines at the final check, and the file is over 63 KB. |
| 2 | The reaction wire format names its envelope and its caps | PASS | Section 1.2 gives `{ v: 1, k: "react", sid, seq, t, e, op }` and states it is a row in the blueprint section 2.4 envelope with `sid` and `seq` consumed by the existing router. Section 1.5 is the cap table: palette 24, distinct per message 24, marks per shortcode 2, session 200, burst 20, sustained 4 per second, drop threshold 5 in 10 s, frame 256 bytes. |
| 3 | Idempotency and both-sides sync are specified | PASS | Section 1.4 gives the state shape `Map<mid, Map<shortcode, {me, peer}>>`, the assignment apply rule, the single-writer argument, the no-echo rule, and the ordered reliable channel as the reason replay converges. |
| 4 | Per-message caps and per-second limits make reaction spam a non-DoS, consistent with the audit | PASS | Section 1.5: DOM cost is one pill per distinct shortcode, not one node per reaction, so F-06's unbounded DOM cannot be reached through reactions; frame processing is bounded by a 20 token bucket refilling at 4 per second, with A8 as the backstop and A1 as the unknown-value backstop. |
| 5 | Reactions die with the session, no persistence | PASS | Section 1.7 table covers reload, `pagehide`, Kill, Rotate, Migrate and log trim. Rotate keeps them and the table says why. No storage API appears anywhere in the design. |
| 6 | Navigation is defined for an ephemeral one-to-one chat | PASS | Section 2.1 lists the three normal navigation jobs that cannot exist and sources each. Section 2.2 is the S0 to S4 screen map with two sheets, entry, contents, and deliberate absences. |
| 7 | The session manager pairs with the M1 to M5 migration protocol | PASS | Section 2.3 has the two slots `active` and `pending`, the M1 to M5 UI strip table with the 15 s timeout and the composer lock, and the Rotate versus New session naming. |
| 8 | Pairing UX covers QR versus pasted code with a verdict | PASS | Section 2.4 has the capacity table (version 20 M 666 bytes, 22 M 779, 23 M 857, 25 M 997, 35 M 1809), the module formula, and the three option table. Verdict: paste default and universal, QR display EXEC-ONLY by choice below 997 bytes, scan EXEC-ONLY, never QR-only. The accessibility argument is stated. |
| 9 | Crypto status surface shows ratchet age and the safety-number verification state | PASS | Section 2.5 defines the Worker status message, the four header chips, `rekeyAge` versus `dhAge`, the 20 minute aging banner, the both-confirms composer gate, and the never-shown list (session id, key bytes, peer address). |
| 10 | Wipe and panic affordances include the keyboard shortcut | PASS | Section 2.6: always-enabled button, double Escape within 800 ms, the layer rule that stops a picker dismissal from wiping, the ended panel countdowns, and the fixed copy. |
| 11 | In-session media gallery is RAM-only | PASS | Section 2.7 table: blob URLs only, raster preview, Save gated on digest, delete removes the node before revoking, drag out blocked, eviction line, one array behind both the gallery and the cards. |
| 12 | Executable shell UX covers chrome, menu, shortcuts, dock badge, dark and light | PASS | Section 3.1 window table, 3.2 menu table, 3.3 shortcut table, 3.4 badge table, 3.5 theming and contrast. Every shell item is tagged EXEC-ONLY in its heading or card. |
| 13 | The discipline section names the temptations and cuts each with reasoning and a threat-model citation | PASS | Section 4 has 14 rows, including accounts, contact discovery, message history, read receipts, editing, search, sync, export, push, telemetry, custom emoji, reaction ledgers, deep links and settings. A script check counted 14 rows and 14 rows containing `03-threat-model.md`. |
| 14 | The file ends with a recommended UI scope for the addendum cards, EXEC-ONLY flagged where the shell is required | PASS | Section 5 has 10 cards, `grep -c '^| UX-'` printed 10. UX-09 and UX-10 are EXEC-ONLY. This SELF-CHECK is the last section of the file, after the source table in section 6. |
| 15 | English, no em dashes or en dashes anywhere | PASS | `grep -rl` for U+2014 and U+2013 over `01-research/output/` printed nothing and exited 1. Code point scan of this file: U+2014 0, U+2013 0, U+2015 0, U+2212 0, U+2012 0. |
| 16 | Every external claim carries a fetched, title-checked URL | PASS | Section 6 lists 8 sources, all fetched in this run: Discord Message Resource, Thonky character capacities, QRcode.com version and module sizes, MDN BarcodeDetector, MDN setAppBadge, Electron Dock, WCAG 2.2 SC 1.4.3, MDN prefers-color-scheme. Titles are quoted as fetched. |
| 17 | No invented numbers. Values are quoted, computed with arithmetic shown, or labelled design defaults | PASS | QR capacities are from the fetched table, module counts from the stated formula. The 650 character code figure is from `04-crypto-design.md` section 3.2; the 800 byte planning figure is labelled inference and its arithmetic is in section 2.4. Reaction caps are labelled design defaults in the section 1.5 table. The reaction map size is labelled arithmetic, not measured. |
| 18 | Read-only mission, only the one output file written in the project | PASS | `ls -lt 01-research/output` shows `13-platform-ux.md` as the newest entry, with every other file at its pre-existing time. Draft part files were written under `~/.hermes/cache/scratch`, outside the repository. No file under `input/`, `01-research/output/01` to `10`, `02-plan/` or `_config/` was edited. |
| 19 | No files beyond this lane's output and no build artifacts | PASS | No HTML, Python or Swift artifact was created in the project. The only project write is this file. |

### Mechanical evidence, verbatim

```
wc -l 01-research/output/13-platform-ux.md       -> 559
grep -c '^## ' 01-research/output/13-platform-ux.md -> 8
grep -rl $'\xe2\x80\x94' 01-research/output/     -> no output, exit=1
grep -rl $'\xe2\x80\x93' 01-research/output/     -> no output, exit=1
code point scan (em, en, bar, minus, figure)     -> 0 0 0 0 0
section 4 rows / rows citing 03-threat-model     -> 14 / 14
grep -c '^| UX-' 01-research/output/13-platform-ux.md -> 10
EXEC-ONLY occurrences                            -> 18
ls 01-research/output/*.md | wc -l               -> 11
```

### Stage note

`01-research/CONTEXT.md` requires 13 output files and the directory held 11 when this lane finished. Files `11-packaging-executable.md` and `12-media-pipeline.md` belong to the peer platform lanes and had not landed at write time. This lane's file is present, non-empty, free of dash violations, and carries this SELF-CHECK. The directory count is the lead's check after the peer lanes land.

### Known limits of this design

- The 800 byte code length is inference from the 650 character V1 figure plus the envelope field sizes. The envelope build must measure the real length, and the QR ceiling decision must follow that measurement, not this estimate.
- QR byte capacity assumes the base64url body contains lowercase characters, so the byte-mode column is used. An uppercase or base32 encoding would raise capacity and could lower the required version.
- The reaction caps, the bucket and the 200 mark session cap are design defaults. No load test was run here; the `react` gate must measure the bucket and the pill count under a flood.
- No browser was driven. This is a design document, so every UI behavior is specified, not observed. The build cards are where the behavior becomes testable.
- The dock badge statement is exact for macOS Electron and marked UNVERIFIED for Windows and Linux in section 3.4.
- The reaction map memory figure is arithmetic on the entry shape, not a measurement.
- The shell section states requirements and deliberately does not pick the wrapper. `01-research/output/11-packaging-executable.md` owns that choice, and the menu and window requirements are written to survive a different wrapper.

STATUS: complete. All 19 lane acceptance items PASS. The two open items are peer-file presence in the stage count and the measured code length, both named above with their owners.
