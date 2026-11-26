# 09 Open security skill collections outside the Hermes registries

RUN ID: w3-ephemeral-skills-20261126
LANE: open-collections
TARGET: single-file WebRTC chat, `/Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/input/ephemeral-chat-v1.html`
STATUS: complete

Scope: security, pentest and red-team skill collections that ship the SKILL.md format Hermes loads, found outside the locally installed Hermes skill tree. The local tree is already covered in `07-skill-sweep.md` and is not re-enumerated here. Nothing was installed, cloned or modified. Every URL below was fetched or queried in this session.

## 1. Method

Four discovery passes, all read only:

1. `hermes skills search` and `hermes skills inspect` against the live registries (skills.sh, ClawHub, URL sources). Inspect only, never install.
2. `gh api` repository metadata and recursive git trees for star count, last push, license and the exact list of `SKILL.md` paths inside each collection.
3. `gh search code` with `--filename SKILL.md` for the capability terms this engagement needs: webrtc, dtls, denial of service phrasing, content-security-policy, zeroize, session wipe.
4. `web_search` and `web_extract` on the awesome-list indexes, then direct `curl` of raw `SKILL.md` files to confirm the content matches the description before grading it.

Grading scale, applied per skill:

- Hermes compatibility: `native` (resolves through `hermes skills inspect` or is a plain SKILL.md folder), `adapt` (loads but its paths, tool names or host conventions do not fit this profile), `method only` (not a SKILL.md, or too host-specific to load).
- Engagement fit: `high` (directly covers a surface the R3 red team will probe), `medium` (covers adjacent procedure or a technique that transfers), `low` (generic or duplicate), `none` (cut).
- Final verdict: `install candidate` (worth a read-only install for R1 to R3), `adapt into authored skill` (harvest the procedure, write our own), `reference only` (read for technique, do not install).

## 2. What "installable" actually means here

Verified behaviour, not assumption:

- `hermes skills install` takes an identifier of the form `owner/repo/skill-name` or a direct HTTPS URL to a SKILL.md file (`hermes skills install --help`, run in this session).
- A direct raw URL resolves: `hermes skills inspect https://raw.githubusercontent.com/trailofbits/skills/main/plugins/zeroize-audit/skills/zeroize-audit/SKILL.md` returned `Source: url` with the parsed frontmatter. Inferred from the CLI contract, and not measured because installing was out of scope: a URL install fetches the single SKILL.md, so any `references/` or `scripts/` folder beside it is lost. Both `zeroize-audit` and `crypto-protocol-diagram` depend on those folders.
- An indexed repository path resolves through skills.sh: `hermes skills inspect trailofbits/skills/zeroize-audit` returned `Identifier: skills-sh/trailofbits/skills/zeroize-audit` and `Repo: https://github.com/trailofbits/skills`.
- Claude-Red is indexed too: `hermes skills inspect SnailSploit/Claude-Red/offensive-xss` returned `Identifier: skills-sh/SnailSploit/Claude-Red/offensive-xss`.
- Consequence for the plan: anything graded `install candidate` below installs natively from its GitHub source. Anything whose value sits in `references/` must be adapted into an authored skill instead, because the one-file install would strip the material that makes it useful.

## 3. Anthropic official sources

### 3.1 anthropics/skills

URL: https://github.com/anthropics/skills
Quality signals: official Anthropic repository, 200,994 stars, last push 2026-11-16, no license declared in the API response. 19 skills plus a template, verified from the recursive tree.
What it encodes: document and artifact skills (docx, pdf, pptx, xlsx), creative and design skills, `mcp-builder`, `skill-creator`, `webapp-testing`, `brand-guidelines`, `internal-comms`.
Security content: none. There is no security, pentest, threat-model or crypto skill in the repository. This is the single most important negative result of the lane, because it kills the assumption that Anthropic ships official security skills.

| Skill | Source URL | What it encodes | Hermes compatibility | Quality signals | Fit | Verdict |
|---|---|---|---|---|---|---|
| webapp-testing | https://github.com/anthropics/skills/tree/main/skills/webapp-testing | Browser automation via Playwright, recon then action, `with_server.py` helper | native, already installed in this profile | Anthropic official, 200,994 star repo | medium, it is the R4 driver for two peer contexts | reference only, the installed copy is the same skill |

### 3.2 anthropics/claude-code-security-review

URL: https://github.com/anthropics/claude-code-security-review
Quality signals: Anthropic official, 7,138 stars, MIT, last push 2026-02-11. Recursive tree contains `action.yml`, `claudecode/`, `.github/workflows/sast.yml` and `.claude/commands/security-review.md`. Count of `SKILL.md` files: 0.
What it encodes: a GitHub Action and a slash command that run Claude over a pull request diff and emit security findings.
Compatibility: not a skill. It cannot be loaded by `hermes skills install` because there is no SKILL.md and no skill folder.

| Item | Source URL | What it encodes | Hermes compatibility | Quality signals | Fit | Verdict |
|---|---|---|---|---|---|---|
| security-review command | https://github.com/anthropics/claude-code-security-review/blob/main/.claude/commands/security-review.md | Diff scoped security review prompt with a category list and false-positive suppression rules | method only, not a SKILL.md | Anthropic official, 7,138 stars, MIT, dormant since 2026-02 | medium, the diff-review prompt transfers to R5 patch review | reference only |

## 4. Awesome lists and indexes

These are discovery surfaces, not skill collections. Each row grades the index itself, and the collections it points at are graded in sections 5 and 6.

