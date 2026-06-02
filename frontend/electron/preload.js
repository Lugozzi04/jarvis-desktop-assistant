// Jarvis Desktop Assistant — Electron preload script
// Exposes a minimal, secure API to the renderer process.

const { contextBridge } = require('electron');

contextBridge.exposeInMainWorld('jarvisDesktop', {
  platform: process.platform,
  isElectron: true,
  version: '0.3.0',
});
