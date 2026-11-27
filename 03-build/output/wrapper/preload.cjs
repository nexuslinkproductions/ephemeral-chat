'use strict';

// BC-W2: one bridge object, one method per capability, primitive arguments only.
// Exactly two verbs, per 11-packaging-executable.md section 9.3: wipe() and badge(on).
// No ipcRenderer, no require and no event object ever crosses the bridge.

const { contextBridge, ipcRenderer } = require('electron');

// The only command ids live in menu.cjs, which main uses to validate before sending. The
// preload validates the shape only: one COMMANDS source, no second list to drift (P-13).
ipcRenderer.on('shell:command', (event, id) => {
  if (typeof id !== 'string' || id.length < 1 || id.length > 32) return;
  window.postMessage({ channel: 'ephemeral:command', id }, '*');
});

contextBridge.exposeInMainWorld('shell', Object.freeze({
  wipe: () => ipcRenderer.invoke('shell:wipe'),
  badge: (on) => (on === true || on === false)
    ? ipcRenderer.invoke('shell:badge', on)
    : Promise.resolve(false)
}));
