# 11. Packaging the executable: macOS, Windows, Linux and Omarchy

RUN: w5-ephemeral-platform-20261126, packaging lane, restarted and expanded to the tri platform ruling. Brief: `01-research/briefs/W5-PLATFORM.md`.
SUBJECT: the shell that opens the single file core in a self contained Chromium window, and the platform packaging that delivers it.
CORE UNDER DISCUSSION: `input/ephemeral-chat-v1.html`, 35,598 bytes, 1,154 lines, SHA-256 `23be3a0b6f53587e50c97c1767fa745980788288145dc79d3dba42095b150337` (measured with `shasum -a 256` in this pass).

This file is design, not code. It decides the wrapper, the per platform artifact, the integrity pin, the runtime posture, and the update story. It does not write the build. Every option carries a source URL. Every number is either measured in this pass, quoted from a fetched source with the source named, or labelled as inference.

Labels used throughout:

| Label | Meaning |
|---|---|
| EXEC-ONLY | Only exists in the shell, has no meaning in the single file mode. |
| CORE | Applies to `ephemeral-chat-v1.html` itself, in both modes. |
| MEASURED | Taken by a command in this pass on this host, command and result quoted. |
| QUOTED | Taken from a fetched source, title checked. |
| INFERRED | Follows from the design or the arithmetic, not demonstrated. |
| UNVERIFIED | Could not confirm in this pass. Do not build a decision on it alone. |

Sources cited by path throughout: `01-research/output/03-threat-model.md` (nine attacker classes, class 9 supply chain, section 11 risk ranking), `01-research/output/06-ops-defense.md` (kill sequence 2.5, kill scope 2.1, monitor 4.1 to 4.6, OS traces 5.2 to 5.3), `01-research/output/13-platform-ux.md` (window, menu, shortcuts, and the shell cut list, sections 3.1 to 3.6), `02-plan/output/blueprint-v2.md` (invariants I-2 and I-3, crypto stack, owner rulings).

## 0. The decision this file has to make, and the constraint it cannot break

The owner ruling says the executable opens the chat in a self contained Chromium window with full UI and navigation (`_config/SETUP.md`, platform expansion). Three consequences follow before any framework is compared.

1. "Self contained Chromium" excludes every system webview option. A wrapper that renders in WebKit on macOS and WebView2 on Windows is not shipping Chromium, it is borrowing whatever Chromium the OS happens to have. Section 1.4 prices that honestly rather than dismissing it, because the size and memory numbers are genuinely better.
2. "Full UI and navigation" is scoped by `13-platform-ux.md` section 2.1: screen navigation, one pending session slot, a menu, keyboard paths. No history, no tabs, no address bar, no session list. That scoping is what makes a wrapper possible at all without building a browser.
3. The core stays one HTML file with no build step (blueprint owner ruling 3). So the shell cannot transform the core at package time. It can only wrap it, hash it, and refuse to run if the hash is wrong. Any design that wants to tree shake, bundle, or compile the core is out.

The hard constraint from the brief: every feature works in both modes or is flagged EXEC-ONLY with the reason. Almost everything in this file is EXEC-ONLY, and the file says so at each item. The one thing that is not EXEC-ONLY is the build hash string in the About panel, which helps the file mode too.

## 1. The option set, honestly

Five candidates, each with what it is, what it does to the security posture, its real size and memory cost, and whether it fits this engagement. The comparison is not "which is best"; it is "which one lets a 36 KB HTML file be the only thing the renderer parses, while keeping the shell small enough to audit and the engine pinnable enough to patch".

### 1.1 Electron, the primary self contained Chromium candidate

**What it is.** A packaged Chromium plus a Node.js main process. The renderer is the same engine as Chrome at a version Electron pins, and the main process is the native host that owns the window, the menu, and the file copy of the core.

**Source.** https://www.electronjs.org/docs/latest/tutorial/security ("Security | Electron") and https://www.electronjs.org/docs/latest/tutorial/fuses ("Electron Fuses | Electron"). Both fetched in this pass, titles as shown.

**What it adds to the security posture.**

- A pinned engine. The Chromium build is whatever the app ships, not whatever the OS has. For a product whose main risk is the platform (threat model class 7, `03-threat-model.md` section 7), a pinnable and testable engine is the single strongest argument for packaging. The browser is the TCB per RFC 8827; packaging does not remove that, but it replaces "any browser the user happens to run, with any extensions" with "one engine version, no extension model".
- No extension surface. Electron has no extension API enabled by default and the app never calls `session.loadExtension`. The class 7 gap that a malicious extension reads the DOM (`03-threat-model.md` section 7) is removed by construction, not mitigated. That is the most concrete security gain in this whole file.
- A real main process. It can hash the core before the renderer sees it (section 3), own the kill (section 8.2), and expose exactly one IPC channel.
- OS enforced integrity. Fuses are "magic bits" flipped at package time, and the docs state the reasoning plainly: "Because they are flipped at package time before you code sign your app, the OS becomes responsible for ensuring those bits aren't flipped back via OS-level code signing validation" (Electron Fuses). That is what makes the asar integrity check in section 3 worth anything.

**What it costs.**

- A main process with the user's full privileges and no sandbox of its own. The renderer is sandboxed (`sandbox: true` is the default since Electron 20 per the security page), but the main process is a native program. Any IPC handler that takes a string from the renderer and acts on it is a privilege boundary the browser mode did not have.
- Node is in the binary. Three fuses exist precisely because Node's environment hooks are living off the land vectors: `runAsNode` (the `ELECTRON_RUN_AS_NODE` variable), `nodeOptions` (`NODE_OPTIONS` and `NODE_EXTRA_CA_CERTS`), `nodeCliInspect` (`--inspect` and `SIGUSR1`). All three default to enabled and must be turned off. Section 6 is the full list.
- Size. Section 7 has the measured numbers. The short version: 115 to 151 MiB compressed, 268 to 373 MB unpacked, to render a 35,598 byte file.

**Honest size and memory.**

| Number | Value | How obtained |
|---|---|---|
| Framework zip, macOS arm64 | 120,872,990 bytes (115.3 MiB) | MEASURED: HTTP `Content-Length` on `electron-v45.5.0-darwin-arm64.zip`, this pass |
| Framework zip, macOS x64 | 125,153,068 bytes (119.4 MiB) | MEASURED, same method, `darwin-x64` |
| Framework zip, Windows x64 | 158,528,093 bytes (151.2 MiB) | MEASURED, same method, `win32-x64` |
| Framework zip, Linux x64 | 123,890,853 bytes (118.2 MiB) | MEASURED, same method, `linux-x64` |
| Unpacked empty app, macOS arm64 | about 268 MB | QUOTED, Elanis benchmark README, build size table |
| Unpacked empty app, macOS x64 | about 275 MB | QUOTED, same table |
| Unpacked empty app, Windows x64 | about 373 MB | QUOTED, same table |
| Unpacked empty app, Linux x64 | about 286 MB | QUOTED, same table |
| Resident memory, macOS arm64 | about 370 MB | QUOTED, same README, memory table, release build, main process plus children |
| Resident memory, Windows x64 | about 279 MB | QUOTED, same table |
| Resident memory, Linux x64 | about 596 MB | QUOTED, same table |

Source for the benchmark rows: https://github.com/Elanis/web-to-desktop-framework-comparison ("GitHub - Elanis/web-to-desktop-framework-comparison: An objective comparison of multiple frameworks that allow us to "transform" our web apps to desktop applications."). That README states its own limits: "These benchmarks are done on GitHub CI. There are ways to make measurements more accurate (e.g., multiple runs), but they will never be perfectly accurate, as they totally depend on system load and resources." So the memory numbers are order of magnitude, not a specification, and the Linux 596 MB figure is visibly noisier than the macOS one. The compression ratio between the zip and the unpacked tree is roughly 2.3 to 1, which is consistent across the three platforms and is arithmetic, not a claim.

**Engagement fit.** High. The core needs WebCrypto (`crypto.subtle`) for X25519 or P-256, AES-256-GCM, HKDF, and a dedicated Worker (blueprint section 2.2, `04-crypto-design.md` sections 2 and 8.2), plus a reliable ordered SCTP data channel. Chromium is the engine the whole V1 test suite already targets, per the brief's TARGET SYSTEM line. Nothing in the crypto design needs a capability Chromium lacks.

**Verdict.** RECOMMENDED as the primary. It is the only candidate that is both self contained and Chromium, and its integrity features (section 3) are real on two of the three platforms.

### 1.2 Chromium Embedded Framework

**What it is.** A C or C++ library that embeds Chromium in a native application. The host app owns the window and the message loop, and calls into `libcef` for the browser. It is the same engine Electron uses, without Electron's Node runtime and without Electron's packaging conventions.

**Source.** https://github.com/chromiumembedded/cef ("GitHub - chromiumembedded/cef: Chromium Embedded Framework (CEF). A simple framework for embedding Chromium-based browsers in other applications."), fetched in this pass.

**What it adds.** The smallest possible host: a native window with a single `CefBrowser` pointed at the core file, no Node, no npm dependency tree, no JavaScript in the privileged layer at all. If the threat you fear most is "the shell's own JavaScript gets compromised", CEF is the strongest answer, because the trusted path is C++ and the renderer has no Node bridge to reach.

**What it costs.** It is the most work by a wide margin. CEF ships as a binary distribution that you build against, not as a project scaffold: "Binary distributions, which include all files necessary to build a CEF-based application, are available on the Downloads page", and the general usage documentation describes a multi process architecture with its own handler interfaces that the host must implement. Every platform needs its own build and its own signing and packaging path. Per the CEF project's own downloads page the distributions track Chromium branches, so the update treadmill is now yours alone, with no Electron release cadence to lean on.

**Honest size.** No measured figure in this pass. CEF embeds the same Chromium that Electron does, so its floor is the Electron unpacked figure in section 1.1 minus the Node runtime; a CEF application of this kind lands in the same 200 to 300 MB unpacked band. That is INFERRED, not measured. I did not build a CEF host, so the number is not verified and the build cost is not priced.

**Engagement fit.** Poor for this engagement. The deliverable is a 36 KB HTML file wrapped for three platforms inside one research and build cycle. CEF means three native codebases (Cocoa, Win32, GTK) plus a build system, and every one of them is a new place for a memory safety bug in a product whose entire pitch is a small audited surface. The size win over Electron is real but the audit surface grows in the language least suited to a fast review.

**Verdict.** REJECTED for V2. Keep it as the named fallback if the Electron main process ever becomes the weak link, and record the reason so a later round does not rediscover it: three native hosts is more new attack surface than one Node main process.

### 1.3 Installed Chrome app mode shim

**What it is.** No bundled engine. A tiny launcher, or a documented shell command, that starts the Chromium or Chrome already installed on the machine with `--app=<url>`, which opens the page in a window with no tabs, no address bar and no browser chrome. The user data directory is pointed at a throwaway location with `--user-data-dir`.

