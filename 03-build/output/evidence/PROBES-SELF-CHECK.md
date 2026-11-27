# PROBES lane self-check, R2-01 harness and spine cases

RUN: w11-ephemeral-build-r2a-20261127
LANE: PROBES. Scope: `03-build/output/probes/`, `03-build/output/evidence/`.
STATUS: partial. The harness and all 14 case names are in place. `selftest` exits 0.
Behavioral cases are red or blocked on the landed artifact for reasons listed below.

## Files

| File | Bytes | Purpose |
|---|---|---|
| `probes/gate.py` | 54400 class | CDP harness, shim, 14 cases, evidence writer |
| `probes/fixtures/pair.html` | 2090 | two page WebRTC fixture used by selftest only |
| `evidence/*.json` | one per run | case, exit code, app SHA-256, duration, reason |

## Harness design, as built

- Python 3.9 stdlib only: `socket` and a hand rolled RFC 6455 client for CDP,
  `subprocess` for Chrome, `gzip`/`base64`/`hashlib` for code and digest work.
- Chrome launched with `--headless=new --remote-debugging-port=0`, one browser
  process, two `Target.createBrowserContext` contexts per case, so the two peers
  never share storage.
- Test side shim installed with `Page.addScriptToEvaluateOnNewDocument`: records
  every `RTCPeerConnection`, every `RTCDataChannel`, every `dc.send` payload
  (strings and base64 binary), every frame received, every
  `URL.createObjectURL`/`revokeObjectURL` with the live blob node count at revoke
  time. No test hook exists in the artifact.
- Exit contract: 0 PASS, 1 FAIL, 2 could not run (blocks the card, never passes).

## Card results

Command form: `python3 03-build/output/probes/gate.py <case> [--app PATH]`.
Run from `04_PROJECTS/EPHEMERAL`.

| Card | Case | Command | Result | Raw output |
|---|---|---|---|---|
| R2-01 | selftest | `gate.py selftest` | PASS exit 0 | `PASS selftest 2 peers, 1 channel, round trip, negative control fired` |
| R2-02 | envelope | `gate.py envelope` | exit 2 | `SKIP envelope could not run: wait timed out: reply code` |
| R2-03 | ratchet | `gate.py ratchet` | not run on v2 | baseline on v1 copy: `FAIL ratchet no Worker holds the ratchet state` |
| R2-04 | sas | `gate.py sas` | exit 1 | `FAIL sas input not found: #input` |
| R2-05 | file | `gate.py file` | exit 2 | `SKIP file could not run: wait timed out: reply code` |
| R2-06 | budget | `gate.py budget` | not run on v2 | baseline on v1 copy: `FAIL budget no 2000 row transcript cap` |
| R2-07 | code | `gate.py code` | PASS exit 0 | `PASS code` |
| R2-08 | lifecycle | `gate.py lifecycle` | exit 2 | `SKIP lifecycle content still locked after a confirm attempt` |
| R2-09 | kill | `gate.py kill` | exit 2 | `SKIP kill content still locked after a confirm attempt` |
| R2-10 | rotate | `gate.py rotate` | not run on v2 | baseline on v1 copy: `FAIL rotate no rekey frame` |
| R2-11 | migrate | `gate.py migrate` | not run on v2 | baseline on v1 copy: `FAIL migrate no migration frame` |
| R2-12 | stun | `gate.py stun` | PASS exit 0 | `PASS stun` |
| R2-13 | cover | `gate.py cover --relay-host turn:127.0.0.1:5349` | PASS exit 0 on v1 baseline, exit 2 without the flag | `SKIP cover could not run: --relay-host is required` |
| R2-15 | mutation-all | `gate.py mutation-all` | exit 1 | `FAIL mutation-all guard preparse-cap not found` |

`gate.py list` prints the 14 names in card order:
`selftest envelope ratchet sas file budget code lifecycle kill rotate migrate stun cover mutation-all`

## Byte scan of lane files

```
probes/gate.py                   bytes=54391 non_ascii=0 en=0 em=0
probes/fixtures/pair.html        bytes=2090  non_ascii=0 en=0 em=0
evidence/*.json                  non_ascii=0 en=0 em=0
```

Command: a Python scan counting bytes above 127 and the UTF-8 sequences
`e2 80 93` and `e2 80 94` in every file this lane wrote.

## Why the behavioral cases are red, measured

Two findings against the landed `ephemeral-chat-v2.html` block the shared
pairing path. Both are CORE lane scope, recorded here with the observation:

1. The invite code is base64url and the unpack path calls `atob` on it. Measured
   on a fresh invite: body contains `-` and `_`, length mod 4 is 3, and
   `atob(body)` throws `The string to be decoded is not correctly encoded`.
   The in page toast reads `Failed to execute 'atob' on 'WorkerGlobalScope'`.
   Result: the reply code never appears, so every case that needs a paired
   session exits 2.
2. The SAS panel renders correctly (`#digits` holds 12 groups of 5 digits, both
   peers equal), but after both sides click `#confirmSas` the page has
   navigated to `about:blank`, so `#input` no longer exists. Either confirm
   runs the kill path or a later step does.

Fix those two and the same cases run without a harness change.

## Verified against a v1 baseline copy

To prove each case fires rather than crashing, every behavioral case was run
against an ASCII copy of `input/ephemeral-chat-v1.html`:

```
kill       FAIL wipe is disabled before connect
file       FAIL a truncated replay produced a Save anchor   (F-02 reproduced: 3 anchors, 2 expected)
envelope   FAIL unknown k left no visible system line
ratchet    FAIL no Worker holds the ratchet state
sas        FAIL composer is not locked before SAS confirmation
budget     FAIL no 2000 row transcript cap
code       FAIL no 64 KB decompressed cap
lifecycle  FAIL pagehide left #offer filled                (F-08 reproduced)
stun       FAIL fewer than three STUN providers
rotate     FAIL no rekey frame
migrate    FAIL no migration frame
mutation   FAIL guard preparse-cap not found
cover      PASS
```

Every one fails for the card's own named failure mode, not a harness error.

## Known gaps, next wave

- `code` and `stun` are static heavy. Their behavioral halves are real but the
  candidate cap probe depends on a successful unpair, blocked by finding 1.
- `mutation-all` needs its guard patterns tuned to the landed artifact. The
  current table looks for the blueprint constants. `preparse-cap` is not present
  as 65536 or 64 * 1024. The case compares against a baseline run and rejects a
  mutated run that fails with the same reason, so a mutation that changes
  nothing cannot pass.
- `rotate` and `migrate` control discovery is text based (`rotate`, `new session`).
  The artifact has `#rotate` and `#migrate`, so selectors should be pinned next.
- Evidence JSON files from the v1 baseline runs carry that copy's hash; the v2
  runs carry the v2 hash. Filter by `app` when reading the folder.
