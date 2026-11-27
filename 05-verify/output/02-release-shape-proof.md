# Release shape proof, packaged macOS app with fuses

LANE: 2, RELEASE SHAPE
RUN: w26-ephemeral-verify-20261127
DATE: 2026-11-27
HOST: macOS 26.4.1, arm64, node v22.23.2, npm 10.9.8
STATUS: PASS, all four accept criteria met, three release defects recorded

Closes the fused binary named limit in `03-build/output/wrapper/BUILD.md`: "No fused
release binary exists in this round, so the passing side of the read is the named limit."

No git command was run in this lane. Build tools live only in the scratch dir. The
packaged app and its SHA256SUMS live in the project's gitignored `.agent-runs/` dir.

## Result table

| Accept criterion | Command | Result |
|---|---|---|
| Fuses read on the PACKAGED binary, runAsNode, nodeOptions, nodeCliInspect all off | `sh scripts/fuses.sh read --app <packaged app>` | PASS, all three Disabled |
| build-gate PASSES on the app where it REFUSED the stock framework | `EPHEMERAL_BUILD_HASH=<core sha> sh scripts/build-gate.sh --app <packaged app>` | PASS, exit 0. Stock framework: REFUSED, exit 1 |
| hash-artifacts includes the app bundle | `sh scripts/hash-artifacts.sh <artifacts dir>` | PASS, 266 of 266 entries under `ephemeral.app/`, reproducible |
| e2e-core-load against the PACKAGED app serves the pinned core and boots to S0 | `ELECTRON_BIN=<packaged app>/Contents/MacOS/ephemeral sh scripts/e2e-core-load.sh` | PASS, served=169810 bytes, screen S0 |

Behavioral accept, beyond the read: with `ELECTRON_RUN_AS_NODE=1` the stock binary
executes node code, the packaged binary does not.

## 1. Inputs and environment

Pinned core, the artifact this run verifies:

```
$ shasum -a 256 03-build/output/ephemeral-chat-v2.html
2092e0e9e8e3418ba167e22b99623094e0f5d05ea876014874be1e3c4b53b87b  03-build/output/ephemeral-chat-v2.html
$ wc -c 03-build/output/ephemeral-chat-v2.html
  169810 03-build/output/ephemeral-chat-v2.html
```

Wrapper inputs, copied, not edited:

```
$ shasum -a 256 03-build/output/wrapper/main.cjs 03-build/output/wrapper/package.json 03-build/output/wrapper/fuses.json
56a3e85d163991aebee0e410550deb2b191fe5e2becd902843b03f8b3f480f94  main.cjs
9df42ef0f889902b2857f6c1506ebc5880fd4e6752a11773858637ffafe2a791  package.json
0df54723768518bcc424d624c3ef18621b6624ce53b2c61fe77b40b35990158e  fuses.json
```

Framework: the stock Electron 45.5.0 darwin-arm64 framework at
`/Users/marcelspatz/.hermes/cache/scratch/w5-electron/node_modules/electron/dist/Electron.app`.
Its `dist/version` reads `45.5.0`. The matching zip was already in the host cache at
`~/Library/Caches/electron/3b240e2bf8f7a3bdbf4436b08f324ce6cefbc1d217c9b8ec4db54ca8fa1ca8de/electron-v45.5.0-darwin-arm64.zip`.

Packaging tools, installed into the scratch dir only, never the project tree:

```
$ mkdir -p /Users/marcelspatz/.hermes/cache/scratch/w26-release-shape/tools
$ cd /Users/marcelspatz/.hermes/cache/scratch/w26-release-shape/tools
$ npm init -y
$ npm install --no-audit --no-fund @electron/packager@latest @electron/fuses@2.1.3 @electron/asar@latest
added 50 packages in 4s

$ npm ls --depth=0
tools@1.0.0 /Users/marcelspatz/.hermes/cache/scratch/w26-release-shape/tools
+-- @electron/asar@4.3.4
+-- @electron/fuses@2.1.3
+-- @electron/packager@20.3.0
```

Tree glyphs above are normalized to ASCII; the version lines are the raw output.

