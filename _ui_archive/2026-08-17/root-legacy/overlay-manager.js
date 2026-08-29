/* ============================================================================
 * overlay-manager.js — 小6 Overlay Implementation Sprint · Step [2]
 * 职责（DOM / UI 控制层，与 overlay-runtime.js 纯数据层严格分离）：
 *   - 在 DOM 中装配  .zz-overlay > .zz-overlay__scrim + .zz-dialog
 *   - 维护打开栈（stack）；多实例按深度递增 z-index（基于 --z-dialog-mask 单一来源）
 *   - 中央 ESC：仅当栈非空时监听 keydown（capture），关闭栈顶并 stopPropagation；
 *               栈空则完全休眠，零页面键盘影响（不干扰 18+ 既有去中心化 ESC 监听）
 *   - 焦点：打开前保存 document.activeElement；关闭后恢复；trapFocus 接口预留（默认关闭）
 * 纪律：不触碰业务逻辑 / AppState / EventBus / 任何遗留 Modal；零默认行为变更。
 *       经典脚本（与 overlay-runtime.js 同模式），暴露 window.OverlayManager。
 * ========================================================================== */
(function (global) {
  'use strict';

  var ROOT_ID = 'zzOverlayRoot';
  var Z_STEP = 1;                 // 每深一层 +1（相对 --z-dialog-mask）
  var REMOVE_DELAY = 300;         // 与 --motion-base 对齐的过渡时长

  var stack = [];                 // [{ id, el, dialog, scrim, returnFocus, opts, external }]
  var templates = {};             // 命名模板（register）
  var escBound = false;

  // 浮层类型枚举（单一来源，供审计/调试/样式钩子）
  var OverlayType = {
    MODAL: 'modal',         // 强制聚焦、背景不可交互（确认/审批/详情）
    PANEL: 'panel',         // 信息面板（天气/监控/记忆…），可非陷阱
    DIALOG: 'dialog',       // 通用对话框
    COMMAND: 'command',     // 指令中心
    MENU: 'menu',           // 浮层菜单（伴侣菜单等）
    NOTIFICATION: 'notification'
  };

  function FM() { return global.FocusManager || null; }

  // —— BASE_Z 单一来源：运行时读取 --z-dialog-mask（Step[1] 令牌），避免第二套数值 ——
  var BASE_Z = 82;
  (function syncBaseZ() {
    try {
      var v = getComputedStyle(document.documentElement).getPropertyValue('--z-dialog-mask');
      var n = parseInt(String(v).trim(), 10);
      if (!isNaN(n)) BASE_Z = n;
    } catch (e) { /* 回退 82 */ }
  })();

  function getRoot() {
    var root = document.getElementById(ROOT_ID);
    if (!root) {
      root = document.createElement('div');
      root.id = ROOT_ID;
      root.setAttribute('aria-hidden', 'true');
      root.style.display = 'contents'; // 零盒模型副作用；fixed 子项仍相对视口
      document.body.appendChild(root);
    }
    return root;
  }

  function buildScrim() {
    var scrim = document.createElement('div');
    scrim.className = 'zz-overlay__scrim';
    return scrim;
  }

  function buildCloseButton() {
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'zz-dialog__close';
    btn.setAttribute('aria-label', '关闭');
    btn.innerHTML =
      '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">' +
      '<path d="M6 6l12 12M18 6L6 18" fill="none" stroke="currentColor" ' +
      'stroke-width="2" stroke-linecap="round"/></svg>';
    return btn;
  }

  function focusDialog(dialog) {
    var target = dialog.querySelector('.zz-dialog__close') ||
      dialog.querySelector('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
    if (target) { try { target.focus(); } catch (e) { /* noop */ } }
  }

  function prefersReduced() {
    return !!(global.matchMedia && global.matchMedia('(prefers-reduced-motion: reduce)').matches);
  }

  function open(config) {
    config = config || {};
    var id = config.id || ('zz-ov-' + Date.now() + '-' + Math.floor(Math.random() * 1e4));

    // 防重复打开同一 id（含正在过渡移除中的 DOM）
    if (stack.some(function (s) { return s.id === id; }) ||
        document.querySelector('[data-overlay-id="' + id + '"]')) {
      return getHandle(id);
    }

    var root = getRoot();
    var overlay = document.createElement('div');
    overlay.className = 'zz-overlay';
    overlay.dataset.overlayId = id;

    var scrim = buildScrim();
    var dialog = document.createElement('div');
    dialog.className = 'zz-dialog' + (config.size ? ' zz-dialog--' + config.size : '');
    dialog.setAttribute('role', config.role || 'dialog');
    dialog.setAttribute('aria-modal', 'true');

    // —— header ——
    if (config.title || config.closable !== false) {
      var header = document.createElement('div');
      header.className = 'zz-dialog__header';
      if (config.title) {
        var h = document.createElement('h2');
        h.className = 'zz-dialog__title';
        h.id = config.titleId || (id + '-title');
        h.textContent = config.title;           // textContent 防 XSS
        header.appendChild(h);
        dialog.setAttribute('aria-labelledby', h.id);
      }
      if (config.closable !== false) {
        var closeBtn = buildCloseButton();
        closeBtn.addEventListener('click', function () { close(id); });
        header.appendChild(closeBtn);
      }
      dialog.appendChild(header);
    }

    // —— body ——
    var body = document.createElement('div');
    body.className = 'zz-dialog__body';
    if (config.content instanceof Node) body.appendChild(config.content);
    else if (typeof config.content === 'string') body.innerHTML = config.content;
    dialog.appendChild(body);

    // —— footer ——
    if (config.footer) {
      var footer = document.createElement('div');
      footer.className = 'zz-dialog__footer';
      if (config.footer instanceof Node) footer.appendChild(config.footer);
      else footer.innerHTML = config.footer;
      dialog.appendChild(footer);
    }

    overlay.appendChild(scrim);
    overlay.appendChild(dialog);

    // 点击 scrim 关闭（点击 dialog 内部不触发：dialog 是 scrim 兄弟且 z-index 在上层）
    if (config.dismissOnScrim !== false) {
      overlay.addEventListener('mousedown', function (e) {
        if (e.target === overlay || e.target === scrim) close(id);
      });
    }

    root.appendChild(overlay);

    // 焦点保存
    var returnFocus = document.activeElement;
    if (!returnFocus || returnFocus === document.body) returnFocus = null;

    var depth = stack.length;
    overlay.style.zIndex = String(BASE_Z + depth * Z_STEP);

    // 下一帧加 .is-open 触发过渡
    if (global.requestAnimationFrame) {
      global.requestAnimationFrame(function () { overlay.classList.add('is-open'); });
    } else {
      overlay.classList.add('is-open');
    }

    var entry = { id: id, el: overlay, dialog: dialog, scrim: scrim, returnFocus: returnFocus, opts: config };
    stack.push(entry);
    ensureEsc();
    applyFocus(entry);

    return makeHandle(entry);
  }

  function close(id) {
    var idx = -1;
    for (var i = 0; i < stack.length; i++) { if (stack[i].id === id) { idx = i; break; } }
    if (idx === -1) return false;
    var entry = stack[idx];

    releaseFocus(entry);

    if (entry.external) {
      // 外部浮层（既有面板）：调用其 onClose 回调，不移除其 DOM
      if (typeof entry.onClose === 'function') {
        try { entry.onClose(); } catch (e) { /* noop */ }
      }
    } else {
      entry.el.classList.remove('is-open');
      var delay = prefersReduced() ? 0 : REMOVE_DELAY;
      (function (el) {
        global.setTimeout(function () {
          if (el && el.parentNode) el.parentNode.removeChild(el);
        }, delay);
      })(entry.el);
    }

    stack.splice(idx, 1);

    if (entry.returnFocus && document.contains(entry.returnFocus)) {
      try { entry.returnFocus.focus(); } catch (e) { /* noop */ }
    }
    if (stack.length === 0) releaseEsc();
    return true;
  }

  function closeAll() {
    var ids = stack.map(function (s) { return s.id; });
    ids.forEach(close);
  }

  function isOpen(id) {
    return stack.some(function (s) { return s.id === id; });
  }

  function getHandle(id) {
    var entry = null;
    for (var i = 0; i < stack.length; i++) { if (stack[i].id === id) { entry = stack[i]; break; } }
    if (!entry) return null;
    return makeHandle(entry);
  }

  function makeHandle(entry) {
    return {
      id: entry.id,
      el: entry.el,
      dialog: entry.dialog,
      close: function () { return close(entry.id); }
    };
  }

  /* —— 中央 ESC：栈非空时捕获并关闭栈顶；栈空则休眠（零键盘影响） —— */
  function onKeydown(e) {
    if (e.key !== 'Escape' && e.keyCode !== 27) return;
    if (stack.length === 0) return;                 // 休眠：不拦截，遗留 ESC 照常工作
    var top = stack[stack.length - 1];
    if (top && top.opts && top.opts.onEsc === false) return; // 允许特定 overlay 禁用 ESC
    e.preventDefault();
    e.stopPropagation();                             // 阻止 18+ 去中心化监听误触
    close(top.id);
  }
  function ensureEsc() {
    if (escBound) return;
    document.addEventListener('keydown', onKeydown, true); // capture 优先于遗留监听
    escBound = true;
  }
  function releaseEsc() {
    if (!escBound) return;
    document.removeEventListener('keydown', onKeydown, true);
    escBound = false;
  }

  /* —— 焦点：打开置陷阱、关闭释放并恢复（委托 FocusManager；无则降级）——
   * 06 §2（Keyboard 集中焦点管理）/ 03 §2.6（退出态焦点恢复）落地。 */
  function applyFocus(entry) {
    var fm = FM();
    var container = entry.dialog || entry.el;
    if (!container) return;
    var trap = entry.opts && entry.opts.trap !== false;
    if (fm && trap) {
      fm.trap(container, {
        backgroundInert: !!(entry.opts && entry.opts.backgroundInert),
        focusFirst: !(entry.opts && entry.opts.autofocus === false)
      });
    } else if (!(entry.opts && entry.opts.autofocus === false)) {
      focusDialog(container);
    }
  }
  function releaseFocus(entry) {
    var fm = FM();
    if (fm && fm.isTrapping()) {
      var container = entry.dialog || entry.el;
      if (fm.current() === container) fm.release();
    }
  }

  /* —— 外部浮层登记：既有面板（settings/weather/doc/…）保留自身 DOM，
   * 仅把 ESC / 焦点 / 栈 / z-index 交给 OverlayManager 统一掌管。
   * opts: { el, dialog?, onClose, type, trap?, autofocus?, backgroundInert? } —— */
  function track(id, opts) {
    opts = opts || {};
    if (!id) return null;
    if (stack.some(function (s) { return s.id === id; })) return getHandle(id);
    var returnFocus = document.activeElement;
    if (!returnFocus || returnFocus === document.body) returnFocus = null;

    var el = opts.el || null;
    // 统一 z-index：按栈深递增，消除各面板散落的硬值；
    // keepZIndex:true 时保留面板自身级别（如 modal-mask 9000 / command 90 等高位浮层）
    if (el && el.style && !opts.keepZIndex) {
      el.style.zIndex = String(BASE_Z + stack.length * Z_STEP);
    }

    var entry = {
      id: id, el: el, dialog: opts.dialog || el, scrim: null,
      returnFocus: returnFocus, opts: opts, external: true, onClose: opts.onClose
    };
    stack.push(entry);
    ensureEsc();
    applyFocus(entry);
    return makeHandle(entry);
  }

  function untrack(id) {
    var idx = -1;
    for (var i = 0; i < stack.length; i++) { if (stack[i].id === id) { idx = i; break; } }
    if (idx === -1) return false;
    var entry = stack[idx];
    releaseFocus(entry);
    stack.splice(idx, 1);
    if (entry.returnFocus && document.contains(entry.returnFocus)) {
      try { entry.returnFocus.focus(); } catch (e) { /* noop */ }
    }
    if (stack.length === 0) releaseEsc();
    return true;
  }

  function closeTop() {
    if (stack.length === 0) return false;
    return close(stack[stack.length - 1].id);
  }

  function trapFocus(entry) { applyFocus(entry); }
  function releaseTrap(entry) { releaseFocus(entry); }

  /* —— 命名模板（register）：open('id') 时合并模板配置 —— */
  function register(id, config) {
    templates[id] = config || {};
    return id;
  }

  /* ════════════════════════════════════════════════════════════════════════
   * Step [3] — Toast System Unification
   * 统一渲染 .zz-toast 到 #zzToastRoot；legacy 调用（window.toast / ZZErrorToast）
   * 经 Adapter 路由至此。全部令牌驱动，不新增第二套颜色 / 阴影 / 圆角 / z-index。
   * 纪律：零业务逻辑变更；仅消费既有的 toast 调用签名（type/message/title/action/
   *       dismissMs/legacyDismissMs/closable/progress）。
   * ════════════════════════════════════════════════════════════════════════ */
  var TOAST_ROOT_ID = 'zzToastRoot';
  var MAX_TOASTS = 4;
  var TOAST_EXIT_MS = 260;        // 与 --motion-base(.28s) 对齐的退出过渡时长
  var toastStack = [];            // [{ id, el, timer }]
  var TOAST_DEFAULT_MS = { info: 3200, success: 3200, warning: 5000, error: 6000, loading: 0, progress: 0 };

  var TOAST_ICONS = {
    success: '<path d="M5 13l4 4L19 7" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>',
    warning: '<path d="M12 3l9.5 16.5H2.5L12 3z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><path d="M12 9v4.5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><circle cx="12" cy="17" r="1.1" fill="currentColor"/>',
    error:   '<circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="2"/><path d="M9 9l6 6M15 9l-6 6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
    info:    '<circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="2"/><path d="M12 11v5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><circle cx="12" cy="7.6" r="1.1" fill="currentColor"/>',
    loading: '<circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="2" stroke-dasharray="42 56" stroke-linecap="round" class="zz-toast__spin"/>',
    progress:'<circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="2"/>'
  };

  function getToastRoot() {
    var root = document.getElementById(TOAST_ROOT_ID);
    if (!root) {
      root = document.createElement('div');
      root.id = TOAST_ROOT_ID;
      root.setAttribute('aria-live', 'polite');
      root.setAttribute('aria-atomic', 'false');
      document.body.appendChild(root);
    }
    return root;
  }

  function findToast(id) {
    for (var i = 0; i < toastStack.length; i++) { if (toastStack[i].id === id) return toastStack[i]; }
    return null;
  }

  function buildToastEl(cfg, id) {
    var type = cfg.type || 'info';
    var el = document.createElement('div');
    el.className = 'zz-toast zz-toast--' + type;
    el.setAttribute('role', type === 'error' ? 'alert' : 'status');

    var icon = document.createElement('span');
    icon.className = 'zz-toast__icon';
    icon.setAttribute('aria-hidden', 'true');
    icon.innerHTML = '<svg viewBox="0 0 24 24">' + (TOAST_ICONS[type] || TOAST_ICONS.info) + '</svg>';
    el.appendChild(icon);

    var body = document.createElement('div');
    body.className = 'zz-toast__body';
    if (cfg.title) {
      var title = document.createElement('div');
      title.className = 'zz-toast__title';
      title.textContent = cfg.title;
      body.appendChild(title);
    }
    var msg = document.createElement('div');
    msg.className = 'zz-toast__message';
    msg.textContent = cfg.message != null ? String(cfg.message) : '';
    body.appendChild(msg);

    if (type === 'progress') {
      var track = document.createElement('div');
      track.className = 'zz-toast__progress';
      var bar = document.createElement('div');
      bar.className = 'zz-toast__progress-bar';
      var pct = typeof cfg.progress === 'number' ? Math.max(0, Math.min(100, cfg.progress)) : 0;
      bar.style.width = pct + '%';
      track.appendChild(bar);
      body.appendChild(track);
    }
    el.appendChild(body);

    if (cfg.action && cfg.action.label) {
      var act = document.createElement('button');
      act.type = 'button';
      act.className = 'zz-toast__action';
      act.textContent = cfg.action.label;
      act.addEventListener('click', function () {
        try { if (typeof cfg.action.onClick === 'function') cfg.action.onClick(); } catch (e) { /* noop */ }
        dismissToast(id);
      });
      el.appendChild(act);
    }

    if (cfg.closable !== false) {
      var close = document.createElement('button');
      close.type = 'button';
      close.className = 'zz-toast__close';
      close.setAttribute('aria-label', '关闭');
      close.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>';
      close.addEventListener('click', function () { dismissToast(id); });
      el.appendChild(close);
    }
    return el;
  }

  /* —— 对外 API：OverlayManager.toast(cfg) ——
   * cfg: { type, message, title, action:{label,onClick}, dismissMs, legacyDismissMs,
   *        closable, progress, id }
   * 返回句柄 { id, dismiss(), setProgress(p) }；dismissMs 优先，其次 legacyDismissMs，
   * 再回退按 type 的默认时长（loading/progress 默认常驻）。 */
  function toast(cfg) {
    cfg = cfg || {};
    if (typeof cfg === 'string') cfg = { message: cfg, type: 'info' };
    var type = cfg.type || 'info';
    var id = cfg.id || ('zz-toast-' + Date.now() + '-' + Math.floor(Math.random() * 1e4));

    var root = getToastRoot();
    var el = buildToastEl(cfg, id);

    if (global.requestAnimationFrame) {
      global.requestAnimationFrame(function () { el.classList.add('is-in'); });
    } else {
      el.classList.add('is-in');
    }
    root.appendChild(el);

    toastStack.push({ id: id, el: el, timer: null });
    if (toastStack.length > MAX_TOASTS) {
      var oldest = toastStack.shift();
      if (oldest) dismissToast(oldest.id, true);
    }

    var ms = (cfg.dismissMs != null) ? cfg.dismissMs
      : (cfg.legacyDismissMs != null) ? cfg.legacyDismissMs
      : (TOAST_DEFAULT_MS[type] != null ? TOAST_DEFAULT_MS[type] : 3200);
    if (ms && ms > 0) {
      var entry = findToast(id);
      if (entry) entry.timer = global.setTimeout(function () { dismissToast(id); }, ms);
    }

    return {
      id: id,
      dismiss: function () { dismissToast(id); },
      setProgress: function (p) { setToastProgress(id, p); }
    };
  }

  function dismissToast(id, immediate) {
    var idx = -1;
    for (var i = 0; i < toastStack.length; i++) { if (toastStack[i].id === id) { idx = i; break; } }
    if (idx === -1) return false;
    var entry = toastStack[idx];
    if (entry.timer) clearTimeout(entry.timer);
    entry.el.classList.remove('is-in');
    var delay = (immediate || prefersReduced()) ? 0 : TOAST_EXIT_MS;
    global.setTimeout(function () {
      if (entry.el && entry.el.parentNode) entry.el.parentNode.removeChild(entry.el);
    }, delay);
    toastStack.splice(idx, 1);
    return true;
  }

  function setToastProgress(id, p) {
    var entry = findToast(id);
    if (!entry) return;
    var bar = entry.el.querySelector('.zz-toast__progress-bar');
    if (bar) bar.style.width = Math.max(0, Math.min(100, p)) + '%';
  }

  global.OverlayManager = {
    register: register,
    toast: toast,
    dismissToast: dismissToast,
    open: function (config) {
      if (typeof config === 'string') {
        var tpl = templates[config] || {};
        config = Object.assign({}, tpl, { id: config });
      } else if (config && templates[config.id]) {
        config = Object.assign({}, templates[config.id], config);
      }
      return open(config);
    },
    close: close,
    closeAll: closeAll,
    closeTop: closeTop,
    track: track,
    untrack: untrack,
    isOpen: isOpen,
    getStack: function () {
      return stack.map(function (s) {
        return { id: s.id, type: s.opts && s.opts.type, external: !!s.external };
      });
    },
    OverlayType: OverlayType,
    trapFocus: trapFocus,
    releaseTrap: releaseTrap
  };
})(window);
