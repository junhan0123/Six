/* ============================================================================
 * keyboard-manager.js — 小6 AI OS Experience Sprint v1.0 · Sprint 2
 * 中央键盘路由（Frontend infra，非业务）
 * 职责：
 *   - 统一注册全局快捷键；按“优先级 + 捕获阶段”分发，避免 18+ 去中心化监听；
 *   - Command Palette 注册为最高优先级（Capture Top），保证任何上下文下 Ctrl/Cmd+K 可用；
 *   - ESC 的所有权留在 OverlayManager（浮层栈顶关闭）；本模块不重复处理 ESC。
 * 纪律：零业务逻辑；仅路由 keydown。不触碰 AppState / EventBus / 后端。
 *       经典脚本，暴露 window.KeyboardManager。各模块用 registerShortcut 接入。
 * ========================================================================== */
(function (global) {
  'use strict';

  var doc = global.document;
  var handlers = [];   // { combo, priority, fn, id }

  function normalize(e) {
    var key = (e.key || '').toLowerCase();
    var parts = [];
    if (e.ctrlKey || e.metaKey) parts.push('mod');
    if (e.altKey) parts.push('alt');
    if (e.shiftKey) parts.push('shift');
    parts.push(key);
    return parts.join('+');
  }

  function dispatch(e) {
    var combo = normalize(e);
    // 按优先级降序匹配（数字大者优先；Command Palette 用最高）
    var matched = handlers
      .filter(function (h) { return h.combo === combo; })
      .sort(function (a, b) { return b.priority - a.priority; });
    for (var i = 0; i < matched.length; i++) {
      var h = matched[i];
      var stop = false;
      try { stop = h.fn(e) === false ? false : true; } catch (err) { /* noop */ }
      // 返回 false 表示“未消费”，继续给下一个 handler；其余情况视为已消费并停止
      if (stop) { e.preventDefault(); e.stopPropagation(); return; }
    }
  }

  function registerShortcut(combo, fn, opts) {
    opts = opts || {};
    var id = opts.id || (combo + ':' + handlers.length);
    // 替换同 id 旧注册
    handlers = handlers.filter(function (h) { return h.id !== id; });
    handlers.push({ combo: combo.toLowerCase(), priority: opts.priority || 0, fn: fn, id: id });
    return id;
  }

  function unregister(id) {
    handlers = handlers.filter(function (h) { return h.id !== id; });
  }

  // 单例捕获监听（capture 优先于各模块遗留监听）
  var bound = false;
  function ensure() {
    if (bound) return;
    doc.addEventListener('keydown', dispatch, true);
    bound = true;
  }

  global.KeyboardManager = {
    register: registerShortcut,
    unregister: unregister,
    start: ensure,
    // Command Palette 专用：最高优先级，capture 阶段独占
    registerCommand: function (fn) {
      return registerShortcut('mod+k', fn, { id: 'command-palette', priority: 1000 });
    }
  };
  ensure();
})(window);
