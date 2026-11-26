# 07 Skill sweep and pen-test round plan

RUN ID: w1-ephemeral-hardening-20261126
LANE: 7 of 7
TARGET: /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/input/ephemeral-chat-v1.html (V1, 35598 bytes)
STATUS: complete

Scope of this file: which installed skills apply to hardening and pen-testing this app, what each actually encodes, and the round plan that uses them. This is a tooling and procedure document, not a findings document. Findings belong to lanes 2 and 3.

## 1. Method and coverage

Searched two roots:

- /Users/marcelspatz/.hermes/skills (464 SKILL.md files outside .archive, 23 under security/)
- /Users/marcelspatz/.hermes/plugins (13 entries, none security specific)

Keyword passes across every SKILL.md: pentest, threat, ddos, monitor, wipe, zeroize, webrtc, SDP, red-team, adversarial, harden, security. Matches were opened and read before any bullet was written. Every absolute path in this file was checked with `ls` in this session and is marked OK in the inventory.

Coverage results that matter for planning:

- Zero skills mention DDoS or denial of service as a procedure. The P2P flood and chunk-exhaustion cases have no library support and must be authored in R3.
- Zero skills mention zeroization or session wipe. The kill switch and the 30-minute wipe have no library support and must be authored as probes.
- One incidental WebRTC match, a `--block-webrtc` scraping flag in research/scrapling (line 88). No skill covers WebRTC signalling, SDP parsing, or DTLS fingerprint verification.
- 7 security skills are hard-gated on a `_codex-security` plugin root that does not exist in this profile. They are listed in section 4 with the evidence, because a planner who assumes they work will schedule rounds that cannot run.

Verified app facts used for mapping (re-checked by grep in this session):

| Fact | Evidence in app source |
|---|---|
| CSP allows inline script, forbids all network sources | line 6: `script-src 'unsafe-inline'`, `connect-src 'none'` |
| Only external dependency is Google STUN | lines 443 to 444 |
| Manual pairing by compressed SDP code | pack at line 723, unpack at line 732 |
| One ordered SCTP data channel named chat | line 755 |
| Idle wipe default 30 minutes, `?idle=` override minimum 5s | lines 431 to 441, timer at line 1136 |
| Wipe button with confirm, then endSession | lines 1076 to 1079 |
| File and image delivery via object URLs | lines 890 and 1047 |
| No app-layer crypto: `crypto.` matches only randomUUID | line 488 |

## 2. Verdict summary

| Verdict | Count | Skills |
|---|---|---|
| use-as-is | 6 | cyber-secure-code, security-threat-model, cyber-detect-respond, fix-finding, webapp-testing, verification-before-completion |
| adapt | 12 | web-pentest, propose-security-hardening, security-best-practices, vulnerability-writeup, define-security-policy, assess-patch-risk, behavioral-verification, red-team-merge-pipeline, feature-gate-verification, interrogate, premortem, dogfood |
| skip | 17 | 7 plugin-gated security skills, security-ownership-map, oss-forensics, sherlock, credential-presence-audit, haze-secret-redaction-sinks, track-findings, system-telemetry, watchers, adversarial-ux-test, reflect |

Count check: 6 + 12 + 17 = 35 skills reviewed. The security directory alone contributes 23, all reviewed.

## 3. Applicable skill cards

Each card gives the absolute path verified on disk, the procedure as bullets taken from that SKILL.md, the mapping to this app, and the verdict.

### 3.1 cyber-secure-code

PATH: /Users/marcelspatz/.hermes/skills/security/cyber-secure-code/SKILL.md (OK)

Procedure encoded:

- Trust boundaries first: map where untrusted input crosses into privileged work, naming route extractors, auth/session, deserialization, path resolution, command exec, SQL, template/HTML, file IO, network egress, secrets.
- Reachability is mandatory: trace a real caller to the defect and grep every caller, not only the path a ticket names. No call path means log the item as unverified, not confirmed.
- Every confirmed finding states the exploit shape (crafted input, bypass, confused deputy) or a fail-closed proof (the guard that actually fires).
- Fix the class, not the site: a defect in a shared helper is one finding with N call sites, so name the shared choke point.
- Severity by real impact, ordered RCE and auth bypass above injection, SSRF, DoS, info leak, hardening gap.
- The internal checklist covers AuthN/AuthZ, injection, SSRF/egress, secrets at every sink, rate limiting and DoS, and gate integrity.

Mapping: this is the R1 and R2 workhorse. The app has four real boundaries to audit this way: the invite code parser (unpack at line 732, including DecompressionStream at line 739), the SDP handed to setRemoteDescription, the data channel frame parser, and the file chunk reassembler with its 50 MB cap. Its "gate integrity" item maps to the pairing gate: a check keyed on a name or a code prefix that drifts silently.

Verdict: use-as-is.

### 3.2 security-threat-model

