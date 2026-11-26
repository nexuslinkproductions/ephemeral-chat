# W10 plan review proof, round 4 of 4 (lead-authorized exception round)

Run: w10-ephemeral-planreview4-20261126. Reviewer: claude-haiku-5-5, fresh context, independent of the blueprint producer (deepseek-v4.1-flash). Tier: Standard (gate review, independent reviewer at delivery). Contract: 02-plan/CONTEXT.md. Brief: 02-plan/briefs/W10-REVIEW4.md. This file replaces the round 3 proof.

Artifact: 02-plan/output/blueprint-v2.md. 155,554 bytes, 1,020 lines, sha256 eb82ce09f57b00e0640199ab2d6dd7ce47a50abf7728b6141c4b10d11d6c833e, mtime 00:36:58. Same bytes, lines and hash at the first read (00:38) and at the last check (00:44).

Lane note: no delegation. Every grade below rests on a command run in this pass or a line read in this pass, from the artifact or from the named research file. Nothing was written except this file.

## Summary

- F4 holds at its second site. R3-W5 (line 791) no longer refuses the older signed artifact. Row 25 (line 603) records that case as the accepted residual, and 6.1 step 4 (line 651) states the limit.
- Stage gates pass under /bin/bash 3.2.57 and /opt/homebrew/bin/bash 5.3.20, with positive controls. One control could not be run. See section 1.
- N1, N2, N3 and N4 each pass as the brief states them.
- The regression sweep is clean: no new external URL, 25 numbered rows in section 5, 7 rows in the round 3 block.
- Six non-blocking residuals are listed in section 5. None is an N-item that landed broken, so no repair is needed.

## 1. Stage gates and regression, both shells

The same script ran under each shell. The output matched in both.

| Check | /bin/bash 3.2.57 | /opt/homebrew/bin/bash 5.3.20 | Result |
|---|---|---|---|
| test -s output/blueprint-v2.md | exit 0 | exit 0 | PASS |
| grep -c '^## ' (bar 5) | 7 | 7 | PASS |
| grep -L 'SELF-CHECK' | no output, exit 0 | no output, exit 0 | PASS |
| grep -rl em byte form over output/ | no output, exit 1 | no output, exit 1 | PASS |
| grep -rl en byte form over output/ | no output, exit 1 | no output, exit 1 | PASS |
| Positive control, em, -rl on a real file (/usr/share/man/man1/heap.1) | listed, exit 0 | listed, exit 0 | holds |
| Positive control, em, stdin byte line | 1 | 1 | holds |
| Positive control, en, stdin byte line | 1 | 1 | holds |
| Negative control, hyphen line, em form | 0, exit 1 | 0, exit 1 | holds |
| Default path (N2): sed range, grep -Eiwc over relay, coturn, turn, turns | 0, exit 1 | 0, exit 1 | PASS |
| Default path positive control: bare TURN and turn:443 | 1 | 1 | holds |
| Default path word control: a return line | 0, exit 1 | 0, exit 1 | holds |
| Body-scoped F4 phrases, before the SELF-CHECK heading | no output, exit 1 | no output, exit 1 | PASS |
| Body-scoped concept count: older signed, rollback, refus | 14 | 14 | read in section 2 |

Limit (measured): no en-dash file exists in the search scope. I searched /usr/share, the sibling 01-research/output and the home tree for uts46data.py, which round 3 used. So the en -rl real-file control was not run. The en byte form was checked through its stdin control, and the -rl form through the em control. The en and em greps differ only in the byte sequence. This is a labelled gap, not a failure.

Other sweep results (measured):
- Code point scan, read-only: U+2014 0, U+2013 0, U+2015 0, U+2212 0, U+2012 0. Non-ASCII bytes 0.
- External URLs: zero http:// or https:// URLs and zero www. tokens. Scheme tokens are file:// on lines 523, 722 and 790 (4 occurrences, local paths), app:// (4 occurrences, the local protocol name), smb:// on line 790 (an attack payload string in R3-W4), and a bare https: name on line 721 (the BC-W3 allowlist). The only domain-like token is ephemeral.app, a bundle name. No round 3 snapshot exists to diff, so this is an inventory check by token class. No new external URL was found.
- Section 5: 25 numbered rows, numbered 1 to 25 in sequence.
- Round 3 disposition block: 7 data rows, each PASS: F4 second site, residual row 25, F4 concept re-grep, N1, N2, N3, N4.

## 2. F4 at its second site (R3-W5): holds

Each item below was read in the current file.

- R3-W5, line 791. Refuses the unsigned artifact, the tampered artifact and the mismatched hash manifest. Names the failing check: the detached signature over the hash list, then the per-artifact SHA-256 comparison. The installed binary is unchanged.
- R3-W5 accepts an older signed artifact whose own hash and signature verify. It records that case as residual row 25. It cites 6.1 step 4 and 11 sections 5.2 and 5.5. The About build date warning is named as the compensating control.
- Row 25, line 603, sits in the section 5 table. Its source is 11 sections 5.2 and 5.5 plus 6.1 step 4. Its decision changer is the signed channel with a monotonic counter, a key off the build machine, a verifying client and a revocation path. The row names 11 section 5.5 as the pricing, and names the case a V3 conversation.
- 6.1 step 4, line 651. States the limit: V2 has no version counter and no signed metadata, so the manual protocol cannot enforce rollback refusal. Keeps the 90-day About warning.
- 11 section 5.2, line 334: "If it is more than 90 days old, get a new one." This is the age warning the blueprint cites.
- 11 section 5.5, line 353: a signed channel needs one new trust root, one new network client and one new key management problem. It is a V3 conversation at the earliest.
- Body-scoped grep, before the SELF-CHECK heading, for "refuse rollback", "refusing an older" and "refuse an older", case-insensitive: no output, exit 1, both shells.
- Body-scoped concept grep for "older signed", "rollback" or "refus": 14 lines, both shells. Each line was read in this pass:

