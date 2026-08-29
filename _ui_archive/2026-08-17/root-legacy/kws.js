// kws.js —— 语音唤醒（KWS）常驻监听控制器
// 由 settings.js 的「语音唤醒(KWS)」开关调用 window.ZZKws.setEnabled(bool) 启动 / 停止。
// 复用 app.js 暴露的 window.ZZVoice 桥（麦克风采集 + 16k 单声道 WAV 编码）抓取 2.5s 音频块，
// 以 application/octet-stream 形式 POST 给 /api/kws，后端返回 { wake:bool, transcript:string }。
// 命中唤醒词：短暂停止 KWS → 触发正常语音对话 → 对话结束后自动恢复 KWS（带防抖，一次唤醒只触发一次）。

const KWS = {
  enabled: false,
  sessionActive: false, // 防抖：一次唤醒只触发一次语音会话
  suspendedByVoice: false,
  indicator: null,
};

function kwsEnsureIndicator() {
  if (KWS.indicator) return KWS.indicator;
  const el = document.createElement('div');
  el.className = 'kws-indicator';
  el.setAttribute('aria-hidden', 'true');
  el.innerHTML = `<span class="kws-pulse"></span><span class="kws-label">唤醒监听中</span>`;
  // 尽量贴着语音球（#btnMic）放置；找不到则固定到左下角
  const mic = document.getElementById('btnMic');
  if (mic && mic.parentNode) mic.parentNode.appendChild(el);
  else document.body.appendChild(el);
  KWS.indicator = el;
  return el;
}

function kwsSetIndicator(on) {
  const el = kwsEnsureIndicator();
  document.body.classList.toggle('kws-listening', on);
  if (el) el.classList.toggle('on', on);
}

// 处理 /api/kws 返回的唤醒结果
async function kwsHandleChunk(wavBuf) {
  if (!KWS.enabled || KWS.sessionActive) return; // 已关闭 / 正在会话中则忽略
  let res;
  try {
    const r = await fetch('/api/kws', {
      method: 'POST',
      headers: { 'Content-Type': 'application/octet-stream' },
      body: wavBuf,
    });
    res = await r.json();
  } catch (e) {
    console.warn('[KWS] 请求失败', e);
    return;
  }
  if (res && res.wake === true) {
    kwsTrigger();
  }
}

// 命中唤醒词：暂停 KWS，启动正常语音对话（对话结束由 onVoiceState 自动恢复）
async function kwsTrigger() {
  if (KWS.sessionActive || !KWS.enabled) return;
  KWS.sessionActive = true;
  kwsSetIndicator(false); // 视觉上先停，进入对话态
  try {
    window.ZZVoice.stopKws();
  } catch (_) {}
  if (!window.ZZVoice.isVoiceActive()) {
    try { window.ZZVoice.startVoice(); } catch (e) { console.warn('[KWS] 启动语音对话失败', e); }
  }
}

function kwsStart() {
  if (KWS.enabled) return;
  KWS.enabled = true;
  kwsSetIndicator(true);
  if (!window.ZZVoice.isVoiceActive()) {
    window.ZZVoice.startKws(kwsHandleChunk);
  } else {
    // 手动语音对话进行中：先标记为被对话挂起，结束后由 onVoiceState 恢复
    KWS.suspendedByVoice = true;
  }
}

function kwsStop() {
  if (!KWS.enabled) return;
  KWS.enabled = false;
  KWS.suspendedByVoice = false;
  KWS.sessionActive = false;
  kwsSetIndicator(false);
  try { window.ZZVoice.stopKws(); } catch (_) {}
}

// 监听语音对话状态：对话开始时暂停 KWS（释放麦克风），结束时恢复
if (window.ZZVoice && window.ZZVoice.onVoiceState) {
  window.ZZVoice.onVoiceState((active) => {
    if (active) {
      if (KWS.enabled) {
        KWS.suspendedByVoice = true;
        try { window.ZZVoice.stopKws(); } catch (_) {}
        kwsSetIndicator(false);
      }
    } else {
      KWS.sessionActive = false;
      if (KWS.enabled && KWS.suspendedByVoice) {
        KWS.suspendedByVoice = false;
        kwsSetIndicator(true);
        window.ZZVoice.startKws(kwsHandleChunk);
      }
    }
  });
}