PATH: /Users/marcelspatz/.hermes/skills/security/security-threat-model/SKILL.md (OK)

Procedure encoded:

- Extract the system model from the repo: components, data stores, external integrations, entrypoints, runtime versus CI, and exclude out of scope items explicitly.
- Derive trust boundaries as concrete edges, listing protocol, auth, encryption, validation and rate limiting on each, then list assets that drive risk and the entry points that reach them.
- Calibrate attacker capabilities from exposure and intended usage, and state non-capabilities explicitly to avoid inflated severity.
- Enumerate threats as abuse paths tied to assets and boundaries, keeping the list small and high quality.
- Prioritise with qualitative likelihood and impact plus a justification, then state which assumptions most influence the ranking.
- Validate assumptions with the owner (1 to 3 targeted questions), then recommend mitigations tied to concrete components and controls, and finish with a quality check that every entrypoint and boundary is represented.

Mapping: produces the R1 blueprint document. Its "state non-capabilities" rule is what keeps this threat model honest: the app has no accounts, no server, no stored data, so most web threat catalogues do not apply and the model must say so. It writes `<repo-or-dir-name>-threat-model.md`, which fits `output/03-threat-model.md` in the sibling lane.

Verdict: use-as-is, writing into the lane 3 output path.

### 3.3 propose-security-hardening

PATH: /Users/marcelspatz/.hermes/skills/security/propose-security-hardening/SKILL.md (OK)

Procedure encoded:

- Keep three products distinct: canonical evidence stays read only, the hardening analysis is a derived revisable design product, implementation happens only after an option is selected.
- Cluster evidence by violated invariant, trust boundary, control owner, dangerous capability and repeated preventive control, not by CWE or title.
- Qualify an opportunity only on evidence: several findings from one dispersed control, a privileged choke point, an invariant held only by convention, or repeated tactical fixes.
- State desired invariants as falsifiable behaviour statements, then map the current design including entry points, control owners, state flow, failure containment and performance sensitive paths.
- Separate Observed, Inferred and Proposed claims, and cite exact evidence for each.
- Present options with before and after views, explicit tradeoffs, migration plan and an implementation handoff, and record `local_remediation_preferred` when no structural change is warranted.

Mapping: this is the R1 design portfolio and the R5 re-harden frame. It is the right tool for the owner's transformer requirement, because continuous key rotation and kill-switch migration are architectural invariants, not per-finding patches. Its warning against inventing an architectural proposal when local fixes suffice keeps the plan from over-building.

Verdict: adapt. Input is a single HTML file, not a scan directory, so evidence IDs and scan artifact conventions are replaced by file:line references.

### 3.4 web-pentest

PATH: /Users/marcelspatz/.hermes/skills/security/web-pentest/SKILL.md (OK)

Procedure encoded:

- Hard guardrails before any active request: written authorization recorded in `engagement/authorization.md`, a scope allowlist in `scope.txt`, no production without paper, cloud metadata off by default, destructive payloads approved, 200ms rate limit.
- Phase 0 to 2: engagement setup, optional offline pre-recon (map architecture, inventory sinks, backward taint to request sources), then live read-only recon of headers, tech fingerprint and endpoints.
- Phase 3: one delegate per vulnerability class (injection, xss, auth, authz, ssrf, infra) producing a queue with witness payload, confidence and verdict.
- Phase 4 proof based exploitation, with levels L1 identified, L2 partial, L3 confirmed, L4 critical, and bypass exhaustion before any false-positive dismissal.
- Evidence per L3/L4: full request, response, reproducer command, impact statement; redact captured secrets to the last 6 chars in chat.
- Phase 5 report: scope, authorization, L3/L4 findings with CVSS and CWE, not-exploited candidates, out of scope observations, methodology, limitations.

Mapping: supplies the R3 structure and the authorization and scope discipline. Its vulnerability classes transfer only partly. There is no server, no SQL, no auth session, no SSRF to metadata. The classes that do transfer are the parser and protocol ones: SDP code injection, decompression bomb in `unpack`, data channel frame confusion, chunk reassembly abuse, and denial of service by flood. The guardrails transfer fully and should be kept verbatim.

Verdict: adapt. Keep phases 0, 1, 2, 4, 5 and the evidence levels. Replace the phase 3 class table with a WebRTC and pairing specific class table, because the shipped table would send testers at surfaces this app does not have.

### 3.5 cyber-detect-respond

PATH: /Users/marcelspatz/.hermes/skills/security/cyber-detect-respond/SKILL.md (OK)

Procedure encoded:

