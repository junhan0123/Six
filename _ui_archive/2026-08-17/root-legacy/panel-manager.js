/*
 * panel-manager.js — Unified Workspace Panel Lifecycle + WorkspaceState (UI-only)
 *
 * 身份：AI OS Experience Sprint v2.0 — Unified Workspace
 * 性质：纯前端 UI 收口层；不引入任何业务能力 / Runtime / API / 状态写入口 / 权限 / 事件 / 域数据。
 * 纪律：
 *   - 复用既有 OverlayManager（唯一浮层栈 / 中央 ESC / 焦点 / z-index），绝不重建第二套。
 *   - 复用既有 CapabilityExposure（T0–T4 档位），不在本文件声明能力。
 *   - WorkspaceState 仅存 UI 工作区状态（当前工作区 / 聚焦面板 / 固定面板 / 最近面板 / 活动上下文引用）。
 *     活动上下文只存"引用 id"（goalId / conversationId / knowledgeNodeId / memoryId / toolName），
 *     不存任何域数据；域真相仍归 AppState（单一写入口）。
 *   - 所有面板 open/close 仍由各模块自身 DOM 逻辑完成；本管理器只统一"生命周期状态"与"入口分发"。
 */
(function () {
  'use strict';

  var STORAGE_KEY = 'zz.workspace.v1';
  var RECENT_MAX = 8;

  /* ───────────────────────── WorkspaceState（UI-only 工作区状态） ───────────────────────── */
  var WorkspaceState = {
    data: {
      workspace: 'home',
      focusedPanelId: null,
      pinnedPanelIds: [],
      recentPanelIds: [],
      activeContext: { goalId: null, conversationId: null, knowledgeNodeId: null, memoryId: null, toolName: null }
    },
    load: function () {
      try {
        var raw = localStorage.getItem(STORAGE_KEY);
        if (raw) {
          var p = JSON.parse(raw);
          if (p && typeof p === 'object') {
            if (typeof p.workspace === 'string') this.data.workspace = p.workspace;
            if (typeof p.focusedPanelId === 'string' || p.focusedPanelId === null) this.data.focusedPanelId = p.focusedPanelId;
            if (Array.isArray(p.pinnedPanelIds)) this.data.pinnedPanelIds = p.pinnedPanelIds.slice(0, 32);
            if (Array.isArray(p.recentPanelIds)) this.data.recentPanelIds = p.recentPanelIds.slice(0, RECENT_MAX);
            if (p.activeContext && typeof p.activeContext === 'object') {
              this.data.activeContext = Object.assign(this.data.activeContext, p.activeContext);
            }
          }
        }
      } catch (e) { /* 隐私模式 / 损坏数据忽略 */ }
      return this.data;
    },
    save: function () {
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify(this.data)); } catch (e) { /* 隐私模式忽略 */ }
    },
    focus: function (id) {
      this.data.focusedPanelId = id;
      this.pushRecent(id);
      this.save();
    },
    pushRecent: function (id) {
      if (!id) return;
      var r = this.data.recentPanelIds.filter(function (x) { return x !== id; });
      r.unshift(id);
      this.data.recentPanelIds = r.slice(0, RECENT_MAX);
    },
    clearFocus: function (id) {
      if (this.data.focusedPanelId === id) this.data.focusedPanelId = null;
      this.save();
    },
    pin: function (id) {
      if (this.data.pinnedPanelIds.indexOf(id) === -1) this.data.pinnedPanelIds.push(id);
      this.save();
    },
    unpin: function (id) {
      this.data.pinnedPanelIds = this.data.pinnedPanelIds.filter(function (x) { return x !== id; });
      this.save();
    },
    isPinned: function (id) { return this.data.pinnedPanelIds.indexOf(id) !== -1; },
    setActiveContext: function (ctx) {
      if (!ctx || typeof ctx !== 'object') return;
      this.data.activeContext = Object.assign(this.data.activeContext, ctx);
      this.save();
    },
    get: function () { return this.data; },
    getActiveContext: function () { return this.data.activeContext; }
  };

  /* ───────────────────────── Panel 生命周期注册表 ─────────────────────────
   * id → { module, openName, overlayId, modeClass, btnId, host }
   * - module/openName : 程序化打开入口（init 时会被包裹以统一记录状态）
   * - overlayId       : 该面板在 OverlayManager 栈中的 id（用于 isOpen / close）
   * - modeClass       : 以 body class 表达的面板模式（sysmon/term 等）
   * - btnId           : 以按钮点击驱动的入口（天气/简报等无 ZZ 全局者）
   * - host            : 是否复用共享 zz-panel 容器（同容器内容互斥）
   */
  var REG = {
    'weather':       { btnId: 'wxOpenBtn', overlayId: 'zz-panel', host: true },
    'briefing':      { btnId: 'btnBriefing', overlayId: 'zz-panel', host: true },
    'memory':        { module: 'JZMemory', openName: 'open', overlayId: 'jz-memory' },
    'ai-memory':     { module: 'ZZMemory', openName: 'open', overlayId: 'memory' },
    'memory-query':  { module: 'ZZMemoryQuery', openName: 'open', overlayId: 'memory-query' },
    'settings':      { module: 'ZZSettings', openName: 'open', overlayId: 'settings' },
    'hotspot':       { module: 'ZZHotspot', openName: 'open', overlayId: 'hotspot' },
    'sysmon':        { module: 'ZZSysmon', openName: 'open', modeClass: 'sysmon-mode' },
    'terminal':      { module: 'ZZTerminal', openName: 'open', modeClass: 'term-mode' },
    'doc':           { module: 'ZZDoc', openName: 'open', overlayId: 'doc' },
    'knowledge':     { module: 'ZZKnowledge', openName: 'open', overlayId: 'knowledge' },
    'map':           { module: 'ZZMap', openName: 'open', overlayId: 'map' },
    'capabilities':  { module: 'ZZCapabilities', openName: 'open', overlayId: 'capabilities-view' },
    'sysprompt':     { module: 'ZZSysPrompt', openName: 'open', overlayId: 'sysprompt' },
    'review':        { module: 'ZZReview', openName: 'open', overlayId: 'review' },
    'video':         { module: 'ZZVideo', openName: 'open', overlayId: 'video' },
    'tasks':         { module: 'ZZTasks', openName: 'open', overlayId: 'zz-task' },
    'agent-profile': { module: 'ZZPanel', openName: 'profile', overlayId: 'zz-panel', host: true },
    'memory-center':     { module: 'ZZMemoryCenter', openName: 'open', overlayId: 'memory-center' },
    'aboutme':           { module: 'ZZAboutMe', openName: 'open', overlayId: 'aboutme' },
    'capability-center': { module: 'ZZCapabilityCenter', openName: 'open', overlayId: 'capability-center' },
    'self-awareness':    { module: 'ZZSelfAwareness', openName: 'open', overlayId: 'self-awareness' },
    'execution':         { module: 'ZZExecution', openName: 'open', overlayId: 'execution' }
  };

  var _collapseState = {};     // id -> { region: bool }
  var _collapseRegions = {};   // 'id:region' -> { el, cls }
  var ready = false;

  function _recordOpen(id) {
    WorkspaceState.focus(id);
  }
  function _recordClose(id) {
    WorkspaceState.clearFocus(id);
  }

  var PanelManager = {
    WorkspaceState: WorkspaceState,
    ready: false,

    /* —— 初始化：包裹模块 open/close 以统一记录状态；绑定按钮入口 —— */
    init: function () {
      if (ready) return;
      WorkspaceState.load();
      Object.keys(REG).forEach(function (id) {
        var e = REG[id];
        if (e.module && !e.btnId) {
          var mod = window[e.module];
          if (mod) {
            var fnName = e.openName || 'open';
            if (typeof mod[fnName] === 'function') {
              var orig = mod[fnName];
              mod[fnName] = function () {
                var r = orig.apply(mod, arguments);
                _recordOpen(id);
                return r;
              };
            }
            if (typeof mod.close === 'function') {
              var oc = mod.close;
              mod.close = function () {
                var r = oc.apply(mod, arguments);
                _recordClose(id);
                return r;
              };
            }
          }
        }
      });
      // 按钮驱动的入口：点击即记录工作区状态
      [['wxOpenBtn', 'weather'], ['btnBriefing', 'briefing'], ['hsOpenBtn', 'hotspot'], ['btnMem', 'memory'], ['settingsOpenBtn', 'settings']]
        .forEach(function (p) {
          var el = document.getElementById(p[0]);
          if (el) el.addEventListener('click', function () { _recordOpen(p[1]); });
        });
      ready = true;
      this.ready = true;
    },

    /* —— 唯一入口分发器：任何代码路径打开能力均经此 —— */
    openCapability: function (id) {
      var e = REG[id];
      if (!e) { console.warn('[PanelManager] 未注册面板:', id); return; }
      var args = Array.prototype.slice.call(arguments, 1);
      if (e.btnId) {
        var b = document.getElementById(e.btnId);
        if (b) b.click();
        _recordOpen(id);
      } else if (e.module && window[e.module]) {
        var mod = window[e.module];
        var fn = e.openName ? mod[e.openName] : mod.open;
        if (typeof fn === 'function') {
          try { fn.apply(mod, args); } catch (_) {}
          _recordOpen(id);
        }
      }
    },

    /* —— 生命周期：open / close / hide / restore / focus / pin / unpin / collapse / expand / toggle —— */
    open: function (id) { this.openCapability(id); },
    close: function (id) {
      var e = REG[id]; if (!e) return;
      var mod = e.module && window[e.module];
      if (mod && typeof mod.close === 'function') { try { mod.close(); } catch (_) {} }
      else if (e.overlayId && window.OverlayManager && window.OverlayManager.isOpen(e.overlayId)) window.OverlayManager.close(e.overlayId);
      else if (e.modeClass) document.body.classList.remove(e.modeClass);
      _recordClose(id);
    },
    // hide = 视觉收起但保留最近记录（语义上等同于 close，面板为模态/独占型）
    hide: function (id) { this.close(id); },
    // restore = 重新打开（用于固定面板恢复）
    restore: function (id) { this.open(id); },
    focus: function (id) { WorkspaceState.focus(id); },
    pin: function (id) {
      WorkspaceState.pin(id);
      this._applyPinChrome(id, true);
    },
    unpin: function (id) {
      WorkspaceState.unpin(id);
      this._applyPinChrome(id, false);
    },
    togglePin: function (id) {
      if (WorkspaceState.isPinned(id)) this.unpin(id); else this.pin(id);
      return WorkspaceState.isPinned(id);
    },
    collapse: function (id, region) {
      var set = _collapseState[id] || (_collapseState[id] = {});
      set[region] = !set[region];
      var reg = _collapseRegions[id + ':' + region];
      if (reg && reg.el && reg.cls) {
        var el = typeof reg.el === 'function' ? reg.el() : reg.el;
        if (el) el.classList.toggle(reg.cls, set[region]);
      }
      WorkspaceState.save();
      return set[region];
    },
    expand: function (id, region) {
      var set = _collapseState[id] || (_collapseState[id] = {});
      set[region] = false;
      var reg = _collapseRegions[id + ':' + region];
      if (reg && reg.el && reg.cls) {
        var el = typeof reg.el === 'function' ? reg.el() : reg.el;
        if (el) el.classList.remove(reg.cls);
      }
      WorkspaceState.save();
    },
    toggle: function (id) { this.isOpen(id) ? this.close(id) : this.open(id); },

    /* —— 查询 —— */
    isOpen: function (id) {
      var e = REG[id]; if (!e) return false;
      if (e.overlayId && window.OverlayManager && window.OverlayManager.isOpen(e.overlayId)) return true;
      if (e.modeClass) return document.body.classList.contains(e.modeClass);
      var mod = e.module && window[e.module];
      if (mod && typeof mod.isOpen === 'function') return mod.isOpen();
      return false;
    },
    isPinned: function (id) { return WorkspaceState.isPinned(id); },
    isCollapsed: function (id, region) {
      var set = _collapseState[id]; return !!(set && set[region]);
    },
    focused: function () { return WorkspaceState.data.focusedPanelId; },
    pinned: function () { return WorkspaceState.data.pinnedPanelIds.slice(); },
    recent: function (n) {
      var r = WorkspaceState.data.recentPanelIds;
      return typeof n === 'number' ? r.slice(0, n) : r.slice();
    },
    list: function () { return Object.keys(REG); },
    getState: function () { return { focused: WorkspaceState.data.focusedPanelId, pinned: this.pinned(), recent: this.recent() }; },

    /* —— 关闭全部（指令中心「关闭所有面板」统一入口）—— */
    closeAll: function () {
      Object.keys(REG).forEach(function (id) {
        if (PanelManager.isOpen(id)) PanelManager.close(id);
      });
      if (window.OverlayManager && typeof window.OverlayManager.closeAll === 'function') {
        window.OverlayManager.closeAll();
      }
      WorkspaceState.data.focusedPanelId = null;
      WorkspaceState.save();
    },

    /* —— 折叠区域注册（面板把自身折叠区域交给管理器，自身不再存工作区状态）—— */
    registerCollapse: function (id, region, opts) {
      _collapseRegions[id + ':' + region] = opts || {};
    },

    /* —— 活动上下文（仅存引用 id；域真相归 AppState）—— */
    setActiveContext: function (ctx) { WorkspaceState.setActiveContext(ctx); },
    getActiveContext: function () { return WorkspaceState.getActiveContext(); },

    _applyPinChrome: function (id, on) {
      var e = REG[id]; if (!e || !e.overlayId) return;
      // 复用 OverlayManager.getHandle（既有 API，返回 { id, el, dialog, close }），不新增第二套查询。
      if (window.OverlayManager && typeof window.OverlayManager.getHandle === 'function') {
        var h = window.OverlayManager.getHandle(e.overlayId);
        var el = h && h.el;
        if (el) el.classList.toggle('ws-pinned', on);
      }
    }
  };

  window.PanelManager = PanelManager;
  window.WorkspaceState = WorkspaceState;
})();
