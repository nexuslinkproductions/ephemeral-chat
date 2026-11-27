import XCTest
@testable import EphemeralMonitor

final class MonitorTests: XCTestCase {

    // MARK: helpers

    private func tempLogURL() -> URL {
        return FileManager.default.temporaryDirectory
            .appendingPathComponent("ephemeral-monitor-test-" + UUID().uuidString)
            .appendingPathComponent("monitor.log")
    }

    private func read(_ url: URL) throws -> String {
        return String(decoding: try Data(contentsOf: url), as: UTF8.self)
    }

    private func sample(_ ts: Double, rate: Double? = nil, cpu: Double? = nil, mem: Double? = nil) -> Sample {
        var s = Sample(ts: ts)
        s.outboundBytesPerSec = rate
        s.cpuPercent = cpu
        s.memoryMB = mem
        return s
    }

    // MARK: hash chain log

    func testAppendAndVerify() throws {
        let url = tempLogURL()
        let log = try HashChainLog(path: url)
        try log.heartbeat(atMillis: 1_000)
        try log.append(kind: "event", rule: "ports", detail: "listening 127.0.0.1:5000", atMillis: 2_000)
        try log.alert(rule: "M2", detail: "camera active", atMillis: 3_000)
        try log.close()

        let text = try read(url)
        let report = HashChainLog.verify(contents: text)
        XCTAssertTrue(report.healthy, report.firstBreak ?? "")
        XCTAssertEqual(report.records, 3)
        XCTAssertEqual(report.heartbeatGaps, [])
        for line in text.split(separator: "\n") {
            XCTAssertEqual(String(line).components(separatedBy: "\t").count, 7)
        }
    }

    func testReopenContinuesChain() throws {
        let url = tempLogURL()
        let first = try HashChainLog(path: url)
        try first.heartbeat(atMillis: 1_000)
        try first.heartbeat(atMillis: 2_000)
        try first.close()

        let second = try HashChainLog(path: url)
        XCTAssertEqual(second.lastSeq, 2)
        try second.heartbeat(atMillis: 3_000)
        try second.close()

        let report = HashChainLog.verify(contents: try read(url))
        XCTAssertTrue(report.healthy, report.firstBreak ?? "")
        XCTAssertEqual(report.records, 3)
    }

    func testTamperedRecordIsDetected() throws {
        let url = tempLogURL()
        let log = try HashChainLog(path: url)
        try log.append(kind: "event", rule: "x", detail: "alpha", atMillis: 1_000)
        try log.append(kind: "event", rule: "x", detail: "bravo", atMillis: 2_000)
        try log.append(kind: "event", rule: "x", detail: "charlie", atMillis: 3_000)
        try log.close()

        var lines = try read(url).split(separator: "\n").map(String.init)
        lines[1] = lines[1].replacingOccurrences(of: "bravo", with: "bravt")
        try Data((lines.joined(separator: "\n") + "\n").utf8).write(to: url)

        let report = HashChainLog.verify(contents: try read(url))
        XCTAssertFalse(report.healthy)
        XCTAssertEqual(report.firstBreak, "hash mismatch at seq 2")

        XCTAssertThrowsError(try HashChainLog(path: url)) { error in
            guard case HashChainError.tampered = error else {
                return XCTFail("expected tampered, got \(error)")
            }
        }
    }

    func testDeletedRecordIsDetected() throws {
        let url = tempLogURL()
        let log = try HashChainLog(path: url)
        try log.append(kind: "event", rule: "x", detail: "one", atMillis: 1_000)
        try log.append(kind: "event", rule: "x", detail: "two", atMillis: 2_000)
        try log.append(kind: "event", rule: "x", detail: "three", atMillis: 3_000)
        try log.close()

        var lines = try read(url).split(separator: "\n").map(String.init)
        lines.remove(at: 1)
        try Data((lines.joined(separator: "\n") + "\n").utf8).write(to: url)

        let report = HashChainLog.verify(contents: try read(url))
        XCTAssertFalse(report.healthy)
        XCTAssertEqual(report.firstBreak, "seq 3 at line 2, expected 2")
    }

    func testHeartbeatGapIsReported() throws {
        let url = tempLogURL()
        let log = try HashChainLog(path: url)
        try log.heartbeat(atMillis: 1_000)
        try log.heartbeat(atMillis: 2_000)
        try log.heartbeat(atMillis: 30_000)
        try log.close()

        let report = HashChainLog.verify(contents: try read(url))
        XCTAssertTrue(report.healthy)
        XCTAssertEqual(report.heartbeatGaps, ["gap 28.0 s before seq 3"])
    }

    func testDetailIsSanitizedToOneAsciiLine() throws {
        let url = tempLogURL()
        let log = try HashChainLog(path: url)
        try log.append(kind: "event", rule: "x", detail: "caf\u{00e9}\tline\nbreak", atMillis: 1_000)
        try log.close()

        let text = try read(url)
        let report = HashChainLog.verify(contents: text)
        XCTAssertTrue(report.healthy, report.firstBreak ?? "")
        for scalar in text.unicodeScalars {
            XCTAssertLessThan(scalar.value, 0x80)
        }
        XCTAssertEqual(text.split(separator: "\n").count, 1)
        XCTAssertTrue(text.contains("caf?"))
    }

