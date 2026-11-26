# W3 SKILLS BRIEF, external security skill expansion

RUN ID: w3-ephemeral-skills-20261126
MODEL LANE: ds-flash option, deepseek-v4.1-flash at opencode-go, reasoning max
STAGE: 01-research
PROJECT ROOT: /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL

WHY: read 01-research/output/07-skill-sweep.md first, especially its Library gaps section. The installed library has zero DDoS, zeroization, WebRTC, WebCrypto and CSP coverage. The owner expanded the search to the Hermes community skill registries and online sources so the pen-test rounds have more proven ground. Do not re-enumerate the local installed library, that file already covers it.

THE PRIMARY TOOL: the hermes skills CLI is live on this host and searches remote registries: skills.sh, well-known agent skill endpoints, GitHub, ClawHub. Use `hermes skills search TERM`, `hermes skills browse` and `hermes skills inspect` read-only. NEVER run install, uninstall, update, audit, publish or any mutating subcommand. Research only, no installs of any kind.

TARGET SYSTEM for fit grading, from accepted wave-1 research:
- Single-file WebRTC chat, DTLS data channel, manual invite and reply pairing codes, zero app-layer crypto, no server, Chromium desktop is the test target.
- The R3 red-team round will probe: pairing MITM, chunk and file framing abuse, wipe and zeroization completeness, transport fingerprinting, swarm and DDoS against a serverless target, and local trace minimization on macOS.

EVALUATION CRITERIA, one row per found item: name, registry id or source URL, what it encodes, compatibility verdict of native Hermes install, needs adaptation, or methodology only. Quality signals: author, recency, popularity where visible. Engagement fit: high, medium, low or none. Final verdict: install candidate, adapt into an authored skill, or reference only. Cut items whose fit is none.

BINDING CONSTRAINTS:
- English. No em dashes and no en dashes anywhere in your output. Periods and commas.
- Every external claim carries a verified source URL; mark UNVERIFIED anything you could not check.
- Read-only mission: no installs, no clones into the skills tree, no writes except your one output file.
- Time budget about 25 minutes of tool work. Past it, write STATUS: partial and stop.
- Incremental writes: one write_file per completed section, never one giant write at the end.
- MANDATORY SELF-CHECK: end your output file with a SELF-CHECK section listing every acceptance item as PASS or FAIL with evidence. Work is not done until each item is PASS or reported FAIL with the reason.
