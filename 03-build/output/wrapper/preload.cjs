'use strict';

// BC-W2: one bridge object, one method per capability, primitive arguments only.
// Exactly two verbs, per 11-packaging-executable.md section 9.3: wipe() and badge(on).
// No ipcRenderer, no require and no event object ever crosses the bridge.

const { contextBridge, ipcRenderer } = require('electron');

const COMMANDS = new Set(['new-invite', 'new-session', 'rotate-keys', 'diagnostics', 'wipe']);

// Main to page direction. postMessage crosses the isolated world boundary through the DOM,
// so the page gets a plain message event and contextBridge stays at two verbs. BC-W3 denies
// every window and frame, so this document is the only possible source.
ipcRenderer.on('shell:command', (event, id) => {
  if (typeof id !== 'string' || !COMMANDS.has(id)) return;
  window.postMessage({ channel: 'ephemeral:command', id }, '*');
});

contextBridge.exposeInMainWorld('shell', Object.freeze({
  wipe: () => ipcRenderer.invoke('shell:wipe'),
  badge: (on) => (on === true || on === false)
    ? ipcRenderer.invoke('shell:badge', on)
    : Promise.resolve(false)
}));
