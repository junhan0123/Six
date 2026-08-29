// main-cognitive.js — 小6 · 主界面认知功能（常驻右侧遥测面板）
// 原独立认知模块（cognitive.html）的"自主行动机制 / 认知指标 / AI 活动"已并入主页面遥测面板：
//   · 自主行动流（#actStream）：连接 /api/stream SSE，展示工具执行 / 主动推送 / 弹窗事件
//   · 认知指标（#act*）：轮询 /api/health /api/memories /api/memories/graph /api/audit
//   · AI 活动（#actAi）：由 app.js 聊天流程经 window.ZZCognitiveFeed 桥接更新
// 语音球状态仍由 app.js 的 setOrb() 驱动（window.ZZAvatar），本模块不再单独建球。

const el = (id) => document.getElementById(id);
const fmtTime = (d = new Date()) => d.toTimeString().slice(0, 8);

const stats = {
  constraint: 1, memory: 0, knowledge: 0, decayed: 0,
  nodes: 0, links: 0, tokRate: '—', recallRate: '—', extractRate: '—'
};

function updateStatusBar() {
  const map = {
    'actConstraint': stats.constraint,
    'actMemory': stats.memory,
    'actKnowledge': stats.knowledge,
    'actDecayed': stats.decayed,
    'actNodes': stats.nodes,
    'actLinks': stats.links,
    'actTok': stats.tokRate,
  };
  for (const [id, v] of Object.entries(map)) {
    const node = el(id);
    if (node) node.textContent = v;
  }
}

