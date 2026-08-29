// 小6 · 系统提示词预览
// 参考参考实现"系统提示预览"能力：一键查看当前注入模型的 system prompt 全文，方便调参/调试。

function initSysPrompt() {
  const overlay = document.getElementById('sysPromptOverlay');
  const panel = document.getElementById('sysPromptPanel');
  const openBtn = document.getElementById('spOpenBtn');
  const closeBtn = document.getElementById('sysPromptClose');
  const textEl = document.getElementById('sysPromptText');
  const metaEl = document.getElementById('sysPromptMeta');
  let loaded = false;

  function open() {
    overlay.classList.add('show');
    panel.classList.add('open');
    openBtn?.classList.add('active');
    if (!loaded) load();
    // Sprint 1/2：登记到 OverlayManager（统一 ESC / 焦点 / 栈）
    if (window.OverlayManager) window.OverlayManager.track('sysprompt', { el: overlay, onClose: closeImpl, type: window.OverlayManager.OverlayType.PANEL, trap: false });
  }
  function closeImpl() {
    overlay.classList.remove('show');
    panel.classList.remove('open');
    openBtn?.classList.remove('active');
  }
  function close() {
    if (window.OverlayManager && window.OverlayManager.isOpen('sysprompt')) window.OverlayManager.close('sysprompt');
    else closeImpl();
  }
  function load() {
    textEl.textContent = '加载中…';
    metaEl.textContent = '';
    fetch('/api/system-prompt')
      .then((r) => r.json())
      .then((d) => {
        const p = d.system_prompt || '(空)';
        textEl.textContent = p;
        metaEl.textContent = `字符数 ${p.length} · 行数 ${p.split('\n').length}`;
        loaded = true;
      })
      .catch((e) => {
        textEl.textContent = '加载失败：' + e.message;
      });
  }

  openBtn?.addEventListener('click', open);
  closeBtn?.addEventListener('click', close);
  overlay?.addEventListener('click', (e) => { if (e.target === overlay) close(); });
  // ESC 由 OverlayManager 中央处理（关闭栈顶）

  window.ZZSysPrompt = { open, close };
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initSysPrompt);
} else {
  initSysPrompt();
}
