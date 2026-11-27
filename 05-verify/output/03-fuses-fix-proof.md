# Fuses fix proof, REL-L1 closed in the project tree

LANE: release engineering
RUN: w28-ephemeral-fuses-fix-20261127
DATE: 2026-11-27
HOST: macOS 26.4.1, arm64, node v22.23.2
STATUS: PASS. REL-L1 fixed in `03-build/output/wrapper/scripts/fuses.sh`, proven against the
packaged app at `.agent-runs/w26-lane2-release-shape/artifacts/ephemeral.app`. REL-L2 carried,
never enabled. No git command was run. Tools stayed in scratch.

## 1. Defect and patch

`scripts/fuses.sh` built its flags from the lowerCamel keys in `fuses.json` (`runAsNode=off`),
and `@electron/fuses` 2.1.3 rejects those with `Invalid fuse name runAsNode`, exit 1. The write
path never worked. The read path was unaffected.

Patch: one block in the flag emitter. It now carries the tool's nine enum names and exits 1 on
any unmapped key instead of passing a name the tool rejects.

```
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
```

Emitter output, and the fail-closed path on a scratch config carrying a bogus key:

```
$ sh -n scripts/fuses.sh && echo syntax_ok
syntax_ok
$ sh scripts/fuses.sh flags
RunAsNode=off EnableNodeOptionsEnvironmentVariable=off EnableNodeCliInspectArguments=off OnlyLoadAppFromAsar=on EnableEmbeddedAsarIntegrityValidation=on GrantFileProtocolExtraPrivileges=off LoadBrowserProcessSpecificV8Snapshot=on EnableCookieEncryption=off WasmTrapHandlers=on
flags_exit=0
$ sh "$T/scripts/fuses.sh" flags            # scratch config with an added bogusFuse row
unmapped fuse name(s): bogusFuse
bad_flags_exit=1
```

## 2. ACCEPT: read on the packaged app

```
$ cd /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/03-build/output/wrapper
$ APP=/Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/.agent-runs/w26-lane2-release-shape/artifacts/ephemeral.app
$ time sh scripts/fuses.sh read --app "$APP"
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

real    0m1.353s
read_exit=0
```

The three required fuses read Disabled. The project release gate agrees:

```
$ EPHEMERAL_BUILD_HASH=2092e0e9e8e3418ba167e22b99623094e0f5d05ea876014874be1e3c4b53b87b sh scripts/build-gate.sh --app "$APP"
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

## 3. ACCEPT: the repaired write path on copies

Two scratch copies, made with `ditto` from the artifact. The artifact itself was only read.

```
$ W=/Users/marcelspatz/.hermes/cache/scratch/w28-fuses
$ ditto "$APP" "$W/copy1.app" ; du -sh "$W/copy1.app"
252M    .../w28-fuses/copy1.app
```

Full table write through the repaired project script, on copy1:

```
$ time sh scripts/fuses.sh write --app "$W/copy1.app"
Analyzing app: copy1.app
Fuse Version: v1
  RunAsNode is already Disabled and will not be changed
  EnableNodeOptionsEnvironmentVariable is already Disabled and will not be changed
  EnableNodeCliInspectArguments is already Disabled and will not be changed
  OnlyLoadAppFromAsar is already Enabled and will not be changed
  EnableEmbeddedAsarIntegrityValidation is already Enabled and will not be changed
  GrantFileProtocolExtraPrivileges is already Disabled and will not be changed
  LoadBrowserProcessSpecificV8Snapshot is Disabled and will become Enabled
  EnableCookieEncryption is already Disabled and will not be changed
  WasmTrapHandlers is already Enabled and will not be changed
Writing to app: copy1.app
Fuses written to disk

real    0m0.589s
write_exit=0
```

All nine enum names were accepted, no name error. Read back on copy1:

```
$ sh scripts/fuses.sh read --app "$W/copy1.app"
  RunAsNode is Disabled
  EnableNodeOptionsEnvironmentVariable is Disabled
  EnableNodeCliInspectArguments is Disabled
  LoadBrowserProcessSpecificV8Snapshot is Enabled
```

The one row that changed is the one `fuses.json` asks for and that REL-L2 says cannot be
applied (section 5). The three required fuses stayed Disabled.

That a write actually flips bytes was proven by flipping and restoring a single fuse, because
the copies were already fused off:

```
$ electron-fuses write --app "$W/copy2.app" RunAsNode=on
  RunAsNode is Disabled and will become Enabled
Writing to app: copy2.app
Fuses written to disk
real    0m0.094s

$ sh scripts/fuses.sh read --app "$W/copy2.app" | grep RunAsNode
  RunAsNode is Enabled

$ electron-fuses write --app "$W/copy2.app" RunAsNode=off
  RunAsNode is Enabled and will become Disabled
Fuses written to disk
real    0m0.104s

$ sh scripts/fuses.sh read --app "$W/copy2.app" | grep RunAsNode
  RunAsNode is Disabled
```

## 4. What a write cycle costs, REL-L3 measured

The write target is the nested framework, not the app executable. Hashing all 266 files of a
copy against `SHA256SUMS` before and after one write:

```
$ python3 compare copy2.app against artifacts/SHA256SUMS
checked: 266 listed: 266 changed: 1
CHANGED Contents/Frameworks/Electron Framework.framework/Versions/A/Electron Framework
  was 8886834c9d96569764b00a04277690ab507270bf1cafc13033910767bebd74b7
  now 307d824ea0da7d712c08a65cc80e75ba22225b9b0c00b909d49a371cdd077446
