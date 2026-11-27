#!/usr/bin/env python3
"""Gate harness for the ephemeral chat V2 artifact.

One command per card. Exit 0 PASS, exit 1 FAIL, exit 2 the case could not run.
Python 3 stdlib only. Behavioral cases drive the installed Chrome over CDP;
structure cases are static scans of the artifact.

Usage:
  python3 gate.py list
  python3 gate.py selftest
  python3 gate.py <case> [--app PATH] [--relay-host turn:127.0.0.1:5349]
"""

import base64
import binascii
import gzip
import hashlib
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.dirname(HERE)
DEFAULT_APP = os.path.join(OUTPUT, 'ephemeral-chat-v2.html')
EVIDENCE = os.path.join(OUTPUT, 'evidence')
FIXTURES = os.path.join(HERE, 'fixtures')

CHROME_CANDIDATES = [
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    '/usr/bin/google-chrome',
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
]


class Fail(Exception):
    """A gate assertion failed. Exit 1."""


class CannotRun(Exception):
    """The case could not run. Exit 2, blocks the card."""


def expect(cond, msg):
    if not cond:
        raise Fail(msg)


def expect_eq(got, want, what):
    if got != want:
        raise Fail('%s: got %r, want %r' % (what, got, want))


def find_chrome():
    for p in CHROME_CANDIDATES:
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    raise CannotRun('no Chrome or Chromium binary found')


# ---------------------------------------------------------------- websocket

class WS(object):
    """Minimal RFC 6455 client. Text frames, fragmented reads, ping reply."""

    def __init__(self, url, timeout=60):
        u = urllib.parse.urlsplit(url)
        host = u.hostname
        port = u.port or 80
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.sock.settimeout(timeout)
        self.buf = b''
        key = base64.b64encode(os.urandom(16)).decode('ascii')
        path = u.path or '/'
        if u.query:
            path += '?' + u.query
        req = ('GET %s HTTP/1.1\r\nHost: %s:%d\r\nUpgrade: websocket\r\n'
               'Connection: Upgrade\r\nSec-WebSocket-Key: %s\r\n'
               'Sec-WebSocket-Version: 13\r\n\r\n') % (path, host, port, key)
        self.sock.sendall(req.encode('ascii'))
        while b'\r\n\r\n' not in self.buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise CannotRun('devtools websocket closed during handshake')
            self.buf += chunk
        head, self.buf = self.buf.split(b'\r\n\r\n', 1)
        if b'101' not in head.split(b'\r\n')[0]:
            raise CannotRun('devtools websocket handshake refused')
        self.acc = b''

    def _read_exact(self, n):
        while len(self.buf) < n:
            chunk = self.sock.recv(max(4096, n - len(self.buf)))
            if not chunk:
                raise CannotRun('devtools websocket closed')
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def send_text(self, text):
        data = text.encode('utf-8')
        mask = os.urandom(4)
        n = len(data)
        head = bytearray([0x81])
        if n < 126:
            head.append(0x80 | n)
        elif n < 65536:
            head.append(0x80 | 126)
            head += n.to_bytes(2, 'big')
        else:
            head.append(0x80 | 127)
            head += n.to_bytes(8, 'big')
        head += mask
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        self.sock.sendall(bytes(head) + masked)

    def send_control(self, opcode, payload=b''):
        mask = os.urandom(4)
        head = bytearray([0x80 | opcode, 0x80 | len(payload)]) + mask
        self.sock.sendall(bytes(head) + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))

    def recv_text(self):
        while True:
            b1, b2 = self._read_exact(2)
            fin = b1 & 0x80
            opcode = b1 & 0x0F
            n = b2 & 0x7F
            masked = b2 & 0x80
            if n == 126:
                n = int.from_bytes(self._read_exact(2), 'big')
            elif n == 127:
                n = int.from_bytes(self._read_exact(8), 'big')
            if masked:
                key = self._read_exact(4)
                raw = self._read_exact(n)
                payload = bytes(b ^ key[i % 4] for i, b in enumerate(raw))
            else:
                payload = self._read_exact(n)
            if opcode == 0x9:
                self.send_control(0xA, payload)
                continue
            if opcode == 0xA:
                continue
            if opcode == 0x8:
                raise CannotRun('devtools websocket closed by peer')
            self.acc += payload
            if fin:
                text, self.acc = self.acc, b''
                return text.decode('utf-8', 'replace')

    def close(self):
        try:
            self.send_control(0x8)
        except Exception:
            pass
        try:
            self.sock.close()
        except Exception:
            pass


# ------------------------------------------------------------------- chrome

def _wait_devtools(profile_dir, timeout=20):
    path = os.path.join(profile_dir, 'DevToolsActivePort')
    end = time.time() + timeout
    while time.time() < end:
        if os.path.isfile(path):
            with open(path) as fh:
                lines = fh.read().split()
            if len(lines) >= 2 and lines[0].isdigit():
                return int(lines[0])
        time.sleep(0.05)
    raise CannotRun('Chrome did not open a devtools port')


class Browser(object):
    def __init__(self):
        self.profile = tempfile.mkdtemp(prefix='gate-chrome-')
        exe = find_chrome()
        args = [
            exe,
            '--headless=new',
            '--remote-debugging-port=0',
            '--user-data-dir=' + self.profile,
            '--no-first-run',
            '--no-default-browser-check',
            '--disable-gpu',
            '--disable-extensions',
            '--disable-background-timer-throttling',
            '--disable-renderer-backgrounding',
            '--disable-backgrounding-occluded-windows',
            '--disable-features=WebRtcHideLocalIpsWithMdns',
            '--allow-loopback-in-peer-connection',
            'about:blank',
        ]
        self.proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        port = _wait_devtools(self.profile)
        url = None
        end = time.time() + 10
        while time.time() < end:
            try:
                with urllib.request.urlopen('http://127.0.0.1:%d/json/version' % port, timeout=2) as r:
                    url = json.loads(r.read().decode('utf-8')).get('webSocketDebuggerUrl')
                if url:
                    break
            except Exception:
                time.sleep(0.1)
        if not url:
            raise CannotRun('devtools endpoint did not answer')
        self.ws = WS(url)
        self.n = 0
        self.dialog_n = 900000
        self.auto_dialog = False
        self.dialog_accept = True
        self.events = []

    def cmd(self, method, params=None, session=None, timeout=45):
        self.n += 1
        msg = {'id': self.n, 'method': method, 'params': params or {}}
        if session:
            msg['sessionId'] = session
        self.ws.send_text(json.dumps(msg))
        while True:
            data = json.loads(self.ws.recv_text())
            if 'id' not in data:
                if data.get('method') == 'Page.javascriptDialogOpening' and self.auto_dialog:
                    # A native confirm blocks the renderer, so accept it out of band.
                    self.dialog_n += 1
                    reply = {'id': self.dialog_n, 'method': 'Page.handleJavaScriptDialog',
                             'params': {'accept': bool(self.dialog_accept), 'promptText': ''}}
                    if data.get('sessionId'):
                        reply['sessionId'] = data['sessionId']
                    self.ws.send_text(json.dumps(reply))
                self.events.append(data.get('method'))
                if len(self.events) > 200:
                    self.events = self.events[-200:]
                continue
            if data['id'] != self.n:
                continue
            if 'error' in data:
                raise CannotRun('%s: %s' % (method, json.dumps(data['error'])[:300]))
            return data.get('result', {})

    def context(self):
        return self.cmd('Target.createBrowserContext')['browserContextId']

    def page(self, ctx, url='about:blank'):
        target = self.cmd('Target.createTarget', {'url': url, 'browserContextId': ctx})['targetId']
        sid = self.cmd('Target.attachToTarget', {'targetId': target, 'flatten': True})['sessionId']
        self.cmd('Page.enable', session=sid)
        self.cmd('Runtime.enable', session=sid)
        return Page(self, sid, target)

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass
        try:
            self.proc.terminate()
            self.proc.wait(timeout=5)
        except Exception:
            try:
                self.proc.kill()
            except Exception:
                pass
        shutil.rmtree(self.profile, ignore_errors=True)


class Page(object):
    def __init__(self, browser, sid, target):
        self.b = browser
        self.sid = sid
        self.target = target
        browser.cmd('DOM.enable', session=sid)

    def set_file(self, selector, path):
        doc = self.b.cmd('DOM.getDocument', {'depth': 1}, session=self.sid)
        node = self.b.cmd('DOM.querySelector', {'nodeId': doc['root']['nodeId'], 'selector': selector}, session=self.sid)
        if not node.get('nodeId'):
            raise Fail('file input not found: ' + selector)
        self.b.cmd('DOM.setFileInputFiles', {'files': [os.path.abspath(path)], 'nodeId': node['nodeId']},
                   session=self.sid)

    def init(self, source):
        self.b.cmd('Page.addScriptToEvaluateOnNewDocument', {'source': source}, session=self.sid)

    def goto(self, url, timeout=20):
        self.b.cmd('Page.navigate', {'url': url}, session=self.sid)
        self.wait('document.readyState === "complete"', timeout=timeout)

    def js(self, expr, timeout=45):
        r = self.b.cmd('Runtime.evaluate', {
            'expression': expr,
            'awaitPromise': True,
            'returnByValue': True,
            'userGesture': True,
        }, session=self.sid, timeout=timeout)
        if 'exceptionDetails' in r:
            det = r['exceptionDetails']
            txt = det.get('text', 'js error')
            try:
                txt += ': ' + str(det['exception']['description'])[:300]
            except Exception:
                pass
            raise Fail('page js threw: ' + txt)
        return r.get('result', {}).get('value')

    def wait(self, expr, timeout=15, poll=0.1, what=None):
        end = time.time() + timeout
        last = None
        while time.time() < end:
            try:
                last = self.js(expr)
            except Fail as exc:
                last = str(exc)
            if last:
                return last
            time.sleep(poll)
        raise CannotRun('wait timed out: %s (%r)' % (what or expr, last))

    def href(self):
        try:
            return self.js('location.href')
        except Exception:
            return ''


def jsval(v):
    """JSON literal safe to inline into a page expression."""
    return json.dumps(v)


# --------------------------------------------------------------------- shim

# Records peers, data channels, frames in both directions, and blob URL use.
# No hook is shipped inside the artifact; this is installed by the gate.
SHIM = r"""
(function () {
  if (window.__probe) { return; }
  var P = {
    peers: [], channels: [], sent: [], recv: [], raw: [], wire: [], media: [],
    blobs: { created: [], revoked: [], domAtRevoke: [] },
    errors: [], lastRevoke: null, clipWrites: [], ctlMut: null, armed: null
  };
  var OrigPC = window.RTCPeerConnection;
  function toB64(u8) {
    var s = '';
    for (var i = 0; i < u8.length; i += 0x8000) {
      s += String.fromCharCode.apply(null, u8.subarray(i, i + 0x8000));
    }
    return btoa(s);
  }
  function recChan(dc) {
    var rec = { dc: dc, id: P.channels.length };
    P.channels.push(rec);
    dc.addEventListener('message', function (e) {
      var v = (typeof e.data === 'string') ? e.data : { bytes: (e.data && (e.data.byteLength || e.data.size)) || 0 };
      if (P.recv.length < 5000) { P.recv.push(v); }
    });
    dc.addEventListener('open', function () { rec.opened = Date.now(); });
    dc.addEventListener('close', function () { rec.closed = Date.now(); });
    var origSend = dc.send.bind(dc);
    dc.send = function (data) {
      if (typeof data === 'string') {
        if (P.sent.length < 5000) { P.sent.push(data); }
      } else {
        var u8 = data instanceof ArrayBuffer ? new Uint8Array(data) : new Uint8Array(data.buffer || data);
        if (P.sent.length < 5000) { P.sent.push({ bytes: u8.length }); }
        if (P.raw.length < 12 && u8.length <= 131072) { P.raw.push(toB64(u8)); }
        if (u8.length <= 131072) { P.lastRaw = toB64(u8); }
        if (P.wire.length < 400 && u8.length <= 262144) {
          P.wire.push({ head: u8[0], len: u8.length, b64: toB64(u8) });
        }
      }
      return origSend(data);
    };
    return rec;
  }
  if (OrigPC) {
    window.RTCPeerConnection = class ProbePC extends OrigPC {
      constructor() {
        super(...arguments);
        var self = this;
        P.peers.push({ pc: self, id: P.peers.length, created: Date.now() });
        var origCreate = self.createDataChannel.bind(self);
        self.createDataChannel = function () {
          var dc = origCreate.apply(null, arguments);
          recChan(dc);
          return dc;
        };
        self.addEventListener('datachannel', function (e) { recChan(e.channel); });
      }
    };
    window.RTCPeerConnection.prototype = OrigPC.prototype;
  }
  var origCreateURL = URL.createObjectURL ? URL.createObjectURL.bind(URL) : null;
  var origRevokeURL = URL.revokeObjectURL ? URL.revokeObjectURL.bind(URL) : null;
  if (origCreateURL) {
    URL.createObjectURL = function (blob) {
      var url = origCreateURL(blob);
      P.blobs.created.push({ url: url, size: blob && blob.size, type: blob && blob.type });
      if (blob && /^(image|video)\//.test(String(blob.type || '')) && blob.size <= 4 * 1024 * 1024 && P.media.length < 20) {
        blob.arrayBuffer().then(function (buf) {
          P.media.push({ url: url, type: blob.type, size: blob.size, b64: toB64(new Uint8Array(buf)) });
        }).catch(function () {});
      }
      return url;
    };
  }
  if (origRevokeURL) {
    URL.revokeObjectURL = function (url) {
      var live = document.querySelectorAll('img[src^="blob:"],a[href^="blob:"],video[src^="blob:"],audio[src^="blob:"]').length;
      var logLive = document.querySelectorAll('#log img[src^="blob:"],#log video[src^="blob:"],#log a[href^="blob:"]').length;
      var tileLive = document.querySelectorAll('#galleryGrid img[src^="blob:"],#galleryGrid video[src^="blob:"]').length;
      P.blobs.revoked.push(url);
      P.blobs.domAtRevoke.push(live);
      P.lastRevoke = { url: url, liveNodes: live, logLive: logLive, tileLive: tileLive };
      return origRevokeURL(url);
    };
  }
  // The send path is the only place a valid control frame is produced. These
  // one shot transforms ride the app's own compress-then-encrypt path, so the
  // receiver gets an authenticated frame with a mutated plaintext envelope.
  function mutateControl(m) {
    if ((!P.ctlMut && !P.armed) || !m || m.t !== 'control' || typeof m.json !== 'string') { return m; }
    var mode = P.ctlMut;
    var o;
    try { o = JSON.parse(m.json); } catch (e) { return m; }
    // A one or n shot rewrite of one control kind into another, riding the
    // app's own seal path. Used by the react and mid cases.
    if (P.armed && P.armed.left > 0 && o && o.k === P.armed.from) {
      var arm = P.armed;
      arm.left--;
      if (arm.left <= 0) { P.armed = null; }
      o = Object.assign({}, o, arm.to);
      return Object.assign({}, m, { json: JSON.stringify(o) });
    }
    if (mode === 'unknown-k') { o.k = 'probe-unknown-k'; }
    else if (mode === 'bad-version') { o.v = 99; }
    else if (mode === 'bad-json') { P.ctlMut = null; return Object.assign({}, m, { json: '{not json' }); }
    else if (mode === 'file-truncate' && o.k === 'file-start') {
      o.size = Number(o.size) + 65536;
      o.chunks = Number(o.chunks) + 1;
      var f = m.file ? Object.assign({}, m.file, { size: o.size, chunks: o.chunks }) : m.file;
      P.ctlMut = null;
      return Object.assign({}, m, { json: JSON.stringify(o), file: f });
    }
    else if (mode === 'file-bad-start' && o.k === 'file-start') { o.size = -1; o.chunks = 1; }
    else if (mode === 'file-bad-digest' && o.k === 'file-end') { o.digest = new Array(65).join('0'); }
    else if (mode === 'mig-bad-fp' && o.k === 'mig' && o.step === 'offer') { o.fp = '00:00'; }
    // UX-01: pin every outgoing msg mid so a duplicate id reaches the peer.
    // Returns before the one shot reset, the mode stays armed until cleared.
    else if (mode === 'msg-fixed-mid' && o.k === 'msg') {
      o.mid = '00000000000000aa';
      return Object.assign({}, m, { json: JSON.stringify(o) });
    }
    else { return m; }
    P.ctlMut = null;
    return Object.assign({}, m, { json: JSON.stringify(o) });
  }
  if (window.Worker && Worker.prototype && Worker.prototype.postMessage) {
    var origPM = Worker.prototype.postMessage;
    Worker.prototype.postMessage = function (msg, transfer) {
      try { msg = mutateControl(msg); } catch (e) {}
      return origPM.call(this, msg, transfer);
    };
  }
  var CP = window.Clipboard && window.Clipboard.prototype;
  if (CP && CP.writeText) {
    CP.writeText = function (text) { P.clipWrites.push(String(text)); return Promise.resolve(); };
  }
  P.mutate = function (mode) { P.ctlMut = mode; return true; };
  P.armRewrite = function (from, to, times) {
    P.armed = { from: from, to: to, left: times || 1 };
    return true;
  };
  P.disarm = function () { P.armed = null; P.ctlMut = null; return true; };
  window.addEventListener('error', function (e) { P.errors.push(String(e.message)); });
  P.open = function () {
    for (var i = 0; i < P.channels.length; i++) {
      if (P.channels[i].dc.readyState === 'open') { return P.channels[i].dc; }
    }
    return null;
  };
  P.send = function (text) {
    var dc = P.open();
    if (!dc) { return false; }
    dc.send(text);
    P.sent.push(typeof text === 'string' ? text : { bytes: text.byteLength || text.length || 0 });
    return true;
  };
  P.sendBytes = function (n, fill) {
    var dc = P.open();
    if (!dc) { return false; }
    var u = new Uint8Array(n);
    u.fill(fill === undefined ? 0x41 : fill);
    dc.send(u);
    return true;
  };
  P.sendB64 = function (b64) {
    var dc = P.open();
    if (!dc) { return false; }
    var bin = atob(b64);
    var u = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) { u[i] = bin.charCodeAt(i); }
    dc.send(u);
    return true;
  };
  P.snapshot = function () {
    return {
      peers: P.peers.length,
      channels: P.channels.map(function (c) { return { state: c.dc.readyState, opened: !!c.opened, closed: !!c.closed }; }),
      sent: P.sent.length,
      recv: P.recv.length,
      sentFrames: P.sent.slice(-400),
      recvFrames: P.recv.slice(-400),
      raw: P.raw.slice(-12),
      lastRaw: P.lastRaw || null,
      lastRevoke: P.lastRevoke,
      wire: P.wire.slice(-200),
      media: P.media.slice(-10),
      clipWrites: P.clipWrites.slice(-10),
      blobCreated: P.blobs.created.slice(-50),
      blobRevoked: P.blobs.revoked.slice(-50),
      domAtRevoke: P.blobs.domAtRevoke.slice(-50),
      errors: P.errors.slice(-20)
    };
  };
  P.logText = function () {
    var el = document.querySelector('#log');
    return el ? (el.innerText || el.textContent || '') : '';
  };
  P.iceServers = function () {
    if (!P.peers.length) { return null; }
    try { return P.peers[0].pc.getConfiguration().iceServers || []; } catch (e) { return null; }
  };
  window.__probe = P;
})();
"""


