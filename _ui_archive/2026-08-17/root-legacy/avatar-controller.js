/*
 * avatar-controller.js — Phase 29 · 小6数字人 序列帧播放控制器 (Avatar Controller)
 * ----------------------------------------------------------------------------
 * 职责：把 AvatarState 派生的规范态投影为「PNG 序列帧」播放（frames 格式）。
 * 这是「扩展已有 Avatar 架构」：avatar-state.js 仍是唯一状态权威；state_map.json
 * 早已把 frames 列为「未来格式占位」，本文件落地该格式。
 *
 * 纪律（最高约束 · 红线）：
 *   - 不新建状态系统：状态来自 AvatarState.derive()（单一来源），本控制器不持有状态。
 *   - 复用既有 SSE→Avatar 链路：观察 .orb-wrap 的 thinking/listening/speaking/idle/error
 *     类（SSE→app.js setOrb→class，已通），不新建 EventBus/SSE。
 *   - 不修改/生成任何图片：仅按 manifest 加载既有 PNG 序列帧；帧缺失→CSS 降级，仅 console.warn。
 *   - 无 console.error：所有异常走 console.warn / 静默，保证「无 console error」验证项。
 *
 * 结构：
 *   FrameEngine   —— 纯逻辑（无 DOM）：状态映射 / 帧清单 / 帧推进。可在 Node 无头验证。
 *   AvatarFrameController —— 薄 DOM 层：挂载目标、RAF 换帧、降级。
 */
