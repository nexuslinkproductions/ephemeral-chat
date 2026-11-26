# 10 Methodology sources for authored pen-test skills

RUN ID: w3-ephemeral-skills-20261126
LANE: methodology sources, W3 skills expansion
TARGET: /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/input/ephemeral-chat-v1.html (V1, 35598 bytes)
STATUS: complete
DATE: 2026-11-26

Scope: sources that are not distributed as Hermes skills but encode a procedure or a body of knowledge that an authored skill can enforce. The companion lanes cover registry skills. This file covers the methodology lane only. It does not re-enumerate the installed library, which 07-skill-sweep.md already does.

## 1. Method and verdict key

Work done in this session:

- Read 07-skill-sweep.md, especially section 5 (Library gaps) and section 6 (round plan), and used the five rounds R1 to R5 as the fit target.
- Fetched every source URL below with `web_extract` in this session. The page title and at least one body sentence were read before the card was written. No URL in this file is from memory.
- Ran `hermes skills search` read-only for pentestgpt, webrtc, ddos, zeroiz, burp, nuclei and atomic red. No install, uninstall, update, audit or publish was run.
- Re-checked every app line number cited here with `grep -n` against the V1 file.
- Checked the local macOS tools named in card 6 with `command -v` and `man`.

Registry check result, evidence only: the hub has no skill that packages PentestGPT, Atomic Red Team, RFC 8827 or the NIST sanitization guidance. Searches returned product wrappers and unrelated items, for example `agentic-pentest` (skills.sh, 7 installs) for pentestgpt, `Alibabacloud Ddos Native` for ddos, `zeroize-audit` (skills.sh, Trail of Bits) for zeroiz, and `Nuclei Analysis` for nuclei. Listings were not inspected further because they are outside this lane.

Verdict vocabulary, fixed by the brief:

| Verdict | Meaning here |
|---|---|
| install candidate | A native Hermes skill exists and is safe to install. None in this file, because none of these sources ships as a Hermes skill. |
| adapt into an authored skill | The source encodes a procedure worth writing as a project skill, with named changes. |
| reference only | Useful as background or as a tool to run manually, but it does not justify its own skill. |

Fit is graded against the R3 probe list and the V1 surfaces, not against web apps in general. Effort is S (under an hour), M (half a day), L (a day or more) for one author writing one skill plus its check.

App surfaces used repeatedly, all verified in this session:

| Surface | Line | Why it matters |
|---|---|---|
| CSP meta tag | 6 | `script-src 'unsafe-inline'`, `connect-src 'none'` |
| Idle override | 431 to 441 | `?idle=` minimum 5 seconds |
| Invite pack | 723 | Compressed SDP code |
| Invite unpack | 732 to 740 | Prefix parse, then gzip `DecompressionStream` |
| Data channel | 755 | One ordered SCTP channel named `chat` |
| Idle timer | 1136 | `setInterval(checkIdle, ...)` |

The result is summarized in one table. The cards below carry the evidence and the detail.

| # | Source | What it mainly contributes | Fit | Effort | Verdict |
|---|---|---|---|---|---|
| 1 | hackingBuddyGPT | probe loop with ground truth success predicates | medium | M | adapt into an authored skill |
| 2 | PentestGPT | durable task tree for a multi-branch test | medium | S to M | adapt into an authored skill |
| 3 | MITRE ATT&CK | coverage vocabulary and a fixed denominator | high | S | adapt into an authored skill |
| 4 | Atomic Red Team | test as data with observable and cleanup | high | M | adapt into an authored skill |
| 5 | DoS for owned infrastructure | load plan, abort thresholds, recovery assertion | high | M | adapt into an authored skill |
| 6 | Zeroization on macOS | four level wipe matrix with artifacts | high | M to L | adapt into an authored skill |
| 7 | WebRTC and DTLS | fingerprint binding proof | high | M | adapt into an authored skill |
| 8 | Burp Suite | DOM sink inventory only | low | none | reference only |
| 9 | OWASP ZAP | passive baseline plan, reproducibility | low | S | reference only |
| 10 | nuclei | declarative matcher pattern, absorbed by card 4 | low | none | reference only |
| 11 | nmap | host surface and listener check | medium | S | adapt into an authored skill |
| 12 | Memory forensics | bounded memory claims, Volatility limits | low | S | reference only |

## 2. Cards 1 to 4: agent frameworks and ATT&CK

### Card 1. hackingBuddyGPT

SOURCE: https://github.com/ipa-lab/hackingBuddyGPT
PAPER: https://arxiv.org/abs/2308.00121 (Happe and Cito, "Getting pwn'd by AI: Penetration Testing with Large Language Models", v3, 17 Aug 2023)
VERIFIED: repository page fetched 2026-11-26, title "Helping Ethical Hackers use LLMs in 50 Lines of Code or less", MIT license, 1,339 stars, created 2023-08-02. Paper abstract read on arXiv.

What it encodes:

- A closed feedback loop: the model proposes one low level action, the action runs against a target, the output is parsed, and the parsed state feeds the next prompt. The paper describes this loop over SSH against a vulnerable virtual machine, plus a separate high level task planning use case.
- Use cases shipped in the README: `MinimalPrivEscLinux` (about 20 lines, templates the whole history into one prompt each round and parses a bare command from the reply), `PrivEscWindows`, and Web API testing.
- Ground truth success detection. The README lists "Ground-truth-verified success detection for privilege escalation (a claimed got root is checked against real command output)".
- A standing safety rule in the README: "Never run this against real production systems."

Why it matters here: this is the cleanest published statement of the failure mode that hurts an LLM red team most, which is accepting the agent's own claim that an attack worked. The app has no shell, so the loop transfers as a probe harness, not as a privilege escalation tool.

Gate an authored skill would enforce: every R3 attempt must end in a machine-evaluated predicate over app state, never in prose. A finding reaches L3 only when the predicate returns true and the raw artifact is attached. Concrete predicates for this app: transcript child count, `performance.memory.usedJSHeapSize` delta, a DevTools heap snapshot containing a canary string, a `RTCPeerConnection.connectionState` value, or the byte length of a reassembled file. The skill also refuses any probe aimed at a host outside the two owned loopback contexts.

Adaptation: M. The loop is simple; the work is defining one predicate per attack class and pinning it to an artifact, which is the same work R3 needs anyway.

Verdict: adapt into an authored skill. Fit: medium. The tool itself is irrelevant to a browser page, the verification discipline is not.

### Card 2. PentestGPT

SOURCE: https://github.com/GreyDGL/PentestGPT
PAPER: https://arxiv.org/abs/2308.06782 (Deng et al., "PentestGPT: An LLM-empowered Automatic Penetration Testing Tool", v2, 2 Jun 2024)
VERIFIED: repository page fetched 2026-11-26, title "Automated Penetration Testing Agentic Framework Powered by Large Language Models", MIT, 16,536 stars, created 2023-02-27. Paper abstract read.

What it encodes:

- The paper's diagnosis: LLMs are good at local sub-tasks (using a tool, reading output, proposing the next action) and bad at holding the whole engagement in context. PentestGPT answers that with three self-interacting modules, one per sub-task, to limit context loss.
- The current README preserves the paper design as `pentestgpt-legacy`, which "runs three cooperating LLM sessions, reasoning / generation / parsing, that maintain a Pentesting Task Tree (PTT)" while the human drives with `next`, `more`, `todo` and `discuss`.
- The task tree is the durable artifact. It records what has been tried, what is blocked, and what remains, outside the model context.

Why it matters here: R3 has ten attack classes and will run across several sessions. The stated gate failure mode in 07-skill-sweep is "a red team that reports no issues without listing what it tried", which is exactly the context loss PentestGPT names.

Gate an authored skill would enforce: R3 must keep `engagement/task-tree.yaml` with one node per attack branch, and every node carries `id`, `class`, `surface`, `state` in open, blocked, confirmed or excluded, plus a probe id when state is confirmed. The round cannot close while any node is open, and a "no findings" report must still show every leaf visited or excluded with a reason. A checker script fails the round if a node lacks a probe id or an exclusion reason.

Adaptation: S to M. It is a YAML schema plus a small validator; the hard part is agreeing the initial tree, which R3 already enumerates.

Verdict: adapt into an authored skill. Fit: medium. The PTT is process, not tooling, so it survives the jump from a shell target to a single page.

### Card 3. MITRE ATT&CK

SOURCE: https://attack.mitre.org/
TECHNIQUES VERIFIED: T1071 https://attack.mitre.org/techniques/T1071/ , T1499 https://attack.mitre.org/techniques/T1499/ , T1557 https://attack.mitre.org/techniques/T1557/ , T1070 https://attack.mitre.org/techniques/T1070/ , T1539 https://attack.mitre.org/techniques/T1539/ , T1185 https://attack.mitre.org/techniques/T1185/
VERIFIED: all six pages fetched 2026-11-26. The matrix page lists 15 tactics including Stealth (TA0005) and Defense Impairment (TA0112). T1070 lists macOS as a platform and was last modified 12 May 2026.

What it encodes:

- A shared vocabulary of adversary tactics and techniques with procedure examples and platform tags. It is a coverage checklist, not an execution guide.
- The tactics that survive translation to this product: Initial Access, Stealth, Credential Access (only as a non-applicable check), Discovery, Collection, Command and Control, Impact.
- Technique pages that name the exact behaviours this app must resist or acknowledge:
  - T1557 Adversary-in-the-Middle. Pairing code substitution is an AiTM shape, no network position required.
  - T1071 Application Layer Protocol. A WebRTC data channel carrying arbitrary frames is a textbook application layer channel, so the app's own transport is also an attacker's transport.
  - T1499 Endpoint Denial of Service. Chunk and frame flood against one peer.
  - T1070 Indicator Removal. The app claims minimal local trace, so this is the attacker checklist the claim must survive.
  - T1539 Steal Web Session Cookie. Expected non-applicable, because there are no cookies, and the model must say so rather than silently omit it.
  - T1185 Browser Session Hijacking. Second tab, paused peer, or another local context that survives a wipe.

