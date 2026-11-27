import Foundation
import CryptoKit

public enum HashChainError: Error, CustomStringConvertible {
    case tampered(String)

    public var description: String {
        switch self {
        case .tampered(let why):
            return "hash chain broken: " + why
        }
    }
}

/// One append-only record. The hash covers every field of the record plus
/// the hash of the record before it, so editing, reordering, inserting or
/// deleting a record breaks the chain at that point.
public struct LogRecord: Equatable {
    public let seq: Int
    public let tsMillis: Int64
    public let kind: String
    public let rule: String
    public let detail: String
    public let prevHash: String
    public let hash: String

    public init(seq: Int, tsMillis: Int64, kind: String, rule: String, detail: String, prevHash: String) {
        self.seq = seq
        self.tsMillis = tsMillis
        self.kind = kind
        self.rule = rule
        self.detail = detail
        self.prevHash = prevHash
        self.hash = HashChainLog.recordHash(seq: seq, tsMillis: tsMillis, kind: kind, rule: rule, detail: detail, prevHash: prevHash)
    }

    /// Tab separated ASCII line, 7 fields. Detail is sanitized so a field
    /// can never contain a tab or a newline.
    public var line: String {
        [String(seq), String(tsMillis), kind, rule, detail, prevHash, hash].joined(separator: "\t")
    }
}

public struct VerifyReport: Equatable {
    public var records: Int = 0
    public var firstBreak: String?
    public var heartbeatGaps: [String] = []

    public init() {}

    public var healthy: Bool { firstBreak == nil }
}

/// Append-only hash-chained log under ~/Library/Application Support.
/// Reopening a file continues the chain; reopening a broken file throws,
/// because a broken chain is evidence and must not be papered over.
public final class HashChainLog {
    public static let genesis = String(repeating: "0", count: 64)
    public static let heartbeatGapMillis: Int64 = 10_000

    public let path: URL
    private var handle: FileHandle
    public private(set) var lastSeq: Int
    public private(set) var lastHash: String

    public static func sha256Hex(_ s: String) -> String {
        SHA256.hash(data: Data(s.utf8)).map { String(format: "%02x", $0) }.joined()
    }

    public static func recordHash(seq: Int, tsMillis: Int64, kind: String, rule: String, detail: String, prevHash: String) -> String {
        sha256Hex([String(seq), String(tsMillis), kind, rule, detail, prevHash].joined(separator: "\t"))
    }

    public init(path: URL) throws {
        self.path = path
        try FileManager.default.createDirectory(at: path.deletingLastPathComponent(), withIntermediateDirectories: true)
        if !FileManager.default.fileExists(atPath: path.path) {
            FileManager.default.createFile(atPath: path.path, contents: nil)
        }
        let data = try Data(contentsOf: path)
        let text = String(decoding: data, as: UTF8.self)
        let report = HashChainLog.verify(contents: text)
        if let brk = report.firstBreak {
            throw HashChainError.tampered(brk)
        }
        let records = HashChainLog.parse(text)
        self.lastSeq = records.last?.seq ?? 0
        self.lastHash = records.last?.hash ?? HashChainLog.genesis
        self.handle = try FileHandle(forWritingTo: path)
        try handle.seekToEnd()
    }

    @discardableResult
    public func append(kind: String, rule: String = "none", detail: String = "", atMillis: Int64? = nil) throws -> LogRecord {
        let ts = atMillis ?? Int64((Date().timeIntervalSince1970 * 1000).rounded())
        let rec = LogRecord(
            seq: lastSeq + 1,
            tsMillis: ts,
            kind: kind,
            rule: rule,
            detail: HashChainLog.sanitize(detail),
            prevHash: lastHash
        )
        try handle.write(contentsOf: Data((rec.line + "\n").utf8))
        try handle.synchronize()
        lastSeq = rec.seq
        lastHash = rec.hash
        return rec
    }

    public func heartbeat(atMillis: Int64? = nil) throws {
        try append(kind: "heartbeat", atMillis: atMillis)
    }

    public func alert(rule: String, detail: String, atMillis: Int64? = nil) throws {
        try append(kind: "alert", rule: rule, detail: detail, atMillis: atMillis)
    }

    public func close() throws {
        try handle.close()
    }

    /// Strip control characters and non ASCII bytes so one record is always
    /// one ASCII line.
    public static func sanitize(_ s: String) -> String {
        var out = ""
        for scalar in s.unicodeScalars {
            if scalar.value < 0x20 || scalar.value == 0x7f {
                out.append(" ")
            } else if scalar.value > 0x7e {
                out.append("?")
            } else {
                out.append(Character(scalar))
            }
        }
        let trimmed = out.trimmingCharacters(in: .whitespaces)
        return trimmed.isEmpty ? "none" : trimmed
    }

    /// Parse a well formed log body. Lines whose hash does not match are
    /// dropped; verify() is the function that reports where the break is.
    public static func parse(_ text: String) -> [LogRecord] {
        text.split(separator: "\n", omittingEmptySubsequences: true).compactMap { raw in
            let f = String(raw).components(separatedBy: "\t")
            guard f.count == 7, let seq = Int(f[0]), let ts = Int64(f[1]) else { return nil }
            let rec = LogRecord(seq: seq, tsMillis: ts, kind: f[2], rule: f[3], detail: f[4], prevHash: f[5])
            guard rec.hash == f[6] else { return nil }
            return rec
        }
    }

    /// Walk the whole file and report the first break, plus every heartbeat
    /// gap longer than 10 s. A missing monitor leaves exactly this trace.
    public static func verify(contents text: String) -> VerifyReport {
        var report = VerifyReport()
        var prev = genesis
        var expectedSeq = 1
        var lastHeartbeat: Int64?
        let lines = text.split(separator: "\n", omittingEmptySubsequences: true)
        for (index, raw) in lines.enumerated() {
            let f = String(raw).components(separatedBy: "\t")
            guard f.count == 7, let seq = Int(f[0]), let ts = Int64(f[1]) else {
                report.firstBreak = "malformed line " + String(index + 1)
                return report
            }
            if seq != expectedSeq {
                report.firstBreak = "seq " + String(seq) + " at line " + String(index + 1) + ", expected " + String(expectedSeq)
                return report
            }
            let recomputed = recordHash(seq: seq, tsMillis: ts, kind: f[2], rule: f[3], detail: f[4], prevHash: f[5])
            if recomputed != f[6] {
                report.firstBreak = "hash mismatch at seq " + String(seq)
                return report
            }
            if f[5] != prev {
                report.firstBreak = "prev hash mismatch at seq " + String(seq)
                return report
            }
            if f[2] == "heartbeat" {
                if let last = lastHeartbeat {
                    let gap = ts - last
                    if gap > heartbeatGapMillis {
                        report.heartbeatGaps.append("gap " + String(format: "%.1f", Double(gap) / 1000.0) + " s before seq " + String(seq))
                    }
                }
                lastHeartbeat = ts
            }
            prev = f[6]
            expectedSeq += 1
            report.records += 1
        }
        return report
    }
}
