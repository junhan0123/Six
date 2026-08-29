// 系统资源监控面板（增强版）
// 数据源：GET /api/sysmon（优先 psutil，缺失时用 Windows 原生 API fallback）
const SM_REFRESH_MS = 2000;

const SM_PANEL_HTML = `
<div class="sysmon-panel" id="sysmonPanel">
  <div class="sm-boot"></div>
  <div class="sm-inner">
    <div class="sm-top">
      <div class="sm-title"><span class="sm-glyph"><svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-monitor"/></svg></span> 系统资源监控 <span class="sm-sub">SYSTEM MONITOR</span></div>
      <div class="sm-actions">
        <span class="sm-badge warn" id="smFallbackBadge" hidden>原生 API 模式</span>
        <span class="sm-fetch" id="smFetch">--</span>
        <button class="sm-exit-btn" id="smExitBtn" title="关闭"><svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-close"/></svg></button>
      </div>
    </div>
    <div class="sm-grid">
      <div class="sm-card sm-cpu">
        <div class="sm-card-h"><span>CPU</span><b id="smCpuVal">--%</b></div>
        <div class="sm-cpu-bar"><div class="sm-cpu-fill" id="smCpuFill"></div></div>
        <div class="sm-percore" id="smPerCore"></div>
        <div class="sm-meta" id="smCpuMeta">--</div>
      </div>
      <div class="sm-card sm-mem">
        <div class="sm-card-h"><span>内存</span><b id="smMemVal">--%</b></div>
        <div class="sm-bar"><div class="sm-bar-fill sm-mem-fill" id="smMemFill"></div></div>
        <div class="sm-meta" id="smMemMeta">--</div>
        <div class="sm-detail-row" id="smMemDetail">
          <span>已用 <b id="smMemUsed">--</b></span>
          <span>可用 <b id="smMemAvail">--</b></span>
        </div>
      </div>
      <div class="sm-card sm-gpu">
        <div class="sm-card-h"><span>GPU</span><b id="smGpuVal">--%</b></div>
        <div class="sm-bar"><div class="sm-bar-fill sm-gpu-fill" id="smGpuFill"></div></div>
        <div class="sm-meta" id="smGpuMeta">--</div>
      </div>
      <div class="sm-card sm-net">
        <div class="sm-card-h"><span>网络</span><b id="smNetVal">--</b></div>
        <div class="sm-meta" id="smNetMeta">↑ -- / ↓ --</div>
        <div class="sm-detail-row" id="smNetDetail">
          <span>总上行 <b id="smNetUpTotal">--</b></span>
          <span>总下行 <b id="smNetDownTotal">--</b></span>
        </div>
      </div>
    </div>
    <div class="sm-detail-row" id="smSysInfo">
      <span>平台 <b id="smPlatform">--</b></span>
      <span>核心数 <b id="smCores">--</b></span>
      <span>运行时长 <b id="smUptime">--</b></span>
      <span>采集时间 <b id="smTs">--</b></span>
    </div>
    <div class="sm-disks" id="smDisks"></div>
    <div class="sm-procs">
      <div class="sm-proc-col">
        <div class="sm-proc-h">进程 · CPU 占用 Top</div>
        <table class="sm-proc-tbl" id="smTopCpu"></table>
      </div>
      <div class="sm-proc-col">
        <div class="sm-proc-h">进程 · 内存 占用 Top</div>
        <table class="sm-proc-tbl" id="smTopMem"></table>
      </div>
    </div>
    <div class="sm-foot">
      <span class="sm-foot-dot"></span>
      <span id="smFoot">实时采集中 · 每 ${SM_REFRESH_MS/1000}s 刷新</span>
    </div>
  </div>
</div>`;

let _smTimer = null;

function fmtBytes(n) {
  if (n == null) return "--";
  const u = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
  return n.toFixed(i > 0 ? 1 : 0) + " " + u[i];
}
function fmtBps(b) {
  if (!b) return "0 B/s";
  const u = ["B/s", "KB/s", "MB/s", "GB/s"];
  let i = 0;
  while (b >= 1024 && i < u.length - 1) { b /= 1024; i++; }
  return b.toFixed(1) + " " + u[i];
}
function fmtUptime(s) {
  if (!s) return "--";
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600),
        m = Math.floor((s % 3600) / 60);
  return (d ? d + "天 " : "") + h + "时" + m + "分";
}
function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
}