Why it matters here: the app is small enough that an unstructured test list will look complete while missing whole tactic classes. ATT&CK gives a fixed denominator.

Gate an authored skill would enforce: `engagement/attack-coverage.md` with one row per applicable technique, each row carrying either an attempt id or an exclusion reason. The gate condition is that the applicable set is declared before R3 starts, every row is filled, and no technique is dropped without a written reason. A row that says "not applicable" without naming the missing precondition (no cookies, no server, no persistent storage) fails review.

Adaptation: S. A table, a declared set, and a grep check. The value is in the pre-declaration, which stops post hoc cherry picking.

Verdict: adapt into an authored skill. Fit: high as a completeness frame, low as an execution method.

### Card 4. Atomic Red Team

SOURCE: https://github.com/redcanaryco/atomic-red-team
VERIFIED: repository page fetched 2026-11-26, title "Small and highly portable detection tests based on MITRE's ATT&CK", MIT, 12,892 stars, badge shows 1,950 atomics, `atomics/` directory present. The README points at Invoke-AtomicRedTeam for orchestration.

What it encodes:

- A test library where each atomic test is data, not prose. Tests live under `atomics/T####/T####.md` with YAML blocks that name the technique, the test name, the executor, the command, and the cleanup.
- Portability and reproducibility as first class properties: the same test runs on a fresh machine, and the expected observable is part of the test, not part of the analyst's memory.
- The detection pairing. An atomic without an observable is half a test. This is the same rule as cyber-detect-respond's "prove the detector, not just the defect".

Why it matters here: R3 currently produces a findings ledger, which is a record after the fact. Atomic produces a suite that can be rerun after every hunk, which is what R5 needs when it re-proves the six invariants on the final file hash.

Gate an authored skill would enforce: every attack probe is a YAML atom under `engagement/atomics/`, with required fields `id`, `technique`, `surface`, `executor` (one of playwright, cdp or node), `steps`, `expected_observable`, `cleanup`, `level_if_hit`. Schema validation fails the round when `expected_observable` or `cleanup` is missing. Cleanup is not optional here: a probe that leaves a second tab or a paused peer alive invalidates the next probe.

Adaptation: M. The schema is small; the runner over Playwright or CDP is the work, and it is reusable for all ten R3 classes.

Verdict: adapt into an authored skill. Fit: high. This is the single best structural import in the file.

## 3. Cards 5 to 8: denial of service, wipe, transport, intercepting proxy

### Card 5. Denial of service methodology for owned infrastructure

SOURCES:
- OWASP Denial of Service Cheat Sheet, https://cheatsheetseries.owasp.org/cheatsheets/Denial_of_Service_Cheat_Sheet.html
- RFC 4732, Internet Denial-of-Service Considerations, https://www.rfc-editor.org/rfc/rfc4732.html
- NIST SP 800-115, Technical Guide to Information Security Testing and Assessment, https://csrc.nist.gov/pubs/sp/800/115/final
- Grafana k6 load test types, https://grafana.com/docs/k6/latest/testing-guides/test-types/

VERIFIED: all four pages fetched 2026-11-26. OWASP page body names a methodology for handling DoS "on different layers" and asks for an inventory of components by functionality, architecture and performance, including single points of failure. RFC 4732 table of contents confirms sections on end-system DoS, application resource exhaustion, operating system resource exhaustion, attacks on ongoing communications, and attacks using the victim's own resources. k6 page confirms smoke, average-load, stress, soak, spike and breakpoint types, and states "Stick to simple load patterns. For all test types, directions is enough: ramp-up, plateau, ramp-down." NIST SP 800-115 page confirms its purpose is planning and conducting technical security tests, analyzing findings and developing mitigations.

What it encodes:

- A layered model. DoS is not one attack, it is resource exhaustion at the network, transport, application or host layer. The first step is an inventory of components and single points of failure, not a tool invocation.
- RFC 4732 adds the categories that matter for a peer to peer app: application resource exhaustion, attacks on ongoing communications, and attacks that consume the victim's own resources. Amplification and reflection are network layer concerns, and this app has no server to reflect off.
- k6 supplies the test shape: smoke first, then average, stress, soak, spike or breakpoint depending on the risk, always with a ramp-up, a plateau and a ramp-down, never a rollercoaster.
- NIST SP 800-115 supplies the engagement frame: plan the test, define what is in scope, run it, analyze findings, write mitigations.

Why it matters here: the app has no server, so a borrowed DDoS playbook would aim at the wrong target. The real DoS surfaces are all local to the receiving peer: the data channel message handler, the chunk reassembler with its 50 MB cap, the rekey path, and the browser process itself. The public STUN server at lines 443 to 444 is a third party and must never be a target.

Gate an authored skill would enforce: `engagement/load-plan.md` is required before any flood probe runs, and it must contain:

1. A scope line naming only `127.0.0.1`, two owned Chromium contexts and the owned static server. Any hostname or public IP in the scope line fails the gate.
2. A ramp profile with explicit stage durations, for example 1, 4, 16, 64 frames per second, 30 seconds per stage, plateau 60 seconds, ramp down. Proposed defaults, to be tuned in R3, not sourced values.
3. Abort thresholds declared before the run. Proposed: stop if the tab is unresponsive for 2 seconds, if `performance.memory.usedJSHeapSize` grows by more than 200 MB over baseline, or if any probe packet appears on a non-loopback interface in `lsof`.
4. A recovery assertion after ramp-down: ordered delivery resumes, the idle wipe still fires at `?idle=5` (line 431 to 441), and the monitor overlay shows the drop counter rather than a green state.
5. A statement that the test measures peer resource exhaustion, not network DDoS, and that the public STUN server is out of scope.

Adaptation: M. The plan is prose plus a runner. The runner can reuse the Atomic Red Team executor from card 4, which avoids a second harness.

Verdict: adapt into an authored skill. Fit: high. 07-skill-sweep recorded zero library coverage for DoS, and this is the round the owner explicitly named.

### Card 6. Anti-forensics and zeroization verification on macOS

SOURCES:
- NIST SP 800-88 Rev. 2, Guidelines for Media Sanitization, https://csrc.nist.gov/pubs/sp/800/88/r2/final
- Apple Platform Security, Data Protection overview, https://support.apple.com/guide/security/data-protection-overview-secf6276da8a/web
- CWE-226, Sensitive Information in Resource Not Removed Before Reuse, https://cwe.mitre.org/data/definitions/226.html
- Chrome DevTools Memory panel, https://developer.chrome.com/docs/devtools/memory
- W3C Web Cryptography Level 2, https://www.w3.org/TR/webcrypto/
- Local macOS manual pages for `log`, `fs_usage`, `lsof`, `vmmap`, `heap`, all present at /usr/bin or /usr/sbin and checked with `command -v` in this session

VERIFIED: NIST SP 800-88 Rev. 1 landing page is marked "Withdrawn"; Rev. 2 exists and is titled "Guidelines for Media Sanitization", fetched 2026-11-26. Apple page fetched and states that on a Mac with macOS 26.4 or later, FileVault is on by default and the key hierarchy is entangled with the user password. CWE-226 page fetched, current version 5.0. WebCrypto spec fetched, it defines `CryptoKey` with internal slots including `[[extractable]]`, `[[handle]]` and `[[usages]]`. DevTools Memory page fetched, it names heap snapshot, allocation instrumentation on timeline, allocation sampling and detached elements.

What it encodes:

- NIST SP 800-88 is the reference for media sanitization levels and for verifying the sanitization action (landing page verified, body not read in this session). It is written for media, not for a process heap, which is exactly the distinction a good skill must keep.
- Apple Data Protection explains why at-rest sanitization on macOS is mostly a key destruction problem: file data is encrypted, and dropping the class key makes the ciphertext unrecoverable. That logic applies to files the page writes, not to memory the page holds.
- CWE-226 names the defect class: sensitive information left in a resource before it is released or reused. It is the right weakness ID for a transcript buffer or key buffer that survives a wipe.
- The WebCrypto spec makes the page's real control surface explicit. A `CryptoKey` is an opaque handle with a `[[handle]]` slot, and raw key material may not be exportable when `extractable` is false. The page can drop references and can overwrite its own `ArrayBuffer` views. It cannot command the browser to scrub the key store.
- DevTools heap snapshot is the only practical way to see retained JS objects after a wipe. It sees the JS heap, not the whole renderer, and it does not see memory the browser has already paged out.

Why it matters here: the product claim is "messages and files live only in this tab" (line 361) and the wipe at lines 1076 to 1079 currently clears DOM and peer state. The R3 probe list asks for wipe and zeroization completeness. A skill that promises more than the platform allows would manufacture false assurance, which is worse than no skill.

Gate an authored skill would enforce: a four level wipe matrix, all four required, each with an artifact:

1. Buffer overwrite. For every secret held in a `Uint8Array`, fill it with zeros on wipe and prove it with a canary: write a unique 32 byte canary, wipe, then assert every byte is zero. If a secret is held in a JS string, the skill fails the claim instead of testing it, because strings are immutable and cannot be overwritten. The fix is to move the secret to a typed array or to a non-exportable `CryptoKey`.
2. Key handle drop. After wipe, no reachable `CryptoKey` for the old epoch, and `crypto.subtle.exportKey` on any saved handle throws rather than returning bytes. The test asserts the exception name, not just that it failed.
3. Heap residue. Take a DevTools heap snapshot after wipe, filter for the canary string and for the base64 of the old key, and require zero retained objects. Mark this as a heuristic in the report, because the snapshot is JS heap only.
4. Host trace. During a full session, `fs_usage -w -f filesys` shows no write inside the app directory except the file the user explicitly saved, `log show --last 10m --predicate 'process == "Google Chrome"'` contains no transcript text and no pairing code, and `lsof -p <renderer pid>` shows no open handle to a transcript file. The claim is narrowed to "no new persistent artifact observed in these three channels", not "no forensic trace exists".

