# W5 PLATFORM BRIEF, platform expansion research

RUN ID: w5-ephemeral-platform-20261126, respawned same evening after an accidental interrupt
MODEL LANE: ds-flash option, deepseek-v4.1-flash at opencode-go, reasoning max
STAGE CONTRACT: /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/01-research/CONTEXT.md
PROJECT ROOT: /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL

RESPAWN STATE, binding: the first wave 5 run was interrupted by accident. File 13 completed before the kill and is not to be touched. File 12 holds 52,648 bytes of verified-through-section-3.4 content and continues from there, verifying rather than rewriting what it inherits. File 11 has nothing on disk and restarts, now expanded to the tri platform ruling. Files 14 and 15 are new.

ADDITIONAL OWNER RULINGS, binding, from _config/SETUP.md:
- The executable ships for macOS, Windows and Linux including Omarchy.
- Extensive research into active vulnerabilities, exploits and CVE reports across the whole surface, covering as much attack surface as possible, feeding the pen test rounds.
- The vulnerability lanes produce a ledger, not exploit code against anything but our own target: every entry maps to a trust boundary in our architecture and names the R3 pen test case it demands. Severity is stated honestly, never inflated. Anything unconfirmed is marked UNVERIFIED.

NEW OWNER RULINGS, binding, from _config/SETUP.md:
- The product elaborates into a platform. An executable launcher opens the chat in a self-contained Chromium window with full UI and navigation.
- The single-file HTML core remains the embedded artifact. The serverless default and the file mode survive intact. The form factor ruling governs that embedded core: it stays one HTML file, no build step for the core itself.
- Video attachments up to 45 MB with onboard compression so larger originals can still be sent and viewed.
- Stronger image encryption and trace avoidance, metadata stripping on the table.
- Discord-style emoji reactions over the versioned control envelope.
- These land as a blueprint addendum before the R2 build wave fires.

TARGET SYSTEM, from accepted research: single-file WebRTC chat, DTLS data channel, 16 KB chunk framing, receiver preallocation up to 50 MiB with the zero-padding export bug F-02, per-message AEAD planned per 01-research/output/04-crypto-design.md, versioned control envelope planned per the blueprint, wipe paths and OS trace limits per 06-ops-defense.md, Chromium desktop is the live test target.

HARD CONSTRAINT on every design: each feature must work in BOTH modes, the standalone HTML file and the executable shell, or be explicitly flagged EXEC-ONLY with the reason. The core file keeps no external assets and no build step. A feature that only makes sense inside packaging is packaging, not core, and gets labeled as such.

BINDING CONSTRAINTS:
- English. No em dashes and no en dashes anywhere in your output. Periods and commas.
- Every external claim carries a verified source URL, fetched by you with the title checked. Mark UNVERIFIED anything you could not verify. Never invent a number: bundle sizes, memory figures and API limits come from measured or documented sources you cite.
- Read-only mission except your one output file. No edits to input/, the research outputs, the blueprint or the contracts.
- Cite the wave-1 research files by path wherever your design builds on them.
- Time budget about 25 minutes of tool work. Past it, STATUS: partial and stop.
- Incremental writes: one write_file per completed section.
- MANDATORY SELF-CHECK: end your output with every acceptance item as PASS or FAIL with evidence.

EVALUATION per option where you rank alternatives: what it is, source URL, what it adds to or costs the security posture, honest size or memory numbers with their source, engagement fit, verdict.