```

`Contents/MacOS/ephemeral` kept the same sha256
(`20b714892f525e28da961e2d5cb5134b34fdb1b2c26ddfe569b9de85979bb7b9`) across the write. So the
stale signature is the framework binary's.

`codesign --verify` on the bundle does not catch that. It still reports valid after a write,
because it does not re-check nested code without `--deep`:

```
$ codesign --verify --verbose=1 "$W/copy1.app"          # after the write
.../copy1.app: valid on disk
.../copy1.app: satisfies its Designated Requirement
verify_exit=0
```

The runtime does catch it. Launch on copy2 after a write and before a re-sign, same command
that printed `NODE_ENTRY_EXECUTED` on the stock binary in the w26 base proof:

```
$ ELECTRON_RUN_AS_NODE=1 copy2.app/Contents/MacOS/ephemeral -e "console.log('NODE_ENTRY_EXECUTED')"
exit=-9 timed_out=False node_entry_executed=False stderr=''
```

`exit=-9` with empty stderr and no timeout is the macOS kill, `Killed: 9`. Re-sign, then the
same shape launches and the smoke passes:

```
$ time codesign --force --deep --sign - "$W/copy2.app"
.../copy2.app: replacing existing signature
real    0m0.346s
sign_exit=0
$ codesign --verify --verbose=2 "$W/copy2.app"
.../copy2.app: valid on disk
.../copy2.app: satisfies its Designated Requirement

$ time ELECTRON_BIN="$W/copy2.app/Contents/MacOS/ephemeral" sh scripts/e2e-core-load.sh
RESULT: PASS, app://core served 169810 bytes from the pinned core and the page booted to S0
real    0m3.345s
```

Cycle cost on this 252 MB bundle, measured:

| Step | Time |
|---|---|
| write, through `fuses.sh` (npx resolve included) | 0.59 s |
| write, direct tool binary | 0.09 to 0.10 s |
| ad-hoc `codesign --force --deep` | 0.35 to 0.54 s |
| `e2e-core-load.sh` smoke against the signed copy | 3.35 s |

A write cycle is under one second of work plus the signature, so it is cheap to run on a copy
and unsafe to skip in a release. Cost is not the constraint; order is. Package, fuse, codesign.

## 5. REL-L2 carried, the snapshot fuse stays off

`fuses.json` still sets `loadBrowserProcessSpecificV8Snapshot: true`, and the repaired script
now emits it, so a full write turns it on. The stock Electron 45.5.0 framework has no
`browser_v8_context_snapshot.bin`, and the copy aborts at launch:

```
$ ELECTRON_BIN="$W/copy1.app/Contents/MacOS/ephemeral" sh scripts/e2e-core-load.sh
... line 48: 51458 Trace/BPT trap: 5  ... e2e: electron exited non zero
[1127/124212.891302:FATAL:gin/v8_initializer.cc:664] Error loading V8 startup snapshot file
```

That is REL-L2, unchanged and not fixed here. The fusion proof on copy2 was made with the row at
its framework default, off, which is the state of the packaged artifact. No lane may enable this
fuse to work around a missing snapshot file. `fuses.json` needs the row false until a framework
build produces the browser snapshot; that edit is outside this lane's write set and is recorded
in `BUILD.md`.

## 6. Self-check

```
$ sh -n 03-build/output/wrapper/scripts/fuses.sh ; echo $?
0
$ sh 03-build/output/wrapper/scripts/fuses.sh flags | tr ' ' '\n' | wc -l
       9
$ LC_ALL=C grep -c "$(printf '\342\200\224')\|$(printf '\342\200\223')" \
    03-build/output/wrapper/scripts/fuses.sh 03-build/output/wrapper/BUILD.md \
    05-verify/output/03-fuses-fix-proof.md
03-build/output/wrapper/scripts/fuses.sh:0
03-build/output/wrapper/BUILD.md:0
05-verify/output/03-fuses-fix-proof.md:0
$ python3 byte scan
scripts/fuses.sh non_ascii_bytes: 0 em_or_en_dash_sequences: 0 ascii_only: True
BUILD.md non_ascii_bytes: 0 em_or_en_dash_sequences: 0 ascii_only: True
03-fuses-fix-proof.md non_ascii_bytes: 0 em_or_en_dash_sequences: 0 ascii_only: True
```

The project self-check still passes with the patched script, and no caller depended on the old
flag spelling: `build-gate.sh` uses only `fuses.sh read`, `selfcheck.sh` only `sh -n`.

```
$ sh scripts/selfcheck.sh 2>&1 | tail -4
RESULT: PASS
real    0m0.632s
selfcheck_exit=0
```

The artifact was not modified by this lane. Both of its key binaries still match the w26
baseline (`SHA256SUMS`):

```
$ shasum -a 256 ephemeral.app/Contents/MacOS/ephemeral \
    "ephemeral.app/Contents/Frameworks/Electron Framework.framework/Versions/A/Electron Framework"
20b714892f525e28da961e2d5cb5134b34fdb1b2c26ddfe569b9de85979bb7b9  .../Contents/MacOS/ephemeral
8886834c9d96569764b00a04277690ab507270bf1cafc13033910767bebd74b7  .../Electron Framework
```

## 7. Files and artifacts

```
edited   /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/03-build/output/wrapper/scripts/fuses.sh
edited   /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/03-build/output/wrapper/BUILD.md
written  /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/05-verify/output/03-fuses-fix-proof.md
copies   /Users/marcelspatz/.hermes/cache/scratch/w28-fuses/copy1.app, copy2.app
artifact /Users/marcelspatz/NEXUS_AI_CENTER/04_PROJECTS/EPHEMERAL/.agent-runs/w26-lane2-release-shape/artifacts/ephemeral.app (read only)
```

`.agent-runs/` is gitignored by the project. `fuses.json` was not edited. REL-L1 is closed.
REL-L2 and REL-L3 stay carried with the measured facts above.
