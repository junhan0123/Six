// 小6 · Personal AI 统一画像面板（Phase 37.2 · Task 6 可信度产品闭环）
//
// 数据层明确区分：🟡AI推断 / 🟢用户确认 / ⚪系统事实
// 允许对每条记忆：确认 / 纠正 / 忽略（append-only 账本，绝不改原始记忆）
// 诚实：推断 ≠ 事实；确认后数据在统一画像中获得更高优先级。
//
// 复用 OverlayManager 统一浮层栈；window.ZZPersonalAI 暴露入口。
// 依赖：/api/personal_ai（GET 聚合视图）、/api/memory/confirm（POST 动作）。

const PAI = { panel: null, open: false, data: null };

function paiEscape(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function paiMark(label) {
  if (label === "CONFIRMED") return "🟢";
  if (label === "CORRECTED") return "🟡";
  if (label === "SYSTEM") return "⚪";
  return "🟡"; // INFERENCE
}

function paiLabelText(label) {
  return ({
    CONFIRMED: "用户确认", CORRECTED: "已纠正", SYSTEM: "系统事实", INFERENCE: "AI推断",
  })[label] || "AI推断";
}

function paiBuild() {
  const el = document.createElement("div");
  el.className = "zz-panel pai-panel";
  el.innerHTML = `
    <div class="zz-panel-head">
      <span class="zz-panel-title">🧠 个性化 · 统一画像</span>
      <span class="zz-panel-sub">让小6更懂你（诚实区分推断与事实）</span>
      <button class="zz-panel-close" data-pai-close>✕</button>
    </div>
    <div class="zz-panel-body" id="pai-body">
      <div class="pai-loading">加载中…</div>
    </div>`;
  return el;
}

async function paiLoad() {
  const body = document.getElementById("pai-body");
  if (!body) return;
  try {
    const r = await fetch("/api/personal_ai", { cache: "no-store" });
    const d = await r.json();
    if (!d || d.ok === false) {
      body.innerHTML = `<div class="pai-empty">暂无数据：${paiEscape(d && d.error || "未知")}</div>`;
      return;
    }
    PAI.data = d;
    paiRender(d, body);
  } catch (e) {
    body.innerHTML = `<div class="pai-empty">加载失败：${paiEscape(e)}</div>`;
  }
}

function paiRender(d, body) {
  const idr = d.identity || {};
  const proj = d.projection || [];
  const stats = d.label_stats || {};
  const uc = d.unified_context || "";

  const conflictHtml = idr.conflict
    ? `<div class="pai-conflict">⚠️ 双源冲突已解析：user_model.role=<b>${paiEscape(idr.role)}</b>
       （来源 ${paiEscape(idr.role_source)}）＞ personal_context.role=<b>${paiEscape(idr.pc_role || "")}</b>。
       解析：${paiEscape(idr.resolution || "")}</div>`
    : "";

  const statHtml = `<div class="pai-stats">记忆可信层级：
    🟢确认 ${stats.CONFIRMED || 0} · 🟡推断 ${stats.INFERENCE || 0} ·
    🟡已纠正 ${stats.CORRECTED || 0} · ⚪系统 ${stats.SYSTEM || 0} ·
    确认账本 ${d.ledger_count || 0} 条</div>`;

  const rows = proj.map((m) => {
    const mark = paiMark(m.label);
    const lt = paiLabelText(m.label);
    return `<div class="pai-mem" data-id="${m.id}">
      <span class="pai-mark" title="${lt}">${mark}</span>
      <span class="pai-mem-content">${paiEscape(m.content || "")}</span>
      <span class="pai-mem-meta">${paiEscape(m.type || "")} · 置信${m.confidence != null ? m.confidence.toFixed(2) : "?"}</span>
      <span class="pai-actions">
        <button data-act="confirm" data-id="${m.id}">确认</button>
        <button data-act="correct" data-id="${m.id}">纠正</button>
        <button data-act="ignore" data-id="${m.id}">忽略</button>
      </span>
    </div>`;
  }).join("");

  body.innerHTML = `
    <div class="pai-section">
      <div class="pai-id">身份：${paiEscape(idr.name || "小6")}（${paiEscape(idr.role || "")}）⚪</div>
      ${conflictHtml}
      ${statHtml}
    </div>
    <div class="pai-section">
      <div class="pai-h">记忆确认 / 纠正 / 忽略</div>
      <div class="pai-mems">${rows || '<div class="pai-empty">（无记忆）</div>'}</div>
    </div>
    <div class="pai-section">
      <div class="pai-h">统一画像（注入系统提示词，🟢确认＞🟡推断）</div>
      <pre class="pai-uc">${paiEscape(uc || "（空）")}</pre>
    </div>`;

  // 绑定动作按钮
  body.querySelectorAll(".pai-actions button").forEach((btn) => {
    btn.addEventListener("click", () => paiAct(btn.getAttribute("data-act"), btn.getAttribute("data-id"), btn));
  });
}

async function paiAct(act, id, btn) {
  if (!id) return;
  let correction = "";
  if (act === "correct") {
    correction = prompt("请输入纠正内容（小6将据此调整行为，且可追溯）：");
    if (correction == null) return;
  }
  btn.disabled = true;
  try {
    const r = await fetch("/api/memory/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ memory_id: Number(id), action: act, correction: correction || "" }),
    });
    const d = await r.json().catch(() => ({}));
    if (d && d.ok) {
      await paiLoad(); // 刷新投影（确认/纠正/忽略立即反映）
    } else {
      alert("操作失败：" + (d && d.error || "未知"));
      btn.disabled = false;
    }
  } catch (e) {
    alert("请求失败：" + e);
    btn.disabled = false;
  }
}

function paiOpen() {
  if (PAI.open && PAI.panel && PAI.panel.isConnected) return;
  PAI.panel = paiBuild();
  document.body.appendChild(PAI.panel);
  PAI.open = true;
  PAI.panel.querySelector("[data-pai-close]").addEventListener("click", paiClose);
  if (window.OverlayManager && typeof window.OverlayManager.track === "function") {
    const type = (window.OverlayManager.OverlayType) ? window.OverlayManager.OverlayType.PANEL : "panel";
    window.OverlayManager.track("personal-ai", { el: PAI.panel, onClose: paiCloseImpl, type: type, trap: false });
  }
  paiLoad();
}

function paiCloseImpl() {
  PAI.open = false;
  if (PAI.panel && PAI.panel.parentNode) PAI.panel.parentNode.removeChild(PAI.panel);
}

function paiClose() {
  if (window.OverlayManager && window.OverlayManager.isOpen && window.OverlayManager.isOpen("personal-ai")) {
    window.OverlayManager.close("personal-ai");
  } else {
    paiCloseImpl();
  }
}

// 若 AboutMe 面板的入口存在，则挂接一个「统一画像」按钮（非侵入）。
window.addEventListener("DOMContentLoaded", () => {
  const hook = document.getElementById("zz-aboutme-open");
  if (hook) hook.addEventListener("click", () => setTimeout(paiOpen, 0));
});

window.ZZPersonalAI = { open: paiOpen, close: paiClose, refresh: paiLoad };
