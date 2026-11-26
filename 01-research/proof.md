# W2 review proof: 01-research acceptance

Run: w2-ephemeral-hardening-20261126. Independent fresh-context review. Reviewer family differs from every producer. Tier: Standard (gate review with an independent reviewer). Run window: 2026-11-26 22:53 to 23:00 CET.

Source under test: input/ephemeral-chat-v1.html, 35598 bytes, 1154 lines, sha256 23be3a0b6f53587e50c97c1767fa745980788288145dc79d3dba42095b150337.
Shell for every command: /opt/homebrew/bin/bash 5.3.20. Working directory: 04_PROJECTS/EPHEMERAL/01-research.
Read-only except this file. No input or output file was edited.

## GATES

Controls run first. The shell must pass the real dash bytes to grep, or the dash greps prove nothing.

```
$ printf '%s' $'\u2014' | od -An -tx1
           e2  80  94
$ printf '%s' $'\u2013' | od -An -tx1
           e2  80  93
$ printf 'x\342\200\224y\n' | grep -c $'\u2014'
1
control_em exit=0
$ printf 'x\342\200\223y\n' | grep -c $'\u2013'
1
control_en exit=0
```

Gate 1, file count (expects 7):
```
$ ls output/0*.md | wc -l
       7
name=file_count exit=0
```

Gate 2, SELF-CHECK presence (expects no output):
```
$ grep -L "SELF-CHECK" output/0*.md
(no output)
name=self_check_grep_L exit=0
```
Supplementary, occurrences per file:
```
$ grep -c "SELF-CHECK" output/0*.md
output/01-trust-map.md:1
output/02-audit-findings.md:2
output/03-threat-model.md:2
output/04-crypto-design.md:2
output/05-transport-hardening.md:1
output/06-ops-defense.md:2
output/07-skill-sweep.md:2
```
Supplementary, heading lines (from awk '/^#/' and grep -n "SELF-CHECK"):
```
01-trust-map.md:372:## SELF-CHECK
02-audit-findings.md:214:## SELF-CHECK
03-threat-model.md:495:## 12. Self-check
03-threat-model.md:518 and :532 contain the word SELF-CHECK in a table row and a command. No SELF-CHECK heading.
04-crypto-design.md:417:## SELF-CHECK
05-transport-hardening.md:388:## SELF-CHECK
06-ops-defense.md:426:## SELF-CHECK
07-skill-sweep.md:499:## 8. SELF-CHECK
```
Gate 2 note: grep -L exited 0 with empty output. The criterion is empty output, and it is met.

Gate 3a, em dash (expects no output):
```
$ grep -rl $'\u2014' output/
(no output)
name=em_dash exit=1
```
Gate 3b, en dash (expects no output):
```
$ grep -rl $'\u2013' output/
(no output)
name=en_dash exit=1
```
Exit 1 is grep's no-match code. Empty output is the pass case for both.

Supplementary, HTML entity dashes:
```
$ grep -rlE '&(mdash|ndash);|&#(8211|8212);|&#x201[34];' output/
(no output)
name=entity_dash exit=1
```

Completeness: all seven files exist. Sizes run from 28216 to 64959 bytes and line counts from 237 to 558.

Rerun against the earlier lane flags (01, 03, 06): the rerun agrees the flags are stale on dashes. None of 01, 03 or 06 contains a dash, and no file in output/ does. The rerun agrees on 01 and 06, which each have a "## SELF-CHECK" heading. It differs on 03. Its self-check is titled "## 12. Self-check" (line 495), so the case-sensitive gate matches the word only in body text (lines 518 and 532). See caveat 3.

## CLAIMS

Line numbers refer to input/ephemeral-chat-v1.html.

### Claim 1. No fingerprint or safety-number comparison; the pairing code is the only trust anchor. PASS.

