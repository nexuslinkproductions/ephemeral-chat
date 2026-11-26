# 02-plan: the V2 hardening blueprint

Goal: synthesize the accepted research into one buildable blueprint: the V2 architecture, what stays from V1, the sliced R2 build plan with gates, and the residual risk list.

## Inputs

| File | Section |
|---|---|
| `../_config/SETUP.md` | full file, owner rulings |
| `../01-research/output/01-trust-map.md` | Trust Boundaries, Wipe Paths, Crypto Reality, Claims Versus Code |
| `../01-research/output/02-audit-findings.md` | findings ledger, strengths S-1 to S-8 |
| `../01-research/output/03-threat-model.md` | Top 10 risks |
| `../01-research/output/04-crypto-design.md` | Recommended Stack, bundle measurements |
| `../01-research/output/05-transport-hardening.md` | ranked options both variants, INFRA flags |
| `../01-research/output/06-ops-defense.md` | kill switch, migration M1 to M5, monitor design |
| `../01-research/output/07-skill-sweep.md` | round plan gates |

## Process

One synthesis lane on deepseek-v4.1-flash at reasoning max, incremental writes. An independent reviewer on claude-haiku-5-5 re-derives the research base in parallel and writes `../01-research/proof.md`; its findings steer the blueprint before the build wave starts.

## Outputs

`output/blueprint-v2.md`

## Acceptance

- `test -s output/blueprint-v2.md` exits 0
- `grep -c '^## ' output/blueprint-v2.md` prints at least 5
- `grep -L 'SELF-CHECK' output/blueprint-v2.md` prints nothing
- `grep -rl $'\xe2\x80\x94' output/ ; grep -rl $'\xe2\x80\x93' output/` print nothing (byte escapes pass under bash 3.2 and 5)
- Every design decision cites the research file it builds on; the default serverless path carries no INFRA item

Scope: these checks prove structure, citation and hygiene, not design correctness. The owner reviews the blueprint against the research before the R2 build wave starts.

Completeness: blueprint-v2.md must exist with five sections: threat baseline, V2 architecture, what stays, build plan, residual risk.
