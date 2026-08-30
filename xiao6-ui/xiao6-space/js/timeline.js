/* ═════════════════════════════════════════════════════════════════
   Xiao6 UI-R1-B · timeline.js — 真实 Agent Timeline（Runtime 状态的 UI 投影）

   数据流（单向）：
       真实 API / 真实 SSE  →  state.timeline（唯一视图模型）  →  本模块渲染

   本模块不持有任何独立状态：所有节点一律经 state.upsertNode / state.patchNode。
   渲染是增量的：节点按 id 建立 DOM 映射，只有 _ver 变化才重绘该节点。

   真实契约（已逐字核对代码，未做任何猜测）：
   · POST /api/chat（SSE 风格）
       {"xiao6_event":"tool_start","tool":<name>,"args":<any>}
       {"xiao6_event":"tool_end","tool":<name>,"result":<any>[,"ok":false]}
       {"xiao6_event":"approval",...} / {"choices":[{"delta":{"content":...}}]} / "[DONE]"
     —— chat 通道**没有** execution_id，工具调用在单次请求内串行，
        因此用「请求内 open 栈 + 同名就近闭合」关联，禁止全局同名匹配。
   · GET /api/stream（EventBus）
       SYSTEM 扁平信封 {"xiao6_event":<name>,...fields}
         tool_started  { execution_id, goal_id, task }
         tool_finished { execution_id, goal_id, task, ok }
       —— **有 execution_id**，必须按唯一 ID 关联（并发安全）。
       DOMAIN 信封 {"xiao6_event":<NAME>,"payload":{...},"ts":<unix>}
         GOAL_* / TASK_* / AGENT_*（字段为 camelCase：goalId / taskId / agentId）

   红线：不生成假的执行过程 / 假进度 / 假成功 / 假停止 / 假工具调用。
   ═════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';
  window.Xiao6 = window.Xiao6 || {};
  var state = window.Xiao6.state;

  function $(id) { return document.getElementById(id); }
  function qs(s) { return document.querySelector(s); }
  function qsa(s) { return Array.prototype.slice.call(document.querySelectorAll(s)); }
  function el(tag, cls, txt) { var n = document.createElement(tag); if (cls) n.className = cls; if (txt != null) n.textContent = txt; return n; }
  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
  function fmtTime(ts) { var d = ts ? new Date(String(ts).replace(/-/g, '/')) : new Date(); if (isNaN(d.getTime())) d = new Date(); var p = function (n) { return n < 10 ? '0' + n : '' + n; }; return p(d.getHours()) + ':' + p(d.getMinutes()); }

  // ───────────────────── 状态符号（UI-R1-B §6，唯一来源）─────────────────────
  var STATUS_SYM = { pending: '○', running: '●', success: '✓', failed: '!', blocked: '!', stopped: '■' };
  var STATUS_TXT = { pending: '等待中', running: '进行中', success: '完成', failed: '失败', blocked: '等待确认', stopped: '已停止' };
  function sym(st) { return STATUS_SYM[st] || '·'; }
  function stxt(st) { return STATUS_TXT[st] || ''; }

  // 值预览：只展示真实存在的 payload，不补全、不猜测
  function preview(v, max) {
    max = max || 400;
    if (v == null) return '';
    var s;
    if (typeof v === 'string') s = v;
    else { try { s = JSON.stringify(v, null, 2); } catch (e) { s = String(v); } }
    s = String(s);
    return s.length > max ? s.slice(0, max) + ' …' : s;
  }

  // ───────────────────── INCREMENTAL STREAMING MARKDOWN（无 O(n²)）─────────────────────
  function StreamingMarkdown(container) {
    this.container = container;
    this.renderedBlocks = 0;
    this.tailEl = null;
  }
  StreamingMarkdown.prototype._splitBlocks = function (text) {
    var lines = String(text || '').replace(/\r\n/g, '\n').split('\n');
    var blocks = [], cur = [], inCode = false, codeLang = '';
    function pushCur() { if (cur.length) { blocks.push({ type: 'lines', lines: cur.slice() }); cur = []; } }
    for (var i = 0; i < lines.length; i++) {
      var ln = lines[i];
      var fence = /^```/.test(ln);
      if (fence) {
        if (!inCode) { pushCur(); inCode = true; codeLang = ln.slice(3).trim(); cur = []; }
        else { blocks.push({ type: 'code', lang: codeLang, code: cur.join('\n') }); inCode = false; cur = []; codeLang = ''; }
        continue;
      }
      if (inCode) { cur.push(ln); continue; }
      if (/^\s*$/.test(ln)) { pushCur(); continue; }
      if (/^\|.*\|\s*$/.test(ln) && i + 1 < lines.length && /^\|[\s:|-]+\|\s*$/.test(lines[i + 1])) {
        pushCur();
        var tbl = [ln]; i++; while (i < lines.length && /^\|.*\|\s*$/.test(lines[i])) { tbl.push(lines[i]); i++; } i--;
        blocks.push({ type: 'table', src: tbl.join('\n') }); continue;
      }
      cur.push(ln);
    }
    if (inCode) blocks.push({ type: 'code', lang: codeLang, code: cur.join('\n') });
    else pushCur();
    return blocks;
  };
  StreamingMarkdown.prototype._renderBlock = function (b) {
    if (b.type === 'code') { return '<pre><code>' + esc(b.code) + '</code></pre>'; }
    if (b.type === 'table') {
      var rows = b.src.trim().split('\n'); var html = '<table>';
      for (var i = 0; i < rows.length; i++) {
        var cells = rows[i].replace(/^\||\|$/g, '').split('|').map(function (c) { return c.trim(); });
        if (i === 1) continue;
        html += '<tr>' + cells.map(function (c) { return (i === 0 ? '<th>' : '<td>') + esc(c) + (i === 0 ? '</th>' : '</td>'); }).join('') + '</tr>';
      }
      return html + '</table>';
    }
    var txt = b.lines.join('\n');
    return '<p>' + this._inline(txt) + '</p>';
  };
  StreamingMarkdown.prototype._inline = function (t) {
    var s = esc(t);
    s = s.replace(/`([^`]+)`/g, '<code>$1</code>');
    s = s.replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>');
    s = s.replace(/\*([^*]+)\*/g, '<i>$1</i>');
    s = s.replace(/\[([^\]]+)\]\((https?:[^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
    return s;
  };
  StreamingMarkdown.prototype.update = function (fullText) {
    var blocks = this._splitBlocks(fullText);
    var n = blocks.length;
    for (var i = this.renderedBlocks; i < n - 1; i++) {
      var be = el('div', 'x6-md-block'); be.innerHTML = this._renderBlock(blocks[i]);
      this.container.appendChild(be);
      this.renderedBlocks++;
    }
    var tailBlock = blocks[n - 1];
    var html = tailBlock ? this._renderBlock(tailBlock) : '';
    if (!this.tailEl) { this.tailEl = el('div', 'x6-md-block'); this.container.appendChild(this.tailEl); }
    this.tailEl.innerHTML = html;
  };
  StreamingMarkdown.prototype.finalize = function () {
    if (this.tailEl) { this.tailEl.className = 'x6-md-block'; this.tailEl = null; }
    this.renderedBlocks = 0;
  };
  function mdToHtml(text) {
    var box = el('div');
    var sm = new StreamingMarkdown(box);
    sm.update(String(text || '')); sm.finalize();
    return box.innerHTML;
  }

  // ───────────────────── 标签词表（与后端枚举一一对应，不发明新语义）─────────────────────
  function intentLabel(i) { return { casual_chat: '普通聊天', knowledge_query: '知识查询', execution_task: '执行任务', long_term_goal: '长期目标' }[i] || (i || '未知'); }
  function decisionLabel(d) { return { auto: '自动执行', confirm: '等待确认', block: '拒绝执行', confirm_rejected: '拒绝执行', rejected: '拒绝执行' }[d] || (d || '—'); }
  function riskCls(r) { return r === 'SAFE' ? 'risk-safe' : (r === 'BLOCK' ? 'risk-block' : 'risk-confirm'); }

  var AVATAR = {
    user: '你', assistant: '小', tool: '⚙', approval: '!', goal: '◆',
    task: '▸', intent: '◎', risk: '⚑', error: '✕', execution: '⚙'
  };

  // ───────────────────── 节点 HTML（只渲染真实字段）─────────────────────
  function statusChip(st) {
    return '<span class="x6-st ' + st + '"><i>' + sym(st) + '</i>' + esc(stxt(st)) + '</span>';
  }
  function detailBlock(n) {
    // §8/§15：只有 payload 里真实存在的信息才展示；错误详情默认收起
    var rows = '';
    if (n.input !== undefined && n.input !== null && n.input !== '') {
      rows += '<div class="x6-tl-kv"><span class="k">输入</span><pre>' + esc(preview(n.input)) + '</pre></div>';
    }
    if (n.output !== undefined && n.output !== null && n.output !== '') {
      rows += '<div class="x6-tl-kv"><span class="k">结果</span><pre>' + esc(preview(n.output)) + '</pre></div>';
    }
    if (n.detail) {
      rows += '<div class="x6-tl-kv"><span class="k">详情</span><pre>' + esc(preview(n.detail)) + '</pre></div>';
    }
    if (!rows) return '';
    return '<button class="x6-tl-toggle" type="button" data-toggle="1">查看详情</button>' +
      '<div class="x6-tl-detail" hidden>' + rows + '</div>';
  }

  function nodeInnerHtml(n) {
    if (n.type === 'user') {
      return '<div class="x6-bubble-body">' + esc(n.title || '') + '</div>';
    }
    if (n.type === 'intent') {
      var h = '<div class="intent-card"><div class="ic-title">小6理解</div>' +
        '<div class="ic-row">意图：' + esc(intentLabel(n.intent)) + '</div>';
      if (n.tools && n.tools.length) h += '<div class="ic-row">计划：' + esc(n.tools.join(' · ')) + '</div>';
      if (n.risk) h += '<div class="ic-row">风险：<span class="risk-tag ' + riskCls(n.risk) + '">' + esc(n.risk) + '</span></div>';
      return h + '</div>';
    }
    if (n.type === 'risk') {
      return '<div class="risk-card ' + riskCls(n.risk) + '"><div class="ic-title">安全检查</div>' +
        '<div class="ic-row">工具：' + esc(n.tool || '') + '</div>' +
        '<div class="ic-row">风险：<span class="risk-tag ' + riskCls(n.risk) + '">' + esc(n.risk || '') + '</span></div>' +
        '<div class="ic-row">结果：' + esc(decisionLabel(n.decision)) + '</div></div>';
    }
    if (n.type === 'tool') {
      var label = n.tool || '工具';
      var line = '<div class="x6-tool-summary">' + statusChip(n.status) +
        '<b>' + esc(label) + '</b>' +
        (n.summary ? '<span class="x6-tl-sub">' + esc(n.summary) + '</span>' : '') + '</div>';
      return line + detailBlock(n);
    }
    if (n.type === 'goal') {
      var gt = n.title ? n.title : ('目标 #' + (n.goalId != null ? n.goalId : '?'));
      var gh = '<div class="x6-tl-card"><div class="x6-tool-summary">' + statusChip(n.status) +
        '<b>目标</b><span class="x6-tl-sub">' + esc(gt) + '</span></div>';
      if (n.summary) gh += '<div class="x6-tl-meta">' + esc(n.summary) + '</div>';
      return gh + '</div>' + detailBlock(n);
    }
    if (n.type === 'task') {
      var tt = n.title ? n.title : ('任务 #' + (n.taskId != null ? n.taskId : '?'));
      var th = '<div class="x6-tool-summary">' + statusChip(n.status) +
        '<b>任务</b><span class="x6-tl-sub">' + esc(tt) + '</span></div>';
      return th + detailBlock(n);
    }
    if (n.type === 'approval') {
      var ah = '<div class="x6-approval-card" data-ticket="' + esc(n.ticket || '') + '">' +
        '<div class="x6-appr-head">' + statusChip(n.status) + '<b>小6请求执行</b></div>';
      if (n.tool) ah += '<div class="x6-tl-meta">工具：' + esc(n.tool) + '</div>';
      if (n.summary) ah += '<div class="x6-tl-meta">操作：' + esc(n.summary) + '</div>';
      if (n.argsPreview) ah += '<div class="x6-tl-meta">参数：' + esc(preview(n.argsPreview, 160)) + '</div>';
      if (n.error) ah += '<div class="x6-tl-err">' + esc(n.error) + '</div>';
      if (n.status === 'blocked') {
        ah += '<div class="x6-approval-act">' +
          '<button class="approve" type="button" data-decision="approve">允许</button>' +
          '<button class="reject" type="button" data-decision="reject">拒绝</button></div>';
      } else if (n.status === 'success') {
        ah += '<div class="x6-tl-meta">已批准</div>';
      } else if (n.status === 'stopped') {
        ah += '<div class="x6-tl-meta">已拒绝</div>';
      }
      return ah + '</div>';
    }
    if (n.type === 'error') {
      var eh = '<div class="x6-tl-errcard"><div class="x6-tool-summary">' + statusChip('failed') +
        '<b>' + esc(n.title || '执行失败') + '</b></div>';
      if (n.summary) eh += '<div class="x6-tl-err">' + esc(n.summary) + '</div>';
      return eh + '</div>' + detailBlock(n);
    }
    if (n.type === 'execution') {
      var xh = '<div class="x6-tool-summary">' + statusChip(n.status) +
        '<b>执行</b><span class="x6-tl-sub">' + esc(n.title || n.summary || '') + '</span></div>';
      return xh + detailBlock(n);
    }
    // RESULT 卡片：AGENT 完成任务后的结果摘要
    if (n.type === 'result') {
      var isFailed = n.status === 'failed';
      var rh = '<div class="x6-res-card">';
      rh += '<div class="x6-tool-summary"><b>' + (isFailed ? '! 任务失败' : '✓ 任务完成') + '</b></div>';
      if (n.title) rh += '<div class="x6-tl-meta">' + esc(n.title) + '</div>';
      if (n.summary) rh += '<div class="x6-tl-meta">' + esc(n.summary) + '</div>';
      if (n.detail) rh += '<div class="x6-tl-meta">' + esc(preview(n.detail, 200)) + '</div>';
      return rh + '</div>';
    }
    return '<div class="x6-bubble-body">' + esc(n.title || '') + '</div>';
  }

  // ───────────────────── 增量渲染器 ─────────────────────
  var domById = Object.create(null);

  function buildNodeDom(n) {
    var root = el('div', 'x6-node ' + n.type);
    root.dataset.nid = n.id;
    root.dataset.status = n.status;
    var av = el('div', 'x6-avatar', AVATAR[n.type] || '·');
    var bub = el('div', 'x6-bubble');
    root.appendChild(av); root.appendChild(bub);
    var rec = { root: root, bub: bub, ver: n._ver || 0, body: null, sm: null };
    if (n.type === 'assistant') {
      var meta = el('div', 'x6-bubble-meta');
      meta.innerHTML = '<span>小6</span><span>' + fmtTime(n.timestamp) + '</span>';
      var body = el('div', 'x6-bubble-body');
      bub.appendChild(meta); bub.appendChild(body);
      rec.body = body;
      rec.sm = new StreamingMarkdown(body);
      if (n.text) { rec.sm.update(n.text); }
      if (n.status !== 'running') { rec.sm.finalize(); }
      else { root.classList.add('streaming'); }
      if (n.error) { var ee = el('div', 'x6-tl-err', n.error); bub.appendChild(ee); }
    } else {
      bub.innerHTML = nodeInnerHtml(n);
    }
    return rec;
  }
  function paintNode(n, rec) {
    rec.root.dataset.status = n.status;
    if (n.type === 'assistant') {
      // 流式节点：正文由 StreamingMarkdown 持有，绝不整体重绘（否则会闪断）
      if (n.status === 'running') rec.root.classList.add('streaming');
      else { rec.root.classList.remove('streaming'); if (rec.sm) rec.sm.finalize(); }
      var errEl = rec.bub.querySelector('.x6-tl-err');
      if (n.error && !errEl) rec.bub.appendChild(el('div', 'x6-tl-err', n.error));
      else if (!n.error && errEl) errEl.remove();
    } else {
      rec.bub.innerHTML = nodeInnerHtml(n);
    }
    rec.ver = n._ver || 0;
  }

  var EMPTY_HTML = '<div class="x6-empty-hero"><div class="x6-empty-orb"></div><div class="x6-empty-title">小6</div><div class="x6-empty-sub">今天想让我做什么？</div></div>';
  function renderTimeline() {
    var list = $('chatList'); if (!list) return;
    var tl = state.timeline;
    var sugg = $('suggestions');
    if (!tl.length) {
      if (list.dataset.empty !== '1') {
        list.innerHTML = EMPTY_HTML;
        list.dataset.empty = '1';
        domById = Object.create(null);
      }
      if (sugg) sugg.hidden = false;
      return;
    }
    if (list.dataset.empty === '1') {
      list.innerHTML = '';
      list.dataset.empty = '0';
      domById = Object.create(null);
    }
    if (sugg) sugg.hidden = true;
    var atBottom = (list.scrollHeight - list.scrollTop - list.clientHeight) < 100;
    // 插入阶段分隔符（不持久化到 timeline，仅渲染时计算）
    // 阶段显示规则：
    //   PLAN  = 有 goal/task 节点
    //   EXECUTE = 有 tool 节点
    //   VERIFY = tool 节点之后出现 assistant success（有工具调用才显示）
    //   RESULT = AGENT_COMPLETED execution 节点或 AGENT 完成 result 节点出现
    var hasGoal = false;
    var hasTool = false;
    var hasExecDone = false;
    var hasResult = false;
    for (var i = 0; i < tl.length; i++) {
      var n = tl[i];
      if (n.type === 'goal' || n.type === 'task') hasGoal = true;
      if (n.type === 'tool') hasTool = true;
      if (n.type === 'execution' && n.status === 'success') hasExecDone = true;
      if (n.type === 'result') hasResult = true;
    }
    var phaseMarker = null;
    // 按顺序追踪哪些阶段标签已插入
    var shownPlan = !hasGoal;       // 如果没有任何 goal/task，PLAN 阶段不存在
    var shownExecute = !hasTool;    // 如果没有任何 tool，EXECUTE 阶段不存在
    var shownVerify = !hasTool;     // VERIFY 只在有工具时才显示
    var shownResult = !hasResult && !hasExecDone; // RESULT 在结果节点或执行完成前不显示
    for (var i = 0; i < tl.length; i++) {
      var n = tl[i];
      // PLAN 阶段：第一个 goal/task 节点前插入（如果没有 goal/task 则不插入）
      if (n.type === 'goal' || n.type === 'task') {
        if (!shownPlan) {
          var pe0 = el('div', 'x6-phase-label');
          pe0.textContent = 'PLAN';
          list.appendChild(pe0);
          shownPlan = true;
        }
      }
      // EXECUTE 阶段：第一个 tool 节点前插入（如果没有 tool 则不插入）
      if (n.type === 'tool') {
        if (!shownExecute) {
          var pe1 = el('div', 'x6-phase-label');
          pe1.textContent = 'EXECUTE';
          list.appendChild(pe1);
          shownExecute = true;
        }
      }
      // VERIFY 阶段：assistant 最终回复出现在 tool 之后
      if (n.type === 'assistant' && n.status === 'success' && hasTool && !shownVerify) {
        var vpe = el('div', 'x6-phase-label');
        vpe.textContent = 'VERIFY';
        list.appendChild(vpe);
        shownVerify = true;
      }
      // RESULT 阶段：result 节点或 execution_completed 节点后
      if ((n.type === 'result' || (n.type === 'execution' && n.title && n.title.indexOf('执行完成') >= 0)) && !shownResult) {
        var rpe = el('div', 'x6-phase-label');
        rpe.textContent = 'RESULT';
        list.appendChild(rpe);
        shownResult = true;
      }
      var rec = domById[n.id];
      if (!rec) {
        rec = buildNodeDom(n);
        domById[n.id] = rec;
        list.appendChild(rec.root);
      } else if ((n._ver || 0) !== rec.ver) {
        paintNode(n, rec);
      }
    }
    if (atBottom) scrollChat();
  }
  function scrollChat() { var c = $('chatList'); if (c) c.scrollTop = c.scrollHeight; }
  function streamOf(nodeId) { var r = domById[nodeId]; return r ? r.sm : null; }

  // ───────────────────── 工具节点去重（chat / stream 双通道合并为同一真实调用）─────────────────────
  // 后端在 chat SSE 与 /api/stream 两条通道都会广播同一工具调用的事件：
  //   chat 通道  tool_start/tool_end（无 execution_id）
  //   stream 通道 tool_started/tool_finished（带 execution_id，唯一主键）
  // 二者指向同一次真实工具执行，必须合并为单个 Timeline 节点，避免重复行。
  function findToolByExec(eid) {
    if (!eid) return null;
    for (var i = state.timeline.length - 1; i >= 0; i--) {
      var n = state.timeline[i];
      if (n.type === 'tool' && n.executionId === eid) return n;
    }
    return null;
  }
  // chat 通道合并：可并入「运行中」的同名节点（含 stream 抢先创建、已带 execution_id 的节点），
  // 或刚结束（<5s）的同类节点。用于把 chat 工具节点挂到同一真实调用的 stream 节点上。
  function findMergeChat(tool) {
    var now = Date.now(), bestRun = null, bestRunTs = 0, bestRecent = null, bestRecentTs = 0;
    for (var i = 0; i < state.timeline.length; i++) {
      var n = state.timeline[i];
      if (n.type !== 'tool' || (n.tool || '') !== (tool || '')) continue;
      var age = now - (n.timestamp || now);
      if (age > 10000) continue;
      if (n.status === 'running' && n.timestamp >= bestRunTs) { bestRunTs = n.timestamp; bestRun = n; }
      if (age < 5000 && n.timestamp >= bestRecentTs) { bestRecentTs = n.timestamp; bestRecent = n; }
    }
    return bestRun || bestRecent;
  }
  // stream 通道合并：仅并入「无 execution_id」的同名节点（chat 节点），
  // 绝不并入其它 execution_id 节点 —— 否则会把两次不同的同名调用错误合并。
  function findMergeStream(tool) {
    var now = Date.now(), bestRun = null, bestRunTs = 0, bestRecent = null, bestRecentTs = 0;
    for (var i = 0; i < state.timeline.length; i++) {
      var n = state.timeline[i];
      if (n.type !== 'tool' || (n.tool || '') !== (tool || '')) continue;
      if (n.executionId) continue;
      var age = now - (n.timestamp || now);
      if (age > 10000) continue;
      if (n.status === 'running' && n.timestamp >= bestRunTs) { bestRunTs = n.timestamp; bestRun = n; }
      if (n.timestamp >= bestRecentTs) { bestRecentTs = n.timestamp; bestRecent = n; }
    }
    return bestRun || bestRecent;
  }
  function upsertTool(opts) {
    opts = opts || {};
    var eid = opts.executionId || null;
    var tool = opts.tool || '工具';
    // 1) 优先按 execution_id 关联（并发安全，唯一主键）
    var node = eid ? findToolByExec(eid) : null;
    // 2) 否则按通道策略合并另一通道已建立的同名节点（同一真实调用，双通道重复）
    //    · stream 通道：仅并入无 execution_id 的 chat 节点（绝不并入其它 execId 节点）
    //    · chat  通道：可并入运行中的同名节点（含 stream 抢先节点）或刚结束（<5s）的同类节点
    if (!node) node = opts.fromStream ? findMergeStream(tool) : findMergeChat(tool);
    if (node) {
      if (eid && !node.executionId) node.executionId = eid;
      if (opts.goalId != null) node.goalId = opts.goalId;
      // 已处于终态（success/failed）的节点不被 running 覆盖（处理 stream 滞后于 chat 完成的竞态）
      if (opts.status && node.status !== 'success' && node.status !== 'failed') node.status = opts.status;
      if (opts.summary) node.summary = opts.summary;
      if (opts.input !== undefined && opts.input !== null) node.input = opts.input;
      if (opts.output !== undefined && opts.output !== null) node.output = opts.output;
      node._ver = (node._ver || 0) + 1;
      return node;
    }
    // 3) 新节点（id：stream 用 execution_id，chat 用请求内序号）
    var id = eid ? ('tool:stream:' + eid) : ('tool:chat:' + (opts.reqId != null ? opts.reqId : 'x') + ':' + (opts.seq != null ? opts.seq : Date.now()));
    return state.upsertNode({
      id: id, type: 'tool', status: opts.status || 'running',
      tool: tool, executionId: eid, goalId: opts.goalId,
      summary: opts.summary || (opts.status === 'running' ? '正在执行' : ''),
      input: opts.input, output: opts.output,
      timestamp: Date.now()
    });
  }

  // ───────────────────── 兼容入口（inspector 调用，节点统一进 state.timeline）─────────────────────
  function addIntentNode(p) {
    p = p || {};
    var tsKey = p.__ts || Date.now();
    return state.upsertNode({
      id: 'intent:' + tsKey, type: 'intent', status: 'success',
      title: '小6理解', intent: p.intent, tools: p.tools, risk: p.risk,
      timestamp: Date.now()
    });
  }
  function addRiskNode(p) {
    p = p || {};
    var tsKey = p.__ts || Date.now();
    return state.upsertNode({
      id: 'risk:' + tsKey + ':' + (p.tool || ''), type: 'risk',
      status: p.decision === 'block' || p.decision === 'rejected' || p.decision === 'confirm_rejected' ? 'failed' : 'success',
      title: '安全检查', tool: p.tool, risk: p.risk, decision: p.decision,
      timestamp: Date.now()
    });
  }

  // ───────────────────── 能力标签（发往后端的 metadata，非用户原话）─────────────────────
  function activePrefix() {
    var order = ['think', 'web', 'code'];
    var on = order.filter(function (k) { return state.toolModes[k]; });
    if (!on.length) return '';
    var names = { think: '深度思考', web: '联网搜索', code: '代码执行' };
    return '【' + on.map(function (k) { return names[k]; }).join('】【') + '】';
  }

  // ───────────────────── CHAT（真实 SSE → state.timeline）─────────────────────
  var chatSeq = 0;
  function sendChat(text, opts) {
    opts = opts || {};
    text = String(text || '').trim();
    if (!text || state.busy) return;

    // 能力标签是发给后端的 metadata，不是用户说的话 —— Timeline 显示原文，请求体仍带标签（契约不变）
    var displayText = text;
    var prefix = activePrefix();
    if (prefix && text.indexOf('【') !== 0) text = prefix + text;

    var reqId = (++chatSeq);
    var now = Date.now();
    var userId = 'u:' + reqId + ':' + now;
    var asstId = 'a:' + reqId + ':' + now;

    state.upsertNode({ id: userId, type: 'user', status: 'success', title: displayText, timestamp: now });
    state.upsertNode({ id: asstId, type: 'assistant', status: 'running', text: '', timestamp: now });

    state.busy = true;
    state.busyDetail = '正在理解你的指令…';
    // 状态来自真实 runtime：只有后端处于 IDLE 时前端才本地标记为「正在分析」（本次请求确实已发出）
    var cur = String(state.snap.agent.state || 'IDLE').toUpperCase();
    state.setState(cur === 'IDLE' ? 'THINKING' : cur);
    state.notify();

    // 本次请求内的工具 open 栈（chat 通道无 execution_id，禁止全局同名匹配）
    var openTools = [];
    var toolSeq = 0;

    var payload = { messages: [{ role: 'user', content: text }], session_id: state.sessionId };
    // R2-F: 传递 mode (smart/expert) 和 goal_id (Project Context)
    if (state.toolModes && state.toolModes.expert) payload.mode = 'expert';
    else payload.mode = 'smart';
    if (state.runtime && state.runtime.currentGoalId != null) payload.goal_id = state.runtime.currentGoalId;

    fetch('/api/chat', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
      .then(function (r) { if (!r.ok || !r.body) throw new Error('HTTP ' + r.status); return r.body.getReader(); })
      .then(function (reader) {
        var decoder = new TextDecoder('utf-8'), buf = '', reply = '', done = false;
        function pump() {
          return reader.read().then(function (res) {
            if (res.done) { finish(); return; }
            buf += decoder.decode(res.value, { stream: true });
            var parts = buf.split('\n\n'); buf = parts.pop();
            for (var i = 0; i < parts.length; i++) {
              var raw = parts[i].trim(); if (!raw) continue;
              if (raw.indexOf('data:') === 0) raw = raw.slice(5).trim();
              var m; try { m = JSON.parse(raw); } catch (e) { m = raw; }
              if (m === '[DONE]' || raw === '[DONE]') { done = true; finish(); return; }
              handle(m);
            }
            if (!done) return pump();
          });
        }
        function handle(m) {
          var ev = m.xiao6_event || m.event;
          if (ev === 'tool_start') { onToolStart(m.tool, m.args); }
          else if (ev === 'tool_end') { onToolEnd(m.tool, m.result, m.ok !== false); }
          else if (ev === 'approval') { window.Xiao6.approval.renderApprovalCard(m); }
          else if (m.choices && m.choices[0] && m.choices[0].delta) {
            var dc = m.choices[0].delta.content || '';
            if (dc) {
              reply += dc;
              var n = state.getNode(asstId); if (n) n.text = reply;   // 视图模型同步（不 bump _ver：正文由 sm 增量写）
              var sm = streamOf(asstId);
              if (sm) { sm.update(reply); scrollChat(); }
              else { state.patchNode(asstId, { text: reply }); state.notify(); }
            }
          }
        }
        function onToolStart(tool, args) {
          var node = upsertTool({ executionId: null, tool: tool || '工具', status: 'running', input: args, summary: '正在执行', reqId: reqId, seq: (++toolSeq) });
          openTools.push({ id: node.id, tool: tool || '' });
          state.busyDetail = '正在调用工具 ' + (tool || '') + '…';
          state.notify();
        }
        function onToolEnd(tool, result, ok) {
          var name = tool || '';
          var idx = -1;
          for (var i = openTools.length - 1; i >= 0; i--) { if (openTools[i].tool === name) { idx = i; break; } }
          if (idx < 0 && openTools.length) idx = openTools.length - 1;   // 同名缺失时闭合最近一个未完成的
          if (idx < 0) return;
          var entry = openTools.splice(idx, 1)[0];
          state.patchNode(entry.id, {
            status: ok === false ? 'failed' : 'success',
            summary: ok === false ? '失败' : '完成',
            output: result
          });
          if (ok === false) state.runtime.lastError = { message: '工具 ' + name + ' 执行失败', source: name, ts: Date.now() };
          state.busyDetail = openTools.length ? state.busyDetail : '正在生成回复…';
          state.notify();
        }
        function finish() {
          // §16：完成只由真实终态（[DONE] / 流结束）决定，不用 setTimeout 判断
          state.busy = false; state.busyDetail = null;
          openTools.forEach(function (e) {
            // 流已结束但工具未收到 tool_end：如实标记为未知终态，不假装成功
            state.patchNode(e.id, { status: 'stopped', summary: '未收到结束事件' });
          });
          openTools = [];
          state.patchNode(asstId, { status: 'success', text: reply });
          if (reply && state.autoSpeak) window.Xiao6.voice.speakText(reply);
          state.setState(String(state.snap.agent.state || 'IDLE').toUpperCase());
          state.notify();
          state.fetchSnapshot();
        }
        pump();
      })
      .catch(function (err) {
        state.busy = false; state.busyDetail = null;
        state.patchNode(asstId, { status: 'failed', error: '请求失败 · 请检查核心服务' });
        state.runtime.lastError = { message: String((err && err.message) || err || '请求失败'), source: '/api/chat', ts: Date.now() };
        state.setState('ERROR'); state.notify();
        state.fetchSnapshot();
      });
  }

  function submitCmd(text) {
    var view = document.body.dataset.view;
    if (view !== 'home') window.Xiao6.main.switchView('home');
    sendChat(text);
  }

  // ───────────────────── 「历史」视图：Agent 活动 / 执行结果（派生自 state.timeline）─────────────────────
  function renderAgentActivity() {
    var list = $('agentList'); if (!list) return;
    var items = state.timeline.filter(function (n) {
      return n.type === 'tool' || n.type === 'goal' || n.type === 'task' ||
             n.type === 'approval' || n.type === 'intent' || n.type === 'risk' || n.type === 'error';
    });
    if (!items.length) { list.innerHTML = '<span class="x6-empty">暂无 Agent 活动</span>'; return; }
    list.innerHTML = items.slice(-40).reverse().map(function (n) {
      var txt = n.type === 'tool' ? ('工具 ' + (n.tool || '') + ' · ' + stxt(n.status))
        : n.type === 'goal' ? ('目标 ' + (n.title || ('#' + n.goalId)) + ' · ' + stxt(n.status))
        : n.type === 'task' ? ('任务 ' + (n.title || ('#' + n.taskId)) + ' · ' + stxt(n.status))
        : n.type === 'approval' ? ('审批 ' + (n.tool || '') + ' · ' + stxt(n.status))
        : n.type === 'intent' ? ('意图 ' + intentLabel(n.intent))
        : n.type === 'risk' ? ('安全检查 ' + (n.tool || '') + ' ' + (n.risk || ''))
        : (n.title || '执行失败');
      return '<div class="x6-agent-item ' + n.type + '"><div class="x6-agent-ic">' + sym(n.status) + '</div>' +
        '<div class="x6-agent-body-txt"><div>' + esc(txt) + '</div><div class="t">' + fmtTime(n.timestamp) + '</div></div></div>';
    }).join('');
  }
  function renderResults() {
    var list = $('resList'); if (!list) return;
    var replies = state.timeline.filter(function (n) { return n.type === 'assistant' && n.text; });
    if (!replies.length) { list.innerHTML = '<span class="x6-empty">暂无结果</span>'; return; }
    list.innerHTML = replies.slice(-12).reverse().map(function (r) {
      return '<div class="x6-res-card"><div class="x6-bubble-meta"><span>小6</span><span>' +
        fmtTime(r.timestamp) + '</span></div>' + mdToHtml(r.text) + '</div>';
    }).join('');
  }

  // 进行中的任务卡片（「当前项目」视图复用；数据源 /api/tasks 真实字段）
  function renderWorkspace(container) {
    var list = container || $('wsList'); if (!list) return;
    var open = state.snap.tasks.filter(function (t) {
      var s = String(t.status || '').toLowerCase();
      return s !== 'done' && s !== 'completed' && s !== 'closed' && t.current_step != null && t.total_steps;
    }).slice(0, 8);
    var running = Number((state.snap.agent || {}).running || 0);
    if (!open.length && !running) { list.innerHTML = '<span class="x6-empty">没有进行中的任务</span>'; return; }
    var html = '';
    open.forEach(function (t) {
      // 真实步骤计数（§7：不创造百分比，用 current/total 表达）
      html += '<div class="x6-ws-card"><div class="ttl">⚙ ' + esc(t.title || '任务') + '</div>' +
        '<div class="meta">步骤 ' + t.current_step + ' / ' + t.total_steps + '</div></div>';
    });
    if (running > 0) html += '<div class="x6-ws-card"><div class="ttl">● 小6核心执行中</div><div class="meta">运行 ' + running + ' 项</div></div>';
    list.innerHTML = html;
  }

  // ───────────────────── JUMPBAR（minimap / scroll-spy）─────────────────────
  function buildJumpbar() {
    var track = $('jumpTrack'); var list = $('chatList'); if (!track || !list) return;
    Array.prototype.slice.call(track.querySelectorAll('.x6-jump-mark, .x6-jump-tip, .x6-jump-thumb')).forEach(function (n) { n.remove(); });
    var nodes = Array.prototype.slice.call(list.querySelectorAll('.x6-node'));
    var total = list.scrollHeight || 1;
    nodes.forEach(function (n, i) {
      var frac = Math.min(1, Math.max(0, n.offsetTop / total));
      var mk = el('div', 'x6-jump-mark');
      mk.style.top = (frac * 100) + '%';
      mk.dataset.idx = i;
      var tip = el('div', 'x6-jump-tip');
      var txt = ((n.querySelector('.x6-bubble-body') || n.querySelector('.x6-bubble') || n).textContent || '').replace(/\s+/g, ' ').trim().slice(0, 80);
      mk.addEventListener('mouseenter', function () { tip.textContent = txt || '（空消息）'; tip.style.top = mk.style.top; tip.classList.add('show'); });
      mk.addEventListener('mouseleave', function () { tip.classList.remove('show'); });
      mk.addEventListener('click', function () { jumpToMessage(i); });
      track.appendChild(mk); track.appendChild(tip);
    });
    updateJumpbarThumb();
  }
  function updateJumpbarThumb() {
    var track = $('jumpTrack'); var list = $('chatList'); if (!track || !list) return;
    var thumb = track.querySelector('.x6-jump-thumb');
    if (!thumb) { thumb = el('div', 'x6-jump-thumb'); track.appendChild(thumb); }
    var total = list.scrollHeight || 1;
    var vh = list.clientHeight;
    thumb.style.top = ((list.scrollTop / total) * 100) + '%';
    thumb.style.height = (Math.max(4, (vh / total) * 100)) + '%';
  }
  function jumpToMessage(i) {
    var list = $('chatList'); if (!list) return;
    var nodes = Array.prototype.slice.call(list.querySelectorAll('.x6-node'));
    var n = nodes[i]; if (!n) return;
    list.scrollTo({ top: n.offsetTop - 24, behavior: 'smooth' });
    Array.prototype.forEach.call(list.parentNode.querySelectorAll('.x6-jump-mark'), function (m) { m.classList.toggle('is-active', m.dataset.idx == i); });
  }

  // ───────────────────── WIRING ─────────────────────
  function init() {
    // 状态变化 → 增量重绘 Timeline（唯一渲染入口）
    state.subscribe(function () {
      renderTimeline();
      if (document.body.dataset.view === 'history') { renderAgentActivity(); renderResults(); }
    });

    // 事件委托：详情展开 / 审批按钮（DOM 会被增量重绘，必须委托而非直接绑定）
    var chatList = $('chatList');
    if (chatList) chatList.addEventListener('click', function (e) {
      var tg = e.target.closest ? e.target.closest('.x6-tl-toggle') : null;
      if (tg) {
        var d = tg.parentNode.querySelector('.x6-tl-detail');
        if (d) { d.hidden = !d.hidden; tg.textContent = d.hidden ? '查看详情' : '收起详情'; }
        return;
      }
      var btn = e.target.closest ? e.target.closest('.x6-approval-act button') : null;
      if (btn) {
        var card = btn.closest('.x6-approval-card');
        var ticket = card ? card.dataset.ticket : '';
        window.Xiao6.approval.postApproval(ticket, btn.dataset.decision);
      }
    });

    // Composer 模式开关（思考 / 联网 / 语音输入 / 语音播报）
    qsa('.x6-mode').forEach(function (b) {
      b.addEventListener('click', function () {
        var t = b.dataset.tool;
        if (t === 'think') { state.toolModes.think = !state.toolModes.think; }
        else if (t === 'web') { state.toolModes.web = !state.toolModes.web; }
        else if (t === 'speak') { state.autoSpeak = !state.autoSpeak; state.lsSet('xiao6_autoSpeak', state.autoSpeak ? '1' : '0'); }
        else if (t === 'voice') { window.Xiao6.voice.startVoice(); return; }
        b.classList.toggle('is-on', (t === 'speak' ? state.autoSpeak : state.toolModes[t]));
      });
    });
    var speakBtn = qs('.x6-mode[data-tool="speak"]'); if (speakBtn) speakBtn.classList.toggle('is-on', state.autoSpeak);
    var webBtn = qs('.x6-mode[data-tool="web"]'); if (webBtn) webBtn.classList.toggle('is-on', !!state.toolModes.web);

    var cf = $('cmdForm');
    if (cf) cf.addEventListener('submit', function (e) {
      e.preventDefault();
      var v = ($('cmdInput').value || '');
      if (v.charAt(0) === '/' && window.Xiao6.palette && window.Xiao6.palette.runCommand(v)) { $('cmdInput').value = ''; return; }
      submitCmd(v);
      $('cmdInput').value = '';
    });
    var ci = $('cmdInput');
    if (ci) ci.addEventListener('input', function (e) { if (window.Xiao6.palette) window.Xiao6.palette.handleTrigger(e.target.value); });

    // 快捷建议按钮绑定
    var sugg = $('suggestions');
    if (sugg) {
      sugg.addEventListener('click', function (e) {
        var btn = e.target.closest ? e.target.closest('.x6-sug') : null;
        if (btn) { var task = btn.dataset.task; if (task) { $('cmdInput').value = task; window.Xiao6.timeline.submitCmd(task); } }
      });
    }

    var jb = $('jumpbar'); if (jb) jb.hidden = false;
    if (chatList) {
      var rafPending = false;
      chatList.addEventListener('scroll', function () { if (!rafPending) { rafPending = true; requestAnimationFrame(function () { rafPending = false; updateJumpbarThumb(); }); } });
      var mo = new MutationObserver(function () { buildJumpbar(); });
      mo.observe(chatList, { childList: true });
      setTimeout(buildJumpbar, 300);
    }
    renderTimeline();
  }

  window.Xiao6.timeline = {
    renderTimeline: renderTimeline,
    scrollChat: scrollChat,
    upsertTool: upsertTool,
    addIntentNode: addIntentNode,
    addRiskNode: addRiskNode,
    sendChat: sendChat,
    submitCmd: submitCmd,
    renderWorkspace: renderWorkspace,
    renderResults: renderResults,
    renderAgentActivity: renderAgentActivity,
    buildJumpbar: buildJumpbar,
    mdToHtml: mdToHtml,
    STATUS_SYM: STATUS_SYM,
    STATUS_TXT: STATUS_TXT,
    init: init
  };
})();
