# W14 PROBES RETARGET BRIEF, the case suite meets V2

RUN ID: w14-ephemeral-probes-retarget-20261127
MODEL LANE: ds-flash option, deepseek-v4.1-flash at opencode-go, reasoning max
STAGE CONTRACT: /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/03-build/CONTEXT.md
GIT: R2b committed b985061, artifact 6c8c1283, 165,202 bytes, final DOM, you never run git

TASK: you own 03-build/output/probes/ and 03-build/output/evidence/ only. The artifact at 03-build/output/ephemeral-chat-v2.html is final for this round: work against it directly, record its hash in every evidence JSON. No snapshot needed, no other lane edits it.

PART 1, retarget the seven red cases to V2 without weakening a single invariant. The authority for what each case must still prove is the card table in 02-plan/output/blueprint-v2.md section 4.2, its failure mode column. Rules: a case that cannot test its invariant in V2's design exits 2, fail open, it never silently passes. Every retarget records the card row it guards. The seven:
- envelope: craft the unknown-type frame from a captured valid encrypted frame via the shim replay, not plaintext injection. Pass condition stays: unknown-k visible line, no crash, no silent return.
- ratchet: the plaintext-identical-ciphertext invariant plus key isolation. Retarget the exportKey string ban to the real invariant: no private or chain key material may cross to the main thread, structural scan of worker postMessage surfaces, plus the ciphertext-difference behavioral check.
- file: binary frame replay with a truncated tail. The F-02 invariant: no Save anchor, no complete state, when digest or completeness fails.
- budget: burst via replayed valid frames at speed, assert the A8 threshold and trim behavior from the card's named numbers.
- lifecycle: exclude the worker script URL and the case's own synthetic URLs from the blob counter, then assert the pagehide wipe state on the final DOM.
- kill: add a CDP javascript dialog handler so the confirm dialog no longer blocks, then assert the wipe path and the clipboard clear on the kill path.
- migrate: confirm the new SAS after the channel count check, then assert the migration completes with the fresh keyset.

PART 2, add the six media cases the R2b cards define, from the card table rows R2-16 to R2-22: media, exif, bitrate, playback, imagecap, paste. Each guards its card's failure mode. Known environment limit: VideoEncoder is undefined under the harness's headless disable-gpu Chromium, so engine A executes static-only there and rung B runs live. Cases must therefore assert engine A structurally and rung B behaviorally, and name the headed engine A execution as R4 work in the evidence file. EXIF, projection gating, blob revoke, 60 MP gate and the single acceptFile path are all assertable in the current harness.

PART 3: unblock and run mutation-all now that kill can run, then run the FULL suite, all 20 cases, against the final artifact, every evidence JSON with the hash, and write the summary table into PROBES-SELF-CHECK.md.

BINDING CONSTRAINTS:
- python3 stdlib plus the installed Chromium, no new dependencies.
- ASCII, no em or en dashes in anything you write.
- The six green cases must stay green: selftest, sas, code, rotate, stun, cover.
- Time budget about 35 minutes. Past it, STATUS: partial and stop.
- MANDATORY SELF-CHECK: every retarget and new case as PASS, FAIL or EXIT-2 with commands and raw output, plus the full suite table.
