/*
 * control-center.js — Xiao6 Control Center（Phase C · Settings Control Center）
 *
 * 性质：纯前端只读 + 最佳努力写回（消费既有 GET/POST 端点）。不修改 Phase 37 核心。
 * 纪律（与任务 §八 一致）：
 *   - EXISTS  → 产品化（展示真实能力）
 *   - PARTIAL → 把现有能力做成可用控件
 *   - MISSING → 明确占位，绝不造假数据
 *   - PLANNED → 标为未来能力（如 oMLX 本地 Apple 模型）
 *   - API Key 永不明文回显 / 不进日志。
 * 复用：ui-v4.css 设计令牌（--bg、--text*、--line、--core-*、--surface-*、--sp-*、--dur*、--ease）。
 */
(function (global) {
  'use strict';

  /* ------------------------------ 工具 ------------------------------ */
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function getJSON(url, opts) {
    var ctrl = new AbortController();
    var t = setTimeout(function () { ctrl.abort(); }, (opts && opts.timeout) || 9000);
    return fetch(url, Object.assign({ signal: ctrl.signal }, opts || {}))
      .then(function (r) { return r.json().catch(function () { return {}; }); })
      .catch(function () { return { _network_error: true }; })
      .then(function (d) { clearTimeout(t); return d; });
  }
  function postJSON(url, body) {
    return getJSON(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {}),
      timeout: 30000,
    });
  }
  function clip(s, n) {
    s = String(s == null ? '' : s).trim();
    return s.length > n ? s.slice(0, n) + '…' : s;
  }
  function yn(v) { return v === true || v === 'true' || v === 1 || v === '1' ? '开' : (v === false || v === 'false' || v === 0 || v === '0' ? '关' : (v ? String(v) : '关')); }
  function truthy(v) { return v === true || v === 'true' || v === 1 || v === '1' || v === 'yes'; }

  /* 状态缓存（一次 open 内复用，避免重复打后端） */
  var cache = { config: null, version: null, health: null, memory: null, knowledge: null, proactive: null, perception: null, boot: null };

  /* ------------------------------ 分类 ------------------------------ */
  var SECTIONS = [
    { id: 'overview',    label: '概览' },
    { id: 'ai',          label: 'AI / 模型' },
    { id: 'cloud',       label: '云端 API' },
    { id: 'local',       label: '本地模型' },
    { id: 'voice',       label: '语音' },
    { id: 'vision',      label: '视觉 / 感知' },
    { id: 'memory',      label: '记忆' },
    { id: 'knowledge',   label: '知识' },
    { id: 'proactive',   label: '主动智能' },
    { id: 'appearance',  label: '外观' },
    { id: 'privacy',     label: '隐私' },
    { id: 'security',    label: '安全' },
    { id: 'dependencies',label: '依赖 / 就绪' },
    { id: 'models',      label: '模型注册表' },
    { id: 'data',        label: '数据' },
    { id: 'startup',     label: '启动' },
    { id: 'developer',   label: '开发者', devOnly: true },
    { id: 'about',       label: '关于' }
  ];
  var current = 'overview';

  /* 云端模型预设（Phase 38E · E1 LLM Provider 抽象；纯前端，路由统一走 llm2 槽，禁新增 ACTIVE_PROVIDER）
     - 全部为 OpenAI /chat/completions 兼容端点；Anthropic 走 OpenAI 兼容网关，base 为占位，需用户填写真实网关。
     - 仅声明元数据与默认 base，不含密钥；密钥由用户在「AI / 模型」输入，写入本机 .env。 */
  var CLOUD_PRESETS = [
    { id: 'openai',      label: 'OpenAI（云端）',               base: 'https://api.openai.com/v1' },
    { id: 'anthropic',   label: 'Anthropic（OpenAI 兼容网关）', base: 'https://api.anthropic.com/v1' },
    { id: 'gemini',      label: 'Google Gemini（云端）',        base: 'https://generativelanguage.googleapis.com/v1beta/openai/' },
    { id: 'deepseek',    label: 'DeepSeek（云端）',             base: 'https://api.deepseek.com/v1' },
    { id: 'qwen',        label: '通义千问 Qwen（云端）',        base: 'https://dashscope.aliyuncs.com/compatible-mode/v1' },
    { id: 'kimi',        label: 'Kimi / Moonshot（云端）',      base: 'https://api.moonshot.cn/v1' },
    { id: 'zhipu',       label: '智谱 GLM（云端）',             base: 'https://open.bigmodel.cn/api/paas/v4' },
    { id: 'minimax',     label: 'MiniMax（云端）',              base: 'https://api.minimax.io/v1' },
    { id: 'siliconflow', label: 'SiliconFlow（云端）',          base: 'https://api.siliconflow.cn/v1' }
  ];

  /* ------------------------------ 入口 ------------------------------ */
  function open(host) {
    if (!host) return;
    var wrap = document.createElement('div');
    wrap.className = 'zz-cc';

    var nav = document.createElement('nav');
    nav.className = 'zz-cc__nav';
    // Phase 38F · 三通道（DEV / RC / RELEASE）：纯表现层，不影响后端行为。
    // 通道真相唯一来自 /api/config 的 build_channel（development | rc | release）；
    // 兼容旧 global.ZZChannel，但以前者为准；拿不到时按 development（最开放）。
    var buildChannel = (cache.config && cache.config.build_channel)
      || (global.ZZChannel && global.ZZChannel.channel)
      || 'development';
    var isRelease = buildChannel === 'release' || buildChannel === 'rc';
    if (isRelease) {
      // 上次停留在被收起的栏目上时，回到概览，避免打开一个已隐藏的栏
      SECTIONS.forEach(function (s) { if (s.devOnly && s.id === current) current = 'overview'; });
    }
    SECTIONS.filter(function (s) { return !(s.devOnly && isRelease); }).forEach(function (s) {
      var b = document.createElement('button');
      b.type = 'button';
      b.textContent = s.label;
      b.className = 'zz-cc__navbtn' + (s.id === current ? ' is-active' : '');
      b.setAttribute('data-cc', s.id);
      b.addEventListener('click', function () {
        current = s.id;
        nav.querySelectorAll('.zz-cc__navbtn').forEach(function (n) {
          n.classList.toggle('is-active', n.getAttribute('data-cc') === current);
        });
        renderSection(panel, current);
      });
      nav.appendChild(b);
    });

    var panel = document.createElement('div');
    panel.className = 'zz-cc__panel';

    wrap.appendChild(nav);
    wrap.appendChild(panel);
    host.innerHTML = '';
    host.appendChild(wrap);

    renderSection(panel, current);
  }

  function renderSection(panel, id) {
    panel.scrollTop = 0;
    panel.innerHTML = '<div class="zz-cc__loading">加载中…</div>';
    var fn = RENDERERS[id] || RENDERERS.overview;
    Promise.resolve(fn(panel)).catch(function (e) {
      panel.innerHTML = '<div class="zz-cc__note">这一栏暂时打不开：' + esc(String(e && e.message || e)) + '</div>';
    });
  }

  /* 每个小渲染器返回 Promise（允许异步拉数据） */
  var RENDERERS = {
    overview: renderOverview,
    ai: renderAi,
    cloud: renderCloud,
    local: renderLocal,
    voice: renderVoice,
    vision: renderVision,
    memory: renderMemory,
    knowledge: renderKnowledge,
    proactive: renderProactive,
    appearance: renderAppearance,
    privacy: renderPrivacy,
    security: renderSecurity,
    dependencies: renderDependencies,
    models: renderModels,
    data: renderData,
    startup: renderStartup,
    developer: renderDeveloper,
    about: renderAbout
  };

  /* ============================ 概览 ============================ */
  function renderOverview(panel) {
    return Promise.all([
      cache.config || (cache.config = getJSON('/api/config')),
      cache.version || (cache.version = getJSON('/api/version')),
      cache.health || (cache.health = getJSON('/api/health'))
    ]).then(function (res) {
      var cfg = res[0] || {}, ver = res[1] || {}, h = res[2] || {};
      var offline = cfg._network_error || ver._network_error || h._network_error;
      var llm = cfg.llm || {};
      var aiName = cfg.ai_name || ver.app_name || '小6';
      // Phase 38I · P0-1 后端身份校验：仅当后端自报 ai_name===小6 且具备 features/tools 才认作「小6服务正常」。
      // 其它服务占用 8000 端口 / 后端未启动 / 非小6实例时，绝不误报「在线 / READY」。
      var identityOk = h && h.ai_name === '小6' && h.features && Array.isArray(h.tools);
      var connBadge;
      if (offline) {
        connBadge = '<span class="zz-cc__badge zz-cc__badge--bad">未连接</span>';
      } else if (!identityOk) {
        connBadge = '<span class="zz-cc__badge zz-cc__badge--bad">非小6服务（端口被占用）</span>';
      } else {
        connBadge = '<span class="zz-cc__badge zz-cc__badge--ok">在线</span>';
      }
      var model = llm.model || (h.model) || (llm.active ? ('active: ' + llm.active) : '未配置');
      var keyOk = llm.key_present || (llm.llm2 && llm.llm2.key_present);
      var rows = [
        ['名字', esc(aiName)],
        ['版本', esc(ver.version || cfg.version && cfg.version.current || '—')],
        ['当前模型', esc(model)],
        ['模型密钥', keyOk ? '<span class="zz-cc__badge zz-cc__badge--ok">已配置</span>' : '<span class="zz-cc__badge zz-cc__badge--warn">未配置</span>'],
        ['数据位置', '<span class="zz-cc__badge zz-cc__badge--ok">本机</span> 不出设备'],
        ['连接状态', connBadge]
      ];
      panel.innerHTML =
        '<h3 class="zz-cc__h">概览</h3>' +
        '<p class="zz-cc__lead">小6住在你的机器上，推理与数据默认不出这台设备。下面是当前最关键的几项状态。</p>' +
        channelTag(cfg.build_channel) +
        rows.map(function (r) { return row(r[0], r[1]); }).join('') +
        baseRowsHtml();
    });
  }

  function baseRowsHtml() {
    return '<div class="zz-cc__planned">' +
      '<div class="zz-cc__k" style="margin-bottom:6px">关于小6</div>' +
      '<div class="zz-cc__note" style="margin-top:0">' +
      '· 我有八种状态：待命 · 等待 · 思考 · 规划 · 执行 · 完成 · 异常 · 离线<br>' +
      '· 只有一个入口：底部那行就是意图线，剩下的交给我<br>' +
      '· 快捷键：⌘1–⌘5 唤起 记忆 / 知识 / 目标 / 世界 / 关于；Esc 返回' +
      '</div></div>';
  }

  /* ============================ AI / 模型 ============================ */
  function renderAi(panel) {
    return (cache.config || (cache.config = getJSON('/api/config'))).then(function (cfg) {
      cfg = cfg || {};
      var providers = cfg.providers || [];
      var selProviders = providers.filter(function (p) { return p.user_selectable !== false; });
      function opt(id, label, tag) { return '<option value="' + esc(id) + '">' + esc(label) + (tag ? '（' + tag + '）' : '') + '</option>'; }
      // Phase 38I · P1-2：仅当 provider 真实携带 implemented===false（后端标记未实现）才加"暂未支持"。
      // 当前 /api/config 的 providers 不含该字段，故为安全 no-op——绝不凭空造"不支持"标签。
      function provTag(p) {
        var t = [];
        if (p.privacy_class === 'local') t.push('本地');
        if (p.implemented === false) t.push('暂未支持');
        return t.length ? t.join(' · ') : null;
      }
      var cloudOpts = selProviders.filter(function (p) { return p.privacy_class !== 'local'; })
        .map(function (p) { return opt(p.id, p.label, provTag(p)); }).join('')
        + CLOUD_PRESETS.map(function (p) { return opt(p.id, p.label); }).join('');
      var localOpts = selProviders.filter(function (p) { return p.privacy_class === 'local'; })
        .map(function (p) { return opt(p.id, p.label, provTag(p)); }).join('');
      var opts = (cloudOpts ? '<optgroup label="云端模型">' + cloudOpts + '</optgroup>' : '')
        + (localOpts ? '<optgroup label="本地模型">' + localOpts + '</optgroup>' : '')
        || '<option value="agnes">Agnes / OpenAI 兼容（云端）</option>';
      panel.innerHTML =
        '<h3 class="zz-cc__h">AI / 模型</h3>' +
        '<p class="zz-cc__lead">小6用大模型理解你。云端需要 API Key；本地模型数据不出本机。</p>' +
        aiStatusLine(cfg) +
        '<label class="zz-cc__field">Provider<select id="ccProv" class="zz-cc__select">' + opts + '</select></label>' +
        '<label class="zz-cc__field">Base URL<input id="ccBase" class="zz-cc__input" placeholder="https://… 或 http://localhost:11434"></label>' +
        '<label class="zz-cc__field">API Key<input id="ccKey" class="zz-cc__input" type="password" placeholder="留空则使用已保存密钥 / 本地无需"></label>' +
        '<div class="zz-cc__btns">' +
          '<button id="ccFetch" class="zz-cc__btn">拉取模型</button>' +
          '<button id="ccTest" class="zz-cc__btn zz-cc__btn--ghost">测试连通</button>' +
          '<button id="ccSave" class="zz-cc__btn zz-cc__btn--ghost">保存来源</button>' +
        '</div>' +
        '<div id="ccAiMsg" class="zz-cc__msg"></div>' +
        '<div class="zz-cc__note">密钥只发送到本地服务并存入本机 .env，绝不明文回显、不离开你的设备。</div>';

      var prov = document.getElementById('ccProv');
      function fillFromProvider() {
        var s = providers.find(function (p) { return p.id === prov.value; });
        if (s) { document.getElementById('ccBase').value = s.resolved_base_url || s.default_base_url || ''; return; }
        var pr = CLOUD_PRESETS.find(function (p) { return p.id === prov.value; });
        if (pr) document.getElementById('ccBase').value = pr.base;
      }
      prov.addEventListener('change', fillFromProvider);
      prov.value = (cfg.active_provider) || (cfg.llm && cfg.llm.active) || 'agnes';
      fillFromProvider();

      document.getElementById('ccFetch').addEventListener('click', function () {
        var base = document.getElementById('ccBase').value.trim();
        var key = document.getElementById('ccKey').value;
        var msg = document.getElementById('ccAiMsg');
        msg.textContent = '拉取中…';
        postJSON('/api/models', { base_url: base, api_key: key }).then(function (r) {
          if (!r.ok) { msg.textContent = '拉取失败：' + (r.error || '未知'); return; }
          if (!r.models || !r.models.length) { msg.textContent = '该来源没有返回模型。'; return; }
          var sel = '<label class="zz-cc__field">模型<select id="ccModel" class="zz-cc__select">' +
            r.models.map(function (m) { return '<option value="' + esc(m.id) + '">' + esc(m.id) + '</option>'; }).join('') +
            '</select></label>';
          msg.innerHTML = sel;
        });
      });
      document.getElementById('ccTest').addEventListener('click', function () {
        var base = document.getElementById('ccBase').value.trim();
        var key = document.getElementById('ccKey').value;
        var m = document.getElementById('ccModel');
        var model = m ? m.value : '';
        var msg = document.getElementById('ccAiMsg');
        postJSON('/api/test-llm', { base_url: base, api_key: key, model: model }).then(function (t) {
          msg.textContent = t.ok ? ('✓ 连通成功 · ' + t.latency_ms + 'ms' + (model ? ' · ' + model : '')) : ('✗ ' + (t.error || '失败'));
        });
      });
      document.getElementById('ccSave').addEventListener('click', function () {
        var base = document.getElementById('ccBase').value.trim();
        var key = document.getElementById('ccKey').value;
        var m = document.getElementById('ccModel'); var model = m && m.value ? m.value : '';
        var body = {};
        var localMap = { ollama: 'OLLAMA_BASE_URL', lmstudio: 'LMSTUDIO_BASE_URL', mlx: 'MLX_BASE_URL' };
        if (prov.value === 'agnes') {
          // 主用云端：写入 AGNES_* 槽
          body.AGNES_BASE_URL = base;
          if (key) body.AGNES_API_KEY = key;
          if (model) body.AGNES_MODEL = model;
          body.ACTIVE_LLM = 'agnes';
        } else if (localMap[prov.value]) {
          // 本地模型运行时：仅写入各自 base（供探针识别），不改 ACTIVE_LLM
          body[localMap[prov.value]] = base;
          if (model) body[localMap[prov.value].replace('BASE_URL', 'MODEL')] = model;
        } else {
          // 第二供应商 / 任意云端预设：统一走 llm2 槽（DC-01：ACTIVE_LLM 仅 agnes / llm2）
          body.LLM2_BASE_URL = base;
          if (key) body.LLM2_API_KEY = key;
          if (model) body.LLM2_MODEL = model;
          body.ACTIVE_LLM = 'llm2';
        }
        postJSON('/api/config', body).then(function (r) {
          document.getElementById('ccAiMsg').textContent = r.ok ? '✓ 已保存（重启后生效）' : ('保存失败：' + (r.error || '未知'));
        });
      });

      // Phase 38I · P1-2：打开 AI 面板即自动探测真实连通性（空 body 回退服务端已配置项），
      // 就地更新状态行。复用 dependency-manager.js 同契约；不新增 API、不改 server.py。
      var aiStatusEl = document.getElementById('ccAiStatus');
      if (aiStatusEl) {
        postJSON('/api/test-llm', {}).then(function (t) {
          if (!t || t._network_error) return; // 离线/未连接：保持"待验证"
          if (t.ok === true) {
            aiStatusEl.innerHTML = statusBadge('READY') + ' <span class="zz-cc__sub">' + esc(t.latency_ms) + ' ms</span>';
          } else {
            aiStatusEl.innerHTML = statusBadge('CONNECTION_FAILED') + (t.error ? ' <span class="zz-cc__sub">' + esc(clip(t.error, 80)) + '</span>' : '');
          }
        }).catch(function () { /* 探测异常：保持"待验证"，不造假 */ });
      }
    });
  }

  /* ============================ 云端 API ============================ */
  function renderCloud(panel) {
    return (cache.config || (cache.config = getJSON('/api/config'))).then(function (cfg) {
      cfg = cfg || {};
      var ws = cfg.web_search || {};
      var soc = cfg.social || {};
      var media = cfg.media || {};
      var items = [
        ['联网搜索 (' + esc(ws.engine || 'tavily') + ')', ws.key_present ? ok() : warn(), '用于实时检索；密钥存于本机 .env'],
        ['飞书 (Feishu)', soc.feishu_app_id ? ok() : off(), soc.feishu_ws_enabled ? '长连接已开' : '未启用'],
        ['Discord', soc.discord_token ? ok() : off(), '未配置'],
        ['社交入站 (Webhook)', soc.inbound_enabled ? ok() : off(), '未配置'],
        ['媒体生成 (MiniMax)', media.group_present ? ok() : off(), media.group_present ? 'Group 已配置' : '未配置']
      ];
      panel.innerHTML =
        '<h3 class="zz-cc__h">云端 API</h3>' +
        '<p class="zz-cc__lead">这里列出已接入的云端服务。密钥只保存在本机 .env，绝不在界面回显。</p>' +
        items.map(function (it) { return row(it[0], it[1], it[2]); }).join('') +
        '<div class="zz-cc__note">没有填密钥的服务保持"未配置"是正常状态——小6的核心能力（对话、记忆、本地工具）不依赖它们。</div>';
    });
  }

  /* ============================ 本地模型 ============================ */
  function renderLocal(panel) {
    return Promise.all([
      cache.config || (cache.config = getJSON('/api/config')),
      getJSON('/api/providers/probe')
    ]).then(function (res) {
      var cfg = res[0] || {}, probe = (res[1] && res[1].probe) || {};
      var providers = (cfg.providers || []).filter(function (p) { return p.privacy_class === 'local'; });
      if (!providers.length) providers = [
        { id: 'ollama', label: 'Ollama' }, { id: 'lmstudio', label: 'LM Studio' }, { id: 'mlx', label: 'MLX' }
      ];
      var rows = providers.map(function (p) {
        var pr = probe[p.id] || {};
        var state = pr.probed ? (pr.reachable ? ok('已连通') : warn('未连通')) : off('未探测');
        var url = (cfg.providers || []).find(function (x) { return x.id === p.id; });
        var base = (url && (url.resolved_base_url || url.default_base_url)) || '';
        return row(p.label, state, base ? esc(base) : '—');
      });
      panel.innerHTML =
        '<h3 class="zz-cc__h">本地模型</h3>' +
        '<p class="zz-cc__lead">本地模型让推理完全在设备上完成。装好 Ollama / LM Studio 后填入 Base URL 即可。</p>' +
        rows.join('') +
        '<div class="zz-cc__planned">' +
          '<div class="zz-cc__k" style="margin-bottom:6px">oMLX <span class="zz-cc__badge zz-cc__badge--plan">计划中</span></div>' +
          '<div class="zz-cc__note" style="margin-top:0">Apple 芯片上的 on-device 模型（oMLX）为未来计划能力，目前走 MLX 运行时接入。未上线前此处仅占位，不假装可用。</div>' +
        '</div>';
    });
  }

  /* ============================ 语音 ============================ */
  function renderVoice(panel) {
    return (cache.config || (cache.config = getJSON('/api/config'))).then(function (cfg) {
      cfg = cfg || {};
      function isAutoTts() { try { return localStorage.getItem('zz.tts') !== '0'; } catch (e) { return true; } }
      var asr = cfg.asr || {}, tts = cfg.tts || {};
      var asrOpts = ['', 'vosk', 'whisper', 'aliyun', 'xfyun', 'volcengine'].map(function (v) {
        return '<option value="' + v + '"' + ((asr.provider || '') === v ? ' selected' : '') + '>' + (v ? v : '关闭') + '</option>';
      }).join('');
      var ttsOpts = ['edge', 'gpt_sovits', 'system'].map(function (v) {
        return '<option value="' + v + '"' + ((tts.backend || 'edge') === v ? ' selected' : '') + '>' + v + '</option>';
      }).join('');
      panel.innerHTML =
        '<h3 class="zz-cc__h">语音</h3>' +
        '<p class="zz-cc__lead">语音是可选能力。不配置也能完全用文字与小6交互。</p>' +
        '<label class="zz-cc__field">语音输入 (ASR)<select id="ccAsr" class="zz-cc__select">' + asrOpts + '</select></label>' +
        '<div class="zz-cc__note">已装密钥：' +
          (asr.aliyun_present ? '阿里云 ' : '') + (asr.xfyun_present ? '讯飞 ' : '') + (asr.volcengine_present ? '火山 ' : '') +
          (asr.local_supported ? '本地 Vosk/Whisper 可用' : '') + (asr.provider ? '' : '（当前关闭）') + '</div>' +
        '<label class="zz-cc__field">语音输出 (TTS)<select id="ccTts" class="zz-cc__select">' + ttsOpts + '</select></label>' +
        '<label class="zz-cc__field">音色 (voice)<input id="ccVoice" class="zz-cc__input" value="' + esc(tts.voice || '') + '" placeholder="如 zh-CN-YunxiNeural"></label>' +
        '<label class="zz-cc__field">语速 (rate)<input id="ccRate" class="zz-cc__input" value="' + esc(tts.rate || '') + '" placeholder="+0%"></label>' +
        '<label class="zz-cc__field" style="display:flex;align-items:center;gap:8px"><input type="checkbox" id="ccAutoTts" ' + (isAutoTts() ? 'checked' : '') + '> 自动朗读对话回复（文字回复也用语音念出）</label>' +
        '<div class="zz-cc__btns">' +
          '<button id="ccVoiceSave" class="zz-cc__btn">保存语音设置</button>' +
          '<button id="ccTtsTest" class="zz-cc__btn zz-cc__btn--ghost">试听 TTS</button>' +
          '<button id="ccAsrTest" class="zz-cc__btn zz-cc__btn--ghost">测试 ASR</button>' +
        '</div>' +
        '<div id="ccVoiceMsg" class="zz-cc__msg"></div>';
      document.getElementById('ccVoiceSave').addEventListener('click', function () {
        postJSON('/api/config', {
          XIAO6_ASR_PROVIDER: document.getElementById('ccAsr').value,
          XIAO6_TTS_BACKEND: document.getElementById('ccTts').value,
          Xiao6_TTS_VOICE: document.getElementById('ccVoice').value,
          Xiao6_TTS_RATE: document.getElementById('ccRate').value
        }).then(function (r) {
          document.getElementById('ccVoiceMsg').textContent = r.ok ? '✓ 已保存（重启后生效）' : ('保存失败：' + (r.error || '未知'));
        });
      });
      var autoChk = document.getElementById('ccAutoTts');
      if (autoChk) autoChk.addEventListener('change', function () {
        try { localStorage.setItem('zz.tts', this.checked ? '1' : '0'); } catch (e) {}
        var m = document.getElementById('ccVoiceMsg'); if (m) m.textContent = this.checked ? '✓ 已开启自动朗读' : '已关闭自动朗读';
      });
      var ttsTest = document.getElementById('ccTtsTest');
      if (ttsTest) ttsTest.addEventListener('click', function () {
        var m = document.getElementById('ccVoiceMsg'); if (m) m.textContent = '正在朗读…';
        if (global.FinalTTS && global.FinalTTS.speak) {
          global.FinalTTS.speak('你好，我是小6，这是一次语音播报测试。', {
            onDone: function () { var x = document.getElementById('ccVoiceMsg'); if (x) x.textContent = '✓ 朗读完成'; }
          });
        } else if (m) { m.textContent = '语音引擎不可用'; }
      });
      var asrTest = document.getElementById('ccAsrTest');
      if (asrTest) asrTest.addEventListener('click', function () {
        var m = document.getElementById('ccVoiceMsg');
        if (!global.FinalVoice || !global.FinalVoice.start) { if (m) m.textContent = '语音引擎不可用'; return; }
        if (m) m.textContent = '请说一句话…（说完小6会回应）';
        var done = false;
        function onRec(t) {
          if (done) return; done = true;
          if (m) m.textContent = '已识别：' + t;
          if (global.FinalVoice.onRecognized) global.FinalVoice.onRecognized(null);
          if (global.FinalVoice.stop) global.FinalVoice.stop();  // 收束测试，避免长唤醒循环
        }
        if (global.FinalVoice.onRecognized) global.FinalVoice.onRecognized(onRec);
        global.FinalVoice.start();
        setTimeout(function () {
          if (done) return; done = true;
          if (global.FinalVoice.onRecognized) global.FinalVoice.onRecognized(null);
          if (global.FinalVoice.stop) global.FinalVoice.stop();
          if (m && m.textContent.indexOf('已识别') !== 0) m.textContent = '测试结束（未识别到内容）';
        }, 9000);
      });
    });
  }

  /* ============================ 视觉 / 感知 ============================ */
  function renderVision(panel) {
    return (cache.perception || (cache.perception = getJSON('/api/perception/status'))).then(function (p) {
      var okState = p && !p._network_error && (p.enabled || p.available || p.ok);
      var rows = [
        ['屏幕感知 (Perception)', okState ? ok('已启用') : warn('未启用'), '增强能力：小6可"看"屏幕'],
        ['上下文注入', truthy(p && p.context_injection) ? ok() : off(), '需你显式授权才把屏幕文字送模型'],
        ['OCR', truthy(p && p.ocr) ? ok() : off(), '本地 OCR，数据不出本机']
      ];
      panel.innerHTML =
        '<h3 class="zz-cc__h">视觉 / 感知</h3>' +
        '<p class="zz-cc__lead">视觉是增强能力。开启后小6能理解屏幕内容，但默认不把屏幕文字送进模型，需你授权。</p>' +
        rows.map(function (r) { return row(r[0], r[1], r[2]); }).join('') +
        '<div class="zz-cc__note">需要本地视觉模型或云端视觉接口。未启用时不影响任何核心能力。</div>';
    });
  }

  /* ============================ 记忆 ============================ */
  function renderMemory(panel) {
    return (cache.memory || (cache.memory = getJSON('/api/memory'))).then(function (m) {
      m = m || {};
      var rem = m.reminders || [];
      var rows = [
        ['已存笔记', String(m.note_count != null ? m.note_count : '—')],
        ['对话沉淀', String(m.log_count != null ? m.log_count : '—')],
        ['提醒事项', String(rem.length)],
        ['长期记忆', truthy(m.summary) ? ok('已有摘要') : off('暂无')]
      ];
      panel.innerHTML =
        '<h3 class="zz-cc__h">记忆</h3>' +
        '<p class="zz-cc__lead">小6记得你说过的、读过的事。这些都在本机数据库里。</p>' +
        rows.map(function (r) { return row(r[0], r[1]); }).join('') +
        '<div class="zz-cc__btns"><button id="ccBackfill" class="zz-cc__btn zz-cc__btn--ghost">重新梳理记忆</button></div>' +
        '<div id="ccMemMsg" class="zz-cc__msg"></div>' +
        '<div class="zz-cc__note">点"重新梳理"会让小6把历史对话沉淀成长期记忆（可随时在「记忆 ⌘1」查看）。</div>';
      document.getElementById('ccBackfill').addEventListener('click', function () {
        var btn = document.getElementById('ccBackfill'); btn.disabled = true; btn.textContent = '梳理中…';
        postJSON('/api/memory/backfill', {}).then(function (r) {
          document.getElementById('ccMemMsg').textContent = r.ok ? '✓ 已触发梳理' : ('失败：' + (r.error || '未知'));
          btn.disabled = false; btn.textContent = '重新梳理记忆';
        });
      });
    });
  }

  /* ============================ 知识 ============================ */
  function renderKnowledge(panel) {
    return (cache.config || (cache.config = getJSON('/api/config'))).then(function (cfg) {
      cfg = cfg || {};
      var enabled = truthy(cfg.feature_knowledge_platform);
      panel.innerHTML =
        '<h3 class="zz-cc__h">知识</h3>' +
        '<p class="zz-cc__lead">把资料交给小6，它读完就记在这里，需要时自动引用。</p>' +
        row('知识平台', enabled ? ok('已启用') : warn('未启用')) +
        '<label class="zz-cc__field">存入一篇文档（粘贴文本）</label>' +
        '<textarea id="ccKbText" class="zz-cc__input" rows="4" placeholder="粘贴你想让小6记住的资料…"></textarea>' +
        '<label class="zz-cc__field">标题<input id="ccKbTitle" class="zz-cc__input" placeholder="可选"></label>' +
        '<div class="zz-cc__btns"><button id="ccKbSave" class="zz-cc__btn">存入知识</button></div>' +
        '<div id="ccKbMsg" class="zz-cc__msg"></div>' +
        '<div class="zz-cc__note">也可在对话中说"记住这篇"，小6会主动归档。</div>';
      document.getElementById('ccKbSave').addEventListener('click', function () {
        var text = document.getElementById('ccKbText').value.trim();
        if (!text) { document.getElementById('ccKbMsg').textContent = '请先粘贴文本'; return; }
        postJSON('/api/knowledge', { action: 'upload', title: document.getElementById('ccKbTitle').value.trim(), text: text }).then(function (r) {
          document.getElementById('ccKbMsg').textContent = r.ok ? '✓ 已存入' : ('失败：' + (r.error || '未知'));
          if (r.ok) { document.getElementById('ccKbText').value = ''; document.getElementById('ccKbTitle').value = ''; }
        });
      });
    });
  }

  /* ============================ 主动智能 ============================ */
  function renderProactive(panel) {
    return (cache.proactive || (cache.proactive = getJSON('/api/proactive/status'))).then(function (p) {
      p = p || {};
      if (p._network_error) p = {};
      var win = (p.window || []).join('–') || '—';
      var quiet = (p.quiet || []).join('–') || '—';
      var dnd = truthy(p.dnd);
      panel.innerHTML =
        '<h3 class="zz-cc__h">主动智能</h3>' +
        '<p class="zz-cc__lead">小6会在合适的时候给你建议和提醒，但绝不会擅自执行。这是"建议"，不是"命令"。</p>' +
        row('主动引擎', truthy(p.feature_proactive_engine) ? ok() : warn('未启用')) +
        row('建议模式', esc(p.suggestion_mode || '—')) +
        row('活跃时段', esc(win)) +
        row('安静时段', esc(quiet)) +
        row('免打扰 (DND)', dnd ? ok('开') : off('关')) +
        '<div class="zz-cc__btns"><button id="ccDnd" class="zz-cc__btn">' + (dnd ? '关闭免打扰' : '开启免打扰') + '</button></div>' +
        '<div id="ccProMsg" class="zz-cc__msg"></div>';
      document.getElementById('ccDnd').addEventListener('click', function () {
        postJSON('/api/proactive/dnd', { enabled: !dnd }).then(function (r) {
          if (r.ok) { cache.proactive = null; renderProactive(panel); }
          else document.getElementById('ccProMsg').textContent = '失败：' + (r.error || '未知');
        });
      });
    });
  }

  /* ============================ 外观 ============================ */
  function renderAppearance(panel) {
    return (cache.config || (cache.config = getJSON('/api/config'))).then(function (cfg) {
      cfg = cfg || {};
      var themes = ['dark-cyan', 'dark-green', 'dark-purple', 'dark-amber', 'dark-rose', 'quantum', 'midnight', 'light'];
      var themeOpts = themes.map(function (t) {
        return '<option value="' + t + '"' + ((cfg.theme || 'dark-cyan') === t ? ' selected' : '') + '>' + t + '</option>';
      }).join('');
      panel.innerHTML =
        '<h3 class="zz-cc__h">外观</h3>' +
        '<p class="zz-cc__lead">小6的样子由你定。主题实时试看，刷新后稳定生效。</p>' +
        '<label class="zz-cc__field">AI 名字<input id="ccName" class="zz-cc__input" value="' + esc(cfg.ai_name || '小6') + '"></label>' +
        '<label class="zz-cc__field">主题<select id="ccTheme" class="zz-cc__select">' + themeOpts + '</select></label>' +
        '<div class="zz-cc__btns"><button id="ccAppSave" class="zz-cc__btn">保存外观</button></div>' +
        '<div id="ccAppMsg" class="zz-cc__msg"></div>';
      document.getElementById('ccTheme').addEventListener('change', function () {
        try { document.documentElement.dataset.theme = this.value; } catch (e) {}
      });
      document.getElementById('ccAppSave').addEventListener('click', function () {
        var name = document.getElementById('ccName').value.trim() || '小6';
        var theme = document.getElementById('ccTheme').value;
        try {
          document.documentElement.dataset.theme = theme;
          var s = {}; try { s = JSON.parse(localStorage.getItem('xiao6_settings_v1') || '{}'); } catch (e) {}
          s.aiName = name; s.theme = theme; localStorage.setItem('xiao6_settings_v1', JSON.stringify(s));
        } catch (e) {}
        postJSON('/api/config', { AI_DISPLAY_NAME: name, XIAO6_THEME: theme }).then(function (r) {
          document.getElementById('ccAppMsg').textContent = r.ok ? '✓ 已保存' : ('保存失败：' + (r.error || '未知'));
        });
      });
    });
  }

  /* ============================ 隐私 ============================ */
  function renderPrivacy(panel) {
    panel.innerHTML =
      '<h3 class="zz-cc__h">隐私</h3>' +
      '<p class="zz-cc__lead">隐私不是开关，而是小6的设计底色。</p>' +
      row('数据存储', '<span class="zz-cc__badge zz-cc__badge--ok">仅本机</span>', '推理与数据默认不出这台设备') +
      row('API Key', '<span class="zz-cc__badge zz-cc__badge--ok">不回显</span>', '只存于本机 .env，界面永不显示') +
      row('云端传输', '仅在你配置并使用时', '对话/搜索/媒体等第三方能力由你显式开启') +
      '<div class="zz-cc__btns"><button id="ccExport" class="zz-cc__btn">导出我的数据</button></div>' +
      '<div id="ccPrivMsg" class="zz-cc__msg"></div>' +
      '<div class="zz-cc__note">导出会把本机数据库打包下载，仅你本人可见。小6不内置任何遥测或远程回传。</div>';
    document.getElementById('ccExport').addEventListener('click', function () {
      var msg = document.getElementById('ccPrivMsg');
      msg.textContent = '准备导出…';
      getJSON('/api/data/export').then(function (r) {
        if (r && r.url) { window.open(r.url, '_blank'); msg.textContent = '✓ 已开始下载'; }
        else if (r && r._network_error) msg.textContent = '未连接，无法导出';
        else msg.textContent = '导出已触发';
      });
    });
  }

  /* ============================ 安全 ============================ */
  function renderSecurity(panel) {
    return (cache.config || (cache.config = getJSON('/api/config'))).then(function (cfg) {
      cfg = cfg || {};
      var sec = cfg.security || {};
      var tf = cfg.tool_factory || {};
      var remote = cfg.remote || {};
      var rows = [
        ['文件沙箱', truthy(sec.fileSandbox) ? ok() : warn()],
        ['命令沙箱', truthy(sec.execSandbox) ? ok() : warn()],
        ['远程访问令牌', remote.token_set ? warn('已设置') : ok('未设置（仅本机）')],
        ['能力工厂·命令执行', truthy(tf.command_enabled) ? warn('已开（谨慎）') : ok('已禁用')]
      ];
      panel.innerHTML =
        '<h3 class="zz-cc__h">安全</h3>' +
        '<p class="zz-cc__lead">小6在本机以沙箱方式运行工具，默认只做低风险的本地操作。</p>' +
        rows.map(function (r) { return row(r[0], r[1]); }).join('') +
        (sec.blockedTools && sec.blockedTools.length ? row('禁用能力', esc(sec.blockedTools.join(', '))) : '') +
        '<div class="zz-cc__planned">' +
          '<div class="zz-cc__k" style="margin-bottom:6px">关于 DRM</div>' +
          '<div class="zz-cc__note" style="margin-top:0">小6不内置任何 DRM、远程锁或激活校验。你始终拥有本机数据的完全控制权，可随时导出、删除或离线运行。</div>' +
        '</div>';
    });
  }

  /* ============================ 依赖 / 就绪 ============================ */
  function renderDependencies(panel) {
    panel.innerHTML = '<div class="zz-cc__loading">检测中…</div>';
    if (global.ZZDependencyManager) {
      global.ZZDependencyManager.probe().then(function (res) {
        var host = document.createElement('div');
        global.ZZDependencyManager.render(host, res);
        panel.innerHTML = '<h3 class="zz-cc__h">依赖 / 就绪</h3>' +
          '<p class="zz-cc__lead">按"核心 / 可选 / 增强"三级评估你的环境。状态含义：' +
          statusBadge('READY') + ' 可用 · ' + statusBadge('NOT_CONFIGURED') + ' 需配置 · ' +
          statusBadge('NOT_INSTALLED') + ' 可装 · ' + statusBadge('OPTIONAL') + ' 可选 · ' +
          statusBadge('UNAVAILABLE') + ' 不可用 · ' + statusBadge('ERROR') + ' 异常。</p>';
        panel.appendChild(host);
      });
    } else {
      panel.innerHTML = '<div class="zz-cc__note">依赖管理器未加载。</div>';
    }
  }

  /* ============================ 数据 ============================ */
  function renderData(panel) {
    return (cache.memory || (cache.memory = getJSON('/api/memory'))).then(function (m) {
      m = m || {};
      panel.innerHTML =
        '<h3 class="zz-cc__h">数据</h3>' +
        '<p class="zz-cc__lead">你的所有数据都在本机。你可以随时导出或重新梳理。</p>' +
        row('笔记', String(m.note_count != null ? m.note_count : '—')) +
        row('对话记录', String(m.log_count != null ? m.log_count : '—')) +
        '<div class="zz-cc__btns">' +
          '<button id="ccExport2" class="zz-cc__btn">导出全部数据</button>' +
          '<button id="ccBackfill2" class="zz-cc__btn zz-cc__btn--ghost">重新梳理记忆</button>' +
        '</div>' +
        '<div id="ccDataMsg" class="zz-cc__msg"></div>' +
        '<div class="zz-cc__note">导出为本地打包文件；梳理会把历史对话沉淀为长期记忆。</div>';
      document.getElementById('ccExport2').addEventListener('click', function () {
        getJSON('/api/data/export').then(function (r) {
          if (r && r.url) window.open(r.url, '_blank');
          document.getElementById('ccDataMsg').textContent = r && r._network_error ? '未连接' : '✓ 已触发导出';
        });
      });
      document.getElementById('ccBackfill2').addEventListener('click', function () {
        postJSON('/api/memory/backfill', {}).then(function (r) {
          document.getElementById('ccDataMsg').textContent = r.ok ? '✓ 已触发' : ('失败：' + (r.error || '未知'));
        });
      });
    });
  }

  /* ============================ 启动 ============================ */
  function renderStartup(panel) {
    return (cache.boot || (cache.boot = getJSON('/api/boot/state'))).then(function (b) {
      b = b || {};
      panel.innerHTML =
        '<h3 class="zz-cc__h">启动</h3>' +
        '<p class="zz-cc__lead">小6随桌面客户端启动。下面是当前启动就绪状态。</p>' +
        row('启动状态', esc(b.state || (b._network_error ? '未连接' : '—'))) +
        row('服务就绪', truthy(b.ready) ? ok() : off()) +
        '<div class="zz-cc__note">' +
          '· 桌面客户端负责拉起服务并常驻托盘，前端零改动。<br>' +
          '· 自启动由操作系统的登录项管理，可在系统设置中开关。<br>' +
          '· 构建渠道（开发 / 发布）由启动脚本决定，运行时不可见，属正常设计。' +
        '</div>';
    });
  }

  /* ============================ 开发者 ============================ */
  function renderDeveloper(panel) {
    return (cache.config || (cache.config = getJSON('/api/config'))).then(function (cfg) {
      cfg = cfg || {};
      var feats = [
        ['知识平台', cfg.feature_knowledge_platform],
        ['主动智能 V2', cfg.feature_proactive_v2],
        ['多端同步', cfg.feature_multi_device],
        ['常驻伴随', cfg.feature_always_on],
        ['跨端接力', cfg.feature_cross_device],
        ['移动伴随端', cfg.feature_mobile_companion],
        ['日历感知', cfg.feature_calendar_sense],
        ['应用焦点', cfg.feature_app_focus],
        ['剪贴板感知', cfg.feature_clipboard_sense],
        ['人格引擎', cfg.feature_persona],
        ['记忆蒸馏', cfg.feature_memory_distill],
        ['唤醒词', cfg.kws_enabled]
      ];
      var rows = feats.map(function (f) { return row(f[0], truthy(f[1]) ? ok() : off()); }).join('');
      var ver = cfg.version || {};
      panel.innerHTML =
        '<h3 class="zz-cc__h">开发者</h3>' +
        '<p class="zz-cc__lead">这些是功能开关的实时状态（只读）。改动需编辑本机配置并重启。</p>' +
        row('应用版本', esc(ver.current || '—')) +
        row('应用名', esc(ver.app_name || cfg.ai_name || '小6')) +
        rows +
        '<div class="zz-cc__note">工具工厂命令执行、远程访问令牌等高危开关默认关闭。需调整请编辑 .env。</div>';
    });
  }

  /* ============================ 关于 ============================ */
  function renderAbout(panel) {
    return (cache.version || (cache.version = getJSON('/api/version'))).then(function (ver) {
      ver = ver || {};
      panel.innerHTML =
        '<h3 class="zz-cc__h">关于</h3>' +
        '<p class="zz-cc__lead">小6 · 你的本地 AI 副驾。</p>' +
        row('名字', esc(ver.app_name || '小6')) +
        row('版本', esc(ver.version || '—')) +
        row('发布通道', channelTag((cache.config && cache.config.build_channel) || 'development')) +
        row('运行方式', '<span class="zz-cc__badge zz-cc__badge--ok">本地</span> 数据不出设备') +
        '<div class="zz-cc__note">' +
          '小6是一个完全运行在你设备上的个人 AI：推理、记忆与工具都在本地完成，' +
          '只有你显式配置的云端能力（如联网搜索）才会对外通信。<br><br>' +
          '本软件不含任何遥测、DRM 或远程锁。你可以随时导出、删除数据，或完全离线使用。' +
        '</div>' +
        (ver.check_url ? '<div class="zz-cc__btns"><a class="zz-cc__btn zz-cc__btn--ghost" href="' + esc(ver.check_url) + '" target="_blank" rel="noopener">查看更新</a></div>' : '');
    });
  }

  /* ============================ 模型注册表（Phase B/C · 纯前端，禁改 server） ============================ */
  function renderModels(panel) {
    return Promise.all([
      cache.config || (cache.config = getJSON('/api/config')),
      getJSON('/api/providers/probe').catch(function () { return { probe: {} }; }),
      cache.health || (cache.health = getJSON('/api/health'))
    ]).then(function (res) {
      var cfg = res[0] || {}, probe = (res[1] && res[1].probe) || {}, h = res[2] || {};
      var asr = cfg.asr || {}, llm = cfg.llm || {};
      var localKeys = Object.keys(probe);

      var cloudKey = truthy(llm.key_present || cfg.AGNES_API_KEY || cfg.AGES_API_KEY);
      var cloudModel = llm.model || cfg.AGNES_MODEL || h.model || '未配置';
      var cloudState = cloudKey ? 'READY' : 'NOT_CONFIGURED';

      var asrOn = asr.provider && asr.provider !== 'none';
      var asrState = asrOn ? 'READY' : (asr.local_supported ? 'NOT_INSTALLED' : 'OPTIONAL');

      var localState = localKeys.length ? 'READY' : 'UNAVAILABLE';

      panel.innerHTML =
        '<h3 class="zz-cc__h">模型注册表</h3>' +
        '<p class="zz-cc__lead">小6按"需要才装"管理模型。核心对话模型为必需；语音识别等重模型为可选，仅在你启用时于本机下载。</p>' +
        modelRow('云端对话模型', cloudState, esc(cloudModel)) +
        modelRow('语音识别 (ASR)', asrState, asrOn ? esc(asr.provider) : '可选能力（默认关闭）') +
        modelRow('本地模型运行时', localState, localKeys.length ? esc(localKeys.join(', ')) : '未检测到（使用云端无需此项）') +
        '<details class="zz-cc__details"><summary>如何安装本地语音识别（~1GB，可选）</summary>' +
        '<div class="zz-cc__note">本地语音识别（Vosk / Whisper）为可选重模型，默认不下载。启用方式：' +
        '在「语音」中选择 ASR 提供方；若需本机识别，可在启动小6前设置环境变量 ' +
        '<code>XIAO6_INSTALL_ASR=1</code> 后启动，小6会在首次启动时于本机拉取所需模型。' +
        '此过程仅使用本机算力，不向任何第三方上传你的语音。</div></details>' +
        '<div class="zz-cc__note">更换云端模型请前往「AI / 模型」；所有密钥仅存于本机 .env，界面不回显。</div>';
    });
  }
  function modelRow(name, state, detail) {
    return '<div class="zz-cc__row"><div class="zz-cc__k">' + esc(name) + '</div>' +
      '<div class="zz-cc__v">' + statusBadge(state) + (detail ? ' <span class="zz-cc__sub">' + detail + '</span>' : '') + '</div></div>';
  }

  /* ------------------------------ 小部件 ------------------------------ */
  function row(k, v, sub) {
    return '<div class="zz-cc__row"><div class="zz-cc__k">' + esc(k) +
      (sub ? ' <span class="zz-cc__sub">' + esc(sub) + '</span>' : '') +
      '</div><div class="zz-cc__v">' + (v || '—') + '</div></div>';
  }
  function ok(t) { return '<span class="zz-cc__badge zz-cc__badge--ok">' + (t || '开') + '</span>'; }
  function warn(t) { return '<span class="zz-cc__badge zz-cc__badge--warn">' + (t || '未配置') + '</span>'; }
  function off(t) { return '<span class="zz-cc__badge zz-cc__badge--bad">' + (t || '关') + '</span>'; }

  /* 能力状态（Phase 38I · P1-1 统一收敛到 capability-health.js 单一真相源；CC 仅复用，不再私有枚举） */
  var STATUS6 = {
    READY:          { cls: 'ok',    label: '就绪' },
    NOT_CONFIGURED: { cls: 'warn',  label: '未配置' },
    NOT_INSTALLED:  { cls: 'warn',  label: '未安装' },
    OPTIONAL:       { cls: 'muted', label: '可选' },
    UNAVAILABLE:    { cls: 'bad',   label: '不可用' },
    ERROR:          { cls: 'bad',   label: '异常' },
    DISABLED:       { cls: 'muted', label: '已停用' }
  };
  function statusBadge(state) {
    // 统一走 capability-health.js 渲染（含规约 12 态 + 兼容态）；入参为大写历史 key，归一化后查 META
    if (global.ZZCapabilityHealth) return global.ZZCapabilityHealth.badge(String(state).toLowerCase());
    var s = STATUS6[state] || STATUS6.UNAVAILABLE;
    return '<span class="zz-cc__badge zz-cc__badge--' + s.cls + '">' + s.label + '</span>';
  }

  /* AI 面板当前连接状态行（Phase 38I · P1-2）
     由真实 /api/test-llm 结果驱动，不再以 key_present 判 READY：
       - ai.state==='ready'   → 已连接（委托 statusBadge('READY')，附真实延迟 ms）
       - ai.state==='failed'  → 连接失败（委托 statusBadge('CONNECTION_FAILED')，附真实 error）
       - 其它（未测/超时/无 key/离线）→ 待验证（委托 statusBadge('NOT_TESTED')）
     ai 为可选：renderAi 初次同步渲染传 null（显示"待验证"），随后异步探测再就地更新 #ccAiStatus。 */
  function aiStatusLine(cfg, ai) {
    cfg = cfg || {};
    var a = cfg.active_provider || (cfg.llm && cfg.llm.active) || 'agnes';
    var sp = (cfg.providers || []).find(function (p) { return p.id === a; });
    var lbl = sp ? sp.label : ((CLOUD_PRESETS.find(function (p) { return p.id === a; }) || { label: a }).label);
    var inner;
    if (ai && ai.state === 'ready') {
      inner = statusBadge('READY') + (ai.latency != null ? ' <span class="zz-cc__sub">' + esc(ai.latency) + ' ms</span>' : '');
    } else if (ai && ai.state === 'failed') {
      inner = statusBadge('CONNECTION_FAILED') + (ai.error ? ' <span class="zz-cc__sub">' + esc(clip(ai.error, 80)) + '</span>' : '');
    } else {
      inner = statusBadge('NOT_TESTED');
    }
    return '<div class="zz-cc__note">当前服务：' + esc(lbl) + ' · <span id="ccAiStatus">' + inner + '</span>' +
      '（填好密钥并保存来源后，点"测试连通"可验证）</div>';
  }

  /* 发布通道徽章（Phase 38F · F1 开发版 / F2 RC 预览 / F3 正式版）
     仅展示标签，不含任何 audit / phase / debug 内部词。 */
  function channelTag(channel) {
    channel = (channel || 'development').toLowerCase();
    if (channel === 'release') return '<span class="zz-cc__badge zz-cc__badge--ok">正式版</span>';
    if (channel === 'rc') return '<span class="zz-cc__badge zz-cc__badge--plan">预览版</span>';
    return '<span class="zz-cc__badge zz-cc__badge--warn">开发版</span>';
  }

  global.ZZControlCenter = { open: open, SECTIONS: SECTIONS, statusBadge: statusBadge, STATUS6: STATUS6 };
})(typeof window !== 'undefined' ? window : globalThis);
