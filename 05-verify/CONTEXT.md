# Stage 05 verify, stage contract

RUN WINDOW: opens 2026-11-27, closes on verdict plus the owner's live peer test.

## Goal

The final gate before the release round. Two things close it: the machine-verifiable acceptance set green on the shipped shape, and the owner's live peer test passing with a real second person. The residual register is consolidated and stated, never hidden.

## Inputs

- The artifact at the pinned sha in the wrapper, plus the packaged executable shape once the release lane lands it
- 03-build/proof.md, 04-pentest/proof.md with its verdict line, 00-register-summary.md with the closure table and the named ceiling list
- The residual rows 1 to 25 in 02-plan/output/blueprint-v2.md plus every residual the pentest and repair rounds added
- 03-build/output/probes/gate.py, the 29 case suite, the authority logs in evidence/
- The monitor package, 21 tests, and the wrapper tree with selfcheck, build-gate, e2e-core-load

## Process

1. The release lane proves the packaged shape: a built macOS app with fuses off on runAsNode, nodeOptions and nodeCliInspect, verified by an @electron/fuses read that ACCEPTS it, hashed with the bundle included, e2e core-load green against the packaged app.
2. The headed engine A leg re-runs on the current artifact, the F-ENV-1 fix verified live, the over-cap clip through the exemption at full speed.
3. The runbook lane consolidates the residual register and writes the live peer test runbook: what the owner and a second person do, in what order, and what proves each step.
4. The lead runs the authority set on the final shape and the stage verdict is written from proof.md.
5. The owner runs the live peer test. Its outcome is the owner's gate, recorded in the runbook file with the date and the pass or fail per step.

## Outputs

- output/00-live-test-runbook.md
- output/01-residual-consolidation.md
- output/02-release-shape-proof.md when the packaged lane lands
- proof.md, one verdict line

## Acceptance

The lead runs and records:
- shasum -a 256 on the artifact, matches the wrapper pin
- The 29 case suite, exit 0 each, cover with its relay host argument
- sh scripts/selfcheck.sh in the wrapper, exit 0
- The fuses read on the packaged binary, all three off
- sh scripts/e2e-core-load.sh against the packaged app, RESULT PASS
- grep -c dash byte escapes over every new file, zero under both shells
- The residual consolidation lists every residual with its source row and its disposition, carried or fixed or owner decision

ASCII only, zero em and en dashes, input/ read-only, workers write only their declared files.
