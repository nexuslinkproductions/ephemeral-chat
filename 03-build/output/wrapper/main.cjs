'use strict';

// EXEC-ONLY shell for the ephemeral chat core.
// Cards: BC-W1 to BC-W5 and BC-W14, plus the UX-09 window host.
// Sources: blueprint v2 sections 6.1, 6.3, 6.4; 11-packaging-executable.md sections 3.2,
// 4.1, 4.2, 6.1, 6.2, 9.2 to 9.4; 13-platform-ux.md sections 3.1 to 3.4.
//
// Order is load bearing: the pin is checked before any window exists, and the verified
// buffer is the only copy this process ever hands out.

const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { app, BrowserWindow, Menu, clipboard, dialog, ipcMain, protocol, session } = require('electron');
const { buildMenu, COMMANDS } = require('./menu.cjs');

const CORE_ORIGIN = 'app://core';
const CORE_URL = CORE_ORIGIN + '/index.html';
const CORE_ENTRY = path.join(__dirname, 'core', 'ephemeral-chat-v2.html');

// BC-W4 layer 3: the 64 hex character SHA-256 of the reviewed core, compiled in.
// Build order rule (11 section 10): hash the core, commit this constant, then build the shell.
// An all zero placeholder fails closed, and so does a stale constant, so a shell built before
// the core, or against a different core, serves nothing.
const CORE_SHA256 = '2092e0e9e8e3418ba167e22b99623094e0f5d05ea876014874be1e3c4b53b87b';
const UNPINNED = '0'.repeat(64);

const BUILD_DATE = '2026-11-27';

// P-09, WB-08: the release hash is a 64 hex character build input. A packaged build refuses
// to start without one. A dev run has one escape hatch, never available in a packaged app,
// and About reports that run as unverified.
const BUILD_HASH_RAW = (process.env.EPHEMERAL_BUILD_HASH || '').trim().toLowerCase();
const BUILD_HASH_OK = /^[0-9a-f]{64}$/.test(BUILD_HASH_RAW);
const BUILD_HASH = BUILD_HASH_OK ? BUILD_HASH_RAW : 'UNVERIFIED';
const ALLOW_UNVERIFIED = process.env.EPHEMERAL_ALLOW_UNVERIFIED === '1' && !app.isPackaged;

// Stricter than the core meta tag at ephemeral-chat-v1.html line 6: frame-ancestors and
// object-src are added, and worker-src plus media-src are present so the Blob Worker and
// in memory playback survive the header (blueprint 6.2, integration constraint).
const CSP = [
  "default-src 'none'",
  "script-src 'unsafe-inline'",
  "style-src 'unsafe-inline'",
  "img-src blob: data:",
  "media-src blob:",
  "worker-src blob:",
  "connect-src 'none'",
  "base-uri 'none'",
  "form-action 'none'",
  "frame-ancestors 'none'",
  "object-src 'none'"
].join('; ');

// BC-W14: DevTools only behind a build flag, and never in a packaged build.
const DEVTOOLS = process.env.EPHEMERAL_DEVTOOLS === '1' && !app.isPackaged;

// Launch scoped profile directory. ponytail: on macOS this is the boot volume for the life
// of the process, add an hdiutil RAM disk if that window matters (11 section 4.2).
const RAM_ROOT = process.platform === 'linux' ? '/dev/shm' : os.tmpdir();
const DATA_DIR = path.join(RAM_ROOT, 'ephemeral-' + process.pid + '-' + crypto.randomBytes(6).toString('hex'));

let win = null;
let coreSession = null;
let killing = false;
let ipcRejections = 0;
let servedBytes = 0;

// Downloads are a user-requested export from the in-memory session, never a page-chosen
// path. The allowlist is the shipped save surface; everything else is refused.
const DOWNLOAD_TYPES = new Set([
  '.pdf', '.txt', '.md', '.csv', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.avif',
  '.mp4', '.webm', '.mp3', '.wav', '.ogg', '.m4a', '.docx', '.xlsx', '.pptx'
]);

// BC-W14, TB-W1: no debugger port in release. Refuse to start instead of opening one.
for (const flag of ['remote-debugging-port', 'remote-debugging-pipe', 'inspect', 'inspect-brk']) {
  if (app.commandLine.hasSwitch(flag)) {
    process.stderr.write('ephemeral: refusing to start with --' + flag + '\n');
    process.exit(1);
  }
}

// P-09: no release hash, no release start. The in-code debug loop above is defense in depth
// only; a fused binary is the control that makes it meaningful.
if (!BUILD_HASH_OK && !ALLOW_UNVERIFIED) {
  process.stderr.write('ephemeral: refusing to start: EPHEMERAL_BUILD_HASH must be 64 hex characters\n');
  process.exit(1);
}

