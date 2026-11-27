# Stage 05 verify, proof

DATE: 2026-11-27
LEAD: the Hermes default session
STATE AT RUN: Development da6fd8e pushed, artifact 2092e0e9e8e3418ba167e22b99623094e0f5d05ea876014874be1e3c4b53b87b, 169,810 bytes

## Acceptance commands and raw output

- shasum -a 256 03-build/output/ephemeral-chat-v2.html: `2092e0e9e8e3418ba167e22b99623094e0f5d05ea876014874be1e3c4b53b87b`
- The wrapper pin in main.cjs: `const CORE_SHA256 = '2092e0e9e8e3418ba167e22b99623094e0f5d05ea876014874be1e3c4b53b87b'` — identical
- The 29 case gate suite, every case exit 0, cover with its relay host argument: see authority-run.log, 29 CASE lines, all exit 0. One process-path error in the first authority script lost the wrapper lines to bad redirects and was rerun with absolute paths, the case lines were never affected.
- sh scripts/selfcheck.sh: exit 0
- sh scripts/fuses.sh read --app <packaged binary>: RunAsNode Disabled, EnableNodeOptionsEnvironmentVariable Disabled, EnableNodeCliInspectArguments Disabled
- sh scripts/e2e-core-load.sh against the packaged app: RESULT: PASS, app://core served 169810 bytes from the pinned core and the page booted to S0
- Stage 04 closed on the round 6 READY verdict at 04-pentest/proof.md; the register summary carries the closure table, sections 6.1 to 6.8
- Engine A headed proof: 04-pentest/output/03-environment-matrix.md section 8, encode 20.5 s end to end, muxer accepting normalized chunks, A8 exemption at 126.5 frames per second, over-cap retry to rung B by disclosed fault injection
- Release shape: 02-release-shape-proof.md, packaged macOS app, fuses read accept side, hash coverage 266 of 266 bundle files, REL-L1 repaired in the project tree per 03-fuses-fix-proof.md
- Residual consolidation: 01-residual-consolidation.md, every residual dispositioned carried or fixed or owner decision
- Dash byte scan over the new stage outputs: zero under /bin/bash 3.2.57 with byte escapes

## Named limits carried honestly

- Windows and Linux fused builds not yet made, macOS only this round
- REL-L2, the V8 snapshot fuse, incompatible with the stock 45.5.0 framework, never enabled, fuses.json row must go false
- Engine A in the shell Chromium 152 not run, the shell core-load blocker there stands
- The fused accept side was proven on the packaged app, the shipped signed-notarized build comes with the release round
- Received file exports land in ~/Downloads/ephemeral by design, planner wording call, owner decision row

## Remaining gate

The owner's live peer test, 12 steps, 05-verify/output/00-live-test-runbook.md, with the result table to be filled by the owner and a second person. The machine-verifiable acceptance set above is green.

VERDICT: READY on the machine acceptance set, the stage closes on the owner's live test.
