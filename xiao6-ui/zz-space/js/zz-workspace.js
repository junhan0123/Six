/* ═════════════════════════════════════════════════════════════════
   SIX · Advanced Workspace — app logic (zz-workspace.js)
   §3C/§3D/§3E/§3F · Presentation/Adapter only. No Core contract change.
   ═════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  // ───────────────────── helpers ─────────────────────
  function $(id) { return document.getElementById(id); }
  function qs(s) { return document.querySelector(s); }
  function qsa(s) { return Array.prototype.slice.call(document.querySelectorAll(s)); }
  function el(tag, cls, txt) { var n = document.createElement(tag); if (cls) n.className = cls; if (txt != null) n.textContent = txt; return n; }
  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
  function getJSON(url) {
    return fetch(url, { credentials: 'same-origin' })
      .then(function (r) { return r.ok ? r.json().catch(function () { return null; }) : null; })
      .catch(function () { return null; });
  }
  function postJSON(url, body) {
    return fetch(url, { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}) })
      .then(function (r) { return r.json().catch(function () { return null; }); })
      .catch(function () { return null; });
  }
  function asList(v, key) { if (Array.isArray(v)) return v; if (v && Array.isArray(v[key])) return v[key]; return []; }
  function fmtTime(ts) { var d = ts ? new Date(String(ts).replace(/-/g, '/')) : new Date(); if (isNaN(d.getTime())) d = new Date(); var p = function (n) { return n < 10 ? '0' + n : '' + n; }; return p(d.getHours()) + ':' + p(d.getMinutes()); }
  function relTime(ts) { if (!ts) return ''; var d = new Date(String(ts).replace(/-/g, '/')); if (isNaN(d.getTime())) return ''; var diff = Date.now() - d.getTime(); if (diff < 0) diff = 0; var min = Math.floor(diff / 60000); if (min < 1) return '刚刚'; if (min < 60) return min + ' 分钟前'; var hr = Math.floor(min / 60); if (hr < 24) return hr + ' 小时前'; var day = Math.floor(hr / 24); return day < 2 ? '昨天' : (day < 7 ? day + ' 天前' : (d.getMonth() + 1) + '/' + d.getDate()); }
  function greetWord() { var h = new Date().getHours(); if (h >= 5 && h < 11) return '早上好'; if (h >= 11 && h < 13) return '中午好'; if (h >= 13 && h < 18) return '下午好'; return '晚上好'; }

  // ───────────────────── state ─────────────────────
  var snap = { agent: { state: 'IDLE' }, tasks: [], goals: [], memories: [], notes: [], knowledge: { docs: [] }, capabilities: [], memory: {}, briefing: {}, calendar: {}, health: {} };
  var busy = false, listening = false, agentMode = false, toolModes = { think: false, web: true, code: 'auto' };
  var autoSpeak = (function () { try { return localStorage.getItem('zz_autoSpeak') !== '0'; } catch (e) { return true; } })();
  var sessionId = null;
  try { sessionId = localStorage.getItem('zhuangzhou_sid'); } catch (e) {}
  if (!sessionId) { sessionId = 'zz-' + Date.now(); try { localStorage.setItem('zhuangzhou_sid', sessionId); } catch (e) {} }
  var agentLog = []; // Agent Activity timeline entries
  var resultLog = []; // final results
  var lastResultText = '';

  // ───────────────────── toast / banner / overlay ─────────────────────
  function toast(msg, kind) {
    var layer = $('toastLayer'); if (!layer) return;
    var t = el('div', 'zz-toast' + (kind ? ' ' + kind : ''), msg);
    layer.appendChild(t);
    setTimeout(function () { t.style.opacity = '0'; setTimeout(function () { t.remove(); }, 250); }, 2200);
  }
  function showBanner(msg) { var b = $('banner'); if (!b) return; b.textContent = msg; b.hidden = false; }
  function hideBanner() { var b = $('banner'); if (b) b.hidden = true; }

  function openOverlay(title, hint, html, after) {
    $('overlayTitle').textContent = title;
    $('overlayHint').textContent = hint || '';
    $('overlayBody').innerHTML = html;
    $('overlay').setAttribute('aria-hidden', 'false');
    if (after) after();
  }
  function closeOverlay() { $('overlay').setAttribute('aria-hidden', 'true'); $('overlayBody').innerHTML = ''; }

  // ───────────────────── runtime / voice orb state ─────────────────────
  var CORE_TEXT = {
    IDLE: '在线待命', LISTENING: '倾听中', THINKING: '思考中', PLANNING: '规划中',
    EXECUTING: '工作中', SPEAKING: '回应中', WAITING_APPROVAL: '等待确认', ERROR: '异常', OFFLINE: '离线'
  };
  function setState(st, opts) {
    opts = opts || {};
    var low = String(st || 'IDLE').toLowerCase();
    // top runtime
    var rt = $('runtimeState');
    if (rt) { rt.dataset.mode = (low === 'thinking' || low === 'planning' || low === 'executing' || low === 'listening' || low === 'speaking') ? 'busy' : (low === 'error' || low === 'offline' ? 'off' : 'online'); rt.querySelector('b').textContent = CORE_TEXT[st] || '在线待命'; }
    // mini orb (top)
    var mo = qs('#orbBtn .zz-mini-orb'); if (mo) mo.dataset.state = low;
    // presence orb
    var op = $('orbPresence'); if (op) op.dataset.state = low;
    // context state dot
    var cs = $('ctxStateDot'); if (cs) { cs.className = 'zz-statedot ' + ((low === 'thinking' || low === 'executing' || low === 'listening') ? 'ongoing' : (low === 'error' ? 'error' : (low === 'idle' || low === 'offline' ? 'done' : 'done'))); }
    if (opts.ctxText && $('ctxStateText')) $('ctxStateText').textContent = opts.ctxText;
  }

  // ───────────────────── API snapshot ─────────────────────
  function fetchSnapshot() {
    return Promise.all([
      getJSON('/api/agent/state'), getJSON('/api/goals'), getJSON('/api/memories'),
      getJSON('/api/knowledge'), getJSON('/api/capabilities'), getJSON('/api/tasks'),
      getJSON('/api/health'), getJSON('/api/memory'), getJSON('/api/briefing'),
      getJSON('/api/calendar/events'), getJSON('/api/notes')
    ]).then(function (r) {
      snap.agent = r[0] || snap.agent;
      snap.goals = asList(r[1], 'goals');
      snap.memories = asList(r[2], 'memories');
      snap.knowledge = r[3] || {};
      snap.capabilities = (r[4] && Array.isArray(r[4].items)) ? r[4].items : asList(r[4], 'capabilities');
      snap.tasks = asList(r[5], 'tasks');
      snap.health = r[6] || {};
      snap.memory = r[7] || {};
      snap.briefing = r[8] || {};
      snap.calendar = r[9] || {};
      snap.notes = asList(r[10], 'notes');
      renderContextAuto();
      renderHome();
      renderListsIfVisible();
    });
  }

  // ───────────────────── INCREMENTAL STREAMING MARKDOWN (§9: no O(n²)) ─────────────────────
  // Block-based: completed blocks rendered once & cached; only the final (partial) block re-renders.
  function StreamingMarkdown(container) {
    this.container = container;
    this.renderedBlocks = 0; // number of leading blocks already permanently rendered
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
      // table detection
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
    if (b.type === 'code') {
      return '<pre><code>' + esc(b.code) + '</code></pre>';
    }
    if (b.type === 'table') {
      var rows = b.src.trim().split('\n'); var html = '<table>';
      for (var i = 0; i < rows.length; i++) {
        var cells = rows[i].replace(/^\||\|$/g, '').split('|').map(function (c) { return c.trim(); });
        if (i === 1) continue; // separator
        html += '<tr>' + cells.map(function (c) { return (i === 0 ? '<th>' : '<td>') + esc(c) + (i === 0 ? '</th>' : '</td>'); }).join('') + '</tr>';
      }
      return html + '</table>';
    }
    // paragraph / list lines -> inline formatting
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
    // render any newly-completed leading blocks permanently
    for (var i = this.renderedBlocks; i < n - 1; i++) {
      var be = el('div', 'zz-md-block'); be.innerHTML = this._renderBlock(blocks[i]);
      this.container.appendChild(be);
      this.renderedBlocks++;
    }
    // the final block (possibly partial) → re-render in tail element
    var tailBlock = blocks[n - 1];
    var html = tailBlock ? this._renderBlock(tailBlock) : '';
    if (!this.tailEl) { this.tailEl = el('div', 'zz-md-block'); this.container.appendChild(this.tailEl); }
    this.tailEl.innerHTML = html;
  };
  StreamingMarkdown.prototype.finalize = function () {
    if (this.tailEl) { this.tailEl.className = 'zz-md-block'; this.tailEl = null; }
    this.renderedBlocks = 0;
  };

  // ───────────────────── CHAT (typed ChatNode + SSE) ─────────────────────
  function addNode(kind, meta) {
    var node = el('div', 'zz-node ' + kind);
    var av = el('div', 'zz-avatar', kind === 'user' ? '你' : (kind === 'assistant' ? '庄' : (kind === 'tool' ? '⚙' : (kind === 'approval' ? '!' : (kind === 'result' ? '✓' : '·')))));
    var bub = el('div', 'zz-bubble');
    node.appendChild(av); node.appendChild(bub);
    $('chatList').appendChild(node);
    scrollChat();
    return { node: node, bub: bub };
  }
  function scrollChat() { var c = $('chatList'); if (c) c.scrollTop = c.scrollHeight; }

  function activePrefix() {
    var order = ['think', 'web', 'code'];
    var on = order.filter(function (k) { return toolModes[k]; });
    if (!on.length) return '';
    var names = { think: '深度思考', web: '联网搜索', code: '代码执行' };
    return '【' + on.map(function (k) { return names[k]; }).join('】【') + '】';
  }

  function sendChat(text, opts) {
    opts = opts || {};
    text = String(text || '').trim();
    if (!text || busy) return;
    var prefix = activePrefix();
    if (prefix && text.indexOf('【') !== 0) text = prefix + text;

    // user node
    var un = addNode('user'); un.bub.innerHTML = '<div class="zz-bubble-body">' + esc(text) + '</div>';

    busy = true; setState(snap.agent.state && String(snap.agent.state).toUpperCase() === 'IDLE' ? 'THINKING' : snap.agent.state);
    var an = addNode('assistant'); an.node.classList.add('streaming');
    var meta = el('div', 'zz-bubble-meta'); meta.innerHTML = '<span>小6</span><span>' + fmtTime() + '</span>';
    var body = el('div', 'zz-bubble-body');
    an.bub.appendChild(meta); an.bub.appendChild(body);
    var stream = new StreamingMarkdown(body);

    var payload = { messages: [{ role: 'user', content: text }], session_id: sessionId };

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
              // SSE 终止标记：解析后可能是 [DONE] 或 "[DONE]"（JSON 字符串形式）
              var m; try { m = JSON.parse(raw); } catch (e) { m = raw; }
              if (m === '[DONE]' || raw === '[DONE]') { done = true; finish(); return; }
              handle(m);
            }
            if (!done) return pump();
          });
        }
        function handle(m) {
          var ev = m.zhuangzhou_event || m.event;
          if (ev === 'tool_start') { onTool('start', m.tool, m.args); }
          else if (ev === 'tool_end') { onTool('end', m.tool, m.result, m.ok !== false); }
          else if (ev === 'approval') { onApproval(m); }
          else if (m.choices && m.choices[0] && m.choices[0].delta) {
            var dc = m.choices[0].delta.content || '';
            if (dc) { reply += dc; stream.update(reply); scrollChat(); }
          }
        }
        pump();
      })
      .catch(function (err) { busy = false; stream.finalize(); an.node.classList.remove('streaming'); an.bub.appendChild(el('div', 'zz-bubble-body')).innerHTML = '<span style="color:var(--zz-danger)">请求失败 · 请检查核心服务</span>'; setState('ERROR'); setTimeout(fetchSnapshot, 600); });

    function onTool(phase, tool, arg, ok) {
      if (phase === 'start') {
        agentLog.unshift({ kind: 'tool', t: Date.now(), tool: tool, arg: arg, ongoing: true });
        var tn = addNode('tool'); tn.bub.innerHTML = '<div class="zz-tool-summary">调用工具 <b>' + esc(tool || '') + '</b> …</div>';
        tn.dataset.toolnode = '1';
      } else {
        agentLog.forEach(function (x) { if (x.tool === tool && x.ongoing) { x.ongoing = false; x.ok = ok; } });
        qsa('.zz-node.tool').forEach(function (n) { if (n.dataset.toolnode) n.querySelector('.zz-tool-summary').innerHTML = '工具 <b>' + esc(tool || '') + '</b> ' + (ok === false ? '失败' : '完成'); });
        renderAgent();
      }
      renderAgent();
    }
    function onApproval(m) {
      var ticket = m.ticket || (m.approval && m.approval.ticket);
      var desc = m.prompt || (m.approval && m.approval.prompt) || '需要你的确认';
      var cn = addNode('approval');
      var card = el('div', 'zz-approval-card');
      card.innerHTML = '<div>' + esc(desc) + '</div>';
      var acts = el('div', 'zz-approval-act');
      var ok = el('button', 'approve', '批准'); var no = el('button', 'reject', '拒绝');
      acts.appendChild(ok); acts.appendChild(no); card.appendChild(acts);
      cn.bub.appendChild(card);
      ok.addEventListener('click', function () { postApproval(ticket, 'approve', cn, card); });
      no.addEventListener('click', function () { postApproval(ticket, 'reject', cn, card); });
    }
    function postApproval(ticket, decision, cn, card) {
      if (ticket) fetch('/api/agent/approval?ticket=' + encodeURIComponent(ticket) + '&decision=' + decision, { method: 'POST' }).catch(function () {});
      card.innerHTML = '<div>已' + (decision === 'approve' ? '批准' : '拒绝') + '</div>';
      toast(decision === 'approve' ? '已批准' : '已拒绝');
    }
    function finish() {
      busy = false; stream.finalize(); an.node.classList.remove('streaming');
      lastResultText = reply; resultLog.unshift({ t: Date.now(), text: reply });
      renderResults(); renderAgent();
      if (reply && autoSpeak) speakText(reply);
      setState(snap.agent.state || 'IDLE');
      setTimeout(fetchSnapshot, 1200);
    }
  }

  function speakText(text) {
    text = String(text || '').replace(/\s+/g, ' ').trim(); if (!text) return;
    fetch('/api/speak', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: text, stream: false }) })
      .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.blob(); })
      .then(function (blob) { var a = new Audio(URL.createObjectURL(blob)); a.onended = function () { URL.revokeObjectURL(a.src); }; a.play().catch(function () {}); })
      .catch(function () { /* 静默 */ });
  }

  // ───────────────────── VOICE (reuse Core contract; no 2nd engine) ─────────────────────
  function startVoice() {
    // W13 GUI→Voice: prefer the Electron orb window if present, else browser mic → /api/asr → /api/chat
    if (window.electronAPI && typeof window.electronAPI.focusOrb === 'function') { window.electronAPI.focusOrb(); return; }
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) { toast('当前环境不支持麦克风'); return; }
    toast('聆听中…说完自动识别');
    navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, sampleRate: 16000 } })
      .then(function (stream) {
        var AC = window.AudioContext || window.webkitAudioContext; var ctx = new AC({ sampleRate: 16000 });
        var src = ctx.createMediaStreamSource(stream); var an = ctx.createAnalyser(); an.fftSize = 2048; src.connect(an);
        var proc = ctx.createScriptProcessor(4096, 1, 1); var chunks = []; var speaking = false; var silent = 0;
        proc.onaudioprocess = function (e) {
          var d = e.inputBuffer.getChannelData(0); var pcm = new Int16Array(d.length);
          for (var i = 0; i < d.length; i++) { var s = Math.max(-1, Math.min(1, d[i])); pcm[i] = s < 0 ? s * 0x8000 : s * 0x7fff; }
          if (speaking) chunks.push(pcm.buffer);
          var rms = 0; for (var j = 0; j < d.length; j++) rms += d[j] * d[j]; rms = Math.sqrt(rms / d.length);
          if (rms > 0.02) { speaking = true; silent = 0; } else if (speaking) { silent++; if (silent > 70) finish(); }
        };
        an.connect(proc); proc.connect(ctx.destination);
        function finish() {
          try { proc.disconnect(); an.disconnect(); src.disconnect(); ctx.close().catch(function () {}); stream.getTracks().forEach(function (t) { t.stop(); }); } catch (e) {}
          if (!chunks.length) { toast('未检测到语音'); return; }
          var total = 0; chunks.forEach(function (c) { total += c.byteLength; });
          var merged = new Int16Array(total / 2); var off = 0;
          chunks.forEach(function (c) { var a = new Int16Array(c); merged.set(a, off); off += a.length; });
          var wav = pcmToWav(merged, 16000); var blob = new Blob([wav], { type: 'audio/wav' });
          var fd = new FormData(); fd.append('audio', blob, 'u.wav');
          fetch('/api/asr?ext=.wav', { method: 'POST', body: fd, credentials: 'same-origin' }).then(function (r) { return r.json(); }).then(function (d) {
            var t = (d && d.text) || ''; if (t.trim()) { $('cmdInput').value = t; submitCmd(t); } else toast('未识别到内容');
          }).catch(function () { toast('语音识别失败'); });
        }
      }).catch(function () { toast('无法访问麦克风'); });
  }
  function pcmToWav(samples, sr) {
    var len = samples.length, buf = new ArrayBuffer(44 + len * 2), v = new DataView(buf);
    function ws(o, s) { for (var i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); }
    ws(0, 'RIFF'); v.setUint32(4, 36 + len * 2, true); ws(8, 'WAVE'); ws(12, 'fmt '); v.setUint32(16, 16, true);
    v.setUint16(20, 1, true); v.setUint16(22, 1, true); v.setUint32(24, sr, true); v.setUint32(28, sr * 2, true);
    v.setUint16(32, 2, true); v.setUint16(34, 16, true); ws(36, 'data'); v.setUint32(40, len * 2, true);
    for (var i = 0; i < len; i++) v.setInt16(44 + i * 2, samples[i], true);
    return new Uint8Array(buf);
  }

  function submitCmd(text) {
    var view = document.body.dataset.view;
    if (view !== 'conversation') switchView('conversation');
    sendChat(text);
  }

  // ───────────────────── VIEW ROUTING ─────────────────────
  function switchView(name) {
    document.body.dataset.view = name;
    qsa('.zz-view').forEach(function (v) { v.hidden = (v.dataset.view !== name); });
    qsa('.zz-nav-btn').forEach(function (b) { b.classList.toggle('is-active', b.dataset.nav === name); });
    if (name === 'home') renderHome();
    else if (name === 'tasks') renderTasks();
    else if (name === 'projects') renderProjects();
    else if (name === 'memory') renderMemory();
    else if (name === 'knowledge') renderKnowledge();
    else if (name === 'capabilities') renderCapabilities();
    else if (name === 'sessions') renderSessions();
    else if (name === 'settings') renderSettings();
  }

  // ───────────────────── HOME ─────────────────────
  function renderHome() {
    $('homeGreet').textContent = greetWord();
    var w = snap.briefing && snap.briefing.weather;
    $('homeSub').textContent = w ? (greetWord() + ' · 当前 ' + w.temp + '℃ ' + (w.condition || '')) : '小6随时待命 · 告诉我今天想完成什么';
    // runtime line
    var rl = $('homeRuntime'); if (rl) rl.innerHTML = '<i class="zz-dot"></i><span>' + (CORE_TEXT[String(snap.agent.state || 'IDLE').toUpperCase()] || '在线待命') + '</span>';
    var hc = snap.health || {}; $('homeCtx').textContent = '模型 ' + (hc.model || '—') + ' · 能力 ' + (snap.capabilities || []).length + ' 项';
    // recent work (last chat history)
    var rc = $('homeRecent'); if (rc) {
      getJSON('/api/chat/history?limit=6').then(function (d) {
        var msgs = []; (d && d.sessions || []).forEach(function (s) { (s.turns || []).forEach(function (t) { msgs.push(t); }); });
        msgs = msgs.slice(-5);
        rc.innerHTML = msgs.length ? msgs.map(function (m) { return '<div class="zz-home-item"><span class="dot"></span><span>' + esc(String(m.content || '').slice(0, 40)) + '</span></div>'; }).join('') : '<span class="zz-empty">暂无对话</span>';
      });
    }
    // active tasks
    var ht = $('homeTasks'); if (ht) {
      var open = snap.tasks.filter(function (t) { var s = String(t.status || '').toLowerCase(); return s !== 'done' && s !== 'completed' && s !== 'closed'; }).slice(0, 4);
      ht.innerHTML = open.length ? open.map(function (t) { return '<div class="zz-home-item"><span class="dot"></span><span>' + esc(t.title || '任务') + '</span></div>'; }).join('') : '<span class="zz-empty">暂无进行中的任务</span>';
    }
    // quick actions
    var qa = $('homeQuick'); if (qa) {
      var acts = [
        { label: '总结今天', cmd: '总结一下今天的情况和待办' },
        { label: '搜索资料', cmd: '帮我联网搜索相关资料' },
        { label: '新建目标', run: function () { openGoalForm(); } },
        { label: '打开记忆', go: 'memory' }
      ];
      qa.innerHTML = '';
      acts.forEach(function (a) { var b = el('button', null, a.label); b.addEventListener('click', function () { if (a.go) switchView(a.go); else if (a.run) a.run(); else submitCmd(a.cmd); }); qa.appendChild(b); });
    }
  }

  // ───────────────────── LIST VIEWS ─────────────────────
  function isOpen(t) { var s = String(t.status || '').toLowerCase(); return s !== 'done' && s !== 'completed' && s !== 'closed'; }
  function isDone(t) { var s = String(t.status || '').toLowerCase(); return s === 'done' || s === 'completed' || s === 'closed'; }

  function renderTasks() {
    var list = $('tasksList'); if (!list) return;
    var tasks = snap.tasks.slice().sort(function (a, b) { return Number(a.id) - Number(b.id); });
    list.innerHTML = tasks.length ? tasks.map(function (t) {
      var open = isOpen(t);
      return row('✓', t.title || ('任务 #' + t.id), (t.status || '') + (t.updated ? ' · ' + relTime(t.updated) : ''), open ? 'run' : 'done', open ? '进行中' : '已完成');
    }).join('') : '<span class="zz-empty">暂无任务</span>';
  }
  function renderProjects() {
    var list = $('projectsList'); if (!list) return;
    var goals = snap.goals.slice().sort(function (a, b) { return String(b.updated || '').localeCompare(String(a.updated || '')); });
    list.innerHTML = goals.length ? goals.map(function (g) {
      var s = String(g.status || ''); var prog = Number(g.progress || 0);
      return row('◆', g.title || ('目标 #' + g.id), s + ' · 进度 ' + prog + '%', s === 'active' ? 'run' : 'done', s);
    }).join('') : '<span class="zz-empty">暂无项目/目标</span>';
  }
  function renderMemory() {
    var list = $('memoryList'); if (!list) return;
    var mems = snap.memories.slice().sort(function (a, b) { return Number(b.id) - Number(a.id); });
    list.innerHTML = mems.length ? mems.map(function (m) {
      var title = String(m.title || m.content || '记忆').replace(/^Hotspot event:\s*/, '').slice(0, 80);
      return row('◷', title, (m.event_type || 'memory') + (m.ts ? ' · ' + relTime(m.ts) : ''), '', '');
    }).join('') : '<span class="zz-empty">暂无记忆 · 与小6对话后自动沉淀</span>';
  }
  function renderKnowledge() {
    var list = $('knowledgeList'); if (!list) return;
    var docs = asList(snap.knowledge, 'docs');
    list.innerHTML = docs.length ? docs.map(function (d) {
      return row('▤', d.title || '文档', (d.domain || '其他') + (d.tags && d.tags.length ? ' · ' + d.tags.join(',') : ''), '', '');
    }).join('') : '<span class="zz-empty">知识库为空</span>';
  }
  function renderCapabilities() {
    var list = $('capabilitiesList'); if (!list) return;
    var caps = snap.capabilities;
    list.innerHTML = caps.length ? caps.map(function (c) {
      return row(c.icon || '⚡', c.label || c.id, c.description || (c.group || ''), c.active ? 'done' : 'run', c.active ? '激活' : '待命');
    }).join('') : '<span class="zz-empty">暂无能⼒数据</span>';
  }
  function renderSessions() {
    var list = $('sessionsList'); if (!list) return;
    getJSON('/api/chat/history?limit=50').then(function (d) {
      var msgs = []; (d && d.sessions || []).forEach(function (s) { (s.turns || []).forEach(function (t) { msgs.push(t); }); });
      list.innerHTML = msgs.length ? msgs.slice(-30).reverse().map(function (m) {
        return row(m.role === 'user' ? '你' : '庄', String(m.content || '').slice(0, 60), m.ts ? relTime(m.ts) : '', '', '');
      }).join('') : '<span class="zz-empty">暂无对话记录</span>';
    });
  }
  function renderListsIfVisible() {
    var v = document.body.dataset.view;
    if (v === 'tasks') renderTasks();
    else if (v === 'projects') renderProjects();
    else if (v === 'memory') renderMemory();
    else if (v === 'knowledge') renderCapabilities();
    else if (v === 'sessions') renderSessions();
  }
  function row(ic, t, s, tagCls, tagTxt) {
    return '<div class="zz-row"><div class="ic">' + esc(ic) + '</div><div class="body"><div class="t">' + esc(t) + '</div>' + (s ? '<div class="s">' + esc(s) + '</div>' : '') + '</div>' + (tagTxt ? '<span class="tag ' + (tagCls || '') + '">' + esc(tagTxt) + '</span>' : '') + '</div>';
  }

  // ───────────────────── CENTER TABS (conversation/workspace/results/agent) ─────────────────────
  function switchConvTab(tab) {
    qsa('.zz-tab').forEach(function (b) { b.classList.toggle('is-active', b.dataset.tab === tab); });
    $('convBody').hidden = tab !== 'conversation';
    $('wsBody').hidden = tab !== 'workspace';
    $('resBody').hidden = tab !== 'results';
    $('agentBody').hidden = tab !== 'agent';
    if (tab === 'workspace') renderWorkspace();
    if (tab === 'results') renderResults();
    if (tab === 'agent') renderAgent();
  }
  function renderWorkspace() {
    var list = $('wsList'); if (!list) return;
    var open = snap.tasks.filter(function (t) { return isOpen(t) && t.current_step != null && t.total_steps; }).slice(0, 8);
    var running = Number((snap.agent || {}).running || 0);
    if (!open.length && !running) { $('wsEmpty').hidden = false; list.innerHTML = ''; return; }
    $('wsEmpty').hidden = true;
    var html = '';
    open.forEach(function (t) { var p = t.total_steps ? Math.round(t.current_step / t.total_steps * 100) : 0;
      html += '<div class="zz-ws-card"><div class="ttl">⚙ ' + esc(t.title || '任务') + '</div><div class="meta">步骤 ' + t.current_step + '/' + t.total_steps + '</div><div class="zz-prog"><i style="width:' + p + '%"></i></div></div>'; });
    if (running > 0) html += '<div class="zz-ws-card"><div class="ttl">◌ 小6核心执行中</div><div class="meta">运行 ' + running + ' 项</div><div class="zz-prog"><i style="width:100%"></i></div></div>';
    list.innerHTML = html;
  }
  function renderResults() {
    var list = $('resList'); if (!list) return;
    if (!resultLog.length) { list.innerHTML = '<span class="zz-empty">暂无结果</span>'; return; }
    list.innerHTML = resultLog.slice(0, 12).map(function (r) {
      var sm = new StreamingMarkdown(el('div')); sm.update(r.text); sm.finalize();
      return '<div class="zz-res-card"><div class="zz-bubble-meta"><span>小6</span><span>' + fmtTime(r.t) + '</span></div>' + sm.container.innerHTML + '</div>';
    }).join('');
  }
  function renderAgent() {
    var list = $('agentList'); if (!list) return;
    if (!agentLog.length) { list.innerHTML = '<span class="zz-empty">暂无 Agent 活动</span>'; return; }
    var icon = { input: '▸', model: '◈', tool: '⚙', result: '✓', error: '✕', approval: '!' };
    list.innerHTML = agentLog.slice(0, 40).map(function (x) {
      var txt = x.kind === 'tool' ? ('工具 ' + (x.tool || '') + (x.ongoing ? ' 运行中…' : (x.ok === false ? ' 失败' : ' 完成')))
        : (x.kind === 'input' ? ('输入：' + (x.text || '')) : (x.kind === 'result' ? ('结果：' + (x.text || '').slice(0, 80)) : (x.text || '')));
      return '<div class="zz-agent-item ' + x.kind + '"><div class="zz-agent-ic">' + (icon[x.kind] || '·') + '</div><div class="zz-agent-body-txt"><div>' + esc(txt) + '</div><div class="t">' + fmtTime(x.t) + '</div></div></div>';
    }).join('');
  }

  // ───────────────────── RIGHT CONTEXT (dynamic stack) ─────────────────────
  function renderContextAuto() {
    var st = String(snap.agent.state || 'IDLE').toUpperCase();
    var body = $('ctxBody'); if (!body) return;
    if (st === 'EXECUTING' || busy) { renderContext('tasks'); }
    else if (st === 'WAITING_APPROVAL') { renderContext('approval'); }
    else if (document.body.dataset.view === 'memory') { renderContext('memory'); }
    else if (document.body.dataset.view === 'capabilities') { renderContext('capability'); }
    else if (resultLog.length) { renderContext('result'); }
    else { renderContext('context'); }
  }
  function renderContext(kind) {
    var body = $('ctxBody'); if (!body) return;
    $('ctxTitle').textContent = { context: '上下文', tasks: '任务进度', memory: '记忆', capability: '能力', result: '最新结果', approval: '待确认' }[kind] || '上下文';
    var html = '';
    if (kind === 'context') {
      html += ctxCard('运行时', '<div class="zz-ctx-state"><span class="zz-statedot ' + ((String(snap.agent.state || '').toUpperCase() === 'ERROR') ? 'error' : 'done') + '" id="ctxStateDot"><span class="sd"></span></span><span id="ctxStateText">' + (CORE_TEXT[String(snap.agent.state || 'IDLE').toUpperCase()] || '在线待命') + '</span></div>');
      var w = snap.briefing && snap.briefing.weather;
      html += ctxCard('当前上下文', '<div class="zz-ctx-item"><span class="dot"></span><span>' + (w ? (w.condition + ' ' + w.temp + '℃') : '无天气数据') + '</span></div>' + ctxItem('能力 ' + (snap.capabilities || []).length + ' · 记忆 ' + (snap.memories || []).length));
    } else if (kind === 'tasks') {
      var open = snap.tasks.filter(isOpen).slice(0, 6);
      html += ctxCard('进行中的任务', open.length ? open.map(function (t) { return ctxItem(t.title || '任务'); }).join('') : '<span class="zz-empty">无</span>');
    } else if (kind === 'memory') {
      var mems = snap.memories.slice(0, 5);
      html += ctxCard('近期记忆', mems.length ? mems.map(function (m) { return ctxItem(String(m.title || m.content || '').slice(0, 40)); }).join('') : '<span class="zz-empty">无</span>');
    } else if (kind === 'capability') {
      var caps = snap.capabilities.slice(0, 6);
      html += ctxCard('能力', caps.length ? caps.map(function (c) { return ctxItem((c.icon || '') + ' ' + (c.label || c.id)); }).join('') : '<span class="zz-empty">无</span>');
    } else if (kind === 'result') {
      html += ctxCard('最新结果', ctxItem((lastResultText || '').slice(0, 120)));
    } else if (kind === 'approval') {
      html += ctxCard('待确认', '<div class="zz-ctx-state"><span class="zz-statedot warning"><span class="sd"></span></span><span>有一项操作需要你确认</span></div>');
    }
    body.innerHTML = html;
  }
  function ctxCard(t, body) { return '<div class="zz-ctx-card"><div class="ct">' + esc(t) + '</div>' + body + '</div>'; }
  function ctxItem(t) { return '<div class="zz-ctx-item"><span class="dot"></span><span>' + esc(t) + '</span></div>'; }

  // ───────────────────── SETTINGS (§19: developer/infra hidden by default) ─────────────────────
  function renderSettings() {
    var body = $('settingsBody'); if (!body) return;
    var h = snap.health || {}, a = snap.agent || {};
    var html = '';
    html += '<div class="zz-set-group"><h3>功能偏好</h3>' +
      setRow('web', '联网搜索', '默认开启，搜索时自动联网', toolModes.web) +
      setRow('think', '深度思考', '回复前先进行深度推理', toolModes.think) +
      setRow('speak', '语音播报', '回复完成后自动朗读', autoSpeak) + '</div>';
    html += '<div class="zz-set-group"><h3>系统概览</h3>' +
      kvRow('目标 / 任务', snap.goals.length + ' / ' + snap.tasks.filter(isOpen).length) +
      kvRow('记忆 / 知识', (snap.memories || []).length + ' / ' + asList(snap.knowledge, 'docs').length) +
      kvRow('能力登记', (snap.capabilities || []).length + ' 项') +
      kvRow('模型', h.model || '—') +
      kvRow('提供方', h.provider || '—') +
      kvRow('TTS 引擎', h.tts_backend || '—') + '</div>';
    body.innerHTML = html;
    body.addEventListener('change', function (e) { var sw = e.target.closest('.zz-switch'); if (!sw) return; var k = sw.dataset.key; if (k === 'web') toolModes.web = sw.classList.contains('on'); else if (k === 'think') toolModes.think = sw.classList.contains('on'); else if (k === 'speak') { autoSpeak = sw.classList.contains('on'); try { localStorage.setItem('zz_autoSpeak', autoSpeak ? '1' : '0'); } catch (e) {} } });
  }
  function setRow(key, label, desc, on) { return '<div class="zz-set-row"><span class="k">' + esc(label) + '<small>' + esc(desc) + '</small></span><span class="zz-switch ' + (on ? 'on' : '') + '" data-key="' + key + '"></span></div>'; }
  function kvRow(k, v) { return '<div class="zz-set-row"><span class="k">' + esc(k) + '</span><span class="v">' + esc(v) + '</span></div>'; }

  // ───────────────────── FEATURE REGISTRY (§19: classify 47 features A–F + visibility) ─────────────────────
  // Derived from Six Hub features.json (real ids). Single Source of Truth for GUI surfacing.
  var FEATURE_REGISTRY = [
    { id: 'start-all', name: '启动小6', cat: 'E', vis: 'hidden' },
    { id: 'web-ui', name: '对话界面', cat: 'A', vis: 'default' },
    { id: 'avatar-ui', name: '数字人界面', cat: 'C', vis: 'hidden' },
    { id: 'open-project', name: '打开项目目录', cat: 'C', vis: 'hidden' },
    { id: 'health', name: '后端健康', cat: 'D', vis: 'hidden' },
    { id: 'ready', name: '就绪状态', cat: 'D', vis: 'hidden' },
    { id: 'boot-state', name: '启动状态机', cat: 'D', vis: 'hidden' },
    { id: 'sysmon', name: '系统监控', cat: 'D', vis: 'hidden' },
    { id: 'logs', name: '后端日志', cat: 'D', vis: 'hidden' },
    { id: 'selfcheck', name: '启动自检', cat: 'D', vis: 'hidden' },
    { id: 'capabilities', name: '能力目录', cat: 'A', vis: 'default' },
    { id: 'capability-os', name: 'Capability OS', cat: 'B', vis: 'advanced' },
    { id: 'version', name: '版本信息', cat: 'D', vis: 'hidden' },
    { id: 'asr-status', name: '语音识别状态', cat: 'D', vis: 'advanced' },
    { id: 'wakeword', name: '唤醒词状态', cat: 'D', vis: 'advanced' },
    { id: 'system-prompt', name: '系统提示词', cat: 'B', vis: 'advanced' },
    { id: 'memory', name: '记忆中心', cat: 'A', vis: 'default' },
    { id: 'conversations', name: '对话历史', cat: 'A', vis: 'default' },
    { id: 'important-dates', name: '重要日期', cat: 'A', vis: 'default' },
    { id: 'notes', name: '笔记', cat: 'A', vis: 'default' },
    { id: 'knowledge', name: '知识库', cat: 'A', vis: 'default' },
    { id: 'user-model', name: '用户画像', cat: 'B', vis: 'advanced' },
    { id: 'personal-ai', name: 'Personal AI 画像', cat: 'B', vis: 'advanced' },
    { id: 'episodes', name: '情节记忆', cat: 'B', vis: 'advanced' },
    { id: 'tasks', name: '任务列表', cat: 'A', vis: 'default' },
    { id: 'goals', name: '目标列表', cat: 'A', vis: 'default' },
    { id: 'weather', name: '天气', cat: 'A', vis: 'default' },
    { id: 'hotspots', name: '热点', cat: 'A', vis: 'default' },
    { id: 'geo', name: '定位与天气', cat: 'A', vis: 'default' },
    { id: 'briefing', name: '每日简报', cat: 'A', vis: 'default' },
    { id: 'calendar', name: '日历事件', cat: 'A', vis: 'conditional' },
    { id: 'perception-status', name: '感知状态', cat: 'B', vis: 'advanced' },
    { id: 'perception-screen', name: '屏幕信息', cat: 'B', vis: 'advanced' },
    { id: 'perception-window', name: '活动窗口', cat: 'B', vis: 'advanced' },
    { id: 'perception-ocr', name: '屏幕 OCR', cat: 'B', vis: 'advanced' },
    { id: 'perception-describe', name: '屏幕描述', cat: 'B', vis: 'advanced' },
    { id: 'proactive-status', name: '主动智能状态', cat: 'B', vis: 'advanced' },
    { id: 'proactive-agent', name: 'Proactive Agent', cat: 'B', vis: 'advanced' },
    { id: 'self-awareness', name: '自我认知', cat: 'B', vis: 'advanced' },
    { id: 'agent-state', name: 'Agent 状态', cat: 'A', vis: 'default' },
    { id: 'hud-state', name: 'HUD 状态', cat: 'B', vis: 'advanced' },
    { id: 'focus-app', name: '应用焦点', cat: 'A', vis: 'conditional' },
    { id: 'clipboard', name: '剪贴板历史', cat: 'A', vis: 'conditional' },
    { id: 'export-data', name: '数据导出', cat: 'C', vis: 'hidden' },
    { id: 'open-config', name: '打开配置目录', cat: 'C', vis: 'hidden' },
    { id: 'open-docs', name: '打开文档目录', cat: 'C', vis: 'hidden' },
    { id: 'github', name: 'GitHub 仓库', cat: 'C', vis: 'hidden' }
  ];
  // visibility resolution (§19): conditional → only if capability enabled
  function featureVisible(f) {
    if (f.vis === 'default') return true;
    if (f.vis === 'advanced') return false; // Command Palette / Right Context only
    if (f.vis === 'hidden') return false;
    if (f.vis === 'conditional') {
      if (f.id === 'calendar') return !!(snap.calendar && snap.calendar.enabled);
      if (f.id === 'focus-app') return !!(snap.health && snap.health.focus_app);
      if (f.id === 'clipboard') return !!(snap.health && snap.health.clipboard);
    }
    return false;
  }

  // ───────────────────── R8-UI RECOVERY: REAL-TIME STREAM + GOAL/INTENT BINDINGS ─────────────────────
  // 只做 UI → API 对接（复用既有 EventSource 语义 / openOverlay / toast / agentLog / addNode），
  // 不重设计 EventBus，不新增后端接口。
  function renderStreamApproval(ev) {
    var ticket = ev.ticket, tool = ev.tool || '', summary = ev.summary || ('有一项操作需要确认（' + tool + '）');
    agentLog.unshift({ kind: 'approval', t: Date.now(), text: '等待确认：' + tool + ' · ' + summary });
    renderAgent();
    var cn = addNode('approval');
    var card = el('div', 'zz-approval-card');
    card.innerHTML = '<div>' + esc(summary) + '</div>';
    var acts = el('div', 'zz-approval-act');
    var ok = el('button', 'approve', '批准'); var no = el('button', 'reject', '拒绝');
    acts.appendChild(ok); acts.appendChild(no); card.appendChild(acts);
    cn.bub.appendChild(card);
    ok.addEventListener('click', function () { postApprovalStandalone(ticket, 'approve', cn, card); });
    no.addEventListener('click', function () { postApprovalStandalone(ticket, 'reject', cn, card); });
    toast('有一项操作需要确认');
  }
  function postApprovalStandalone(ticket, decision, cn, card) {
    if (ticket) fetch('/api/agent/approval?ticket=' + encodeURIComponent(ticket) + '&decision=' + decision, { method: 'POST' }).catch(function () {});
    card.innerHTML = '<div>已' + (decision === 'approve' ? '批准' : '拒绝') + '</div>';
    toast(decision === 'approve' ? '已批准' : '已拒绝');
  }
  function startStream() {
    if (!('EventSource' in window)) return;
    var es = new EventSource('/api/stream');
    es.onmessage = function (e) {
      var m; try { m = JSON.parse(e.data); } catch (err) { return; }
      var ev = m.zhuangzhou_event || m.event;
      if (!ev) return;
      if (ev === 'modal') {
        if (m.kind === 'agent_approval') renderStreamApproval(m);
      } else if (ev === 'tool_started') {
        agentLog.unshift({ kind: 'tool', t: Date.now(), tool: m.task || m.tool || '', ongoing: true });
        renderAgent();
      } else if (ev === 'tool_finished') {
        var tname = m.task || m.tool || '';
        agentLog.forEach(function (x) { if (x.tool === tname && x.ongoing) { x.ongoing = false; x.ok = m.ok !== false; } });
        renderAgent();
      } else if (ev === 'execution_started' || ev === 'execution_completed' || ev === 'execution_cancelled') {
        agentLog.unshift({ kind: ev === 'execution_completed' ? 'result' : 'model', t: Date.now(),
          text: '执行 ' + (m.task || '') + (ev === 'execution_started' ? ' 开始' : ev === 'execution_completed' ? ' 完成' : ' 取消') });
        renderAgent();
      } else if (ev.indexOf('GOAL_') === 0 || ev.indexOf('TASK_') === 0 || ev.indexOf('INTENT_') === 0 || ev.indexOf('AGENT_') === 0) {
        var p = m.payload || {};
        var label = { GOAL_CREATED: '目标已创建', GOAL_PLANNED: '目标已规划', GOAL_STARTED: '目标已启动', GOAL_RUNNING: '目标执行中', GOAL_COMPLETED: '目标已完成', GOAL_FAILED: '目标失败', TASK_CREATED: '任务已创建', TASK_STARTED: '任务开始', TASK_RUNNING: '任务执行中', TASK_COMPLETED: '任务完成', TASK_FAILED: '任务失败', INTENT_CLASSIFIED: '意图已识别', INTENT_ACCEPTED: '意图已接受', INTENT_REJECTED: '意图已拒绝', INTENT_CONVERTED_TO_GOAL: '意图转为目标', AGENT_COMPLETED: 'Agent 完成', AGENT_FAILED: 'Agent 失败' }[ev] || ev;
        agentLog.unshift({ kind: (ev.indexOf('GOAL') === 0 || ev.indexOf('TASK') === 0) ? 'result' : 'model', t: Date.now(), text: label + (p.title ? '：' + p.title : '') });
        renderAgent();
        if (ev === 'GOAL_CREATED' || ev === 'GOAL_COMPLETED' || ev === 'GOAL_FAILED' || ev === 'TASK_COMPLETED' || ev === 'TASK_FAILED') toast(label);
        fetchSnapshot();
      }
    };
  }
  function openGoalForm() {
    openOverlay('新建目标', 'POST /api/agent/goal → Agent Runtime', 
      '<div style="display:flex;flex-direction:column;gap:10px">' +
      '<input id="goalTitle" class="zz-cmd-input" placeholder="目标标题（必填）" style="width:100%" />' +
      '<input id="goalDesc" class="zz-cmd-input" placeholder="目标描述（可选）" style="width:100%" />' +
      '<button id="goalSubmit" class="zz-send" type="button" style="align-self:flex-start">创建目标</button>' +
      '<div id="goalResult" class="zz-tool-summary"></div></div>',
      function () {
        $('goalSubmit').addEventListener('click', function () {
          var title = $('goalTitle').value.trim(); if (!title) { toast('请输入目标标题'); return; }
          $('goalSubmit').disabled = true;
          postJSON('/api/agent/goal', { title: title, description: $('goalDesc').value.trim() }).then(function (d) {
            $('goalSubmit').disabled = false;
            if (d && d.ok) {
              $('goalResult').innerHTML = '<b>创建成功</b> · goalId=' + d.goalId + ' · ' + esc(d.title);
              toast('目标已创建 #' + d.goalId);
              fetchSnapshot();
            } else {
              $('goalResult').innerHTML = '<span style="color:var(--zz-danger)">失败：' + esc((d && d.error) || '未知错误') + '</span>';
            }
          });
        });
      });
  }
  function openIntentForm() {
    openOverlay('意图识别', 'POST /api/agent/intent → IntentGateway → GDE',
      '<div style="display:flex;flex-direction:column;gap:10px">' +
      '<input id="intentText" class="zz-cmd-input" placeholder="输入用户意图文本" style="width:100%" />' +
      '<button id="intentSubmit" class="zz-send" type="button" style="align-self:flex-start">识别意图</button>' +
      '<div id="intentResult" class="zz-tool-summary"></div></div>',
      function () {
        $('intentSubmit').addEventListener('click', function () {
          var text = $('intentText').value.trim(); if (!text) { toast('请输入意图文本'); return; }
          $('intentSubmit').disabled = true;
          postJSON('/api/agent/intent', { text: text, source: 'ui_workspace' }).then(function (d) {
            $('intentSubmit').disabled = false;
            if (d && d.ok) {
              var cls = { create: '创建目标', propose: '建议确认', resume: '恢复目标', skip: '跳过' }[d.action] || d.action;
              $('intentResult').innerHTML = '<b>' + esc(cls) + '</b> · 分类 ' + esc(d.classification) + ' · 置信度 ' + Math.round((d.confidence || 0) * 100) + '%' +
                (d.goalId ? ' · goalId=' + d.goalId : '') +
                (d.reason ? '<br/><span style="color:var(--zz-text-muted)">' + esc(d.reason) + '</span>' : '');
              toast('意图识别：' + cls);
              if (d.goalId) fetchSnapshot();
            } else {
              $('intentResult').innerHTML = '<span style="color:var(--zz-danger)">失败：' + esc((d && d.error) || '未知错误') + '</span>';
            }
          });
        });
      });
  }

  // ───────────────────── COMMAND PALETTE (§13) + TRIGGER (§14) ─────────────────────
  var COMMANDS = [
    { id: 'ask', name: '问小6', desc: '直接对小6说话', group: '命令', run: function () { switchView('conversation'); $('cmdInput').focus(); } },
    { id: 'search', name: '联网搜索', desc: '搜索资料', group: '命令', run: function () { submitCmd('帮我联网搜索相关资料'); } },
    { id: 'task', name: '运行任务', desc: '让小6完成一件事', group: '命令', run: function () { switchView('conversation'); $('cmdInput').value = '帮我完成一个任务：'; $('cmdInput').focus(); } },
    { id: 'goal', name: '新建目标', desc: '创建目标并交给 Agent 执行（POST /api/agent/goal）', group: '命令', run: function () { openGoalForm(); } },
    { id: 'intent', name: '意图识别', desc: '提交意图 → GDE 决策（POST /api/agent/intent）', group: '命令', run: function () { openIntentForm(); } },
    { id: 'memory', name: '打开记忆', desc: '查看小6记住的内容', group: '导航', run: function () { switchView('memory'); } },
    { id: 'capabilities', name: '打开能力', desc: '查看已登记能力', group: '导航', run: function () { switchView('capabilities'); } },
    { id: 'projects', name: '打开项目', desc: '查看目标与项目', group: '导航', run: function () { switchView('projects'); } },
    { id: 'tasks', name: '打开任务', desc: '查看任务清单', group: '导航', run: function () { switchView('tasks'); } },
    { id: 'settings', name: '设置', desc: '偏好与系统概览', group: '导航', run: function () { switchView('settings'); } },
    { id: 'voice', name: '语音输入', desc: '用语音对小6说话', group: '命令', run: function () { startVoice(); } }
  ];
  // append feature-derived commands (advanced + conditional-visible) to palette
  FEATURE_REGISTRY.forEach(function (f) {
    if (f.vis === 'advanced' || f.vis === 'conditional') {
      COMMANDS.push({ id: 'feat:' + f.id, name: f.name, desc: '能力 · ' + f.id, group: '能力', feat: f.id, run: function () { openFeature(f.id); } });
    }
  });
  function openFeature(id) {
    // GUI is Presentation/Adapter: surface via existing backend API (read-only GET) in overlay
    var f = FEATURE_REGISTRY.filter(function (x) { return x.id === id; })[0]; if (!f) return;
    openOverlay(f.name, '能力 · /api/' + id.replace(/-/g, '/').replace('capability/os', 'capability_os'), '<div class="zz-loading">读取中…</div>', function () {
      getJSON('/api/' + id.replace(/-/g, '/').replace('capability/os', 'capability_os')).then(function (d) {
        $('overlayBody').innerHTML = '<pre style="white-space:pre-wrap;word-break:break-word;font-size:12.5px">' + esc(JSON.stringify(d, null, 2) || '（空）') + '</pre>';
      }).catch(function () { $('overlayBody').innerHTML = '<span class="zz-empty">读取失败</span>'; });
    });
  }

  var palActive = -1, palItems = [];
  function openPalette() {
    var p = $('palette'); p.setAttribute('aria-hidden', 'false');
    var inp = $('paletteInput'); inp.value = ''; palActive = 0; renderPalette(''); setTimeout(function () { inp.focus(); }, 30);
  }
  function closePalette() { $('palette').setAttribute('aria-hidden', 'true'); }
  function fuzzy(s, q) { s = String(s).toLowerCase(); q = String(q).toLowerCase(); if (!q) return true; if (s.indexOf(q) >= 0) return true; var i = 0; for (var j = 0; j < q.length; j++) { i = s.indexOf(q[j], i); if (i < 0) return false; i++; } return true; }
  function renderPalette(q) {
    var list = $('paletteList'); list.innerHTML = '';
    palItems = COMMANDS.filter(function (c) { return fuzzy(c.name, q) || fuzzy(c.desc, q); });
    if (!palItems.length) { list.innerHTML = '<div class="zz-palette-group">无匹配命令</div>'; return; }
    var groups = {}; palItems.forEach(function (c) { (groups[c.group] = groups[c.group] || []).push(c); });
    Object.keys(groups).forEach(function (g) {
      list.appendChild(el('div', 'zz-palette-group', g));
      groups[g].forEach(function (c, idx) {
        var globalIdx = palItems.indexOf(c);
        var item = el('div', 'zz-palette-item' + (globalIdx === palActive ? ' is-active' : ''));
        item.innerHTML = '<span class="pi-ic">›</span><div class="pi-body"><div class="pi-name">' + esc(c.name) + '</div><div class="pi-desc">' + esc(c.desc) + '</div></div>';
        item.addEventListener('click', function () { closePalette(); c.run(); });
        item.addEventListener('mousemove', function () { palActive = globalIdx; renderPalette($('paletteInput').value); });
        list.appendChild(item);
      });
    });
  }
  function paletteKey(e) {
    if (e.key === 'ArrowDown') { e.preventDefault(); palActive = Math.min(palActive + 1, palItems.length - 1); renderPalette($('paletteInput').value); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); palActive = Math.max(palActive - 1, 0); renderPalette($('paletteInput').value); }
    else if (e.key === 'Enter') { e.preventDefault(); if (palItems[palActive]) { closePalette(); palItems[palActive].run(); } }
    else if (e.key === 'Escape') { closePalette(); }
  }

  // Trigger system: /command, @mention in the input
  function handleTrigger(val) {
    var hint = $('triggerHint');
    if (val.charAt(0) === '/') {
      var q = val.slice(1).toLowerCase();
      var matches = COMMANDS.filter(function (c) { return c.name.toLowerCase().indexOf(q) >= 0 || c.id.toLowerCase().indexOf(q) >= 0; }).slice(0, 5);
      hint.hidden = !matches.length;
      hint.textContent = matches.length ? '命令：' + matches.map(function (c) { return c.name; }).join(' · ') : '';
    } else if (val.charAt(0) === '@') {
      var m = val.slice(1).toLowerCase();
      var caps = snap.capabilities.filter(function (c) { return (c.label || c.id).toLowerCase().indexOf(m) >= 0; }).slice(0, 5);
      hint.hidden = !caps.length;
      hint.textContent = caps.length ? '能力：' + caps.map(function (c) { return c.label || c.id; }).join(' · ') : '';
    } else { hint.hidden = true; hint.textContent = ''; }
  }

  // ───────────────────── WIRING ─────────────────────
  function init() {
    // nav
    qsa('.zz-nav-btn').forEach(function (b) { b.addEventListener('click', function () { switchView(b.dataset.nav); }); });
    // conversation tabs
    qsa('.zz-tab').forEach(function (b) { b.addEventListener('click', function () { switchConvTab(b.dataset.tab); }); });
    // tools
    qsa('.zz-tool').forEach(function (b) {
      b.addEventListener('click', function () {
        var t = b.dataset.tool;
        if (t === 'think') { toolModes.think = !toolModes.think; }
        else if (t === 'web') { toolModes.web = !toolModes.web; }
        else if (t === 'speak') { autoSpeak = !autoSpeak; try { localStorage.setItem('zz_autoSpeak', autoSpeak ? '1' : '0'); } catch (e) {} }
        else if (t === 'voice') { startVoice(); return; }
        b.classList.toggle('is-on', (t === 'speak' ? autoSpeak : toolModes[t]));
      });
    });
    var speakBtn = qs('.zz-tool[data-tool="speak"]'); if (speakBtn) speakBtn.classList.toggle('is-on', autoSpeak);
    // command form
    $('cmdForm').addEventListener('submit', function (e) { e.preventDefault(); var v = $('cmdInput').value; if (v.charAt(0) === '/') { var name = v.slice(1).trim().split(' ')[0]; var c = COMMANDS.filter(function (x) { return x.id === name || x.name === name; })[0]; if (c) { c.run(); $('cmdInput').value = ''; return; } } submitCmd(v); });
    $('cmdInput').addEventListener('input', function (e) { handleTrigger(e.target.value); });
    // cmdk + palette
    $('cmdkBtn').addEventListener('click', openPalette);
    $('paletteScrim').addEventListener('click', closePalette);
    $('paletteInput').addEventListener('input', function (e) { palActive = 0; renderPalette(e.target.value); });
    $('paletteInput').addEventListener('keydown', paletteKey);
    // overlay
    $('overlayClose').addEventListener('click', closeOverlay);
    $('overlayScrim').addEventListener('click', closeOverlay);
    // context close
    $('ctxClose').addEventListener('click', function () { $('zzContext').parentElement.classList.add('context-collapsed'); });
    // voice orb presence (W12 Voice→GUI: clicking focuses/activates voice)
    $('orbPresence').addEventListener('click', startVoice);
    $('orbBtn').addEventListener('click', function () { var v = document.body.dataset.view; if (v !== 'conversation') switchView('conversation'); });
    // global keys
    document.addEventListener('keydown', function (e) {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); openPalette(); }
      else if (e.key === 'Escape') { closeOverlay(); closePalette(); $('zzContext').parentElement.classList.remove('context-collapsed'); }
    });

    // boot
    setState('IDLE');
    startStream();   // R8-UI Recovery: 实时通道（approval / execution / goal 状态）
    fetchSnapshot();
    setInterval(function () {
      getJSON('/api/agent/state').then(function (r) { if (r) { snap.agent = r; setState(String(r.state || 'IDLE').toUpperCase()); renderContextAuto(); } });
    }, 8000);
    setInterval(fetchSnapshot, 30000);
    renderHome();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
