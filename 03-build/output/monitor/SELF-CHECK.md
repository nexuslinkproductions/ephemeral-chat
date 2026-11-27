# SELF-CHECK, R2-14 monitor lane

Run: w11-ephemeral-build-r2a-20261127, MONITOR lane.
Scope written: `03-build/output/monitor/` only. No app file touched, no git run.
Host: macOS 26.4.1, Swift 6.3.3 (swiftlang-6.3.3.1.3), arm64.

## Card R2-14: PASS

Gate command, run from the project root `/Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL`:

```
$ swift test --package-path 03-build/output/monitor
Test Suite 'MonitorTests' passed at 2026-11-27 00:52:46.687.
	 Executed 21 tests, with 0 failures (0 unexpected) in 0.012 (0.015) seconds
Test Suite 'All tests' passed at 2026-11-27 00:52:46.687.
	 Executed 21 tests, with 0 failures (0 unexpected) in 0.012 (0.017) seconds
EXIT 0
```

Re-run after the last source edit, same command:

```
$ swift test --package-path 03-build/output/monitor
	 Executed 21 tests, with 0 failures (0 unexpected) in 0.028 (0.030) seconds
TEST EXIT 0
```

`swift build --package-path 03-build/output/monitor` exits 0, no warnings.

### Failure mode 1: a rule that cannot fire

`testEveryRuleCanFire` builds a firing scenario per rule in its own engine and
asserts both the rule id and the blueprint severity:

| Rule | Scenario | Severity | Result |
|---|---|---|---|
| M1 | 120 s at 10 KB per s, then 30 s at 100 KB per s | amber | PASS |
| M2 | device active while frontmost | red | PASS |
| M3 | 4 clipboard changes in 60 s while frontmost | amber | PASS |
| M4 | CPU 90 percent for 60 s, and RSS 3000 MB | amber | PASS |
| M5 | heartbeat age 12.5 s | red | PASS |

Negative controls also pass: M1 stays quiet on steady traffic and during the
baseline, M3 is quiet when not frontmost, M4 does not fire on a CPU spike that
does not sustain 60 s, M2 does not repeat while the condition holds. Test
cases: testM1FiresOnBurstAboveFiveTimesMedian, testM1StaysQuietOnSteadyTraffic,
testM2FiresOnDeviceWhileFrontmost, testM3FiresOnClipboardChurn,
testM3QuietWhenNotFrontmost, testM4FiresOnSustainedCpuAndOnMemory,
testM4CpuSpikeDoesNotSustain, testM5FiresOnHeartbeatGap, testEveryRuleCanFire,
testSilenceMutesButKeepsState.

### Failure mode 2: a command channel to the browser

Static scan of Sources, Tests, launchd and Package.swift:

```
$ grep -rnE "NWListener|NWConnection|URLSession|NSXPC|NSAppleScript|osascript|listen\(|bind\(|socket\(|accept\(" Sources/ Tests/ launchd/ Package.swift
no hits
```

Imports are Apple system frameworks only: Foundation, CryptoKit, AppKit,
CoreMediaIO, XCTest. Package.swift declares no dependencies. The only inputs
are ps, lsof, nettop, NSWorkspace, NSPasteboard and CoreMediaIO device
properties. The only output is the log file and stdout.

### Hash-chained log

Tests PASS: append and verify (3 records, 7 fields per line, healthy), reopen
continues the chain at seq 3, edited detail is caught as
`hash mismatch at seq 2` and reopening throws, a deleted middle record is
caught as `seq 3 at line 2, expected 2`, heartbeat gaps are reported as
`gap 28.0 s before seq 3`, detail with a tab, a newline and a non ASCII byte
is sanitized to one ASCII line.

### Behavioral run on the real binary

```
$ .build/debug/ephemeral-monitor --once --log scratch/monitor.log
event ports *:17500 (LISTEN) *:18480 (LISTEN) *:3283 (LISTEN) *:4564 (LISTEN) *:4592 (LISTEN)
ONCE EXIT 0

$ cat scratch/monitor.log
1	1795737219396	event	ports	*:17500 (LISTEN) ...	0000...0000	304373db...
2	1795737219396	heartbeat	none	none	304373db...	097acaf7...

$ .build/debug/ephemeral-monitor --verify --log scratch/monitor.log
records 2
OK
VERIFY EXIT 0
```

Sequence and timestamps monotonic: `monotonic ts: True | seq: [1, 2]`.
This exercised the real ps, lsof, nettop, NSPasteboard and CoreMediaIO calls,
not only the rule engine.

### launchd plist

`launchd/com.nexus.ephemeral-monitor.plist` parses with
PropertyListSerialization. `testLaunchdPlist` PASS asserts Label
com.nexus.ephemeral-monitor, RunAtLoad true, KeepAlive true,
LimitLoadToSessionType Aqua, and one absolute ProgramArguments path.
`plutil -lint` is not needed because the test parses it, but the file follows
the Apple DTD.

## ASCII and dash byte scan of this lane's files

```
$ python3 scan (walk ., skip .build, read bytes)
files scanned: 10
non-ascii: none
em/en dashes: none
SCAN EXIT 0
```

Every written file is ASCII. The only non ASCII byte test uses the escape
`\u{00e9}` inside a Swift string literal, which is ASCII source and the
sanitizer test proves it becomes `?` in the log.

## Deliberate ceilings, named

- Frontmost is the application, not the tab. M2 and M3 therefore fire on any
  frontmost browser window. The OS does not expose the tab, per 06 section 4.3.
- M1 is blind to bursts shorter than one 2 s tick and stays quiet until it has
  30 s of baseline.
- The lsof listener scan runs every 30 s and can take seconds; all records in
  a tick share the tick timestamp so the chain stays ordered.
- No log rotation, about 2.4 MB per day at a 2 s heartbeat.
- The menu bar item, notifications, HUD and the signed app bundle are not in
  this card. This card is the package, the rules, the log and the plist.

## Not done, out of scope

No app file edit, no probe file, no wrapper file, no install into
~/Library/LaunchAgents on this host. Nothing outside `monitor/` was written.
