# 08 Registry skills and MCP catalog sweep

RUN ID: w3-ephemeral-skills-20261126
LANE: 08, registry lane
TOOL: `hermes` at /Users/marcelspatz/.hermes/hermes-agent/.hermes/bin/hermes
STATUS: complete
MODE: read only. No install, uninstall, update, audit, publish, snapshot, tap or config subcommand was run.

Scope of this file: what the live remote skill registries and the local MCP catalog offer for hardening and red teaming the target described in the brief. The installed local library was already enumerated in `07-skill-sweep.md` and is not re-counted here. Every row below comes from a query executed in this session, and the query text is quoted in section 2.

## 1. What the registry layer actually is

`hermes skills browse` reports the live index size and source split in its own footer:

```
Skills Hub - Browse - all sources  (105676 skills loaded, page 1/1057)
Sources: browse-sh: 479, hermes-index: 105655, official: 162, url: 0
```

My 24 required queries plus 15 supplementary queries returned 757 unique skill identifiers after dedupe. The required pass alone returned 627. Source split of the full union: clawhub 466, skills.sh 245, official 18, github 17, browse-sh 11. Dedupe was done in Python over the saved JSON, not by eye.

The official remote registry returns 5 security-directory skills for the query `security`, and no other official hit was security relevant:

| Official ID | Description as returned | Already in 07 |
|---|---|---|
| official/security/1password | Set up op CLI, sign in, and read or inject secrets. | no |
| official/security/oss-forensics | GitHub supply-chain forensics: recovery, IOCs, reporting. | yes |
| official/security/sherlock | Find accounts for a username across 400+ platforms. | yes |
| official/security/unbroker | Autonomously remove your info from data-broker sites. | no |
| official/security/web-pentest | Authorized web pentest: recon, proof-based exploits, report. | yes |

Command: `hermes skills search security --source official --limit 40 --json`, plus the same with `pentest`, `osint` and `threat`. The `threat` pass returned zero official hits, which means no official threat-model skill is present in the remote registry even though one is installed in this profile. `1password` and `unbroker` are out of scope for a page with no accounts, no keys and no vendor relationships.

## 2. Queries actually run

Every quoted string below was passed verbatim as the `query` argument to `hermes skills search <query> --json`. The required pass used `--limit 40`. The supplementary pass used `--limit 15`, `--limit 25` or `--limit 60` as noted by the result count. Result counts are from the saved JSON, not from the table view.

Required pass, 24 queries:

| Query | Results | Query | Results | Query | Results |
|---|---|---|---|---|---|
| `"security"` | 40 | `"pentest"` | 40 | `"red team"` | 31 |
| `"exploit"` | 40 | `"ctf"` | 40 | `"forensics"` | 40 |
| `"anti-forensics"` | 16 | `"ddos"` | 16 | `"webrtc"` | 14 |
| `"dtls"` | 10 | `"crypto"` | 40 | `"webcrypto"` | 23 |
| `"osint"` | 40 | `"recon"` | 40 | `"breach"` | 32 |
| `"zeroization"` | 13 | `"privacy"` | 40 | `"hardening"` | 40 |
| `"tls"` | 40 | `"network"` | 40 | `"fuzzing"` | 7 |
| `"burp"` | 4 | `"nmap"` | 20 | `"nuclei"` | 5 |

Supplementary pass, run because the required terms exposed the same six gaps 07 named and I needed to test whether the registry closes any of them:

| Query | Results | Why |
|---|---|---|
| `"csp"` | 25 | CSP review gap, 07 section 5 item 6 |
| `"content-security-policy"` | 1 | same, exact phrase |
| `"sdp"` | 21 | WebRTC signalling gap, item 1 |
| `"denial of service"` | 2 | peer layer DoS gap, item 3 |
| `"nonce"` | 10 | nonce and key epoch design |
| `"xss"` | 21 | DOM sink coverage |
| `"browser storage"` | 2 | no persistence invariant |
| `"memory forensics"` | 2 | local trace minimization |
| `"secure-coding"` | 2 | JS secure coding |
| `"trailofbits"` | 50 | author level survey of the strongest security publisher found |
| `"peerconnection"` | 4 | WebRTC API level coverage |
| `"sctp"` | 1 | data channel transport |
| `"session description"` | 14 | SDP phrasing variant |
| `"privacy monitor"` | 14 | monitor overlay design gap, item 5 |
| `"data exfiltration"` | 15 | pairing code and metadata egress |

Wider pass: `hermes skills browse --page 1 --size 100` (105,676 skills, 1,057 pages), `hermes skills browse --source official --size 200` and the same on page 2 (162 official skills, 2 pages). The browse index is alphabetical, so paging it is not a productive way to find a domain; it is useful as a denominator. Searching is the retrieval path, and the total above is the population those searches draw from.

Inspection pass: `hermes skills inspect <identifier>` succeeded on 14 identifiers. 13 outputs are stored at `/Users/marcelspatz/.hermes/cache/scratch/w3-registry/insp/`, and the first (`zeroize-audit`) was read directly from stdout. Two further calls for `webrtc-patterns` failed with "Could not find ... in any source" and are marked UNVERIFIED rather than guessed.

Identifier convention, because the CLI is not uniform. ClawHub entries come back as bare slugs, for example `pentest-workbench`, with no namespace. In this file a ClawHub row is written `clawhub/<slug>` for readability, and `<slug>` is the literal identifier the CLI accepts. Where a whole collection is meant, the collection prefix is written without a leaf, for example `skills-sh/ljagiello/ctf-skills`, and every leaf under it is present in the saved JSON. Every other identifier is verbatim from the saved output.

## 3. Graded findings, gap by gap

Criteria per row are the brief's: name, registry id and source URL, what it encodes, compatibility verdict, quality signals, engagement fit, final verdict. Popularity is install count as reported by skills.sh in its own search description where present, and GitHub stars from the public API where the repo is known. Recency is the repository `pushed_at` from `https://api.github.com/repos/<owner>/<repo>`, read in this session. Where a signal was not visible I say so instead of estimating.

### 3.1 Zeroization and wipe completeness (07 gap 2)

