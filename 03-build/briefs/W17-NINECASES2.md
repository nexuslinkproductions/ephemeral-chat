# W17 NINE CASES RESPAWN BRIEF, continue from the triaged state

RUN ID: w17-ephemeral-ninecases2-20261127
MODEL LANE: ds-flash option, deepseek-v4.1-flash at opencode-go, reasoning max
STAGE CONTRACT: /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/03-build/CONTEXT.md
YOU NEVER RUN GIT. Prior lane w16 was interrupted at its runtime ceiling before registering any case. gate.py parses clean with its groundwork patches in place: file-bad-start and file-bad-digest mutation modes plus an open_app copy_offer parameter. Keep them, build on them.

TASK: same as 03-build/briefs/W16-NINECASES.md, the nine cases transcode, mid, react, nav, sas-ui, pair, panic, gallery, a11y, each guarding its card failure mode from the blueprint card table. Read the W16 brief for the per case detail. The differences that make this respawn succeed:

1. INCREMENTAL PERSISTENCE, the binding discipline: build ONE case fully, run it, confirm its exit code, write its evidence, then move to the next, in this order: panic, react, mid, nav, gallery, pair, sas-ui, a11y, transcode. The priority front loads the two binding proof cases. At any moment the file must hold only complete cases, never a half written one. An interrupt then costs one case, not nine.
2. READ SMALL: do NOT read gate.py whole. Read only the case dispatch table and ONE existing behavioral case as the pattern, at most 200 lines. You already have the artifact structure from the W16 brief's card list.
3. The 20 existing cases must stay green. After your last case lands, run the full 29 case suite and write the suite table into PROBES-SELF-CHECK.md.
4. Binding proof stays: revert the panic and react guards, show each FAIL, restore, show PASS.
5. A case that cannot test its invariant exits 2, never a silent pass.
6. python3 stdlib plus the installed Chromium only. ASCII, zero em or en dashes. Your writes: probes/ and evidence/ only.
7. Budget: work the case list until done. If you are stopped early, the incremental discipline means your landed cases stand.

MANDATORY SELF-CHECK: per case PASS or FAIL or EXIT 2 with commands and raw output, the 29 case suite table, the binding proof for panic and react.
