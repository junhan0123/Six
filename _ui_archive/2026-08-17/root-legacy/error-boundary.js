// error-boundary.js — 全局错误兜底，避免单点未捕获异常导致整页白
// 作为普通脚本最先执行，确保即使后续模块加载失败也能兜住。
(function () {
  'use strict';

  function toast(msg, kind) {
    // Step[3] 统一路由：优先 OverlayManager.toast（调用时 OverlayManager 已在后续脚本中加载）；
    // 缺失时回退原有 DOM toast，保持全局兜底能力不变。
    if (window.OverlayManager && typeof window.OverlayManager.toast === 'function') {
      window.OverlayManager.toast({
        type: kind === 'warn' ? 'warning' : 'error',
        message: msg,
        legacyDismissMs: 6000
      });
      return;
    }
    // —— 以下为原有兼容回退，保持不动 ——
    let el = document.getElementById('zz-error-toast');
    if (!el) {
      el = document.createElement('div');
      el.id = 'zz-error-toast';
      el.setAttribute('role', 'alert');
      el.style.cssText =
        'position:fixed;left:50%;bottom:24px;transform:translateX(-50%);z-index:99999;' +
        'max-width:82vw;background:rgba(20,20,28,.94);color:#fca5a5;' +
        'border:1px solid rgba(252,165,165,.4);padding:10px 16px;border-radius:12px;' +
        'font:13px/1.5 system-ui,-apple-system,sans-serif;backdrop-filter:blur(10px);' +
        'box-shadow:0 8px 30px rgba(0,0,0,.45);opacity:0;transition:opacity .3s;pointer-events:none;';
      (document.body || document.documentElement).appendChild(el);
    }
    // 网络/连接类错误用更温和的琥珀色，避免"红色报错"惊扰用户
    if (kind === 'warn') {
      el.style.color = '#f5b544';
      el.style.borderColor = 'rgba(245,181,68,.45)';
    } else {
      el.style.color = '#fca5a5';
      el.style.borderColor = 'rgba(252,165,165,.4)';
    }
    el.textContent = msg;
    el.style.opacity = '1';
    clearTimeout(el._t);
    el._t = setTimeout(function () { el.style.opacity = '0'; }, 6000);
  }

  window.ZZErrorToast = toast;

  // 判断是否为网络/连接类错误：后端重启、离线、网络抖动、请求被中断等。
  // 这类错误不该作为"程序报错"惊扰用户，应静默并交给后台自动重连。
  function isNetworkError(r) {
    if (!r) return false;
    const name = String((r && r.name) || '').toLowerCase();
    const msg = String((r && r.message) || (typeof r === 'string' ? r : '')).toLowerCase();
    if (name === 'typeerror' && /fetch|network|load|abort/i.test(msg)) return true; // fetch 失败在 Chromium 下抛 TypeError
    return /network|failed to fetch|net::err|load failed|timeout|abort|connection|econn|socket hang|request failed/i.test(msg);
  }

  // 网络错误去抖：30s 内最多轻提示一次，避免后端重启/离线时红色 toast 刷屏
  let lastNetToast = 0;
  const NET_THROTTLE_MS = 30000;

  window.addEventListener('error', function (e) {
    var msg = (e && e.message) || '未知脚本错误';
    // 完整堆栈输出到控制台便于排查
    console.error('[global error]', msg, '\n  at', (e && e.filename) + ':' + (e && e.lineno) + ':' + (e && e.colno), '\nstack:', e && e.error && e.error.stack);
    toast('界面出了点小问题（已记录）：' + msg);
  });

  window.addEventListener('unhandledrejection', function (e) {
    var r = e && e.reason;
    var msg = (r && r.message) || (typeof r === 'string' ? r : '异步任务异常');
    // 完整堆栈输出到控制台便于排查
    console.error('[unhandledrejection]', r, '\nstack:', r && r.stack);
    if (isNetworkError(r)) {
      var now = Date.now();
      if (now - lastNetToast > NET_THROTTLE_MS) {
        lastNetToast = now;
        toast('网络暂时不可用（后台会自动重连）：' + msg, 'warn');
      }
      return; // 限频窗口内不再重复提示
    }
    toast('后台任务出错（已记录）：' + msg);
  });
})();
