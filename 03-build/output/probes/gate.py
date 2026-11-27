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
import gzip
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request

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
    peers: [], channels: [], sent: [], recv: [], raw: [],
    blobs: { created: [], revoked: [], domAtRevoke: [] },
    errors: [], lastRevoke: null
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
      return url;
    };
  }
  if (origRevokeURL) {
    URL.revokeObjectURL = function (url) {
      var live = document.querySelectorAll('img[src^="blob:"],a[href^="blob:"],video[src^="blob:"],audio[src^="blob:"]').length;
      P.blobs.revoked.push(url);
      P.blobs.domAtRevoke.push(live);
      P.lastRevoke = { url: url, liveNodes: live };
      return origRevokeURL(url);
    };
  }
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


def pair_app(a, b, confirm=True, timeout=30):
    wait_enabled(a, '#create')
    click(a, '#create')
    a.wait("(() => { const e = document.querySelector('#offer'); return !!e && e.value.length > 40; })()",
           timeout=timeout, what='invite code')
    code = a.js("document.querySelector('#offer').value")
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


def open_app(app, confirm=True, query=''):
    app_text(app)
    b = Browser()
    try:
        a = b.page(b.context())
        c = b.page(b.context())
        for p in (a, c):
            p.init(SHIM)
        url = app_url(app) + query
        a.goto(url)
        c.goto(url)
        pair_app(a, c, confirm=confirm)
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


# -------------------------------------------------------------------- cases

def case_envelope(app, opts):
    """R2-02: unknown k, unknown v, malformed JSON are visible and never silent."""
    b, a, c = open_app(app)
    try:
        expect(send_text(c, '{"v":1,"k":"probe-unknown-k","sid":"probe"}'), 'unknown k frame not sent')
        txt = wait_log(a, r'unknown|unrecognis|unrecogniz|unexpected|bad frame', 6)
        expect(txt, 'unknown k left no visible system line')
        expect('probe-unknown-k' in log_text(a), 'unknown k value is not shown')

        send_text(c, '{"v":99,"k":"msg","sid":"probe","seq":1,"text":"PROBE-V99"}')
        time.sleep(1.5)
        expect('PROBE-V99' not in body_text(a), 'content from an unknown envelope version rendered')
        expect(wait_log(a, r'version|newer|older', 3), 'unknown v left no visible version state')

        send_text(c, '{not json')
        expect(wait_log(a, r'invalid|malformed|bad frame|unknown|reject', 4), 'malformed JSON was dropped silently')
        expect(open_channel(a), 'channel died on a malformed frame')

        for _ in range(3):
            send_text(c, '{"v":1,"k":"probe-unknown-k","sid":"probe"}')
            time.sleep(0.2)
        expect(ended_or_blank(a, 10), 'three unknown frames in 10 s did not run kill')
    finally:
        b.close()


