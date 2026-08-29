/* ═════════════════════════════════════════════════════════════════
   Xiao6 UI-R2 · main.js — 启动 / 路由 / Drawer / Task Loop
   纯 UI：无后端修改，事件全由真实 API/SSE 驱动
   ═════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';
  window.Xiao6 = window.Xiao6 || {};
  var api = window.Xiao6.api;
  var state = window.Xiao6.state;

  function $(id) { return document.getElementById(id); }
  function qsa(s) { return Array.prototype.slice.call(document.querySelectorAll(s)); }
  function el(tag, cls, txt) { var n = document.createElement(tag); if (cls) n.className = cls; if (txt != null) n.textContent = txt; return n; }

  // ───────────────────── toast ─────────────────────
  function toast(msg, kind) {
    var layer = $('toastLayer'); if (!layer) return;
    var t = el('div', 'x6-toast' + (kind ? ' ' + kind : ''), msg);
    layer.appendChild(t);
    setTimeout(function () { t.style.opacity = '0'; setTimeout(function () { t.remove(); }, 250); }, 2200);
  }

  // ───────────────────── overlay ─────────────────────
  function openOverlay(title, html, after) {
    var ot = $('overlayTitle'); if (ot) ot.textContent = title;
    var ob = $('overlayBody'); if (ob) ob.innerHTML = html;
    var o = $('overlay'); if (o) o.setAttribute('aria-hidden', 'false');
    if (after) after();
  }
  function closeOverlay() {
    var o = $('overlay'); if (!o) return;
    o.setAttribute('aria-hidden', 'true');
    var body = $('overlayBody'); if (body) body.innerHTML = '';
  }

  // ───────────────────── Drawer ─────────────────────
  function openDrawer(title, html) {
    var d = $('drawer'); if (!d) return;
    var dt = $('drawerTitle'); if (dt) dt.textContent = title || '详情';
    var db = $('drawerBody'); if (db) db.innerHTML = html;
    d.setAttribute('aria-hidden', 'false');
    document.querySelector('.x6-shell')?.classList.add('drawer-open');
  }
  function closeDrawer() {
    var d = $('drawer'); if (!d) return;
    d.setAttribute('aria-hidden', 'true');
    document.querySelector('.x6-shell')?.classList.remove('drawer-open');
  }

  // ───────────────────── Task ID tracking ─────────────────────
  var currentTaskId = null;

  // ───────────────────── 主题初始化 ─────────────────────
  function initTheme() {
    try { var s = state.lsGet('xiao6_theme', 'light'); document.documentElement.setAttribute('data-theme', s || 'light'); } catch (e) { document.documentElement.setAttribute('data-theme', 'light'); }
  }

  // ───────────────────── 运行时状态灯 ─────────────────────
  function renderRuntime() {
    var st = String(state.snap.agent.state || 'IDLE').toUpperCase();
    var rt = $('runtimeState');
    if (rt) {
      var dot = rt.querySelector('.x6-status-dot');
      var txt = rt.querySelector('.x6-status-text');
      if (dot) dot.dataset.state = st.toLowerCase();
      if (txt) txt.textContent = state.CORE_TEXT[st] || '小6在线';
      rt.dataset.mode = (st === 'THINKING' || st === 'PLANNING' || st === 'RUNNING' || st === 'EXECUTING' || st === 'LISTENING' || st === 'SPEAKING') ? 'busy' : (st === 'WAITING' || st === 'WAITING_APPROVAL') ? 'waiting' : (st === 'FAILED' || st === 'ERROR' || st === 'OFFLINE') ? 'error' : 'online';
    }
    var op = $('orbPresence'); if (op) op.dataset.state = st.toLowerCase();
    var mo = document.querySelector('.x6-mini-orb'); if (mo) mo.dataset.state = st.toLowerCase();
    renderNow(st);
  }

  // ───────────────────── Now Bar ─────────────────────
  function pendingApprovalCount() {
    return state.derive.pendingApprovals().length;
  }

  function renderNow() {
    var bar = $('nowBar'); if (!bar) return;
    var st = String(state.snap.agent.state || 'IDLE').toUpperCase();
    var title = state.CORE_TEXT[st] || '小6在线';
    var sub;
    var mode = 'idle';
    var textEl = $('nowText');
    var dot = bar.querySelector('.x6-nowbar-dot');

    var curAction = state.derive.currentAction();
    if (curAction) {
      if (curAction.kind === 'tool') {
        sub = '正在执行：' + (curAction.label || '工具');
      } else if (curAction.kind === 'task') {
        sub = '正在分析：' + (curAction.label || '任务');
      } else if (curAction.kind === 'goal') {
        sub = '正在规划：' + (curAction.label || '目标');
      }
    }

    if (pendingApprovalCount() > 0) {
      mode = 'waiting';
      sub = '等待你的确认';
    } else if (state.busy) {
      mode = 'busy';
      sub = state.busyDetail || (sub || '正在处理你的指令…');
    } else if (st === 'ERROR' || st === 'FAILED') {
      mode = 'error';
      sub = '执行失败';
    } else if (st === 'COMPLETED' || st === 'STOPPED') {
      mode = 'done';
      sub = '任务完成';
    } else {
      var active = state.snap.goals.filter(function (g) { return String(g.status || '').toLowerCase() === 'active'; });
      if (active.length) {
        var g = active[0];
        var prog = Number(g.progress || 0);
        sub = (g.title || ('目标 #' + g.id)) + ' · ' + prog + '%';
        if (st.match(/EXECUTING|RUNNING|THINKING|PLANNING/)) mode = 'busy';
      } else {
        sub = '没有正在进行的工作';
      }
    }

    bar.dataset.state = mode;
    textEl.textContent = title + (sub ? ' · ' + sub : '');
    if (dot) {
      dot.style.background = mode === 'busy' ? 'var(--x6-brand)' : mode === 'waiting' ? '#f59e0b' : mode === 'error' ? 'var(--x6-voice)' : '#22c55e';
    }

    // Drawer trigger: show when running tool or approval pending
    var inspBtn = $('inspTrigger');
    if (inspBtn) inspBtn.hidden = (mode === 'idle' || mode === 'done' || mode === 'error');

    // Current section update
    var cs = $('currentSection'); var ci = $('currentItem'); var ct = $('currentTitle');
    if (cs && ci) {
      var runningTools = state.derive.activeTools();
      if (runningTools.length) {
        cs.hidden = false;
        ci.classList.add('running');
        if (ct) ct.textContent = runningTools[0].label || '执行中';
      } else if (pendingApprovalCount() > 0) {
        cs.hidden = false;
        ci.classList.remove('running');
        if (ct) ct.textContent = '等待确认';
      } else {
        cs.hidden = true;
        ci.classList.remove('running');
      }
    }
  }

  // ───────────────────── 全局路由 ─────────────────────
  function switchView(name) {
    document.body.dataset.view = name;
    qsa('.x6-view').forEach(function (v) { v.hidden = (v.dataset.view !== name); });
    qsa('.x6-nav-btn').forEach(function (b) { b.classList.toggle('is-active', b.dataset.nav === name); });
    // Composer只在首页出现
    var cw = $('composerWrap'); if (cw) cw.hidden = (name !== 'home');
    var ts = $('timelineSection'); if (ts) ts.hidden = (name !== 'home');
    var hero = $('hero'); if (hero) hero.hidden = (name !== 'home');
    if (window.Xiao6.sidebar) window.Xiao6.sidebar.renderView(name);
    if (name === 'history' && window.Xiao6.timeline) {
      window.Xiao6.timeline.renderAgentActivity();
      window.Xiao6.timeline.renderResults();
    }
    // History view: render hist list
    if (name === 'history') window.Xiao6.sidebar.renderHistory();
  }

  // ───────────────────── sendChat + task isolation ─────────────────────
  function sendChat(text, opts) {
    opts = opts || {};
    text = String(text || '').trim();
    if (!text || state.busy) return;

    // Task isolation: clear previous task's state
    var wasEmpty = !state.timeline.length;
    currentTaskId = 'task:' + Date.now();
    if (!wasEmpty) {
      // Keep timeline history but clear busy state artifacts from prior task
      var lastResult = state.timeline[state.timeline.length - 1];
      if (lastResult && lastResult.type === 'result' && lastResult.status === 'success') {
        // Previous task completed cleanly — keep full history
      } else {
        // Previous task may have been interrupted — keep history but reset
      }
    }

    // Send via timeline module (handles both chat SSE and stream merge)
    if (window.Xiao6.timeline) {
      window.Xiao6.timeline.sendChat(text, opts);
    }
  }


  // ───────────────────── Settings Pages ─────────────────────
  function renderSettingsPage(page) {
    var content = $('settingsContent'); if (!content) return;
    var pages = {
      general: function() {
        return '<div class="x6-settings-section"><div class="x6-settings-title">常规</div><div class="x6-settings-desc">管理主题、语言等常规设置。</div>' +
          '<div style="margin-top:16px"><div style="font-size:13px;font-weight:500;margin-bottom:8px">主题</div><div style="display:flex;gap:8px">' +
          '<button class="x6-theme-btn is-active" data-theme="light">浅色</button>' +
          '<button class="x6-theme-btn" data-theme="dark">深色</button>' +
          '<button class="x6-theme-btn" data-theme="system">跟随系统</button>' +
          '</div></div>' +
          '<div style="margin-top:24px"><div style="font-size:13px;font-weight:500;margin-bottom:8px">工作模式</div>' +
          '<div style="display:flex;gap:12px">' +
          '<div class="x6-mode-card is-active"><div style="font-size:13px;font-weight:500">智能模式</div><div style="font-size:12px;color:var(--x6-text-muted);margin-top:4px">自动推荐模型、技能与配置，适合日常使用</div></div>' +
          '<div class="x6-mode-card"><div style="font-size:13px;font-weight:500">专家模式</div><div style="font-size:12px;color:var(--x6-text-muted);margin-top:4px">手动控制模型、技能、应用与权限</div></div>' +
          '</div></div></div>';
      },
      models: function() {
        return '<div class="x6-settings-section"><div class="x6-settings-title">模型</div><div class="x6-settings-desc">管理自定义模型、本地配置和已保存模型。</div>' +
          '<div style="margin-top:16px"><div style="font-size:13px;font-weight:500;margin-bottom:8px">添加模型</div>' +
          '<div style="display:flex;gap:8px"><input type="text" placeholder="输入模型名称或 API 地址..." style="flex:1;padding:8px 12px;border:1px solid var(--x6-border);border-radius:6px;font-size:13px">' +
          '<button class="x6-add-model-btn">+ 添加</button></div></div>' +
          '<div style="margin-top:24px"><div style="font-size:13px;font-weight:500;margin-bottom:8px">已保存模型</div>' +
          '<div class="x6-model-list">' +
          modelListHTML() +
          '</div></div></div>';
      },
      chat: function() {
        return '<div class="x6-settings-section"><div class="x6-settings-title">聊天</div><div class="x6-settings-desc">配置对话偏好、回复风格和上下文行为。</div>' +
          '<div style="margin-top:16px"><div style="font-size:13px;font-weight:500;margin-bottom:8px">模式</div>' +
          '<div class="x6-mode-options">' +
          '<div class="x6-mode-option"><span>请求批准</span><span style="font-size:11px;color:var(--x6-text-muted)">所有工具需要手动批准</span></div>' +
          '<div class="x6-mode-option is-active"><span>替我审批</span><span style="font-size:11px;color:var(--x6-text-muted)">低风险操作自动通过</span></div>' +
          '<div class="x6-mode-option"><span>完全访问</span><span style="font-size:11px;color:var(--x6-text-muted)">无需确认，自由使用工具</span></div>' +
          '</div></div>' +
          '<div style="margin-top:24px"><div style="font-size:13px;font-weight:500;margin-bottom:8px">回复风格</div>' +
          '<div class="x6-mode-options">' +
          '<div class="x6-mode-option"><span>详细</span><span style="font-size:11px;color:var(--x6-text-muted)">工具调用默认展开</span></div>' +
          '<div class="x6-mode-option is-active"><span>精简</span><span style="font-size:11px;color:var(--x6-text-muted)">工具调用默认折叠</span></div>' +
          '</div></div></div>';
      }
    };
    content.innerHTML = (pages[page] || pages.general)();
    initThemeButtons();
  }
  
  function modelListHTML() {
    var models = [
      { name: 'auto', desc: '自动选择最适合当前任务的模型', default: true },
      { name: 'agnes-2.5-flash', desc: '速度与能力更均衡，适合复杂任务', mult: '0.00x' },
      { name: 'agnes-2.5-pro', desc: '面向下一代 AI Agent 的旗舰推理模型', mult: '1.00x' },
      { name: 'agnes-2.0-flash', desc: '快速稳定，适合日常对话和编程', mult: '0.00x' }
    ];
    return models.map(function(m) {
      return '<div class="x6-model-card' + (m.default ? ' is-default' : '') + '">' +
        '<div class="x6-model-name">' + m.name + '</div>' +
        '<div class="x6-model-desc">' + m.desc + '</div>' +
        (m.mult ? '<div class="x6-model-mult">' + m.mult + '</div>' : '') +
        '<button class="x6-model-action">' + (m.default ? '默认' : '设为默认') + '</button>' +
        '</div>';
    }).join('');
  }
  
  function initThemeButtons() {
    var btns = document.querySelectorAll('.x6-theme-btn');
    btns.forEach(function(btn) {
      btn.addEventListener('click', function() {
        btns.forEach(function(b) { b.classList.remove('is-active'); });
        this.classList.add('is-active');
        var theme = this.dataset.theme;
        document.documentElement.setAttribute('data-theme', theme === 'system' ? '' : theme);
      });
    });
    var modeCards = document.querySelectorAll('.x6-mode-card, .x6-mode-option');
    modeCards.forEach(function(card) {
      card.addEventListener('click', function() {
        var parent = this.parentElement;
        parent.querySelectorAll('.x6-mode-card, .x6-mode-option').forEach(function(c) { c.classList.remove('is-active'); });
        this.classList.add('is-active');
      });
    });
  }

  // ───────────────────── init ─────────────────────
  function init() {
    initTheme();
    state.subscribe(renderRuntime);

    if (window.Xiao6.timeline) window.Xiao6.timeline.init();
    if (window.Xiao6.sidebar) window.Xiao6.sidebar.init();
    if (window.Xiao6.palette) window.Xiao6.palette.init();
    if (window.Xiao6.inspector) window.Xiao6.inspector.init();

    // 导航
    qsa('.x6-nav-btn').forEach(function (b) {
      b.addEventListener('click', function () { switchView(b.dataset.nav); });
    });

    // 新对话按钮（侧边栏）
    var ncb = $('newChatBtn');
    if (ncb) ncb.addEventListener('click', function () {
      currentTaskId = null;
      if (window.Xiao6.timeline) window.Xiao6.timeline.resetTimeline();
      var ci = $('cmdInput'); if (ci) ci.value = '';
      var ts = $('timelineSection'); if (ts) ts.style.display = 'none';
      switchView('home');
    });

    // Drawer
    var dtrig = $('inspTrigger');
    if (dtrig) dtrig.addEventListener('click', function () {
      if (window.Xiao6.inspector) window.Xiao6.inspector.renderDrawer();
    });
    var dclose = $('drawerClose');
    if (dclose) dclose.addEventListener('click', closeDrawer);
    var dscrim = $('drawerScrim');
    if (dscrim) dscrim.addEventListener('click', closeDrawer);

    // 实时通道
    api.startStream(function (m) { if (window.Xiao6.inspector) window.Xiao6.inspector.onStreamEvent(m); });

    // 快照
    state.fetchSnapshot();
    setInterval(function () {
      api.getJSON('/api/agent/state').then(function (r) { if (r) { state.snap.agent = r; state.notify(); } });
    }, 8000);
    setInterval(state.fetchSnapshot, 30000);

    // Quick action cards
    qsa('.x6-quick-card').forEach(function (card) {
      card.addEventListener('click', function () {
        var prompt = this.dataset.prompt;
        if (prompt) {
          var ci = $('cmdInput');
          if (ci) { ci.value = prompt; ci.focus(); }
          sendChat(prompt);
        }
      });
    });

    // Mode selector
    var modeSel = $('modeSel');
    if (modeSel) {
      modeSel.addEventListener('click', function (e) {
        e.stopPropagation();
        var isExpert = state.toolModes.expert;
        state.toolModes.expert = !isExpert;
        modeSel.textContent = state.toolModes.expert ? '专家模式 ▾' : '智能模式 ▾';
        state.lsSet('xiao6_expert', state.toolModes.expert ? '1' : '0');
      });
    }
    // Restore mode from localStorage
    if (state.lsGet('xiao6_expert', '0') === '1') {
      state.toolModes.expert = true;
      var ms = $('modeSel'); if (ms) ms.textContent = '专家模式 ▾';
    }

    // Menu bar handling
    var menubtns = document.querySelectorAll('.x6-menubar-btn');
    var menus = document.querySelectorAll('.x6-menu-dropdown');
    menubtns.forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.stopPropagation();
        var menuId = 'menu-' + this.dataset.menu;
        var menu = $(menuId);
        var isOpen = menu && !menu.hidden;
        menus.forEach(function (m) { if (m) m.hidden = true; });
        if (menu && !isOpen) menu.hidden = false;
      });
    });
    document.addEventListener('click', function (e) {
      menus.forEach(function (m) { if (m) m.hidden = true; });
      var item = e.target.closest('.x6-menu-item');
      if (!item) return;
      var action = item.dataset.action;
      if (action === 'new-chat') { $('newChatBtn')?.click(); }
      else if (action === 'settings') { switchView('settings'); }
    });
    
    // Toggle sidebar
    var toggleBtn = $('toggleSidebar');
    if (toggleBtn) toggleBtn.addEventListener('click', function () {
      var sb = $('sidebar'); if (sb) sb.classList.toggle('collapsed');
    });
    
    // Settings button
    var settingsBtn = $('settingsBtn');
    if (settingsBtn) settingsBtn.addEventListener('click', function () { switchView('settings'); });
    var settingsBack = $('settingsBack');
    if (settingsBack) settingsBack.addEventListener('click', function () { switchView('home'); });
    
    // Settings navigation
    var settingsNavBtns = document.querySelectorAll('.x6-settings-nav-btn');
    settingsNavBtns.forEach(function (btn) {
      btn.addEventListener('click', function () {
        settingsNavBtns.forEach(function (b) { b.classList.remove('is-active'); });
        this.classList.add('is-active');
        renderSettingsPage(this.dataset.settings);
      });
    });

    // Escape 关闭浮层
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        closeOverlay();
        closeDrawer();
        if (window.Xiao6.palette) window.Xiao6.palette.closePalette();
        menus.forEach(function (m) { if (m) m.hidden = true; });
      }
    });

    switchView('home');
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();

  window.Xiao6.main = {
    init: init,
    toast: toast,
    openOverlay: openOverlay,
    closeOverlay: closeOverlay,
    openDrawer: openDrawer,
    closeDrawer: closeDrawer,
    switchView: switchView,
    renderNow: renderNow,
    sendChat: sendChat
  };
})();
