# W9 REPAIR 3 BRIEF, the F4 second site plus round 3 residuals

RUN ID: w9-ephemeral-planrepair3-20261126
MODEL LANE: ds-flash option, deepseek-v4.1-flash at opencode-go, reasoning max
STAGE CONTRACT: /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/02-plan/CONTEXT.md
ARTIFACT TO REPAIR: /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/02-plan/output/blueprint-v2.md, in place
AUTHORITY: /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/02-plan/proof.md, the round 3 ledger, read it first

TASK, five items, dispositions binding:

F4 SECOND SITE, the must. R3-W5 at line 790 still refuses an older signed artifact, which contradicts the limit at line 650. Rewrite the row: unsigned artifact, tampered artifact, mismatched hash manifest, all three refused, the failing check named, the installed binary unchanged. An older signed artifact whose own hash and signature verify is accepted as the documented residual, because V2 has no version counter and no signed metadata to refuse it, the About build date warning is the compensating control, cite 6.1 step 4 and 11 sections 5.2 and 5.5. Then add residual row 25 to the section 5 table: the older signed rollback case, its source the same 11 sections, its decision changer the signed channel with a monotonic counter that 11 section 5.5 prices, named as a V3 conversation. Then re-grep the concept across the whole file: every remaining occurrence of refuse, rollback, older, refuse-rollback must either be a test case, a control that actually fires, or the limit statement. The known legitimate ones are the unknown-frame refusal at line 263, the window.close refusal at 295, the migration refusal at 317, the R2-13 gathering refusal at 444, the rekey rollback test case at 478, the third-context refusal at 536, the ladder refusal above 600 s at 677, the R3-BS-15 channel refusal at 773 and the R3-W6 refuse-to-launch at 791. Confirm each, fix any that contradict the limit.

N1. Four SELF-CHECK evidence rows, lines 937, 940, 943 and 945, quote absence counts like grep -c equals 0 while the row text itself contains the counted phrase, so a rerun counts the row and prints 1. Rework each evidence cell so the quoted check is scoped to the body of the file, before the SELF-CHECK heading, or counts section occurrences only, and quote the fresh scoped output.

N2. The default-path check at lines 840, 870 and 978 matches relay, coturn and turns: but omits bare turn: and bare TURN tokens. Extend the pattern to cover both, keeping the case insensitive flag, re-run it, and quote the fresh output, which must stay 0 with exit 1.

N3. UX-01, UX-05, UX-07 and UX-08 rows drift from 13 section 5 names and scopes. Restore all four verbatim from 13, the same fix the round 2 pass already applied to UX-02, UX-03, UX-04, UX-06 and UX-09.

N4. BC-W8 at line 725 says Notify, while 6.1 at line 645 states no auto updater, no update check, no version ping. Align BC-W8 to the design: no silent auto update, the app performs no update check and sends no notification, replacement is manual and hash verified per 6.1, a download may happen only by the user's own action and an install may not.

CLOSE: update the SELF-CHECK with a round 3 disposition block, one row per item above, each PASS with the command or source line that proves it, and update the STATUS line.

BINDING CONSTRAINTS:
- English. No em dashes and no en dashes anywhere.
- Incremental patches. Existing content stays except the rows each item names.
- Only blueprint-v2.md is written. Everything else read-only.
- Keep the stage gates green: size, at least 5 sections, SELF-CHECK present, both dash greps clean.
- Time budget about 20 minutes of tool work. Past it, STATUS: partial and stop.
