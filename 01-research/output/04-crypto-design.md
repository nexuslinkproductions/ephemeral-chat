# 04 Crypto Design, V2 application layer

RUN: w1-ephemeral-hardening-20261126, lane 4 of 7.
INPUT: `input/ephemeral-chat-v1.html`, 35,598 bytes.
SCOPE: application-layer cryptography for V2. Transport hardening is lane 5, threat model is lane 3, ops is lane 6. This file owns pairing, the key schedule, per-message AEAD, post-quantum options, deniability, wipe semantics, and single-file library fit.

## 0. What V1 actually does, and why it is not enough

V1 has no application-layer cryptography at all. Every byte of user content is written to the SCTP data channel as plaintext and protected only by DTLS, which the browser terminates inside its own stack.

| Fact | Evidence |
|---|---|
| Text is sent as plaintext JSON over the data channel | `input/ephemeral-chat-v1.html:849` |
| File bytes are sent as raw ArrayBuffer chunks, no per-chunk tag | `input/ephemeral-chat-v1.html:906-923` |
| File metadata (name, size, MIME) is sent as plaintext JSON | `input/ephemeral-chat-v1.html:898-904` |
| Pairing code is base64(gzip(SDP)), nothing else | `input/ephemeral-chat-v1.html:722-730`, `:761`, `:792` |
| The code carries the DTLS fingerprint because it carries the whole SDP | `input/ephemeral-chat-v1.html:761`, `:815` |
| One data channel, ordered, reliable | `input/ephemeral-chat-v1.html:755` |
| ICE is Google STUN only | `input/ephemeral-chat-v1.html:442-445` |
| Wipe closes the peer, revokes blob URLs, clears the DOM and textareas | `input/ephemeral-chat-v1.html:541-552`, `:554-605` |

Three consequences drive every recommendation below.

1. **Whoever carries the invite code can read and rewrite it.** The code is the SDP, so it is also the DTLS fingerprint. A party that can modify the code in transit (Slack, email, a link shortener) can substitute its own SDP on both sides and become a DTLS-terminating MITM. V1 has no second check, no out-of-band comparison, and no binding between the code and the people using it.
2. **Transport keys are the only keys.** If DTLS is broken later, or a future relay or SFU terminates DTLS, or the browser process is dumped after the session, the content is exposed and there is nothing underneath. There is no key the page controls, and therefore nothing the page can destroy.
3. **The wipe is a UI and buffer cleanup.** It clears `dc`, `pc`, `incoming`, the DOM, and textareas (`:541-552`, `:559-570`). The DTLS keys live in the browser's network stack and the page can neither read nor zero them. That is not a flaw in V1's code, it is the ceiling of transport-only encryption.

V2 fixes this with four layers, in dependency order: an authenticated pairing step, an initial key agreement that mixes classical and optionally post-quantum secrets, a double ratchet that derives a fresh key for every message, and per-message AEAD for all content including files. Each layer is independently useful, and each is small enough to inline.

---

## 1. Pairing: from a swappable code to an authenticated exchange

### 1.1 The failure to fix

The invite code is an SDP blob (`:761`). The DTLS fingerprint is inside it, so the code is self-authenticating only in the sense that both ends agree on whatever fingerprint arrived. If Mallory rewrites the code, Alice and Bob each complete DTLS with Mallory, and neither can tell. The in-page copy's "encrypted in transit" claim (`:361`) is true hop by hop and false end to end under an active code-channel attacker.

Three candidate mechanisms are worth considering, and they differ in who has to do work.


### 1.2 Option A, safety numbers (recommended default)

Mechanism. After the DTLS connection opens, both sides compute a short authentication string over the complete public transcript, which is every public value in the key schedule:

```
th  = SHA-256( "eph-v2-transcript" || sort(fpA, fpB) || sort(ephA, ephB) ||
               sort(statA, statB) || kem_pk || suite_id )
sas = SHA-256( "eph-v2-sas" || th )
display = 12 groups of 5 decimal digits from sas  (60 digits)
rk  = HKDF-SHA256( salt = 32 zero bytes, ikm = dh_concat,
                   info = "eph-v2-root" || th, 32 )
```

The transcript hash goes into the HKDF info field, not the salt. It is public, so it adds no entropy; its job is binding. It guarantees that the number on screen and the keys in use describe the same transcript, so a UI cannot end up showing a matching number for a different key schedule.

Both users then compare the number over a channel the attacker does not control, ideally voice or in person. If it matches, the pairing is authenticated. If it does not, the session aborts before any content is sent, and the UI must refuse to display the number as "verified" until a human confirms.


Why this is the Signal approach. Signal's safety number is a sorted concatenation of two 30-digit fingerprints, displayed as 12 groups of 5 digits, specifically so that two comparisons collapse into one and the encoding survives localization and can be read aloud ([signal.org/blog/safety-number-updates](https://signal.org/blog/safety-number-updates/), fetched, title "Safety number updates").

Fit for a single file with no dependencies. Zero bytes of library. About 25 lines: parse both SDP fingerprints, hash the transcript with `crypto.subtle.digest`, render 60 digits, gate the chat UI on a match or an explicit override. WebCrypto SHA-256 is native.

What it does not fix. It is a human check. A user who clicks through without comparing gets no protection. It also cannot be automated, so it does not help the "unkeyed inbound traffic never gets an answer" goal on its own; it authenticates after the transport is up, so it must be paired with a rule that no content frame is accepted before the SAS is confirmed.

### 1.3 Option B, SPAKE2+ (RFC 9383), and why it is not the V2 default