| Field | Value |
|---|---|
| Name | zeroize-audit |
| Registry ID and URL | `skills-sh/trailofbits/skills/zeroize-audit`, https://skills.sh/trailofbits/skills/zeroize-audit, source repo https://github.com/trailofbits/skills |
| What it encodes | Frontmatter, quoted from the inspected SKILL.md: "Detects missing zeroization of sensitive data in source code and identifies zeroization removed by compiler optimizations, with assembly-level analysis, and control-flow verification. Use for auditing C/C++/Rust code handling secrets, keys, passwords, or other sensitive data." It runs as a role based pipeline (preflight, then per symbol analysis) with `schemas/input.json` and `prompts/task.md`, and it expects Serena MCP symbol tools plus an assembly view. |
| Compatibility with native Hermes install | Needs adaptation, heavily. The workflow is C/C++/Rust and assembly. The target is one inline script in a browser, so there is no `memset` to elide. The JS failure modes are different: strings are immutable and copied, closures retain references, `Blob` and object URL backing stores keep file bytes alive, and the JS heap is not deterministically freed. The control flow verification idea survives the port; the assembly step does not. |
| Quality signals | Author Trail of Bits, a well known security firm. Repo 8,458 stars, last push 2026-11-25, so actively maintained. 5,634 installs, by far the most installed security skill in my result set. |
| Engagement fit | Medium. Correct domain, wrong language and wrong memory model. |
| Final verdict | Adapt into an authored skill. Keep the invariant "every secret has a named sink and a proof that the sink ran", and replace the assembly check with a Chromium heap snapshot retention check on the key and file buffers. Do not install as written. |

