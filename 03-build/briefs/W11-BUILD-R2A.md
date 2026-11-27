# W11 BUILD R2A BRIEF, the security spine

RUN ID: w11-ephemeral-build-r2a-20261127
MODEL LANE: ds-flash option, deepseek-v4.1-flash at opencode-go, reasoning max
STAGE CONTRACT: /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/03-build/CONTEXT.md
PROJECT ROOT: /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL
GIT: repo initialized, baseline 7df5cd7 on main and Development, lanes never run git, the lead commits after integration

TASK: build the V2 security spine, four lanes, single writer per scope.

LANE SCOPE RULE, binding: you write only inside your named scope. Another lane owns every other path. gate.py is owned by the PROBES lane only, the core HTML artifact is owned by the CORE lane only, monitor/ by the MONITOR lane, wrapper/ and cover/ by the WRAPPER lane. input/, 01-research/, 02-plan/ and _config/ are read-only to every lane.

COMMON CONSTRAINTS, binding:
- English. No em dashes and no en dashes anywhere in any file you write, including UI strings, comments and code comments. A byte scan is part of your self-check.
- ASCII only in every written file.
- No new dependencies: python3 stdlib for probes, the installed Chromium for behavioral cases, Swift stdlib for the monitor, static files only for the wrapper.
- Incremental work: one card at a time, run the check you can run, record evidence, then the next card.
- Time budget: CORE about 35 minutes, PROBES about 30, MONITOR and WRAPPER about 25 each. Past it, STATUS: partial and stop, partial work is kept, it is the next wave's base.
- MANDATORY SELF-CHECK per lane: every card as PASS or FAIL with the command and raw output, plus the dash and ASCII byte scans of your own files.

CARD DEFINITIONS: the authority is the card table in 02-plan/output/blueprint-v2.md section 4.2, each row carries scope, gate command and failure mode. Read the blueprint sections named for your cards before writing. The research files it cites are the design sources, read the named sections only.