```
grep -n -i -E 'safety|fingerprint|verif|compar|digest|hash|sha|getstats|certif|emoji|sas|confirm|match|trust|anchor|pair' input/ephemeral-chat-v1.html
grep -n -i -E 'finger|identity|authent|signature|sign\(|secret|password|passphrase|\bpin\b|sdp' input/ephemeral-chat-v1.html
```
- Zero hits for fingerprint, safety, verif, compar, digest, hash, SAS, emoji, getstats, certif, trust, anchor, identity, authent, signature, secret or password.
- The only "sha" hit is the CSS box-shadow at line 64.
- The only "confirm" is the Wipe dialog at line 1078.
- SDP handling is limited to pack (722-723, 761, 792), unpack (783, 812) and setRemoteDescription (786, 815). The source never reads the DTLS fingerprint attribute. The out-of-band code exchange is the only identity-binding step. Output 01 line 74 says the same.

### Claim 2. endIncoming exports the full preallocated buffer when bad is false, and card.done enables Save before the incomplete check, so a truncated transfer saves zero-padded bytes. PASS.

```
awk 'NR>=966 && NR<=1056 {printf "%d|%s\n", NR, $0}' input/ephemeral-chat-v1.html
awk 'NR>=820 && NR<=840 {printf "%d|%s\n", NR, $0}' input/ephemeral-chat-v1.html
```
- 1011: `buffer: new Uint8Array(size)`. The buffer is preallocated to the declared size.
- 1045: `const bytes = bad ? buffer.slice(0, offset) : buffer;`. With bad false, the full buffer is exported, unwritten zero bytes included.
- 1050: `card.done(url, preview);` runs before the check at 1051.
- 980-984: done sets `save.hidden = false` for a receiver.
- 1051: `if (offset !== meta.size || bad) card.error('incomplete');`
- 991-994: error changes only the status text and bar color. It does not hide or disable Save.
- 834: the peer's file-end calls endIncoming. A peer that sends file-end before the declared size is filled reaches this path.

### Claim 3. The only crypto API is crypto.randomUUID; text, file bytes and file names cross the channel as plaintext inside DTLS. PASS.

```
grep -n -E 'crypto|subtle|getRandom|randomUUID|encrypt|decrypt|cipher|AES|btoa|atob|TextEncoder|Compression|gzip' input/ephemeral-chat-v1.html
awk 'NR>=842 && NR<=926 {printf "%d|%s\n", NR, $0}' input/ephemeral-chat-v1.html
```
- crypto appears only at 488-489 (crypto.randomUUID). The fallback at 490 uses Date.now and Math.random, which are not crypto APIs. There is no subtle, getRandomValues, cipher or AES anywhere in the file.
- Text: 849, `dc.send(JSON.stringify({ k: 'msg', text: ... }))`.
- File names and sizes: 898-904, JSON that carries `name: file.name.slice(0, 200)`.
- File bytes: 914-915, `file.slice(...).arrayBuffer()` followed by `dc.send(buffer)`.
- Transport: one RTCPeerConnection (634) and one data channel (755).
- Spot-check: RFC 8831 (WebRTC Data Channels) was fetched. Its page text contains DTLS and SCTP. "Inside DTLS" is WebRTC protocol behavior. The app source does not show it.

### Claim 4. Wipe stays disabled until the data channel opens, so a user stuck at pairing cannot kill a live code. PASS for the mechanism. The wording needs a caveat.

```
grep -n -i -E 'wipe|disabled' input/ephemeral-chat-v1.html
awk 'NR>=660 && NR<=682 {printf "%d|%s\n", NR, $0}' input/ephemeral-chat-v1.html
awk 'NR>=541 && NR<=552 {printf "%d|%s\n", NR, $0}' input/ephemeral-chat-v1.html
```
- 354: `id="wipe" ... disabled` in the HTML.
- 676: `el.wipe.disabled = false;` inside the bindChannel `open` listener (664-680). This is the only line that enables Wipe.
- 578-579: endSession disables and hides Wipe. No code makes it visible again.
- 1076-1088: wipe() asks for confirmation (1078), then calls endSession('wipe'). It is bound on click at 1088.
- Wording: the phrase "cannot kill a live code" is not supported. createInvite (750-751) and joinSession (779-780) both call closePeer (541-552). That closes the pending peer connection and invalidates the old invite. Both buttons are enabled at load (369, 388). The pairing panel is hidden once connected (671), so these buttons run only before the channel opens. closePeer does not call endSession, so the session is not ended and Wipe stays blocked. Output 06 line 26 says "cannot kill the session", which the source supports.