## 2. Stage the wrapper beside the pinned core

```
$ W=/Users/marcelspatz/.hermes/cache/scratch/w26-release-shape
$ S=/Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/03-build/output/wrapper
$ mkdir -p "$W/stage/app/core"
$ cp "$S/main.cjs" "$S/preload.cjs" "$S/menu.cjs" "$S/qr.cjs" "$S/package.json" "$W/stage/app/"
$ cp /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/03-build/output/ephemeral-chat-v2.html \
    "$W/stage/app/core/ephemeral-chat-v2.html"
$ ls -la "$W/stage/app" "$W/stage/app/core"
-rw-r--r--  18067 main.cjs
-rw-r--r--   2987 menu.cjs
-rw-r--r--    680 package.json
-rw-r--r--    924 preload.cjs
-rw-r--r--   2330 qr.cjs
-rw-r--r-- 169810 core/ephemeral-chat-v2.html
```

## 3. Package with @electron/packager 20.3.0

```
$ cd "$W/tools"
$ ./node_modules/.bin/electron-packager "$W/stage/app" ephemeral \
    --platform=darwin --arch=arm64 --electron-version=45.5.0 \
    --electron-zip-dir="$HOME/Library/Caches/electron/3b240e2bf8f7a3bdbf4436b08f324ce6cefbc1d217c9b8ec4db54ca8fa1ca8de" \
    --out="$W/out" --overwrite --asar --asar-integrity-digest \
    --app-bundle-id=com.ephemeral.shell --app-version=2.0.0 --build-version=2.0.0 \
    --no-osx-sign
Packaging app for platform darwin arm64 using electron v45.5.0
Wrote new app to: /Users/marcelspatz/.hermes/cache/scratch/w26-release-shape/out/ephemeral-darwin-arm64
```

Bundle contents:

```
$ ./node_modules/.bin/asar list out/ephemeral-darwin-arm64/ephemeral.app/Contents/Resources/app.asar
/core
/core/ephemeral-chat-v2.html
/main.cjs
/menu.cjs
/package.json
/preload.cjs
/qr.cjs
```

The asar carries the pinned core byte for byte:

```
$ mkdir -p "$W/extract" && cd "$W/extract"
$ "$W/tools/node_modules/.bin/asar" extract-file \
    /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/.agent-runs/w26-lane2-release-shape/artifacts/ephemeral.app/Contents/Resources/app.asar \
    core/ephemeral-chat-v2.html
$ shasum -a 256 ephemeral-chat-v2.html
2092e0e9e8e3418ba167e22b99623094e0f5d05ea876014874be1e3c4b53b87b  ephemeral-chat-v2.html
$ wc -c ephemeral-chat-v2.html
  169810 ephemeral-chat-v2.html
```

Packager 20.3.0 embeds the asar integrity digest because `--asar-integrity-digest`
defaults true on macOS with Electron >= 41.0.0:

```
$ /usr/libexec/PlistBuddy -c "Print :ElectronAsarIntegrity" "$APP/Contents/Info.plist"
Dict {
    Resources/app.asar = Dict {
        hash = 9d38abc95711010121055bcec1933b27f6202d6804b7efaf3b1ce7174e81c094
        algorithm = SHA256
    }
}
```

`ElectronAsarIntegrity` is the asar header digest, not the file hash, which is why it
differs from `shasum` on `app.asar`. The proof that it validates is that the app boots
with `EnableEmbeddedAsarIntegrityValidation` enabled (section 6).

## 4. Flip the fuses, defect found in the wrapper script

The lane requires the wrapper's own script. Run as shipped, it fails.

Exact sequence used, in order, each step below with its raw output:

1. write the full fuse table from `fuses.json`
2. launch, killed by macOS (invalid signature after the write)
3. ad-hoc codesign
4. launch, aborts on the missing browser V8 snapshot (4a)
5. return `loadBrowserProcessSpecificV8Snapshot` to off
6. ad-hoc codesign again
7. launch, PASS

