// sse-manager.js — 全局单例 SSE：统一重连与状态广播
// 所有需要服务端推送的模块（主动智能、认知遥测…）都订阅本单例，
// 不再各自开 EventSource，避免：重复长连接、简报双推、重连策略不统一。
(function () {
  'use strict';
  let es = null;
  let retries = 0;
  let state = 'idle';

  function setState(s) {
    if (state === s) return;
    state = s;
    window.dispatchEvent(new CustomEvent('zz:sse-state', { detail: { state: state } }));
  }

  function scheduleReconnect() {
    const delay = Math.min(30000, 1000 * Math.pow(2, retries)); // 指数退避，封顶 30s
    retries++;
    setTimeout(connect, delay);
  }

  function connect() {
    if (typeof EventSource === 'undefined') {
      setState('unsupported');
      return;
    }
    setState(retries === 0 ? 'connecting' : 'reconnecting');
    try {
      es = new EventSource('/api/stream');
    } catch (e) {
      scheduleReconnect();
      return;
    }
    es.onopen = function () {
      retries = 0;
      setState('open');
    };
    es.onmessage = function (ev) {
      if (!ev.data || ev.data.charAt(0) === ':') return; // 心跳/注释行忽略
      window.dispatchEvent(new CustomEvent('zz:sse', { detail: { data: ev.data } }));
    };
    es.onerror = function () {
      // EventSource 出错即断开；手动关闭后按指数退避重连
      try { es.close(); } catch (_) {}
      es = null;
      setState('reconnecting');
      scheduleReconnect();
    };
  }

  window.ZZSSE = {
    start: function () { if (!es) connect(); },
    onMessage: function (cb) {
      window.addEventListener('zz:sse', function (e) { cb(e.detail.data); });
    },
    onState: function (cb) {
      window.addEventListener('zz:sse-state', function (e) { cb(e.detail.state); });
    },
    getState: function () { return state; }
  };

  // 立即启动：EventSource 不依赖 DOM，尽早建连可让后续模块订阅不漏首条推送（如每日简报）
  window.ZZSSE.start();
})();
