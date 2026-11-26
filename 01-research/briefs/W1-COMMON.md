# W1 COMMON BRIEF, ephemeral hardening recon wave

RUN ID: w1-ephemeral-hardening-20261126
MODEL LANE: deepseek-v4.1-flash at opencode-go, reasoning max
STAGE CONTRACT: /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/01-research/CONTEXT.md. Your lane is one of seven parallel workers, each owning exactly one output file.
PROJECT ROOT: /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL

INPUTS (read only, never edit):
- App source: /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/input/ephemeral-chat-v1.html, a single-file WebRTC chat, 35598 bytes, V1.
- Product sheet: /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/input/ephemeral-chat-overview.pdf, one page.

VERIFIED FACTS about the app, grepped by the orchestrator, cheap to re-verify:
- One RTCPeerConnection, one SCTP data channel over DTLS, non-trickle ICE, gzip SDP about 650 chars.
- Pairing is manual: an invite code, then a reply code, exchanged out of band, carrying the DTLS fingerprint.
- The only third-party touch is Google public STUN, stun.l.google.com:19302 and stun1.
- Zero persistence APIs: localStorage, IndexedDB, cookies and serviceWorker are all absent. Zero innerHTML.
- 30-minute idle wipe, a Wipe button, peer-loss wipe, files up to 50 MB in 16 KB chunks, receiver-initiated save.

ENGAGEMENT: multi-round security hardening of this product, then adversarial pen testing, then a live two-party test. Target posture: unkeyed inbound traffic never gets an answer, the channel is undetectable to network observers, images and files cross encrypted with zero local trace, key material rotates continuously (the owner calls these transformers that constantly change), a breach triggers a kill switch that wipes the session and migrates both peers to a fresh keyset, and an external monitor overlay watches system health and privacy with alerts.

LOCATE RULE: locate anything with yuri search and docs/index/, never a recursive find across /Users.

TOOLSET: read_file, search_files, terminal, web_search, web_extract.

BINDING CONSTRAINTS:
- English output. No em dashes and no en dashes anywhere in your output file. Use periods and commas.
- Never fabricate links, quotes, numbers or citations. Every external claim carries its source URL, verified before you write it: fetch it and confirm the title matches the claim. Anything you could not verify is marked UNVERIFIED.
- Write for an engineer: mechanism, why, where it applies. No marketing prose.
- FORBIDDEN ACTIONS: no edits to any file under input/, no writes anywhere except your one output file, no git, no installs, no servers or long-running processes.
- Time budget: about 25 minutes of tool work. Past it, write STATUS: partial with what is done, then stop.
- OUTPUT DISCIPLINE: create the output directory if it is missing, then write the file incrementally, one write_file per completed major section, never one giant write at the end.

MANDATORY SELF-CHECK, binding: before reporting done, re-read your output file, re-run your checks, and end the file with a SELF-CHECK section listing every acceptance item as PASS or FAIL with evidence. The work is not done until each item is PASS or reported FAIL with the reason.
