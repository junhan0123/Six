/* ═════════════════════════════════════════════════════════════════
   Xiao6 UI-R1 · approval.js — 审批卡（Phase 2 + RC2 truthful 修复）
   统一双通道：chat SSE 的 xiao6_event:approval + /api/stream 的 modal(kind=agent_approval)
   冻结契约：ticket 解析 m.ticket || m.approval.ticket
             POST /api/agent/approval?ticket=<t>&decision=approve|reject（query 参数）
   RC2：审批结果必须 truthful —— 只有 HTTP ok 且后端 {ok:true} 才显示成功；
        网络错误/4xx/5xx/ticket 过期一律「提交失败 · 请重试」并恢复按钮，禁止假成功。
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
    card.dataset.ticket = ticket || '';
    card.dataset.desc = desc;
    card.innerHTML = '<div>' + esc(desc) + '</div>';
    var acts = el('div', 'xiao6-approval-act');
    var ok = el('button', 'approve', '批准'); var no = el('button', 'reject', '拒绝');
    acts.appendChild(ok); acts.appendChild(no); card.appendChild(acts);
    cn.bub.appendChild(card);
    ok.addEventListener('click', function () { postApproval(ticket, 'approve', card); });
    no.addEventListener('click', function () { postApproval(ticket, 'reject', card); });
    window.Xiao6.main.toast('有一项操作需要确认');
  }

  // ───────────────────── 审批提交（query 参数冻结；truthful 判定）─────────────────────
  function postApproval(ticket, decision, card) {
    if (!ticket) { renderApprovalError(card, ticket); return; }
    fetch('/api/agent/approval?ticket=' + encodeURIComponent(ticket) + '&decision=' + decision, { method: 'POST' })
      .then(function (r) {
        return r.json()
          .then(function (d) { return { ok: r.ok, data: d }; })
          .catch(function () { return { ok: false, data: null }; });
      })
      .then(function (res) {
        if (res.ok && res.data && res.data.ok === true) {
          if (card) card.innerHTML = '<div>已' + (decision === 'approve' ? '批准' : '拒绝') + '</div>';
          window.Xiao6.main.toast(decision === 'approve' ? '已批准' : '已拒绝');
        } else {
          renderApprovalError(card, ticket);
        }
      })
      .catch(function () { renderApprovalError(card, ticket); });
  }

  // 失败：显示「提交失败 · 请重试」+ 恢复按钮（truthful，禁止假成功）
  function renderApprovalError(card, ticket) {
    if (!card) return;
    var desc = card.dataset.desc || '';
    card.innerHTML = '<div style="color:var(--xiao6-danger)">提交失败 · 请重试</div><div>' + esc(desc) + '</div>';
    var acts = el('div', 'xiao6-approval-act');
    var ok = el('button', 'approve', '批准'); var no = el('button', 'reject', '拒绝');
    acts.appendChild(ok); acts.appendChild(no); card.appendChild(acts);
    ok.addEventListener('click', function () { postApproval(ticket, 'approve', card); });
    no.addEventListener('click', function () { postApproval(ticket, 'reject', card); });
    window.Xiao6.main.toast('提交失败 · 请重试', 'err');
  }

  window.Xiao6.approval = { renderApprovalCard: renderApprovalCard, postApproval: postApproval };
})();