    // MARK: rules, each one must be able to fire

    func testM1FiresOnBurstAboveFiveTimesMedian() {
        let engine = RuleEngine()
        var t = 0.0
        var alerts: [Alert] = []
        while t <= 120 {
            alerts += engine.evaluate(sample(t, rate: 10_000))
            t += 5
        }
        XCTAssertTrue(alerts.isEmpty, "baseline must stay quiet")

        while t <= 165 {
            alerts += engine.evaluate(sample(t, rate: 100_000))
            t += 5
        }
        let m1 = alerts.filter { $0.rule == "M1" }
        XCTAssertEqual(m1.count, 1, "one alert per transition")
        XCTAssertEqual(m1.first?.severity, .amber)
    }

    func testM1StaysQuietOnSteadyTraffic() {
        let engine = RuleEngine()
        var t = 0.0
        var alerts: [Alert] = []
        while t <= 300 {
            alerts += engine.evaluate(sample(t, rate: 50_000))
            t += 5
        }
        XCTAssertTrue(alerts.filter { $0.rule == "M1" }.isEmpty)
    }

    func testM2FiresOnDeviceWhileFrontmost() {
        let engine = RuleEngine()
        var s = Sample(ts: 10)
        s.deviceActive = true
        s.chatFrontmost = true
        var quiet = Sample(ts: 0)
        quiet.deviceActive = true
        quiet.chatFrontmost = false
        XCTAssertTrue(engine.evaluate(quiet).isEmpty)
        let alerts = engine.evaluate(s)
        XCTAssertEqual(alerts.first?.rule, "M2")
        XCTAssertEqual(alerts.first?.severity, .red)
        XCTAssertEqual(alerts.first?.needsSound, true)
        XCTAssertTrue(engine.evaluate(s).isEmpty, "no repeat while the condition holds")
    }

    func testM3FiresOnClipboardChurn() {
        let engine = RuleEngine()
        var alerts: [Alert] = []
        for (i, count) in [1, 1, 2, 3, 4, 5].enumerated() {
            var s = Sample(ts: Double(i) * 2)
            s.chatFrontmost = true
            s.clipboardChangeCount = count
            alerts += engine.evaluate(s)
        }
        let m3 = alerts.filter { $0.rule == "M3" }
        XCTAssertEqual(m3.count, 1)
        XCTAssertEqual(m3.first?.severity, .amber)
        XCTAssertEqual(m3.first?.detail, "clipboard 4 changes in 60 s")
    }

    func testM3QuietWhenNotFrontmost() {
        let engine = RuleEngine()
        var alerts: [Alert] = []
        for (i, count) in [1, 2, 3, 4, 5].enumerated() {
            var s = Sample(ts: Double(i))
            s.chatFrontmost = false
            s.clipboardChangeCount = count
            alerts += engine.evaluate(s)
        }
        XCTAssertTrue(alerts.filter { $0.rule == "M3" }.isEmpty)
    }

    func testM4FiresOnSustainedCpuAndOnMemory() {
        let cpuEngine = RuleEngine()
        var cpuAlerts: [Alert] = []
        var t = 0.0
        while t <= 70 {
            cpuAlerts += cpuEngine.evaluate(sample(t, cpu: 90))
            t += 10
        }
        XCTAssertEqual(cpuAlerts.filter { $0.rule == "M4" }.count, 1)
        XCTAssertEqual(cpuAlerts.first?.severity, .amber)

        let memEngine = RuleEngine()
        let memoryAlerts = memEngine.evaluate(sample(5, mem: 3_000))
        XCTAssertEqual(memoryAlerts.filter { $0.rule == "M4" }.count, 1)
        XCTAssertEqual(memoryAlerts.first?.severity, .amber)
    }

    func testM4CpuSpikeDoesNotSustain() {
        let engine = RuleEngine()
        var alerts: [Alert] = []
        var t = 0.0
        while t <= 120 {
            alerts += engine.evaluate(sample(t, cpu: t < 40 ? 95 : 10))
            t += 10
        }
        XCTAssertTrue(alerts.filter { $0.rule == "M4" }.isEmpty)
    }

    func testM5FiresOnHeartbeatGap() {
        let engine = RuleEngine()
        var s = Sample(ts: 100)
        s.lastHeartbeatAgo = 12.5
        let alerts = engine.evaluate(s)
        XCTAssertEqual(alerts.first?.rule, "M5")
        XCTAssertEqual(alerts.first?.severity, .red)
        XCTAssertEqual(alerts.first?.detail, "heartbeat gap 12.5 s")
    }