| Index | Source URL | What it encodes | Hermes compatibility | Quality signals | Fit | Verdict |
|---|---|---|---|---|---|---|
| awesome-security-skills | https://github.com/securityfortech/awesome-security-skills | The only index in this lane dedicated to security skills. 11 repository entries across offensive, secure code review and SOC | not installable, it is a README | 5 stars, CC0, created 2026-03-11, last push 2026-03-29, single maintainer | high as a map, it found four collections this lane would otherwise have missed | reference only |
| awesome-claude-skills | https://github.com/travisvn/awesome-claude-skills | General Claude skill index, official skills plus community tooling, updated badge says Feb 2026 | not installable | 15,948 stars, 2,195 forks, last push 2026-04-28, no license declared | low, no security category at all | reference only |
| awesome-claude-code | https://github.com/hesreallyhim/awesome-claude-code | Broad Claude Code resource list, agents, status lines, plugins | not installable | 58,865 stars, last push 2026-11-26, very active | low, security is a thin slice and nothing WebRTC or client-crypto specific | reference only |
| agentic-awesome-skills | https://github.com/sickn33/agentic-awesome-skills | 3,000+ skill mirror, includes a copy of `zeroize-audit` at `skills/zeroize-audit/SKILL.md` | native, indexed | 50,394 stars, MIT, last push 2026-11-26 | medium, but it is a redistribution | reference only, use the Trail of Bits upstream instead |
| claude-skill-registry | https://github.com/majiayu000/claude-skill-registry | Generated catalogue with duplicates, for example `skills/security/zeroize-audit/SKILL.md` and three near copies under `skills/other/` | native, indexed | 754 stars, MIT, last push 2026-11-26 | low, dedupe cost is high | reference only |
| awesome-skills (gmh5225) | https://github.com/gmh5225/awesome-skills | Broad index plus a meta skill `.claude/skills/security-skills/SKILL.md` that categorises security skills | native for the meta skill | 100 stars, MIT, last push 2026-10-24 | low, the meta skill is a taxonomy, not a procedure | reference only |
| awesome-openclaw-skills | https://github.com/sundial-org/awesome-openclaw-skills | Popular OpenClaw and ClawHub skills | native, ClawHub source | 676 stars, last push 2026-03-07 | low, no security pack of note | reference only |

## 5. ClawHub

Homepage: https://clawhub.ai (HTTP 200 in this session, title "Tools for your agents"). It is a publishing registry with an official creators section, a skill CLI (`npm i -g clawhub`, `clawhub skill publish`) and skill pages under `/skills?q=`.
Quality signals: no visible review gate, no star count, and near duplicate entries are common. `nmap-pentest-scans` and `nmap-pentest-scans-hardened` are the same skill published twice by the same author (`@0x-professor`), which is a reliable signal that publishing is unmoderated.
What it encodes: a mixed bag of narrow operational skills, mostly tool wrappers (Nmap plans, AWS Shield configuration, ReDoS auditing).
Hermes compatibility: native. `hermes skills inspect nmap-pentest-scans` resolved to `Identifier: @0x-professor/nmap-pentest-scans`, `Source: clawhub`.

Note on the CTF entries: `hermes skills search ctf` lists `ctf-misc`, `ctf-malware` and `ctf-osint` as `clawhub community`, but `hermes skills inspect ctf-misc` resolves the canonical source to `skills-sh/ljagiello/ctf-skills/ctf-misc` with `Repo: https://github.com/ljagiello/ctf-skills`. ClawHub is mirroring the skills.sh entry. Grade it once, under section 6.

| Skill | Source URL | What it encodes | Hermes compatibility | Quality signals | Fit | Verdict |
|---|---|---|---|---|---|---|
| nmap-pentest-scans | https://clawhub.ai/skills?q=nmap | PTES 2-3 and MITRE TA0007 aligned Nmap host, port and service enumeration with reporting artifacts | native | author `@0x-professor`, community trust, duplicate hardened variant published | low, the target is one local HTML file with no listening service | reference only, cut from the round plan |
| phy-regex-audit | https://clawhub.ai/skills?q=denial+of+service | Static ReDoS audit of regular expressions | native | community, no popularity signal | medium, the invite code parser and the frame parser both take attacker regex-adjacent input, and ReDoS is the one DoS shape that exists in a single page | install candidate, read only, for the R3 parser probe |
| shieldadvanced | https://clawhub.ai/skills?q=denial+of+service | Configures AWS Shield Advanced | native | community | none, there is no cloud account or edge in this product | cut |

## 6. Security skill collections

### 6.1 SnailSploit/Claude-Red

URL: https://github.com/SnailSploit/Claude-Red
Quality signals: 11,615 stars, MIT, last push 2026-11-17, 79 SKILL.md files, one per attack surface, organised by domain (web, crypto, exploit-dev, forensics, wireless, active-directory). Indexed by skills.sh, so `hermes skills install SnailSploit/Claude-Red/<skill>` resolves natively.
What it encodes: offensive methodology per surface, written as operator procedure with tool commands, not as a checklist. Strongest on web and wireless. Weakest on anything requiring a live host, and it has no denial-of-service skill at all.

| Skill | Source URL | What it encodes | Hermes compatibility | Quality signals | Fit | Verdict |
|---|---|---|---|---|---|---|
| offensive-xss | https://github.com/SnailSploit/Claude-Red/blob/main/Skills/web/offensive-xss/SKILL.md | Stored, reflected, DOM and blind XSS, polyglots, filter bypass, DOM clobbering, mutation XSS, and CSP bypass | native, indexed | Claude-Red, MIT, 2026-11 | high, the app ships `script-src 'unsafe-inline'` and renders peer supplied text, so CSP bypass and DOM clobbering are live surfaces | install candidate |
| offensive-crypto-attacks | https://github.com/SnailSploit/Claude-Red/blob/main/Skills/crypto/offensive-crypto-attacks/SKILL.md | Mode misuse, nonce and IV reuse, padding oracles, key derivation weaknesses, downgrade and oracle attacks | native, indexed | Claude-Red, MIT, 2026-11 | high, R1 designs AES-GCM with epochs and R3 probes replay and rollback, which is exactly the nonce reuse class | install candidate |
| offensive-race-condition | https://github.com/SnailSploit/Claude-Red/blob/main/Skills/web/offensive-race-condition/SKILL.md | Race windows, TOCTOU, concurrent request and state confusion, single packet attack technique | native, indexed | Claude-Red, MIT, 2026-11 | high, chunk reassembly and rekey are concurrent state machines, and a duplicate index or a rekey during transfer is a race | install candidate |
| offensive-tls-attacks | https://github.com/SnailSploit/Claude-Red/blob/main/Skills/crypto/offensive-tls-attacks/SKILL.md | Protocol downgrade, BEAST, CRIME and BREACH, certificate validation and pinning bypass, TLS 1.3 0-RTT replay, mTLS relay | native, indexed | Claude-Red, MIT, 2026-11 | medium, the browser owns DTLS, so most of it does not apply, but the 0-RTT replay and certificate validation reasoning transfers to the pairing and fingerprint question | install candidate |
| offensive-anti-forensics | https://github.com/SnailSploit/Claude-Red/blob/main/Skills/forensics/offensive-anti-forensics/SKILL.md | Artifact elimination and trace minimisation across host and browser surfaces | native, indexed | Claude-Red, MIT, 2026-11 | medium, it is the attacker side of the R4 trace check, useful to enumerate what a Chromium session leaves behind before asserting the app leaves nothing | install candidate |
| offensive-reporting | https://github.com/SnailSploit/Claude-Red/blob/main/Skills/utility/offensive-reporting/SKILL.md | Finding write-up structure, severity, reproduction, evidence | native, indexed | Claude-Red, MIT, 2026-11 | medium, duplicates the installed `vulnerability-writeup` | reference only |
| offensive-fast-checking | https://github.com/SnailSploit/Claude-Red/blob/main/Skills/utility/offensive-fast-checking/SKILL.md | Triage heuristics for discarding low value leads quickly | native, indexed | Claude-Red, MIT, 2026-11 | medium, useful in R3 when 20 probes return noise | reference only |

