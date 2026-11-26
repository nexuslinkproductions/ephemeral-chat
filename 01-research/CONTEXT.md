# 01-research: recon and hardening knowledge base

Goal: produce the verified trust map, the defect ledger, the threat model, and sourced design research that the hardening rounds build on.

## Inputs

| File | Section |
|---|---|
| `../input/ephemeral-chat-v1.html` | full file |
| `../input/ephemeral-chat-overview.pdf` | full file |

## Process

Seven parallel worker lanes on deepseek-v4.1-flash at reasoning max, each owning exactly one output file below. The lead reviews each landing, re-derives its key claims, and accepts it or sends it back. Wave 3, 2026-11-26, added three lanes on the same terms for the user-ordered skill expansion, files 08, 09 and 10. Wave 5, 2026-11-26, added three platform expansion lanes per the owner scope pivot, files 11, 12 and 13. An accidental interrupt killed wave 5 mid flight: file 13 had already completed and stands, file 12 continues from its partial, file 11 restarts expanded to tri platform, and the vulnerability surface expansion adds files 14 and 15.

## Outputs

`output/01-trust-map.md`, `output/02-audit-findings.md`, `output/03-threat-model.md`, `output/04-crypto-design.md`, `output/05-transport-hardening.md`, `output/06-ops-defense.md`, `output/07-skill-sweep.md`, `output/08-registry-skills.md`, `output/09-open-collections.md`, `output/10-methodology-sources.md`, `output/11-packaging-executable.md`, `output/12-media-pipeline.md`, `output/13-platform-ux.md`, `output/14-cve-browser-stack.md`, `output/15-cve-packaging-native.md`

## Acceptance

- `ls output/*.md | wc -l` prints 15, seven from wave 1, three from the skill expansion, three from the platform expansion, two from the vulnerability surface expansion, contract amended 2026-11-26
- `grep -L "SELF-CHECK" output/*.md` prints nothing
- `grep -rl $'\xe2\x80\x94' output/ ; grep -rl $'\xe2\x80\x93' output/` print nothing (no em or en dashes; byte escapes pass under bash 3.2 and 5)
- Per file: every claim about the app source carries a file:line reference, every external claim carries a source URL, anything unverified is marked UNVERIFIED

Scope: these commands prove presence, self-check sections, and dash hygiene. They do not prove external sources true; the reviewer spot-check carries that.

Completeness: all 15 files above must exist with content before this stage is accepted.
