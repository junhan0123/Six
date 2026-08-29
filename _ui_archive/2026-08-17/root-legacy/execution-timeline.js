/*
 * execution-timeline.js — Phase 10.1 P4 · Execution Timeline（自然语言）
 * ----------------------------------------------------------------------------
 * 把执行过程映射为 5 段自然语言阶段：理解任务 → 制定计划 → 调用工具 → 执行 → 完成。
 * 数据：AppState(intent/goal/agent 状态) + ExecutionChannel(当前执行 step)。
 * 纪律：仅读、仅投影；不写状态、不建事件总线。禁显原始事件名/JSON（非 Developer Debug 风格）。
 */
(function (global) {
  'use strict';

  var PHASES = [
    { key: 'understand', name: '理解任务', desc: '解析意图与上下文' },
    { key: 'plan',      name: '制定计划', desc: '拆解目标与步骤' },
    { key: 'tool',      name: '调用工具', desc: '选取并执行能力' },
    { key: 'execute',   name: '执行',     desc: '推进任务与验证' },
    { key: 'done',      name: '完成',     desc: '交付结果' }
  ];

  var root = null, els = [];
  var unsubs = [];

  function appState() { return (global.AppState && global.AppState.getState) ? global.AppState.getState() : {}; }
  function execSnap() {
    if (global.ExecutionChannel) {
      return { current: global.ExecutionChannel.getCurrent() || null,
               history: global.ExecutionChannel.getExecutions() || [] };
    }
    return { current: null, history: [] };
  }

  function hasIntentStatus(states) {
    var intents = appState().intents || {};
    for (var id in intents) { if (intents[id] && states.indexOf(intents[id].status) >= 0) return true; }
    return false;
  }
  function hasAgentStatus(states) {
    var agents = appState().agents || {};
    for (var id in agents) { if (agents[id] && states.indexOf(agents[id].status) >= 0) return true; }
    return false;
  }
  function hasGoalStatus(states) {
    var goals = appState().goals || {};
    for (var id in goals) { if (goals[id] && states.indexOf(goals[id].status) >= 0) return true; }
    return false;
  }

  // 返回 {activeIdx, doneCount, stepText}
  function compute() {
    var ex = execSnap();
    var cur = ex.current;
    var runningStep = null, lastStep = null;
    if (cur && cur.steps && cur.steps.length) {
      for (var i = 0; i < cur.steps.length; i++) {
        if (cur.steps[i].status === 'running') runningStep = cur.steps[i];
        lastStep = cur.steps[i];
      }
    }
    var execRunning = !!(cur && cur.status === 'running');
    var execCompleted = !!(cur && cur.status === 'completed');

    // 阶段派生
    var s = { understand: false, plan: false, tool: false, execute: false, done: false };
    // 理解：意图分析中/已分类 或 智能体思考
    if (hasIntentStatus(['Received', 'Analyzing', 'Classified']) || hasAgentStatus(['Thinking'])) s.understand = true;
    // 制定计划：意图已接受/已转换 或 目标已建/已启 或 智能体已启
    if (hasIntentStatus(['Accepted', 'Converted']) || hasGoalStatus(['Created', 'Started', 'Running']) || hasAgentStatus(['Started'])) s.plan = true;
    // 调用工具：有 step（任何）
    if (lastStep) s.tool = true;
    // 执行：智能体工作 或 执行进行中
    if (hasAgentStatus(['Working']) || execRunning) s.execute = true;
    // 完成：执行已完成
    if (execCompleted) s.done = true;

    // 活动阶段：取最后一个为 true 的索引（流程向前推进）
    var activeIdx = -1;
    for (var p = 0; p < PHASES.length; p++) if (s[PHASES[p].key]) activeIdx = p;
    if (execCompleted && !s.execute && !s.tool) activeIdx = 4;

    var doneCount = (s.understand ? 1 : 0) + (s.plan ? 1 : 0) + (s.tool ? 1 : 0) + (s.execute ? 1 : 0) + (s.done ? 1 : 0);

    var stepText = '';
    if (runningStep) stepText = '进行：' + (runningStep.label || runningStep.tool);
    else if (lastStep) stepText = '最近：' + (lastStep.label || lastStep.tool);
    else if (execCompleted) stepText = '已交付结果';
    else stepText = cur && cur.prompt ? ('指令：' + cur.prompt.slice(0, 18)) : '待命';

    return { activeIdx: activeIdx, doneCount: doneCount, stepText: stepText };
  }

  function render() {
    if (!root) return;
    var c = compute();
    // UI Consolidation Sprint：无真实任务（activeIdx < 0）时打 .is-idle，
    // 由 ui2.css 收口为轻量一行，不再以 5 个大方块长期占据主界面底部。
    // 纯表现投影——不改变任何阶段判定逻辑，不缓存状态。
    root.classList.toggle('is-idle', c.activeIdx < 0);
    for (var i = 0; i < PHASES.length; i++) {
      var el = els[i]; if (!el) continue;
      el.classList.remove('active', 'done');
      if (i < c.activeIdx) el.classList.add('done');
      else if (i === c.activeIdx) el.classList.add('active');
    }
    var stepEl = root.querySelector('.os-tl-step');
    if (stepEl) stepEl.textContent = c.stepText;
  }

  function build() {
    if (!root) return;
    root.innerHTML = '<div class="os-tl-track"></div>';
    var track = root.querySelector('.os-tl-track');
    els = [];
    PHASES.forEach(function (ph, i) {
      var d = document.createElement('div');
      d.className = 'os-tl-phase';
      d.innerHTML = '<div class="os-tl-step"></div>' +
                    '<div class="os-tl-name">' + ph.name + '</div>' +
                    '<div class="os-tl-desc">' + ph.desc + '</div>';
      track.appendChild(d);
      els.push(d);
    });
    render();
  }

  function init(container) {
    root = container;
    if (!root) return;
    build();
    if (global.AppState && global.AppState.subscribe) {
      unsubs.push(global.AppState.subscribe('*', render));
    }
    if (global.ExecutionChannel && global.ExecutionChannel.subscribe) {
      unsubs.push(global.ExecutionChannel.subscribe(render));
    }
    // 兜底：ZZSSE intent 事件也可能不经过 AppState（系统事件）
    if (global.ZZSSE && global.ZZSSE.onMessage) {
      global.ZZSSE.onMessage(function (raw) {
        try { var m = (typeof raw === 'string') ? JSON.parse(raw) : raw;
          if (m && (m.xiao6_event === 'proactive')) render();
        } catch (e) {}
      });
    }
  }

  global.ExecutionTimeline = { init: init };
})(typeof window !== 'undefined' ? window : globalThis);