SPAKE2+ derives a strong shared key from a password with no risk of disclosing the password, is simple to implement, works in any prime-order group, and is efficient ([RFC 9383](https://www.rfc-editor.org/rfc/rfc9383.html), fetched, title "SPAKE2+, an Augmented Password-Authenticated Key Exchange (PAKE) Protocol").

The important structural detail: SPAKE2+ is **augmented**. Only one party uses the password directly (the Prover); the other holds a registration record computed once during a registration phase (the Verifier). RFC 9383 states this explicitly in its introduction, and says the record "cannot be used directly to successfully run the protocol as a Prover".

That is a client-server shape. In a two-party ephemeral chat both people know the same short password and neither has a registration record, so the correct primitive is balanced SPAKE2, not SPAKE2+. Using SPAKE2+ here would force one peer to store a verifier record, which contradicts the product's zero-persistence rule and adds a state file that the kill switch would then have to wipe.

The security argument that matters is the online-guessing bound. A PAKE converts an active MITM into an online password guess. With a 6-digit code and a hard limit of three attempts per pairing, an attacker's success probability is about 3 in 10^6 per session, and the session is dead after that. That is the mechanism that kills the MITM and code-leak scenarios: a leaked invite code is useless without the separately shared password, and a code-channel attacker who can read and rewrite everything still has to guess the password online, once, with no offline oracle.

Cost. SPAKE2 needs group operations that WebCrypto does not expose: scalar multiplication is available through ECDH, but point addition and arbitrary point hashing are not. So it needs a curve library, and the cheapest audited option is noble-curves at 32.5 KB minified (measured below), which nearly doubles the 35.6 KB app. It also needs a password entry UI, a wrong-password path, and a lockout counter, and it needs the password to travel on a channel independent of the code, or the whole exercise is circular.

Verdict. Correct primitive, wrong rung for V2. Ship it as an opt-in "high assurance pairing" mode in V2.2, gated on a user who actually has a second channel. Do not make it the default, because the default must work with one pasted code and no setup.

### 1.4 Option C, OPAQUE (RFC 9807), rejected for this product

OPAQUE is an augmented PAKE "that supports mutual authentication in a client-server setting without reliance on PKI" and provides security against pre-computation attacks upon server compromise ([RFC 9807](https://www.rfc-editor.org/rfc/rfc9807.html), fetched, title "The OPAQUE Augmented Password-Authenticated Key Exchange (aPAKE) Protocol"). It requires a registration phase, a server-side credential file, and a server that answers credential requests, including fake responses for unknown users to prevent enumeration (section 6.3.2.2 of the RFC).

There is no server in this product, by design, and adding one to hold OPAQUE records would create exactly the central store the product exists to avoid. OPAQUE is the right answer to a different question (password login to a service). Reject, and say so in the design notes so nobody reopens it.

### 1.5 Pairing recommendation

Default V2: safety number comparison, bound into the key schedule info field, with content frames rejected until the user confirms. Optional V2.2: balanced SPAKE2 with a 6-digit password typed by both, using P-256 from noble-curves, with a 3-attempt lockout and a hard abort. OPAQUE: out of scope, documented as rejected.

The SAS value must cover the complete transcript, not just the DTLS fingerprint. If it covered only the fingerprint, an attacker who terminates DTLS on both legs and runs a separate app handshake would have two different fingerprints and the numbers would not match, but the code would be verifying the wrong layer. Hashing the app public keys and the suite id into the same transcript makes the displayed number a statement about the keys actually used, which is the property the check is supposed to have.


---

## 2. Key schedule: PQXDH shape plus the double ratchet

### 2.1 Initial agreement

V2 uses a three-DH X25519 agreement (ephemeral to ephemeral, plus each side's per-session static key against the other side's ephemeral) and optionally one ML-KEM-768 encapsulation. The shape follows PQXDH, which establishes a shared secret between two parties who authenticate each other based on public keys and provides post-quantum forward secrecy ([PQXDH spec](https://signal.org/docs/specifications/pqxdh/), fetched, title "The PQXDH Key Agreement Protocol"). PQXDH is built for asynchronous sessions with published prekeys; this product is synchronous and has no server, so drop the prekey lookup and keep the combiner:

```
ikm = X25519(ephA, ephB) || X25519(ephA, statB) || X25519(statA, ephB)   [|| mlkem_ss]
rk  = HKDF-SHA256(salt = 32 zero bytes, ikm = ikm, info = "eph-v2-root" || th, 32)
```

where `th` is the transcript hash from section 1.2.

All three DH outputs are needed for the same reason X3DH uses three: it keeps the session secret if any one of the ephemeral keys is weak, and it binds both identities without signatures. If ML-KEM is enabled, its 32-byte shared secret is concatenated and the whole thing goes through one HKDF, which is exactly the construction RFC 10024 uses for TLS 1.3 hybrids (see section 4).

### 2.2 The double ratchet is the "transformers" mechanism

The owner's ask, keys that constantly change, is the double ratchet. The Signal specification states the property directly: "The parties derive new keys for every Double Ratchet message so that earlier keys cannot be calculated from later ones", and DH outputs are mixed in "so that later keys cannot be calculated from earlier ones" ([Double Ratchet spec, revision 4, 2025-11-04](https://signal.org/docs/specifications/doubleratchet/), fetched, title "The Double Ratchet Algorithm").

State per peer (eight variables, all small):

```
RK              root key, 32 bytes
CKs, CKr        sending and receiving chain keys, 32 bytes each
DHs, DHr        current ratchet key pairs and peer public keys
Ns, Nr          message counters per chain
PN              previous chain length
skipped         bounded map of (dh_pub, n) -> message key, max 32 entries
```

Two KDF steps, both native:

```
KDF_RK(rk, dh_out) = HKDF-SHA256(salt = rk, ikm = dh_out, info = "eph-v2-ratchet", 64)
                     -> (new_rk, new_ck)
KDF_CK(ck)         = HMAC-SHA256(ck, 0x01) -> mk
                     HMAC-SHA256(ck, 0x02) -> next_ck
```

Per-message send: `mk, CKs = KDF_CK(CKs)`, then encrypt with a key derived from `mk`, then zero `mk`. Per-message receive: step `CKr` until `Nr` matches, reject anything beyond the skip window, decrypt, zero.

DH ratchet: when a peer receives a header with a new `DHs` public key, it performs `KDF_RK` with the new DH output, resets the receiving chain, and on its next send generates a new key pair and resets the sending chain. That is one X25519 operation per turn change, not per message, so the cost is negligible.

Simplification that is safe here. The data channel is ordered and reliable (`:755`), so messages arrive in order and skipped keys are only needed for the turn-overlap window where both peers send before receiving the other's new ratchet key. Keep a 32-entry skipped cache and drop the general out-of-order machinery. Mark the ceiling: if the transport ever moves to unordered or to a relay that reorders, the cache size and the replay window must be revisited.

### 2.3 Header encryption

Without it, every frame leaks `dh_pub, PN, N` in the clear to any relay or network observer, which reveals message counts, turn structure, and timing even though content is encrypted. The Signal spec defines a header encryption variant (section 4) at the cost of one extra AEAD per message and a header key chain.

Recommendation: encrypt headers for message frames in V2.1. The cost is one HMAC and one AES-GCM call per message over about 48 bytes, and it removes a metadata channel that lane 5 cannot close at the transport layer. File chunk frames do not need it because they already sit inside a file key with a counter nonce and the file-start frame carries the metadata once.

### 2.4 What this buys against a later DTLS or relay compromise

- **Later DTLS break.** Transport keys and app keys are independent. A future DTLS flaw, or a browser build with a weak RNG, or a captured handshake does not yield any message key, because every message key came from an HMAC chain seeded by a DH output the attacker never saw.
- **Relay or TURN operator.** A TURN relay forwards DTLS records and never holds keys, so it sees ciphertext plus IP metadata. An SFU or a recording relay that terminates DTLS would see plaintext at the transport layer; with the ratchet in place it sees ciphertext at the app layer and cannot derive keys.
- **Later device compromise.** Past messages stay closed because chain keys were deleted as they advanced. The spec treats this as a first-class requirement (section 8.1, "Secure deletion", and section 8.10, "Deletion of old KDF Chain state").
- **Session key dump from a live tab.** An attacker who dumps the JS heap gets the current `RK, CKs, CKr` and can read messages from that point forward until the next DH ratchet step, and can read nothing before it. That is the correct and expected failure mode, and it is why the kill switch must force a DH ratchet, not just a UI reset.

---

## 3. Post-quantum hybrid, ML-KEM with X25519

### 3.1 What the standard actually says

RFC 10024 defines X25519MLKEM768 for TLS 1.3 and gives exact sizes: the client share is 1216 bytes (1184 bytes ML-KEM-768 encapsulation key plus 32 bytes X25519), the server share is 1120 bytes (1088 bytes ML-KEM ciphertext plus 32 bytes X25519), and the shared secret is 64 bytes, 32 from each part, concatenated with the ML-KEM secret first ([RFC 10024](https://www.rfc-editor.org/rfc/rfc10024.html), fetched, title "Post-Quantum Traditional (PQ/T) Hybrid Key Agreement Mechanisms for TLS 1.3", Standards Track, August 2026).

The ordering rule in that RFC is worth copying exactly: the ML-KEM secret goes first for the X25519 combiner because it must be the FIPS-approved component in that suite. For this product the order only needs to be fixed and domain-separated, but using the standard order costs nothing and makes the code auditable against the RFC.

### 3.2 Fit and cost

- Wire cost at pairing: 1184 bytes of ML-KEM public key added to the invite code, and 1088 bytes of ciphertext added to the reply. Base64 inflates by 4/3 and the bytes are random, so gzip does not help. The invite code grows from about 650 characters to roughly 1.7 KB, the reply by about 1.5 KB. That is a real UX change for a code people paste by hand.
- Code cost: noble-post-quantum `ml-kem` bundles to 23,232 bytes minified, 9,779 bytes gzipped (measured, see section 8). That is 65 percent of the entire V1 file before any glue.
- Security value: it closes harvest-now-decrypt-later against the initial agreement. Against a 30-minute ephemeral chat the value is low, because the record an adversary would need to keep is small and the content is usually not worth a future quantum computer. The honest framing is defense in depth for a specific user, not a general need.

### 3.3 The ratchet stays classical in V2

The double ratchet's DH steps are X25519 only, so the initial hybrid protects the start of the session but not the ongoing ratchet. The Signal spec now defines a Sparse Post-Quantum Ratchet (section 5) and a Triple Ratchet (section 6) for hybrid ongoing security. Implementing either correctly is a multi-week job with new failure modes (epoch state clearing, SCKA choice), and neither is needed for a session that lives 30 minutes.

Recommendation: hybrid ML-KEM at initial agreement in V3, as a separate build variant with an explicit badge, and no PQ ratchet. Mark this as a deliberate ceiling. Revisit if sessions become long-lived or if the product starts carrying content with a long confidentiality lifetime.

---

## 4. Per-message AEAD for text, files, and images

### 4.1 The nonce problem disappears when the key is per message

The usual AEAD footgun is nonce reuse. libsodium's own documentation is blunt about the precondition: "The public nonce npub should never ever be reused with the same key" ([XChaCha20-Poly1305 construction](https://libsodium.gitbook.io/doc/secret-key_cryptography/aead/chacha20-poly1305/xchacha20-poly1305_construction), fetched, title "XChaCha20-Poly1305 construction | The Sodium crypto library").

A double ratchet gives us a fresh key per message, so the nonce cannot collide across messages even if it is constant. That removes the entire reason to prefer an extended-nonce AEAD here. Concretely:

```
key   = HKDF-SHA256(ikm = mk, salt = 32 zero bytes, info = "eph-v2-aead", 32)  -> AES-256-GCM
nonce = 12 zero bytes
aad   = "eph-v2-msg" || direction || counter
```

The invariant to enforce in code, with an assertion, is that `mk` is never used twice and the counter is strictly monotonic per direction. Everything else follows.

### 4.2 AES-GCM versus XChaCha20-Poly1305

| | AES-256-GCM, WebCrypto | XChaCha20-Poly1305, noble-ciphers |
|---|---|---|
| Library bytes | 0 | 11,383 minified, 4,796 gzipped (measured) |
| Nonce | 96 bit, constant under a per-message key | 192 bit, safe with random nonces under a long-lived key |
| Speed | Hardware AES on every current CPU and phone | Pure JS, slower, constant time by construction |
| Availability | SubtleCrypto in all target browsers | Any JS engine, including non-browser test harnesses |
| Misuse resistance if a key repeats | Fails catastrophically | Also fails, Poly1305 does not save you |

XChaCha exists so that random 192-bit nonces are safe under one long-lived key. We do not have a long-lived key. The correct choice for this app is AES-256-GCM through WebCrypto: zero bytes, hardware speed, and no dependency. Keep XChaCha as the fallback for the non-WebCrypto test harness and for a future non-browser client, where its 11.4 KB is acceptable.

Note one deviation from the Signal spec's recommendation. Section 7.2 suggests SIV or AES-CBC with HMAC for misuse resistance. We do not need misuse resistance because the key schedule makes reuse structurally impossible, and AES-GCM is the only AEAD the platform gives us everywhere for free. Record the deviation and the reason.

### 4.3 Files and images

V1 trusts the sender's declared size and writes incoming bytes into a preallocated buffer of that size (`:998-1016`), then wraps the result in a Blob with no integrity check (`:1038-1053`). A malicious peer can therefore claim 50 MB and send nothing, or send a corrupted image that the receiver previews. There is no per-chunk authentication and no binding between the metadata frame and the bytes that follow.

V2 file transfer:

```
file-start  { k:"file-start", id, name, size, type, chunks, key_wrapped, nonce_prefix }
              key_wrapped = AES-GCM(HKDF(mk, "eph-v2-wrap"), file_key)   // 32 byte file key, 16 byte tag
chunk i      AES-256-GCM(file_key, nonce = prefix(4) || be64(i), aad = id || i || size || chunks)
file-end     { k:"file-end", id, digest = SHA-256(plaintext) }
```

The wrap uses its own derived key, never `mk` directly, because the message body is also encrypted under `mk` and two AES-GCM calls with one key and one constant nonce is exactly the nonce reuse we are trying to make impossible. Derive separate keys with distinct `info` strings for the body, the wrap, and the header, and zero `mk` after the last use.

Rules:

1. The file key is random 32 bytes per file, wrapped under the current message key and zeroed immediately after the wrap. A file is therefore forward secret to the same degree as the message that started it.
2. Chunk size 64 KiB. 16 KiB in V1 (`:428`) is fine for throughput but means 3,200 GCM calls for a 50 MB file; 64 KiB cuts that to 800 with the same tag overhead.
3. Nonce = 4-byte random prefix per file plus an 8-byte big-endian counter. Unique per file key by construction. Do not derive the prefix from the file id, because the id is attacker-controlled metadata.
4. AAD binds the id, the chunk index, the declared size, and the chunk count. A truncated file, a reordered chunk, or a swapped file id all fail the tag.
5. Reject the whole file on any tag failure. Never render a partial image. V1's `bad` flag keeps partial data (`:1045`); V2 must discard.
6. Hard cap in-memory allocation at the declared size before allocating, and refuse a `size` or `chunks` that disagrees with the bytes received. Fail closed on `size > MAX_FILE` (V1 does this at `:1001`, keep it).
7. Decrypt into an array of `Uint8Array` and only at `file-end` build `new Blob(parts, { type })`. Verify the SHA-256 digest at `file-end` as a cheap end-to-end check, then revoke and zero on wipe.
8. Never write to disk. No downloads until the user clicks Save, which V1 already does. The download path is the only place plaintext leaves the page, and it is user initiated.

Memory ceiling, mark this as an inference: a 50 MB file costs about 50 MB of ciphertext plus 50 MB of plaintext at peak, and Blob construction may copy once more. That is 100 to 150 MB of tab memory, which is fine on desktop and risky on iOS Safari under memory pressure. Keep the 50 MB cap and drop to 16 MB on mobile if the tab is killed in testing.

### 4.4 Why per-message AEAD also fixes the file-name leak

V1 sends the file name and MIME type in plaintext JSON (`:898-904`). Names are content. In V2 the metadata frame is inside the ratchet envelope, so the relay sees only ciphertext and a length.

---

## 5. Deniability

### 5.1 What the protocol gives

PQXDH "provides post-quantum forward secrecy and a form of cryptographic deniability" ([PQXDH spec](https://signal.org/docs/specifications/pqxdh/), section 4.4 is titled "Deniability"). The mechanism is the absence of signatures: authentication comes from DH and from MACs over keys both parties can compute, so either party can produce a transcript that is indistinguishable from a real one. The double ratchet keeps that property because it never adds a signature over message content.

V2 preserves it by construction:

- No long-term identity keys. The per-session static key is generated at invite time and destroyed at wipe.
- No Ed25519 signatures anywhere in the message path.
- SAS comparison is a shared check, not a signature. It proves both sides derived the same keys; it does not produce evidence a third party can verify.
- PAKE key confirmation is deniable between the two parties, because both know the password and either could have simulated the exchange. A stored verifier record would weaken this, which is another reason to avoid SPAKE2+ here.

### 5.2 What breaks it

- Adding identity keys or signed messages, for example to support multi-device or a contact list. That trade must be explicit, and it is not worth it for a 30-minute session.
- OPAQUE or any server-side credential record, which is verifiable evidence held by a third party.
- Screenshots, OS-level screen recording, and the peer's own copy of the plaintext. Deniability is a property of the protocol transcript, not of the human at the other end. Say this plainly in the product copy and do not oversell it.
- Any logging on either endpoint. V1 has none, keep it that way.

### 5.3 Honest verdict

Deniability here is real but narrow: it protects against a later claim that a specific message was sent, as long as the attacker does not have either endpoint's device or a screenshot. It is not a defense against a compromised peer. State that in the threat model handoff to lane 3.

---

## 6. What zero trace honestly means, per OS

The page controls its own heap and nothing else. Every row below is a place where plaintext or key material can outlive the wipe, with the honest verdict and the only real mitigation. Do not put any of these in marketing copy as solved.

| Surface | Mechanism | Owner | Mitigation in V2 | Residual |
|---|---|---|---|---|
| Swap | Page memory can be written to the swap file | OS | Rely on full volume encryption. macOS FileVault encrypts the data volume and on Apple silicon the volume is created encrypted even with FileVault off, key protected by the hardware UID. Windows BitLocker secures the paging file by default on OS drives | Plaintext exists in swap while the tab is open. Encryption at rest only helps after power off |
| Hibernation | Memory image written to disk | OS | Same volume encryption. Windows: hiberfil.sys is secured on an encrypted volume by default | A live machine with the volume unlocked can still be resumed and inspected |
| Screenshots | OS compositor captures the window | OS, or the peer | Blank the chat on `visibilitychange` and `blur`, tight idle wipe | Cannot be prevented from a web page. Full stop |
| Clipboard | System clipboard is readable by every app | OS | Never auto-copy message text. Copy the invite code on explicit click, then overwrite the clipboard with an empty string after 30 s if the page still has focus | Clipboard managers and cross-device clipboard sync can retain the value |
| QuickLook thumbnails | Saved files get indexed and thumbnailed by the OS | OS | Default to in-memory preview only. Save is an explicit click. Warn on Save that the file leaves the app | A saved file is a file. Once it is in Downloads, the app has no say |
| Back and forward cache | The browser can freeze the page with its heap, blobs and keys intact | Browser | Wipe on `pagehide`. On `pageshow` with `persisted`, force a full re-pair rather than resuming | A frozen page can be restored before handlers run in some engines |
| HTTP cache, service worker | Stored response or offline copy | Browser | Single document, `Cache-Control: no-store`, no service worker, no fetch after load. V1 already has none | Browser disk cache is outside page control |
| Crash reports, telemetry | Browser vendors may capture memory | Browser, OS | Nothing in-page. Recommend a browser with crash upload disabled for high-risk users | Unverifiable from the page |
| Network metadata | STUN and DTLS reveal IPs, timing and volume | Network | Not a crypto fix. Lane 5 owns it | Out of scope here |

Sources for the table: FileVault volume encryption and the Apple silicon always-encrypted volume ([Apple Platform Security, "Volume encryption with FileVault in macOS"](https://support.apple.com/guide/security/volume-encryption-with-filevault-sec4c6dc1b6e/web), fetched, title "Volume encryption with FileVault in macOS"). BitLocker paging file, crash dump and hiberfil.sys on encrypted OS volumes ([Microsoft Learn, "BitLocker countermeasures"](https://learn.microsoft.com/en-us/windows/security/operating-system-security/data-protection/bitlocker/countermeasures), fetched, title "BitLocker countermeasures"). Clipboard system buffer and permission model ([MDN, "Clipboard API"](https://developer.mozilla.org/en-US/docs/Web/API/Clipboard_API), fetched, title "Clipboard API"). bfcache restore and the `persisted` flag ([MDN, "Window: pageshow event"](https://developer.mozilla.org/en-US/docs/Web/API/Window/pageshow_event), fetched, title "Window: pageshow event").

Claims marked as inference rather than source-backed:

- macOS swap files live on the data volume, so FileVault covers them. Apple documents the volume encryption, not swap specifically.
- Linux encrypted swap requires explicit dm-crypt configuration and depends on the distribution. UNVERIFIED for any specific distro. If Linux is a target, test it, do not assume.
- QuickLook and Spotlight index downloaded files. UNVERIFIED as a citable statement, but it is the observed default on macOS and the mitigation costs nothing.

Practical framing for the copy: "no trace on disk" is true only when the user does not click Save and the volume is encrypted. "No trace in memory" is never true while the tab is open. The honest phrase is "nothing is persisted by the app, and everything the app holds is destroyed when the session ends".

---

## 7. Key wipe semantics for the kill switch

### 7.1 What JavaScript can and cannot destroy

| Object | Can be zeroed | Note |
|---|---|---|
| `Uint8Array` we allocated | Yes, `.fill(0)` | The only reliable primitive. Use it for every raw key and every plaintext buffer |
| `CryptoKey` | No destroy API | Drop the reference; the key becomes unreachable. A non-extractable key was never readable by JS in the first place |
| String | No | Strings are immutable primitives. A key that ever becomes a string lives until GC and may be copied. Never do that |
| `Blob` and object URL | Revoke only | `URL.revokeObjectURL` drops the handle; the bytes live until the Blob is collected |
| `ArrayBuffer` | No direct API | Wrap it in a `Uint8Array` and fill that. The raw allocation is freed by GC, not by the page |

Design rule that follows: all key material lives in either a `Uint8Array` or a non-extractable `CryptoKey`. No hex, no base64, no `JSON.stringify` of a key, ever. The only strings in the app are user content and the public invite code.

Better still, avoid raw bytes for the symmetric keys entirely. `HKDF` can derive an AES-GCM `CryptoKey` with `extractable: false`, so the per-message key never exists as bytes the page can read. The ratchet chain keys still need to be raw for the HMAC step, and those are the ones that get `.fill(0)` on every advance.

### 7.2 Where the ratchet lives

Put the ratchet and all key material in a dedicated Worker, and keep only ciphertext and UI state on the main thread. `Worker.terminate()` "immediately terminates the Worker", with no opportunity to finish ([MDN, "Worker: terminate()"](https://developer.mozilla.org/en-US/docs/Web/API/Worker/terminate), fetched, title "Worker: terminate() method"). That is the closest thing a browser has to deterministic heap destruction: the whole isolate, its stack and its key material go away in one call. It is not a guarantee against a process dump or a compromised renderer, but it is strictly better than dropping references in a long-lived main thread that also holds the DOM, the message log, and every Blob.

### 7.3 Kill switch sequence

Two different actions, do not conflate them.

**Rotate (soft, keeps the session).** For the "keys rotate now" panic button.

1. Both sides generate a fresh X25519 key pair (and ML-KEM if enabled).
2. Send `{ k:"rekey", pk }` over the existing channel.
3. On receipt of the peer's `pk`, compute `RK' = HKDF(salt = old_RK, ikm = DH(my_new_sk, peer_new_pk), info="eph-v2-rekey", 32)`. If this side has not generated its pair yet, generate it now and send its `pk` before deriving.
4. Reset both chains, `Ns = Nr = 0`, clear the skipped cache, zero the old `RK, CKs, CKr` and both old static keys.
5. Ack with `{ k:"rekey-ok", mac }` where `mac = HMAC(RK', "rekey-ok")`, so both sides prove they derived the same key. If the MAC fails, hard kill.

Honest limit: a soft rekey over a channel the attacker already controls does not remove the attacker. It only limits how much future traffic one compromised key can read. That is still worth having.

**Kill (hard, ends the session).** For a suspected breach.

1. Stop timers, close the data channel and the peer connection (`:541-552` already does the transport half).
2. Zero every `Uint8Array`: root key, chain keys, skipped keys, file keys, partial plaintext.
3. Drop every `CryptoKey` reference and call `worker.terminate()`.
4. Revoke every object URL (`:559-561`), clear the log and the textareas (`:564-570`).
5. Display a fixed "session destroyed" state with no session identifier. Never show a session id, it is a correlation handle.
6. Re-pairing requires a brand new invite. Never reuse the old SDP, the old DTLS certificate, or the old ratchet state.

The owner's "migrate both peers to a fresh keyset" is the Rotate path, not the Kill path. Automatic migration after a breach is a contradiction: if the breach is real, the channel is suspect, so the only safe migration is out of band. Recommend Rotate for the UI button and Kill for the monitor's alert path.

### 7.4 What the monitor overlay can honestly claim

The overlay (lane 6 owns it) can report: session age, messages sent, bytes sent, last rekey, whether the SAS was confirmed, and whether any tag verification failed. It cannot report "memory wiped" or "no trace on disk" with any confidence. Give it a "destroyed" state that is a fact about the app's own state, not a claim about the OS.

---

## 8. Libraries that can inline into one file, with measured sizes

### 8.1 Measurement method

All numbers below are byte counts from real artifacts, not quoted from a README.

- Bundles were built with `esbuild --bundle --minify --format=iife --platform=browser` from the published npm packages (`@noble/curves@1.9.7`, `@noble/hashes@1.8.0`, `@noble/ciphers@1.3.0`, `@noble/post-quantum@0.4.1`), then compressed with `gzip -9`.
- TweetNaCl numbers are the published minified files `nacl-fast.min.js` and `nacl.min.js` fetched from unpkg, since those are the artifacts a single-file build would paste.
- libsodium numbers are the published `libsodium-wrappers` browser module. The package contains only that JS file, which is a wrapper, so a real build also needs the libsodium core payload loaded alongside. That payload is not included in the count. Inferred from the package contents, not measured.

Baseline for comparison: the whole V1 app is 35,598 bytes, and that is uncompressed source including HTML and CSS.

| Component | Minified bytes | gzip -9 | Fits no-build single file |
|---|---|---|---|
| WebCrypto (AES-GCM, HKDF, SHA-256, ECDH, X25519 where available) | 0 | 0 | Native, nothing to inline |
| `tweetnacl` `nacl.min.js` (box, secretbox, sign, hash) | 18,456 | 6,704 | Yes, UMD global, paste as is |
| `tweetnacl` `nacl-fast.min.js` | 32,110 | 10,570 | Yes, UMD global, paste as is |
| noble `x25519` | 32,503 | 13,720 | No, ESM imports. Needs one esbuild pass, then inline |
| noble `ed25519` | 30,670 | 12,934 | No, same |
| noble `x25519 + hkdf + sha256 + hmac` (core) | 36,426 | 15,216 | No, same. Costs more than the entire V1 file |
| noble `xchacha20poly1305` | 11,383 | 4,796 | No, same |
| noble `ml-kem` (ML-KEM-768) | 23,232 | 9,779 | No, same |
| `libsodium-wrappers` browser module | 101,748 | 13,477 | Not viable. Needs a wasm payload on top, and the JS alone is 2.9x the app |

Reading the table:

- **Nothing curve-based is free.** Adding X25519 or Ed25519 in JS costs roughly the entire current app, whichever library you pick. That is the single most important sizing fact in this file.
- **TweetNaCl is the only true paste-in dependency.** It is UMD, it has no imports, and it has a wide install base. `nacl.min.js` is 18,456 bytes minified and 6,704 compressed, and gives X25519 plus XSalsa20-Poly1305 plus Ed25519 in one go. The fast variant is 32,110 bytes minified and 10,570 compressed.
- **noble is smaller per primitive but needs a build step.** It ships ESM with relative imports only, so you cannot concatenate it by hand without breaking. One `esbuild` run produces a static IIFE that then behaves exactly like TweetNaCl. That is a build-time step, not a runtime dependency, so it satisfies "single file, no runtime dependencies" but not "no build step at all". Say which one the project means before choosing.
- **libsodium.js is out.** Even the non-sumo wrapper is 101,748 bytes and still needs the core payload. For a 36 KB app this is a 4x to 8x size increase for primitives we already have natively.

### 8.2 The native option is not a compromise

`SubtleCrypto.deriveBits` supports ECDH, HKDF, PBKDF2 and X25519, and is available in Workers ([MDN, "SubtleCrypto: deriveBits()"](https://developer.mozilla.org/en-US/docs/Web/API/SubtleCrypto/deriveBits), fetched, title "SubtleCrypto: deriveBits() method"). MDN's support note says some parts of this feature have varying levels of support, so treat X25519 as a negotiated capability, not an assumption.

Fallback plan, zero bytes either way:

- If `crypto.subtle.deriveBits` accepts `{name:"X25519"}`, use X25519 for the DH ratchet.
- Otherwise use ECDH P-256, which has been in every WebCrypto implementation for years.
- The suite identifier goes into the SAS input and is displayed next to the safety number, so a downgrade is visible to the user and changes the number.

The one primitive WebCrypto lacks is ML-KEM, which is why the PQ option costs 23 KB and the classical option costs nothing.

### 8.3 If a library is required anyway

Ranked within this section only: TweetNaCl first when a paste-in file is mandatory, because it needs no toolchain and its API is small. noble first when a build step is allowed, because per-primitive bundles are smaller, the code is audited, and tree shaking keeps only what is used. libsodium never, at this size.

---

## RECOMMENDED STACK

Ranked by adoption order. Every line is shippable on its own, and the first seven cost zero bytes.

1. **Security numbers over the complete public transcript, gated before content.** SHA-256 via WebCrypto, 60 digits, transcript hash hashed into the HKDF info field of the root key. This is the MITM fix and it costs about 25 lines. Source for the display convention: [signal.org/blog/safety-number-updates](https://signal.org/blog/safety-number-updates/).
2. **Three-DH X25519 initial agreement with a per-session static key, HKDF-SHA256 root.** Native, zero bytes. PQXDH-shaped but without the server: [PQXDH spec](https://signal.org/docs/specifications/pqxdh/).
3. **Double ratchet with a fresh message key per frame, 32-entry skipped cache, DH ratchet on turn change.** Hand-written, about 150 lines, zero bytes. This is the mechanism behind the "transformers" ask: [Double Ratchet spec, revision 4](https://signal.org/docs/specifications/doubleratchet/).
4. **AES-256-GCM for every message, with a constant 12-byte nonce under the per-message key.** Zero bytes, hardware speed. Nonce uniqueness rule per [libsodium's XChaCha documentation](https://libsodium.gitbook.io/doc/secret-key_cryptography/aead/chacha20-poly1305/xchacha20-poly1305_construction). Explicit assertion that `mk` is never reused.
5. **Per-file random key, 64 KiB chunks, counter nonce, AAD binding id, index, size and chunk count, streaming decrypt into `Uint8Array` parts, Blob only at the end, never disk.** Zero bytes.
6. **Ratchet and keys in a dedicated Worker, `terminate()` on wipe, `.fill(0)` on every raw buffer, non-extractable `CryptoKey` for symmetric keys.** Zero bytes. [Worker.terminate](https://developer.mozilla.org/en-US/docs/Web/API/Worker/terminate). This is what makes the kill switch mean something.
7. **Rotate and Kill as separate actions.** Rotate does an in-channel X25519 rekey with a MAC ack. Kill terminates the Worker and the peer and requires a fresh invite. No automatic migration after a real breach.
8. **noble-curves X25519, conditional.** Only if X25519 must be guaranteed on browsers without WebCrypto X25519, or if the test harness needs a reproducible all-JS suite. Cost: 32,503 bytes minified, 13,720 gzipped, plus a one-time esbuild step. That is a 91 percent increase over V1.
9. **noble-ciphers XChaCha20-Poly1305, conditional.** Only for a non-WebCrypto harness or if a non-AES AEAD is mandated. Cost: 11,383 bytes minified, 4,796 gzipped.
10. **TweetNaCl, fallback only.** If the team refuses a bundler and insists on one pasted file, `nacl.min.js` at 18,456 bytes minified is the smallest audited paste-in that covers X25519 and an AEAD.
11. **noble-post-quantum ML-KEM-768, V3 separate build.** 23,232 bytes minified, 9,779 gzipped, and the invite code grows by about 1.6 KB of base64. Construction per [RFC 10024](https://www.rfc-editor.org/rfc/rfc10024.html): concatenate the ML-KEM secret first with the X25519 secret and run one HKDF.
12. **SPAKE2+ or balanced SPAKE2, V2.2 opt-in only.** Balanced SPAKE2 is the correct shape for two peers with a shared password. RFC 9383 is written for the augmented variant with a verifier record, which does not fit a zero-persistence app: [RFC 9383](https://www.rfc-editor.org/rfc/rfc9383.html).
13. **OPAQUE, rejected.** Client-server only, needs a credential record and a server: [RFC 9807](https://www.rfc-editor.org/rfc/rfc9807.html). Document the rejection so it does not get reopened.
14. **libsodium.js, rejected on size.** 101,748 bytes of JS plus a wasm payload for primitives WebCrypto already provides.

Default build after this stack: V1's 35,598 bytes plus roughly 4 to 6 KB of new source and no new dependency bytes. That is the only variant that preserves the single-file, no-dependency property without a build step.

---

## SELF-CHECK

| Acceptance item | Result | Evidence |
|---|---|---|
| Output file exists at the required path | PASS | `/Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/01-research/output/04-crypto-design.md` |
| Pairing upgrade covered: SPAKE2+, OPAQUE, Signal safety numbers | PASS | Sections 1.2, 1.3, 1.4, with RFC 9383, RFC 9807 and the Signal safety number blog, each fetched and title-checked |
| Why PAKE kills the MITM and code-leak scenarios | PASS | Section 1.3, online-guessing bound argument, plus the balanced versus augmented distinction |
| Double ratchet as continuously rotating per-message keys, tied to the transformers ask | PASS | Section 2.2, KDF_CK and KDF_RK defined, ordered-SCTP simplification with its ceiling |
| Forward secrecy against a later DTLS or relay compromise | PASS | Section 2.4, four cases, each tied to a mechanism |
| Post-quantum hybrid ML-KEM with X25519 as in TLS 1.3 | PASS | Section 3, RFC 10024 sizes quoted exactly (1216, 1120, 64 bytes), cost in bytes and code |
| Per-message AEAD for files and images, XChaCha or AES-GCM, streaming decrypt to memory, never disk | PASS | Sections 4.2 and 4.3, with the nonce rationale and the 8 file rules |
| Deniability properties | PASS | Section 5, what holds, what breaks it, honest verdict |
| Zero trace per OS: swap, hibernation, screenshots, clipboard, QuickLook, mitigations | PASS | Section 6 table, every row has owner, mitigation and residual |
| Key wipe semantics for the kill switch | PASS | Section 7, object-by-object wipe table, Worker termination, Rotate versus Kill |
| Inlineable libraries with realistic bundle impact for a 36 KB app | PASS | Section 8 table. Sizes measured from published artifacts: esbuild bundles for noble, published minified dist files for TweetNaCl, published wrapper module for libsodium. Method stated in 8.1 |
| Every external claim in a recommendation carries a source URL verified by fetch | PASS | RFC 9383, RFC 9807, RFC 10024, Double Ratchet rev 4, PQXDH, Signal safety numbers, libsodium XChaCha, Apple FileVault, Microsoft BitLocker countermeasures, MDN Clipboard, MDN pageshow, MDN deriveBits, MDN Worker.terminate, all fetched with titles confirmed |
| Fit note for the single-file no-dependency form | PASS | Section 8 table column plus per-library notes in 8.1 and 8.3 |
| Bundle-size impact line where a library is involved | PASS | Section 8 table, plus each ranked item 8 through 11 carries its byte cost |
| File ends with a ranked RECOMMENDED STACK | PASS | RECOMMENDED STACK is the final design section, 14 ranked items, and the binding SELF-CHECK follows it because the brief requires the file to end with SELF-CHECK |
| No em dashes or en dashes | PASS | Checked by grep, see below |
| Every app claim carries a file:line reference | PASS | `:428`, `:442-445`, `:541-552`, `:554-605`, `:559-561`, `:564-570`, `:722-730`, `:755`, `:761`, `:792`, `:815`, `:849`, `:898-904`, `:906-923`, `:998-1016`, `:1038-1053`, `:1045`, `:1001` |
| Unverified items marked | PASS | Linux swap and QuickLook indexing marked UNVERIFIED in section 6 |

Unverified or inferred items, listed for the reviewer:

- macOS swap placement on the encrypted data volume is an inference from Apple's volume encryption statement, not a direct Apple statement about swap.
- The 100 to 150 MB peak memory estimate for a 50 MB file is an inference from blob and buffer behavior.
- Linux encrypted swap is UNVERIFIED for any specific distribution.
- QuickLook and Spotlight indexing of downloaded files is UNVERIFIED as a citable claim.

Known gap, out of scope for this lane: the SAS gate still depends on a human comparison, so it does not by itself satisfy the "unkeyed inbound traffic never gets an answer" goal. That requires the transport-level rule set in lane 5 plus the content gate in section 1.5.
