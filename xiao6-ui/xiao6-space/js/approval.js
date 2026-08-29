/* ═════════════════════════════════════════════════════════════════
   Xiao6 UI-R1 · approval.js — 审批卡（Phase 2）
   统一双通道：chat SSE 的 xiao6_event:approval + /api/stream 的 modal(kind=agent_approval)
   冻结契约：ticket 解析 m.ticket || m.approval.ticket
            POST /api/agent/approval?ticket=<t>&decision=approve|reject（query 参数）
   ═════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';
  window.Xiao6 = window.Xiao6 || {};

  function el(tag, cls, txt) { var n = document.createElement(tag); if (cls) n.className = cls; if (txt != null) n.textContent = txt; return n; }
  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  // ───────────────────── 统一审批卡渲染（chat SSE + /api/stream 双通道）─────────────────────
  function renderApprovalCard(m) {
    m = m || {};
    var ticket = m.ticket || (m.approval && m.approval.ticket);
    var desc = m.prompt || (m.approval && m.approval.prompt) || m.summary || ('有一项操作需要确认' + (m.tool ? '（' + m.tool + '）' : ''));

    var state = window.Xiao6.state;
    state.agentLog.unshift({ kind: 'approval', t: Date.now(), text: '等待确认：' + (m.tool || '') + ' · ' + desc });
    state.notify();

    var cn = window.Xiao6.timeline.addNode('approval');
    var card = el('div', 'xiao6-approval-card');
    card.innerHTML = '<div>' + esc(desc) + '</div>';
    var acts = el('div', 'xiao6-approval-act');
    var ok = el('button', 'approve', '批准'); var no = el('button', 'reject', '拒绝');
    acts.appendChild(ok); acts.appendChild(no); card.appendChild(acts);
    cn.bub.appendChild(card);
    ok.addEventListener('click', function () { postApproval(ticket, 'approve', card); });
    no.addEventListener('click', function () { postApproval(ticket, 'reject', card); });
    window.Xiao6.main.toast('有一项操作需要确认');
  }

  // ───────────────────── 审批提交（query 参数冻结）─────────────────────
  function postApproval(ticket, decision, card) {
    if (ticket) fetch('/api/agent/approval?ticket=' + encodeURIComponent(ticket) + '&decision=' + decision, { method: 'POST' }).catch(function () {});
    if (card) card.innerHTML = '<div>已' + (decision === 'approve' ? '批准' : '拒绝') + '</div>';
    window.Xiao6.main.toast(decision === 'approve' ? '已批准' : '已拒绝');
  }

  window.Xiao6.approval = { renderApprovalCard: renderApprovalCard, postApproval: postApproval };
})();