### Claim 5. No ICE candidate filtering, no iceTransportPolicy and no relay config, so the packed invite ships the browser default candidates, including the public-IP server-reflexive candidate. PASS for the source chain. Live emission not observed.

```
awk 'NR>=442 && NR<=444 {printf "%d|%s\n", NR, $0}' input/ephemeral-chat-v1.html
grep -n -i -E 'candidate|transportpolicy|relay|turns?:|filter|iceCandidatePool|setConfiguration|onicecandidate' input/ephemeral-chat-v1.html
grep -n -E 'RTCPeerConnection|iceServers' input/ephemeral-chat-v1.html
awk 'NR>=687 && NR<=704 {printf "%d|%s\n", NR, $0}' input/ephemeral-chat-v1.html
```
- 442-444: two Google STUN URLs and no TURN URL.
- 634: `new RTCPeerConnection({ iceServers: ICE })`. No iceTransportPolicy is set.
- The case-insensitive grep returned no hits for candidate, transportPolicy, relay, turn:, filter or onicecandidate. Exit 1, empty output.
- Non-trickle: iceDone waits for "complete" or 4500 ms (687-704). Then pack(pc.localDescription.sdp) runs at 761 and 792. The packed SDP carries every gathered candidate, unfiltered.
- Server-reflexive: with STUN configured, browsers gather server-reflexive candidates. RFC 8445 defines them. The fetched text (first 50,000 characters the tool returned) contains the definition. Live emission was not observed in this review.
- Not verified: 05-transport-hardening.md lines 30-51 present an SDP sample as "A real Chromium run on 2026-11-26". No artifact backs it. The run.json values under .agent-runs contain no Chromium record. The W1 toolset names no browser tool. Terminal could have run one, but nothing shows that it did. The verdict does not depend on this sample (caveat 2).

### Claim 6. unpack decompresses peer-supplied gzip through DecompressionStream with no size cap, near lines 732 to 740. PASS.

```
awk 'NR>=732 && NR<=746 {printf "%d|%s\n", NR, $0}' input/ephemeral-chat-v1.html
grep -n -i -E 'maxlength|max-length|max=|code\.length|length >|limit' input/ephemeral-chat-v1.html
```
- 737: the body is fromBase64 of the pasted text. 740: `pipeThrough(new DecompressionStream('gzip'))`. 741: `await new Response(stream).arrayBuffer()` buffers the whole decompressed output.
- No length check on the code or on the output. The grep hits at 436, 589 and 1023 are a comment, UI text and chunk bounds. None caps the code. No textarea has maxlength.
- Callers: joinSession (783) and acceptAnswer (812) pass pasted text straight to unpack.
- The code comes from the other party, so "peer-supplied" holds.

### External spot-check (three URLs fetched)

- https://www.rfc-editor.org/rfc/rfc8827: title "RFC 8827: WebRTC Security Architecture". The page contains "fingerprint". PASS.
- https://www.rfc-editor.org/rfc/rfc8831: title "RFC 8831: WebRTC Data Channels". The page contains DTLS and SCTP. PASS.
- https://www.rfc-editor.org/rfc/rfc8445: title "RFC 8445: Interactive Connectivity Establishment (ICE)...". The first 50,000 characters the tool returned contain "server reflexive" (1 hit) and "server-reflexive" (20 hits). PASS.
- Not checked: all other URLs. The seven files contain 136 lines with URLs (grep -c per file: 9, 5, 24, 19, 31, 48, 0).

## VERDICT

STAGE ACCEPTED WITH CAVEATS