```
$ cd /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/03-build/output/wrapper
$ APP="/Users/marcelspatz/.hermes/cache/scratch/w26-release-shape/out/ephemeral-darwin-arm64/ephemeral.app"
$ sh scripts/fuses.sh flags
runAsNode=off nodeOptions=off nodeCliInspect=off onlyLoadAppFromAsar=on embeddedAsarIntegrityValidation=on grantFileProtocolExtraPrivileges=off loadBrowserProcessSpecificV8Snapshot=on cookieEncryption=off wasmTrapHandlers=on

$ sh scripts/fuses.sh write --app "$APP"
Analyzing app: ephemeral.app
Fuse Version: v1
Invalid fuse name runAsNode
Expected name to be one of ["RunAsNode","EnableCookieEncryption","EnableNodeOptionsEnvironmentVariable","EnableNodeCliInspectArguments","EnableEmbeddedAsarIntegrityValidation","OnlyLoadAppFromAsar","LoadBrowserProcessSpecificV8Snapshot","GrantFileProtocolExtraPrivileges","WasmTrapHandlers"]
write_exit=1
```

Root cause: `fuses.sh` builds flags from the lowerCamel keys in `fuses.json`, but
`@electron/fuses` 2.1.3 accepts only the enum names above. This is not app specific;
the write path never worked.

To stay inside this lane's declared file, the project tree was not edited. A scratch
copy of `scripts/fuses.sh` beside a copy of `fuses.json` got one mapping table, and
nothing else:

```
$ cp "$S/scripts/fuses.sh" "$W/stage/scripts/fuses-fixed.sh"
$ cp "$S/fuses.json" "$W/stage/fuses.json"
# python3 patch, one block replaced in the flag emitter:
NAMES = {
    "runAsNode": "RunAsNode",
    "nodeOptions": "EnableNodeOptionsEnvironmentVariable",
    "nodeCliInspect": "EnableNodeCliInspectArguments",
    "onlyLoadAppFromAsar": "OnlyLoadAppFromAsar",
    "embeddedAsarIntegrityValidation": "EnableEmbeddedAsarIntegrityValidation",
    "grantFileProtocolExtraPrivileges": "GrantFileProtocolExtraPrivileges",
    "loadBrowserProcessSpecificV8Snapshot": "LoadBrowserProcessSpecificV8Snapshot",
    "cookieEncryption": "EnableCookieEncryption",
    "wasmTrapHandlers": "WasmTrapHandlers",
}
pairs = []
unknown = [key for key in data["fuses"] if key not in NAMES]
if unknown:
    raise SystemExit("unmapped fuse name(s): %s" % ", ".join(unknown))
for name, value in data["fuses"].items():
    pairs.append("%s=%s" % (NAMES[name], "on" if value else "off"))
print(" ".join(pairs))
```

The scratch copy emits the tool's names and writes:

```
$ sh "$W/stage/scripts/fuses-fixed.sh" flags
RunAsNode=off EnableNodeOptionsEnvironmentVariable=off EnableNodeCliInspectArguments=off OnlyLoadAppFromAsar=on EnableEmbeddedAsarIntegrityValidation=on GrantFileProtocolExtraPrivileges=off LoadBrowserProcessSpecificV8Snapshot=on EnableCookieEncryption=off WasmTrapHandlers=on

$ sh "$W/stage/scripts/fuses-fixed.sh" write --app "$APP"
Analyzing app: ephemeral.app
Fuse Version: v1
  RunAsNode is Enabled and will become Disabled
  EnableNodeOptionsEnvironmentVariable is Enabled and will become Disabled
  EnableNodeCliInspectArguments is Enabled and will become Disabled
  OnlyLoadAppFromAsar is Disabled and will become Enabled
  EnableEmbeddedAsarIntegrityValidation is Disabled and will become Enabled
  GrantFileProtocolExtraPrivileges is Enabled and will become Disabled
  LoadBrowserProcessSpecificV8Snapshot is Disabled and will become Enabled
  EnableCookieEncryption is already Disabled and will not be changed
  WasmTrapHandlers is already Enabled and will not be changed
Writing to app: ephemeral.app
Fuses written to disk
write_exit=0
```

### 4a. The browser snapshot fuse cannot be enabled on this framework