Also reviewed inside this collection and cut on fit: offensive-waf-bypass, offensive-network-attacks, offensive-osint-methodology, offensive-data-exfiltration, offensive-lateral-movement, offensive-edr-evasion, and all 14 wireless skills. None maps to a serverless browser to browser app.

### 6.2 trailofbits/skills

URL: https://github.com/trailofbits/skills
Quality signals: 8,458 stars, CC-BY-SA-4.0, last push 2026-11-25, 97 SKILL.md files under `plugins/<plugin>/skills/<skill>/`. Professional audit firm, the only collection in this lane with a real zeroization and constant-time capability.
What it encodes: audit-grade procedures with reference tables, scripts and multi phase orchestration. The zeroization skill runs Phases 0 to 8 with per translation unit compilation and assembly inspection.

| Skill | Source URL | What it encodes | Hermes compatibility | Quality signals | Fit | Verdict |
|---|---|---|---|---|---|---|
| zeroize-audit | https://github.com/trailofbits/skills/blob/main/plugins/zeroize-audit/skills/zeroize-audit/SKILL.md | Detects missing zeroization and zeroization removed by compiler optimisation, via assembly and control-flow verification | native, indexed (`skills-sh/trailofbits/skills/zeroize-audit`), but its phases need `schemas/` and `workflows/` beside it, so a single URL install loses them | Trail of Bits, CC-BY-SA-4.0, 2026-11-25 | high, zeroization is the number one library gap and this is the only serious treatment found. It targets C, C++ and Rust. A browser has no `memset` elision, so the JS answer is different, but its taxonomy of what counts as wiped is the right frame | adapt into authored skill for JavaScript and WebCrypto, reference only for the C and Rust phases |
| mutation-testing | https://github.com/trailofbits/skills/blob/main/plugins/mutation-testing/skills/mutation-testing/SKILL.md | Mutation testing workflow, mutation operators, survival triage | native, indexed | Trail of Bits, 2026-11 | high, the R2 gate is literally a hand run mutation test, and this skill supplies the operator taxonomy so the gate is not just one revert | install candidate |
| cvss-scoring | https://github.com/trailofbits/skills/blob/main/plugins/cvss-scoring/skills/cvss-scoring/SKILL.md | CVSS vector selection with justification, avoiding inflated scores | native, indexed | Trail of Bits, 2026-11 | medium, R3 needs consistent severity, and the app has no server, so calibration matters | install candidate |
| fp-check | https://github.com/trailofbits/skills/blob/main/plugins/fp-check/skills/fp-check/SKILL.md | False positive adjudication before a finding is published | native, indexed | Trail of Bits, 2026-11 | high, this is the bypass exhaustion discipline the red team needs before calling a probe clean | install candidate |
| differential-review | https://github.com/trailofbits/skills/blob/main/plugins/differential-review/skills/differential-review/SKILL.md | Review a diff for security regressions, change scoped rather than file scoped | native, indexed | Trail of Bits, 2026-11 | medium, R2 and R5 each produce a diff on one file | install candidate |
| crypto-protocol-diagram | https://github.com/trailofbits/skills/blob/main/plugins/trailmark/skills/crypto-protocol-diagram/SKILL.md | Build protocol and crypto diagrams from source, sequence and state | native, indexed | Trail of Bits, 2026-11 | medium, a DTLS and pairing sequence diagram is the clearest artifact for the R1 blueprint and the R3 report | reference only, it is part of the trailmark plugin and expects a codebase |
| constant-time-analysis | https://github.com/trailofbits/skills/blob/main/plugins/constant-time-analysis/skills/constant-time-analysis/SKILL.md | Detect timing side channels in crypto code by inspecting emitted assembly or bytecode, with a JavaScript and TypeScript guide | native, indexed | Trail of Bits, 2026-11 | medium, WebCrypto hides the primitives, but key comparison and code comparison in the pairing gate are ours and can be variable time | install candidate |
| sharp-edges | https://github.com/trailofbits/skills/blob/main/plugins/sharp-edges/skills/sharp-edges/SKILL.md | Dangerous defaults and footguns in APIs and libraries | native, indexed | Trail of Bits, 2026-11 | medium, WebCrypto defaults, `crypto.randomUUID` misuse and object URL lifetime are exactly this class | install candidate |
| property-based-testing | https://github.com/trailofbits/skills/blob/main/plugins/property-based-testing/skills/property-based-testing/SKILL.md | Property design, generators, shrinking for parser and protocol code | native, indexed | Trail of Bits, 2026-11 | medium, the invite code parser and frame parser are ideal property targets, round trip plus rejection | install candidate |
| vuln triage brocards | https://github.com/trailofbits/skills/blob/main/plugins/vulnerability-triage-brocards/skills/vulnerability-triage-brocards/SKILL.md | Triage decision cards for candidate findings | native, indexed | Trail of Bits, 2026-11 | medium, R3 to R5 routing | reference only |

Also reviewed and cut: the 13 `testing-handbook-skills` fuzzers (C and Rust harnesses, no browser target), `building-secure-contracts` (12 blockchain skills), `yara-authoring`, `burpsuite-project-parser`, `agentic-actions-auditor`, `supply-chain-risk-auditor`.

### 6.3 mukul975/Anthropic-Cybersecurity-Skills

