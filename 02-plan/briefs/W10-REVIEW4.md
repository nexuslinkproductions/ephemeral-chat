# W10 PLAN REVIEW 4 BRIEF, the authorized exception round

RUN ID: w10-ephemeral-planreview4-20261126
MODEL LANE: haiku-review option, claude-haiku-5-5 at anthropic, reasoning max for this review
STAGE CONTRACT: /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/02-plan/CONTEXT.md
ARTIFACT UNDER REVIEW: /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/02-plan/output/blueprint-v2.md, 155,554 bytes, 1,020 lines, 7 sections
YOUR ONLY WRITE: /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/02-plan/proof.md, fresh, replacing the round 3 verdict
ROUND: 4 of 4, authorized by the lead as a disclosed exception because the gate converged from 18 findings to 1, the round 3 verifier wrote the third failure rule does not apply, and its prescribed path was this fix plus an authorized recheck. The owner can strike the exception with one word.

TASK, one blocker plus four confirmations:

THE BLOCKER, F4 at its second site. Verify in the current file:
- R3-W5 no longer demands refusing an older signed artifact. It refuses unsigned, tampered and mismatched-hash-manifest cases, names the failing check, and accepts the older signed artifact that verifies against its own hash and signature as the documented residual, citing section 6.1 step 4 and 11 sections 5.2 and 5.5, with the About build date warning as the compensating control.
- Residual row 25 exists in the section 5 table with its source and its decision changer, the signed channel priced in 11 section 5.5 as a V3 conversation.
- A body-scoped grep, excluding the SELF-CHECK section, finds zero occurrences of refuse rollback, refusing an older, or refuse an older anywhere in the file. The remaining refuse and rollback occurrences are firing controls, test cases, or the limit statement.

THE FOUR CONFIRMATIONS, non-blocking: N1 the four SELF-CHECK evidence cells now scope their absence counts to the body before the SELF-CHECK heading and the quoted outputs reproduce. N2 the default-path pattern covers bare turn and TURN with a word-boundary flag and the fresh output is 0 exit 1. N3 UX-01, UX-05, UX-07 and UX-08 names and scopes match 13 section 5. N4 BC-W8 performs no update check and sends no notification.

REGRESSION SWEEP: re-run the stage acceptance commands under both shells, both dash greps in byte form with a positive control, confirm no new external URL, confirm section 5 has 25 numbered rows, and confirm the round 3 disposition block carries the seven rows.

VERDICT: end proof.md with exactly one verdict line. READY when F4 holds and the gates pass, with any non-blocking residuals listed. REPAIR only if a non-blocking item landed broken. BLOCKED if F4 fails, which is its third failure, with the full trail named.

BINDING: English. No em or en dashes anywhere in proof.md. Read-only except proof.md. Time budget about 20 minutes of tool work, then STATUS: partial and stop. Never claim verified what you did not run.