| Line | Content | Class |
|---|---|---|
| 263 | Unknown v shows peer is newer or older, and refuses content | firing control |
| 295 | window.close is refused by browsers, so the panic exit uses location.replace | design rationale, not a rollback claim |
| 317 | Migration refused while a transfer is active | firing control |
| 444 | R2-13 gathering refused when no relay host is configured | test case |
| 478 | Rekey rollback and replay of an old epoch | test case |
| 506 | csp-policy-generator install refused by the lead's Hermes session | record of an install refusal, not an update |
| 536 | Third context refused | test case |
| 603 | Row 25, the rollback limit | residual, states the limit |
| 651 | 6.1 step 4 | limit statement |
| 673 | R2-19 over-cap refusal | firing control |
| 678 | Ladder refuses above 600 s | firing control |
| 774 | R3-BS-15 extra channels refused | firing control |
| 791 | R3-W5 | three refusals, plus the accepted residual |
| 792 | R3-W6 refuse to launch | firing control |

No line promises rollback refusal.

- The brief lists the ladder, R3-BS-15 and R3-W6 at lines 677, 773 and 791. In the current file they sit at 678, 774 and 792, one row later, because row 25 was inserted at 603. The repair block uses the current numbers, and they match the file.
- Trail. The round 3 proof (replaced by this file, section 2) recorded F4 as first flagged in round 2 at 6.1 step 4. The round 2 repair (briefs/W7-REPAIR2.md, line 17) changed step 4. The round 3 review failed F4 again at R3-W5 (line 790 then). The W9 repair (briefs/W9-REPAIR3.md) fixed R3-W5. This pass finds F4 holding. Two failing reviews are on the record, and the third-failure rule does not apply.

## 3. The four confirmations

- N1 passes. Rows F1 (line 938), F4 (line 941), F7 (line 944) and F9 (line 946) now scope counts to the body before the SELF-CHECK heading. Reruns under both shells reproduce each quoted output: "focus signal" 0, exit 1; "Refuse rollback" 0, exit 1; "top unaudited" 0, exit 1; "runs as the user with no sandbox" 1, exit 0, with the one hit at line 730 (BC-W12).
- N2 passes. Rows 841, 871 and 979 carry the default-path check with the case flag and the word flag. The fresh output is 0, exit 1, under both shells. The positive control prints 1 for bare TURN and turn:443, and 0 for a return line, so the word flag works.
- N3 passes, with a cosmetic residual. UX-01, UX-05, UX-07 and UX-08 names match 13 section 5 exactly (13 lines 466, 470, 472 and 473). Their scope items match 13 item for item. Two differences remain: the gate path is written as gate.py where 13 writes 03-build/output/probes/gate.py, and the parentheses around "case" are dropped. The same form is in the round 2 rows that round 3 accepted. See R-3.
- N4 passes. BC-W8 (line 726) states: no update check, no notification, manual hash-verified replacement, a download only by the user's own action, and no install. That matches 6.1 line 646 ("Updater: none. No auto-updater, no update check, no version ping") and the 6.6 row at line 807 ("No update check in V2").

## 4. Regression sweep

The results are in section 1. Every item in the brief's sweep was run. The en -rl real-file control is the one gap, as stated in section 1.

## 5. Non-blocking residuals

- R-1. Source conflict on R3-W5. 15 section 2 (15-cve-packaging-native.md line 64) still says "The app refuses all four", and that list includes "an older signed artifact (rollback)". The blueprint still cites 15 section 2 as the R3-W5 source but no longer refuses that case. The departure is disclosed in R3-W5 and in row 25, so it is not hidden. Owner call: add the same residual note to 15, or keep the blueprint as the record.
- R-2. UX-06 scope drift. Line 697 reads "Always enabled button" and "the layer rule". 13 line 471 reads "Always-enabled button" and "layer rule". Round 3 recorded UX-06 as matching apart from punctuation, which missed the article. UX-06 is outside N3. The N3 repair row lists only UX-01, 05, 07 and 08, so this repair did not touch it (inferred). Meaning unchanged.
- R-3. Gate path form. UX-01, UX-05, UX-07 and UX-08 write gate.py where 13 writes the full path. This is the same form as the accepted round 2 rows. Strict verbatim text would be one string per row.
- R-4. Failure-mode wording. The failure column differs in wording from 13 in nine of ten UX rows. UX-09 matches. The meaning matches in every row read. UX-10 adds "of 997 bytes", which traces to 13 section 2.4 (lines 224 and 238). This is outside N3.
- R-5. Brief line numbers. The brief's 677, 773 and 791 are one row behind the file. The artifact's repair block uses the current numbers, which match the file.
- R-6. Not run. "Every design decision cites the research file" has no shell command in the contract. It was not re-derived this round, as in round 3. The default-path check is run through its pattern (N2), not by a whole-file INFRA read. The en -rl real-file control is missing (section 1).

## 6. Outcome

Gates pass under both shells. F4 holds at R3-W5, in 6.1 step 4 and in row 25. N1 to N4 pass. No non-blocking item is broken, so no repair is needed. R-1 to R-6 are for the owner. Round 4 is the last permitted round.

STATUS: complete, inside the 20 minute budget.

VERDICT: READY
