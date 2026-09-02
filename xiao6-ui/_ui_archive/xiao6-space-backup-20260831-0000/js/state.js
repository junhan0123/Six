/* ═════════════════════════════════════════════════════════════════
   Xiao6 UI-R1 · state.js — 全局状态层（UI-R1-B：唯一 Runtime 状态源）
   数据流（单向，禁止旁路）：
       API / SSE  →  state.js  →  Timeline / Inspector / Status Bar
   所有 Agent 状态来自真实 API 与真实 SSE 事件，绝不生成假的：
   执行过程 / 进度 / 成功 / 停止 / 工具调用。
   localStorage key 冻结：不得改名。
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

  // ───────────────────── 快照字段 ─────────────────────
  var snap = {
    agent: { state: 'IDLE' },
    tasks: [], goals: [], memories: [], notes: [],
    knowledge: { docs: [] }, capabilities: [],
    memory: {}, briefing: {}, calendar: {}, health: {}
  };
  var busy = false;
  var busyDetail = null;   // 「小6现在正在做什么」的当前动作描述（真实事件驱动）
  var toolModes = { think: false, web: true, code: 'auto' };
  var autoSpeak = lsGet('xiao6_autoSpeak', '1') !== '0';
  var sessionId = lsGet('xiao6_sid', null);
  if (!sessionId) { sessionId = 'x6-' + Date.now(); lsSet('xiao6_sid', sessionId); }
  var trust = { intent: null, risk: null };

  // ───────────────────── Runtime 状态（真实 API/SSE 驱动）─────────────────────
  // 只存「无法从 timeline 派生」的最小集合，其余一律由 derive 计算。
  var runtime = {
    agentState: 'IDLE',     // 来自 /api/agent/state 与 agent_state SSE
    currentGoalId: null,    // 来自 GOAL_* 事件 / /api/agent/state.current_goal
    currentTaskId: null,    // 来自 TASK_* 事件
    lastError: null,        // { message, source, ts } —— 真实错误，不吞
    streamConnected: false  // EventSource onopen 置真
  };

  // ───────────────────── Timeline（UI view model，唯一事件真相源）─────────────────────
  // 节点：{ id, type, status, title, summary, detail, timestamp,
  //         tool, goalId, taskId, executionId, actionId, agentId, ticket }
  // id 必须由真实主键构成（execution_id / goalId / taskId / ticket）或事件自身的 ts，
  // 禁止随机 ID —— 否则刷新/重连会重复生成节点。
  var timeline = [];
  var timelineIndex = Object.create(null);

  function nodeSeq() { return timeline.length; }

  /**
   * 插入或更新一个 Timeline 节点。
   * - 已存在：就地合并（保留首次 timestamp，更新 status/detail）
   * - 不存在：追加到末尾（事件按到达顺序即时间顺序）
   * 返回节点对象。
   */
  function upsertNode(node) {
    if (!node || !node.id) return null;
    var existing = timelineIndex[node.id];
    if (existing) {
      // 只覆盖真实给出的字段；undefined 不覆盖，避免把已完成状态冲掉
      Object.keys(node).forEach(function (k) {
        if (k.charAt(0) === '_') return;
        if (node[k] !== undefined) existing[k] = node[k];
      });
      existing._ver = (existing._ver || 0) + 1;
      return existing;
    }
    node.seq = nodeSeq();
    if (node.status === undefined) node.status = 'pending';
    if (node.timestamp === undefined) node.timestamp = Date.now();
    node._ver = 1;
    timeline.push(node);
    timelineIndex[node.id] = node;
    return node;
  }
  function patchNode(id, patch) {
    var n = timelineIndex[id];
    if (!n) return null;
    Object.keys(patch || {}).forEach(function (k) { if (k.charAt(0) !== '_') n[k] = patch[k]; });
    n._ver = (n._ver || 0) + 1;
    return n;
  }
  function getNode(id) { return timelineIndex[id] || null; }
  function resetTimeline() { timeline.length = 0; timelineIndex = Object.create(null); }

  // ───────────────────── 派生视图（不重复存储，避免两份真相）─────────────────────
  function byType(type) {
    return timeline.filter(function (n) { return n.type === type; });
  }
  var derive = {
    /** 正在执行的工具：[{ executionId, tool, goalId, startedAt }] */
    activeTools: function () {
      return timeline
        .filter(function (n) { return n.type === 'tool' && n.status === 'running'; })
        .map(function (n) {
          return { executionId: n.executionId, tool: n.tool, goalId: n.goalId, startedAt: n.timestamp };
        });
    },
    /** 等待确认的审批单：[{ ticket, tool, summary, ts }] */
    pendingApprovals: function () {
      return timeline
        .filter(function (n) { return n.type === 'approval' && n.status === 'blocked'; })
        .map(function (n) {
          return { ticket: n.ticket, tool: n.tool, summary: n.summary, ts: n.timestamp };
        });
    },
    /** 当前动作：优先正在跑的工具，其次最近一次尚未终结的分析/规划节点 */
    currentAction: function () {
      var running = timeline.filter(function (n) { return n.status === 'running'; });
      for (var i = running.length - 1; i >= 0; i--) {
        var n = running[i];
        if (n.type === 'tool') return { kind: 'tool', label: n.tool, executionId: n.executionId, node: n };
        if (n.type === 'task') return { kind: 'task', label: n.title || ('任务 #' + n.taskId), node: n };
        if (n.type === 'goal') return { kind: 'goal', label: n.title || ('目标 #' + n.goalId), node: n };
      }
      return null;
    },
    /** 当前目标（标题从 /api/goals 真实快照取，SSE 只给 ID） */
    currentGoal: function () {
      var gid = runtime.currentGoalId;
      if (gid == null) return null;
      for (var i = 0; i < snap.goals.length; i++) {
        if (Number(snap.goals[i].id) === Number(gid)) return snap.goals[i];
      }
      // 快照还没到（首屏竞态）：不编造标题，返回仅含 ID 的占位
      return { id: gid, title: null, status: null, progress: null };
    },
    /** 当前任务（标题从 /api/tasks 真实快照取） */
    currentTask: function () {
      var tid = runtime.currentTaskId;
      if (tid == null) return null;
      for (var i = 0; i < snap.tasks.length; i++) {
        if (Number(snap.tasks[i].id) === Number(tid)) return snap.tasks[i];
      }
      return { id: tid, title: null, status: null };
    },
    /** 某个 Goal 的真实任务计数（done / total）——没有真实数据就返回 null，不生成百分比 */
    taskCounts: function (goalId) {
      var re = new RegExp('来自目标\\s*#' + Number(goalId) + '\\b');
      var list = snap.tasks.filter(function (t) { return re.test(String(t.note || '')); });
      if (!list.length) return null;
      var done = list.filter(function (t) {
        var s = String(t.status || '').toLowerCase();
        return s === 'done' || s === 'completed' || s === 'closed';
      }).length;
      return { done: done, total: list.length };
    },
    /** 最近一条未完成（失败）节点 */
    lastFailed: function () {
      for (var i = timeline.length - 1; i >= 0; i--) {
        if (timeline[i].status === 'failed') return timeline[i];
      }
      return null;
    },
    nodesOfType: byType
  };

  // ───────────────────── 订阅 / 通知 ─────────────────────
  var _subs = [];
  function subscribe(fn) { _subs.push(fn); return function () { var i = _subs.indexOf(fn); if (i >= 0) _subs.splice(i, 1); }; }
  function notify() { _subs.forEach(function (fn) { try { fn(); } catch (e) { console.error('[Xiao6.state] subscriber error', e); } }); }

  // ───────────────────── 运行时状态（CORE_TEXT 词表 + DOM 联动）─────────────────────
  var CORE_TEXT = {
    IDLE: '小6在线', LISTENING: '倾听中', THINKING: '正在分析', PLANNING: '正在规划',
    RUNNING: '正在执行', EXECUTING: '正在执行', SPEAKING: '回应中',
    WAITING: '等待确认', WAITING_APPROVAL: '等待确认',
    FAILED: '执行失败', ERROR: '执行失败', OFFLINE: '离线',
    COMPLETED: '已完成', STOPPED: '已停止'
  };
  function setState(st, opts) {
    opts = opts || {};
    var low = String(st || 'IDLE').toLowerCase();
    runtime.agentState = String(st || 'IDLE').toUpperCase();
    var rt = $('runtimeState');
    if (rt) { rt.dataset.mode = (low === 'thinking' || low === 'planning' || low === 'executing' || low === 'running' || low === 'listening' || low === 'speaking') ? 'busy' : (low === 'waiting' || low === 'waiting_approval') ? 'waiting' : (low === 'failed' || low === 'error' || low === 'offline') ? 'off' : 'online'; var rtText = rt.querySelector('.x6-status-text') || rt.querySelector('b'); if (rtText) rtText.textContent = CORE_TEXT[runtime.agentState] || '小6在线'; }
    var mo = qs('#orbBtn .x6-mini-orb'); if (mo) mo.dataset.state = low;
    var op = $('orbPresence'); if (op) op.dataset.state = low;
    var cs = $('ctxStateDot'); if (cs) { cs.className = 'x6-statedot ' + ((low === 'thinking' || low === 'executing' || low === 'listening') ? 'ongoing' : (low === 'error' ? 'error' : 'done')); }
    if (opts.ctxText && $('ctxStateText')) $('ctxStateText').textContent = opts.ctxText;
  }

  // ───────────────────── 快照拉取（逐项落地，慢端点不阻塞首屏）─────────────────────
  function asList(v, key) { if (Array.isArray(v)) return v; if (v && Array.isArray(v[key])) return v[key]; return []; }

  var SNAPSHOT_ENDPOINTS = [
    { url: '/api/agent/state', apply: function (d) { if (d) { snap.agent = d; if (d.state) runtime.agentState = String(d.state).toUpperCase(); if (d.current_goal && d.current_goal.id != null) runtime.currentGoalId = d.current_goal.id; } } },
    { url: '/api/goals', apply: function (d) { snap.goals = asList(d, 'goals'); } },
    { url: '/api/memories', apply: function (d) { snap.memories = asList(d, 'memories'); } },
    { url: '/api/knowledge', apply: function (d) { if (d) snap.knowledge = d; } },
    { url: '/api/capabilities', apply: function (d) { snap.capabilities = (d && Array.isArray(d.items)) ? d.items : asList(d, 'capabilities'); } },
    { url: '/api/tasks', apply: function (d) { snap.tasks = asList(d, 'tasks'); } },
    { url: '/api/health', apply: function (d) { if (d) snap.health = d; } },
    { url: '/api/memory', apply: function (d) { if (d) snap.memory = d; } },
    { url: '/api/briefing', apply: function (d) { if (d) snap.briefing = d; } },
    { url: '/api/calendar/events', apply: function (d) { if (d) snap.calendar = d; } },
    { url: '/api/notes', apply: function (d) { snap.notes = asList(d, 'notes'); } }
  ];
  function fetchSnapshot() {
    return Promise.all(SNAPSHOT_ENDPOINTS.map(function (ep) {
      return api.getJSON(ep.url).then(function (d) {
        try { ep.apply(d); } catch (e) { console.error('[Xiao6.state] snapshot apply error', ep.url, e); }
        notify();
      });
    }));
  }

  window.Xiao6.state = {
    snap: snap,
    busy: busy,
    busyDetail: busyDetail,
    toolModes: toolModes,
    autoSpeak: autoSpeak,
    sessionId: sessionId,
    timeline: timeline,
    runtime: runtime,
    derive: derive,
    trust: trust,
    CORE_TEXT: CORE_TEXT,
    lsGet: lsGet,
    lsSet: lsSet,
    subscribe: subscribe,
    notify: notify,
    setState: setState,
    fetchSnapshot: fetchSnapshot,
    upsertNode: upsertNode,
    patchNode: patchNode,
    getNode: getNode,
    resetTimeline: resetTimeline
  };
})();