def snapshot(page):
    v = page.js('window.__probe.snapshot()')
    if not isinstance(v, dict):
        raise CannotRun('probe shim missing from the page')
    return v


def open_channel(page):
    return page.js("(() => { const p = window.__probe; const c = p.open(); return !!c; })()")


def wait_pair(a, b, timeout=25):
    end = time.time() + timeout
    last = None
    while time.time() < end:
        try:
            sa = snapshot(a)
            sb = snapshot(b)
            last = (sa['peers'], sb['peers'], [c['state'] for c in sa['channels']], [c['state'] for c in sb['channels']])
            if sa['peers'] >= 1 and sb['peers'] >= 1 and open_channel(a) and open_channel(b):
                return sa, sb
        except CannotRun:
            pass
        time.sleep(0.2)
    raise CannotRun('two live peers with an open channel not observed, last=%r' % (last,))


# ----------------------------------------------------------------- app flow

APP_JS_SET = ("(() => { const i = document.querySelector(%s); if (!i) return false;"
              " i.value = %s; i.dispatchEvent(new Event('input', {bubbles:true}));"
              " i.dispatchEvent(new Event('change', {bubbles:true})); return true; })()")


def click(page, selector):
    ok = page.js("(() => { const e = document.querySelector(%s); if (!e) return false; e.click(); return true; })()"
                 % jsval(selector))
    if not ok:
        raise Fail('control not found: ' + selector)


def fill(page, selector, value):
    ok = page.js(APP_JS_SET % (jsval(selector), jsval(value)))
    if not ok:
        raise Fail('input not found: ' + selector)


def wait_enabled(page, selector, timeout=20):
    page.wait("(() => { const e = document.querySelector(%s); return !!e && !e.disabled; })()"
              % jsval(selector), timeout=timeout, what='enabled ' + selector)


def content_locked(page):
    return page.js("""(() => {
      const i = document.querySelector('#input');
      const s = document.querySelector('#send');
      const log = document.querySelector('#log');
      if (i && (i.disabled || i.readOnly)) return true;
      if (s && s.disabled) return true;
      if (log && (log.classList.contains('locked') || log.getAttribute('data-locked') === 'on')) return true;
      const gate = document.querySelector('[data-locked="on"], .lock-veil:not([hidden])');
      return !!gate;
    })()""")


def confirm_sas(a, b, timeout=12):
    """Click the app's own confirm control on both sides, waiting for it to enable."""
    js = """(() => {
      const el = document.querySelector('#confirmSas');
      if (el && !el.disabled) { el.click(); return (el.textContent || '').trim() || '#confirmSas'; }
      return '';
    })()"""
    js_text = """(() => {
      const all = Array.from(document.querySelectorAll('button, [role="button"]'));
      const hit = all.find(x => !x.disabled && /^(confirm|verify|they match|it matches|match|confirm match|yes)$/i.test((x.textContent || '').trim()));
      if (hit) { hit.click(); return (hit.textContent || '').trim(); }
      return '';
    })()"""
    got = []
    for p in (a, b):
        end = time.time() + timeout
        while time.time() < end:
            r = p.js(js) or p.js(js_text)
            if r:
                got.append(r)
                break
            time.sleep(0.3)
    return got


def pair_app(a, b, confirm=True, timeout=30, copy_offer=False):
    wait_enabled(a, '#create')
    click(a, '#create')
    a.wait("(() => { const e = document.querySelector('#offer'); return !!e && e.value.length > 40; })()",
           timeout=timeout, what='invite code')
    code = a.js("document.querySelector('#offer').value")
    if copy_offer:
        click(a, '#copyOffer')
        time.sleep(0.3)
    fill(b, '#offerIn', code)
    wait_enabled(b, '#join')
    click(b, '#join')
    b.wait("(() => { const e = document.querySelector('#answer'); return !!e && e.value.length > 40; })()",
           timeout=timeout, what='reply code')
    reply = b.js("document.querySelector('#answer').value")
    fill(a, '#answerIn', reply)
    wait_enabled(a, '#connect')
    click(a, '#connect')
    wait_pair(a, b, timeout=timeout)
    if confirm:
        if content_locked(a) or content_locked(b):
            confirm_sas(a, b)
            end = time.time() + timeout
            while time.time() < end:
                if not content_locked(a) and not content_locked(b):
                    return
                time.sleep(0.3)
            raise CannotRun('content still locked after a confirm attempt, SAS gate not usable by the gate')


def send_text(page, text):
    ok = page.js("window.__probe.send(%s)" % jsval(text))
    if not ok:
        raise CannotRun('no open channel to send on')
    return ok


def recv_marker(page, marker, timeout=8):
    end = time.time() + timeout
    while time.time() < end:
        txt = page.js("window.__probe.logText()") or ''
        if marker in txt:
            return True
        time.sleep(0.15)
    return False


def recv_shim(page, marker, timeout=8):
    """True when the shim saw the marker on the captured channel."""
    end = time.time() + timeout
    while time.time() < end:
        frames = snapshot(page)['recvFrames']
        for f in frames:
            if isinstance(f, str) and marker in f:
                return True
        time.sleep(0.15)
    return False


def app_url(path):
    return 'file://' + urllib.parse.quote(os.path.abspath(path))


# ------------------------------------------------------------------ helpers

def read_app(path):
    if not os.path.isfile(path):
        raise CannotRun('artifact missing: ' + path)
    with open(path, 'rb') as fh:
        raw = fh.read()
    return raw


def app_text(path):
    raw = read_app(path)
    try:
        return raw.decode('ascii')
    except UnicodeDecodeError as exc:
        raise Fail('artifact is not ASCII: %s' % exc)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for block in iter(lambda: fh.read(65536), b''):
            h.update(block)
    return h.hexdigest()


def has(text, *names):
    return all(n in text for n in names)


def dash_scan(path):
    with open(path, 'rb') as fh:
        raw = fh.read()
    bad = []
    for i, b in enumerate(raw):
        if b > 127:
            bad.append(('non-ascii', i, b))
            continue
    for token, label in ((b'\xe2\x80\x93', 'en dash'), (b'\xe2\x80\x94', 'em dash')):
        if token in raw:
            bad.append((label, raw.index(token), 0))
    return bad


def decode_code(code):
    """Return the plaintext payload of an app code, both v1 and v2 shapes."""
    code = (code or '').strip()
    if code.startswith('E2.'):
        parts = code.split('.', 2)
        if len(parts) != 3:
            raise CannotRun('code is not E2.<version>.<body>')
        body = parts[2]
        data = base64.urlsafe_b64decode(body + '=' * (-len(body) % 4))
        try:
            data = gzip.decompress(data)
        except OSError:
            raise CannotRun('E2 body is not gzip')
        return data.decode('utf-8')
    head, _, body = code.partition('.')
    if head in ('GZ1', 'RAW1'):
        data = base64.b64decode(body)
        if head == 'GZ1':
            data = gzip.decompress(data)
        return data.decode('utf-8')
    raise CannotRun('unrecognised code prefix: %r' % head)


def encode_code(prefix, payload):
    data = payload.encode('utf-8')
    if prefix == 'E2':
        return 'E2.1.' + base64.urlsafe_b64encode(gzip.compress(data)).decode('ascii').rstrip('=')
    if prefix == 'GZ1':
        return 'GZ1.' + base64.b64encode(gzip.compress(data)).decode('ascii')
    return 'RAW1.' + base64.b64encode(data).decode('ascii')


def mutate_code(code, mutate):
    """Apply mutate to the decoded payload, re-encode in the same shape."""
    prefix = 'E2' if code.startswith('E2.') else code.split('.', 1)[0]
    payload = decode_code(code)
    return encode_code(prefix, mutate(payload))


# -------------------------------------------------------------------- cases

def case_selftest(app, opts):
    """R2-01: the harness can see two live peers, a captured channel, and fails closed."""
    bad = dash_scan(__file__)
    expect(not bad, 'gate.py carries non-ASCII or dash bytes: %r' % bad[:3])

    b = Browser()
    try:
        ca = b.context()
        cb = b.context()
        a = b.page(ca)
        bb = b.page(cb)
        a.init(SHIM)
        bb.init(SHIM)
        a.goto('about:blank')
        bb.goto('about:blank')
        expect_eq(a.js('!!window.__probe'), True, 'shim installed on peer A')
        expect_eq(bb.js('!!window.__probe'), True, 'shim installed on peer B')

        # Negative control for the channel assertion itself.
        empty = a.js('window.__probe.snapshot()')
        expect_eq(empty['peers'], 0, 'a fresh page starts with zero peers')
        try:
            wait_pair(a, bb, timeout=1.5)
            raise Fail('wait_pair passed with no peers')
        except CannotRun:
            pass

        url = 'file://' + os.path.join(FIXTURES, 'pair.html')
        a.goto(url + '?role=a')
        bb.goto(url + '?role=b')
        expect_eq(a.js('typeof window.__fx'), 'object', 'fixture exposed on A')
        a.js('window.__fx.make()')
        bb.js('window.__fx.make()')
        offer = a.js('window.__fx.offer()')
        expect(isinstance(offer, str) and 'a=' in offer, 'A produced an SDP offer')
        answer = bb.js('window.__fx.accept(%s)' % jsval(offer))
        expect(isinstance(answer, str) and 'a=' in answer, 'B produced an SDP answer')
        a.js('window.__fx.finish(%s)' % jsval(answer))

        sa, sb = wait_pair(a, bb, timeout=20)
        expect_eq(sa['peers'], 1, 'exactly one peer on A')
        expect_eq(sb['peers'], 1, 'exactly one peer on B')
        expect(len(sa['channels']) >= 1 and len(sb['channels']) >= 1, 'channel captured on both sides')

        marker = 'PROBE-SELFTEST-1'
        expect(a.js('window.__fx.send(%s)' % jsval(marker)), 'send returned true')
        got = recv_shim(bb, marker, timeout=8)
        expect(got, 'marker frame arrived on the far side')
        expect_eq(len(snapshot(bb)['recvFrames']) >= 1, True, 'received frame recorded by the shim')

        # A broken predicate must fail, otherwise this gate is a green light.
        try:
            expect_eq(snapshot(a)['peers'], 2, 'negative control')
            raise Fail('negative control did not fail')
        except Fail as exc:
            expect('negative control' in str(exc), 'negative control raised for the right reason')

        # An assertion without a channel must not pass.
        try:
            expect_eq(snapshot(a)['channels'][0]['state'], 'open', 'channel state')
        except Fail:
            raise Fail('selftest could not read a channel state')

        print('PASS selftest 2 peers, 1 channel, round trip, negative control fired')
    finally:
        b.close()


# ------------------------------------------------------------ case helpers

TINY_PNG = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==')


def log_text(page):
    return page.js("(() => { const e = document.querySelector('#log'); return e ? (e.innerText || e.textContent || '') : ''; })()") or ''


def body_text(page):
    return page.js('document.body ? document.body.innerText : ""') or ''


def wait_log(page, pattern, timeout=6):
    end = time.time() + timeout
    while time.time() < end:
        txt = log_text(page)
        if re.search(pattern, txt, re.I):
            return txt
        time.sleep(0.15)
    return ''


def anchor_count(page):
    return page.js("document.querySelectorAll('#log a[download], #log a[href^=\"blob:\"]').length") or 0


def ended_or_blank(page, timeout=10):
    end = time.time() + timeout
    while time.time() < end:
        href = page.href()
        if href.startswith('about:'):
            return 'about:blank' if href.startswith('about:blank') else href
        try:
            on = page.js("(() => { const e = document.querySelector('#ended');"
                         " if (!e) return false; return !e.hidden && getComputedStyle(e).display !== 'none'; })()")
        except Exception:
            on = False
        if on:
            return 'ended'
        time.sleep(0.2)
    return ''


def wait_blank(page, timeout=10):
    """Wait only for the navigation, never settle for the ended panel."""
    end = time.time() + timeout
    last = ''
    while time.time() < end:
        last = page.href()
        if last == 'about:blank':
            return 'about:blank'
        time.sleep(0.2)
    raise Fail('kill did not navigate to about:blank, last href=%r' % (last,))


def sas_digits(page):
    txt = page.js("""(() => {
      const el = document.querySelector('#digits, [data-sas], [class*="sas" i]');
      return el ? (el.innerText || el.textContent || '') : (document.body ? document.body.innerText : '');
    })()""") or ''
    best = ''
    for run in re.findall(r'\d[\d\s\-]*\d', txt):
        digits = re.sub(r'\D', '', run)
        if len(digits) > len(best):
            best = digits
    return best if len(best) >= 40 else ''


def click_text(page, pattern):
    """Click the first enabled button whose text matches pattern. Returns its text."""
    js = """(() => {
      const re = new RegExp(%s, 'i');
      const all = Array.from(document.querySelectorAll('button, [role="button"], a'));
      const hit = all.find(x => !x.disabled && re.test((x.textContent || '').trim()));
      if (hit) { hit.click(); return (hit.textContent || '').trim(); }
      return '';
    })()"""
    return page.js(js % jsval(pattern))


def open_app(app, confirm=True, query='', copy_offer=False, pre_init=''):
    app_text(app)
    b = Browser()
    try:
        a = b.page(b.context())
        c = b.page(b.context())
        for p in (a, c):
            p.init(SHIM)
            if pre_init:
                p.init(pre_init)
        url = app_url(app) + query
        a.goto(url)
        c.goto(url)
        pair_app(a, c, confirm=confirm, copy_offer=copy_offer)
        return b, a, c
    except Exception:
        b.close()
        raise


def scratch_file(name, data):
    d = tempfile.mkdtemp(prefix='gate-file-')
    path = os.path.join(d, name)
    with open(path, 'wb') as fh:
        fh.write(data)
    return path


def send_file_and_wait(sender, receiver, path, timeout=25):
    """Drive the real file input and require one new Save anchor."""
    before = anchor_count(receiver)
    sender.set_file('#file', path)
    end = time.time() + timeout
    while time.time() < end:
        if anchor_count(receiver) > before:
            return True
        time.sleep(0.25)
    return False


def decode_b64(text):
    return base64.b64decode(text)


def wire_since(page, start):
    return snapshot(page)['wire'][start:]


def ended_text(page):
    try:
        return page.js("(() => { const e = document.querySelector('#endedText');"
                       " return e ? (e.innerText || e.textContent || '') : ''; })()") or ''
    except Fail:
        return ''


def png_chunk(tag, data):
    return (struct.pack('>I', len(data)) + tag + data +
            struct.pack('>I', binascii.crc32(tag + data) & 0xffffffff))


def png_bytes(width, height, metadata=True):
    """A real PNG. metadata adds tEXt and eXIf chunks the re-encode must drop."""
    row = b'\x00' + bytes([180, 40, 40]) * width
    raw = row * height
    out = b'\x89PNG\r\n\x1a\n'
    out += png_chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
    if metadata:
        out += png_chunk(b'tEXt', b'Comment\x00Exif GPS XMP ICC profile probe')
        out += png_chunk(b'eXIf', b'MM\x00\x2a\x00\x00\x00\x08\x00\x00')
    out += png_chunk(b'IDAT', zlib.compress(raw, 6))
    out += png_chunk(b'IEND', b'')
    return out


def dispatch_files(page, items, event='paste'):
    """Dispatch a real ClipboardEvent or DragEvent carrying generated Files."""
    js = """(() => {
      const items = %s;
      const dt = new DataTransfer();
      for (const it of items) {
        const bin = atob(it.b64);
        const u = new Uint8Array(bin.length);
        for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
        dt.items.add(new File([u], it.name, { type: it.type }));
      }
      const ev = %s === 'drop'
        ? new DragEvent('drop', { dataTransfer: dt, bubbles: true, cancelable: true })
        : new ClipboardEvent('paste', { clipboardData: dt, bubbles: true, cancelable: true });
      document.dispatchEvent(ev);
      return { files: dt.files.length, prevented: ev.defaultPrevented };
    })()""" % (jsval(items), jsval(event))
    return page.js(js)


def dispatch_text_paste(page, text):
    js = """(() => {
      const dt = new DataTransfer();
      dt.setData('text/plain', %s);
      const ev = new ClipboardEvent('paste', { clipboardData: dt, bubbles: true, cancelable: true });
      document.dispatchEvent(ev);
      return { prevented: ev.defaultPrevented };
    })()""" % jsval(text)
    return page.js(js)


def image_node(page):
    return page.js("""(() => {
      const i = document.querySelector('#log img[src^="blob:"]');
      if (!i) return null;
      return { src: i.getAttribute('src'), w: i.naturalWidth, h: i.naturalHeight, complete: i.complete };
    })()""")


def video_node(page):
    return page.js("""(() => {
      const v = document.querySelector('#log video[src^="blob:"]');
      if (!v) return null;
      return { src: v.getAttribute('src'), ready: v.readyState, w: v.videoWidth, h: v.videoHeight,
               err: v.error ? v.error.code : null, dur: v.duration };
    })()""")


def wait_image(page, timeout=15):
    end = time.time() + timeout
    last = None
    while time.time() < end:
        last = image_node(page)
        if last and last.get('src'):
            return last
        time.sleep(0.2)
    raise CannotRun('no received image node appeared, last=%r' % (last,))


def wait_video(page, timeout=20):
    end = time.time() + timeout
    last = None
    while time.time() < end:
        last = video_node(page)
        if last and last.get('src'):
            return last
        time.sleep(0.2)
    raise CannotRun('no received video node appeared, last=%r' % (last,))


def media_for(page, url):
    for rec in snapshot(page)['media']:
        if rec.get('url') == url:
            return rec
    return None