- Every finding gets a reproduction on the current tree with the smallest probe; no repro means unverified, not confirmed.
- Prove the detector, not just the defect: deliberately trip the guard, monitor or gate and watch it fire, then restore. A detector that never fires is a finding of its own.
- Triage by blast radius and exploitability, confirmed and reachable first, and name affected callers rather than only the defect site.
- Classify before routing: genuine defect, transient artifact, design intent, deferred scope. Only genuine defects gate.
- One scoped fix per defect carrying the finding verbatim plus a regression test that fails without the fix, then re-verify correction and preservation.
- Loop is DETECT, TRIAGE, ROUTE, VERIFY, CLOSE, with an independent lane confirming closure.

Mapping: this is the R4 and R5 gate. The app is adding a monitor overlay and a kill switch, which are detectors. This skill is the only one in the library that says a monitor which cannot fire is itself a defect. That is exactly the failure mode of a privacy HUD that always shows green.

Verdict: use-as-is.

### 3.6 security-best-practices

PATH: /Users/marcelspatz/.hermes/skills/security/security-best-practices/SKILL.md (OK)
REFERENCES: javascript-general-web-frontend-security.md verified present under references/.

Procedure encoded:

- Identify every language and framework in scope, frontend and backend, then load all matching reference files from the references directory.
- Three modes: write secure by default code, passively flag critical issues while working, or produce a prioritised report when asked.
- Report format: markdown file, short executive summary, sections by severity, numeric IDs, one sentence impact for critical findings, line numbers for every code reference.
- Fix one finding at a time with a short comment naming the practice, and consider functional regressions before changing insecure code that other behaviour relies on.
- General advice includes avoiding incrementing public IDs and being careful about TLS and secure-cookie recommendations when the app is not actually served over TLS.

Mapping: the frontend reference is the relevant one, since this is a single inline-script page. It covers DOM sinks, CSP, postMessage and client storage. Note the app currently ships `script-src 'unsafe-inline'` at line 6, which this guidance would flag, but the file is a single self-contained page by design, so the fix is a nonce or hash, not an external bundle.

Verdict: adapt. Use the frontend reference only; the python, go and server framework references do not apply.

### 3.7 fix-finding

PATH: /Users/marcelspatz/.hermes/skills/security/fix-finding/SKILL.md (OK)

Procedure encoded:

- Classify current state first as vulnerable, already safe, or unproven; return `no_change` when evidence shows the path is already safe.
- Before editing, establish the attacker-controlled input and source-to-sink path, the security invariant, the narrowest shared enforcement boundary, and the compatible behaviour that must remain.
- Run one fresh read-only investigator pass that independently traces the boundary and the sibling paths, then reconcile with the parent's trace before choosing the patch boundary.
- Implement the smallest repository-native fix at the shared boundary, and explicitly handle unsafe state rather than truncating or reinterpreting it.
- Challenge the patch before verification: inspect every direct caller and both outcomes of each changed condition, looking for one surviving route and one newly rejected legitimate input.
- Verify in order: diff and syntax check, rerun the trigger plus an alternate malicious input class, rerun the legitimate control and the owning package's checks. Return `blocked` rather than guessing when essential evidence is missing.

Mapping: the R2 and R5 patch procedure. The "both outcomes of each changed condition" rule is what stops a pairing gate that rejects the attacker but also rejects a legitimate reply code with a different compression prefix.

Verdict: use-as-is.

### 3.8 vulnerability-writeup

PATH: /Users/marcelspatz/.hermes/skills/security/vulnerability-writeup/SKILL.md (OK)

Procedure encoded:

- Treat the original finding as a hypothesis: establish version, attacker position, reachable entry point, expected behaviour, actual failure and narrowest demonstrated impact before deciding how strongly to speak.
- Never invent a source excerpt, line number, affected version, CVSS vector, exploit route, execution result or observation. Distinguish source evidence, inspected but unexecuted PoC, runtime observation, inference and unknowns.
- Reduce each finding to one concrete attack sentence (who the attacker is, what they control, what they do, which boundary should stop them, which sink they reach) and state the important non-claims beside it.
- Challenge the claim: is the required configuration default, does the attacker already need the access, does a guard prevent the path, what negative control distinguishes the claim from a benign explanation.
- One report directory and exactly one drafting sub-agent per distinct vulnerability, then an independent read of the draft against the raw artefacts.
- Report language is reader-facing: public release identifiers, repository-relative paths, no author-machine absolute paths, named actors used consistently.

Mapping: the R3 disclosure output. Two adjustments are needed. There is no release history to trace (V1, single file), and the report must not claim a CVE or affected version range. The "state the non-claims" rule is unusually valuable here, because most scary sounding WebRTC findings die once the non-claim is written down (for example, "the attacker does not break DTLS, they replace the code before it is pasted").

Verdict: adapt. Drop the release history workflow; keep the evidence taxonomy, the attack sentence, and the draft review.

### 3.9 define-security-policy

PATH: /Users/marcelspatz/.hermes/skills/security/define-security-policy/SKILL.md (OK)

Procedure encoded:

- Inventory policy paths before reading them, and compose root to leaf with the policy closest to the code taking precedence.
- Establish the security boundary: system and scope, assets, threat model and invariants, reportability and severity, exclusions and accepted risks.
- Compare existing guidance against evidence and call out stale exposure claims, missing boundaries, broad exclusions that could hide a finding, and new surfaces.
- Confirm material scope, severity, exclusion and accepted-risk decisions with the owner; never turn an inference into suppression authority.
- Keep secrets and unnecessary exploit detail out of repository policy.

Mapping: R1 should produce a short SECURITY.md for this product even though it is one file, because the engagement will otherwise keep re-litigating what counts as a finding. It is the natural home for the six posture invariants and for the explicit exclusion list (no server, no accounts, no persistence, no third-party content).

Verdict: adapt. The repository is a single HTML file; the policy is four paragraphs plus an invariants table, not a multi-component policy tree.

### 3.10 assess-patch-risk

PATH: /Users/marcelspatz/.hermes/skills/security/assess-patch-risk/SKILL.md (OK)

Procedure encoded:

- Bind the exact patch: immutable artifact, base, head, changed files, SHA-256 of the patch bytes; stop with `hold_for_evidence` if identity changes.
- Keep five concepts separate: impact if wrong, regression likelihood, regression protection, recoverability, confidence.
- Map program impact from source by tracing changed symbols through callers to production entry points, and check dynamic dispatch and configuration-selected paths.
- Try to falsify safety: for each material boundary state one concrete counterexample and one legitimate control, traced through the patched source.
- Recommendation is exactly one of merge, revise, no_op, block, hold_for_evidence. Patch size, caller count and green CI never prove low risk.

Mapping: R5 patch review for each hardening diff. The "recoverability" dimension matters more than usual here, because a bad key-rotation change can lock both peers out of an existing session with no server to recover through.

Verdict: adapt. Its JSON schema path points into the absent `_codex-security` plugin, so use the rubric and the five dimensions manually and skip schema validation.

### 3.11 behavioral-verification

PATH: /Users/marcelspatz/.hermes/skills/software-development/behavioral-verification/SKILL.md (OK)

Procedure encoded:

- A single pass is smoke, not testing. Every shipped feature gets a matrix: happy path, negative path, race or burst, isolation, monotonicity and cycles, hidden or backgrounded state, persistence and reload, mutation storm, boundary limits, cross-surface isolation.
- One case equals act, then a deterministic diagnostic assertion, then an evidence artifact plus exact quoted values.
- The verifier must be independent of the producer; producers never grade their own feature.
- Case failures go to a bounded fix loop, then the whole affected group is re-run; a post-fix single re-pass is not the gate.
- Verify only against a producer-declared stable build, with a freeze set named before the lane starts.
- Browser-driving lanes run capped (one browser and one context at a time), and a lane's chat self-report is not evidence; read the verdict artifact and re-check cited evidence.

Mapping: the R4 live two-party matrix. The app's real feature list gives the case classes: create invite, paste reply, connect, send text, send image, send 50 MB file, save on receiver, idle wipe, manual wipe, peer loss, reload and background. The "persistence and reload" class is the direct test of the zero-trace claim, and "race or burst" covers chunk flood and simultaneous sends.

Verdict: adapt. Drop the extension and mobile profiles; use the web-app surface adapter and the case-class baseline as written.

### 3.12 webapp-testing

PATH: /Users/marcelspatz/.hermes/skills/webapp-testing/SKILL.md (OK)
SCRIPT: scripts/with_server.py verified present.

Procedure encoded:

- Decide by surface: static HTML gets selectors read directly from the file; dynamic apps use the reconnaissance-then-action pattern.
- Use the bundled `with_server.py` helper as a black box, running `--help` first rather than reading its source.
- Start servers through the helper (single or multiple) and keep only Playwright logic in the automation script.
- Always wait for `networkidle` before inspecting the DOM on dynamic apps.
- Launch chromium headless from the sync API, use descriptive selectors, add explicit waits, and close the browser when done.

Mapping: R4 driver. Two independent browser contexts are needed to play both peers. Because the app is a static file, `file://` works, but a local HTTP server is better for a realistic origin and for testing the `?idle=` override. The `networkidle` wait is not meaningful here: the page never fetches, so wait for the invite textarea to populate instead.

Verdict: use-as-is, with the `networkidle` caveat noted for the R4 author.

### 3.13 red-team-merge-pipeline

PATH: /Users/marcelspatz/.hermes/skills/software-development/red-team-merge-pipeline/SKILL.md (OK)

Procedure encoded:

- Verify the builder's claims against the tree, not the report: an actual commit, the correct base, a diff limited to declared files, and the gate re-run by the verifier with an exact count.
- Independent red-team on a lane that did not build the work. The brief must demand a mutation test: revert the core fix in scratch state and require at least one new test to fail, else the verdict is BLOCK.
- Per-acceptance-item probes: every checkbox gets PASS or FAIL plus one line of evidence, none skipped.
- Call-path trace: confirm the fix is reachable from the production caller, not only tested in isolation.
- BLOCK is a repair dispatch, not a rebuild: one small fix builder on the same branch carrying the verdict verbatim, then re-review with the same mutation protocol.
- Merge serially and re-gate on the merged state, then clean the lane.

Mapping: R3's verdict discipline. The mutation test is the single most valuable import: revert the pairing gate and prove the red-team's exploit probe comes back. Without it a "we hardened it" claim is unverified. The git and merge stages do not apply to a single file, so keep Stage 2 and the BLOCK definition only.

Verdict: adapt. Use Stage 2, Stage 3 and the standing rule that the reviewer must not be the builder. Drop Stages 1 and 4, which assume branches and worktrees.

### 3.14 feature-gate-verification

PATH: /Users/marcelspatz/.hermes/skills/autonomous-ai-agents/feature-gate-verification/SKILL.md (OK)

Procedure encoded:

- Snapshot the tree first (status, branch, last commits) and scope every operation to your own files in a shared working tree.
- Run the project's exact gate commands and capture real exit codes; a pipeline ending in `tail` returns tail's code, not the test runner's.
- Attribute failures before claiming regression: check whether failures come from someone else's uncommitted diff and prove a clean baseline with a scoped stash.
- Live smoke on a throwaway server with isolated env, health check first, then probe the contract and assert stored state byte for byte.
- Diff discipline and static reachability proof as separate gates.
- Update the evidence envelope early and checkpoint it; record exact outputs and exit codes, never a bare "pass". Preserve separate verdicts for source, deployment and user-visible behaviour.

Mapping: R2 and R3 evidence envelope. The app has no test runner, so the "gate contract" must be invented once in R1: a probe script plus exact commands. The rule about exit codes matters because most HTML checks are `grep` pipelines that hide failures.

Verdict: adapt. Keep the envelope, exact exit codes, failure attribution and separate verdicts. Drop the shared-tree and stash mechanics.

### 3.15 verification-before-completion

PATH: /Users/marcelspatz/.hermes/skills/verification-before-completion/SKILL.md (OK)

Procedure encoded:

- The iron law: no completion claims without fresh verification evidence, run in this message.
- Gate function: identify the command that proves the claim, run it in full, read the full output and exit code, then claim or state actual status.
- Never claim a pass from a partial run, a stale run, or an agent's self-report.

Mapping: applies to every round gate and to the final engagement report. Every "hardened" claim in R2 and R5 needs its probe output quoted.

Verdict: use-as-is.

### 3.16 interrogate

PATH: /Users/marcelspatz/.hermes/skills/interrogate/SKILL.md (OK)

Procedure encoded:

- Scope the review from a named diff or files, then state the intent in one paragraph before spawning reviewers.
- Spawn one reviewer per configured model with the same prompt and rubric; the adversarial signal comes from model diversity, not assigned personas.
- Synthesize a verdict and never auto-apply changes.

Mapping: R3 second opinion on the red-team report. If the red team finds nothing, a different model family reading the same file is the cheapest way to detect a blind spot. Its default model table is stale for this profile, so the reviewer list must come from the live model config.

Verdict: adapt. Replace the hardcoded model table and the Task tool references with the Hermes delegation equivalents.

### 3.17 premortem

PATH: /Users/marcelspatz/.hermes/skills/premortem/SKILL.md (OK)

Procedure encoded:

- Prompt: imagine the project failed spectacularly in three months, then explain why.
- Classify each risk as Tiger (real threat), Paper Tiger (looks threatening but is fine), or Elephant (the thing nobody wants to discuss).
- Verify before flagging: read context around the finding, check for a fallback, check scope, and check whether the code is dev-only before calling it a tiger.
- Record the verification fields so each tiger is evidenced rather than pattern matched.

Mapping: R1 design review. The Elephants for this product are already visible: manual code exchange is a social-engineering surface, the DTLS fingerprint is never shown to the user for comparison, and the monitor overlay can only observe what the page exposes. Naming them in R1 is cheaper than discovering them in R4.

Verdict: adapt. Use the Tiger, Paper Tiger, Elephant classification and the verification checklist as the R1 design critique; skip the slash-command framing.

### 3.18 dogfood

PATH: /Users/marcelspatz/.hermes/skills/software-development/dogfood/SKILL.md (OK)

Procedure encoded:

- Five phases: plan the sitemap and flows, explore each feature, capture evidence, triage issues, write a structured report.
- Evidence first: screenshots and console output per issue, with reproduction steps.
- Structured bug report with severity and scope.

Mapping: R4 exploratory pass alongside the deterministic matrix. Exploratory use is where pairing usability and failure recovery problems show up, for example what a user sees when the reply code has a stray newline.