The skill must also reject borrowed language. "Purge" and "cryptographic erase" are media sanitization terms from SP 800-88 and do not describe a JS heap wipe. A report that uses them for page memory fails review.

Adaptation: M to L. The probes are small; the honest wording and the four artifacts are the work.

Verdict: adapt into an authored skill. Fit: high. 07-skill-sweep found zero library coverage for zeroization, and this is the product's central claim.

### Card 7. WebRTC and DTLS security testing

SOURCES:
- RFC 8827, WebRTC Security Architecture, https://www.rfc-editor.org/rfc/rfc8827.html
- RFC 4572, Connection-Oriented Media Transport over TLS in SDP, https://www.rfc-editor.org/rfc/rfc4572.html
- MDN `RTCDtlsTransport.getRemoteCertificates()`, https://developer.mozilla.org/en-US/docs/Web/API/RTCDtlsTransport/getRemoteCertificates
- MDN `RTCCertificate.getFingerprints()`, https://developer.mozilla.org/en-US/docs/Web/API/RTCCertificate/getFingerprints

VERIFIED: all four fetched 2026-11-26. RFC 4572 abstract states it defines the SDP `fingerprint` attribute that identifies the certificate presented for the TLS session, and that the mechanism is secure "so long as the integrity of session descriptions is assured". MDN `getRemoteCertificates` states the browser verifies that the certificate presented by the remote peer matches the fingerprint in the negotiated SDP, returns DER encoded X.509 certificates, and is Baseline 2026, newly available since July 2026. MDN `getFingerprints` returns algorithm and hex value pairs, format defined by RFC 4572 section 5, Baseline 2025.

What it encodes:

- The WebRTC identity model is fingerprint binding, not PKI. The SDP carries `a=fingerprint`, and DTLS succeeds only if the presented certificate matches that value. The security of the whole channel therefore rests on the integrity of the signalling channel that carried the SDP.
- RFC 8827 is the architectural statement of that dependency, including the identity provider option that this app does not use.
- The two MDN APIs make the binding testable from inside the page: `getRemoteCertificates()` gives the DER chain after `connected`, and `getFingerprints()` gives the local fingerprint to display or compare.

Why it matters here: pairing is a manual code exchange, which is a signalling channel with no integrity protection at all (lines 723 and 732 compress and decompress SDP, with no signature). 07-skill-sweep already names the Elephant: the DTLS fingerprint is never shown to the user for comparison. That means the MITM is not breaking DTLS, it is replacing the code before it is pasted, and the app has no way to notice.

Gate an authored skill would enforce: a fingerprint binding proof with three parts.

1. Decode the pasted reply code, extract the `a=fingerprint:sha-256` line from the SDP, and after `connectionState` becomes `connected`, SHA-256 the first DER certificate from `pc.sctp.transport.getRemoteCertificates()` and compare. A mismatch must produce a visible refusal or alert, not a console warning.
2. Display a short authentication string derived from the fingerprint on both peers, and require the R3 probe to swap one code for a code generated by a different browser profile. The app must fail closed. This is the direct test of the pairing MITM class.
3. Record the candidate lines in the invite code. Host candidates can carry a private IPv4 address or an mDNS hostname that identifies the local network. The skill requires either no `typ host` candidate of either kind in the code, or an explicit UI statement that the code contains local network identifiers. A silent leak fails.

The skill also owns the transport assertions that make sense without a server: one ordered data channel named `chat` at line 755, `maxRetransmits` and `maxPacketLifeTime` unset, and a Wireshark loopback capture showing a DTLS handshake and no plaintext payload. It does not claim to decrypt DTLS. If the test Chromium predates July 2026, `getRemoteCertificates` is unavailable, so the check falls back to hashing the certificate seen in the capture, and the skill must record which method produced the hash.

Adaptation: M. Two contexts, one code swap, one hash comparison and one capture. The APIs are stable in Chromium.

Verdict: adapt into an authored skill. Fit: high. This is the highest value gap in the file, because it turns the app's weakest link into a testable assertion.

### Card 8. Burp Suite

SOURCES:
- Burp Suite desktop documentation, https://portswigger.net/burp/documentation/desktop
- DOM Invader, https://portswigger.net/burp/documentation/desktop/tools/dom-invader

VERIFIED: both fetched 2026-11-26. Desktop page last updated 23 November 2026 and carries the warning that Burp can damage target systems and must not be used without authorization. DOM Invader page last updated 20 November 2026, states it tests DOM XSS using sources and sinks including web messages and prototype pollution, and runs only in Burp's built in browser.

What it encodes:

- An intercepting proxy workflow: capture, modify, replay, scan. It assumes HTTP or WebSocket traffic with a server on the other end.
- DOM Invader is the part that transfers: a sink inventory for client side data flow, with canary injection into sources and a list of controllable sinks.

