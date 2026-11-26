# W2 REVIEW BRIEF, fresh-context acceptance of the 01-research stage

RUN ID: w2-ephemeral-hardening-20261126
MODEL LANE: claude-haiku-5-5 at anthropic, reasoning max. You are the independent reviewer; a different model family produced every file you grade.
STAGE CONTRACT: /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/01-research/CONTEXT.md
SOURCE, read only: /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/input/ephemeral-chat-v1.html

TASK: two jobs, one output file.

JOB 1: rerun the stage acceptance commands from the stage contract verbatim and record each with its raw output and a name=gate exit=code line: the file count over output/0*.md expecting 7; grep -L over output/0*.md for SELF-CHECK expecting no output; the em dash and en dash greps over output/ expecting no output.

JOB 2: re-derive these six load-bearing claims against the source with your own grep and sed evidence, each marked PASS, FAIL or UNVERIFIABLE with the command you ran:
1. No safety-number or fingerprint comparison exists anywhere in the source; the pairing code is the only trust anchor.
2. endIncoming exports the full preallocated buffer when bad is false, and card.done enables Save before the incomplete check, so a truncated transfer saves zero-padded bytes.
3. The only crypto API usage is crypto.randomUUID; text, file bytes and file names cross the channel as plaintext inside DTLS.
4. The Wipe button stays disabled until the data channel opens, so a user stuck at pairing cannot kill a live code.
5. The source applies no ICE candidate filtering, no iceTransportPolicy and no relay config, so the packed invite ships the browser default candidates, which include the public-IP server-reflexive candidate.
6. unpack decompresses peer-supplied gzip through DecompressionStream with no size cap, near lines 732 to 740.

Context note: an earlier lane flagged missing SELF-CHECK sections and dashes in output files 01, 03 and 06 while those files were still being written. The disk state after all lanes finished shows those flags stale. Say whether your rerun agrees.

REQUIRED OUTPUT: /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/01-research/proof.md
Structure: a GATES section with name=gate exit= lines and raw output, a CLAIMS section with the six verdicts and the commands, then exactly one final verdict line: STAGE ACCEPTED, or STAGE ACCEPTED WITH CAVEATS plus the caveat list, or STAGE FAILED plus the reasons.

BINDING CONSTRAINTS:
- English. No em dashes and no en dashes in your output.
- Read-only except proof.md. No edits to the research outputs or the source.
- Never fabricate a command result; UNVERIFIABLE is an acceptable verdict.
- Time budget about 15 minutes of tool work.
- MANDATORY SELF-CHECK: end proof.md with every acceptance item as PASS or FAIL with evidence.