    func testEveryRuleCanFire() {
        let cases: [(String, Severity)] = [
            ("M1", .amber), ("M2", .red), ("M3", .amber), ("M4", .amber), ("M5", .red)
        ]
        var seen: [String: Severity] = [:]

        let net = RuleEngine()
        var t = 0.0
        while t <= 120 { _ = net.evaluate(sample(t, rate: 10_000)); t += 5 }
        while t <= 165 {
            for a in net.evaluate(sample(t, rate: 100_000)) { seen[a.rule] = a.severity }
            t += 5
        }

        let dev = RuleEngine()
        var devSample = Sample(ts: 1)
        devSample.deviceActive = true
        devSample.chatFrontmost = true
        for a in dev.evaluate(devSample) { seen[a.rule] = a.severity }

        let clip = RuleEngine()
        for (i, c) in [1, 2, 3, 4, 5].enumerated() {
            var s = Sample(ts: Double(i))
            s.chatFrontmost = true
            s.clipboardChangeCount = c
            for a in clip.evaluate(s) { seen[a.rule] = a.severity }
        }

        let mem = RuleEngine()
        for a in mem.evaluate(sample(1, mem: 3_000)) { seen[a.rule] = a.severity }

        let hb = RuleEngine()
        var gapSample = Sample(ts: 1)
        gapSample.lastHeartbeatAgo = 11
        for a in hb.evaluate(gapSample) { seen[a.rule] = a.severity }

        for (rule, severity) in cases {
            XCTAssertEqual(seen[rule], severity, "rule \(rule) did not fire with the blueprint severity")
        }
    }

    func testSilenceMutesButKeepsState() {
        let engine = RuleEngine()
        engine.silence(rule: "M2", from: 0)
        var s = Sample(ts: 10)
        s.deviceActive = true
        s.chatFrontmost = true
        XCTAssertTrue(engine.evaluate(s).isEmpty)
        XCTAssertEqual(engine.state, .red)
    }

    // MARK: parsers

    func testParsePS() {
        let text = """
          501   3.5  204800 /Applications/Google Chrome.app/Contents/MacOS/Google Chrome
          502  12.0 1048576 /Applications/Google Chrome.app/Contents/MacOS/Google Chrome Helper (Renderer)
           99   0.1   10240 /usr/sbin/some daemon
        """
        let rows = ProcessSampler.parsePS(text)
        XCTAssertEqual(rows.count, 3)
        XCTAssertEqual(rows[0].pid, 501)
        XCTAssertEqual(rows[0].command, "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        let totals = ProcessSampler.browserTotals(rows, match: "Google Chrome")
        XCTAssertEqual(totals.cpuPercent, 15.5, accuracy: 0.001)
        XCTAssertEqual(totals.rssMB, 1224.0, accuracy: 0.001)
        XCTAssertEqual(totals.pids, [501, 502])
    }

    func testParseLsof() {
        let text = """
        COMMAND  PID USER   FD   TYPE             DEVICE SIZE/OFF NODE NAME
        Google  501 marcel   45u  IPv4 0x1234567890abcdef      0t0  TCP 192.168.1.10:53122->93.184.216.34:443 (ESTABLISHED)
        Google  501 marcel   46u  IPv4 0xabcdef1234567890      0t0  UDP *:52111
        """
        let rows = ProcessSampler.parseLsof(text)
        XCTAssertEqual(rows.count, 2)
        XCTAssertEqual(rows[0].pid, 501)
        XCTAssertEqual(rows[0].proto, "TCP")
        XCTAssertEqual(rows[0].endpoint, "192.168.1.10:53122->93.184.216.34:443 (ESTABLISHED)")
        XCTAssertEqual(rows[1].proto, "UDP")
    }

    func testParseNettop() {
        let text = """
        Google Chrome.501,  15234,  98765,
        Google Chrome Helper.502,  100,  200,
        """
        let rows = ProcessSampler.parseNettop(text)
        XCTAssertEqual(rows[501]?.bytesIn, 15_234)
        XCTAssertEqual(rows[501]?.bytesOut, 98_765)
        XCTAssertEqual(rows[502]?.bytesOut, 200)
    }

    func testNewListeningEndpoints() {
        let added = ProcessSampler.newListeningEndpoints(previous: ["a", "b"], current: ["b", "c"])
        XCTAssertEqual(added, ["c"])
    }

    // MARK: launchd plist

    func testLaunchdPlist() throws {
        let testFile = URL(fileURLWithPath: #filePath)
        let root = testFile
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        let plistURL = root.appendingPathComponent("launchd/com.nexus.ephemeral-monitor.plist")
        let data = try Data(contentsOf: plistURL)
        let object = try PropertyListSerialization.propertyList(from: data, options: [], format: nil)
        guard let dict = object as? [String: Any] else {
            return XCTFail("plist is not a dictionary")
        }
        XCTAssertEqual(dict["Label"] as? String, "com.nexus.ephemeral-monitor")
        XCTAssertEqual(dict["RunAtLoad"] as? Bool, true)
        XCTAssertEqual(dict["KeepAlive"] as? Bool, true)
        XCTAssertEqual(dict["LimitLoadToSessionType"] as? String, "Aqua")
        let program = try XCTUnwrap(dict["ProgramArguments"] as? [String])
        XCTAssertEqual(program.count, 1)
        XCTAssertTrue(program[0].hasPrefix("/"))
    }
}
