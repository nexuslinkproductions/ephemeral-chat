import Foundation

public enum Severity: String, Comparable, Equatable {
    case green
    case amber
    case red

    public static func < (a: Severity, b: Severity) -> Bool {
        return rank(a) < rank(b)
    }

    private static func rank(_ s: Severity) -> Int {
        switch s {
        case .green: return 0
        case .amber: return 1
        case .red: return 2
        }
    }
}

public struct Alert: Equatable {
    public let rule: String
    public let severity: Severity
    public let detail: String

    public init(rule: String, severity: Severity, detail: String) {
        self.rule = rule
        self.severity = severity
        self.detail = detail
    }

    /// Red alerts sound, amber ones do not (`06-ops-defense.md` 4.4).
    public var needsSound: Bool { severity == .red }
}

/// One poll of public system counters. Every field is optional except the
/// timestamp, because a missing counter must not look like a zero.
public struct Sample {
    public var ts: Double
    public var browserRunning: Bool = false
    public var chatFrontmost: Bool = false
    public var outboundBytesPerSec: Double? = nil
    public var cpuPercent: Double? = nil
    public var memoryMB: Double? = nil
    public var clipboardChangeCount: Int? = nil
    public var deviceActive: Bool = false
    public var lastHeartbeatAgo: Double? = nil

    public init(ts: Double) {
        self.ts = ts
    }
}

/// The five rules from blueprint section 2.7 and `06-ops-defense.md` 4.4.
/// No scoring: each rule has one condition and one action.
public final class RuleEngine {
    public static let networkWindow = 600.0
    public static let networkSustain = 30.0
    public static let networkFactor = 5.0
    public static let clipboardLimit = 3
    public static let clipboardWindow = 60.0
    public static let cpuLimit = 80.0
    public static let cpuSustain = 60.0
    public static let memoryLimitMB = 2048.0
    public static let heartbeatLimit = 10.0
    public static let silenceSeconds = 900.0

    public private(set) var state: Severity = .green

    private var rateSamples: [(ts: Double, rate: Double)] = []
    private var cpuSamples: [(ts: Double, cpu: Double)] = []
    private var clipboardEvents: [Double] = []
    private var lastClipboardCount: Int?
    private var active: Set<String> = []
    private var silencedUntil: [String: Double] = [:]

    public init() {}

    /// Silence one rule for a while (blueprint 2.7: one alert per transition,
    /// 15 minute silence action). The rule still counts toward `state`.
    public func silence(rule: String, seconds: Double = RuleEngine.silenceSeconds, from now: Double) {
        silencedUntil[rule] = now + seconds
    }

    public func evaluate(_ s: Sample) -> [Alert] {
        var fired: [Alert] = []

        // M1: outbound rate above five times its 10 minute median for 30 s.
        if let rate = s.outboundBytesPerSec {
            rateSamples.append((s.ts, rate))
            rateSamples.removeAll { $0.ts < s.ts - Self.networkWindow }
            if let med = median(rateSamples.map { $0.rate }), med > 0 {
                let hasBaseline = rateSamples.contains { $0.ts <= s.ts - Self.networkSustain }
                let recent = rateSamples.filter { $0.ts > s.ts - Self.networkSustain }
                if hasBaseline, recent.count >= 3, recent.allSatisfy({ $0.rate > Self.networkFactor * med }) {
                    fired.append(Alert(
                        rule: "M1",
                        severity: .amber,
                        detail: String(format: "outbound %.0f bytes per s vs median %.0f", rate, med)
                    ))
                }
            }
        }

        // M2: camera or microphone active while the browser is frontmost.
        if s.deviceActive && s.chatFrontmost {
            fired.append(Alert(rule: "M2", severity: .red, detail: "camera or microphone active while chat is frontmost"))
        }

        // M3: more than three clipboard changes in 60 s, counts only.
        if let count = s.clipboardChangeCount {
            if let last = lastClipboardCount, count > last {
                let delta = min(count - last, 50)
                clipboardEvents.append(contentsOf: Array(repeating: s.ts, count: delta))
            }
            lastClipboardCount = count
            clipboardEvents.removeAll { $0 < s.ts - Self.clipboardWindow }
            if s.chatFrontmost && clipboardEvents.count > Self.clipboardLimit {
                fired.append(Alert(
                    rule: "M3",
                    severity: .amber,
                    detail: "clipboard " + String(clipboardEvents.count) + " changes in 60 s"
                ))
            }
        }

        // M4: browser CPU above 80 percent for 60 s, or memory above 2 GB.
        if let cpu = s.cpuPercent {
            cpuSamples.append((s.ts, cpu))
            cpuSamples.removeAll { $0.ts < s.ts - Self.cpuSustain - 10 }
            if let first = cpuSamples.first, s.ts - first.ts >= Self.cpuSustain,
               cpuSamples.allSatisfy({ $0.cpu > Self.cpuLimit }) {
                fired.append(Alert(
                    rule: "M4",
                    severity: .amber,
                    detail: String(format: "cpu %.0f percent for 60 s", cpu)
                ))
            }
        }
        if let mem = s.memoryMB, mem > Self.memoryLimitMB {
            fired.append(Alert(rule: "M4", severity: .amber, detail: String(format: "memory %.0f MB", mem)))
        }

        // M5: heartbeat missing for more than 10 s.
        if let ago = s.lastHeartbeatAgo, ago > Self.heartbeatLimit {
            fired.append(Alert(rule: "M5", severity: .red, detail: String(format: "heartbeat gap %.1f s", ago)))
        }

        let nowActive = Set(fired.map { $0.rule })
        state = fired.map { $0.severity }.max() ?? .green

        var emitted: [Alert] = []
        for alert in fired {
            let isNew = !active.contains(alert.rule)
            let muted = (silencedUntil[alert.rule] ?? 0) > s.ts
            if isNew && !muted {
                emitted.append(alert)
            }
        }
        active = nowActive
        return emitted
    }

    private func median(_ values: [Double]) -> Double? {
        guard !values.isEmpty else { return nil }
        let sorted = values.sorted()
        let mid = sorted.count / 2
        if sorted.count % 2 == 0 {
            return (sorted[mid - 1] + sorted[mid]) / 2
        }
        return sorted[mid]
    }
}
