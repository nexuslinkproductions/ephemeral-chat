# W15 BUILD REVIEW BRIEF, the whole R2

RUN ID: w15-ephemeral-buildreview-20261127
MODEL LANE: haiku-review option, claude-haiku-5-5 at anthropic, reasoning max for this review
STAGE CONTRACT: /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/03-build/CONTEXT.md
YOUR ONLY WRITE: /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/03-build/proof.md, fresh
ARTIFACTS UNDER REVIEW, all at commit 4a5d553 on Development:
- 03-build/output/ephemeral-chat-v2.html, 165,202 bytes, sha256 6c8c1283, the V2 core, single file, no external assets
- 03-build/output/probes/gate.py with fixtures, 20 cases
- 03-build/output/monitor/, the Swift package, 21 tests
- 03-build/output/wrapper/ plus cover/relay.env.example, the shell config tree
- 03-build/output/CORE-SELFCHECK.md and 03-build/output/evidence/ including lead-integration-run.log

TASK, five parts:

Part 1, artifact form and hygiene: single HTML file, no external assets, no build step for the core, ASCII only, zero em and en dashes, byte scan yourself. The muxer block measures 31,133 bytes against the blueprint pin of 31,103: the builder documented that the pinned build discards its exports so a 30 byte global assignment was required; verify that explanation holds in the code.

Part 2, gates, your own runs: run gate.py selftest, sas, code, rotate, stun, cover, media-order, exif, playback, and mutation-all against the artifact. Compare against evidence/lead-integration-run.log, the lead's 20 case run. Any disagreement between your runs and the recorded ones is a finding.

Part 3, invariant integrity, the anti fake green check: read the retarget code for envelope, ratchet, file, budget, lifecycle, kill and migrate in gate.py against each card's failure mode in the blueprint card table. Confirm no retarget weakened what it guards: unknown frames still cause visible state or kill, private key material still cannot cross to the main thread, truncated transfers still produce no Save anchor, the A8 budget still trips, pagehide still wipes, the kill path still clears the clipboard, migration still refuses a tampered fingerprint. Sample at least five of the seven.

Part 4, satellites: run swift test --package-path 03-build/output/monitor and the wrapper scripts/selfcheck.sh yourself. Verify the wrapper still fails closed on the zero CORE_SHA256 placeholder, which is correct until the post review paste.

Part 5, blueprint coverage spot check: sample six cards across the spine, media and UX, and confirm each card's named scope exists in the artifact: R2-03 crypto in the worker, R2-09 kill switch, R2-16 encryption ordering, R2-18 engine A, UX-02 reactions, UX-03 screen machine.

VERDICT: end proof.md with exactly one verdict line, READY, REPAIR with the item list, or BLOCKED with the reason. Findings ledger with severity, location, evidence, fix. The build is READY when your gate runs match the recorded runs, no invariant is weakened, the satellites pass, and the spot checks hold. Non-blocking items get listed, not repaired.

BINDING: English. No em or en dashes anywhere in proof.md. Read-only except proof.md. Time budget about 30 minutes. Never claim verified what you did not run.