**Source.** The `--user-data-dir` switch is documented in the Debian chromium(1) manual page, https://manpages.debian.org/bookworm/chromium/chromium.1.en.html, which says of it: "Specifies the directory that user data (your "profile") is kept in. Defaults to $HOME/.config/chromium. Separate instances of chromium must use separate user data directories". The same page also says the quiet part out loud: "chromium has hundreds of undocumented command-line flags that are added and removed at the whim of the developers. Here, we document relatively stable flags." `--app` is not in that documented list. Its behavior is described only by third party write ups, for example https://mrd0x.com/phishing-with-chromium-application-mode/ ("Security Research | mr.d0x"), which documents that the flag hides the address bar, launches in a separate window, and shows the site favicon in the taskbar.

**What it adds.** Zero bundle size, zero engine duplication, and the engine is patched by the browser vendor, which is the best patch cadence available anywhere. The core file is the entire app. There is no new native code to audit, no installer, no notarization bill, no SmartScreen reputation problem.

**What it costs.** It fails the owner ruling. It is not a self contained Chromium window; it is the user's Chromium, at the user's version, with the user's extensions loaded, because `--app` opens a normal profile window when a profile is reused. Extensions are exactly the class 7 threat (`03-threat-model.md` section 7) that packaging was supposed to remove. It also fails on machines without Chrome, and on Linux the binary is `chromium` or `chromium-browser` or `google-chrome` depending on the distro, so the launcher is a pile of platform ifs. And the flag itself is undocumented, which means it can change without notice.

There is a worse variant worth naming so nobody builds it: `--app` plus the user's default profile. That inherits cookies, history, extensions, and autofill into a product that promises none of those exist. Any use of this option must create a fresh `--user-data-dir` per launch and delete it, and even then the extension model is still loaded from the user's Chrome installation policy.

**Honest size.** The launcher is a few kilobytes. Memory is the resident cost of the user's own Chrome process, roughly what the Electron number would be minus the framework duplication, and I did not measure it. Marked UNVERIFIED.

**Engagement fit.** Low as the product, high as the escape hatch. It is the honest fallback for a user on a platform we do not ship, and it is a good thing to document in the About panel: "if you do not want the app, open this file in Chrome with a throwaway profile". That is a real distribution option with no supply chain at all, because the file is the whole thing.

**Verdict.** REJECTED as the shipped default, RECOMMENDED as the documented fallback path. It fails the owner ruling on self containment and it keeps the extension surface, which is the one thing the shell exists to remove.

### 1.4 Tauri, the system webview mismatch

**What it is.** A Rust host with a system webview renderer: WKWebView on macOS, WebView2 on Windows, WebKitGTK on Linux. The app is a few megabytes because the engine is not shipped.

**Source.** https://v2.tauri.app/reference/webview-versions/ ("Webview Versions"), fetched in this pass. It states: "Tauri uses WebKit on macOS (through WKWebView) and Linux (through webkit2gtk)", "Tauri uses WebView2 which is based on Microsoft Edge and therefore Chromium. WebView2 can update itself, you are guaranteed a relatively recent chromium build on all Windows targets", and the sentence that decides this for us: "On macOS, Tauri uses the webview that comes preinstalled with macOS since version 10.10 (Yosemite). It is considered a core component and is therefore updated with the regular OS updates. This means unsupported macOS versions do not receive WebKit updates."

**What it adds.** A genuinely tiny artifact and a Rust trusted core, which is a better memory safety story than a Node main process.

**What it costs, concretely, in this engagement.**

1. Three engines, three behavior sets, for one crypto stack. The blueprint's suite negotiation is X25519 where `crypto.subtle.deriveBits` accepts it and ECDH P-256 otherwise, with the suite id in the SAS transcript (blueprint section 2.2, `04-crypto-design.md` section 8.2). That fallback exists precisely because WebCrypto coverage varies. On WebKit the app would be on the fallback path on some platforms and the primary path on others, so the SAS digits, the displayed suite label, and the tested configuration differ per platform. Every R3 pen test case would need three variants. That is not a size trade, it is a test matrix multiplication.
2. The engine version is outside our control on two of three platforms. WebKit is the OS's and stops updating when the OS does. WebView2 updates itself on its own schedule. A security product that cannot say which engine build it ran on cannot answer the first question in any incident review.
3. Not self contained on Linux. Tauri's prerequisites page lists `libwebkit2gtk-4.1-dev` and friends as system packages (https://v2.tauri.app/start/prerequisites/). On Arch the equivalent is `webkit2gtk-4.1` from the repos. So the AppImage is not actually self contained; it depends on the host's WebKitGTK version, which is the classic "works on my distro" failure.

**Honest size and memory.** About 3 MB (Windows x64), 4 MB (Linux x64), 5 MB (macOS arm64) unpacked per the Elanis benchmark build size table. Memory, release: about 312 MB Windows, 96 MB macOS, 94 MB Linux, same README. That macOS number is a third of Electron's and it is real. Note the benchmark's Tauri Linux start duration of about 30 seconds, which tells you how noisy that CI row is; treat the memory figures as a range, not a spec. Source: https://github.com/Elanis/web-to-desktop-framework-comparison.

**Engagement fit.** Poor, for the reasons above. If the product were a normal chat client, Tauri would win on size and memory without argument. For a product whose threat model names the platform as an attacker and whose crypto path is suite negotiated, three unpinnable engines is the wrong trade.

**Verdict.** REJECTED, and the rejection reason is the mismatch, not the quality. Tauri is a good framework that solves a different problem: minimum footprint for apps that do not care which engine renders them.

### 1.5 Neutralino, the same mismatch with a web server attached

**What it is.** A small native binary that serves the app over a local static web server and drives the system webview, with a WebSocket for native calls.

**Source.** https://neutralino.js.org/docs/ ("Introduction | Neutralinojs"), fetched in this pass. It states: "Neutralinojs doesn't bundle Chromium and uses the existing web browser library in the operating system (e.g., gtk-webkit2 on Linux). Neutralinojs implements a WebSocket connection for native operations and embeds a static web server to serve the web content."

**What it adds.** About 2 MB, per the benchmark table, and the least ceremony of any option.

**What it costs.** The same engine mismatch as Tauri, plus two things that are worse for this product specifically. First, a local HTTP server is a listening socket on the loopback interface. The engagement's strongest structural property is "no signaling server and no inbound listener" (`03-threat-model.md` section 10, class 5). Adding a loopback web server does not break DTLS, but it puts a listening port and an origin into a product that has spent its whole design budget removing exactly that. Second, a WebSocket bridge for native calls is a second unauthenticated local channel next to the IPC bridge, and it is reachable by any local process that can guess the port or read the config. The benchmark's Neutralino memory row, about 821 MB on Linux and 502 MB on Windows, also suggests the "lightweight" label does not survive contact with a real renderer.

**Honest size and memory.** 2 MB unpacked per the benchmark; memory 180 MB (macOS, debug only in that table), 502 MB Windows, 821 MB Linux. Source: https://github.com/Elanis/web-to-desktop-framework-comparison. Those memory numbers are suspiciously high for a 2 MB binary precisely because the cost is the system webview's process, which the app does not own or measure well.

**Engagement fit.** Poor, and for a sharper reason than Tauri. A local HTTP server is a listening socket, and the engagement's strongest structural property is that unsolicited inbound traffic has no path to an answer (`03-threat-model.md` section 10). The WebSocket bridge is a second local channel with no authentication story in the framework's own description.

**Verdict.** REJECTED. It is the only option that adds a network listener, and it buys nothing the other options do not already give.

### 1.6 Option matrix

| Option | Engine | Self contained | Extension surface | Engine pinnable | Unpacked size | Verdict |
|---|---|---|---|---|---|---|
| Electron | Chromium, shipped | Yes | None by default | Yes | 268 to 373 MB | RECOMMENDED |
| CEF | Chromium, shipped | Yes | None by default | Yes | Same band as Electron, INFERRED | Fallback only |
| Chrome app mode | User's Chrome | No | User's extensions | No | A few KB, plus the user's Chrome | Documented fallback |
| Tauri | WebKit, WebView2, WebKitGTK | No | None | No on macOS and Linux | 3 to 5 MB | Rejected |
| Neutralino | System webview | No | None | No | 2 MB | Rejected |

Sources for the table: the framework rows come from the five sources named in 1.1 to 1.5. The size column comes from https://github.com/Elanis/web-to-desktop-framework-comparison and the measured Electron zips in section 1.1.

## 2. Per platform packaging

Three platforms, three different trust machines, and they disagree about what a signature means. This section covers what each OS actually checks, what artifact to ship, and what fails if you get it wrong.

### 2.1 macOS: app bundle, Developer ID, notarization, Gatekeeper

**The artifact.** A `.app` directory bundle: `Contents/Info.plist`, `Contents/MacOS/<binary>`, `Contents/Resources/`, `Contents/Frameworks/` for Electron's helpers. Apple documents the required members plainly: "Info.plist file (Required)... Executable (Required) Every application must have an executable file... Resource files" (https://developer.apple.com/library/archive/documentation/CoreFoundation/Conceptual/CFBundles/BundleTypes/BundleTypes.html, "Bundle Structures", fetched this pass). Ship it inside a signed, notarized DMG so the drag to Applications is obvious; notarization accepts "Disk images (UDIF format)" as a deliverable per the notarization page.

**The signature chain.** Two steps, not one. Sign with a Developer ID Application certificate, then notarize.

- Signing: Apple requires "a Developer ID application, kernel extension, system extension, or installer certificate" and warns against ad hoc or local development certificates (https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution, "Notarizing macOS software before distribution", fetched this pass).
- Hardened runtime: the same page requires you to "Enable the Hardened Runtime capability for your app and command line targets".
- Secure timestamp: required, and Xcode's workflow includes it by default.
- No `get-task-allow`: the notary service rejects it when set true.
- Notarization: upload with `notarytool`, wait for the ticket, then staple it. The page states the mechanism: "the notary service generates a ticket for you to staple to your software; the notary service also publishes that ticket online where Gatekeeper can find it."

**What Gatekeeper does at first launch.** Apple's support page is explicit: "When you install Mac apps, plug-ins, and installer packages from outside the App Store, macOS checks the Developer ID signature to verify that the software is from an identified developer and that it has not been altered. By default, macOS Catalina and later also requires software to be notarized" (https://support.apple.com/en-us/102445, "Safely open apps on your Mac", fetched this pass). The same page documents the failure modes a user will hit if any step is skipped: "Apple cannot check ... for malicious software", "the app developer cannot be verified", "the app is damaged", and the manual Open Anyway path in System Settings.