Verdict: adapt. Use the plan and evidence phases; the sitemap concept collapses to one page with several states.

## 4. Reviewed and skipped

Every path below was verified with `ls` in this session. None is invented.

### 4.1 Plugin gated, inert in this profile

Root cause: these skills call Codex Security MCP tools and read `../_codex-security/references/...`. `find /Users/marcelspatz/.hermes -maxdepth 5 -type d -name _codex-security` returns nothing, and both `~/.hermes/plugins/_codex-security` and `~/.hermes/skills/security/_codex-security` are absent.

| Skill | Path (OK) | Why skipped |
|---|---|---|
| security-scan | /Users/marcelspatz/.hermes/skills/security/security-scan/SKILL.md | Requires `start_codex_security_standard_scan` and the `_codex-security` reference tree. |
| deep-security-scan | /Users/marcelspatz/.hermes/skills/security/deep-security-scan/SKILL.md | Requires `start_codex_security_deep_scan` coordinator; no local equivalent. |
| threat-model | /Users/marcelspatz/.hermes/skills/security/threat-model/SKILL.md | Only a wrapper around the `_codex-security` scan artifact conventions; use security-threat-model instead. |
| attack-path-analysis | /Users/marcelspatz/.hermes/skills/security/attack-path-analysis/SKILL.md | Requires candidate ledger and scan artifact paths; suppress and calibrate inside cyber-secure-code instead. |
| finding-discovery | /Users/marcelspatz/.hermes/skills/security/finding-discovery/SKILL.md | Diff scan phase worker, needs `list_codex_security_review_items` and rank input scripts. |
| security-diff-scan | /Users/marcelspatz/.hermes/skills/security/security-diff-scan/SKILL.md | Needs `scanId` or the `generate_in_scope_files.py` helper from the absent plugin. |
| triage-finding | /Users/marcelspatz/.hermes/skills/security/triage-finding/SKILL.md | Backlog burn-down for imported scanner tickets; also depends on `_codex-security/references`. |

### 4.2 Reviewed, not applicable

| Skill | Path (OK) | Reason |
|---|---|---|
| security-ownership-map | /Users/marcelspatz/.hermes/skills/security/security-ownership-map/SKILL.md | Builds ownership from git history; the target is one untracked HTML file with no history. |
| oss-forensics | /Users/marcelspatz/.hermes/skills/security/oss-forensics/SKILL.md | Supply chain incident recovery for GitHub repos; nothing to recover. |
| sherlock | /Users/marcelspatz/.hermes/skills/security/sherlock/SKILL.md | Username OSINT across platforms; no identity investigation in scope. |
| credential-presence-audit | /Users/marcelspatz/.hermes/skills/security/credential-presence-audit/SKILL.md | Finds existing logins and keys; the app has no accounts, keys or integrations, and the only external host is public STUN. |
| haze-secret-redaction-sinks | /Users/marcelspatz/.hermes/skills/security/haze-secret-redaction-sinks/SKILL.md | Product specific to Haze redaction sinks. |
| track-findings | /Users/marcelspatz/.hermes/skills/security/track-findings/SKILL.md | Pushes findings to Linear, Jira or GitHub. No tracker in scope, and no credentials to use one. |
| system-telemetry | /Users/marcelspatz/.hermes/skills/system-telemetry/SKILL.md | Host HUD collector for the Linux box (`hud-collect`, Arc B580). This session runs on macOS and the product monitor is in-page, not host level. |
| watchers | /Users/marcelspatz/.hermes/skills/devops/watchers/SKILL.md | Polls RSS, JSON and GitHub feeds with a watermark. Useful for watching a deploy, not for app health or privacy monitoring. |
| adversarial-ux-test | /Users/marcelspatz/.hermes/skills/dogfood/adversarial-ux-test/SKILL.md | Finds UX friction through a hostile persona. Adjacent to R4 but not a security gate, so it does not gate a round. |
| reflect | /Users/marcelspatz/.hermes/skills/reflect/SKILL.md | Skill maintenance from the session transcript; not part of the engagement. |

## 5. What the library does not cover

These gaps are the reason the round plan adds authored probes rather than assuming a skill exists.

1. WebRTC protocol review. No skill covers SDP structure, ICE candidate handling, DTLS fingerprint binding, or data channel framing. R3 must define these cases from the spec, not from a skill.
2. Zeroization and wipe verification. No skill mentions zeroize or wipe. Proving that key material and transcript buffers are gone after wipe needs a heap or DevTools inspection probe authored in R2 and re-run in R4.
3. Denial of service at the peer layer. No DDoS or rate limiting skill for a P2P channel. The 50 MB cap and 16 KB chunk loop are the relevant surfaces, and the probes must be written by hand.
4. Client-side crypto review. No skill covers WebCrypto usage, nonce management, key derivation or rotation epochs. `crypto.subtle` is currently unused (only `randomUUID` at line 488), so all of this is new design, reviewed by hand in R1 and R2.
5. No privacy monitor design skill. The overlay is a product feature; only cyber-detect-respond governs whether its alerts can actually fire.
6. No CSP review skill. The inline script policy at line 6 needs a manual nonce or hash decision in R2.

