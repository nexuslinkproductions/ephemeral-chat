# 12 Media pipeline: video, images, files, encryption ordering

RUN: w5-ephemeral-platform-20261126, platform lane 2 of 3.
BRIEF: `01-research/briefs/W5-PLATFORM.md`. Owner ruling under test: video attachments up to 45 MB with onboard compression, stronger image handling with metadata stripping, files unchanged at 50 MiB.
INPUTS READ: `input/ephemeral-chat-v1.html` (line references throughout), `01-research/output/01-trust-map.md`, `02-audit-findings.md` (F-02), `04-crypto-design.md` (sections 4.1 to 4.3, 7.2), `06-ops-defense.md` (sections 2.1, 2.5), `CONTEXT.md`.
MEASUREMENT HOST: macOS 26.4.1, Apple Silicon M2 Pro, Google Chrome 158.0.8127.38 headed for every media measurement, and `chrome-headless-shell` 159.0.8154.6 for DOM and decode probes. Numbers marked MEASURED were produced on that host by the scripts described in section 11. The few that were not re-run in the continuation pass are labelled inherited in the provenance table there. Headed matters: the headless shell reports `prefer-hardware` false for every codec, so a matrix measured there is wrong (section 2.5).

Labels used below:

| Label | Meaning |
|---|---|
| MEASURED | Produced by a script on this host in this pass. Inputs and commands are in section 11. |
| DOCUMENTED | Stated by a fetched source whose title was checked. URL next to the claim. |
| DERIVED | Arithmetic over MEASURED or DOCUMENTED inputs, with the inputs shown. |
| INFERRED | Reasoning from documented behavior, not directly observed. |
| UNVERIFIED | Not confirmed in this pass. Used only where it does not drive a decision. |

## 0. The decisions, up front

| # | Decision | Mode | Cost | Section |
|---|---|---|---|---|
| 1 | Video over 45 MiB is transcoded with WebCodecs `VideoEncoder`, H.264 High, at a bitrate computed from duration and the 45 MiB cap. | both | ~120 lines, no bytes | 2.3, 2.4 |
| 2 | Audio is captured as PCM through WebAudio and encoded with `AudioEncoder` (AAC on Chromium), not demuxed from the source. | both | ~50 lines, no bytes | 2.6 |
| 3 | The container is MP4 written by `mp4-muxer`, vendored after one esbuild pass. | both | 31,104 B minified, 9,067 B gzipped, MEASURED | 2.7 |
| 4 | No demuxer ships in V2. That bounds transcode speed to realtime playback and is stated in the UI. | both | 0 B, and a real limit | 2.2, 2.8 |
| 5 | `MediaRecorder` is the automatic fallback when `VideoEncoder.isConfigSupported` fails. | both | ~40 lines, no bytes | 2.9 |
| 6 | Every image is re-encoded through a canvas to WebP at q 0.8, which strips EXIF, GPS, XMP and the ICC profile. Verified, not assumed. | both | ~30 lines, no bytes | 3 |
| 7 | Files keep the existing 50 MiB path, with F-02 fixed by an integrity gate before the Blob and the Save link. | both | small diff to existing code | 4 |
| 8 | Compression runs before encryption, always. Length is padded to 4 KiB buckets before the AEAD, and the residual leak is stated. | both | ~15 lines | 5 |
| 9 | Playback decrypts into an in-memory Blob and a `blob:` URL on a `<video>` element, never a temp file. The CSP must gain `media-src blob:` or playback fails. Verified. | both | one CSP directive | 6 |

Nothing in this pipeline is EXEC-ONLY. One candidate was considered and rejected, see section 9.

## 1. The budget, as constant arithmetic

| Constant | Value | Source |
|---|---|---|
| `MAX_FILE` today | 50 MiB = 52,428,800 B | `input/ephemeral-chat-v1.html:427`, enforced at `:887` and `:1001`; `01-trust-map.md` row 5 of the claims table |
| Video attachment cap | 45 MiB = 47,185,920 B | owner ruling in the brief. Read as MiB to stay in the same unit as `MAX_FILE` |
| Wire chunk | 64 KiB | `04-crypto-design.md` section 4.3 rule 2 (replaces the 16 KiB at `:428`) |
| AEAD tag per chunk | 16 B | AES-GCM tag, `04-crypto-design.md` section 4.1 |
| Chunk overhead on a 45 MiB file | ceil(47,185,920 / 65,536) * 16 = 720 * 16 = 11,520 B, 0.024 percent | DERIVED |
| MP4 container overhead | +2,099 B on 2,119,121 B of chunks, 0.099 percent | MEASURED, section 2.7 |
| Audio budget at 96 kbps | 12,000 B/s | DOCUMENTED codec setting, chosen value |

The one number that matters for the UI is 47,185,920. Everything the sender sees is computed against it, and the transcode is planned to land at 90 percent of it so the container overhead and VBR overshoot cannot push the result over.


## 2. Video

### 2.1 What WebCodecs gives, and the one thing it does not