Caveats:
1. Per-file contract rule not met as written. 01-trust-map.md lines 72 and 74 make app-source claims with no line reference. Files 01, 02, 05, 06 and 07 mostly cite bare line numbers without the file name. Grep counts: 01 has 82 bare refs and names the source file 2 times; 02 has 29 and 1; 05 has 7 and 2; 06 has 30 and 2; 07 has 9 and 1. This is not one of the three acceptance commands the brief names, so it does not fail the gate here. The lead decides whether it blocks.
2. Unlabelled live-run sample. 05-transport-hardening.md lines 30-51 call an SDP sample a real Chromium run and do not mark it UNVERIFIED. Attach the run evidence or mark it UNVERIFIED before the next stage cites it. Claim 5 does not depend on it.
3. Self-check title. 03-threat-model.md uses "## 12. Self-check" (line 495). The case-sensitive gate matches it only through body text (lines 518 and 532). Rename it to "## 12. SELF-CHECK".
4. Claim 4 wording. Do not repeat "cannot kill a live code". Create invite and Create reply both call closePeer, which invalidates a pending invite. Output 06 line 26 is correct as written.
5. Live server-reflexive emission not observed. The source chain is verified. Browser gathering of server-reflexive candidates rests on standard WebRTC behavior (RFC 8445).
6. External sources sampled, not audited. Three URLs were fetched and matched. The rest were not checked.
7. Stale note. 02-audit-findings.md line 235 says the directory held 6 files when that lane finished. It holds 7 now. Correct the note.

## SELF-CHECK

- Gate 1, file count expected 7: PASS. Raw output `7`, name=file_count exit=0.
- Gate 2, grep -L SELF-CHECK prints nothing: PASS. Empty output, name=self_check_grep_L exit=0. All seven files contain the string.
- Gate 3a, em dash grep prints nothing: PASS. Empty output, exit 1 (no match). Control matched a synthetic em dash.
- Gate 3b, en dash grep prints nothing: PASS. Empty output, exit 1 (no match). Control matched a synthetic en dash.
- Rerun agrees with the earlier stale flags: PASS. Agrees on dashes for 01, 03 and 06, and on the 01 and 06 headings. Differs only on the 03 title (caveat 3).
- Claim 1 verdict with commands: PASS.
- Claim 2 verdict with commands: PASS.
- Claim 3 verdict with commands: PASS.
- Claim 4 verdict with commands: PASS for the mechanism. Wording caveat 4.
- Claim 5 verdict with commands: PASS for the source chain. Caveats 2 and 5.
- Claim 6 verdict with commands: PASS.
- GATES section holds name=gate exit= lines with raw output: PASS.
- CLAIMS section holds six verdicts with commands: PASS.
- Exactly one final verdict line: PASS. The verdict phrase occurs once. Verified after writing.
- No em or en dashes in this file: PASS. Verified after writing with the gate 3 method.
- Read-only except proof.md: PASS. The only write was this file. Input and output were read with grep, awk, od, shasum and a python json read.
- Per-file contract rule (file:line, URL, UNVERIFIED marks): FAIL. Caveats 1 and 2. It is a contract criterion and not one of the brief's acceptance commands, so it is carried as a caveat.
- External spot-check: PASS for the three sampled URLs. Coverage is limited (caveat 6).
- Time budget of about 15 minutes: PASS. Tool work ran from 22:53:05 to about 23:00, plus the fetches.
- All seven files exist with content: PASS.
- No fabricated results: PASS. Every quoted output came from a tool call in this session. The 05 sample is reported as unverified, not confirmed.

## Acceptance addendum, lead, 2026-11-26 23:55

The stage contract grew twice after the original seven file verdict: files 08 to 10 for the skill expansion, files 11 to 15 for the platform and vulnerability expansion. Gates re-run by the lead over all 15 files: `ls output/*.md | wc -l` prints 15, the SELF-CHECK grep prints nothing, both dash greps print nothing under the byte escape form.

Lead level spot checks on the five expansion landings: the Electron fuse pair with the launch time SHA-256 pin and its stated Linux gap in file 11, the 290 frame muxer failure with its required assertion and fallback in file 12, the libwebrtc no advisory channel finding and the 2026-11-10 KEV row in file 14, the CVE-2023-44402 fuse limitation and the launch environment attack shapes in file 15. File 13 was verified at its landing earlier the same evening.

Carried caveats: three lanes overran the 25 minute budget and each discloses it in its own SELF-CHECK. File 12 carries one open item with an UNVERIFIED cause, fenced by a required assertion before the build. Files 14 and 15 are design time analysis with no exploit tested against the artifact, which is the R3 round's job. The UNVERIFIED items each file names stay open and travel to the addendum.

Verdict: stage accepted, 15 of 15 files.