## 6. Pen-test round plan

Five rounds. Each round has one gate check that fails loudly if the round did not happen. A round cannot start until the previous gate is recorded as PASS with quoted output.

### R1 Blueprint

Purpose: decide what "hardened" means in falsifiable terms before touching code.

Work:
- Run security-threat-model on the single file. Boundaries: boot page and CSP, invite code input, reply code input, SDP to setRemoteConnection, data channel frames, file chunk stream, object URL save path, monitor overlay.
- Run premortem on the design (Tigers, Paper Tigers, Elephants; verify before flagging).
- Write the six posture invariants as falsifiable statements, each with the probe that would break it:
  1. Unkeyed inbound never gets an answer.
  2. No plaintext or metadata leaves the page except STUN binding traffic.
  3. No persistence API is touched at any point in the session.
  4. Key material rotates on a stated cadence and on demand.
  5. A breach triggers wipe plus migration to a fresh keyset on both peers.
  6. The monitor overlay raises an alert when a privacy or health invariant is violated.
- Run propose-security-hardening to produce two or three architecture options with tradeoffs, and pick one.
- Write the SECURITY.md style policy (define-security-policy, adapted) with the exclusion list: no server, no accounts, no persistence, no third-party content.

Gate check: the invariant table exists with exactly six rows, each row names a probe command or browser assertion, and an independent reviewer confirms that each of the six owner requirements maps to at least one row. Failure mode caught: a blueprint that lists controls but no test for any of them.

### R2 Build

Purpose: implement the hardening against the R1 blueprint.

Work:
- Apply fix-finding per invariant, at the shared boundary, with the read-only investigator pass before each edit.
- Use security-best-practices frontend reference for the CSP, DOM and storage decisions. Replace `script-src 'unsafe-inline'` with a hash or nonce if the build stays single file.
- Add app-layer encryption (WebCrypto AES-GCM) with a key epoch, a rekey message type, and explicit zeroization of old keys; there is no crypto today.
- Add the pairing gate: reject before any answer is generated, and never auto-answer an unknown or malformed code.
- Add the kill switch on top of the existing wipe function (lines 1076 to 1079) so it also clears keys, closes the peer, clears transcript buffers, and signals the peer to migrate.
- Add the monitor overlay with counters and alert thresholds, wired so a violation produces a visible alert rather than a green light.
- Record each gate result in a feature-gate-verification style envelope with exact exit codes.

Gate check: one runnable probe per invariant passes on the built file, and a mutation run reverts each guard in turn and shows the matching probe failing. Failure mode caught: a guard that passes because the probe never exercises it.

### R3 Independent red-team pen test

Purpose: break R2 with a lane that did not build it.

Work:
- web-pentest guardrails: write `engagement/authorization.md` and `scope.txt` even for a local file, and keep the 200ms pacing rule for any live host.
- Replace the phase 3 class table with the classes that exist here:
  - pairing MITM by code substitution, and fingerprint comparison absent from the UI
  - `unpack` parser abuse: malformed prefix, decompression bomb at line 739, oversized code, unicode and whitespace variants of the same code
  - SDP field injection into setRemoteDescription
  - data channel frame confusion and unknown message types
  - chunk reassembly abuse: duplicate indices, out of range index, total size over 50 MB, memory growth before the cap fires
  - flood: many small frames, many chunks, repeated rekey requests
  - CSP bypass attempts against inline script
  - monitor bypass: can the attacker make the overlay report healthy while a violation is happening
  - kill switch bypass: does a second tab or a paused peer survive the wipe
  - rotation rollback and replay of an old epoch
- Every attempt gets a level L1 to L4 per web-pentest, and every blocked attempt gets bypass exhaustion before being called clean.
- Run interrogate with a different model family over the red-team report. If the report has zero L2 or above, treat that as a signal to re-scope, not as proof of safety.
- Write the disclosure report with vulnerability-writeup, adapted: one attack sentence and explicit non-claims per finding, no invented CVSS or version ranges.

Gate check: the findings ledger has one row per attempt with level, evidence and reproducer; zero L3 or L4 rows remain open; every closed row has a regression probe that fails on the pre-fix file. Failure mode caught: a red team that reports "no issues" without listing what it tried.

### R4 Live two-party test

Purpose: prove the hardened product works for two real peers, and that the privacy claims hold on a real machine.

