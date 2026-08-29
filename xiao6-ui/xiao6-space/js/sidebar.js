/* ═════════════════════════════════════════════════════════════════
   Xiao6 UI-R1 · sidebar.js — 列表视图渲染（Phase 2）
   迁移自 x6-workspace.js：Goals/Tasks/Memory/Knowledge/Capabilities/
   Settings 渲染 + openGoalForm/openIntentForm + row/isOpen/isDone/asList
   兼容裸数组：/api/goals、/api/tasks、/api/memories 均返回数组
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
  function relTime(ts) { if (!ts) return ''; var d = new Date(String(ts).replace(/-/g, '/')); if (isNaN(d.getTime())) return ''; var diff = Date.now() - d.getTime(); if (diff < 0) diff = 0; var min = Math.floor(diff / 60000); if (min < 1) return '刚刚'; if (min < 60) return min + ' 分钟前'; var hr = Math.floor(min / 60); if (hr < 24) return hr + ' 小时前'; var day = Math.floor(hr / 24); return day < 2 ? '昨天' : (day < 7 ? day + ' 天前' : (d.getMonth() + 1) + '/' + d.getDate()); }
  function asList(v, key) { if (Array.isArray(v)) return v; if (v && Array.isArray(v[key])) return v[key]; return []; }

  function isOpen(t) { var s = String(t.status || '').toLowerCase(); return s !== 'done' && s !== 'completed' && s !== 'closed'; }
  function isDone(t) { var s = String(t.status || '').toLowerCase(); return s === 'done' || s === 'completed' || s === 'closed'; }

  function row(ic, t, s, tagCls, tagTxt) {
    return '<div class="x6-row"><div class="ic">' + esc(ic) + '</div><div class="body"><div class="t">' + esc(t) + '</div>' + (s ? '<div class="s">' + esc(s) + '</div>' : '') + '</div>' + (tagTxt ? '<span class="tag ' + (tagCls || '') + '">' + esc(tagTxt) + '</span>' : '') + '</div>';
  }

  // ───────────────────── 列表渲染 ─────────────────────
  function renderTasks() {
    var list = $('tasksList'); if (!list) return;
    var tasks = state.snap.tasks.slice().sort(function (a, b) { return Number(a.id) - Number(b.id); });
    list.innerHTML = tasks.length ? tasks.map(function (t) {
      var open = isOpen(t);
      return row('✓', t.title || ('任务 #' + t.id), (t.status || '') + (t.updated ? ' · ' + relTime(t.updated) : ''), open ? 'run' : 'done', open ? '进行中' : '已完成');
    }).join('') : '<span class="x6-empty">暂无任务</span>';
  }
  function renderProjects() {
    var list = $('projectsList'); if (!list) return;
    var goals = state.snap.goals.slice().sort(function (a, b) { return String(b.updated || '').localeCompare(String(a.updated || '')); });
    list.innerHTML = goals.length ? goals.map(function (g) {
      var s = String(g.status || ''); var prog = Number(g.progress || 0);
      return row('◆', g.title || ('目标 #' + g.id), s + ' · 进度 ' + prog + '%', s === 'active' ? 'run' : 'done', s);
    }).join('') : '<span class="x6-empty">暂无项目/目标</span>';
  }
  function renderMemory() {
    var list = $('memoryList'); if (!list) return;
    var mems = state.snap.memories.slice().sort(function (a, b) { return Number(b.id) - Number(a.id); });
    list.innerHTML = mems.length ? mems.map(function (m) {
      var title = String(m.title || m.content || '记忆').replace(/^Hotspot event:\s*/, '').slice(0, 80);
      return row('◷', title, (m.event_type || 'memory') + (m.ts ? ' · ' + relTime(m.ts) : ''), '', '');
    }).join('') : '<span class="x6-empty">暂无记忆 · 与小6对话后自动沉淀</span>';
  }
  function renderKnowledge() {
    var list = $('knowledgeList'); if (!list) return;
    var docs = asList(state.snap.knowledge, 'docs');
    list.innerHTML = docs.length ? docs.map(function (d) {
      return row('▤', d.title || '文档', (d.domain || '其他') + (d.tags && d.tags.length ? ' · ' + d.tags.join(',') : ''), '', '');
    }).join('') : '<span class="x6-empty">知识库为空</span>';
  }
  function renderCapabilities() {
    var list = $('capabilitiesList'); if (!list) return;
    var caps = state.snap.capabilities;
    list.innerHTML = caps.length ? caps.map(function (c) {
      return row(c.icon || '⚡', c.label || c.id, c.description || (c.group || ''), c.active ? 'done' : 'run', c.active ? '激活' : '待命');
    }).join('') : '<span class="x6-empty">暂无能力数据</span>';
  }
  function renderTools() {
    var list = $('toolsList'); if (!list) return;
    var tools = (state.snap.health && state.snap.health.tools) || [];
    list.innerHTML = tools.length ? tools.map(function (t) {
      return row('⚙', t, '工具', '', '');
    }).join('') : '<span class="x6-empty">暂无工具数据</span>';
  }

  // ───────────────────── 历史（GET /api/chat/history，只读真实会话记录）─────────────────────
  function renderHistory() {
    var list = $('historyList'); if (!list) return;
    list.innerHTML = '<span class="x6-empty">读取中…</span>';
    window.Xiao6.api.getJSON('/api/chat/history?limit=60').then(function (d) {
      var sessions = (d && d.sessions) || [];
      if (!sessions.length) { list.innerHTML = '<span class="x6-empty">暂无会话记录</span>'; return; }
      // 会话按最近一轮时间倒序（后端返回顺序不保证，前端按 turns 末尾 ts 排序）
      sessions.sort(function (a, b) {
        var ta = (a.turns && a.turns.length ? a.turns[a.turns.length - 1].ts : '') || '';
        var tb = (b.turns && b.turns.length ? b.turns[b.turns.length - 1].ts : '') || '';
        return String(tb).localeCompare(String(ta));
      });
      list.innerHTML = sessions.slice(0, 30).map(function (s) {
        var turns = s.turns || [];
        var first = '';
        for (var i = 0; i < turns.length; i++) { if (turns[i].role === 'user') { first = turns[i].content || ''; break; } }
        var last = turns.length ? turns[turns.length - 1].ts : '';
        return row('◷', first.slice(0, 60) || '（无用户输入）',
          turns.length + ' 条消息 · ' + (relTime(last) || last), '', '');
      }).join('');
    });
  }

  // ───────────────────── 当前项目（活跃目标 + 其任务，真实数据）─────────────────────
  // 任务归属：解析 task.note 中后端写入的「来自目标 #N 拆解」。
  // 匹配不到即视为无归属，绝不按标题相似度猜。
  function goalTasks(goalId) {
    var re = new RegExp('来自目标\\s*#' + Number(goalId) + '\\b');
    return state.snap.tasks.filter(function (t) { return re.test(String(t.note || '')); });
  }
  function renderCurrent() {
    var body = $('currentBody'); if (!body) return;
    var active = state.snap.goals.filter(function (g) { return String(g.status || '').toLowerCase() === 'active'; });
    if (!active.length) {
      body.innerHTML = '<span class="x6-empty">当前没有活跃的目标 · 让小6帮你推进一件事</span>';
      return;
    }
    body.innerHTML = active.map(function (g) {
      var prog = Number(g.progress || 0);
      // /api/tasks 不下发 goal_id（API 契约冻结，不改后端）；改用后端真实写入的
      // note 元数据「来自目标 #N 拆解」做归属，无法归属的任务不硬塞进任何目标。
      var gt = goalTasks(g.id);
      var done = gt.filter(isDone).length;
      var html = '<div class="x6-cur-card">' +
        '<div class="x6-cur-title">◆ #' + g.id + ' ' + esc(g.title || ('目标 #' + g.id)) + '</div>' +
        '<div class="x6-cur-meta">' + esc(g.status || '') + ' · 进度 ' + prog + '%' +
          (g.horizon ? ' · ' + esc(g.horizon) : '') + (g.due_date ? ' · 截止 ' + esc(g.due_date) : '') +
          (gt.length ? ' · 任务 ' + done + '/' + gt.length : '') + '</div>' +
        '<div class="x6-prog"><i style="width:' + Math.max(0, Math.min(100, prog)) + '%"></i></div>';
      if (g.description) html += '<div class="x6-cur-meta" style="margin-top:10px">' + esc(g.description) + '</div>';
      if (gt.length) {
        html += '<div class="x6-list" style="margin-top:12px">' + gt.map(function (t) {
          return row(isOpen(t) ? '◌' : '✓', t.title || ('任务 #' + t.id),
            (t.total_steps ? '步骤 ' + (t.current_step || 0) + '/' + t.total_steps + ' · ' : '') + (t.status || ''),
            isOpen(t) ? 'run' : 'done', isOpen(t) ? '进行中' : '已完成');
        }).join('') + '</div>';
      }
      return html + '</div>';
    }).join('');

    // 未归属到任何活跃目标、但仍在进行中的任务（如实列出，不归入任何目标）
    var linked = {};
    active.forEach(function (g) { goalTasks(g.id).forEach(function (t) { linked[t.id] = 1; }); });
    var loose = state.snap.tasks.filter(function (t) { return isOpen(t) && !linked[t.id]; });
    if (loose.length) {
      body.innerHTML += '<div class="x6-cur-card"><div class="x6-cur-title">进行中的任务</div>' +
        '<div class="x6-cur-meta">未关联到当前活跃目标 · 共 ' + loose.length + ' 项</div>' +
        '<div class="x6-list" style="margin-top:12px">' + loose.slice(0, 12).map(function (t) {
          return row('◌', t.title || ('任务 #' + t.id),
            (t.total_steps ? '步骤 ' + (t.current_step || 0) + '/' + t.total_steps + ' · ' : '') + (t.status || ''),
            'run', '进行中');
        }).join('') + '</div></div>';
    }
  }

  // ───────────────────── SETTINGS ─────────────────────
  function renderSettings() {
    var body = $('settingsBody'); if (!body) return;
    var h = state.snap.health || {}, a = state.snap.agent || {};
    var html = '';
    html += '<div class="x6-set-group"><h3>功能偏好</h3>' +
      setRow('web', '联网搜索', '默认开启，搜索时自动联网', state.toolModes.web) +
      setRow('think', '深度思考', '回复前先进行深度推理', state.toolModes.think) +
      setRow('speak', '语音播报', '回复完成后自动朗读', state.autoSpeak) + '</div>';
    html += '<div class="x6-set-group"><h3>系统概览</h3>' +
      kvRow('目标 / 任务', state.snap.goals.length + ' / ' + state.snap.tasks.filter(isOpen).length) +
      kvRow('记忆 / 知识', (state.snap.memories || []).length + ' / ' + asList(state.snap.knowledge, 'docs').length) +
      kvRow('能力登记', (state.snap.capabilities || []).length + ' 项') +
      kvRow('模型', h.model || '—') +
      kvRow('提供方', h.provider || '—') +
      kvRow('TTS 引擎', h.tts_backend || '—') + '</div>';
    body.innerHTML = html;
    Array.prototype.forEach.call(body.querySelectorAll('.x6-switch'), function (sw) {
      sw.addEventListener('click', function () {
        sw.classList.toggle('on');
        var k = sw.dataset.key;
        if (k === 'web') state.toolModes.web = sw.classList.contains('on');
        else if (k === 'think') state.toolModes.think = sw.classList.contains('on');
        else if (k === 'speak') { state.autoSpeak = sw.classList.contains('on'); state.lsSet('xiao6_autoSpeak', state.autoSpeak ? '1' : '0'); }
      });
    });
  }
  function setRow(key, label, desc, on) { return '<div class="x6-set-row"><span class="k">' + esc(label) + '<small>' + esc(desc) + '</small></span><span class="x6-switch ' + (on ? 'on' : '') + '" data-key="' + key + '"></span></div>'; }
  function kvRow(k, v) { return '<div class="x6-set-row"><span class="k">' + esc(k) + '</span><span class="v">' + esc(v) + '</span></div>'; }

  // ───────────────────── 表单（新建目标 / 意图识别）─────────────────────
  function openGoalForm() {
    window.Xiao6.main.openOverlay('新建目标', 'POST /api/agent/goal → Agent Runtime',
      '<div style="display:flex;flex-direction:column;gap:10px">' +
      '<input id="goalTitle" class="x6-cmd-input" placeholder="目标标题（必填）" style="width:100%" />' +
      '<input id="goalDesc" class="x6-cmd-input" placeholder="目标描述（可选）" style="width:100%" />' +
      '<button id="goalSubmit" class="x6-send" type="button" style="align-self:flex-start">创建目标</button>' +
      '<div id="goalResult" class="x6-tool-summary"></div></div>',
      function () {
        var gs = $('goalSubmit');
        gs.addEventListener('click', function () {
          var title = $('goalTitle').value.trim(); if (!title) { window.Xiao6.main.toast('请输入目标标题'); return; }
          gs.disabled = true;
          window.Xiao6.api.postJSON('/api/agent/goal', { title: title, description: $('goalDesc').value.trim() }).then(function (d) {
            gs.disabled = false;
            if (d && d.ok) {
              $('goalResult').innerHTML = '<b>创建成功</b> · goalId=' + d.goalId + ' · ' + esc(d.title);
              window.Xiao6.main.toast('目标已创建 #' + d.goalId);
              state.fetchSnapshot();
            } else {
              $('goalResult').innerHTML = '<span style="color:var(--x6-danger)">失败：' + esc((d && d.error) || '未知错误') + '</span>';
            }
          });
        });
      });
  }
  function openIntentForm() {
    window.Xiao6.main.openOverlay('意图识别', 'POST /api/agent/intent → IntentGateway → GDE',
      '<div style="display:flex;flex-direction:column;gap:10px">' +
      '<input id="intentText" class="x6-cmd-input" placeholder="输入用户意图文本" style="width:100%" />' +
      '<button id="intentSubmit" class="x6-send" type="button" style="align-self:flex-start">识别意图</button>' +
      '<div id="intentResult" class="x6-tool-summary"></div></div>',
      function () {
        var is = $('intentSubmit');
        is.addEventListener('click', function () {
          var text = $('intentText').value.trim(); if (!text) { window.Xiao6.main.toast('请输入意图文本'); return; }
          is.disabled = true;
          window.Xiao6.api.postJSON('/api/agent/intent', { text: text, source: 'ui_workspace' }).then(function (d) {
            is.disabled = false;
            if (d && d.ok) {
              var cls = { create: '创建目标', propose: '建议确认', resume: '恢复目标', skip: '跳过' }[d.action] || d.action;
              $('intentResult').innerHTML = '<b>' + esc(cls) + '</b> · 分类 ' + esc(d.classification) + ' · 置信度 ' + Math.round((d.confidence || 0) * 100) + '%' +
                (d.goalId ? ' · goalId=' + d.goalId : '') +
                (d.reason ? '<br/><span style="color:var(--x6-text-muted)">' + esc(d.reason) + '</span>' : '');
              window.Xiao6.main.toast('意图识别：' + cls);
              if (d.goalId) state.fetchSnapshot();
            } else {
              $('intentResult').innerHTML = '<span style="color:var(--x6-danger)">失败：' + esc((d && d.error) || '未知错误') + '</span>';
            }
          });
        });
      });
  }

  // ───────────────────── 视图调度 / 刷新 ─────────────────────
  function renderView(name) {
    if (name === 'projects') renderProjects();
    else if (name === 'tasks') renderTasks();
    else if (name === 'history') { renderHistory(); window.Xiao6.inspector.renderAgent(); window.Xiao6.timeline.renderResults(); }
    else if (name === 'current') renderCurrent();
    else if (name === 'memory') renderMemory();
    else if (name === 'knowledge') renderKnowledge();
    else if (name === 'capabilities') renderCapabilities();
    else if (name === 'tools') renderTools();
    else if (name === 'settings') renderSettings();
  }
  function renderListsIfVisible() {
    var v = document.body.dataset.view;
    if (v === 'projects') renderProjects();
    else if (v === 'tasks') renderTasks();
    else if (v === 'current') renderCurrent();
    else if (v === 'memory') renderMemory();
    else if (v === 'knowledge') renderKnowledge();
    else if (v === 'capabilities') renderCapabilities();
    else if (v === 'tools') renderTools();
    else if (v === 'settings') renderSettings();
  }

  function init() {
    state.subscribe(renderListsIfVisible);
  }

  window.Xiao6.sidebar = {
    renderView: renderView,
    renderProjects: renderProjects,
    renderTasks: renderTasks,
    renderHistory: renderHistory,
    renderCurrent: renderCurrent,
    renderMemory: renderMemory,
    renderKnowledge: renderKnowledge,
    renderCapabilities: renderCapabilities,
    renderTools: renderTools,
    renderSettings: renderSettings,
    openGoalForm: openGoalForm,
    openIntentForm: openIntentForm,
    init: init
  };
})();
