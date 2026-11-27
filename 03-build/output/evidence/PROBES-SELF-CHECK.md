# PROBES lane self-check, R2a wave 2, tuning and snapshot run

RUN: w12-ephemeral-fix-r2a-20261127, PROBES2 lane
SCOPE: `03-build/output/probes/`, `03-build/output/evidence/`.
STATUS: partial. Control pins and mutation guard tuning landed. All 14 cases
were run against one frozen snapshot. Five cards pass on that snapshot,
eight expose artifact defects, one is blocked by a harness timeout. The
COREFIX lane edits the live artifact in parallel, so these verdicts describe
the snapshot only. The lead's post-landing re-run is the authority.

## Snapshot

Taken once at lane start, before any other lane could change the file:

```
path   03-build/output/probes/snapshots/ephemeral-chat-v2.R2A-PROBES2.html
sha256 998fedd53fab676f695032c73353407f7d7b18cb4b6f7b52e3710765a68ba191
bytes  87484
mtime  2026-11-27T01:05:26
```

The live `output/ephemeral-chat-v2.html` had the same hash and byte count at
snapshot time. Every run below passes `--app` pointing at the snapshot.

## Tuning rows

| Item | Before | After | Proof |
|---|---|---|---|
| rotate control | `click_text(a, r'rotate')` | asserts enabled `#rotate`, then `click(a, '#rotate')` | `rotate` PASS on snapshot, raw log line `rotate rc=0` |
| migrate control | `click_text(a, r'new session|migrate|new keys')` | asserts enabled `#migrate`, then `click(a, '#migrate')` | reaches migration state poll, raw log line `migrate rc=1 ... last=(0, 0, 0, 0)` |
| migrate timeout assert | `\b15000\b`, matched `IDLE_CHECK_MS` at line 921 | `migFail\('timeout'\),\s*15000` | first match line 2292, the real migration timer |
| rotate replay | replayed a string frame; V2 sends binary only, so `no wire frame captured` | shim records `lastRaw` (last binary frame, base64, 128 KiB cap), case replays with `__probe.sendB64` | `rotate rc=0` after the pin, `PASS rotate` |
| rotate verdict | required the marker count to stay exactly 1; a replayed frame trips integrity wipe and clears the log | accepts 0 or 1, fails only on a second render | `rotate rc=0` with the wipe path |
| preparse-cap guard | `65536`, `64 * 1024`, `65_536` | unchanged, now verified against V2: first match line 696 `if (text.length > 65536)`, other matches CHUNK and PAYLOAD_MAX | preflight output below |
| sas-gate guard | `!\s*(?:sasOk|sasConfirmed|sasVerified|verified)\b`, no match in V2 | renamed `sas-lock`, pattern pins the three disabled flags before `showSas()` at line 1479 | preflight `sas-lock matches=1 first_line=1479` |
| completeness guard | `\breceived\s*===\s*size\b`, no match in V2 | `f\.received\s*!==\s*f\.size`, line 760 | preflight `completeness matches=1 first_line=760` |
| mutation preflight | baseline cases ran before any pattern was checked | every guard pattern is checked first and all misses are named in one failure | code path in `case_mutation` |

Guard preflight against the snapshot:

```
code-cap      matches=1 first_line=915 case=code
preparse-cap  matches=3 first_line=696 case=code
ttl           matches=1 first_line=919 case=code
row-cap       matches=1 first_line=912 case=budget
kill-nav      matches=1 first_line=1353 case=kill
sas-lock      matches=1 first_line=1479 case=sas
completeness  matches=1 first_line=760 case=file
```

`preparse-cap` matches three sites by design (the `64 * 1024` forms are
`CHUNK` and `PAYLOAD_MAX`); mutation replaces the first match, which is the
`65536` pre-parse gate on the decrypted text.

## Case results on the snapshot

Command form, run from `04_PROJECTS/EPHEMERAL`:

```
python3 03-build/output/probes/gate.py <case> --app 03-build/output/probes/snapshots/ephemeral-chat-v2.R2A-PROBES2.html
```

