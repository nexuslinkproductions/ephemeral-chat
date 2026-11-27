# Ephemeral monitor, R2-14

A separate process macOS monitor. It is a witness, not a guard: it cannot
block the chat, cannot inspect DTLS, and cannot prove the absence of an
attack. The architecture is blueprint section 2.7 and the rules are
`06-ops-defense.md` sections 4.1 to 4.4.

No listener, no socket, no AppleScript, no command channel. The process reads
public system counters and appends to its own hash-chained log. That is the
whole input and output path.

## Layout

```
Package.swift                              SwiftPM manifest, no package dependencies
Sources/EphemeralMonitor/HashChainLog.swift   append-only SHA-256 chained log
Sources/EphemeralMonitor/Rules.swift          M1 to M5 rule engine
Sources/EphemeralMonitor/ProcessSampler.swift ps, lsof, nettop parsers
Sources/EphemeralMonitor/DeviceWatch.swift    camera and mic via CoreMediaIO
Sources/ephemeral-monitor/main.swift          launchd daemon, 2 s tick
launchd/com.nexus.ephemeral-monitor.plist     LaunchAgent with KeepAlive
Tests/EphemeralMonitorTests/MonitorTests.swift 21 tests
```

## Rules

| Rule | Condition | Action |
|---|---|---|
| M1 | browser outbound above 5x its 10 minute median for 30 s | amber, log |
| M2 | camera or mic active while the browser is frontmost | red, sound, HUD, log |
| M3 | more than 3 clipboard changes in 60 s while frontmost | amber, counts only |
| M4 | browser CPU above 80 percent for 60 s, or RSS above 2 GB | amber, log |
| M5 | heartbeat missing more than 10 s, seen on restart | red with gap duration |

One alert per transition. `RuleEngine.silence` mutes a rule for 15 minutes
without hiding it from the menu bar state.

## Log

`~/Library/Application Support/EphemeralMonitor/monitor.log`, one ASCII record
per line, tab separated:

```
seq  tsMillis  kind  rule  detail  prevHash  hash
```

`hash` is SHA-256 over the first six fields. `prevHash` is the previous
record's hash, so editing, deleting, reordering or inserting a record breaks
the chain at that point. Each append is fsync'd. Reopening a broken file
throws instead of appending to it.

```
swift build --package-path 03-build/output/monitor
./03-build/output/monitor/.build/debug/ephemeral-monitor --verify --log <path>
```

## Install

```
swift build --package-path 03-build/output/monitor -c release
cp launchd/com.nexus.ephemeral-monitor.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.nexus.ephemeral-monitor.plist
```

The plist points at `/Applications/EphemeralMonitor.app/Contents/MacOS/ephemeral-monitor`.
The signed app bundle and the menu bar item are not in this card.

## What it cannot do, stated in the About window

- It cannot see inside DTLS.
- It cannot attribute traffic per tab, only per process.
- It cannot prove the absence of an attack.
- It cannot block the chat.
- It loses to root, and to the same user killing it. The gap in the log is
  the evidence, not a prevention.

## Deliberate ceilings

- Frontmost is the frontmost application, not the frontmost tab. The OS does
  not expose the tab, so M2 and M3 fire on any browser window being frontmost.
- M1 samples every 2 s and cannot see bursts shorter than one tick. The
  10 minute median starts empty, so the rule is quiet for its first 30 s.
  That is intended: no baseline, no alarm.
- The listening port scan runs `lsof` every 30 s and `lsof` can take seconds
  on a busy host. The chain stays ordered because every record in a tick
  shares the tick timestamp.
- No log rotation. At a 2 s heartbeat the file grows by roughly 2.4 MB per
  day. Rotate externally if that matters.
- Clipboard is an event count only, never content (`NSPasteboard.changeCount`).
- CryptoKit is an Apple system framework, not a package dependency. The only
  imports are Foundation, CryptoKit, AppKit, CoreMediaIO.
