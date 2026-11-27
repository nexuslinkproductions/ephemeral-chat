# V2 hardening blueprint, ephemeral chat

RUN: w2-ephemeral-hardening-20261126. Lane: synthesis, 1 of 1.
TARGET: `input/ephemeral-chat-v1.html`, 35,598 bytes, SHA-256 `23be3a0b6f53587e50c97c1767fa745980788288145dc79d3dba42095b150337`.
FORM: this is the plan, not the code. The R2 build wave follows it.

Sources, cited by file name throughout:

- `01-trust-map.md`, trust boundaries, wipe paths, crypto reality, claims versus code.
- `02-audit-findings.md`, findings F-01 to F-13 and strengths S-1 to S-8.
- `03-threat-model.md`, nine attacker classes and the top 10 risks.
- `04-crypto-design.md`, pairing, key schedule, AEAD, file format, wipe semantics, measured bundle sizes.
- `05-transport-hardening.md`, observer models, INFRA-tagged transport options.
- `06-ops-defense.md`, kill switch, migration M1 to M5, anomaly rules, monitor design.
- `07-skill-sweep.md`, round plan and gate discipline.
- `08-registry-skills.md`, remote registry and local MCP skill survey, gap coverage.
- `09-open-collections.md`, open security skill collections outside the registries.
- `10-methodology-sources.md`, methodology sources, authored-skill shortlist section 5.3.
- `11-packaging-executable.md`, `../01-research/output/11-packaging-executable.md`, the tri platform shell, its packaging, its integrity pin and its update story.
- `12-media-pipeline.md`, `../01-research/output/12-media-pipeline.md`, video transcode, image re-encode, encryption ordering and in-memory playback.
- `13-platform-ux.md`, `../01-research/output/13-platform-ux.md`, reactions, navigation, session slots, shell UX and the discipline cut list.
- `14-cve-browser-stack.md`, `../01-research/output/14-cve-browser-stack.md`, the browser stack CVE ledger, trust boundaries TB-1 to TB-12 and the R3-BS case register.
- `15-cve-packaging-native.md`, `../01-research/output/15-cve-packaging-native.md`, the wrapper, updater and native trust ledger, TB-W1 to TB-W7, R3-W1 to R3-W10 and BC-W1 to BC-W14.

Owner rulings that bind this plan, from `_config/SETUP.md`:

1. HYBRID form factor (SETUP.md, R18 questionnaire answers). The one-file serverless core is the default and stays fully usable with zero infrastructure. A private relay or tunnel cover mode is optional. Every item that needs standing infrastructure carries the tag INFRA and exists only in that optional mode. The INFRA tag rule itself is `05-transport-hardening.md`, Method and tags, line 11, not an owner ruling.
2. Live test target is Chromium on desktop, macOS, Windows or Linux class (SETUP.md, R18 questionnaire answers). Safari and iOS are stretch targets, not gates.
3. The app stays a single HTML file, no build step, no external assets (SETUP.md line 14, the form factor source added after the plan review; its source is the V1 product sheet `input/ephemeral-chat-overview.pdf`, its no install, build step or dependency line).

Citation rule used below: a design decision cites the research file and section it builds on. Bundle sizes are quoted only from the measured table in `04-crypto-design.md` section 8.1. Where this blueprint chooses a numeric budget that research did not measure, it says "design default" and names the finding that makes a bound necessary.

## 1. THREAT BASELINE

### 1.1 High finding one, the pairing code is an unauthenticated bearer token

The invite and reply codes are base64 of gzip of the complete SDP (`01-trust-map.md`, SESSION LIFECYCLE; `02-audit-findings.md` F-01). The SDP carries the DTLS `a=fingerprint`, the ICE ufrag and password, and the candidate set. The app never displays the fingerprint, never derives a short authentication string, and never asks either user to compare anything (`03-threat-model.md` section 0.1: the strings fingerprint, SAS, verify and safety are absent from the file).

Consequence: anyone who can write to the code channel replaces the fingerprint and the candidates, becomes the DTLS endpoint on both legs, and both users see a normal connected state. RFC 8827 section 6.5, Communications Security, says the security characteristics MUST include "some mechanism to allow an out-of-band verification of the peer, such as a certificate fingerprint or a Short Authentication String (SAS)"; V1 has the material but no check (`02-audit-findings.md` F-01). An on-path attacker who can only observe is still blocked by DTLS fingerprint verification, which is strength S-5. The defect is specific to a writable or leaked code channel, and `03-threat-model.md` ranks it risk 1 with score 15.

The second, softer edge of the same defect is that the code has no version, session id, timestamp, or one-time flag (`01-trust-map.md`, SESSION LIFECYCLE; `03-threat-model.md` class 3). Replay produces a failed connection rather than an auth bypass, but a stale or reused code cannot be distinguished from a fresh one, and a leaked code is valid until the tab closes.

### 1.2 High finding two, truncated transfers export zero padding with Save live

`endIncoming` computes `bytes = bad ? buffer.slice(0, offset) : buffer` (`02-audit-findings.md` F-02, source lines 1044 to 1051). On a short transfer `bad` is false and `offset` is below the declared size, so the exported Blob is the entire preallocated buffer, not the received prefix. A 50 MiB declared transfer that delivers 1 KB exports the full 52,428,800 byte buffer, which is about 52.4 million zero bytes appended. `02-audit-findings.md` F-02 computes 49,999,000 for a declared size of 50,000,000 bytes, a decimal-MB convention the V1 cap does not use: `MAX_FILE = 50 * 1024 * 1024` at source line 427. `card.done` runs first and unhides the Save anchor at lines 981 to 983; the incomplete check at 1051 only changes the footer text and never removes the link or the Blob.

This is data loss and a memory amplification primitive in one sequence: about 1 KB of peer traffic forces a 50 MiB typed array plus a 50 MiB Blob, repeatable on every `file-end` (`02-audit-findings.md` F-02). The preallocation is also eager, so a `file-start` alone pins 50 MiB with no bytes sent (`01-trust-map.md`, DATA FLOW; `05-transport-hardening.md` section 5.3). `06-ops-defense.md` section 2.1 records the follow-on problem: the completed transfer already holds two copies of the bytes (the receive buffer and the Blob), so overwriting the receive buffer alone does not reach the export.

### 1.3 Top 10 risks accepted from the research

Scores are likelihood times impact from `03-threat-model.md` section 11. Disposition is what V2 does about each.

| Rank | Risk | Class | Score | V2 disposition |
|---|---|---|---|---|
| 1 | Pairing code read or substituted, attacker becomes the peer | 3 | 15 | FIX. Safety number over the full transcript, content gated on human confirmation, code TTL and single use. Residual is click-through, section 5. |
| 2 | Pairing code persists in the OS clipboard or clipboard history | 3, 6 | 15 | MITIGATE. Copy only on explicit click, clear the textarea 30 s after a copy when the page still has focus, keep a Show button that regenerates the code, clear the clipboard only on kill, disclose that history may keep a copy. This follows `06-ops-defense.md` section 3.5: clear the textarea, not the clipboard, because clipboard history keeps the copy anyway. |
| 3 | A swapped or backdoored HTML file is loaded | 9 | 15 | NOT SOLVED IN APP. Published hash and signature are ops, not code (`03-threat-model.md` class 9, `07-skill-sweep.md` R1 policy). Disclosed in residual risk. |
| 4 | Screenshot or shoulder surfing captures the transcript | 6 | 12 | MITIGATE. Blank the transcript on blur and visibilitychange, click to reveal, tight idle wipe. Cannot stop OS capture (`04-crypto-design.md` section 6). |
| 5 | A malicious extension or compromised browser reads the session | 7 | 10 | OUT OF SCOPE. Monitor is a witness in a separate process. Stated in first-run text (`03-threat-model.md` class 7). |
| 6 | Disk, swap, hibernation or crash dump holds plaintext | 6 | 10 | DISCLOSE. OS checklist and honest copy; no in-page fix exists (`04-crypto-design.md` section 6, `06-ops-defense.md` section 5). |
| 7 | Public STUN operator correlates the session or is blocked | 8 | 10 | MITIGATE. Three independent STUN providers in default mode, optional relay cover mode. Correlation and block remain. |
| 8 | A passive network observer profiles the session | 1 | 10 | DISCLOSE. Default mode is classified and blockable with one rule (`05-transport-hardening.md` section 1.3). Cover mode, the optional infrastructure path in section 2.6, is the only answer. |
| 9 | A malicious peer floods the channel and exhausts the tab | 4, 5 | 9 | FIX. Inbound budgets, pre-parse caps, log row cap, A8 rate rule. |
| 10 | User saves and opens a malicious file from the peer | 4 | 8 | MITIGATE. Completeness and digest gate before Save, real type shown, warning on executable types, raster-only preview. The final click remains the user's. |

### 1.4 The rest of the findings ledger

Every finding must close or be explicitly accepted. Card ids map to section 4.

| Finding | Sev | V2 disposition | Card |
|---|---|---|---|
| F-01 pairing code is an unauthenticated bearer token | High | SAS over the full transcript, content gated on human confirmation, versioned envelope with a TTL and single use. Section 1.1. | R2-04, R2-07 |
| F-02 truncated transfer exports zero padding with Save live | High | Lazy parts array, digest and completeness gate before Save, export only the received span. Section 1.2. | R2-05 |
| F-03 retained blob memory, no session budget | Med | Session byte and file count cap, revoke after Save or after a small ring. | R2-06 |
| F-04 one invalid file-start disables all later receives | Med | Per-transfer state machine with an id and a timeout, reject cleared on end or timeout, later starts accepted. | R2-06 |
| F-05 gzip bomb in `unpack` | Med | Cap the pasted code and the decompressed output before parsing; the code envelope carries its own length. | R2-07 |
| F-06 unbounded transcript DOM, no rate limit | Med | Log row cap, per-session frame and byte budgets, screen reader safe trimming. | R2-06 |
| F-07 attacker chosen ICE candidates emit UDP probes | Med | Cap candidate count and SDP size before setRemoteDescription; no inbound answer without a user paste. | R2-07 |
| F-08 `pagehide` is a partial wipe | Low | `pagehide` runs the full in-page wipe: codes, draft, blob URLs, receive buffer. | R2-08 |
| F-09 passive listener makes expiry preventDefault a no-op | Low | Register the idle-expiry activity handler non-passive, or cancel the drop default in the guard. | R2-08 |
| F-10 `?idle=` lets a link shorten the session | Low | Remove the URL override from the production artifact; inbound traffic bumps and an active transfer pauses idle. | R2-08 |
| F-11 meta CSP cannot frame-guard | Low | Documented residual; a server header is the only fix and there is no server by ruling. | residual 16 |
| F-12 file id never validated, positional reassembly | Low | Envelope carries id and chunk index, AAD binds both, mismatch rejects the file. | R2-05 |
| F-13 peer controls saved filename including bidi controls | Low | Strip bidi and control characters from the display name, show the real type, warn on executable types. | R2-05 |

## 2. V2 ARCHITECTURE

Two modes, one artifact family. Default mode is the serverless single HTML file and carries no INFRA item. Cover mode is the same app with a relay configuration block enabled, marked INFRA, and is the only place standing infrastructure appears.

| Capability | Default mode | Cover mode, INFRA |
|---|---|---|
| Pairing | Safety number, code envelope v2 | Same |
| App-layer crypto | Three-DH, double ratchet, AES-GCM | Same |
| Peer IP visible to the other peer | Yes, in the code (inference, sample UNVERIFIED) | No, relay candidates only |
| Third party in the path | Public STUN only | Private TURN relay |
| Wire detectability | Classifiable, disclosed | TLS to one relay host |
| Monitor | Optional separate app | Optional separate app |

### 2.1 Pairing and verification

DECISION: safety numbers (SAS) are the default and the only gate on content. Balanced SPAKE2 is an opt-in second mode, deferred to V2.2. The code gains a versioned envelope with a session id, an issue time, a 120 second TTL and single use.

Mechanism, default mode:

```
th  = SHA-256("eph-v2-transcript" || sort(fpA, fpB) || sort(ephA, ephB) ||
              sort(statA, statB) || suite_id)
sas = SHA-256("eph-v2-sas" || th)
display = 12 groups of 5 decimal digits (60 digits)
rk  = HKDF-SHA256(salt = 32 zero bytes, ikm = dh_concat,
                  info = "eph-v2-root" || th, 32)
```

Rules:

1. Both users compare the 60 digits over a channel the attacker does not control, ideally voice or in person. The composer and all content frames stay locked until each side records a local confirmation.
2. The frame router drops every `msg`, `file-start` and chunk before confirmation and counts the drop. Only `sas-confirm`, `sas-bad` and `panic` are accepted in the pre-confirm state. This is the rule `04-crypto-design.md` section 1.2 names as the pairing for a human check.
3. The transcript covers the app public keys and the suite id, not only the DTLS fingerprint, so the number is a statement about the keys actually in use (`04-crypto-design.md` section 1.5).
4. A mismatch aborts the session with a visible reason. There is no override that silently continues; an override is a separate, logged action if the owner wants one.
5. The suite id is displayed next to the number. If X25519 is unavailable and P-256 is negotiated, the number and the label change, so a downgrade is visible (`04-crypto-design.md` section 8.2).

Code envelope:

```
E2.<version>.<base64url(gzip({ v, sid, ts, sdp, eph_pk, stat_pk, suite }))>
sid    = 16 random bytes, hex
ts     = issue time, epoch milliseconds
eph_pk = per-session ephemeral X25519 (or P-256) public key
stat_pk = per-session static public key
```

The app public keys travel inside the code envelope, not over the data channel. That is what lets both sides compute the SAS before any content frame exists, and it keeps the pre-confirm router down to `sas-confirm`, `sas-bad` and `panic` (`04-crypto-design.md` sections 1.2 and 2.1).

Receiver rules: reject a code over 16 KB before decode, reject a decompressed payload over 64 KB before parsing, reject `ts` older than 120 seconds, reject a `sid` already consumed on this page. These caps are the ones `03-threat-model.md` class 3 lists as the cheap guard against the gzip bomb and the oversized SDP, and the TTL and single-use rules are `06-ops-defense.md` section 3.5. The candidate count is capped at a design default of 32 before `setRemoteDescription`, which bounds the ICE probe surface in F-07. The 120 second TTL is the ops lane's value. If R4 shows that human code exchange routinely exceeds it, raise it to the ICE lifetime and record the change, because a TTL users work around by disabling the check is worse than a slightly longer window.

SPAKE2, opt-in:

- Balanced SPAKE2, not SPAKE2+. The augmented variant requires a verifier registration record, which contradicts zero persistence and adds state the kill switch would have to wipe (`04-crypto-design.md` section 1.3).
- Six digit password typed by both users, three attempts, hard abort. The online guessing bound is about 3 in 10^6 per session (`04-crypto-design.md` section 1.3).
- It needs P-256 point addition and arbitrary point hashing, which WebCrypto does not expose, so it needs a curve library. No P-256 bundle is measured anywhere in `04-crypto-design.md`. The 32,503 byte minified and 13,720 gzipped figure is the noble x25519 row of section 8.1 only, and the 32.5 KB in section 1.3 is an estimate for noble-curves, not a P-256 measurement. The smallest measured row in section 8.1 is TweetNaCl `nacl.min.js` at 18,456 bytes minified and 6,704 gzipped, which has no P-256 point arithmetic and so cannot carry SPAKE2. The SPAKE2 library cost is therefore unmeasured; the nearest measured rows are noble x25519 at 32,503 and noble core at 36,426, and neither includes P-256 point addition.
- Build conflict, stated rather than hidden: noble ships ESM and needs one esbuild pass. The owner ruling forbids a build step for the app. Resolution: the SPAKE2 mode ships as a separate prebuilt single HTML file, produced once by the maintainer, still with no runtime dependency and no build step for the user. The default artifact never contains it. If the owner will not allow even that, SPAKE2 waits until a paste-in curve implementation exists.
- OPAQUE is rejected and recorded as rejected (`04-crypto-design.md` section 1.4). It needs a server and a credential record.

What this does not fix: a user who clicks through the comparison gets no protection, and the SAS proves that both sides derived the same keys, not that the other person is who they claim (`04-crypto-design.md` sections 1.2 and 5.1). Both limits go in the first-run copy.

Cites: `04-crypto-design.md` sections 1.2, 1.3, 1.4, 1.5, 8.1, 8.2; `06-ops-defense.md` section 3.5; `03-threat-model.md` class 3.

### 2.2 Application-layer crypto stack

DECISION: three-DH X25519 initial agreement, HKDF-SHA256 root, double ratchet with header encryption deferred to V2.1 as `04-crypto-design.md` section 2.3 recommends, AES-256-GCM per message, all inside a dedicated Worker. WebCrypto only. Zero library bytes in the default artifact.

Key schedule:

```
ikm = X25519(ephA, ephB) || X25519(ephA, statB) || X25519(statA, ephB)
rk  = HKDF-SHA256(salt = 32 zero bytes, ikm = ikm, info = "eph-v2-root" || th, 32)

KDF_RK(rk, dh_out) = HKDF-SHA256(salt = rk, ikm = dh_out,"eph-v2-ratchet", 64)
                     -> (new_rk, new_ck)
KDF_CK(ck)         = HMAC-SHA256(ck, 0x01) -> mk
                     HMAC-SHA256(ck, 0x02) -> next_ck
```

Per-message AEAD:

```
key   = HKDF-SHA256(ikm = mk, salt = 32 zero bytes, info = "eph-v2-aead", 32)
nonce = 12 zero bytes
aad   = "eph-v2-msg" || direction || counter
```

The invariant, enforced with an assertion, is that `mk` is never used twice and the counter is strictly monotonic per direction. A fresh key per message is what makes a constant nonce safe, and it removes the reason to prefer an extended-nonce cipher (`04-crypto-design.md` section 4.1). AES-256-GCM is chosen over XChaCha20-Poly1305 because it costs zero bytes and uses hardware AES (`04-crypto-design.md` section 4.2).

Ratchet shape:

- State per peer: root key, sending and receiving chain keys, current DH pair and peer public key, message counters, previous chain length, and a bounded 32-entry skipped key map.
- The data channel is ordered and reliable, so the skipped map only covers the turn overlap. The ceiling is recorded: if transport moves to unordered or a reordering relay, the cache size and replay window must be revisited (`04-crypto-design.md` section 2.2).
- DH ratchet on turn change, one X25519 operation per turn, not per message.
- Header encryption is deferred to V2.1, which is what `04-crypto-design.md` section 2.3 recommends ("encrypt headers for message frames in V2.1"). This blueprint does not pull it forward into R2 and says so rather than re-sequencing silently. Without it every frame leaks `dh_pub, PN, N` to a relay or observer, which reveals message counts and turn structure; lane 5 cannot close that at the transport layer. The V2 artifact ships with that metadata leak and V2.1 closes it. File chunk frames do not need header encryption because they sit inside a file key with a counter nonce.

