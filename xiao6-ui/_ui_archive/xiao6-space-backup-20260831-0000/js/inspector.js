/* ═════════════════════════════════════════════════════════════════
   Xiao6 UI-R2 · inspector.js — Drawer 检视器 + Stream 事件处理
   R2 重构：Inspector 从固定右栏改为可滑入 Drawer
   默认隐藏，执行中有工具/审批时才打开
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
  function fmtTime(ts) {
    var d = ts ? new Date(String(ts).replace(/-/g, '/')) : new Date();
    if (isNaN(d.getTime())) d = new Date();
    var p = function (n) { return n < 10 ? '0' + n : '' + n; };
    return p(d.getHours()) + ':' + p(d.getMinutes());
  }

  function isOpen(t) {
    var s = String(t.status || '').toLowerCase();
    return s !== 'done' && s !== 'completed' && s !== 'closed';
  }

  // ───────────────────── Drawer 渲染 ─────────────────────
  function renderDrawer() {
    var body = $('drawerBody'); if (!body) return;
    var st = String(state.snap.agent.state || 'IDLE').toUpperCase();
    var h = state.snap.health || {};
    var curAction = state.derive.currentAction();
    var curGoal = state.derive.currentGoal();
    var pending = state.derive.pendingApprovals();
    var activeTools = state.derive.activeTools();
    var lastResult = state.timeline.filter(function (n) { return n.type === 'result'; }).pop();
    var lastFailed = state.derive.lastFailed();

    var html = '';

    // Agent 状态
    var stateCls = st === 'EXECUTING' || st === 'THINKING' || st === 'LISTENING' || st === 'PLANNING' ? 'ongoing'
      : st === 'ERROR' ? 'error' : 'done';
    html += drawerCard('状态',
      '<div class="x6-ctx-state"><span class="x6-statedot ' + stateCls + '"><span class="sd"></span></span><span>' + esc(state.CORE_TEXT[st] || '在线待命') + '</span></div>'
    );

    // 当前动作
    if (curAction) {
      var actionLabel = curAction.kind === 'tool' ? '正在执行：' + esc(curAction.label)
        : curAction.kind === 'task' ? '正在分析：' + esc(curAction.label)
        : '正在规划：' + esc(curAction.label);
      html += drawerCard('当前动作', '<div class="x6-ctx-item"><span class="dot"></span><span>' + esc(actionLabel) + '</span></div>');
    }

    // 当前目标
    if (curGoal) {
      var prog = Number(curGoal.progress || 0);
      html += drawerCard('当前目标',
        '<div class="x6-ctx-item"><span class="dot"></span><span>' + esc(curGoal.title || ('目标 #' + curGoal.id)) + '</span></div>' +
        '<div class="x6-prog"><i style="width:' + Math.max(0, Math.min(100, prog)) + '%"></i></div>' +
        '<div style="font-size:11px;color:var(--x6-text-faint);margin-top:3px">进度 ' + prog + '%</div>'
      );
    }

    // 活跃工具
    if (activeTools.length) {
      html += drawerCard('工具',
        activeTools.map(function (t) {
          return '<div class="x6-ctx-item"><span class="dot"></span><span>' + esc(t.tool) + '</span></div>';
        }).join('')
      );
    }

    // 待确认审批
    if (pending.length) {
      html += drawerCard('待确认',
        '<div class="x6-ctx-state"><span class="x6-statedot warning"><span class="sd"></span></span><span>' +
        pending.length + ' 项操作等待确认</span></div>'
      );
    }

    // 最新结果
    if (lastResult) {
      var isFail = lastResult.status === 'failed';
      html += drawerCard(isFail ? '执行失败' : '结果',
        '<div class="x6-tool-summary">' + (isFail ? '! 任务失败' : '✓ 任务完成') + '</div>' +
        (lastResult.title ? '<div class="x6-tl-meta">' + esc(lastResult.title) + '</div>' : '') +
        (lastResult.summary ? '<div class="x6-tl-meta">' + esc(lastResult.summary) + '</div>' : '')
      );
    }

    // 最近错误
    if (lastFailed && !lastResult) {
      html += drawerCard('错误',
        '<div class="x6-tl-errcard"><div class="x6-tool-summary"><b>' + esc(lastFailed.title || '执行失败') + '</b></div>' +
        (lastFailed.summary ? '<div class="x6-tl-err">' + esc(lastFailed.summary) + '</div>' : '') +
        '</div>'
      );
    }

    // 模型信息
    html += drawerCard('模型',
      '<div class="x6-ctx-item"><span class="dot"></span><span>' + esc(h.model || '—') + ' · ' + esc(h.provider || '—') + '</span></div>'
    );

    body.innerHTML = html;
  }

  function drawerCard(title, body) {
    return '<div class="x6-ctx-card"><div class="ct">' + esc(title) + '</div>' + body + '</div>';
  }

  // ───────────────────── /api/stream 事件处理 ─────────────────────
  function onStreamEvent(m) {
    var ev = m.xiao6_event || m.event;
    if (!ev) return;

    if (ev === 'AGENT_INTENT_ANALYZED') {
      var ip = m.payload || {};
      if (ip.intent === 'casual_chat') return;
      state.trust.intent = ip;
      if (window.Xiao6.timeline) window.Xiao6.timeline.addIntentNode(ip);
      state.notify();
      return;
    }
    if (ev === 'TOOL_RISK_CHECKED') {
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
    if (ev === 'AGENT_COMPLETED' || ev === 'AGENT_FAILED') {
      var p = m.payload || {};
      var rstatus = /COMPLETED/.test(ev) ? 'success' : 'failed';
      var rid = 'result:' + (p.agentId || Date.now());
      state.upsertNode({
        id: rid, type: 'result', status: rstatus,
        title: p.title || '',
        summary: p.summary || '',
        detail: p.result || '',
        timestamp: Date.now()
      });
      state.setState('COMPLETED');
      state.notify();
      return;
    }
    if (ev.indexOf('GOAL_') === 0 || ev.indexOf('TASK_') === 0 || ev.indexOf('INTENT_') === 0 || ev.indexOf('AGENT_') === 0) {
      var p = m.payload || {};
      var label = {
        GOAL_CREATED: '目标已创建', GOAL_PLANNED: '目标已规划', GOAL_STARTED: '目标已启动',
        GOAL_RUNNING: '目标执行中', GOAL_COMPLETED: '目标已完成', GOAL_FAILED: '目标失败',
        TASK_CREATED: '任务已创建', TASK_STARTED: '任务开始', TASK_RUNNING: '任务执行中',
        TASK_COMPLETED: '任务完成', TASK_FAILED: '任务失败',
        INTENT_CLASSIFIED: '意图已识别', INTENT_ACCEPTED: '意图已接受',
        INTENT_REJECTED: '意图已拒绝', INTENT_CONVERTED_TO_GOAL: '意图转为目标',
        AGENT_COMPLETED: 'Agent 完成', AGENT_FAILED: 'Agent 失败'
      }[ev] || ev;
      if (ev.indexOf('GOAL') === 0) {
        var gstatus = /COMPLETED/.test(ev) ? 'success' : (/FAILED/.test(ev) ? 'failed' : 'running');
        state.upsertNode({
          id: 'goal:' + p.goalId, type: 'goal', status: gstatus,
          goalId: p.goalId, title: p.title, summary: label, timestamp: Date.now()
        });
        if (p.goalId != null) state.runtime.currentGoalId = p.goalId;
      } else if (ev.indexOf('TASK') === 0) {
        var tstatus = /COMPLETED/.test(ev) ? 'success' : (/FAILED/.test(ev) ? 'failed' : 'running');
        state.upsertNode({
          id: 'task:' + p.taskId, type: 'task', status: tstatus,
          taskId: p.taskId, goalId: p.goalId, title: p.title, summary: label, timestamp: Date.now()
        });
        if (p.taskId != null) state.runtime.currentTaskId = p.taskId;
      } else {
        state.upsertNode({
          id: (ev.indexOf('AGENT') === 0 ? 'agent:' : 'intent2:') + (p.agentId || p.intentId || (ev + ':' + Date.now())),
          type: ev.indexOf('AGENT') === 0 ? 'execution' : 'intent',
          status: /REJECTED|FAILED/.test(ev) ? 'failed' : 'success',
          title: label, summary: p.title ? ('：' + p.title) : '', timestamp: Date.now()
        });
      }
      if (ev === 'GOAL_CREATED' || ev === 'GOAL_COMPLETED' || ev === 'GOAL_FAILED' ||
          ev === 'TASK_COMPLETED' || ev === 'TASK_FAILED') {
        window.Xiao6.main.toast(label);
      }
      state.fetchSnapshot();
      state.notify();
    }
  }

  function init() {
    state.subscribe(function () {
      // 自动打开 drawer：有运行中工具或待确认审批时
      var activeTools = state.derive.activeTools();
      var pending = state.derive.pendingApprovals();
      if (activeTools.length || pending.length) {
        renderDrawer();
      }
    });
  }

  window.Xiao6.inspector = {
    renderDrawer: renderDrawer,
    onStreamEvent: onStreamEvent,
    init: init
  };
})();
