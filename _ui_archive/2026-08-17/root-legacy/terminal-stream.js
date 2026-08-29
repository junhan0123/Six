// 终端流面板（原生 · Task #42）
// 数据源：GET /api/logs（服务端 xiao6.log 尾部实时轮询）。
const TS_REFRESH_MS = 2500;

const TS_PANEL_HTML = `
<div class="term-panel" id="termPanel">
  <div class="ts-boot"></div>
  <div class="ts-inner">
    <div class="ts-top">
      <div class="ts-title"><span class="ts-glyph"><svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-scroll"/></svg></span> 终端流 · TERMINAL <span class="ts-sub">LIVE LOG</span></div>
      <div class="ts-actions">
        <button class="ts-clear-btn" id="tsClearBtn" title="清屏(仅视图)">清屏</button>
        <button class="ts-exit-btn" id="tsExitBtn" title="关闭"><svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-close"/></svg></button>
      </div>
    </div>
    <div class="ts-screen" id="tsScreen"></div>
    <div class="ts-inputline">
      <span class="ts-prompt">xiao6@xiao6:~$</span>
      <span class="ts-cursor">▋</span>
    </div>
  </div>
</div>`;

let _tsTimer = null;
let _tsBuffer = [];

function appendLog(lines) {
  const screen = document.getElementById("tsScreen");
  if (!screen) return;
  (lines || []).forEach(ln => {
    const div = document.createElement("div");
    div.className = "ts-line";
    // 简单上色：含 ERROR/失败 红，API/GET 青，时间戳灰
    if (/ERROR|失败|错误|Traceback/i.test(ln)) div.classList.add("ts-err");
    else if (/API|GET|POST/i.test(ln)) div.classList.add("ts-api");
    else if (/^\[\d{2}:\d{2}:\d{2}\]/.test(ln)) div.classList.add("ts-time");
    div.textContent = ln;
    screen.appendChild(div);
  });
  // 控制 DOM 体积
  while (screen.childElementCount > 400) screen.removeChild(screen.firstChild);
  screen.scrollTop = screen.scrollHeight;
}

function refreshTerm() {
  fetch("/api/logs").then(r => r.json()).then(d => {
    if (!d || !d.ok) return;
    const lines = d.lines || [];
    // 只追加比已显示多的新行（按末尾对齐）
    const prev = _tsBuffer;
    if (prev.length && lines.length >= prev.length &&
        lines.slice(-prev.length).join("\n") === prev.join("\n")) {
      return; // 无新增
    }
    const diff = lines.slice(prev.length);
    if (diff.length) appendLog(diff);
    _tsBuffer = lines.slice(-200);
  }).catch(() => {});
}

function setTermMode(on) {
  document.body.classList.toggle("term-mode", on);
  const p = document.getElementById("termPanel");
  if (on) {
    p.classList.add("ts-booting");
    setTimeout(() => p.classList.remove("ts-booting"), 700);
    _tsBuffer = [];
    document.getElementById("tsScreen").innerHTML = "";
    refreshTerm();
    _tsTimer = setInterval(refreshTerm, TS_REFRESH_MS);
  } else {
    if (_tsTimer) clearInterval(_tsTimer);
    _tsTimer = null;
  }
}

function initTerm() {
  if (document.getElementById("termPanel")) return;
  document.body.insertAdjacentHTML("beforeend", TS_PANEL_HTML);
  document.getElementById("tsExitBtn").onclick = () => setTermMode(false);
  document.getElementById("tsClearBtn").onclick = () => {
    document.getElementById("tsScreen").innerHTML = "";
    _tsBuffer = [];
  };
  const btn = document.getElementById("tsOpenBtn");
  if (btn) btn.onclick = () => setTermMode(!document.body.classList.contains("term-mode"));
}

if (typeof document !== "undefined") {
  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", initTerm);
  else initTerm();
}

// 暴露给「更多」菜单 / 任务弹窗系统统一调度
if (typeof window !== "undefined") {
  window.ZZTerminal = { open: () => setTermMode(true), close: () => setTermMode(false) };
}
