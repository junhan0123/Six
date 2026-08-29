/* ═════════════════════════════════════════════════════════════════
   Xiao6 UI-R1 · inspector.js — 右侧 Inspector（检视器）+ Agent 活动 + 实时事件
   由 agent-panel.js 更名而来：职责从「上下文面板」升级为「检视器」，
   承载 5 个分区：概览 / 记忆 / 知识 / 技能 / 工具。

   R1-B（真实 Runtime 状态投影）：
   · 所有 /api/stream 真实事件一律经 state.upsertNode / state.patchNode 写入
     state.timeline（唯一真相源），不再写已废弃的 state.agentLog。
   · 并发安全：stream 通道的 tool_started/tool_finished 带 execution_id，
     按唯一 ID 关联，绝不用 tool name 做并发关联依据。
   · agentList（历史视图「Agent 活动」）由 timeline.renderAgentActivity() 唯一拥有，
     此处仅做向后兼容转发。
   所有数据来自 state.snap（真实 API）与 SSE 真实事件，无任何伪造条目。
   ═════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';
  window.Xiao6 = window.Xiao6 || {};
  var state = window.Xiao6.state;

  function $(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
  function fmtTime(ts) { var d = ts ? new Date(String(ts).replace(/-/g, '/')) : new Date(); if (isNaN(d.getTime())) d = new Date(); var p = function (n) { return n < 10 ? '0' + n : '' + n; }; return p(d.getHours()) + ':' + p(d.getMinutes()); }
  function isOpen(t) { var s = String(t.status || '').toLowerCase(); return s !== 'done' && s !== 'completed' && s !== 'closed'; }

  // ───────────────────── Agent 活动（agentList）─────────────────────
  // agentList 由 timeline.renderAgentActivity() 唯一拥有（派生自 state.timeline）。
  // 此处仅做向后兼容转发，不再直接持有任何状态。
  function renderAgent() {
    if (window.Xiao6.timeline && window.Xiao6.timeline.renderAgentActivity) {
      window.Xiao6.timeline.renderAgentActivity();
    }
  }

  // ───────────────────── RIGHT AGENT PANEL（完整多区块）─────────────────────
  function stateDotHtml(st, text) {
    var cls = (st === 'EXECUTING' || st === 'THINKING' || st === 'LISTENING' || st === 'PLANNING') ? 'ongoing' : (st === 'ERROR' ? 'error' : 'done');
    return '<div class="xiao6-ctx-state"><span class="xiao6-statedot ' + cls + '" id="ctxStateDot"><span class="sd"></span></span><span id="ctxStateText">' + esc(text) + '</span></div>';
  }
  function renderContextAuto() {
    var body = $('ctxBody'); if (!body) return;
    var st = String(state.snap.agent.state || 'IDLE').toUpperCase();
    var h = state.snap.health || {};

    var html = '';
    var title = $('ctxTitle'); if (title) title.textContent = '概览';

    // 当前状态（最高优先级）
    var curAction = state.derive.currentAction();
    var curGoal = state.derive.currentGoal();
    var curTask = state.derive.currentTask();

    // 状态卡片
    html += ctxCard('Agent 状态', stateDotHtml(st, state.CORE_TEXT[st] || '在线待命'));

    // 当前任务
    if (curAction) {
      var actionHtml = '';
      if (curAction.kind === 'tool') {
        actionHtml = '正在执行：' + esc(curAction.label);
      } else if (curAction.kind === 'task') {
        actionHtml = '正在分析：' + esc(curAction.label);
      } else if (curAction.kind === 'goal') {
        actionHtml = '正在规划：' + esc(curAction.label);
      }
      html += ctxCard('当前动作', ctxItem(actionHtml));
    }

    // 当前目标
    if (curGoal) {
      var prog = Number(curGoal.progress || 0);
      html += ctxCard('当前目标',
        ctxItem((curGoal.title || ('目标 #' + curGoal.id))) +
        '<div style="margin-top:6px"><div class="xiao6-prog"><i style="width:' + Math.max(0, Math.min(100, prog)) + '%"></i></div><div style="font-size:11px;color:var(--xiao6-text-faint);margin-top:2px">进度 ' + prog + '%</div></div>'
      );
    }

    // 当前任务列表
    var open = state.snap.tasks.filter(isOpen).slice(0, 4);
    var running = Number((state.snap.agent || {}).running || 0);
    var taskHtml = '';
    if (open.length) {
      taskHtml = open.map(function (t) { return ctxItem((t.title || '任务') + ' · ' + (t.status || '')); }).join('');
    } else if (running) {
      taskHtml = ctxItem('小6核心执行中（' + running + ' 项）');
    } else {
      taskHtml = '<span class="xiao6-empty">无</span>';
    }
    html += ctxCard('任务列表', taskHtml);

    // 审批状态
    var pendingApprovals = state.derive.pendingApprovals();
    if (pendingApprovals.length) {
      html += ctxCard('待确认',
        '<div class="xiao6-ctx-state"><span class="xiao6-statedot warning"><span class="sd"></span></span><span>' +
        pendingApprovals.length + ' 项操作等待确认</span></div>'
      );
    }

    // Tools
    var tools = (h.tools || []);
    html += ctxCard('Tools', tools.length ? ctxItem(tools.length + ' 项可用 · ' + tools.slice(0, 6).join(' · ')) : '<span class="xiao6-empty">无</span>');
    // 模型信息
    html += ctxCard('模型', ctxItem((h.model || '—') + ' · ' + (h.provider || '—')));
    // 信任分析（Phase 8 · Trust Inspector 第 7 卡）
    html += trustCard(state.trust);
    body.innerHTML = html;
  }

  // ───────────────────── Inspector 分区调度 ─────────────────────
  // 5 个分区：概览 / 记忆 / 知识 / 技能 / 工具。
  // 每个分区只展示真实数据快照的前若干条，底部「查看全部」跳到对应的全量视图。
  var inspTab = 'overview';
  function asList(v, key) { if (Array.isArray(v)) return v; if (v && Array.isArray(v[key])) return v[key]; return []; }
  function moreBtn(view) {
    return '<button class="xiao6-insp-more" data-goto="' + view + '" type="button">查看全部 →</button>';
  }
  function renderInspector() {
    var body = $('ctxBody'); if (!body) return;
    var title = $('ctxTitle');
    if (inspTab === 'overview') { if (title) title.textContent = '概览'; renderContextAuto(); return; }

    var html = '';
    if (inspTab === 'memory') {
      if (title) title.textContent = '记忆';
      var mems = state.snap.memories.slice().sort(function (a, b) { return Number(b.id) - Number(a.id); }).slice(0, 5);
      html = mems.length
        ? mems.map(function (m) { return ctxItem(String(m.title || m.content || '记忆').replace(/^Hotspot event:\s*/, '').slice(0, 46)); }).join('') + moreBtn('memory')
        : '<span class="xiao6-empty">暂无记忆 · 与小6对话后自动沉淀</span>';
    } else if (inspTab === 'knowledge') {
      if (title) title.textContent = '知识';
      var docs = asList(state.snap.knowledge, 'docs').slice(0, 5);
      var total = Number((state.snap.knowledge && (state.snap.knowledge.count || (state.snap.knowledge.stats && state.snap.knowledge.stats.total))) || docs.length);
      html = docs.length
        ? ctxItem('共 ' + total + ' 篇') + docs.map(function (d) { return ctxItem((d.title || '文档') + (d.domain ? ' · ' + d.domain : '')); }).join('') + moreBtn('knowledge')
        : '<span class="xiao6-empty">知识库为空</span>';
    } else if (inspTab === 'capability') {
      if (title) title.textContent = '技能';
      var caps = state.snap.capabilities.slice(0, 6);
      html = caps.length
        ? caps.map(function (c) { return ctxItem((c.icon || '') + ' ' + (c.label || c.id)); }).join('') + moreBtn('capabilities')
        : '<span class="xiao6-empty">暂无能力数据</span>';
    } else if (inspTab === 'tools') {
      if (title) title.textContent = '工具';
      var tools = (state.snap.health && state.snap.health.tools) || [];
      html = tools.length
        ? ctxItem(tools.length + ' 项可用') + tools.slice(0, 6).map(function (t) { return ctxItem(t); }).join('') + moreBtn('tools')
        : '<span class="xiao6-empty">暂无工具数据</span>';
    }
    body.innerHTML = html;
  }
  function setInspTab(tab) {
    inspTab = tab || 'overview';
    Array.prototype.forEach.call(document.querySelectorAll('.xiao6-insp-tab'), function (b) {
      b.classList.toggle('is-active', b.dataset.insp === inspTab);
    });
    renderInspector();
  }

  function renderContext(kind) {
    var body = $('ctxBody'); if (!body) return;
    var title = $('ctxTitle'); if (title) title.textContent = { context: '上下文', tasks: '任务进度', memory: '记忆', capability: '能力', result: '最新结果', approval: '待确认' }[kind] || '上下文';
    var html = '';
    if (kind === 'context') {
      var st = String(state.snap.agent.state || 'IDLE').toUpperCase();
      html += ctxCard('运行时', stateDotHtml(st, state.CORE_TEXT[st] || '在线待命'));
      html += ctxCard('模型', ctxItem((state.snap.health && state.snap.health.model || '—') + ' · ' + (state.snap.health && state.snap.health.provider || '—')));
    } else if (kind === 'tasks') {
      var open = state.snap.tasks.filter(isOpen).slice(0, 6);
      html += ctxCard('进行中的任务', open.length ? open.map(function (t) { return ctxItem(t.title || '任务'); }).join('') : '<span class="xiao6-empty">无</span>');
    } else if (kind === 'memory') {
      var mems = state.snap.memories.slice(0, 5);
      html += ctxCard('近期记忆', mems.length ? mems.map(function (m) { return ctxItem(String(m.title || m.content || '').slice(0, 40)); }).join('') : '<span class="xiao6-empty">无</span>');
    } else if (kind === 'capability') {
      var caps = state.snap.capabilities.slice(0, 6);
      html += ctxCard('能力', caps.length ? caps.map(function (c) { return ctxItem((c.icon || '') + ' ' + (c.label || c.id)); }).join('') : '<span class="xiao6-empty">无</span>');
    } else if (kind === 'result') {
      // R1-B：最新结果派生自 state.timeline 中的真实 assistant 回复，不再读已废弃的 resultLog
      var replies = state.timeline.filter(function (n) { return n.type === 'assistant' && n.text; });
      var last = replies.length ? replies[replies.length - 1] : null;
      html += ctxCard('最新结果', ctxItem((last && last.text ? last.text : '').slice(0, 120)));
    } else if (kind === 'approval') {
      html += ctxCard('待确认', '<div class="xiao6-ctx-state"><span class="xiao6-statedot warning"><span class="sd"></span></span><span>有一项操作需要你确认</span></div>');
    }
    body.innerHTML = html;
  }
  function ctxCard(t, body) { return '<div class="xiao6-ctx-card"><div class="ct">' + esc(t) + '</div>' + body + '</div>'; }
  function ctxItem(t) { return '<div class="xiao6-ctx-item"><span class="dot"></span><span>' + esc(t) + '</span></div>'; }

  // ───────────────────── Phase 8 · Trust Inspector（信任分析）─────────────────────
  function intentLabel(i) { return { casual_chat: '普通聊天', knowledge_query: '知识查询', execution_task: '执行任务', long_term_goal: '长期目标' }[i] || (i || '未知'); }
  function riskLabel(r) { return (r || 'SAFE'); }
  function decisionLabel(d) { return { auto: '自动执行', confirm: '等待确认', block: '拒绝执行', confirm_rejected: '拒绝执行', rejected: '拒绝执行' }[d] || (d || '—'); }
  function riskItem(risk) {
    var r = riskLabel(risk);
    var cls = r === 'SAFE' ? 'risk-safe' : (r === 'BLOCK' ? 'risk-block' : 'risk-confirm');
    return '<div class="xiao6-ctx-item"><span class="dot"></span><span>风险：</span><span class="risk-tag ' + cls + '">' + esc(r) + '</span></div>';
  }
  function trustCard(trust) {
    var t = trust || {};
    var html = '';
    if (!t.intent && !t.risk) {
      return ctxCard('信任分析', '<span class="xiao6-empty">暂无执行分析</span>');
    }
    if (t.intent) {
      var ip = t.intent;
      html += '<div class="xiao6-ctx-item"><span class="dot"></span><span>意图：' + esc(intentLabel(ip.intent)) + '</span></div>';
      if (ip.tools && ip.tools.length) html += '<div class="xiao6-ctx-item"><span class="dot"></span><span>计划：' + esc(ip.tools.join(' · ')) + '</span></div>';
      if (ip.risk) html += riskItem(ip.risk);
    }
    if (t.risk) {
      var rp = t.risk;
      html += '<div class="xiao6-ctx-item"><span class="dot"></span><span>工具：' + esc(rp.tool) + '</span></div>';
      html += riskItem(rp.risk);
      html += '<div class="xiao6-ctx-item"><span class="dot"></span><span>结果：' + esc(decisionLabel(rp.decision)) + '</span></div>';
    }
    return ctxCard('信任分析', html);
  }

  // ───────────────────── Phase 9-A · 记忆洞察（只读，不写记忆）─────────────────────
  function sourceLabel(et) {
    return { hotspot_event: '来自热点', note: '来自笔记', conversation: '来自对话', project: '来自项目上下文', memory: '来自长期记忆' }[et] || '来自长期记忆';
  }
  function relTimeShort(ts) {
    if (!ts) return '';
    var d = new Date(String(ts).replace(/-/g, '/'));
    if (isNaN(d.getTime())) return '';
    var diff = Date.now() - d.getTime(); if (diff < 0) diff = 0;
    var min = Math.floor(diff / 60000);
    if (min < 1) return '刚刚'; if (min < 60) return min + ' 分钟前';
    var hr = Math.floor(min / 60); if (hr < 24) return hr + ' 小时前';
    var day = Math.floor(hr / 24);
    return day < 2 ? '昨天' : (day < 7 ? day + ' 天前' : (d.getMonth() + 1) + '/' + d.getDate());
  }
  function memoryInsightCard() {
    var mems = state.snap.memories.slice(0, 3);
    if (!mems.length) {
      return ctxCard('记忆洞察', '<span class="xiao6-empty">暂无记忆 · 与小6对话后自动沉淀</span>');
    }
    var html = mems.map(function (m) {
      var title = String(m.title || m.content || '记忆').replace(/^Hotspot event:\s*/, '').slice(0, 50);
      var src = sourceLabel(m.event_type);
      var time = relTimeShort(m.ts);
      return '<div class="xiao6-mem-insight" data-goto="memory">' +
        '<div class="mi-t">' + esc(title) + '</div>' +
        '<div class="mi-s">' + esc(src) + (time ? ' · ' + esc(time) : '') + '</div>' +
        '</div>';
    }).join('');
    return ctxCard('记忆洞察', html);
  }

  // ───────────────────── Phase 9-B · 小6主动观察（仅展示后端已有数据，不伪造建议）─────────────────────
  function proactiveCard() {
    var items = [];
    var activeGoals = state.snap.goals.filter(function (g) { return String(g.status || '').toLowerCase() === 'active'; });
    if (activeGoals.length) items.push('◆ ' + activeGoals.length + ' 个目标进行中');
    var open = state.snap.tasks.filter(isOpen);
    if (open.length) items.push('✓ ' + open.length + ' 项任务待处理');
    var reminders = (state.snap.memory && state.snap.memory.reminders) || [];
    if (reminders.length) items.push('⏰ 提醒：' + reminders.slice(0, 2).map(function (r) { return r.content || r.due || ''; }).join(' · '));
    if (!items.length) {
      return ctxCard('小6主动观察', '<span class="xiao6-empty">暂无需要主动处理的事项</span>');
    }
    return ctxCard('小6主动观察', items.slice(0, 4).map(function (t) { return ctxItem(t); }).join(''));
  }

  // ───────────────────── /api/stream 事件处理（冻结事件名）─────────────────────
  // R1-B：所有事件一律写入 state.timeline（唯一真相源），不再写已废弃的 agentLog。
  // 并发安全：stream 通道的 tool_started/tool_finished 带 execution_id，按唯一 ID 关联，
  // 绝不用 tool name 做并发关联依据。
  function onStreamEvent(m) {
    var ev = m.xiao6_event || m.event;
    if (!ev) return;

    if (ev === 'AGENT_INTENT_ANALYZED') {
      // Phase 8 · Trust Layer：意图报告 → trust inspector + timeline 透明节点
      var ip = m.payload || {};
      if (ip.intent === 'casual_chat') return;  // 普通聊天：无信任分析，直接回复
      state.trust.intent = ip;
      if (window.Xiao6.timeline) window.Xiao6.timeline.addIntentNode(ip);
      state.notify();
      return;
    }
    if (ev === 'TOOL_RISK_CHECKED') {
      // Phase 8 · Trust Layer：风险检查 → trust inspector + timeline 透明节点
      var rp = m.payload || {};
      state.trust.risk = rp;
      if (window.Xiao6.timeline) window.Xiao6.timeline.addRiskNode(rp);
      state.notify();
      return;
    }
    if (ev === 'modal') {
      if (m.kind === 'agent_approval') window.Xiao6.approval.renderApprovalCard(m);
      return;
    }
    if (ev === 'tool_started') {
      // STREAM 通道：带 execution_id —— 经 upsertTool 与 chat 通道合并为同一真实节点（去重）
      window.Xiao6.timeline.upsertTool({
        executionId: m.execution_id || null,
        tool: m.task || m.tool || '工具',
        status: 'running',
        goalId: m.goal_id,
        summary: '正在执行',
        fromStream: true
      });
      state.notify();
      return;
    }
    if (ev === 'tool_finished') {
      // 必须按 execution_id 找到对应节点（禁止按 tool name 全局匹配）；与 chat 通道共用节点
      var fo = {
        executionId: m.execution_id || null,
        tool: m.task || m.tool || '工具',
        status: m.ok === false ? 'failed' : 'success',
        summary: m.ok === false ? '失败' : '完成',
        fromStream: true
      };
      if (m.result !== undefined) fo.output = m.result;
      window.Xiao6.timeline.upsertTool(fo);
      state.notify();
      return;
    }
    if (ev === 'execution_started' || ev === 'execution_completed' || ev === 'execution_cancelled') {
      var xstat = ev === 'execution_started' ? 'running' : (ev === 'execution_cancelled' ? 'stopped' : 'success');
      var xid = m.execution_id || m.task || ('exec:' + Date.now());
      state.upsertNode({
        id: 'exec:' + xid, type: 'execution', status: xstat,
        title: ev === 'execution_started' ? '执行开始' : (ev === 'execution_cancelled' ? '执行取消' : '执行完成'),
        summary: m.task || '', executionId: xid,
        timestamp: Date.now()
      });
      state.notify();
      return;
    }
    if (ev.indexOf('GOAL_') === 0 || ev.indexOf('TASK_') === 0 || ev.indexOf('INTENT_') === 0 || ev.indexOf('AGENT_') === 0) {
      var p = m.payload || {};
      var label = { GOAL_CREATED: '目标已创建', GOAL_PLANNED: '目标已规划', GOAL_STARTED: '目标已启动', GOAL_RUNNING: '目标执行中', GOAL_COMPLETED: '目标已完成', GOAL_FAILED: '目标失败', TASK_CREATED: '任务已创建', TASK_STARTED: '任务开始', TASK_RUNNING: '任务执行中', TASK_COMPLETED: '任务完成', TASK_FAILED: '任务失败', INTENT_CLASSIFIED: '意图已识别', INTENT_ACCEPTED: '意图已接受', INTENT_REJECTED: '意图已拒绝', INTENT_CONVERTED_TO_GOAL: '意图转为目标', AGENT_COMPLETED: 'Agent 完成', AGENT_FAILED: 'Agent 失败' }[ev] || ev;
      if (ev.indexOf('GOAL') === 0) {
        var gstatus = /COMPLETED/.test(ev) ? 'success' : (/FAILED/.test(ev) ? 'failed' : 'running');
        state.upsertNode({
          id: 'goal:' + p.goalId, type: 'goal', status: gstatus,
          goalId: p.goalId, title: p.title, summary: label,
          timestamp: Date.now()
        });
        if (p.goalId != null) state.runtime.currentGoalId = p.goalId;
      } else if (ev.indexOf('TASK') === 0) {
        var tstatus = /COMPLETED/.test(ev) ? 'success' : (/FAILED/.test(ev) ? 'failed' : 'running');
        state.upsertNode({
          id: 'task:' + p.taskId, type: 'task', status: tstatus,
          taskId: p.taskId, goalId: p.goalId, title: p.title, summary: label,
          timestamp: Date.now()
        });
        if (p.taskId != null) state.runtime.currentTaskId = p.taskId;
      } else {
        // INTENT_* / AGENT_*：透明节点（不重复造 Agent 活动）
        state.upsertNode({
          id: (ev.indexOf('AGENT') === 0 ? 'agent:' : 'intent2:') + (p.agentId || p.intentId || (ev + ':' + Date.now())),
          type: ev.indexOf('AGENT') === 0 ? 'execution' : 'intent',
          status: /REJECTED|FAILED/.test(ev) ? 'failed' : 'success',
          title: label, summary: p.title ? ('：' + p.title) : '',
          timestamp: Date.now()
        });
      }
      if (ev === 'GOAL_CREATED' || ev === 'GOAL_COMPLETED' || ev === 'GOAL_FAILED' || ev === 'TASK_COMPLETED' || ev === 'TASK_FAILED') window.Xiao6.main.toast(label);
      state.fetchSnapshot();
      state.notify();
    }
  }

  function init() {
    state.subscribe(function () {
      renderInspector();
    });
    // 分区切换
    var tabs = $('inspTabs');
    if (tabs) tabs.addEventListener('click', function (e) {
      var b = e.target.closest ? e.target.closest('.xiao6-insp-tab') : null;
      if (b) setInspTab(b.dataset.insp);
    });
    var ctxBody = $('ctxBody');
    if (ctxBody) ctxBody.addEventListener('click', function (e) {
      // 记忆洞察条目 / 「查看全部」→ 进入对应全量视图
      var more = e.target.closest ? e.target.closest('.xiao6-insp-more') : null;
      if (more && more.dataset.goto) { window.Xiao6.main.switchView(more.dataset.goto); return; }
      var t = e.target.closest ? e.target.closest('.xiao6-mem-insight') : null;
      if (t) window.Xiao6.main.switchView('memory');
    });
    setInspTab('overview');
  }

  var inspectorApi = {
    renderAgent: renderAgent,
    renderContext: renderContext,
    renderContextAuto: renderContextAuto,
    renderInspector: renderInspector,
    setInspTab: setInspTab,
    onStreamEvent: onStreamEvent,
    init: init
  };
  window.Xiao6.inspector = inspectorApi;
  // 兼容别名：历史调用点（timeline / 外部脚本）仍可按 agentPanel 取用
  window.Xiao6.agentPanel = inspectorApi;
})();
