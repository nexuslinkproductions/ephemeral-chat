# W28 FUSES FIX BRIEF, REL-L1 in the project tree

RUN ID: w28-ephemeral-fuses-fix-20261127
MODEL LANE: ds-flash option, deepseek-v4.1-flash at opencode-go, reasoning max
STAGE CONTRACT: /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/05-verify/CONTEXT.md
STATE: Development e9930c9. The packaged app proof lives at 05-verify/output/02-release-shape-proof.md and its defects REL-L1 to REL-L3 are recorded there. Never run git.

TASK: fix REL-L1 in the project tree and prove the fix:

1. Load the electron-release-packaging skill first, it is newly installed and covers the fused release build.
2. Read 03-build/output/wrapper/scripts/fuses.sh. The defect: it passes lowerCamel fuse names to @electron/fuses 2.1.3, which requires the enum names. The w26 release lane repaired a scratch copy with a 9 entry mapping; re-derive that mapping and apply it to the project tree script.
3. Prove the fix on a scratch copy of the packaged app at .agent-runs/w26-lane2-release-shape/artifacts/ephemeral.app: run the repaired fuses.sh read against it and confirm the three required fuses read Disabled, then run a write noop or a full write re-read cycle if the ad-hoc signature cost REL-L3 makes that safe on a copy, and record what you measured.
4. Update BUILD.md with the corrected invocation and the release order from REL-L3: package, fuse, codesign.
5. The V8 snapshot fuse REL-L2 stays carried, do not enable it.

BINDING: your writes are wrapper/scripts/fuses.sh, wrapper/BUILD.md, and your evidence file 05-verify/output/03-fuses-fix-proof.md. Tools install only in scratch. ASCII, zero em or en dashes. Budget about 25 minutes. MANDATORY SELF-CHECK with commands and raw output.
