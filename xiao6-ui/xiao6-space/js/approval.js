/* ═════════════════════════════════════════════════════════════════
   Xiao6 UI-R1 · approval.js — 审批卡（R1-B：进入 Timeline 唯一真相源）
   双通道统一：/api/stream 的 modal(kind=agent_approval) 与（防御性）chat SSE 的 approval。
   冻结契约：ticket 解析 m.ticket || m.approval.ticket
             POST /api/agent/approval?ticket=<t>&decision=approve|reject（query 参数）
   R1-B 红线：审批单一律经 state.upsertNode 进入 Timeline；提交结果由 patchNode 反映，
   绝对不伪造成功 —— 只有 HTTP ok 且后端 {ok:true} 才置 success/stopped，
   否则保留 blocked + error 提示「提交失败 · 请重试」，按钮仍在，等待重试。
   ═════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';
  window.Xiao6 = window.Xiao6 || {};

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  // ───────────────────── 统一审批卡（进入 Timeline）─────────────────────
  function renderApprovalCard(m) {
    m = m || {};
    var ticket = m.ticket || (m.approval && m.approval.ticket) || '';
    var tool = m.tool || (m.approval && m.approval.tool) || '';
    var summary = m.summary || (m.approval && m.approval.summary) || m.prompt || (m.approval && m.approval.prompt) || '';
    var argsPreview = m.args_preview || m.argsPreview || (m.approval && (m.approval.args_preview || m.approval.argsPreview)) || '';

    // 唯一真相源：审批单作为 timeline 节点（id 由真实 ticket 构成，刷新/重连可去重）
    var state = window.Xiao6.state;
    state.upsertNode({
      id: 'approval:' + (ticket || ('pending:' + Date.now())),
      type: 'approval', status: 'blocked',
      ticket: ticket, tool: tool, summary: summary, argsPreview: argsPreview,
      timestamp: Date.now()
    });
    state.notify();

    if (window.Xiao6.main && window.Xiao6.main.toast) window.Xiao6.main.toast('有一项操作需要确认');
  }

  // ───────────────────── 审批提交（query 参数冻结；truthful 判定）─────────────────────
  function postApproval(ticket, decision, card) {
    if (!ticket) { patchError(ticket, '缺少 ticket，无法提交'); return; }
    fetch('/api/agent/approval?ticket=' + encodeURIComponent(ticket) + '&decision=' + decision, { method: 'POST' })
      .then(function (r) {
        return r.json()
          .then(function (d) { return { ok: r.ok, data: d }; })
          .catch(function () { return { ok: false, data: null }; });
      })
      .then(function (res) {
        if (res.ok && res.data && res.data.ok === true) {
          // 只有后端确认 {ok:true} 才改变终态（truthful：不假成功）
          var state = window.Xiao6.state;
          state.patchNode('approval:' + ticket, { status: decision === 'approve' ? 'success' : 'stopped', error: undefined });
          if (window.Xiao6.main && window.Xiao6.main.toast)
            window.Xiao6.main.toast(decision === 'approve' ? '已批准' : '已拒绝');
          state.notify();
        } else {
          patchError(ticket, '提交失败 · 请重试');
        }
      })
      .catch(function () { patchError(ticket, '提交失败 · 请重试'); });
  }

  // 失败：保留 blocked 状态（按钮仍在），仅附加错误提示，绝对不假成功
  function patchError(ticket, msg) {
    var state = window.Xiao6.state;
    if (ticket) state.patchNode('approval:' + ticket, { status: 'blocked', error: msg });
    if (window.Xiao6.main && window.Xiao6.main.toast) window.Xiao6.main.toast(msg, 'err');
    state.notify();
  }

  window.Xiao6.approval = { renderApprovalCard: renderApprovalCard, postApproval: postApproval };
})();