if (!app.requestSingleInstanceLock()) {
  // BC-W14: one instance, one session surface. The second launch exits, the first focuses.
  app.exit(0);
} else {
  main();
}

function main() {
  // BC-W1: sandbox every renderer, called before ready.
  app.enableSandbox();

  // BC-W4: a standard secure scheme with no file privileges. Registered before ready.
  protocol.registerSchemesAsPrivileged([{
    scheme: 'app',
    privileges: {
      standard: true,
      secure: true,
      supportFetchAPI: false,
      corsEnabled: false,
      allowServiceWorkers: false,
      codeCache: false,
      stream: false
    }
  }]);

  // Runtime posture, 11 section 4.1. Switches must be appended before the ready event.
  app.commandLine.appendSwitch('disable-http-cache');
  app.commandLine.appendSwitch('disable-breakpad');
  app.commandLine.appendSwitch('disable-session-crashed-bubble');
  app.commandLine.appendSwitch('disable-features', 'AutofillServerCommunication,Translate');

  fs.mkdirSync(DATA_DIR, { recursive: true });
  app.setPath('userData', DATA_DIR);

  app.on('second-instance', onSecondInstance);
  app.on('web-contents-created', hardenContents);
  app.on('before-quit', onBeforeQuit);
  // The window is only destroyed inside the kill, so a window-all-closed before that is an
  // unplanned teardown and still routes through the full sequence.
  app.on('window-all-closed', () => {
    if (!killing) kill();
  });

  app.whenReady().then(start);
}

function start() {
  const core = readAndVerifyCore();

  // P-01, F-ENV-2: the window lives on the core partition, so the app protocol must be
  // handled by that session. Registering on the default session served nobody, and the
  // old origin compare failed because app://core has an opaque origin in the main process.
  coreSession = session.fromPartition('core');
  coreSession.setSpellCheckerEnabled(false);
  coreSession.protocol.handle('app', (request) => serveCore(request, core));
  coreSession.on('will-download', onDownload);

  ipcMain.handle('shell:wipe', (event) => {
    assertSender(event);
    kill();
    return true;
  });
  ipcMain.handle('shell:badge', (event, on) => {
    assertSender(event);
    if (on !== true && on !== false) throw new Error('badge expects a boolean');
    setBadge(on);
    return true;
  });

  createWindow();

  // P-01 proof hook, release inert: only a run with the variable set takes this path.
  if (process.env.EPHEMERAL_E2E === '1') attachE2EProbe();

  app.setAboutPanelOptions({
    applicationName: 'ephemeral',
    applicationVersion: app.getVersion(),
    version: process.versions.electron,
    credits: 'Core SHA-256: ' + CORE_SHA256 + '\nBuild hash: ' + buildHashLine() + '\nBuild date: ' + BUILD_DATE
  });
}

// P-09: a start without a release hash is explicitly unverified, never silently labeled.
function buildHashLine() {
  return BUILD_HASH_OK ? BUILD_HASH : 'UNVERIFIED (development run, not a release build)';
}

// BC-W4: read the entry once, hash it, compare in constant time, and serve the same buffer.
function readAndVerifyCore() {
  let buffer;
  try {
    buffer = fs.readFileSync(CORE_ENTRY);
  } catch (error) {
    return fatal('Core entry unreadable at ' + CORE_ENTRY + ' (' + error.message + ')');
  }
  if (CORE_SHA256 === UNPINNED) {
    return fatal('Core pin is not set. Hash the core, commit the constant, then build the shell.');
  }
  const expected = Buffer.from(CORE_SHA256, 'hex');
  const actual = crypto.createHash('sha256').update(buffer).digest();
  if (expected.length !== 32 || actual.length !== expected.length || !crypto.timingSafeEqual(actual, expected)) {
    return fatal('Core hash mismatch. Expected ' + CORE_SHA256 + ', got ' + actual.toString('hex') + '.');
  }
  return buffer;
}

// P-01: app://core is a custom standard scheme, so new URL().origin is the string "null"
// in the main process. Compare the parsed scheme, host and path instead. The same predicate
// is used for serving and for the IPC sender check, so one URL rule covers both.
function isCoreUrl(value) {
  let url;
  try {
    url = new URL(String(value || ''));
  } catch (error) {
    return false;
  }
  return url.protocol === 'app:' && url.hostname === 'core' && url.pathname === '/index.html';
}

// BC-W4: nothing but the pinned core is ever served, and the header cannot be dropped by
// editing the file, which the meta tag can.
function serveCore(request, core) {
  if (!isCoreUrl(request.url)) {
    return new Response('not found', { status: 404 });
  }
  servedBytes += core.length;
  return new Response(core, {
    status: 200,
    headers: {
      'content-type': 'text/html; charset=utf-8',
      'content-security-policy': CSP,
      'cache-control': 'no-store',
      'referrer-policy': 'no-referrer'
    }
  });
}

