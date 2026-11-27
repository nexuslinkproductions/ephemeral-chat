import Foundation
import AppKit
import EphemeralMonitor

// rst2-14 monitor daemon. Separate process, launchd started, no listener,
// no socket, no AppleScript, no inbound command path. It only reads public
// system counters and appends to its own hash-chained log.

func stderrLine(_ s: String) {
    FileHandle.standardError.write(Data((s + "\n").utf8))
}

func run(_ path: String, _ arguments: [String]) -> String {
    let process = Process()
    process.executableURL = URL(fileURLWithPath: path)
    process.arguments = arguments
    let pipe = Pipe()
    process.standardOutput = pipe
    process.standardError = FileHandle.nullDevice
    do {
        try process.run()
    } catch {
        return ""
    }
    let data = pipe.fileHandleForReading.readDataToEndOfFile()
    process.waitUntilExit()
    return String(decoding: data, as: UTF8.self)
}

var logURL = FileManager.default.homeDirectoryForCurrentUser
    .appendingPathComponent("Library/Application Support/EphemeralMonitor/monitor.log")
var once = false
var verifyOnly = false
var args = Array(CommandLine.arguments.dropFirst())
while !args.isEmpty {
    let a = args.removeFirst()
    if a == "--log", !args.isEmpty {
        logURL = URL(fileURLWithPath: args.removeFirst())
    } else if a == "--once" {
        once = true
    } else if a == "--verify" {
        verifyOnly = true
    }
}

if verifyOnly {
    let data = (try? Data(contentsOf: logURL)) ?? Data()
    let report = HashChainLog.verify(contents: String(decoding: data, as: UTF8.self))
    print("records " + String(report.records))
    if let brk = report.firstBreak {
        print("BROKEN " + brk)
        exit(1)
    }
    for gap in report.heartbeatGaps {
        print("M5 " + gap)
    }
    print("OK")
    exit(0)
}

let log: HashChainLog
do {
    log = try HashChainLog(path: logURL)
} catch {
    stderrLine("monitor cannot open log: " + String(describing: error))
    exit(3)
}

// A restart after a kill leaves a heartbeat gap in the chain. Report it.
let before = (try? String(decoding: Data(contentsOf: logURL), as: UTF8.self)) ?? ""
if let lastGap = HashChainLog.verify(contents: before).heartbeatGaps.last {
    try? log.alert(rule: "M5", detail: "restart saw " + lastGap)
    print("alert M5 red restart saw " + lastGap)
}

let engine = RuleEngine()
let browserIDs: Set<String> = [
    "com.google.Chrome", "com.google.Chrome.canary", "org.chromium.Chromium",
    "com.apple.Safari", "com.apple.SafariTechnologyPreview", "org.mozilla.firefox",
    "com.brave.Browser", "com.microsoft.edgemac", "com.vivaldi.Vivaldi",
    "com.operasoftware.Opera", "company.thebrowser.Browser"
]
let browserNames = [
    "Google Chrome", "Chromium", "Safari", "firefox", "Firefox",
    "Brave Browser", "Microsoft Edge", "Vivaldi", "Opera", "Arc"
]

func browserRows(_ rows: [ProcessStat]) -> [ProcessStat] {
    return rows.filter { row in
        return browserNames.contains { row.command.contains($0) }
    }
}

var lastBytesOut: UInt64?
var lastBytesAt: Double?
var previousListeners: Set<String> = []
var lastListenerScan = 0.0

func tick() {
    let now = Date().timeIntervalSince1970
    let rows = ProcessSampler.parsePS(run("/bin/ps", ["-Ao", "pid=,pcpu=,rss=,comm="]))
    let mine = browserRows(rows)
    let totals = ProcessSampler.browserTotals(mine, match: "")

    var sample = Sample(ts: now)
    sample.browserRunning = !mine.isEmpty
    let frontID = NSWorkspace.shared.frontmostApplication?.bundleIdentifier ?? ""
    // Blind spot, stated in the About window: the OS exposes the frontmost
    // application, not the frontmost tab.
    sample.chatFrontmost = browserIDs.contains(frontID)
    sample.cpuPercent = mine.isEmpty ? nil : totals.cpuPercent
    sample.memoryMB = mine.isEmpty ? nil : totals.rssMB
    sample.clipboardChangeCount = Int(NSPasteboard.general.changeCount)
    sample.deviceActive = DeviceWatch.cameraOrMicActive()

    // M1 input: summed outbound bytes for the browser process tree.
    let nettop = ProcessSampler.parseNettop(run("/usr/bin/nettop", ["-P", "-x", "-l", "1", "-J", "bytes_in,bytes_out"]))
    var totalOut: UInt64 = 0
    for pid in totals.pids {
        totalOut += nettop[pid]?.bytesOut ?? 0
    }
    if let last = lastBytesOut, let lastAt = lastBytesAt, now > lastAt {
        sample.outboundBytesPerSec = Double(totalOut >= last ? totalOut - last : 0) / (now - lastAt)
    }
    lastBytesOut = totalOut
    lastBytesAt = now

    // New listening ports, a watched event, not one of the five rules.
    if now - lastListenerScan > 30 {
        lastListenerScan = now
        let listening = ProcessSampler.parseLsof(run("/usr/sbin/lsof", ["-nP", "-iTCP", "-sTCP:LISTEN"]))
        let current = Set(listening.map { $0.endpoint })
        let added = ProcessSampler.newListeningEndpoints(previous: previousListeners, current: current)
        previousListeners = current
        if !added.isEmpty {
            _ = try? log.append(kind: "event", rule: "ports", detail: added.prefix(5).joined(separator: " "), atMillis: Int64(now * 1000))
            print("event ports " + added.prefix(5).joined(separator: " "))
        }
    }

    for alert in engine.evaluate(sample) {
        try? log.alert(rule: alert.rule, detail: alert.detail, atMillis: Int64(now * 1000))
        print("alert " + alert.rule + " " + alert.severity.rawValue + " " + alert.detail)
    }
    try? log.heartbeat(atMillis: Int64(now * 1000))
}

tick()
if once {
    exit(0)
}
while true {
    Thread.sleep(forTimeInterval: 2.0)
    tick()
}
