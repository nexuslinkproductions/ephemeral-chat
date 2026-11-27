# 03-build stage contract, round R2a, the security spine

## Goal

Build the V2 security spine from the READY blueprint: cards R2-01 to R2-15 plus the EXEC-ONLY wrapper tree, four lanes in parallel, each with a single writer scope. Media and UX cards, R2-16 to R2-22 and UX-01 to UX-08, are R2b on the landed spine and are not this round.

## Inputs

- `02-plan/output/blueprint-v2.md`, sections 1 and 2 carry the architecture, section 4.2 carries the card table with every gate command, sections 6.1 and 6.4 carry the wrapper decisions
- `input/ephemeral-chat-v1.html`, read-only source, copied to `03-build/output/ephemeral-chat-v2.html` as the working base
- `01-research/output/` files as the blueprint cites them, read-only

## Process

Four lanes, single writer per scope, no lane writes another lane's files:
- CORE lane owns `03-build/output/ephemeral-chat-v2.html` and applies R2-02 to R2-12 in that order, one card at a time, running the available gate cases as they land
- PROBES lane owns `03-build/output/probes/` and `03-build/output/evidence/`, builds `gate.py` per the R2-01 harness card and the case definitions in the card table, selftest first, spine cases next
- MONITOR lane owns `03-build/output/monitor/`, the R2-14 Swift package with its launchd plist and hash-chained log writer, gate `swift test --package-path 03-build/output/monitor`
- WRAPPER lane owns `03-build/output/wrapper/` and `03-build/output/cover/`, the EXEC-ONLY shell files, UX-09 and UX-10 shell parts and the BC-W1 to BC-W8 config tree plus `relay.env.example`, files only, no binary build, no npm install

The lead integrates after the lanes land: runs every gate case, commits on Development, then files R2b.

## Outputs

`03-build/output/ephemeral-chat-v2.html`, `03-build/output/probes/gate.py` with `probes/fixtures/`, `03-build/output/monitor/` package, `03-build/output/wrapper/` tree, `03-build/output/cover/relay.env.example`, `03-build/output/evidence/`

## Acceptance

- Each lane's named gate command runs and exits 0 at integration, cases still red mid-build are expected and named in the lane SELF-CHECK
- `gate.py selftest` exits 0
- The core artifact holds its form factor: single HTML file, no external assets, no build step, ASCII only, no em or en dashes anywhere including UI strings and comments, byte scan proves it
- No lane writes outside its scope. input/, 01-research/, 02-plan/, _config/ are read-only to all lanes
- Every lane output carries a SELF-CHECK with per-card evidence: command, raw output, PASS or FAIL
- Probes must use python3 stdlib plus the installed Chromium for behavioral cases, zero new dependencies
- The wrapper tree is static files with a self-check that parses them, JSON validity, flag table completeness, no binary produced this round

Completeness: all four scopes above exist with content before this round is accepted.
