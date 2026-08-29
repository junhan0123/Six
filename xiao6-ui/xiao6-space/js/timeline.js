/* ═════════════════════════════════════════════════════════════════
   Xiao6 UI-R1 · timeline.js — Conversation Timeline 核心（Phase 2）
   迁移自 xiao6-workspace.js：StreamingMarkdown / addNode / scrollChat /
   sendChat（pump·handle·onTool·onApproval·finish 闭包链整体保留）/
   submitCmd / renderWorkspace / renderResults / jumpbar
   冻结契约：POST /api/chat（body {messages,session_id}，SSE delta.content /
   tool_start / tool_end / approval / [DONE] 双形态）
   状态统一改 Xiao6.state.xxx
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

  // ───────────────────── INCREMENTAL STREAMING MARKDOWN（§9：无 O(n²)）─────────────────────
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
      var be = el('div', 'xiao6-md-block'); be.innerHTML = this._renderBlock(blocks[i]);
      this.container.appendChild(be);
      this.renderedBlocks++;
    }
    var tailBlock = blocks[n - 1];
    var html = tailBlock ? this._renderBlock(tailBlock) : '';
    if (!this.tailEl) { this.tailEl = el('div', 'xiao6-md-block'); this.container.appendChild(this.tailEl); }
    this.tailEl.innerHTML = html;
  };
  StreamingMarkdown.prototype.finalize = function () {
    if (this.tailEl) { this.tailEl.className = 'xiao6-md-block'; this.tailEl = null; }
    this.renderedBlocks = 0;
  };

  // ───────────────────── CHAT（typed ChatNode + SSE）─────────────────────
  function addNode(kind, meta) {
    var node = el('div', 'xiao6-node ' + kind);
    var av = el('div', 'xiao6-avatar', kind === 'user' ? '你' : (kind === 'assistant' ? '小' : (kind === 'tool' ? '⚙' : (kind === 'approval' ? '!' : (kind === 'result' ? '✓' : (kind === 'intent' ? '◎' : (kind === 'risk' ? '⚑' : '·')))))));
    var bub = el('div', 'xiao6-bubble');
    node.appendChild(av); node.appendChild(bub);
    var list = $('chatList'); if (list) list.appendChild(node);
    scrollChat();
    return { node: node, bub: bub };
  }
  function scrollChat() { var c = $('chatList'); if (c) c.scrollTop = c.scrollHeight; }

  // ───────────────────── Phase 8 · Trust 透明节点（intent / risk）─────────────────────
  function intentLabel(i) { return { casual_chat: '普通聊天', knowledge_query: '知识查询', execution_task: '执行任务', long_term_goal: '长期目标' }[i] || (i || '未知'); }
  function decisionLabel(d) { return { auto: '自动执行', confirm: '等待确认', block: '拒绝执行', confirm_rejected: '拒绝执行', rejected: '拒绝执行' }[d] || (d || '—'); }
  function riskCls(r) { return r === 'SAFE' ? 'risk-safe' : (r === 'BLOCK' ? 'risk-block' : 'risk-confirm'); }
  function addIntentNode(p) {
    p = p || {};
    var cn = addNode('intent');
    var html = '<div class="intent-card"><div class="ic-title">小6理解</div>' +
      '<div class="ic-row">意图：' + esc(intentLabel(p.intent)) + '</div>';
    if (p.tools && p.tools.length) html += '<div class="ic-row">计划：' + esc(p.tools.join(' · ')) + '</div>';
    if (p.risk) html += '<div class="ic-row">风险：<span class="risk-tag ' + riskCls(p.risk) + '">' + esc(p.risk) + '</span></div>';
    html += '</div>';
    cn.bub.innerHTML = html;
    return cn;
  }
  function addRiskNode(p) {
    p = p || {};
    var cn = addNode('risk');
    var html = '<div class="risk-card ' + riskCls(p.risk) + '"><div class="ic-title">安全检查</div>' +
      '<div class="ic-row">工具：' + esc(p.tool) + '</div>' +
      '<div class="ic-row">风险：<span class="risk-tag ' + riskCls(p.risk) + '">' + esc(p.risk) + '</span></div>' +
      '<div class="ic-row">结果：' + esc(decisionLabel(p.decision)) + '</div>' +
      '</div>';
    cn.bub.innerHTML = html;
    return cn;
  }

  function activePrefix() {
    var order = ['think', 'web', 'code'];
    var on = order.filter(function (k) { return state.toolModes[k]; });
    if (!on.length) return '';
    var names = { think: '深度思考', web: '联网搜索', code: '代码执行' };
    return '【' + on.map(function (k) { return names[k]; }).join('】【') + '】';
  }

  function sendChat(text, opts) {
    opts = opts || {};
    text = String(text || '').trim();
    if (!text || state.busy) return;
    // 能力标签（【深度思考】【联网搜索】【代码执行】）是发给后端的 metadata，
    // 不是用户说的话 —— 时间线上必须显示用户原文，请求体仍带标签（契约不变）。
    var displayText = text;
    var prefix = activePrefix();
    if (prefix && text.indexOf('【') !== 0) text = prefix + text;

    var un = addNode('user'); un.bub.innerHTML = '<div class="xiao6-bubble-body">' + esc(displayText) + '</div>';

    state.busy = true;
    state.busyDetail = '正在理解你的指令…';
    state.setState(state.snap.agent.state && String(state.snap.agent.state).toUpperCase() === 'IDLE' ? 'THINKING' : state.snap.agent.state);
    state.notify();
    var an = addNode('assistant'); an.node.classList.add('streaming');
    var meta = el('div', 'xiao6-bubble-meta'); meta.innerHTML = '<span>小6</span><span>' + fmtTime() + '</span>';
    var body = el('div', 'xiao6-bubble-body');
    an.bub.appendChild(meta); an.bub.appendChild(body);
    var stream = new StreamingMarkdown(body);

    var payload = { messages: [{ role: 'user', content: text }], session_id: state.sessionId };

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
          if (ev === 'tool_start') { onTool('start', m.tool, m.args); }
          else if (ev === 'tool_end') { onTool('end', m.tool, m.result, m.ok !== false); }
          else if (ev === 'approval') { onApproval(m); }
          else if (m.choices && m.choices[0] && m.choices[0].delta) {
            var dc = m.choices[0].delta.content || '';
            if (dc) { reply += dc; stream.update(reply); scrollChat(); }
          }
        }
        function onTool(phase, tool, arg, ok) {
          if (phase === 'start') {
            state.agentLog.unshift({ kind: 'tool', t: Date.now(), tool: tool, arg: arg, ongoing: true });
            state.busyDetail = '正在调用工具 ' + (tool || '') + '…';
            var tn = addNode('tool'); tn.bub.innerHTML = '<div class="xiao6-tool-summary">调用工具 <b>' + esc(tool || '') + '</b> …</div>';
            tn.node.dataset.toolnode = '1';
            tn.node.classList.add('tool-running');
          } else {
            state.agentLog.forEach(function (x) { if (x.tool === tool && x.ongoing) { x.ongoing = false; x.ok = ok; } });
            qsa('.xiao6-node.tool').forEach(function (n) { if (n.dataset.toolnode) { n.querySelector('.xiao6-tool-summary').innerHTML = '工具 <b>' + esc(tool || '') + '</b> ' + (ok === false ? '失败' : '完成'); n.classList.remove('tool-running'); n.classList.add('tool-done'); } });
            window.Xiao6.inspector.renderAgent();
          }
          window.Xiao6.inspector.renderAgent();
        }
        function onApproval(m) { window.Xiao6.approval.renderApprovalCard(m); }
        function finish() {
          state.busy = false; state.busyDetail = null; stream.finalize(); an.node.classList.remove('streaming');
          state.resultLog.unshift({ t: Date.now(), text: reply });
          renderResults(); window.Xiao6.inspector.renderAgent();
          if (reply && state.autoSpeak) window.Xiao6.voice.speakText(reply);
          state.setState(state.snap.agent.state || 'IDLE');
          state.notify();
          setTimeout(state.fetchSnapshot, 1200);
        }
        pump();
      })
      .catch(function (err) {
        state.busy = false; state.busyDetail = null; stream.finalize(); an.node.classList.remove('streaming');
        an.bub.appendChild(el('div', 'xiao6-bubble-body')).innerHTML = '<span style="color:var(--xiao6-danger)">请求失败 · 请检查核心服务</span>';
        state.setState('ERROR'); state.notify(); setTimeout(state.fetchSnapshot, 600);
      });
  }

  function submitCmd(text) {
    var view = document.body.dataset.view;
    if (view !== 'home') window.Xiao6.main.switchView('home');
    sendChat(text);
  }

  // 进行中的任务卡片（供「当前项目」视图复用；数据源 /api/tasks）
  function renderWorkspace(container) {
    var list = container || $('wsList'); if (!list) return;
    var open = state.snap.tasks.filter(function (t) {
      var s = String(t.status || '').toLowerCase();
      return s !== 'done' && s !== 'completed' && s !== 'closed' && t.current_step != null && t.total_steps;
    }).slice(0, 8);
    var running = Number((state.snap.agent || {}).running || 0);
    if (!open.length && !running) { list.innerHTML = '<span class="xiao6-empty">没有进行中的任务</span>'; return; }
    var html = '';
    open.forEach(function (t) { var p = t.total_steps ? Math.round(t.current_step / t.total_steps * 100) : 0;
      html += '<div class="xiao6-ws-card"><div class="ttl">⚙ ' + esc(t.title || '任务') + '</div><div class="meta">步骤 ' + t.current_step + '/' + t.total_steps + '</div><div class="xiao6-prog"><i style="width:' + p + '%"></i></div></div>'; });
    if (running > 0) html += '<div class="xiao6-ws-card"><div class="ttl">◌ 小6核心执行中</div><div class="meta">运行 ' + running + ' 项</div><div class="xiao6-prog"><i style="width:100%"></i></div></div>';
    list.innerHTML = html;
  }
  function renderResults() {
    var list = $('resList'); if (!list) return;
    if (!state.resultLog.length) { list.innerHTML = '<span class="xiao6-empty">暂无结果</span>'; return; }
    list.innerHTML = state.resultLog.slice(0, 12).map(function (r) {
      var sm = new StreamingMarkdown(el('div')); sm.update(r.text); sm.finalize();
      return '<div class="xiao6-res-card"><div class="xiao6-bubble-meta"><span>小6</span><span>' + fmtTime(r.t) + '</span></div>' + sm.container.innerHTML + '</div>';
    }).join('');
  }

  // ───────────────────── JUMPBAR（minimap / scroll-spy）─────────────────────
  function buildJumpbar() {
    var track = $('jumpTrack'); var list = $('chatList'); if (!track || !list) return;
    Array.prototype.slice.call(track.querySelectorAll('.xiao6-jump-mark, .xiao6-jump-tip, .xiao6-jump-thumb')).forEach(function (n) { n.remove(); });
    var nodes = Array.prototype.slice.call(list.querySelectorAll('.xiao6-node'));
    var total = list.scrollHeight || 1;
    nodes.forEach(function (n, i) {
      var frac = Math.min(1, Math.max(0, n.offsetTop / total));
      var mk = el('div', 'xiao6-jump-mark');
      mk.style.top = (frac * 100) + '%';
      mk.dataset.idx = i;
      var tip = el('div', 'xiao6-jump-tip');
      var txt = ((n.querySelector('.xiao6-bubble-body') || n.querySelector('.xiao6-bubble') || n).textContent || '').replace(/\s+/g, ' ').trim().slice(0, 80);
      mk.addEventListener('mouseenter', function () { tip.textContent = txt || '（空消息）'; tip.style.top = mk.style.top; tip.classList.add('show'); });
      mk.addEventListener('mouseleave', function () { tip.classList.remove('show'); });
      mk.addEventListener('click', function () { jumpToMessage(i); });
      track.appendChild(mk); track.appendChild(tip);
    });
    updateJumpbarThumb();
  }
  function updateJumpbarThumb() {
    var track = $('jumpTrack'); var list = $('chatList'); if (!track || !list) return;
    var thumb = track.querySelector('.xiao6-jump-thumb');
    if (!thumb) { thumb = el('div', 'xiao6-jump-thumb'); track.appendChild(thumb); }
    var total = list.scrollHeight || 1;
    var vh = list.clientHeight;
    thumb.style.top = ((list.scrollTop / total) * 100) + '%';
    thumb.style.height = (Math.max(4, (vh / total) * 100)) + '%';
  }
  function jumpToMessage(i) {
    var list = $('chatList'); if (!list) return;
    var nodes = Array.prototype.slice.call(list.querySelectorAll('.xiao6-node'));
    var n = nodes[i]; if (!n) return;
    list.scrollTo({ top: n.offsetTop - 24, behavior: 'smooth' });
    Array.prototype.forEach.call(list.parentNode.querySelectorAll('.xiao6-jump-mark'), function (m) { m.classList.toggle('is-active', m.dataset.idx == i); });
  }

  // ───────────────────── WIRING ─────────────────────
  function init() {
    // Composer 模式开关（思考 / 联网 / 语音输入 / 语音播报）
    qsa('.xiao6-mode').forEach(function (b) {
      b.addEventListener('click', function () {
        var t = b.dataset.tool;
        if (t === 'think') { state.toolModes.think = !state.toolModes.think; }
        else if (t === 'web') { state.toolModes.web = !state.toolModes.web; }
        else if (t === 'speak') { state.autoSpeak = !state.autoSpeak; state.lsSet('xiao6_autoSpeak', state.autoSpeak ? '1' : '0'); }
        else if (t === 'voice') { window.Xiao6.voice.startVoice(); return; }
        b.classList.toggle('is-on', (t === 'speak' ? state.autoSpeak : state.toolModes[t]));
      });
    });
    var speakBtn = qs('.xiao6-mode[data-tool="speak"]'); if (speakBtn) speakBtn.classList.toggle('is-on', state.autoSpeak);
    var webBtn = qs('.xiao6-mode[data-tool="web"]'); if (webBtn) webBtn.classList.toggle('is-on', !!state.toolModes.web);

    var cf = $('cmdForm');
    if (cf) cf.addEventListener('submit', function (e) {
      e.preventDefault();
      var v = ($('cmdInput').value || '');
      if (v.charAt(0) === '/' && window.Xiao6.palette && window.Xiao6.palette.runCommand(v)) { $('cmdInput').value = ''; return; }
      submitCmd(v);
    });
    var ci = $('cmdInput');
    if (ci) ci.addEventListener('input', function (e) { if (window.Xiao6.palette) window.Xiao6.palette.handleTrigger(e.target.value); });

    var jb = $('jumpbar'); if (jb) jb.hidden = false;
    var chatList = $('chatList');
    if (chatList) {
      var rafPending = false;
      chatList.addEventListener('scroll', function () { if (!rafPending) { rafPending = true; requestAnimationFrame(function () { rafPending = false; updateJumpbarThumb(); }); } });
      var mo = new MutationObserver(function () { buildJumpbar(); });
      mo.observe(chatList, { childList: true, subtree: true });
      setTimeout(buildJumpbar, 300);
    }
  }

  window.Xiao6.timeline = {
    addNode: addNode,
    scrollChat: scrollChat,
    addIntentNode: addIntentNode,
    addRiskNode: addRiskNode,
    sendChat: sendChat,
    submitCmd: submitCmd,
    renderWorkspace: renderWorkspace,
    renderResults: renderResults,
    buildJumpbar: buildJumpbar,
    init: init
  };
})();