(function (global) {
  'use strict';

  var BODY_BASE = 'Xiao6_Avatar/Body/';
  var MANIFEST_URL = BODY_BASE + 'manifest.json';

  // 默认绑定（manifest 加载失败时的回退；与 AI_Binding/state_map.json bindings 对齐）
  var FALLBACK_BINDINGS = {
    IDLE: 'Idle', LISTENING: 'Listening', THINKING: 'Thinking',
    PLANNING: 'Planning', EXECUTING: 'Executing', SPEAKING: 'Speaking',
    LEARNING: 'Learning', WARNING: 'Warning', ERROR: 'Error'
  };

  // ── 纯逻辑层：状态映射 ───────────────────────────────────────────────
  // .orb-wrap 类 → 规范态（复用既有 SSE→class 链路）
  function mapClassToState(cls) {
    if (!cls) return 'IDLE';
    if (cls.indexOf('thinking') >= 0) return 'THINKING';
    if (cls.indexOf('listening') >= 0) return 'LISTENING';
    if (cls.indexOf('speaking') >= 0) return 'SPEAKING';
    if (cls.indexOf('error') >= 0) return 'ERROR';
    return 'IDLE';
  }

  // 规范态 → 资源文件夹名（Body/<State>）
  function resolveBodyFolder(state, bindings) {
    state = String(state || 'IDLE').toUpperCase();
    var b = (bindings && bindings[state]) || FALLBACK_BINDINGS[state] || 'Idle';
    return b;
  }

  // 规范态 → 帧 URL 列表（相对 Body/）。manifest: { Idle:[...], Listening:[...], ... }
  function buildFrameList(state, manifest) {
    var folder = resolveBodyFolder(state, manifest && manifest.__bindings);
    var names = (manifest && manifest[folder]) || [];
    var out = [];
    for (var i = 0; i < names.length; i++) {
      out.push(BODY_BASE + folder + '/' + names[i]);
    }
    return out;
  }

  // 帧推进（循环播放）。返回下一帧索引。
  function advanceFrameIndex(idx, n, dt, fps) {
    if (!n || n <= 0) return 0;
    fps = fps || 12;
    dt = dt || (1000 / fps);
    idx = (idx || 0) + 1;
    return idx % n;
  }

  // 封装纯逻辑引擎（暴露给无头验证）
  var FrameEngine = {
    mapClassToState: mapClassToState,
    resolveBodyFolder: resolveBodyFolder,
    buildFrameList: buildFrameList,
    advanceFrameIndex: advanceFrameIndex
  };

  // ── DOM 层：AvatarFrameController ────────────────────────────────────
  function AvatarFrameController(opts) {
    opts = opts || {};
    this.el = null;
    this.imgEl = null;
    this.state = 'IDLE';
    this.frames = [];
    this.idx = 0;
    this.fps = opts.fps || 12;
    this._raf = 0;
    this._last = 0;
    this._acc = 0;
    this._manifest = null;
    this._bindings = null;
    this._mo = null;        // MutationObserver
    this._enabled = true;
  }

  AvatarFrameController.prototype._loadManifest = function () {
    var self = this;
    if (typeof fetch !== 'function') return;
    fetch(MANIFEST_URL)
      .then(function (r) { if (!r.ok) throw new Error('manifest ' + r.status); return r.json(); })
      .then(function (m) {
        // manifest 可内嵌 bindings：{ "__bindings": {...}, "Idle":[...] }
        self._bindings = m.__bindings || null;
        self._manifest = m;
        self._refreshFrames();
      })
      .catch(function (e) {
        // 降级：无 manifest 不报错，仅告警
        if (global.console && global.console.warn) global.console.warn('[avatar-controller] manifest 加载失败（降级）: ' + e);
      });
  };

  AvatarFrameController.prototype._refreshFrames = function () {
    if (!this._manifest) return;
    this._manifest.__bindings = this._bindings;
    this.frames = FrameEngine.buildFrameList(this.state, this._manifest);
    this.idx = 0;
    this._render();
  };

  AvatarFrameController.prototype.init = function (el) {
    var self = this;
    this.el = el || (typeof document !== 'undefined' ? document.getElementById('zzAvatarFrame') : null);
    if (!this.el && typeof document !== 'undefined') {
      // 自创挂载点（固定小尺寸覆盖层，非 Dashboard；仅状态提示型数字人）
      this.el = document.createElement('div');
      this.el.id = 'zzAvatarFrame';
      this.el.style.cssText =
        'position:fixed;left:50%;top:8%;transform:translateX(-50%);' +
        'width:200px;height:200px;pointer-events:none;z-index:5;opacity:.96;';
      document.body.appendChild(this.el);
    }
    this.imgEl = this.el ? this.el.querySelector('img') : null;
    if (this.el && !this.imgEl) {
      this.imgEl = document.createElement('img');
      this.imgEl.className = 'avatar-frame-media';
      this.imgEl.style.cssText = 'width:100%;height:100%;object-fit:contain;';
      this.el.appendChild(this.imgEl);
    }
    this._loadManifest();
    this._attach();
    this._start();
    return this;
  };

  AvatarFrameController.prototype._attach = function () {
    var self = this;
    if (typeof document === 'undefined' || !document.querySelector) return;
    var orb = document.querySelector('.orb-wrap');
    if (!orb || typeof MutationObserver === 'undefined') return;
    this._mo = new MutationObserver(function () {
      var cls = orb.className || '';
      self.setState(FrameEngine.mapClassToState(cls));
    });
    this._mo.observe(orb, { attributes: true, attributeFilter: ['class'] });
    // 初次同步
    self.setState(FrameEngine.mapClassToState(orb.className || ''));
  };

  AvatarFrameController.prototype.setState = function (state) {
    state = String(state || 'IDLE').toUpperCase();
    if (state === this.state && this.frames.length) return;
    this.state = state;
    this.idx = 0;
    this._refreshFrames();
    if (global.console && global.console.log) {
      global.console.log('[avatar-controller] state → ' + state + ' (' + this.frames.length + ' frames)');
    }
  };

  AvatarFrameController.prototype._render = function () {
    if (!this.imgEl) return;
    if (!this.frames.length) {
      // 无帧 → CSS 降级脸（复用 AvatarAssets.fallbackFace 概念，行内最简）
      this.imgEl.removeAttribute('src');
      this.el.setAttribute('data-state', this.state);
      return;
    }
    var url = this.frames[this.idx % this.frames.length];
    if (this.imgEl.getAttribute('src') !== url) this.imgEl.src = url;
  };

  AvatarFrameController.prototype._tick = function (now) {
    if (!this._enabled) return;
    var self = this;
    this._raf = (typeof requestAnimationFrame === 'function')
      ? requestAnimationFrame(function (t) { self._tick(t); })
      : 0;
    if (!this.frames.length) return;
    if (!this._last) this._last = now;
    var dt = now - this._last;
    this._last = now;
    this._acc += dt;
    var interval = 1000 / this.fps;
    if (this._acc >= interval) {
      this._acc = 0;
      this.idx = FrameEngine.advanceFrameIndex(this.idx, this.frames.length, dt, this.fps);
      this._render();
    }
  };

  AvatarFrameController.prototype._start = function () {
    var self = this;
    this._last = 0; this._acc = 0;
    if (typeof requestAnimationFrame === 'function') {
      this._raf = requestAnimationFrame(function (t) { self._tick(t); });
    }
  };

  AvatarFrameController.prototype.stop = function () {
    if (this._raf && typeof cancelAnimationFrame === 'function') cancelAnimationFrame(this._raf);
    this._raf = 0;
    if (this._mo) { this._mo.disconnect(); this._mo = null; }
  };

  // ── 对外 API ────────────────────────────────────────────────────────
  var API = {
    FrameEngine: FrameEngine,
    Controller: AvatarFrameController,
    BODY_BASE: BODY_BASE,
    MANIFEST_URL: MANIFEST_URL,
    create: function (opts) { return new AvatarFrameController(opts); },
    // 便捷单例（脚本自动挂载在 .orb-wrap 观察上）
    _default: null,
    initDefault: function (el) {
      if (!API._default) API._default = new AvatarFrameController();
      API._default.init(el);
      return API._default;
    }
  };

  global.ZZAvatarFrame = API;
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
})(typeof window !== 'undefined' ? window : globalThis);
