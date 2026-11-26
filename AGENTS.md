# EPHEMERAL

Security hardening engagement for "ephemeral", Marcel's single-file WebRTC chat. V1 app and product sheet live in input/, read-only. Lead: the Hermes default session. Owner: Marcel Spatz.

## Out of scope

- No public repo. Owner ruling 2026-11-26: a private repo named ephemeral-chat under the active gh account is created once the first completed iteration lands, with nixfred invited. Nothing public and no push beyond that private remote until the owner says ship.
- input/ is read-only source material. Workers never edit it.
- No client or third-party personal data in this workspace.
- Workers write only inside their declared output scope.

## Tools

- Lane liveness and pin: python3 /Users/marcelspatz/.hermes/skills/autonomous-ai-agents/conductor/scripts/pin-delegation.py --show
- Delegation: delegate_task. Standing lane deepseek-v4.1-flash at opencode-go. Verifier family is always a non-builder family, primary claude-haiku-5-5.
- Locate: yuri search "query" -n 10 --json. Never a recursive find across /Users.
- Stage acceptance: run the commands in each stage CONTEXT.md Acceptance block with terminal.

## Pointers

- Rules home: /Users/marcelspatz/.hermes/skills/autonomous-ai-agents/conductor/references/icm-project-setup.md
- Spec: input/ephemeral-chat-overview.pdf
- Stage contracts: 01-research/CONTEXT.md, then 02-plan, 03-build, 04-pentest, 05-verify contracts open at each round start
- Wave briefs: 01-research/briefs/
- Run records: .agent-runs/, gitignored, no credentials

## Known gap

koshirae.py is absent on this host, so K18 doctor cannot run. The Acceptance blocks in each stage contract are the gate; say so rather than claiming a checker verdict.
