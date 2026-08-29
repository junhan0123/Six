/* ============================================================================
 * focus-manager.js — 小6 AI OS Experience Sprint v1.0 · Sprint 2
 * 中央焦点管理器（Frontend infra，非业务）
 * 职责：
 *   - 打开浮层时把焦点移入浮层并“陷阱”在内部（Tab / Shift+Tab 循环）；
 *   - 关闭浮层时把焦点恢复到打开前的元素；
 *   - 可选：浮层打开期间把“背景”（容器祖先链之外的兄弟子树）置 inert，彻底不可聚焦。
 * 纪律：零业务逻辑；仅操作 DOM 焦点；不触碰 AppState / EventBus / 后端。
 *       经典脚本，暴露 window.FocusManager；overlay-manager.js 在 open/track/close 时委托它。
 *       背景 inert 默认关闭（opt-in），原因：本仓面板可能嵌套于统一包装层，
 *       全局 inert 有禁用整棵应用的风险；GUI Review 通过后再按需开启。
 * ========================================================================== */
(function (global) {
  'use strict';

  var FOCUSABLE = [
    'a[href]',
    'button:not([disabled])',
    'input:not([disabled]):not([type="hidden"])',
    'select:not([disabled])',
    'textarea:not([disabled])',
    '[tabindex]:not([tabindex="-1"])',
    '[contenteditable="true"]'
  ].join(', ');

  var activeTrap = null;     // 当前陷阱容器（DOM 元素）
  var inerted = [];          // 本次陷阱期间被置 inert 的背景根节点

  function containsNode(ancestor, node) {
    if (!ancestor || !node) return false;
    if (ancestor.contains) return ancestor.contains(node);
    return false;
  }

  function setInert(el, on) {
    try {
      if (typeof el.setInert === 'function') el.setInert(on);
      else if ('inert' in el) el.inert = on;
    } catch (e) { /* noop */ }
  }

  function visibleFocusable(container) {
    var nodes = container.querySelectorAll(FOCUSABLE);
    var out = [];
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      if (el.getAttribute && el.getAttribute('aria-hidden') === 'true') continue;
      if (el.offsetWidth || el.offsetHeight || el === global.document.activeElement) out.push(el);
    }
    return out;
  }

  function firstFocusable(container) {
    var f = visibleFocusable(container);
    if (f.length) return f[0];
    if (container.getAttribute && !container.hasAttribute('tabindex')) {
      try { container.setAttribute('tabindex', '-1'); } catch (e) { /* noop */ }
    }
    return container;
  }

  /* 仅把“容器祖先链之外的兄弟子树”置 inert（祖先链本身保持可用）。
   * 这样即使面板嵌套于统一包装层，也不会误伤容器或整棵应用。 */
  function markBackgroundInert(container) {
    inerted = [];
    var node = container;
    while (node && node.parentElement && node.parentElement !== global.document.body) {
      var sibs = node.parentElement.children;
      for (var i = 0; i < sibs.length; i++) {
        if (sibs[i] !== node) setInert(sibs[i], true);
      }
      node = node.parentElement;
    }
    var bk = global.document.body.children;
    for (var j = 0; j < bk.length; j++) {
      if (!containsNode(bk[j], container)) setInert(bk[j], true);
    }
  }

  function clearBackgroundInert() {
    for (var i = 0; i < inerted.length; i++) setInert(inerted[i], false);
    inerted = [];
  }

  function onKeydown(e) {
    if (e.key !== 'Tab' || !activeTrap) return;
    var f = visibleFocusable(activeTrap);
    if (!f.length) {
      e.preventDefault();
      try { firstFocusable(activeTrap).focus(); } catch (err) { /* noop */ }
      return;
    }
    var first = f[0], last = f[f.length - 1];
    var cur = global.document.activeElement;
    if (e.shiftKey) {
      if (cur === first || !activeTrap.contains(cur)) { e.preventDefault(); last.focus(); }
    } else {
      if (cur === last || !activeTrap.contains(cur)) { e.preventDefault(); first.focus(); }
    }
  }

  /* trap(container, opts): 进入焦点陷阱
   * opts.focusFirst（默认 true）: 是否立即把焦点移入容器首个可聚焦元素
   * opts.backgroundInert（默认 false）: 是否把背景置 inert（opt-in，GUI Review 后开启） */
  function trap(container, opts) {
    if (!container) return;
    if (activeTrap && activeTrap !== container) release();
    activeTrap = container;
    opts = opts || {};
    if (opts.backgroundInert) markBackgroundInert(container);
    if (opts.focusFirst !== false) {
      var target = firstFocusable(container);
      if (target) { try { target.focus(); } catch (e) { /* noop */ } }
    }
    global.document.addEventListener('keydown', onKeydown, true);
  }

  function release() {
    if (!activeTrap) return;
    global.document.removeEventListener('keydown', onKeydown, true);
    clearBackgroundInert();
    activeTrap = null;
  }

  global.FocusManager = {
    trap: trap,
    release: release,
    getFocusable: visibleFocusable,
    isTrapping: function () { return !!activeTrap; },
    current: function () { return activeTrap; }
  };
})(window);
