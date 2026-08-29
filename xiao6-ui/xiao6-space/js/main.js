/* ═════════════════════════════════════════════════════════════════
   Xiao6 UI-R1 · main.js — 启动装配 / 路由 / 轮询（UI-R1-A）
   Agent Workbench：核心问题「小6现在正在做什么」由 renderNow 回答。
   数据来源全部真实：state.snap（GET /api/agent/state + /api/goals + /api/tasks …）
   与 EventSource('/api/stream')；无任何伪造进度 / 伪造 Agent 活动。
   ═════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';
  window.Xiao6 = window.Xiao6 || {};
  var api = window.Xiao6.api;
  var state = window.Xiao6.state;

  function $(id) { return document.getElementById(id); }
  function qsa(s) { return Array.prototype.slice.call(document.querySelectorAll(s)); }
  function el(tag, cls, txt) { var n = document.createElement(tag); if (cls) n.className = cls; if (txt != null) n.textContent = txt; return n; }

  // ───────────────────── toast / banner ─────────────────────
  function toast(msg, kind) {
    var layer = $('toastLayer'); if (!layer) return;
    var t = el('div', 'xiao6-toast' + (kind ? ' ' + kind : ''), msg);
    layer.appendChild(t);
    setTimeout(function () { t.style.opacity = '0'; setTimeout(function () { t.remove(); }, 250); }, 2200);
  }
  function showBanner(msg) { var b = $('banner'); if (!b) return; b.textContent = msg; b.hidden = false; }
  function hideBanner() { var b = $('banner'); if (b) b.hidden = true; }

  // ───────────────────── overlay ─────────────────────
  function openOverlay(title, hint, html, after) {
    var ot = $('overlayTitle'); if (ot) ot.textContent = title;
    var oh = $('overlayHint'); if (oh) oh.textContent = hint || '';
    var ob = $('overlayBody'); if (ob) ob.innerHTML = html;
    var o = $('overlay'); if (o) o.setAttribute('aria-hidden', 'false');
    if (after) after();
  }
  function closeOverlay() {
    var o = $('overlay'); if (!o) return;
    o.setAttribute('aria-hidden', 'true');
    var body = $('overlayBody'); if (body) body.innerHTML = '';
  }

  // ───────────────────── 主题初始化 ─────────────────────
  function initTheme() {
    try { var s = state.lsGet('xiao6_theme', 'light'); document.documentElement.setAttribute('data-theme', s || 'light'); } catch (e) { document.documentElement.setAttribute('data-theme', 'light'); }
    api.getJSON('/api/config').then(function (cfg) {
      if (cfg && cfg.theme) { document.documentElement.setAttribute('data-theme', cfg.theme); state.lsSet('xiao6_theme', cfg.theme); }
    });
  }

  // ───────────────────── 运行时状态灯 ─────────────────────
  function renderRuntime() {
    state.setState(String(state.snap.agent.state || 'IDLE').toUpperCase());
    renderNow();
  }

  // ───────────────────── 「小6现在正在做什么」─────────────────────
  // 严格只读真实状态：/api/agent/state + /api/goals + /api/tasks + 本地 busy /
  // 待确认审批计数。后端没给出的数据一律显示「—」，不猜测、不伪造。
  function pendingApprovalCount() {
    // R1-B：审批计数来自 state.derive.pendingApprovals()（派生自 state.timeline，唯一真相源）
    return state.derive.pendingApprovals().length;
  }
  function renderNow() {
    var bar = $('nowBar'); if (!bar) return;
    var st = String(state.snap.agent.state || 'IDLE').toUpperCase();
    var title = state.CORE_TEXT[st] || '在线待命';
    var sub;
    var mode = 'idle';

    if (pendingApprovalCount() > 0) {
      mode = 'waiting';
      sub = '有一项操作等你确认';
    } else if (state.busy) {
      mode = 'busy';
      sub = state.busyDetail || '正在处理你的指令…';
    } else if (st === 'ERROR' || st === 'FAILED') {
      mode = 'error';
      sub = '上一次执行遇到问题';
    } else {
      var cur = state.snap.agent.current_goal;
      var active = state.snap.goals.filter(function (g) { return String(g.status || '').toLowerCase() === 'active'; });
      var goal = cur || active[0] || null;
      if (goal) {
        var prog = Number(goal.progress || 0);
        sub = '目标 #' + goal.id + '「' + (goal.title || '') + '」· 进度 ' + prog + '%';
        if (String(st).match(/EXECUTING|RUNNING|THINKING|PLANNING/)) mode = 'busy';
      } else {
        var open = state.snap.tasks.filter(function (t) {
          var s = String(t.status || '').toLowerCase();
          return s !== 'done' && s !== 'completed' && s !== 'closed';
        });
        sub = open.length ? (open.length + ' 项任务待处理 · ' + (open[0].title || '')) : '没有正在进行的工作';
      }
    }

    bar.dataset.state = mode;
    var t = $('nowTitle'); if (t) t.textContent = title;
    var s = $('nowSub'); if (s) { s.textContent = sub; s.title = sub; }

    // 「当前项目」导航徽标：真实活跃目标数
    var badge = $('currentNavBadge');
    if (badge) {
      var n = state.snap.goals.filter(function (g) { return String(g.status || '').toLowerCase() === 'active'; }).length;
      badge.textContent = n ? String(n) : '';
      badge.hidden = !n;
    }
  }

  // ───────────────────── 全局路由（视图切换）─────────────────────
  function switchView(name) {
    document.body.dataset.view = name;
    qsa('.xiao6-view').forEach(function (v) { v.hidden = (v.dataset.view !== name); });
    qsa('.xiao6-nav-btn').forEach(function (b) { b.classList.toggle('is-active', b.dataset.nav === name); });
    // Composer 只在首页出现（任务下达入口）
    var comp = $('composer'); if (comp) comp.hidden = (name !== 'home');
    if (window.Xiao6.sidebar) window.Xiao6.sidebar.renderView(name);
    if (name !== 'home') { var jb = $('jumpbar'); if (jb) jb.hidden = true; }
    else { var jb2 = $('jumpbar'); if (jb2) jb2.hidden = false; }
    // 历史视图：切到该视图时立即渲染真实 Agent 活动 / 结果（派生自 state.timeline）
    if (name === 'history' && window.Xiao6.timeline) {
      window.Xiao6.timeline.renderAgentActivity();
      window.Xiao6.timeline.renderResults();
    }
  }

  // ───────────────────── overlay / inspector 关闭绑定 ─────────────────────
  function wireOverlay() {
    var c = $('overlayClose'); if (c) c.addEventListener('click', closeOverlay);
    var s = $('overlayScrim'); if (s) s.addEventListener('click', closeOverlay);
    var cx = $('ctxClose'); if (cx) cx.addEventListener('click', function () {
      var sh = document.querySelector('.xiao6-shell'); if (sh) sh.classList.toggle('inspector-collapsed');
    });
  }

  function init() {
    initTheme();
    state.subscribe(renderRuntime);

    // 各模块装配（依赖顺序：timeline / sidebar / palette / inspector）
    if (window.Xiao6.timeline) window.Xiao6.timeline.init();
    if (window.Xiao6.sidebar) window.Xiao6.sidebar.init();
    if (window.Xiao6.palette) window.Xiao6.palette.init();
    if (window.Xiao6.inspector) window.Xiao6.inspector.init();
    wireOverlay();

    // 导航路由绑定（左侧导航 → switchView）
    qsa('.xiao6-nav-btn').forEach(function (b) {
      b.addEventListener('click', function () { switchView(b.dataset.nav); });
    });

    // 实时通道：冻结 EventSource('/api/stream')；事件转交 inspector
    api.startStream(function (m) { if (window.Xiao6.inspector) window.Xiao6.inspector.onStreamEvent(m); });

    // 快照 + 轮询（节奏冻结：8s 状态 / 30s 快照）
    state.fetchSnapshot();
    setInterval(function () {
      api.getJSON('/api/agent/state').then(function (r) { if (r) { state.snap.agent = r; state.notify(); } });
    }, 8000);
    setInterval(state.fetchSnapshot, 30000);

    // 全局键盘：Escape 关闭浮层
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        closeOverlay();
        if (window.Xiao6.palette) window.Xiao6.palette.closePalette();
        var sh = document.querySelector('.xiao6-shell'); if (sh) sh.classList.remove('inspector-collapsed');
      }
    });

    switchView('home');
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();

  window.Xiao6.main = {
    init: init,
    toast: toast,
    showBanner: showBanner,
    hideBanner: hideBanner,
    openOverlay: openOverlay,
    closeOverlay: closeOverlay,
    switchView: switchView,
    renderNow: renderNow
  };
})();
