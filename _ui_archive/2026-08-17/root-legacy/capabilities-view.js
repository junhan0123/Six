// 小6 · 能力清单视图（2.0）
// 一键查看小6当前已注册的能力：按分组呈现、卡片可展开看「工作原理」、
// 「试一试」把样本问句填入输入框并直接发送；打开时轻量轮询实时激活状态。

function initCapabilitiesView() {
  const overlay = document.getElementById('capOverlay');
  const panel = document.getElementById('capPanel');
  const openBtn = document.getElementById('capOpenBtn');
  const closeBtn = document.getElementById('capClose');
  const refreshBtn = document.getElementById('capRefresh');
  const bodyEl = document.getElementById('capBody');
  const metaEl = document.getElementById('capMeta');

  const state = { items: [], loaded: false, expanded: new Set(), pollTimer: null };

  function open() {
    overlay.classList.add('show');
    panel.classList.add('open');
    openBtn?.classList.add('active');
    if (!state.loaded) load();
    startPolling();
    // Sprint 1/2：登记到 OverlayManager（统一 ESC / 焦点 / 栈）
    if (window.OverlayManager) {
      window.OverlayManager.track('capabilities-view', { el: overlay, onClose: closeImpl, type: window.OverlayManager.OverlayType.PANEL, trap: false });
    }
  }
  function closeImpl() {
    overlay.classList.remove('show');
    panel.classList.remove('open');
    openBtn?.classList.remove('active');
    stopPolling();
  }
  function close() {
    if (window.OverlayManager && window.OverlayManager.isOpen('capabilities-view')) {
      window.OverlayManager.close('capabilities-view');   // 触发 onClose + 出栈 + 焦点恢复
    } else {
      closeImpl();
    }
  }

  function startPolling() {
    stopPolling();
    state.pollTimer = setInterval(refreshStatus, 20000);
  }
  function stopPolling() {
    if (state.pollTimer) { clearInterval(state.pollTimer); state.pollTimer = null; }
  }

  // 数据源：ZZCapabilities（前端注册表，无 REST 直连，符合"数据来自 AppState/本地投影"纪律）
  //   + 实时激活态由 ExecutionChannel / AppState 派生。
  function liveActiveIds() {
    const ids = new Set();
    const ex = (window.ExecutionChannel) ? window.ExecutionChannel.getCurrent() : null;
    if (ex && ex.steps) ex.steps.forEach((s) => { if (s && s.tool) ids.add(s.tool); });
    const st = (window.AppState && window.AppState.getState) ? window.AppState.getState() : {};
    if (st.computer && st.computer.actions) {
      Object.keys(st.computer.actions).forEach((k) => ids.add(st.computer.actions[k].capability));
    }
    return ids;
  }

  function load() {
    bodyEl.innerHTML = '<div class="cap-loading">加载中…</div>';
    metaEl.textContent = '';
    const caps = (window.ZZCapabilities && window.ZZCapabilities.allCapabilities)
      ? window.ZZCapabilities.allCapabilities() : [];
    const live = liveActiveIds();
    state.items = caps.map((c) => ({
      id: c.id,
      label: c.label,
      description: c.expected_effect || '',
      group: (c.risk === 'LOW') ? '只读' : (c.risk === 'MEDIUM') ? '需确认' : '高危',
      triggers: [c.target_kind || ''].filter(Boolean),
      how: '风险等级 ' + c.risk + '；' + (c.implemented === false ? '（规划中）' : '已接入 Policy Engine 裁决'),
      icon: (c.risk === 'LOW') ? '<svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-search"/></svg>' : (c.risk === 'MEDIUM') ? '<svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-wrench"/></svg>' : '<svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-warning"/></svg>',
      active: live.has(c.id)
    }));
    state.loaded = true;
    render();
  }

  // 轻量刷新：只更新各卡片的激活徽标，不重建 DOM（保留展开态）
  function refreshStatus() {
    if (!panel.classList.contains('open')) return;
    const live = liveActiveIds();
    if (!state.items.length) return;
    let active = 0;
    state.items.forEach((c) => { c.active = live.has(c.id); if (c.active) active++; });
    bodyEl.querySelectorAll('.cap-card').forEach((el) => {
      const a = live.has(el.getAttribute('data-id'));
      el.classList.toggle('is-active', !!a);
      const st = el.querySelector('.cap-status');
      if (st) {
        st.className = 'cap-status ' + (a ? 'on' : 'off');
        st.textContent = a ? '● 实时注入中' : '○ 可调用';
      }
    });
    metaEl.textContent = '已注册 ' + state.items.length + ' · 实时注入 ' + active;
  }

  function render() {
    const items = state.items;
    if (!items.length) {
      bodyEl.innerHTML = '<div class="cap-loading">暂无可用的能力</div>';
      return;
    }
    const active = items.filter((c) => c.active).length;
    metaEl.textContent = '已注册 ' + items.length + ' · 实时注入 ' + active;

    // 按 group 分组
    const groups = {};
    items.forEach((c) => {
      const g = c.group || '其他';
      (groups[g] = groups[g] || []).push(c);
    });

    let html = '';
    Object.keys(groups).forEach((g) => {
      html += '<section class="cap-group">';
      html += '<div class="cap-group-title">' + escapeHTML(g) + '</div>';
      html += '<div class="cap-grid">';
      html += groups[g].map(cardHTML).join('');
      html += '</div></section>';
    });
    bodyEl.innerHTML = html;
    bindCards();
  }

  function cardHTML(c) {
    const expanded = state.expanded.has(c.id);
    const chips = (c.triggers || [])
      .map((t) => '<span class="cap-chip">' + escapeHTML(t) + '</span>')
      .join('');
    const sample = (c.triggers && c.triggers[0]) || '介绍一下' + c.label;
    return (
      '<div class="cap-card ' + (c.active ? 'is-active' : '') + (expanded ? ' expanded' : '') +
        '" data-id="' + escapeAttr(c.id) + '" data-sample="' + escapeAttr(sample) + '">' +
        '<div class="cap-card-top">' +
          '<span class="cap-icon">' + (c.icon || '<svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-puzzle"/></svg>') + '</span>' +
          '<div class="cap-card-h">' +
            '<div class="cap-card-title">' + escapeHTML(c.label) + '</div>' +
            '<div class="cap-status ' + (c.active ? 'on' : 'off') + '">' +
              (c.active ? '● 实时注入中' : '○ 可调用') + '</div>' +
          '</div>' +
          '<span class="cap-expand" aria-hidden="true">▾</span>' +
        '</div>' +
        '<p class="cap-desc">' + escapeHTML(c.description || '') + '</p>' +
        (chips ? '<div class="cap-chips">' + chips + '</div>' : '') +
        '<div class="cap-detail">' +
          '<div class="cap-detail-label">工作原理</div>' +
          '<p class="cap-how">' + escapeHTML(c.how || '（暂无说明）') + '</p>' +
        '</div>' +
        '<button class="cap-try" type="button">试一试：' + escapeHTML(sample) + '</button>' +
      '</div>'
    );
  }

  function bindCards() {
    bodyEl.querySelectorAll('.cap-card').forEach((el) => {
      // 点击卡片（排除「试一试」按钮）展开/收起工作原理
      el.addEventListener('click', (e) => {
        if (e.target.closest('.cap-try')) return;
        const id = el.getAttribute('data-id');
        const now = el.classList.toggle('expanded');
        if (now) state.expanded.add(id); else state.expanded.delete(id);
      });
      el.querySelector('.cap-try')?.addEventListener('click', (e) => {
        e.stopPropagation();
        const q = el.getAttribute('data-sample') || '';
        const input = document.getElementById('input');
        if (input) { input.value = q; input.focus(); }
        close();
        document.getElementById('btnSend')?.click();
      });
    });
  }

  function escapeHTML(s) {
    return String(s).replace(/[&<>"']/g, (m) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[m]));
  }
  function escapeAttr(s) { return escapeHTML(s); }

  openBtn?.addEventListener('click', open);
  closeBtn?.addEventListener('click', close);
  refreshBtn?.addEventListener('click', () => {
    state.loaded = false;
    state.expanded.clear();
    load();
  });
  overlay?.addEventListener('click', (e) => { if (e.target === overlay) close(); });
  // ESC 由 OverlayManager 中央处理（关闭栈顶），不再注册去中心化监听

  // UI Consolidation Sprint 修复：此前整体覆盖 window.ZZCapabilities，
  // 销毁了 capability-registry.js 挂载的 allCapabilities()/riskOf()，
  // 导致 capability-matrix.js 能力计数恒为 0、capability-exposure.js 档位失真。
  // 收口：增量挂载 open/close，保留注册表既有 API（不新增能力，不改数据源）。
  window.ZZCapabilities = window.ZZCapabilities || {};
  window.ZZCapabilities.open = open;
  window.ZZCapabilities.close = close;
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initCapabilitiesView);
} else {
  initCapabilitiesView();
}