function renderSysmon(d) {
  if (!d || !d.ok) {
    const foot = document.getElementById("smFoot");
    if (foot) foot.textContent = "监控不可用：" + (d && d.error || "未知");
    return;
  }

  const fbBadge = document.getElementById("smFallbackBadge");
  if (fbBadge) fbBadge.hidden = !d.fallback;

  // CPU
  const cpu = d.cpu || {};
  const cpuPct = cpu.percent ?? 0;
  document.getElementById("smCpuVal").textContent = (cpu.percent ?? "--") + "%";
  document.getElementById("smCpuFill").style.width = cpuPct + "%";
  document.getElementById("smCpuMeta").textContent =
    `${cpu.cores || "?"} 核 · ${cpu.freqMHz ? (cpu.freqMHz/1000).toFixed(2)+' GHz' : '频率未识别'}`;
  const pc = document.getElementById("smPerCore");
  pc.innerHTML = "";
  (cpu.perCore || []).forEach((v, i) => {
    const b = document.createElement("div");
    b.className = "sm-core" + (v >= 80 ? " crit" : v >= 55 ? " hot" : "");
    b.style.height = Math.max(3, v * 0.34) + "px";
    b.title = `核心 ${i + 1}: ${v.toFixed(1)}%`;
    pc.appendChild(b);
  });

  // MEM
  const mem = d.mem || {};
  document.getElementById("smMemVal").textContent = (mem.percent ?? "--") + "%";
  document.getElementById("smMemFill").style.width = (mem.percent ?? 0) + "%";
  document.getElementById("smMemMeta").textContent =
    `${fmtBytes(mem.usedGB * 1024**3)} / ${fmtBytes(mem.totalGB * 1024**3)}`;
  document.getElementById("smMemUsed").textContent = fmtBytes(mem.usedGB * 1024**3);
  document.getElementById("smMemAvail").textContent = fmtBytes(mem.availableGB * 1024**3);

  // GPU
  const gpu = d.gpu || {};
  const gv = document.getElementById("smGpuVal");
  const gf = document.getElementById("smGpuFill");
  const gm = document.getElementById("smGpuMeta");
  if (gpu.available) {
    gv.textContent = gpu.util + "%";
    gf.style.width = gpu.util + "%";
    gm.textContent = `${esc(gpu.name)} · ${gpu.memUsedMB}/${gpu.memTotalMB}MB · ${gpu.tempC}°C`;
  } else {
    gv.textContent = "N/A";
    gf.style.width = "0%";
    gm.textContent = "未检测到 NVIDIA GPU";
  }

  // NET
  const net = d.net || {};
  document.getElementById("smNetVal").textContent = fmtBps(net.downBps);
  document.getElementById("smNetMeta").textContent =
    `↑ ${fmtBps(net.upBps)} / ↓ ${fmtBps(net.downBps)}`;
  document.getElementById("smNetUpTotal").textContent = fmtBytes(net.sentGB * 1024**3);
  document.getElementById("smNetDownTotal").textContent = fmtBytes(net.recvGB * 1024**3);

  // System info
  document.getElementById("smPlatform").textContent = navigator.platform || "--";
  document.getElementById("smCores").textContent = cpu.cores || "--";
  document.getElementById("smUptime").textContent = fmtUptime(d.uptimeSec);
  document.getElementById("smTs").textContent = d.ts || "--";

  // DISKS
  const dc = document.getElementById("smDisks");
  dc.innerHTML = "";
  (d.disks || []).forEach(dk => {
    const el = document.createElement("div");
    el.className = "sm-disk";
    const pct = dk.percent ?? 0;
    const warn = pct >= 85 ? " sm-danger" : pct >= 70 ? " sm-warn" : "";
    el.innerHTML = `<div class="sm-disk-h"><span>${esc(dk.mount)}</span><b>${pct}%</b></div>
      <div class="sm-bar"><div class="sm-bar-fill sm-disk-fill${warn}" style="width:${pct}%"></div></div>
      <div class="sm-meta">${fmtBytes(dk.usedGB * 1024**3)} / ${fmtBytes(dk.totalGB * 1024**3)}</div>`;
    dc.appendChild(el);
  });

  // PROCS
  const fillTbl = (id, rows, key) => {
    const t = document.getElementById(id);
    t.innerHTML = "";
    (rows || []).forEach((r, idx) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td class="sm-p-name">${idx + 1}. ${esc(r.name)}</td>
        <td class="sm-p-val">${r[key]}%</td>
        <td class="sm-p-pid">#${r.pid}</td>`;
      t.appendChild(tr);
    });
  };
  fillTbl("smTopCpu", d.topCpu, "cpu");
  fillTbl("smTopMem", d.topMem, "mem");

  // footer
  let foot = `运行时长 ${fmtUptime(d.uptimeSec)} · 采集于 ${d.ts}`;
  if (d.fallback) foot += " · 未安装 psutil，使用 Windows 原生 API 采集";
  document.getElementById("smFoot").textContent = foot;
}

function refreshSysmon() {
  fetch("/api/sysmon").then(r => r.json()).then(d => {
    renderSysmon(d);
    const fetchEl = document.getElementById("smFetch");
    if (fetchEl) fetchEl.textContent = new Date().toLocaleTimeString();
  }).catch(e => {
    document.getElementById("smFoot").textContent = "采集失败：" + e;
  });
}

function setSysmonMode(on) {
  document.body.classList.toggle("sysmon-mode", on);
  const p = document.getElementById("sysmonPanel");
  if (on) {
    p.classList.add("sm-booting");
    setTimeout(() => p.classList.remove("sm-booting"), 700);
    refreshSysmon();
    _smTimer = setInterval(refreshSysmon, SM_REFRESH_MS);
  } else {
    if (_smTimer) clearInterval(_smTimer);
    _smTimer = null;
  }
}

function initSysmon() {
  if (document.getElementById("sysmonPanel")) return;
  document.body.insertAdjacentHTML("beforeend", SM_PANEL_HTML);
  document.getElementById("smExitBtn").onclick = () => setSysmonMode(false);
  const btn = document.getElementById("smOpenBtn");
  if (btn) btn.onclick = () => setSysmonMode(!document.body.classList.contains("sysmon-mode"));
}

if (typeof document !== "undefined") {
  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", initSysmon);
  else initSysmon();
}

// 暴露给「更多」菜单 / 任务弹窗系统统一调度
if (typeof window !== "undefined") {
  window.ZZSysmon = { open: () => setSysmonMode(true), close: () => setSysmonMode(false) };
}