| Card | Case | Exit | Raw last line | Evidence JSON |
|---|---|---|---|---|
| R2-01 | selftest | 0 | `PASS selftest 2 peers, 1 channel, round trip, negative control fired` | `selftest-20261127-011715.json` |
| R2-02 | envelope | 1 | `FAIL envelope unknown k left no visible system line` | `envelope-20261127-011254.json` |
| R2-03 | ratchet | 1 | `FAIL ratchet artifact calls exportKey, key bytes are readable from the main thread` | `ratchet-20261127-011308.json` |
| R2-04 | sas | 0 | `PASS sas` | `sas-20261127-011338.json` |
| R2-05 | file | 1 | `FAIL file file-start and file-end were not captured` | `file-20261127-011308.json` |
| R2-06 | budget | 1 | `FAIL budget a 200 frame burst did not trip the A8 rate rule` | `budget-20261127-011316.json` |
| R2-07 | code | 0 | `PASS code` | `code-20261127-011120.json` |
| R2-08 | lifecycle | 1 | `FAIL lifecycle pagehide left #input filled: got 'PROBE-DRAFT', want ''` | `lifecycle-20261127-011347.json` |
| R2-09 | kill | 2 | `SKIP kill harness error: timeout: timed out` | `kill-20261127-011355.json` |
| R2-10 | rotate | 0 | `PASS rotate` | `rotate-20261127-011739.json` |
| R2-11 | migrate | 1 | `FAIL migrate migration did not open a new channel on both peers, last=(0, 0, 0, 0)` | `migrate-20261127-011750.json` |
| R2-12 | stun | 0 | `PASS stun` | `stun-20261127-011134.json` |
| R2-13 | cover | 0 | `PASS cover` with `--relay-host turn:127.0.0.1:5349` | `cover-20261127-011144.json` |
| R2-15 | mutation-all | 2 | `SKIP mutation-all could not run: case kill cannot run on the artifact, mutation has no baseline: SKIP kill harness error: timeout: timed out` | `mutation-all-20261127-011505.json` |

Raw transcript of the whole run: `evidence/probes2-raw-snapshot.log`.

## What the red cases mean

- `envelope`: an unknown `k` frame leaves no visible system line on the peer.
  The card requires a visible rejection.
- `ratchet`: the artifact calls `exportKey`, so key material is readable from
  the main thread. Static failure, no browser needed.
- `file`: the harness cannot slice per-transfer frames because V2 sends binary
  only and the shim keeps string frames separately. This is a probe defect, not
  an artifact verdict; see gaps.
- `budget`: 200 noise frames in a burst do not end the session, so the A8 rate
  rule is not landing.
- `lifecycle`: `pagehide` leaves the draft in `#input`; the card requires the
  field cleared.
- `kill`: CDP wait timed out inside the case (70 s). The first half (double
  Escape) may pass; the second half times out around the wipe and blob revoke
  check. Needs a harness look next wave.
- `migrate`: both pages end with zero channels and the shim reset, consistent
  with `migration-failed` wiping to `about:blank`. The pinned `#migrate` control
  is found and clicked; the artifact does not reach a new channel.
- `mutation-all`: the guard table is complete and its preflight passes, but the
  case needs a baseline from every guarded case first. `kill` exits 2, so the
  run stops by design rather than reporting a false pass.

## Known gaps for the next wave

- `case_file` and `case_ratchet` still slice `sentFrames` by string type. V2
  sends binary frames only, so both need the same `raw` boundary treatment
  `rotate` now uses. `file` fails before its real assertions because of this.
- `kill` timeout at 70 s needs isolation: run the first half and the blob
  revoke half separately to find the wait that never settles.
- `mutation-all` cannot be judged until `kill` runs and the artifact stops
  wiping on migration; both are artifact side for now.
- `code` passes on the snapshot, so the 16 KB paste cap, 64 KB pre-parse cap,
  120 s TTL and 32 candidate cap are all present and behave.

## Byte scan

```
probes/gate.py                   bytes=56300 non_ascii=0 en=0 em=0
evidence/probes2-raw-snapshot.log bytes=1249 non_ascii=0 en=0 em=0
```

Command: a Python scan counting bytes above 127 and the UTF-8 sequences
`e2 80 93` and `e2 80 94` in every file this lane wrote.