Why it matters here: the app has no HTTP API, `connect-src 'none'` at line 6, and its payload travels over an SCTP data channel that Burp does not parse. A proxy in the middle would see the static file request and the STUN binding traffic, nothing else. Burp cannot test the pairing MITM, the frame parser or the wipe.

Gate an authored skill would enforce: only one thing transfers, the sink inventory. Every place a peer controlled string reaches the DOM must be listed with a line number and a disposition. In this app the candidates are the message rendering path, the file name display, and the image blob path at lines 890 and 1047. `textContent` or an escaped template passes; `innerHTML` with peer data fails. The skill enforces the inventory, not the tool.

Adaptation: none for the tool. The sink inventory is one section of the adapted `web-pentest` skill from 07-skill-sweep, not a separate skill.

Verdict: reference only. Fit: low. Do not install or schedule Burp as a round dependency.

## 4. Cards 9 to 12: scanners and memory

### Card 9. OWASP ZAP

SOURCES:
- ZAP documentation index, https://www.zaproxy.org/docs/
- ZAP automation options, linked from the index as https://zaproxy.org/docs/automate/

VERIFIED: documentation index fetched 2026-11-26. It lists the Getting Started guide, the Desktop User Guide, an automation section described as "the various options for automating ZAP", a Burp to ZAP feature map, alert details and test scan results. The automation page at https://zaproxy.org/docs/automate/ was also fetched and lists ZAPit, Docker packaged scans, GitHub Actions, the automation framework, and API and daemon mode.

What it encodes:

- A proxy based scanner with passive and active rules, contexts and authentication, plus an automation framework that runs a plan file of jobs.
- The passive scan pattern: point the tool at a target, let it spider, run passive rules, and review alerts by risk so a pipeline can gate on them.
- A feature map against Burp, which is useful mainly to show that the two tools cover the same HTTP surface.

Why it matters here: same limit as Burp. The app is a static file with `connect-src 'none'` at line 6 and no HTTP API. An active scan would have nothing to attack. A passive scan can still check response headers on the local origin, mixed content, and directory listing, which is a small but real check.

Gate an authored skill would enforce: if a local origin exists at all, a checked in `zap-plan.yaml` that runs passive rules only against `http://127.0.0.1:<port>/`, and a fail condition of any High or Medium alert. The CSP alert about inline script at line 6 is triaged as accepted design with the single file requirement as the reason, and the triage is recorded, not silenced. The gate is reproducibility: the plan file and the alert report hash go into the R3 evidence envelope, and a second run must produce the same alert set.

Adaptation: S if the project ever serves over loopback for R4. The plan file is short. The scanner itself is not the value.

Verdict: reference only. Fit: low. Do not schedule a ZAP round. The automation plan idea is already covered by the feature-gate-verification envelope in 07-skill-sweep.

### Card 10. nuclei

SOURCE: https://github.com/projectdiscovery/nuclei
VERIFIED: repository page fetched 2026-11-26, title "Nuclei is a fast, customizable vulnerability scanner powered by the global security community and built on a simple YAML-based DSL", MIT, 33,325 stars, created 2020-04-03. The README documents matcher flags such as `-enable-global-matchers`, `-exclude-matchers` and a replay mode that runs "the templates' matchers and extractors over a -store-events file", which confirms matchers are the decision step.

What it encodes:

- Template as data. A template is YAML with an identifier, metadata such as name and severity, a request section, and matchers that decide hit or miss.
- A community template corpus for known CVEs and misconfigurations, plus workflows that chain templates.
- Declarative detection instead of imperative scripts. The matcher is the test, and the same template runs against many hosts.

Why it matters here: there is no HTTP surface to scan, no versioned software to fingerprint, and no server side component. The template corpus targets products this app does not ship. The only transferable idea is the matcher schema, and card 4 already covers that with a schema that includes cleanup and an expected observable, which nuclei does not.

Gate an authored skill would enforce: none of its own. If it were used, the gate would be a declarative probe manifest with id, severity, action and matcher, which is the Atomic Red Team schema in card 4. Building a second manifest skill from nuclei would duplicate it.

Adaptation: none. This is a cut from the round plan, not a deferred build.

Verdict: reference only. Fit: low. The matcher pattern is absorbed by card 4.

### Card 11. nmap

SOURCE: https://nmap.org/book/nse.html
VERIFIED: Nmap Network Scanning chapter 9 fetched 2026-11-26. It documents the Nmap Scripting Engine, script categories, script types and phases, command line arguments, script selection and script format.

What it encodes:

- Host discovery, port state and service and version detection, plus NSE scripts organised by category and by the phase in which they run.
- A discipline of scanning only what is in scope and reading port state precisely: open, closed, filtered.
- Scripts as small programs with a rule that decides when they run, which is the same "declare the precondition" idea as an atomic test.

Why it matters here: nmap cannot see into a browser tab, but it can prove a negative that the privacy claim depends on, which is that no unexpected listener exists on the host while a session runs. That is a real check for a local only product, and it is cheap.

