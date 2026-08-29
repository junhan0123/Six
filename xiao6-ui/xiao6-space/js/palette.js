/* ═════════════════════════════════════════════════════════════════
   Xiao6 UI-R1 · palette.js — 命令面板 / 模型选择 / 权限选择（Phase 2）
   迁移自 x6-workspace.js：FEATURE_REGISTRY / COMMANDS / openFeature /
   openPalette/closePalette/softMatch/renderPalette/paletteKey / handleTrigger /
   MODELS / renderModelSelector / permMode / renderPerm / buildPermPop
   保持 localStorage：xiao6_model / xiao6_policy（不得改名）
   ═════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';
  window.Xiao6 = window.Xiao6 || {};
  var state = window.Xiao6.state;

  function $(id) { return document.getElementById(id); }
  function el(tag, cls, txt) { var n = document.createElement(tag); if (cls) n.className = cls; if (txt != null) n.textContent = txt; return n; }
  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  // ───────────────────── FEATURE REGISTRY（47 项，单一真相源）─────────────────────
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
  function featureVisible(f) {
    if (f.vis === 'default') return true;
    if (f.vis === 'advanced') return false;
    if (f.vis === 'hidden') return false;
    if (f.vis === 'conditional') {
      if (f.id === 'calendar') return !!(state.snap.calendar && state.snap.calendar.enabled);
      if (f.id === 'focus-app') return !!(state.snap.health && state.snap.health.focus_app);
      if (f.id === 'clipboard') return !!(state.snap.health && state.snap.health.clipboard);
    }
    return false;
  }

  // ───────────────────── COMMAND PALETTE ─────────────────────
  // 端点登记表（禁止字符串拼接构造 /api 路径；每个命令显式声明目标）
  var NAV_VIEWS = [
    { view: 'home', name: '回到首页', desc: 'Agent Timeline · 小6现在正在做什么' },
    { view: 'projects', name: '打开项目', desc: '查看目标与项目' },
    { view: 'tasks', name: '打开任务', desc: '查看任务清单' },
    { view: 'history', name: '打开历史', desc: '会话记录 · Agent 活动 · 执行结果' },
    { view: 'current', name: '打开当前项目', desc: '活跃目标及其任务' },
    { view: 'memory', name: '打开记忆', desc: '查看小6记住的内容' },
    { view: 'knowledge', name: '打开知识', desc: '查看知识库' },
    { view: 'capabilities', name: '打开技能', desc: '查看已登记能力' },
    { view: 'tools', name: '打开工具', desc: '查看可用工具清单' },
    { view: 'settings', name: '设置', desc: '偏好与系统概览' }
  ];
  var COMMANDS = [
    { id: 'ask', name: '问小6', desc: '直接对小6说话', group: '命令', run: function () { window.Xiao6.main.switchView('home'); var ci = $('cmdInput'); if (ci) ci.focus(); } },
    { id: 'search', name: '联网搜索', desc: '搜索资料', group: '命令', run: function () { window.Xiao6.timeline.submitCmd('帮我联网搜索相关资料'); } },
    { id: 'task', name: '运行任务', desc: '让小6完成一件事', group: '命令', run: function () { window.Xiao6.main.switchView('home'); var ci = $('cmdInput'); if (ci) { ci.value = '帮我完成一个任务：'; ci.focus(); } } },
    { id: 'goal', name: '新建目标', desc: '创建目标并交给 Agent 执行（POST /api/agent/goal）', group: '命令', run: function () { window.Xiao6.sidebar.openGoalForm(); } },
    { id: 'intent', name: '意图识别', desc: '提交意图 → GDE 决策（POST /api/agent/intent）', group: '命令', run: function () { window.Xiao6.sidebar.openIntentForm(); } },
    { id: 'voice', name: '语音输入', desc: '用语音对小6说话', group: '命令', run: function () { window.Xiao6.voice.startVoice(); } }
  ];
  NAV_VIEWS.forEach(function (v) {
    COMMANDS.push({
      id: 'nav:' + v.view, name: v.name, desc: v.desc, group: '导航',
      run: function () { window.Xiao6.main.switchView(v.view); }
    });
  });
  FEATURE_REGISTRY.forEach(function (f) {
    if (f.vis === 'advanced' || f.vis === 'conditional') {
      COMMANDS.push({ id: 'feat:' + f.id, name: f.name, desc: '能力 · ' + f.id, group: '能力', feat: f.id, run: function () { openFeature(f.id); } });
    }
  });
  function openFeature(id) {
    var f = FEATURE_REGISTRY.filter(function (x) { return x.id === id; })[0]; if (!f) return;
    window.Xiao6.main.openOverlay(f.name, '能力 · /api/' + id.replace(/-/g, '/').replace('capability/os', 'capability_os'), '<div class="x6-loading">读取中…</div>', function () {
      window.Xiao6.api.getJSON('/api/' + id.replace(/-/g, '/').replace('capability/os', 'capability_os')).then(function (d) {
        var ob = $('overlayBody'); if (ob) ob.innerHTML = '<pre style="white-space:pre-wrap;word-break:break-word;font-size:12.5px">' + esc(JSON.stringify(d, null, 2) || '（空）') + '</pre>';
      }).catch(function () { var ob = $('overlayBody'); if (ob) ob.innerHTML = '<span class="x6-empty">读取失败</span>'; });
    });
  }

  var palActive = -1, palItems = [];
  function openPalette() {
    var p = $('palette'); if (!p) return;
    p.setAttribute('aria-hidden', 'false');
    var inp = $('paletteInput'); inp.value = ''; palActive = 0; renderPalette(''); setTimeout(function () { inp.focus(); }, 30);
  }
  function closePalette() { var p = $('palette'); if (p) p.setAttribute('aria-hidden', 'true'); }
  function softMatch(s, q) { s = String(s).toLowerCase(); q = String(q).toLowerCase(); if (!q) return true; if (s.indexOf(q) >= 0) return true; var i = 0; for (var j = 0; j < q.length; j++) { i = s.indexOf(q[j], i); if (i < 0) return false; i++; } return true; }
  function renderPalette(q) {
    var list = $('paletteList'); if (!list) return;
    list.innerHTML = '';
    palItems = COMMANDS.filter(function (c) { return softMatch(c.name, q) || softMatch(c.desc, q); });
    if (!palItems.length) { list.innerHTML = '<div class="x6-palette-group">无匹配命令</div>'; return; }
    var groups = {}; palItems.forEach(function (c) { (groups[c.group] = groups[c.group] || []).push(c); });
    Object.keys(groups).forEach(function (g) {
      list.appendChild(el('div', 'x6-palette-group', g));
      groups[g].forEach(function (c, idx) {
        var globalIdx = palItems.indexOf(c);
        var item = el('div', 'x6-palette-item' + (globalIdx === palActive ? ' is-active' : ''));
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

  // ───────────────────── / 命令解析（cmdForm 委托）+ @ 能力提示 ─────────────────────
  function runCommand(v) {
    if (v.charAt(0) !== '/') return false;
    var name = v.slice(1).trim().split(' ')[0];
    var c = COMMANDS.filter(function (x) { return x.id === name || x.name === name; })[0];
    if (c) { c.run(); return true; }
    return false;
  }
  function handleTrigger(val) {
    var hint = $('triggerHint'); if (!hint) return;
    if (val.charAt(0) === '/') {
      var q = val.slice(1).toLowerCase();
      var matches = COMMANDS.filter(function (c) { return c.name.toLowerCase().indexOf(q) >= 0 || c.id.toLowerCase().indexOf(q) >= 0; }).slice(0, 5);
      hint.hidden = !matches.length;
      hint.textContent = matches.length ? '命令：' + matches.map(function (c) { return c.name; }).join(' · ') : '';
    } else if (val.charAt(0) === '@') {
      var m = val.slice(1).toLowerCase();
      var caps = state.snap.capabilities.filter(function (c) { return (c.label || c.id).toLowerCase().indexOf(m) >= 0; }).slice(0, 5);
      hint.hidden = !caps.length;
      hint.textContent = caps.length ? '能力：' + caps.map(function (c) { return c.label || c.id; }).join(' · ') : '';
    } else { hint.hidden = true; hint.textContent = ''; }
  }

  // ───────────────────── 模型选择器 ─────────────────────
  var MODELS = [
    { id: 'agnes-2.5-flash', name: 'Agnes 2.5 Flash', meta: '推荐 · 快速' },
    { id: 'agnes-2.0-flash', name: 'Agnes 2.0 Flash', meta: '均衡' },
    { id: 'agnes-1.5-flash', name: 'Agnes 1.5 Flash', meta: '旧版' },
    { id: 'agnes-image-2.1-flash', name: 'Agnes Image 2.1', meta: '图像生成' },
    { id: 'agnes-video-v2.0', name: 'Agnes Video 2.0', meta: '视频生成' }
  ];
  var currentModel = 'agnes-2.5-flash';
  function loadModelFromConfig(cfg) {
    try { var m = state.lsGet('xiao6_model', null); if (m) currentModel = m; else if (cfg && cfg.llm && cfg.llm.model) currentModel = cfg.llm.model; } catch (e) {}
    renderModelSelector();
  }
  function renderModelSelector() {
    var pop = $('modelPop'); if (!pop) return;
    pop.innerHTML = '';
    pop.appendChild(el('h4', null, '选择模型'));
    MODELS.forEach(function (m) {
      var it = el('div', 'x6-model-item' + (m.id === currentModel ? ' is-sel' : ''));
      it.innerHTML = '<span class="mi-name">' + esc(m.name) + '</span><span class="mi-meta">' + esc(m.meta) + '</span>' + (m.id === currentModel ? '<span class="mi-check">✓</span>' : '');
      it.addEventListener('click', function () {
        currentModel = m.id;
        state.lsSet('xiao6_model', m.id);
        var lab = $('modelLabel'); if (lab) lab.textContent = m.name;
        renderModelSelector(); pop.hidden = true;
      });
      pop.appendChild(it);
    });
    var cust = el('div', 'x6-model-custom', '＋ 自定义模型');
    cust.addEventListener('click', function () {
      var v = prompt('输入自定义模型 ID：', currentModel);
      if (v && v.trim()) { currentModel = v.trim(); state.lsSet('xiao6_model', currentModel); var lab = $('modelLabel'); if (lab) lab.textContent = currentModel; renderModelSelector(); pop.hidden = true; }
    });
    pop.appendChild(cust);
    var lab = $('modelLabel'); if (lab) { var hit = MODELS.filter(function (x) { return x.id === currentModel; })[0]; lab.textContent = hit ? hit.name : currentModel; }
  }

  // ───────────────────── 权限（手动确认 / 自动执行）─────────────────────
  var permMode = 'ask';
  function loadPermFromConfig(cfg) {
    try { var p = state.lsGet('xiao6_policy', null); if (p) permMode = p; else if (cfg && (cfg.agent_policy_default || cfg.AGENT_POLICY_DEFAULT)) permMode = (cfg.agent_policy_default || cfg.AGENT_POLICY_DEFAULT); } catch (e) {}
    if (permMode !== 'auto') permMode = 'ask';
    renderPerm();
  }
  function renderPerm() {
    var btn = $('permBtn'); if (!btn) return;
    var auto = permMode === 'auto';
    btn.classList.toggle('is-auto', auto);
    var lab = $('permLabel'); if (lab) lab.textContent = auto ? '自动执行' : '手动确认';
  }
  function buildPermPop() {
    var btn = $('permBtn'); if (!btn) return;
    var pop = $('permPop');
    if (!pop) { pop = el('div', 'x6-perm-pop'); pop.id = 'permPop'; pop.hidden = true; btn.appendChild(pop); }
    if (pop.getAttribute('data-built') === '1') return;
    pop.setAttribute('data-built', '1');
    pop.innerHTML = '<p>小6 执行工具或命令前，是否需要你手动确认？</p><div class="x6-seg"><button data-m="ask" class="' + (permMode === 'ask' ? 'is-sel' : '') + '">手动确认</button><button data-m="auto" class="' + (permMode === 'auto' ? 'is-sel' : '') + '">自动执行</button></div>';
    Array.prototype.forEach.call(pop.querySelectorAll('.x6-seg button'), function (b) {
      b.addEventListener('click', function () {
        permMode = b.dataset.m;
        state.lsSet('xiao6_policy', permMode);
        renderPerm(); pop.hidden = true;
      });
    });
  }

  // ───────────────────── WIRING ─────────────────────
  function init() {
    window.Xiao6.api.getJSON('/api/config').then(function (cfg) {
      loadModelFromConfig(cfg);
      loadPermFromConfig(cfg);
    });
    var ck = $('cmdkBtn'); if (ck) ck.addEventListener('click', openPalette);
    var ps = $('paletteScrim'); if (ps) ps.addEventListener('click', closePalette);
    var pi = $('paletteInput');
    if (pi) { pi.addEventListener('input', function (e) { palActive = 0; renderPalette(e.target.value); }); pi.addEventListener('keydown', paletteKey); }
    var modelBtn = $('modelBtn'); if (modelBtn) {
      modelBtn.addEventListener('click', function (e) { e.stopPropagation(); var pop = $('modelPop'); if (pop) pop.hidden = !pop.hidden; var pp = $('permPop'); if (pp) pp.hidden = true; });
    }
    var permBtn = $('permBtn'); if (permBtn) {
      permBtn.addEventListener('click', function (e) { e.stopPropagation(); buildPermPop(); var pop = $('permPop'); if (pop) pop.hidden = !pop.hidden; var mp = $('modelPop'); if (mp) mp.hidden = true; });
    }
    document.addEventListener('click', function () { var mp = $('modelPop'); if (mp) mp.hidden = true; var pp = $('permPop'); if (pp) pp.hidden = true; });
    document.addEventListener('keydown', function (e) {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); openPalette(); }
    });
  }

  window.Xiao6.palette = {
    runCommand: runCommand,
    handleTrigger: handleTrigger,
    openPalette: openPalette,
    closePalette: closePalette,
    init: init
  };
})();
