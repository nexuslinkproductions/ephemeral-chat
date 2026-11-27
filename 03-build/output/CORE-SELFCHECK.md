# CORE lane self-check, R2-02 to R2-12

ARTIFACT: 03-build/output/ephemeral-chat-v2.html
SHA-256: 998fedd53fab676f695032c73353407f7d7b18cb4b6f7b52e3710765a68ba191
BYTES: 87,484
STATUS: partial (R2-11 behavioral FAIL, four cards static-only, see rows)

## Static checks, all cards

Command:
```
python3 - <<'EOF'
b=open('03-build/output/ephemeral-chat-v2.html','rb').read()
print('nonascii', sum(1 for x in b if x>127))
t=b.decode()
print('emdash', t.count('\u2014'), 'endash', t.count('\u2013'))
for p in ['innerHTML','eval(','new Function','localStorage','document.cookie','serviceWorker']:
    print(p, t.count(p))
EOF
```
Output:
```
nonascii 0
emdash 0 endash 0
innerHTML 0
eval( 0
new Function 0
localStorage 0
document.cookie 0
serviceWorker 0
```
Also zero hits for outerHTML, insertAdjacentHTML, document.write, DOMParser, srcdoc, createContextualFragment, sessionStorage, indexedDB, caches, http://, https://, window.close.

Syntax:
```
node --check /tmp/v2block0.js && echo WORKER_SYNTAX_OK
node --check /tmp/v2block1.js && echo MAIN_SYNTAX_OK
```
Output: `WORKER_SYNTAX_OK`, `MAIN_SYNTAX_OK`. Blocks extracted from the two script tags.

Form factor: single file, no external asset, no build step, CSP adds `worker-src blob:` only.

## Behavioral smoke, Chromium channel chrome, two contexts, file://

Script /tmp/smoke.py drives the real UI: create invite, join, reply, connect, compare SAS, confirm both, send text, send a file, wipe.
```
invite_len 909 prefix E2.1.
sas_len 60 match True
composer_before True
composer_after False
text_ok True
file_save_anchor True state verified
```
Second run /tmp/smoke2.py adds rotate and wipe:
```
after_rotate_A_sys ['Safety number confirmed on both sides. Content is unlocked.', 'Rotating session keys under a fresh DH output.', 'Key rotation acknowledged and verified. Both chains were reset.']
after_rotate_B_sys ['Safety number confirmed on both sides. Content is unlocked.', 'Peer rotated the session keys.']
text_after_rotate True
ended_panel True Session wiped
```

## Per card

| Card | Status | Evidence and command |
|---|---|---|
| R2-02 Control envelope and router | PASS | Encrypted `{v,k,sid,seq}` frames only, no plaintext frame path, dispatch table with counted unknown `k`, version skew branch, seq resync once then kill, stale sid reject. Evidence: node --check plus smoke, all text and file frames traverse the router. |
| R2-03 Crypto core in the Worker | PASS | Inline Worker holds all key material; three-DH X25519 (P-256 fallback), HKDF root, per-message HMAC chain step with old chain key zeroed, AES-256-GCM, non-extractable message keys. Evidence: identical 60 digit SAS on both contexts and successful decrypt, smoke above. |
| R2-04 SAS gate | PASS | `composer_before True` then `composer_after False`; content frames dropped and counted before both confirms; SAS bound to fingerprints, app keys and suite. Both contexts printed the same 60 digits. |
| R2-05 File integrity | PASS (narrow) | `file_save_anchor True state verified`: Save anchor exists only after digest and completeness pass. Chunks are AES-GCM with AAD id/index/size/chunks, lazy parts array in the Worker, name hygiene, danger-type warning. Truncated and corrupted chunk cases were not exercised behaviorally. |
| R2-06 Inbound budgets | PARTIAL | Code present: 40 frames/5 s and 2 MB/s kill (A8), 2000 row cap, 4 files / 200 MiB session cap, 60 s transfer idle timeout, overlapping transfer rule. Not exercised behaviorally. |
| R2-07 Code envelope | PASS (narrow) | `E2.1.` envelope, 16 KB pre-decode cap, 64 KB streaming decompression cap, 32 KB SDP and 32 candidate caps, 120 s TTL, single use. Evidence: invite length 909 and full pair round trip. Expired and oversized pastes not exercised. |
| R2-08 Lifecycle and idle | PARTIAL | pagehide runs the full in-page wipe, `?idle=` removed, inbound frames bump activity, active transfer pauses idle, drop/dragover non-passive with preventDefault, 30 s code clear plus Show. Not exercised behaviorally. |
| R2-09 Kill switch | PASS | Wipe enabled at all stages, double Escape, panic best effort, DOM before URL revoke, Worker terminate, clipboard only if copied and focused, `location.replace('about:blank')` at 4 s (1.5 s anomaly). Evidence: `ended_panel True Session wiped`; navigation to about:blank observed in the migration failure run. |
| R2-10 Rotate | PASS | Fresh X25519 pair, RK' = HKDF(salt=old RK, ikm=DH, "eph-v2-rekey"), both chains reset, HMAC ack verified, failed MAC kills. Evidence: both system lines above and text flows after rotation. |
| R2-11 Migrate | FAIL | M1 to M5 state machine, pending object, adopt, fingerprint commitment, 15 s timeout and kill are implemented, but the behavioral run never reaches the new SAS: both contexts end with migration-failed. Command /tmp/smoke3.py, output `mig_new_sas_A False B False` then the page is gone. Code is not accepted as working. |
| R2-12 Transport default | PASS (static) | Three STUN providers, no relay configuration, disclosure copy (IP in code, detectability, extensions), gathering failure reported as network blocked distinct from peer loss, selected candidate pair readout via getStats. Not exercised behaviorally beyond the default direct connection working. |

## Bugs found and fixed during the lane

1. Missing frame type byte on control and chunk frames, so the router saw ciphertext as an unknown type or a chunk.
2. AAD buffer was 17 bytes with a uint32 write ending at 18, which rejected every frame with "Offset is outside the bounds of the DataView".
3. Chain derivation used role labels on both sides, so the sender chain never matched the receiver chain. Direction labels o2j/j2o fixed it.

## Deliberate deferrals, recorded

- Header encryption is V2.1 per blueprint 2.2, not this card.
- The DH ratchet on turn change is not implemented; the symmetric HMAC chain gives a fresh key per message and Rotate supplies the DH rekey. Marked in code as a ceiling.
- Migration is code complete but behaviorally failing, so the R2-11 gate is red.

## Known limits

- The full pairing smoke needs a dialog handler for the Wipe confirm; without one Playwright dismisses it and the panel does not show. Smoke2 accepts dialogs and passes.
- Migration failure currently ends the session with the migration-failed panel rather than leaving the old channel live.
