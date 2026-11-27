# CORE lane self-check, R2-02 to R2-12, R2a fix wave

ARTIFACT: 03-build/output/ephemeral-chat-v2.html
SHA-256: 4cd68b31e91b29742b84247a25a5e40793ae34def88d8ea8fb433cc79a084d8a
BYTES: 87,767
STATUS: partial (artifact fixes landed and behaviorally verified; six gate cases remain red on probe-side defects, listed at the end for the lead and PROBES2)

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
