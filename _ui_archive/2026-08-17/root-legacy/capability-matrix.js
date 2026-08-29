/*
 * capability-matrix.js — Phase 10.1 P5 · Capability Matrix（六维生命力）
 * ----------------------------------------------------------------------------
 * 六维：思考 / 感知 / Memory / Agent / Tool / Network。全部由既有源派生：
 *   AppState(memory/knowledge/agents/intents) + ExecutionChannel(tool/web)
 *   + PerceptionState(感知, sanctioned 只读投影) + ZZCapabilities(目录规模)。
 * 纪律：取代既有 capabilities-view.js 的 fetch('/api/capabilities') 直连（违规已修正）；
 *       不新建状态/事件总线；仅读投影。
 */
(function (global) {
  'use strict';

  var DIMS = [
    { key: 'think',    ico: '<svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-brain"/></svg>', name: '思考' },
    { key: 'sense',    ico: '<svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-eye"/></svg>', name: '感知' },
    { key: 'memory',   ico: '<svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-save"/></svg>', name: 'Memory' },
    { key: 'agent',    ico: '<svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-robot"/></svg>', name: 'Agent' },
    { key: 'tool',     ico: '<svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-wrench"/></svg>', name: 'Tool' },
    { key: 'network',  ico: '<svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-globe"/></svg>', name: 'Network' }
  ];

  var root = null, tiles = {};
  var unsubs = [];
  var lastWebTs = 0;

  function st() { return (global.AppState && global.AppState.getState) ? global.AppState.getState() : {}; }
  function exec() {
    if (global.ExecutionChannel) return { current: global.ExecutionChannel.getCurrent() || null, history: global.ExecutionChannel.getExecutions() || [] };
    return { current: null, history: [] };
  }

  function countByStatus(coll, statuses) {
    var n = 0; for (var id in coll) { if (coll[id] && statuses.indexOf(coll[id].status) >= 0) n++; } return n;
  }

  function compute() {
    var s = st();
    var ex = exec();
    var cur = ex.current;
    var runningTool = null;
    if (cur && cur.steps) for (var i = 0; i < cur.steps.length; i++) if (cur.steps[i].status === 'running') runningTool = cur.steps[i];

    // web 活动（最近 8s 有 web_fetch/web_search）
    var now = Date.now();
    if (cur && cur.steps) for (var j = 0; j < cur.steps.length; j++) {
      var t = cur.steps[j];
      if ((t.tool === 'web_fetch' || t.tool === 'web_search') && t.completedAt && now - t.completedAt < 8000) lastWebTs = Math.max(lastWebTs, t.completedAt);
    }

    var agents = s.agents || {};
    var thinking = countByStatus(agents, ['Thinking', 'Planning']);
    var agentActive = countByStatus(agents, ['Created', 'Started', 'Thinking', 'Planning', 'Working', 'Waiting']);
    var memCount = Object.keys(s.memory || {}).length + Object.keys(s.knowledge || {}).length;
    var reflecting = !!(s.execution && s.execution.reflecting);

    // 感知（PerceptionState sanctioned 只读投影）
    var senseOn = false;
    if (global.PerceptionState && global.PerceptionState.getPerception) {
      var p = global.PerceptionState.getPerception();
      senseOn = !!(p && ((p.visionFacts && p.visionFacts.length) || (p.ocrSpans && p.ocrSpans.length)));
    }

    var capCount = (global.ZZCapabilities && global.ZZCapabilities.allCapabilities) ? global.ZZCapabilities.allCapabilities().length : 0;

    return {
      think:   { vit: thinking > 0 ? 'busy' : (agentActive > 0 ? 'on' : 'off'), meta: thinking > 0 ? ('思考中 ×' + thinking) : (agentActive > 0 ? '就绪' : '空闲') },
      sense:   { vit: senseOn ? 'on' : 'off', meta: senseOn ? '实时感知' : '待唤醒' },
      memory:  { vit: reflecting ? 'busy' : (memCount > 0 ? 'on' : 'off'), meta: reflecting ? '反思中' : ('已存 ' + memCount) },
      agent:   { vit: agentActive > 0 ? 'busy' : 'off', meta: agentActive > 0 ? ('活跃 ×' + agentActive) : '无任务' },
      tool:    { vit: runningTool ? 'busy' : 'on', meta: runningTool ? ('运行 ' + (runningTool.label || runningTool.tool)) : ('目录 ' + capCount) },
      network: { vit: (now - lastWebTs < 8000) ? 'on' : 'off', meta: (now - lastWebTs < 8000) ? '联网中' : '静默' }
    };
  }

  function render() {
    if (!root) return;
    var c = compute();
    DIMS.forEach(function (d) {
      var tile = tiles[d.key]; if (!tile) return;
      var info = c[d.key];
      tile.el.classList.remove('vit-on', 'vit-busy', 'vit-warn', 'vit-off');
      tile.el.classList.add('vit-' + info.vit);
      tile.meta.textContent = info.meta;
      tile.bar.style.width = (info.vit === 'busy' ? '100%' : info.vit === 'on' ? '60%' : '12%');
    });
  }

  function build() {
    if (!root) return;
    root.innerHTML = '';
    tiles = {};
    DIMS.forEach(function (d) {
      var el = document.createElement('div');
      el.className = 'os-cap';
      el.innerHTML = '<span class="os-cap-vit"></span>' +
        '<div class="os-cap-ico">' + d.ico + '</div>' +
        '<div class="os-cap-name">' + d.name + '</div>' +
        '<div class="os-cap-meta"></div>' +
        '<div class="os-cap-bar"></div>';
      root.appendChild(el);
      tiles[d.key] = { el: el, meta: el.querySelector('.os-cap-meta'), bar: el.querySelector('.os-cap-bar') };
    });
    render();
  }

  function init(container) {
    root = container;
    if (!root) return;
    build();
    if (global.AppState && global.AppState.subscribe) unsubs.push(global.AppState.subscribe('*', render));
    if (global.ExecutionChannel && global.ExecutionChannel.subscribe) unsubs.push(global.ExecutionChannel.subscribe(render));
    if (global.PerceptionState && global.PerceptionState.onPerceptionChange) unsubs.push(global.PerceptionState.onPerceptionChange(render));
    setInterval(render, 2500); // web 活动时效刷新
  }

  global.CapabilityMatrix = { init: init };
})(typeof window !== 'undefined' ? window : globalThis);