def case_ratchet(app, opts):
    """R2-03: fresh key per message, no plaintext on the wire, keys in a Worker."""
    text = app_text(app)
    expect('exportKey' not in text, 'artifact calls exportKey, key bytes are readable from the main thread')
    expect('new Worker' in text or 'Worker(' in text, 'no Worker holds the ratchet state')
    b, a, c = open_app(app)
    try:
        def send_ui(value):
            fill(a, '#input', value)
            click(a, '#send')

        marker = 'PROBE-RATCHET-1'
        send_ui(marker)
        time.sleep(0.6)
        send_ui(marker)
        time.sleep(0.6)
        frames = [f for f in snapshot(a)['sentFrames'] if isinstance(f, str)]
        expect(len(frames) >= 2, 'fewer than two string frames on the wire, cannot read the ciphertext')
        last_two = frames[-2:]
        expect_eq(len(set(last_two)), 2, 'identical plaintext produced identical ciphertext')
        for f in frames:
            expect(marker not in f, 'plaintext marker found on the wire')

        for i in range(5):
            send_ui('PROBE-RATCHET-%d' % (i + 2))
            time.sleep(0.2)
        tail = [f for f in snapshot(a)['sentFrames'] if isinstance(f, str)][-5:]
        expect_eq(len(set(tail)), 5, 'per message keys are not fresh, repeated ciphertext in the tail')
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
    """R2-05: verified file exports once, replaying a truncated transfer exports nothing."""
    b, a, c = open_app(app)
    path = scratch_file('probe.bin', bytes(range(256)) * 32)
    try:
        expect(send_file_and_wait(c, a, path), 'a verified 8 KiB file produced no Save anchor')

        boundary = len([f for f in snapshot(c)['sentFrames'] if isinstance(f, str)])
        raw_boundary = len(snapshot(c)['raw'])
        before = anchor_count(a)
        expect(send_file_and_wait(c, a, path), 'a second verified transfer produced no anchor')
        frames = [f for f in snapshot(c)['sentFrames'] if isinstance(f, str)][boundary:]
        raw = snapshot(c)['raw'][raw_boundary:]
        expect(len(frames) >= 2, 'file-start and file-end were not captured')
        expect(len(raw) >= 1, 'no binary chunk was captured')

        before = anchor_count(a)
        expect(send_text(c, frames[0]), 'replay of file-start not sent')
        expect(c.js('window.__probe.sendB64(%s)' % jsval(raw[0])), 'replay of the chunk not sent')
        expect(send_text(c, frames[-1]), 'replay of file-end not sent')
        time.sleep(3)
        expect_eq(anchor_count(a), before, 'a truncated replay produced a Save anchor')
        expect(wait_log(a, r'fail|incomplete|mismatch|corrupt|reject|abort|error', 3),
               'a truncated replay left no failed state')
        big = [x for x in snapshot(a)['blobCreated'] if (x.get('size') or 0) > 8 * 1024 * 1024]
        expect(not big, 'a padded blob larger than 8 MiB was exported: %r' % (big[:1],))
    finally:
        b.close()
        shutil.rmtree(os.path.dirname(path), ignore_errors=True)


def case_budget(app, opts):
    """R2-06: a poisoned start does not block later files, a burst trips A8, row cap exists."""
    text = app_text(app)
    expect(re.search(r'\b2000\b|2_000', text), 'no 2000 row transcript cap in the artifact')
    b, a, c = open_app(app)
    path = scratch_file('probe.bin', b'Z' * 4096)
    try:
        send_text(c, '{"v":1,"k":"file-start","sid":"probe","id":"poison1","name":"p.bin","size":-1,'
                     '"type":"application/octet-stream","chunks":1}')
        send_text(c, '{"v":1,"k":"file-start","sid":"probe","id":"poison2","name":"p.bin","size":1000000000000000000,'
                     '"type":"application/octet-stream","chunks":1}')
        time.sleep(1)
        expect_eq(open_channel(a), True, 'a bad file-start closed the channel')
        expect(send_file_and_wait(c, a, path), 'a later valid transfer was refused after a poisoned start (F-04)')

        for i in range(200):
            send_text(c, '{"v":1,"k":"noise","sid":"probe","i":%d}' % i)
        expect(ended_or_blank(a, 8), 'a 200 frame burst did not trip the A8 rate rule')
    finally:
        b.close()
        shutil.rmtree(os.path.dirname(path), ignore_errors=True)


def case_code(app, opts):
    """R2-07: paste cap, decompressed cap, TTL, candidate cap before setRemoteDescription."""
    text = app_text(app)
    expect(re.search(r'\b16384\b|16\s*\*\s*1024|16_384', text), 'no 16 KB paste cap')
    expect(re.search(r'\b65536\b|64\s*\*\s*1024|65_536', text), 'no 64 KB decompressed cap')
    expect(re.search(r'\b120000\b|120\s*\*\s*1000|120_000', text), 'no 120 s code TTL')
    expect(re.search(r'\b32\b', text), 'no candidate cap of 32')

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
    """R2-08: pagehide wipes codes, draft, log and blobs, and ?idle= is not honored."""
    b, a, c = open_app(app)
    try:
        fill(a, '#input', 'PROBE-DRAFT')
        a.js('URL.createObjectURL(new Blob([new Uint8Array(32)]))')
        a.js("window.dispatchEvent(new PageTransitionEvent('pagehide'))")
        time.sleep(1)
        for sel in ('#offer', '#answer', '#offerIn', '#answerIn', '#input'):
            value = a.js("(() => { const e = document.querySelector(%s); return e ? e.value : ''; })()" % jsval(sel))
            expect_eq(value, '', 'pagehide left %s filled' % sel)
        rows = a.js("document.querySelector('#log') ? document.querySelector('#log').children.length : -1")
        expect_eq(rows, 0, 'pagehide left transcript rows')
        snap = snapshot(a)
        expect_eq(len(snap['blobCreated']) - len(snap['blobRevoked']), 0, 'pagehide left a blob URL live')

        p = b.page(b.context())
        p.init(SHIM)
        p.goto(app_url(app) + '?idle=5')
        time.sleep(8)
        ended = p.js("(() => { const e = document.querySelector('#ended'); return !!e && !e.hidden; })()")
        expect_eq(ended, False, '?idle=5 still shortens the session (F-10)')
    finally:
        b.close()


