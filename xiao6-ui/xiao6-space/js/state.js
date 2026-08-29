/* ═════════════════════════════════════════════════════════════════
   Xiao6 UI-R1 · state.js — 全局状态层（Phase 1）
   建立 window.Xiao6.state：snap / busy / sessionId / autoSpeak / toolModes /
   agentLog / resultLog + subscribe() / setState() / fetchSnapshot()
   状态唯一实例，禁止副本。localStorage key 保持不变。
   ═════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';
  window.Xiao6 = window.Xiao6 || {};
  var api = window.Xiao6.api;

  function $(id) { return document.getElementById(id); }
  function qs(s) { return document.querySelector(s); }

  // ───────────────────── localStorage 辅助（key 冻结：不得改名）─────────────────────
  function lsGet(key, fallback) { try { var v = localStorage.getItem(key); return v === null ? fallback : v; } catch (e) { return fallback; } }
  function lsSet(key, value) { try { localStorage.setItem(key, value); } catch (e) {} }

  // ───────────────────── 状态字段 ─────────────────────
  var snap = {
    agent: { state: 'IDLE' },
    tasks: [], goals: [], memories: [], notes: [],
    knowledge: { docs: [] }, capabilities: [],
    memory: {}, briefing: {}, calendar: {}, health: {}
  };
  var busy = false;
  var toolModes = { think: false, web: true, code: 'auto' };
  var autoSpeak = lsGet('xiao6_autoSpeak', '1') !== '0';
  var sessionId = lsGet('xiao6_sid', null);
  if (!sessionId) { sessionId = 'xiao6-' + Date.now(); lsSet('xiao6_sid', sessionId); }
  var agentLog = [];   // Agent 活动时间线
  var resultLog = [];  // 最终结果
  var trust = { intent: null, risk: null };  // Phase 8 · 信任分析（意图报告 + 风险检查）

  // ───────────────────── 订阅 / 通知 ─────────────────────
  var _subs = [];
  function subscribe(fn) { _subs.push(fn); return function () { var i = _subs.indexOf(fn); if (i >= 0) _subs.splice(i, 1); }; }
  function notify() { _subs.forEach(function (fn) { try { fn(); } catch (e) { console.error('[Xiao6.state] subscriber error', e); } }); }

  // ───────────────────── 运行时状态（CORE_TEXT 词表 + DOM 联动）─────────────────────
  var CORE_TEXT = {
    IDLE: '在线待命', LISTENING: '倾听中', THINKING: '正在理解', PLANNING: '正在规划',
    RUNNING: '正在执行', EXECUTING: '正在执行', SPEAKING: '回应中',
    WAITING: '等待确认', WAITING_APPROVAL: '等待确认',
    FAILED: '执行失败', ERROR: '执行失败', OFFLINE: '离线'
  };
  function setState(st, opts) {
    opts = opts || {};
    var low = String(st || 'IDLE').toLowerCase();
    var rt = $('runtimeState');
    if (rt) { rt.dataset.mode = (low === 'thinking' || low === 'planning' || low === 'executing' || low === 'running' || low === 'listening' || low === 'speaking') ? 'busy' : (low === 'waiting' || low === 'waiting_approval') ? 'waiting' : (low === 'failed' || low === 'error' || low === 'offline') ? 'off' : 'online'; rt.querySelector('b').textContent = CORE_TEXT[st] || '在线待命'; }
    var mo = qs('#orbBtn .xiao6-mini-orb'); if (mo) mo.dataset.state = low;
    var op = $('orbPresence'); if (op) op.dataset.state = low;
    var cs = $('ctxStateDot'); if (cs) { cs.className = 'xiao6-statedot ' + ((low === 'thinking' || low === 'executing' || low === 'listening') ? 'ongoing' : (low === 'error' ? 'error' : 'done')); }
    if (opts.ctxText && $('ctxStateText')) $('ctxStateText').textContent = opts.ctxText;
  }

  // ───────────────────── 快照拉取（11 接口 → snap → notify）─────────────────────
  function asList(v, key) { if (Array.isArray(v)) return v; if (v && Array.isArray(v[key])) return v[key]; return []; }

  function fetchSnapshot() {
    return Promise.all([
      api.getJSON('/api/agent/state'), api.getJSON('/api/goals'), api.getJSON('/api/memories'),
      api.getJSON('/api/knowledge'), api.getJSON('/api/capabilities'), api.getJSON('/api/tasks'),
      api.getJSON('/api/health'), api.getJSON('/api/memory'), api.getJSON('/api/briefing'),
      api.getJSON('/api/calendar/events'), api.getJSON('/api/notes')
    ]).then(function (r) {
      snap.agent = r[0] || snap.agent;
      snap.goals = asList(r[1], 'goals');
      snap.memories = asList(r[2], 'memories');
      snap.knowledge = r[3] || {};
      snap.capabilities = (r[4] && Array.isArray(r[4].items)) ? r[4].items : asList(r[4], 'capabilities');
      snap.tasks = asList(r[5], 'tasks');
      snap.health = r[6] || {};
      snap.memory = r[7] || {};
      snap.briefing = r[8] || {};
      snap.calendar = r[9] || {};
      snap.notes = asList(r[10], 'notes');
      notify();
    });
  }

  window.Xiao6.state = {
    snap: snap,
    busy: busy,
    toolModes: toolModes,
    autoSpeak: autoSpeak,
    sessionId: sessionId,
    agentLog: agentLog,
    resultLog: resultLog,
    trust: trust,
    CORE_TEXT: CORE_TEXT,
    lsGet: lsGet,
    lsSet: lsSet,
    subscribe: subscribe,
    notify: notify,
    setState: setState,
    fetchSnapshot: fetchSnapshot
  };
})();
