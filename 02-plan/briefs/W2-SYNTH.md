# W2 SYNTH BRIEF, V2 hardening blueprint

RUN ID: w2-ephemeral-hardening-20261126
MODEL LANE: deepseek-v4.1-flash at opencode-go, reasoning max
STAGE CONTRACT: /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/02-plan/CONTEXT.md, its Inputs table scopes what you read per research file.
PROJECT ROOT: /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL

OWNER RULINGS, binding:
- Hybrid form factor: the one-file serverless core is the default and must stay fully usable with zero infrastructure. A private relay or tunnel cover mode is an optional second mode; every item that needs standing infrastructure is marked INFRA and lives only in that mode.
- Live test target: Chromium on desktop for both parties. Safari and iOS are stretch targets, not gates.
- The chat app stays a single HTML file, no build step, no external assets.

TASK: write the V2 hardening blueprint. Required sections:

1. THREAT BASELINE. The top risks as accepted from the research, the two High findings first: the pairing code is an unauthenticated bearer token with no fingerprint compare, and endIncoming exports zero-padded buffers with Save enabled on truncated transfers. Cite research files.

2. V2 ARCHITECTURE. One decision per pillar, each citing its research file: pairing and verification, safety-number SAS as default with balanced SPAKE2 as opt-in per 04-crypto-design. The app-layer crypto stack, double ratchet over the data channel plus per-message AEAD for files, WebCrypto-first, with the measured bundle numbers from 04-crypto-design for anything that must be inlined. File transfer integrity, export only the received span, Save gated on completeness. A versioned control envelope so panic and migration frames cannot be silently dropped, the prerequisite named in 06-ops-defense. Kill switch and migration, the M1 to M5 in-band protocol, plus the wipe completeness fixes for pagehide, the idle override and the code textareas. Transport, default-mode hardening plus the optional cover mode per 05-transport-hardening, INFRA flagged. The monitor overlay as a separate macOS component in a separate trust domain per 06-ops-defense.

3. WHAT STAYS. The V1 strengths S-1 to S-8 from 02-audit-findings, preserved by name.

4. BUILD PLAN. R2 sliced into ordered cards: each card gets file scope, one acceptance gate command, and the failure mode the gate catches, following the round-plan gates in 07-skill-sweep. Then the R3 red-team plan and the R4 live-test checklist for Chromium desktop, including the packet-capture check: no plaintext, and no host visible but the STUN server.

5. RESIDUAL RISK. What V2 honestly does not solve, drawn from the limits sections of the research.

BINDING CONSTRAINTS:
- English. No em dashes and no en dashes anywhere in the output. Periods and commas.
- Every design decision cites the research file it builds on. No invented numbers; bundle sizes come from the 04-crypto-design measurements.
- This is the plan, not the code. The build wave follows.
- Time budget about 30 minutes of tool work. Past it, write STATUS: partial and stop.
- Incremental writes: one write_file per completed section, never one giant write at the end.
- FORBIDDEN: no edits to input/, no edits to the research outputs, your only write is the output file.

MANDATORY SELF-CHECK, binding: before reporting done, re-read your output, re-run your checks, and end the file with a SELF-CHECK section listing every acceptance item as PASS or FAIL with evidence. Work is not done until each item is PASS or reported FAIL with the reason.

REQUIRED OUTPUT: /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/02-plan/output/blueprint-v2.md
