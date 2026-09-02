/**
 * Xiao6 Desktop — 最小 Electron App 入口
 * ------------------------------------------------------------------
 * 职责（严格限定）：创建一个桌面 BrowserWindow，并加载 Xiao6 后端
 * 已 serve 的正式 UI：http://127.0.0.1:8000/
 *
 * 本文件明确【不】负责：
 *   - 启动/托管后端、API、代理（后端由 launcher/start.ps1 单独启动并等待 health）
 *   - 提供或第二次托管 UI 文件（UI 唯一真身：G:\xiao6\ui，由 :8000 直接 serve）
 *   - 任何 UI 构建、数据存储、Agent Runtime
 *
 * 所有页面请求（/api/*、/css/*、/js/*）均与窗口同源，
 * 因此前端可使用相对路径，无需任何代理或跨端口配置。
 */

const { app, BrowserWindow } = require('electron');

// 唯一目标地址：Xiao6 后端。禁止改为其它端口（如已废弃的 8765）。
const TARGET_URL = 'http://127.0.0.1:8000/';

// 关闭硬件加速，改用软件渲染。理由：
//   1) Xiao6 UI 为纯文本/表格/图标，开销极小，软件渲染无感；
//   2) 降低对 GPU 进程的依赖，减少驱动/独显调度带来的渲染进程不稳定。
// 必须在 app.whenReady() 之前调用。
app.disableHardwareAcceleration();

// 关闭 Chromium 沙箱 —— 本机能启动 Electron 的必要条件。
// 实测证据（2026-08-31，Electron 33.4.11 / Windows 10.0.26200）：
//   不关闭沙箱时，GPU 子进程反复崩溃并触发主进程 FATAL 退出：
//     ERROR:gpu_process_host.cc(982)] GPU process exited unexpectedly: exit_code=1
//     FATAL :gpu_data_manager_impl_private.cc(423)] GPU process isn't usable. Goodbye.
//   即使绕开 GPU 崩溃，Renderer 子进程仍会挂起：窗口标题正常、内容区全白，
//   且对 CDP（含最基础的 Runtime.evaluate('1+1')）完全无响应。
//   加 --no-sandbox 后，Renderer 立即恢复响应（readyState=complete，DOM 可读）。
// 说明：本机 Windows 沙箱环境（受限令牌 / Job 对象）无法正常初始化 Electron 子进程。
// 影响面可接受：本窗口只加载同源的 http://127.0.0.1:8000/，且已关闭 nodeIntegration、
// 保留 contextIsolation，页面无任何本地资源访问能力。
// 必须在 app.whenReady() 之前调用。
app.commandLine.appendSwitch('no-sandbox');

// start.ps1 已保证 8000 health 通过后才启动本进程；
// 这里仅在后端极偶发慢绑定时做有限重试，避免白屏。
const MAX_RETRY = 20;
const RETRY_MS = 1000;
const SHOW_FALLBACK_MS = 5000;

let win = null;
let retries = 0;
let showTimer = null;

function loadTarget() {
  if (!win || win.isDestroyed()) return;
  win.loadURL(TARGET_URL).catch(() => {
    /* 加载失败统一由 did-fail-load 处理 */
  });
}

function createWindow() {
  win = new BrowserWindow({
    width: 1320,
    height: 880,
    minWidth: 960,
    minHeight: 640,
    title: '小6 (Six)',
    backgroundColor: '#ffffff',
    autoHideMenuBar: true,
    show: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      // 与上面的 --no-sandbox 保持一致：本机沙箱无法初始化子进程，
      // 单独开启 renderer sandbox 会导致渲染进程挂起（窗口标题在、内容全白）。
      sandbox: false,
      spellcheck: false,
    },
  });

  // 外部链接（非 127.0.0.1:8000）交给系统默认浏览器，不在本窗口内跳转。
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (url && url.startsWith(TARGET_URL)) return { action: 'allow' };
    if (url && /^https?:\/\//i.test(url)) {
      require('electron').shell.openExternal(url);
    }
    return { action: 'deny' };
  });

  win.webContents.on('did-fail-load', (_event, errorCode) => {
    // -3 (ERR_ABORTED) / -2 为导航中断，非真实失败，忽略
    if (errorCode === -3 || errorCode === -2) return;
    if (retries++ < MAX_RETRY) {
      setTimeout(loadTarget, RETRY_MS);
    }
  });

  // 首帧就绪即显示；兜底超时避免后端异常时永久无窗口
  win.once('ready-to-show', showWindow);
  showTimer = setTimeout(showWindow, SHOW_FALLBACK_MS);

  win.on('closed', () => {
    win = null;
    if (showTimer) clearTimeout(showTimer);
  });

  loadTarget();
}

function showWindow() {
  if (showTimer) {
    clearTimeout(showTimer);
    showTimer = null;
  }
  if (win && !win.isDestroyed() && !win.isVisible()) win.show();
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  // Windows / Linux：关闭所有窗口即退出
  if (process.platform !== 'darwin') app.quit();
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
