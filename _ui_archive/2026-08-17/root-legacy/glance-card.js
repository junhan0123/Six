// glance-card.js — 小6 P11-2 情境 Glance 卡（全息 HUD 信息层）
// 右下角单行玻璃卡：依 活跃 Goal / 提醒 / 天气变化 / IDLE 展示；
// 任意更新重置 5s 计时，超时无变化自动淡出。
// 订阅全局 SSE（window.ZZSSE）的 proactive(hud_state) 事件；
// 同时暴露 window.ZZGlance.update(text, opts) 供 app.js 主动推送（如当前活跃目标）。
// 关闭：/api/hud/config 返回 glance_card=false 时不挂载。

let cfg = { enabled: true };
let el = null;
let hideTimer = 0;
const HOLD_MS = 5000;

const ICONS = {
  reminder: '⏰',
  weather: '🌤',
  goal: '<svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-target"/></svg>',
  thinking: '<svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-brain"/></svg>',
  idle: '💎',
  info: '<svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-info"/></svg>',
};

function ensureEl() {
  el = document.getElementById('glanceCard');
  if (el) return;
  el = document.createElement('div');
  el.id = 'glanceCard';
  el.className = 'glance-card';
  el.setAttribute('role', 'status');
  el.setAttribute('aria-live', 'polite');
  el.style.cssText =
    'position:fixed;right:18px;bottom:18px;max-width:42vw;' +
    'display:flex;align-items:center;gap:8px;padding:10px 14px;' +
    'font-size:13px;line-height:1.4;border-radius:14px;pointer-events:none;' +
    'background:rgba(15,23,42,.55);backdrop-filter:blur(14px) saturate(160%);' +
    '-webkit-backdrop-filter:blur(14px) saturate(160%);' +
    'border:1px solid rgba(255,255,255,.12);color:#e2e8f0;' +
    'box-shadow:0 8px 30px rgba(0,0,0,.35);' +
    'opacity:0;transform:translateY(8px);transition:opacity .45s ease,transform .45s ease;' +
    'z-index:60;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;';
  document.body.appendChild(el);
}

function show() {
  if (!el) return;
  el.style.opacity = '1';
  el.style.transform = 'translateY(0)';
}

function scheduleHide(holdMs) {
  if (hideTimer) clearTimeout(hideTimer);
  hideTimer = setTimeout(() => {
    if (el) {
      el.style.opacity = '0';
      el.style.transform = 'translateY(8px)';
    }
  }, holdMs || HOLD_MS);
}

// 公开：更新卡片内容（kind 决定图标）
function update(text, opts) {
  if (!cfg.enabled || !el) return;
  opts = opts || {};
  const icon = ICONS[opts.kind] || ICONS.info;
  const accent = opts.accent || '';
  el.innerHTML =
    '<span class="glance-ico" style="' + (accent ? 'color:' + accent + ';' : '') + '">' + icon + '</span>' +
    '<span class="glance-txt"></span>';
  el.querySelector('.glance-txt').textContent = text;
  if (opts.title) el.title = opts.title;
  else el.removeAttribute('title');
  // 让每日简报等较长内容可被悬停阅读（pointer-events 仅在该类启用）
  if (opts.kind === 'briefing') el.style.pointerEvents = 'auto';
  else el.style.pointerEvents = '';
  show();
  scheduleHide(opts.hold || HOLD_MS);
}

// ---- SSE 事件处理 ----
function onSse(raw) {
  if (!cfg.enabled || !raw) return;
  let msg;
  try { msg = JSON.parse(raw); } catch { return; }
  const ev = msg.xiao6_event;

  if (ev === 'proactive') {
    const kind = msg.kind;
    if (kind === 'reminder') {
      update(String(msg.content || '有提醒'), { kind: 'reminder' });
    } else if (kind === 'weather') {
      update(String(msg.content || '天气更新'), { kind: 'weather' });
    } else if (kind === 'briefing') {
      // Phase 36.2 · 每日智能（孤儿信号消费）：低打扰、较长驻留、悬停可读全文
      update(String(msg.content || '小6每日简报'), {
        kind: 'briefing',
        accent: '#6cc4ff',
        hold: 9000,
        title: String(msg.content || ''),
      });
    }
    return;
  }

  if (ev === 'hud_state') {
    const s = (msg.state || 'idle');
    if (s === 'thinking') {
      const gid = msg.goal_id ? ' #' + String(msg.goal_id).slice(-4) : '';
      const prog = (msg.progress != null) ? ' ' + Math.round(msg.progress * 100) + '%' : '';
      update('推进目标中' + gid + prog, { kind: 'thinking', accent: '#F5B544' });
    } else if (s === 'idle') {
      // IDLE：短暂提示后淡出
      update('待命中', { kind: 'idle' });
    }
    return;
  }

  if (ev === 'agent_state') {
    // 兜底：未走 hud_state 时也能反映编排态
    const st = msg.state;
    if (st && st !== 'IDLE') {
      update('智能体中 · ' + st, { kind: 'thinking', accent: '#F5B544' });
    }
  }
}

// ---- 自举 ----
async function bootstrap() {
  try {
    const r = await fetch('/api/hud/config');
    const d = await r.json();
    cfg.enabled = !!d.glance_card;
  } catch {
    cfg.enabled = true;
  }
  if (!cfg.enabled) return;
  ensureEl();
  if (window.ZZSSE && window.ZZSSE.onMessage) {
    window.ZZSSE.onMessage(onSse);
  } else {
    window.addEventListener('zz:sse', (e) => onSse(e.detail && e.detail.data));
  }
  // 首屏：轻提示已就绪
  update('全息 HUD 已就绪', { kind: 'idle' });
}

window.ZZGlance = { update, show, hide: scheduleHide, isEnabled: () => cfg.enabled };

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', bootstrap, { once: true });
} else {
  bootstrap();
}