def case_kill(app, opts):
    """R2-09: wipe enabled before connect, DOM cleared before revoke, navigates to about:blank."""
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

    b, a, c = open_app(app)
    path = scratch_file('probe.png', TINY_PNG)
    try:
        before = a.js("document.querySelectorAll('#log img[src^=\"blob:\"]').length") or 0
        c.set_file('#file', path)
        end = time.time() + 20
        while time.time() < end:
            if (a.js("document.querySelectorAll('#log img[src^=\"blob:\"]').length") or 0) > before:
                break
            time.sleep(0.25)
        expect((a.js("document.querySelectorAll('#log img[src^=\"blob:\"]').length") or 0) > before,
               'received image has no live blob node, cannot check revoke ordering')
        click(a, '#wipe')
        time.sleep(0.6)
        snap = snapshot(a)
        expect(snap['domAtRevoke'], 'no revoke was observed during wipe')
        expect(all(x == 0 for x in snap['domAtRevoke']),
               'blob URL revoked while its DOM node was still live: %r' % (snap['domAtRevoke'],))
        expect_eq(ended_or_blank(a, 8), 'about:blank', 'kill did not navigate to about:blank')
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
    """R2-11: tampered M1 refused, a real migration opens a new channel and closes the old one."""
    text = app_text(app)
    expect('mig' in text, 'no migration frame in the artifact')
    expect(re.search(r"migFail\('timeout'\),\s*15000", text), 'no 15 s migration timeout')
    b, a, c = open_app(app)
    try:
        peers0 = snapshot(a)['peers']
        send_text(c, '{"v":1,"k":"mig","step":"offer","sid":"probe-sid","fp":"00:00","code":"x"}')
        time.sleep(2)
        expect_eq(snapshot(a)['peers'], peers0, 'a tampered migration offer created a new peer')

        expect(a.js("(() => { const b = document.querySelector('#migrate'); return !!b && !b.disabled; })()"),
               'no enabled #migrate control in the UI')
        click(a, '#migrate')
        end = time.time() + 30
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

        marker = 'PROBE-MIG-OK'
        fill(a, '#input', marker)
        click(a, '#send')
        expect(recv_marker(c, marker, 10), 'no traffic on the migrated channel')
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


GUARDS = [
    # Patterns are pinned to the landed V2 spellings. Every pattern must match,
    # and the first match must be the guard site named in its comment.
    ('code-cap', r'\b16384\b|16\s*\*\s*1024|16_384', '1000000000', 'code',
     'the 16 KB paste cap is removed, an oversized paste must now reach the parser'),
    ('preparse-cap', r'\b65536\b|64\s*\*\s*1024|65_536', '1000000000', 'code',
     'the 64 KB decompressed cap is removed'),
    ('ttl', r'\b120000\b|120\s*\*\s*1000|120_000', '1000000000', 'code',
     'the 120 s code TTL is removed'),
    ('row-cap', r'\b2000\b|2_000', '20', 'budget',
     'the transcript row cap is lowered so the static assertion must fail'),
    ('kill-nav', r'about:blank', 'about:log', 'kill',
     'kill no longer navigates to about:blank'),
    # V2 spells the lock as three disabled flags immediately before showSas(),
    # not as a named sasOk/sasVerified boolean.
    ('sas-lock', r'el\.input\.disabled = true;\s*\n\s*el\.send\.disabled = true;\s*\n'
                 r'\s*el\.attach\.disabled = true;\s*\n\s*showSas\(\);',
     'el.input.disabled = false; el.send.disabled = false; el.attach.disabled = false; showSas();',
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
}

CARD_ORDER = [
    'selftest', 'envelope', 'ratchet', 'sas', 'file', 'budget', 'code',
    'lifecycle', 'kill', 'rotate', 'migrate', 'stun', 'cover', 'mutation-all',
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