URL: https://github.com/mukul975/Anthropic-Cybersecurity-Skills
Quality signals: 36,820 stars, Apache-2.0, 818 SKILL.md files across 29 domains, each with `references/` and `scripts/`, mapped to MITRE ATT&CK, NIST CSF 2.0 and ATLAS. Last push 2026-08-31, so roughly three months stale at the time of this run. Owner is `mukul975`, not Anthropic; the name describes the format it follows, the agentskills.io standard.
What it encodes: task shaped defensive and offensive procedures with framework mappings in the frontmatter. Breadth is enormous and per skill depth is moderate. This is the only collection found with a CSP bypass skill and a browser forensics skill.

| Skill | Source URL | What it encodes | Hermes compatibility | Quality signals | Fit | Verdict |
|---|---|---|---|---|---|---|
| performing-content-security-policy-bypass | https://github.com/mukul975/Anthropic-Cybersecurity-Skills/blob/main/skills/performing-content-security-policy-bypass/SKILL.md | CSP directive analysis, bypass classes, reporting endpoint abuse, nonce and hash weaknesses | native, indexed | 818 skill pack, Apache-2.0, ATT&CK mapped, 2026-08 | high, the app ships `script-src 'unsafe-inline'` and the R2 fix must choose a hash or nonce, so this is both attack and verification material | install candidate |
| analyzing-browser-forensics-with-hindsight | https://github.com/mukul975/Anthropic-Cybersecurity-Skills/blob/main/skills/analyzing-browser-forensics-with-hindsight/SKILL.md | Parses Chromium history, downloads, cookies, cache, autofill, saved passwords, local storage, session and tab state into a timeline | native, indexed | same pack, ATT&CK T1217 and T1539 mapped | high, R4 must prove no recoverable transcript after reload and no trace on macOS. This tells the prober exactly which Chromium artifacts to inspect | install candidate |
| performing-cryptographic-audit-of-application | https://github.com/mukul975/Anthropic-Cybersecurity-Skills/blob/main/skills/performing-cryptographic-audit-of-application/SKILL.md | Crypto inventory, algorithm and parameter review, key management and rotation review | native, indexed | same pack | high, R1 is adding app layer crypto from zero, and key rotation plus epochs is the stated owner requirement | install candidate |
| testing-websocket-api-security | https://github.com/mukul975/Anthropic-Cybersecurity-Skills/blob/main/skills/testing-websocket-api-security/SKILL.md | Handshake, message framing, origin checks, injection over frames, flood and resource exhaustion | native, indexed | same pack | medium, a WebRTC data channel is not a WebSocket, but frame confusion and flood procedure map one to one | install candidate |
| exploiting-websocket-vulnerabilities | https://github.com/mukul975/Anthropic-Cybersecurity-Skills/blob/main/skills/exploiting-websocket-vulnerabilities/SKILL.md | Exploitation recipes for the same surface | native, indexed | same pack | medium, same mapping caveat | reference only |
| performing-privacy-impact-assessment | https://github.com/mukul975/Anthropic-Cybersecurity-Skills/blob/main/skills/performing-privacy-impact-assessment/SKILL.md | Data flow inventory, minimisation, retention and reidentification analysis | native, indexed | same pack | medium, it gives R1 a vocabulary for the no persistence, no server claim | reference only |
| implementing-ddos-mitigation-with-cloudflare | https://github.com/mukul975/Anthropic-Cybersecurity-Skills/blob/main/skills/implementing-ddos-mitigation-with-cloudflare/SKILL.md | Edge rate limiting, L3 to L7 mitigation | native, indexed | same pack | none, there is no edge and no server | cut |
| performing-ssl-tls-security-assessment | https://github.com/mukul975/Anthropic-Cybersecurity-Skills/blob/main/skills/performing-ssl-tls-security-assessment/SKILL.md | testssl.sh style TLS assessment | native, indexed | same pack | low, there is no TLS endpoint to scan | cut |

### 6.4 briiirussell/cybersecurity-skills

URL: https://github.com/briiirussell/cybersecurity-skills
Quality signals: 536 stars, MIT, last push 2026-11-23, 42 SKILL.md files, installable via `npx skills` or the Claude plugin marketplace. Each skill is a real procedure with grep patterns and framework mapping, not a link list. Author is a working security engineer; the repo has a skill template and eval triggers, which is a maturity signal.
What it encodes: red, blue and purple team procedures plus audit and compliance mapping.

| Skill | Source URL | What it encodes | Hermes compatibility | Quality signals | Fit | Verdict |
|---|---|---|---|---|---|---|
| crypto-audit | https://github.com/briiirussell/cybersecurity-skills/blob/main/skills/crypto-audit/SKILL.md | Algorithm and mode choice, key sizes, KDF parameters, IV and nonce handling, signature verification, randomness, TLS config, key rotation. Explicitly defaults custom crypto to "use WebCrypto" | native, indexed | 536 stars, MIT, 2026-11-23 | high, it is the closest match to the R1 crypto design review and it names WebCrypto as the default, which is the decision this app faces | install candidate |
| privacy-engineering | https://github.com/briiirussell/cybersecurity-skills/blob/main/skills/privacy-engineering/SKILL.md | Data minimisation, retention, deletion and trace reduction in product design | native, indexed | same repo | medium, the zero trace claim in R4 needs a privacy engineering frame, not only a forensics check | install candidate |
| personal-opsec | https://github.com/briiirussell/cybersecurity-skills/blob/main/skills/personal-opsec/SKILL.md | Operational security for an individual operator, metadata and identity hygiene | native, indexed | same repo | medium, maps to the local trace minimisation requirement on macOS | reference only |
| red-team-engagement | https://github.com/briiirussell/cybersecurity-skills/blob/main/skills/red-team-engagement/SKILL.md | Engagement scoping, rules of engagement, objectives, reporting for a red team | native, indexed | same repo | medium, duplicates the installed web-pentest guardrails | reference only |
| fuzzing-harness | https://github.com/briiirussell/cybersecurity-skills/blob/main/skills/fuzzing-harness/SKILL.md | Harness design and property tests for encoders and decoders | native, indexed | same repo | medium, the invite code pack and unpack path is the target | reference only |
| agent-supply-chain-audit | https://github.com/briiirussell/cybersecurity-skills/blob/main/skills/agent-supply-chain-audit/SKILL.md | Audits what an agent loads, hidden instructions, invisible Unicode, unpinned MCP servers, exfil hooks | native, indexed | same repo | low for the app, medium for this research lane itself, since it is the check to run before installing any skill from this file | reference only |

### 6.5 transilienceai/communitytools

