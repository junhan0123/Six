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
      stateMode = 'waiting';
      sub = '等待你的确认';
    } else if (state.busy) {
      stateMode = 'busy';
      sub = state.busyDetail || (sub || '正在处理你的指令…');
    } else if (st === 'ERROR' || st === 'FAILED') {
      stateMode = 'error';
      sub = '执行失败';
    } else if (st === 'COMPLETED' || st === 'STOPPED') {
      stateMode = 'done';
      sub = '任务完成';
    } else {
      var active = state.snap.goals.filter(function (g) { return String(g.status || '').toLowerCase() === 'active'; });
      if (active.length) {
        var g = active[0];
        var prog = Number(g.progress || 0);
        sub = (g.title || ('目标 #' + g.id)) + ' · ' + prog + '%';
        if (st.match(/EXECUTING|RUNNING|THINKING|PLANNING/)) stateMode = 'busy';
      } else {
        sub = '没有正在进行的工作';
      }
    }

    bar.dataset.state = stateMode;
    textEl.textContent = title + (sub ? ' · ' + sub : '');
    if (dot) {
      dot.style.background = stateMode === 'busy' ? 'var(--x6-brand)' : stateMode === 'waiting' ? '#f59e0b' : stateMode === 'error' ? 'var(--x6-voice)' : '#22c55e';
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

    // 新任务按钮
    var ntb = $('newTaskBtn');
    if (ntb) ntb.addEventListener('click', function () {
      currentTaskId = null;
      if (window.Xiao6.timeline) window.Xiao6.timeline.resetTimeline();
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

    // Escape 关闭浮层
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        closeOverlay();
        closeDrawer();
        if (window.Xiao6.palette) window.Xiao6.palette.closePalette();
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