def extract_js_function(text, name):
    """Return the source of a top level async function by brace matching."""
    m = re.search(r'(?:async\s+)?function\s+%s\s*\([^)]*\)\s*\{' % re.escape(name), text)
    if not m:
        raise CannotRun('function %s not found in the artifact' % name)
    depth = 0
    for i in range(m.start(), len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return text[m.start():i + 1]
    raise CannotRun('function %s has unbalanced braces' % name)


# -------------------------------------------------------------------- cases

def case_envelope(app, opts):
    """R2-02: unknown k, unknown v, malformed JSON are visible and never silent.

    V2 sends authenticated binary control frames only, so a plaintext injection
    would be rejected before the router and would prove nothing. Every probe
    frame here is produced by the app's own compress-then-encrypt path: a one
    shot shim transform rewrites the envelope plaintext before the worker seals
    it, so the receiver decrypts a valid frame that carries the unknown k.
    """
    b, a, c = open_app(app)
    try:
        # Unknown k, once: visible, named, no crash.
        expect(c.js("window.__probe.mutate('unknown-k')"), 'shim mutation not armed')
        fill(c, '#input', 'PROBE-K-1')
        click(c, '#send')
        txt = wait_log(a, r'unknown|unrecognis|unrecogniz|unexpected|bad frame', 8)
        expect(txt, 'unknown k left no visible system line')
        expect('probe-unknown-k' in log_text(a), 'unknown k value is not shown')
        expect(open_channel(a), 'channel died on an unknown k frame')

        # Unknown v: visible version state, and no content from the frame.
        expect(c.js("window.__probe.mutate('bad-version')"), 'version mutation not armed')
        fill(c, '#input', 'PROBE-V99')
        click(c, '#send')
        time.sleep(1.5)
        expect('PROBE-V99' not in body_text(a), 'content from an unknown envelope version rendered')
        expect(wait_log(a, r'version|newer|older', 4), 'unknown v left no visible version state')

        # Malformed JSON inside a valid sealed frame: a counted unknown frame.
        expect(c.js("window.__probe.mutate('bad-json')"), 'json mutation not armed')
        fill(c, '#input', 'PROBE-J-1')
        click(c, '#send')
        expect(wait_log(a, r'invalid|malformed|bad frame|unknown|reject', 5),
               'malformed JSON inside a valid frame was dropped silently')
        expect(open_channel(a), 'channel died on a malformed frame')

        # Three unknown frames in 10 s runs Kill (A1).
        for _ in range(2):
            expect(c.js("window.__probe.mutate('unknown-k')"), 'shim mutation not re-armed')
            fill(c, '#input', 'PROBE-K-2')
            click(c, '#send')
            time.sleep(0.3)
        expect(ended_or_blank(a, 10), 'three unknown frames in 10 s did not run kill')
    finally:
        b.close()


def case_ratchet(app, opts):
    """R2-03: fresh key per message, no private or chain key crosses to the main thread.

    The exportKey ban is retargeted to its real invariant: exporting a public
    key is fine, exporting or posting private or chain key bytes is not. The
    scan reads every exportKey call and both postMessage surfaces (worker to
    main, main to worker), then the behavioral half checks that identical
    plaintext never yields identical ciphertext on the captured binary wire.
    """
    text = app_text(app)
    wstart = text.find('id="cryptoWorker"')
    expect(wstart >= 0, 'no crypto worker script in the artifact')
    wend = text.find('</script>', wstart)
    expect(wend > wstart, 'crypto worker script is not closed')
    worker = text[wstart:wend]
    main = text[wend:]

    exports = re.findall(r'exportKey\s*\([^)]*\)', text)
    expect(exports, 'no key export found, the public key path changed shape')
    for call in exports:
        expect('.publicKey' in call and 'privateKey' not in call,
               'exportKey is called on private material: %s' % call)
    expect('exportKey' not in main, 'the main thread exports a key, key bytes are readable there')
    expect(re.search(r'\bfunction\s+genPair\b', worker), 'key generation is not inside the Worker')
    expect(len(re.findall(r'generateKey\s*\(', main)) == 0,
           'the main thread generates key pairs, private material lives outside the Worker')

    banned = re.compile(r'(\.priv\b|\bmkBytes\b|\brk\b|\bckS\b|\bckR\b|\bfile\.key\b|\bprivateKey\b)')
    worker_posts = [m.start() for m in re.finditer(r'self\.postMessage\s*\(', worker)]
    expect(worker_posts, 'the Worker never posts to the main thread, cannot scan the surface')
    for at in worker_posts:
        snippet = worker[at:at + 160]
        expect(not banned.search(snippet),
               'Worker postMessage carries key material: %s' % snippet.replace('\n', ' ')[:120])
    main_posts = [m.start() for m in re.finditer(r'worker\.postMessage\s*\(', main)]
    expect(main_posts, 'the main thread never posts to the Worker')
    for at in main_posts:
        snippet = main[at:at + 160]
        expect(not banned.search(snippet),
               'main to Worker postMessage carries key material: %s' % snippet.replace('\n', ' ')[:120])
    expect('let rk' not in main and 'let ckS' not in main and 'let ckR' not in main,
           'chain key state is declared outside the Worker')

    b, a, c = open_app(app)
    try:
        def send_ui(value):
            fill(a, '#input', value)
            click(a, '#send')

        start = len(snapshot(a)['wire'])
        marker = 'PROBE-RATCHET-1'
        send_ui(marker)
        time.sleep(0.5)
        send_ui(marker)
        time.sleep(0.8)
        frames = [f for f in wire_since(a, start) if f.get('head') == 1]
        expect(len(frames) >= 2, 'fewer than two sealed control frames on the wire')
        last_two = frames[-2:]
        expect(last_two[0]['b64'] != last_two[1]['b64'],
               'identical plaintext produced identical ciphertext')
        for f in frames:
            raw = decode_b64(f['b64'])
            expect(marker.encode('ascii') not in raw, 'plaintext marker found on the wire')

        sent = snapshot(a)['sentFrames']
        expect(not any(isinstance(x, str) for x in sent), 'a plaintext string frame is on the wire')

        start = len(snapshot(a)['wire'])
        for i in range(5):
            send_ui('PROBE-RATCHET-%d' % (i + 2))
            time.sleep(0.15)
        time.sleep(0.8)
        tail = [f['b64'] for f in wire_since(a, start) if f.get('head') == 1]
        tail = tail[-5:]
        expect_eq(len(tail), 5, 'control frame count in the tail')
        expect_eq(len(set(tail)), 5, 'per message keys are not fresh, repeated ciphertext in the tail')
        expect(not snapshot(a)['errors'], 'page errors on the ratchet path: %r' % (snapshot(a)['errors'],))
    finally:
        b.close()


def case_sas(app, opts):
    """R2-04: content locked before confirmation, 60 digits equal, pre-confirm frames dropped."""
    b, a, c = open_app(app, confirm=False)
    try:
        expect(content_locked(a) or content_locked(c), 'composer is not locked before SAS confirmation')
        da = sas_digits(a)
        dc = sas_digits(c)
        panel = a.js("(() => { const e = document.querySelector('#digits'); return e ? e.innerText : 'no #digits element'; })()")
        expect(da, 'no 60 digit SAS found on A, digits panel: %r' % (str(panel)[:160],))
        expect(dc, 'no 60 digit SAS found on B')
        expect_eq(len(da), 60, 'SAS length on A')
        expect_eq(da, dc, 'SAS differs between the two peers')

        # The gate must hold on the app's own send path, not only on a synthetic frame.
        sent0 = snapshot(c)['sent']
        c.js("(() => { const i = document.querySelector('#input'); if (!i) return false; i.value = 'PROBE-PRE'; return true; })()")
        c.js("(() => { const s = document.querySelector('#send'); if (s) s.click(); return true; })()")
        time.sleep(1.2)
        expect_eq(snapshot(c)['sent'], sent0, 'a content frame left the app before SAS confirmation')
        expect('PROBE-PRE' not in body_text(a), 'content rendered before SAS confirmation')

        confirm_sas(a, c)
        end = time.time() + 15
        while time.time() < end and (content_locked(a) or content_locked(c)):
            time.sleep(0.3)
        expect(not content_locked(a), 'composer did not unlock after both confirms')

        marker = 'PROBE-SAS-POST'
        fill(a, '#input', marker)
        click(a, '#send')
        expect(recv_marker(c, marker, 8), 'no content flowed after confirmation')
    finally:
        b.close()


def case_file(app, opts):
    """R2-05: no Save anchor and no complete state when digest or completeness fails.

    V2 sends binary frames only. The first transfer proves the wire shape
    (file-start, chunk, file-end all binary). The next two ride the app's own
    sealed send path with one plaintext field mutated, so they reach the real
    completeness and digest branches: a declared size over the delivered bytes,
    and a wrong digest over a complete file. A literal replay of the captured
    binary frames with the file-end tail dropped closes the case.
    """
    b, a, c = open_app(app)
    path = scratch_file('probe.bin', bytes(range(256)) * 32)
    try:
        start = len(snapshot(c)['wire'])
        expect(send_file_and_wait(c, a, path), 'a verified 8 KiB file produced no Save anchor')
        frames = wire_since(c, start)
        heads = [f.get('head') for f in frames]
        expect(heads.count(1) >= 2 and 2 in heads,
               'the first transfer was not binary start, chunk, end: %r' % (heads,))
        expect(anchor_count(a) >= 1, 'the verified transfer left no Save anchor')

        # Completeness: declared size 64 KiB over the delivered bytes, one extra chunk.
        before = anchor_count(a)
        blobs = len(snapshot(a)['blobCreated'])
        expect(c.js("window.__probe.mutate('file-truncate')"), 'truncate mutation not armed')
        c.set_file('#file', path)
        expect(wait_log(a, r'incomplete|rejected|fail', 20),
               'a truncated transfer left no failed state on the receiver')
        time.sleep(1)
        expect_eq(anchor_count(a), before, 'a truncated transfer produced a Save anchor')
        expect_eq(len(snapshot(a)['blobCreated']), blobs, 'a truncated transfer created a blob')
        big = [x for x in snapshot(a)['blobCreated'] if (x.get('size') or 0) > 8 * 1024 * 1024]
        expect(not big, 'a padded blob larger than 8 MiB was exported: %r' % (big[:1],))

        # Digest: complete file, wrong digest, no export.
        before = anchor_count(a)
        blobs = len(snapshot(a)['blobCreated'])
        expect(c.js("window.__probe.mutate('file-bad-digest')"), 'digest mutation not armed')
        c.set_file('#file', path)
        expect(wait_log(a, r'digest|rejected|fail', 20), 'a bad digest left no failed state')
        time.sleep(1)
        expect_eq(anchor_count(a), before, 'a bad digest produced a Save anchor')
        expect_eq(len(snapshot(a)['blobCreated']), blobs, 'a bad digest created a blob')

        # Literal binary replay with a truncated tail: start and chunk, no end.
        expect(len(frames) >= 3, 'not enough captured frames to replay')
        blobs = len(snapshot(a)['blobCreated'])
        for f in frames[:-1]:
            c.js('window.__probe.sendB64(%s)' % jsval(f['b64']))
            time.sleep(0.1)
        time.sleep(2)
        expect(anchor_count(a) <= before, 'a truncated binary replay produced a Save anchor')
        expect_eq(len(snapshot(a)['blobCreated']), blobs,
                  'a truncated binary replay still exported a blob')
        expect(ended_or_blank(a, 8) or wait_log(a, r'fail|incomplete|reject|authentication', 3),
               'a truncated binary replay left no failed or ended state')
    finally:
        b.close()
        shutil.rmtree(os.path.dirname(path), ignore_errors=True)


def case_budget(app, opts):
    """R2-06: a bad start does not block later files, a valid burst trips A8, row cap 2000.

    A8 is 40 frames in a 5 s window. The burst is 45 frames the app seals
    itself, so every one is a valid frame; a plaintext flood would be rejected
    before the counter and would never reach the rule.
    """
    text = app_text(app)
    m = re.search(r'MAX_ROWS\s*=\s*(\d+)', text)
    expect(m and int(m.group(1)) == 2000, 'no 2000 row transcript cap in the artifact')
    expect(re.search(r'children\.length\s*>\s*MAX_ROWS', text), 'no trim loop against the row cap')
    expect(re.search(r'frameTimes\.length\s*>\s*40', text), 'no A8 40 frame rule in the artifact')
    expect(re.search(r'2\s*\*\s*1024\s*\*\s*1024', text), 'no A8 2 MB byte rule in the artifact')
    b, a, c = open_app(app)
    path = scratch_file('probe.bin', b'Z' * 4096)
    try:
        # One refused file-start must not poison the next transfer (F-04).
        expect(c.js("window.__probe.mutate('file-bad-start')"), 'bad start mutation not armed')
        c.set_file('#file', path)
        expect(wait_log(a, r'refused|invalid|rejected|fail', 15), 'a bad file-start left no visible refusal')
        expect_eq(open_channel(a), True, 'a bad file-start closed the channel')
        expect(send_file_and_wait(c, a, path), 'a later valid transfer was refused after a poisoned start (F-04)')

        # A8: 45 valid sealed frames in one burst.
        marker = 'PROBE-BUDGET-OK'
        fill(c, '#input', marker)
        click(c, '#send')
        expect(recv_marker(a, marker, 8), 'the pre-burst message did not arrive')
        a.js("""(() => {
          const i = document.querySelector('#input');
          const s = document.querySelector('#send');
          for (let n = 0; n < 45; n++) { i.value = 'PROBE-A8-' + n; s.click(); }
          return true;
        })()""")
        expect(ended_or_blank(c, 12), '45 valid frames in a burst did not trip the A8 rate rule')
        expect(re.search(r'A8|frame rate', ended_text(c), re.I),
               'the kill did not name the A8 frame rate rule: %r' % (ended_text(c)[:160],))
    finally:
        b.close()
        shutil.rmtree(os.path.dirname(path), ignore_errors=True)


def case_code(app, opts):
    """R2-07: paste cap, decompressed cap, TTL, candidate cap before setRemoteDescription."""
    text = app_text(app)
    expect(re.search(r'CODE_MAX\s*=\s*16\s*\*\s*1024', text), 'no 16 KB paste cap')
    expect(re.search(r'text\.length\s*>\s*65536', text), 'no 64 KB decompressed cap')
    expect(re.search(r'TTL_MS\s*=\s*120000', text), 'no 120 s code TTL')
    expect(re.search(r'CAND_MAX\s*=\s*32\b', text), 'no candidate cap of 32')

    b = Browser()
    try:
        ca = b.context()
        a = b.page(ca)
        c = b.page(b.context())
        for p in (a, c):
            p.init(SHIM)
        a.goto(app_url(app))
        c.goto(app_url(app))
        wait_enabled(a, '#create')
        click(a, '#create')
        a.wait("(() => { const e = document.querySelector('#offer'); return !!e && e.value.length > 40; })()",
               timeout=25, what='invite code')
        code = a.js("document.querySelector('#offer').value")

        peers0 = snapshot(c)['peers']
        fill(c, '#offerIn', 'A' * 20000)
        click(c, '#join')
        time.sleep(1.5)
        expect_eq(snapshot(c)['peers'], peers0, 'an oversized paste created a peer before the cap')
        expect(wait_log(c, r'too long|16|cap|limit|invalid|valid', 4) or body_text(c).strip(),
               'oversized paste left no visible rejection')

        # 40 candidates in a well formed SDP must be refused before setRemoteDescription.
        def add_candidates(payload):
            extra = ''.join('a=candidate:probe%d 1 udp 2130706431 10.0.0.%d 9000 typ host\r\n' % (i, i + 1)
                            for i in range(40))
            if 'a=candidate' not in payload:
                return payload
            return payload + extra

        tampered = mutate_code(code, add_candidates)
        expect(tampered != code, 'candidate injection did not change the code')
        peers1 = snapshot(c)['peers']
        fill(c, '#offerIn', tampered)
        click(c, '#join')
        time.sleep(1.5)
        expect_eq(snapshot(c)['peers'], peers1, 'an SDP with 40 candidates reached setRemoteDescription')

        bad_version = 'E2.9.' + code.split('.', 2)[-1] if code.startswith('E2.') else 'ZZ9.' + code.split('.', 1)[-1]
        fill(c, '#offerIn', bad_version)
        click(c, '#join')
        time.sleep(1.2)
        expect_eq(snapshot(c)['peers'], peers1, 'an unknown code version created a peer')
    finally:
        b.close()


def case_lifecycle(app, opts):
    """R2-08: pagehide wipes codes, draft, log, blob URLs and the channel.

    The blob counter excludes the Worker script URL, which the app creates but
    never puts in its revoke list, and the case's own synthetic URL. Every app
    media URL it created is asserted revoked on the final DOM.
    """
    b, a, c = open_app(app)
    try:
        path = scratch_file('probe.png', TINY_PNG)
        c.set_file('#file', path)
        img = wait_image(a, 20)
        expect(img.get('src'), 'no received image URL to revoke on pagehide')

        fill(a, '#input', 'PROBE-DRAFT')
        synthetic = a.js("URL.createObjectURL(new Blob([new Uint8Array(32)]))")
        a.js("window.dispatchEvent(new PageTransitionEvent('pagehide'))")
        time.sleep(1.2)

        for sel in ('#offer', '#answer', '#offerIn', '#answerIn', '#input'):
            value = a.js("(() => { const e = document.querySelector(%s); return e ? e.value : ''; })()" % jsval(sel))
            expect_eq(value, '', 'pagehide left %s filled' % sel)
        expect_eq(a.js("document.querySelector('#file').value"), '', 'pagehide left the file input filled')
        rows = a.js("document.querySelector('#log') ? document.querySelector('#log').children.length : -1")
        expect_eq(rows, 0, 'pagehide left transcript rows')
        expect_eq(a.js("document.querySelector('#gallery').hidden"), True, 'pagehide left the gallery open')
        expect_eq(a.js("document.querySelector('#about').hidden"), True, 'pagehide left the about panel open')

        snap = snapshot(a)
        created = [x for x in snap['blobCreated'] if x.get('url') != synthetic and x.get('type') != 'text/javascript']
        revoked = set(snap['blobRevoked'])
        live = [x for x in created if x.get('url') not in revoked]
        expect(not live, 'pagehide left an app blob URL live: %r' % (live[:2],))
        expect(img.get('src') in revoked, 'the received media URL was not revoked on pagehide')
        expect(snap['lastRevoke'] and snap['lastRevoke'].get('liveNodes') == 0,
               'pagehide revoked a URL before its DOM node was removed: %r' % (snap['lastRevoke'],))
        expect(all(ch.get('state') != 'open' for ch in snap['channels']),
               'pagehide left a data channel open')

        p = b.page(b.context())
        p.init(SHIM)
        p.goto(app_url(app) + '?idle=5')
        time.sleep(8)
        ended = p.js("(() => { const e = document.querySelector('#ended'); return !!e && !e.hidden; })()")
        expect_eq(ended, False, '?idle=5 still shortens the session (F-10)')
    finally:
        b.close()


def case_kill(app, opts):
    """R2-09: wipe enabled before connect, DOM cleared before revoke, clipboard clear, about:blank.

    The wipe button asks with a native confirm. The harness installs a CDP
    dialog handler so the dialog is accepted out of band and no longer blocks
    the renderer. A copied code is required for the clipboard clear branch, so
    the shim records writeText calls instead of touching the OS clipboard.
    """
    app_text(app)
    b = Browser()
    try:
        a = b.page(b.context())
        a.init(SHIM)
        a.goto(app_url(app))
        expect_eq(a.js("(() => { const e = document.querySelector('#wipe'); return !!e && !e.disabled; })()"),
                  True, 'wipe is disabled before connect')
        a.js("(() => { const i = document.querySelector('#input') || document.body; i.focus(); return true; })()")
        a.js("""(() => {
          const t = { key: 'Escape', code: 'Escape', bubbles: true };
          document.dispatchEvent(new KeyboardEvent('keydown', t));
          setTimeout(() => document.dispatchEvent(new KeyboardEvent('keydown', t)), 120);
          return true;
        })()""")
        expect(ended_or_blank(a, 8), 'double Escape did not run kill')
    finally:
        b.close()

    b, a, c = open_app(app, copy_offer=True)
    path = scratch_file('probe.png', TINY_PNG)
    try:
        c.set_file('#file', path)
        img = wait_image(a, 20)
        expect(img.get('src'), 'received image has no live blob node, cannot check revoke ordering')
        expect_eq(a.js("document.querySelectorAll('#log img[src^=\"blob:\"]').length") >= 1, True,
                  'received image node is not in the log')
        b.auto_dialog = True
        click(a, '#wipe')
        time.sleep(0.8)
        snap = snapshot(a)
        expect(snap['domAtRevoke'], 'no revoke was observed during wipe')
        expect(all(x == 0 for x in snap['domAtRevoke']),
               'blob URL revoked while its DOM node was still live: %r' % (snap['domAtRevoke'],))
        expect('' in snap['clipWrites'], 'the kill path did not clear the copied code from the clipboard')
        wait_blank(a, 10)
    finally:
        b.close()
        shutil.rmtree(os.path.dirname(path), ignore_errors=True)


def case_rotate(app, opts):
    """R2-10: rotate rekeys, the pre-rotate epoch is rejected, the session survives."""
    text = app_text(app)
    expect('rekey' in text, 'no rekey frame in the artifact')
    expect('eph-v2-rekey' in text, 'no dedicated rekey info string')
    b, a, c = open_app(app)
    try:
        marker = 'PROBE-ROT-1'
        fill(a, '#input', marker)
        click(a, '#send')
        expect(recv_marker(c, marker, 8), 'pre-rotate message did not arrive')
        old = snapshot(a)['lastRaw']
        expect(old, 'no binary wire frame captured to replay')

        expect(a.js("(() => { const b = document.querySelector('#rotate'); return !!b && !b.disabled; })()"),
               'no enabled #rotate control in the UI')
        click(a, '#rotate')
        time.sleep(2.5)

        expect(a.js("window.__probe.sendB64(%s)" % jsval(old)),
               'no open channel to replay the pre-rotate frame')
        time.sleep(1.8)
        seen = log_text(c).count(marker)
        expect(seen <= 1, 'the pre-rotate frame was rendered again, old epoch is live: got %d' % seen)

        if not ended_or_blank(a, 1):
            marker2 = 'PROBE-ROT-2'
            fill(a, '#input', marker2)
            click(a, '#send')
            expect(recv_marker(c, marker2, 8), 'no traffic after rotate, the session did not survive')
    finally:
        b.close()


def case_migrate(app, opts):
    """R2-11: tampered M1 fp is refused, a real migration commits with fresh keys.

    V2 wipes the old epoch and demands a fresh SAS comparison after adopt, so
    the case confirms the new safety number before it asserts content on the
    migrated channel. The fresh keyset is proven by a different 60 digit SAS on
    both peers, not by a channel count alone.
    """
    text = app_text(app)
    expect('mig' in text, 'no migration frame in the artifact')
    expect(re.search(r"migFail\('timeout'\),\s*15000", text), 'no 15 s migration timeout')
    b, a, c = open_app(app)
    try:
        old_sas = sas_digits(a)
        expect(len(old_sas) == 60, 'no pre-migration SAS to compare against')
        peers0 = snapshot(a)['peers']

        expect(a.js("(() => { const b = document.querySelector('#migrate'); return !!b && !b.disabled; })()"),
               'no enabled #migrate control in the UI')
        click(a, '#migrate')
        end = time.time() + 35
        state = None
        while time.time() < end:
            sa = snapshot(a)
            sc = snapshot(c)
            opened = [x for x in sa['channels'] if x['state'] == 'open']
            closed = [x for x in sa['channels'] if x['state'] == 'closed']
            state = (len(sa['channels']), len(sc['channels']), len(opened), len(closed))
            if len(sa['channels']) >= 2 and opened and closed and len(sc['channels']) >= 2:
                break
            time.sleep(0.4)
        expect(len(snapshot(a)['channels']) >= 2 and len(snapshot(c)['channels']) >= 2,
               'migration did not open a new channel on both peers, last=%r' % (state,))
        expect(snapshot(a)['peers'] > peers0, 'migration did not create a new peer connection')

        # The old channel is closed and content is locked again until the new
        # safety number is compared on both sides.
        end = time.time() + 12
        new_a = ''
        new_c = ''
        while time.time() < end:
            new_a = sas_digits(a)
            new_c = sas_digits(c)
            if len(new_a) == 60 and len(new_c) == 60 and new_a != old_sas:
                break
            time.sleep(0.3)
        expect(len(new_a) == 60 and len(new_c) == 60,
               'the migrated peers show no 60 digit safety number, got %r/%r' % (len(new_a), len(new_c)))
        expect(new_a != old_sas, 'the safety number did not change, the keyset is not fresh')
        expect_eq(new_a, new_c, 'the new safety number differs between peers')
        expect(content_locked(a) and content_locked(c),
               'the composer unlocked after migration before the new SAS was confirmed')

        confirm_sas(a, c)
        end = time.time() + 20
        while time.time() < end and (content_locked(a) or content_locked(c)):
            time.sleep(0.3)
        expect(not content_locked(a) and not content_locked(c),
               'the composer did not unlock after the new SAS was confirmed on both sides')

        marker = 'PROBE-MIG-OK'
        fill(a, '#input', marker)
        click(a, '#send')
        expect(recv_marker(c, marker, 10), 'no traffic on the migrated channel')

        # A tampered fp in M1 must not commit. The frame is sealed by the app;
        # the shim rewrites one plaintext field before encryption.
        expect(a.js("window.__probe.mutate('mig-bad-fp')"), 'fp mutation not armed')
        click(a, '#migrate')
        expect(ended_or_blank(a, 20), 'a tampered migration fingerprint still committed')
        expect(re.search(r'Migration failed|migration failed',
                         (a.js("document.querySelector('#endedTitle') ? document.querySelector('#endedTitle').textContent : ''") or '')
                         + ' ' + ended_text(a), re.I),
               'a tampered migration did not report a migration failure')
    finally:
        b.close()


def case_stun(app, opts):
    """R2-12: three STUN providers, no relay in default mode, disclosure and error split."""
    text = app_text(app)
    providers = sorted(set(re.findall(r'stun:[A-Za-z0-9.\-:]+', text)))
    expect(len(providers) >= 3, 'fewer than three STUN providers in the ICE config: %r' % (providers,))
    expect(not re.search(r'turns?:', text), 'relay configuration present in the default artifact')
    expect(re.search(r'public IP|peer IP|IP address|exposes', text, re.I), 'no peer address disclosure copy')
    expect(re.search(r'network blocked|network is', text, re.I) or re.search(r'blocked', text, re.I),
           'no network blocked error path')

    b = Browser()
    try:
        p = b.page(b.context())
        p.init(SHIM)
        p.goto(app_url(app))
        wait_enabled(p, '#create')
        click(p, '#create')
        p.wait("(() => { const e = document.querySelector('#offer'); return !!e && e.value.length > 40; })()",
               timeout=25, what='invite code')
        servers = p.js('window.__probe.iceServers()') or []
        urls = []
        for entry in servers:
            u = entry.get('urls') if isinstance(entry, dict) else None
            if isinstance(u, str):
                urls.append(u)
            elif isinstance(u, list):
                urls.extend(u)
        expect(len(urls) >= 3, 'live ICE config has fewer than three STUN URLs: %r' % (urls,))
        expect(all(u.startswith('stun:') for u in urls), 'non STUN server in the default ICE config: %r' % (urls,))

        code = p.js("document.querySelector('#offer').value")
        payload = decode_code(code)
        expect('typ relay' not in payload, 'the invite code carries a relay candidate in default mode')
    finally:
        b.close()


def case_cover(app, opts):
    """R2-13: no relay in the default artifact, relay-only policy leaks no host or srflx."""
    host = opts.get('relay_host')
    if not host:
        raise CannotRun('--relay-host is required, for example turn:127.0.0.1:5349')
    text = app_text(app)
    expect(not re.search(r'turns?:', text), 'default artifact carries a relay URL')
    expect(host not in text, 'default artifact carries the supplied relay host')
    b = Browser()
    try:
        p = b.page(b.context())
        p.goto('about:blank')
        p.js("""(() => {
          window.__c = { list: [] };
          window.__pc = new RTCPeerConnection({
            iceServers: [{ urls: %s, username: 'probe', credential: 'probe' }],
            iceTransportPolicy: 'relay'
          });
          window.__pc.onicecandidate = function (e) { if (e.candidate) { window.__c.list.push(e.candidate.candidate); } };
          window.__pc.createDataChannel('x');
          return window.__pc.createOffer()
            .then(function (o) { return window.__pc.setLocalDescription(o); })
            .then(function () { return true; });
        })()""" % jsval(host))
        time.sleep(5)
        cands = p.js('window.__c.list') or []
        bad = [x for x in cands if 'typ host' in x or 'typ srflx' in x]
        expect(not bad, 'relay-only policy emitted host or srflx candidates: %r' % (bad[:2],))
    finally:
        b.close()


def case_media_order(app, opts):
    """R2-16: compress before pad before encrypt, 4 KiB buckets, true length in the AAD.

    WebCodecs is absent under the headless disable-gpu Chromium, so engine A is
    asserted structurally here. The behavioral half reads the sealed wire: every
    control frame lands on a 4096 byte bucket and every media chunk is the raw
    encoded bytes with no gzip pass.
    """
    text = app_text(app)
    expect(re.search(r'PAD\s*=\s*4096', text), 'no 4 KiB padding bucket in the artifact')
    fp = extract_js_function(text, 'framePlain')
    sc = extract_js_function(text, 'sealControl')
    oc = extract_js_function(text, 'openControl')
    expect('gzipBytes' in fp and 'padded' in fp, 'framePlain does not compress and pad')
    expect(fp.index('gzipBytes') < fp.index('padded'),
           'padding runs before compression, the entropy coder has less to remove')
    expect(sc.index('framePlain') < sc.index('additionalData: aad('),
           'encryption runs before compression in sealControl')
    expect('plain.length + 16' in sc, 'the padded length is not bound in the AAD')
    expect('bytes.length !== pt.length + 16' in oc and 'padding is not zero' in oc,
           'openControl does not assert the length and zero padding')
    chunk = extract_js_function(text, 'sendChunk')
    expect('gzip' not in chunk, 'sendChunk attempts a gzip pass over encoded media bytes')

    b, a, c = open_app(app)
    try:
        start = len(snapshot(c)['wire'])
        fill(c, '#input', 'PROBE-PAD-1')
        click(c, '#send')
        time.sleep(0.8)
        frames = [f for f in wire_since(c, start) if f.get('head') == 1]
        expect(frames, 'no sealed control frame captured')
        for f in frames:
            body = f['len'] - 1 - 16
            expect(body >= 4096 and body % 4096 == 0,
                   'a control frame is off the 4096 byte bucket: body=%d' % body)

        path = scratch_file('probe.png', png_bytes(64, 64, metadata=False))
        start = len(snapshot(c)['wire'])
        c.set_file('#file', path)
        img = wait_image(a, 20)
        rec = media_for(a, img['src'])
        expect(rec, 'no sent image bytes captured for the chunk check')
        chunks = [f for f in wire_since(c, start) if f.get('head') == 2]
        expect(chunks, 'no binary media chunk captured')
        expect_eq(chunks[0]['len'] - 17, rec['size'],
                  'the chunk frame is not the raw encoded bytes plus the GCM tag')
        expect_eq(rec['type'] in ('image/webp', 'image/jpeg'), True,
                  'media re-encode produced an unexpected type: %r' % (rec['type'],))
    finally:
        b.close()
        try:
            shutil.rmtree(os.path.dirname(path), ignore_errors=True)
        except NameError:
            pass


def case_exif(app, opts):
    """R2-17: no Exif, GPS, XMP or ICC marker survives the re-encode, type is honest."""
    text = app_text(app)
    expect(len(re.findall(r'encodeImage\s*\(', text)) == 2,
           'encodeImage is called outside the single acceptFile path')
    accept = extract_js_function(text, 'acceptFile')
    expect('encodeImage(file, name)' in accept, 'acceptFile does not own the image re-encode')
    qf = extract_js_function(text, 'queueFiles')
    expect('acceptFile(file' in qf, 'the drop and paste queue does not route through acceptFile')
    expect('sendFile' in text and 'acceptFile(file' in extract_js_function(text, 'sendFile'),
           'the picker does not route through acceptFile')

    source = png_bytes(64, 64, metadata=True)
    expect(b'Exif' in source and b'GPS' in source, 'the metadata fixture is not carrying markers')
    path = scratch_file('probe-meta.png', source)
    b, a, c = open_app(app)
    try:
        c.set_file('#file', path)
        img = wait_image(a, 20)
        rec = media_for(a, img['src'])
        expect(rec, 'no re-encoded image bytes captured')
        expect(rec['type'] in ('image/webp', 'image/jpeg'),
               'the sent image is not a re-encode target: %r' % (rec['type'],))
        raw = decode_b64(rec['b64'])
        for token in (b'Exif', b'GPS', b'XMP', b'iCCP', b'eXIf', b'Comment'):
            expect(token not in raw, 'metadata marker survived the re-encode: %s' % token.decode('ascii'))
        name = log_text(a)
        expect(re.search(r'\.(webp|jpg)\b', name), 'the received name does not match the encoded type')
        expect(not re.search(r'\.png\b', name), 'the original PNG name was kept over the re-encode')
        for rec2 in snapshot(a)['media']:
            if rec2.get('type', '').startswith('image/'):
                raw2 = decode_b64(rec2['b64'])
                expect(b'Exif' not in raw2 and b'eXIf' not in raw2,
                       'a second image blob still carries metadata')
    finally:
        b.close()
        shutil.rmtree(os.path.dirname(path), ignore_errors=True)


def case_bitrate(app, opts):
    """R2-19: projection before commit, 45 MiB cap, one retry formula, named refusal.

    planBitrate is extracted and executed with the artifact's own VIDEO_CAP, so
    the card's numbers are checked as behavior. Engine A is structural: the
    decoderConfig assertion must run before finalize, frames close in finally,
    and the queue is bounded at 8. Headed engine A execution is R4 work.
    """
    text = app_text(app)
    expect(re.search(r'VIDEO_CAP\s*=\s*47185920', text), 'no exact 47,185,920 B video cap')
    expect(re.search(r'Math\.floor\(VIDEO_CAP\s*\*\s*0\.90\)', text), 'no 90 percent bitrate budget')
    expect('projected' in text and 'about ' in text, 'no projected size shown before commit')
    expect('Send video' in text, 'no explicit send control on the projection card')
    expect(re.search(r'plan\.bitrate\s*\*\s*\(VIDEO_CAP\s*/\s*blob\.size\)\s*\*\s*0\.95', text),
           'no single retry at bitrate * (cap / size) * 0.95')
    expect(re.search(r'still\s*.*formatSize\(blob\.size\)|formatSize\(blob\.size\).*after one retry', text),
           'the refusal does not name the size actually reached')

    ta = extract_js_function(text, 'transcodeA')
    expect(ta.index('decoderConfig') < ta.index('muxer.finalize()'),
           'the muxer finalizes before the decoderConfig assertion')
    expect('frame.close()' in ta, 'a VideoFrame is leaked without close()')
    expect(re.search(r'encodeQueueSize\s*>\s*8', ta), 'the encode queue is not bounded at 8')
    expect(re.search(r'\}\s*finally\s*\{', ta), 'no finally block in transcodeA')
    tb = extract_js_function(text, 'transcodeAndSend')
    expect('transcodeB' in tb, 'no MediaRecorder rung B fallback')

    src = extract_js_function(text, 'planBitrate')
    b = Browser()
    try:
        p = b.page(b.context())
        p.goto('about:blank')
        # The evaluated source is the artifact under test, read from the local
        # file. No user or peer input reaches this string; this is a unit probe
        # of planBitrate with the artifact's own VIDEO_CAP constant.
        out = p.js("""(() => {
          const src = %s;
          const fn = new Function('VIDEO_CAP', 'return (' + src + ')');
          const f = fn(47185920);
          return { short: f(10, 1920, 1080), mid: f(120, 1920, 1080),
                   long: f(300, 1920, 1080), max: f(600, 1920, 1080),
                   over: f(601, 1920, 1080), zero: f(0, 1920, 1080) };
        })()""" % jsval(src))
    finally:
        b.close()
    expect(out, 'planBitrate could not be executed')
    budget = 47185920 * 9 // 10
    expect_eq(out['short']['projected'], budget, 'projected budget')
    expect_eq(out['short']['bitrate'], max(120000, (budget - 120000) * 8 // 10), 'ten second bitrate')
    expect_eq(out['short']['height'], 1080, 'ten second resolution cap')
    expect_eq(out['mid']['height'], 720, 'two minute resolution cap')
    expect_eq(out['long']['height'], 480, 'five minute resolution cap')
    expect_eq(out['max']['height'], 480, 'ten minute resolution cap')
    expect(out['over'] is None, 'a clip over 600 s still plans a bitrate')
    expect(out['zero'] is None, 'a zero duration clip still plans a bitrate')
    expect_eq(out['short']['seconds'], int(10 * 1.04 + 0.999999), 'processing seconds projection')


def case_playback(app, opts):
    """R2-20: media-src blob: is present, a received video plays from RAM, revoke follows DOM.

    The video is generated in the page with MediaRecorder and dropped through
    the real drop path, so this is the live rung B pipeline, not a mock.
    """
    text = app_text(app)
    expect(re.search(r'media-src\s+blob:', text), 'media-src blob: is missing from the CSP')
    expect(re.search(r'video\.src\s*=|\.preview\(', text), 'no video src assignment path')
    b, a, c = open_app(app)
    try:
        made = c.js("""(() => new Promise((resolve) => {
          const cv = document.createElement('canvas');
          cv.width = 64; cv.height = 64;
          const ctx = cv.getContext('2d');
          ctx.fillStyle = '#2a6'; ctx.fillRect(0, 0, 64, 64);
          if (!window.MediaRecorder || !cv.captureStream) { resolve({ ok: false, why: 'no MediaRecorder' }); return; }
          const mime = MediaRecorder.isTypeSupported('video/webm;codecs=vp8') ? 'video/webm' : '';
          if (!mime) { resolve({ ok: false, why: 'no webm encoder' }); return; }
          const rec = new MediaRecorder(cv.captureStream(24), { mimeType: mime });
          const parts = [];
          rec.ondataavailable = (e) => { if (e.data && e.data.size) parts.push(e.data); };
          rec.onstop = () => {
            const blob = new Blob(parts, { type: 'video/webm' });
            const dt = new DataTransfer();
            dt.items.add(new File([blob], 'clip.webm', { type: 'video/webm' }));
            document.dispatchEvent(new DragEvent('drop', { dataTransfer: dt, bubbles: true, cancelable: true }));
            resolve({ ok: true, size: blob.size });
          };
          rec.start();
          setTimeout(() => { try { rec.stop(); } catch (e) {} }, 700);
        }))()""", timeout=60)
        expect(made and made.get('ok'), 'could not generate a video in the page: %r' % (made,))
        v = wait_video(a, 25)
        expect(v.get('err') is None, 'video error %r under the CSP' % (v.get('err'),))
        expect(v.get('ready') >= 1, 'video readyState is %r, media-src is not effective' % (v.get('ready'),))
        expect((v.get('w') or 0) > 0 and (v.get('dur') or 0) > 0,
               'video has no dimensions or duration: %r' % (v,))
        rec = media_for(a, v['src'])
        expect(rec and rec.get('type', '').startswith('video/'), 'the received video blob was not captured')

        b.auto_dialog = True
        click(a, '#wipe')
        time.sleep(0.8)
        snap = snapshot(a)
        expect(v['src'] in snap['blobRevoked'], 'the received video URL was not revoked on wipe')
        expect(all(x == 0 for x in snap['domAtRevoke']),
               'a blob URL was revoked while its node was still live: %r' % (snap['domAtRevoke'],))
        wait_blank(a, 10)
    finally:
        b.close()


def case_imagecap(app, opts):
    """R2-21: the 60 MP gate runs before canvas allocation, bitmap closes in finally.

    A fake createImageBitmap reports a 200 MP bitmap, so the gate is exercised
    without allocating the image. The real small image then proves the 1080p
    long edge ladder downscales before send.
    """
    text = app_text(app)
    expect(re.search(r'IMAGE_MAX_PX\s*=\s*60000000', text), 'no 60,000,000 px image gate')
    enc = extract_js_function(text, 'encodeImage')
    gate_at = enc.index('px > IMAGE_MAX_PX')
    canvas_at = enc.index("document.createElement('canvas')")
    expect(gate_at < canvas_at, 'the destination canvas is allocated before the 60 MP gate')
    expect('bitmap.close()' in enc and 'finally' in enc, 'bitmap.close() is not in a finally')

    b, a, c = open_app(app)
    try:
        c.js("""(() => {
          window.__fake = { closed: 0 };
          window.__realCIB = createImageBitmap;
          createImageBitmap = function () {
            return Promise.resolve({ width: 20000, height: 10000, close: function () { window.__fake.closed++; } });
          };
          return true;
        })()""")
        start = len(snapshot(c)['wire'])
        item = {'name': 'huge.png', 'type': 'image/png',
                'b64': base64.b64encode(png_bytes(8, 8, metadata=False)).decode('ascii')}
        dispatch_files(c, [item], 'paste')
        expect(wait_log(c, r'60 MP|pixel|refused', 12), 'the 60 MP gate left no visible refusal')
        time.sleep(0.8)
        expect_eq(c.js('window.__fake.closed'), 1, 'the refused bitmap was not closed in finally')
        expect_eq(len(wire_since(c, start)), 0, 'a refused 200 MP image still produced wire frames')

        c.js("createImageBitmap = window.__realCIB; true")
        item2 = {'name': 'wide.png', 'type': 'image/png',
                 'b64': base64.b64encode(png_bytes(2000, 10, metadata=False)).decode('ascii')}
        dispatch_files(c, [item2], 'paste')
        img = wait_image(a, 20)
        expect(0 < img.get('w', 0) <= 1600, 'the long edge was not capped at 1600: %r' % (img.get('w'),))
        expect(0 < img.get('h', 0) <= 1600, 'the short edge is out of range: %r' % (img.get('h'),))
    finally:
        b.close()


def case_paste(app, opts):
    """R2-22: one acceptFile path, text paste not intercepted, counter names, one transcode.

    Drop and paste both route through acceptFile; a text-only paste is not
    prevented, so normal typing is untouched. Two unnamed pasted images get
    counter names, not a timestamp.
    """
    text = app_text(app)
    expect(len(re.findall(r'acceptFile\s*\(', text)) >= 2, 'no acceptFile entry point')
    qf = extract_js_function(text, 'queueFiles')
    expect('acceptFile(file' in qf, 'queueFiles does not route through acceptFile')
    expect('acceptFile(file' in extract_js_function(text, 'sendFile'), 'sendFile does not route through acceptFile')
    expect(re.search(r'function synthName\(type, source\)\s*\{[^}]*draftSeq\+\+', text),
           'synthName does not use a counter')
    expect('Date.now' not in extract_js_function(text, 'synthName'), 'synthName uses a timestamp')
    expect(re.search(r'if\s*\(transcoding\)', text) and 'transcoding = true' in text,
           'no single transcode guard')

    b, a, c = open_app(app)
    try:
        got = dispatch_text_paste(c, 'PROBE-TEXT-PASTE')
        expect_eq(got.get('prevented'), False, 'a text-only paste was intercepted')

        tiny = base64.b64encode(png_bytes(16, 16, metadata=False)).decode('ascii')
        items = [{'name': '', 'type': 'image/png', 'b64': tiny},
                 {'name': '', 'type': 'image/png', 'b64': tiny}]
        out = dispatch_files(c, items, 'paste')
        expect_eq(out.get('files'), 2, 'two pasted files were not carried by the event')
        end = time.time() + 25
        while time.time() < end:
            n = a.js("document.querySelectorAll('#log img[src^=\"blob:\"]').length") or 0
            if n >= 2:
                break
            time.sleep(0.25)
        expect((a.js("document.querySelectorAll('#log img[src^=\"blob:\"]').length") or 0) >= 2,
               'a pasted image skipped the acceptFile send path')
        log = log_text(a)
        expect('paste-1' in log and 'paste-2' in log,
               'the synthesized names are not counter based: %r' % (log[-300:],))
        expect(not re.search(r'paste-\d{10,}', log), 'the synthesized name embeds a timestamp')
    finally:
        b.close()


GUARDS = [
    # Patterns are pinned to the landed V2 spellings. Every pattern must match,
    # and the first match must be the guard site named in its comment. Each
    # pattern names the constant or expression it guards, not a bare number, so
    # the mutation cannot hit an unrelated site.
    ('code-cap', r'CODE_MAX\s*=\s*16\s*\*\s*1024', 'CODE_MAX = 1000000000', 'code',
     'the 16 KB paste cap is removed, an oversized paste must now reach the parser'),
    ('preparse-cap', r'text\.length\s*>\s*65536', 'text.length > 1000000000', 'code',
     'the 64 KB decompressed cap is removed'),
    ('ttl', r'TTL_MS\s*=\s*120000', 'TTL_MS = 1000000000', 'code',
     'the 120 s code TTL is removed'),
    ('row-cap', r'MAX_ROWS\s*=\s*2000', 'MAX_ROWS = 20', 'budget',
     'the transcript row cap is lowered so the static assertion must fail'),
    ('kill-nav', r'about:blank', 'about:log', 'kill',
     'kill no longer navigates to about:blank'),
    # V2 spells the lock as three disabled flags before showScreen('S2') and
    # showSas(), not as a named sasOk/sasVerified boolean.
    ('sas-lock', r'el\.input\.disabled = true;\s*\n\s*el\.send\.disabled = true;\s*\n'
                 r'\s*el\.attach\.disabled = true;\s*\n\s*showScreen\(\'S2\'\);\s*\n\s*showSas\(\);',
     "el.input.disabled = false; el.send.disabled = false; el.attach.disabled = false; showScreen('S2'); showSas();",
     'sas', 'the pre-confirm composer lock is removed, content is usable before SAS confirmation'),
    # V2 compares the running byte count against the declared size on the
    # prefixed fields, not bare received === size.
    ('completeness', r'f\.received\s*!==\s*f\.size', 'false', 'file',
     'the completeness check before Save is forced true'),
]


def run_gate_case(case, app):
    env = dict(os.environ)
    env['GATE_NO_EVIDENCE'] = '1'
    proc = subprocess.run(
        [sys.executable, os.path.abspath(__file__), case, '--app', app],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=240, env=env)
    lines = (proc.stdout or b'').decode('utf-8', 'replace').strip().splitlines()
    return proc.returncode, (lines[-1] if lines else '')


def case_mutation(app, opts):
    """R2-15: every reverted guard must change the verdict of its matching case."""
    text = app_text(app)
    work = tempfile.mkdtemp(prefix='gate-mutation-')
    baseline = {}
    try:
        missing = [name for name, pattern, _, _, _ in GUARDS if not re.search(pattern, text)]
        expect(not missing, 'guards not found in the artifact: %s' % ', '.join(missing))
        for _, _, _, case, _ in GUARDS:
            if case in baseline:
                continue
            rc, last = run_gate_case(case, app)
            if rc == 2:
                raise CannotRun('case %s cannot run on the artifact, mutation has no baseline: %s' % (case, last))
            baseline[case] = (rc, last)

        for name, pattern, repl, case, why in GUARDS:
            m = re.search(pattern, text)
            if not m:
                raise Fail('guard %s not found, cannot mutate it: %s' % (name, why))
            scratch = os.path.join(work, name + '.html')
            with open(scratch, 'w') as fh:
                fh.write(text[:m.start()] + repl + text[m.end():])
            rc, last = run_gate_case(case, scratch)
            expect_eq(rc, 1, 'guard %s reverted but %s exited %d (%s): %s'
                      % (name, case, rc, last, why))
            base_rc, base_last = baseline[case]
            if base_rc == 1:
                expect(last != base_last,
                       'guard %s reverted but %s failed with the same reason as the unmutated artifact '
                       '(%s), the mutation changed nothing' % (name, case, base_last))
    finally:
        shutil.rmtree(work, ignore_errors=True)


ESC = ("(() => { const t = { key: 'Escape', code: 'Escape', bubbles: true };"
       " document.dispatchEvent(new KeyboardEvent('keydown', t)); return true; })()")


def case_panic(app, opts):
    """UX-06: wipe is always enabled, one Escape closes a layer, and the ended
    panel carries no session id. A dismissed confirm must not wipe."""
    text = app_text(app)
    tag = re.search(r'<button[^>]*id="wipe"[^>]*>', text)
    tag_text = tag.group(0) if tag else ''
    expect(tag_text, 'no wipe button in the artifact')
    expect('disabled' not in tag_text, 'the wipe button ships disabled')
    expect(not re.search(r'el\.wipe\.disabled\s*=\s*true', text),
           'a code path disables the wipe button')

    b, a, c = open_app(app, confirm=False)
    try:
        # A fresh page before pairing: wipe is usable at S0.
        d = b.page(b.context())
        d.init(SHIM)
        d.goto(app_url(app))
        expect_eq(d.js('document.body.dataset.screen'), 'S0', 'fresh page screen')
        expect_eq(d.js("(() => { const e = document.querySelector('#wipe'); return !!e && !e.disabled; })()"),
                  True, 'wipe disabled before connect')
        expect_eq(d.js("(() => { const p = document.querySelector('#pairing'); return !!p && !p.hidden; })()"),
                  True, 'pairing panel hidden at S0')

        expect_eq(a.js('document.body.dataset.screen'), 'S2', 'connected screen')
        expect_eq(a.js("(() => !document.querySelector('#wipe').disabled)()"), True,
                  'wipe disabled after connect')

        sid = json.loads(decode_code(a.js("document.querySelector('#offer').value")))['sid']
        expect(re.match(r'^[0-9a-f]{32}$', sid), 'the invite carries no 32 hex session id')

        # The layer rule: one Escape closes the sheet, it never wipes.
        click(a, '#chipFiles')
        expect_eq(a.js("(() => !document.querySelector('#gallery').hidden)()"), True, 'gallery did not open')
        a.js(ESC)
        expect_eq(a.js("(() => document.querySelector('#gallery').hidden)()"), True,
                  'one Escape did not close the gallery')
        expect_eq(a.js('document.body.dataset.screen'), 'S2', 'Escape inside the gallery ended the session')
        click(a, '#chipAbout')
        expect_eq(a.js("(() => !document.querySelector('#about').hidden)()"), True, 'about did not open')
        a.js(ESC)
        expect_eq(a.js("(() => document.querySelector('#about').hidden)()"), True,
                  'one Escape did not close the about sheet')
        expect_eq(a.js('document.body.dataset.screen'), 'S2', 'Escape inside about ended the session')

        # The confirm is dismissed: the session survives.
        click(a, '#copyOffer')
        time.sleep(0.3)
        expect(snapshot(a)['clipWrites'], 'copy offer recorded no clipboard write')
        b.auto_dialog = True
        b.dialog_accept = False
        click(a, '#wipe')
        time.sleep(0.6)
        b.auto_dialog = False
        expect_eq(a.js('document.body.dataset.screen'), 'S2', 'a dismissed confirm still wiped the session')
        expect(open_channel(a), 'a dismissed confirm closed the channel')

        # Two Escapes inside 800 ms wipe, clear the clipboard, and show no sid.
        a.js(ESC)
        time.sleep(0.1)
        a.js(ESC)
        expect_eq(a.js('document.body.dataset.screen'), 'S4', 'double Escape did not wipe')
        expect_eq(a.js("(() => !document.querySelector('#ended').hidden)()"), True,
                  'ended panel is hidden after a wipe')
        expect_eq(a.js("document.querySelector('#log').children.length"), 0, 'the log survived the wipe')
        expect_eq(a.js("(() => document.querySelector('#verify').hidden)()"), True,
                  'the verify panel survived the wipe')
        txt = body_text(a)
        expect('erased' in txt.lower(), 'the ended panel does not say the session was erased')
        expect(sid not in a.js('document.body.innerHTML'), 'the session id is present in the DOM after a wipe')
        expect(not re.search(r'\b[0-9a-f]{32}\b', txt), 'a 32 hex session id is visible in the ended panel')
        writes = snapshot(a)['clipWrites']
        expect_eq(writes[-1] if writes else None, '', 'the kill path did not clear the clipboard')
        expect(not snapshot(a)['errors'], 'page errors on the panic path: %r' % (snapshot(a)['errors'],))
    finally:
        b.close()


def last_mid(page):
    return page.js("(() => { const rows = document.querySelectorAll('#log .msg');"
                   " const r = rows[rows.length - 1]; return r ? r.dataset.mid : null; })()")


def case_react(app, opts):
    """UX-02: the react frame is gated before confirm, duplicate adds do not
    double count, unknown codes never render, and the bucket turns a flood into
    a kill at five drops."""
    text = app_text(app)
    for pat, what in ((r'REACT_FRAME_MAX\s*=\s*256', 'frame cap 256'),
                      (r'REACT_SESSION_MAX\s*=\s*200', 'session cap 200'),
                      (r'REACT_BURST\s*=\s*20', 'burst 20'),
                      (r'REACT_REFILL_MS\s*=\s*250', 'refill 250 ms')):
        expect(re.search(pat, text), 'no %s' % what)
    palette = re.search(r'const PALETTE = \[(.*?)\];', text, re.S)
    expect(palette, 'no reaction palette')
    palette_body = palette.group(1) if palette else ''
    expect_eq(len(re.findall(r"\['[a-z0-9-]+',", palette_body)), 24, 'palette size')
    apply_ = extract_js_function(text, 'applyReact')
    expect(re.search(r'/\^\[0-9a-f\]\{16\}\$/', apply_), 'applyReact does not validate a 16 hex mid')
    expect('PALETTE_MAP.has(code)' in apply_, 'applyReact does not gate the shortcode')
    expect("op !== 'add' && op !== 'remove'" in apply_, 'applyReact does not gate the op')
    expect('if (!msgRows.has(mid))' in apply_, 'applyReact can resurrect a trimmed row')
    route = extract_js_function(text, 'route')
    expect(re.search(r"k === 'react' && JSON\.stringify\(msg\)\.length > REACT_FRAME_MAX", route),
           'route does not cap the react frame')
    send_react = extract_js_function(text, 'sendReact')
    expect("phase !== 'live'" in send_react, 'sendReact does not require a live session')
    expect('reactBudget()' in send_react, 'sendReact does not spend the bucket')
    pills = extract_js_function(text, 'renderPills')
    expect_eq(pills.count('(slot.me ? 1 : 0) + (slot.peer ? 1 : 0)'), 2,
              'the pill count is not the two boolean slots')
    expect('aria-pressed' in pills, 'a pill carries no aria-pressed state')
    drop = extract_js_function(text, 'dropRow')
    expect('reactions.delete(mid)' in drop and 'msgRows.delete(mid)' in drop,
           'dropping a row leaves its reaction or mid map entry')
    trim = extract_js_function(text, 'trimLog')
    expect(trim.index('dropRow(first)') < trim.index('el.log.removeChild(first)'),
           'the log trims a row before its reaction map entry is dropped')

    # A reaction that arrives before the receiver confirms is dropped.
    b, a, c = open_app(app, confirm=False)
    try:
        expect(c.js("window.__probe.armRewrite('sas-confirm',"
                    " {k: 'react', t: 'ffffffffffffffff', e: 'heart', op: 'add'}, 1)"),
               'react rewrite not armed')
        click(c, '#confirmSas')
        expect(wait_log(a, r'before verification|dropped', 6),
               'a react frame before SAS confirm left no drop line')
        expect_eq(a.js('document.body.dataset.screen'), 'S2', 'a react frame before confirm unlocked S3')
        expect_eq(a.js("document.querySelectorAll('#log .msg').length"), 0,
                  'a react frame before confirm rendered a row')
    finally:
        b.close()

    b, a, c = open_app(app)
    try:
        fill(c, '#input', 'REACT-BASE')
        click(c, '#send')
        expect(recv_marker(a, 'REACT-BASE', 8), 'the base message did not arrive')
        mid = last_mid(a)
        expect(mid and re.match(r'^[0-9a-f]{16}$', mid), 'the received row carries no 16 hex mid')

        row_open = ("(() => { const rows = document.querySelectorAll('#log .msg');"
                    " const r = rows[rows.length - 1]; const b = r && r.querySelector('.react-add');"
                    " if (!b) return false; b.click(); return !!document.querySelector('.palette'); })()")
        expect(a.js(row_open), 'the palette did not open')
        expect_eq(a.js("document.querySelectorAll('.palette button').length"), 8, 'palette button count')
        labels = a.js("Array.from(document.querySelectorAll('.palette button')).map(b => b.getAttribute('aria-label'))")
        expect(len(labels) == 8 and all(labels), 'a palette button has no accessible name')
        a.js(ESC)
        expect_eq(a.js("(() => !document.querySelector('.palette'))()"), True, 'Escape did not close the palette')

        # Two identical react adds for one mid must count once.
        expect(c.js("window.__probe.armRewrite('msg', {k: 'react', t: %s, e: 'heart', op: 'add'}, 2)" % jsval(mid)),
               'duplicate rewrite not armed')
        start = len(snapshot(c)['wire'])
        for n in (1, 2):
            fill(c, '#input', 'DUP-%d' % n)
            click(c, '#send')
            time.sleep(0.4)
        end = time.time() + 6
        marks = None
        while time.time() < end:
            marks = a.js("(() => { const r = document.querySelector('.msg[data-mid=\"%s\"]');"
                         " return r ? r.dataset.marks : null; })()" % mid)
            if marks == '1':
                break
            time.sleep(0.2)
        expect_eq(marks, '1', 'two duplicate adds rendered a count other than 1')
        expect_eq(a.js("(() => { const r = document.querySelector('.msg[data-mid=\"%s\"]');"
                       " const p = r && r.querySelector('.pill .n'); return p ? p.textContent : null; })()" % mid),
                  '1', 'the pill count is not 1 after two duplicate adds')
        expect_eq(len([f for f in wire_since(c, start) if f.get('head') == 1]), 2,
                  'the two rewritten reaction frames did not both reach the wire')

        click(a, '#chipAbout')
        diag = a.js("document.querySelector('#aboutDiag').textContent")
        click(a, '#aboutClose')
        expect(re.search(r'reactions: 1\b', diag or ''), 'the session reaction count is not 1: %r' % (diag,))

        # A react for a mid that is not in the log must not create a row.
        rows_before = a.js("document.querySelectorAll('#log .msg').length")
        expect(c.js("window.__probe.armRewrite('msg', {k: 'react', t: 'aaaaaaaaaaaaaaaa',"
                    " e: 'heart', op: 'add'}, 1)"), 'miss rewrite not armed')
        fill(c, '#input', 'MISS-1')
        click(c, '#send')
        time.sleep(0.8)
        expect_eq(a.js("document.querySelectorAll('#log .msg').length"), rows_before,
                  'a react for an unknown mid created a row')
        expect_eq(a.js("document.querySelectorAll('.msg[data-mid=\"aaaaaaaaaaaaaaaa\"]').length"), 0,
                  'a react resurrected a trimmed row')

        # An unknown shortcode must not render.
        expect(c.js("window.__probe.armRewrite('msg', {k: 'react', t: %s, e: 'notacode',"
                    " op: 'add'}, 1)" % jsval(mid)), 'unknown code rewrite not armed')
        fill(c, '#input', 'BAD-CODE-1')
        click(c, '#send')
        time.sleep(0.8)
        expect_eq(a.js("document.querySelectorAll('[aria-label^=\"notacode\"]').length"), 0,
                  'an unknown shortcode rendered a pill')
        expect_eq(a.js("(() => { const r = document.querySelector('.msg[data-mid=\"%s\"]');"
                       " const p = r && r.querySelector('.pill .n'); return p ? p.textContent : null; })()" % mid),
                  '1', 'an unknown shortcode changed the reaction count')

        # A flood spends the bucket and the fifth drop kills the session.
        start = len(snapshot(a)['wire'])
        a.js("""(() => {
          for (let i = 0; i < 40; i++) {
            const p = document.querySelector('.msg[data-mid="%s"] .pill');
            if (!p) break;
            p.click();
          }
          return true;
        })()""" % mid)
        end = time.time() + 4
        while time.time() < end and a.js('document.body.dataset.screen') != 'S4':
            time.sleep(0.2)
        expect_eq(a.js('document.body.dataset.screen'), 'S4', 'the reaction flood did not kill the session')
        expect('react-flood' in body_text(a), 'the flood kill does not name react-flood')
        sent = [f for f in wire_since(a, start) if f.get('head') == 1]
        expect(0 <= len(sent) <= 20,
               'the flood put %d frames on the wire, the bucket caps a burst at 20' % len(sent))
        expect(not snapshot(a)['errors'], 'page errors on the react path: %r' % (snapshot(a)['errors'],))
    finally:
        b.close()


def case_mid(app, opts):
    """UX-01: every msg frame carries a 16 hex mid, both peers agree on the id,
    a duplicate id is rejected instead of overwriting, and a reaction lands on
    the row its mid names."""
    text = app_text(app)
    expect(re.search(r"sendControl\(\{ k: 'msg', mid: mid, text:", text),
           'the msg frame does not carry mid')
    expect(re.search(r'const mid = randomHex\(8\)', text), 'the msg mid is not 8 random bytes')
    add = extract_js_function(text, 'addMessage')
    expect(re.search(r'/\^\[0-9a-f\]\{16\}\$/', add), 'addMessage does not validate a 16 hex mid')
    expect('if (msgRows.has(id)) return null' in add, 'addMessage accepts a duplicate mid')
    expect('row.dataset.mid = id' in add, 'the row does not expose its mid')
    on = extract_js_function(text, 'onMsg')
    expect('msg.mid' in on and 'addMessage' in on, 'onMsg does not pass the frame mid to addMessage')
    expect('duplicate message id was rejected' in on, 'a duplicate msg id is not named')
    drop = extract_js_function(text, 'dropRow')
    expect('msgRows.delete(mid)' in drop and 'reactions.delete(mid)' in drop,
           'dropping a row leaves the mid or reaction map populated')
    trim = extract_js_function(text, 'trimLog')
    expect(trim.index('dropRow(first)') < trim.index('el.log.removeChild(first)'),
           'the trim removes a row before purging its mid')

    b, a, c = open_app(app)
    try:
        rows = "(() => { const o = {}; document.querySelectorAll('#log .msg').forEach(r => {" \
               " const t = r.querySelector('.bubble') ? r.querySelector('.bubble').textContent : '';" \
               " o[t] = { mid: r.dataset.mid, marks: r.dataset.marks || '0' }; }); return o; })()"
        for m in ('MID-A', 'MID-B'):
            fill(c, '#input', m)
            click(c, '#send')
            time.sleep(0.3)
        expect(recv_marker(a, 'MID-B', 8), 'both messages did not arrive')
        ra = a.js(rows) or {}
        rc = c.js(rows) or {}
        for m in ('MID-A', 'MID-B'):
            expect(m in ra and m in rc, 'row %s missing on one side' % m)
            expect(re.match(r'^[0-9a-f]{16}$', ra[m]['mid'] or ''), 'received mid for %s is not 16 hex' % m)
            expect_eq(ra[m]['mid'], rc[m]['mid'], 'mid for %s differs across peers' % m)
        expect(ra['MID-A']['mid'] != ra['MID-B']['mid'], 'two messages share one mid')

        # One reaction, addressed by mid, lands on that row only.
        m1 = ra['MID-A']['mid']
        expect(a.js("(() => { const r = document.querySelector('.msg[data-mid=\"%s\"]');"
                    " const b = r && r.querySelector('.react-add'); if (!b) return false;"
                    " b.click(); const p = document.querySelector('.palette');"
                    " const h = p && Array.from(p.querySelectorAll('button')).find(x =>"
                    " x.getAttribute('aria-label') === 'heart'); if (h) { h.click(); return true; }"
                    " return false; })()" % m1), 'could not react to the first message')
        time.sleep(0.8)
        ra = a.js(rows) or {}
        expect_eq(ra['MID-A']['marks'], '1', 'the reaction did not land on the addressed row')
        expect_eq(ra['MID-B']['marks'], '0', 'the reaction landed on a different row')

        # A duplicate mid is rejected, not overwritten.
        expect(c.js("window.__probe.mutate('msg-fixed-mid')"), 'fixed mid mutation not armed')
        for m in ('MID-DUP-1', 'MID-DUP-2'):
            fill(c, '#input', m)
            click(c, '#send')
            time.sleep(0.4)
        c.js('window.__probe.disarm(); true')
        expect(wait_log(a, r'duplicate message id was rejected', 6),
               'a duplicate mid left no rejection line')
        dup = a.js("(() => Array.from(document.querySelectorAll('.msg[data-mid=\"00000000000000aa\"]'))"
                   ".map(r => r.querySelector('.bubble').textContent))()")
        expect_eq(dup, ['MID-DUP-1'], 'the duplicate mid overwrote the first row')
        expect_eq(a.js("document.querySelectorAll('.msg').length"), 3, 'row count after a duplicate mid')
        expect(not snapshot(a)['errors'], 'page errors on the mid path: %r' % (snapshot(a)['errors'],))
    finally:
        b.close()


def case_nav(app, opts):
    """UX-03: one screen at a time from S0 to S4, no history entries, the
    composer locks during migration, and the two session slots never both act
    as the live slot."""
    text = app_text(app)
    show = extract_js_function(text, 'showScreen')
    for state in ('S0', 'S1', 'S2', 'S3', 'S4'):
        expect("'%s'" % state in show, 'showScreen does not handle %s' % state)
    expect("document.body.dataset.screen = name" in show, 'the screen is not exposed on body')
    for call in ('el.create.focus', 'el.offer.focus', 'el.digits.focus', 'el.input.focus', 'el.restart.focus'):
        expect(call in show, 'showScreen does not move focus with %s' % call)
    expect('history.pushState' not in text and 'history.replaceState' not in text,
           'the app writes a history entry')
    expect('onpopstate' not in text and 'hashchange' not in text, 'the app listens for a back path')
    expect_eq(len(re.findall(r'slots\.active\s*=\s*\{', text)), 2,
              'slots.active assignment count, the slot must be replaced not appended')
    expect_eq(len(re.findall(r'slots\.pending\s*=\s*\{', text)), 2,
              'slots.pending assignment count')
    expect('slots.pending = null' in text, 'a migration never clears the pending slot')
    expect('A2 second channel' in text, 'a second channel on the live peer is not fatal')
    mig = extract_js_function(text, 'startMigrate')
    expect(mig.index('phase = \'migrating\'') < mig.index('el.input.disabled = true'),
           'the composer is not locked when migration starts')
    expect('slots.pending =' in mig and 'el.log.classList.add(\'locked\')' in mig,
           'migration leaves the composer or the log unlocked')
    adopt = extract_js_function(text, 'adopt')
    expect(adopt, 'no migration adopt path')
    expect(adopt.index('slots.pending = null') < adopt.index('slots.active = {'),
           'the pending slot is active before it is cleared')
    route = extract_js_function(text, 'route')
    expect("phase === 'migrating' && k !== 'mig' && k !== 'panic'" in route,
           'content frames are not dropped during migration')

    b, a, c = open_app(app)
    try:
        # The harness navigates each page once from about:blank, so the initial
        # length is the baseline, not 1.
        d = b.page(b.context())
        d.init(SHIM)
        d.goto(app_url(app))
        h0 = d.js('history.length')
        expect_eq(d.js('document.body.dataset.screen'), 'S0', 'fresh page screen')
        expect_eq(d.js("(() => { const p = document.querySelector('#pairing');"
                       " const ch = document.querySelector('#chat');"
                       " return !!p && !p.hidden && !!ch && ch.hidden; })()"), True,
                  'S0 does not show only the pairing panel')

        expect_eq(a.js('document.body.dataset.screen'), 'S3', 'live screen')
        expect_eq(a.js('document.activeElement.id'), 'input', 'live focus')
        expect_eq(a.js('history.length'), h0, 'the pairing flow wrote a history entry')

        # One screen at a time, S3 only.
        visible = a.js("""(() => { const ids = ['pairing', 'chat', 'ended'];
          const o = {}; ids.forEach(id => { const e = document.getElementById(id); o[id] = !!(e && !e.hidden); });
          o.screen = document.body.dataset.screen; return o; })()""")
        expect_eq(visible, {'pairing': False, 'chat': True, 'ended': False, 'screen': 'S3'},
                  'S3 visible sections')

        # Migration: the composer locks while the pending slot exists. The
        # strip is shown right before the M1 send and hidden on adopt, so a
        # poll can miss it. Record the state at the strip's own mutation.
        a.js("""(() => {
          window.__migLock = null;
          const strip = document.querySelector('#strip');
          const grab = () => {
            if (window.__migLock || strip.hidden) return;
            window.__migLock = {
              screen: document.body.dataset.screen,
              status: document.querySelector('#status').textContent,
              input: document.querySelector('#input').disabled,
              send: document.querySelector('#send').disabled,
              attach: document.querySelector('#attach').disabled,
              strip: !strip.hidden,
              logLocked: document.querySelector('#log').classList.contains('locked'),
              chan: window.__probe.snapshot().channels.filter(c => c.state === 'open').length
            };
          };
          new MutationObserver(grab).observe(strip, { attributes: true, attributeFilter: ['hidden'], childList: true, subtree: true });
          grab();
          return true;
        })()""")
        a.js("""(() => {
          const orig = RTCPeerConnection.prototype.setLocalDescription;
          window.__sld = orig;
          RTCPeerConnection.prototype.setLocalDescription = function () {
            const self = this, args = arguments;
            return new Promise((res) => setTimeout(res, 500)).then(() => window.__sld.apply(self, args));
          };
          return true;
        })()""")
        click(a, '#migrate')
        a.wait("(() => !!window.__migLock)()", timeout=25, what='migration strip')
        expect(a.js('document.body.dataset.screen') != 'S4', 'migration failed before the pending slot was observed')
        locked = a.js('window.__migLock')
        expect_eq(locked['screen'], 'S3', 'migration changed the screen')
        expect_eq(locked['status'], 'migrating', 'the strip is visible before the migrating status')
        expect_eq([locked['input'], locked['send'], locked['attach']], [True, True, True],
                  'the composer unlocked during migration')
        expect_eq([locked['strip'], locked['logLocked']], [True, True], 'the migration strip or log lock is missing')
        expect(locked['chan'] >= 1, 'no live channel during migration')

        a.wait("(() => (document.querySelector('#log').innerText || '').indexOf('Migrated to a new connection') >= 0)()",
               timeout=25, what='migration adopt')
        time.sleep(0.5)
        after = a.js("""(() => ({
          screen: document.body.dataset.screen,
          input: document.querySelector('#input').disabled,
          verify: !document.querySelector('#verify').hidden,
          open: window.__probe.snapshot().channels.filter(c => c.state === 'open').length,
          strip: !document.querySelector('#strip').hidden
        }))()""")
        expect_eq(after['screen'], 'S2', 'the adopted session is not on S2')
        expect_eq(after['input'], True, 'the composer is unlocked before the new SAS is confirmed')
        expect_eq(after['verify'], True, 'the new safety number is not shown')
        expect_eq(after['open'], 1, 'more than one channel stayed open after adoption')
        expect_eq(after['strip'], False, 'the migration strip survived adoption')

        # The new connection needs its own confirm, and only then unlocks.
        confirm_sas(a, c)
        end = time.time() + 12
        while time.time() < end and a.js("document.querySelector('#input').disabled"):
            time.sleep(0.3)
        expect_eq(a.js("document.querySelector('#input').disabled"), False, 'the migrated session never unlocked')
        expect_eq(a.js('document.body.dataset.screen'), 'S3', 'the migrated session did not reach S3')
        expect_eq(a.js('document.activeElement.id'), 'input', 'focus did not move to the composer')
        expect_eq(a.js('history.length'), h0, 'migration wrote a history entry')
        expect(not snapshot(a)['errors'], 'page errors on the nav path: %r' % (snapshot(a)['errors'],))
    finally:
        b.close()


def case_gallery(app, opts):
    """UX-07: the gallery is a RAM-only view over one array, eviction names the
    drop, delete detaches the message card before revoking, drag out is blocked,
    and Save appears only after the digest verifies."""
    text = app_text(app)
    for token in ('localStorage', 'sessionStorage', 'indexedDB', 'caches.', 'showSaveFilePicker'):
        expect(token not in text, 'the artifact uses %s, the gallery is not RAM only' % token)
    expect(re.search(r'MAX_FILES\s*=\s*4', text), 'no file retention cap')
    delete = extract_js_function(text, 'deleteRetained')
    expect(delete.index('parentNode.removeChild(item.row)') < delete.index('URL.revokeObjectURL(item.url)'),
           'delete revokes a blob before the message card is detached')
    expect('retained.indexOf(item)' in delete and 'retained.splice' in delete,
           'delete does not remove the one retained array entry')
    expect('receivedFiles--' in delete, 'delete does not free a retained slot')
    start = extract_js_function(text, 'onFileStart')
    expect('evict(1)' in start, 'a new file at the cap does not evict the oldest first')
    evict = extract_js_function(text, 'evict')
    expect('const keep = MAX_FILES - (need || 0)' in evict and 'receivedFiles > keep' in evict,
           'eviction does not ride the file cap with a caller reserve')
    expect(evict.index('parentNode.removeChild(first.row)') < evict.index('URL.revokeObjectURL(first.url)'),
           'eviction revokes before the row is detached')
    expect('evictedCount++' in evict, 'eviction does not count the drop')
    expect('files retained. Older files were dropped.' in text, 'the eviction line is missing')
    gal = extract_js_function(text, 'renderGallery')
    expect('tile.draggable = false' in gal and "addEventListener('dragstart'" in gal and
           'event.preventDefault()' in gal, 'a gallery tile can be dragged out')
    end = extract_js_function(text, 'onFileEnd')
    expect(end.index("call('fileEndIn'") < end.index('cur.card.done(url'),
           'the Save card is built before the digest verifies')
    expect_eq(text.count('save.href = url'), 1, 'the Save anchor is assigned outside the done path')

    b, a, c = open_app(app)
    try:
        item = {'name': 'gal-1.png', 'type': 'image/png',
                'b64': base64.b64encode(png_bytes(64, 64, metadata=False)).decode('ascii')}
        expect_eq(dispatch_files(c, [item], 'paste').get('files'), 1, 'the paste carried one file')
        img = wait_image(a, 20)
        url = img.get('src')
        expect(url and url.startswith('blob:'), 'the received image has no blob URL')
        expect_eq(a.js("document.querySelectorAll('#log a.save:not([hidden])').length"), 1,
                  'the verified file has no Save anchor')
        expect_eq(a.js("document.querySelectorAll('#log .msg.has-file').length"), 1,
                  'the verified file has no message card')

        click(a, '#chipFiles')
        expect_eq(a.js("document.querySelectorAll('#galleryGrid .tile').length"), 1, 'gallery tile count')
        expect_eq(a.js("document.querySelector('#galleryNote').textContent"), '',
                  'the gallery shows an eviction line with no eviction')

        drag = a.js("""(() => {
          const t = document.querySelector('#galleryGrid .tile');
          if (!t) return null;
          const ev = new DragEvent('dragstart', { bubbles: true, cancelable: true });
          const ok = t.dispatchEvent(ev);
          return { prevented: ev.defaultPrevented, draggable: t.draggable, ok: ok };
        })()""")
        expect(drag and drag['prevented'], 'a gallery tile dragstart is not prevented')
        expect_eq(drag['draggable'], False, 'a gallery tile is draggable')

        marked = a.js("(() => { const im = document.querySelector('#log img[src=%s]');"
                      " const r = im && im.closest('.msg'); if (!r) return false;"
                      " r.dataset.probeDel = '1'; return true; })()" % jsval(url))
        expect(marked, 'the log row behind the tile was not found')
        expect(a.js("(() => { const t = document.querySelector('#galleryGrid .tile');"
                    " const b = Array.from(t.querySelectorAll('button')).find(x => x.textContent === 'Delete');"
                    " if (!b) return false; b.click(); return true; })()"), 'the tile Delete control did not fire')
        time.sleep(0.6)
        last = snapshot(a)['lastRevoke']
        expect(last and last['url'] == url, 'the deleted tile URL was not revoked')
        expect_eq(last['logLive'], 0, 'the message card row was still live when the blob was revoked')
        expect_eq(a.js("document.querySelectorAll('#galleryGrid .tile').length"), 0, 'tile count after delete')
        expect_eq(a.js("document.querySelectorAll('#log .msg.has-file').length"), 0,
                  'the message card survived a gallery delete')
        expect_eq(a.js("document.querySelectorAll('#log a.save:not([hidden])').length"), 0,
                  'the Save anchor survived a gallery delete')
        expect_eq(a.js("document.querySelector('#chipFiles').textContent"), 'Files 0', 'the file chip after delete')
        expect_eq(a.js("document.querySelectorAll('#log img[src^=\"blob:\"]').length"), 0,
                  'a blob image node survived the delete')
        click(a, '#galleryClose')

        # A bad digest must not produce a Save anchor or a tile.
        expect(c.js("window.__probe.mutate('file-bad-digest')"), 'digest mutation not armed')
        bad = {'name': 'bad.png', 'type': 'image/png',
               'b64': base64.b64encode(png_bytes(32, 32, metadata=False)).decode('ascii')}
        dispatch_files(c, [bad], 'paste')
        expect(wait_log(a, r'File rejected|verification failed', 20),
               'a bad digest left no rejection line')
        time.sleep(0.5)
        expect_eq(a.js("document.querySelectorAll('#log a.save:not([hidden])').length"), 0,
                  'a bad digest produced a Save anchor')
        click(a, '#chipFiles')
        expect_eq(a.js("document.querySelectorAll('#galleryGrid .tile').length"), 0,
                  'a bad digest produced a gallery tile')

        # UX-07 budget, behavioral: delete frees a retained slot, and a new
        # start at the cap evicts the oldest retained media then proceeds.
        click(a, '#galleryClose')

        def tile_bases():
            return a.js("Array.from(document.querySelectorAll('#galleryGrid .tile-name'))"
                        ".map((n) => n.textContent.replace(/\\.[^.]+$/, ''))") or []

        def send_cap(name):
            item = {'name': name + '.png', 'type': 'image/png',
                    'b64': base64.b64encode(png_bytes(48, 48, metadata=False)).decode('ascii')}
            dispatch_files(c, [item], 'paste')
            expect(wait_log(a, r'File received and verified: ' + re.escape(name), 30),
                   'a file at or under the cap was not received: ' + name)

        for name in ('cap1', 'cap2', 'cap3', 'cap4'):
            send_cap(name)
        click(a, '#chipFiles')
        expect_eq(tile_bases(), ['cap1', 'cap2', 'cap3', 'cap4'], 'the retained order at the cap')
        expect(a.js("(() => { const t = document.querySelector('#galleryGrid .tile');"
                    " const b = Array.from(t.querySelectorAll('button')).find(x => x.textContent === 'Delete');"
                    " if (!b) return false; b.click(); return true; })()"),
               'the tile Delete control did not fire at the cap')
        time.sleep(0.4)
        expect_eq(a.js("document.querySelector('#chipFiles').textContent"), 'Files 3',
                  'a gallery delete did not free a retained slot')
        click(a, '#galleryClose')
        send_cap('cap5')
        click(a, '#chipFiles')
        expect_eq(tile_bases(), ['cap2', 'cap3', 'cap4', 'cap5'],
                  'a new file was not accepted after a delete freed a slot')
        click(a, '#galleryClose')
        send_cap('cap6')
        click(a, '#chipFiles')
        expect_eq(tile_bases(), ['cap3', 'cap4', 'cap5', 'cap6'],
                  'a new start at the cap did not evict the oldest retained file')
        note = a.js("document.querySelector('#galleryNote').textContent") or ''
        expect('files retained. Older files were dropped.' in note,
               'the eviction did not name the dropped file: %r' % (note,))
        expect(wait_log(a, r'removed to stay within the session budget', 3),
               'the eviction left no system line')
        click(a, '#galleryClose')
        expect(not snapshot(a)['errors'], 'page errors on the gallery path: %r' % (snapshot(a)['errors'],))
    finally:
        b.close()


def case_pair(app, opts):
    """UX-05: the TTL counts down, a stale code and a reused code are both
    refused, a malformed code fails without an SDP or candidate leak, and the
    reply path is single use."""
    text = app_text(app)
    expect(re.search(r'TTL_MS\s*=\s*120000', text), 'no 120 s TTL')
    unpack = extract_js_function(text, 'unpackCode')
    for msg in ('That code has expired', 'already used on this page', 'That is not a V2 code',
                'That code is damaged', 'That code expands beyond the size limit'):
        expect(msg in unpack, 'unpackCode does not carry: %s' % msg)
    expect(not re.search(r'throw new Error\([^)]*(sdp|candidate|ufrag)', unpack, re.I),
           'unpackCode throws decoded SDP or candidate material')
    ttl = extract_js_function(text, 'startTtl')
    expect('TTL_MS - (Date.now() - offerIssuedAt)' in ttl, 'the TTL is not counted from issue time')
    expect('setInterval(tick, 1000)' in ttl, 'the TTL does not tick once a second')
    expect('el.connect.disabled = true' in ttl, 'the connect control is not disabled at zero')
    join = extract_js_function(text, 'joinSession')
    expect(join.index('consumedSids.add(env.sid)') < join.index("pc.setRemoteDescription"),
           'a code is used before it is marked consumed')
    expect('replyUsed' in text and 'That reply was already used' in text, 'the reply is not single use')
    preview = extract_js_function(text, 'pairPreview')
    expect('error.message' in preview and 'candidate' not in preview.lower(),
           'the preview error path can echo candidate material')

    b = Browser()
    try:
        a = b.page(b.context())
        j = b.page(b.context())
        for p in (a, j):
            p.init(SHIM)
            p.goto(app_url(app))

        expect_eq(a.js('document.body.dataset.screen'), 'S0', 'offer screen')
        click(a, '#create')
        a.wait("(() => { const e = document.querySelector('#offer'); return !!e && e.value.length > 40; })()",
               timeout=20, what='invite code')
        code1 = a.js("document.querySelector('#offer').value")
        env1 = json.loads(decode_code(code1))
        expect(re.match(r'^[0-9a-f]{32}$', env1['sid']), 'the offer carries no 32 hex sid')
        expect_eq(a.js('document.body.dataset.screen'), 'S1', 'offer screen after create')
        expect('waiting for reply' in (a.js("document.querySelector('#status').textContent") or ''),
               'the status does not name the waiting state')

        ttl1 = re.search(r'expires in (\d+)', a.js("document.querySelector('#offerTtl').textContent") or '')
        expect(ttl1, 'the TTL line is missing')
        t1 = int(ttl1.group(1)) if ttl1 else 0
        expect(110 <= t1 <= 120, 'the TTL does not start near 120 s')
        time.sleep(2.2)
        ttl2 = re.search(r'expires in (\d+)', a.js("document.querySelector('#offerTtl').textContent") or '')
        expect(ttl2, 'the TTL line disappeared')
        t2 = int(ttl2.group(1)) if ttl2 else 0
        expect(1 <= t1 - t2 <= 3, 'the TTL did not count down')

        def join_error(page, code, want, timeout=10):
            fill(page, '#offerIn', code)
            wait_enabled(page, '#join')
            click(page, '#join')
            end = time.time() + timeout
            txt = ''
            while time.time() < end:
                txt = page.js("(() => { const t = document.querySelector('#toast');"
                              " return (t && !t.hidden ? t.textContent : '') + ' ' +"
                              " (document.querySelector('#pairState').textContent || ''); })()") or ''
                if re.search(want, txt, re.I):
                    return txt
                time.sleep(0.2)
            raise Fail('joining did not report %s, last=%r' % (want, txt))

        leak = re.compile(r'(v=0|candidate:|a=fingerprint|ice-ufrag|ice-pwd|sdp=)', re.I)

        # A damaged code fails closed and says nothing about the decoded media.
        txt = join_error(j, 'E2.1.AAAA', r'damaged|not valid|incorrect header|read|code|error')
        expect(not leak.search(txt), 'a damaged code error leaked SDP or candidates: %r' % txt)
        expect_eq(j.js("document.querySelector('#answer').value"), '', 'a damaged code produced an answer')

        # A valid code joins once.
        fill(j, '#offerIn', code1)
        wait_enabled(j, '#join')
        click(j, '#join')
        j.wait("(() => { const e = document.querySelector('#answer'); return !!e && e.value.length > 40; })()",
               timeout=20, what='reply code')
        answer1 = j.js("document.querySelector('#answer').value")
        reply = json.loads(decode_code(answer1))
        expect_eq(reply['sid'], env1['sid'], 'the reply is for a different session')
        expect('reply ready' in (j.js("document.querySelector('#status').textContent") or ''),
               'the reply state is not named')

        # The same code again is refused on the page that consumed it.
        txt = join_error(j, code1, r'already used')
        expect(not leak.search(txt), 'a reused code error leaked SDP or candidates: %r' % txt)
        expect_eq(j.js("document.querySelector('#answer').value"), '', 'a reused code still produced an answer')

        # A stale code is refused before anything is parsed into a connection.
        stale_env = dict(env1)
        stale_env['ts'] = int(time.time() * 1000) - 125000
        stale = encode_code('E2', json.dumps(stale_env))
        txt = join_error(j, stale, r'expired')
        expect(not leak.search(txt), 'a stale code error leaked SDP or candidates: %r' % txt)
        expect_eq(j.js("document.querySelector('#answer').value"), '', 'a stale code produced an answer')

        # A fresh invite from the same page reaches a live, verified session.
        click(a, '#create')
        a.wait("(() => { const e = document.querySelector('#offer');"
               " return !!e && e.value.length > 40 && e.value !== %s; })()" % jsval(code1),
               timeout=20, what='second invite code')
        code2 = a.js("document.querySelector('#offer').value")
        expect(code2 != code1, 'the second invite reused the first code')
        fill(j, '#offerIn', code2)
        wait_enabled(j, '#join')
        click(j, '#join')
        j.wait("(() => { const e = document.querySelector('#answer'); return !!e && e.value.length > 40; })()",
               timeout=20, what='second reply code')
        answer2 = j.js("document.querySelector('#answer').value")
        fill(a, '#answerIn', answer2)
        wait_enabled(a, '#connect')
        click(a, '#connect')
        wait_pair(a, j, timeout=25)
        expect_eq(a.js('document.body.dataset.screen'), 'S2', 'connected screen')
        expect(content_locked(a), 'the composer is unlocked before verification')
        confirm_sas(a, j)
        end = time.time() + 12
        while time.time() < end and content_locked(a):
            time.sleep(0.3)
        expect_eq(content_locked(a), False, 'the verified session never unlocked')
        expect(not snapshot(a)['errors'], 'page errors on the pair path: %r' % (snapshot(a)['errors'],))
    finally:
        b.close()


def case_sas_ui(app, opts):
    """UX-04: the panel renders the 60 digit SAS and the crypto chips, the
    composer and the verified label stay locked until both confirm, and no
    session id or key byte reaches the DOM."""
    text = app_text(app)
    sas = extract_js_function(text, 'showSas')
    expect('i < 12' in sas and 'sas.slice(i * 5, i * 5 + 5)' in sas,
           'the panel does not render twelve five digit cells')
    expect('el.confirmSas.disabled = localConfirm' in sas, 'confirm is not single shot')
    chips = extract_js_function(text, 'updateChips')
    expect("localConfirm && peerConfirm" in chips and "'verified'" in chips,
           'the verified label is not gated on both confirms')
    live = extract_js_function(text, 'maybeLive')
    expect('if (!localConfirm || !peerConfirm)' in live, 'maybeLive unlocks without both confirms')
    expect(live.index('phase = \'live\'') > live.index('if (!localConfirm || !peerConfirm)'),
           'the live phase is set before the peer confirm gate')
    expect('sessionSid' not in extract_js_function(text, 'showSas'), 'the SAS panel writes the session id')

    b, a, c = open_app(app, confirm=False)
    try:
        env = json.loads(decode_code(a.js("document.querySelector('#offer').value")))
        sid = env['sid']
        expect_eq(a.js('document.body.dataset.screen'), 'S2', 'confirm screen')
        expect_eq(a.js("(() => !document.querySelector('#verify').hidden)()"), True, 'verify panel hidden')
        cells_a = a.js("Array.from(document.querySelectorAll('#digits span')).map(s => s.textContent)")
        cells_c = c.js("Array.from(document.querySelectorAll('#digits span')).map(s => s.textContent)")
        expect_eq(len(cells_a or []), 12, 'SAS cell count')
        expect(all(re.match(r'^\d{5}$', x or '') for x in cells_a), 'a SAS cell is not five digits')
        expect_eq(len(''.join(cells_a)), 60, 'SAS digit count')
        expect_eq(cells_a, cells_c, 'the two peers render different safety numbers')
        expect_eq(a.js("document.querySelectorAll('#digits span').length"), 12, 'SAS DOM cell count')
        expect_eq(a.js("document.querySelector('#chipVerify').textContent"), 'unverified', 'initial chip')
        expect_eq(a.js("document.querySelector('#chipVerify').dataset.tone"), 'wait', 'initial chip tone')
        expect_eq(a.js("document.querySelector('#suite').textContent"),
                  a.js("document.querySelector('#chipSuite').textContent"), 'the suite chip and panel differ')
        expect(a.js("document.querySelector('#chipSuite').textContent") != 'suite', 'the suite chip is a placeholder')

        # Locked before either confirm.
        expect_eq([a.js("document.querySelector('#input').disabled"),
                   a.js("document.querySelector('#send').disabled")], [True, True],
                  'the composer is unlocked at S2')
        start = len(snapshot(a)['wire'])
        a.js("document.querySelector('#send').click(); true")
        fill(a, '#input', 'SAS-UI-BLOCKED')
        time.sleep(0.6)
        expect_eq(len(snapshot(a)['wire']), start, 'a send left the composer before the SAS confirm')
        expect_eq(a.js("document.querySelectorAll('#log .msg').length"), 0, 'a message appeared before the confirm')

        # One confirm: still locked, chip names the missing side.
        click(a, '#confirmSas')
        end = time.time() + 8
        while time.time() < end and a.js("document.querySelector('#chipVerify').textContent") != 'waiting for peer':
            time.sleep(0.2)
        expect_eq(a.js("document.querySelector('#chipVerify').textContent"), 'waiting for peer',
                  'one confirm does not name the waiting peer')
        expect_eq(a.js("document.querySelector('#chipVerify').dataset.tone"), 'wait', 'one confirm tone')
        expect_eq(a.js("document.querySelector('#input').disabled"), True,
                  'the composer unlocked after one confirm')
        expect('waiting' in (a.js("document.querySelector('#verifyState').textContent") or '').lower(),
               'the verify state does not name the wait')
        start = len(snapshot(a)['wire'])
        a.js("document.querySelector('#send').click(); true")
        time.sleep(0.5)
        expect_eq(len(snapshot(a)['wire']), start, 'a send left after one confirm')

        # Both confirmed: verified label, unlocked composer, message flows.
        click(c, '#confirmSas')
        end = time.time() + 12
        while time.time() < end and a.js("document.querySelector('#input').disabled"):
            time.sleep(0.3)
        expect_eq(a.js("document.querySelector('#input').disabled"), False, 'the composer never unlocked')
        expect_eq(a.js("document.querySelector('#chipVerify').textContent"), 'verified', 'verified chip')
        expect_eq(a.js("document.querySelector('#chipVerify').dataset.tone"), 'ok', 'verified tone')
        expect_eq(a.js('document.body.dataset.screen'), 'S3', 'verified screen')
        expect('Confirmed on both sides' in (a.js("document.querySelector('#verifyState').textContent") or ''),
               'the verify state does not say both sides')
        fill(a, '#input', 'SAS-UI-LIVE')
        click(a, '#send')
        expect(recv_marker(c, 'SAS-UI-LIVE', 8), 'a message did not flow after both confirms')

        # No session id, SDP, or key byte is in the rendered DOM. Script and
        # textarea source is not rendered content; the invite code field is a
        # deliberate user facing code, not a panel leak.
        html = a.js("""(() => Array.from(document.querySelectorAll('body *'))
          .filter(e => e.tagName !== 'SCRIPT' && e.tagName !== 'TEXTAREA')
          .map(e => e.outerHTML).join('\\n'))()""") or ''
        visible = body_text(a)
        expect(sid not in html and sid not in visible, 'the session id is in the DOM')
        for field in ('eph_pk', 'stat_pk'):
            expect(env[field] not in html, 'the %s value is in the DOM' % field)
        expect(not re.search(r'\b[0-9a-f]{64}\b', html), 'a 64 hex key byte string is in the DOM')
        expect('v=0' not in html and 'v=0' not in visible, 'the SDP is in the DOM')
        expect('a=fingerprint' not in html and 'a=fingerprint' not in visible, 'the SDP is in the DOM')
        expect(not snapshot(a)['errors'], 'page errors on the sas-ui path: %r' % (snapshot(a)['errors'],))
    finally:
        b.close()

    # A mismatch ends the session before content.
    b, a, c = open_app(app, confirm=False)
    try:
        click(a, '#badSas')
        a.wait("(() => document.body.dataset.screen === 'S4')()", timeout=8, what='mismatch end')
        expect('Verification failed' in (a.js("document.querySelector('#endedTitle').textContent") or ''),
               'a mismatch does not title the end as a verification failure')
        expect('safety number did not match' in (a.js("document.querySelector('#endedText').textContent") or ''),
               'a mismatch end does not name the safety number')
        expect_eq(a.js("document.querySelectorAll('#log .msg').length"), 0, 'a mismatch left content')
    finally:
        b.close()


def _lum(hexcolor):
    h = hexcolor.lstrip('#')
    parts = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    lin = [(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4) for c in parts]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _contrast(a, b):
    la, lb = _lum(a), _lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def case_a11y(app, opts):
    """UX-08: both theme palettes clear 4.5:1, the focus ring and reduced motion
    rules exist, and the reaction UI is a set of named buttons inside a live
    region that is off, so a reaction never re-announces the message."""
    text = app_text(app)
    dark_block = re.search(r':root\s*\{(.*?)\}', text, re.S)
    light_block = re.search(r'@media \(prefers-color-scheme: light\)\s*\{\s*:root\s*\{(.*?)\}', text, re.S)
    expect(dark_block, 'no dark token block')
    expect(light_block, 'no light token block')
    dark = dict(re.findall(r'--([a-z-]+):\s*(#[0-9a-fA-F]{6})', dark_block.group(1) if dark_block else ''))
    light = dict(re.findall(r'--([a-z-]+):\s*(#[0-9a-fA-F]{6})', light_block.group(1) if light_block else ''))
    for name, block in (('dark', dark), ('light', light)):
        expect(block.get('bg') and block.get('text'), 'the %s block has no bg or text token' % name)
        for token in ('text', 'muted', 'faint', 'accent', 'danger', 'ok', 'wait'):
            expect(token in block, 'the %s block has no %s token' % (name, token))
            ratio = _contrast(block[token], block['bg'])
            expect(ratio >= 4.5, '%s %s on bg is %.2f:1, below 4.5:1' % (name, token, ratio))
    expect('background: var(--bg)' in text and 'color: var(--text)' in text,
           'body does not consume the theme tokens')
    expect(re.search(r':focus-visible\s*\{\s*outline:\s*2px solid var\(--accent\);\s*outline-offset:\s*2px;', text),
           'no two pixel focus ring with an offset')
    expect('prefers-reduced-motion: reduce' in text, 'no reduced motion block')
    expect('transition: none !important' in text and 'animation: none !important' in text and
           'scroll-behavior: auto !important' in text, 'the reduced motion block does not zero motion')
    expect('role="log"' in text and 'aria-live="polite"' in text, 'the transcript is not a polite live log')
    expect('role="alert"' in text and 'role="status"' in text, 'no alert or status roles')
    expect("pills.setAttribute('aria-live', 'off')" in text,
           'the reaction pill container is a live region')
    expect_eq(text.count('role="button"'), 0, 'a div is dressed as a button')
    expect_eq(text.count('onclick='), 0, 'an inline click handler is used')
    palette = re.search(r'const PALETTE = \[(.*?)\];', text, re.S)
    entries = re.findall(r"\['([a-z0-9-]+)',\s*'", palette.group(1) if palette else '')
    expect_eq(len(entries), 24, 'palette entry count')
    expect(all(re.match(r'^[a-z0-9-]+$', e) for e in entries), 'a palette entry has no word code')
    pills = extract_js_function(text, 'renderPills')
    expect('pill.type = \'button\'' in pills and 'aria-label' in pills and 'aria-pressed' in pills,
           'a pill is not a named button with a pressed state')

    b, a, c = open_app(app)
    try:
        live = a.js("""(() => ({
          logRole: document.querySelector('#log').getAttribute('role'),
          logLive: document.querySelector('#log').getAttribute('aria-live'),
          endedRole: document.querySelector('#ended').getAttribute('role'),
          digitsLabel: document.querySelector('#digits').getAttribute('aria-label')
        }))()""")
        expect_eq(live['logRole'], 'log', 'transcript role')
        expect_eq(live['logLive'], 'polite', 'transcript live setting')
        expect_eq(live['endedRole'], 'alert', 'ended panel role')
        expect(live['digitsLabel'], 'the safety number has no accessible name')

        # Reduced motion: the one animated rule goes to 0 s.
        normal = a.js("""(() => {
          const bar = document.createElement('div'); bar.className = 'bar';
          const i = document.createElement('i'); bar.appendChild(i);
          document.body.appendChild(bar);
          const st = getComputedStyle(i);
          return { duration: st.transitionDuration, animation: st.animationName };
        })()""")
        expect(normal and normal['duration'] not in ('0s', ''), 'the probe element has no transition to disable')
        b.cmd('Emulation.setEmulatedMedia',
              {'features': [{'name': 'prefers-reduced-motion', 'value': 'reduce'}]}, session=a.sid)
        reduced = a.js("""(() => {
          const i = document.querySelector('body > .bar > i');
          const st = getComputedStyle(i);
          return { duration: st.transitionDuration, animation: st.animationName,
                   scroll: getComputedStyle(document.documentElement).scrollBehavior };
        })()""")
        expect_eq(reduced['duration'], '0s', 'reduced motion does not zero the transition')
        expect_eq(reduced['animation'], 'none', 'reduced motion does not zero the animation')
        expect_eq(reduced['scroll'], 'auto', 'reduced motion does not zero smooth scrolling')
        b.cmd('Emulation.setEmulatedMedia', {'features': []}, session=a.sid)

        # Light and dark both apply from tokens.
        dark_bg = a.js('getComputedStyle(document.body).backgroundColor')
        expect_eq(dark_bg, 'rgb(11, 12, 14)', 'the dark background token does not apply')
        b.cmd('Emulation.setEmulatedMedia',
              {'features': [{'name': 'prefers-color-scheme', 'value': 'light'}]}, session=a.sid)
        light_bg = a.js('getComputedStyle(document.body).backgroundColor')
        light_fg = a.js('getComputedStyle(document.body).color')
        expect_eq(light_bg, 'rgb(246, 247, 249)', 'the light background block does not apply')
        expect_eq(light_fg, 'rgb(22, 25, 29)', 'the light text token does not apply')
        b.cmd('Emulation.setEmulatedMedia',
              {'features': [{'name': 'prefers-color-scheme', 'value': 'dark'}]}, session=a.sid)

        # The reaction UI is buttons inside an off live region.
        fill(a, '#input', 'A11Y-BASE')
        click(a, '#send')
        expect(recv_marker(c, 'A11Y-BASE', 8), 'the base message did not arrive')
        expect(c.js("(() => { const rows = document.querySelectorAll('#log .msg');"
                    " const r = rows[rows.length - 1]; const b = r && r.querySelector('.react-add');"
                    " if (!b) return null; b.click(); const p = document.querySelector('.palette');"
                    " const h = p && Array.from(p.querySelectorAll('button')).find(x =>"
                    " x.getAttribute('aria-label') === 'heart'); if (!h) return null;"
                    " const out = { add: b.tagName, palette: h.tagName, label: h.getAttribute('aria-label') };"
                    " h.click(); return out; })()"),
               'the palette did not offer a named heart button')
        time.sleep(0.6)
        state = c.js("""(() => {
          const pill = document.querySelector('#log .msg .pill');
          const holder = pill && pill.parentNode;
          return {
            tag: pill ? pill.tagName : null,
            pressed: pill ? pill.getAttribute('aria-pressed') : null,
            label: pill ? pill.getAttribute('aria-label') : null,
            holderLive: holder ? holder.getAttribute('aria-live') : null,
            logLive: document.querySelector('#log').getAttribute('aria-live')
          };
        })()""")
        expect_eq(state['tag'], 'BUTTON', 'a reaction pill is not a button')
        expect_eq(state['pressed'], 'true', 'a self reaction pill has no pressed state')
        expect('reaction' in (state['label'] or ''), 'the pill has no spoken reaction label')
        expect_eq(state['holderLive'], 'off', 'the pill container announces reactions')
        expect_eq(state['logLive'], 'polite', 'a reaction changed the transcript live setting')
        expect(not snapshot(c)['errors'], 'page errors on the a11y path: %r' % (snapshot(c)['errors'],))
    finally:
        b.close()


def case_transcode(app, opts):
    """R2-18: engine A asserts decoderConfig before finalize, closes every
    VideoFrame, and bounds the encode queue at 8; a failed engine A falls to the
    live MediaRecorder rung B instead of throwing."""
    text = app_text(app)
    expect('window.Mp4Muxer' in text and re.search(r'MUXER_PIN\s*=\s*31103', text),
           'the pinned muxer is missing')
    ta = extract_js_function(text, 'transcodeA')
    expect('if (!firstMeta || !firstMeta.decoderConfig)' in ta,
           'engine A does not assert a decoderConfig on the first chunk')
    expect(ta.index('firstMeta.decoderConfig') < ta.index('muxer.finalize()'),
           'engine A finalizes the muxer before the decoderConfig assertion')
    expect_eq(ta.count('new VideoFrame('), 2, 'the VideoFrame creation sites changed')
    expect(re.search(r'finally\s*\{\s*if \(frame\) frame\.close\(\);', ta),
           'a VideoFrame is not closed in a finally')
    expect(re.search(r'encodeQueueSize\s*>\s*8', ta), 'the encode queue is not capped at 8')
    expect("addEventListener('dequeue'" in ta, 'the encoder never resumes after a full queue')
    expect('video.pause()' in ta and 'video.play()' in ta, 'the queue cap does not pause the decoder')
    expect('VideoEncoder.isConfigSupported' in ta, 'engine A does not probe support')
    ts = extract_js_function(text, 'transcodeAndSend')
    expect(ts.index('await transcodeA') < ts.index('await transcodeB'),
           'engine A is not the first rung')
    expect('Falling back to MediaRecorder' in ts, 'a failed engine A does not name the fallback')
    expect('out.engine' in ts, 'the engine that produced the blob is not recorded')

    b, a, c = open_app(app)
    try:
        engine_a = c.js('typeof VideoEncoder')
        print('transcode engine A in this harness: %s' % engine_a)
        # Force the no WebCodecs environment so rung B runs live and deterministic.
        c.js('window.VideoEncoder = undefined; true')
        # A real clip over the 45 MB cap: 14 s of 720p shifting noise. This is
        # the only path that reaches the transcode draft, and it keeps engine A
        # out of reach on a headless no GPU box so rung B is the live rung.
        made = c.js("""(() => new Promise((resolve) => {
          const W = 1280, H = 720;
          const noise = document.createElement('canvas'); noise.width = W + 320; noise.height = H + 320;
          const nctx = noise.getContext('2d');
          const nimg = nctx.createImageData(noise.width, noise.height);
          const d = nimg.data;
          for (let i = 0; i < d.length; i += 4) {
            d[i] = Math.random() * 255; d[i+1] = Math.random() * 255; d[i+2] = Math.random() * 255; d[i+3] = 255;
          }
          nctx.putImageData(nimg, 0, 0);
          const cv = document.createElement('canvas'); cv.width = W; cv.height = H;
          const ctx = cv.getContext('2d');
          let painting = true;
          function paint() {
            if (!painting) return;
            ctx.drawImage(noise, -Math.floor(Math.random() * 320), -Math.floor(Math.random() * 320));
            setTimeout(paint, 40);
          }
          paint();
          const mime = MediaRecorder.isTypeSupported('video/webm;codecs=vp8') ? 'video/webm' : '';
          if (!mime) { resolve({ ok: false, why: 'no webm encoder' }); return; }
          const rec = new MediaRecorder(cv.captureStream(24), { mimeType: mime, videoBitsPerSecond: 80000000 });
          const parts = [];
          rec.ondataavailable = (e) => { if (e.data && e.data.size) parts.push(e.data); };
          rec.onstop = () => {
            painting = false;
            const blob = new Blob(parts, { type: 'video/webm' });
            if (blob.size <= 45 * 1024 * 1024) { resolve({ ok: false, why: 'clip too small', size: blob.size }); return; }
            const dt = new DataTransfer();
            dt.items.add(new File([blob], 'probe-big.webm', { type: 'video/webm' }));
            document.dispatchEvent(new DragEvent('drop', { dataTransfer: dt, bubbles: true, cancelable: true }));
            resolve({ ok: true, size: blob.size });
          };
          rec.start(); setTimeout(() => rec.stop(), 14000);
        }))()""", timeout=180)
        expect(made and made.get('ok'), 'could not generate a clip over 45 MB: %r' % (made,))
        draft = c.wait("(() => { const d = document.querySelector('.file.draft');"
                       " const b = d && Array.from(d.querySelectorAll('button')).find(x => x.textContent === 'Send video');"
                       " return b ? d.querySelector('.draft-line').textContent : ''; })()",
                       timeout=30, what='transcode draft card')
        expect('Will be re-encoded' in draft, 'the draft card does not project the re-encode: %r' % draft)
        # Record the MediaRecorder that rung B starts, so the engine is proven
        # even if the short file state line is missed. No link model and no
        # per chunk delay here: the 14 MB output is delivered at full speed,
        # which proves the A8 budget exempts authenticated bulk chunk frames.
        c.js("""(() => {
          window.__recMimes = [];
          const Orig = window.MediaRecorder;
          window.MediaRecorder = class extends Orig {
            constructor(stream, opts) { super(stream, opts); window.__recMimes.push((opts && opts.mimeType) || ''); }
          };
          return true;
        })()""")
        expect(c.js("(() => { const d = document.querySelector('.file.draft');"
                    " const b = d && Array.from(d.querySelectorAll('button')).find(x => x.textContent === 'Send video');"
                    " if (!b) return false; b.click(); return true; })()"), 'the draft Send video control did not fire')
        expect(wait_log(c, r'WebCodecs could not encode|Falling back to MediaRecorder', 30),
               'a failed engine A left no fallback line')
        engine = ''
        recs = []
        end = time.time() + 150
        while time.time() < end:
            recs = c.js('window.__recMimes') or []
            st = c.js("(() => { const d = document.querySelector('.file.draft');"
                      " const s = d && d.querySelector('.file-foot span');"
                      " return s ? s.textContent : ''; })()") or ''
            if 'recorder-webm' in st or 'recorder-mp4' in st:
                engine = st
                break
            if recs:
                break
            time.sleep(0.2)
        if not engine:
            expect(recs, 'rung B never constructed a MediaRecorder')
            engine = 'recorder-webm' if any('webm' in (m or '') for m in recs) else 'recorder-mp4'
        expect('recorder-webm' in engine or 'recorder-mp4' in engine, 'rung B was not named: %r' % engine)
        v = wait_video(a, 180)
        # wait_video returns as soon as the blob src is attached. Metadata is
        # still loading at that instant, so poll for HAVE_METADATA or an error.
        end = time.time() + 90
        while time.time() < end:
            v = video_node(a)
            if v and (v.get('err') is not None or (v.get('ready') or 0) >= 1):
                break
            time.sleep(0.2)
        expect(v and v.get('src'), 'no received video node appeared')
        expect(v.get('err') is None, 'the rung B video errors: %r' % (v,))
        expect(v.get('ready') >= 1, 'the rung B video never reached HAVE_METADATA')
        expect((v.get('w') or 0) > 0 and (v.get('dur') or 0) > 0,
               'the rung B video has no dimensions or duration: %r' % (v,))
        expect(v['src'].startswith('blob:'), 'the received video is not a RAM blob')
        expect((v.get('dur') or 0) > 1, 'the received video duration is not the rung B clip')
        expect(not snapshot(a)['errors'], 'page errors on the transcode path: %r' % (snapshot(a)['errors'],))
    finally:
        b.close()


CASES = {
    'selftest': case_selftest,
    'envelope': case_envelope,
    'ratchet': case_ratchet,
    'sas': case_sas,
    'file': case_file,
    'budget': case_budget,
    'code': case_code,
    'lifecycle': case_lifecycle,
    'kill': case_kill,
    'rotate': case_rotate,
    'migrate': case_migrate,
    'stun': case_stun,
    'cover': case_cover,
    'mutation-all': case_mutation,
    'media-order': case_media_order,
    'media': case_media_order,
    'exif': case_exif,
    'bitrate': case_bitrate,
    'playback': case_playback,
    'imagecap': case_imagecap,
    'paste': case_paste,
    'panic': case_panic,
    'react': case_react,
    'mid': case_mid,
    'nav': case_nav,
    'gallery': case_gallery,
    'pair': case_pair,
    'sas-ui': case_sas_ui,
    'a11y': case_a11y,
    'transcode': case_transcode,
}

CARD_ORDER = [
    'selftest', 'envelope', 'ratchet', 'sas', 'file', 'budget', 'code',
    'lifecycle', 'kill', 'rotate', 'migrate', 'stun', 'cover', 'mutation-all',
    'media-order', 'exif', 'bitrate', 'playback', 'imagecap', 'paste',
    'panic',
    'react',
    'mid',
    'nav',
    'gallery',
    'pair',
    'sas-ui',
    'a11y',
    'transcode',
]


def parse_args(argv):
    opts = {'app': DEFAULT_APP, 'relay_host': None, 'case': None}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == '--app':
            i += 1
            opts['app'] = argv[i]
        elif arg == '--relay-host':
            i += 1
            opts['relay_host'] = argv[i]
        elif arg in ('-h', '--help'):
            print(__doc__)
            raise SystemExit(0)
        elif opts['case'] is None:
            opts['case'] = arg
        else:
            raise SystemExit('unknown argument: ' + arg)
        i += 1
    return opts


def write_evidence(case, app, code, detail, started):
    if os.environ.get('GATE_NO_EVIDENCE'):
        return None
    os.makedirs(EVIDENCE, exist_ok=True)
    record = {
        'case': case,
        'run': time.strftime('%Y-%m-%dT%H:%M:%S%z', time.localtime(started)),
        'duration_s': round(time.time() - started, 2),
        'argv': sys.argv,
        'app': os.path.abspath(app),
        'app_sha256': sha256_file(app) if os.path.isfile(app) else None,
        'app_bytes': os.path.getsize(app) if os.path.isfile(app) else None,
        'exit': code,
        'detail': detail,
    }
    path = os.path.join(EVIDENCE, '%s-%s.json' % (case, time.strftime('%Y%m%d-%H%M%S', time.localtime(started))))
    with open(path, 'w') as fh:
        json.dump(record, fh, indent=2, sort_keys=True)
        fh.write('\n')
    return path


def main(argv):
    opts = parse_args(argv)
    case = opts['case']
    if case in (None, 'list'):
        for name in CARD_ORDER:
            print(name)
        return 0
    if case == 'mutation':
        case = 'mutation-all'
    fn = CASES.get(case)
    if fn is None:
        print('FAIL %s unknown case, known: %s' % (case, ' '.join(CARD_ORDER)), file=sys.stderr)
        return 1
    started = time.time()
    code = 0
    detail = ''
    try:
        fn(opts['app'], opts)
        print('PASS %s' % case)
    except Fail as exc:
        code = 1
        detail = str(exc)
        print('FAIL %s %s' % (case, exc))
    except CannotRun as exc:
        code = 2
        detail = str(exc)
        print('SKIP %s could not run: %s' % (case, exc))
    except Exception as exc:  # harness defect, never a pass
        code = 2
        detail = '%s: %s' % (type(exc).__name__, exc)
        print('SKIP %s harness error: %s' % (case, detail))
    finally:
        try:
            write_evidence(case, opts['app'], code, detail, started)
        except Exception as exc:
            print('evidence write failed: %s' % exc, file=sys.stderr)
    return code


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