window.ZZKws = {
  setEnabled: (b) => { if (b) kwsStart(); else kwsStop(); },
  isEnabled: () => KWS.enabled,
  toggle: () => { KWS.enabled ? kwsStop() : kwsStart(); },
};

// ── P11-4：常驻 KWS 自动启动 + CPU 负载监控降频 ──
// 页面加载即依据后端 XIAO6_KWS_ENABLED 自动开始常驻监听，
// 用户说「小6」即可免点击进入语音模式（不再依赖手动开启开关）。
// CPU 监控：rAF 采样帧耗时，持续过载则调高分块间隔（降频）以减轻麦克风处理负担；
// 负载恢复后自动还原 2.5s 分块。
const KWS_CPU = {
  normalMs: 2500,
  slowMs: 6000,
  pauseMs: 50, // 完全暂停阈值（avg 帧耗时 > 50ms ≈ <20fps）
  resumeMs: 33, // 暂停恢复阈值（迟滞，avg < 33ms ≈ >30fps）
  samples: [],
  downclocked: false,
  paused: false,
  raf: 0,
  last: 0,
};

function kwsCpuTick(now) {
  KWS_CPU.raf = requestAnimationFrame(kwsCpuTick);
  if (!KWS_CPU.last) { KWS_CPU.last = now; return; }
  const dt = now - KWS_CPU.last;
  KWS_CPU.last = now;
  KWS_CPU.samples.push(dt);
  if (KWS_CPU.samples.length > 60) KWS_CPU.samples.shift();
  if (KWS_CPU.samples.length < 45) return;
  const avg = KWS_CPU.samples.reduce((a, b) => a + b, 0) / KWS_CPU.samples.length;

  // 完全暂停级（最严重）：持续 < 20fps（avg > pauseMs）停止麦克风采集，保全主链路
  if (!KWS_CPU.paused && !KWS_CPU.downclocked && avg > KWS_CPU.pauseMs) {
    KWS_CPU.paused = true;
    try { window.ZZVoice.stopKws(); } catch (_) {}
    document.body.classList.add('kws-paused');
    console.warn('[KWS] 帧率过低(<20fps)，完全暂停唤醒监听以保全性能');
    return;
  }
  if (KWS_CPU.paused) {
    if (avg < KWS_CPU.resumeMs) {
      KWS_CPU.paused = false;
      document.body.classList.remove('kws-paused');
      if (KWS.enabled && !KWS.sessionActive) {
        try { window.ZZVoice.startKws(kwsHandleChunk); } catch (_) {}
      }
      console.warn('[KWS] 负载恢复，唤醒监听已重启');
    }
    return; // 暂停期间不参与降频切换
  }

  // 降频级：持续低于 ~38fps（>26ms）视为过载，调高分块间隔
  if (!KWS_CPU.downclocked && avg > 26) {
    KWS_CPU.downclocked = true;
    if (window.ZZVoice && window.ZZVoice.setKwsChunkMs) {
      try { window.ZZVoice.setKwsChunkMs(KWS_CPU.slowMs); } catch (_) {}
    }
    document.body.classList.add('kws-downclocked');
    console.warn('[KWS] CPU 负载过高，降级分块间隔至 ' + KWS_CPU.slowMs + 'ms');
  } else if (KWS_CPU.downclocked && avg < 20) {
    KWS_CPU.downclocked = false;
    if (window.ZZVoice && window.ZZVoice.setKwsChunkMs) {
      try { window.ZZVoice.setKwsChunkMs(KWS_CPU.normalMs); } catch (_) {}
    }
    document.body.classList.remove('kws-downclocked');
  }
}

function kwsAutoStart() {
  // 已显式开启（如用户手动开关）则不重复
  if (KWS.enabled) return;
  // 默认尝试常驻监听；以后端 XIAO6_KWS_ENABLED 为准（默认开启 → 免点击唤醒）。
  // 用户若在设置中显式关闭，settings.js 会把后端 kws_enabled 置 false，此处即不自动启动。
  let enabled = true;
  fetch('/api/config')
    .then((r) => r.json())
    .then((d) => {
      if (d && d.kws_enabled === false) enabled = false;
      if (enabled) kwsStart();
    })
    .catch(() => { if (enabled) kwsStart(); });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => { kwsAutoStart(); KWS_CPU.raf = requestAnimationFrame(kwsCpuTick); });
} else {
  kwsAutoStart();
  KWS_CPU.raf = requestAnimationFrame(kwsCpuTick);
}