function createWindow() {
  win = new BrowserWindow({
    width: 980,
    height: 720,
    minWidth: 720,
    minHeight: 560,
    resizable: true,
    show: false,
    title: 'ephemeral',
    backgroundColor: '#111111',
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      partition: 'core',
      // BC-W1: every one of these is in the closed position on purpose.
      nodeIntegration: false,
      nodeIntegrationInWorker: false,
      nodeIntegrationInSubFrames: false,
      contextIsolation: true,
      sandbox: true,
      webviewTag: false,
      webSecurity: true,
      allowRunningInsecureContent: false,
      spellcheck: false,
      devTools: DEVTOOLS,
      navigateOnDragDrop: false,
      safeDialogs: true,
      enableWebSQL: false,
      v8CacheOptions: 'none'
    }
  });

  win.once('ready-to-show', () => win.show());
  win.on('close', (event) => {
    if (killing) return;
    // A window close is a kill by construction (13 section 3.3).
    event.preventDefault();
    kill();
  });
  win.on('closed', () => {
    win = null;
  });
  win.loadURL(CORE_URL);

  Menu.setApplicationMenu(buildMenu({
    isDev: DEVTOOLS,
    sendCommand,
    onWipe: kill,
    onAbout: showAbout
  }));
}

// BC-W3: deny navigation, frames, webviews and window creation everywhere, not just on the
// main window. BC-W1: deny every permission, camera and clipboard read included.
// P-13, WB-04: the core evicts its own document with location.replace('about:blank') at the
// end of a session, which is a security action. Allow that one exact URL by predicate and
// keep every other navigation denied.
function isBlankNavigation(url) {
  return url === 'about:blank';
}

function hardenContents(event, contents) {
  contents.on('will-navigate', (navEvent, url) => {
    if (!isBlankNavigation(url)) navEvent.preventDefault();
  });
  contents.on('will-frame-navigate', (navEvent) => navEvent.preventDefault());
  contents.on('will-attach-webview', (webviewEvent) => webviewEvent.preventDefault());
  contents.setWindowOpenHandler(() => ({ action: 'deny' }));
  contents.session.setPermissionRequestHandler((webContents, permission, callback) => callback(false));
  contents.session.setPermissionCheckHandler(() => false);
}

// TB-W1: the second instance payload is hostile input. Cap it, validate its shape, and use
// it for nothing except a focus signal.
function onSecondInstance(event, argv, workingDirectory) {
  if (!Array.isArray(argv) || argv.length > 64) return;
  for (const arg of argv) {
    if (typeof arg !== 'string' || arg.length > 4096) return;
  }
  if (win && !win.isDestroyed()) {
    if (win.isMinimized()) win.restore();
    win.focus();
  }
}

function sendCommand(id) {
  if (!COMMANDS.includes(id)) return;
  if (win && !win.isDestroyed()) win.webContents.send('shell:command', id);
}

// BC-W2: reject any sender that is not the pinned core frame in this window, and count it.
// BC-W2/P-01: check the frame URL with the same app://core predicate the server uses. The
// old frame.origin compare is not stable for a custom standard scheme.
function assertSender(event) {
  let ok = false;
  try {
    ok = !!win &&
      event.sender.id === win.webContents.id &&
      !!event.senderFrame &&
      isCoreUrl(event.senderFrame.url);
  } catch (error) {
    ok = false;
  }
  if (!ok) {
    ipcRejections += 1;
    process.stderr.write('ephemeral: ipc rejected (' + ipcRejections + ')\n');
    throw new Error('ipc rejected');
  }
}

// UX-09 badge: a dot, never a count, and no OS notification anywhere.
function setBadge(on) {
  if (process.platform === 'darwin' && app.dock) app.dock.setBadge(on === true ? '\u2022' : '');
}

// Shell kill, 11 section 9.4: 300 ms for the renderer to close DTLS and send panic, then
// the process takes the rest. app.exit skips will-quit, so the directory is deleted here.
function kill() {
  if (killing) return;
  killing = true;
  if (win && !win.isDestroyed()) {
    sendCommand('wipe');
    setTimeout(hardKill, 300);
    return;
  }
  hardKill();
}

function hardKill() {
  const appSession = coreSession || session.fromPartition('core');
  // P-13, WB-03: one clipboard policy. The core clears only when the document has focus
  // (artifact:1818); the shell clears the OS clipboard only when its window is focused, so a
  // background wipe never eats another application's clipboard.
  const focused = !!(win && !win.isDestroyed() && win.isFocused());
  try {
    if (win && !win.isDestroyed()) win.destroy();
  } catch (error) {
    // already gone
  }
  try {
    appSession.clearStorageData();
  } catch (error) {
    // best effort
  }
  try {
    appSession.clearCache();
  } catch (error) {
    // best effort
  }
  try {
    if (focused) clipboard.clear();
  } catch (error) {
    // best effort
  }
  try {
    fs.rmSync(DATA_DIR, { recursive: true, force: true });
  } catch (error) {
    // best effort, and not a secure erase
  }
  app.exit(0);
}

