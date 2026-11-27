// swift-tools-version:5.9
import PackageDescription

// R2-14 monitor package. Apple system frameworks only (Foundation,
// CryptoKit, AppKit). No external package dependencies by design.
let package = Package(
    name: "EphemeralMonitor",
    platforms: [.macOS(.v13)],
    targets: [
        .target(name: "EphemeralMonitor"),
        .executableTarget(
            name: "ephemeral-monitor",
            dependencies: ["EphemeralMonitor"]
        ),
        .testTarget(
            name: "EphemeralMonitorTests",
            dependencies: ["EphemeralMonitor"]
        )
    ]
)