URL: https://github.com/transilienceai/communitytools
Quality signals: 638 stars, MIT, last push 2026-07-29, 50 SKILL.md files plus 35 agents and 264 PortSwigger lab walkthroughs. Broad but shallow per skill, and several skills are thin tables.

| Skill | Source URL | What it encodes | Hermes compatibility | Quality signals | Fit | Verdict |
|---|---|---|---|---|---|---|
| client-side | https://github.com/transilienceai/communitytools/blob/main/skills/client-side/SKILL.md | XSS, CSRF, CORS, clickjacking, DOM sinks, prototype pollution, and the defence enumeration step including CSP and Trusted Types | native, indexed | 638 stars, MIT, 2026-07 | medium, the source, sink and defence enumeration step is the right shape for the DOM surface, but it is one page of tables | adapt into authored skill |
| cryptography | https://github.com/transilienceai/communitytools/blob/main/skills/cryptography/SKILL.md | Crypto testing checklist | native, indexed | same repo | medium, thinner than briiirussell crypto-audit | reference only |
| pentest-engagement | https://github.com/transilienceai/communitytools/blob/main/skills/pentest-engagement/SKILL.md | Engagement lifecycle and scoping | native, indexed | same repo | medium, duplicates installed web-pentest | reference only |
| web-app-logic | https://github.com/transilienceai/communitytools/blob/main/skills/web-app-logic/SKILL.md | Business logic testing patterns | native, indexed | same repo | low, the app has almost no business logic | cut |

### 6.6 florianbuetow/claude-code, appsec plugin

URL: https://github.com/florianbuetow/claude-code (plugin at `plugins/appsec/`)
Quality signals: 21 stars, MIT, last push 2026-10-06, 133 SKILL.md files in the repository. Small audience, but the most systematic threat catalogue found: one skill per STRIDE letter, per PASTA step, plus per vulnerability family. Skills reference `../../shared/schemas/flags.md`, so they only work inside the plugin tree.

| Skill | Source URL | What it encodes | Hermes compatibility | Quality signals | Fit | Verdict |
|---|---|---|---|---|---|---|
| dos | https://github.com/florianbuetow/claude-code/blob/main/plugins/appsec/skills/dos/SKILL.md | STRIDE D analysis: resource exhaustion, algorithmic complexity, zip bombs, unbounded operations, with a file scope filter that names WebSocket handlers and long lived connections | adapt, it reads `../../shared/schemas/` and `../../shared/frameworks/stride.md` | MIT, 2026-10, small repo | high, this is the only denial-of-service procedure found in any collection, and it covers decompression bombs, which the invite code path uses | adapt into authored skill |
| race-conditions | https://github.com/florianbuetow/claude-code/blob/main/plugins/appsec/skills/race-conditions/SKILL.md | Concurrency and TOCTOU analysis for request handlers | adapt | same repo | medium, chunk reassembly state machine | reference only |
| websocket | https://github.com/florianbuetow/claude-code/blob/main/plugins/appsec/skills/websocket/SKILL.md | Message framing and long lived connection review | adapt | same repo | medium, closest structural analogue to the data channel | reference only |
| crypto | https://github.com/florianbuetow/claude-code/blob/main/plugins/appsec/skills/crypto/SKILL.md | Crypto misuse review | adapt | same repo | medium, duplicate of stronger skills above | reference only |
| harden | https://github.com/florianbuetow/claude-code/blob/main/plugins/appsec/skills/harden/SKILL.md | Turns findings into hardening recommendations | adapt | same repo | medium, R5 | reference only |
| serverless | https://github.com/florianbuetow/claude-code/blob/main/plugins/appsec/skills/serverless/SKILL.md | Serverless specific attack surface | adapt | same repo | none, serverless here means no server at all | cut |

### 6.7 hassan-algo/open-sesame

URL: https://github.com/hassan-algo/open-sesame
Quality signals: 107 stars, NOASSERTION license (check before reuse), last push 2026-10-22, 2 skills each with `references/`, `assets/`, `scripts/render-report.sh` and `evals/`. Evals plus a PDF renderer is unusually complete for a small repo. This is the closest open analogue to the installed `web-pentest` skill, and it is richer in reporting.

| Skill | Source URL | What it encodes | Hermes compatibility | Quality signals | Fit | Verdict |
|---|---|---|---|---|---|---|
| web-pentest | https://github.com/hassan-algo/open-sesame/blob/main/.claude/skills/web-pentest/SKILL.md | OWASP WSTG across recon, config, auth, session, access control, injection, crypto, business logic, client side and API, with safe RCE validation and three report audiences | native SKILL.md, but the value is in `references/`, so a single file install is lossy | 107 stars, 2026-10, evals present, license unclear | high, the multi audience report and the WSTG phase order are better than what is installed, and client side plus crypto phases cover two gap areas | adapt into authored skill |
| net-pentest | https://github.com/hassan-algo/open-sesame/blob/main/.claude/skills/net-pentest/SKILL.md | PTES and NIST 800-115 network testing, Active Directory, pivoting, wireless, containers | native SKILL.md, needs its references | same repo | none, no network or directory in scope | cut |

### 6.8 securityfortech/hacking-skills

URL: https://github.com/securityfortech/hacking-skills
Quality signals: 28 stars, last push 2026-03-15, 43 SKILL.md files organised as `skills/<platform>/<class>/<skill>/`. Checked-in frontmatter is consistent. Low popularity, decent taxonomy, and it is the only pack with a dedicated client-side path traversal skill and a DOM XSS skill.

| Skill | Source URL | What it encodes | Hermes compatibility | Quality signals | Fit | Verdict |
|---|---|---|---|---|---|---|
| cspt | https://github.com/securityfortech/hacking-skills/blob/main/skills/web/client-side/cspt/SKILL.md | Client side path traversal, gadget chaining from a DOM sink to a fetch or navigation | native | 28 stars, 2026-03 | medium, the app has no fetch sink and `connect-src 'none'`, so the gadget chain is short, but the sink enumeration transfers | reference only |
| dom-xss | https://github.com/securityfortech/hacking-skills/blob/main/skills/web/client-side/dom-xss/SKILL.md | DOM source to sink tracing, `innerHTML` and `insertAdjacentHTML` abuse | native | same repo | high, the message render path is DOM based and peer controlled | install candidate |
| cors-misconfig | https://github.com/securityfortech/hacking-skills/blob/main/skills/web/client-side/cors-misconfig/SKILL.md | CORS origin and credential misconfiguration | native | same repo | low, there is no server and no cross origin request | cut |
| clickjacking | https://github.com/securityfortech/hacking-skills/blob/main/skills/web/client-side/clickjacking/SKILL.md | Frame based UI redress against the wipe and send buttons | native | same repo | medium, the kill switch and wipe button are UI redressing targets if the page is ever framed | reference only |