Where keys live:

- All key material and the ratchet live in a dedicated Worker, built from an inline Blob so the artifact stays one file. The CSP adds `worker-src blob:` and keeps `default-src 'none'`.
- The main thread holds ciphertext and UI state only. `worker.terminate()` on kill is the closest thing a browser has to deterministic heap destruction (`04-crypto-design.md` section 7.2).
- Raw chain keys live in `Uint8Array` and are `.fill(0)` on every advance. Symmetric keys are derived as non-extractable `CryptoKey` objects, so the per-message key never exists as readable bytes. No hex, no base64, no `JSON.stringify` of a key (`04-crypto-design.md` section 7.1).
- A per-session static X25519 key is generated at invite time and destroyed at wipe. There are no long-term identity keys and no signatures, which preserves deniability (`04-crypto-design.md` section 5.1).

Fallback and negotiation: use X25519 when `crypto.subtle.deriveBits` accepts it, otherwise ECDH P-256. The suite id goes into the SAS transcript and is displayed next to the number (`04-crypto-design.md` section 8.2).

Bundle budget, measured numbers from `04-crypto-design.md` section 8.1. Nothing in this table is inlined in the default build. The table exists to price the optional variants and to justify saying no.

| Component | Minified bytes | gzip -9 | Role |
|---|---|---|---|
| WebCrypto AES-GCM, HKDF, SHA-256, ECDH, X25519 | 0 | 0 | Default, native |
| noble x25519 | 32,503 | 13,720 | Only if X25519 must be guaranteed in JS |
| noble core, x25519 + hkdf + sha256 + hmac | 36,426 | 15,216 | Same, bigger surface |
| noble xchacha20poly1305 | 11,383 | 4,796 | Non-WebCrypto harness only |
| noble ml-kem | 23,232 | 9,779 | V3 PQ variant |
| tweetnacl `nacl.min.js` | 18,456 | 6,704 | Paste-in fallback, smallest audited |
| tweetnacl `nacl-fast.min.js` | 32,110 | 10,570 | Faster paste-in variant |
| libsodium-wrappers | 101,748 | 13,477 | Rejected, plus a wasm payload |

Default build size: V1's 35,598 bytes plus roughly 4 to 6 KB of new source and no new dependency bytes (`04-crypto-design.md`, RECOMMENDED STACK closing line). PQ hybrid ML-KEM is a V3 separate build; the ratchet stays classical in V2 because a PQ ratchet is a multi-week job with new failure modes and no value for a 30 minute session (`04-crypto-design.md` section 3.3).

Cites: `04-crypto-design.md` sections 2.1, 2.2, 2.3, 3.3, 4.1, 4.2, 5.1, 7.1, 7.2, 8.1, 8.2.

### 2.3 File transfer integrity

DECISION: authenticated chunks, a per-file key, a digest at the end, export only the received span, and Save is created only after completeness and digest both pass.

Wire format, from `04-crypto-design.md` section 4.3:

```
file-start  { k, id, name, size, type, chunks, key_wrapped, nonce_prefix }
              key_wrapped = AES-GCM(HKDF(mk, "eph-v2-wrap"), file_key)
chunk i      AES-256-GCM(file_key, nonce = prefix(4) || be64(i),
                         aad = id || i || size || chunks)
file-end     { k, id, digest = SHA-256(plaintext) }
```

Rules, numbered so the build cards can cite them:

1. The file key is 32 random bytes, wrapped under a key derived from `mk`, and zeroed immediately after the wrap. The wrap uses its own `info` string, never `mk` directly, because the body is also encrypted under `mk` and two calls with one key and one constant nonce is the reuse this design exists to prevent (`04-crypto-design.md` section 4.3).
2. Chunk size 64 KiB. A 50 MiB file is 800 GCM calls instead of 3,200 at 16 KiB, with the same tag overhead.
3. Nonce is a 4 byte random prefix per file plus an 8 byte big-endian counter. The prefix must not derive from the file id, because the id is peer supplied.
4. AAD binds id, chunk index, declared size and chunk count. A truncated, reordered, or misattributed chunk fails the tag.
5. Reject the whole file on any tag failure. Never render a partial image and never keep partial plaintext.
6. Allocation is lazy: received plaintext chunks go into a parts array. The declared size is checked against `MAX_FILE` before any allocation, but the app does not allocate 50 MiB up front. This keeps the S-3 principle, cap before allocate, and removes the eager 50 MiB pin from F-02 and F-03.
7. At `file-end`, concatenate only if `received === size` and the SHA-256 of the plaintext matches the digest. Only then build the Blob and the object URL.
8. Export only the received span. On completion the concatenation is exactly `size` bytes of verified plaintext. On any failure nothing is exported: no Blob, no object URL, no anchor. The old `bad ? slice(0, offset) : buffer` branch is deleted, not guarded. This is the direct fix for F-02.
9. Save gating: the anchor exists in the DOM only in the success branch, with `href` and `download` assigned at the same moment. On any failure the card shows a failed state and no anchor exists. Ordering is Save last, never Save then mark incomplete (`02-audit-findings.md` F-02; `01-trust-map.md`, DATA FLOW step 6).
10. Filename hygiene: strip Unicode bidi controls and C0 control characters, keep the 200 character cap, display the real MIME type, and warn on `text/html`, `image/svg+xml` and executable extensions (`02-audit-findings.md` F-13).
11. Never write to disk. No download starts until the user clicks Save, and that click is the only place plaintext leaves the page; received plaintext lives in the parts array until then (`04-crypto-design.md` section 4.3 rule 8, which is also V1's current behaviour and is kept rather than replaced).

Resource budgets, design defaults chosen to bound what the findings show is unbounded:

| Budget | Value | Why |
|---|---|---|
| Per file | 50 MiB, unchanged | V1 cap, S-3, `04-crypto-design.md` section 4.3 |
| Retained received files | 4, or 200 MiB per session, whichever first | F-03 shows 20 files retain about 1 GB |
| Log rows | 2,000, oldest trimmed | F-06 shows no cap and a 1 GB text case |
| Pre-parse text frame | 64 KB | `03-threat-model.md` class 4 option 2 |
| Transfer idle timeout | 60 s without progress aborts that file | F-04 stuck stub and eager allocation |
| Frame rate | 40 frames/s for 5 s, or 2 MB/s with no transfer active, kills | `06-ops-defense.md` rule A8 |

Memory ceiling, labelled as inference: a 50 MiB file costs about 50 MiB of ciphertext plus 50 MiB of plaintext at peak, and Blob construction may copy once more. That is 100 to 150 MB of tab memory, acceptable on desktop and risky on iOS, which is a stretch target (`04-crypto-design.md` section 4.3).

Cites: `04-crypto-design.md` sections 4.3 and 4.4; `02-audit-findings.md` F-02, F-03, F-04, F-12, F-13; `01-trust-map.md`, DATA FLOW; `06-ops-defense.md` rule A8.

### 2.4 Versioned control envelope

DECISION: one envelope for every frame, one dispatch table, and an explicit counted branch for anything unknown. No frame is ever dropped silently.

```
{ v: 1, k: "<type>", sid, seq, ... }
```

Known types: `msg`, `file-start`, `chunk-meta`, `file-end`, `sas-confirm`, `sas-bad`, `panic`, `rekey`, `rekey-ok`, `mig`. The `mig` type carries the M1 to M5 step field from section 2.5.

Router rules:

1. Parse JSON inside the envelope. A malformed frame increments `unknownFrames`, shows a system line, and never passes to a handler.
2. Unknown `k` increments `unknownFrames` and shows the value. Unknown `v` shows "peer is newer" or "peer is older" and refuses content. Both are visible states, not silent returns.
3. Three unknown frames in 10 seconds runs Kill. This is rule A1 in `06-ops-defense.md` section 2.4, and its version-skew false positive is why the `v` field exists.
4. `seq` is monotonic per direction. A gap is a live event, not a crash: it triggers a resync request once, then Kill.
5. `sid` must match the pairing envelope's sid. A frame from a stale session is rejected before any handler runs.

Why this is the first build card: `06-ops-defense.md` section 1 records that the protocol has exactly three inbound types, `msg`, `file-start` and `file-end`, and that invalid JSON is dropped at line 828. Adding `panic` or migration frames to that router without a version and a counted default branch produces the exact failure the ops lane names: a control frame that vanishes with no evidence. The envelope is the prerequisite for sections 2.1 and 2.5.

Cites: `06-ops-defense.md` sections 1, 2.3, 2.4, 3.3.

### 2.5 Kill switch, rotate and migration

DECISION: three distinct actions with fixed names, and the wipe fixes that make the existing kill path complete.

| Action | What it does | When | Source |
|---|---|---|---|
| Kill | Destroys local state, closes the peer, terminates the Worker, navigates to about:blank | Suspected breach, anomaly, panic, user choice | `04-crypto-design.md` section 7.3, `06-ops-defense.md` section 2.5 |
| Rotate | In-channel X25519 rekey with a MAC acknowledgement, same session and same codes | "Rotate keys now", or the 20 minute aging prompt | `04-crypto-design.md` section 7.3, `06-ops-defense.md` section 3.7 |
| Migrate | New RTCPeerConnection, new certificate, new SDP, new codes, M1 to M5 | Code leakage, session aging, fresh identity | `06-ops-defense.md` section 3.3 |

Naming note: `04-crypto-design.md` calls the owner's "migrate both peers to a fresh keyset" the Rotate path, while `06-ops-defense.md` uses migration for a whole new connection. Both are real and they are not the same operation. This blueprint fixes the words: Rotate changes keys inside the channel, Migrate changes identity and codes. The UI exposes "Rotate keys" and "New session", and Kill is the only path that ends the session.

Kill sequence, ordered, from `06-ops-defense.md` section 2.5:

1. Set `sessionEnded`, disable input, clear the composer. Stop new data first.
2. Send `{k:"panic"}` if the channel is open, no await, best effort.
3. `closePeer()`, then clear idle, disconnect and anomaly timers.
4. Clear the log DOM before revoking blob URLs, because image and anchor nodes hold the blob references (`06-ops-defense.md` section 2.1 ordering note).
5. Clear all five textareas and the file input.
6. Revoke every object URL and empty the array.
7. Overwrite every received plaintext part and the reassembly buffer with random bytes, then drop them.
8. Drop the send queue and file handles.
9. Attempt clipboard clear only if a code was copied and the page still has focus.
10. Show the ended panel with the reason, then `location.replace('about:blank')` at 4 seconds, or 1.5 seconds on the anomaly path. Never `window.close()`, which browsers refuse for tabs the script did not open.

Availability: the Wipe button is enabled at every stage, including before connection. Remove the `disabled` attribute at line 354 and the enable gate at line 676; `closePeer` is already null safe and `endSession` is already idempotent (`06-ops-defense.md` section 2.2). Add double Escape within 800 ms, working when focus is inside a textarea.

Wipe completeness fixes required by the baseline:

1. `pagehide` runs the same in-page wipe as Kill, minus navigation: codes, draft, blob URLs, receive buffer, log. V1 clears only the log, so the SDP with fingerprint, ufrag, pwd and candidates survives the handler (`02-audit-findings.md` F-08; `01-trust-map.md`, WIPE PATHS).
2. The `?idle=` URL override is removed from the production artifact. A link can no longer force a 5 second session (`02-audit-findings.md` F-10). A test build may keep it behind a build-time constant.
3. Inbound traffic counts as activity, and an active transfer pauses the idle timer. V1 bumps only on local UI events, so a slow 50 MiB receive can be wiped mid flight (`03-threat-model.md` class 5; `01-trust-map.md`, CONSEQUENCES FOR HARDENING item 5).
4. The drop handler cancels the browser default before returning on the ended path, or the activity listener is registered non-passive, so a dropped file cannot replace the ended screen (`02-audit-findings.md` F-09).
5. Codes are cleared from the textareas on `pagehide` and 30 seconds after a copy, with a Show button that regenerates the display. The clipboard is cleared only on kill, and only when a code was copied and the page still has focus (`06-ops-defense.md` sections 3.5 and 2.5).

Migration M1 to M5, in-band over the old authenticated channel (`06-ops-defense.md` section 3.3):

| Step | Sender | Frame | Receiver check |
|---|---|---|---|
| M1 | Offerer | `{k:"mig", step:"offer", sid, fp, code}` | `sid` is new, no migration active; store `sid` and `fp`; create the new peer and answer |
| M2 | Answerer | `{k:"mig", step:"answer", sid, fp, code, check}` | `sid` matches; `check` equals the first 6 hex of SHA-256 over `sid`, `fp_offer` and `fp_answer` |
| M3 | Both | `{k:"mig", step:"commit", sid, fp_self, fp_peer}` on the new channel | `fp_peer` equals the fingerprint actually in the peer SDP and matches the M1 and M2 commitment |
| M4 | Both | `{k:"mig", step:"done", sid}` on the old channel | Close the old peer, clear the old log, adopt the new objects |
| M5 | Both | timeout at 15 s on any step | Close both peers, Kill with reason `migration-failed` |

State discipline: one `pending` object `{pc, dc, sid, fp, role, deadline}`, one `adopt(pending)` function that swaps the globals and clears the old log, and the Kill path closes `pending.pc` as well as `pc` (`06-ops-defense.md` section 3.7). Migration is refused while a file transfer is active, and a tie between two initiators is broken by the lexicographically lower current DTLS fingerprint.

Rotate, from `04-crypto-design.md` section 7.3: both sides generate a fresh X25519 pair, exchange `{k:"rekey", pk}`, derive `RK' = HKDF(salt = old_RK, ikm = DH(new_sk, peer_pk), info = "eph-v2-rekey", 32)`, reset both chains, zero the old root and chain keys, and acknowledge with `{k:"rekey-ok", mac}` where the MAC is over the new root. A failed MAC is a hard kill. A soft rekey over a channel the attacker already controls does not remove the attacker; it limits how much future traffic one compromised key can read.

Cites: `04-crypto-design.md` section 7.3; `06-ops-defense.md` sections 1, 2.1, 2.2, 2.5, 2.6, 3.3, 3.5, 3.7; `02-audit-findings.md` F-08, F-09, F-10.

### 2.6 Transport

DECISION: default mode keeps the serverless chain and adds only zero-infrastructure hardening. Cover mode is the single optional INFRA path.

Default mode, no INFRA item:

1. Keep the existing default-deny chain intact: no listener at rest, undiscoverable 5-tuple, ICE short-term credentials, DTLS cookie, certificate fingerprint, SCTP inside DTLS, DCEP, and 30 second consent freshness (`05-transport-hardening.md` section 4.1). This chain is the reason unsolicited traffic has no path to an answer, and V2 must not weaken it.
2. STUN diversity: three independent providers in a declared fallback order, with the provider that answered recorded in the code. The fallback order is design intent for error reporting and for which URL the code reports, not a browser mechanism: the browser gathers from every configured STUN URL (inferred from standard ICE behaviour, R3 re-derives), so a capture can legitimately show more than one. Section 4.4 pass condition 3 states what the capture accepts. A single provider block currently looks identical to a peer failure (`05-transport-hardening.md` section 5.1, recommendation A2).
3. Error split: a gathering or pre-connection `failed` state reports "network blocked", distinct from peer loss after connection (`03-threat-model.md` class 2 hardening option 5, `05-transport-hardening.md` section 1.3).
4. Honest disclosure in the pairing UI: the code is expected to carry the public IP and port, a VPN changes the egress address, and default mode does not hide who is talking to whom (`05-transport-hardening.md` section 7.1 item 4). The address-in-code claim is inference from the source chain and standard WebRTC behaviour (RFC 8445), not an observed live run: the SDP sample behind it is marked UNVERIFIED in `05-transport-hardening.md` section 1.1 ("no artifact backs this sample, R3 must re-derive the live run"), and R3 re-derivation is the closer. No anonymity claim anywhere.
5. Detectability disclosure: default mode is identifiable as WebRTC and blockable with one firewall rule (`05-transport-hardening.md` section 1.3). The product says so rather than implying stealth.
6. Keep non-trickle ICE as it is. That the app delivers candidates in one blob after gathering is source-verified (lines 687 to 704, 761, 792), so the session is non-trickle in practice. The claim that `a=ice-options:trickle` is a browser default leftover rests on the SDP sample in `05-transport-hardening.md` section 1.1, which that file marks UNVERIFIED, flagged by the stage review, with no artifact behind it; R3 re-derives the live run and confirms or drops the attribute claim.

Cover mode, INFRA, optional:

- coturn with `iceTransportPolicy: "relay"`, `turns:` on 443, and short-lived TURN REST credentials rather than a static user and password (`05-transport-hardening.md` sections 2.1 and 2.2).
- With relay forced, the code contains relay candidates only, so the peer IP and the LAN mDNS name are absent (`05-transport-hardening.md` section 2.1).
- Cost, stated: every byte crosses the relay twice, a 50 MiB file becomes 100 MiB of relay egress, and the relay operator sees both source IPs and the volume (`05-transport-hardening.md` section 2.1). The operator becomes a metadata holder, which is a real change in trust position.
- This is the only place INFRA items live: the relay host, its certificate and credential issuer, and any later REALITY or ECH front (`05-transport-hardening.md` sections 3.6 and 7.2). The default artifact contains zero relay configuration and a gate asserts it.

Not building, with reasons from `05-transport-hardening.md` section 7.3: a pre-auth proof of work (it cannot run below the browser DTLS stack), classic domain fronting as a primary transport (closed by the major clouds between 2018 and 2024), plain WireGuard sold as undetectable (its own ecosystem ships a fork to fix the signature), SDP address rewriting (breaks ICE and hides nothing), and a custom pairing protocol (use SPAKE2 if a short code is ever needed).

Cites: `05-transport-hardening.md` sections 1.1, 1.3, 2.1, 2.2, 3.6, 4.1, 5.1, 7.1, 7.2, 7.3; `03-threat-model.md` classes 1, 2, 8.

### 2.7 Monitor overlay

DECISION: a separate native macOS menu bar app in a separate trust domain. It is a witness, not a guard, and it is not part of the HTML file.

Architecture, from `06-ops-defense.md` section 4.1:

- Separate process, launched by launchd with `KeepAlive`, started at login.
- Separate bundle identifier and code signing identity, installed by the user, never loaded by the browser.
- Separate input path: public system counters and kernel APIs only. No HTTP listener, no WebSocket, no AppleScript, and no command channel. A listener would let a compromised page switch the monitor off, so no listener is a security property.
- Separate failure domain: a hash-chained append-only log under `~/Library/Application Support`, which the browser cannot write. A killed monitor restarts and the gap is visible in the log.

Placement: menu bar `NSStatusItem` as the always-on surface with green, amber and red states, plus a user notification on transitions. A floating HUD appears only for a critical event and can be dismissed. No permanently floating HUD; it is the first feature users disable (`06-ops-defense.md` section 4.2).

Signals and rules, from `06-ops-defense.md` sections 4.3 and 4.4:

| Rule | Condition | Action |
|---|---|---|
| M1 unexpected network | Browser outbound rate above five times its 10 minute median for 30 s | Amber banner and log |
| M2 camera or microphone | Device activation while the chat tab is frontmost | Red alert, sound, HUD, log |
| M3 clipboard churn | More than three clipboard changes in 60 s while chat is frontmost | Amber banner, counts only |
| M4 load | Browser CPU above 80 percent for 60 s, or memory above 2 GB | Amber banner, log |
| M5 monitor gap | Heartbeat missing for more than 10 s, detected on restart | Red alert with the gap duration |

Watched signals: browser frontmost, `lsof` connections by browser PID, `nettop` per-process bytes, `ps` CPU and RSS, `NSPasteboard.changeCount` as an event only, camera and microphone activation, new listening ports, and the monitor's own heartbeat. Deliberately not watched: browser history, page content, keystrokes, and the chat's memory (`06-ops-defense.md` section 4.3).

What it cannot do, stated in the About window: it cannot see inside DTLS, cannot attribute traffic per tab, cannot prove the absence of an attack, cannot block the chat, and loses to root or to the same user killing it (`06-ops-defense.md` sections 4.1 and 4.6). The monitor must be able to fire on every rule; a monitor that always shows green is a defect of its own (`07-skill-sweep.md` section 3.5 mapping).

Cites: `06-ops-defense.md` sections 4.1, 4.2, 4.3, 4.4, 4.6; `03-threat-model.md` class 7; `07-skill-sweep.md` section 3.5.

## 3. WHAT STAYS

The eight V1 strengths from `02-audit-findings.md` are preserved by name. Each row states the evidence and the V2 obligation, so a build card can be checked against it.

| Id | Strength | V1 evidence | V2 obligation |
|---|---|---|---|
| S-1 | No HTML injection sink | Zero hits for `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, `eval`, `new Function`, `DOMParser`, `srcdoc`, `createContextualFragment`; every peer string reaches the DOM through `textContent` at lines 522, 534, 938, 942, 992 (`02-audit-findings.md` S-1) | Keep the grep at zero. Every new surface uses `textContent`: SAS digits, suite label, envelope errors, migration step text, digest failure, filename. No template strings that build HTML. |
| S-2 | No persistence APIs | Zero hits for `localStorage`, `sessionStorage`, `indexedDB`, `document.cookie`, `serviceWorker`, `caches`; `endSession` revokes blobs, clears the log and textareas, is idempotent via `sessionEnded` (`02-audit-findings.md` S-2) | SAS confirmation, consumed code ids, migration `pending` state and rotate counters stay in memory only. No storage API for any of them. A reload loses the session, which is the intended behavior. |
| S-3 | Receiver caps size before allocating | `beginIncoming` rejects non-finite, zero, negative and above `MAX_FILE` before `new Uint8Array(size)` at lines 1000 to 1005; `addChunk` clamps by room (`02-audit-findings.md` S-3) | Keep the check before any allocation. Replace the eager 50 MiB allocation with a parts array, and add the session total and file count budget. The principle is cap first, not allocate first. |
| S-4 | Framing fails closed on stray frames | Binary with no active transfer dropped, `file-end` with no transfer is a no-op, rejected transfer cleared on `file-end`, unknown code format throws (`02-audit-findings.md` S-4) | Keep fail closed, and make the default branch counted and visible. An unknown frame is never passed to a handler and never silently returns. |
| S-5 | On-path-only MITM is blocked | DTLS verifies the peer certificate against the fingerprint in the SDP; ICE consent expires after 30 seconds per RFC 7675; `connectionstatechange` maps failure to `endSession('peer')` at lines 635 to 651 (`02-audit-findings.md` S-5) | Keep DTLS as the transport identity. Add the SAS for the writable-code case, do not replace DTLS. Cover mode must relay DTLS records without terminating them. |
| S-6 | Capability reduction in the policy | `default-src 'none'`, `img-src blob: data:`, `base-uri 'none'`, `form-action 'none'`, `referrer no-referrer` at lines 6 and 7; no third-party code, fonts, analytics or assets (`02-audit-findings.md` S-6) | Keep every directive. Add `worker-src blob:` for the inline Worker and nothing else. No external origin is ever added. |
| S-7 | Idle wipe is local and peer independent | `checkIdle` on an interval at 1136 plus `visibilitychange` at 1137 and `pageshow` at 1147; a silent peer cannot extend the session (`02-audit-findings.md` S-7) | Keep the local timer and the peer independence. Add inbound activity as a bump, pause during an active transfer, remove the URL override. |
| S-8 | Message size is bounded on both ends | `MAX_TEXT` truncates on send at 849 and again on receive at 830; 20,000 UTF-16 code units at line 429 (`02-audit-findings.md` S-8) | Keep both truncations. Add a 64 KB pre-parse guard before `JSON.parse` so the cap does not depend on the peer respecting it. |

One structural property outside S-1 to S-8 also stays, because `03-threat-model.md` section 10 names it as the design's strongest property: there is no signaling server and no inbound listener, so unsolicited traffic has no path to an answer. Cover mode does not add a signaling server; it adds a relay, and the relay forwards DTLS without terminating it. Any future hosted entry must keep the keyed-admission rule rather than adding an open lobby.

Two deliberate amendments, recorded so nobody reads them as regressions:

- `worker-src blob:` is added to the CSP. It is required for the inline Worker that holds the ratchet. It introduces no external origin and no script from a third party.
- `script-src 'unsafe-inline'` is kept. A hash would require a build step the owner ruling forbids, and S-1 means there is no injection sink for it to protect. This is a known ceiling, listed in section 5.

## 4. BUILD PLAN

### 4.1 Build target and gate harness

Build target: `03-build/output/ephemeral-v2.html`, a single file, no external assets, no build step. Each card edits named functions inside that file and leaves it runnable. A card's diff is limited to its declared scope; anything else is a separate card. Where a card's scope names a `gate.py` case, that one case is part of the declared scope, so the gate the card is graded on can be written inside its own diff.

Harness: `03-build/output/probes/gate.py`, Python 3 with Playwright driving Google Chrome by `channel="chrome"`. Headless for R2 gates, headed for R4. Each case opens two independent browser contexts, drives the real UI, and reads the wire through a test-side shim installed with `add_init_script` that records every `RTCPeerConnection` and `RTCDataChannel` instance. The shim also records `URL.createObjectURL` and `URL.revokeObjectURL` calls and can send arbitrary frames on the captured channel. No test hook ships inside `ephemeral-v2.html`: the app has no probe flag, no debug global, and no test branch.

Gate discipline, from `07-skill-sweep.md` sections 3.14 and 3.15:

- One command per card, exact exit code read. A command that ends in a pipe returns the pipe's exit code, so no gate command pipes into `tail`, `head` or `grep` without `set -o pipefail` and an explicit assertion.
- A case prints `PASS name` or `FAIL name reason` and exits 0 or 1. Exit 2 means the case could not run, which blocks the card rather than passing it.
- Evidence per run goes to `03-build/output/evidence/` with the app's SHA-256 and the case name.
- The builder never grades its own card. The R2 card gate is re-run by a second lane before the card is marked done, per the producer and reviewer split in `07-skill-sweep.md` R3 and `behavioral-verification`.

Six posture invariants from `07-skill-sweep.md` R1, mapped to cards. The mutation sweep must cover each one.

| Id | Invariant | Cards |
|---|---|---|
| I-1 | Unkeyed inbound never gets an answer | R2-02, R2-04 |
| I-2 | No plaintext or metadata leaves the page except STUN binding traffic | R2-03, R2-12, R4 capture |
| I-3 | No persistence API is touched at any point | R2-08, static grep case |
| I-4 | Key material rotates on demand and on a 20 minute aging prompt | R2-03, R2-10 |
| I-5 | A breach triggers wipe plus migration to a fresh keyset on both peers | R2-09, R2-11 |
| I-6 | The monitor raises an alert when a privacy or health invariant is violated | R2-14 |

The I-4 cadence is one concrete value, not a promise: the 20 minute session aging prompt in `06-ops-defense.md` section 3.7, which says session aging can be a UI prompt at 20 minutes asking whether to rotate. The number is a design default the owner can change without changing the invariant, and Rotate stays available on demand at any time.

### 4.2 R2 cards, in build order

Each card names its file scope, one acceptance gate command, and the failure mode the gate catches. Card order follows dependency, not severity.

| Card | File scope | Acceptance gate command | Failure mode the gate catches |
|---|---|---|---|
| R2-01 Harness and baseline | `03-build/output/probes/gate.py`, `probes/fixtures/`, `evidence/`; no app edit | `python3 03-build/output/probes/gate.py selftest` | A gate that reports pass with fewer than two live peers or without a captured channel. This is the "green light that never fires" defect `07-skill-sweep.md` R4 and `06-ops-defense.md` section 4 warn about. |
| R2-02 Control envelope and router | App constants block, `onMessage`, system-line helper, dispatch table, `03-build/output/probes/gate.py` (case `envelope`) | `python3 03-build/output/probes/gate.py envelope` | Unknown `k` or `v` silently dropped, which is the V1 behavior at line 828 and would swallow every panic or migration frame (`06-ops-defense.md` section 1). Also catches an unknown frame reaching a content handler. |
| R2-03 Crypto core in the Worker | App Worker source, suite negotiation, three-DH, HKDF root, ratchet, AEAD; header encryption is V2.1 and not this card; no UI change; `03-build/output/probes/gate.py` (case `ratchet`) | `python3 03-build/output/probes/gate.py ratchet` | Repeated plaintext yielding identical ciphertext, a counter that is not monotonic, a chain key not zeroed on advance, or key bytes readable from the main thread. Any one breaks the per-message key invariant in `04-crypto-design.md` section 4.1. |
| R2-04 SAS gate | SAS computation, pairing panel elements, pre-confirm router state, `03-build/output/probes/gate.py` (case `sas`) | `python3 03-build/output/probes/gate.py sas` | Composer or content frames enabled before confirmation, so content flows before authentication. Also catches a SAS that does not change when the peer public key changes, which means it is not bound to the transcript (`04-crypto-design.md` section 1.5). |
| R2-05 File integrity | `sendFile`, `beginIncoming`, `addChunk`, `endIncoming`, `createFileCard`, `03-build/output/probes/gate.py` (case `file`) | `python3 03-build/output/probes/gate.py file` | A truncated transfer produces a Save anchor or a full-size zero-padded blob (F-02). Also catches a corrupted chunk that still previews, and a chunk whose id or index does not match its AAD (F-12). |
| R2-06 Inbound budgets | `onMessage`, `addChunk`, `addMessage`, log trim, session counters, `03-build/output/probes/gate.py` (case `budget`) | `python3 03-build/output/probes/gate.py budget` | One bad `file-start` poisons every later transfer (F-04), the transcript grows past the row cap (F-06), or a 40 frame per second flood fails to trip rule A8. |
| R2-07 Code envelope | `pack`, `unpack`, paste and join handlers, SDP and candidate caps, `03-build/output/probes/gate.py` (case `code`) | `python3 03-build/output/probes/gate.py code` | An oversized paste decompresses before a length check (F-05), a stale or reused code still pairs (class 3), or an SDP with too many candidates reaches `setRemoteDescription` (F-07). |
| R2-08 Lifecycle and idle | `checkIdle`, `bump`, `pagehide`, `pageshow`, drop guard, textarea clearing, `03-build/output/probes/gate.py` (case `lifecycle`) | `python3 03-build/output/probes/gate.py lifecycle` | `pagehide` leaves codes, draft or blob URLs (F-08), `?idle=5` is still honored (F-10), a passive listener lets a dropped file navigate the ended page (F-09), or a slow receive is wiped mid transfer. |
| R2-09 Kill switch | Wipe button markup, `wipe`, `endSession`, keydown, clipboard clear, `03-build/output/probes/gate.py` (case `kill`) | `python3 03-build/output/probes/gate.py kill` | Wipe disabled before connect (`06-ops-defense.md` section 2.2), a kill that awaits the network and stalls, URLs revoked before the DOM so blob nodes survive, or no navigation to about:blank. |
| R2-10 Rotate | `rekey`, `rekey-ok`, root derivation, MAC acknowledgement, `03-build/output/probes/gate.py` (case `rotate`) | `python3 03-build/output/probes/gate.py rotate` | An old epoch still accepted after a rekey, a MAC that is not verified, or chain counters and skipped keys not reset (`04-crypto-design.md` section 7.3). |
| R2-11 Migrate | M1 to M5 state machine, `pending`, `adopt`, fingerprint parsing, `03-build/output/probes/gate.py` (case `migrate`) | `python3 03-build/output/probes/gate.py migrate` | A tampered `fp` in M1 still commits, the old channel stays live after M4, a 15 second timeout leaves both peers open, or Wipe during migration leaves `pending.pc` alive (`06-ops-defense.md` sections 3.3 and 3.7). |
| R2-12 Transport default | ICE configuration, STUN list, status and error text, disclosure copy, candidate pair readout, `03-build/output/probes/gate.py` (case `stun`) | `python3 03-build/output/probes/gate.py stun` | The first STUN provider being blocked is reported as peer loss, the disclosure is missing while the code still contains the peer IP, or relay configuration leaks into the default artifact (`05-transport-hardening.md` sections 5.1 and 7.1). |
| R2-13 Cover mode, INFRA, optional | Config block, `03-build/output/cover/relay.env.example`, docs, `03-build/output/probes/gate.py` (case `cover`); no default logic change | `python3 03-build/output/probes/gate.py cover --relay-host turns:127.0.0.1:5349` | The default artifact contains a relay host, or forced relay mode still emits host or server-reflexive candidates (`05-transport-hardening.md` section 2.1). The relay host is the parameter the harness supplies: the command passes a loopback address, so the case needs no external relay and no credential. PASS is exit 0 with `PASS cover` after three assertions: the default artifact has no relay URL (static scan), a relay-only policy against the loopback address emits no host or server-reflexive candidate, and gathering is refused when no relay host is configured. Exit 2 only when the flag is omitted. |
| R2-14 Monitor app | `03-build/output/monitor/` Swift package, launchd plist, hash-chained log writer, rules; no app file edit | `swift test --package-path 03-build/output/monitor` | A rule that cannot fire, which is the monitor equivalent of a green light that never blinks, or a monitor that exposes a command channel to the browser (`06-ops-defense.md` sections 4.1 and 4.4). |
| R2-15 Mutation and invariant sweep | `03-build/output/probes/gate.py` (case `mutation-all`) and scratch copies only; no app edit | `python3 03-build/output/probes/gate.py mutation-all` | A guard that passes because the probe never exercises it. Each guard is reverted on a scratch copy and its case must fail, per the R2 gate in `07-skill-sweep.md`. |

R2 exit gate: `mutation-all` passes with every reverted guard producing its matching FAIL, the six invariant cases pass on the built file, and the artifact hash is recorded in the evidence envelope.

Build notes that apply to every card:

- The app must load and pair after every card, even if the new feature is incomplete behind a constant. A card that leaves the file unable to pair is a failed card, not a merge candidate.
- No card adds a dependency, a CDN reference, a font, or an analytics call. S-6 is a gate, not a preference.
- No card adds a persistence API. S-2 is a gate, and the static case greps for all six names plus `document.cookie`.
- The Worker is created from an inline Blob. That is the only reason `worker-src blob:` appears in the CSP.

### 4.3 R3 red-team plan

Purpose: break R2 with a lane that did not build it, on a non-builder model family.

Authorization and scope, even for a local file (`07-skill-sweep.md` section 3.4):

- `04-pentest/engagement/authorization.md` names the artifact hash, the date, the tester, and the allowed actions: local two-context runs, local packet capture, no external host.
- `04-pentest/scope.txt` lists the one artifact plus the monitor app. Anything else is out of scope.
- 200 ms pacing on any live host, no destructive payloads beyond the local test machine, no cloud metadata probing.

Classes to test, replacing the generic web table from `07-skill-sweep.md` R3 with the classes this app actually has:

1. Pairing MITM by code substitution, both invite and reply, including a code that is well formed and signed by nothing.
2. `unpack` parser abuse: malformed prefix, wrong version, truncated base64, decompression bomb, oversized code, unicode and whitespace variants of the same code.
3. SDP field injection into `setRemoteDescription`: extra candidates, huge candidate sets, wrong `a=setup`, mismatched ufrag.
4. Data channel frame confusion: unknown `k`, unknown `v`, missing `sid`, replayed `seq`, a `panic` from a stale channel, a migration frame during content flow.
5. Chunk reassembly abuse: duplicate index, out of range index, chunk from a different file id, total over 50 MiB, many small files to test the session budget.
6. Flood: many small frames, chunk bursts, repeated rekey requests, repeated migrate requests.
7. CSP bypass attempts against the inline script and the inline Worker.
8. Monitor bypass: can a page make the monitor report healthy while a violation is happening.
9. Kill switch bypass: does a second tab survive, does a paused peer survive, does a pending migration survive.
10. Rotation rollback and replay of an old epoch: a rekey frame replayed, a `rekey-ok` MAC replayed, a message from before the rekey accepted after it.

Method:

- Every attempt gets a level L1 to L4 as defined in `07-skill-sweep.md` section 3.4: L1 identified, L2 partial, L3 confirmed, L4 critical. Every blocked attempt gets bypass exhaustion before it is called clean.
- Evidence per L3 and L4: full frame bytes, reproducer command, artifact hash, impact statement.
- Mutation test: for each claimed fix, revert the guard on a scratch copy and require the red-team probe to come back. A fix whose probe still passes after the guard is removed is not a fix (`07-skill-sweep.md` section 3.13).
- Independence: the R3 lane did not build R2. A second model family reviews the report with `interrogate`; a report with zero L2 or above is a signal to re-scope, not proof of safety (`07-skill-sweep.md` R3).
- Disclosure text follows `vulnerability-writeup`: one attack sentence per finding, explicit non-claims, no invented CVSS, no version ranges.

Named targets that must be attempted, because they are the two High findings:

- F-01: substitute the invite code with an attacker SDP and confirm the SAS mismatch aborts before any content frame. Then revert the SAS gate and confirm the probe succeeds.
- F-02: send `file-start` with size 50 MiB, send 1 KB, send `file-end`, and assert no Save anchor exists, the exported byte count is not 50 MiB, and the receive buffer is zeroed. Then revert the completeness gate and confirm the anchor returns.

R3 gate, from `07-skill-sweep.md` R3: the findings ledger has one row per attempt with level, evidence and reproducer; zero L3 or L4 rows remain open; every closed row has a regression probe that fails on the pre-fix file. Failure mode caught: a red team that reports "no issues" without listing what it tried.

#### 4.3.1 Skill expansion that landed after this blueprint

Three registry skills were vetted in the skill lanes after this blueprint's first write. The outcomes change the R3 toolset, not the plan.

Installed:

- `fec-security-review`, install identifier `clawhub/@bovinphang/fec-security-review`. A frontend review protocol with three scope modes and a rule that scope is stated before any diff is read, which maps onto a one file target with no diff (`01-research/output/08-registry-skills.md` section 3.8). Use it for the review scoping half of R3; the installed `security-best-practices` frontend reference stays the remediation text.
- `csp-bypass-advanced`, install identifier `skills-sh/yaklang/hack-skills/csp-bypass-advanced`. Per directive bypass techniques plus a directive reference matrix that flags `base-uri` and `form-action` as having no fallback, so an absent directive is unrestricted (`01-research/output/08-registry-skills.md` section 3.4). This is the R3 CSP class tool.

Blocked:

- `csp-policy-generator`, install identifier `clawhub/@charlie-morrison/csp-policy-generator`, was refused by the lead's Hermes install session on 2026-11-26, whose install scan returned a DANGEROUS supply-chain verdict. That verdict is the lead's install session observation, recorded here as such and not as a finding in `08-registry-skills.md`, `09-open-collections.md` or `10-methodology-sources.md`, none of which contains it. Its knowledge is substituted by the attack side directive matrix in `csp-bypass-advanced`. The R2 question it was meant to answer, whether `script-src 'unsafe-inline'` can be replaced by a hash or nonce, is already decided in section 3 and residual 16: the hash needs a build step, so the directive stays and the ceiling is disclosed. A later move to a hash is tested against the matrix, not against a generated policy.

Authored-skill queue, in the order `01-research/output/10-methodology-sources.md` section 5.3 sets, five items:

1. Atomic Red Team, card 4. The substrate for every other probe: one YAML atom per R3 attempt with an expected observable and a cleanup step.
2. WebRTC and DTLS fingerprint binding, card 7. Asserts that the pasted SDP fingerprint matches the live DER certificate, that a swapped code fails closed, and that the invite does not silently leak host candidates.
3. Zeroization and macOS trace verification, card 6. Four levels that separate what the page controls from what it can only observe, and it rejects media sanitization language for a JS heap.
4. Denial of service for owned infrastructure, card 5. Scope limited to loopback and two owned contexts, a ramp profile, pre-declared abort thresholds and a recovery assertion.
5. hackingBuddyGPT ground truth, card 1. Every attempt ends in a predicate over app state plus a raw artifact, so no L3 or L4 finding rests on an agent self-report.

Gap status, from `01-research/output/08-registry-skills.md` section 6 and `01-research/output/09-open-collections.md` section 7: CSP review is the only gap the registries closed. WebRTC protocol review, gap 1, and privacy monitor design, gap 5, have no skill in either sweep and stay authored-probe territory, as do client side crypto, gap 4, which is methodology only, and peer layer denial of service, gap 3, which has none. The six invariant cases in section 4.1 and the ten R3 classes in section 4.3 are therefore still built from the RFCs and the source, not from a skill.

### 4.4 R4 live-test checklist, Chromium desktop

Setup:

- Two Chrome profiles or two contexts on the same desktop, both headed, both Chromium class as the owner ruling requires.
- Primary run over `file://` to prove the zero-infrastructure path. Secondary run over a local HTTPS origin to prove a realistic deployment origin. Safari and iOS are stretch, not gates.
- Capture interface: `en0` or the active interface from `route get default`. The capture filter is all UDP and TCP, so STUN, the data flow and any HTTPS attempt are all in the file.
- One marker string, unique for the run, sent as a chat message and repeated inside a 1 MiB file payload.
- Evidence record per case: action, exact observed value, artifact SHA-256, evidence path, verdict.

Matrix:

| # | Case | Action | Expected observation |
|---|---|---|---|
| 1 | Happy path | Create invite, paste reply, confirm SAS on both | Both sides show the same 60 digits, composer unlocks only after confirm, text and file flow |
| 2 | SAS mismatch | Substitute the invite with an attacker SDP built by the probe | Both numbers differ, session aborts before any content frame, no message is rendered |
| 3 | Wrong, expired or malformed code | Paste a reply into the invite box, a truncated code, and a code the probe back-dates past the TTL | Visible rejection, no peer created, pairing UI stays usable |
| 4 | Race and burst | Both sides send at once, then a burst above 40 frames per second | No reorder loss, burst trips A8 at the threshold, session ends with the rule id shown |
| 5 | Third context | A third browser context pastes the same code after pairing | Refused, no second peer, no channel open |
| 6 | Reload | Reload mid session | No transcript, no code, no storage entry under DevTools Application, pairing screen only |
| 7 | File boundaries | 0 byte file, exactly one chunk, one chunk plus one byte, 50 MiB file | 0 byte rejected with a message, boundary files complete and verify, 50 MiB saves only after digest |
| 8 | Truncated transfer | Probe sends 1 KB of a declared 50 MiB then `file-end` | No Save anchor, failed card, no 50 MiB blob, buffer zeroed |
| 9 | Idle and background | Background the tab, idle past the limit; then a slow receive | Idle wipes on time, inbound keeps the session alive, an active transfer pauses the timer, no `?idle=` effect |
| 10 | Peer loss | Kill one browser process | Other side wipes within the grace period, reason shown |
| 11 | Manual wipe | Wipe button, then double Escape from inside the composer | Kill completes locally first, panic frame best effort, ended panel, about:blank |
| 12 | Kill during transfer | Start a 50 MiB transfer, then Wipe | Transfer aborts, no Save, no blob URL remains, no pending promise keeps the tab alive |
| 13 | Rotate and Migrate | Rotate keys, then start a new session | Rotate keeps the session and rekeys; Migrate completes M1 to M5, new fingerprints, old channel closed |
| 14 | Monitor alert | Induce a camera activation and a clipboard churn during a session | M2 red alert with sound and HUD, M3 amber banner, log entries with timestamps |
| 15 | Cover mode, optional INFRA | Run with relay configuration | Code contains relay candidates only, no host or srflx candidate, capture shows the relay |

Packet-capture check, required:

```sh
sudo tcpdump -i en0 -n -s 0 -w 05-verify/output/evidence/r4-capture.pcap 'udp or tcp'
# during the capture: pair, send the marker message, send the marker file, save it
# the filter is 'udp or tcp', not a port 53 filter. The no-HTTPS claim is only
# provable if port 443 traffic is in the file
tshark -r 05-verify/output/evidence/r4-capture.pcap -Y 'frame contains "EPHEMERAL_MARKER_7Q"' | wc -l
# expect 0
tshark -r 05-verify/output/evidence/r4-capture.pcap -Y 'tcp.port == 443' | wc -l
# expect 0. This check is what backs the no-HTTPS claim in pass condition 2
tshark -r 05-verify/output/evidence/r4-capture.pcap -Y 'dns' -T fields -e dns.qry.name | sort -u
# expect only the configured STUN hostnames
tshark -r 05-verify/output/evidence/r4-capture.pcap -T fields -e ip.src -e ip.dst | tr '\t' '\n' | sort -u
# expect only the two peer addresses and STUN endpoints from the configured list
```

Pass condition, stated precisely because a direct channel has a visible peer:

1. No plaintext. The marker appears in zero frames, in the chat message and in the file bytes.
2. No hostname other than the configured STUN servers is resolved or contacted. No HTTPS, no CDN, no analytics, no telemetry endpoint.
3. In default mode the address table resolves to peer A, peer B, and STUN endpoints drawn only from the configured provider list. The provider recorded in the code is the expected one; a second configured STUN endpoint appearing in the table is a PASS, and any address outside the peer pair and the configured list is a FAIL. The peer address is expected and is the documented residual from `05-transport-hardening.md` section 1.1; the check counts third-party hosts, not the peer. In cover mode the table contains peer A, peer B, and the relay, and the peer addresses are absent from the wire.

R4 gate, from `07-skill-sweep.md` R4: the matrix has one record per case with evidence; the reload case shows no recoverable transcript and no storage entry; the capture shows no marker and no third party other than STUN. Failure mode caught: a works-on-my-machine pass with no reload, no third context, and no capture.

## 5. RESIDUAL RISK

What V2 honestly does not solve, drawn from the limits sections of the research. Each row names the source and what would change the decision.

| # | Residual | Why V2 does not solve it | Source | What changes the decision |
|---|---|---|---|---|
| 1 | The SAS is a human check | A user who clicks through without comparing gets no protection, and the number proves shared keys, not personhood | `04-crypto-design.md` sections 1.2 and 5.1 | Make PAKE the default, or add a second device or channel for confirmation |
| 2 | The code channel remains the root of trust | If the code and the SAS both travel over a compromised channel and the user confirms without reading, the attacker wins | `03-threat-model.md` class 3 and section 10 | Out-of-band SAS over voice, or SPAKE2 with an independently delivered password |
| 3 | Default mode exposes peer IPs and is detectable | A direct channel needs a reachable candidate, and the code carries it. The address-in-code half is inference from the source chain and RFC 8445, not an observed run, and the sample in 05 section 1.1 is UNVERIFIED pending R3 re-derivation. WebRTC is classifiable and blockable with one rule | `05-transport-hardening.md` sections 1.1, 1.3, 2.5 | Turn on cover mode with a relay, or use a network-level VPN or Tor outside the app |
| 4 | No TURN in default mode | Symmetric NAT and UDP blocking fail closed; there is no fallback without infrastructure | `03-threat-model.md` classes 2 and 5 | Cover mode, or a second transport with a relay |
| 5 | Clipboard history and cross-device clipboard | The page can clear the current pasteboard, not the OS history, Universal Clipboard, or clipboard managers | `03-threat-model.md` risk 2, `06-ops-defense.md` section 2.6 | Avoid copying codes, shorten them, or move pairing off the clipboard entirely |
| 6 | Platform adversary | An extension or a compromised browser reads plaintext before encryption, and CSP is not a boundary against extensions | `03-threat-model.md` class 7, `04-crypto-design.md` section 6 | A signed native build, or a dedicated browser profile with no extensions and an honest first-run statement |
| 7 | No provable key erasure | DTLS keys live in the browser network process. JavaScript strings and Blobs cannot be zeroed, only dropped | `04-crypto-design.md` section 7.1, `06-ops-defense.md` section 2.6 | A native client that owns its memory, or platform attestation |
| 8 | Swap, hibernation, crash dumps, screenshots | The OS writes memory and pixels outside the page's reach | `04-crypto-design.md` section 6, `06-ops-defense.md` section 5 | Full volume encryption, hibernation off, a strict post-session checklist |
| 9 | No supply-chain verification in the product | There is no hash, signature, or version display in the file, so a swapped copy voids every control | `03-threat-model.md` class 9 | Publish a hash in two channels, sign releases with minisign or cosign, serve over HTTPS with HSTS |
| 10 | A saved malicious file can still be opened | Save gates completeness and warns on executable types, but the receiver's click and the OS handler are outside the app | `03-threat-model.md` risk 10, `02-audit-findings.md` F-13 | Do not allow Save for executable types, or open received files in a sandbox |
| 11 | Anomaly detection is blind to a normal-behaving peer | The rules see protocol abuse and transport anomalies, not intent or a human reading messages | `06-ops-defense.md` section 2.4 | Accept; the peer already has the plaintext by definition |
| 12 | Monitor limits | Same-user can kill it and root can hide from it. It is macOS only, and Linux and Windows rows are unverified | `06-ops-defense.md` sections 4.1, 4.6, 5.3 | A second device watching the first, or Endpoint Security with an Apple entitlement |
| 13 | Deniability is narrow | It holds against a later claim about the transcript, not against a compromised peer, a screenshot, or a saved copy | `04-crypto-design.md` section 5.3 | Accept and state it; do not oversell |
| 14 | No post-quantum protection | The ratchet is classical. ML-KEM is a V3 separate build, and it only protects the initial agreement | `04-crypto-design.md` section 3.3 | Sessions with a long confidentiality lifetime, or a PQ ratchet when one is specified and testable |
| 15 | SPAKE2 is not in the default artifact | It needs a curve library and a build-time bundle, which conflicts with the no-build-step ruling | `04-crypto-design.md` sections 1.3 and 8.1 | Owner allows a prebuilt optional file, or a paste-in curve implementation is audited |
| 16 | CSP limits | `frame-ancestors` cannot be set from a meta tag, and `script-src 'unsafe-inline'` is kept | `02-audit-findings.md` F-11, `07-skill-sweep.md` section 3.6 | A server header for frame-ancestors, and a build-time hash if a build step is allowed |
| 17 | No revocation in a serverless design | A leaked code is valid until its 120 second TTL and the session ends; there is no directory to revoke against | `03-threat-model.md` class 3, `06-ops-defense.md` section 3.5 | Migrate to a fresh session after any leak, and treat the old one as burned |
| 18 | The owner target "undetectable transport" is only partly met | No V2 default mode is undetectable against a passive ISP observer. The flow is classifiable as WebRTC and blockable with one firewall rule (`05-transport-hardening.md` sections 1.3 and 3.6). Cover mode narrows it: TURN over TLS on 443 looks like HTTPS until the flow is examined, and it hides peer IPs from each other, but the relay stays a visible endpoint and a metadata holder | `05-transport-hardening.md` sections 1.3, 2.2, 3.6 | A REALITY or ECH front in cover mode, both infrastructure; or accept the disclosure and state it in the product copy |
| 19 | Linux has no asar integrity layer | Layer 2 of the pin does not exist on Linux: ASAR integrity is macOS Electron 16 and later and Windows Electron 30 and later only. A replaced AppImage, or a package a user builds locally, is caught only by the published hash and the user's willingness to compare it | `11-packaging-executable.md` sections 3.2, 3.3, 3.4; `15-cve-packaging-native.md` L-02, L-03, U-10 | A signed repository package as the only Linux path, or a package format that carries a vendor signature check |
| 20 | The pinned engine accumulates known CVEs between releases | No in-app updater and no version check, by design, so a user who installs once runs a frozen Chromium with a growing public exploit list. The KEV catalog held 15 Chrome rows added since 2025-01-01 at the snapshot, 8 of them in 2026, and the newest was 16 days old. This is the largest residual the shell creates | `11-packaging-executable.md` sections 5.2, 8.3; `14-cve-browser-stack.md` section 3.2; `15-cve-packaging-native.md` E-14 | Ship often, show the build date and warn past 90 days; or accept a signed auto updater as a new trust root, which is a V3 conversation |
| 21 | Windows cannot keep the profile off disk while running | There is no user mode RAM disk, so the launch scoped `userData` directory is real files for the life of the process. macOS and Linux can point it at a RAM disk or tmpfs, which is why the "user data in memory" claim is platform qualified | `11-packaging-executable.md` sections 4.1, 4.2 | Accept for a per user install, document it, and rely on full volume encryption; or move to a native client that owns its memory |
| 22 | libwebrtc has no advisory channel | It is not distributed as a package, so the GitHub Advisory Database has no entry and an NVD keyword query returns `totalResults` 0. Fixes arrive as Chrome milestone CVEs with vague descriptions and a crbug link, so a CVE list cannot drive a code audit of the SDP, ICE, DTLS and SCTP entry points. BoringSSL has the same gap one layer down | `14-cve-browser-stack.md` sections 4.1, 4.3, 6.2 | Fuzz the parsers on the pinned build as a standing case (R3-BS-08), and treat the SDP parser reached through the reply code as the only libwebrtc code a party with an invite reaches with zero authentication, and as a better pen test target than any CVE in `14-cve-browser-stack.md` section 4.2 (14 section 4.3, line 223) |
| 23 | The muxer `finalize()` failure is unexplained | One measured 290 frame run failed inside `finalize()` with `TypeError: Cannot read properties of null (reading 'colorSpace')`, while 3, 5, 60 and 300 frame runs through the same page completed. The cause is UNVERIFIED | `12-media-pipeline.md` sections 2.7, 10 | The chunk 0 `decoderConfig` assertion and the rung B fallback turn it into a visible downgrade rather than an intermittent crash. Close the item when a rerun either reproduces it under the assertion or cannot |
| 24 | The QR ceiling rests on an inferred code length | The V2 envelope length was never measured. 800 bytes is a planning figure built from the 650 character V1 code plus the new envelope fields, and the version 25 decision, 997 bytes of byte mode capacity, follows from that inference | `13-platform-ux.md` sections 2.4, known limits | Measure the envelope when it lands and set the QR ceiling from the measurement. Above 997 bytes there is no display path below version 25 |
| 25 | An older signed build can be reinstalled, so rollback is not refused | V2 has no version counter and no signed metadata, so an older artifact that verifies against its own hash and signature passes every check the manual protocol can make. A user who keeps an old signed build, or an attacker who serves one, can return the install to a version with a known CVE, and the published hash comparison cannot tell new from old | `11-packaging-executable.md` sections 5.2, 5.5; section 6.1 step 4 of this file | A signed channel with signed metadata, a monotonic counter, a key off the build machine, a verifying client and a revocation path, which `11-packaging-executable.md` section 5.5 prices as one new trust root, one new network client and one new key management problem. That is a V3 conversation |

Residual 6 is narrowed by section 6.1, not closed. A signed shell removes the extension model and the shared browser profile by construction, which is the class 7 attacker the browser could never exclude. It does not remove a compromised OS, a stolen signing key, or a user who clicks through the first run warning (`15-cve-packaging-native.md` section 9.3).

The addendum adds a second ranking for the platform layer, and it is ordered by exposure rather than by severity: the frozen engine (row 20) first, because it is the one new exposure packaging creates; then the Linux gap (row 19), the one platform with no layer 2; then libwebrtc coverage (row 22), because a parser with no advisory channel cannot be audited from a CVE list; then the muxer item (row 23), which is a known crash with a known mitigation waiting on a rerun.

The three residuals that would change the product most, in order: the human SAS (row 1), the direct-channel metadata (row 3), and the platform trust boundary (row 6). The first is a UX and protocol decision. The second is a hosting decision. The third is a distribution decision, and no browser page can win it.

## 6. PLATFORM ADDENDUM

Folded from `../01-research/output/11-packaging-executable.md`, `../01-research/output/12-media-pipeline.md`, `../01-research/output/13-platform-ux.md`, `../01-research/output/14-cve-browser-stack.md` and `../01-research/output/15-cve-packaging-native.md`, cited below by file name as the rest of this blueprint does. Those five files decide the shell, the media pipeline, the platform UI, and the vulnerability and case base for both. Detail stays there; this section carries the decisions, one card or case id per row, and the new residuals, so the build wave can schedule the work without reopening them. Nothing below changes a decision in sections 1 to 5 beyond the residual rows it adds to section 5.

### 6.1 Packaging decision

DECISION: Electron, pinned to one supported major, upgraded quarterly or on a Chromium critical (`11-packaging-executable.md` section 9.1). It is the only candidate that is both self contained and Chromium, so it is the only one whose engine version the product can name, test and patch on its own schedule.

The four rejected options, one row each (`11-packaging-executable.md` sections 1.2 to 1.6):

| Rejected option | Reason, in one line |
|---|---|
| CEF | Same engine without Node, but three native hosts, Cocoa, Win32 and GTK, are more new memory-unsafe attack surface than one Node main process, and the size was never measured here. Named fallback only if the main process ever becomes the weak link. |
| Tauri | Three engines that cannot be pinned. On macOS WebKit stops updating when the OS stops, WebView2 updates on its own schedule, and the X25519 to P-256 fallback makes the suite per platform, so every R3 case needs three variants. 3 to 5 MB buys a test matrix multiplication. |
| Neutralino | System webview plus a local static HTTP server and a WebSocket bridge. The only option that adds a listening socket and a second unauthenticated local channel to a design whose strongest structural property is that inbound traffic has no path to an answer. |
| Chrome app mode shim | Not self contained, so it keeps the user's Chrome version and the user's extension model, which is the class 7 threat packaging exists to remove, and `--app` is an undocumented flag. Kept as the documented fallback path, never shipped as the product. |

Pinning design, four layers, named (`11-packaging-executable.md` sections 3.1 to 3.4):

1. OS code signature over the bundle: Developer ID plus notarization on macOS, Authenticode over the installer and every exe on Windows, nothing at OS level on Linux.
2. The Electron fuse pair `EnableEmbeddedAsarIntegrityValidation` and `OnlyLoadAppFromAsar`. The asar header hash lives outside the archive, in `Info.plist` under `ElectronAsarIntegrity` on macOS and in a Windows resource of type `Integrity` named `ElectronAsar`. Supported on macOS as of Electron 16.0.0 and on Windows as of Electron 30.0.0 (`11-packaging-executable.md` section 3.2, line 250). Absent on Linux.
3. A 64 character SHA-256 of the core compiled into the main process, compared with `crypto.timingSafeEqual` over the bytes read from the asar. On a match the same in-memory Buffer is served over a custom `app://` protocol, and nothing else is ever loaded. Hashing the buffer and serving that buffer, rather than hashing a path and loading the path, removes the check-then-load window, and the response header can carry a CSP stricter than the core's meta tag at `ephemeral-chat-v1.html:6`.
4. On Linux only, the package manager is the root: `sha256sums` in the `PKGBUILD` plus pacman `SigLevel` for a repository package. For the AppImage there is no root beyond the published hash the user compares.

What the pin closes and what it does not: it closes a swapped HTML file inside an otherwise genuine installer, not a wholly replaced build that is signed by someone else, and not Linux, which has no layer 2. The mitigation is free and belongs in the About panel: show the build hash and the core hash, with the command to check them (`11-packaging-executable.md` section 3.4).

Artifacts, one line per platform (`11-packaging-executable.md` sections 2.1 to 2.3 and 9.5):

| Platform | Artifact | Signing |
|---|---|---|
| macOS arm64 and x64 | Two DMGs, one per arch, each containing the `.app` | Developer ID Application, hardened runtime, secure timestamp, no `get-task-allow`, `notarytool`, stapled ticket. V8 needs JIT, so `com.apple.security.cs.allow-jit` is the one named entitlement and the release note says so. |
| Windows x64 | Per user NSIS installer, plus a portable zip | Authenticode over the installer and every exe. A new certificate has no SmartScreen reputation, so the first users see a warning. State that in the install guide instead of treating it as a defect. |
| Arch and Omarchy | `PKGBUILD` with `sha256sums`, or a signed repository package, which is the better anchor | pacman PGP for a repository package. A package built locally with `makepkg` carries no signature guarantee, so a tarball the user built is checked only by the published hash (`11-packaging-executable.md` section 2.3). |
| Other Linux x86_64 | AppImage | No OS check at all. Detached signature plus published hash, and the FUSE requirement (`fuse2` on Arch) stated in the same sentence as the hash, not a footnote. |

Updater: none. No auto-updater, no update check, no version ping (`11-packaging-executable.md` section 5; `15-cve-packaging-native.md` BC-W8). An update client is a network client with standing write access to the app directory, and a background version check leaks that this person runs this app. The replacement protocol is manual and hash verified:

1. Publish the SHA-256 of every artifact in two independent channels, and a detached minisign or cosign signature over the hash list, with the public key in the repository and in the About panel.
2. Give the command per platform in the download page and the About panel: `shasum -a 256` on macOS, `sha256sum` on Linux, `certutil -hashfile <file> SHA256` on Windows.
3. The app shows its own build and core hashes, so the comparison has both sides.
4. Keep the previous artifact and its hash, so a return to a version already verified is not a blind download. State the limit: V2 has no version counter and no signed metadata, so the manual protocol cannot enforce rollback refusal, and a user can reinstall an older signed build. Enforcing rollback refusal needs the signed channel that `11-packaging-executable.md` section 5.5 prices: signed metadata with a monotonic counter, a key off the build machine, a verifying client and a revocation path. That is a V3 conversation. The About panel shows the build date and warns past 90 days (`11-packaging-executable.md` sections 5.2 to 5.5). `pacman -Syu` is the only real update channel in the design, and it is not ours.

Size, stated because it is the largest objection: 115.3 MiB (macOS arm64), 119.4 MiB (macOS x64), 151.2 MiB (Windows x64) and 118.2 MiB (Linux x64) of download for a 35,598 byte file, and 268 to 373 MB installed (`11-packaging-executable.md` section 7.1, measured framework zips and quoted empty-app rows). The defense that is not available is "everyone uses Electron". The two that are: the engine is pinnable and testable, and the code a reviewer must read is three files, `main.cjs`, `preload.cjs` and the core HTML.

Runtime posture: in-memory session partition with no `persist:` prefix, `--disable-http-cache`, and a launch scoped `userData` directory deleted on exit (`11-packaging-executable.md` sections 4.1 and 4.2). Windows is the one platform where the RAM claim does not fully hold, because there is no user mode RAM disk and the profile is real files on disk for the life of the process. That gap is residual row 21.

Two interactions with existing sections, recorded rather than re-decided:

- Section 2.7 named per-tab traffic as a monitor blind spot. The shell closes it: the chat is its own process tree with its own UDP socket, so rules M1 and M4 get a real boundary, and `codesign -v`, `spctl -a -vv`, `Get-AuthenticodeSignature` or `pacman -Qkk` answer whether the installed binary is the signed one (`11-packaging-executable.md` section 8.1). That narrows a stated monitor limit; it does not make the monitor a guard.
- Section 2.5's kill is a page killing itself. The shell kill is a parent killing a child: the menu item is built in the main process, so a renderer that swallows `keydown` cannot disable it, and the order is renderer first, then storage, then process, with a hard destroy at 300 ms (`11-packaging-executable.md` section 8.2). The in-page sequence still runs first because it owns the DTLS close and the panic frame.

Cites: `11-packaging-executable.md` sections 1.1 to 1.6, 2.1 to 2.3, 3.1 to 3.4, 4.1, 4.2, 5.1 to 5.5, 7.1, 8.1, 8.2, 9.1, 9.5; `15-cve-packaging-native.md` BC-W8.

### 6.2 Media pipeline, cards R2-16 to R2-22

DECISION: video over 45 MiB is transcoded in the page with WebCodecs engine A, images are re-encoded through a canvas to WebP, files keep the 50 MiB path, and compression always runs before encryption (`12-media-pipeline.md` section 0). Seven cards, numbered on from R2-15, in the same columns as section 4.2. Every one is CORE and works in both modes; none is EXEC-ONLY.

| Card | File scope | Acceptance gate command | Failure mode the gate catches |
|---|---|---|---|
| R2-16 Encryption ordering | `acceptFile`, encoder call order, 4 KiB frame padding, true length bound in the AAD, `03-build/output/probes/gate.py` (case `media-order`) | `python3 03-build/output/probes/gate.py media-order` | Encryption run before compression, so the entropy coder has nothing left to remove; a gzip pass attempted on WebP or MP4 bytes; a padded frame whose true length is not inside the plaintext and bound by the AAD, then asserted to agree on decrypt (`12-media-pipeline.md` sections 5.1, 5.2). |
| R2-17 Metadata strip | `acceptFile`, `encodeImage`, the startup WebP probe, the `blob.type` assertion, `gate.py` (case `exif`) | `python3 03-build/output/probes/gate.py exif` | Any `Exif`, `GPS`, XMP or ICC marker surviving in the sent WebP, or any `blob.type` that is not the requested type, which is how the measured AVIF request silently became a PNG. Also catches a second ingest path that skips the re-encode (`12-media-pipeline.md` sections 3.1 to 3.3). |
| R2-18 Transcode engine A | `transcode`, `planBitrate`, the `requestVideoFrameCallback` loop, `VideoFrame.close()`, the `encodeQueueSize` cap of 8, the muxer, `gate.py` (case `transcode`) | `python3 03-build/output/probes/gate.py transcode` | The named gate condition is `finalize()`: chunk 0 must carry a non null `decoderConfig`, asserted before the muxer finalizes, because one measured 290 frame run died inside `finalize()` on a null `colorSpace`. A failed assertion falls to rung B, `MediaRecorder`, instead of throwing. Also catches a frame leaked without `close()` and an unbounded encode queue (`12-media-pipeline.md` sections 2.3, 2.7, 2.9, 10). |
| R2-19 Projected size before commit | `planBitrate` output rendered, Send gated on the projection, a post `flush()` size check, `gate.py` (case `bitrate`) | `python3 03-build/output/probes/gate.py bitrate` | A transfer that starts before the projection is shown, or a result over 45 MiB (47,185,920 B) with no single retry at `bitrate * (cap / size) * 0.95` and then a refusal that names the size actually reached (`12-media-pipeline.md` sections 2.4, 2.8). |
| R2-20 Playback from RAM, revoke on wipe | `media-src blob:` in the CSP, the in-memory Blob, `video.src`, the `urls` array, the revoke order, `gate.py` (case `playback`) | `python3 03-build/output/probes/gate.py playback` | A missing `media-src`, measured as `videoError 4` with `readyState 0` under the V1 policy; a revoke that runs before the log node is removed; a blob URL still live after wipe or after `pagehide` (`12-media-pipeline.md` sections 6.2, 6.3). |
| R2-21 Image memory ceiling | `encodeImage` pixel gate, `bitmap.close()` in `finally`, `gate.py` (case `imagecap`) | `python3 03-build/output/probes/gate.py imagecap` | A destination canvas allocated before the 60 MP gate (60,000,000 px, 240,000,000 B), or a bitmap not closed in `finally`. Also catches a 200 MP source reaching a canvas that cannot allocate it at all (`12-media-pipeline.md` section 3.5). |
| R2-22 Paste, drop and picker, one path | `acceptFile(file, source)` as the only entry point, all three callers routed through it, `gate.py` (case `paste`) | `python3 03-build/output/probes/gate.py paste` | A pasted screenshot that skips the re-encode and therefore the metadata strip; a paste handler that intercepts text; a second transcode started while one is running; a synthesized name built from a timestamp instead of a counter (`12-media-pipeline.md` section 7). |

Numbers this section adds, all from `12-media-pipeline.md`: the video cap is 47,185,920 B with the bitrate planned at 90 percent of it; chunks are 64 KiB; the padding bucket is 4,096 B; the image gate is 60 MP; the resolution ladder caps at 1080p and refuses above 600 s. The container is MP4 written by `mp4-muxer` 5.2.2, which its author has deprecated in favour of mediabunny. That is a deliberate pin, recorded not floated: 31,103 B minified and 9,062 B gzipped against 135,497 B and 34,761 B gzipped for the successor's mux only path, for a feature (write an ISO BMFF file) that is finished (`12-media-pipeline.md` section 2.2).

Bundle reconciliation, stated because section 2.2 prices the crypto and control work at 4 to 6 KB of new source and no new dependency bytes, which is true for that scope and not for this one: with the muxer and about 250 new lines the core is about 76,700 B raw and 22,100 B gzipped, roughly 2.2 times the raw file (`12-media-pipeline.md` section 8). Two budgets, not one contradiction.

One integration constraint that spans two inputs: in exec mode the `app://` response header from section 6.1 is stricter than the core's meta tag, so it must carry `media-src blob:` and `worker-src blob:` as well, or the header silently re-breaks playback that the meta tag allows (`11-packaging-executable.md` section 9.2 step 5; `12-media-pipeline.md` section 6.2).

Cites: `12-media-pipeline.md` sections 0, 2.2 to 2.9, 3.1 to 3.5, 5.1, 5.2, 6.2, 6.3, 7, 8, 10; `11-packaging-executable.md` section 9.2.

### 6.3 Platform UX, cards UX-01 to UX-10

DECISION: the platform surface is a screen state machine, one pending session slot, a reaction frame, and a shell that mirrors keyboard paths rather than adding mechanisms. The ten cards are named here and specified in `13-platform-ux.md` section 5; this table is the schedule entry, not a second copy. UX-01 to UX-08 are CORE. UX-09 and UX-10 keep their EXEC-ONLY flag: they have no core half and never gate the default artifact.

| Card | Scope, by reference | Mode | Gate | Failure mode the gate catches |
|---|---|---|---|---|
| UX-01 Message identity | `msg` frame gains `mid`, `addMessage`, log trim, `gate.py` case `mid` | CORE | `python3 03-build/output/probes/gate.py mid` | A reaction that addresses the wrong message, or two messages sharing an id, which is F-12's positional bug in a new field |
| UX-02 Reactions | `react` frame, dispatch row, `applyReact`, reaction map, pill render, hover row, palette, bucket, `gate.py` case `react` | CORE | `python3 03-build/output/probes/gate.py react` | A reaction before SAS confirm, a duplicate that double counts, an unknown shortcode that renders, a flood that misses the bucket or A8, a reaction that resurrects a trimmed row |
| UX-03 Screen state machine and session slots | Panel container, S0 to S4 transitions plus two sheets (gallery, about), `active` and `pending` slots, migration strip, focus moves, `gate.py` case `nav` | CORE | `python3 03-build/output/probes/gate.py nav` | A back path into a live session, a composer that unlocks during migration, two slots that can both be live |
| UX-04 Verification panel and crypto status | SAS panel, 60 digit render, confirm and mismatch, peer confirm gate, status chips, ratchet age, aging banner, `gate.py` case `sas-ui` | CORE | `python3 03-build/output/probes/gate.py sas-ui` | A composer unlocked before the peer confirms, a "verified" label before both confirms, a session id or a key byte in the DOM |
| UX-05 Pairing panel states | Paste, parse, preview, TTL countdown, single use, error strings, show and regenerate, `gate.py` case `pair` | CORE | `python3 03-build/output/probes/gate.py pair` | A stale or reused code that still pairs, an error that leaks the decoded SDP or the candidates |
| UX-06 Wipe and panic | Always enabled button, confirm rules, double Escape, the layer rule, ended panel, countdowns, `gate.py` case `panic` | CORE | `python3 03-build/output/probes/gate.py panic` | Wipe disabled before connect, Escape in a picker that wipes the session, an ended panel that shows a session id |
| UX-07 Media gallery | Gallery sheet, grid, delete order, save gate, eviction line, drag block, `gate.py` case `gallery` | CORE | `python3 03-build/output/probes/gate.py gallery` | A delete that revokes before removing the node, a save anchor before the digest, a drag that writes plaintext to disk |
| UX-08 Theme and accessibility baseline | Token set, light and dark blocks, focus ring, reduced motion, emoji fallback, `gate.py` case `a11y` | CORE | `python3 03-build/output/probes/gate.py a11y` | A dark palette below 4.5:1, a pill that is not a button, a live region that re-announces a message on every reaction |
| UX-09 Shell window, menu, shortcuts, badge | Wrapper main process, menu template, disabled defaults, badge bridge, `gate.py` case `shell` | EXEC-ONLY | `python3 03-build/output/probes/gate.py shell --app 04-shell/output/ephemeral.app` | A reachable Reload, a second window, a badge with a count, an OS notification, or a renderer with `nodeIntegration` on |
| UX-10 QR display and scan | Encoder in the shell, size ceiling check, scan permission flow, paste fallback, `gate.py` case `qr` | EXEC-ONLY | `python3 03-build/output/probes/gate.py qr` | A QR rendered above the version 25 ceiling of 997 bytes, a scan path with no paste fallback, a camera permission requested before the user asks to scan |

Order, from `13-platform-ux.md` section 5: UX-01 then UX-02, because a reaction cannot be built or gated without message ids; UX-03 before UX-04 and UX-05; UX-06 last in the core group because it touches every panel's Escape and focus handling; UX-09 and UX-10 after the core group and after the wrapper lands.

Three protocol facts this section adds to the sections already written, recorded here rather than edited into them:

- The `react` frame is one more row in the section 2.4 dispatch table. It carries `{v, k: "react", sid, seq, t, e, op}` with a 16 hex target, a shortcode from a 24 entry allowlist, and `add` or `remove`. There is no actor field, no count and no timestamp, because the channel already authenticates the peer and a peer supplied count is an integer the UI would have to trust (`13-platform-ux.md` sections 1.2, 1.6). The frame cap is 256 bytes, after the 64 KB pre-parse cap in section 2.3.
- Caps that keep reaction spam out of the F-06 DoS class: 24 shortcodes, one pill per distinct shortcode so the DOM cost is bounded by the palette and not by the frame count, 200 marks per session, a 20 frame burst refilling at 4 per second, and five drops in 10 s running the A1 kill with reason `react-flood` (`13-platform-ux.md` section 1.5).
- The composer unlocks only when the local confirm and the peer's `sas-confirm` are both in. That is tighter than the section 2.1 wire rule, which drops content frames before the local confirm, and the tightening prevents a sent message that never renders (`13-platform-ux.md` section 2.5).

Cites: `13-platform-ux.md` sections 1.2, 1.5, 1.6, 2.5, 5.

### 6.4 Wrapper build cards, BC-W1 to BC-W14

Fourteen cards from `15-cve-packaging-native.md` section 2, folded by reference. Mode is EXEC-ONLY for wrapper configuration and RELEASE for the distribution steps that file calls release engineering and says must be owned by name (`15-cve-packaging-native.md` section 9.3). No card has a core half, so none gates the default artifact.

| Card | Requirement, one line | Mode | Check |
|---|---|---|---|
| BC-W1 | `nodeIntegration`, `contextIsolation`, `sandbox`, `webviewTag`, `nodeIntegrationInWorker`, `nodeIntegrationInSubFrames` and the `remote` module all in the closed position, with `app.enableSandbox()` before ready | EXEC-ONLY | Static scan of every window option, plus a renderer assertion that `process` and `require` are undefined, inside the crypto Worker too |
| BC-W2 | One preload, one bridge object, one method per capability, primitive arguments only, `ipcMain.handle` with sender origin check and argument validation | EXEC-ONLY | Grep for any `ipcRenderer` exposure; a test call from a foreign origin with a polluted object must be rejected and counted |
| BC-W3 | Deny all navigation and all window creation. External links only through an explicit confirmation, `https:` only, opened in the system browser | EXEC-ONLY | `will-navigate` and `setWindowOpenHandler` tests, plus R3-W3 |
| BC-W4 | Serve the core from `app://`, not `file://`, with `grantFileProtocolExtraPrivileges` off | EXEC-ONLY | Fuse read shows the grant off, and the app loads with `file://` requests blocked |
| BC-W5 | Every production fuse flipped: `runAsNode` off, `nodeOptions` off, `nodeCliInspect` off, `onlyLoadAppFromAsar` on, `embeddedAsarIntegrityValidation` on, `grantFileProtocolExtraPrivileges` off, `loadBrowserProcessSpecificV8Snapshot` on, `cookieEncryption` left at the value section 6.6 records, `wasmTrapHandlers` untouched | EXEC-ONLY | `npx @electron/fuses read --app <installed app>`, output attached to the release evidence |
| BC-W6 | Exact Electron pin, Chromium security tracking, a written SLA (High in 7 days, Critical in 72 hours), version and build hash in About | RELEASE | Release checklist plus the About panel string |
| BC-W7 | Detached signature over each artifact's SHA-256, hash published in two independent channels, verifier that shares no code with the downloader | RELEASE | R3-W5, and release evidence carrying both channel URLs and a verification transcript |
| BC-W8 | No auto update in V2. The app performs no update check and sends no notification; replacement is manual and hash verified per section 6.1. A download may happen only by the user's own action, and an install may not | RELEASE | Code inspection of the update path plus R3-W5 |
| BC-W9 | macOS: Developer ID, hardened runtime, notarization, stapled ticket, no `get-task-allow`, `codesign` and `spctl` in CI, every weakening entitlement named and justified in the release note | RELEASE | `codesign --verify --deep --strict`, `spctl -a -vvv`, `xcrun stapler validate`, plus R3-W7 |
| BC-W10 | Windows: Authenticode on every exe and dll, RFC 3161 timestamp, per user install in a directory the user cannot be tricked into sharing, `SetDefaultDllDirectories(LOAD_LIBRARY_SEARCH_SYSTEM32)` before any load, no unquoted path | RELEASE | `signtool verify /pa /all` over the whole install tree, a planted DLL loader test, plus R3-W8 |
| BC-W11 | Linux: AppImage signed with an embedded gpg signature, `--appimage-signature` checked by an external validator, `LD_LIBRARY_PATH`, `LD_PRELOAD` and `PYTHONPATH` cleared before launch, absolute `Exec`, `desktop-file-validate` in CI | RELEASE | Release transcript plus R3-W9 |
| BC-W12 | Arch and Omarchy: a signed pacman repository preferred over AUR. If AUR, a pinned `PKGBUILD` with verified checksums, a documented review step, and the statement that `makepkg` runs as the user with no sandbox. Never instruct `makepkg` from a moving branch | RELEASE | Package diff review, the AUR page and the install doc |
| BC-W13 | Crash reporting off or local only, and no dump, GPU cache or log may contain message text, filenames, codes or keys. Document the Chromium cache path and clear it on wipe where the platform allows | RELEASE | A post crash and post wipe disk scan for a canary string, extending the R4 zero trace case |
| BC-W14 | Single instance lock with a validated payload, no listening socket, no remote debugging in release, DevTools behind a build flag | EXEC-ONLY | R3-W1 and R3-W10, plus a port scan and process list after launch |

BC-W14 is decided explicitly as EXEC-ONLY. `15-cve-packaging-native.md` section 9.3 names BC-W1 to BC-W5 as wrapper configuration and BC-W6 to BC-W13 as release engineering, and does not name BC-W14; its row at 15 section 2 is the single instance lock, the no listening socket rule, the release mode debug posture and the DevTools flag, which is wrapper configuration and not a distribution step. The split is 6 EXEC-ONLY and 8 RELEASE.

Trust map, TB-W1 to TB-W7, folded here because the section 1 trust map predates the wrapper (`15-cve-packaging-native.md` sections 1 and 9.3). One line per boundary, control side only:

| ID | Boundary | Control |
|---|---|---|
| TB-W1 | OS user account and launch environment to wrapper process (argv, environment, working directory, protocol URLs, second instance payloads) | Fuses off for every Node style launch path, argv parsed by allowlist, single instance payload validated |
| TB-W2 | Renderer to main process, every bridged call and argument | contextIsolation on, sandbox on, one method per capability, primitive arguments, sender origin check |
| TB-W3 | Main process to OS primitives (file dialogs, `shell.openPath`, `shell.openExternal`, clipboard, notifications, tray, login item, protocol registration) | Explicit allowlists, no shell interpolation, path resolution before open, no peer supplied path |
| TB-W4 | Update channel to installed binary | Detached signature plus SHA-256 published in two channels, verified outside the updater |
| TB-W5 | Build inputs to shipped artifact (dependency tree, Electron and Chromium version, CI scripts, signing keys, notarization credentials) | Lockfile with integrity, exact Electron pin, isolated CI, hardware backed signing keys |
| TB-W6 | OS trust machinery to launched app (code signature, ticket, quarantine, MOTW, AppImage mount, package manager trust) | Correct signing on every platform, documented verification commands, no instruction that strips a protection |
| TB-W7 | Peer supplied data to privileged shell surface (filenames, MIME types, link looking text, received files) | Treat as hostile at the boundary, never place peer text in a path, a command, a URL opener or a notification action without escaping and allowlisting |

TB-W4 is the highest value boundary in the product: every control in files 01 to 13 lives inside an artifact the update chain can replace, and a wrapper that verifies its own update can be told to verify the attacker's update (`15-cve-packaging-native.md` lines 43 and 52). For the same reason the update chain is the critical path, the one target whose compromise defeats every other control (`15-cve-packaging-native.md` line 163). That is why the minimum is the manual, hash verified replacement in section 6.1 and why R3-W5 is a release gate.

Cites: `15-cve-packaging-native.md` sections 2, 3.1, 3.2, 9.3.

### 6.5 Expanded R3 register, R3-BS-01 to R3-BS-27 and R3-W1 to R3-W10

DECISION: the ten classes in section 4.3 stand, and the platform work extends them with 37 named cases. The browser stack register is `14-cve-browser-stack.md` section 11, with per case action and pass condition in its sections 3.6 to 9.6. The wrapper register is `15-cve-packaging-native.md` section 2, with action and pass condition per row. One line each here, because the pass conditions are long and duplicating them would create two sources of truth.

How the register joins section 4.3: R3-BS-02 and R3-BS-06 extend class 1. R3-BS-09 and R3-BS-06 extend class 2. R3-BS-06 and R3-BS-07 extend class 3; R3-BS-16 and R3-BS-17 extend class 4; R3-BS-12, R3-BS-15 and R3-BS-27 extend class 6. R3-BS-03, 04 and 05 add a class the plan does not have, platform patch state, class 11. R3-W1 to R3-W10 add the wrapper class, class 12. R3-W5 and R3-W6 are release gates, not optional probes (`15-cve-packaging-native.md` section 9.3).

| Case | Entry point | What it proves, one line | Detail |
|---|---|---|---|
| R3-BS-01 | Page source | Negative control: grep the built artifact for `eval`, `new Function`, `innerHTML`, `srcdoc`, `import(` and `document.write`, and expect zero hits. This case is what keeps every V8 row below it ranked down | 14 section 3.6 |
| R3-BS-02 | Static host | Substitute a modified copy of identical byte length over the same path. The app cannot detect it, which is the expected result, recorded as accepted and handed to the integrity work | 14 section 3.6 |
| R3-BS-03 | Renderer | Run a known public Pwn2Own or GitHub Security Lab renderer proof of concept for the pinned build's major version from a local file URL. Either the build is patched and it fails, or the finding is L3 with the version named. No third outcome | 14 section 3.6 |
| R3-BS-04 | OS sandbox and kernel | Confirm the sandbox is on and dump the seccomp or seatbelt profile, then attempt the Project Zero `MSG_OOB` pattern. The syscall surface must not include it | 14 section 3.6 |
| R3-BS-05 | Pinned build | Print the Chromium version, compare it to stable and to KEV rows added since the build. More than one major behind is an L3 finding on its own | 14 section 3.6 |
| R3-BS-06 | `setRemoteDescription` | Mutate a valid answer: duplicate m-lines, unknown attributes, flipped `a=setup`, ufrag mismatch, 5,000 candidates, 1 MB of attributes, NUL, unicode. Every one rejected with no crash, no hang over 5 s, no half configured peer. This is the only libwebrtc code a party with an invite reaches with zero authentication, and a better pen test target than any CVE in `14-cve-browser-stack.md` section 4.2 (14 section 4.3, line 223) | 14 section 4.4 |
| R3-BS-07 | ICE credentials | Wrong ufrag and pwd fail closed. Candidates pointing at a third party are either ignored or attempted, and the report says which, with no content before DTLS completes | 14 section 4.4 |
| R3-BS-08 | SDP and ICE fuzz | A corpus run against the pinned build. A clean result states corpus size and CPU hours or it is not a result | 14 section 4.4 |
| R3-BS-09 | STUN response | Malformed Binding responses: truncated attribute, length beyond the message, unknown comprehension-required attribute, zero length, 64 KB padding. No crash, a defined state, no infinite `connecting` | 14 section 5.4 |
| R3-BS-10 | Candidates | Candidates that route media through a third host. The connection fails or completes only through it, and the report states which | 14 section 5.4 |
| R3-BS-11 | STUN reflection | No packet is sent to an address that was not configured or discovered through a validated ICE check | 14 section 5.4 |
| R3-BS-12 | DTLS handshake | Maximum count fragments, out of order, duplicated, zero length final fragment. No crash, and the RSS delta is measured and reported | 14 section 6.6 |
| R3-BS-13 | DTLS record | Zero byte record, length larger than the datagram, bad MAC. All dropped, association survives or fails closed, no undefined state | 14 section 6.6 |
| R3-BS-14 | Replay | Replay one application data record, then an old sequence AEAD frame. DTLS level acceptance is expected per RFC 9147 and is a finding against the design; the AEAD build must reject, and this case is its regression probe | 14 section 6.6 |
| R3-BS-15 | Data channels | 500 channels, each stream reset, then another 500. `dc` stays on the first channel or the extras are refused, memory growth bounded and reported. The V1 build fails this by design | 14 section 7.4 |
| R3-BS-16 | Frame types | Binary where JSON is expected and the reverse, an empty frame, 16 KiB of NUL, a UTF-8 BOM. No uncaught exception, no text frame treated as a chunk | 14 section 7.4 |
| R3-BS-17 | Message size | One 256 KiB and one 1 MiB `dc.send`, then a burst of 16 KiB chunks with no `file-start`. The observed browser limit is reported, and no allocation happens without a transfer | 14 section 7.4 |
| R3-BS-18 | AEAD nonce | Log every nonce and key epoch across 10,000 messages, a reload, a rekey and a migration. Zero duplicates, and the harness fails on the first one | 14 section 8.8 |
| R3-BS-19 | Nonce counter wrap | Force the counter to maximum, wrap it, reuse an epoch id after migration, encrypt an empty plaintext. A wrap rekeys or fails hard, never repeats | 14 section 8.8 |
| R3-BS-20 | `CryptoKey.extractable` | Enumerate every key the app creates and call `exportKey` on each. Every traffic key is non extractable, and any key that exports is L3 with the key name | 14 section 8.8 |
| R3-BS-21 | Tag comparison | 100,000 timing samples at each byte position plus a code read. No position dependent difference above noise, and one compare function with a test that fails if an early return is reintroduced | 14 section 8.8 |
| R3-BS-22 | Entropy and KDF | Zero `Math.random` in any key path, no passphrase derived key, every salt per session and 128 bits or more from `getRandomValues` | 14 section 8.8 |
| R3-BS-23 | Image decoder | 200 crafted images through the real file path, including one known public proof of concept for the pinned build. No crash, no hang over 5 s, memory measured | 14 section 9.6 |
| R3-BS-24 | Decode memory | A 30,000 by 30,000 image in a 200 KB file, then a 45 MB video that decodes to a larger frame buffer. Renderer survives or fails the decode, peak RSS reported | 14 section 9.6 |
| R3-BS-25 | `VideoDecoder` | Crafted MP4 and WebM: bad `stsd` entry, zero duration, negative timestamp, 1000 tracks, chunk offset past EOF. Errors handled, attachment discarded, no half decoded frame kept | 14 section 9.6 |
| R3-BS-26 | Buffer transfer | No held `Uint8Array` view is handed to `ImageDecoder` or `VideoDecoder` by transfer, and a detached view is never read afterwards. Code read plus a runtime assertion | 14 section 9.6 |
| R3-BS-27 | Decoder limits | Ten 45 MB videos in a row plus one unsupported codec. Memory reclaimed between attachments, the unsupported codec fails cleanly, the session is still usable | 14 section 9.6 |
| R3-W1 | Launch environment | `ELECTRON_RUN_AS_NODE=1`, `NODE_OPTIONS=--require`, `--inspect`, a crafted protocol URL, a malformed second instance payload. No Node context, no probe load, no debugger port, and both pass conditions quoted from `15-cve-packaging-native.md` section 2: "the protocol URL is rejected or opened in an unprivileged context" and "the second instance handler does not crash or leak memory" | 15 section 2 |
| R3-W2 | Bridge | Every bridged method with a foreign origin, a polluted prototype, oversized arguments, `..`, null bytes and a `blob:` origin. Every call rejected by origin and own property checks, and counted | 15 section 2 |
| R3-W3 | Popups and frames | `window.open`, `target=_blank`, meta refresh, redirect chains, iframe popups, `<webview>` creation. All denied, no new renderer receives the preload | 15 section 2 |
| R3-W4 | Shell sinks | `file://`, `smb://`, `javascript:`, embedded null, UNC paths, and `.app`, `.lnk`, `.desktop`, `.exe` names derived from a peer filename. Sinks accept only resolved paths inside the download directory with an allowlisted type | 15 section 2 |
| R3-W5 | Update | Unsigned artifact, tampered artifact, mismatched hash manifest. All three refused, the failing check is named: the detached signature over the hash list, then the per artifact SHA-256 comparison. The installed binary is unchanged. An older signed artifact whose own hash and signature verify is accepted, and that is residual row 25, because V2 has no version counter and no signed metadata for the manual protocol to refuse it with, and the About build date warning is the compensating control (section 6.1 step 4; `11-packaging-executable.md` sections 5.2 and 5.5) | 15 section 2 |
| R3-W6 | Installed package | Modify `app.asar`, add an `app/` directory beside it, replace a dylib or DLL, flip one fuse byte, all in a scratch copy. ASAR integrity and the code signature refuse to launch, and every single layer removal that still launches is recorded as a residual | 15 section 2 |
| R3-W7 | macOS trust | Remove quarantine, run from a translocated path, replace a nested helper with an unsigned binary, assess with `spctl`. Each tampered copy fails verification and the app reports its true signature state | 15 section 2 |
| R3-W8 | Windows trust | `Unblock-File`, a proxy DLL beside the exe, an unsigned nested binary, a run from a user writable directory. Verification fails and the loader does not pick up the planted DLL | 15 section 2 |
| R3-W9 | Linux launch | No FUSE, `--appimage-extract-and-run`, a hostile `LD_LIBRARY_PATH` and `LD_PRELOAD`, a crafted `.desktop` with field codes. Loader environment cleared, absolute paths, `desktop-file-validate` clean | 15 section 2 |
| R3-W10 | Instance and traces | A second instance, a tray survivor, a crash, cache and log inspection, a port scan. One instance, no survivor, no plaintext in a dump or cache, no listening port | 15 section 2 |

Cites: `14-cve-browser-stack.md` sections 2, 3.6, 4.4, 5.4, 6.6, 7.4, 8.8, 9.6, 11; `15-cve-packaging-native.md` sections 1, 2, 9.3.

### 6.6 Conflicts between the five inputs, resolved

Three places where the inputs disagree, or appear to. Each is resolved here so the build wave does not have to choose from memory.

| Conflict | What each input says | Resolution |
|---|---|---|
| The `cookieEncryption` fuse | `11-packaging-executable.md` section 6.1 leaves it disabled because no cookies exist, the session is in memory, and enabling it on macOS needs Keychain access and a valid signature. `15-cve-packaging-native.md` BC-W5 sets it on as cheap insurance and calls it a one way transition | Follow the packaging owner and leave it disabled in V2, recording the decision in the BC-W5 evidence so a later round changes it deliberately rather than by copying a checklist. S-2 means there is no storage API to create a cookie trail in the first place |
| Whether an update check exists | `14-cve-browser-stack.md` rule P2 asks the shell to fail closed when it has not checked for updates in N days. `11-packaging-executable.md` sections 5.1 to 5.3 forbid any version check, because it is a network request that tells whoever answers that this person runs this app | No update check in V2. Rule P1 is adopted (Chromium version and build hash in the About panel and the health file). P2's network requirement is rejected with its reason, and the offline substitute is the build date with a warning past 90 days. The cost is residual row 20 |
| The media bytes against the bundle line | `04-crypto-design.md` RECOMMENDED STACK and section 2.2 price the V2 delta at 4 to 6 KB of source and no dependency bytes. `12-media-pipeline.md` section 8 adds a 31,103 byte muxer and about 10 KB of code | Section 2.2's figure is the crypto and control delta and stays true for that scope. The media pipeline is a separate additive budget of about 76,700 B raw and 22,100 B gzipped in total. Two numbers for two scopes |

Cites: `11-packaging-executable.md` sections 5.1 to 5.3, 6.1; `12-media-pipeline.md` section 8; `14-cve-browser-stack.md` section 1; `15-cve-packaging-native.md` section 2; `04-crypto-design.md`, RECOMMENDED STACK.

One scope note on that last line, since section 6 is otherwise bounded to the five inputs. The third conflict is the one place where the comparison crosses outside them: the bundle line it argues against lives in `04-crypto-design.md` section 8.1, which section 2.2 of this blueprint already quotes, so 04 is named here as a cross-reference and not as a sixth input. The conflict itself is `12-media-pipeline.md` section 8 against section 2.2's figure.

## SELF-CHECK

Re-read the file end to end after the last edit, re-ran the stage acceptance commands under both shells, and verified every disposition from the round 1 review and the round 2 ledger against the current text. Results below are from the commands quoted, not from memory. The platform addendum was folded after the round 1 repair; its own re-run is the `### Addendum re-run` block, and the round 2 repair is the `### Round 2 repair dispositions` block at the end, which also retires the whole file INFRA count in favour of the default-path check.

### Stage acceptance

| # | Acceptance item | Result | Evidence |
|---|---|---|---|
| 1 | Output exists and is non-empty at `02-plan/output/blueprint-v2.md` | PASS | `test -s` exited 0 on the final file. Size and line count are not restated as literal totals beyond this point, because every edit to this SELF-CHECK changes them and the figure went stale twice; the gate is `test -s` plus `wc -c -l output/blueprint-v2.md`, run at the gate. The two historic figures, 86,122 bytes and 666 lines at the round 1 repair and 133,209 bytes and 916 lines at the addendum, stay as records of those moments. |
| 2 | At least five `## ` sections | PASS | `grep -c '^## '` printed 6 at the repair and 7 after the addendum: THREAT BASELINE, V2 ARCHITECTURE, WHAT STAYS, BUILD PLAN, RESIDUAL RISK, PLATFORM ADDENDUM, SELF-CHECK. The skill annex at 4.3.1 is a `####` heading and adds no `## ` line. |
| 3 | File contains a SELF-CHECK section | PASS | This section. `grep -L 'SELF-CHECK'` over the file prints nothing. |
| 4 | English, no em dashes or en dashes anywhere | PASS | `grep -rl $'\xe2\x80\x94' output/` and the `\xe2\x80\x93` twin both print nothing and exit 1, under /opt/homebrew/bin/bash 5.3.20 and under /bin/bash 3.2.57. Code point scan: U+2014 0, U+2013 0, U+2015 0, U+2212 0, U+2012 0. |
| 5 | The five required sections exist in the required order | PASS | Headings in file order: `## 1. THREAT BASELINE`, `## 2. V2 ARCHITECTURE`, `## 3. WHAT STAYS`, `## 4. BUILD PLAN`, `## 5. RESIDUAL RISK`. |
| 6 | The two High findings come first, and all 13 findings appear in the ledger | PASS | Section 1.1 is F-01, section 1.2 is F-02. The 1.4 table now has 13 rows, F-01 through F-13 (`grep -c '^\| F-'` = 13), with F-01 and F-02 added at the top and each naming its cards. |
| 7 | One architecture decision per pillar, each citing its research file | PASS | Seven `Cites:` lines, one per subsection 2.1 to 2.7. Citation counts in the file: 04-crypto-design 49, 06-ops-defense 43, 02-audit-findings 27, 05-transport-hardening 24, 03-threat-model 23, 07-skill-sweep 17, 01-trust-map 10, 08-registry-skills 4, 09-open-collections 2, 10-methodology-sources 2. |
| 8 | Safety-number SAS is the default, balanced SPAKE2 is opt-in, per 04 | PASS | Section 2.1 states SAS as the only content gate with the transcript formula, 60 digits in 12 groups, and content frames rejected before confirmation. SPAKE2 is balanced, opt-in, 6 digits, 3 attempts, with the verifier-record reason for rejecting SPAKE2+ and the OPAQUE rejection recorded. |
| 9 | Crypto stack is double ratchet over the data channel plus per-message AEAD for files, WebCrypto-first | PASS | Section 2.2 gives the three-DH HKDF root, KDF_RK and KDF_CK, AES-256-GCM with a constant nonce under a per-message key, and the Worker key boundary. Section 2.3 gives the per-file key, 64 KiB chunks, counter nonce and AAD. Bundle numbers are quoted only from the 04 8.1 table. |
| 10 | File transfer exports only the received span and Save is gated on completeness | PASS | Section 2.3 rules 6 to 9: lazy parts, concatenation only when received equals size and the digest matches, no Blob, no URL and no anchor on failure, and the old zero-padding branch deleted. |
| 11 | Versioned control envelope prevents silent drops of panic and migration frames | PASS | Section 2.4 defines `{v, k, sid, seq}`, a single dispatch table, counted unknown frames and the A1 kill threshold. |
| 12 | Kill switch, M1 to M5 migration, and the pagehide, idle override and code textarea fixes | PASS | Section 2.5 has the ordered Kill sequence, the Wipe availability fix, the M1 to M5 table, and five numbered wipe fixes. The clipboard is cleared only on kill, matching 06 3.5. |
| 13 | Transport default hardening plus optional cover mode, INFRA flagged | PASS | Section 2.6 lists six default items with no infrastructure, then the cover mode block with `iceTransportPolicy: "relay"`, `turns:` on 443 and short-lived credentials, tagged INFRA. |
| 14 | Monitor overlay is a separate macOS component in a separate trust domain | PASS | Section 2.7 specifies a launchd menu bar app with its own bundle id, signing identity, no listener, hash-chained log, the M1 to M5 rules and the explicit witness limits. |
| 15 | V1 strengths S-1 to S-8 preserved by name | PASS | Section 3 table rows S-1 through S-8, each with V1 evidence and a V2 obligation. |
| 16 | R2 sliced into ordered cards, each with file scope, one gate command, and the failure mode caught | PASS | 15 card rows R2-01 to R2-15. A script check found every row carrying exactly one backticked `python3` or `swift test` command, and 14 of 15 rows naming `03-build/output/probes/gate.py` in the file-scope column; the fifteenth, R2-14, runs `swift test` inside its own package scope. |
| 17 | R3 red-team plan present | PASS | Section 4.3: authorization and scope, ten app-specific classes, L1 to L4 levels, bypass exhaustion, mutation testing, an independent lane, the named F-01 and F-02 probes, and the R3 gate. |
| 18 | R4 Chromium checklist includes a packet-capture check that proves its own pass condition | PASS | Section 4.4 captures `'udp or tcp'`, so TCP 443 is in the file, and adds a tshark check on `tcp.port == 443` expecting a zero count. That check, not the DNS check, backs the no-HTTPS claim. Pass condition 3 accepts any STUN endpoint on the configured list and fails any other address. |
| 19 | Residual risk section, drawn from the limits sections | PASS | Section 5 had 18 rows at the repair, 24 after the addendum, and has 25 after the round 3 repair, each with source and what changes the decision. Row 18 records that no V2 default mode is undetectable against a passive ISP and that cover mode only narrows it; rows 19 to 24 are the platform residuals, and row 25 is the accepted rollback limit that R3-W5 no longer promises to refuse. |
| 20 | Default serverless path carries no INFRA item | PASS | Checked by default path rather than by a whole file count, because a literal count moves every time this SELF-CHECK grows and it has gone stale twice. Command: `sed -n '/^Default mode, no INFRA item:/,/^Cover mode, INFRA, optional:/p' output/blueprint-v2.md \| grep -Eiwc 'relay\|coturn\|turn\|turns'`. Fresh output on the final file: `0`, exit 1, which is the pass condition, since grep exits 1 when nothing matches. The `-w` flag matches the four tokens as words, so bare `turn:` and bare `TURN` are covered as well as `turns:`, and a word like `return` is not counted. Positive control on the same pattern: a line carrying bare `TURN` and `turn:443` prints 1, and a `return` line prints 0. The range depends on two headings that each occur once (`grep -c` with two `-e` patterns prints 2). Everything that needs infrastructure, coturn, `turns:` on 443 and the relay host, sits after the second heading. No whole file INFRA count is stated anywhere in this check. |
| 21 | No invented numbers, bundle sizes only from 04 | PASS | Every comma-grouped size in the bundle table was matched against `04-crypto-design.md` section 8.1. The zero-byte figure is now 52,428,800 bytes for a 50 MiB declared size, with the 49,999,000 figure explicitly attributed to 02 F-02's 50,000,000 byte example. The 32,503 figure is attributed to the noble x25519 row only. The only non-04 numbers elsewhere are 20,000 (MAX_TEXT), 52,428,800 (MAX_FILE arithmetic), and labelled design defaults: 4 files, 200 MiB, 2,000 log rows, 60 s timeout, 32 candidates, 20 minute aging prompt. |
| 22 | This is the plan, not the code, and only the output file was written | PASS | No HTML, Python or Swift artifact was created. The research base was re-checked after the lead's amendments: 03-threat-model.md and 05-transport-hardening.md were last written at 23:02:39, 08-registry-skills.md at 23:10:14, 09-open-collections.md at 23:06:24 and 10-methodology-sources.md at 23:06:30, all after this blueprint's first write at 23:00:59. This repair read the current files and cites them, and the annex states that 08, 09 and 10 landed after the first write. The only file in `02-plan/output/` is `blueprint-v2.md`. |
| 23 | Time budget about 25 minutes of tool work | PASS | Tool work for this repair ran inside the budget; the file was last written at the time recorded by `stat` below. |
| 24 | Addendum time budget about 30 minutes of tool work | PASS | Brief written at 23:48:33 and the file last written at the time recorded by `stat` below. The five inputs and the blueprint were read in full before the first edit, and the fold ran patch by patch. |

### Addendum re-run

The seven items the addendum brief names, each with the evidence that it landed. Results are from the commands quoted in the block after this table, run after the last addendum edit.

| # | Addendum item | Result | Evidence |
|---|---|---|---|
| 1 | Packaging decision, compressed: Electron on all three platforms, the rejection table, the pin, the per platform artifacts, the no updater protocol | PASS | Section 6.1: one DECISION line, four rejection rows (CEF, Tauri, Neutralino, Chrome app mode shim), the four layer pin naming the fuse pair and the compiled in SHA-256 with `app://` buffer serving, four artifact rows for macOS, Windows, Arch and other Linux, and the four step manual replacement protocol with the 90 day build date warning. |
| 2 | Media cards as build card rows in the R2 format | PASS | Section 6.2: seven rows R2-16 to R2-22, each with a file scope, one gate command and the failure it catches. A script check found all seven carrying exactly one `python3` gate. `finalize()` is named as the R2-18 gate condition, the muxer is priced at 31,103 B minified and 9,062 B gzipped, and the 60 MP image gate and the paste single path each have their own row. |
| 3 | UX cards folded by reference, both EXEC-ONLY flags kept | PASS | Section 6.3: ten rows UX-01 to UX-10 (`grep -c '^\| UX-'` = 10), each citing `13-platform-ux.md` section 5 rather than restating its pass condition. UX-09 and UX-10 carry EXEC-ONLY in the mode column, and the intro says they never gate the default artifact. |
| 4 | Wrapper build cards BC-W1 to BC-W14, folded by reference | PASS | Section 6.4: fourteen rows (`grep -c '^\| BC-W'` = 14), mode column splitting 6 EXEC-ONLY from 8 RELEASE after the round 2 repair, each row citing `15-cve-packaging-native.md` section 2 and naming its check. |
| 5 | Expanded R3 register, R3-BS-01 to 27 and R3-W1 to 10, joined as named cases with one line each | PASS | Section 6.5: `grep -c '^\| R3-BS-'` = 27 and `grep -c '^\| R3-W'` = 10, one line per case with its entry point and detail section. The joining paragraph maps the groups onto classes 1, 2, 3, 4 and 6, adds class 11 (platform patch state) and class 12 (wrapper), and names R3-W5 and R3-W6 as release gates. |
| 6 | Six new residual rows with their sources | PASS | Section 5 rows 19 to 24, appended to the existing table, which counted 24 rows numbered 1 to 24 at the addendum: Linux pinning gap, frozen engine, Windows RAM write gap, libwebrtc coverage gap, mux `finalize()` item, QR length inference. Each row carries a source and what changes the decision. The round 3 repair appends row 25, the rollback limit. |
| 7 | SELF-CHECK updated for the addendum, existing rows kept, section count and dash gates held | PASS | This block, plus rows 1, 2 and 19 carrying both the repair-time and the addendum-time figures, row 20 rewritten to the default-path check, plus row 24 for the fold budget. `grep -c '^## '` printed 7 and the two dash gates printed 0. |

Hygiene and scope, checked after the last edit:

| Check | Result | Evidence |
|---|---|---|
| English, no em dash and no en dash | PASS | Direct byte scan of the file: 0 occurrences of the three byte sequence E2 80 94, 0 of E2 80 93, and 0 non-ASCII bytes at all. `grep -rl` for both sequences under /bin/bash printed nothing and exited 1. |
| No new external claims and no new URL | PASS | Section 6 cites only the five input files, by name and section, so every claim traces without a network. It contains no link of any scheme. The only two network-shaped tokens in the whole file are the Chromium disk cache switch and the scheme allowlist in BC-W3, both code rather than links, and both predate this fold. All five inputs are listed with full paths in the header and at the top of section 6. |
| Only the blueprint was written | PASS | `02-plan/output/` holds `blueprint-v2.md` as its only file. The five research files, `CONTEXT.md`, `proof.md`, the briefs and `_config` were read only. |
| Existing content untouched apart from new rows | PASS | At the addendum, sections 1 to 5, the annex 4.3.1 and the repair tables kept their text: the changes outside section 6 were five source bullets in the header, six rows appended to the section 5 table, two new sentences after that table, and four SELF-CHECK rows whose figures moved plus row 24 and this block. The round 2 repair then edited 2.3 (rule 11), 4.3.1 (the install scan label), section 5 row 22 and the section 6 rows that F1 to F13 name. |
| Every addendum card row owns its gate case | PASS | All seven media rows and all ten UX rows carry exactly one `python3 ... gate.py` command, and each names the same case in its file scope column. |
| Classes and counts reconcile | PASS | 7 media cards, 10 UX cards (8 CORE, 2 EXEC-ONLY), 14 wrapper cards (6 EXEC-ONLY, 8 RELEASE), 7 trust map rows, 27 browser stack cases, 10 wrapper cases, 6 new residuals. |
| INFRA stays off the default path | PASS | Default-path check, not a whole file count: `sed -n '/^Default mode, no INFRA item:/,/^Cover mode, INFRA, optional:/p' output/blueprint-v2.md \| grep -Eiwc 'relay\|coturn\|turn\|turns'` prints `0` and exits 1. The pattern covers bare `turn:` and bare `TURN` as word matches, not only `turns:`. Section 6 contains no relay or TURN term at all, and the block between the two headings is unchanged. The whole file INFRA line and occurrence counts quoted in the two earlier blocks are retired, see the round 2 block. |

Addendum mechanical evidence, verbatim at the addendum, point in time rather than re-runnable: `wc` and the addendum size in this block describe the file as it stood then. The live totals are row 1 and the round 2 block.

```
test -s output/blueprint-v2.md                    -> exit=0
wc -c -l output/blueprint-v2.md                   -> 133209 916
grep -c '^## ' output/blueprint-v2.md             -> 7
grep -L 'SELF-CHECK' output/blueprint-v2.md       -> no output, exit=0
grep -c $'\xe2\x80\x94' output/blueprint-v2.md    -> 0
grep -c $'\xe2\x80\x93' output/blueprint-v2.md    -> 0
grep -c '^| F-' output/blueprint-v2.md            -> 13
grep -c '^| UX-' output/blueprint-v2.md           -> 10
grep -c '^| BC-W' output/blueprint-v2.md          -> 14
grep -c '^| R3-BS-' output/blueprint-v2.md        -> 27
grep -c '^| R3-W' output/blueprint-v2.md          -> 10
section 5 rows, numbered                          -> 24, sequentially 1 to 24
media and UX card rows without exactly one gate   -> 0 of 17
addendum size                                     -> 34601 bytes, section 6
URLs of any scheme in the addendum                -> 0
```

What this block does not prove: that the packaging choice is right, that the gates named in the new cards can be implemented as written, or that any CVE in the ledgers reaches this artifact. Nothing was built, signed, installed or run for this fold. The five inputs are design and ledger documents at their own stated confidence, and the four open measurements they name, the envelope length for the QR ceiling, the muxer `finalize()` failure, the iOS memory kill threshold and the audio drift past 60 s, stay open: two of them as residuals 23 and 24, and all four as UNVERIFIED marks in `12-media-pipeline.md`.

### Repair dispositions

| Item | Disposition | Result | Evidence |
|---|---|---|---|
| a1 | 32,503 attributed to the x25519 row only, P-256 labelled unmeasured | PASS | Section 2.1 SPAKE2 bullet now says no P-256 bundle is measured, the figure is the noble x25519 row, the 32.5 KB is a section 1.3 estimate, TweetNaCl 18,456 has no P-256 arithmetic, and the SPAKE2 library cost is unmeasured. |
| a2 | Header encryption aligned with 04 2.3, V2.1, stated rather than claimed as R2 | PASS | Section 2.2 DECISION and the header-encryption bullet both say deferred to V2.1 per 04 2.3, and say so explicitly. Card R2-03 scope removes header encryption and names V2.1. |
| a3 | 50 MiB zero count stated as 52,428,800 bytes | PASS | Section 1.2 says the export is the full 52,428,800 byte buffer, about 52.4 million zero bytes, and names 02 F-02's 49,999,000 as the decimal-MB example against `MAX_FILE = 50 * 1024 * 1024`. |
| a4 | RFC 8827 section 7 changed to 6.5 | PASS | Section 1.1 cites section 6.5, Communications Security, and quotes the MUST for out-of-band verification. |
| b1 | R2-13 has a gate that can pass as written | PASS | Card names the relay host parameter, `--relay-host turns:127.0.0.1:5349`, a loopback address the harness supplies, and defines PASS as exit 0 with `PASS cover` after three named assertions. Exit 2 only when the flag is omitted. |
| b2 | Gate cases inside their cards' declared scopes | PASS | Twelve card rows now name `03-build/output/probes/gate.py` with their case name in the file-scope column, R2-01 already named it, and section 4.1 states that a card owns the one case its scope names. |
| c | F-01 and F-02 rows in the 1.4 ledger | PASS | Both rows added above F-03 with High severity, disposition and card ids. The ledger now has all 13 findings. |
| d1 | Single-file no-build ruling cited to SETUP.md with its product-sheet source | PASS | Owner ruling 3 cites SETUP.md line 14 and `input/ephemeral-chat-overview.pdf`, its no install, build step or dependency line. |
| d2 | INFRA tag rule cited to 05 | PASS | Owner ruling 1 names `05-transport-hardening.md`, Method and tags, line 11, as the home of the tag rule, and says it is not an owner ruling. |
| d3 | I-4 has one concrete cadence | PASS | Invariant table says on demand and on a 20 minute aging prompt; a note after the table cites `06-ops-defense.md` section 3.7 and calls the number a design default; the Rotate row carries the same 20 minute prompt and source. |
| d4 | Residual row for the unmet undetectable target | PASS | Section 5 row 18: no V2 default mode is undetectable against a passive ISP, cover mode narrows it, the relay stays visible, the owner target is partly met, sources 05 sections 1.3, 2.2 and 3.6. |
| e1 | Trickle-attribute claim marked as resting on the UNVERIFIED sample | PASS | Section 2.6 item 6 keeps the source-verified gathering behaviour with line cites and marks the trickle attribute claim as resting on the 05 1.1 sample, quoting 05's UNVERIFIED wording and naming R3 re-derivation. |
| e2 | Invite-carries-public-IP claim marked the same way | PASS | Section 2.6 item 4, the mode table row and residual row 3 now label it inference from the source chain and RFC 8445, not an observed run, with the sample UNVERIFIED and R3 as the closer. |
| f1 | R4 capture filter proves the no-HTTPS claim | PASS | Filter is `'udp or tcp'`; the block adds a `tcp.port == 443` count expecting 0 and comments that this check, not the DNS one, backs the claim. The address table is built from the same full capture. |
| f2 | STUN count resolved | PASS | Section 2.6 item 2 replaces "tried in order" with a declared fallback order, states it is design intent and not a browser mechanism, and says the browser gathers from every configured URL (inferred, R3 re-derives). Pass condition 3 accepts configured endpoints, names the recorded provider as expected, and fails any other address. |
| f3 | 30 second clipboard rule aligned with 06 3.5 | PASS | Risk row 2 and wipe fix 5 both clear the textarea after 30 s, keep a Show button, and clear the clipboard only on kill, citing 06 3.5 and 2.5. |
| g | Skill annex under 4.3 | PASS | Section 4.3.1: two installed skills with identifiers, the blocked skill with its DANGEROUS scan verdict and its substitution, the five item authored queue in 10 section 5.3 order, and the gap status from 08 and 09 with WebRTC and privacy-monitor left as authored probes. Cites 08, 09 and 10 by path. |
| h | Stale SELF-CHECK row 22 updated | PASS | Row 22 now records the 23:02:39 amendments to 03 and 05 and the later 08, 09 and 10 writes, and states what this repair re-read. |

Mechanical evidence, verbatim at the round 1 repair, point in time rather than re-runnable. The INFRA count line is removed: the figure moved twice after this run and the default-path check replaces it.

```
test -s output/blueprint-v2.md                    -> exit=0
grep -c '^## ' output/blueprint-v2.md             -> 6
grep -L 'SELF-CHECK' output/blueprint-v2.md       -> no output, exit=0
grep -rl $'\xe2\x80\x94' output/                -> no output, exit=1 (bash 5.3.20 and bash 3.2.57)
grep -rl $'\xe2\x80\x93' output/                -> no output, exit=1 (bash 5.3.20 and bash 3.2.57)
grep -c '^| F-' output/blueprint-v2.md            -> 13
card rows with exactly one gate command           -> 15 of 15
card rows naming gate.py in scope                 -> 14 of 15 (R2-14 is the Swift package)
default mode block relay terms                    -> none
```

### Round 2 repair dispositions

One row per finding from the round 2 ledger, plus one per unverified lead. Every result is from the text and the commands in the evidence column, run after the last edit.

| Finding | Disposition | Result | Evidence |
|---|---|---|---|
| F1 | R3-W1 pass condition replaced, severity Medium | PASS | 6.5, R3-W1. Both 15 line 60 conditions are quoted: "the protocol URL is rejected or opened in an unprivileged context" and "the second instance handler does not crash or leak memory". The focus clause is gone from the file. Scoped absence check on the body only, before the SELF-CHECK heading: `sed -n '1,/^## SELF-CHECK/p' output/blueprint-v2.md \| grep -c 'focus signal'` printed 0 and exited 1, so the row text cannot count itself. The wording stays with E-12 at 15 line 108 and is not used as a pass condition here. |
| F2 | Release mode labels, severity Medium | PASS | 6.4. BC-W9, BC-W10, BC-W11 and BC-W13 are RELEASE. BC-W14 is decided explicitly EXEC-ONLY in a paragraph that names 15 section 9.3 and reads its own row at 15 section 2 as wrapper configuration. Measured mode column: 6 EXEC-ONLY, 8 RELEASE. Both SELF-CHECK rows that restated 10 and 4 now state 6 and 8. |
| F3 | TB-W rows and the update chain critical path, severity Medium | PASS | 6.4. TB-W1 to TB-W7 added, one row each, `grep -c '^\| TB-W'` = 7, cited to `15-cve-packaging-native.md` sections 1 and 9.3. TB-W4 flagged as the highest value boundary with 15 lines 43 and 52. The update chain is named the critical path once, citing 15 line 163. |
| F4 | Rollback refusal replaced with its limit in 6.1, severity Medium | PASS | 6.1 step 4. Scoped absence check on the body only, before the SELF-CHECK heading: `sed -n '1,/^## SELF-CHECK/p' output/blueprint-v2.md \| grep -c 'Refuse rollback'` printed 0 and exited 1. The step states that V2 has no version counter and no signed metadata, so the manual protocol cannot enforce rollback refusal, and that enforcing it needs the signed channel priced at 11 section 5.5. The 90 day build date warning stays, 11 line 334. The second site, R3-W5, was the remaining blocker on the older signed case in round 3; it now accepts that case as residual row 25, recorded in the round 3 block below. |
| F5 | Stale INFRA figure, method replaced | PASS | The literal whole file counts are retired from row 20, the addendum hygiene row and both verbatim blocks; row 1 stops restating a final byte count and line count for the same reason. Row 20 and the hygiene row now quote the default-path command and its fresh output: `0`, exit 1. That figure went stale twice because the text that states it grows with the file, so the check is now a property of the default block, not a count of the file. |
| F6 | R2-21 failure mode, severity Low | PASS | 6.2 R2-21. Failure mode now reads "A destination canvas allocated before the 60 MP gate (60,000,000 px, 240,000,000 B), or a bitmap not closed in `finally`". The 200 MP clause stays. |
| F7 | Top unaudited phrase, severity Low | PASS | 6.5 R3-BS-06 and section 5 row 22 both carry the 14 line 223 wording: the only libwebrtc code a party with an invite reaches with zero authentication, and a better pen test target than any CVE in 14 section 4.2. Scoped absence check on the body only, before the SELF-CHECK heading: `sed -n '1,/^## SELF-CHECK/p' output/blueprint-v2.md \| grep -ci 'top unaudited'` printed 0 and exited 1. |
| F8 | Class map, severity Low | PASS | 6.5 class map now reads "R3-BS-02 and R3-BS-06 extend class 1. R3-BS-09 and R3-BS-06 extend class 2", so R3-BS-09 is no longer unmapped. |
| F9 | makepkg sandbox clause, severity Low | PASS | 6.1 Arch and Omarchy artifact row. The no sandbox clause is gone from that row. Scoped count on the body only, before the SELF-CHECK heading: `sed -n '1,/^## SELF-CHECK/p' output/blueprint-v2.md \| grep -c 'runs as the user with no sandbox'` printed 1, and the one hit is BC-W12, where 15 line 86 does say it. The row now carries the 11 section 2.3 caveat, a locally built package has no signature guarantee. |
| F10 | UX names and scopes, severity Low | PASS | 6.3. UX-09 restored as "Shell window, menu, shortcuts, badge" with the 13 line 474 scope "Wrapper main process, menu template, disabled defaults, badge bridge". UX-02, UX-03, UX-04 and UX-06 restored to the 13 section 5 names and scopes, including `applyReact`, reaction map, pill render, hover row, palette, panel container, `pending` slots, 60 digit render and countdowns. Both EXEC-ONLY flags unchanged, ten rows, one gate each. |
| F11 | Sixth research file in 6.6, severity Low | PASS | 6.6. 04 is named as a cross-reference outside the five inputs, with the reason: the bundle line is `04-crypto-design.md` section 8.1, already quoted in section 2.2, and the conflict itself is 12 section 8 against section 2.2. The choice is stated as a scope note, not left implicit. |
| F12 | Never write to disk rule, severity Low, carried from round 1 fix 6 | PASS | 2.3 rule 11 added with the `04-crypto-design.md` section 4.3 rule 8 citation and a note that V1 already behaves this way. Missed in the round 1 repair pass, carried by the round 2 reviewer, and recorded here as carried rather than newly found. |
| F13 | Blocked skill verdict sourcing, severity Low | PASS | 4.3.1. The DANGEROUS verdict is labelled the lead's Hermes install session observation of 2026-11-26, and the entry states that `08-registry-skills.md`, `09-open-collections.md` and `10-methodology-sources.md` do not contain it. No research file is cited for it. |

Unverified leads, each checked against its input in this pass:

| Lead | Check | Result | Evidence |
|---|---|---|---|
| L1 | BC-W9 to BC-W13 qualifiers | PASS | All five verified against the 15 rows and restored where missing: BC-W9 "justified in the release note", BC-W10 "a directory the user cannot be tricked into sharing", BC-W11 `--appimage-signature` named for the external validator, BC-W12 "Never instruct `makepkg` from a moving branch", BC-W13 document the Chromium cache path and clear it on wipe. |
| L2 | R3-BS-03 attribution | PASS | 14 line 191 names a known public Pwn2Own or GitHub Security Lab renderer PoC for the build's major version from a local file URL. Restored. |
| L3 | R3-BS-17 burst | PASS | 14 line 331 reads "a burst of 16 KiB chunks with no `file-start`". Restored. |
| L4 | R3-W6 scratch copy | PASS | 15 line 65 reads "flip one fuse byte in a scratch copy". Restored as "all in a scratch copy", which covers the whole set of modifications. |
| L5 | 6.3 UX details | PASS | Covered by F10. `applyReact`, reaction map, pill render, hover row and palette are in UX-02; panel container and `pending` slots in UX-03; 60 digit render in UX-04; countdowns in UX-06. |
| L6 | Fuse version precision | PASS | 6.1 layer 2 now reads Electron 16.0.0 and Electron 30.0.0, matching 11 line 250. Section 5 row 19 keeps "Electron 16 and later" and "Electron 30 and later", which is 11 line 268's own wording. |

Round 2 mechanical evidence, verbatim:

```
test -s output/blueprint-v2.md                     -> exit=0
grep -c '^## ' output/blueprint-v2.md              -> 7
grep -L 'SELF-CHECK' output/blueprint-v2.md        -> no output, exit=0
grep -c $'\xe2\x80\x94' output/blueprint-v2.md     -> 0
grep -c $'\xe2\x80\x93' output/blueprint-v2.md     -> 0
grep -c '^| F-' output/blueprint-v2.md             -> 13
grep -c '^| UX-' output/blueprint-v2.md            -> 10
grep -c '^| BC-W' output/blueprint-v2.md           -> 14
grep '^| BC-W' output/blueprint-v2.md | grep -c '| EXEC-ONLY |'   -> 6
grep '^| BC-W' output/blueprint-v2.md | grep -c '| RELEASE |'     -> 8
grep -c '^| TB-W' output/blueprint-v2.md           -> 7
grep -c '^| R3-BS-' output/blueprint-v2.md         -> 27
grep -c '^| R3-W' output/blueprint-v2.md           -> 10
sed -n '/^Default mode, no INFRA item:/,/^Cover mode, INFRA, optional:/p' output/blueprint-v2.md | grep -Eiwc 'relay|coturn|turn|turns'  -> 0, exit=1
```

### Round 3 repair dispositions

One row per item in the round 3 brief, with the F4 item split into its second site, its residual row and its concept re-grep. Every result is from the text and the commands quoted, run after the last edit.

| Item | Disposition | Result | Evidence |
|---|---|---|---|
| F4 second site | R3-W5 stops refusing an older signed artifact | PASS | 6.5, R3-W5 (line 791). The row tests three cases, unsigned artifact, tampered artifact and mismatched hash manifest. All three are refused, the failing check is named as the detached signature over the hash list and then the per artifact SHA-256 comparison, and the installed binary is unchanged. An older signed artifact whose own hash and signature verify is accepted as residual row 25, because V2 has no version counter and no signed metadata for the manual protocol to refuse it with, with the About build date warning as the compensating control. The row cites section 6.1 step 4 and `11-packaging-executable.md` sections 5.2 and 5.5. |
| Residual row 25 | The rollback limit sits in the section 5 table, not only in 6.1 | PASS | Section 5 row 25 (line 603). It names the case, an older signed build that verifies and can be reinstalled, the reason, no version counter and no signed metadata so a hash comparison cannot tell new from old, the source `11-packaging-executable.md` sections 5.2 and 5.5 plus section 6.1 step 4, and the decision changer, the signed channel with a monotonic counter, a key off the build machine, a verifying client and a revocation path that 11 section 5.5 prices. It is named a V3 conversation. The table now counts 25 numbered rows, which `awk` over section 5 counting `^\| [0-9]` printed as 25. |
| F4 concept re-grep | Every remaining occurrence is a test case, a firing control or the limit | PASS | Body-scoped, so the rows in this block that quote the check cannot count themselves: `sed -n '1,/^## SELF-CHECK/p' output/blueprint-v2.md \| grep -n -i 'older signed\|rollback\|refus'` printed 14 lines and `grep -c` printed 14. Read one by one: 263 the unknown `v` refusal, 295 the `window.close` refusal, 317 the migration refusal, 444 the R2-13 gathering refusal, 478 the rekey rollback test case, 506 the refused install of `csp-policy-generator`, 536 the third context refusal, 603 row 25, 651 the 6.1 step 4 limit, 673 the R2-19 over-cap refusal, 678 the 600 s ladder refusal, 774 R3-BS-15, 791 R3-W5, 792 R3-W6. No line promises rollback refusal: 651 and 603 state that it cannot be enforced and what would enforce it, and 791 accepts the case. |
| N1 | Four evidence cells rescoped to the body, fresh output quoted | PASS | Rows F1 (line 938), F4 (941), F7 (944) and F9 (946). Each check now runs `sed -n '1,/^## SELF-CHECK/p' output/blueprint-v2.md` first, so the row text is outside the counted range. Fresh output: `grep -c 'focus signal'` 0, exit 1; `grep -c 'Refuse rollback'` 0, exit 1; `grep -ci 'top unaudited'` 0, exit 1; `grep -c 'runs as the user with no sandbox'` 1, exit 0, the one hit being BC-W12 at line 730. Every value reproduces on a rerun. |
| N2 | Default-path pattern covers bare `turn:` and bare `TURN` | PASS | Rows 841 (stage item 20), 871 (hygiene) and 979 (round 2 evidence) now run `grep -Eiwc 'relay\|coturn\|turn\|turns'` on the same `sed` range. Fresh output: `0`, exit 1. Positive control on the same pattern: a line carrying bare `TURN` and `turn:443` prints 1, and a `return` line prints 0, so the `-w` anchor adds the two missing token forms without counting `return`. |
| N3 | UX-01, UX-05, UX-07 and UX-08 names and scopes restored from 13 section 5 | PASS | 6.3. UX-01 reads "`msg` frame gains `mid`", matching 13 line 466. UX-05 is "Pairing panel states" with "TTL countdown", matching 13 line 470. UX-07 opens "Gallery sheet", matching 13 line 472. UX-08 is "Theme and accessibility baseline" with "light and dark blocks", matching 13 line 473. All four keep one `gate.py` command and their failure mode column. |
| N4 | BC-W8 aligned to the no-updater design | PASS | 6.4, BC-W8 (line 726). It reads: no auto update in V2, the app performs no update check and sends no notification, replacement is manual and hash verified per section 6.1, a download may happen only by the user's own action and an install may not. That matches 6.1 (line 646) and the second row of 6.6, no update check in V2. |

Round 3 mechanical evidence, verbatim after the last edit:

```
test -s output/blueprint-v2.md                     -> exit=0
grep -c '^## ' output/blueprint-v2.md              -> 7
grep -L 'SELF-CHECK' output/blueprint-v2.md        -> no output, exit=0
grep -rl $'\xe2\x80\x94' output/                    -> no output, exit=1 (/bin/bash and /opt/homebrew/bin/bash)
grep -rl $'\xe2\x80\x93' output/                    -> no output, exit=1 (/bin/bash and /opt/homebrew/bin/bash)
grep -c $'\xe2\x80\x94' output/blueprint-v2.md      -> 0
grep -c $'\xe2\x80\x93' output/blueprint-v2.md      -> 0
non-ASCII bytes in the file                        -> 0
section 5 numbered rows                            -> 25
body before SELF-CHECK, grep -c 'focus signal'     -> 0, exit=1
body before SELF-CHECK, grep -c 'Refuse rollback'  -> 0, exit=1
body before SELF-CHECK, grep -ci 'top unaudited'   -> 0, exit=1
body before SELF-CHECK, no sandbox clause count    -> 1
default block, grep -Eiwc 'relay|coturn|turn|turns' -> 0, exit=1
body before SELF-CHECK, grep -Eic 'older signed|rollback|refus' -> 14
```

Size and line count are not restated here, for the reason row 1 gives: the figure moves with every edit to this block. `wc -c -l` at the gate is the check.

Known limitations of this self-check: it proves structure, citation presence, number provenance and hygiene, and that each named review disposition has a landed edit. It does not prove that the design is correct, that the R2 gates can be implemented as written, or that the UNVERIFIED SDP observations hold. The owner review against the research, the R3 re-derivation and the R3 red team are the checks for that, as `02-plan/CONTEXT.md` states.

STATUS: complete. All stage acceptance items PASS, all repair dispositions PASS, all seven addendum items PASS, all thirteen round 2 findings F1 to F13 PASS with the six unverified leads checked and fixed or confirmed, and every round 3 item PASS: the F4 second site in R3-W5, residual row 25, the whole file concept re-grep, and N1 to N4. Item 18's no-HTTPS claim has a capture check that can fail; the two sample-derived transport claims stay labelled UNVERIFIED until R3 re-derives them. Section 5 now has 25 rows: the platform addendum added six (rows 19 to 24) and the round 3 repair added row 25, the rollback limit. The round 2 repair changed no design decision. The round 3 repair changes one gate condition, because R3-W5 no longer refuses an older signed artifact that V2 cannot detect, and it records that case as accepted, with the signed channel named as the V3 change. Stage gates were green under /bin/bash 3.2.57 and /opt/homebrew/bin/bash 5.3.20 after the last edit.