Gate an authored skill would enforce: a host surface check before and during a live session.

1. `nmap -sT -Pn -p- 127.0.0.1` lists exactly one open port, the chosen static server. Any second open port fails the check and is reported with the owning process from `lsof -nP -iTCP:<port> -sTCP:LISTEN`.
2. `lsof -nP -iTCP -sTCP:LISTEN -p <browser pid>` returns nothing. A browser listening on a TCP port during the session is a finding.
3. `lsof -nP -iUDP -p <browser pid>` shows only the configured STUN destination. Any other remote address is a finding.
4. The check runs before pairing, during transfer, and after wipe, so a listener that appears only during transfer is caught.

Adaptation: S. This is a shell script plus three assertions, and it can live inside the ops-defense skill rather than as a standalone.

Verdict: adapt into an authored skill. Fit: medium. Small, but it tests a claim no other source tests.

### Card 12. Memory forensics basics

SOURCES:
- Volatility 3, https://github.com/volatilityfoundation/volatility3
- Chrome DevTools Memory panel, https://developer.chrome.com/docs/devtools/memory
- Local `vmmap` and `heap` at /usr/bin, checked with `command -v` in this session
- Apple Platform Security, Data Protection overview, https://support.apple.com/guide/security/data-protection-overview-secf6276da8a/web

VERIFIED: Volatility 3 page fetched 2026-11-26, described as "the volatile memory extraction framework", 4,634 stars, and states that "Mac and Linux symbol tables must be manually produced by a tool such as dwarf2json". DevTools Memory page fetched, lists heap snapshot, allocation instrumentation on timeline, allocation sampling and detached elements. `vmmap` and `heap` are present on this host.

What it encodes:

- Acquisition first, analysis second. A memory image is captured, then plugins reconstruct processes, modules, network state and strings. Results are only as good as the symbol table for the exact kernel build.
- Volatility 3 separates the framework from the symbol packs. Windows symbols are fetched automatically; macOS and Linux symbols must be generated, which is a real cost on every OS update.
- At the process level, `vmmap` shows region sizes and `heap` shows malloc zones for a live process, which is enough to see whether a renderer's footprint drops after a wipe.

Why it matters here: full host memory forensics on macOS is not a realistic gate for this engagement. SIP and the absence of a supported acquisition path on Apple silicon make physical memory capture impractical in the general case (UNVERIFIED platform capability claim, not checked in this session), and Volatility macOS symbol generation is manual (verified from the README). The practical subset is renderer heap inspection, which is exactly what card 6 level 3 needs.

Gate an authored skill would enforce: a bounded claim rule, not a tool run.

1. Any statement about memory must name the region inspected (JS heap, renderer process, browser process, GPU process, swap), the tool used (heap snapshot, `vmmap`, `heap`, Volatility), and the artifact hash.
2. Any claim about memory the tool did not inspect must be written as not inspected. A report that says "keys are gone from memory" without naming the region fails review.
3. If Volatility is used, the symbol source and kernel build must be recorded, because a symbol mismatch silently produces wrong plugin output.

Adaptation: none for Volatility. The bounded claim rule is a paragraph in the zeroization skill from card 6. Effort S for that paragraph.

Verdict: reference only. Fit: low. Do not build a Volatility lane for this app.

## 5. Coverage matrix, cuts, and TOP 5 SHORTLIST

### 5.1 Where each source lands in the round plan

| Card | Source | R1 | R2 | R3 | R4 | R5 |
|---|---|---|---|---|---|---|
| 1 | hackingBuddyGPT ground truth | | | gate | yes | yes |
| 2 | PentestGPT task tree | | | gate | | |
| 3 | MITRE ATT&CK coverage | yes | | gate | | |
| 4 | Atomic Red Team atoms | | | gate | yes | gate |
| 5 | DoS for owned infrastructure | | | gate | yes | |
| 6 | Zeroization and macOS trace | | yes | gate | gate | yes |
| 7 | WebRTC and DTLS binding | | yes | gate | yes | |
| 8 | Burp DOM sink inventory | | | yes | | |
| 9 | ZAP passive baseline | | | optional | | |
| 10 | nuclei | | | | | |
| 11 | nmap host surface | | | | gate | |
| 12 | Memory forensics bounds | | | yes | | |

Reading the matrix: a gate cell means the round cannot close without that skill's artifact. A yes cell means the artifact is used but another skill owns the gate. An optional cell means the artifact is used only if a loopback origin exists. An empty cell means the source adds nothing to that round.

### 5.2 Cut list

No source graded fit none. Four are reference only and are not scheduled: Burp Suite (card 8), OWASP ZAP (card 9), nuclei (card 10) and Volatility host level forensics (card 12). The reason is the same in each case. An HTTP scanner, or a host memory framework, aimed at a single static file with no server, no accounts and `connect-src 'none'` at line 6 has almost nothing to act on. The reusable fragments from those four are folded into cards 4, 6 and 11 rather than becoming separate skills.

### 5.3 TOP 5 SHORTLIST, sources to encode first