// ─── 思考流 ───
class ThoughtStream {
  constructor(containerId, color) {
    this.el = el(containerId);
    this.color = color;
    this.lines = [];
    this.maxLines = 80;
  }
  beginRound() {
    this.lines = [];
    if (this.el) this.el.innerHTML = '';
  }
  newLine(type, { content = '', time = fmtTime() } = {}) {
    const id = `l_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;
    const line = { id, type, content, time, status: null };
    this.lines.push(line);
    if (this.lines.length > this.maxLines) {
      this.lines.shift();
      if (this.el && this.el.firstChild) this.el.firstChild.remove();
    }
    const div = document.createElement('div');
    div.className = 'stream-line';
    div.id = id;
    div.innerHTML = this.renderLine(line);
    this.el?.appendChild(div);
    this.el?.scrollTo({ top: this.el.scrollHeight, behavior: 'smooth' });
    return line;
  }
  setStatus(id, text, state = 'busy') {
    const line = this.lines.find(l => l.id === id);
    if (line) line.status = { text, state };
    const node = document.getElementById(id);
    if (node) {
      let badge = node.querySelector('.line-status');
      if (!badge) {
        badge = document.createElement('span');
        badge.className = 'line-status';
        node.appendChild(badge);
      }
      badge.textContent = text;
      badge.className = `line-status ${state}`;
    }
  }
  appendText(id, text) {
    const line = this.lines.find(l => l.id === id);
    if (line) line.content += text;
    const node = document.getElementById(id);
    if (node) {
      let txt = node.querySelector('.line-text');
      if (!txt) {
        txt = document.createElement('div');
        txt.className = 'line-text';
        node.appendChild(txt);
      }
      txt.textContent = line.content;
      this.el?.scrollTo({ top: this.el.scrollHeight, behavior: 'smooth' });
    }
  }
  tool(id, name, ok) {
    const line = this.lines.find(l => l.id === id);
    if (!line) return;
    const node = document.getElementById(id);
    if (!node) return;
    let toolEl = node.querySelector('.line-tool');
    if (!toolEl) {
      toolEl = document.createElement('div');
      toolEl.className = 'line-tool';
      node.appendChild(toolEl);
    }
    const icon = ok ? '✓' : '✗';
    const spinner = ok ? 'done' : '';
    toolEl.innerHTML = `<span class="tool-spinner ${spinner}"></span><span>${icon} ${name}</span>`;
  }
  renderLine(line) {
    const typeLabels = {
      user: 'USER MSG', tick: 'TICK', tool: 'TOOL', system: 'SYSTEM', reply: 'REPLY', error: 'ERROR'
    };
    const label = typeLabels[line.type] || line.type.toUpperCase();
    return `
      <div class="line-header">
        <span class="line-dot" style="background:${this.color}"></span>
        <span class="line-type" style="color:${this.color}">${label}</span>
        <span class="line-time">${line.time}</span>
      </div>
      ${line.content ? `<div class="line-text">${this.escape(line.content)}</div>` : ''}
    `;
  }
  escape(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
}

let l2 = null;

function setAi(label, detail = '', state = 'busy') {
  const act = el('actAi');
  if (act) act.dataset.state = state;
  if (el('actAi-label')) el('actAi-label').textContent = label;
  if (el('actAi-detail')) el('actAi-detail').textContent = detail;
}

function setConnectionState(text, live = true) {
  const elc = el('actState');
  if (!elc) return;
  elc.innerHTML = live ? `<span class="live-dot"></span>${text}` : text;
  elc.classList.toggle('live', live);
}

// ─── SSE（自主行动机制） ───
function connectSSE() {
  if (!window.ZZSSE) return;
  window.ZZSSE.onState((s) => {
    setConnectionState(s === 'open' ? '已连接' : (s === 'connecting' ? '连接中' : '重连中'), s === 'open');
  });
  window.ZZSSE.onMessage((raw) => {
    try { handleSSE(JSON.parse(raw)); } catch (_) {}
  });
}

function handleSSE(data) {
  if (!data || !data.xiao6_event) return;
  handleEvent(data.xiao6_event, data);
}

function handleEvent(kind, data) {
  if (kind === 'tool_start') {
    l2?.newLine('tool', { content: data.tool || '' });
  } else if (kind === 'tool_end') {
    const lastTool = l2?.lines.slice().reverse().find(l => l.type === 'tool');
    if (lastTool) l2?.tool(lastTool.id, data.tool || lastTool.content, true);
  } else if (kind === 'proactive') {
    l2?.newLine('system', { content: data.content || '' });
  } else if (kind === 'modal') {
    l2?.newLine('system', { content: `[弹窗] ${data.kind || ''}` });
  }
}

// ─── 数据轮询 ───
async function refreshHealth() {
  try {
    const data = await fetch('/api/health').then(r => r.json());
    stats.constraint = data.ok ? 1 : 0;
    updateStatusBar();
  } catch {}
}
async function refreshMemories() {
  try {
    const data = await fetch('/api/memories').then(r => r.json());
    if (Array.isArray(data)) {
      stats.memory = data.length;
      stats.knowledge = data.filter(m => (m.event_type || m.type) === 'knowledge' || (m.tags && String(m.tags).trim())).length;
      stats.decayed = data.filter(m => m.score != null && m.score < 0.3).length;
      updateStatusBar();
    }
  } catch {}
}
async function refreshGraph() {
  try {
    const data = await fetch('/api/memories/graph').then(r => r.json());
    stats.nodes = (data.nodes || data.nodes_ || []).length;
    stats.links = (data.edges || data.links || []).length;
    updateStatusBar();
  } catch {}
}
async function refreshAudit() {
  try {
    const data = await fetch('/api/audit?limit=120').then(r => r.json());
    if (Array.isArray(data)) {
      const oneHour = Date.now() - 3600_000;
      const recent = data.filter(r => new Date(r.ts).getTime() > oneHour);
      const extractTools = new Set(['note_save', 'profile_set', 'reminder_set', 'compress_memory']);
      const recallTools = new Set(['note_list', 'profile_get', 'reminder_list']);
      stats.recallRate = recent.filter(r => recallTools.has(r.tool)).length.toString();
      stats.extractRate = recent.filter(r => extractTools.has(r.tool)).length.toString();
      updateStatusBar();
      const rNode = el('actRecall');
      const eNode = el('actExtract');
      if (rNode) rNode.textContent = stats.recallRate;
      if (eNode) eNode.textContent = stats.extractRate;
    }
  } catch {}
}
function startPolling() {
  refreshHealth(); refreshMemories(); refreshGraph(); refreshAudit();
  setInterval(refreshHealth, 30000);
  setInterval(refreshMemories, 30000);
  setInterval(refreshGraph, 30000);
  setInterval(refreshAudit, 60000);
}

// ─── 聊天流程桥接（由 app.js 调用，更新 AI 活动指示） ───
// 说明：用户消息处理器（L1）已由主界面对话流本身覆盖，这里只同步 AI 活动状态，
// 不再维护独立 L1 流，避免与主对话重复。
const feed = {
  beginTurn(text) {
    setAi('思考中', (text || '').slice(0, 36), 'busy');
  },
  speaking() {
    setAi('回应中', '', 'busy');
  },
  appendReply() {
    setAi('生成中', '', 'busy');
  },
  endTurn() {
    setAi('空闲', '', 'idle');
  }
};
window.ZZCognitiveFeed = feed;

// ─── 初始化 ───
function init() {
  l2 = new ThoughtStream('actStream', '#F5B544');
  setAi('空闲', '', 'idle');
  connectSSE();
  startPolling();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
