# W18 FIX BRIEF, two confirmed findings, the artifact lane

RUN ID: w18-ephemeral-fix-two-20261127
MODEL LANE: ds-flash option, deepseek-v4.1-flash at opencode-go, reasoning max
STAGE CONTRACT: /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/03-build/CONTEXT.md
GIT: Development at 8bbbe74, artifact 6c8c1283, 165,202 bytes. You never run git.

FINDING SOURCE: the W17 lane's findings ledger, confirmed with case evidence in evidence/PROBES-SELF-CHECK.md.

CARD 1, A8 bulk transfer kill, the headline fix:
The burst budget counts every frame equally, and a 64 KiB file chunk is a frame, so over about 40 frames in 5 seconds the A8 guard kills the session. On a fast link any file over roughly 2.6 MB dies as a flood, which breaks the owner's 45 MB video requirement. The design adjudication, already ruled at the lead, apply it: authenticated bulk data inside an accepted file transfer is not unwanted traffic. It is integrity gated by the AEAD frame seal, the digest check, and the receiver preallocation cap. Exempt file data chunks from the A8 window while keeping the full budget on text, control, and unknown frame types. The flood resistance invariant stays: unknown or non bulk floods still trip the kill at the card's named threshold. Then REMOVE the transcode case's 150 ms per chunk throttle workaround so the case proves a full speed 14 MB rung B delivery end to end.

CARD 2, gallery budget leak:
onFileStart refuses at receivedFiles >= MAX_FILES, evict only runs when the count exceeds MAX_FILES which can never happen, and deleteRetained never decrements the count. So the gallery cap is permanent for the session and deletes free nothing. Fix per the UX-07 card's design intent: decrement the count on delete, and when a new file starts at cap, evict the oldest retained media first, then proceed. The eviction path becomes reachable and the case can pin it behaviorally, retarget the gallery case assertion from static to behavioral if the harness needs it.

BINDING RULES:
- Form factor holds: single file, no external assets, ASCII, zero em or en dashes.
- Your writes: the artifact, CORE-SELFCHECK.md, and, if the harness assertion moves, probes/gate.py.
- The 29 case suite must be green at your end, with card 1's throttle workaround removed from the transcode case.
- The artifact hash will change: report the new sha256 and byte count in your self-check, do NOT touch the wrapper pin, the lead pins it after review.
- Budget about 30 minutes, then STATUS: partial and stop.
- MANDATORY SELF-CHECK: both cards PASS or FAIL with commands and raw output, the full 29 case suite table, the new artifact sha256, byte scan clean.
