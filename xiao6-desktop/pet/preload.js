/* 小6桌宠 · preload bridge（最小 IPC 白名单）
   仅向 renderer 暴露 hide/show 两个安全操作，不暴露 ipcRenderer / Node 能力。 */
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('petAPI', {
  hide: () => ipcRenderer.send('pet-hide'),
  show: () => ipcRenderer.send('pet-show')
});