After the write above, launch fails:

```
$ ELECTRON_BIN="$APP/Contents/MacOS/ephemeral" sh scripts/e2e-core-load.sh
scripts/e2e-core-load.sh: line 48: 44010 Trace/BPT trap: 5       EPHEMERAL_BUILD_HASH="$core_hash" EPHEMERAL_E2E=1 "$electron" "$stage/app" > "$log" 2>&1
e2e: electron exited non zero
[1127/122536.992466:FATAL:gin/v8_initializer.cc:664] Error loading V8 startup snapshot file
```

Root cause: the stock Electron 45.5.0 darwin-arm64 framework ships only
`v8_context_snapshot.arm64.bin`. It has no `browser_v8_context_snapshot.bin`:

```
$ find /Users/marcelspatz/.hermes/cache/scratch/w5-electron/node_modules/electron/dist/Electron.app -name "*snapshot*"
.../Electron Framework.framework/Versions/A/Resources/v8_context_snapshot.arm64.bin
```

`fuses.json` sets `loadBrowserProcessSpecificV8Snapshot: true` and its own note says the
release build must produce the browser process snapshot. This framework does not. The
fuse was therefore returned to the framework default, off, on the packaged binary with
the pinned tool. Every required-off fuse is unaffected:

```
$ "$W/tools/node_modules/.bin/electron-fuses" write --app "$APP" LoadBrowserProcessSpecificV8Snapshot=off
Analyzing app: ephemeral.app
Fuse Version: v1
  LoadBrowserProcessSpecificV8Snapshot is Enabled and will become Disabled
Writing to app: ephemeral.app
Fuses written to disk
```

### 4b. Fuse write invalidates the signature, re-sign is a required release step

The first launch after the fuse write was killed by macOS before any app code ran:

```
scripts/e2e-core-load.sh: line 48: 43901 Killed: 9               EPHEMERAL_BUILD_HASH="$core_hash" EPHEMERAL_E2E=1 "$electron" "$stage/app" > "$log" 2>&1
e2e: electron exited non zero
```

Cause: `@electron/fuses` rewrites the main executable and does not re-sign. On arm64 an
invalid code signature is fatal. Release order is package, fuse, sign. Ad-hoc sign for
this local proof:

```
$ codesign --force --deep --sign - "$APP"
.../ephemeral.app: replacing existing signature
$ codesign --verify --verbose=2 "$APP"
.../ephemeral.app: valid on disk
.../ephemeral.app: satisfies its Designated Requirement
sign_exit=0, verify_exit=0

$ codesign -dv "$APP"
Executable=.../ephemeral.app/Contents/MacOS/ephemeral
Identifier=com.ephemeral.shell
Format=app bundle with Mach-O thin (arm64)
CodeDirectory v=20400 size=300 flags=0x2(adhoc) hashes=3+3 location=embedded
Signature=adhoc
```

## 5. ACCEPT: fuse read on the packaged binary

Read through the wrapper's own reader, which works, on the PACKAGED app:

```
$ sh scripts/fuses.sh read --app "$APP"
Analyzing app: ephemeral.app
Fuse Version: v1
  RunAsNode is Disabled
  EnableCookieEncryption is Disabled
  EnableNodeOptionsEnvironmentVariable is Disabled
  EnableNodeCliInspectArguments is Disabled
  EnableEmbeddedAsarIntegrityValidation is Enabled
  OnlyLoadAppFromAsar is Enabled
  LoadBrowserProcessSpecificV8Snapshot is Disabled
  GrantFileProtocolExtraPrivileges is Disabled
  WasmTrapHandlers is Enabled
read_exit=0
```

All three required fuses are Disabled on the packaged binary:
RunAsNode, EnableNodeOptionsEnvironmentVariable, EnableNodeCliInspectArguments.

## 6. ACCEPT: build-gate PASSES where it refused the stock framework

Final copy lives in the project's gitignored build dir. `.gitignore` line 1 is
`.agent-runs/`, so nothing here is committed:

```
$ P=/Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL
$ DEST="$P/.agent-runs/w26-lane2-release-shape/artifacts"
$ mkdir -p "$DEST"
$ ditto "$APP" "$DEST/ephemeral.app"
$ du -sh "$DEST/ephemeral.app"
252M    $DEST/ephemeral.app
$ codesign --verify --verbose=1 "$DEST/ephemeral.app"
.../ephemeral.app: valid on disk
.../ephemeral.app: satisfies its Designated Requirement
```

Gate on the packaged app:

```
$ H=2092e0e9e8e3418ba167e22b99623094e0f5d05ea876014874be1e3c4b53b87b
$ EPHEMERAL_BUILD_HASH=$H sh scripts/build-gate.sh --app "$DEST/ephemeral.app"
== 1. build hash shape
build hash: 2092e0e9e8e3418ba167e22b99623094e0f5d05ea876014874be1e3c4b53b87b
== 2. fuse table
runAsNode, nodeOptions and nodeCliInspect are required off and are off in fuses.json
table ok
== 3. core pin
core:    /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/03-build/output/wrapper/scripts/../../ephemeral-chat-v2.html
bytes:   169810
sha256:  2092e0e9e8e3418ba167e22b99623094e0f5d05ea876014874be1e3c4b53b87b
in code: 2092e0e9e8e3418ba167e22b99623094e0f5d05ea876014874be1e3c4b53b87b
pin matches
== 4. fuse read on the shipped binary
Analyzing app: ephemeral.app
Fuse Version: v1
  RunAsNode is Disabled
  EnableCookieEncryption is Disabled
  EnableNodeOptionsEnvironmentVariable is Disabled
  EnableNodeCliInspectArguments is Disabled
  EnableEmbeddedAsarIntegrityValidation is Enabled
  OnlyLoadAppFromAsar is Enabled
  LoadBrowserProcessSpecificV8Snapshot is Disabled
  GrantFileProtocolExtraPrivileges is Disabled
  WasmTrapHandlers is Enabled
all three node entry point fuses are Disabled on the shipped binary

RESULT: PASS
gate_exit=0
```

Same command against the stock framework, the negative control:

```
$ EPHEMERAL_BUILD_HASH=$H sh scripts/build-gate.sh --app /Users/marcelspatz/.hermes/cache/scratch/w5-electron/node_modules/electron/dist/Electron.app
== 1. build hash shape
build hash: 2092e0e9e8e3418ba167e22b99623094e0f5d05ea876014874be1e3c4b53b87b
== 2. fuse table
runAsNode, nodeOptions and nodeCliInspect are required off and are off in fuses.json
table ok
== 3. core pin
core:    /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/03-build/output/wrapper/scripts/../../ephemeral-chat-v2.html
bytes:   169810
sha256:  2092e0e9e8e3418ba167e22b99623094e0f5d05ea876014874be1e3c4b53b87b
in code: 2092e0e9e8e3418ba167e22b99623094e0f5d05ea876014874be1e3c4b53b87b
pin matches
== 4. fuse read on the shipped binary
Analyzing app: Electron.app
Fuse Version: v1
  RunAsNode is Enabled
  EnableCookieEncryption is Disabled
  EnableNodeOptionsEnvironmentVariable is Enabled
  EnableNodeCliInspectArguments is Enabled
  EnableEmbeddedAsarIntegrityValidation is Disabled
  OnlyLoadAppFromAsar is Disabled
  LoadBrowserProcessSpecificV8Snapshot is Disabled
  GrantFileProtocolExtraPrivileges is Enabled
  WasmTrapHandlers is Enabled
REFUSED: RunAsNode is not Disabled on /Users/marcelspatz/.hermes/cache/scratch/w5-electron/node_modules/electron/dist/Electron.app. This binary cannot ship.
stock_gate_exit=1
```

The gate distinguishes the two binaries on the fused bytes alone.

## 7. ACCEPT: hash-artifacts includes the app bundle

