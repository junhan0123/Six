// execution-panel.js — Phase 37.1 · Execution Transparency Layer (Execution Visibility)
//
// 定位：小6执行能力的「只读观察镜」。把已有的执行态从「用户不知道小6在做什么」
//      升级为「用户能看状态 / 步骤 / 风险 / 结果」。
//
// 数据来源（全部为既有 GET 端点，零新增 API / 零新增 SSE / 零修改 Runtime）：
//   GET /api/agent/state  → { enabled, state, current_goal, queue, running,
//                             last_report, consecutive_failures }
//   GET /api/tasks        → [{ id, title, steps[], current_step, total_steps,
//                             status, note:"...suggested_tool=<tool> args={}", created, updated }]
//   GET /api/hud/state    → { state, goal_id, progress }
//   GET /api/health       → { ok, tools[], self_check:{ checks:[{name,ok,detail}] } }
//
// 红线（ABSOLUTE）：
//   - 绝不 POST / 绝不调用任何 tools / 绝不改动 Agent Runtime / Planner / Executor / EventBus。
//   - 不新增路由 / 不新增 SSE kind / 不新增 EventBus 事件。
//   - 不暴露 CoT / 内部 prompt / secret / 原始敏感参数（透明 ≠ 暴露内部思维）。
//   - Task 4 确认 UX 仅「前端预填问句」：绝不自动发送 / 执行 / 确认 / 点击。
//   - 无数据则如实显示「暂无数据 / 当前无法获取执行状态」，绝不编造。
//
// 集成（Task 6）：PanelManager(REG 'execution') + OverlayManager.track('execution')
//                + body.execution-mode + command-palette + more 下拉 + window.ZZExecution

