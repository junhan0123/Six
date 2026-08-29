/* ═════════════════════════════════════════════════════════════════
   Xiao6 UI-R1 · main.js — 启动装配 / 路由 / 轮询（Phase 2）
   装配各模块 init；switchView 全局路由；openOverlay/closeOverlay；
   8s 状态轮询 + 30s 快照轮询；EventSource 事件转交 agent-panel
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
  }

  // ───────────────────── 全局路由（视图切换）─────────────────────
  function switchView(name) {
    document.body.dataset.view = name;
    qsa('.xiao6-view').forEach(function (v) { v.hidden = (v.dataset.view !== name); });
    qsa('.xiao6-nav-btn').forEach(function (b) { b.classList.toggle('is-active', b.dataset.nav === name); });
    if (window.Xiao6.sidebar) window.Xiao6.sidebar.renderView(name);
  }

  // ───────────────────── overlay / panel 关闭绑定 ─────────────────────
  function wireOverlay() {
    var c = $('overlayClose'); if (c) c.addEventListener('click', closeOverlay);
    var s = $('overlayScrim'); if (s) s.addEventListener('click', closeOverlay);
    var cx = $('ctxClose'); if (cx) cx.addEventListener('click', function () {
      var sh = document.querySelector('.xiao6-shell'); if (sh) sh.classList.toggle('context-collapsed');
    });
  }

  function init() {
    initTheme();
    state.subscribe(renderRuntime);

    // 各模块装配（依赖顺序：timeline/sidebar/palette/agentPanel）
    if (window.Xiao6.timeline) window.Xiao6.timeline.init();
    if (window.Xiao6.sidebar) window.Xiao6.sidebar.init();
    if (window.Xiao6.palette) window.Xiao6.palette.init();
    if (window.Xiao6.agentPanel) window.Xiao6.agentPanel.init();
    wireOverlay();

    // 导航路由绑定（sidebar 按钮 → switchView）
    qsa('.xiao6-nav-btn').forEach(function (b) {
      b.addEventListener('click', function () { switchView(b.dataset.nav); });
    });

    // 实时通道：冻结 EventSource('/api/stream')；事件转交 agent-panel
    api.startStream(function (m) { if (window.Xiao6.agentPanel) window.Xiao6.agentPanel.onStreamEvent(m); });

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
        var sh = document.querySelector('.xiao6-shell'); if (sh) sh.classList.remove('context-collapsed');
      }
    });

    switchView('conversation');
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
    switchView: switchView
  };
})();