```
$ sh scripts/hash-artifacts.sh "$DEST"
wrote /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/.agent-runs/w26-lane2-release-shape/artifacts/SHA256SUMS

$ wc -l "$DEST/SHA256SUMS"
     266 $DEST/SHA256SUMS

$ grep -c '^.*  ephemeral\.app/' "$DEST/SHA256SUMS"
266

$ grep -E 'Contents/MacOS/ephemeral$|Contents/Resources/app\.asar$|Contents/Info\.plist$' "$DEST/SHA256SUMS"
9088f571731bffd100231a6762c6e21877a13d70fcd33e818afabd56eead6e36  ephemeral.app/Contents/Info.plist
20b714892f525e28da961e2d5cb5134b34fdb1b2c26ddfe569b9de85979bb7b9  ephemeral.app/Contents/MacOS/ephemeral
1f2c18a3fd8316d17afc5d6dd9141dda16bb959abbb594305a136a789a89c379  ephemeral.app/Contents/Resources/app.asar
```

Every regular file in the bundle is covered, 266 of 266. Symlinks are skipped by the
script by design and their targets are listed. Reproducible:

```
$ shasum -a 256 "$DEST/SHA256SUMS"
85d8287837086eb2da5bb683b0046e27aaf652f65889ade379d60c36131e036b  $DEST/SHA256SUMS
$ sh scripts/hash-artifacts.sh "$DEST" >/dev/null
$ shasum -a 256 "$DEST/SHA256SUMS"
85d8287837086eb2da5bb683b0046e27aaf652f65889ade379d60c36131e036b  $DEST/SHA256SUMS
```

## 8. ACCEPT: e2e-core-load against the PACKAGED app

```
$ ELECTRON_BIN="$DEST/ephemeral.app/Contents/MacOS/ephemeral" sh scripts/e2e-core-load.sh
ephemeral-e2e: served=169810 bytes electron=45.5.0 {"href":"app://core/index.html","title":"Ephemeral chat","screen":"S0","elements":112,"pageBytes":169879,"shell":"object","badge":"ok"}

RESULT: PASS, app://core served 169810 bytes from the pinned core and the page booted to S0
e2e_exit=0
```

The served byte count equals the pinned core, 169810, so the bytes came from the asar
copy that was verified against the compiled-in hash at startup. The document URL is
`app://core/index.html`, the page booted to S0, the preload bridge is an object, and the
IPC badge round trip was accepted by the sender check.

The script stages files in a temp dir and passes that path as argv[1]. A packaged
Electron binary ignores argv, so the load came from `Contents/Resources/app.asar`, not
the stage. Direct run with a nonexistent argument proves it:

```
$ EPHEMERAL_BUILD_HASH=$H EPHEMERAL_E2E=1 "$DEST/ephemeral.app/Contents/MacOS/ephemeral" /nonexistent/stage/app
ephemeral-e2e: served=169810 bytes electron=45.5.0 {"href":"app://core/index.html","title":"Ephemeral chat","screen":"S0","elements":112,"pageBytes":169879,"shell":"object","badge":"ok"}
```

## 9. Behavioral accept: ELECTRON_RUN_AS_NODE is dead

The read proves the fuse bytes. This proves the behavior. Same environment for both
binaries:

```
$ python3 - <<'PY'
import os, subprocess
H = "2092e0e9e8e3418ba167e22b99623094e0f5d05ea876014874be1e3c4b53b87b"
app = ".../artifacts/ephemeral.app/Contents/MacOS/ephemeral"
stock = ".../electron/dist/Electron.app/Contents/MacOS/Electron"
env = dict(os.environ, ELECTRON_RUN_AS_NODE="1", EPHEMERAL_BUILD_HASH=H)
for label, binary in (("packaged", app), ("stock", stock)):
    p = subprocess.Popen([binary, "-e", "console.log('NODE_ENTRY_EXECUTED')"],
                         env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        out, err = p.communicate(timeout=10)
        timed_out = False
    except subprocess.TimeoutExpired:
        p.kill(); out, err = p.communicate(); timed_out = True
    print("== %s ==" % label)
    print("exit=%s timed_out=%s" % (p.returncode, timed_out))
    print("stdout=%r" % out.strip()[:300])
    print("stderr=%r" % err.strip()[:300])
    print("node_entry_executed=%s" % ("NODE_ENTRY_EXECUTED" in out))
PY
== packaged ==
exit=-9 timed_out=True
stdout=''
stderr=''
node_entry_executed=False
== stock ==
exit=0 timed_out=False
stdout='NODE_ENTRY_EXECUTED'
stderr=''
node_entry_executed=True
```