### 6.9 Eyadkelleh/awesome-skills-security

URL: https://github.com/Eyadkelleh/awesome-skills-security
Quality signals: 415 stars, last push 2026-06-08, 7 SKILL.md files, no license declared, published on skills.sh. Content is derived from SecLists. It ships payload and wordlist corpora, not methodology, so the security value is in the reference files.

| Skill | Source URL | What it encodes | Hermes compatibility | Quality signals | Fit | Verdict |
|---|---|---|---|---|---|---|
| security-payloads | https://github.com/Eyadkelleh/awesome-skills-security/blob/main/skills/security-payloads/SKILL.md | Injection payload corpus: XSS, SQLi, command injection, traversal, SSRF, and LLM prompts | native | 415 stars, SecLists derived, 2026-06 | medium, XSS and SSRF payload lists are useful for the DOM probe, the rest does not apply | reference only |
| security-fuzzing | https://github.com/Eyadkelleh/awesome-skills-security/blob/main/skills/security-fuzzing/SKILL.md | Fuzzing wordlists for parameters and paths | native | same repo | low, there are no URL parameters in this app | cut |
| llm-testing | https://github.com/Eyadkelleh/awesome-skills-security/blob/main/skills/llm-testing/SKILL.md | LLM bias, alignment and safety prompts | native | same repo | none, no model in the product | cut |

### 6.10 ljagiello/ctf-skills

URL: https://github.com/ljagiello/ctf-skills
Quality signals: 3,803 stars, MIT, last push 2026-11-15, 12 SKILL.md files, author named in the frontmatter metadata, requires bash, Python 3 and network for tool installation. Indexed on both skills.sh and ClawHub, which is why `ctf-misc` shows a clawhub source in search results.
What it encodes: per category CTF playbooks, each with a quick reference and supporting files.

| Skill | Source URL | What it encodes | Hermes compatibility | Quality signals | Fit | Verdict |
|---|---|---|---|---|---|---|
| ctf-web | https://github.com/ljagiello/ctf-skills/blob/main/ctf-web/SKILL.md | Web challenge exploitation: source disclosure, auth bypass, injection, deserialisation, JWT, race | native | 3,803 stars, MIT, 2026-11 | medium, the browser only, no server shape of CTF web challenges is close to this app | reference only |
| ctf-forensics | https://github.com/ljagiello/ctf-skills/blob/main/ctf-forensics/SKILL.md | File, memory and network forensics, artifact carving | native | same repo | medium, the artifact carving mindset applies to the local trace check | reference only |
| ctf-crypto | https://github.com/ljagiello/ctf-skills/blob/main/ctf-crypto/SKILL.md | Classical and modern crypto attacks, oracle abuse | native | same repo | low, the app will use standard WebCrypto AES-GCM, not a puzzle cipher | cut |
| ctf-misc | https://github.com/ljagiello/ctf-skills/blob/main/ctf-misc/SKILL.md | Encoding, pyjails, DNS oddities, unicode tricks, constraint solving | native | same repo | low, the unicode and whitespace variant section is the only transferable part, for the invite code normalisation probe | reference only |

### 6.11 ghostsecurity/skills

URL: https://github.com/ghostsecurity/skills
Quality signals: 447 stars, Apache-2.0, last push 2026-09-28, 8 SKILL.md files across three plugins. The skills drive the Ghost proxy plugin (`plugins/ghost/skills/scan-code`, `scan-deps`, `scan-secrets`, `validate`, `report`, `proxy`, `repo-context`) and the `exo` plugin.
What it encodes: harnessed scanning through a hosted proxy, not standalone procedure.
Compatibility: the SKILL.md files load, but every step calls Ghost MCP tools that are not present in this profile.

| Skill | Source URL | What it encodes | Hermes compatibility | Quality signals | Fit | Verdict |
|---|---|---|---|---|---|---|
| scan-secrets | https://github.com/ghostsecurity/skills/blob/main/plugins/ghost/skills/scan-secrets/SKILL.md | Secret discovery and triage | method only, requires the Ghost proxy MCP | 447 stars, Apache-2.0, 2026-09 | low, the app has no secrets and no repository history | cut |
| validate | https://github.com/ghostsecurity/skills/blob/main/plugins/ghost/skills/validate/SKILL.md | Finding validation before reporting | method only | same repo | medium, overlaps fp-check | reference only |

### 6.12 alirezarezvani/claude-skills

URL: https://github.com/alirezarezvani/claude-skills
Quality signals: 30,539 stars, MIT, last push 2026-11-26, 410 skills. Huge but general purpose; the security content is a handful of skills inside a large engineering and business catalogue.

| Skill | Source URL | What it encodes | Hermes compatibility | Quality signals | Fit | Verdict |
|---|---|---|---|---|---|---|
| security-pen-testing | https://github.com/alirezarezvani/claude-skills/blob/main/engineering-team/skills/security-pen-testing/SKILL.md | OWASP Top 10 checks, dependency audit, secret scan, a three day engagement plan, and a `pentest_report_generator.py` | native | 30,539 stars, MIT, 2026-11-26 | low, broad and OWASP generic, weaker than the installed web-pentest | reference only |

### 6.13 BehiSecc/VibeSec-Skill

URL: https://github.com/BehiSecc/VibeSec-Skill
Quality signals: 1,435 stars, Apache-2.0, last push 2026-11-26, a single SKILL.md named `vibesec`. Popular because it is one drop in file, which also means no references and no depth.
What it encodes: secure coding rules and a review workflow for web apps, covering auth, authz, input handling and common vulnerability classes.

| Skill | Source URL | What it encodes | Hermes compatibility | Quality signals | Fit | Verdict |
|---|---|---|---|---|---|---|
| vibesec | https://github.com/BehiSecc/VibeSec-Skill/blob/main/SKILL.md | Bug hunter secure coding rules, per vulnerability class, with a review workflow | native | 1,435 stars, Apache-2.0, 2026-11-26 | medium, it is a good R2 coding standard for the fix round and needs no adaptation | install candidate |

