# W4 REPAIR BRIEF, blueprint round 1 repair per the independent review

RUN ID: w4-ephemeral-planrepair-20261126
MODEL LANE: deepseek-v4.1-flash at opencode-go, reasoning max
STAGE CONTRACT: /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/02-plan/CONTEXT.md
ARTIFACT TO REPAIR: /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/02-plan/output/blueprint-v2.md, in place
REVIEW TO SATISFY: /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/02-plan/proof.md, read it first, it is the authority on what to fix

DISPOSITIONS, binding, do not re-litigate these, apply them:

Item a, citations. Four fixes. Attribute the 32,503 byte measurement to the x25519 row only and label any P-256 figure as unmeasured. Align header encryption with what 04-crypto-design.md actually recommends, V2.1, and say so instead of claiming R2. Correct the 50 MiB zero count to 52,428,800 bytes or state the 50,000,000 byte figure as a decimal-MB convention, one or the other, clearly. Change the RFC 8827 reference from section 7 to 6.5.

Item e, flagged claims. Mark the trickle-attribute claim and the invite-carries-public-IP claim as resting on the transport file's now-UNVERIFIED Chromium sample, with R3 re-derivation named as the closer. The lead already tagged the sample UNVERIFIED in 01-research/output/05-transport-hardening.md; match that wording.

Item d, ruling sources. The single-file no-build no-external-assets ruling now lives in _config/SETUP.md with its product-sheet source, cite SETUP.md there. Cite 01-research/output/05-transport-hardening.md as the home of the INFRA tag rule. For I-4, either state one concrete cadence taken from 06-ops-defense.md or delete the cadence promise. Add one residual row recording honestly that no V2 default mode achieves undetectability against a passive ISP, that the cover mode narrows it, and that the owner's undetectable target is therefore partially met.

Item b, cards. Give R2-13 a gate that can pass as written: name the relay-host input the harness provides, a loopback mock or a parameterized host, and write the gate command against it. Re-scope the gate cases that sit outside their cards' declared scopes, either widen the declared scope to name the harness path or move the gate inside it.

Item f, contradictions. Fix the R4 capture check so the filter actually proves the no-HTTPS claim, name the right expression. Resolve the three-STUN-providers line against the singular STUN expectation, one expected provider or an explicit fallback order with what the capture shows for each. Align the 30 second clipboard rule with 06-ops-defense.md section 3.5, whichever of the two is the source of truth.

Item c, ledger. Add F-01 and F-02 as rows in the 1.4 findings ledger so all 13 appear there, they are already the headers of 1.1 and 1.2, the ledger must not omit them.

Stale self-check. The blueprint's self-check row 22 predates the lead's 23:02:39 amendments to research files 03 and 05. Update that row to reflect the current files.

Skill annex, new section under 4.3. Add a short subsection covering the skill expansion that landed after this blueprint was written: the two installed skills, fec-security-review and csp-bypass-advanced, with their install identifiers; the blocked one, csp-policy-generator, blocked by the Hermes install scan on a DANGEROUS supply-chain verdict, its knowledge substituted by the attack-side directive matrix; the authored-skill queue from 01-research/output/10-methodology-sources.md section 5.3, five items in order; and the gap status from 08 and 09, WebRTC and privacy-monitor stay authored-probe territory. Cite 08, 09 and 10 by path.

BINDING CONSTRAINTS:
- English. No em dashes and no en dashes anywhere in the artifact.
- Every edit preserves the stage gates: size, section count at least 5, SELF-CHECK present, dash greps clean under the byte-escape form now in the stage contract.
- Only the blueprint file is written. SETUP.md, the contracts, the research outputs and proof.md are read-only to you.
- Cite sources for every corrected claim. No invented numbers.
- Time budget about 25 minutes of tool work. Past it, STATUS: partial and stop.
- Incremental edits: patch the file per item as you go, never one giant rewrite.

MANDATORY SELF-CHECK, binding: after the repairs, re-run the stage acceptance commands, confirm every disposition above is applied, and update the artifact's SELF-CHECK section listing every item as PASS or FAIL with evidence.