The packaged binary ignored `ELECTRON_RUN_AS_NODE` and started the app, which loaded the
core and stayed up until the harness killed it. The stock binary ran the node expression
and exited 0. This is the F-ENV-3 path closed on the shipped shape.

## 10. Named limits and defects, with disposition

| ID | Finding | Evidence | Disposition |
|---|---|---|---|
| REL-L1 | `scripts/fuses.sh write` cannot flip any fuse. It passes lowerCamel names from `fuses.json`; `@electron/fuses` 2.1.3 requires the enum names. | Section 4, `Invalid fuse name runAsNode`, exit 1 | Carried. One block patch in the flag emitter given in section 4. Proven working from a scratch copy. Wrapper lane fixes it before the next build; no project file was edited in this lane. |
| REL-L2 | `loadBrowserProcessSpecificV8Snapshot: true` cannot be applied to the stock Electron 45.5.0 framework. The dist has no `browser_v8_context_snapshot.bin`; the packaged app aborted with `FATAL:gin/v8_initializer.cc:664 Error loading V8 startup snapshot file`. | Section 4a | Carried. Fuse left at the framework default, off, on this shape. `fuses.json` should set the row false until a framework build produces the browser snapshot, or the build must supply one. The three required-off fuses are unaffected. |
| REL-L3 | A fuse write invalidates the code signature. Without re-signing, macOS kills the binary with `Killed: 9`. `--no-osx-sign` also leaves the stock Electron outer signature, which does not describe the modified bundle. | Section 4b | Carried. Release order is package, fuse, codesign. This proof uses ad-hoc signing; a shippable artifact still needs a Developer ID signature and notarization, which is outside this lane. |
| REL-L4 | The artifact is ad-hoc signed and 252 MB, and no dmg was produced. | Section 4b, section 6 | Not a defect for shape proof. Distribution packaging is a later release card. |
| F-ENV-3 | A stock framework lets `ELECTRON_RUN_AS_NODE`, `NODE_OPTIONS` and `--inspect` reach node code. | Section 9 | Closed on this shape: all three fuses Disabled, behavior proven. |

Packaging tool availability: none blocked. `@electron/packager` 20.3.0 installed from
the registry, and the Electron zip came from the existing host cache, so the package
step needed no framework download.

## 11. Artifact locations

```
packaged app   /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/.agent-runs/w26-lane2-release-shape/artifacts/ephemeral.app
hash list      /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/.agent-runs/w26-lane2-release-shape/artifacts/SHA256SUMS
build scratch  /Users/marcelspatz/.hermes/cache/scratch/w26-release-shape
packaging tools /Users/marcelspatz/.hermes/cache/scratch/w26-release-shape/tools/node_modules
```

`.agent-runs/` is gitignored by the project. Nothing in this lane was written to a
tracked path except this proof file.

## 12. Self-check

File is ASCII and has no em or en dash bytes:

```
$ python3 - <<'PY'
data = open('/Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/05-verify/output/02-release-shape-proof.md','rb').read()
bad = [b for b in (b'\xe2\x80\x94', b'\xe2\x80\x93') if b in data]
print('non_ascii_bytes:', sum(1 for b in data if b > 127))
print('em_or_en_dash_sequences:', len(bad))
print('ascii_only:', all(b < 128 for b in data))
PY
non_ascii_bytes: 0
em_or_en_dash_sequences: 0
ascii_only: True

$ LC_ALL=C grep -c "$(printf '\342\200\224')\|$(printf '\342\200\223')" 05-verify/output/02-release-shape-proof.md
0
```

The dash count is 0 under `sh` and under `bash`. The final grep ran from the project
root; every other block ran from the wrapper directory unless it shows a `cd`.

Commands were run from
`/Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/03-build/output/wrapper`
unless the block shows a `cd`. No git command was run. The project tree files named in
section 1 were read and copied, never modified.
