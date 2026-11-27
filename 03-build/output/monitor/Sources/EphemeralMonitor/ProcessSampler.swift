import Foundation

public struct ProcessStat: Equatable {
    public let pid: Int32
    public let cpuPercent: Double
    public let rssKB: Double
    public let command: String
}

public struct Connection: Equatable {
    public let process: String
    public let pid: Int32
    public let proto: String
    public let endpoint: String
}

/// Parsers for the public counters the monitor is allowed to read:
/// `ps`, `lsof`, `nettop`. They are pure functions over command output so
/// the rule inputs are testable without running a browser.
public enum ProcessSampler {
    /// `ps -Ao pid=,pcpu=,rss=,comm=`, one process per line.
    public static func parsePS(_ text: String) -> [ProcessStat] {
        var rows: [ProcessStat] = []
        for line in text.split(separator: "\n") {
            let f = line.split(separator: " ", maxSplits: 3, omittingEmptySubsequences: true)
            guard f.count == 4,
                  let pid = Int32(f[0]),
                  let cpu = Double(f[1]),
                  let rss = Double(f[2]) else { continue }
            rows.append(ProcessStat(pid: pid, cpuPercent: cpu, rssKB: rss, command: String(f[3])))
        }
        return rows
    }

    /// `lsof -nP -i`. COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME.
    /// NAME is the last column and may contain one space before the state.
    public static func parseLsof(_ text: String) -> [Connection] {
        var rows: [Connection] = []
        for line in text.split(separator: "\n") {
            let f = line.split(separator: " ", omittingEmptySubsequences: true)
            guard f.count >= 9,
                  let pid = Int32(f[1]),
                  f[7] == "TCP" || f[7] == "UDP" else { continue }
            let name = f[8...].joined(separator: " ")
            rows.append(Connection(process: String(f[0]), pid: pid, proto: String(f[7]), endpoint: name))
        }
        return rows
    }

    /// `nettop -P -x -l 1 -J bytes_in,bytes_out`: `Process.pid, in, out,`.
    public static func parseNettop(_ text: String) -> [Int32: (bytesIn: UInt64, bytesOut: UInt64)] {
        var rows: [Int32: (bytesIn: UInt64, bytesOut: UInt64)] = [:]
        for line in text.split(separator: "\n") {
            let f = line.split(separator: ",", omittingEmptySubsequences: false)
            guard f.count >= 3 else { continue }
            let head = String(f[0]).trimmingCharacters(in: .whitespaces)
            guard let dot = head.lastIndex(of: "."), let pid = Int32(head[head.index(after: dot)...]) else { continue }
            let bytesIn = UInt64(String(f[1]).trimmingCharacters(in: .whitespaces)) ?? 0
            let bytesOut = UInt64(String(f[2]).trimmingCharacters(in: .whitespaces)) ?? 0
            rows[pid] = (bytesIn, bytesOut)
        }
        return rows
    }

    /// Sum every helper process whose command path contains `match`.
    public static func browserTotals(_ rows: [ProcessStat], match: String) -> (cpuPercent: Double, rssMB: Double, pids: [Int32]) {
        let browser = rows.filter { $0.command.contains(match) }
        let cpu = browser.reduce(0.0) { $0 + $1.cpuPercent }
        let rss = browser.reduce(0.0) { $0 + $1.rssKB } / 1024.0
        return (cpu, rss, browser.map { $0.pid })
    }

    /// Listening endpoint strings present now but not before.
    public static func newListeningEndpoints(previous: Set<String>, current: Set<String>) -> [String] {
        return current.subtracting(previous).sorted()
    }
}
