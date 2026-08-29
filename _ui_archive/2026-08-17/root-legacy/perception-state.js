/*
 * perception-state.js — 小6 Phase 8 MVP · Perception 纯投影层（非视觉）
 * ----------------------------------------------------------------------------
 * 职责：把 PERCEPTION_* 事件投影为"用户当前看到的世界"状态。
 * 纪律（严格对齐 computer-state.js / app-state.js 唯一写入口纪律）：
 *   - 本文件绝不触碰 UI / Three.js / WebGL / Overlay；只维护纯数据。
 *   - 纯投影：只读、不 emit；数据单向派生自 AppState('*') 事件流。
 *   - 不得写 AppState（无 state.perception 子树、无 reducer）；只维护本地投影。
 *   - 订阅 AppState('*') 重建本地投影（PERCEPTION_* 事件即使无 reducer 仍被 emit）。
 * 可在 Node 中单测（不依赖 window）。
 */
(function (global) {
  'use strict';
  var AppState = global.AppState;

  // 本地投影（不写入 AppState；AppState 仅作为事件来源）
  var data = {
    screenId: null,
    monitors: [],
    focusedElement: null,
    uiTree: null,
    ocrSpans: [],
    visionFacts: [],
    mergedText: [],
    lastUpdated: 0,
    ttl: 0
  };
  var subs = [];

  function applyPerception(name, payload) {
    if (name === 'PERCEPTION_SYNC') {
      var p = payload && payload.perception;
      if (!p) return;
      if (p.screenId != null) data.screenId = p.screenId;
      if (p.monitors) data.monitors = p.monitors;
      if (p.focusedElement !== undefined) data.focusedElement = p.focusedElement;
      if (p.uiTree !== undefined) data.uiTree = p.uiTree;
      if (p.ocrSpans) data.ocrSpans = p.ocrSpans;
      if (p.visionFacts) data.visionFacts = p.visionFacts;
      if (p.mergedText) data.mergedText = p.mergedText;
      if (p.lastUpdated != null) data.lastUpdated = p.lastUpdated;
      if (p.ttl != null) data.ttl = p.ttl;
    } else if (name === 'PERCEPTION_UI_UPDATED') {
      if (payload && payload.elementId) {
        data.focusedElement = {
          elementId: payload.elementId,
          windowId: payload.windowId || null,
          role: payload.role || null,
          name: payload.name || null
        };
      }
    } else if (name === 'PERCEPTION_OCR_UPDATED') {
      if (payload && payload.spanId) {
        var replaced = false;
        for (var i = 0; i < data.ocrSpans.length; i++) {
          if (data.ocrSpans[i].spanId === payload.spanId) {
            data.ocrSpans[i] = payload; replaced = true; break;
          }
        }
        if (!replaced) data.ocrSpans.push(payload);
      }
    } else if (name === 'PERCEPTION_VISION_FACT') {
      if (payload && payload.factId) {
        var rep = false;
        for (var j = 0; j < data.visionFacts.length; j++) {
          if (data.visionFacts[j].factId === payload.factId) {
            data.visionFacts[j] = payload; rep = true; break;
          }
        }
        if (!rep) data.visionFacts.push(payload);
      }
    } else if (name === 'PERCEPTION_FOCUS_CHANGED') {
      if (payload) {
        data.focusedElement = {
          elementId: payload.elementId || null,
          windowId: payload.windowId || null,
          role: payload.role || null,
          name: payload.name || null
        };
      }
    } else {
      return;
    }
  }

  function snapshot(d) {
    try { return JSON.stringify(d); } catch (e) { return ''; }
  }

  function notify() {
    for (var i = 0; i < subs.length; i++) subs[i](data);
  }

  var unsub = AppState.subscribe('*', function (evt) {
    if (!evt || !evt.name) return;
    var before = snapshot(data);
    applyPerception(evt.name, evt.payload);
    if (snapshot(data) !== before) notify();   // 仅在确有变化时通知（避免噪声）
  });

  var API = {
    // —— 整感知快照 ——
    getPerception: function () { return data; },

    // —— 派生读取（只读观察；无写入口）——
    getFocusedElement: function () { return data.focusedElement; },
    getVisionFacts: function () { return data.visionFacts; },
    getOcrSpans: function () { return data.ocrSpans; },
    getMergedText: function () { return data.mergedText; },

    // —— 订阅（只读观察；无写入口）——
    onPerceptionChange: function (cb) {
      subs.push(cb);
      return function () {
        var i = subs.indexOf(cb);
        if (i >= 0) subs.splice(i, 1);
      };
    },

    _unsub: unsub
  };

  global.PerceptionState = API;
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
})(typeof window !== 'undefined' ? window : globalThis);
