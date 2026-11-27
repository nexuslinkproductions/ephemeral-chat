'use strict';

// UX-09 application menu, 13-platform-ux.md section 3.2. The menu mirrors keyboard paths
// that already exist in the core; it adds no mechanism of its own.
//
// Three omissions are requirements: no Reload (a reload is a wipe with no confirmation and
// no panic frame), no Preferences (there are no persisted settings), and no History,
// Bookmarks, Downloads or Developer items. DevTools appears only behind the build flag.
//
// Accelerators are spelled CmdOrCtrl so one template covers macOS, Windows and Linux.

const { Menu } = require('electron');

// The only command ids main may send. The preload enforces the same set on its side.
const COMMANDS = Object.freeze(['new-invite', 'new-session', 'rotate-keys', 'diagnostics']);

function buildMenu({ isDev, sendCommand, onWipe, onAbout }) {
  const template = [
    {
      label: 'ephemeral',
      submenu: [
        { label: 'About ephemeral', click: onAbout },
        { type: 'separator' },
        { role: 'quit', accelerator: 'CmdOrCtrl+Q' }
      ]
    },
    {
      label: 'File',
      submenu: [
        { label: 'New Invite', accelerator: 'CmdOrCtrl+N', click: () => sendCommand('new-invite') },
        { label: 'New Session', accelerator: 'CmdOrCtrl+Shift+N', click: () => sendCommand('new-session') },
        { type: 'separator' },
        { role: 'close', accelerator: 'CmdOrCtrl+W' }
      ]
    },
    {
      label: 'Edit',
      submenu: [
        { role: 'undo' },
        { role: 'redo' },
        { type: 'separator' },
        { role: 'cut' },
        { role: 'copy' },
        { role: 'paste' },
        { role: 'selectAll' }
      ]
    },
    {
      label: 'Session',
      submenu: [
        { label: 'Rotate Keys', accelerator: 'CmdOrCtrl+Shift+K', click: () => sendCommand('rotate-keys') },
        // No accelerator on purpose: double Escape is the panic chord, and a second menu
        // accelerator would be a second path to test.
        { label: 'Wipe Session', click: onWipe }
      ]
    },
    {
      label: 'View',
      submenu: [
        { label: 'Diagnostics', accelerator: 'CmdOrCtrl+Shift+D', click: () => sendCommand('diagnostics') },
        { type: 'separator' },
        { role: 'resetZoom', label: 'Actual Size' },
        { type: 'separator' },
        { role: 'togglefullscreen' }
      ]
    },
    {
      label: 'Window',
      submenu: [
        { role: 'minimize' },
        { role: 'zoom' },
        { type: 'separator' },
        { role: 'front' }
      ]
    },
    {
      label: 'Help',
      submenu: [
        { label: 'What This Protects', click: onAbout },
        { label: 'Verify Build', click: onAbout }
      ]
    }
  ];

  if (isDev) {
    template.push({
      label: 'Developer',
      submenu: [{ role: 'toggleDevTools' }]
    });
  }

  return Menu.buildFromTemplate(template);
}

module.exports = { COMMANDS, buildMenu };
