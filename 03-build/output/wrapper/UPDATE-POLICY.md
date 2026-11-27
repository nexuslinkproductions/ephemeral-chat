# Update policy, BC-W8

V2 has no updater. This file is the policy a release reviewer checks, and the text the
download page and the About panel are allowed to claim.

## The rule

- The app performs no update check, no version ping and no notification, at any interval,
  on any trigger. There is no code path in the wrapper that opens a socket for updates.
- A download may happen only by the user's own action in a browser. The app never downloads
  an update, and it may not install one. The one download sink in the shell is the received
  file export: fixed type allowlist, fixed app owned directory, never a network update.
- Replacement is manual and hash verified. Steps 1 to 4 in blueprint 6.1 are the protocol:
  publish the SHA-256 of every artifact in two independent channels, publish a detached
  minisign or cosign signature over the hash list, give the verify command per platform, and
  show both the build hash and the core hash in About so the comparison has both sides.
- `scripts/verify-artifacts.sh` is the verifier. It shares no code with the downloader, does
  no network access, verifies the detached signature first and refuses to check hashes if the
  signature fails. `scripts/selfcheck.sh` section 12 asserts that property.

## Enforced by

| Check | Command | Failure it catches |
|---|---|---|
| No updater symbol | `scripts/selfcheck.sh` section 11 | `autoUpdater`, `setFeedURL` or `checkForUpdates` reintroduced |
| No relay or update host in the default tree | same | a network endpoint shipped inside the artifact |
| Signature first, then hashes | `scripts/verify-artifacts.sh` | a mirror serving a matching bad hash |
| Manual replacement only | review of the release checklist | a background client with standing write access to the app directory |

## What this policy does not do

- It does not tell the user a new version exists. That is deliberate: a version check is a
  network request that tells whoever answers that this person runs this app.
- It cannot refuse rollback. V2 has no version counter and no signed metadata, so an older
  signed artifact whose own hash and signature verify is accepted. That is residual row 25.
  The compensating control is the build date in About with a warning past 90 days.
- It does not cover Linux at the same strength as macOS and Windows. Layer 2 is absent on
  Linux, so the published hash and the package manager are the root (residual row 19).

## Release gates named here, owned by name

BC-W9 macOS signing and notarization, BC-W10 Windows Authenticode and loader hygiene,
BC-W11 Linux AppImage signature and loader environment, BC-W12 Arch and Omarchy packaging,
BC-W13 crash reporting and cache clearing. Each is a release step with a command and a
transcript, not a promise. They are not implemented in this EXEC-ONLY tree.
