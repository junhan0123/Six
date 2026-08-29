/* ═════════════════════════════════════════════════════════════════
   Xiao6 UI-R1 · api.js — 唯一网络层（Phase 1）
   迁移自 x6-workspace.js helpers：getJSON / postJSON
   + EventSource 封装（冻结：new EventSource('/api/stream')，禁止 fetch 替代）
   所有 /api/ 字符串集中于此文件
   ═════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';
  window.Xiao6 = window.Xiao6 || {};

  // ───────────────────── JSON GET（静默失败 → null）─────────────────────
  function getJSON(url) {
    return fetch(url, { credentials: 'same-origin' })
      .then(function (r) { return r.ok ? r.json().catch(function () { return null; }) : null; })
      .catch(function () { return null; });
  }

  // ───────────────────── JSON POST（返回解析后 JSON 或 null）─────────────────────
  function postJSON(url, body) {
    return fetch(url, { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}) })
      .then(function (r) { return r.json().catch(function () { return null; }); })
      .catch(function () { return null; });
  }

  // ───────────────────── SSE 实时通道（冻结契约）─────────────────────
  // 必须保持 EventSource 方式；业务事件处理由调用方 onEvent 回调接管（Phase 3 实现）
  function startStream(onEvent) {
    if (!('EventSource' in window)) { console.warn('[Xiao6] EventSource 不可用'); return null; }
    var es = new EventSource('/api/stream');
    es.onmessage = function (e) {
      var m;
      try { m = JSON.parse(e.data); } catch (err) { return; }
      if (onEvent) onEvent(m);
    };
    return es;
  }

  window.Xiao6.api = {
    getJSON: getJSON,
    postJSON: postJSON,
    startStream: startStream,
    // Phase 8 · Trust Layer 事件名（单一来源，供 agent-panel 识别）
    EVENTS: {
      AGENT_INTENT_ANALYZED: 'AGENT_INTENT_ANALYZED',
      TOOL_RISK_CHECKED: 'TOOL_RISK_CHECKED'
    }
  };
})();