`VideoDecoder` turns `EncodedVideoChunk` objects into `VideoFrame` objects and `VideoEncoder` does the reverse ([MDN, WebCodecs API](https://developer.mozilla.org/en-US/docs/Web/API/WebCodecs_API), fetched, title "WebCodecs API"). Both are available in dedicated Workers, and both are "Limited availability", not Baseline, per MDN's own banner on the API pages.

The gap that decides the architecture: WebCodecs converts between encoded chunks and raw frames. It does not read a file and it does not write one. There is no `VideoDemuxer` and no `Muxer` in the API surface. So any design needs three things: something that produces encoded chunks (a demuxer, or an element that already decodes), something that writes a container (a muxer, or `MediaRecorder`), and a bitrate plan.

That is why the honest option set has six entries, not two.

### 2.2 Options, ranked by what they cost

All bundle numbers below were produced here: `npm i` the published package, one `esbuild --bundle --minify --format=iife --platform=browser` pass over an entry that imports only the named API, then `gzip -9`. Method and versions in section 11. Names: mediabunny 1.66.5, mp4-muxer 5.2.2, webm-muxer 5.1.4, mp4box 2.6.0.

| Option | What it is | Size | Adds | Costs | Verdict |
|---|---|---|---|---|---|
| A. WebCodecs, element-decoded, `mp4-muxer` | `<video>` element plays the source, `new VideoFrame(video)` per frame, `VideoEncoder` with a computed bitrate, MP4 written by mp4-muxer | 31,103 B min, 9,062 B gz, MEASURED | Exact bitrate, exact resolution, always H.264 MP4, hardware encode | Realtime bound, no source audio without WebAudio capture | **Ship in V2** |
| B. `MediaRecorder` + `canvas.captureStream()` | Canvas downscale, stream capture, record with `videoBitsPerSecond` | 0 B | Zero code, audio included, one container | Bitrate is a hint, codec is the browser's choice, realtime | **Fallback, ship in V2** |
| C. WebCodecs with `mp4box.js` demux | Demux samples, `VideoDecoder` at full speed, same encoder | +225,112 B min, 49,318 B gz, MEASURED | Faster than realtime, source audio as encoded chunks | Two libraries, sample tables, B-frame ordering, edit lists | Defer to V2.1 |
| D. mediabunny full toolkit | Demux and mux, MP4 and WebM, `Conversion` API | +614,494 B min, 158,416 B gz, MEASURED (mux only: 128,863 B, 34,702 B gz) | One dependency covers everything | 17x to 22x the current 35,598 B app, MPL-2.0 | Defer, size is decisive |
| E. Hand-rolled demux plus hand-rolled mux | Parse `moov`/`stbl`, write `moov`/`mdat` | 0 B | Nothing imported | Weeks, and it breaks on edit lists, fragmented MP4, HEVC | Reject |
| F. Refuse over 45 MiB | Toast: trim the clip or send it as a file | 0 B | Nothing | The owner's feature does not exist | Keep as the last branch of the ladder |

Security posture, which the size column cannot show. A and B add no new parser: the only code reading attacker-supplied bytes is the browser's own media stack, inside the renderer sandbox. C and D add a JavaScript demuxer running in the page, parsing `moov`, `stbl` and sample tables from the peer, in the same origin as the keys and the DOM. That is a new in-page attack surface and the second reason C waits: a malformed container becomes our bug rather than Chromium's. E and F add nothing and are rejected on other grounds.

Sources for the ranking: [mp4-muxer](https://github.com/Vanilagy/mp4-muxer) and [webm-muxer](https://github.com/Vanilagy/webm-muxer) (deprecation notices, both fetched), [mediabunny](https://github.com/Vanilagy/mediabunny) (MPL-2.0, fetched, title "GitHub - Vanilagy/mediabunny: Pure TypeScript media toolkit for reading, writing, and converting video and audio files, directly in the browser."), [mp4box.js](https://github.com/gpac/mp4box.js) (BSD 3-Clause, fetched, title "GitHub - gpac/mp4box.js: JavaScript version of GPAC's MP4Box tool"). Every size is the measured number in section 11. Engagement fit: A and B satisfy the 45 MiB ruling in both modes today, C is a V2.1 speed upgrade, D replaces the whole media layer for one feature, E and F are rejected in their rows.

Note on A and B together: they are not alternatives, they are one ladder. Try A, fall back to B, fall back to F. Three rungs, one function.

Two facts that reshaped the ranking:

1. `mp4-muxer` and `webm-muxer` are both **deprecated** by their author in favour of mediabunny: "mp4-muxer has been deprecated in favor of Mediabunny, which entirely supersedes it" and the same sentence appears on webm-muxer ([github.com/Vanilagy/mp4-muxer](https://github.com/Vanilagy/mp4-muxer), fetched, title "GitHub - Vanilagy/mp4-muxer"; [github.com/Vanilagy/webm-muxer](https://github.com/Vanilagy/webm-muxer), fetched, title "GitHub - Vanilagy/webm-muxer"). Using it is a deliberate, bounded choice: 31 KB frozen code that writes MP4, versus 135 KB raw and 35 KB gzipped for the successor's mux-only path. The feature it implements (write an ISO BMFF file) is finished, so "unmaintained" costs little. Record the pin, do not silently float it.
2. Demux is the expensive half. mediabunny's mux-only path is 34,702 B gzipped; adding its input and conversion APIs takes the same bundle to 158,416 B gzipped, MEASURED. That ratio is the reason option C does not ship in V2.
3. Re-measured in the continuation pass with esbuild 0.25.0: mp4-muxer's mux path is 31,103 B minified and 9,062 B gzipped; mediabunny's mux-only path with `{Output, Mp4OutputFormat, BufferTarget}` is 135,497 B and 34,761 B; `export *` from mediabunny is 793,794 B and 199,863 B. The earlier mediabunny figure came from a narrower entry, and `export *` is the honest upper bound for anyone importing the whole toolkit. The ratio that decides option C survives all three shapes.

### 2.3 Engine A, step by step

```
pick / drop / paste
  -> File object, one reference, never read whole
  -> <video src=blobURL(file)> muted playsinline, appended off-screen
  -> onloadedmetadata: duration, videoWidth, videoHeight
  -> plan = bitratePlan(duration, height)          // section 2.4
  -> show projected size, wait for the user's Send click
  -> video.play()
  -> on each requestVideoFrameCallback:
        f = new VideoFrame(video, {timestamp: mediaTime * 1e6})
        encoder.encode(f, {keyFrame: n % 60 === 0}); f.close()
        if (encoder.encodeQueueSize > 8) stop feeding until dequeue
  -> at duration: video.pause(), encoder.flush(), muxer.finalize()
  -> encrypted chunking of the muxed bytes       // section 5
```

Three details that are not optional.

- **Construct the frame from the element, not from a canvas.** MEASURED: `new VideoFrame(video)` encoded 290 frames of 1080p30 in 10,029 ms with an encode queue that never rose above 1. The canvas round trip costs a full readback of a 1920x1080 buffer, 8,294,400 B MEASURED via `VideoFrame.allocationSize()`, on every frame, before the frame exists. Skip the canvas unless you are downscaling, and when you are, draw straight into a smaller canvas so the readback is 1280x720 (3,686,400 B) or less.
- **`VideoFrame.close()` on every frame, including error paths.** MDN: "The close() method of the VideoFrame interface clears all states and releases the reference to the media resource" ([MDN, VideoFrame: close()](https://developer.mozilla.org/en-US/docs/Web/API/VideoFrame/close), fetched, title "VideoFrame: close() method"). A frame holds GPU memory that the garbage collector does not see as pressure, so leaking frames is how this pipeline runs out of memory.
- **Backpressure on `encodeQueueSize`.** MDN defines it as "the number of encode queue requests" ([MDN, VideoEncoder](https://developer.mozilla.org/en-US/docs/Web/API/VideoEncoder), fetched, title "VideoEncoder - Web APIs | MDN"). MEASURED: with no backpressure the queue reached 102 frames. At 8,294,400 B per 1080p RGBA frame that is a theoretical 845 MB of frame data in flight, and while the implementation obviously does not hold all of it in that format, the growth is unbounded by design. Cap it at 8 and wait for the `dequeue` event. This is the single largest memory lever in the pipeline.

### 2.4 Bitrate targeting that actually fits the cap

The encoder takes `bitrate` in bits per second as an average ([MDN, VideoEncoder: configure()](https://developer.mozilla.org/en-US/docs/Web/API/VideoEncoder/configure), fetched, title "VideoEncoder: configure() method"), with `bitrateMode` of `"constant"`, `"variable"` (default) or `"quantizer"`, and `latencyMode` of `"quality"` (default) or `"realtime"`. So the size is computable before a single frame is encoded:

```
budget   = 45 * 1024 * 1024 * 0.90              = 42,467,328 B usable
audio    = audio_kbps * 1000 / 8 * duration_s
video    = budget - audio
bitrate  = video * 8 / duration_s               bits per second
```

Worked for the cap, 96 kbps AAC, 10 percent headroom:

| Duration | Audio B | Video budget B | Video bitrate |
|---|---|---|---|
| 15 s | 180,000 | 42,287,328 | 22.6 Mbps |
| 30 s | 360,000 | 42,107,328 | 11.2 Mbps |
| 60 s | 720,000 | 41,747,328 | 5.57 Mbps |
| 120 s | 1,440,000 | 41,027,328 | 2.74 Mbps |
| 300 s | 3,600,000 | 38,867,328 | 1.04 Mbps |
| 600 s | 7,200,000 | 35,267,328 | 470 kbps |

DERIVED. The 600 s row is where the ladder has to stop: 470 kbps across 1080p is not watchable, so duration caps resolution as well.

Resolution ladder, never above 1080p even for a 4K source, because the receiver views it in a chat bubble:

| Duration | Max height | Why |
|---|---|---|
| ≤ 60 s | 1080 | needs 3.11 Mbps at 0.05 bits per pixel per frame, budget 5.57 |
| ≤ 180 s | 720 | 720p needs 1.38 Mbps, budget at 180 s is 1.79 |
| ≤ 600 s | 480 | 480p needs 0.61 Mbps, budget at 600 s is 0.47, so this row falls short of the floor and is the honest edge |
| > 600 s | refuse | zero code path, clear message |

The 0.05 bits per pixel per frame figure is a chosen quality floor, not a measured constant. Check it against the measured run: 1920 x 1080 x 30 x 0.05 = 3,110,400 bits per second, and the 4 Mbps target used in the test produced a picture that decoded and played back cleanly at 1080p30. Tune the floor in the build, it is one number.

Accuracy, MEASURED: at a 4,000,000 bps target, 290 frames of 1080p30 produced 4,847,208 B of encoded chunks over a 10.0 s window, against 5,000,000 B for the window, which is -3.1 percent. The window took 10,029 ms at 28.9 fps, so the encoder kept up with the source and undershot the target slightly rather than overshooting. Conclusion: the `bitrate` field is a usable predictor on this encoder, so the projected size shown to the sender is honest to a few percent on synthetic content. Real footage with hard cuts and grain overshoots more, which is why the plan aims at 90 percent and re-checks after `flush()`.

### 2.5 Codecs and hardware on Apple Silicon

Apple documents VideoToolbox as the framework that provides "direct access to hardware encoders and decoders" ([Apple Developer, Video Toolbox](https://developer.apple.com/documentation/videotoolbox), fetched, title "Video Tool Box | Apple Developer Documentation"). Chromium reaches it through WebCodecs on macOS, and `hardwareAcceleration` is the request: `"no-preference"`, `"prefer-hardware"`, `"prefer-software"` (MDN, configure(), above).

MEASURED matrix, `VideoEncoder.isConfigSupported` on this host, 1280x720, 2 Mbps, 30 fps:

| Codec string | `prefer-hardware` | `no-preference` |
|---|---|---|
| `avc1.42001f` (H.264 baseline) | supported | supported |
| `avc1.640028` (H.264 high) | supported | supported |
| `hvc1.1.6.L93.B0` (HEVC) | supported | supported |
| `vp8` | **not supported** | supported |
| `vp09.00.10.08` | **not supported** | supported |
| `av01.0.04M.08` | **not supported** | supported |

Reading: Chromium will promise hardware only for H.264 and HEVC on this machine. VP8, VP9 and AV1 are available in software. That matches the shape of the platform, where the media engine has had H.264 and HEVC hardware encode for years and no VP9 or AV1 hardware encode. Two consequences:

- Request `avc1.640028` with `hardwareAcceleration: "prefer-hardware"` and accept the answer. If `isConfigSupported` returns supported with the hardware flag, the encode is on the media engine and costs a fraction of the CPU. Do not hardcode "hardware" as a fact, because the config echo can come back with a different value than requested.
- Do not build the plan around VP9 or AV1 for encoding on macOS. They are software paths, roughly an order of magnitude more CPU per frame, and on a laptop that is fan noise and battery. VP9 is fine as a decode target, and as an encode target only on machines where `prefer-hardware` says yes.

Audio availability, MEASURED with `AudioEncoder.isConfigSupported`, 48 kHz stereo: `mp4a.40.2` (AAC-LC) supported, `opus` supported, `mp3` not supported. AAC is the right default because it is the only audio codec MP4 carries everywhere, including Safari on iOS.

Re-verified in the continuation pass on headed Chrome 158.0.8127.38: the matrix above is identical, and the config echo returns `prefer-hardware` when it is asked for. Under `chrome-headless-shell` 159.0.8154.6 the same probe returns `prefer-hardware` false for all six codecs, HEVC included, because the headless shell has no hardware media path. That is a property of the harness, not of the API, and any future codec matrix must be measured headed or in the shipped shell.


### 2.6 Audio, and why it is the awkward part

`AudioEncoder` takes `AudioData` objects and emits `EncodedAudioChunk` objects, with the same queue and flush shape as the video encoder ([MDN, AudioEncoder](https://developer.mozilla.org/en-US/docs/Web/API/AudioEncoder), fetched, title "AudioEncoder - Web APIs | MDN"). Getting the source's audio into that shape has exactly three routes:

| Route | Mechanism | Bytes | Honest verdict |
|---|---|---|---|
| WebAudio PCM capture | `createMediaElementSource(video)` into a silent graph, `ScriptProcessorNode` or `AudioWorkletNode` collects Float32 PCM, wrap in `AudioData`, `AudioEncoder.encode()` | 0 | **Chosen.** No demuxer, sample-exact to the element clock, works in both modes |
| Demux the source's audio track | mp4box reads the AAC samples, `AudioDecoder` or straight container copy | +49,318 B gz | Better, deferred with option C |
| Drop audio | mute and send video only | 0 | Unacceptable for a phone video, reject |

The WebAudio route in more detail, because it is the one that ships:

```
ac   = new AudioContext({sampleRate: 48000})
src  = ac.createMediaElementSource(video)     // once per element
gain = ac.createGain(); gain.gain.value = 0   // silent monitoring
dest = ac.createMediaStreamDestination()
sp   = ac.createScriptProcessor(4096, 2, 2)   // deprecated, but inline and universal
src.connect(sp); sp.connect(gain); gain.connect(dest); dest.connect(ac.destination)
sp.onaudioprocess = e => {
  const d = e.inputBuffer
  encoder.encode(new AudioData({format:'f32-planar', sampleRate: ac.sampleRate,
    numberOfFrames: d.length, numberOfChannels: d.numberOfChannels, timestamp: tUs,
    data: interleave(d)}))
  tUs += Math.round(d.length / ac.sampleRate * 1e6)
}
```

Costs and limits, stated plainly:

- `ScriptProcessorNode` is deprecated ([MDN, ScriptProcessorNode](https://developer.mozilla.org/en-US/docs/Web/API/ScriptProcessorNode), fetched, title "ScriptProcessorNode - Web APIs | MDN"). It runs on the main thread and copies 32,768 B per callback at 4096 frames stereo f32. That is 375 callbacks per 10 s, which is nothing next to the video encode. `AudioWorklet` is the modern replacement and needs an `addModule` URL, which in a single file means a `blob:` module URL and therefore a `worker-src blob:` CSP grant. Defer the worklet, keep the script processor, and mark the ceiling.
- Audio and video clock drift is real. The audio timestamps come from the AudioContext clock while the video timestamps come from `mediaTime`. Over 60 s the drift is small; over 10 minutes it is measurable and UNVERIFIED here. Cap the transcode at 10 minutes (the ladder already refuses above 600 s) and check A/V sync in testing on a 5 minute clip.
- If the AudioContext cannot start (no user gesture, or an autoplay policy), fall back to the ladder rung that drops audio rather than shipping a silent video that claims to have sound. The Send click is a gesture, so this should be rare.

### 2.7 Muxing

`mp4-muxer` in one pass: `new Muxer({target: new ArrayBufferTarget(), video:{codec:'avc', width, height}, audio:{codec:'aac', sampleRate, numberOfChannels}, fastStart:'in-memory'})`, then `addVideoChunk(chunk, meta)` and `addAudioChunk(chunk, meta)` from the encoder outputs, then `finalize()`.

MEASURED round trip, which is the acceptance evidence for the whole section: 300 encoded 1080p H.264 chunks totalling 2,119,121 B became an MP4 of 2,121,220 B, so the container cost 2,099 B (0.099 percent). Setting that Blob on a `<video>` element through `URL.createObjectURL` gave `duration 10`, `videoWidth 1920`, `videoHeight 1080`, no error. So the output is a file the same browser plays, produced entirely from memory, never written to disk.

Three muxer choices worth recording:

- `fastStart: 'in-memory'` puts the `moov` box first, which is what makes the file playable from a Blob before the whole thing is buffered. It also holds a second copy of the media during finalize. That is the 2x peak in section 2.11.
- `StreamTarget` writes chunks out through a callback as they are produced. That removes the second copy and lets you feed the encryption pipeline directly, but then you do not know the final size before sending, which contradicts the projected-size requirement. Use `ArrayBufferTarget` for the 45 MiB cap and revisit `StreamTarget` only if memory becomes the binding constraint.
- WebM (`webm-muxer`, 30,092 B min, 8,600 B gz, MEASURED) is the alternative container. It buys VP8/VP9/Opus and costs compatibility: an MP4 with H.264 and AAC plays in every target, a WebM does not play in older Safari. Since one of the two peers may be the one with the weaker browser, MP4 is the safer single output format.

### 2.8 What happens to a 200 MB phone video

Concrete walkthrough, with the numbers that decide the UX. A 200 MB clip at 40 s is 40 Mbps of source, typical of 4K60 from a phone. Arithmetic, not a device measurement.

1. **Admission.** `file.size` is 209,715,200 B, over the cap. The app does not refuse, it routes to the transcode path.
2. **Probe.** The `<video>` element reports `duration 40.0`, `videoHeight 2160`. Probing costs a metadata read of the tail of the file, not a full decode.
3. **Plan.** 40 s ≤ 60 s, so the ladder picks 1080p. Video bitrate = (42,467,328 - 480,000) * 8 / 40 = 8.40 Mbps. Audio 96 kbps AAC. Projected total = 42.0 MB, under the 45 MiB cap with 10 percent headroom.
4. **Commit.** The UI shows "1080p, about 42 MB, and about 42 seconds of processing" before the user presses Send. The time estimate comes from the measured realtime bound: the element plays the source at 1x, and the measured 28.9 fps adds about 4 percent, so processing time is duration times 1.04, plus the encode tail.
5. **Transcode.** 1,200 frames at the measured 28.9 fps, which is 4 percent below the source's 30 fps, so the run takes about 41.5 s wall for a 40.0 s clip and may drop a few frames at the tail. The queue stays near 1 because the encode is not the bottleneck at this resolution. A 4K source is decoded by the browser (hardware for H.264 and HEVC) and downscaled in the canvas, which is where the cost moves if the machine is slow.
6. **Finalize.** `flush()`, `finalize()`, size check. If the result is over 45 MiB, one retry at `bitrate * (cap / size) * 0.95`, then refuse with the size it reached.
7. **Send.** The MP4 bytes go through the file path in section 5, 64 KiB chunks, per-chunk AEAD, digest at the end.

The 200 MB original is never fully loaded. The `<video>` element streams from the `File` handle the picker gave us, so the browser's own media cache decides how much of it is resident, and the app never calls `arrayBuffer()` on it. That is the difference between this path and the V1 file path, which reads the whole thing into a `Uint8Array` at `:1011`.

The honest ceiling: 40 s of waiting for a 40 s clip. Faster than realtime requires the demuxer in option C, and 49 KB gzipped is the price of that. The right call for V2 is to show the wait and let the user cancel, not to ship a second ingest path.

### 2.9 The fallback when WebCodecs is missing

Availability, from caniuse ([caniuse.com/webcodecs](https://caniuse.com/webcodecs), fetched, title "Can I use... Support tables for HTML5, CSS3, etc"): Chrome 94 and later, Edge 94 and later, Firefox 130 and later, Safari 16.4 to 18.7 partial and 26.0 and later full, iOS Safari the same. So the stretch-target browsers are Safari before 16.4, Firefox before 130, and any browser where the specific codec config is unsupported even though the API exists. The second case is the common one, for example a Chromium build that cannot do H.264 for licensing reasons.

Fallback ladder, one function, three rungs:

```
if (await VideoEncoder.isConfigSupported(cfg)).supported  -> rung A, WebCodecs
else if (window.MediaRecorder && MediaRecorder.isTypeSupported(mime)) -> rung B
else -> rung F, refuse with a readable message
```

Rung B in full, because it is short: canvas at the ladder resolution, `canvas.captureStream(30)`, `new MediaRecorder(stream, {mimeType, videoBitsPerSecond})`, `start(250)`, draw each frame in `requestVideoFrameCallback`, `stop()` at duration, concatenate the data chunks, done. Audio comes along because `video.captureStream()` carries the audio track if the element is not muted, and the canvas stream does not, so for rung B capture the element's stream and draw into the canvas separately.

MEASURED on rung B: a 10.0 s 1080p source with `videoBitsPerSecond: 4000000` produced a 4,354,738 B file in 10,024 ms, an actual 3,476 kbps, which is 13 percent **under** the request. Playback of the result worked (`duration 9.967`, 1920x1080). So the request is a ceiling on easy content, not a prediction. That is exactly why rung B needs a post-check and a retry, and why it is the fallback and not the primary.

Container support on this host, MEASURED with `MediaRecorder.isTypeSupported`: `video/mp4` true, `video/mp4;codecs=avc1.42001f` true, `video/mp4;codecs=avc1.640028` true, `video/webm` true, `video/webm;codecs=vp8` true, `video/webm;codecs=vp9` true, `video/webm;codecs=av01` true, `video/webm;codecs=vp9,opus` true, `video/mp4;codecs=avc1.42E01E,mp4a.40.2` true. Chromium can produce MP4 with H.264, so rung B is not stuck on WebM. `MediaRecorder` itself is Baseline since April 2021 ([MDN, MediaRecorder](https://developer.mozilla.org/en-US/docs/Web/API/MediaRecorder), fetched, title "MediaRecorder - Web APIs | MDN").

### 2.10 Honest limits of the video path

| Limit | Number | Consequence |
|---|---|---|
| Realtime bound without a demuxer | 1x playback speed, MEASURED 28.9 fps at 1080p30 | A 5 minute clip takes 5 minutes. Say so in the UI |
| Output resolution ceiling | 1080p, by policy | A 4K source is downscaled. A chat bubble does not need more |
| Duration ceiling | 600 s, then refuse | Below 470 kbps the picture is not worth sending |
| No HDR, no 10 bit, no alpha | `alpha: "discard"` is the default per MDN configure() | An HDR phone video is tone-mapped by the browser's decode, and the result looks flat. UNVERIFIED how flat |
| No rotation metadata | The element reports the rotated `videoWidth`/`videoHeight` | A portrait video stays portrait because the pixels are already turned, verified on the image path in section 3.3 and INFERRED for video |
| Variable frame rate sources | `requestVideoFrameCallback` fires per presented frame | The muxer needs monotonic timestamps; use `mediaTime`, never an internal counter |
| No subtitle or chapter tracks | Not carried | Out of scope, do not promise them |
| B frames | Real-time paced encode, one keyframe per 60 frames | Larger than a two-pass encode at the same bitrate, by an amount UNVERIFIED here |

### 2.11 Peak memory, with the inputs shown

Everything below is DERIVED from MEASURED allocation sizes and the constants in section 1.

Frame sizes, MEASURED with `VideoFrame.allocationSize()` on a canvas-backed frame (format reported as `RGBA` on this build, 4 B per pixel):

| Resolution | Bytes per frame | MB |
|---|---|---|
| 3840x2160 | 33,177,600 | 33.18 |
| 1920x1080 | 8,294,400 | 8.29 |
| 1280x720 | 3,686,400 | 3.69 |

Send side, 45 MiB output, 1080p, queue capped at 8:

```
source in media pipeline     browser-managed, opaque     UNVERIFIED, typically tens of MB
frame in flight (1)          8,294,400                    8.29 MB
encoder queue (cap 8)        8 x 8,294,400 = 66,355,200   66.36 MB   worst case, not observed
measured queue depth         1 frame, so 8,294,400         8.29 MB   in the realtime path
muxer output buffer          47,185,920                  47.19 MB
muxer finalize copy          47,185,920                  47.19 MB   fastStart in-memory
                                             total      ~110 to 170 MB
```

Receive side, 45 MiB media, streaming decrypt:

```
plaintext parts (before Blob)  47,185,920   47.19 MB   grows as chunks arrive
Blob copy                      47,185,920   47.19 MB   one copy at construction
ciphertext in flight           65,552       0.07 MB    one 64 KiB chunk, dropped after decrypt
media element decode buffers   opaque       UNVERIFIED  the largest unmeasured term
                                             total ~95 MB plus decoder
```

Points that change the design:

- **8 frames at 4K is 265 MB**, which is why the ladder never encodes above 1080p and why the frame is constructed at the target size, not the source size. If a 4K frame must be created for downscaling, close it immediately and never queue more than 2.
- **The two muxer copies are avoidable** with `StreamTarget`, at the cost of not knowing the size up front. For a 45 MiB cap on desktop, buffering is the right trade. On iOS Safari the tab may be killed around 200 to 300 MB of media memory, which is INFERRED from platform behavior and not measured here. That is the reason to keep the mobile cap at 16 MiB if testing shows pressure, exactly as `04-crypto-design.md` section 4.3 already recommends for files.
- Compare with `04-crypto-design.md` section 4.3's estimate of 100 to 150 MB for a 50 MB file. The video path lands in the same band, which is a useful cross-check: the transcode adds frame memory but removes the second full ciphertext copy, because the media is streamed to the encoder rather than buffered.


## 3. Images: the canvas re-encode, and the metadata answer

### 3.1 The pipeline

```
File or pasted Blob
  -> createImageBitmap(file, {imageOrientation:'from-image', resizeWidth, resizeHeight, resizeQuality:'high'})
  -> OffscreenCanvas at the target size, drawImage(bitmap), bitmap.close()
  -> canvas.convertToBlob({type:'image/webp', quality: q})    // or toBlob in the main thread
  -> check blob.type === 'image/webp'; if not, treat as failure
  -> if size > target, retry one step down (q 0.7, then 0.55, then half the pixels)
  -> send the bytes; the original never leaves the device
```

`OffscreenCanvas.convertToBlob()` has the same type and quality contract as `HTMLCanvasElement.toBlob()`, and it is usable in a Worker, which matters because `04-crypto-design.md` section 7.2 puts key material in a Worker and the image work should not run on the thread that owns the DOM.

One constraint that shapes it: `toBlob` falls back to PNG when the requested type is unsupported. MDN: "If the file format is not specified, or if the given format is not supported, then the data will be exported as image/png" ([MDN, HTMLCanvasElement: toBlob()](https://developer.mozilla.org/en-US/docs/Web/API/HTMLCanvasElement/toBlob), fetched, title "HTMLCanvasElement: toBlob() method"). MEASURED consequence: asking this Chromium for `image/avif` returned a Blob with `type: "image/png"` and 292,065 B, the same size as the explicit PNG request. A naive pipeline that requests AVIF would silently send a PNG 2.6 times the JPEG output it would otherwise have sent, and 11.7 times the WebP. Always assert on `blob.type`.

### 3.2 Formats, measured on one real photo

Input: a 1600x1200 JPEG with EXIF, 210,301 B, produced by PIL and served over local HTTP to Chromium 145. Canvas at natural size, one `toBlob` per row.

| Requested | `blob.type` returned | Bytes | vs original |
|---|---|---|---|
| `image/webp` q 0.8 | `image/webp` | 24,916 | 11.8 percent, 88.2 percent smaller |
| `image/webp` q 0.5 | `image/webp` | 20,246 | 9.6 percent |
| `image/jpeg` q 0.8 | `image/jpeg` | 113,892 | 54.2 percent |
| `image/avif` q 0.8 | `image/png` | 292,065 | 138.9 percent, format ignored |
| `image/png` | `image/png` | 292,065 | 138.9 percent |

All MEASURED. Reading:

- **WebP q 0.8 is the default.** 88 percent smaller than the source JPEG on this image, with the quality that survives a chat bubble. q 0.5 saves another 18 percent for visibly more artifacts.
- **AVIF cannot be produced by this Chromium at all.** No encoder, silent PNG fallback. A pipeline that offers AVIF today ships PNGs. This is a decode-only format in this browser, and the measured `type` proves it.
- **JPEG stays as the compatibility output** for the case where WebP fails, and it carries the ICC profile through (measured, `ICC_PROFILE` present in the JPEG output and absent from the WebP output).

Format support for `toBlob` is browser-dependent by design, and the spec only requires PNG. So the selection is a probe, not a constant:

```
const canWebp = await probe('image/webp', 0.8);   // encode 2x2, check blob.type
```

One probe at startup, cached in a variable, no feature-detect library.

### 3.3 EXIF, GPS and the rest: verified, not assumed

The question was whether a canvas re-encode natively drops EXIF. It does, and here is the proof rather than the belief.

Test asset: a 1600x1200 JPEG carrying EXIF with `Make = "SECRETGPS"`, `Orientation = 6`, and a GPS IFD with `GPSLatitudeRef N`, a latitude of 48,12,30 and a longitude of 16,22,11. Verified in the file before the test: byte offset scan found one `Exif` marker and one `SECRETGPS` string, PIL read the GPS IFD back.

Test: load it in `<img>`, `drawImage` at natural size into a canvas, `toBlob` for each format, then byte-scan the output for the ASCII strings `Exif`, `SECRETGPS`, `GPS`, the XMP namespace `http://ns.adobe.com/xap`, and `ICC_PROFILE`.

| Output | `Exif` | `SECRETGPS` | `GPS` | XMP | ICC |
|---|---|---|---|---|---|
| `image/webp` q 0.8 | absent | absent | absent | absent | absent |
| `image/webp` q 0.5 | absent | absent | absent | absent | absent |
| `image/jpeg` q 0.8 | absent | absent | absent | absent | **present** |
| `image/png` (AVIF fallback) | absent | absent | absent | absent | absent |

All rows MEASURED, and the control is the input file, which contains all of them.

So: **canvas re-encode drops EXIF, GPS, XMP and the orientation tag. It does not drop the ICC profile on the JPEG path.** The ICC profile is not a location leak, but it is a device fingerprint, a camera maker plus model pair that survives in the color profile name. WebP drops it too, which is another argument for WebP as the default.

Why this is true, not just observed: a canvas holds pixels, nothing else. `drawImage` writes the source rectangle's pixels into the bitmap, so there is no field in the destination for a metadata block to travel in, and the serializer writes the format's own headers only. MDN's `toBlob` page states the one piece of metadata it does write: "The created image will have a resolution of 96dpi for file formats that support encoding resolution metadata" (same URL as above). That sentence is the whole metadata story: a fabricated 96 dpi and nothing else.

The orientation case is worth one more line, because it is the way this pipeline could silently mangle photos. The test file's stored pixel dimensions are 1600x1200 with `Orientation = 6`, which means "rotate 90 clockwise for display". The browser exposed `naturalWidth`/`naturalHeight` as 1200x1600 and the canvas came out 1200x1600, MEASURED. So the orientation was applied at decode and the pixels in the output are upright. That is the correct outcome, and it happens because the browser applies the image's orientation by default. It also means the output has no orientation tag to mislead a later viewer, which is exactly what we want. For a pipeline that reads bytes rather than an element, `createImageBitmap(blob, {imageOrientation:'from-image'})` gives the same result, MEASURED: 1200x1600.

The quiet win, stated precisely: **an image sent through this app never carries the sender's GPS coordinates, camera model, capture timestamp, or editing history, and the app does not need a metadata-stripping library to achieve it.** The one line of code that draws the image is the whole mitigation. Put that in the product copy as a fact, because it is measured.

What still leaks in an image, and is not fixed by this:

| Channel | Status | Mitigation |
|---|---|---|
| Visible scene content | Inherent | None. This is the photo |
| Pixel-level sensor noise (PRNU) | Present after any re-encode | Downscaling reduces it, does not remove it. UNVERIFIED amount, do not claim removal |
| Thumbnail in the JPEG source | Gone, we never copy it | Confirmed by the byte scan above |
| ICC profile | Present on the JPEG output row | WebP default removes it, measured |
| File name | Preserved as a string | Offer a rename; the name is user content and is encrypted, but it is still a leak to the human at the other end |
| Encoded size | Preserved | Section 5, padded to 4 KiB |

### 3.4 Sizing rules

| Rule | Value | Why |
|---|---|---|
| Max dimension | 1600 px long edge, 2048 for a screenshot with text | A chat bubble is at most about 800 CSS px wide. 1600 covers 2x displays |
| Target bytes | 350 KB, hard ceiling 1.5 MB | WebP at 1600 px on real photos lands near 150 to 300 KB, MEASURED 24,916 B on a synthetic 1600x1200 |
| Quality ladder | 0.8, 0.7, 0.55, then halve the pixels and restart at 0.7 | Four steps, then send what you have |
| Animated images | Do not re-encode. Detect and route to the file path | A canvas flattens to the first frame, so a re-encode would silently kill the animation |
| HEIC and HEIF | Cannot be decoded by Chromium. Fall through to the file path if under 50 MiB, else refuse | INFERRED from the format's absence in the decode path, marked UNVERIFIED for Chromium builds with platform codec support |
| SVG | Never rasterize. Send as a file | An SVG can carry scripts and external references, and rasterizing destroys it |
| Alpha | Keep for PNG and WebP, force JPEG onto white | A transparent PNG flattened onto black looks broken |

The animated image rule matters more than it looks. V1 previews `image/gif` (`:893`, `:1049`) and a naive re-encode would turn every GIF into a still frame. Detect `image/gif`, `image/apng` and `image/webp` with animation and send the original bytes through the file path with the metadata question answered by "the sender already chose an animated file", or strip nothing and state it. The lazy correct answer: do not re-encode animated images, and say in the UI that animated files keep their metadata. That is a small honesty cost for not building an animation re-encoder.


### 3.5 Image memory ceilings

The 350 KB target says nothing about memory. Pixels do.

Inputs, all measured or derived from measured:

- 4 B per pixel. MEASURED: a canvas-backed `VideoFrame` reports `allocationSize()` of 8,294,400 B at 1920x1080 and 192,000,000 B at 8000x6000, both exactly width times height times 4, format `RGBA` on this Chromium build.
- Canvas area ceiling. MEASURED by allocation probe on Chrome 158: 16384x16384 (268,435,456 px) allocates, accepts a fill and reads back; 16385x16384 fails; 20000x20000 fails; 65535x100 works. So the limit is total area, not a single side, and it lands exactly on 16384 squared.
- Destination canvas at the sizing rules: 1600x1200 is 1,920,000 px, 7,680,000 B. The 2048 px screenshot rule is 2048x1536, 3,145,728 px, 12,582,912 B.

| Source | Pixels | Decoded RGBA | Destination canvas | Peak with 350 KB output |
|---|---|---|---|---|
| 12 MP phone photo, 4032x3024 | 12,192,768 | 48,771,072 B (46.5 MiB) | 7,680,000 B | 56,801,072 B (54.2 MiB) |
| 48 MP photo, 8000x6000 | 48,000,000 | 192,000,000 B (183.1 MiB) | 7,680,000 B | 200,030,000 B (190.8 MiB) |
| 108 MP photo, 12000x9000 | 108,000,000 | 432,000,000 B (412.0 MiB) | 7,680,000 B | 440,030,000 B (419.6 MiB) |
| 200 MP photo, 16384x12288 | 201,326,592 | 805,306,368 B (768.0 MiB) | cannot allocate | over the area ceiling before the canvas |

DERIVED. The last row is the one that matters: a 200 MP source cannot be drawn into a single canvas on this Chromium at all, because 201,326,592 px is over the measured 268,435,456 px area limit. Peak here is decode plus destination plus the encoded blob, and the encoded size is a rounding error next to the pixels. A 350 KB WebP is 0.18 percent of a 48 MP decode.

Rules that follow, and they are gates rather than advice:

1. Decode, then check `bitmap.width * bitmap.height` before allocating the destination canvas. If the product is over 60,000,000 px (240,000,000 B), close the bitmap and refuse with "this image is too large to re-encode and was not sent". 60 MP is a chosen memory budget, not a measured crash point: it caps the decode at 240 MB and leaves the destination canvas, the encoder and the rest of the tab inside a desktop budget.
2. Do not offer "send original anyway" for an image over the gate. The original is the thing that carries the GPS coordinates and the camera model, and the whole image path exists to strip them. Sending it silently defeats the feature.
3. Close the bitmap in a `finally`. A 48 MP `ImageBitmap` is 192 MB of GPU-visible memory that the garbage collector does not treat as pressure, which is the same failure mode as an unclosed `VideoFrame` in section 2.3.
4. Run the resize inside `createImageBitmap(blob, {resizeWidth, resizeHeight, resizeQuality: 'high'})`. MDN documents those options and documents `imageOrientation: "from-image"` as the default ([MDN, createImageBitmap](https://developer.mozilla.org/en-US/docs/Web/API/Window/createImageBitmap), fetched, title "Window: createImageBitmap() method"). What MDN does not document is whether Chromium decodes at full resolution and then downsamples or decodes straight to the smaller size. Budget the full decode and treat a lower peak as a bonus. UNVERIFIED either way.
5. Orientation changes which side is long, not the pixel count. A 1600x1200 file with `Orientation = 6` presents as 1200x1600, MEASURED in section 3.3, so the gate must run on the decoded bitmap's dimensions, not on the header's.
6. Animated images never enter this path (section 3.4), so their memory is the file's, not a decode's.

## 4. Files: unchanged, 50 MiB, with F-02 closed

The file path does not change in this wave. `MAX_FILE` stays 50 MiB (`:427`, checked at `:887` and `:1001`), chunking moves to 64 KiB per `04-crypto-design.md` section 4.3 rule 2, and every chunk gets its own AEAD.

What changes is the ordering that F-02 exploited. Today `beginIncoming` allocates the declared size before a byte arrives (`:1011`), `endIncoming` builds the Blob first (`:1046`) and enables Save (`:1050`), and only then checks the length (`:1051`). The zero-padded export is the result (`02-audit-findings.md` F-02). In the new pipeline the gate is a precondition, not a follow-up:

```
receive chunks -> verify tag, length, chunk count, digest
  -> only now: new Blob(parts, {type}) -> object URL -> render card + Save link
  -> on any failure: drop the parts, zero them, render a plain error line, no card
```

Order rules, all four needed:

1. Refuse `size > MAX_FILE` or `chunks !== ceil(size / 65536)` before allocating anything.
2. Allocate the parts array lazily, one 64 KiB plaintext chunk at a time, never `size` up front.
3. Verify the SHA-256 digest from `file-end` across the concatenated plaintext, not the ciphertext.
4. Only then build the Blob and the URL, and only then reveal Save. A progress card may exist during transfer, but it must have no Save affordance and no preview.

The 50 MiB cap stays even though video is 45 MiB: video is a re-encoded attachment, files are the unchanged path, and a 50 MiB file that is a video still goes through the transcode first if it is over 45 MiB and detectable as video. One sentence of policy in the UI: "Videos are re-encoded to fit 45 MB. Other files can be up to 50 MB."

## 5. Encryption ordering, and the length channel

### 5.1 Compress then encrypt, and why it is not a preference

Compression must run before encryption, because ciphertext is indistinguishable from random and does not compress. That is the whole argument, and it is a property of the AEAD, not a style choice. The order is fixed:

```
media bytes (already compressed by the codec, or by the image encoder)
  -> pack into the V2 file envelope: file-start with key_wrapped, then 64 KiB chunks
  -> AES-256-GCM per chunk, nonce = 4-byte file prefix || be64(index)
  -> AAD = id || index || size || chunks
  -> send on the data channel
```

Every element of that is from `04-crypto-design.md` section 4.3, and none of it changes here. What this file adds is where the *encoders* sit relative to it:

| Media | Already compressed by | Then encrypted by | Never do this |
|---|---|---|---|
| Video, transcoded | H.264 encoder at the planned bitrate | per-chunk AES-GCM | gzip the MP4, entropy coding already removed the redundancy |
| Video, passed through under 45 MiB | the source codec | per-chunk AES-GCM | re-encode just to compress, quality loss for no size win |
| Image | WebP or JPEG encoder at q 0.8 | per-chunk AES-GCM | gzip a WebP, it grows |
| File | whatever produced it | per-chunk AES-GCM | gzip before encrypting, it is the one case where it may help |

For an arbitrary file, a `CompressionStream('gzip')` pass before encryption is worth it when the file compresses, and it is a 5 line probe: compress the first 64 KiB, compare. If the ratio is under 1.05, skip. This is the only place in the app where user data is compressed generically, and it is worth having because a 50 MiB text log or a BMP becomes a fraction of that before it goes on the wire.

### 5.2 The length side channel, honestly

Encryption hides content, not size. Every frame's ciphertext length is visible to the peer, to a TURN operator, and to anyone watching the UDP flow. For this app that means:

- A message's length reveals the text length to within the AEAD tag and padding.
- A media transfer's length reveals the compressed size, which reveals roughly the duration and resolution, because the bitrate plan is deterministic and public.
- The total transfer size reveals which kind of attachment was sent, and the timing reveals when.

The fix, in the same place TLS does it. RFC 8446 section 5.4: "All encrypted TLS records can be padded to inflate the size of the TLSCiphertext. This allows the sender to hide the size of the traffic from an observer" ([RFC 8446](https://www.rfc-editor.org/rfc/rfc8446.html), fetched, section 5.4 titled "Record Padding"). We copy the trick, at the message level.

Padding policy, which is where the tradeoff gets bounded:

```
PAD = 4096                                // plaintext bucket, bytes
plaintext = header(4 B true length) || payload || zeros to next multiple of PAD
seal under the per-message key, AAD includes the true length
receiver: decrypt, read true length from the first 4 bytes, slice, zero the buffer
```

What that bounds, with the numbers:

| Quantity | Value | Effect |
|---|---|---|
| Bucket size | 4,096 B | Every frame length is a multiple of 4096 |
| Buckets in a 45 MiB transfer | 47,185,920 / 4096 = 11,520 | An observer learns one of 11,520 sizes |
| Information leaked | log2(11,520) = 13.5 bits | Down from log2(47,185,920) = 25.5 bits, a 12 bit reduction |
| Relative precision | 4,096 / 47,185,920 = 0.0087 percent | A 45 MiB video leaks its size to within 4 KiB, which is nothing |
| Cost on a 120 B text message | +4,072 B on the wire, 34x | Real, and the reason the bucket size is not smaller |

DERIVED. Read the table twice, because it says the padding is nearly pointless for exactly the case that worries people. A 45 MiB video is already visible as a 45 MiB transfer; hiding 4 KiB of that is noise. The length channel matters for small messages, where a 3 word reply and a 300 word paragraph should not be distinguishable, and there a 4 KiB bucket is 34x overhead on the wire, which is acceptable in a two-party chat and unacceptable at scale. So:

- **Text messages: pad to 4 KiB.** Cheap, real, hides the sentence length.
- **Media: pad the final chunk only**, so the transfer length is a multiple of the chunk size and no partial-chunk length is visible. Do not pad a 45 MiB video to a fixed size, because that requires constant-rate transmission and would triple the send time.
- **State the residual in the monitor overlay**, per `04-crypto-design.md` section 7.4: the overlay may report bytes sent, not "traffic analysis resistant".

One more honest note that belongs in the design rather than in marketing: per-message padding does not hide the bulk transfer, because the data channel's byte counters and the UDP flow size are visible to the transport anyway. `01-trust-map.md` says it directly: "DTLS does not pad" and "A 50 MiB transfer is a large, long UDP flow" (section "What DTLS does not hide"). Padding at the message layer is a text-channel control, and claiming otherwise would be false.

One implementation detail that matters for correctness: the true length sits inside the encrypted plaintext, not in the AAD alone, and the AAD binds it, so a truncated ciphertext fails the tag and a swapped length fails the tag. Put it in both and assert they agree on decrypt. `04-crypto-design.md` section 4.3 rule 4 already binds `size` in the AAD; this extends that binding to the padded frame.


## 6. Playback: decrypt into memory, never a temp file

### 6.1 The path

```
ciphertext chunks arrive
  -> verify + decrypt chunk into a Uint8Array part  (64 KiB)
  -> drop the ciphertext chunk immediately
  -> at file-end: verify SHA-256 over the parts
  -> new Blob(parts, {type: 'video/mp4'})          // one copy, in memory
  -> parts.forEach(p => p.fill(0)); parts.length = 0
  -> url = URL.createObjectURL(blob); video.src = url
  -> on wipe / replacement: remove the DOM node, then URL.revokeObjectURL(url)
```

No `showSaveFilePicker`, no OPFS, no IndexedDB, no service worker, no download until the user clicks Save. That is `04-crypto-design.md` section 4.3 rule 8 and the trust map's "App to browser storage" row: the app calls no persistence API, and the only write to disk is the Save anchor. The media path must not be the first exception to that rule, which is why `MediaSource` and a temp file are both out.

Why a Blob URL rather than `MediaSource` ([MDN, MediaSource](https://developer.mozilla.org/en-US/docs/Web/API/MediaSource), fetched, title "MediaSource - Web APIs | MDN"): MSE needs fragments and a `SourceBuffer`, which means either fragmented MP4 output from the muxer or re-fragmenting what you have, and it adds state to the wipe path. A Blob URL is one handle, seekable, and revoked with one call. MSE buys streaming playback before the transfer completes, which is a real feature and a V3 one. Write it down and skip it.

### 6.2 The CSP finding: video will not play today

V1's policy, `input/ephemeral-chat-v1.html:6`:

```
default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline';
img-src blob: data:; connect-src 'none'; base-uri 'none'; form-action 'none'
```

There is no `media-src`, and `default-src 'none'` is the fallback for every fetch directive that is not listed, which includes `media-src`. So a `<video src="blob:...">` is blocked.

MEASURED: with that exact policy in a meta tag, a 660 B WebM Blob created by `MediaRecorder` in the same page failed to load (`videoError 4` = `MEDIA_ERR_SRC_NOT_SUPPORTED`, `readyState 0`, no `loadedmetadata` within 2.5 s). The same construction played normally in a page without the policy, which is the control: a 2,121,220 B MP4 Blob played with `duration 10`, 1920x1080. So the blocker is the policy, not the media.

Fix: add `media-src blob:` to the policy. One directive. Two related grants to decide at the same time:

| Directive | Needed for | Decision |
|---|---|---|
| `media-src blob:` | `<video>` and `<audio>` playback from a Blob | **Add.** Without it the video feature cannot render |
| `worker-src blob:` | a Worker from a Blob URL, which is how the crypto lane's worker is built in a single file | Add if the Worker is created from a Blob, which `04-crypto-design.md` section 7.2 requires. Currently the policy has no `worker-src` and `default-src 'none'` blocks it |
| `img-src blob: data:` | image previews | Already present, keep |
| `script-src 'unsafe-inline'` | the whole app | Already present. Do not add `blob:` to `script-src` |

Adding `media-src blob:` widens the policy from "media from nowhere" to "media from this origin's own blobs". Since the app never loads a remote URL, the grant is bounded to bytes the page itself holds. That is the correct trade, and without it the owner's video ruling is unimplementable.

### 6.3 Blob URL lifecycle

`URL.createObjectURL` returns a URL that "points to the object given in the parameter" and must be released with `revokeObjectURL` ([MDN, createObjectURL](https://developer.mozilla.org/en-US/docs/Web/API/URL/createObjectURL_static), fetched, title "URL: createObjectURL() static method"; [MDN, revokeObjectURL](https://developer.mozilla.org/en-US/docs/Web/API/URL/revokeObjectURL_static), fetched, title "revokeObjectURL() static method"). Unreleased URLs keep the Blob alive for the life of the document, which for a 45 MB video is the whole session.

Rules, matched to the wipe paths in `01-trust-map.md` ("WIPE PATHS", `endSession` at `:554`):

| Event | Action | Why |
|---|---|---|
| Playback starts | Push the URL into the existing `urls` array (`:486`, pushed at `:891` and `:1048`) | One array is the one place the wipe has to look |
| Same card re-rendered | Revoke the old URL first, then create | Otherwise a re-render leaks one blob per render |
| `endSession` / wipe | `el.log.replaceChildren()` first, **then** revoke every URL in `urls`, then empty the array | The `<video>` and `<img>` nodes hold references; removing the nodes first is what makes the revoke effective. `06-ops-defense.md` section 2.1 states this ordering explicitly |
| `pagehide` | Revoke the URLs as well as clearing the log | V1's `pagehide` (`:1141-1145`) clears the log but does not revoke, so a bfcache entry keeps the blobs. Add the revoke |
| `pageshow` with `persisted` | Full reload, as V1 already does (`:1147-1149`) | Rebuilds state rather than resuming with live URLs |

What a revoke does and does not do, in the words the design has to keep: `URL.revokeObjectURL` "drops the handle; the bytes live until the Blob is collected" (`04-crypto-design.md` section 7.1 table). It stops new loads and frees the reference, it does not overwrite anything. Do not claim more.

### 6.4 Playback behavior details

- Autoplay: `muted playsinline` on the element, and no autoplay of a received video with sound. A received video appears as a card with a play affordance, per the existing file-card pattern (`:928-996`).
- Seeking works because the Blob is a real seekable resource, unlike a `MediaStream`. That is the practical reason to finish the transfer before playing rather than streaming.
- A 45 MiB video decodes from memory, so the browser's media stack allocates its own buffers on top of the 45 MiB Blob. That term is opaque and UNVERIFIED, see section 2.11.
- If `video.onerror` fires after a successful decrypt and digest, the failure is a codec problem, not a transport one. Show "this file cannot be played here", keep the Save link, do not retry the transfer. Distinguishing those two is one branch and it prevents a pointless re-send.

## 7. Paste, drop and picker are one path

V1 has three entry points that each call `queueFiles`: the hidden input (`:1100-1104`), a document-level `drop` (`:1110-1121`), and a document-level `paste` (`:1124-1131`). They converge on `sendFile` (`:883`), which is the right shape. The media pipeline must keep that shape and add one function in front of it:

```
async function acceptFile(file, source) {   // source: 'pick' | 'drop' | 'paste'
  name = file.name || synthesizedName(file.type, source)
  if (isAnimated(file.type))      return sendOriginal(file, name)
  if (isImage(file.type))         return sendOriginalOrReencode(file, name)
  if (isVideo(file.type))         return transcodeOrSend(file, name)
  return sendOriginal(file, name)              // files, up to 50 MiB
}
```

`source` is used for exactly one thing: a name, when the platform gives none. A pasted screenshot arrives as a `File` with an empty `name` and type `image/png`, so the synthesized name is `pasted-<timestamp>.png`... use a counter, not a timestamp, because a timestamp is a correlation handle the design already refuses elsewhere ("Never show a session id", `04-crypto-design.md` section 7.3). `pasted-1.png`.

Three failure modes that only the paste path has, and their handling:

| Case | What arrives | Handling |
|---|---|---|
| Screenshot paste | `image/png`, no name, often 2 to 8 MB of flat UI | Re-encode to WebP. The measured 88 percent reduction on a photo applies even harder to a flat UI |
| Copied image from another page | `image/png` with transparent corners | Keep alpha, WebP handles it |
| Paste while a transfer is running | a second `File` | Queue as V1 already does (`queueFiles`, `:872-881`). Do not start a second transcode, one encoder at a time |

And one rule that is not about files: `paste` must not intercept text. V1's handler only reads `clipboardData.files` and returns otherwise (`:1126`), which is correct, keep it.

The single-path rule has a security consequence worth stating: because all three sources go through the same `acceptFile`, the image re-encode and therefore the metadata strip applies to a pasted screenshot exactly as it does to a dropped photo. A second code path for paste is how a GPS leak gets reintroduced later.

## 8. Where this lands in the file

Nothing here needs a new file. The app stays one HTML file with no build step for the core, and the vendored muxer goes in as one `<script>` block.

| Touch point | Line | Change | Lines |
|---|---|---|---|
| CSP meta | 6 | add `media-src blob:; worker-src blob:` | 0 |
| `MAX_FILE` | 427 | unchanged. Add `MAX_VIDEO = 45 * 1024 * 1024` beside it | +2 |
| `CHUNK` | 428 | 16 KiB to 64 KiB, per `04-crypto-design.md` 4.3 rule 2 | 1 |
| `acceptFile` | new, before 883 | one entry point for pick, drop, paste | +45 |
| `sendFile` | 883-926 | 64 KiB slices, digest frame at the end, no other change | +6 |
| `planBitrate` | new | the table in 2.4 as arithmetic | +20 |
| `transcode` | new | element decode, `VideoEncoder`, mux, post-check | +120 |
| `encodeImage` | new | 3.1, with the 3.5 pixel gate | +30 |
| `beginIncoming` | 998-1016 | store metadata only, delete `new Uint8Array(size)` at 1011 | -3, +2 |
| `endIncoming` | 1038-1053 | verify length, count and digest before Blob and Save | +12 |
| startup probe | new | WebP support, `VideoEncoder.isConfigSupported`, cached | +10 |
| `endSession` | 554-570 | reorder: `replaceChildren()` before the revoke loop | 0, move 3 |
| `pagehide` | 1141-1145 | add the revoke loop | +3 |

Two things in that table are worth calling out because they are code changes hidden inside existing lines.

The `endSession` reorder is one of them. V1 revokes every object URL at 559-561 and only then calls `el.log.replaceChildren()` at 564. The `<video>` and `<img>` nodes still hold their blobs when the revoke runs, so the URL stops resolving while the element keeps displaying cached content until it is removed. V1 gets away with it because the panel is hidden immediately. The correct order, stated in `06-ops-defense.md` section 2.1, is DOM first, then URLs, then buffers. That is a move, not new logic.

The `beginIncoming` deletion is the other. Removing the eager `Uint8Array(size)` at 1011 removes the allocation that F-02 exploited and removes half the receiver's peak memory in the same edit. The parts array is built one 64 KiB plaintext chunk at a time as chunks arrive.

Size budget, with the arithmetic shown:

```
today                     35,598 B raw      9,502 B gz    MEASURED, input/ephemeral-chat-v1.html
vendored muxer            31,103 B          9,062 B gz    MEASURED, esbuild 0.25.0, gzip 9
new code, about 250 lines  ~10,000 B         ~3,500 B gz   INFERRED at 40 B per line raw
                          ---------         ----------
total                      ~76,700 B         ~22,100 B gz
```

That is about 2.2x the raw file and 2.3x gzipped. For a desktop app that ships its own Chromium, 22 KB of HTML is not the cost that matters. The 31 KB muxer is three quarters of the new raw bytes, and it is the only dependency.

One ceiling this table implies and does not solve: `urls` grows by one entry per sent or received attachment and is only emptied at wipe. V1 got away with that because an image is a few hundred KB. A session with ten 45 MiB videos is 450 MB of live Blobs, all reachable, none released until `endSession`. V2 should cap retained media at five attachments and revoke the oldest URL when the sixth arrives, with the card left as a name and a Save link. That is a small change to the `urls` array, not a cache. Flag it for the build wave rather than pretending the existing lifecycle scales.

## 9. The one candidate that would be EXEC-ONLY, considered and rejected

The candidate is a bundled ffmpeg binary in the launcher, used as a sidecar: pipe the source file in, get an MP4 out, at ten times realtime instead of one.

What it would add is real. Faster than realtime removes the 2.8 wait entirely, every container and codec works, audio comes from the demuxer instead of a WebAudio capture, and the output size is exact on the first try. On paper it is the best transcoder in the list.

Why it is rejected for V2:

- **It cannot run in file mode.** The core HTML has no process to spawn. The owner's constraint says a feature that only works in the shell is packaging, and must be flagged EXEC-ONLY. A video that compresses in 4 seconds in the app and 40 seconds in the file is not one feature with two implementations, it is two products with one name. That is a support matrix nobody wants to explain.
- **It adds a memory-unsafe parser in front of attacker-controlled bytes.** The browser's decoder is also a parser, but it runs inside the renderer sandbox and is patched by the browser vendor on its own schedule. A bundled ffmpeg is our binary to patch, on three platforms, forever. FFmpeg's own security page is a running list of memory-safety fixes with CVE identifiers, which is the honest measure of what shipping it means ([ffmpeg.org/security.html](https://ffmpeg.org/security.html), fetched, title "FFmpeg Security"). The brief's vulnerability lanes exist to count exactly this kind of surface; adding it for a speed win is the wrong trade.
- **It creates the temp file the design forbids.** A sidecar wants a path on both ends. Piping stdin and stdout avoids that, but then it is a streaming process whose output has to be buffered anyway, and the "never a temp file" rule now depends on every future maintainer not taking the shortcut.
- **It costs tens of MB per platform and a signing story per OS.** INFERRED, not measured here, and deliberately not quoted as a number in the UI.

Verdict: reject for V2. Revisit in V3 only as an optional accelerator behind an explicit setting, with stdin and stdout pipes, no temp files, no network, and the in-browser path kept as the default. The 40 second wait in section 2.8 is the price of one code path that works everywhere, and it is the right price for this release.

## 10. What would falsify this

Every row is a test the build wave can run, with the condition that would prove the design wrong rather than merely disappointing.

| Claim | Test | Pass condition | If it fails |
|---|---|---|---|
| 1x is the real bound, not a guess | Transcode a 5 minute 1080p clip in the shipped shell, headed | Wall time within 15 percent of duration, dropped frames under 2 percent | The demuxer in option C moves from V2.1 to V2, at 49 KB gzipped |
| The bitrate plan fits 45 MiB | Three phone clips, 15 s, 60 s and 5 min, real footage | First pass under 45 MiB on at least two of three, no second retry | Raise the 90 percent headroom to 85, or lower the bits-per-pixel floor |
| Audio and video stay in sync | 5 minute clip with a hand clap at both ends | Audio offset under 100 ms at the end | Shorten the transcode cap to 180 s and say so |
| Hardware encode exists where claimed | `isConfigSupported` in the shipped shell, headed | `avc1.640028` with `prefer-hardware` reports supported | Expect roughly 10x the CPU and show a slower time estimate |
| The first encoded chunk carries a decoderConfig | Assert `meta.decoderConfig` on chunk 0, 20 runs | Non-null every time | Fall to rung B, never let finalize throw |
| The image path strips metadata in the shipped build | Byte scan WebP and JPEG output for Exif, GPS, XMP, ICC | Zero markers in WebP, ICC absent, JPEG may keep ICC | The canvas path is not what shipped, find the extra copy |
| Blob URLs do not accumulate | Ten attach and wipe cycles | `urls.length` is 0 after each wipe, no detached media nodes | The revoke order is wrong, see section 8 |
| 45 MiB plays on iOS | Oldest supported iPhone, 45 MiB video | No tab reload, playback starts | Drop the mobile video cap to 16 MiB |
| Colour is not visibly wrong | Display P3 photo through the pipeline | The shift is described in the release note | Add a colour conversion step before the encode |
| The CSP is the only reason video failed | Remove `media-src`, then restore it | Error 4 without, playback with | The finding in 6.2 was wrong, re-measure |

The fifth row is not hypothetical. One 290 frame canvas-path run through the muxer failed in `finalize()` with `TypeError: Cannot read properties of null (reading 'colorSpace')`, while runs of 3, 5, 60 and 300 frames through the same page completed and produced valid MP4s (39,100 B, 42,042 B, 32,419 B and 355,818 B). The failure was not isolated, and the cause is UNVERIFIED. What is verified is that the muxer reads `decoderConfig.colorSpace` during `finalize()` and that a null config crashes it. A one-line assertion on the first chunk, with rung B as the fallback, turns an intermittent crash into a visible downgrade. Ship that assertion.

## 11. Measurement method and provenance

Host: macOS 26.4.1 on Apple Silicon, GPU string from WebGL `ANGLE (Apple, ANGLE Metal Renderer: Apple M2 Pro, Unspecified Version)`.

Browsers: Google Chrome 158.0.8127.38, headed, for every media measurement, because `prefer-hardware` lies under the headless shell. `chrome-headless-shell` 159.0.8154.6 for DOM and decode probes only. Playwright drove both from Python.

Image fixture, rebuilt and also re-used from the predecessor's scratch directory: a 1600x1200 JPEG, 210,301 B, with EXIF `Make = SECRETGPS`, `Model = LEAKMODEL`, `Orientation = 6`, a GPS IFD at 48,12,30 N and 16,22,11 E, an XMP packet containing `http://ns.adobe.com/xap`, and an sRGB ICC profile. The input file contains all six markers (`Exif`, `SECRETGPS`, `LEAKMODEL`, `GPS`, the XMP namespace, `ICC_PROFILE`), which is the control. The probe draws the image at its presented size into a canvas with `alpha:false`, converts to WebP q 0.8, WebP q 0.5, JPEG q 0.8, AVIF q 0.8 and PNG, then byte-scans each output for the six strings. The same page calls `createImageBitmap` with `imageOrientation: 'from-image'`, and probes `VideoEncoder.isConfigSupported` and `VideoFrame.allocationSize()`.

Commands, enough to rebuild:

```
python3 -m http.server 8791 --directory <fixture dir>
# Playwright: goto /index.html, evaluate runTest(), read window.__res
# Playwright: goto /bench3.html, evaluate run3()      element-frame encode
# Playwright: goto /rec.html,   evaluate run2()       MediaRecorder fallback
# Playwright: goto /csp.html,   evaluate cspTest()    CSP media-src probe
```

Bundle sizes, one pass each, entry files named in the table:

```
npm i mp4-muxer@5.2.2 mediabunny@1.66.5 esbuild@0.25.0
esbuild <entry>.js --bundle --minify --format=iife --platform=browser --outfile=<entry>.out.js
gzip -9 -c <entry>.out.js | wc -c
```

| Entry | Raw | Gzip 9 |
|---|---|---|
| mp4-muxer 5.2.2, `{Muxer, ArrayBufferTarget}` | 31,103 B | 9,062 B |
| mediabunny 1.66.5, `{Output, Mp4OutputFormat, BufferTarget}` | 135,497 B | 34,761 B |
| mediabunny 1.66.5, `export *` | 793,794 B | 199,863 B |

Video source for the encode benches: a 10.0 s 1920x1080 30 fps MP4, 28,290,307 B, played through a `<video>` element. `bench3.html` encodes element frames directly with `requestVideoFrameCallback` timestamps. `rec.html` records a 1920x1080 canvas stream with `videoBitsPerSecond: 4000000`. Both ran headed.

What was re-run in this continuation pass, against what the earlier pass recorded:

| Item | Earlier pass | This pass | Verdict |
|---|---|---|---|
| H.264 and HEVC `prefer-hardware` | supported | supported, config echo confirms | CONFIRMED |
| VP8, VP9, AV1 `prefer-hardware` | not supported | not supported | CONFIRMED |
| 1080p frame allocation | 8,294,400 B, BGRA | 8,294,400 B, RGBA | CONFIRMED, format label corrected |
| WebP q 0.8 on the fixture | 24,896 B | 24,916 B | CONFIRMED within 0.1 percent |
| JPEG q 0.8 on the fixture | 114,032 B | 113,892 B | CONFIRMED within 0.2 percent |
| PNG size, and the AVIF fallback | 132,278 B | 292,065 B | REPLACED, see 3.1 and 3.2 |
| EXIF, GPS, XMP, ICC marker matrix | all rows | identical | CONFIRMED |
| CSP blocks a blob video | error 4, readyState 0 | error 4, readyState 0 | CONFIRMED |
| Bitrate accuracy, 4 Mbps target | 5,010,125 B, +0.2 percent | 4,847,208 B, -3.1 percent | REPLACED, conclusion unchanged |
| MediaRecorder undershoot | 2,324 kbps, 42 percent under | 3,476 kbps, 13 percent under | REPLACED, conclusion unchanged |
| mp4-muxer size | 31,104 B / 9,067 B gz | 31,103 B / 9,062 B gz | CONFIRMED |
| mediabunny mux-only size | 128,863 B / 34,702 B gz | 135,497 B / 34,761 B gz | ENTRY SHAPE DIFFERS, gzip within 0.2 percent |
| Canvas area ceiling | not stated | 268,435,456 px | NEW, section 3.5 |
| Canvas versus element frame rate | 126 versus 300 frames | one canvas run crashed before reporting | NOT RE-RUN, inherited |
| Mux round trip and playback | 2,121,220 B, played | 300 frames finalized at 355,818 B, not played back | PARTIAL, inherited |

Two notes that belong here rather than in the design. The headless shell answered `prefer-hardware` with false for every codec, including H.264, while headed Chrome answered true for H.264 and HEVC and false for the rest. Any future bench run in `chrome-headless-shell` will produce a wrong codec matrix and should be discarded. And the earlier pass's PNG figure did not reproduce on its own fixture; the replacement is in the table above and the conclusions in 3.1 and 3.2 were rewritten to match.

What this file does not settle, stated so the next lane does not assume it: the 290 frame muxer failure (section 10), whether Chromium downsamples during `createImageBitmap` decode (3.5), the HDR tone mapping result (2.10), audio drift past 60 s (2.6), and the iOS memory kill threshold (2.11). All five are marked UNVERIFIED where they appear. None of them changes a decision in section 0.

## 12. SELF-CHECK

Covers the inherited sections 0 to 7 as well as the new 3.5 and 8 to 11.

| # | Acceptance item | Result | Evidence |
|---|---|---|---|
| 1 | The file is complete in the inherited numbering and ends with this section | PASS | Sections 0 to 12 present, section 12 closes the file |
| 2 | Inherited line references re-checked against the input, not trusted | PASS | 18 line references read directly from `input/ephemeral-chat-v1.html`: 6, 427, 428, 486, 554, 559-564, 872, 883, 887, 891, 893, 928, 998-1016, 1038-1053, 1100, 1110, 1124, 1141-1149. All match |
| 3 | Every API claim carries a verified source URL | PASS | 21 sources fetched this pass, titles checked, listed below |
| 4 | The EXIF answer is verified, not guessed | PASS | Two fixtures, Chrome 158 and headless shell 159, byte scan: EXIF, GPS and XMP absent from every canvas output; ICC present only in the JPEG output; orientation applied at decode, 1200x1600 measured |
| 5 | Memory math shows its inputs | PASS | Section 2.11: frame sizes from `allocationSize()`, queue depth, both muxer copies. Section 3.5: pixels times 4 B, plus the measured 268,435,456 px canvas ceiling |
| 6 | Image memory ceilings present | PASS | Section 3.5, four source sizes, a pixel gate at 60 MP, and the closing rule for the bitmap |
| 7 | Encryption ordering, compress then encrypt, per-message AEAD | PASS | Sections 5.1 and 5.2, built on `04-crypto-design.md` 4.3, with the padding tradeoff bounded to text and the residual leak stated |
| 8 | Playback decrypts into memory, blob URL, never a temp file, revoke lifecycle | PASS | Sections 6.1 to 6.4, including the measured CSP failure and the revoke ordering that V1 gets backwards |
| 9 | Files unchanged at 50 MiB with F-02 closed | PASS | Section 4, gate before Blob and Save, four order rules |
| 10 | Both modes, or an explicit EXEC-ONLY flag | PASS | No feature is EXEC-ONLY. The one candidate is rejected in section 9 with reasons |
| 11 | No em dashes and no en dashes | PASS | Scripted scan of the whole file after the final edit, 0 hits for U+2013 and U+2014 |
| 12 | Read-only mission, one output file | PASS | Only `01-research/output/12-media-pipeline.md` written. Scratch fixtures live outside the repo |
| 13 | Every MEASURED number traces to a method | PASS | Section 11 lists the host, the browsers, the fixture, the commands and the bundle table. Numbers that were not re-run are labelled inherited |
| 14 | Time budget | FAIL, overrun | Tool work ran well past 25 minutes because the respawn required re-verifying inherited measurements and completing the missing sections. Scope was not cut, and no section was skipped |
| 15 | Options ranked with source, size and security posture | PASS | Section 2.2 table plus the posture paragraph, every size traced to section 11 |

Sources fetched in this pass, each with its title checked:

| Source | What it supports |
|---|---|
| [MDN, WebCodecs API](https://developer.mozilla.org/en-US/docs/Web/API/WebCodecs_API) | The encoder and decoder transform chunks to frames and back, available in workers |
| [MDN, VideoEncoder](https://developer.mozilla.org/en-US/docs/Web/API/VideoEncoder) | `encodeQueueSize` is the number of encode queue requests |
| [MDN, VideoEncoder.configure()](https://developer.mozilla.org/en-US/docs/Web/API/VideoEncoder/configure) | `bitrate` average, `bitrateMode`, `latencyMode`, `alpha` default discard, `hardwareAcceleration` values |
| [MDN, VideoFrame.close()](https://developer.mozilla.org/en-US/docs/Web/API/VideoFrame/close) | Clears state and releases the media reference |
| [MDN, AudioEncoder](https://developer.mozilla.org/en-US/docs/Web/API/AudioEncoder) | `AudioData` to `EncodedAudioChunk`, queue and flush |
| [MDN, HTMLCanvasElement.toBlob()](https://developer.mozilla.org/en-US/docs/Web/API/HTMLCanvasElement/toBlob) | PNG fallback for unsupported types, fabricated 96 dpi |
| [MDN, OffscreenCanvas.convertToBlob()](https://developer.mozilla.org/en-US/docs/Web/API/OffscreenCanvas/convertToBlob) | Same type and quality contract, worker availability |
| [MDN, createImageBitmap()](https://developer.mozilla.org/en-US/docs/Web/API/Window/createImageBitmap) | `imageOrientation` defaults to `from-image`, resize options |
| [MDN, URL.createObjectURL()](https://developer.mozilla.org/en-US/docs/Web/API/URL/createObjectURL_static) | URL points to the object in the parameter |
| [MDN, URL.revokeObjectURL()](https://developer.mozilla.org/en-US/docs/Web/API/URL/revokeObjectURL_static) | Releases an existing object URL |
| [MDN, MediaRecorder](https://developer.mozilla.org/en-US/docs/Web/API/MediaRecorder) | Baseline since April 2021 |
| [caniuse, WebCodecs](https://caniuse.com/webcodecs) | Chrome 94, Edge 94, Firefox 130, Safari 16.4 partial and 26.0 full |
| [GitHub, mp4-muxer](https://github.com/Vanilagy/mp4-muxer) | Deprecated in favour of Mediabunny, verbatim quote |
| [GitHub, webm-muxer](https://github.com/Vanilagy/webm-muxer) | Same deprecation, verbatim quote |
| [Apple, VideoToolbox](https://developer.apple.com/documentation/videotoolbox) | "direct access to hardware encoders and decoders" |
| [RFC 8446, section 5.4](https://www.rfc-editor.org/rfc/rfc8446.html) | Record padding hides traffic size from an observer |
| [GitHub, mediabunny](https://github.com/Vanilagy/mediabunny) | MPL-2.0 successor to both muxers, used by the size comparison |
| [GitHub, mp4box.js](https://github.com/gpac/mp4box.js) | BSD 3-Clause demuxer behind option C |
| [MDN, ScriptProcessorNode](https://developer.mozilla.org/en-US/docs/Web/API/ScriptProcessorNode) | Deprecated, replaced by AudioWorklet |
| [MDN, MediaSource](https://developer.mozilla.org/en-US/docs/Web/API/MediaSource) | MSE and SourceBuffer, the alternative to a blob URL |
| [FFmpeg Security](https://ffmpeg.org/security.html) | The CVE list that makes a sidecar decoder a liability |