Work:
- webapp-testing plus behavioral-verification: two independent browser contexts, one matrix, one evidence record per case.
- Matrix classes: happy path pairing, negative path wrong code, race and burst (simultaneous sends, chunk flood), isolation (third context cannot join), persistence and reload (reload must not recover the transcript), boundary limits (50 MB file, 0 byte file, 16 KB chunk boundary), backgrounded tab and idle timing, peer loss, manual wipe, kill switch, monitor alert on induced fault.
- Record: action, exact observed value, artifact identity (file hash), evidence path, verdict.
- Triage with cyber-detect-respond: for each guard and monitor, deliberately trip it and watch it fire, then restore.

Gate check: matrix has one record per case with evidence, the reload case shows no recoverable transcript in DevTools Application and no storage entry, and a packet capture during transfer shows no plaintext payload and no host other than the STUN server. Failure mode caught: a "works on my machine" pass with no reload, no third context and no capture.

### R5 Re-harden

Purpose: close what R3 and R4 found, and leave a residual risk list rather than a claim of perfection.

Work:
- Triage every finding (cyber-detect-respond), fix genuine defects with fix-finding, and re-run the whole affected group, not just the failing case.
- Assess each hardening diff with assess-patch-risk across the five dimensions, including recoverability for key rotation (a bad epoch change can lock both peers out).
- Re-prove all six invariants on the merged file, then run the full R4 matrix again on the final artifact and record the hash.
- Update the monitor so it can detect the class of each fixed finding. A fix the monitor cannot see is a regression waiting to happen.
- Write the residual risk list: accepted items, why accepted, and what would change the decision.

Gate check: every ledger row is closed with a regression probe that fails without the fix, the six invariant probes pass on the final file hash, the full matrix has no FAIL, and the residual risk list is non-empty with named owners. Failure mode caught: a re-harden round that fixes symptoms and leaves the monitor blind to the class.

## 7. Skill to round matrix

| Skill | R1 | R2 | R3 | R4 | R5 |
|---|---|---|---|---|---|
| security-threat-model | gate | | | | |
| premortem | yes | | | | |
| propose-security-hardening | gate | | | | yes |
| define-security-policy | yes | | | | |
| cyber-secure-code | yes | gate | yes | | yes |
| fix-finding | | gate | | | gate |
| security-best-practices | | yes | | | |
| web-pentest | | | gate | | |
| red-team-merge-pipeline | | | gate | | |
| interrogate | | | yes | | |
| vulnerability-writeup | | | yes | | |
| webapp-testing | | | | gate | |
| behavioral-verification | | | | gate | yes |
| cyber-detect-respond | | | yes | gate | gate |
| dogfood | | | | yes | |
| feature-gate-verification | | yes | yes | yes | yes |
| assess-patch-risk | | | | | yes |
| verification-before-completion | yes | yes | yes | yes | yes |

## 8. SELF-CHECK

| Acceptance item | Verdict | Evidence |
|---|---|---|
| Every listed skill path exists on disk | PASS | Extracted all 35 unique absolute SKILL.md paths from this file, ran a `[ -f ]` loop over each: `missing=0`. Unique path count printed 35, matching the 35 skills reviewed. |
| Bullets come from the actual SKILL.md files | PASS | Each card was written after reading that file's body in this session; app facts were re-grepped (CSP line 6, ICE 443, pack 723, unpack 732, channel 755, wipe 1076). |
| Round plan names a gate check per round | PASS | R1 to R5 each end with a "Gate check" paragraph naming a concrete artifact, a pass condition, and the failure mode it catches. |
| No skill name invented | PASS | All 35 names exist in `find /Users/marcelspatz/.hermes/skills -name SKILL.md`; the security directory has 23 skill directories and all 23 appear in sections 3 or 4. |
| Plugin-gated skills identified with evidence | PASS | `find /Users/marcelspatz/.hermes -maxdepth 5 -type d -name _codex-security` returned nothing; both candidate roots reported "No such file or directory". |
| Coverage gaps stated | PASS | Section 5 lists 6 gaps, each backed by the keyword sweep (zero hits for ddos, zeroize, wipe session, WebRTC). |
| No em or en dashes | PASS | `grep -n $'\u2014'` and `grep -n $'\u2013'` both printed nothing. |
| Claims about the app carry file:line | PASS | Section 1 table and each mapping cite line numbers verified by grep in this session. |

Verification commands actually run against this file, with results:

```
grep -o '/Users/.../SKILL.md' 07-skill-sweep.md | sort -u | wc -l   -> 35
while read -r p; do [ -f "$p" ] || echo MISSING; done               -> no output, missing=0
grep -n $'\u2014' 07-skill-sweep.md                                 -> no output
grep -n $'\u2013' 07-skill-sweep.md                                 -> no output
grep -c "SELF-CHECK" 07-skill-sweep.md                              -> 1
```

Status: PASS on all acceptance items. Time budget was respected; no files outside this output path were written.