function onBeforeQuit(event) {
  if (killing) return;
  event.preventDefault();
  kill();
}

// P-12, WB-06: every download goes through this one sink. The page proposes a name; the
// shell decides the type, the directory and the final path. A name never chooses a path.
function safeDownloadName(raw) {
  const base = path.basename(String(raw || ''))
    .replace(/[^A-Za-z0-9._ -]/g, '_')
    .replace(/^\.+/, '')
    .trim();
  return (base || 'download').slice(0, 120);
}

function uniqueDownloadPath(dir, name) {
  const ext = path.extname(name);
  const stem = name.slice(0, name.length - ext.length);
  let target = path.join(dir, name);
  let n = 1;
  while (fs.existsSync(target)) {
    target = path.join(dir, stem + '-' + n + ext);
    n += 1;
  }
  return target;
}

function onDownload(event, item) {
  const name = safeDownloadName(item.getFilename());
  const ext = path.extname(name).toLowerCase();
  if (!DOWNLOAD_TYPES.has(ext)) {
    process.stderr.write('ephemeral: download refused, type not allowed: ' + (ext || 'none') + '\n');
    item.cancel();
    return;
  }
  const dir = path.join(app.getPath('downloads'), 'ephemeral');
  fs.mkdirSync(dir, { recursive: true });
  item.setSavePath(uniqueDownloadPath(dir, name));
}

// P-01 live proof. Reports the bytes the app:// handler served, the loaded URL, the boot
// screen and one bridge round trip, then exits. A normal run never sets EPHEMERAL_E2E.
function attachE2EProbe() {
  win.webContents.once('did-fail-load', (event, code, description) => {
    process.stderr.write('ephemeral-e2e: FAIL load ' + code + ' ' + description + '\n');
    app.exit(1);
  });
  win.webContents.once('did-finish-load', async () => {
    try {
      const report = await win.webContents.executeJavaScript(
        '(async () => {' +
        '  const out = {' +
        '    href: location.href,' +
        '    title: document.title,' +
        '    screen: document.body.dataset.screen || "",' +
        '    elements: document.querySelectorAll("*").length,' +
        '    pageBytes: document.documentElement.outerHTML.length,' +
        '    shell: typeof window.shell' +
        '  };' +
        '  try { await window.shell.badge(true); out.badge = "ok"; }' +
        '  catch (error) { out.badge = "fail:" + (error && error.message); }' +
        '  return JSON.stringify(out);' +
        '})()'
      );
      process.stderr.write('ephemeral-e2e: served=' + servedBytes + ' bytes electron=' +
        process.versions.electron + ' ' + report + '\n');
      app.exit(0);
    } catch (error) {
      process.stderr.write('ephemeral-e2e: FAIL ' + (error && error.message) + '\n');
      app.exit(1);
    }
  });
}

function buildAgeDays() {
  const built = Date.parse(BUILD_DATE + 'T00:00:00Z');
  if (Number.isNaN(built)) return 0;
  return Math.max(0, Math.floor((Date.now() - built) / 86400000));
}

// BC-W6: Electron version, build hash and core hash in About, with the verify command.
function showAbout() {
  const age = buildAgeDays();
  const lines = [
    'Electron ' + process.versions.electron + ' (Chromium ' + process.versions.chrome + ')',
    'Build hash: ' + buildHashLine(),
    'Core SHA-256: ' + CORE_SHA256,
    'Build date: ' + BUILD_DATE + ' (' + age + ' days old)'
  ];
  if (age > 90) lines.push('WARNING: this build is more than 90 days old. Get a new one.');
  lines.push(
    '',
    'Verify on macOS: shasum -a 256 <artifact>',
    'Verify on Linux: sha256sum <artifact>',
    'Verify on Windows: certutil -hashfile <file> SHA256',
    '',
    'The hash proves the file is the reviewed one. It does not prove who built the shell.',
    'No history, no cookies, no transcript between launches.',
    'The operating system can still write: swap, crash reports, the package manager database.'
  );
  dialog.showMessageBox({
    type: 'info',
    title: 'About ephemeral',
    message: 'ephemeral ' + app.getVersion(),
    detail: lines.join('\n')
  });
}

function fatal(message) {
  process.stderr.write('ephemeral: ' + message + '\n');
  try {
    dialog.showErrorBox('ephemeral', message);
  } catch (error) {
    // headless, stderr is the record
  }
  app.exit(1);
  throw new Error(message);
}