**The honest cost of the hardened runtime.** It is not free. Apple: "The Hardened Runtime doesn't affect the operation of most apps, but it does disallow certain less common capabilities, like just-in-time (JIT) compilation. If your app relies on a capability that the Hardened Runtime restricts, add an entitlement to disable an individual protection" (https://developer.apple.com/documentation/security/hardened-runtime, "Hardened Runtime", fetched this pass). V8 needs JIT, so the macOS build must carry `com.apple.security.cs.allow-jit` (the entitlement Apple names and links on that page). That is one hardened runtime protection explicitly disabled for the whole app, including the main process. State it in the release notes rather than pretending the app is fully hardened. Whether any additional Electron entitlement beyond `allow-jit` is needed in the current Electron version is UNVERIFIED in this pass; Electron's default macOS signing configuration is the place to check before shipping.

**Quarantine.** A downloaded DMG carries `com.apple.quarantine`, which is what triggers the first launch check. Notarization is the thing that turns that check into "identified developer, notarized" instead of a block. Do not tell users to strip the attribute; that trains them to defeat the only OS control that is protecting them.

**What this costs the project.** An Apple Developer Program membership, a Mac in CI, and a notarization step that needs credentials in CI. Notarization also means Apple scans the binary. That is a third party seeing the artifact, not the user's data, but it is a disclosure the About panel should name if the product is going to be honest about its supply chain.

### 2.2 Windows: NSIS, MSI, MSIX, portable zip, SmartScreen, Mark of the Web

Four artifact choices, and they differ mostly in what Windows can enforce about them.

| Artifact | What it is | What it buys | What it costs | Source |
|---|---|---|---|---|
| NSIS per user installer | The default target for electron-builder, an installer exe that unpacks the app to `%LOCALAPPDATA%` | No admin prompt, small installer, familiar flow, one signed exe to distribute | Writes an uninstaller entry in the registry, and the installer itself is what SmartScreen judges | https://www.electron.build/docs/nsis/ ("NSIS | electron-builder") |
| MSI | A Windows Installer package, typically per machine | Enterprise deployment, Group Policy, repair and uninstall semantics | Needs admin, needs a WiX style toolchain, and the per machine install widens the write scope | https://www.electronjs.org/docs/latest/tutorial/code-signing (documents the `electron-wix-msi` path and its signing hook) |
| MSIX | The modern package format with a package identity and a container | "Reliable install and uninstall... a 99.96% install success rate... guarantees a clean uninstall with no leftover files or registry entries", differential updates, optional containerized execution | Requires signing, and the identity model means the app is managed by Windows, not by us. Updates want App Installer or the Store | https://learn.microsoft.com/en-us/windows/msix/overview ("What is MSIX? - MSIX") |
| Portable zip | A zip the user unpacks and runs | No installation, no registry, nothing to uninstall, which fits an ephemeral product | No Start menu entry, no file association, and the exe inherits Mark of the Web from the zip, so first launch is a SmartScreen decision | https://support.apple.com/en-us/102445 is not the source here; see the MOTW row below |

**SmartScreen, stated honestly.** Microsoft's page says the check is reputation based: "SmartScreen also determines whether a downloaded app or app installer is potentially malicious by: Checking downloaded files against a list of reported malicious software sites and programs known to be unsafe... Checking downloaded files against a list of well-known files. If the file is a dangerous type and not well-known, SmartScreen displays a caution alert" (https://learn.microsoft.com/en-us/windows/security/operating-system-security/virus-and-threat-protection/microsoft-defender-smartscreen/, "Microsoft Defender SmartScreen", fetched this pass). It also says reputation attaches to the signing certificate: "If a URL, a file, an app, or a certificate has an established reputation, users don't see any warnings. If there's no reputation, the item is marked as a higher risk and presents a warning to the user."

Consequence for a new product: the first users of a freshly signed installer will see a warning no matter how correct the signature is, because the certificate has no history. EV certificates used to short circuit this; the modern cheapest path is a cloud signing service. Electron's own code signing page recommends one: "Azure Artifact Signing (formerly known as Azure Trusted Signing) is Microsoft's modern cloud-based signing service. It is the cheapest option for code signing on Windows, and it gets rid of SmartScreen warnings" (https://www.electronjs.org/docs/latest/tutorial/code-signing, "Code Signing | Electron"). Treat "gets rid of" as the vendor's claim about reputation building, not a guarantee for day one.

**Mark of the Web.** Windows records that a file came from the internet in an NTFS alternate data stream named `Zone.Identifier`, with a body like `[ZoneTransfer]` and `ZoneId=3`; Microsoft specifies this in [MS-FSCC] "Zone.Identifier Stream Name" (https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-fscc/6e3f7352-d11c-4d76-8c39-2516a9df36e8, fetched this pass). A zip carries it, and Explorer propagates it to extracted files. So a portable zip does not escape SmartScreen; it just moves the decision to the exe. An installer that the user runs knowingly is the cleaner path, because the user has already made a trust decision at the installer, and the installed exe then typically does not carry MOTW.

**Signing requirement.** Sign the installer and every executable inside it. An unsigned Electron app on Windows triggers the same class of warning as an unsigned Mac app, and Electron's page opens with that: "Both Windows and macOS prevent users from running unsigned applications. It is possible to distribute applications without codesigning them, but in order to run them, users need to go through multiple advanced and manual steps." Private key custody (HSM or cloud service) is now the norm for publicly trusted code signing certificates; the Azure option above is the cheap compliant path. The exact CA/Browser Forum requirement text is UNVERIFIED in this pass and is not needed to make the decision.

**Verdict for Windows.** NSIS per user installer, signed, no auto-update, plus a portable zip as the "no install" alternative for users who want nothing written to the registry.

### 2.3 Linux: AppImage versus a pacman package for Arch and Omarchy

Linux has no OS level code signing gate. There is no Gatekeeper and no SmartScreen. What exists is the package manager's signature checking, and only if the software goes through it. That single fact decides the recommendation.

**AppImage.**

- What it is: one file that contains the app and everything it needs. The project's own description: "The key idea of the AppImage format is one app = one file. Every AppImage contains an app and all the files the app needs to run." And the install story: "AppImages can be downloaded and run without installation or the need for root rights." Source: https://appimage.org/ ("AppImage"), fetched this pass.
- How a user runs it: `chmod a+x` then `./my.AppImage`, per the same page. There is no verification step in that flow, which is why the hash check in section 3 matters more on Linux than anywhere else.
- It needs FUSE. The AppImage docs are direct: "AppImages require a Linux technology called Filesystem in Userspace (or short FUSE). The majority of systems ships with a working FUSE setup. However, sometimes, it doesn't quite work." Source: https://docs.appimage.org/user-guide/troubleshooting/fuse.html ("I get some errors related to something called "FUSE""), fetched this pass.
- On Arch the package is `fuse2`: the same page's Arch instructions are `sudo pacman -S fuse2`, and it warns that "a common issue, however, is that the `fusermount` binary's permissions may be incorrect", with a `chmod u+s` fix. On Ubuntu the package is `libfuse2`, and on 24.04 it was renamed `libfuse2t64`.
- Fallback when FUSE is unavailable: `--appimage-extract-and-run`, documented on that page as extracting, running, and cleaning up, with the warning "Extracting an AppImage to run its contents is pretty expensive. It should only be done if you have no other options left." That fallback writes the whole app tree to a temp directory on every launch, which is both slow and a disk artifact.
- The runtime mounts the image for the life of the process, which is what the FUSE requirement means in practice. The exact mount point and its permissions are UNVERIFIED in this pass; treat "the app's files are a mounted filesystem while it runs" as the design consequence and check the mount options before claiming anything about other local users reading them.

**pacman package for Arch and Omarchy.**

- Omarchy is Arch based, and its own manual says so in the place that matters: "Arch has an amazing wealth of packages available for almost any type of software between the official repository and the Arch User Repository (AUR)... You can do the same with AUR, just use Install > AUR. Just remember that the AUR isn't vetted by the Arch team. It's like RubyGems or npm. Anyone can upload." Source: https://omarchy.org/manual/other-packages/ ("Other Packages - Omarchy Manual"), fetched this pass. Installation is `omarchy pkg add [package]` from the menu or the terminal.
- The package format: a `PKGBUILD` is "a Bash script containing the build information required for Arch Linux packages", built with `makepkg` into `pkgname.pkg.tar.zst`, "readily installable with pacman". Source: https://wiki.archlinux.org/title/PKGBUILD ("PKGBUILD - ArchWiki"), fetched this pass.
- Integrity: the `PKGBUILD` carries a `sha256sums` array over the `source` entries, and pacman verifies package signatures through `SigLevel`. Arch's page: "To determine if packages are authentic, pacman uses OpenPGP keys in a web of trust model... The `SigLevel` option in `/etc/pacman.conf` determines the level of trust required to install a package with `pacman -S`." Source: https://wiki.archlinux.org/title/Pacman/Package_signing ("pacman/Package signing"), fetched this pass. Note the page's own caveat: with the default `LocalFileSigLevel`, "any packages you build, and install with `pacman -U`, will not need to be signed using makepkg". So the signature guarantee applies to repo packages, not to a tarball a user built locally.
- What this buys over an AppImage: the source tarball is hash pinned in a file the user can read, the install is tracked by pacman (`pacman -Q`, clean removal), and updates arrive with `pacman -Syu` instead of a manual re-download. That last point is the only real update channel in this design (section 5.4).
- What it costs: an AUR package is only as trustworthy as its maintainer, and the AUR page says so: "AUR packages are user-produced content. These PKGBUILDs are completely unofficial and have not been thoroughly vetted. Any use of the provided files is at your own risk." (https://wiki.archlinux.org/title/Arch_User_Repository, "Arch User Repository", fetched this pass). If we control the AUR package ourselves, the trust anchor is our AUR account plus the `sha256sums` in the PKGBUILD, which is the same anchor as a published hash, just delivered through a channel Arch users already trust.

**Recommendation for Linux.** Ship both, with different roles. The pacman package is the primary for Arch and Omarchy, because that audience already has pacman and AUR in their workflow and it is the only artifact that updates through a signature-checking path. The AppImage is the portable fallback for every other distro, with the FUSE requirement stated on the download page in the same sentence as the hash, not in a footnote.

Do not ship an unsigned AppImage as the only Linux artifact. It is the one artifact in this whole design that arrives with no signature, no package manager, and no OS check, and it is also the one that is most often downloaded from a link in a chat message, which is exactly the class 9 delivery path in `03-threat-model.md`.

## 3. The embedded core and its integrity pin

This is the mechanism that answers the supply chain finding. It is three layers, and only two of them exist on all three platforms. Naming which is which is the whole point of this section.

### 3.1 How the core is embedded

The core, `ephemeral-chat-v1.html`, 35,598 bytes, goes into the app's `app.asar` archive as a single resource. It is not transformed at package time. No minification, no bundling, no inlining, no build step. The bytes in the asar are the bytes that were reviewed, and their SHA-256 is the hash published for the file mode.

At runtime the main process does not use `file://`. Electron's security checklist is explicit about why: "Pages running on `file://` have unilateral access to every file on your machine meaning that XSS issues can be used to load arbitrary files from the users machine. Using a custom protocol prevents issues like this as you can limit the protocol to only serving a specific set of files" (https://www.electronjs.org/docs/latest/tutorial/security, item 18). So the shell registers a custom scheme, reads the core once, and serves it.

### 3.2 The pinning mechanism, named

Four verification layers, in the order they execute.

**Layer 1, OS code signature.** On macOS, Developer ID plus notarization over the bundle. On Windows, Authenticode over the installer and every exe. On Linux, nothing at the OS level; see layer 4.

**Layer 2, the Electron fuse pair.** `EnableEmbeddedAsarIntegrityValidation` plus `OnlyLoadAppFromAsar`, both flipped at package time. This is the named mechanism:

- The asar header contains an `integrity` object with "a hex encoded hash of the entire archive as well as an array of hex encoded hashes for each block of `blockSize` bytes", and the app verifies the header hash at load: "If no hash is present or if there is a mismatch in the hashes, the app will forcefully terminate." Source: https://www.electronjs.org/docs/latest/tutorial/asar-integrity ("ASAR Integrity | Electron"), fetched this pass.
- The header hash is stored outside the archive, in `Info.plist` under `ElectronAsarIntegrity` on macOS, or in a Windows resource of type `Integrity` named `ElectronAsar` on Windows.
- The fuse doc states why the pair is required: "When combined with the `embeddedAsarIntegrityValidation` fuse, this fuse ensures that it is impossible to load non-validated code" (https://www.electronjs.org/docs/latest/tutorial/fuses).
- **Platform support, stated plainly: macOS as of Electron 16.0.0 and Windows as of Electron 30.0.0. Not Linux.** The ASAR integrity page lists exactly those two, and the fuse doc says the feature "validates the content of the `app.asar` file when it is loaded" on "macOS and Windows".

**Layer 3, our own SHA-256 of the core, checked at launch.** A 64 character constant compiled into the main process, compared against the hash of the bytes about to be served. Node provides the primitive: `node:crypto` "provides cryptographic functionality that includes a set of wrappers for OpenSSL's hash" functions (https://nodejs.org/api/crypto.html, "Crypto | Node.js v26.13.1 Documentation", fetched this pass). The order matters more than the API:

1. Read `app.asar` entry for the core into a single `Buffer`.
2. `createHash('sha256').update(buffer).digest('hex')`.
3. Compare to the constant with `crypto.timingSafeEqual` on the decoded bytes.
4. On mismatch: a dialog with the expected and actual hash, then `app.exit(1)`. No window is created, so no renderer ever parses the wrong file.
5. On match: register `protocol.handle('app', ...)` to serve that same in-memory Buffer, and load `app://core/index.html`.

Step 5 is the part that is easy to get wrong. Hashing a path and then loading the path leaves a window between check and load. Hashing the buffer and serving the same buffer removes it. It also means the renderer cannot read the file by any other route, because the buffer is the only copy the process hands out.

**Layer 4, the package manager, on Linux only.** For the pacman package, `sha256sums` in the `PKGBUILD` plus pacman's `SigLevel` checking is the root. For the AppImage there is no root at all beyond the user comparing the published hash, which is why the About panel must show the value.

### 3.3 What each layer proves, per platform

| Platform | Layer 1 | Layer 2 (asar integrity) | Layer 3 (core SHA-256) | Net statement |
|---|---|---|---|---|
| macOS | Developer ID, notarized, stapled | Yes, Electron 16 and later | Yes | "The app is the signed build, and the HTML inside it is the reviewed file." This is the strongest chain of the three. |
| Windows | Authenticode over installer and exes | Yes, Electron 30 and later | Yes | Same statement, with the caveat that SmartScreen reputation is separate from signature validity. |
| Linux, pacman | None at OS level; pacman PGP over repo packages, PKGBUILD hash for local builds | **No** | Yes | "The HTML is the reviewed file if the package is genuine." The package's provenance is the root, not the binary's signature. |
| Linux, AppImage | None | **No** | Yes | "The HTML is the reviewed file if the shell binary is genuine." The shell binary is unverified. Say this on the download page. |

### 3.4 What the pin closes and what it does not

**Closes.** The finding in `03-threat-model.md` class 9, "No signature, no published hash, no version display, no build provenance", in the specific form that matters most: a swapped HTML file inside an otherwise genuine installer. On macOS and Windows the OS signature covers the asar header hash, the header hash covers every block, and layer 3 covers the exact bytes the renderer parses. A user who downloads from the real release page gets the reviewed file or a hard failure.

**Does not close.** Three limits, each real.

1. **A modified shell honestly reports a modified hash.** If an attacker replaces the whole app with their own build and can get it signed (or the user's OS to accept it), layer 3 compares their HTML against their own constant. The check is a tripwire, not a signature. Only layer 1 and layer 4 are roots.
2. **Linux has no layer 2.** An AppImage can be replaced wholesale, and its internal HTML replaced with it. The only defense is the published hash and the user's willingness to compare it.
3. **The hash constant is in the binary, not in a signed manifest.** There is no detached signature over the core that a third party can verify without trusting the binary. Adding one (minisign or cosign over the core file, public key in the repo and in the About panel) is cheap and is listed as a build card in section 9.

The mitigation for limit 1 and 2 is the same and it is free: show both hashes in the About panel, the build hash and the core hash, with the command to check them. `03-threat-model.md` class 9 option 4 asks for exactly this ("Display the build hash in the UI footer, generated at build time"), and `13-platform-ux.md` section 3.2 puts it in the About menu item. It is the one part of this file that also helps the file mode.

## 4. Runtime posture: what is in RAM and what is on disk

The promise is "user data in memory, cache disabled, no history". Here is exactly what that means per platform, including the parts that do not hold.

### 4.1 The three settings that do the work

1. **An in-memory session.** `session.fromPartition('core')` with no `persist:` prefix. The session doc: "If `partition` starts with `persist:`, the page will use a persistent session available to all pages in the app with the same `partition`. if there is no `persist:` prefix, the page will use an in-memory session" (https://www.electronjs.org/docs/latest/api/session, "session | Electron", fetched this pass). Cookies, localStorage, IndexedDB, and the HTTP cache for that partition do not outlive the process.
2. **The disk cache switched off.** `app.commandLine.appendSwitch('disable-http-cache')`, which the switch reference describes as "Disables the disk cache for HTTP requests" (https://www.electronjs.org/docs/latest/api/command-line-switches, "Supported Command Line Switches | Electron", fetched this pass). Belt and braces with the in-memory partition, because the switch is global and the partition is per session.
3. **A per launch user data directory.** `app.setPath('userData', <path>)` before `ready`. What the path defaults to: on macOS `~/Library/Application Support/<name>`, on Linux `$XDG_CONFIG_HOME` or `~/.config/<name>`, on Windows the appData directory plus the app name (https://www.electronjs.org/docs/latest/api/app, "app | Electron", fetched this pass). The app points it at a launch scoped directory and deletes it on exit.

### 4.2 What still writes to disk, per platform

The honest answer is that a Chromium app always wants a writable profile, and the settings above shrink it rather than remove it. Everything below was present unless the row says otherwise.

| Platform | Artifact | Written by | Can the shell stop it? |
|---|---|---|---|
| macOS | `userData` directory in Application Support | Chromium profile data, now launch scoped | Moved and deleted on exit. While running, it is real files on disk. Pointing it at a RAM disk with `hdiutil` removes the writes but leaves a mount to clean up. |
| macOS | `~/Library/Caches/<bundle id>` | Chromium cache, unless the partition is in memory | Empty with an in-memory partition and `--disable-http-cache`; the directory itself may still be created. |
| macOS | GPU shader cache and code cache under the profile | Chromium | Only by putting `userData` on a RAM disk. This is the residue most designs forget. |
| macOS | `com.apple.quarantine` xattr on the DMG and app | The downloading browser or mail client | No. Removed only by the user, and stripping it is bad advice. |
| macOS | LaunchServices registration, saved application state | The OS | State restoration is disabled at the window level (`13-platform-ux.md` section 3.1: no window state restore). LaunchServices registration is unavoidable for a bundled app. |
| macOS | Crash reports in `~/Library/Logs/DiagnosticReports` | The OS, for hard crashes | Partly: the app never calls the crash reporter, so no app minidumps are produced. A crash at the OS level can still write one. |
| Windows | `userData` under `%APPDATA%` | Chromium profile | Moved to a temp path and deleted on exit. There is no user mode RAM disk on Windows, so the bytes are on disk while the app runs. This is the one platform where the RAM claim is not fully achievable. |
| Windows | Registry uninstall entry, Start menu shortcut | The NSIS installer | No. That is what an install is. The portable zip avoids all of it. |
| Windows | `Zone.Identifier` ADS on the downloaded installer | The browser | No, and it is a feature, not a leak: it is what lets SmartScreen judge the installer. |
| Windows | Prefetch entries, Windows Error Reporting dumps | The OS | No. Both are system level and not app controlled. |
| Linux | `~/.config/<name>` and `~/.cache/<name>` | Chromium profile and cache | Moved to a launch scoped directory and deleted. A tmpfs path such as `/dev/shm/<name>-<pid>` removes the writes entirely. |
| Linux | The AppImage's mounted image while running | The AppImage runtime, through FUSE | No. It exists for the life of the process. |
| Linux | `systemd-coredump` entry on a hard crash | The OS | No. `coredumpctl` retention is a system setting (`06-ops-defense.md` section 5.3). |
| Linux | Journal lines if launched with logging | The shell's own stderr | Yes: do not enable file logging in release. |
| All | The core HTML itself in `app.asar` | Us, at package time | Not applicable. This is the app, and it is public by design. |

Two conclusions that belong in the About panel, in this order.

1. "The app keeps no history: no cookies, no transcript, no cache between launches, and no window state." That is true and it is a real improvement over the browser mode, where a crashed tab can restore form values (`03-threat-model.md` section 6, marked UNVERIFIED there).
2. "Your operating system can still write: swap, crash reports, Prefetch, the package manager's database. The app cannot prevent that." That is the same residual `03-threat-model.md` section 6 already concedes, and packaging does not change it.

What is only in RAM, in both modes: the transcript, the codes, the DTLS and SCTP state, the decrypted file buffers, the blob URLs, the reaction map (`13-platform-ux.md` section 1.7), and the session keys. The shell does not improve any of that; it only reduces what else is on disk around it.

## 5. The update problem

### 5.1 Why there is no in-app updater

Electron ships an auto-updater. The comparison table records it as "Official" for Electron (https://github.com/Elanis/web-to-desktop-framework-comparison). This design does not use it, and the reason is in `03-threat-model.md` class 9: an update channel is a network client with standing write access to the app directory, and a compromised update server is total compromise with no user action beyond launching the app. `13-platform-ux.md` section 3.6 states the same rule from the UX side: "No auto-update channel that phones home."

### 5.2 The cost, stated as plainly as the benefit

`03-threat-model.md` class 9 already names it: "No auto-update. This avoids an update-channel hijack, but it also lets users keep an old vulnerable copy indefinitely. The trade-off should be explicit." With a bundled Chromium this gets sharper. A user who installs once and never updates is running a frozen engine with a growing list of known CVEs. The browser mode at least inherits the browser vendor's patch cadence; the shell does not.

So the honest product statement is not "no update channel, therefore safer". It is: "no silent update, so nothing changes under you, and you must re-download to get engine fixes. The build date is on the About panel. If it is more than 90 days old, get a new one." That is a policy the UI can enforce by showing an age warning, which is a `CORE` feature and costs one line.

### 5.3 Manual replacement with hash verification, the minimum

Four steps, all of them boring, which is the point.

1. Publish the SHA-256 of every artifact next to it, in at least two channels: the release page and one independent one (a signed message, a second host, or the repo). `03-threat-model.md` class 9 option 1 asks for exactly this and gives the current core hash as the example.
2. Publish a detached signature over the artifact or over the hash list, with the public key in the repo and in the About panel. Without this, a compromised mirror serves a matching bad hash and step 3 verifies nothing. `03-threat-model.md` class 9 option 2 recommends minisign or cosign for precisely this reason.
3. Give the command per platform, in the download page and in the About panel: `shasum -a 256` on macOS, `sha256sum` on Linux, `certutil -hashfile <file> SHA256` on Windows. macOS and most Linux distros ship these binaries; a user who has to install a tool to verify will not verify.
4. The app shows its own two hashes, build and core, so the comparison has both sides.

What this does not do: it does not tell the user that a new version exists. That is deliberate. A version check is a network request that leaks "this person runs this app" to whoever answers, which is a metadata emission the product otherwise avoids entirely (`03-threat-model.md` class 1 and class 8). If a version check is ever added, it must be a user-initiated action with the result shown, not a background poll.

### 5.4 The one update channel that exists, and it is not ours

For Arch and Omarchy, the pacman package updates through `pacman -Syu` from the AUR or a repo. That path is signature checked (section 2.3), it is the user's normal maintenance, and it does not require us to run an update server. It is the best answer available in this design, and it is another argument for shipping the pacman package rather than only an AppImage.

### 5.5 What a signed update channel would cost, if anyone asks for it later

Record it so the answer is ready and the estimate is not invented on the spot. A real channel is not "download an exe and run it". It needs: signed metadata with a version, a hash, and a monotonic counter to stop rollback; a key that is not on the build machine; a client that verifies before executing; and a revocation path. That is one new trust root, one new network client, and one new key management problem, in a product whose entire supply chain advantage is that it has none. It is a V3 conversation at the earliest, and the answer for V2 is the manual replacement in 5.3.

## 6. Fuses and hardening flags

Everything here is EXEC-ONLY. Fuses are flipped at package time and then covered by the OS signature, which is what makes them stick (Electron Fuses doc, quoted in 1.1).

### 6.1 Fuses

| Fuse | Set to | What it prevents | Source |
|---|---|---|---|
| `runAsNode` | false | `ELECTRON_RUN_AS_NODE` turning the app into a Node interpreter, a known living off the land technique. The doc says disabling it also makes `child_process.fork` throw. | https://www.electronjs.org/docs/latest/tutorial/fuses |
| `nodeOptions` | false | `NODE_OPTIONS` and `NODE_EXTRA_CA_CERTS` injection through the environment | same |
| `nodeCliInspect` | false | `--inspect`, `--inspect-brk`, and inspector activation through `SIGUSR1` | same |
| `embeddedAsarIntegrityValidation` | true | Loading an asar whose header hash does not match the packaged value | same, plus https://www.electronjs.org/docs/latest/tutorial/asar-integrity |
| `onlyLoadAppFromAsar` | true | The search order fallback to `app/` or `default_app.asar`, which would bypass the integrity check | same |
| `grantFileProtocolExtraPrivileges` | false | `file://` pages getting `fetch` over `file://`, service workers, and universal child frame access | same |
| `cookieEncryption` | leave disabled | Nothing to encrypt: no cookies exist because the session is in memory. Enabling it is a one way transition and on macOS it needs Keychain access and a valid signature. | same |
| `loadBrowserProcessSpecificV8Snapshot` | true if the build produces the browser snapshot | A renderer using a snapshot built with `nodeIntegration` enabled | same |
| `wasmTrapHandlers` | leave enabled | Not a security switch. Disabling it trades memory safety checks for speed. Do not touch it. | same |

Verify the result in CI with `npx @electron/fuses read --app <artifact>`, which the fuse doc documents as the way to check an arbitrary Electron app.

### 6.2 Window and session settings

| Setting | Value | Why | Source |
|---|---|---|---|
| `nodeIntegration` | false | Renderer gets no Node. Default since Electron 5. | https://www.electronjs.org/docs/latest/tutorial/security |
| `contextIsolation` | true | Preload and page in separate JS contexts. Default since Electron 12. | same |
| `sandbox` | true | Renderer in the OS sandbox. Default since Electron 20. | same |
| `preload` | one file, one channel | `contextBridge` exposes wipe and badge only. Never expose `ipcRenderer` itself. | same, item 20 |
| `webSecurity` | true (default) | Do not disable. | same, item 6 |
| `allowRunningInsecureContent` | false | No mixed content, ever. | same, item 8 |
| `spellcheck` | false | A spell checker can send typed words off the page, which breaks invariant I-2 ("no plaintext or metadata leaves the page except STUN binding traffic", blueprint section 3). The core sets `spellcheck` false on the composer; the shell disables it globally. | blueprint section 3; `13-platform-ux.md` section 3.3 |
| `devTools` | false in release | Devtools on a live session is a plaintext inspector. | `13-platform-ux.md` section 3.1 |
| `setWindowOpenHandler` | deny all | No second window, ever. | security item 14 |
| `will-navigate` | deny everything except the `app://` origin | The core has no navigation. | security item 13 |
| `setPermissionRequestHandler` | deny every permission | Camera, mic, notifications, clipboard read: none are needed. | security item 5 |
| `session.setSpellCheckerEnabled(false)` | false | Same reason as the row above. | derived from the spellcheck rule |
| Crash reporter | never started | No minidumps, no upload, no telemetry. | `13-platform-ux.md` section 3.6 |

Two settings deliberately absent, so a later round does not add them back as "hardening".

- No `--no-sandbox`. It is the single most common Electron "fix" for a Linux problem and it removes the renderer sandbox.
- No `--disable-web-security`, no `--ignore-certificate-errors`. Both exist in the switch list and neither has any legitimate use here.

## 7. Bundle size and memory, per platform, with the trade named

### 7.1 The numbers

| Target | Download, compressed | Installed on disk | Resident memory, release | Source |
|---|---|---|---|---|
| macOS arm64 | 115.3 MiB (120,872,990 bytes) | about 268 MB | about 370 MB | MEASURED zip; QUOTED benchmark |
| macOS x64 | 119.4 MiB (125,153,068 bytes) | about 275 MB | not measured separately | MEASURED zip; QUOTED benchmark |
| Windows x64 | 151.2 MiB (158,528,093 bytes) | about 373 MB | about 279 MB | MEASURED zip; QUOTED benchmark |
| Linux x64 | 118.2 MiB (123,890,853 bytes) | about 286 MB | about 596 MB | MEASURED zip; QUOTED benchmark |
| Tauri, for comparison, macOS arm64 | not measured | about 5 MB | about 96 MB | QUOTED benchmark |
| Tauri, for comparison, Linux x64 | not measured | about 4 MB | about 94 MB | QUOTED benchmark |

Methods and sources, stated so the table can be audited.

- The zip column is MEASURED in this pass: `curl -sIL` against `https://github.com/electron/electron/releases/download/v45.5.0/electron-v45.5.0-<arch>.zip` and read `Content-Length`. That is the framework archive, which is the dominant term in any Electron app's download; our own code adds 35,598 bytes plus a few kilobytes of shell.
- The installed and memory columns are QUOTED from https://github.com/Elanis/web-to-desktop-framework-comparison, an empty app, built and measured on GitHub CI. That README warns about its own accuracy: measurements depend on system load, so read them as an order of magnitude. The 596 MB Linux resident figure and the 30 second Tauri Linux startup in the same table are the clearest evidence of that noise.
- INFERRED, arithmetic: 35,598 bytes against a 268 MB install is 0.013 percent. The app payload is a rounding error inside its own container.

### 7.2 The trade, stated without flinching

We ship 115 to 151 MiB of download and 268 to 373 MB of install to render a 36 KB file. That is the honest cost, and it is the largest single objection to this design. Three things make it acceptable and one thing does not.

Acceptable, in order of weight:

1. **The engine is pinnable, testable and patchable on our schedule.** The alternative is a system engine that stops updating when the OS does (Tauri's own documentation says unsupported macOS versions do not receive WebKit updates) or one that updates itself out from under the test matrix (WebView2). For a product whose threat model names the platform as an attacker, an engine you can name the version of is worth more than 260 MB of disk.
2. **The audit surface that is ours is tiny.** The binary is large, but the code we wrote and a reviewer must read is three files: `main.cjs`, `preload.cjs`, and the core HTML. Chromium is somebody else's reviewed code. "Large binary" and "large attack surface we own" are not the same claim, and only the second one matters for a review budget.
3. **The memory is not additive in practice.** 370 MB resident on a machine that already runs a browser is close to what the browser tab costs, and the shell replaces a browser tab rather than sitting beside one during a session.

Not acceptable as a defense, and should never be written down: "Electron is fine because everyone uses it". Popularity is not a security argument, and the same three fuses that make Electron workable exist because the defaults are unsafe.

### 7.3 What the size does to the distribution story

A 115 MB download is big enough that users will not verify hashes out of habit, which makes the published hash less useful than it looks. Two consequences for the build.

- The About panel must show the hash with the command, because the download page is where attention is lowest.
- A torrent or a signed archive is not an improvement; the artifact is the artifact. Do not add a second distribution path to make the size feel smaller. One artifact per platform, one hash per artifact.

## 8. What the shell adds, honestly

Three things get better and one gets worse. This section gives each its own weight.

### 8.1 A native process the external monitor can actually watch

`06-ops-defense.md` section 4 specifies a monitor in a separate process and a separate trust domain, and section 4.6 lists what it cannot see. One of those blind spots is removed by packaging:

> "Per-tab traffic. A browser multiplexes everything through shared sockets and helper processes."

With a browser, every tab shares the browser's sockets, so a monitor cannot attribute bytes to the chat. With the shell, the chat is its own process tree: one main process, its GPU and renderer children, and its own UDP socket for WebRTC. That means rules M1 (unexpected network rate) and M4 (CPU and memory) in `06-ops-defense.md` section 4.4 get a target with a real boundary instead of a guess. The monitor can compute a baseline for this app alone, which was impossible for a tab.

Two more signals the shell makes available, both cheap:

| Signal | How the monitor reads it | What it proves | What it does not |
|---|---|---|---|
| Binary integrity | `codesign -v` and `spctl -a -vv` on macOS, `Get-AuthenticodeSignature` on Windows, `pacman -Qkk` / `pacman -Q` on Linux | The installed app is the signed build, or the package files are unmodified | Nothing about the running process's memory |
| Version identity | The bundle's `CFBundleShortVersionString`, the exe's file version, or `pacman -Q` | Which engine build is running, so a CVE report can be answered | Nothing about whether that version is vulnerable |

That second row is worth more than it looks. `03-threat-model.md` class 7 says the app cannot attest the platform. True. But the shell lets a separate process ask the OS "is this binary the one that was signed", which the browser mode could never do for a tab. It is the closest thing to attestation available without an Apple entitlement or a kernel driver.

The honest limits, unchanged from `06-ops-defense.md` section 4.1: the monitor runs as the same user, so it can be killed; root defeats it; it cannot see inside DTLS; and a compromised renderer that behaves normally looks like a normal app. Attribution granularity is not detection.

### 8.2 Cleaner kill switch scoping

The browser kill is a page killing itself. The shell kill is a parent killing a child, and that is a different security property.

| Capability | Browser mode (`06-ops-defense.md` section 2.1) | Shell, EXEC-ONLY |
|---|---|---|
| Close the peer and channel | Yes, `pc.close()` | Yes, same code in the renderer, plus the main process can kill the process |
| Destroy the DOM and the JS heap | `location.replace('about:blank')`, best effort, the renderer may be reused | `webContents.close()` then `win.destroy()`, the renderer process goes with the window |
| Clear session storage | Not reachable, there is none | `session.clearStorageData()` and `session.clearCache()` from the main process |
| Delete the profile directory | Not reachable, the page cannot see the filesystem | Yes, `rm -rf` on the launch scoped `userData` path after the window is gone |
| Clear the clipboard | Requires focus and permission, and cannot clear history | The main process can clear the pasteboard without a focus gate, and still cannot clear clipboard history |
| Survive a compromised renderer | No. The renderer owns the kill path | Partly. A main process menu item and `app.exit()` do not depend on renderer cooperation |
| Prove the transport is dead | Yes, the connection object is closed | Yes, plus the process that owned it is gone |

Three design rules follow, and they are the actual deliverable of this subsection.

1. **The menu item, not the keystroke, is the authoritative kill.** The menu is built in the main process, so a renderer that swallows `keydown` cannot disable it. Double Escape stays as the fast path in both modes (`13-platform-ux.md` section 2.6), and the menu is the path that survives a hostile page.
2. **Kill order: renderer first, then storage, then process.** Ask the renderer to run the in-page sequence (it owns the DTLS close and the panic frame), wait at most 300 ms, then destroy the window, clear storage, delete the profile, and `app.exit(0)`. If the renderer does not answer, go straight to destroy. Never wait indefinitely on a compromised renderer.
3. **No global shortcut by default.** A process-wide `globalShortcut` would survive a renderer compromise completely, and it would also grab a chord system wide, which is a new OS-level surface and a collision risk with every other app. If it is offered at all, register it only while a session is live and unregister on kill. Default: off.

What the shell kill still cannot do, so the About copy does not overclaim: zero the DTLS keys inside Chromium, zero JavaScript strings, clear clipboard history, remove a screenshot, or touch swap. Those are the same ceilings as `06-ops-defense.md` section 2.6, and packaging does not move them.

### 8.3 The new attack surface the wrapper creates, per platform

This is the part a packaging document usually omits. Every row is a surface that does not exist in the file mode, with the honest mitigation and the residual that remains.

**Common to all three platforms.**

| New surface | Who can use it | Why it exists | Mitigation | Residual |
|---|---|---|---|---|
| A main process with full user privileges, outside the renderer sandbox | Anyone who gets code execution in the main process | It is the native host | Three files, one IPC channel, no `eval`, no remote content, sender validation on every IPC message | A main process bug is a full local compromise. It is smaller than a browser, not safer than one. |
| An IPC bridge | The renderer | The shell needs to be told to wipe or badge | One channel, allowlisted verbs, no strings passed to `exec` or `fs`, `event.senderFrame` checked | Any renderer compromise now has a native call surface. Keep it to two verbs. |
| A frozen engine with no auto-update | Anyone with a Chromium exploit for the shipped version | Deliberate: no update client, no update server | Publish build date, warn past 90 days, ship often | Users who never re-download accumulate known CVEs. This is the largest residual in this file. |
| A durable install | Local forensics (`03-threat-model.md` class 6) | Installing is writing files | Minimal footprint, no logs, no state, no recent files | The app's existence, version and install date are visible. A browser tab leaves less. |
| Installer as the trust gate | Whoever serves the download | Distribution | Signed, notarized where applicable, hash published in two channels | Users who skip verification get whatever the mirror served. |

**macOS.**

| New surface | Detail | Mitigation | Residual |
|---|---|---|---|
| Notarization upload | The binary goes to Apple's notary service | None available; it is a condition of distribution | A third party has a copy of the artifact. Say so in the release notes. |
| Hardened runtime JIT exception | `com.apple.security.cs.allow-jit` is required for V8 (Apple: the hardened runtime "disallows certain less common capabilities, like just-in-time (JIT) compilation") | Only that one entitlement, no others without a written reason | One hardening protection is off for the whole app, including the main process. |
| First launch online check | Gatekeeper verifies the notarization ticket and certificate revocation over the network | None; it is the OS | Apple states it does not associate these checks with a user or device (`https://support.apple.com/en-us/102445`), which is a claim about Apple's logging, not a guarantee for a network observer. |
| TCC prompts | A bundled app, unlike a tab, may be asked for Local Network access when WebRTC sends UDP to the LAN | Request nothing else, and explain the one prompt | UNVERIFIED for this macOS version. Verify on the build machine before writing the copy. |

**Windows.**

| New surface | Detail | Mitigation | Residual |
|---|---|---|---|
| SmartScreen reputation | A new certificate has no history, so early users see a warning | Sign with a reputable certificate, submit for reputation, publish the hash | Warning fatigue trains users to click through, which is exactly the habit the product should not teach. |
| Registry and Program Files writes | The installer creates an uninstall entry and a shortcut | Per user NSIS install, minimal keys | The uninstaller is code that runs later with the user's privileges. An attacker who can modify it gets execution at uninstall time. |
| Mark of the Web inheritance | A zip carries `Zone.Identifier`, and extraction propagates it | Prefer the installer, where the user made a deliberate choice | A portable zip user gets two prompts, not one. |
| Defender heuristics on packed installers | A packed, unsigned-at-first installer can look like malware to a heuristic | Sign, and submit false positives | UNVERIFIED. Expect at least one false positive on a new release. |

**Linux.**

| New surface | Detail | Mitigation | Residual |
|---|---|---|---|
| AppImage has no signature at all | The documented run path is `chmod a+x` and execute | Publish the hash and a detached signature, and say the binary is unverified | A replaced AppImage is indistinguishable from a good one without the user checking. |
| FUSE dependency | The app depends on the FUSE stack, and on Arch the docs themselves flag `fusermount` permission problems | Prefer the pacman package where FUSE is not needed for the app's own install | The AppImage's launch path now includes a setuid helper (`fusermount`). That risk is inherited, not created, but the app now requires it. |
| AUR PKGBUILD is executable bash | A user who builds from the AUR runs the PKGBUILD on their machine | Keep the PKGBUILD trivial: one `source=`, one `sha256sums=`, `install -Dm755`, no `curl | bash`, no post install script | Anyone who can edit the AUR package runs code on every user who builds it. This is the sharpest Linux residual after the missing signature. |
| No Secure Boot chain | Omarchy's own install guide says "You must turn off Secure Boot and/or TPM in the BIOS" (`https://omarchy.org/manual/getting-started/`) | None at app level | On that platform there is no boot-time chain of trust, so an offline binary swap is not caught by the firmware. It makes the published hash more important, not less. |

The pattern: the wrapper removes one whole class of attacker (the extension model and the shared browser profile) and adds a smaller but real native surface on each platform. It is a net gain for the class 7 threat and a net loss for the "nothing to install" property. Both belong in the same paragraph of the product copy.

## 9. Recommended packaging design

### 9.1 The decisions, in one table

| Dimension | Decision | Why |
|---|---|---|
| Framework | Electron, pinned to one supported major, upgraded on a quarterly cadence or on a Chromium critical | Section 1.1. Only option that is both self contained and Chromium, with an OS backed integrity chain on two of three platforms. |
| Core embedding | One unmodified HTML file inside `app.asar` | Blueprint owner ruling 3. No build step, and the reviewed bytes are the shipped bytes. |
| Integrity anchor | OS signature, plus the asar fuse pair where supported, plus a compiled in SHA-256 checked before serving | Section 3.2. Named mechanism, and section 3.3 says which layer exists where. |
| Load path | Custom `app://` protocol serving a verified in-memory buffer | No `file://` privileges, no check-then-load window, and the shell can send a real CSP header that a modified core cannot weaken. |
| Renderer posture | `contextIsolation`, `sandbox`, no Node, two IPC verbs, devtools off in release | Section 6.2. |
| Runtime state | In-memory session, disk cache off, per launch `userData` deleted on exit, RAM backed where the OS allows | Section 4. |
| Update | None in app. Manual replacement, hash plus detached signature, build date shown | Section 5. |
| macOS artifact | Two signed, notarized, stapled DMGs, arm64 and x64 | Section 2.1. Separate arch avoids a doubled download. |
| Windows artifact | Signed per user NSIS installer, plus a portable zip | Section 2.2. |
| Linux artifact | pacman package as primary for Arch and Omarchy, AppImage as the portable fallback | Section 2.3, and 5.4 for the update path. |
| Kill authority | Main process menu item, renderer assist, hard destroy after 300 ms | Section 8.2. |

### 9.2 Boot sequence, numbered, EXEC-ONLY

1. `app.requestSingleInstanceLock()`. A second launch focuses the first window, per `13-platform-ux.md` section 3.2. No second instance, no second session surface.
2. Before `ready`: `app.commandLine.appendSwitch('disable-http-cache')`. Switches must be appended before the ready event, which the switch reference states directly.
3. Before `ready`: compute a launch scoped directory, `app.setPath('userData', dir)`. On macOS and Linux prefer a RAM backed location; on Windows use the temp path and delete on exit, and accept that the bytes are on disk while running (section 4.2).
4. Read the core entry from `app.asar` into one `Buffer`. Hash it with `node:crypto`. Compare with the compiled constant using `timingSafeEqual`. On mismatch: native dialog with both hashes, `app.exit(1)`, and never create a window.
5. Register `protocol.handle('app', ...)` returning that same buffer with `Content-Type: text/html; charset=utf-8` and a `Content-Security-Policy` response header. The header is stricter than the core's meta tag at `ephemeral-chat-v1.html:6`, and unlike the meta tag it cannot be dropped by editing the file, because it comes from the response and not from the document.
6. Create exactly one `BrowserWindow` with the section 6.2 settings, `show: false`, then show on `ready-to-show`.
7. `will-navigate` handler denies anything that is not `app://core/`. `setWindowOpenHandler` returns deny. `setPermissionRequestHandler` calls back false for every permission.
8. Attach the application menu from `13-platform-ux.md` section 3.2, with no reload item and no devtools item. Register the two IPC verbs.
9. Load `app://core/index.html`. Nothing else is ever loaded.
10. On `will-quit`, delete the launch scoped `userData` directory. Best effort, and the deletion is not a secure erase. Note that `app.exit()` in the kill path does not emit `will-quit` (the app doc: "All windows will be closed immediately without asking the user, and the `before-quit` and `will-quit` events will not be emitted"), which is why section 9.4 deletes the directory explicitly instead of relying on this handler.

Note on step 5: the core's own CSP still matters for the file mode, and the shell must not weaken it. Adding a header does not relax the meta tag; both apply, and the intersection is what the renderer enforces.

### 9.3 What each file in the shell may do

| File | May do | Must not do |
|---|---|---|
| `main.cjs` | Window, menu, `app://` protocol, the hash check, the kill, `clipboard` clear | `child_process`, `shell.openExternal`, any network call, any `eval`, any string from the renderer reaching `fs` |
| `preload.cjs` | `contextBridge.exposeInMainWorld('shell', ...)` with exactly `wipe()` and `badge(on)` | Expose `ipcRenderer`, expose `require`, expose any event object |
| `app.asar/core/index.html` | The whole app | Anything the core already forbids: no external asset, no `innerHTML`, no `eval` |

That is the entire trusted computing base we wrote: one native file, one bridge file, one HTML file. If a future card wants to add a third IPC verb, it needs a line in this table first.

### 9.4 The kill, in shell terms

| t | Step | Owner |
|---|---|---|
| 0 ms | Renderer runs the `06-ops-defense.md` section 2.5 sequence, sends `{k:'panic'}` best effort | Renderer |
| 300 ms | Hard stop waiting. `win.destroy()` | Main |
| 320 ms | `session.clearStorageData()`, `session.clearCache()` | Main |
| 340 ms | Delete the launch scoped `userData` directory | Main |
| 360 ms | Clear the system clipboard, best effort | Main |
| 380 ms | `app.exit(0)`, which skips `before-quit` handlers by design | Main |

If the menu item starts the kill, the renderer still gets the 300 ms window to close the DTLS connection cleanly and send the panic frame. If it does not answer, the session still dies. That is the improvement over the page-only path, where a hostile renderer can decline to wipe itself.

### 9.5 What the user downloads

| Platform | Artifact | Also published |
|---|---|---|
| macOS arm64 | `ephemeral-<version>-arm64.dmg`, signed, notarized, stapled | `SHA256SUMS`, `SHA256SUMS.minisig` |
| macOS x64 | `ephemeral-<version>-x64.dmg`, same treatment | same |
| Windows x64 | `ephemeral-<version>-setup-x64.exe` (NSIS, per user) and `ephemeral-<version>-portable-x64.zip` | same |
| Arch and Omarchy | `PKGBUILD` in the AUR, plus the source tarball it points at | `sha256sums` inside the `PKGBUILD`, plus the release hash |
| Other Linux x86_64 | `ephemeral-<version>-x86_64.AppImage` | `SHA256SUMS`, `SHA256SUMS.minisig`, and the FUSE requirement on the same page |

One page, one hash file, one signature, one set of commands per OS. No mirrors, no torrents, no "download from our CDN" second path.

### 9.6 Build cards

Each card names its scope, its mode, one gate command, and the failure it catches. Modelled on `13-platform-ux.md` section 5 so the two lists can merge.

| Card | Scope | Mode | Gate | Failure caught |
|---|---|---|---|---|
| PKG-01 Shell skeleton | `main.cjs` window, protocol, navigation denies, permission denies | EXEC-ONLY | `python3 03-build/output/probes/gate.py shell --app <artifact>` | A second window, a reachable `file://` load, an allowed navigation, a granted permission |
| PKG-02 Core pin | Hash constant, buffer read, `timingSafeEqual`, serve verified buffer | EXEC-ONLY | Flip one byte of the core inside the built asar, relaunch, expect exit code 1 and no window | A core that loads despite a hash mismatch, or a check-then-load race |
| PKG-03 Fuses | Six flips from section 6.1 | EXEC-ONLY | `npx @electron/fuses read --app <artifact>` | A fuse left at its unsafe default, including the two that carry the asar integrity chain |
| PKG-04 Runtime posture | In-memory partition, `--disable-http-cache`, `userData` redirect, spellcheck off, crash reporter absent | EXEC-ONLY | Run 60 s, quit, then assert the profile directory is gone and no `persist:` string is in the bundle | A profile that survives the session, or a cache directory that persists |
| PKG-05 macOS signing | Developer ID, hardened runtime, notarize, staple | EXEC-ONLY | `codesign -v --deep --strict <app>` and `spctl -a -vv <app>` and `xcrun stapler validate <dmg>` | An unstapled ticket, a missing entitlement, a nested binary that was not signed |
| PKG-06 Windows signing | Authenticode over installer and exes, first run on a clean VM | EXEC-ONLY | `signtool verify /pa /all <exe>`, plus a recorded first run state | An unsigned nested binary, or a first run that is silently blocked |
| PKG-07 Linux artifacts | `PKGBUILD` with `sha256sums`, AppImage with a documented FUSE fallback | EXEC-ONLY | `makepkg --verifysource`, `pacman -Qip`, `sha256sum -c`, and one run with `--appimage-extract-and-run` | A package that builds from an unpinned source, or an AppImage that only works on a machine with FUSE |
| PKG-08 Kill path | Menu kill, 300 ms deadline, storage clear, profile delete, exit | EXEC-ONLY | Kill during a live session, then assert exit within 1 s and no surviving child process | A kill that waits on the renderer forever, or a profile left behind |

### 9.7 Deliberately not built

Each of these is a small convenience that would restore a surface this design spent its budget removing.

- No auto-updater, no update check, no version ping. Section 5.
- No crash reporter, local or remote. `13-platform-ux.md` section 3.6.
- No telemetry, no usage counters, no first run analytics.
- No `ephemeral://` protocol handler or deep link. A URL that opens the app is attacker controlled input, and `03-threat-model.md` class 4 already shows what one query parameter did in V1 (`02-audit-findings.md` F-10).
- No tray icon, no dock menu beyond the standard one, no login item, no autostart.
- No file association, no printing, no "reveal in Finder" or "open folder".
- No second window, no tab, no address bar, no reload accelerator.
- No extension support and no plugin directory.
- No settings file. Every setting in this file is fixed or derived from the OS.

## 10. Build matrix

One row per artifact. No cross compilation: each artifact is built and gated on its own OS, because signing and first run behavior cannot be verified from another platform.

| # | Target | Runner | Artifact | Arch | Signing | Integrity layers present | Gate |
|---|---|---|---|---|---|---|---|
| 1 | macOS arm64 | macOS arm64 runner | `.dmg` containing the `.app` | arm64 | Developer ID Application, hardened runtime, notarized, stapled | 1, 2, 3 | PKG-05, PKG-03, PKG-02 |
| 2 | macOS x64 | macOS x64 runner | `.dmg` containing the `.app` | x86_64 | same | 1, 2, 3 | PKG-05, PKG-03, PKG-02 |
| 3 | Windows x64 | Windows runner | NSIS `.exe` and portable `.zip` | x86_64 | Authenticode, cloud signing service | 1, 2, 3 | PKG-06, PKG-03, PKG-02 |
| 4 | Windows arm64, optional | Windows runner | NSIS `.exe` | arm64 | same | 1, 2, 3 | PKG-06. Runner support for arm64 Electron builds is UNVERIFIED here. |
| 5 | Arch and Omarchy | Arch container (`archlinux:latest`) with `base-devel` | `pkg.tar.zst` plus the `PKGBUILD` | x86_64 | pacman PGP for a repo package, `sha256sums` for the AUR | 3, 4. Layer 2 is absent on Linux. | PKG-07, PKG-02 |
| 6 | Other Linux x86_64 | Linux runner | `.AppImage` | x86_64 | Detached signature over the artifact, no OS check | 3 only | PKG-07, PKG-02 |

Two matrix rules, both learned the hard way in other projects and worth writing down before the first release.

1. **The hash constant is build input, not build output.** If the build computes the core hash and writes it into `main.cjs` after packaging the core, then the hash is self referential and proves nothing. Order: build the core, hash it, commit the constant, then build the shell. The gate in PKG-02 is what catches a violation.
2. **The macOS and Windows artifacts must be built on the same commit as the Linux ones, or the hashes will not match the published `SHA256SUMS`.** One pipeline, six artifacts, one manifest, generated at the end from the artifacts themselves.

## 11. Sources

All fetched in this pass, titles as returned. Where a title contained a dash character it is rendered here without it, and the URL is authoritative.

| # | Source | Title | What it supports |
|---|---|---|---|
| 1 | https://www.electronjs.org/docs/latest/tutorial/fuses | Electron Fuses \| Electron | The fuse list, their defaults, what each disables, and the package time plus OS signature argument |
| 2 | https://www.electronjs.org/docs/latest/tutorial/security | Security \| Electron | contextIsolation, sandbox, nodeIntegration defaults, the 20 item checklist, the `file://` warning |
| 3 | https://www.electronjs.org/docs/latest/tutorial/asar-integrity | ASAR Integrity \| Electron | The asar hash mechanism, the platform support matrix (macOS 16, Windows 30), the header hash location |
| 4 | https://www.electronjs.org/docs/latest/api/session | session \| Electron | In-memory session with no `persist:` prefix, the cache option |
| 5 | https://www.electronjs.org/docs/latest/api/app | app \| Electron | `getPath` and `setPath`, the default `userData` locations per OS, single instance lock |
| 6 | https://www.electronjs.org/docs/latest/api/command-line-switches | Supported Command Line Switches \| Electron | `--disable-http-cache`, `--disk-cache-size`, and the append before ready rule |
| 7 | https://www.electronjs.org/docs/latest/tutorial/code-signing | Code Signing \| Electron | macOS signing and notarization requirements, the Windows cloud signing recommendation, the `electron-wix-msi` path |
| 8 | https://www.electronjs.org/docs/latest/tutorial/electron-timelines | Electron Release Timelines | Referenced by the security page as the release cadence document. Not fetched separately. |
| 9 | https://v2.tauri.app/reference/webview-versions/ | Webview Versions | WKWebView, WebView2, WebKitGTK, and the statement that unsupported macOS versions get no WebKit updates |
| 10 | https://v2.tauri.app/start/prerequisites/ | Prerequisites | The Linux system dependency list including `libwebkit2gtk-4.1-dev` |
| 11 | https://neutralino.js.org/docs/ | Introduction \| Neutralinojs | No bundled Chromium, system webview, embedded static web server and WebSocket bridge |
| 12 | https://appimage.org/ | AppImage | One app one file, no installation, no root, the `chmod a+x` run path |
| 13 | https://docs.appimage.org/user-guide/troubleshooting/fuse.html | I get some errors related to something called "FUSE" | FUSE requirement, `fuse2` on Arch, `libfuse2` and `libfuse2t64` elsewhere, `--appimage-extract-and-run` and its cost |
| 14 | https://github.com/chromiumembedded/cef | GitHub - chromiumembedded/cef | What CEF is, binary distributions, the embedding use case |
| 15 | https://github.com/Elanis/web-to-desktop-framework-comparison | GitHub - Elanis/web-to-desktop-framework-comparison | Measured build size, memory and startup for Electron, Tauri, Neutralino and others, with its own accuracy caveat |
| 16 | https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution | Notarizing macOS software before distribution | Developer ID requirement, hardened runtime requirement, staple and ticket, accepted deliverable types |
| 17 | https://developer.apple.com/documentation/security/hardened-runtime | Hardened Runtime | The JIT restriction and the entitlement that lifts it |
| 18 | https://support.apple.com/en-us/102445 | Safely open apps on your Mac | Gatekeeper behavior, notarization required on Catalina and later, the failure dialogs, Apple's privacy statement about the checks |
| 19 | https://developer.apple.com/library/archive/documentation/CoreFoundation/Conceptual/CFBundles/BundleTypes/BundleTypes.html | Bundle Structures | What a `.app` bundle must contain |
| 20 | https://learn.microsoft.com/en-us/windows/security/operating-system-security/virus-and-threat-protection/microsoft-defender-smartscreen/ | Microsoft Defender SmartScreen | Reputation based checks, certificate reputation, the no reputation warning |
| 21 | https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-fscc/6e3f7352-d11c-4d76-8c39-2516a9df36e8 | [MS-FSCC]: Zone.Identifier Stream Name | Mark of the Web as an NTFS alternate data stream with `ZoneId=3` |
| 22 | https://learn.microsoft.com/en-us/windows/msix/overview | What is MSIX? - MSIX | Package identity, clean uninstall, containerized execution, differential updates |
| 23 | https://www.electron.build/docs/nsis/ | NSIS \| electron-builder | NSIS as the default Windows target and its behavior |
| 24 | https://manpages.debian.org/bookworm/chromium/chromium.1.en.html | chromium(1), chromium, Debian bookworm | `--user-data-dir` semantics and the statement that hundreds of Chromium flags are undocumented |
| 25 | https://mrd0x.com/phishing-with-chromium-application-mode/ | Security Research \| mr.d0x | What the undocumented `--app` flag actually does |
| 26 | https://wiki.archlinux.org/title/PKGBUILD | PKGBUILD - ArchWiki | What a PKGBUILD is, `makepkg`, the output package, `sha256sums` |
| 27 | https://wiki.archlinux.org/title/Arch_User_Repository | Arch User Repository | AUR as community content, the unvetted warning, the build and install flow |
| 28 | https://wiki.archlinux.org/title/Pacman/Package_signing | pacman/Package signing | OpenPGP web of trust, `SigLevel`, the local build caveat |
| 29 | https://omarchy.org/manual/other-packages/ | Other Packages - Omarchy Manual | Omarchy uses the Arch repos and the AUR, `omarchy pkg add` |
| 30 | https://omarchy.org/manual/getting-started/ | Getting Started - Omarchy Manual | Omarchy is Arch based in practice, and its install requires Secure Boot and TPM off |
| 31 | https://nodejs.org/api/crypto.html | Crypto \| Node.js v26.13.1 Documentation | The hash primitives used for the core SHA-256 check |

Local evidence, not external sources: the `shasum -a 256` of the core and the four `Content-Length` measurements, both run in this pass on this host on 2026-11-26.

## SELF-CHECK

Re-read the file end to end after the last edit and ran the checks below. Results are from the commands quoted, not from memory.

### Lane acceptance

| # | Acceptance item | Result | Evidence |
|---|---|---|---|
| 1 | Every option carries a source URL | PASS | Section 1.1 Electron (electronjs.org fuses and security), 1.2 CEF (github.com/chromiumembedded/cef), 1.3 Chrome app mode (manpages.debian.org chromium(1) and mrd0x), 1.4 Tauri (v2.tauri.app webview versions and prerequisites), 1.5 Neutralino (neutralino.js.org). The matrix in 1.6 names the same sources. |
| 2 | All three platforms covered | PASS | macOS in 2.1, Windows in 2.2, Linux and Omarchy in 2.3, plus the per platform tables in 3.3, 4.2, 7.1, 8.3, and the six row build matrix in section 10. |
| 3 | The embedded core pinning mechanism is named | PASS | 3.2: `EnableEmbeddedAsarIntegrityValidation` plus `OnlyLoadAppFromAsar`, asar header hash stored in `Info.plist` (`ElectronAsarIntegrity`) or the Windows `Integrity` resource `ElectronAsar`, plus a compiled in SHA-256 of the core compared at launch and the verified buffer served over `app://`. |
| 4 | A SHA-256 check at launch closes the supply chain finding from 03-threat-model.md | PASS with stated limits | 3.2 layer 3 gives the five step order, including serving the same verified buffer to remove the check and load race. 3.4 names what it closes (class 9, swapped HTML inside a genuine installer) and the three limits (self reporting shell, no layer 2 on Linux, no detached signature). |
| 5 | In memory user data directory, cache disabled, no history surface | PASS | 4.1: in memory partition with no `persist:` prefix, `--disable-http-cache`, per launch `userData` with `app.setPath`. 4.2 states where the claim does not fully hold, which is Windows. |
| 6 | Document per platform what the process still writes to disk versus RAM | PASS | 4.2 is a 14 row table with platform, artifact, writer, and whether the shell can stop it. The RAM only list follows it. |
| 7 | The update problem, with manual replacement plus hash verification as the minimum | PASS | 5.1 no updater, 5.2 the cost including stale engine CVEs, 5.3 the four manual steps per platform with commands, 5.4 the pacman exception, 5.5 what a signed channel would require. |
| 8 | Electron fuses and hardening flags, with sources | PASS | 6.1 is a nine row fuse table with a source column and the CI readback command. 6.2 is a thirteen row window and session table. |
| 9 | Honest bundle size and memory per platform with sources | PASS | 7.1: four measured `Content-Length` values with the exact `curl` method, four quoted installed sizes, four quoted memory figures, and the benchmark's own accuracy caveat. 7.2 refuses the weak defenses. |
| 10 | What the shell ADDS: monitorable native process, cleaner kill scope, new attack surface | PASS | 8.1 the per process attribution the browser could not give, plus signature and version checks. 8.2 a seven row before and after table plus three kill rules. 8.3 five common, four macOS, four Windows and four Linux new surfaces, each with residual. |
| 11 | Ends with the recommended packaging design, a build matrix for the three platforms, and EXEC-ONLY labels | PASS | Section 9 has the decision table, the ten step boot sequence, the file permission table, the kill timeline, the download list, eight build cards and the not built list. Section 10 is the six row build matrix. EXEC-ONLY appears 19 times. |
| 12 | English, no em dashes or en dashes anywhere | PASS | Code point scan of the file: em 0, en 0, horizontal bar 0, minus sign 0, figure dash 0. Non ASCII characters in the file: none at all. |
| 13 | Read only mission, one output file | PASS | `ls -lT` shows `11-packaging-executable.md` at 23:42 as the only file written by this lane. No file under `input/`, `02-plan/` or `_config/` was touched. |
| 14 | File ends with a SELF-CHECK | PASS | This section is the last thing in the file. |

### Mechanical evidence, verbatim

```
wc -l 11-packaging-executable.md           -> 746 (about 95 KiB)
grep -rl $'\xe2\x80\x94' .                 -> no output, exit=1
grep -rl $'\xe2\x80\x93' .                 -> no output, exit=1
code point scan (em, en, bar, minus)       -> 0 0 0 0
non ascii characters in file               -> {} (none)
'## ' section count                        -> 13
EXEC-ONLY occurrences                      -> 19
https:// occurrences                      -> 76
table row count                            -> 211
numbered source rows                       -> 31
last characters of the file                -> "...the file is complete rather than partial."
shasum -a 256 input/ephemeral-chat-v1.html -> 23be3a0b6f53587e50c97c1767fa745980788288145dc79d3dba42095b150337
electron-v45.5.0-darwin-arm64.zip          -> 120872990
electron-v45.5.0-darwin-x64.zip            -> 125153068
electron-v45.5.0-win32-x64.zip             -> 158528093
electron-v45.5.0-linux-x64.zip             -> 123890853
ls 01-research/output/*.md | wc -l         -> 14 (file 15 belongs to another lane and had not landed)
```

### Claim discipline

| Claim type | How it is handled |
|---|---|
| External facts | Every one carries a URL in the sentence or in the source column. Section 11 lists 31 sources, all fetched in this pass except item 8, which is marked as a pointer only. |
| Numbers | Measured numbers say MEASURED with the command. Benchmark numbers say QUOTED with the repository named and its own accuracy warning repeated. The only INFERRED number is the CEF size band and the 0.013 percent ratio, both labelled. |
| App claims | Cite `ephemeral-chat-v1.html:6` for the CSP, and cite the research files by path and section for everything else. |
| Unverifiable items | Marked UNVERIFIED at the point of use: CEF size, macOS local network TCC prompt, Windows arm64 runner support, Defender false positive expectation, AppImage mount permissions, the exact CA/Browser Forum signing requirement text. |

### Known limits of this deliverable

- No build was run. The boot sequence, fuses and kill timeline are specified, not exercised. The gate cards in 9.6 are where they become testable, and every one of them is EXEC-ONLY because there is no shell yet.
- CEF has no measured size in this file. The comparison in 1.2 is an argument from "it embeds the same Chromium", which is true but is not a measurement.
- The Tauri rejection rests on engine identity and version control, both quoted from Tauri's own documentation. I did not test whether the core's WebCrypto suite negotiation actually degrades on WebKitGTK. That is a real open question and it is the first thing to measure if anyone reopens the framework choice.
- The memory figures are third party CI numbers for an empty app. They will be higher for this app once a 50 MiB file transfer is in flight, because the ciphertext and plaintext both live in memory at peak (`02-plan/output/blueprint-v2.md` section 2.3 puts that at 100 to 150 MB for one 50 MiB file).
- The macOS `userData` on a RAM disk idea is described, not measured. `hdiutil` RAM disks need a size, a mount, and a cleanup path, and none of that is priced here.
- The Windows "no user mode RAM disk" statement is a design conclusion from the absence of such an API in the platform documentation I read. It is not a proof that no third party driver offers one.

STATUS: complete. All 14 lane acceptance items PASS. Tool time ran to roughly 30 minutes of wall clock including the source fetches and the writes, slightly past the 25 minute guidance in the brief, and the file is complete rather than partial.