(function () {
  'use strict';

  var EXEC = {
    panel: null,
    open: false,
    timer: null,
    pollMs: 3000,            // 懒轮询：仅面板打开时运行，2–5s 一次
    data: { state: null, tasks: [], hud: null, health: null, loaded: false, failed: false },
  };

  // 高危工具（归纳自 /api/health.tools）→ 透明文案（动作 / 影响）。仅用于前端派生展示。
  var HIGH_RISK = {
    run_shell:        { label: '执行终端命令',     impact: '将在本机运行命令行，可能影响文件、系统或网络。' },
    file_delete:      { label: '删除文件',         impact: '将永久删除文件，删除后不可直接恢复。' },
    file_write:       { label: '写入文件',         impact: '将覆盖或创建文件内容，可能改动现有文件。' },
    file_rename:      { label: '重命名 / 移动文件', impact: '将移动或重命名文件，可能改变路径引用。' },
    install_software: { label: '安装软件',         impact: '将下载并安装软件，可能改动系统环境。' },
    kill_process:     { label: '结束进程',         impact: '将强制结束一个正在运行的进程，可能中断其工作。' },
    computer_action:  { label: '操控电脑界面',     impact: '将模拟鼠标 / 键盘操作你的界面，可能影响当前窗口。' },
  };

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function el(id) { return document.getElementById(id); }

  // 从 task.note 解析 suggested_tool 名（note 为真实字段，仅取工具名，绝不取 args/原始参数）。
  function parseSuggestedTool(note) {
    if (!note) return null;
    var m = String(note).match(/suggested_tool=([A-Za-z0-9_]+)/);
    return m ? m[1] : null;
  }

  // 状态 → 徽章（覆盖 IDLE / RUNNING / COMPLETED / FAILED，未知态 graceful fallback）
  function stateBadge(state) {
    switch (String(state || '').toUpperCase()) {
      case 'IDLE':       return { cls: 'idle', label: '空闲' };
      case 'RUNNING':    return { cls: 'running', label: '执行中' };
      case 'COMPLETED':  return { cls: 'done', label: '已完成' };
      case 'FAILED':     return { cls: 'failed', label: '执行失败' };
      default:           return { cls: 'unknown', label: '状态未知' };
    }
  }

  /* ───────────────────────── 构建 DOM ───────────────────────── */
  function build() {
    if (EXEC.panel) return;
    var html = [
      '<div class="execv-panel" id="execv-panel" role="dialog" aria-label="执行状态">',
      '  <div class="execv-backdrop" data-close="1"></div>',
      '  <div class="execv-stage glass">',
      '    <div class="execv-bar">',
      '      <div class="execv-title"><span class="execv-dot"></span>执行状态 · 小6实况</div>',
      '      <div class="execv-meta" id="execv-meta"></div>',
      '      <button class="execv-refresh" id="execv-refresh" title="重新加载" aria-label="重新加载">↻</button>',
      '      <button class="execv-close" id="execv-close" title="关闭（Esc）" aria-label="关闭"><svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-close"/></svg></button>',
      '    </div>',
      '    <div class="execv-body" id="execv-body"></div>',
      '  </div>',
      '</div>',
    ].join('\n');
    document.body.insertAdjacentHTML('beforeend', html);
    EXEC.panel = el('execv-panel');
    el('execv-close').addEventListener('click', exClose);
    EXEC.panel.querySelector('[data-close]').addEventListener('click', exClose);
    el('execv-refresh').addEventListener('click', function () { exLoad(true); });
    EXEC.panel.addEventListener('click', function (e) {
      var t = e.target.closest('[data-exec-toggle]');
      if (t) {
        var card = t.closest('[data-exec-detail]');
        if (card) card.classList.toggle('is-open');
      }
    });
  }

  /* ───────────────────────── 数据加载（仅 GET） ───────────────────────── */
  function getJSON(url) {
    return fetch(url, { cache: 'no-store' }).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    });
  }

  function exLoad(force) {
    var body = el('execv-body');
    if (body && !EXEC.data.loaded && !force) body.innerHTML = '<div class="execv-loading">正在读取执行状态…</div>';
    Promise.all([
      getJSON('/api/agent/state').catch(function () { return null; }),
      getJSON('/api/tasks').catch(function () { return null; }),
      getJSON('/api/hud/state').catch(function () { return null; }),
      getJSON('/api/health').catch(function () { return null; }),
    ]).then(function (res) {
      EXEC.data.state = res[0];
      EXEC.data.tasks = Array.isArray(res[1]) ? res[1] : [];
      EXEC.data.hud = res[2];
      EXEC.data.health = res[3];
      EXEC.data.loaded = true;
      EXEC.data.failed = !(res[0] || res[1] || res[2] || res[3]);
      render();
    }).catch(function () {
      EXEC.data.failed = true;
      EXEC.data.loaded = true;
      render();
    });
  }

  /* ───────────────────────── 渲染 ───────────────────────── */
  function render() {
    var body = el('execv-body');
    if (!body) return;
    var d = EXEC.data;

    if (d.failed && !d.loaded) {
      body.innerHTML = '<div class="execv-empty">当前无法获取执行状态，请稍后重试。</div>';
      return;
    }

    var st = d.state || {};
    var tasks = d.tasks || [];
    var hud = d.hud || {};
    var health = d.health || {};

    var parts = [];

    // ── Task 1：执行状态表面 ──
    parts.push(renderStatus(st, hud, health, tasks));

    // ── Task 2 + Task 3：进度 / 细节（进行中任务） ──
    var activeTasks = tasks.filter(function (t) { return t && (t.status === 'open' || t.status === 'running' || t.status === 'in_progress'); });
    if (activeTasks.length) {
      parts.push('<div class="execv-section-title">进行中任务</div>');
      activeTasks.forEach(function (t) { parts.push(renderTaskCard(t, health)); });
    }

    // ── Task 4：高风险动作确认（前端派生，仅预填） ──
    var riskCard = renderHighRisk(activeTasks);
    if (riskCard) parts.push(riskCard);

    // ── Task 5：执行历史 ──
    parts.push(renderHistory(tasks));

    body.innerHTML = parts.join('');
    bindRiskButtons(body);
  }

  function renderStatus(st, hud, health, tasks) {
    var badge = stateBadge(st.state);
    var goal = st.current_goal || (hud && hud.goal_id ? ('目标 #' + hud.goal_id) : '') ||
               (tasks.length ? tasks[0].title : '');
    var running = st.running === true;
    var fails = Number(st.consecutive_failures || 0);
    var queueLen = Array.isArray(st.queue) ? st.queue.length : 0;

    var lines = [];
    lines.push('<div class="execv-row"><span class="execv-k">当前意图</span><span class="execv-v">' +
      (goal ? esc(goal) : '空闲') + '</span></div>');
    lines.push('<div class="execv-row"><span class="execv-k">运行状态</span><span class="execv-v">' +
      (running ? '运行中' : '未运行') + '</span></div>');
    if (queueLen > 0) lines.push('<div class="execv-row"><span class="execv-k">待处理队列</span><span class="execv-v">' + queueLen + ' 项</span></div>');
    if (fails > 0) lines.push('<div class="execv-row execv-row-warn"><span class="execv-k">连续失败</span><span class="execv-v">' + fails + ' 次</span></div>');
    if (st.last_report) lines.push('<div class="execv-row"><span class="execv-k">最近报告</span><span class="execv-v execv-report">' + esc(st.last_report) + '</span></div>');

    // 系统健康（来自 /api/health）
    var healthWarn = '';
    if (health && health.ok === false) {
      var bad = (health.self_check && Array.isArray(health.self_check.checks))
        ? health.self_check.checks.filter(function (c) { return !c.ok; }) : [];
      var detail = bad.length
        ? bad.map(function (c) { return esc(c.name) + '：' + esc(c.detail || ''); }).join('；')
        : '系统自检未通过';
      healthWarn = '<div class="execv-risk"><span class="execv-risk-ico">⚠</span><div><b>系统风险</b><br>' + detail + '</div></div>';
    }

    var meta = el('execv-meta');
    if (meta) {
      meta.textContent = (st.state ? ('' + st.state) : '') + (running ? ' · 运行' : '');
    }

    return '' +
      '<div class="execv-status execv-status-' + badge.cls + '">' +
        '<span class="execv-badge ' + badge.cls + '"><span class="dot"></span>' + esc(badge.label) + '</span>' +
        '<div class="execv-status-main">' +
          (lines.join('')) +
        '</div>' +
      '</div>' +
      healthWarn;
  }

  function renderTaskCard(t, health) {
    var steps = Array.isArray(t.steps) ? t.steps : [];
    var cur = Number(t.current_step || 0);
    var total = Number(t.total_steps || steps.length || 0);
    var suggested = parseSuggestedTool(t.note);

    // Task 2：进度（真实步骤，不编造百分比）
    var stepHtml = '';
    if (steps.length) {
      stepHtml = '<div class="execv-steps">' + steps.map(function (s, i) {
        var cls = i < cur ? 'is-done' : (i === cur ? 'is-current' : '');
        return '<div class="execv-step ' + cls + '"><span class="execv-step-no">' + (i + 1) + '</span><span>' + esc(s) + '</span></div>';
      }).join('') + '</div>';
    } else {
      stepHtml = '<div class="execv-sub">该任务尚未登记子步骤</div>';
    }

    var metaLine = total > 0
      ? ('步骤 ' + Math.min(cur + 1, total) + ' / ' + total)
      : (suggested ? ('建议工具：' + esc(suggested)) : '');

    // Task 3：细节（默认折叠，低打扰）
    var detailRows = [];
    detailRows.push('<div class="execv-row"><span class="execv-k">任务</span><span class="execv-v">' + esc(t.title || ('任务 #' + t.id)) + '</span></div>');
    if (t.step) detailRows.push('<div class="execv-row"><span class="execv-k">当前步骤</span><span class="execv-v">' + esc(t.step) + '</span></div>');
    if (suggested) detailRows.push('<div class="execv-row"><span class="execv-k">建议工具</span><span class="execv-v">' + esc(suggested) + '</span></div>');
    if (t.created) detailRows.push('<div class="execv-row"><span class="execv-k">创建于</span><span class="execv-v">' + esc(t.created) + '</span></div>');
    if (t.updated) detailRows.push('<div class="execv-row"><span class="execv-k">更新于</span><span class="execv-v">' + esc(t.updated) + '</span></div>');

    return '' +
      '<div class="execv-task" data-exec-detail>' +
        '<button class="execv-task-head" type="button" data-exec-toggle>' +
          '<span class="execv-task-title">' + esc(t.title || ('任务 #' + t.id)) + '</span>' +
          '<span class="execv-task-meta">' + esc(metaLine) + '</span>' +
          '<span class="execv-caret">▶</span>' +
        '</button>' +
        '<div class="execv-task-detail">' +
          stepHtml +
          '<div class="execv-detail-rows">' + detailRows.join('') + '</div>' +
        '</div>' +
      '</div>';
  }

  // Task 4：高风险动作确认（前端派生自真实 suggested_tool，仅预填问句，绝不自动执行）
  function renderHighRisk(activeTasks) {
    var hit = null;
    for (var i = 0; i < activeTasks.length; i++) {
      var tool = parseSuggestedTool(activeTasks[i].note);
      if (tool && HIGH_RISK[tool]) { hit = { tool: tool, task: activeTasks[i] }; break; }
    }
    if (!hit) return '';
    var info = HIGH_RISK[hit.tool];
    return '' +
      '<div class="execv-confirm">' +
        '<div class="execv-confirm-title"><span class="execv-risk-ico">⚠</span>即将执行高风险动作</div>' +
        '<div class="execv-confirm-body">' +
          '<div class="execv-confirm-row"><span class="execv-k">动作</span><span class="execv-v"><b>' + esc(info.label) + '</b>（' + esc(hit.tool) + '）</span></div>' +
          '<div class="execv-confirm-row"><span class="execv-k">影响</span><span class="execv-v">' + esc(info.impact) + '</span></div>' +
          '<div class="execv-confirm-row"><span class="execv-k">来源</span><span class="execv-v">来自目标拆解任务「' + esc(hit.task.title || ('#'+hit.task.id)) + '」</span></div>' +
        '</div>' +
        '<div class="execv-confirm-note">小6不会自行执行。你可继续询问，或请它先说明步骤再等你确认。</div>' +
        '<div class="execv-confirm-actions">' +
          '<button class="execv-confirm-ask" data-exec-ask="' + esc(info.label) + '" data-exec-tool="' + esc(hit.tool) + '">继续询问小6</button>' +
          '<button class="execv-confirm-cancel" data-exec-cancel="' + esc(info.label) + '" data-exec-tool="' + esc(hit.tool) + '">取消</button>' +
        '</div>' +
      '</div>';
  }

  function bindRiskButtons(body) {
    body.querySelectorAll('[data-exec-ask]').forEach(function (b) {
      b.addEventListener('click', function () {
        prefill('小6，你下一步要执行「' + b.getAttribute('data-exec-tool') + '」，请先说明具体步骤、原因和影响，等我确认后再继续。');
      });
    });
    body.querySelectorAll('[data-exec-cancel]').forEach(function (b) {
      b.addEventListener('click', function () {
        prefill('取消这次「' + b.getAttribute('data-exec-tool') + '」操作，先不动手。');
      });
    });
  }

  // Task 5：执行历史（仅用 /api/tasks 真实数据；不编造跨会话历史）
  function renderHistory(tasks) {
    if (!tasks.length) {
      return '<div class="execv-section-title">执行历史</div><div class="execv-empty">暂无可用执行记录。</div>';
    }
    var sorted = tasks.slice().sort(function (a, b) {
      return String(b.updated || '').localeCompare(String(a.updated || ''));
    });
    var items = sorted.map(function (t) {
      var st = (t.status === 'completed' || t.status === 'done') ? 'is-done'
        : (t.status === 'failed' || t.status === 'error') ? 'is-failed' : 'is-open';
      var suggested = parseSuggestedTool(t.note);
      return '<div class="execv-hist-item ' + st + '">' +
        '<div class="execv-hist-main">' + esc(t.title || ('任务 #' + t.id)) + '</div>' +
        '<div class="execv-hist-meta">' + esc(t.status || 'open') +
          (suggested ? ' · ' + esc(suggested) : '') +
          (t.updated ? ' · ' + esc(t.updated) : '') + '</div>' +
        '</div>';
    }).join('');
    return '<div class="execv-section-title">执行历史</div><div class="execv-hist">' + items + '</div>';
  }

  /* ───────────────────────── Task 4：仅预填，绝不发送 ───────────────────────── */
  // 复用 root 应用主输入逻辑（#input / #osDockInput；chat-mode 优先 #input）。
  function prefill(text) {
    var inChat = document.body.classList.contains('chat-mode');
    var chatEl = el('input');
    var dockEl = el('osDockInput');
    var target = inChat ? (chatEl || dockEl) : (dockEl || chatEl);
    if (!target) {
      exToast('未找到对话输入框，请手动输入你的确认。');
      return;
    }
    target.focus();
    target.value = text;           // 仅预填真实问句，绝不 .submit() / 模拟点击发送
    exToast('已为你填入对话，请确认后发送。');
  }

  function exToast(msg) {
    var t = el('execv-toast');
    if (!t) {
      t = document.createElement('div');
      t.id = 'execv-toast';
      t.className = 'execv-toast';
      document.body.appendChild(t);
    }
    t.textContent = msg;
    t.classList.add('show');
    clearTimeout(t._t);
    t._t = setTimeout(function () { t.classList.remove('show'); }, 2600);
  }

  /* ───────────────────────── 轮询（懒：仅打开时） ───────────────────────── */
  function startPoll() {
    stopPoll();
    EXEC.timer = setInterval(function () {
      if (!EXEC.open) return;
      if (document.visibilityState === 'hidden') return;   // 页面不可见时停轮询
      exLoad();
    }, EXEC.pollMs);
  }
  function stopPoll() {
    if (EXEC.timer) { clearInterval(EXEC.timer); EXEC.timer = null; }
  }

  /* ───────────────────────── 打开 / 关闭 ───────────────────────── */
  function exOpen() {
    build();
    exLoad();
    requestAnimationFrame(function () { document.body.classList.add('execution-mode'); });
    EXEC.open = true;
    if (window.OverlayManager) {
      var type = (window.OverlayManager.OverlayType) ? window.OverlayManager.OverlayType.PANEL : 'panel';
      window.OverlayManager.track('execution', {
        el: EXEC.panel, onClose: exCloseImpl, type: type, trap: false,
      });
    }
    startPoll();
  }
  function exCloseImpl() {
    document.body.classList.remove('execution-mode');
    EXEC.open = false;
    stopPoll();
  }
  function exClose() {
    if (window.OverlayManager && window.OverlayManager.isOpen && window.OverlayManager.isOpen('execution')) {
      window.OverlayManager.close('execution');
    } else {
      exCloseImpl();
    }
  }

  // 页面不可见时停轮询（省开销，不影响主对话）
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') stopPoll();
    else if (EXEC.open) startPoll();
  });

  window.ZZExecution = { open: exOpen, close: exClose, isOpen: function () { return EXEC.open; } };
})();
