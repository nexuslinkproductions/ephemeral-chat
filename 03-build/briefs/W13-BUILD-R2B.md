# W13 R2B BRIEF, media and UX cards on the proven spine

RUN ID: w13-ephemeral-build-r2b-20261127
MODEL LANE: ds-flash option, deepseek-v4.1-flash at opencode-go, reasoning max
STAGE CONTRACT: /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/03-build/CONTEXT.md
GIT: fixes committed c50617b on Development, artifact 4cd68b31, you never run git

TASK: apply the R2b cards to 03-build/output/ephemeral-chat-v2.html, one card at a time, in this order:

MEDIA, from the blueprint card table 6.2 and file 12:
- R2-16 Encryption ordering: compress then encrypt, per-message keys, 4 KiB frame padding, true length bound in the AAD.
- R2-17 Metadata strip: canvas re-encode path, EXIF strip through the single acceptFile path, startup WebP probe, the blob.type assertion.
- R2-18 Transcode engine A: WebCodecs decode and encode, planBitrate to fit the 47,185,920 B cap at 90 percent, requestVideoFrameCallback loop, VideoFrame.close, encodeQueueSize cap of 8, the mp4-muxer pin at exactly 31,103 bytes minified, and the finalize() decoderConfig assertion with the rung B fallback.
- R2-19 Projected size before commit: the projection rendered to the sender, Send gated on it, the post flush() size check.
- R2-20 Playback from RAM: media-src blob: in the CSP, in-memory Blob, video.src, the urls array, revoke order on wipe.
- R2-21 Image memory ceiling: the 60 MP pixel gate before destination allocation, bitmap.close() in finally.
- R2-22 One path: acceptFile(file, source) as the only entry, paste, drop and picker all routed through it.

UX, from the blueprint 6.3 and file 13 section 5:
- UX-01 mid on every msg frame, addMessage, log trim.
- UX-02 the react frame, applyReact, the reaction map, pills, caps and the token bucket.
- UX-03 screen state machine S0 to S5 and the two session slots.
- UX-04 verification panel and crypto status chips.
- UX-05 pairing panel states, TTL countdown, single use.
- UX-06 wipe and panic affordances, always enabled, double Escape.
- UX-07 media gallery sheet, RAM-only, eviction.
- UX-08 theme tokens and accessibility baseline.

BINDING RULES:
- Preserve the selectors the green gate cases pin: confirmSas, digits, rotate, migrate, input, offer, reply, wipe. New UI wraps these ids, it never renames them. If a card truly requires moving one, stop and name it in your STATUS instead of moving it.
- The six currently green cases must STAY green at your end: selftest, sas, code, rotate, stun, cover. Run them after every three cards and record raw output. That is your regression guard.
- Form factor holds: single file, no external assets, no build step, ASCII only, zero em or en dashes anywhere.
- The mp4-muxer bytes are the exact 31,103 from the blueprint pin, embedded, not fetched.
- Do not touch gate.py, probes, evidence, monitor, wrapper. Your writes are the HTML artifact and CORE-SELFCHECK.md only.
- The seven red gate cases are KNOWN probe-side defects, do NOT change the artifact to satisfy them. Their retarget wave runs after you land.
- Time budget about 45 minutes. Past it, STATUS: partial and stop.
- MANDATORY SELF-CHECK: every card PASS or FAIL with commands and raw output, plus byte scans and the six-green regression table.
