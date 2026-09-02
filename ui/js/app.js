/* =========================================================
   小6 (Six) UI 2.0 — app.js
   唯一正式 UI：G:\xiao6\ui，由 Xiao6 server :8000 同源托管
   所有 API 使用同源相对路径 /api/*（无代理、无跨端口、无硬编码 8765）
   无任何 mock / 假数据；加载中显示 loading，失败显示 error+重试
   ========================================================= */
(function () {
  "use strict";

  /* ---------------- 基础工具 ---------------- */
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => Array.from(document.querySelectorAll(s));
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  let toastTimer = null;
  function toast(msg, isErr) {
    const t = $("#toast");
    t.textContent = msg;
    t.className = "toast show" + (isErr ? " err" : "");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { t.className = "toast"; }, isErr ? 4200 : 2400);
  }

  const LOADING = '<div class="mini-loading"><span class="spinner"></span>加载中…</div>';
  function empty(text) { return '<div class="empty-state">' + esc(text) + "</div>"; }
  function errorBox(text, detail) {
    return '<div class="error-state"><div>' + esc(text) + "</div>" +
      (detail ? '<div class="detail">' + esc(detail) + "</div>" : "") +
      '<button class="customize-btn" style="margin-top:10px" onclick="location.reload()">重试</button></div>';
  }

  /* ---------------- API ---------------- */
  async function api(path, opts) {
    const res = await fetch(path, opts || {});
    const ct = res.headers.get("content-type") || "";
    if (!res.ok) {
      let detail = "";
      try { const j = await res.json(); detail = j.detail || j.error || JSON.stringify(j); } catch (e) { detail = res.statusText; }
      throw new Error("HTTP " + res.status + " · " + detail);
    }
    return ct.indexOf("application/json") >= 0 ? res.json() : res.text();
  }
  const getJSON = (p) => api(p);
  const postJSON = (p, body) => api(p, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  /* ---------------- 全局状态 ---------------- */
  const S = {
    health: null,       // /api/health → 62 工具
    caps: null,         // /api/capability_os/catalog → 33 能力（含分组/图标/可用状态）
    tasks: [],
    goals: [],
    knowledge: [],
    memories: [],
    profile: null,      // /api/memory → 用户画像
    notes: [],
    learnings: [],
    episodes: [],
    activity: null,
    trace: null,
    version: null,
    userModel: null,
    briefing: null,
    agentState: null,
    config: null,
    history: [],
    conversation: [],   // 当前会话 messages（发送给 /api/chat）
    busy: false,
    search: false,
    deep: false,
  };

  // 能力目录：真实后端 /api/capability_os/catalog（33 项 / 27 可用 / 10 分组）
  async function ensureCaps() {
    if (S.caps) return S.caps;
    try {
      S.caps = await getJSON("/api/capability_os/catalog");
    } catch (e) {
      S.caps = null;   // 不让单个接口失败拖垮整个页面
    }
    return S.caps;
  }

  /* =========================================================
     启动
     ========================================================= */
  boot();

  async function boot() {
    bindNav();
    bindComposer();
    bindActions();
    bindToolSearch();
    bindMemorySearch();
    await refreshHealth();   // 先探活，决定整体状态
    loadRecent();
    loadAbilities();
    loadBriefing();        // 今日简报 + 天气 + 热点
    loadTaskPreview();
    initEventStream();     // 实时事件总线：主动推送 + 审批请求
    // 其余页面进入时再加载，避免启动打爆后端
  }

  async function refreshHealth() {
    const dot = $("#liveDot");
    try {
      S.health = await getJSON("/api/health");
      dot.className = "live-dot online";
      dot.title = "后端在线 · " + (S.health.model || "") + " · 工具 " + ((S.health.tools || []).length);
      const n = (S.health.tools || []).length;
      $("#toolBadge").textContent = n ? n + " tools" : "—";
      $("#heroSub").textContent = "你的专属 AI 助手 · " + (S.health.model || "") +
        " · 已挂载 " + n + " 个工具";
      return true;
    } catch (e) {
      dot.className = "live-dot offline";
      dot.title = "后端不可达";
      $("#heroSub").textContent = "无法连接后端：" + e.message;
      $("#toolBadge").textContent = "offline";
      $("#abilityGrid").innerHTML = errorBox("后端不可达", e.message);
      $("#taskPreview").innerHTML = "";
      $("#recentList").innerHTML = errorBox("后端不可达", e.message);
      setHeart("error");
      return false;
    }
  }

  /* =========================================================
     导航
     ========================================================= */
  function bindNav() {
    $$(".nav-item").forEach((btn) => {
      btn.addEventListener("click", () => switchView(btn.dataset.view));
    });
    document.addEventListener("click", (e) => {
      const el = e.target.closest("[data-view]");
      if (el && !el.classList.contains("nav-item")) switchView(el.dataset.view);
    });
  }

  function switchView(name) {
    $$(".nav-item").forEach((b) => b.classList.toggle("active", b.dataset.view === name));
    $$(".view").forEach((v) => v.classList.toggle("active", v.id === "view-" + name));
    // 进入页面时按需拉取真实数据
    if (name === "tasks") loadTasks();
    if (name === "knowledge") loadKnowledge();
    if (name === "memory") loadMemory();
    if (name === "tools") loadTools();
    if (name === "agents") loadAgents();
    if (name === "settings") loadSettings();
    if (name === "chat") {
      const box = $("#chatScroll");
      box.scrollTop = box.scrollHeight;
      $("#input").focus();
    }
  }

  function bindActions() {
    // 侧栏最近对话点击 → 真实会话恢复
    document.addEventListener("click", (e) => {
      const s = e.target.closest("[data-session]");
      if (s && s.dataset.session) resumeSession(s.dataset.session);
    });
    document.addEventListener("click", (e) => {
      const el = e.target.closest("[data-act]");
      if (!el) return;
      const a = el.dataset.act;
      if (a === "reload-tasks") loadTasks();
      if (a === "reload-knowledge") loadKnowledge();
      if (a === "reload-memory") loadMemory();
      if (a === "reload-tools") loadTools();
      if (a === "reload-agents") loadAgents();
      if (a === "reload-settings") loadSettings();
      if (a === "reload-briefing") loadBriefing();
    });
  }

  /* =========================================================
     最近对话（真实 /api/chat/history）
     ========================================================= */
  // 最近对话 = 真实会话列表 /api/sessions（可点击恢复）
  async function loadRecent() {
    const box = $("#recentList");
    try {
      const r = await getJSON("/api/sessions");
      const list = (r && r.sessions) || [];
      S.history = list;
      if (!list.length) { box.innerHTML = empty("暂无历史会话"); return; }
      box.innerHTML = list.slice(0, 6).map((s) => {
        const sid = s.session_id || s.id || "";
        // 去掉内部前缀与 _stale 后缀，尽量显示可读名
        const label = String(sid).replace(/^p\d+_/, "").replace(/_stale$/, "").slice(0, 20) || "会话";
        const time = String(s.updated_at || s.created_at || "").slice(5, 16);
        return '<button class="recent-item" data-session="' + esc(sid) + '" title="' + esc(sid) + '">' +
          '<span class="title">' + esc(label) + "</span>" +
          '<span class="time">' + esc(time) + "</span></button>";
      }).join("");
    } catch (e) {
      box.innerHTML = errorBox("会话列表读取失败", e.message);
    }
  }

  // 会话恢复：POST /api/session/resume {session_id}
  async function resumeSession(sid) {
    try {
      const d = await postJSON("/api/session/resume", { session_id: sid });
      const r = (d && d.resume) || {};
      if (d && d.ok) {
        toast("已恢复会话：" + String(sid).slice(0, 18));
        await renderHistoryIntoChat();
        switchView("chat");
      } else {
        toast("无法恢复：" + (r.reason || r.status || "无检查点"), true);
      }
    } catch (e) {
      toast("会话恢复失败：" + e.message, true);
    }
  }

  // 把真实对话历史渲染进消息流
  async function renderHistoryIntoChat() {
    try {
      const rows = await getJSON("/api/chat/history?limit=20");
      const list = Array.isArray(rows) ? rows : (rows.items || rows.history || []);
      if (!list.length) return;
      ensureChatMode();
      $("#messages").innerHTML = "";
      list.forEach((h) => {
        const role = (h.role === "user" || h.role === "human") ? "user" : "assistant";
        addMsg(role, esc(h.content || h.text || h.message || ""));
      });
    } catch (e) {
      toast("历史加载失败：" + e.message, true);
    }
  }

  /* =========================================================
     能力卡片（来自真实工具名，不硬编码）
     ========================================================= */
  const ABILITY_DEF = [
    { key: "memory_search", name: "智能记忆", desc: "记住你的偏好与上下文", ico: "brain" },
    { key: "file_write", name: "代码助手", desc: "读写代码、调试、优化", ico: "code" },
    { key: "add_knowledge", name: "知识库", desc: "文档入库与检索", ico: "doc" },
    { key: "run_shell", name: "系统执行", desc: "命令、进程与自动化", ico: "term" },
    { key: "web_search", name: "联网搜索", desc: "实时检索网络信息", ico: "globe" },
    { key: "media_generate", name: "内容生成", desc: "图像、媒体与创作", ico: "img" },
  ];
  const ICONS = {
    brain: '<path d="M9 4a3 3 0 1 1-3 3"/><path d="M6 10v3a6 6 0 0 0 12 0v-3"/><path d="M9 7v6"/><path d="M15 7v3"/>',
    code: '<path d="M8 6l-5 6 5 6"/><path d="M16 6l5 6-5 6"/>',
    doc: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/>',
    term: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 9l3 3-3 3M13 15h4"/>',
    globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0 18"/>',
    img: '<rect x="3" y="5" width="18" height="14" rx="2"/><circle cx="9" cy="11" r="2"/><path d="M21 17l-5-5-7 7"/>',
  };

  /* =========================================================
     今日简报（真实 /api/briefing + /api/weather + /api/hotspots）
     ========================================================= */
  async function loadBriefing() {
    const box = $("#briefingBox");
    if (!box) return;
    box.innerHTML = LOADING;
    let html = "", errs = [];

    // ① 简报
    try {
      const b = await getJSON("/api/briefing");
      S.briefing = b;
      const parts = [];
      if (b.date) parts.push("日期 " + b.date);
      if (b.generatedAt) parts.push("生成 " + b.generatedAt);
      const w = b.weather || {};
      if (w.city) parts.push(w.city + " " + (w.condition || ""));
      let body = b.summary || b.content || b.text || "";
      if (!body && b.weather) body = JSON.stringify(w);
      html += '<div class="proactive-card"><div class="pc-head">☀️ 每日简报</div>' +
        '<div class="pc-body">' + esc(body || "（简报为空）") + "</div>" +
        (parts.length ? '<div class="pc-time">' + esc(parts.join(" · ")) + "</div>" : "") +
        "</div>";
    } catch (e) { errs.push("简报：" + e.message); }

    // ② 天气
    try {
      const w = await getJSON("/api/weather");
      const d = w.data || w;
      html += '<div class="proactive-card"><div class="pc-head">🌤 天气</div>' +
        '<div class="pc-body">' + esc(JSON.stringify(d).slice(0, 300)) + "</div>" +
        (w.fetchedAt ? '<div class="pc-time">获取于 ' + esc(w.fetchedAt) + "</div>" : "") +
        "</div>";
    } catch (e) { errs.push("天气：" + e.message); }

    // ③ 热点
    try {
      const h = await getJSON("/api/hotspots");
      const list = h.items || h.hotspots || (Array.isArray(h) ? h : []);
      if (list.length) {
        html += '<div class="proactive-card"><div class="pc-head">🔥 热点</div>' +
          '<div class="pc-body">' +
          list.slice(0, 8).map((x, i) =>
            esc((i + 1) + ". " + (x.title || x.topic || String(x)))).join("\n") +
          "</div></div>";
      }
    } catch (e) { errs.push("热点：" + e.message); }

    if (errs.length) html += errorBox("部分简报数据读取失败", errs.join(" · "));
    box.innerHTML = html || empty("暂无简报数据");
  }

  // 首页能力卡片：数据源为真实 /api/capability_os/catalog，不硬编码
  async function loadAbilities() {
    const box = $("#abilityGrid");
    box.innerHTML = LOADING;
    const caps = await ensureCaps();
    if (!caps || !caps.groups) {
      // 降级：退回 health.tools 的真实工具名
      const tools = (S.health && S.health.tools) || [];
      box.innerHTML = tools.length
        ? '<div class="grid">' + tools.slice(0, 6).map((t) =>
            '<div class="tool-card"><div class="tool-name">' + esc(t) + "</div>" +
            '<div class="tool-desc">已挂载工具</div></div>').join("") + "</div>"
        : empty("能力目录不可用");
      return;
    }
    // 优先展示 available 的能力，最多 6 个
    const all = [];
    Object.keys(caps.groups).forEach((g) => {
      caps.groups[g].forEach((c) => all.push(c));
    });
    all.sort((a, b) => (b.available ? 1 : 0) - (a.available ? 1 : 0));
    const picked = all.slice(0, 6);
    box.innerHTML = '<div class="grid">' + picked.map((c) =>
      '<div class="tool-card" title="' + esc(c.id) + " · risk=" + esc(c.risk || "?") +
      " · permission=" + esc(c.permission || "?") + '">' +
      '<div class="tool-name">' + esc(c.icon || "") + " " + esc(c.name || c.id) + "</div>" +
      '<div class="tool-desc">' + esc((c.description || "").slice(0, 40)) + "</div>" +
      '<div class="row-foot"><span>' + esc(c.group || "") + "</span>" +
      '<span class="badge ' + (c.available ? "ok" : "") + '">' +
      (c.available ? "可用" : "不可用") + "</span></div></div>").join("") + "</div>";
  }

  /* =========================================================
     任务
     ========================================================= */
  async function loadTaskPreview() {
    const box = $("#taskPreview");
    try {
      const rows = await getJSON("/api/tasks");
      S.tasks = Array.isArray(rows) ? rows : [];
      const running = S.tasks.filter((t) => {
        const s = String(t.status || "").toLowerCase();
        return s === "running" || s === "in_progress" || s === "active" || s === "pending";
      });
      if (!S.tasks.length) { box.innerHTML = empty("暂无任务"); return; }
      const list = (running.length ? running : S.tasks).slice(0, 2);
      box.innerHTML = list.map(taskCardHTML).join("");
    } catch (e) {
      box.innerHTML = errorBox("任务读取失败", e.message);
    }
  }

  function taskCardHTML(t) {
    const st = String(t.status || "unknown");
    const pct = Number(t.progress || t.percent || 0) || 0;
    const steps = Array.isArray(t.steps) ? t.steps.length : 0;
    return '<div class="task-card">' +
      '<div class="task-icon">&gt;_</div>' +
      '<div class="task-meta">' +
      '<div class="task-title">' + esc(t.title || "(无标题)") + "</div>" +
      '<div class="task-sub"><span class="pulse-dot"></span>' + esc(st) +
      (steps ? " · " + steps + " 步" : "") + "</div>" +
      "</div>" +
      '<div class="progress-wrap"><div class="progress"><span style="width:' + Math.min(100, pct) + '%"></span></div>' +
      '<div class="progress-pct">' + Math.round(pct) + "%</div></div>" +
      '<button class="customize-btn" data-view="tasks">详情</button></div>';
  }

  async function loadTasks() {
    const tb = $("#tasksBody"), gb = $("#goalsBody");
    tb.innerHTML = LOADING; gb.innerHTML = LOADING;
    try {
      const rows = await getJSON("/api/tasks");
      S.tasks = Array.isArray(rows) ? rows : [];
      tb.innerHTML = S.tasks.length
        ? '<div class="list">' + S.tasks.map(taskRowHTML).join("") + "</div>"
        : empty("暂无任务");
    } catch (e) { tb.innerHTML = errorBox("任务读取失败", e.message); }

    try {
      const g = await getJSON("/api/goals");
      S.goals = Array.isArray(g) ? g : (g.goals || []);
      gb.innerHTML = S.goals.length
        ? '<div class="list">' + S.goals.map(goalRowHTML).join("") + "</div>"
        : empty("暂无目标");
    } catch (e) { gb.innerHTML = errorBox("目标读取失败", e.message); }

    // ③ 活动统计 /api/activity + 执行追踪 /api/trace（真实后端能力）
    try {
      const act = await getJSON("/api/activity");
      S.activity = act && act.activity ? act.activity : null;
    } catch (e) { S.activity = null; }
    try {
      const tr = await getJSON("/api/trace");
      S.trace = tr && tr.trace ? tr.trace : null;
    } catch (e) { S.trace = null; }

    const extra = document.createElement("div");
    let eh = '<div class="page-head" style="margin-top:30px"><h1>运行状况</h1></div>';
    if (S.activity) {
      const a = S.activity;
      eh += '<div class="row-card"><div class="row-foot">' +
        (a.session_id ? "<span>会话 " + esc(a.session_id) + "</span>" : "") +
        (a.conversation_turns != null ? "<span>对话轮次 " + esc(a.conversation_turns) + "</span>" : "") +
        (a.active_goals != null ? "<span>活跃目标 " + esc(a.active_goals) + "</span>" : "") +
        "</div></div>";
    }
    if (S.trace && Array.isArray(S.trace.trace)) {
      const rows = S.trace.trace.slice(-15).reverse();
      eh += '<div class="page-head" style="margin-top:20px"><h1 style="font-size:16px">最近执行追踪' +
        '<span class="badge" style="margin-left:10px">' + S.trace.trace.length + "</span></h1></div>" +
        '<div class="list">' + rows.map((t) =>
          '<div class="row-card"><div class="row-title">' + esc(t.event || t.type || t.action || "event") + "</div>" +
          (t.detail ? '<div class="row-desc">' + esc(String(t.detail).slice(0, 140)) + "</div>" : "") +
          (t.timestamp ? '<div class="row-foot"><span>' + esc(t.timestamp) + "</span></div>" : "") +
          "</div>").join("") + "</div>";
    }
    if (!S.activity && !S.trace) eh += empty("活动与追踪数据不可用");
    extra.innerHTML = eh;
    const host = $("#view-tasks .page");
    const old = host.querySelector("#runtimeExtra");
    if (old) old.remove();
    extra.id = "runtimeExtra";
    host.appendChild(extra);
  }

  function taskRowHTML(t) {
    const st = String(t.status || "unknown");
    const cls = /complet|done|成功/.test(st) ? "ok" : /running|progress|active|pending/.test(st) ? "run" : "";
    return '<div class="row-card"><div class="row-title">' + esc(t.title || "(无标题)") +
      '<span class="badge ' + cls + '">' + esc(st) + "</span></div>" +
      (t.description ? '<div class="row-desc">' + esc(t.description) + "</div>" : "") +
      '<div class="row-foot">' +
      "<span>ID " + esc(t.id) + "</span>" +
      (t.created_at ? "<span>创建 " + esc(t.created_at) + "</span>" : "") +
      (Array.isArray(t.steps) ? "<span>" + t.steps.length + " 个步骤</span>" : "") +
      "</div></div>";
  }

  function goalRowHTML(g) {
    const st = String(g.status || "unknown");
    const cls = /complet|done/.test(st) ? "ok" : /active|progress|pending/.test(st) ? "run" : "";
    return '<div class="row-card"><div class="row-title">' + esc(g.title || "(无标题)") +
      '<span class="badge ' + cls + '">' + esc(st) + "</span></div>" +
      (g.description ? '<div class="row-desc">' + esc(g.description) + "</div>" : "") +
      '<div class="row-foot">' +
      (g.horizon ? "<span>周期 " + esc(g.horizon) + "</span>" : "") +
      (g.priority ? "<span>优先级 " + esc(g.priority) + "</span>" : "") +
      (g.progress != null ? "<span>进度 " + esc(g.progress) + "</span>" : "") +
      "</div></div>";
  }

  /* =========================================================
     知识库
     ========================================================= */
  async function loadKnowledge() {
    const box = $("#knowledgeBody");
    box.innerHTML = LOADING;
    try {
      const r = await getJSON("/api/knowledge");
      S.knowledge = Array.isArray(r) ? r : (r.docs || []);
      if (!S.knowledge.length) { box.innerHTML = empty("知识库为空"); return; }
      box.innerHTML = '<div class="list">' + S.knowledge.map((d) =>
        '<div class="row-card"><div class="row-title">' + esc(d.title || d.doc_id || "(无标题)") +
        '<span class="badge ' + (d.status === "reviewed" ? "ok" : "") + '">' + esc(d.status || "unknown") + "</span></div>" +
        (d.path ? '<div class="row-desc">' + esc(d.path) + "</div>" : "") +
        '<div class="row-foot">' +
        (d.type ? "<span>类型 " + esc(d.type) + "</span>" : "") +
        (Array.isArray(d.tags) && d.tags.length ? "<span>" + esc(d.tags.join(" / ")) + "</span>" : "") +
        "</div></div>").join("") + "</div>";
    } catch (e) { box.innerHTML = errorBox("知识库读取失败", e.message); }
  }

  /* =========================================================
     记忆
     ========================================================= */
  async function loadMemory() {
    const box = $("#memoryBody");
    box.innerHTML = LOADING;
    let html = "", errs = [];

    // ① 记忆条目
    try {
      const r = await getJSON("/api/memories");
      S.memories = Array.isArray(r) ? r : (r.items || r.memories || []);
      html += '<div class="page-head"><h1 style="font-size:16px">记忆条目' +
        '<span class="badge" style="margin-left:10px">' + S.memories.length + "</span></h1></div>";
      html += S.memories.length ? renderMemoryHTML(S.memories) : empty("暂无记忆");
    } catch (e) { errs.push("记忆：" + e.message); }

    // ② 用户画像（/api/memory → profile）
    try {
      const m = await getJSON("/api/memory");
      S.profile = m && m.profile ? m.profile : null;
      html += '<div class="page-head" style="margin-top:26px"><h1 style="font-size:16px">用户画像' +
        (S.profile ? '<span class="badge" style="margin-left:10px">' + S.profile.length + "</span>" : "") +
        "</h1></div>";
      html += S.profile && S.profile.length
        ? '<div class="grid">' + S.profile.map((p) =>
            '<div class="tool-card"><div class="tool-name">' + esc(p.key) + "</div>" +
            '<div class="tool-desc">' + esc(p.value) + "</div>" +
            (p.updated ? '<div class="row-foot"><span>' + esc(p.updated) + "</span></div>" : "") +
            "</div>").join("") + "</div>"
        : empty("暂无画像数据");
    } catch (e) { errs.push("画像：" + e.message); }

    // ③ 笔记 /api/notes
    try {
      const n = await getJSON("/api/notes");
      S.notes = Array.isArray(n) ? n : (n.notes || []);
      html += '<div class="page-head" style="margin-top:26px"><h1 style="font-size:16px">笔记' +
        '<span class="badge" style="margin-left:10px">' + S.notes.length + "</span></h1></div>";
      html += S.notes.length
        ? '<div class="list">' + S.notes.slice(0, 20).map((x) =>
            '<div class="row-card"><div class="row-title">' + esc(x.title || "(无标题)") + "</div>" +
            (x.markdown ? '<div class="row-desc">' + esc(String(x.markdown).slice(0, 120)) + "</div>" : "") +
            (x.ts ? '<div class="row-foot"><span>' + esc(x.ts) + "</span></div>" : "") +
            "</div>").join("") + "</div>"
        : empty("暂无笔记");
    } catch (e) { errs.push("笔记：" + e.message); }

    // ④ 学习记录 /api/learnings
    try {
      const l = await getJSON("/api/learnings");
      S.learnings = (l && l.learnings) || [];
      html += '<div class="page-head" style="margin-top:26px"><h1 style="font-size:16px">学习记录' +
        '<span class="badge" style="margin-left:10px">' + S.learnings.length + "</span></h1></div>";
      html += S.learnings.length
        ? '<div class="list">' + S.learnings.slice(0, 20).map((x) =>
            '<div class="row-card"><div class="row-title">' + esc(x.type || "learning") + "</div>" +
            '<div class="row-desc">' + esc(String(x.content || "").slice(0, 140)) + "</div>" +
            "</div>").join("") + "</div>"
        : empty("暂无学习记录");
    } catch (e) { errs.push("学习：" + e.message); }

    // ⑤ 事件 /api/episodes
    try {
      const ep = await getJSON("/api/episodes");
      S.episodes = (ep && ep.episodes) || [];
      html += '<div class="page-head" style="margin-top:26px"><h1 style="font-size:16px">事件' +
        '<span class="badge" style="margin-left:10px">' + S.episodes.length + "</span></h1></div>";
      html += S.episodes.length
        ? '<div class="list">' + S.episodes.slice(0, 20).map((x) =>
            '<div class="row-card"><div class="row-title">' + esc(x.title || "(无标题)") + "</div>" +
            (x.summary ? '<div class="row-desc">' + esc(String(x.summary).slice(0, 140)) + "</div>" : "") +
            "</div>").join("") + "</div>"
        : empty("暂无事件");
    } catch (e) { errs.push("事件：" + e.message); }

    // ⑥ 对话历史 /api/memory/conversations
    try {
      const c = await getJSON("/api/memory/conversations");
      const list = (c && c.conversations) || [];
      html += '<div class="page-head" style="margin-top:26px"><h1 style="font-size:16px">对话历史' +
        '<span class="badge" style="margin-left:10px">' + list.length + "</span></h1></div>";
      html += list.length
        ? '<div class="list">' + list.slice(0, 20).map((x) =>
            '<div class="row-card"><div class="row-title">' + esc(x.topic || "(无主题)") + "</div>" +
            (x.summary ? '<div class="row-desc">' + esc(String(x.summary).slice(0, 140)) + "</div>" : "") +
            (x.date ? '<div class="row-foot"><span>' + esc(x.date) + "</span></div>" : "") +
            "</div>").join("") + "</div>"
        : empty("暂无对话历史");
    } catch (e) { errs.push("对话历史：" + e.message); }

    // ⑦ 重要日期 /api/memory/important-dates
    try {
      const d = await getJSON("/api/memory/important-dates");
      const list = (d && d.dates) || [];
      html += '<div class="page-head" style="margin-top:26px"><h1 style="font-size:16px">重要日期' +
        '<span class="badge" style="margin-left:10px">' + list.length + "</span></h1></div>";
      html += list.length
        ? '<div class="list">' + list.slice(0, 20).map((x) =>
            '<div class="row-card"><div class="row-title">' + esc(x.description || x.title || "(无描述)") +
            '<span class="badge">' + esc(x.type || "date") + "</span></div>" +
            (x.date ? '<div class="row-foot"><span>' + esc(x.date) + "</span></div>" : "") +
            "</div>").join("") + "</div>"
        : empty("暂无重要日期");
    } catch (e) { errs.push("重要日期：" + e.message); }

    if (errs.length) html += errorBox("部分数据读取失败", errs.join(" · "));
    box.innerHTML = html || empty("无数据");
  }

  function renderMemoryHTML(list) {
    return '<div class="list">' + list.map((m) =>
      '<div class="row-card"><div class="row-title">' + esc(m.title || "(无标题)") +
      '<span class="badge">' + esc(m.event_type || m.type || "memory") + "</span></div>" +
      (m.content ? '<div class="row-desc">' + esc(m.content) + "</div>" : "") +
      '<div class="row-foot">' +
      (m.mem_id ? "<span>" + esc(m.mem_id) + "</span>" : "") +
      (m.created_at ? "<span>" + esc(m.created_at) + "</span>" : "") +
      (m.source ? "<span>来源 " + esc(m.source) + "</span>" : "") +
      "</div></div>").join("") + "</div>";
  }

  function renderMemory(list) {
    const box = $("#memoryBody");
    if (!list.length) { box.innerHTML = empty("没有匹配的记忆"); return; }
    box.innerHTML = '<div class="list">' + list.map((m) =>
      '<div class="row-card"><div class="row-title">' + esc(m.title || "(无标题)") +
      '<span class="badge">' + esc(m.event_type || m.type || "memory") + "</span></div>" +
      (m.content ? '<div class="row-desc">' + esc(m.content) + "</div>" : "") +
      '<div class="row-foot">' +
      (m.mem_id ? "<span>" + esc(m.mem_id) + "</span>" : "") +
      (m.created_at ? "<span>" + esc(m.created_at) + "</span>" : "") +
      (m.source ? "<span>来源 " + esc(m.source) + "</span>" : "") +
      "</div></div>").join("") + "</div>";
  }

  /* =========================================================
     工具（真实 62 个）
     ========================================================= */
  async function loadTools() {
    const box = $("#toolsBody");
    box.innerHTML = LOADING;
    try {
      if (!S.health) S.health = await getJSON("/api/health");
      const tools = (S.health && S.health.tools) || [];
      const caps = await ensureCaps();

      let html = "";
      // ① 能力目录（真实 33 项，按分组）
      if (caps && caps.groups) {
        $("#toolCount").textContent = (caps.total || 0) + " 项能力 · " +
          (caps.available || 0) + " 可用 · " + tools.length + " 个工具";
        Object.keys(caps.groups).forEach((g) => {
          const items = caps.groups[g];
          html += '<div class="page-head" style="margin-top:22px"><h1 style="font-size:16px">' +
            esc(g) + '<span class="badge" style="margin-left:10px">' + items.length + "</span></h1></div>" +
            '<div class="grid">' + items.map((c) =>
              '<div class="tool-card" title="entry: ' + esc(c.entry || "—") + '">' +
              '<div class="tool-name">' + esc(c.icon || "") + " " + esc(c.name || c.id) + "</div>" +
              '<div class="tool-desc">' + esc(c.description || "") + "</div>" +
              '<div class="row-foot">' +
              '<span>' + esc(c.group || "") + "</span>" +
              '<span>risk ' + esc(c.risk || "?") + "</span>" +
              '<span>' + esc(c.permission || "?") + "</span>" +
              (c.implemented === false ? '<span class="badge">未实现</span>' : "") +
              '<span class="badge ' + (c.available ? "ok" : "") + '">' +
              (c.available ? "可用" : "不可用") + "</span>" +
              "</div></div>").join("") + "</div>";
        });
      } else {
        $("#toolCount").textContent = tools.length + " 个工具";
        html += empty("能力目录不可用，仅展示工具清单");
      }

      // ② Agent 实际挂载的可调用工具（62 个）
      html += '<div class="page-head" style="margin-top:26px"><h1 style="font-size:16px">Agent 可调用工具' +
        '<span class="badge" style="margin-left:10px">' + tools.length + "</span></h1></div>";
      html += tools.length
        ? '<div class="grid">' + tools.map((t) =>
            '<div class="tool-card"><div class="tool-name">' + esc(t) + "</div>" +
            '<div class="tool-desc">已挂载 · 由 Agent 按需求自动调用</div></div>').join("") + "</div>"
        : empty("后端未返回工具");

      box.innerHTML = html;
    } catch (e) { box.innerHTML = errorBox("工具列表读取失败", e.message); }
  }

  // 工具搜索：同时筛能力名与工具名
  function bindToolSearch() {
    const input = $("#toolSearch");
    if (!input) return;
    input.addEventListener("input", () => {
      const q = input.value.trim().toLowerCase();
      let shown = 0;
      $$("#toolsBody .tool-card").forEach((card) => {
        const hit = !q || card.textContent.toLowerCase().indexOf(q) >= 0;
        card.style.display = hit ? "" : "none";
        if (hit) shown++;
      });
      const c = $("#toolCount");
      if (c && q) c.textContent = "匹配 " + shown + " 项";
    });
  }

  // 记忆搜索：回车/点击走真实后端 /api/memory/query，失败则本地过滤
  function bindMemorySearch() {
    const input = $("#memSearch"), btn = $("#btnMemSearch");
    if (!input) return;
    const run = async () => {
      const q = input.value.trim();
      if (!q) { $("#memoryBody").innerHTML = renderMemoryHTML(S.memories); return; }
      try {
        const r = await postJSON("/api/memory/query", { query: q });
        const list = Array.isArray(r) ? r : (r.results || r.items || []);
        if (list.length) {
          $("#memoryBody").innerHTML =
            '<div class="page-head"><h1 style="font-size:16px">后端检索结果' +
            '<span class="badge" style="margin-left:10px">' + list.length + "</span></h1></div>" +
            renderMemoryHTML(list);
          return;
        }
      } catch (e) { /* 后端检索不可用 → 降级本地过滤 */ }
      const low = q.toLowerCase();
      const hit = S.memories.filter((m) =>
        JSON.stringify(m).toLowerCase().indexOf(low) >= 0);
      $("#memoryBody").innerHTML = hit.length
        ? '<div class="page-head"><h1 style="font-size:16px">本地匹配' +
          '<span class="badge" style="margin-left:10px">' + hit.length + "</span></h1></div>" +
          renderMemoryHTML(hit)
        : empty("没有匹配的记忆");
    };
    if (btn) btn.addEventListener("click", run);
    input.addEventListener("keydown", (e) => { if (e.key === "Enter") run(); });
  }

  /* =========================================================
     智能体
     ========================================================= */
  async function loadAgents() {
    const box = $("#agentsBody");
    box.innerHTML = LOADING;
    try {
      const st = await getJSON("/api/agent/state");
      S.agentState = st;
      const tools = (S.health && S.health.tools) || [];
      const enabled = st.enabled ? '<span class="badge ok">enabled</span>' : '<span class="badge">disabled</span>';
      const running = st.running ? '<span class="badge run">running</span>' : '<span class="badge">stopped</span>';
      box.innerHTML =
        '<div class="row-card"><div class="row-title">小6 主 Agent ' + enabled + running + "</div>" +
        '<div class="row-desc">模型 ' + esc((S.health && S.health.model) || "—") +
        " · 已挂载 " + tools.length + " 个工具</div>" +
        '<div class="row-foot"><span>状态 ' + esc(st.state || "—") + "</span>" +
        "<span>连续失败 " + esc(st.consecutive_failures) + "</span>" +
        (st.current_goal ? "<span>当前目标 " + esc(String(st.current_goal).slice(0, 40)) + "</span>" : "") +
        "</div></div>" +
        '<div class="empty-state" style="margin-top:14px">后端当前未暴露多 Agent 注册表端点，' +
        "因此此处只展示真实存在的主 Agent，不虚构其余 Agent。</div>";
    } catch (e) { box.innerHTML = errorBox("Agent 状态读取失败", e.message); }
  }

  /* =========================================================
     设置
     ========================================================= */
  async function loadSettings() {
    const box = $("#settingsBody");
    box.innerHTML = LOADING;
    try {
      const cfg = await getJSON("/api/config");
      S.config = cfg;
      const rows = [
        ["AI 名称", cfg.ai_name],
        ["主题", cfg.theme],
        ["模型", cfg.llm && cfg.llm.model],
        ["Provider", cfg.llm && cfg.llm.active],
        ["Base URL", cfg.llm && cfg.llm.base_url],
        ["API Key", cfg.llm && cfg.llm.key_present ? "已配置（仅存于服务端）" : "未配置"],
        ["记忆图", String(cfg.memory_graph)],
        ["构建通道", cfg.build_channel],
      ];
      let html = '<div class="row-card"><div class="kv">' + rows.map((r) =>
        '<div class="k">' + esc(r[0]) + '</div><div class="v">' + esc(r[1] == null ? "—" : r[1]) + "</div>"
      ).join("") + "</div></div>";

      // 版本信息 /api/version
      try {
        const v = await getJSON("/api/version");
        S.version = v;
        html += '<div class="page-head" style="margin-top:24px"><h1 style="font-size:16px">版本</h1></div>' +
          '<div class="row-card"><div class="kv">' +
          '<div class="k">应用</div><div class="v">' + esc(v.app_name) + "</div>" +
          '<div class="k">版本</div><div class="v">' + esc(v.version) + "</div>" +
          (v.check_url ? '<div class="k">更新地址</div><div class="v">' + esc(v.check_url) + "</div>" : "") +
          "</div></div>";
      } catch (e) { /* 版本接口失败不影响主配置 */ }

      // 用户模型 /api/user_model
      try {
        const um = await getJSON("/api/user_model");
        S.userModel = um && um.model ? um.model : null;
        if (S.userModel) {
          const idt = S.userModel.identity || {};
          html += '<div class="page-head" style="margin-top:24px"><h1 style="font-size:16px">用户模型</h1></div>' +
            '<div class="row-card"><div class="kv">' +
            '<div class="k">身份</div><div class="v">' + esc(idt.name || "—") + " / " + esc(idt.role || "—") + "</div>" +
            (idt.org ? '<div class="k">组织</div><div class="v">' + esc(idt.org) + "</div>" : "") +
            '<div class="k">字段</div><div class="v">' + esc(Object.keys(S.userModel).join("、")) + "</div>" +
            "</div></div>";
        }
      } catch (e) { /* 用户模型失败不影响主配置 */ }

      // 诊断：就绪状态 /api/ready
      try {
        const rd = await getJSON("/api/ready");
        const chk = (rd && rd.self_check && rd.self_check.checks) || [];
        const failed = chk.filter((c) => !c.ok);
        html += '<div class="page-head" style="margin-top:24px"><h1 style="font-size:16px">就绪状态' +
          '<span class="badge ' + (failed.length ? "warn" : "ok") + '" style="margin-left:10px">' +
          (failed.length ? failed.length + " 项异常" : "全部通过") + "</span></h1></div>";
        html += chk.length
          ? '<div class="list">' + chk.slice(0, 12).map((c) =>
              '<div class="row-card"><div class="row-title">' + esc(c.name) +
              '<span class="badge ' + (c.ok ? "ok" : "") + '">' + (c.ok ? "通过" : "失败") + "</span></div>" +
              (c.detail ? '<div class="row-desc">' + esc(String(c.detail).slice(0, 120)) + "</div>" : "") +
              "</div>").join("") + "</div>"
          : empty("无自检项");
      } catch (e) { /* 就绪检查失败不阻断 */ }

      // 诊断：系统监控 /api/sysmon
      try {
        const sm = await getJSON("/api/sysmon");
        html += '<div class="page-head" style="margin-top:24px"><h1 style="font-size:16px">系统监控</h1></div>' +
          '<div class="row-card"><div class="kv">' +
          (sm.cpu ? '<div class="k">CPU</div><div class="v">' + esc(sm.cpu.percent) + "%</div>" : "") +
          (sm.memory ? '<div class="k">内存</div><div class="v">' + esc(sm.memory.percent) + "%</div>" : "") +
          (sm.ts ? '<div class="k">采样时间</div><div class="v">' + esc(sm.ts) + "</div>" : "") +
          "</div></div>";
      } catch (e) { /* 系统监控失败不阻断 */ }

      // 诊断：后端日志 /api/logs（最近 15 行）
      try {
        const lg = await getJSON("/api/logs");
        const lines = (lg && lg.lines) || [];
        if (lines.length) {
          html += '<div class="page-head" style="margin-top:24px"><h1 style="font-size:16px">后端日志' +
            '<span class="badge" style="margin-left:10px">最近 ' + lines.length + " 行</span></h1></div>" +
            '<div class="row-card"><div class="ap-args" style="max-height:200px">' +
            esc(lines.slice(-15).join("\n")) + "</div></div>";
        }
      } catch (e) { /* 日志失败不阻断 */ }

      html += '<div class="empty-state" style="margin-top:14px">设置项为只读展示：后端 /api/config 的写入语义未验证，' +
        "为避免破坏现有配置，此处不做修改。</div>";
      box.innerHTML = html;
    } catch (e) { box.innerHTML = errorBox("配置读取失败", e.message); }
  }

  /* =========================================================
     输入框
     ========================================================= */
  function bindComposer() {
    const ta = $("#input"), send = $("#btnSend");

    ta.addEventListener("input", () => {
      ta.style.height = "auto";
      ta.style.height = Math.min(200, ta.scrollHeight) + "px";
    });
    ta.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); }
    });
    send.addEventListener("click", submit);

    $("#btnSearch").addEventListener("click", function () {
      S.search = !S.search; this.classList.toggle("on", S.search);
      toast(S.search ? "已开启联网搜索（Agent 将优先使用 web_search）" : "已关闭联网搜索");
    });
    $("#btnThink").addEventListener("click", function () {
      // 诚实：后端 /api/models 返回 404，无模型切换端点
      toast("后端暂无模型切换端点（/api/models → 404），深度思考未接入，不做假装实现", true);
    });
    $("#btnAttach").addEventListener("click", () => $("#fileInput").click());
    $("#fileInput").addEventListener("change", onFiles);

    // 拖拽上传
    const cw = $("#composer");
    ["dragenter", "dragover"].forEach((ev) => cw.addEventListener(ev, (e) => {
      e.preventDefault(); cw.style.borderColor = "#ff4d4f";
    }));
    ["dragleave", "drop"].forEach((ev) => cw.addEventListener(ev, (e) => {
      e.preventDefault(); cw.style.borderColor = "";
    }));
    cw.addEventListener("drop", (e) => {
      if (e.dataTransfer && e.dataTransfer.files.length) attachPaths(e.dataTransfer.files);
    });

    // 快捷胶囊
    const QUICK = [
      "帮我写一段代码",
      "分析当前项目结构",
      "现在几点了",
      "帮我查一下今天的热点",
    ];
    $("#quickChips").innerHTML = QUICK.map((q) =>
      '<button class="chip" data-q="' + esc(q) + '">' + esc(q) + "</button>").join("");
    $("#quickChips").addEventListener("click", (e) => {
      const b = e.target.closest("[data-q]");
      if (b) { ta.value = b.dataset.q; ta.dispatchEvent(new Event("input")); submit(); }
    });

    bindVoice();
  }

  function onFiles(e) { attachPaths(e.target.files); e.target.value = ""; }
  function attachPaths(files) {
    const names = Array.from(files).map((f) => f.name).join("、");
    if (!names) return;
    // 沙箱约束提示：后端文件工具仅限 xiao6-ui/sandbox
    toast("已选择：" + names + "（注意：后端文件工具仅限沙箱目录，上传链路需后端端点支持）");
  }

  /* =========================================================
     语音（真实 /api/asr）
     ========================================================= */
  let rec = null, recStream = null, recChunks = [];
  function bindVoice() {
    const btn = $("#btnVoice");
    btn.addEventListener("click", async () => {
      if (rec && rec.state === "recording") { rec.stop(); return; }
      if (!navigator.mediaDevices || !window.MediaRecorder) {
        toast("当前环境不支持录音", true); return;
      }
      try {
        recStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      } catch (e) {
        toast("麦克风不可用：" + e.message, true); return;
      }
      recChunks = [];
      rec = new MediaRecorder(recStream);
      rec.ondataavailable = (e) => { if (e.data && e.data.size) recChunks.push(e.data); };
      rec.onstop = async () => {
        recStream.getTracks().forEach((t) => t.stop());
        setHeart(S.busy ? "thinking" : "idle");
        btn.classList.remove("on");
        const blob = new Blob(recChunks, { type: rec.mimeType || "audio/webm" });
        if (!blob.size) { toast("未采集到音频", true); return; }
        setHeart("thinking");
        try {
          // 冻结契约（源自旧 UI voice.js）：POST /api/asr?ext=.wav
          // multipart 字段名必须是 audio，不得修改
          const fd = new FormData();
          fd.append("audio", blob, "voice.wav");
          const text = await api("/api/asr?ext=.wav", {
            method: "POST",
            body: fd,   // 不手工设 Content-Type，让浏览器生成 multipart boundary
          });
          const out = (typeof text === "string" ? text : (text.text || text.result || "")).trim();
          if (!out) { toast("识别结果为空", true); setHeart("idle"); return; }
          $("#input").value = out;
          $("#input").dispatchEvent(new Event("input"));
          setHeart("idle");
          toast("识别完成：" + out.slice(0, 20));
        } catch (e) {
          setHeart("error");
          toast("语音识别失败：" + e.message, true);
          setTimeout(() => setHeart("idle"), 1600);
        }
      };
      rec.start();
      btn.classList.add("on");
      setHeart("listening");
      toast("正在聆听… 再次点击结束");
    });
  }

  /* =========================================================
     SSE 事件总线 /api/stream（主动推送 + 审批请求）
     契约源自旧 UI：api.js 用 EventSource 连接 /api/stream；
     approval.js 用 POST /api/agent/approval?ticket=<t>&decision=approve|reject
     truthful 红线：只有后端 {ok:true} 才置终态，否则保留按钮等重试，绝不假成功
     ========================================================= */
  let evtSource = null;

  function initEventStream() {
    if (typeof EventSource === "undefined") return;
    if (evtSource) return;
    try { evtSource = new EventSource("/api/stream"); } catch (e) { return; }

    evtSource.onopen = function () {
      const dot = $("#liveDot");
      if (dot) dot.title = "后端在线 · 实时事件通道已连接";
    };
    evtSource.onmessage = function (e) {
      let m = null;
      try { m = JSON.parse(e.data); } catch (_) { return; }
      handleStreamEvent(m);
    };
    // EventSource 自带重连，onerror 不做破坏性动作
    evtSource.onerror = function () { /* 静默等待自动重连 */ };
  }

  function handleStreamEvent(m) {
    if (!m || typeof m !== "object") return;
    const ap = m.approval || m.modal || {};
    const ticket = m.ticket || ap.ticket;
    if (ticket) { renderApprovalCard(m, ticket); return; }            // ① 审批请求（最高优先）
    if (m.xiao6_event === "proactive" || m.kind) { renderProactive(m); return; } // ② 主动推送
    // ③ 其余事件忽略，避免刷屏
  }

  function renderProactive(m) {
    const kind = m.kind || "notice";
    const icon = kind === "alert" ? "📡" : kind === "briefing" ? "☀️" :
                 kind === "reminder" ? "⏰" : "💬";
    const content = m.content || m.text || m.message || "";
    if (!content) return;
    const time = m.ts || "";
    const card = '<div class="proactive-card">' +
      '<div class="pc-head">' + icon + " " + esc(kind) + "</div>" +
      '<div class="pc-body">' + esc(content) + "</div>" +
      (time ? '<div class="pc-time">' + esc(time) + "</div>" : "") + "</div>";

    const hero = $("#hero");
    if (hero && hero.style.display !== "none") {
      const feed = $("#proactiveFeed");
      if (feed) feed.insertAdjacentHTML("afterbegin", card);
    } else {
      addMsg("assistant", card);
    }
    toast(icon + " 小6 有新的主动消息");
  }

  function renderApprovalCard(m, ticket) {
    const ap = m.approval || m.modal || {};
    const tool = m.tool || ap.tool || "";
    const summary = m.summary || ap.summary || m.prompt || ap.prompt || "有一项操作需要你确认";
    const args = m.args_preview || ap.args_preview || m.argsPreview || ap.argsPreview || "";

    ensureChatMode();
    const bubble = addMsg("assistant", "");
    const card = document.createElement("div");
    card.className = "approval-card";
    card.innerHTML =
      '<div class="ap-head">⚠️ 需要确认' +
      (tool ? '<span class="ap-tool">' + esc(tool) + "</span>" : "") + "</div>" +
      '<div class="ap-body">' + esc(summary) + "</div>" +
      (args ? '<div class="ap-args">' + esc(args) + "</div>" : "") +
      '<div class="ap-actions">' +
      '<button class="ap-yes">批准</button>' +
      '<button class="ap-no">拒绝</button>' +
      '<span class="ap-state">ticket ' + esc(String(ticket).slice(0, 12)) + "</span>" +
      "</div>";
    bubble.appendChild(card);

    card.querySelector(".ap-yes").addEventListener("click", () => postApproval(ticket, "approve", card));
    card.querySelector(".ap-no").addEventListener("click", () => postApproval(ticket, "reject", card));
    toast("有一项操作需要确认");
  }

  async function postApproval(ticket, decision, card) {
    const yes = card.querySelector(".ap-yes"), no = card.querySelector(".ap-no");
    const stateEl = card.querySelector(".ap-state");
    if (yes) yes.disabled = true;
    if (no) no.disabled = true;
    if (stateEl) stateEl.textContent = "提交中…";
    try {
      const res = await fetch("/api/agent/approval?ticket=" + encodeURIComponent(ticket) +
        "&decision=" + decision, { method: "POST" });
      const d = await res.json().catch(() => null);
      if (res.ok && d && d.ok === true) {
        card.classList.add(decision === "approve" ? "ok" : "stopped");
        const head = card.querySelector(".ap-head");
        if (head) head.textContent = decision === "approve" ? "✓ 已批准" : "已拒绝";
        const actions = card.querySelector(".ap-actions");
        if (actions) actions.innerHTML = '<span class="ap-state">' +
          (decision === "approve" ? "已批准执行" : "已拒绝该操作") + "</span>";
        toast(decision === "approve" ? "已批准" : "已拒绝");
      } else {
        throw new Error((d && (d.error || d.detail)) || "HTTP " + res.status);
      }
    } catch (e) {
      // truthful：恢复按钮、保留 blocked，等待重试
      if (yes) yes.disabled = false;
      if (no) no.disabled = false;
      if (stateEl) stateEl.textContent = "提交失败 · 请重试";
      toast("审批提交失败：" + e.message, true);
    }
  }

  /* =========================================================
     发送 + SSE 流式
     ========================================================= */
  function setHeart(state) {
    const h = $("#heartBig");
    if (!h) return;
    h.className = "heart-big state-" + state;
  }

  function ensureChatMode() {
    // 隐藏首页 hero，进入对话模式（直接置 display，不依赖不存在的 .hidden 类）
    const hero = $("#hero");
    if (hero && hero.style.display !== "none") hero.style.display = "none";
  }

  function addMsg(role, html, id) {
    const wrap = document.createElement("div");
    wrap.className = "msg " + role;
    if (id) wrap.id = id;
    wrap.innerHTML = '<div class="avatar">' + (role === "user" ? "S" : "6") + "</div>" +
      '<div class="bubble">' + html + "</div>";
    $("#messages").appendChild(wrap);
    const box = $("#chatScroll");
    box.scrollTop = box.scrollHeight;
    return wrap.querySelector(".bubble");
  }

  function addToolLine(text, cls) {
    const b = addMsg("assistant",
      '<span class="tool-evt ' + cls + '"><span class="dot"></span>' + text + "</span>");
    return b;
  }

  /* ---------------- TTS 朗读（真实 POST /api/speak → edge-tts mp3） ---------------- */
  let currentAudio = null;
  async function speak(text, btn) {
    if (!text || !text.trim()) return;
    try {
      if (btn) { btn.disabled = true; btn.textContent = "合成中…"; }
      setHeart("thinking");
      // 冻结契约（源自旧 UI voice.js）：body { text, stream:false }
      const res = await fetch("/api/speak", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: text, stream: false }),
      });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const blob = await res.blob();
      if (!blob.size) throw new Error("返回音频为空");
      const url = URL.createObjectURL(blob);
      if (currentAudio) { currentAudio.pause(); currentAudio = null; }
      const audio = new Audio(url);
      currentAudio = audio;
      setHeart("speaking");
      if (btn) { btn.classList.add("playing"); btn.textContent = "播放中…"; }
      audio.onended = () => {
        URL.revokeObjectURL(url);
        setHeart("idle");
        if (btn) { btn.classList.remove("playing"); btn.disabled = false; btn.textContent = "朗读"; }
      };
      audio.onerror = () => {
        URL.revokeObjectURL(url);
        setHeart("idle");
        toast("音频播放失败", true);
        if (btn) { btn.classList.remove("playing"); btn.disabled = false; btn.textContent = "朗读"; }
      };
      await audio.play();
    } catch (e) {
      setHeart("error");
      setTimeout(() => setHeart("idle"), 1500);
      toast("语音合成失败：" + e.message, true);
      if (btn) { btn.classList.remove("playing"); btn.disabled = false; btn.textContent = "朗读"; }
    }
  }

  // 给一条 assistant 回答挂上朗读按钮
  function attachSpeak(bubble, text) {
    if (!text || !text.trim()) return;
    const btn = document.createElement("button");
    btn.className = "speak-btn";
    btn.textContent = "朗读";
    btn.addEventListener("click", () => speak(text, btn));
    bubble.appendChild(document.createElement("br"));
    bubble.appendChild(btn);
  }

  async function submit() {
    const ta = $("#input");
    const text = (ta.value || "").trim();
    if (!text || S.busy) return;

    let payload = text;
    if (S.search) payload = "请使用 web_search 工具联网检索后回答：" + text;

    ensureChatMode();
    addMsg("user", esc(text));
    ta.value = ""; ta.style.height = "auto";

    S.conversation.push({ role: "user", content: payload });

    S.busy = true;
    $("#btnSend").disabled = true;
    setHeart("thinking");

    const bubble = addMsg("assistant", '<span class="typing"><i></i><i></i><i></i></span>');
    let acc = "";
    let gotAny = false;

    try {
      await streamChat(S.conversation, (evt) => {
        // 1) 文本流
        const delta = evt.choices && evt.choices[0] && evt.choices[0].delta;
        if (delta && typeof delta.content === "string") {
          if (!gotAny) { bubble.innerHTML = ""; gotAny = true; }
          acc += delta.content;
          bubble.textContent = acc;
          const box = $("#chatScroll");
          box.scrollTop = box.scrollHeight;
        }
        // 2) 真实工具事件
        if (evt.xiao6_event === "tool_start") {
          setHeart("executing");
          const name = (evt.tool || "tool") + (evt.args ? " " + JSON.stringify(evt.args).slice(0, 60) : "");
          addToolLine("正在调用 <code>" + esc(evt.tool || "tool") + "</code> …", "running");
        }
        if (evt.xiao6_event === "tool_end") {
          addToolLine("<code>" + esc(evt.tool || "tool") + "</code> 调用完成", "done");
        }
      });

      if (!gotAny) {
        bubble.innerHTML = '<span style="color:#8a8a8a">（本次请求未返回文本内容）</span>';
      } else {
        S.conversation.push({ role: "assistant", content: acc });
        attachSpeak(bubble, acc);   // 真实 TTS：POST /api/speak
      }
      setHeart("idle");
      // 刷新任务/记忆（Agent 可能已写入）
      loadTaskPreview();
      loadRecent();
    } catch (e) {
      bubble.innerHTML = '<div class="error-state" style="text-align:left">' +
        "<div>小6暂时无法完成这个请求</div>" +
        '<div class="detail" style="text-align:left">' + esc(e.message) + "</div>" +
        '<button class="customize-btn" style="margin-top:10px" data-retry="1">重试</button></div>';
      setHeart("error");
      setTimeout(() => setHeart("idle"), 1800);
      toast("请求失败：" + e.message, true);
    } finally {
      S.busy = false;
      $("#btnSend").disabled = false;
    }
  }

  // 重试
  document.addEventListener("click", (e) => {
    if (e.target && e.target.dataset && e.target.dataset.retry) {
      if (S.conversation.length && S.conversation[S.conversation.length - 1].role === "user") {
        submit();
      }
    }
  });

  /* ---------------- SSE 解析 ---------------- */
  async function streamChat(messages, onEvent) {
    let res;
    try {
      res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: messages }),
      });
    } catch (e) {
      throw new Error("网络请求失败：" + e.message);
    }
    if (!res.ok) {
      let detail = "";
      try { const j = await res.json(); detail = j.detail || j.error || JSON.stringify(j); } catch (_) { detail = res.statusText; }
      throw new Error("HTTP " + res.status + " · " + detail);
    }
    if (!res.body) {
      const t = await res.text();
      try { onEvent(JSON.parse(t)); } catch (_) {}
      return;
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buf = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const parts = buf.split("\n\n");
      buf = parts.pop() || "";
      for (const raw of parts) {
        const line = raw.trim();
        if (!line.startsWith("data:")) continue;
        const payload = line.slice(5).trim();
        if (!payload || payload === "[DONE]") continue;
        try { onEvent(JSON.parse(payload)); } catch (_) { /* 忽略非 JSON 心跳 */ }
      }
    }
    // 收尾残留
    const tail = buf.trim();
    if (tail.startsWith("data:")) {
      const p = tail.slice(5).trim();
      if (p && p !== "[DONE]") { try { onEvent(JSON.parse(p)); } catch (_) {} }
    }
  }
})();