### 6.14 ahmdobeidat/pentest-skills

URL: https://github.com/ahmdobeidat/pentest-skills
Quality signals: 1 star, MIT, last push 2026-11-17, 14 SKILL.md files plus hooks and schemas. Popularity is effectively zero, but the design is the most evidence disciplined of the small packs: scope as `scope.json`, assets as `assets.json`, and hooks that enforce scope rather than asking the model to remember it.

| Skill | Source URL | What it encodes | Hermes compatibility | Quality signals | Fit | Verdict |
|---|---|---|---|---|---|---|
| engagement-kickoff | https://github.com/ahmdobeidat/pentest-skills/blob/main/skills/engagement-kickoff/SKILL.md | Scope intake into `scope.json`, dispatch to phase one | adapt, hooks are Claude Code specific | 1 star, MIT, 2026-11 | medium, R3 authorization artifact | reference only |
| vuln-chaining | https://github.com/ahmdobeidat/pentest-skills/blob/main/skills/vuln-chaining/SKILL.md | Ten pattern composition catalogue for multi finding exploits | adapt | same repo | medium, pairing MITM plus parser abuse may only be critical when chained | reference only |
| finding-writeup | https://github.com/ahmdobeidat/pentest-skills/blob/main/skills/finding-writeup/SKILL.md | Three way dispatch: client report, HackerOne, CVE email, plus retest mode | adapt | same repo | low, duplicates installed vulnerability-writeup | cut |
| poc-building | https://github.com/ahmdobeidat/pentest-skills/blob/main/skills/poc-building/SKILL.md | Minimise, reproduce, redact before shipping a PoC | adapt | same repo | medium, R3 evidence hygiene | reference only |

### 6.15 45ck/pentest-security-testing-skills

URL: https://github.com/45ck/pentest-security-testing-skills
Quality signals: 1 star, MIT, last push 2026-04-11, 11 skills mirrored three times (`.claude/skills/`, `.agents/skills/`, `skills/`). Platform neutral by design. Very low popularity, but the skill set is exactly the boring scaffolding a red team needs.

| Skill | Source URL | What it encodes | Hermes compatibility | Quality signals | Fit | Verdict |
|---|---|---|---|---|---|---|
| authorized-scope-checker | https://github.com/45ck/pentest-security-testing-skills/blob/main/skills/authorized-scope-checker/SKILL.md | Verifies the assessment is authorized, scoped and constrained to permitted methods | native | 1 star, MIT, 2026-04 | medium, R3 guardrail, the installed web-pentest covers it more fully | reference only |
| owasp-wstg-checklist-runner | https://github.com/45ck/pentest-security-testing-skills/blob/main/skills/owasp-wstg-checklist-runner/SKILL.md | WSTG checklist execution with per item evidence | native | same repo | medium, a checklist is a useful cross check against the adapted R3 class table | reference only |
| repro-steps-writer | https://github.com/45ck/pentest-security-testing-skills/blob/main/skills/repro-steps-writer/SKILL.md | Reproduction steps with exact inputs and observed output | native | same repo | medium, R3 evidence format | reference only |
| parameter-pollution-checker | https://github.com/45ck/pentest-security-testing-skills/blob/main/skills/parameter-pollution-checker/SKILL.md | HTTP parameter pollution | native | same repo | none, the app has no query parameters except `?idle=` | cut |

### 6.16 awarexone/Agentic-Bug-Hunter (formerly shuvonsec/claude-bug-bounty)

URL: https://github.com/awarexone/Agentic-Bug-Hunter (the `shuvonsec/claude-bug-bounty` path still resolves here, verified by `gh api`)
Quality signals: 6,078 stars, MIT, last push 2026-11-12, 26 SKILL.md files. High popularity, aimed at bug bounty hunters against live web targets with many endpoints.

| Skill | Source URL | What it encodes | Hermes compatibility | Quality signals | Fit | Verdict |
|---|---|---|---|---|---|---|
| recon and web attack skills (collection level) | https://github.com/awarexone/Agentic-Bug-Hunter | Bug bounty workflow: subdomain recon, endpoint discovery, OWASP classes, report drafting | native | 6,078 stars, MIT, 2026-11 | low, the app has one file and no attack surface to enumerate | cut |

## 7. Gap coverage against the six library gaps

The six gaps come from `07-skill-sweep.md` section 5. This table says what the open collections actually close.

| Gap | Best open coverage found | Where | Residual work |
|---|---|---|---|
| 1. WebRTC protocol review (SDP, ICE, DTLS fingerprint, data channel framing) | No skill covers SDP structure or DTLS fingerprint binding. The nearest are `offensive-tls-attacks` (0-RTT replay, certificate validation) and `crypto-protocol-diagram` (sequence and state diagrams) | Claude-Red, Trail of Bits | Still authored. The protocol cases must come from the RFC, not from a skill |
| 2. Zeroization and wipe verification | `zeroize-audit` with assembly and control flow verification, C, C++ and Rust only | Trail of Bits | Adapt to JavaScript. The browser has no `memset` elision, so the check becomes: no retained references, keys zeroed via `fill(0)`, object URLs revoked, no storage entry, no DevTools retainable buffer |
| 3. Denial of service at the peer layer | `dos` (STRIDE D: resource exhaustion, algorithmic complexity, zip bombs, unbounded operations) plus `phy-regex-audit` for ReDoS | florianbuetow/claude-code, ClawHub | Partially closed. Neither covers SCTP chunk flooding or memory growth before a 50 MB cap fires. Those probes stay authored |
| 4. Client-side crypto review | `crypto-audit`, `performing-cryptographic-audit-of-application`, `offensive-crypto-attacks`, `constant-time-analysis` | briiirussell, mukul975, Claude-Red, Trail of Bits | Closed at the methodology level. The AES-GCM epoch design and rekey protocol remain ours to specify |
| 5. Privacy monitor design | No skill found. `privacy-engineering` covers data minimisation, not monitor design | briiirussell | Still authored. The installed `cyber-detect-respond` rule that a detector which never fires is itself a defect remains the operative control |
| 6. CSP review | `performing-content-security-policy-bypass` (directive and bypass classes) plus `offensive-xss` (CSP bypass inside the XSS workflow) | mukul975, Claude-Red | Closed. R2 can pick hash vs nonce with evidence, and R3 can attack the choice |