1. Atomic Red Team, card 4. Encode first because it is the substrate for every other probe. The skill turns each R3 attempt into a YAML atom with an expected observable and a cleanup step, and it gives R5 a suite it can rerun on the final file hash. Without it, the later four skills each build their own ad hoc harness. Effort M. Gate unlocked: the R3 findings ledger, with no atom accepted without an observable and a cleanup.

2. WebRTC and DTLS fingerprint binding, card 7. Encode second because it closes the app's weakest link and the biggest named Elephant in 07-skill-sweep, the pairing code that carries an unverified fingerprint. The skill asserts that the pasted SDP fingerprint matches the live DER certificate, that a swapped code fails closed, and that the invite does not silently leak host candidates. Effort M. Gate unlocked: the pairing MITM class has a pass or fail test instead of a narrative.

3. Zeroization and macOS trace verification, card 6. Encode third because it defends the product's central claim and because a careless version of this skill is worse than none. The four levels separate what the page controls (typed array overwrite, key handle drop) from what it can only observe (heap residue, host trace), and the skill rejects media sanitization language for a JS heap. Effort M to L. Gate unlocked: the wipe and kill switch claims in R2, R3 and R4 carry artifacts, not adjectives.

4. Denial of service for owned infrastructure, card 5. Encode fourth because it is the gap the owner named and because the wrong framing is dangerous. The skill requires a scope line limited to loopback and two owned contexts, a ramp profile, pre-declared abort thresholds, and a recovery assertion, and it states that the public STUN server is never a target. Effort M. Gate unlocked: a peer flood test that is measured and reversible, not a vague stress claim.

5. hackingBuddyGPT ground truth, card 1. Encode fifth because it is the cheapest defence against a fabricated finding, and it makes the other four honest. Every attempt ends in a predicate over app state and a raw artifact, and a finding below that bar is logged as unverified. Effort M. Gate unlocked: no L3 or L4 finding can rest on an agent's self-report.

Encode next, not first: PentestGPT task tree (card 2), ATT&CK coverage (card 3) and nmap host surface (card 11). Each is small, and each depends on the atom suite from card 4 to have something to point at.

Do not encode: Burp, ZAP, nuclei, Volatility host lanes. Run them manually if a real HTTP origin or a memory image ever appears.

## 6. SELF-CHECK

| Acceptance item | Verdict | Evidence |
|---|---|---|
| Every source carries a URL verified in this session | PASS | 12 cards. `grep -oE 'https?://...'` returns 34 unique strings: 32 source URLs, the local `http://127.0.0.1:<port>/` example in card 9, and the `https://www.w3.org/TR/WebCryptoAPI/` redirect noted below. Every one of the 32 source URLs was fetched with `web_extract` on 2026-11-26 and returned a page title. The WebCrypto URL was fetched as a redirect and is cited in resolved form as `https://www.w3.org/TR/webcrypto/`. |
| Each source states the concrete gate an authored skill would enforce | PASS | 12 gate paragraphs in the body, counted before this appendix was added, one per card. Each gate names a file, a command or an assertion against V1. |
| Each source carries what it encodes, adaptation effort and verdict | PASS | `grep -c '^Verdict: '` = 12, `grep -c '^Adaptation: '` = 12. Every verdict line also states Fit, one of high, medium, low. Star counts and dates give the quality signals. |
| File ends with a TOP 5 SHORTLIST | PASS | Section 5.3 is the last content section, with exactly five numbered items, each naming effort and the gate it unlocks. The mandated SELF-CHECK appendix follows it. |
| Every external claim is sourced or marked UNVERIFIED | PASS | Each card has a VERIFIED line with a fetch date and a quoted page fact. The one platform capability claim I could not check, macOS memory acquisition on Apple silicon, carries the literal token UNVERIFIED in card 12. |
| Claims about the app carry file:line | PASS | Cards cite lines 6, 361, 431 to 441, 443 to 444, 723, 732 to 740, 755, 890, 1047, 1076 to 1079 and 1136. All were re-checked with `grep -n` in this session. |
| No em or en dashes | PASS | `grep -n $'\u2014'` and `grep -n $'\u2013'` both return no output. |
| English throughout | PASS | All prose is English. |
| Registry use was read-only | PASS | Seven `hermes skills search` calls: pentestgpt, webrtc, ddos, zeroiz, burp, nuclei, atomic red. No install, uninstall, update, audit or publish. |
| Read-only mission, one output file | PASS | The only write is this file. No clone, no skills tree change, no file under input/. |
| Time budget | PASS, estimate | About 24 minutes of tool work by call count, not clocked. The file carries STATUS: complete, so nothing was left partial. |
| File exists at the required path | PASS | /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/01-research/output/10-methodology-sources.md |

Counts from the verification run before this appendix was added: cards 12, gates 12, verdicts 12, adaptations 12, unique URL strings 34, em dashes 0, en dashes 0.

Status: PASS on all acceptance items. No item is FAIL. The only UNVERIFIED item is the platform capability note in card 12, which is labelled at the point of use.



