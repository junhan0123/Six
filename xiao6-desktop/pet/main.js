const { app, BrowserWindow, ipcMain, screen } = require('electron');
const path = require('path');

let petWindow = null;

function createPetWindow() {
  const { width: sw, height: sh } = screen.getPrimaryDisplay().workAreaSize;

  petWindow = new BrowserWindow({
    width: 240,
    height: 240,
    x: Math.floor(sw * 0.82),
    y: Math.floor(sh * 0.68),
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: false,
    maximizable: false,
    minimizable: false,
    hasShadow: false,
    focusable: true,
    fullscreenable: false,
    titleBarStyle: 'hidden',
    type: 'toolbar', // Linux/Win 帮助系统把它当作工具窗，部分桌面环境可使其更浮窗化
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
      backgroundThrottling: false
    }
  });

  petWindow.loadFile(path.join(__dirname, 'pet.html'));

  // 调试时可取消注释
  // petWindow.webContents.openDevTools({ mode: 'detach' });

  petWindow.on('closed', () => { petWindow = null; });

  // 失焦时保持置顶（部分桌面环境需要）
  petWindow.on('blur', () => {
    if (petWindow && !petWindow.isDestroyed()) petWindow.setAlwaysOnTop(true, 'screen-saver');
  });
}

app.whenReady().then(() => {
  createPetWindow();
  app.on('activate', () => { if (petWindow === null) createPetWindow(); });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

// IPC：让渲染进程请求隐藏/显示/移动
ipcMain.on('pet-hide', () => { if (petWindow) petWindow.hide(); });
ipcMain.on('pet-show', () => { if (petWindow) petWindow.show(); });
ipcMain.on('pet-move', (e, { x, y }) => { if (petWindow) petWindow.setPosition(x, y, true); });