Transport fingerprinting, one of the R3 probe areas, has no usable skill. `gh search code` for `dtls` returned only unrelated Unity and mbedtls skills, and the only JA4 related hit, `hckhanh/ja4` at https://github.com/hckhanh/ja4, is a zero star library wrapper around a parser, not a procedure. Cut.

## 8. Installability summary

Verified with `hermes skills inspect` only. Nothing was installed.

| Group | Status | Note |
|---|---|---|
| Trail of Bits, Claude-Red, briiirussell, mukul975, transilienceai, ljagiello, securityfortech/hacking-skills, BehiSecc, alirezarezvani, open-sesame, ahmdobeidat, 45ck, Eyadkelleh | native, indexed or plain folder | `hermes skills install <owner>/<repo>/<skill>` resolves for the indexed ones. A raw URL install also works but drops `references/` and `scripts/` |
| ClawHub entries | native | `@0x-professor/nmap-pentest-scans` style identifiers resolve through the clawhub source |
| florianbuetow appsec, ghostsecurity | install loads, run fails | both depend on sibling folders or MCP tools that a one file install does not bring |
| anthropics/claude-code-security-review | not installable | zero SKILL.md files, it is an Action plus a slash command |

## 9. TOP 5 SHORTLIST

Ranked by what unblocks a gate in R1 to R4, not by stars.

| Rank | Item | Source URL | Why it is in the top five | Action |
|---|---|---|---|---|
| 1 | briiirussell `crypto-audit` | https://github.com/briiirussell/cybersecurity-skills/blob/main/skills/crypto-audit/SKILL.md | R1 decides the whole crypto layer from zero. This is the only skill that forces the "do not roll your own, use WebCrypto" verdict and then audits nonce, KDF, rotation and comparison. It maps one to one onto the epoch and rekey requirement | Install, read only, before the R1 blueprint is written |
| 2 | Trail of Bits `zeroize-audit` | https://github.com/trailofbits/skills/blob/main/plugins/zeroize-audit/skills/zeroize-audit/SKILL.md | The largest library gap. Nothing else in any registry treats wiping as an auditable property with phases and evidence. Its C and Rust mechanics do not apply, its definition of "wiped" does | Adapt into an authored JavaScript and WebCrypto wipe probe; do not install, the single file install loses the phase files |
| 3 | mukul975 `analyzing-browser-forensics-with-hindsight` | https://github.com/mukul975/Anthropic-Cybersecurity-Skills/blob/main/skills/analyzing-browser-forensics-with-hindsight/SKILL.md | The zero trace claim is unverifiable without knowing which Chromium artifacts to inspect. This skill enumerates them: history, downloads, cookies, cache, autofill, saved passwords, local storage, session and tab state | Install, read only, then turn its artifact list into the R4 reload and trace checklist |
| 4 | mukul975 `performing-content-security-policy-bypass` | https://github.com/mukul975/Anthropic-Cybersecurity-Skills/blob/main/skills/performing-content-security-policy-bypass/SKILL.md | The app ships `script-src 'unsafe-inline'` and the R2 fix is a hash or nonce choice. This is the only skill that treats CSP as an attack surface rather than a header checklist | Install, read only, use in R2 for the fix and R3 for the bypass attempt |
| 5 | florianbuetow appsec `dos` | https://github.com/florianbuetow/claude-code/blob/main/plugins/appsec/skills/dos/SKILL.md | The only denial-of-service procedure found in any collection, and it explicitly covers decompression bombs and unbounded operations, which are the `unpack` and chunk reassembly surfaces | Adapt into an authored peer layer DoS probe; the skill needs its `shared/` folder and a request handler model that this app does not have |

Next in line if a sixth slot appears: Claude-Red `offensive-race-condition` for the rekey and chunk races, and Claude-Red `offensive-xss` for DOM clobbering and CSP bypass in one pass.

## 10. SELF-CHECK

| Acceptance item | Verdict | Evidence |
|---|---|---|
| Every collection and skill carries a source URL fetched by me | PASS | 98 unique URLs extracted from this file and checked with `curl -sL -o /dev/null -w '%{http_code}'` in this session: 98 checked, 0 non 200. Repository facts come from `gh api repos/<owner>/<repo>` and recursive git trees, not from memory |
| Every row carries the full criteria | PASS | Every table uses the same 7 columns: name, source URL, what it encodes, Hermes compatibility, quality signals (author, recency, popularity), engagement fit, final verdict. Section 1 defines all three scales |
| Collections covered as briefed: Anthropic official, awesome lists, ClawHub, GitHub code search for CTF, pentest, bug bounty, recon, forensics, privacy, community repos | PASS | Anthropic in section 3, awesome lists in section 4, ClawHub in section 5, the rest in section 6. `gh search code --filename SKILL.md` was used for webrtc, dtls, denial of service, content-security-policy, zeroize and session wipe, and the hits are graded where they fit |
| Installability noted, nothing installed | PASS | Section 8. Commands run were `hermes skills --help`, `search`, `inspect`, `tap list`. No `install`, `uninstall`, `update`, `audit` or `publish` was executed. No clone was made |
| Items with fit none cut from the verdict | PASS | Cut rows are labelled cut inside their collection table and excluded from section 9. Examples: shieldadvanced, serverless, performing-ssl-tls-security-assessment, all 14 wireless Claude-Red skills |
| File ends with a TOP 5 SHORTLIST | PASS | Section 9, five ranked rows with action per row, followed by this self-check |
| English, no em dashes, no en dashes | PASS | Checked with `grep -n $'\u2014'` and `grep -n $'\u2013'` on this file, no output |
| One write per completed section, not one giant write | PASS | Four writes: header and method, sections 3 and 4, sections 5 and 6.1 to 6.3, sections 6.4 to 6.16, then this closing block |
| Time budget | FAIL, overrun | The brief allowed about 25 minutes of tool work. This run took roughly 40. The extra time went to URL verification and to reading the two collections that changed the ranking, Trail of Bits and mukul975. The work was finished rather than truncated at partial, which is the deliberate trade |

Two claims I could not fully verify and am labelling:

- Star counts and last push timestamps are from the GitHub API at run time, 2026-11-26. They move.
- mukul975 licenses each skill Apache-2.0 in the frontmatter and the repository API reports Apache-2.0. Trail of Bits reports CC-BY-SA-4.0, which is share alike and matters if authored skills are derived from it. open-sesame reports NOASSERTION, so its license needs a human read before any reuse.

