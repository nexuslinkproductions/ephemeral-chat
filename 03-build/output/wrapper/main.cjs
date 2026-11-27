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
// The all zero placeholder fails closed, so a shell built before the core serves nothing.
const CORE_SHA256 = '6c8c1283047f6ce7d3b926e6fd190d3c46b345926aa0142e02827cf2dc02558d';
const UNPINNED = '0'.repeat(64);

const BUILD_DATE = '2026-11-27';
const BUILD_HASH = process.env.EPHEMERAL_BUILD_HASH || 'unset-local-build';

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
let killing = false;
let ipcRejections = 0;

// BC-W14, TB-W1: no debugger port in release. Refuse to start instead of opening one.
for (const flag of ['remote-debugging-port', 'remote-debugging-pipe', 'inspect', 'inspect-brk']) {
  if (app.commandLine.hasSwitch(flag)) {
    process.stderr.write('ephemeral: refusing to start with --' + flag + '\n');
    process.exit(1);
  }
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

  session.fromPartition('core').setSpellCheckerEnabled(false);
  protocol.handle('app', (request) => serveCore(request, core));

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

  app.setAboutPanelOptions({
    applicationName: 'ephemeral',
    applicationVersion: app.getVersion(),
    version: process.versions.electron,
    credits: 'Core SHA-256: ' + CORE_SHA256 + '\nBuild hash: ' + BUILD_HASH + '\nBuild date: ' + BUILD_DATE
  });
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

// BC-W4: nothing but the pinned core is ever served, and the header cannot be dropped by
// editing the file, which the meta tag can.
function serveCore(request, core) {
  let url;
  try {
    url = new URL(request.url);
  } catch (error) {
    return new Response('bad request', { status: 400 });
  }
  if (url.origin !== CORE_ORIGIN || url.pathname !== '/index.html') {
    return new Response('not found', { status: 404 });
  }
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
function hardenContents(event, contents) {
  contents.on('will-navigate', (navEvent) => navEvent.preventDefault());
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
function assertSender(event) {
  let origin = null;
  let senderId = null;
  try {
    origin = event.senderFrame ? event.senderFrame.origin : null;
    senderId = event.sender.id;
  } catch (error) {
    origin = null;
  }
  if (origin !== CORE_ORIGIN || !win || senderId !== win.webContents.id) {
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
    win.webContents.send('shell:command', 'wipe');
    setTimeout(hardKill, 300);
    return;
  }
  hardKill();
}

function hardKill() {
  const appSession = session.fromPartition('core');
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
    clipboard.clear();
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
    'Build hash: ' + BUILD_HASH,
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
