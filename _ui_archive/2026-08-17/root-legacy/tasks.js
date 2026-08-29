// 小6 · 科技感右侧任务弹窗系统
// 统一承载「做什么任务」的半透明玻璃拟态对话框，从右侧滑入。
const ZZTasks = (() => {
  let root = null;
  let overlay = null;
  let bodyEl = null;
  let titleEl = null;
  let activeKind = null;

  const TASK_TITLES = {
    weather: '天气观测',
    hotspot: '热点追踪',
    sysmon: '系统监控',
    terminal: '终端日志',
    sysprompt: '系统提示词',
    capabilities: '能力清单',
  };

  function ensureRoot() {
    if (root) return root;
    overlay = document.createElement('div');
    overlay.className = 'zz-task-overlay';
    overlay.addEventListener('click', close);

    root = document.createElement('aside');
    root.className = 'zz-task-panel';
    root.setAttribute('aria-hidden', 'true');
    root.innerHTML = `
      <div class="zz-task-hud" aria-hidden="true">
        <span class="zz-task-corner tl"></span>
        <span class="zz-task-corner tr"></span>
        <span class="zz-task-corner bl"></span>
        <span class="zz-task-corner br"></span>
        <div class="zz-task-scanline"></div>
      </div>
      <div class="zz-task-head">
        <div class="zz-task-title-wrap">
          <span class="zz-task-dot"></span>
          <span class="zz-task-title" id="zzTaskTitle">TASK</span>
          <span class="zz-task-sub" id="zzTaskSub">READY</span>
        </div>
        <button class="zz-task-close" id="zzTaskClose" title="关闭 (Esc)"><svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-close"/></svg></button>
      </div>
      <div class="zz-task-body" id="zzTaskBody"></div>
    `;
    document.body.appendChild(overlay);
    document.body.appendChild(root);

    root.querySelector('#zzTaskClose').addEventListener('click', close);

    titleEl = document.getElementById('zzTaskTitle');
    bodyEl = document.getElementById('zzTaskBody');
    return root;
  }

  function open(kind, title, html) {
    ensureRoot();
    kind = kind || 'task';
    activeKind = kind;
    titleEl.textContent = title || TASK_TITLES[kind] || 'TASK';
    document.getElementById('zzTaskSub').textContent = String(kind).toUpperCase();
    bodyEl.innerHTML = html || '';
    overlay.classList.add('show');
    root.classList.add('show');
    root.setAttribute('aria-hidden', 'false');
    document.body.classList.add('zz-task-mode');
    root.classList.add('zz-task-booting');
    setTimeout(() => root.classList.remove('zz-task-booting'), 700);
    if (window.OverlayManager) {
      window.OverlayManager.track('zz-task', {
        el: root,
        onClose: _closeVisual,
        type: window.OverlayManager.OverlayType.PANEL,
        trap: false,
        autofocus: false
      });
    }
  }

  function _closeVisual() {
    if (overlay) overlay.classList.remove('show');
    if (root) {
      root.classList.remove('show');
      root.setAttribute('aria-hidden', 'true');
    }
    document.body.classList.remove('zz-task-mode');
    activeKind = null;
  }
  function close() {
    if (window.OverlayManager && window.OverlayManager.isOpen('zz-task')) {
      window.OverlayManager.close('zz-task');
    } else {
      _closeVisual();
    }
  }

  function isOpen() {
    return !!activeKind;
  }

  // 启动已有的独立面板（如系统监控、终端等），同时给出科技感过渡提示
  function launch(kind) {
    const title = TASK_TITLES[kind] || kind;
    const map = {
      sysmon: { fn: () => { if (window.PanelManager) PanelManager.openCapability('sysmon'); else if (window.ZZSysmon) window.ZZSysmon.open(); } },
      terminal: { fn: () => { if (window.PanelManager) PanelManager.openCapability('terminal'); else if (window.ZZTerminal) window.ZZTerminal.open(); } },
      sysprompt: { fn: () => { if (window.PanelManager) PanelManager.openCapability('sysprompt'); else if (window.ZZSysPrompt) window.ZZSysPrompt.open(); } },
      capabilities: { fn: () => { if (window.PanelManager) PanelManager.openCapability('capabilities'); else if (window.ZZCapabilities) window.ZZCapabilities.open(); } },
    };
    const target = map[kind];
    const run = () => {
      if (target?.fn) target.fn();
    };
    open(kind, title, `
      <div class="zz-task-launch">
        <div class="zz-task-launch-icon">${iconFor(kind)}</div>
        <div class="zz-task-launch-title">${title}</div>
        <div class="zz-task-launch-desc">正在打开 ${title} 模块…</div>
        <button class="zz-task-launch-btn" id="zzTaskLaunchBtn">立即启动</button>
      </div>
    `);
    bodyEl.querySelector('#zzTaskLaunchBtn')?.addEventListener('click', () => {
      close();
      setTimeout(run, 180);
    });
    // 自动启动：弹窗出现 400ms 后自动打开目标面板
    setTimeout(() => {
      if (activeKind === kind) {
        close();
        setTimeout(run, 180);
      }
    }, 420);
  }

  function iconFor(kind) {
    const icons = {
      weather: '<svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-weather"/></svg>', hotspot: '<svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-signal"/></svg>', sysmon: '<svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-monitor"/></svg>', terminal: '<svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-scroll"/></svg>',
      sysprompt: '<svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-receipt"/></svg>', capabilities: '<svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-puzzle"/></svg>',
    };
    return icons[kind] || '◈';
  }

  return { open, close, launch, isOpen };
})();

if (typeof window !== 'undefined') window.ZZTasks = ZZTasks;
