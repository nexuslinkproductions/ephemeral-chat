# W12 FIX WAVE BRIEF, R2a blockers and probe tuning

RUN ID: w12-ephemeral-fix-r2a-20261127
MODEL LANE: ds-flash option, deepseek-v4.1-flash at opencode-go, reasoning max
STAGE CONTRACT: /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/03-build/CONTEXT.md
GIT: spine committed e18733a on Development, lanes never run git

TASK, two lanes in parallel:

COREFIX lane, owns 03-build/output/ephemeral-chat-v2.html and CORE-SELFCHECK.md only:
1. Class fix, base64url. Lines 499 and 1137 both call atob on a base64url body, padding it but never converting the URL safe alphabet, so any invite or reply containing dash or underscore throws and the pair never completes. Write one shared decode helper, convert dash to plus and underscore to slash before padding, route BOTH call sites through it, then grep the whole artifact for any remaining raw atob and route those too. Verify: a 909 character invite containing both a dash and an underscore round trips between two contexts.
2. SAS confirm navigation. The probes lane measured: both sides render the same 60 digits, both click confirmSas, then the page is at about:blank and the composer is gone. Read the evidence JSONs in 03-build/output/evidence/ and the confirmSas handler at line 1525, re-derive the cause, fix it so after both sides confirm the session screen stays, the composer is enabled, and no navigation fires.
3. R2-11 Migrate. The current artifact ends both contexts at migration-failed and never reaches the new SAS. Read CORE-SELFCHECK.md and the migrate evidence, reproduce the failure in two browser contexts, root cause it, fix it, and verify the behavioral run reaches the new SAS on both sides with the fresh keyset.
4. Close: run every gate case against the fixed artifact and record raw output per case. At your end, every spine case that can pass must pass: selftest, envelope, ratchet, sas, file, budget, code, lifecycle, kill, rotate, migrate, stun, cover with the relay flag. Update CORE-SELFCHECK.md with per-card rows.

PROBES2 lane, owns 03-build/output/probes/ and 03-build/output/evidence/ only:
1. Pin control discovery for the rotate and migrate cases to the literal selectors, button id rotate, button id migrate, per the lane's own left-over note.
2. Tune the mutation-all guard patterns to the landed V2: the preparse cap appears as 65536 and as 64 times 1024, and any other guard whose pattern no longer matches the real code.
3. Snapshot the artifact ONCE at your start, hash the snapshot, run all cases against that snapshot, record evidence. The COREFIX lane is editing the live file in parallel, so your snapshot isolates you. The lead re-runs everything after both lanes land, and that integration run is the authority.
4. Update PROBES-SELF-CHECK.md with the tuning rows and the snapshot hash.

BINDING CONSTRAINTS, both lanes:
- English. No em dashes and no en dashes in any file you write, ASCII only.
- Single writer scopes as named above. input/, 01-research/, 02-plan/, _config/, monitor/, wrapper/ are read-only to you.
- No new dependencies. python3 stdlib, installed Chromium, the artifact as it stands.
- COREFIX budget about 35 minutes, PROBES2 about 20. Past it, STATUS: partial and stop, partial work is the next wave's base.
- MANDATORY SELF-CHECK update with commands and raw output for every item.