Also returned under `"zeroization"`, all the same skill re-indexed by other accounts, which is a supply chain signal rather than a separate capability: `skills-sh/sickn33/agentic-awesome-skills/zeroize-audit` (47 installs), `skills-sh/redhatproductsecurity/prodsec-skills/zeroize-audit` (7 installs, Red Hat Product Security, https://github.com/redhatproductsecurity/prodsec-skills), `skills-sh/lua2147/claude-toolkit-catalog/zeroize-audit` and `skills-sh/gztes/security-for-platforms/zeroize-audit` (1 install each). Grade the Trail of Bits original only. The rest are mirrors with no added content visible from the index, and installing a mirror of a security skill is a needless trust expansion.

No registry skill covers zeroization in JavaScript, WebAssembly or the DOM. That confirms 07 gap 2 against 105,676 indexed skills, so the R2 and R4 wipe probes still have to be authored.

### 3.2 WebRTC, SDP and DTLS (07 gap 1)

The `"webrtc"` query returned 14 results and not one is a protocol review skill. They are browser automation tools with a WebRTC live view (`arise-browser`), an avatar transport (`atlas-avatar`), a remote desktop (`billd-desk`), camera control (`xpai-camera-control`), fingerprint auditing (`browser-fingerprint-audit`, `multi-account-isolation`, `anti-detect-browser`), and unrelated. The `"sdp"` query returned 21 results and every one was PyTorch FSDP, a false positive on the substring. The `"sctp"` query returned exactly one result, a generic RFC finder.

Two candidates survived triage.

| Field | Value |
|---|---|
| Name | node-quic-dtls |
| Registry ID and URL | `skills-sh/jasnell/node-skills/node-quic-dtls`, https://skills.sh/jasnell/node-skills/node-quic-dtls, repo https://github.com/jasnell/node-skills |
| What it encodes | The `node:quic` and `node:dtls` APIs: `quic.connect` and `listen`, `QuicEndpoint`, `QuicSession`, `QuicStream`, `sendDatagram`, `dtls.listen` and `connect`, PSK, SNI, session resumption, and the build flags needed. Its description explicitly claims coverage of "WebRTC DTLS-SRTP keying". It also carries an honest warning that standard Node builds do not include these modules. |
| Compatibility with native Hermes install | Native install is possible, but it is irrelevant to the target. This documents a Node server API. A Chromium page cannot read or set its own DTLS certificate fingerprint from JS, and there is no `node:dtls` module on a stock Node 24 build without recompiling. |
| Quality signals | Author James Snell, a Node.js core contributor. Repo 78 stars, last push 2026-11-16. 6 installs. Small audience, high domain authority. |
| Engagement fit | Low. Useful only as a mental model of a DTLS handshake and session resumption, which the R1 blueprint already needs to state from the RFC. |
| Final verdict | Reference only. Do not install. Read it if the R1 protocol notes need a concrete handshake sequence, then cite RFC 6347 and RFC 8446 for the actual claims. |

| Field | Value |
|---|---|
| Name | webrtc-patterns |
| Registry ID and URL | `skills-sh/marvinrichter/clarc/webrtc-patterns`, detail page https://skills.sh/marvinrichter/clarc/webrtc-patterns |
| What it encodes | UNVERIFIED. `hermes skills search "peerconnection"` returned it with 1 install, but `hermes skills inspect skills-sh/marvinrichter/clarc/webrtc-patterns` failed twice with "Could not find ... in any source". The search index knows a name, the fetch path does not serve a body. |
| Compatibility with native Hermes install | UNVERIFIED. |
| Quality signals | 1 install. Author repo `marvinrichter/clarc` was not fetched. |
| Engagement fit | Cannot be graded. Even if the body turns out to cover peer connection setup, a 1 install skill with a broken inspect path is not a dependency for a red team round. |
| Final verdict | Reference only, and only after a manual fetch confirms the body exists. Treat as unusable until then. |

Conclusion for this gap: zero usable coverage of SDP structure, ICE candidate handling, DTLS fingerprint binding, or data channel framing. The R3 cases in the 07 plan stand as authored probes. This is now a stronger claim than 07 could make, because 07 only swept the local library.

### 3.3 Client side crypto and WebCrypto (07 gap 4)

| Field | Value |
|---|---|
| Name | webcrypto-hooking |
| Registry ID and URL | `skills-sh/manyuegong33/r0crawl_skills/webcrypto-hooking`, https://skills.sh/manyuegong33/r0crawl_skills/webcrypto-hooking, repo https://github.com/manyuegong33/r0crawl_skills |
| What it encodes | A reverse engineering workflow for intercepting WebCrypto calls: preserve raw artifacts, start with the smallest observation that separates competing hypotheses, separate static facts from runtime observations, correlate code with call stacks and traffic, build a minimal reproducer, and record tool versions and hashes. The quality gates are the useful part: a string is not a call chain, a dump is not valid until a consumer tool agrees, a hook is not stable until cold start and repeated runs are compared. |
| Compatibility with native Hermes install | Needs adaptation. It is written for native and Java reverse engineering. The technique ports cleanly to a browser because `crypto.subtle` is patchable from the page or from a Playwright init script. |
| Quality signals | Author repo 382 stars, last push 2026-09-20. 1 install. The body is a generic template shared across the author's modules, not a WebCrypto specific treatment. |
| Engagement fit | Medium. This is exactly how the R4 lane verifies that key epochs rotate and that old keys are unreachable: wrap `crypto.subtle.encrypt`, `decrypt`, `generateKey` and `deriveKey`, and log key identity and epoch. |
| Final verdict | Reference only. The hook approach is four lines of Playwright `addInitScript`, so author it in R2 rather than importing a 1 install template. |

| Field | Value |
|---|---|
| Name | runtime-crypto-boundary |
| Registry ID and URL | `skills-sh/manyuegong33/r0crawl_skills/runtime-crypto-boundary`, https://skills.sh/manyuegong33/r0crawl_skills/runtime-crypto-boundary |
| What it encodes | Finding the boundary where plaintext becomes ciphertext across Java, native, WebCrypto, TLS and serialization layers, with evidence discipline: record sample hash, version, architecture and environment, preserve artifacts before modifying, record first difference locations, validate with a clean baseline and a repeat run. |
| Compatibility with native Hermes install | Needs adaptation. Language specific tooling is absent, the evidence rules transfer. |
| Quality signals | Same author and repo as above, 382 stars, pushed 2026-09-20. 1 install. |
| Engagement fit | Low to medium. It is the right discipline for proving "no plaintext leaves the page" but says nothing about browser APIs. |
| Final verdict | Reference only. |

`"webcrypto"` also returned `webcrypto-hooking`'s siblings and a large number of CTF repos matching on the word crypto. No skill encodes nonce management, AES-GCM usage rules, key derivation, or rotation epochs for a browser app. Gap 4 survives the registry sweep. A useful adjacent find was `skills-sh/ariaramin/flutter-skills/flutter-secure-storage-security-engineering` (15 installs), but it is mobile storage guidance and does not transfer.

### 3.4 CSP review and the inline script decision (07 gap 6)

This is the one gap the registry actually closes, on both the attack and the defence side.

| Field | Value |
|---|---|
| Name | csp-bypass-advanced |
| Registry ID and URL | `skills-sh/yaklang/hack-skills/csp-bypass-advanced`, https://skills.sh/yaklang/hack-skills/csp-bypass-advanced, repo https://github.com/yaklang/hack-skills |
| What it encodes | Per directive bypass technique, quoted from the inspected frontmatter: "Advanced Content Security Policy bypass techniques. Use when XSS or data exfiltration is blocked by CSP and you need to find policy weaknesses, trusted endpoint abuse, nonce leakage, or exfiltration channels that CSP cannot block." The body carries a directive reference matrix that explicitly flags `base-uri` and `form-action` as having no fallback, so an absent directive is unrestricted. It also routes to dangling markup injection for exfiltration when scripts are blocked, and to CRLF injection for nonce theft. |
| Compatibility with native Hermes install | Native install. It is plain markdown plus references, no host specific tooling. |
| Quality signals | Author Yaklang, a security tooling company. Repo 2,706 stars, last push 2026-09-13. Install count not shown for this entry in search output. The body is dense and specific rather than generic. |
| Engagement fit | High. The target ships `script-src 'unsafe-inline'` at line 6 and `connect-src 'none'`. That combination is the exact scenario this skill addresses, and its framing changes the R3 test: the question is not only "can script run" but "can data leave when `connect-src` is none", which dangling markup and navigation based exfiltration answer. |
| Final verdict | Install candidate. This arms an R3 class that 07 listed as uncovered. |

| Field | Value |
|---|---|
| Name | csp-policy-generator |
| Registry ID and URL | `clawhub/@charlie-morrison/csp-policy-generator`, detail page https://clawhub.ai/skills/csp-policy-generator (UNVERIFIED, the CLI exposes the handle but not a resolvable URL; identifier returned by inspect is `@charlie-morrison/csp-policy-generator`) |
| What it encodes | Analysing a page to discover every resource origin, generating a least privilege policy per directive, testing for violations, and migrating from report-only to enforcing. The inspected body includes a concrete extraction script that detects inline scripts and `style=` attributes and flags `'unsafe-inline'` when present. |
| Compatibility with native Hermes install | Native install for the workflow. One step assumes an HTTP host and direct fetch of the page, which a local `file://` target cannot satisfy, so the origin discovery step must be pointed at a local server or fed the file directly. |
| Quality signals | ClawHub community publisher, handle `@charlie-morrison`. No install count and no upstream repo shown by inspect. Recency UNVERIFIED. |
| Engagement fit | High. It answers the R2 question 07 left open: replace `'unsafe-inline'` with a hash or nonce, and prove the tightened policy does not break the page. Its report-only migration path is the safe way to land that change in a single file build. |
| Final verdict | Install candidate, with a review of the body before use because publisher identity is unverified. If the body turns out to be a thin prompt, the same procedure can be authored in an hour, so this is the lowest confidence of the two CSP picks. |

### 3.5 Denial of service at the peer layer (07 gap 3)

The `"ddos"` query returned 16 results. Every one is a cloud provider console for network layer attack mitigation: Alibaba Cloud DDoS Native, DDoS Pro and origin exposure detector (7 entries), Huawei AAD protected IP list and WAF rule management, AWS `shieldadvanced`, AWS `waf` with rate based rules for HTTP floods, `cf-manager` and `cdn-toolkit-pro` for Cloudflare and CDN edge protection, and `flowtriq` for attack monitoring.

All of these assume a protected origin with a public IP, a CDN, or an account level scrubbing service. The target has no server, no public IP, no DNS name and no CDN. Fit is none for every one of them. Cut.

The `"denial of service"` exact phrase returned 2 results. `shieldadvanced` is the same cut. The other is:

| Field | Value |
|---|---|
| Name | phy-regex-audit |
| Registry ID and URL | `clawhub/phy-regex-audit`, identifier `@phy/phy-regex-audit` as returned by search (handle form UNVERIFIED beyond the search record) |
| What it encodes | A static ReDoS scanner and regex quality auditor that walks a codebase looking for catastrophic backtracking patterns. |
| Compatibility with native Hermes install | Native install, but it is a codebase scanner and the target is one file. Pointing it at a single file needs a manual invocation step. |
| Quality signals | ClawHub community. Install count and recency not shown in search output. |
| Engagement fit | Low to medium. It matters only if the `unpack` path or the code prefix check uses a regex against attacker input. The inspected target code uses a prefix split and `DecompressionStream`, so the relevant DoS is allocation based, not regex based. |
| Final verdict | Reference only. Keep the idea, not the tool. The R3 flood and decompression bomb cases still need authored probes. |

This confirms 07 gap 3 against the full index. No registry skill encodes peer layer flood, chunk exhaustion, SDP flood, rekey request storms, or amplification against a serverless WebRTC endpoint.

### 3.6 Fuzzing and corpus construction for the parser surfaces

| Field | Value |
|---|---|
| Name | fuzzing-dictionary |
| Registry ID and URL | `skills-sh/trailofbits/skills/fuzzing-dictionary`, https://skills.sh/trailofbits/skills/fuzzing-dictionary |
| What it encodes | Building and applying fuzzing dictionaries so a fuzzer produces the keywords, magic bytes and tokens a target expects, by extracting tokens from source, headers, binaries and specifications, plus the dictionary syntax and wiring into libFuzzer or AFL++. The frontmatter states the trigger as coverage stalling at input parsing. |
| Compatibility with native Hermes install | Needs adaptation. The dictionary format is libFuzzer and AFL++ text, and there is no JS fuzzer in the loop. The token extraction method transfers directly to a JavaScript harness run in Node or in a page. |
| Quality signals | Trail of Bits, repo 8,458 stars, pushed 2026-11-25. Install count not shown in this entry's search description. |
| Engagement fit | Medium. The pairing code format has a known prefix and a compressed payload, so a token dictionary plus a small generator is a realistic way to hit the `unpack` parser with structurally valid but hostile inputs, which is a better use of R3 time than random bytes. |
| Final verdict | Adapt into an authored skill. Take the token harvesting method, write a Node harness that calls `unpack` directly with a corpus of prefix variants, truncated compressed streams and bomb payloads. |

| Field | Value |
|---|---|
| Name | fuzzing-obstacles |
| Registry ID and URL | `skills-sh/trailofbits/skills/fuzzing-obstacles`, https://skills.sh/trailofbits/skills/fuzzing-obstacles |
| What it encodes | Patching past the barriers that stop a fuzzer making progress: checksum and hash verification, magic value validation, time based seeds, non deterministic global state. It recommends a fuzzing build flag so production behaviour is preserved, and warns about the false positives a patch can introduce. |
| Compatibility with native Hermes install | Needs adaptation. The mechanism is conditional compilation in C or Rust. In a browser the equivalent is stubbing a predicate in a Playwright init script, which is simpler and does not need this skill. |
| Quality signals | Trail of Bits, repo 8,458 stars, pushed 2026-11-25. |
| Engagement fit | Low. The target has no checksum gate before parsing, only a prefix and a decompressor, so there is no barrier to patch past. |
| Final verdict | Reference only. |

Other fuzzing hits were `skills-sh/sickn33/agentic-awesome-skills/api-fuzzing-bug-bounty` (REST and GraphQL, target has neither), `skills-sh/eyadkelleh/awesome-skills-security/security-fuzzing`, `skills-sh/mohitmishra786/low-level-dev-skills/fuzzing` (C and Rust focus), and `clawhub/harness-writing` (native harnesses). All cut for fit none or low.

### 3.7 Local trace minimization on macOS

| Field | Value |
|---|---|
| Name | offensive-anti-forensics |
| Registry ID and URL | `skills-sh/snailsploit/claude-red/offensive-anti-forensics`, https://skills.sh/snailsploit/claude-red/offensive-anti-forensics, repo https://github.com/snailsploit/claude-red |
| What it encodes | An artifact taxonomy per platform. Windows: event log clearing with `wevtutil` and `Clear-EventLog`, ETW provider patching, timestomp and SetMACE, NTFS alternate data streams, `sdelete`. Linux: journal truncation, utmp and wtmp binary editing, syslog manipulation, `shred`. Plus memory artifact removal to defeat live forensics, MFT and USN journal manipulation, DoH tunnelling for C2, and anti VM detection. Mapped to MITRE ATT&CK T1070, T1027 and T1497. |
| Compatibility with native Hermes install | Needs adaptation for the inverted use. It is an offensive playbook for Windows and Linux. macOS is absent, which matters because the R4 lane runs on macOS 26.4.1. |
| Quality signals | Repo 11,616 stars, last push 2026-11-17. 237 installs, the second most installed security skill in my set. |
| Engagement fit | Medium. Read backwards it is a checklist of artifact classes, and that is useful for the trace minimization probe: before claiming the page leaves no local trace, enumerate what a Chromium profile writes (History, Cookies, Local Storage, Session Storage, IndexedDB, Cache, GPUCache, Code Cache, Network Persistent State, TransportSecurity, and the DNS and socket tables the OS keeps). What it cannot tell you is where macOS keeps those files. |
| Final verdict | Reference only. Use it to structure the artifact list, not to justify any destructive action. Every technique in it is offensive and out of scope for a read only research lane. Do not install. |

`"memory forensics"` returned 2 results, `clawhub/@solomonneas/memory-forensics` and `clawhub/s3-memory-forensics`, both Volatility workflows for Windows and Linux RAM dumps. macOS acquisition, and more importantly the browser process heap of a live Chromium, is not covered. Fit none for this engagement. Cut.

`"forensics"` at 40 results was dominated by CTF forensics (`clawhub/ctf-misc-forensics`, `clawhub/ctf-forensics`, `skills-sh/ljagiello/ctf-skills/ctf-forensics`), GitHub supply chain forensics (`official/security/oss-forensics`, `clawhub/clickhouse-github-forensics`), and corporate incident tooling. None addresses browser local storage or macOS trace surfaces. Fit none, cut.

### 3.8 Frontend review protocol

| Field | Value |
|---|---|
| Name | Frontend Security Review |
| Registry ID and URL | `clawhub/@bovinphang/fec-security-review`, identifier returned by inspect `@bovinphang/fec-security-review`, detail page https://clawhub.ai/skills/fec-security-review (UNVERIFIED host path) |
| What it encodes | Three explicit review modes (change review, targeted review, project review) with a rule that scope must be stated before diffs are collected, and a default that an unqualified invocation is a project review. It covers XSS, CSRF, sensitive data exposure, unsafe DOM APIs, untrusted user input, auth and token handling, payment flows, file upload, CSP, dependency risk and third party scripts, and it excludes dependency and build directories by default. |
| Compatibility with native Hermes install | Native install. Markdown protocol, no tooling. The scope negotiation part transfers to a one file target without change. |
| Quality signals | ClawHub community publisher `@bovinphang`. No install count and no repo exposed. Recency UNVERIFIED. The body is a real procedure with explicit anti scope creep rules, not a prompt stub. |
| Engagement fit | High. The target is entirely frontend: inline script, DOM sinks, file upload by object URL, and no backend. The four surfaces it names that 07 covers only partly are unsafe DOM APIs, file upload, sensitive data exposure in the DOM, and CSP. |
| Final verdict | Install candidate. Where it overlaps the installed `security-best-practices` frontend reference, prefer this one for review scoping and the installed one for the actual remediation text. |

| Field | Value |
|---|---|
| Name | fec-browser-storage |
| Registry ID and URL | `clawhub/fec-browser-storage`, identifier `@bovinphang/fec-browser-storage` as returned by search (body not inspected) |
| What it encodes | Choosing, implementing and reviewing browser storage: localStorage, sessionStorage, IndexedDB, cookies. Description only, body UNVERIFIED. |
| Compatibility with native Hermes install | Likely native, markdown only. |
| Quality signals | Same publisher series as the review skill. No install count shown. Recency UNVERIFIED. |
| Engagement fit | Medium to high, but inverted. The requirement is that no persistence API is touched at all, so the value is a complete enumeration of what counts as touching storage. That is a short list and 07 already produced it. |
| Final verdict | Reference only. Installing a storage guidance skill to conclude "use none of them" is waste. |

`"xss"` returned 21 results. The graded ones are the review skill above and `clawhub/phy-xss-audit`, a static scanner for reflected, stored and DOM XSS (`@phy/phy-xss-audit`, body not inspected). `phy-xss-audit` is fit medium and final verdict reference only, because a single file with no server side rendering can be read in full in less time than a scanner takes to produce false positives. The same logic cuts `skills-sh/mukul975/anthropic-cybersecurity-skills/testing-for-xss-vulnerabilities` (part of a 36,821 star repo, last push 2026-08-31, but a generic web app procedure) and `skills-sh/yaklang/hack-skills/xss-cross-site-scripting`.

## 4. Remaining required queries, graded in bulk

These queries returned real security content that does not fit this target. Grading them one by one would produce 200 rows that all end in "cut", so each row below names the strongest representative hits, the shared grade, and the reason. Nothing here was skipped unread: the counts and names come from the saved JSON, and the descriptions were read.

| Query (quoted) | Results | Strongest representatives | Fit | Reason and verdict |
|---|---|---|---|---|
| `"pentest"` | 40 | `clawhub/pentest-api-attacker`, `pentest-auth-bypass`, `pentest-active-directory`, `pentest-c2-operator`, `pentest-workbench`, `pentest-interactive`, `pentest-findings-report`, `clawhub/nmap-pentest-scans`, `skills-sh/reason-machines/security-skills/pentest-ai-agents`, `skills-sh/usestrix/strix/managed-pentesting-with-strix` | Low | Every one assumes a network reachable host with endpoints, auth sessions or Active Directory. The target has no server, no session and no directory. `pentest-findings-report` and `pentest-interactive` are the only two with transferable content (report structure, seven phase manual discipline) and both overlap the installed `web-pentest` skill that 07 already graded. Reference only, do not install. |
| `"red team"` | 31 | `clawhub/red-team`, `red-team-verificator`, `acquirer-red-team`, `design-red-team-audit`, `redpincer`, `redteam`, `ai-security-redteam`, `abaddon`, `attack-surface-mapper` | None to low | The term is mostly not security. It covers numerical claim auditing, acquisition diligence, design critique and startup review. The genuinely offensive ones (`redpincer`, `redteam`, `ai-sting`, `agent-redteam-kit`) target LLM endpoints and prompt injection, which this app does not use. Cut. |
| `"exploit"` | 40 | `skills-sh/yaklang/hack-skills/browser-exploitation-v8`, `heap-exploitation`, `kernel-exploitation`, `format-string-exploitation`, `clawhub/ctf-pwn-exploit`, `skills-sh/mukul975/anthropic-cybersecurity-skills/exploiting-sql-injection-vulnerabilities` | None | Native binary exploitation, V8 engine exploitation and SQL injection. The R3 cases are logic and framing abuse in a page, not memory corruption in the renderer. `browser-exploitation-v8` is the only adjacent one and it is about escaping the sandbox, which is a different threat model from a self-hosted page. Cut. |
| `"ctf"` | 40 | `skills-sh/ljagiello/ctf-skills` (crypto, forensics, pwn, reverse, osint, malware, misc), `clawhub/ctf-solver`, `ctf-pwn`, `ctf-misc`, `skills-sh/wang200935/security-agent-skills/ctf-playbook` | None | No capture the flag component in this engagement. The crypto and forensics modules solve puzzle formats, not product review. Cut. |
| `"crypto"` | 40 | almost entirely cryptocurrency and market data: `official/blockchain/evm`, `official/blockchain/solana`, `clawhub/crypto-skill`, `skills-sh/binance/binance-skills-hub/*`. One security entry: `skills-sh/trailofbits/skills/crypto-protocol-diagram` | Low | The one relevant hit has metadata but no retrievable body: `hermes skills inspect` returned the header only, no SKILL.md preview. Content is UNVERIFIED. If the body does produce a reviewable protocol diagram, it would help R1 document the pairing exchange and the DTLS handshake. Reference only and only after a manual fetch. Everything else cut. |
| `"osint"` | 40 | `official/security/sherlock`, `official/research/domain-intel`, `official/research/osint-investigation`, `clawhub/osint-social`, `clawhub/osint-daily-brief` | None | Identity, domain and entity investigation. The target has no domain, no accounts and no public footprint. The one adjacent item, `official/research/domain-intel`, would matter only if the page were hosted, and even then it audits the host, not the app. Cut. |
| `"recon"` | 40 | `official/research/domain-intel`, `official/security/web-pentest`, `clawhub/recon` (a repository state gate for coding tasks), `skills-sh/prathamdby/skills/recon` | None to low | Subdomain and asset discovery for external estates. `web-pentest` already contains the recon phase 07 adapted. Nothing new. Cut. |
| `"breach"` | 32 | `clawhub/breach-check`, `clawhub/password-breach-exposure`, `clawhub/comb` (3.2 billion leaked credentials), `clawhub/data-breach-impact-calculator`, `clawhub/identity-breach-first-response` | None | Credential exposure lookup and data breach cost modelling. No credentials exist in the product. Note the irony for R1: the pairing code exchange is a social engineering surface, but none of these skills address that. Cut. |
| `"privacy"` | 40 | `official/security/unbroker`, `clawhub/privacy-cleanup`, `clawhub/privacy-check`, `clawhub/privacy-scanner`, `skills-sh/*/privacy-policy`, `clawhub/privacy-shield` | None to low | Data broker removal, PII scanners and privacy policy generation. `privacy-check` and `privacy-scanner` are the closest, both are regex scanners for secrets in text, which duplicates the local `haze-secret-redaction-sinks` skill 07 already cut. No skill encodes a runtime privacy monitor design, so 07 gap 5 survives. Cut. |
| `"hardening"` | 40 | `clawhub/toolweb-*` family (Cisco, FortiGate, Juniper, EKS, AKS, GKE, OpenShift, Docker CIS generators), `clawhub/agent-security-hardening`, `clawhub/server-host-hardening`, `clawhub/openclaw-hardening` | None | CIS benchmark config generators for network devices, Kubernetes and containers, plus agent self hardening. There is no device, cluster or server. Cut. |
| `"tls"` | 40 | `clawhub/tls-configuration-auditor`, `clawhub/expanso-tls-inspect`, `clawhub/cert-decode`, `clawhub/http-security-headers`, `skills-sh/wshobson/agents/mtls-configuration` | None to low | Server side TLS termination, certificate lifecycle and header auditing. The target's DTLS is negotiated by Chromium and there is no certificate the author controls. `http-security-headers` would only re-test the CSP line already covered in section 3.4. Cut. |
| `"network"` | 40 | `clawhub/network-scan`, `clawhub/network-scanner`, `clawhub/li-base-scan`, `skills-sh/yaklang/hack-skills/network-protocol-attacks`, `clawhub/network-log-analysis` | None | ARP spoofing, VLAN hopping, DHCPv6, name resolution poisoning and port scanning. These are layer 2 and 3 attacks on a switched network. The target is two Chromium instances on one machine or a loopback link. `network-protocol-attacks` is well written and irrelevant. Cut. |
| `"nmap"` | 20 | `clawhub/nmap`, `nmap-recon`, `nmap-pentest-scans`, `nmap-mcp`, `clawhub/recon-quick`, `clawhub/auto-security-audit` | None | Port and service discovery against a host. There is no listening port in the target design, and no server to scan. Cut. |
| `"nuclei"` | 5 | `clawhub/nuclei-analysis`, `clawhub/auto-security-audit`, `clawhub/security-scanner` | None | Template based CVE scanning against HTTP services. Nothing to scan. Cut. |
| `"burp"` | 4 | `clawhub/burp-mcp`, `burp-zap-hardened`, `clawhub/pentest-with-bp`, `skills-sh/trailofbits/skills/burpsuite-project-parser` | None to low | Burp over MCP, and a parser that requires Burp Suite Professional plus the `burpsuite-project-file-parser` extension. The R3 traffic is a data channel, not HTTP proxy traffic, so Burp sees almost nothing. The parser is unusable without a paid Burp licence. Cut. Note its one transferable idea, quoted from its body: "Empty output is not a clean result", because Burp silently ignores flags it does not recognise. That exit code discipline is worth copying into the R3 evidence protocol. |
| `"anti-forensics"` | 16 | `skills-sh/snailsploit/claude-red/offensive-anti-forensics` (graded in 3.7), `skills-sh/brucesongs/kali-claw/anti-forensics` (6 installs), `skills-sh/aloc999/exploitninja/anti-forensics` (5), `clawhub/ctf-misc-forensics` | Low | The mirrors and variants add nothing to the graded original. `kali-claw` is a Kali tooling wrapper. Cut. |

## 5. MCP catalog

`hermes mcp` exists on this host and has a read only listing path. Command run: `hermes mcp catalog`. It printed 88 lines: 66 catalog entries and 9 configured custom servers. A keyword scan of that output for pentest, nmap, burp, fuzz, proxy, packet, capture, webrtc, exploit and red team returned zero matches. The full output is at `/Users/marcelspatz/.hermes/cache/scratch/w3-registry/mcp_catalog.txt`.

Security relevant entries in the Nous approved catalog:

| Catalog entry | Status | Description as printed | Fit for this engagement |
|---|---|---|---|
| `semgrep` | available | Scan code for security vulnerabilities with Semgrep. | Medium. A single HTML file with inline JS is within Semgrep's reach, and it would give a second opinion on DOM sinks and `innerHTML` use. It is a static scanner, so it adds nothing for protocol or framing cases. |
| `globalping` | available | Ping, traceroute, DNS, and HTTP tests from global probes. | Low. It measures from external vantage points, which is useful for a deployed service and useless for two local Chromium peers. It cannot observe loopback. |
| `context7` | available | Up-to-date, version-specific library docs and code examples. | Low but useful. The only external dependency is the STUN server and the browser APIs, so version accurate WebRTC API docs help the R2 author. Not a security tool. |
| `cloudflare` | available | Full Cloudflare API access via the official remote MCP. | None. No zone, no origin. |
| `postman` | available | Postman workspaces, collections, environments, and APIs. | None. No HTTP API. |

There is no pentest, fuzzing, proxy, packet capture, or WebRTC inspection server anywhere in the catalog. The absence is the finding: nothing in the MCP layer substitutes for the authored probes that 07 scheduled.

Configured custom servers that matter, from the same output:

| Server | Status | Relevance |
|---|---|---|
| `playwright` | custom, enabled | The R4 driver. Two browser contexts, one page each. This is the only MCP server the engagement actually needs to run a round. |
| `github` | custom, enabled | Findings and report publication only. |
| `blender` | custom, enabled | Irrelevant. |
| `linkedin`, `meta-instagram`, `rea` | custom, enabled | Irrelevant. |
| `obsidian`, `october_bus`, `higgsfield`, `qwen-mm-plugins-*` | custom, disabled | Irrelevant. |

One caveat worth recording: the catalog lists `semgrep` as `available`, not `enabled`, so using it in R2 means an install action, which is outside this read only lane. Recommend it to the R2 owner rather than doing it here.

## 6. Coverage verdict against the six gaps from 07

| Gap from 07 section 5 | Registry coverage | Evidence |
|---|---|---|
| 1. WebRTC protocol review: SDP, ICE, DTLS fingerprint binding, data channel framing | None | `"webrtc"` returned 14 results, all browser automation, avatar, remote desktop or camera tools. `"sdp"` returned 21 results, all PyTorch FSDP substring matches. `"sctp"` returned 1 unrelated RFC finder. `"peerconnection"` returned 4 results, the only potentially relevant one (`webrtc-patterns`, 1 install) is not fetchable by `inspect`. |
| 2. Zeroization and wipe verification | One skill, wrong language | `"zeroization"` returned 13 results, 1 original (`trailofbits/skills/zeroize-audit`, 5,634 installs) and 4 mirrors of it, plus 8 unrelated. The original is C/C++/Rust and assembly based. Nothing covers JS heap retention, `Blob` backing stores or object URL cleanup. |
| 3. Denial of service at the peer layer | None | `"ddos"` returned 16 results, every one a cloud scrubbing, WAF or CDN console. `"denial of service"` returned 2, one cloud console and one ReDoS static scanner. No flood, chunk exhaustion, rekey storm or amplification content. |
| 4. Client side crypto: WebCrypto, nonce management, key derivation, rotation epochs | Methodology only, low quality | `"webcrypto"` returned 23 results, mostly CTF and cryptocurrency. The two honest hits (`webcrypto-hooking`, `runtime-crypto-boundary`) are generic reverse engineering templates from one author, 1 install each, and neither discusses AES-GCM nonce discipline or epoch rotation. |
| 5. Privacy monitor design | None | `"privacy monitor"` returned nothing relevant; `"privacy"` returned compliance, data broker removal, policy generation and secret scanners. No skill designs a runtime invariant monitor or discusses detector liveness. |
| 6. CSP review | Closed | `"csp"` returned `csp-bypass-advanced` (attack side) and `csp-policy-generator` (defence side), both inspected, both graded high fit. |

Net result: 1 gap closed, 1 partially addressed with a language mismatch, 4 still open. The four open ones stay authored probes in R2 and R3 as 07 planned. That plan does not need to change, and the registry sweep now gives it a stronger basis than a local library scan alone.

One secondary finding matters for the R1 threat model. The registry is full of skill-supply-chain content: `clawhub/clawhub-skill-scanner`, `clawguard-scanner`, `clawskillguard`, `dcl-skill-auditor`, `agenttrust-scanner`, and one entry whose own description claims "534 out of 3,984 ClawHub skills contained critical vulns". Every item in this file is therefore a dependency on an untrusted author. The two install candidates I recommend are read before install, and the four low quality entries I cut are cut partly on that basis. No skill in this sweep was installed or executed.

## 7. TOP 5 SHORTLIST

Ranked by how much R3 and R2 time each one saves, with the score for the target only, not for security work in general.

| Rank | Skill | ID | Fit | Verdict | Why this one |
|---|---|---|---|---|---|
| 1 | csp-bypass-advanced | `skills-sh/yaklang/hack-skills/csp-bypass-advanced` | High | Install candidate | Directly arms the R3 CSP class that 07 listed as uncovered. Its directive matrix reframes the test: with `connect-src 'none'`, the question becomes what still leaves the page without a network call, which is dangling markup and navigation, not fetch. 2,706 star repo, pushed 2026-09-13. |
| 2 | Frontend Security Review | `clawhub/@bovinphang/fec-security-review` | High | Install candidate, read before install | Supplies the review protocol for a page that is entirely frontend, with explicit scope modes and a rule that scope is stated before any diff is read. That discipline maps onto a one file target with no diff. Publisher identity unverified. |
| 3 | csp-policy-generator | `clawhub/@charlie-morrison/csp-policy-generator` | High | Install candidate, read before install | Answers the R2 decision 07 left open: replace `script-src 'unsafe-inline'` with a hash or nonce and prove the page still works, with a report-only step before enforcement. Lowest confidence of the three installs because there is no repo and no install count. |
| 4 | zeroize-audit | `skills-sh/trailofbits/skills/zeroize-audit` | Medium | Adapt into an authored skill | The only real zeroization content in 105,676 skills, from the highest credibility author in the set, 5,634 installs, pushed 2026-11-25. Do not install as written: port the invariant and the control flow proof, and replace its assembly step with a Chromium heap snapshot retention check. |
| 5 | fuzzing-dictionary | `skills-sh/trailofbits/skills/fuzzing-dictionary` | Medium | Adapt into an authored skill | Turns the `unpack` and SDP parser probes from random bytes into structurally valid hostile inputs, which is the difference between a red team that finds a parser bug and one that reports "no issues". Harness must be authored for Node or Playwright. |

Honourable mentions that did not make the five: `offensive-anti-forensics` (11,616 star repo, but a Windows and Linux playbook used backwards as an artifact checklist), `node-quic-dtls` (authoritative DTLS mental model, wrong runtime), `burpsuite-project-parser` (unusable without a paid Burp licence, but its "empty output is not a clean result" rule is worth copying into R3).

Not run, deliberately: `hermes skills install <id>` for any of the above. This lane is read only. The R2 owner should read the body of each candidate from its detail page before installing, and should install at most items 1 to 3, adapting 4 and 5 into the engagement's own probe skill.

## 8. SELF-CHECK

| Acceptance item | Verdict | Evidence |
|---|---|---|
| Every listed skill comes from a live registry query actually run, with the query quoted | PASS | Section 2 lists the 24 required and 15 supplementary query strings verbatim with result counts read from saved JSON at `/Users/marcelspatz/.hermes/cache/scratch/w3-registry/search_*.json`, `x_*.json` and `y_*.json`. Every identifier in sections 3, 4 and 7 was copied from those files, not typed from memory. |
| Every row carries the full criteria set (name, id or URL, what it encodes, compatibility verdict, quality signals, fit, final verdict) | PASS | Sections 3.1 to 3.8 use a per skill field table with all seven fields. Section 4 rows carry query, representatives, fit, reason and verdict, because the shared reason is what makes those rows cuttable; the seven field detail is applied in full to every item that was not cut. |
| The catalogue is deduped and counted, not eyeballed | PASS | `combined_all.json` built in Python from every saved search JSON: 757 unique identifiers across all queries, 627 from the required pass alone. Source split clawhub 466, skills.sh 245, official 18, github 17, browse-sh 11. |
| Recency and popularity are verified, not estimated | PASS | Install counts parsed from skills.sh search descriptions. GitHub stars and `pushed_at` read from `https://api.github.com/repos/<owner>/<repo>` for trailofbits/skills (8,458 stars, pushed 2026-11-25), snailsploit/claude-red (11,616, 2026-11-17), jasnell/node-skills (78, 2026-11-16), manyuegong33/r0crawl_skills (382, 2026-09-20), yaklang/hack-skills (2,706, 2026-09-13), mukul975/anthropic-cybersecurity-skills (36,821, 2026-08-31). |
| `hermes skills browse` wider pass was run | PASS | `hermes skills browse --page 1 --size 100` returned "105676 skills loaded, page 1/1057". `hermes skills browse --source official --size 200` and page 2 returned 162 official skills across 2 pages. |
| `hermes skills inspect` was run on the strongest hits | PASS | 14 successes, 13 saved under `insp/`. Two `webrtc-patterns` attempts failed and are marked UNVERIFIED in section 3.2. |
| MCP catalog checked, and the `hermes mcp` subcommand existence tested | PASS | `hermes mcp --help` exits 0 and lists `catalog` and `list`. `hermes mcp catalog` printed 88 lines: 66 catalog entries and 9 configured custom servers, full text at `mcp_catalog.txt`. Section 5 grades the 5 security or network relevant entries. A keyword scan of that output for pentest, nmap, burp, fuzz, proxy, packet, capture, webrtc, exploit and red team returned 0 matches, so the claim that no pentest or WebRTC server exists is measured, not assumed. |
| File ends with a TOP 5 SHORTLIST for this engagement | PASS | Section 7 is the TOP 5, ranked, with per item fit, verdict and reason. The SELF-CHECK block is placed after it only because the brief also mandates that SELF-CHECK be the final section; section 7 is the last substantive content and the last forward looking content. |
| Read only, no installs or mutating subcommands | PASS | Only `search`, `browse`, `inspect`, `mcp catalog` and `mcp --help` were run against the CLI, plus `skills --help` variants. No `install`, `uninstall`, `update`, `audit`, `publish`, `snapshot`, `tap`, `config`, `trust` or `reset`. The only writes are the scratch JSON under `/Users/marcelspatz/.hermes/cache/scratch/w3-registry/` and this output file, which the brief permits. |
| English, no em dashes and no en dashes | PASS | `grep -c $'\u2014'` and `grep -c $'\u2013'` on the assembled file both return 0. Command output is quoted in the verification block below. |
| Every external claim carries a source URL, uncheckable items marked UNVERIFIED | PASS | Registry rows cite the skills.sh detail URL and the GitHub repo. ClawHub entries whose host path could not be resolved from the CLI are marked UNVERIFIED on the URL and on publisher identity. `webrtc-patterns`, `crypto-protocol-diagram` body, `fec-browser-storage` body and the `node:dtls` version facts are marked UNVERIFIED where not inspected. |
| Incremental writes | PASS | Four part files were written in sequence (`part1.md`, `part2.md`, `part3.md`, `part4.md`, `part5.md`) and assembled at the end. |
| Time budget respected | PASS | Roughly 22 minutes of tool work. `STATUS: complete`, not partial. |

Verification commands run against the assembled file, with actual results:

```
grep -c $'\u2014' 08-registry-skills.md             -> 0
grep -c $'\u2013' 08-registry-skills.md             -> 0
grep -c 'TOP 5 SHORTLIST' 08-registry-skills.md     -> 1
grep -c '^## 8. SELF-CHECK' 08-registry-skills.md   -> 1
identifier audit                                    -> 90 backticked identifiers, 89 resolved, 1 prose ellipsis
```

The identifier audit extracts every backticked token shaped like a registry id from the finished file, then checks membership in the union of the saved search JSON. It resolves 40 verbatim, 49 more through the two documented conventions in section 2 (ClawHub bare slugs, collection prefixes), and leaves exactly one unmatched string, `skills-sh/...`, which is a prose ellipsis in section 4 and not an identifier. Zero fabricated identifiers.

End of file.
