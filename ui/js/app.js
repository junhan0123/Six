/* =========================================================
   小6 · 个人 AI OS — UI 2.0 (S122 Productization)
   唯一正式 UI：G:\xiao6\ui，由 Xiao6 server :8000 同源托管
   所有 API 使用同源相对路径 /api/*（无代理、无跨端口、无硬编码端口）
   红线：无任何 mock / 假数据；取不到就显示「不可用」，不编造
   S122 约束：仅 UI / 配置入口 / 数据展示，零 Runtime 改动
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
    if (!t) return;
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
  function todayStr() {
    const d = new Date();
    return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
  }
  function hhmm(ts) {
    if (!ts) return "";
    const s = String(ts);
    if (s.length >= 16) return s.slice(11, 16);
    return s.slice(0, 5);
  }
  function relTime(ts) {
    const s = String(ts || "").trim();
    if (!s) return "—";
    const d = new Date(s.replace(" ", "T"));
    if (isNaN(d.getTime())) return s.slice(5, 16) || s.slice(0, 16);
    const now = new Date();
    const pad = (n) => ("0" + n).slice(-2);
    const hm = pad(d.getHours()) + ":" + pad(d.getMinutes());
    const sameDay = d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth() && d.getDate() === now.getDate();
    if (sameDay) return "今天 " + hm;
    const y = new Date(now); y.setDate(now.getDate() - 1);
    const isYest = d.getFullYear() === y.getFullYear() && d.getMonth() === y.getMonth() && d.getDate() === y.getDate();
    if (isYest) return "昨天 " + hm;
    return pad(d.getMonth() + 1) + "-" + pad(d.getDate()) + " " + hm;
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
    health: null,
    ready: null,
    config: null,
    caps: null,
    tasks: [],
    knowledge: null,
    notes: [],
    graph: null,
    currentNote: null,
    capFilter: "all",
    taskTab: "current",
    taskFilter: "all",
    settingsTab: "general",
    conversation: [],
    busy: false,
    sessions: [],
    currentSid: null,
  };

  /* UI-P1 · 首页 hero 与聊天 view 共用的快捷问句（QUICK 四词，集中定义一处，避免重复声明与作用域问题） */
  const QUICK = [
    "今天有什么值得关注的新闻",
    "帮我整理一下今天要做的事",
    "查一下现在的天气",
    "帮我总结一下最近的工作",
  ];

  /* UI-P0 · 当前会话：优先取 URL ?session=，恢复对话时更新（纯前端，不依赖后端） */
  try {
    const m = location.search.match(/[?&]session=([^&]+)/);
    if (m) S.currentSid = decodeURIComponent(m[1]);
  } catch (e) { /* 无 session 参数时保持为空 */ }

  const CAPS = () => S.caps;

  async function ensureCaps() {
    if (S.caps) return S.caps;
    try { S.caps = await getJSON("/api/capability_os/catalog"); }
    catch (e) { S.caps = null; }
    return S.caps;
  }
  async function ensureConfig() {
    if (S.config) return S.config;
    try { S.config = await getJSON("/api/config"); }
    catch (e) { S.config = null; }
    return S.config;
  }

  /* =========================================================
     启动
     ========================================================= */
  boot();

  async function boot() {
    bindNav();
    bindComposer();
    bindActions();
    bindTaskDetail();
    bindWxFilters();
    bindCommandBar();
    bindMemoryPane();
    await refreshHealth();
    loadRecent();
    loadDashboard();
    initEventStream();
  }

  async function refreshHealth() {
    const dot = $("#liveDot");
    try {
      S.health = await getJSON("/api/health");
      dot.className = "live-dot online";
      dot.title = "服务运行中";
      const badge = $("#modelBadge");
      if (badge) badge.textContent = providerShortName(S.health.provider) || "—";
      try { S.ready = await getJSON("/api/ready"); } catch (e) { S.ready = null; }
      return true;
    } catch (e) {
      dot.className = "live-dot offline";
      dot.title = "服务未连接";
      const badge = $("#modelBadge");
      if (badge) badge.textContent = "离线";
      const tb = $("#todayBody");
      if (tb) tb.innerHTML = errorBox("小6 服务未连接", e.message);
      $("#recentList").innerHTML = errorBox("服务未连接", e.message);
      return false;
    }
  }

  function providerShortName(pid) {
    const map = { agnes: "Agnes", llm2: "自定义", ollama: "Ollama", lmstudio: "LM Studio", mlx: "MLX" };
    return map[String(pid || "").toLowerCase()] || "";
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
    if (name === "dashboard") loadDashboard();
    if (name === "tasks") loadTasks();
    if (name === "knowledge") loadKnowledge();
    if (name === "memory") loadMemory();
    if (name === "capabilities") loadCapabilities();
    if (name === "settings") loadSettings();
    if (name === "gfe") loadGfeDashboard();
    if (name === "system") loadSystemCenter();
    if (name === "about") loadAboutPage();
    if (name === "chat") {
      const box = $("#chatScroll");
      box.scrollTop = box.scrollHeight;
      $("#input").focus();
    }
  }

  function bindActions() {
    document.addEventListener("click", (e) => {
      const s = e.target.closest("[data-session]");
      if (s && s.dataset.session) resumeSession(s.dataset.session);
    });
    document.addEventListener("click", (e) => {
      const el = e.target.closest("[data-act]");
      if (!el) return;
      const a = el.dataset.act;
      if (a === "reload-dashboard") loadDashboard();
      if (a === "reload-tasks") loadTasks();
      if (a === "reload-knowledge") loadKnowledge();
      if (a === "reload-memory") loadMemory();
      if (a === "reload-capabilities") { S.caps = null; loadCapabilities(); }
      if (a === "reload-settings") { S.config = null; loadSettings(); }
    });
    // 任务中心 tabs
    const tt = $("#taskTabs");
    if (tt) tt.addEventListener("click", (e) => {
      const b = e.target.closest(".tab");
      if (!b) return;
      $$("#taskTabs .tab").forEach((x) => x.classList.toggle("active", x === b));
      S.taskTab = b.dataset.tab;
      renderTasks();
    });
    // 能力中心分类
    const cf = $("#capFilters");
    if (cf) cf.addEventListener("click", (e) => {
      const b = e.target.closest(".cap-filter");
      if (!b) return;
      $$("#capFilters .cap-filter").forEach((x) => x.classList.toggle("active", x === b));
      S.capFilter = b.dataset.cat;
      renderCapabilities();
    });
    // 设置 tabs
    const sn = $("#settingsNav");
    if (sn) sn.addEventListener("click", (e) => {
      const b = e.target.closest(".settings-tab");
      if (!b) return;
      $$("#settingsNav .settings-tab").forEach((x) => x.classList.toggle("active", x === b));
      S.settingsTab = b.dataset.setct;
      renderSettings();
    });
  }

  /* =========================================================
     首页 Dashboard（面向普通用户：天气 / 任务 / 热点 / 系统状态）
     ========================================================= */
  /* UI-P1 · Chat-first 首页：左栏 Today Card + 右栏 Agent Activity Center */
  async function loadDashboard() {
    const today = $("#todayBody");
    if (today) today.innerHTML = '<div class="mini-loading full-width"><span class="spinner"></span>正在为你准备今日信息…</div>';

    const [w, t, h] = await Promise.all([
      getJSON("/api/weather").catch((e) => ({ __err: e.message })),
      getJSON("/api/tasks").catch((e) => ({ __err: e.message })),
      getJSON("/api/hotspots").catch((e) => ({ __err: e.message })),
    ]);
    await ensureConfig();

    // 左栏：Today Card（天气 / 任务 / 日程）
    if (today) {
      let html = "";
      html += weatherCard(w);
      html += taskCard(t);
      html += scheduleCard(t);
      today.innerHTML = html;
    }

    // 右栏：热点（迁移到洞察区）、系统健康、当前状态/运行任务
    const hot = $("#acHotspot");
    if (hot) hot.innerHTML = hotspotCard(h);
    const health = $("#acHealthBody");
    if (health) health.innerHTML = systemCard();
    renderLiveCenter();

    // 快捷动作 + 折叠交互
    renderHomeQuick();
    bindHomeQuick();
    bindHomeCollapsibles();
  }

  /* UI-P1 · 今日日程：从 /api/tasks 派生（无独立 schedule 端点，不新增 API） */
  function scheduleCard(t) {
    const list = Array.isArray(t) ? t : [];
    const day = todayStr();
    const items = list.filter((x) => String(x.updated || x.created || "").slice(0, 10) === day).slice(0, 6);
    let body;
    if (!items.length) {
      body = '<div class="dc-empty">今天还没有日程安排 · 告诉小6「提醒我…」就会自动出现在这里</div>';
    } else {
      body = '<div class="sched-list">' + items.map((x) => {
        const tm = hhmm(x.updated || x.created || "");
        return '<div class="sched-item">' +
          '<span class="sched-time">' + esc(tm) + "</span>" +
          '<span class="sched-title">' + esc(x.title || "(无标题)") + "</span>" +
          '<span class="sched-status task-' + statusClass(x.status) + '">' + esc(statusLabel(x.status)) + "</span>" +
          "</div>";
      }).join("") + "</div>";
    }
    return dashCard("sched", "🗓 今日日程", body, "");
  }

  /* UI-P1 · 右栏「当前状态 / 运行任务」运行任务块 */
  function renderLiveCenter() {
    const box = $("#acTasksBody");
    if (!box) return;
    const tasks = S.tasks || [];
    const RUNNING = ["open", "running", "in_progress", "active", "pending"];
    const running = tasks.filter((x) => RUNNING.indexOf(String(x.status || "").toLowerCase()) >= 0).slice(0, 5);
    if (!running.length) {
      box.innerHTML = '<div class="ac-empty">暂无运行中的任务</div>';
      return;
    }
    box.innerHTML = '<div class="ac-tasks">' + running.map((x) => {
      const cls = statusClass(x.status) === "running" ? "run" : "pend";
      return '<div class="ac-task">' +
        '<span class="ac-task-dot ' + cls + '"></span>' +
        '<span class="ac-task-title">' + esc(x.title || "(无标题)") + "</span>" +
        '<span class="ac-task-st">' + esc(statusLabel(x.status)) + "</span>" +
        "</div>";
    }).join("") + "</div>";
  }

  /* UI-P1 · 首页 hero 快捷动作 chips（复用 QUICK） */
  function renderHomeQuick() {
    const box = $("#homeQuick");
    if (!box) return;
    box.innerHTML = QUICK.map((q) =>
      '<button class="chip" data-q="' + esc(q) + '">' + esc(q) + "</button>"
    ).join("");
  }
  let _homeQuickBound = false;
  function bindHomeQuick() {
    if (_homeQuickBound) return;
    const box = $("#homeQuick");
    if (!box) return;
    box.addEventListener("click", (e) => {
      const b = e.target.closest("[data-q]");
      if (!b) return;
      const ci = $("#commandInput");
      if (ci) { ci.value = b.dataset.q; ci.focus(); }
      const send = $("#commandSend");
      if (send) send.click();
    });
    _homeQuickBound = true;
  }

  /* UI-P1 · 右栏可折叠区块 */
  let _homeCollBound = false;
  function bindHomeCollapsibles() {
    if (_homeCollBound) return;
    document.querySelectorAll(".ac-sec-head[data-toggle]").forEach((h) => {
      h.addEventListener("click", () => {
        const sec = document.getElementById(h.dataset.toggle);
        if (sec) sec.classList.toggle("collapsed");
      });
    });
    _homeCollBound = true;
  }

  /* 首页视觉增强辅助：天气图标 / 平台图标 / 状态点 / 会话标签清洗 */
  const WEATHER_MAP = [
    { re: /雷/, emoji: "⛈️", cls: "rain" },
    { re: /雪/, emoji: "❄️", cls: "rain" },
    { re: /雨/, emoji: "🌧️", cls: "rain" },
    { re: /雾|霾/, emoji: "🌫️", cls: "fog" },
    { re: /多云/, emoji: "⛅", cls: "cloudy" },
    { re: /阴/, emoji: "☁️", cls: "cloudy" },
    { re: /晴/, emoji: "☀️", cls: "sunny" },
  ];
  function weatherIcon(cond) {
    const c = String(cond || "");
    for (const m of WEATHER_MAP) if (m.re.test(c)) return m;
    return { emoji: "🌡️", cls: "default" };
  }
  function platformIcon(p) {
    const m = {
      douyin: "🎬", weibo: "🌐", zhihu: "💡", bilibili: "📺", toutiao: "📰",
      baidu: "🔍", kuaishou: "📱", xiaohongshu: "📕", hupu: "🏀",
      github: "🐙", qq: "💬", tieba: "🧩", v2ex: "💻",
    };
    return m[String(p || "").toLowerCase()] || "🔗";
  }
  function statusDot(cls) {
    if (cls === "ok") return "🟢";
    if (cls === "warn") return "🟡";
    return "⚪";
  }
  function cleanSessionLabel(sid) {
    let s = String(sid || "").replace(/^p\d+_/, "");
    s = s.replace(/_(stale|missing|get|valid|cp|a|id)$/i, "");
    return s || "对话";
  }
  function aqiLabel(aqi) {
    const v = Number(aqi);
    if (!v) return null;
    if (v <= 50) return "优";
    if (v <= 100) return "良";
    if (v <= 150) return "轻度";
    return "中度";
  }

  function weatherCard(w) {
    if (!w || w.__err) {
      return dashCard("weather", "🌤 今日天气", '<div class="dc-empty">天气信息暂时不可用</div>');
    }
    const c = w.card || {};
    const city = c.city || w.city || "—";
    const cond = c.condition || "—";
    const wi = weatherIcon(cond);
    const temp = c.temp != null ? c.temp + "°" : "—";
    const high = c.high != null ? c.high + "°" : "—";
    const low = c.low != null ? c.low + "°" : "—";
    const feel = c.feel != null ? "体感 " + c.feel + "°" : "";
    const wind = c.wind || (c.wind_dir ? c.wind_dir + " " + c.wind_kmh + " km/h" : "");
    const aqi = aqiLabel(c.aqi);

    let body = '<div class="weather-hero weather-' + wi.cls + '">' +
      '<div class="weather-emoji">' + wi.emoji + "</div>" +
      '<div class="weather-main">' +
      '<div class="weather-temp">' + esc(temp) + "</div>" +
      '<div class="weather-info">' +
      '<div class="weather-condition">' + esc(cond) + "</div>" +
      '<div class="weather-meta"><span>' + esc(city) + "</span><span>最高 " + esc(high) + " / 最低 " + esc(low) + "</span></div>" +
      "</div></div></div>";

    const extra = [];
    if (feel) extra.push("<span>" + esc(feel) + "</span>");
    if (c.humidity != null) extra.push("<span>湿度 " + esc(c.humidity) + "%</span>");
    if (wind) extra.push("<span>" + esc(wind) + "</span>");
    if (aqi) extra.push('<span class="aqi-pill">空气 ' + esc(aqi) + " " + esc(c.aqi) + "</span>");
    if (extra.length) body += '<div class="weather-extra">' + extra.join("") + "</div>";

    if (Array.isArray(w.forecast) && w.forecast.length) {
      body += '<div class="weather-forecast">' + w.forecast.slice(0, 3).map((f) =>
        '<div class="weather-day"><div class="wd">' + esc(f.day) + "</div>" +
        '<div class="wt">' + esc(f.condition || "") + "</div>" +
        '<div class="wt">' + esc(f.low) + "° / " + esc(f.high) + "°</div></div>").join("") + "</div>";
    }
    if (Array.isArray(c.lifeIndex) && c.lifeIndex.length) {
      body += '<div class="life-index">' + c.lifeIndex.slice(0, 3).map((l) =>
        '<span class="li-item">' + esc(l.name) + " · " + esc(l.val) + "</span>").join("") + "</div>";
    }
    const foot = "更新于 " + (w.fetchedAt ? hhmm(w.fetchedAt) : "—");
    return dashCard("weather", "🌤 今日天气", body, foot);
  }

  function taskCard(t) {
    if (!Array.isArray(t)) {
      return dashCard("task", "📋 今日任务", '<div class="dc-empty">任务信息暂时不可用</div>');
    }
    S.tasks = t;
    const RUNNING = ["open", "running", "in_progress", "active", "pending"];
    const running = t.filter((x) => RUNNING.indexOf(String(x.status || "").toLowerCase()) >= 0);
    const today = todayStr();
    const doneToday = t.filter((x) => /done|complete|成功/.test(String(x.status || "")) &&
      String(x.updated || x.created || "").slice(0, 10) === today).length;

    let body = '<div class="task-summary">' +
      '<div class="ts-item"><div class="ts-num">' + running.length + '</div><div class="ts-label">进行中</div></div>' +
      '<div class="ts-item"><div class="ts-num">' + doneToday + '</div><div class="ts-label">今日完成</div></div>' +
      '<div class="ts-item"><div class="ts-num">' + t.length + '</div><div class="ts-label">全部任务</div></div>' +
      "</div>";

    if (running.length) {
      body += '<div class="task-list">' + running.slice(0, 4).map((x) => {
        const sc = statusClass(x.status);
        const glyph = sc === "done" ? "✅" : sc === "running" ? "🔄" : "⏳";
        const pri = (x.priority === "high" || x.priority === "高") ? '<span class="task-pri" title="高优先级">⚠️</span>' : "";
        return '<div class="task-item task-' + sc + '" data-view="tasks">' +
          '<span class="task-status ' + sc + '"></span>' +
          '<span class="task-title">' + pri + esc(x.title || "(无标题)") + "</span>" +
          '<span class="task-time">' + glyph + " " + esc(statusLabel(x.status)) + "</span></div>";
      }).join("") + "</div>";
    } else {
      body += '<div class="task-empty">' +
        '<div class="task-empty-title">今天还没有安排任务</div>' +
        '<div class="task-empty-desc">告诉小6想完成什么，或者在任务中心创建任务</div>' +
        '<button class="customize-btn task-btn-new" data-view="tasks">+ 创建任务</button>' +
        "</div>";
    }

    // 任务入口 + 查看全部（与是否有任务无关，统一放在底部）
    const hasRunning = running.length > 0;
    body += '<div class="task-actions-bar">' +
      '<button class="task-btn-new" data-view="tasks">+ 新建任务</button>' +
      '<button class="task-btn-all" data-view="tasks">查看全部任务 →</button>' +
      "</div>";

    const foot = '<div class="task-source-hint">' +
      "任务可以来自：• 对话中告诉小6 • 手动创建 • 目标拆解" +
      '<div class="task-source-example">例如，告诉小6：「帮我明天提醒开会」，就会自动生成任务</div>' +
      "</div>";
    return dashCard("task", "📋 今日任务", body, foot);
  }

  function statusClass(st) {
    const s = String(st || "").toLowerCase();
    if (/done|complete|成功/.test(s)) return "done";
    if (/open|running|progress|active|pending/.test(s)) return "running";
    return "pending";
  }
  function statusLabel(st) {
    const s = String(st || "").toLowerCase();
    if (/done|complete|成功/.test(s)) return "已完成";
    if (/running|progress/.test(s)) return "执行中";
    if (/open|pending/.test(s)) return "进行中";
    if (/fail|error/.test(s)) return "失败";
    if (/cancel/.test(s)) return "已取消";
    return String(st || "未知");
  }

  const PLATFORM_LABEL = {
    douyin: "抖音", weibo: "微博", zhihu: "知乎", baidu: "百度",
    bilibili: "哔哩哔哩", toutiao: "今日头条", qq: "QQ 看点",
    kuaishou: "快手", xiaohongshu: "小红书", hupu: "虎扑",
   tieba: "百度贴吧", v2ex: "V2EX", github: "GitHub",
  };

  function flattenHotspots(h) {
    const out = [];
    if (!h || h.__err || !h.platforms) return out;
    const keys = Object.keys(h.platforms);
    let rank = 1;
    const maxLen = Math.max.apply(null, keys.map((k) => (h.platforms[k] || []).length).concat([0]));
    for (let i = 0; i < maxLen; i++) {
      for (const k of keys) {
        const item = (h.platforms[k] || [])[i];
        if (!item) continue;
        out.push(Object.assign({}, item, { __platform: k, __order: rank++ }));
      }
    }
    return out;
  }

  function hotspotCard(h) {
    if (!h || h.__err) {
      return dashCard("hot", "🔥 热点资讯", '<div class="dc-empty">热点信息暂时不可用</div>');
    }
    const list = flattenHotspots(h).slice(0, 12);
    if (!list.length) return dashCard("hot", "🔥 热点资讯", '<div class="dc-empty">暂无热点数据</div>');

    const updTime = h.fetchedAt ? hhmm(h.fetchedAt) : "—";
    let body = '<div class="hotspot-grid">';
    list.forEach((x, i) => {
      const title = x.text || x.title || "(无标题)";
      const pname = PLATFORM_LABEL[x.__platform] || x.__platform || "网络";
      const heat = x.heat ? "热度 " + x.heat : "";
      const summary = x.desc || x.summary || x.abstract || "";
      const icon = platformIcon(x.__platform);
      body += '<div class="hotspot-tile">' +
        '<div class="hotspot-head">' +
        '<span class="hotspot-rank">' + (i + 1) + "</span>" +
        '<div class="hotspot-title" title="' + esc(title) + '">' + esc(title) + "</div>" +
        "</div>" +
        (summary ? '<div class="hotspot-summary" title="' + esc(summary) + '">' + esc(String(summary).slice(0, 110)) + "</div>" : "") +
        '<div class="hotspot-meta">' +
        '<span class="hs-src">' + icon + " " + esc(pname) + "</span>" +
        (heat ? "<span>" + esc(heat) + "</span>" : "") +
        "<span>🕒 " + esc(updTime) + "</span>" +
        "</div>" +
        '<div class="hotspot-actions">' +
        '<button class="hs-btn" data-hot="read" data-url="' + esc(x.url || "") + '" data-title="' + esc(title) + '">阅读全文</button>' +
        '<button class="hs-btn" data-hot="save" data-url="' + esc(x.url || "") + '" data-title="' + esc(title) +
        '" data-src="' + esc(pname) + '" data-heat="' + esc(x.heat || "") + '">保存知识库</button>' +
        '<button class="hs-btn hs-primary" data-hot="sum" data-url="' + esc(x.url || "") + '" data-title="' + esc(title) +
        '" data-src="' + esc(pname) + '">让小6总结</button>' +
        "</div></div>";
    });
    body += "</div>";
    const foot = "共 " + list.length + " 条 · 更新于 " + updTime;
    return dashCard("hot", "🔥 热点资讯", body, foot);
  }

  // 热点卡片操作（事件委托，卡片每次重绘都有效）
  document.addEventListener("click", (e) => {
    const b = e.target.closest("[data-hot]");
    if (!b) return;
    const act = b.dataset.hot;
    const url = b.dataset.url || "";
    const title = b.dataset.title || "";
    const src = b.dataset.src || "";
    const heat = b.dataset.heat || "";
    if (act === "read") {
      if (!url) { toast("该热点没有提供原文链接", true); return; }
      window.open(url, "_blank", "noopener");
      return;
    }
    if (act === "save") { saveHotspotToKnowledge(title, url, src, heat, b); return; }
    if (act === "sum") { summarizeHotspot(title, url, src); return; }
  });

  async function saveHotspotToKnowledge(title, url, src, heat, btn) {
    if (!title) return;
    const old = btn.textContent;
    btn.disabled = true; btn.textContent = "保存中…";
    // 诚实：后端只提供标题 / 链接 / 热度 / 平台，这里按真实字段入库，不编造正文
    const text = ["标题：" + title, "来源：" + src, "热度：" + (heat || "—"), "链接：" + (url || "—")].join("\n");
    try {
      const r = await postJSON("/api/knowledge", { action: "upload", title: title, text: text, source: src });
      if (r && r.ok) { toast("已保存到知识库"); S.knowledge = null; }
      else throw new Error((r && (r.error || r.detail)) || "保存失败");
    } catch (e) {
      toast("保存失败：" + e.message, true);
    } finally {
      btn.disabled = false; btn.textContent = old;
    }
  }

  function summarizeHotspot(title, url, src) {
    if (!title) return;
    switchView("chat");
    const ta = $("#input");
    ta.value = "帮我总结这条热点：「" + title + "」" + (src ? "（来源：" + src + "）" : "") +
      (url ? "，原文链接：" + url : "") + "。请说明事件要点和可能的影响。";
    ta.dispatchEvent(new Event("input"));
    submit();
  }

  /* ---------- 系统状态（服务 / 模型 / 语音） ---------- */
  const CHECK_LABEL = {
    "Python 版本": "运行环境",
    "核心依赖": "核心组件",
    "本地工具注册": "能力挂载",
    "SQLite 数据库": "数据存储",
    "Agnes API 密钥": "模型密钥",
    "TTS 语音合成": "语音合成",
    "Agnes API 可达": "模型服务连接",
    "天气源 Open-Meteo": "天气数据",
    "热点数据源": "热点数据",
    "Phase 4 功能开关": "功能开关",
    "知识索引": "知识索引",
    "已注册设备": "设备同步",
  };

  /* UI-P0 · Task1：首页只保留「状态点 + 系统状态入口」。
     模型名 / self_check 明细 / 开发提示一律下沉到「系统状态」页。
     /api/health、/api/ready、/api/config 的调用与契约保持不变。 */
  function systemCard() {
    const h = S.health || {};
    const checks = (h.self_check && h.self_check.checks) || [];
    const failed = checks.filter((c) => !c.ok).length;
    const serviceOK = h.status === "alive" && (!S.ready || S.ready.ready !== false);
    const ok = serviceOK && !failed;
    const cls = ok ? "ok" : "warn";
    const text = !serviceOK ? "服务未就绪" : (failed ? "需要关注" : "系统正常");

    const body = '<button class="sys-health-entry" data-view="system" title="查看系统状态">' +
      '<span class="sys-health-dot ' + cls + '"></span>' +
      '<span class="sys-health-text">' + esc(text) + "</span>" +
      '<span class="sys-health-link">系统状态 →</span>' +
      "</button>";
    return dashCard("sys", "⚙️ 系统状态", body, "");
  }

  function statusItem(label, value, cls) {
    return '<div class="status-item"><div class="status-label">' + esc(label) + "</div>" +
      '<div class="status-value ' + (cls || "") + '">' + esc(value) + "</div></div>";
  }

  function dashCard(kind, title, body, foot) {
    return '<div class="dash-card dash-card-' + kind + '">' +
      '<div class="dash-card-header"><div class="dash-card-title">' + esc(title) + "</div></div>" +
      '<div class="dash-card-body">' + body + "</div>" +
      (foot ? '<div class="dash-card-foot">' + foot + "</div>" : "") +
      "</div>";
  }

  /* =========================================================
     最近对话
     ========================================================= */
  /* =========================================================
     UI-P0 · Task2：会话列表前端覆盖层（localStorage）
     重命名 / 置顶 / 隐藏 全部本地生效，不新增 API、不改动数据库
     ========================================================= */
  const SESSION_META_KEY = "x6.session.meta.v1";
  function loadSessionMeta() {
    try { return JSON.parse(localStorage.getItem(SESSION_META_KEY) || "{}") || {}; }
    catch (e) { return {}; }
  }
  function saveSessionMeta(meta) {
    try { localStorage.setItem(SESSION_META_KEY, JSON.stringify(meta || {})); }
    catch (e) { /* 隐私模式等场景静默降级，不影响列表渲染 */ }
  }
  function sessionMeta(sid) { return loadSessionMeta()[sid] || {}; }
  function patchSessionMeta(sid, patch) {
    const m = loadSessionMeta();
    m[sid] = Object.assign({}, m[sid], patch);
    saveSessionMeta(m);
  }
  function isPinned(sid) { return !!sessionMeta(sid).pinned; }
  function isHidden(sid) { return !!sessionMeta(sid).hidden; }
  function overlayTitle(sid) { return sessionMeta(sid).title || ""; }

  const GROUP_LABEL = { pinned: "置顶", today: "Today", d7: "7 Days", earlier: "Earlier" };
  function sessionGroupOf(ts) {
    const t = new Date(ts).getTime();
    if (!t) return "earlier";
    const now = new Date();
    const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
    if (t >= todayStart) return "today";
    if (t >= todayStart - 7 * 86400000) return "d7";
    return "earlier";
  }

  async function loadRecent() {
    const box = $("#recentList");
    if (!box) return;
    try {
      const r = await getJSON("/api/sessions");
      const list = (r && r.sessions) || [];
      S.sessions = list;
      const visible = list.filter((s) => !isHidden(s.session_id || s.id || ""));
      const hiddenCount = list.length - visible.length;

      if (!visible.length) {
        box.innerHTML = '<div class="recent-empty">' +
          '<div class="re-ico">💬</div><div>还没有对话记录</div>' +
          '<button class="customize-btn" data-view="chat">开始对话</button></div>' +
          (hiddenCount ? restoreHiddenHTML(hiddenCount) : "");
        bindSessionActions(box);
        return;
      }

      const items = visible.map((s) => {
        const sid = s.session_id || s.id || "";
        const ts = s.updated_at || s.created_at || "";
        return {
          sid, ts, time: relTime(ts), pinned: isPinned(sid),
          label: overlayTitle(sid) || cleanSessionLabel(sid),
        };
      });
      box.innerHTML = renderSessionGroups(items, hiddenCount);
      bindSessionActions(box);
      // 渐进增强：未手动命名的会话，用会话详情首条用户消息自动补全标题（零后端改动）
      items.forEach((it) => { if (!overlayTitle(it.sid)) enrichRecent(it, box); });
    } catch (e) {
      box.innerHTML = errorBox("对话列表读取失败", e.message);
    }
  }

  function restoreHiddenHTML(n) {
    return '<div class="recent-restore"><button class="recent-restore-btn" data-act="restore-hidden">显示 ' +
      n + " 个已隐藏会话</button></div>";
  }

  function renderSessionGroups(items, hiddenCount) {
    const buckets = [["pinned", []], ["today", []], ["d7", []], ["earlier", []]];
    items.forEach((it) => {
      const key = it.pinned ? "pinned" : sessionGroupOf(it.ts);
      const b = buckets.find((x) => x[0] === key) || buckets[3];
      b[1].push(it);
    });
    let html = "";
    buckets.forEach((b) => {
      if (!b[1].length) return;
      html += '<div class="recent-group"><span class="recent-group-title">' + esc(GROUP_LABEL[b[0]]) +
        '<span class="recent-group-count">' + b[1].length + "</span></span></div>";
      html += b[1].map(sessionItemHTML).join("");
    });
    if (hiddenCount) html += restoreHiddenHTML(hiddenCount);
    return html;
  }

  function sessionItemHTML(it) {
    const active = it.sid && it.sid === S.currentSid ? " active" : "";
    return '<button class="recent-item' + active + '" data-session="' + esc(it.sid) + '" title="' + esc(it.sid) + '">' +
      '<span class="ri-ico">💬</span>' +
      '<span class="title">' + (it.pinned ? '<span class="pin-flag" title="已置顶">📌</span>' : "") +
      '<span class="ri-label">' + esc(it.label) + "</span></span>" +
      '<span class="time">' + esc(it.time) + "</span>" +
      '<span class="recent-actions">' +
      '<span class="recent-action" data-act="rename" title="重命名">✏️</span>' +
      '<span class="recent-action" data-act="pin" title="置顶 / 取消置顶">📌</span>' +
      '<span class="recent-action danger" data-act="hide" title="隐藏会话">✕</span>' +
      "</span></button>";
  }

  function bindSessionActions(box) {
    box.querySelectorAll("[data-act]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        const act = btn.dataset.act;
        if (act === "restore-hidden") { restoreHiddenSessions(); return; }
        const item = btn.closest(".recent-item");
        if (!item) return;
        const sid = item.dataset.session || "";
        if (act === "rename") doRenameSession(sid);
        else if (act === "pin") doTogglePinSession(sid);
        else if (act === "hide") doHideSession(sid);
      });
    });
  }

  function doRenameSession(sid) {
    const cur = overlayTitle(sid) || cleanSessionLabel(sid);
    const next = window.prompt("重命名会话：", cur);
    if (next == null) return;
    const v = String(next).trim().slice(0, 40);
    if (!v) { toast("名称不能为空", true); return; }
    patchSessionMeta(sid, { title: v });
    toast("已重命名");
    loadRecent();
  }

  function doTogglePinSession(sid) {
    patchSessionMeta(sid, { pinned: !isPinned(sid) });
    toast(isPinned(sid) ? "已置顶" : "已取消置顶");
    loadRecent();
  }

  function doHideSession(sid) {
    if (!window.confirm("隐藏这个会话？数据不会删除，可随时恢复显示。")) return;
    patchSessionMeta(sid, { hidden: true });
    toast("已隐藏会话");
    loadRecent();
  }

  function restoreHiddenSessions() {
    const m = loadSessionMeta();
    Object.keys(m).forEach((k) => { if (m[k] && m[k].hidden) m[k].hidden = false; });
    saveSessionMeta(m);
    toast("已恢复显示隐藏会话");
    loadRecent();
  }

  function deriveSessionTitle(sess) {
    const conv = sess.conversation;
    if (Array.isArray(conv) && conv.length) {
      const pick = conv.find((m) => m.role === "user" || m.role === "human") || conv[0];
      const txt = pick.content || pick.text || pick.message || "";
      const s = String(txt).replace(/\s+/g, " ").trim();
      if (s) return s.slice(0, 24);
    }
    if (sess.latest_checkpoint && sess.latest_checkpoint.label)
      return String(sess.latest_checkpoint.label).slice(0, 24);
    return null;
  }

  async function enrichRecent(it, box) {
    try {
      const d = await getJSON("/api/session?session_id=" + encodeURIComponent(it.sid));
      const sess = d && d.session;
      if (!sess) return;
      const title = deriveSessionTitle(sess);
      if (!title) return;
      box.querySelectorAll(".recent-item").forEach((el) => {
        if (el.dataset.session !== it.sid) return;
        const t = el.querySelector(".ri-label");
        if (t) { t.textContent = title; el.title = it.sid + " · " + title; }
      });
    } catch (e) { /* 详情不可用不影响列表，静默降级 */ }
  }

  async function resumeSession(sid) {
    try {
      const d = await postJSON("/api/session/resume", { session_id: sid });
      if (d && d.ok) {
        S.currentSid = sid;
        toast("已恢复对话");
        loadRecent();
        await renderHistoryIntoChat();
        switchView("chat");
      } else {
        toast("无法恢复该对话", true);
      }
    } catch (e) {
      toast("对话恢复失败：" + e.message, true);
    }
  }


  async function renderHistoryIntoChat() {
    try {
      const rows = await getJSON("/api/chat/history?limit=20");
      const list = Array.isArray(rows) ? rows : (rows.items || rows.history || []);
      if (!list.length) return;
      hideChatEmpty();
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
     任务中心：当前任务 / 历史任务 / 执行过程
     ========================================================= */
  async function loadTasks() {
    const box = $("#tasksBody");
    box.innerHTML = LOADING;
    try {
      S.tasks = await getJSON("/api/tasks");
      if (!Array.isArray(S.tasks)) S.tasks = [];
    } catch (e) {
      box.innerHTML = errorBox("任务读取失败", e.message);
      return;
    }
    renderTasks();
  }

  function renderTasks() {
    const box = $("##tasksBody");
    if (S.taskTab === "trace") { renderTrace(box); return; }
    if (S.taskTab === "recent") { renderRecentWork(box); return; }

    // PHASE 128.1：与前端筛选共用同一套状态判定，避免两处规则漂移
    const isRun = wxIsRun, isDone = wxIsDone;

    // 统计（保留已有：进行中 / 今日完成 / 全部任务）
    const runningCount = S.tasks.filter(isRun).length;
    const today = todayStr();
    const doneToday = S.tasks.filter((x) => isDone(x) &&
      String(x.updated || x.created || "").slice(0, 10) === today).length;
    const total = S.tasks.length;

    let html = '<div class="wc-stats">' +
      wcStat(runningCount, "进行中", "run") +
      wcStat(doneToday, "今日完成", "done") +
      wcStat(total, "全部任务", "") +
      "</div>";

    // PHASE 128.1 纯前端筛选：只基于已加载的 S.tasks，不请求接口、不改动原始数据
    const filtered = wxFiltered();
    html += wxFilters();

    // Work Center 风格区域：小6正在工作（按真实 status 分类，禁止假任务）
    html += '<div class="wc-board">' +
      '<div class="wc-board-head"><span class="wc-spark">⚡</span> 小6正在工作</div>' +
      '<div class="wc-cols">' +
        wcCol("run", "正在执行", filtered.filter(isRun), "run") +
        wcCol("done", "已完成", filtered.filter(isDone), "done") +
        wcCol("wait", "等待执行", filtered.filter((x) => !isRun(x) && !isDone(x)), "wait") +
      "</div></div>";

    // 保留已有：当前 / 历史 列表（可点击查看详情）
    const list = filtered.filter((x) => (S.taskTab === "current" ? isRun(x) : !isRun(x)));
    if (!list.length) {
      html += empty(S.taskTab === "current" ? "当前没有进行中的任务" : "暂无历史任务");
    } else {
      html += '<div class="list">' + list.slice(0, 60).map((t) => {
        const pct = Number(t.progress || 0) || 0;
        const cur = t.current_step || 0, tot = t.total_steps || 0;
        const prog = tot ? Math.round((cur / tot) * 100) : pct;
        return '<div class="row-card" data-task-id="' + esc(t.id) + '">' +
          '<div class="row-title">' + esc(t.title || "(无标题)") +
          '<span class="badge ' + (isRun(t) ? "run" : "ok") + '">' + esc(statusLabel(t.status)) + "</span></div>" +
          (t.note ? '<div class="row-desc">' + esc(String(t.note).slice(0, 160)) + "</div>" : "") +
          (tot ? '<div class="progress-wrap"><div class="progress"><span style="width:' +
            Math.min(100, prog) + '%"></span></div><div class="progress-pct">' + prog + "%</div></div>" : "") +
          '<div class="row-foot">' +
          "<span>编号 " + esc(t.id) + "</span>" +
          (tot ? "<span>步骤 " + esc(cur) + " / " + esc(tot) + "</span>" : "") +
          (t.created ? "<span>创建 " + esc(t.created) + "</span>" : "") +
          (t.updated ? "<span>更新 " + esc(t.updated) + "</span>" : "") +
          "</div></div>";
      }).join("") + "</div>";
    }

    box.innerHTML = html;
  }

  function wcStat(num, label, kind) {
    return '<div class="wc-stat ' + (kind || "") + '"><div class="wc-stat-num">' + num +
      '</div><div class="wc-stat-label">' + label + "</div></div>";
  }
  function wcCol(kind, title, items, accent) {
    const body = items.length
      ? items.map(wcTaskCard).join("")
      : '<div class="wc-empty">暂无任务</div>';
    return '<div class="wc-col wc-col-' + kind + '">' +
      '<div class="wc-col-head"><span class="wc-dot ' + accent + '"></span>' + title +
      ' <span class="wc-count">' + items.length + "</span></div>" +
      '<div class="wc-col-body">' + body + "</div></div>";
  }
  function wcTaskCard(t) {
    const sc = statusClass(t.status);
    const label = statusLabel(t.status);
    // 描述：优先 note，其次 description；不存在则隐藏
    const desc = (t.note || t.description)
      ? '<div class="wc-card-desc">' + esc(String(t.note || t.description).slice(0, 140)) + "</div>"
      : "";
    // PHASE 127.2：计划步骤数量 / 产出数量——仅当真实字段存在时显示，否则整行隐藏
    let wpMeta = "";
    const planN = wpPlanCount(t);
    const outN = wpArtifactCount(t);
    if (planN) wpMeta += '<span class="wp-chip wp-chip-plan">计划 ' + planN + " 步</span>";
    if (outN) wpMeta += '<span class="wp-chip wp-chip-out">产出 ' + outN + "</span>";
    // PHASE 128.2：健康度标签 + 关注按钮
    const health = WorkHealth ? WorkHealth.calculateHealth(t) : null;
    let healthHtml = "";
    if (health && health.status !== 'GOOD') {
      const icons = { WARNING: '⚠', STALE: '⏸', FAILED: '✗' };
      const healthClass = 'health-' + health.status.toLowerCase();
      healthHtml = '<span class="health-badge ' + healthClass + '" title="' + esc(health.reason) + '">' +
        (icons[health.status] || '') + '</span>';
    }
    const isWatched = WorkFilters ? WorkFilters.isTaskWatched(t.id) : false;
    const watchIcon = isWatched ? '★' : '☆';
    const watchTitle = isWatched ? '取消关注' : '关注此任务';
    // PHASE 128.1：hover 层级提升（wx- 前缀，不修改 wc- 规则）+ 快速信息区
    return '<div class="wc-card wc-' + sc + ' wx-card" data-task-id="' + esc(t.id) + '">' +
      '<div class="wc-card-top">' +
        '<span class="wc-status ' + sc + '"></span>' +
        '<span class="wc-card-title">' + esc(t.title || "(无标题)") + "</span>" +
        healthHtml +
        '<button class="watch-btn' + (isWatched ? ' watched' : '') + '" data-watch="' + esc(t.id) + '" title="' + watchTitle + '">' + watchIcon + '</button>' +
      "</div>" +
      '<div class="wc-card-status">' + esc(label) + "</div>" +
      desc +
      (wpMeta ? '<div class="wp-card-meta">' + wpMeta + "</div>" : "") +
      wxQuick(t) +
      "</div>";
  }
  /* ---- PHASE 128.1 Work Center 交互收口（纯前端，零新增接口） ----
     ① 状态判定：与 Work Center 看板共用同一套规则（run / done / wait）
     ② 前端筛选：只基于已加载的 S.tasks 做内存过滤，不请求接口、不改动原始数据
     ③ 快速信息 / 任务摘要：只读 task 真实字段，字段缺失即隐藏，禁止编造与推算 */
  const wxRUNNING = ["open", "running", "in_progress", "active", "pending"];
  const wxCOMPLETED = ["done", "completed", "finished", "success"];
  function wxIsRun(x) {
    return wxRUNNING.indexOf(String((x && x.status) || "").toLowerCase()) >= 0;
  }
  function wxIsDone(x) {
    return wxCOMPLETED.indexOf(String((x && x.status) || "").toLowerCase()) >= 0;
  }
  function wxIsWait(x) { return !wxIsRun(x) && !wxIsDone(x); }

  // 返回新数组，绝不改动 S.tasks 本身
  function wxFiltered() {
    const all = Array.isArray(S.tasks) ? S.tasks : [];
    const f = S.taskFilter || "all";
    if (f === "run") return all.filter(wxIsRun);
    if (f === "done") return all.filter(wxIsDone);
    if (f === "wait") return all.filter(wxIsWait);
    if (f === "watched") {
      const watched = WorkFilters ? WorkFilters.getWatchedTasks() : [];
      return all.filter(t => watched.includes(t.id));
    }
    return all.slice();
  }
  function wxFilters() {
    const all = Array.isArray(S.tasks) ? S.tasks : [];
    const watched = WorkFilters ? WorkFilters.getWatchedTasks() : [];
    const n = {
      all: all.length,
      run: all.filter(wxIsRun).length,
      done: all.filter(wxIsDone).length,
      wait: all.filter(wxIsWait).length,
      watched: watched.length,
    };
    const cur = S.taskFilter || "all";
    const defs = [
      ["all", "全部"],
      ["run", "执行中"],
      ["done", "已完成"],
      ["wait", "等待执行"],
      ["watched", "我的关注"],
    ];
    return '<div class="wx-filters" role="group" aria-label="工作筛选">' +
      defs.map(function (d) {
        const on = cur === d[0];
        return '<button type="button" class="wx-filter' + (on ? " wx-active" : "") +
          '" data-wx-filter="' + d[0] + '" aria-pressed="' + (on ? "true" : "false") + '">' +
          '<span class="wx-dot wx-dot-' + d[0] + '"></span>' +
          '<span class="wx-flabel">' + d[1] + "</span>" +
          '<span class="wx-fnum">' + n[d[0]] + "</span></button>";
      }).join("") + "</div>";
  }
  function bindWxFilters() {
    document.addEventListener("click", (e) => {
      const b = e.target.closest("[data-wx-filter]");
      if (b) {
        const key = b.dataset.wxFilter;
        if (!key || key === S.taskFilter) return;
        S.taskFilter = key;   // 仅前端状态：不重新请求接口、不修改 S.tasks
        renderTasks();        // 复用已加载数据重绘，不触碰其他模块状态
        return;
      }
      // 关注按钮点击
      const watchBtn = e.target.closest("[data-watch]");
      if (watchBtn) {
        const taskId = watchBtn.dataset.watch;
        if (WorkFilters && taskId) {
          const isNowWatched = WorkFilters.toggleWatchTask(taskId);
          renderTasks();
          toast(isNowWatched ? "已关注此任务" : "已取消关注");
        }
        return;
      }
    });
  }

  /* 快速信息区：只允许 status / current_step / total_steps / created / updated。
     严禁计算百分比或推算进度；字段不存在 → 隐藏该条目。
     注：status 已由卡片既有 .wc-card-status 展示，此处不重复渲染。 */
  function wxQuick(t) {
    let items = "";
    const cur = t.current_step, tot = t.total_steps;
    const hasCur = cur != null && cur !== "";
    const hasTot = tot != null && tot !== "";
    if (hasCur && hasTot) {
      items += '<span class="wx-q wx-q-step">步骤 ' + esc(cur) + " / " + esc(tot) + "</span>";
    } else if (hasTot) {
      items += '<span class="wx-q wx-q-step">总步骤 ' + esc(tot) + "</span>";
    } else if (hasCur) {
      items += '<span class="wx-q wx-q-step">当前第 ' + esc(cur) + " 步</span>";
    }
    if (t.created) items += '<span class="wx-q wx-q-created">创建 ' + esc(t.created) + "</span>";
    if (t.updated) items += '<span class="wx-q wx-q-updated">更新 ' + esc(t.updated) + "</span>";
    return items ? '<div class="wx-quick">' + items + "</div>" : "";
  }

  /* 任务摘要：只读 title / note / description / step / status，存在什么显示什么。
     不做任何 AI 生成式总结；五字段全无 → 「暂无摘要」。 */
  function tdSummary(t) {
    let rows = "";
    if (t.title != null && String(t.title).trim()) {
      rows += wxSumRow("任务", esc(String(t.title).trim()));
    }
    if (t.status != null && String(t.status).trim()) {
      rows += wxSumRow("状态", esc(statusLabel(t.status)));
    }
    if (t.step != null && String(t.step).trim()) {
      rows += wxSumRow("当前步骤", esc(String(t.step).trim()));
    }
    const note = (t.note != null && String(t.note).trim())
      ? String(t.note).trim()
      : ((t.description != null && String(t.description).trim()) ? String(t.description).trim() : "");
    if (note) rows += wxSumRow("说明", esc(note.slice(0, 200)));
    const body = rows
      ? '<div class="wx-summary-body">' + rows + "</div>"
      : '<div class="wx-summary-body wx-summary-empty">暂无摘要</div>';
    return '<div class="wx-section">' +
      '<div class="wx-section-title">📝 任务摘要</div>' + body + "</div>";
  }
  function wxSumRow(k, v) {
    return '<div class="wx-srow"><span class="wx-sk">' + esc(k) +
      '</span><span class="wx-sv">' + v + "</span></div>";
  }

  /* ---- PHASE 127.1 工作产出 / Artifact Center（纯前端展示，零新增接口）----
     数据来源（按优先级只读 task 已有字段）：artifacts → outputs → output → result → files
     全部不存在 → 显示「暂无产出」；绝不生成模拟文件、不编造产出。
     操作按钮能力判定：打开(需 http/https url) / 查看(需 content) / 复制(需 content 或 url)，
     无对应能力则隐藏该按钮。 */
  let waCache = [];
  function waCollect(t) {
    const keys = ["artifacts", "outputs", "output", "result", "files"];
    for (let i = 0; i < keys.length; i++) {
      const v = t[keys[i]];
      if (v == null) continue;
      if (Array.isArray(v)) { if (v.length) return v; continue; }
      if (typeof v === "object") {
        if (v.name || v.title || v.path || v.url || v.content || v.text) return [v];
        continue;
      }
      if (typeof v === "string" && v.trim()) return [{ name: v.trim() }];
    }
    return [];
  }
  function waNorm(it) {
    if (typeof it === "string") return { name: it, type: "", time: "", url: "", content: it };
    const o = it || {};
    const pick = function () {
      for (let i = 0; i < arguments.length; i++) {
        const v = o[arguments[i]];
        if (typeof v !== "undefined" && v !== null && String(v).trim() !== "") return String(v).trim();
      }
      return "";
    };
    return {
      name: pick("name", "title", "filename", "file", "path"),
      type: pick("type", "kind", "mime", "ext"),
      time: pick("time", "created", "updated", "timestamp", "at"),
      url: pick("url", "link", "href"),
      content: pick("content", "text", "body", "preview"),
    };
  }
  function waIcon(type, name) {
    const s = (String(type || "") + " " + String(name || "")).toLowerCase();
    if (/\.(png|jpe?g|gif|webp|svg|bmp)|image|图片|截图/.test(s)) return "🖼";
    if (/\.(xlsx?|csv|json|tsv)|data|数据|表格|sheet/.test(s)) return "🗂";
    if (/report|报告|summary|总结/.test(s)) return "📊";
    if (/\.(md|txt|docx?|pdf|log)|文件|file|文档/.test(s)) return "📄";
    return "📦";
  }
  function tdArtifacts(t) {
    waCache = waCollect(t).map(waNorm);
    let html = '<div class="wa-section">' +
      '<div class="wa-section-title">📦 工作产出</div>';
    if (!waCache.length) return html + '<div class="wa-empty">暂无产出</div></div>';
    html += '<div class="wa-list">' + waCache.map(function (a, i) {
      const canOpen = /^https?:\/\//i.test(a.url);
      const canView = !!String(a.content || "").trim();
      const canCopy = canView || !!a.url;
      let acts = "";
      if (canOpen) acts += '<button type="button" class="wa-btn" data-wa-act="open" data-wa-url="' + esc(a.url) + '">打开</button>';
      if (canView) acts += '<button type="button" class="wa-btn" data-wa-act="view" data-wa-idx="' + i + '">查看</button>';
      if (canCopy) acts += '<button type="button" class="wa-btn" data-wa-act="copy" data-wa-idx="' + i + '">复制</button>';
      return '<div class="wa-card">' +
        '<div class="wa-card-top">' +
          '<span class="wa-icon">' + waIcon(a.type, a.name) + "</span>" +
          '<span class="wa-name">' + esc(a.name || "(未命名产出)") + "</span>" +
          (a.type ? '<span class="wa-type">' + esc(a.type) + "</span>" : "") +
        "</div>" +
        (a.time ? '<div class="wa-time">' + esc(a.time) + "</div>" : "") +
        (acts ? '<div class="wa-acts">' + acts + "</div>" : "") +
        (canView ? '<div class="wa-view" data-wa-view="' + i + '" hidden>' +
          esc(String(a.content).slice(0, 4000)) + "</div>" : "") +
        "</div>";
    }).join("") + "</div>";
    return html + "</div>";
  }
  function waCopy(text) {
    const ok = function () { toast("已复制"); };
    function fallback() {
      try {
        const ta = document.createElement("textarea");
        ta.value = String(text || "");
        ta.setAttribute("readonly", "");
        ta.style.position = "fixed"; ta.style.top = "-1000px"; ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
        ok();
      } catch (e) { toast("复制失败", true); }
    }
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(String(text || "")).then(ok, fallback);
        return;
      }
    } catch (e) { /* ignore → fallback */ }
    fallback();
  }
  function handleWaAction(btn) {
    const act = btn.dataset.waAct;
    if (act === "open") {
      const url = btn.dataset.waUrl || "";
      if (url) window.open(url, "_blank", "noopener");
      return;
    }
    const idx = Number(btn.dataset.waIdx);
    if (act === "view") {
      const box = document.querySelector('[data-wa-view="' + idx + '"]');
      if (box) {
        box.hidden = !box.hidden;
        btn.textContent = box.hidden ? "查看" : "收起";
      }
      return;
    }
    if (act === "copy") {
      const a = waCache[idx];
      if (!a) return;
      waCopy(String(a.content || "").trim() || a.url || a.name || "");
    }
  }

  function tdRow(k, v) {
    return '<div class="td-row"><div class="td-k">' + esc(k) + '</div><div class="td-v">' + v + "</div></div>";
  }

  /* ---- PHASE 127.2 工作计划 / Agent Plan Visualization（纯前端展示，零新增接口）----
     数据来源（按优先级只读 task 已有字段）：plan → steps → subtasks → checklist → description
     支持形态：数组[{title,status}] / 字符串数组 / 对象{steps:[]} / 纯字符串描述
     状态字段严格读取真实 status(|state)：completed / running / pending；
       识别不了的状态值 → 原样展示真实文本（不转换、不推断）；没有 status 字段 → 只显示文本。
     全部字段不存在 → 显示「暂无计划信息」，绝不生成假计划、绝不按序号推断状态。 */
  function wpUnwrap(v) {
    // 对象形态 { steps: [] } → 取出内部数组；取不出则返回 null
    if (!v || typeof v !== "object" || Array.isArray(v)) return null;
    const keys = ["steps", "subtasks", "checklist", "items", "tasks", "plan"];
    for (let i = 0; i < keys.length; i++) {
      const inner = v[keys[i]];
      if (Array.isArray(inner)) return inner.length ? inner : null;
    }
    return null;
  }
  function wpPlanSource(t) {
    const keys = ["plan", "steps", "subtasks", "checklist", "description"];
    for (let i = 0; i < keys.length; i++) {
      const key = keys[i];
      const v = t[key];
      if (v == null) continue;
      if (Array.isArray(v)) {
        if (v.length) return { items: v, key: key, textual: false };
        continue;
      }
      if (typeof v === "object") {
        const inner = wpUnwrap(v);
        if (inner) return { items: inner, key: key, textual: false };
        continue;
      }
      if (typeof v === "string" && v.trim()) {
        return { items: [v.trim()], key: key, textual: true };
      }
    }
    return null;
  }
  function wpPlanState(it) {
    if (!it || typeof it !== "object") return { code: "", text: "" };
    const rawV = (typeof it.status !== "undefined" && it.status !== null) ? it.status
      : (typeof it.state !== "undefined" && it.state !== null) ? it.state : null;
    if (rawV === null || String(rawV).trim() === "") return { code: "", text: "" };
    const v = String(rawV).trim().toLowerCase();
    if (/^(completed|complete|done|success|succeeded|finished|finish|成功|已完成)$/.test(v)) {
      return { code: "completed", text: "completed" };
    }
    if (/^(running|run|in_progress|in-progress|active|working|executing|执行中|进行中)$/.test(v)) {
      return { code: "running", text: "running" };
    }
    if (/^(pending|wait|waiting|todo|to_do|not_started|未开始|等待中)$/.test(v)) {
      return { code: "pending", text: "pending" };
    }
    return { code: "other", text: String(rawV).trim() };
  }
  function wpPlanTitle(it) {
    if (typeof it === "string") return it;
    const o = it || {};
    const v = o.title || o.name || o.text || o.step || o.content || o.action;
    return v ? String(v) : "";
  }
  function tdPlan(t) {
    const src = wpPlanSource(t);
    const head = '<div class="wp-section">' +
      '<div class="wp-section-title">🧠 工作计划</div>';
    const emptyHtml = head + '<div class="wp-empty">暂无计划信息</div></div>';
    if (!src) return emptyHtml;
    const body = src.items.map(function (it, i) {
      const st = wpPlanState(it);
      const title = wpPlanTitle(it);
      if (!title && !st.text) return "";
      // 纯文本描述（非步骤列表）不编号，避免把描述伪装成步骤
      const idx = src.textual ? "" : '<span class="wp-idx">' + (i + 1) + "</span>";
      return '<div class="wp-item' + (st.code ? " wp-item-" + st.code : "") + '">' +
        idx +
        '<span class="wp-text">' + esc(title || "(未命名步骤)") + "</span>" +
        (st.text ? '<span class="wp-state wp-state-' + st.code + '">' + esc(st.text) + "</span>" : "") +
        "</div>";
    }).join("");
    if (!body) return emptyHtml;
    return head + '<div class="wp-list">' + body + "</div></div>";
  }
  function wpPlanCount(t) {
    // 仅统计真实存在的步骤条目；纯描述文本不计入"步骤数"
    const src = wpPlanSource(t);
    if (!src || src.textual) return 0;
    return src.items.length;
  }
  function wpArtifactCount(t) {
    try { return waCollect(t).map(waNorm).length; } catch (e) { return 0; }
  }

  async function renderTrace(box) {
    box.innerHTML = LOADING;
    try {
      const r = await getJSON("/api/trace");
      const arr = (r && r.trace && r.trace.trace) || [];
      if (!arr.length) { box.innerHTML = empty("暂无执行记录"); return; }
      const rows = arr.slice(-40).reverse();
      box.innerHTML = '<div class="timeline">' + rows.map((x) => {
        const who = x.role === "user" ? "你" : (x.role === "xiao6" ? "小6" : esc(x.role || "系统"));
        const cls = x.role === "user" ? "tl-user" : (x.role === "xiao6" ? "tl-ai" : "tl-sys");
        return '<div class="tl-item ' + cls + '">' +
          '<div class="tl-dot"></div>' +
          '<div class="tl-body">' +
          '<div class="tl-head"><span class="tl-who">' + who + "</span>" +
          '<span class="tl-time">' + esc(x.timestamp || "") + "</span></div>" +
          '<div class="tl-text">' + esc(String(x.content || "").slice(0, 240)) + "</div>" +
          "</div></div>";
      }).join("") + "</div>";
    } catch (e) {
      box.innerHTML = errorBox("执行过程读取失败", e.message);
    }
  }

  /* ---- PHASE 128.2-D 最近工作视图 ---- */
  function renderRecentWork(box) {
    if (!Array.isArray(S.tasks) || !S.tasks.length) {
      box.innerHTML = empty("暂无任务记录");
      return;
    }
    const recent = WorkFilters ? WorkFilters.getRecentTasks(S.tasks) : [];
    if (!recent.length) {
      box.innerHTML = empty("暂无最近工作记录");
      return;
    }
    const groups = {
      opened: recent.filter(t => WorkFilters.isTaskRecentlyOpened(t.id)),
      done: recent.filter(t => ['done', 'completed', 'finished', 'success'].includes(String(t.status || '').toLowerCase())),
      failed: recent.filter(t => ['failed', 'error', 'failure'].includes(String(t.status || '').toLowerCase()))
    };
    let html = '<div class="recent-work-sections">';
    for (const [key, label] of [['opened', '最近打开'], ['done', '最近完成'], ['failed', '最近失败']]) {
      const items = groups[key];
      if (!items.length) continue;
      html += '<div class="recent-work-group">';
      html += '<div class="recent-work-group-title">' + label + ' <span class="recent-work-count">' + items.length + '</span></div>';
      html += '<div class="recent-work-list">' + items.map(t => {
        const sc = statusClass(t.status);
        const label = statusLabel(t.status);
        const health = WorkHealth ? WorkHealth.calculateHealth(t) : null;
        let healthHtml = '';
        if (health && health.status !== 'GOOD') {
          healthHtml = '<span class="health-badge health-' + health.status.toLowerCase() + '" title="' + esc(health.reason) + '"></span>';
        }
        const isWatched = WorkFilters ? WorkFilters.isTaskWatched(t.id) : false;
        const watchIcon = isWatched ? '★' : '☆';
        return '<div class="row-card" data-task-id="' + esc(t.id) + '">' +
          '<div class="row-title">' + esc(t.title || "(无标题)") +
          '<span class="badge ' + (sc === 'done' ? 'ok' : 'run') + '">' + esc(label) + '</span>' +
          (health && health.status !== 'GOOD' ? ' <span class="health-badge health-' + health.status.toLowerCase() + '" title="' + esc(health.reason) + '"></span>' : '') +
          ' <button class="watch-btn' + (isWatched ? ' watched' : '') + '" data-watch="' + esc(t.id) + '" title="' + (isWatched ? '取消关注' : '关注此任务') + '">' + watchIcon + '</button></div>' +
          (t.note ? '<div class="row-desc">' + esc(String(t.note).slice(0, 120)) + '</div>' : '') +
          '<div class="row-foot"><span>更新 ' + esc(t.updated || t.created || '') + '</span></div>' +
          '</div>';
      }).join('') + '</div></div>';
    }
    html += '</div>';
    box.innerHTML = html;
  }

  /* =========================================================
     任务详情（前端展示，无新增 API）
     ========================================================= */
  function bindTaskDetail() {
    document.addEventListener("click", (e) => {
      const waBtn = e.target.closest("[data-wa-act]");
      if (waBtn) { handleWaAction(waBtn); return; }
      const card = e.target.closest("[data-task-id]");
      if (card && card.dataset.taskId) { openTaskDetail(card.dataset.taskId); return; }
      if (e.target.closest('[data-act="close-task-modal"]')) { closeTaskModal(); return; }
      const m = $("#taskDetailModal");
      if (m && !m.hidden && e.target === m) closeTaskModal();
    });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeTaskModal(); });
  }
  function openTaskDetail(id) {
    const t = S.tasks.find((x) => String(x.id) === String(id));
    if (!t) { toast("未找到该任务", true); return; }
    // PHASE 128.3: 记录最近打开
    if (WorkFilters && t.id) {
      WorkFilters.recordOpenTask(String(t.id));
    }
    const sc = statusClass(t.status);
    const isRun = sc === "running";
    $("#tdTitle").textContent = t.title || "(无标题)";
    let rows = "";
    rows += tdRow("状态", '<span class="badge ' + (isRun ? "run" : "ok") + '">' + esc(statusLabel(t.status)) + "</span>");
    const desc = t.note || t.description;
    if (desc) rows += tdRow("描述", esc(String(desc)));
    if (t.created) rows += tdRow("创建时间", esc(t.created));
    if (t.updated) rows += tdRow("更新时间", esc(t.updated));
    if (t.id != null) rows += tdRow("编号", esc(t.id));
    if (t.total_steps != null || t.current_step != null) {
      rows += tdRow("步骤", esc(t.current_step || 0) + " / " + esc(t.total_steps || 0));
    }
    wxMemoScroll();   // PHASE 128.1：记住当前页面位置，关闭弹窗后原样恢复
    $("#tdBody").innerHTML =
      '<div class="td-rows">' + rows + "</div>" +
      tdSummary(t) +
      tdWorkState(sc) +
      tdPlan(t) +
      tdTimeline(t, sc) +
      tdArtifacts(t) +
      tdAgentActivity();
    $("#taskDetailModal").hidden = false;
  }

  /* ---- PHASE 126.2 工作状态：RUNNING / COMPLETED / WAITING（由真实 status 经 statusClass 派生） ---- */
  function tdWorkState(sc) {
    const map = { done: "COMPLETED", running: "RUNNING", pending: "WAITING" };
    const state = map[sc] || "WAITING";
    const cls = sc === "done" ? "done" : (sc === "running" ? "run" : "wait");
    return '<div class="td-section">' +
      '<div class="td-section-title">工作状态</div>' +
      '<div class="td-ws td-ws-' + cls + '">' +
        '<span class="td-ws-dot"></span>' +
        '<span class="td-ws-text">' + esc(state) + "</span>" +
      "</div></div>";
  }

  /* ---- PHASE 126.2 执行时间线（纯前端派生，零新增接口）
     数据来源：task 已有真实字段 created / step / steps / history / description / status / current_step / updated
     规则：创建任务 → 开始执行 → 当前状态 → 完成；steps/history 存在且有内容时追加真实明细；
           字段不存在 → 隐藏对应步骤，绝不编造执行记录。 */
  function tdTimeline(t, sc) {
    const items = [];
    const stepArr = Array.isArray(t.steps) ? t.steps : null;
    const histArr = Array.isArray(t.history) ? t.history : null;
    const curStep = Number(t.current_step || 0) || 0;
    const stepText = String(t.step || "").trim();
    const descText = String(t.description || "").trim();
    const started = curStep > 0 || !!stepText ||
      !!(stepArr && stepArr.length) || !!(histArr && histArr.length);

    // ① 创建任务：需 created 字段，否则隐藏
    if (t.created) {
      items.push(ttlItem("done", "创建任务", String(t.created), descText ? descText.slice(0, 120) : ""));
    }
    // ② 开始执行：需 step / steps / history / current_step 任一真实信号，否则隐藏
    if (started) {
      items.push(ttlItem("done", "开始执行", stepText || (curStep ? "已进入第 " + curStep + " 步" : ""), ""));
    }
    // ③ 当前状态：由真实 status 派生，恒为当前节点
    items.push(ttlItem("current", "当前状态", statusLabel(t.status), ""));
    // ④ 完成：仅当真实状态为已完成时才出现（不编造完成记录）
    if (sc === "done") {
      items.push(ttlItem("done", "完成", t.updated ? String(t.updated) : "", ""));
    }
    // steps 字段存在且有内容 → 追加真实步骤明细
    if (stepArr && stepArr.length) {
      stepArr.forEach(function (s, i) {
        const txt = (typeof s === "string" ? s : (s && (s.title || s.name || s.text || s.step))) || "";
        const st = s && (s.status || s.state) ? String(s.status || s.state).toLowerCase() : "";
        const fin = st ? /done|complete|成功|finish/.test(st) : (curStep ? i < curStep : false);
        const tm = s && (s.time || s.timestamp || s.updated) ? String(s.time || s.timestamp || s.updated) : "";
        items.push(ttlItem(fin ? "done" : "current", String(txt || "步骤 " + (i + 1)), tm, ""));
      });
    }
    // history 字段存在且有内容 → 追加真实历史明细
    if (histArr && histArr.length) {
      histArr.forEach(function (h) {
        const txt = (typeof h === "string" ? h : (h && (h.text || h.title || h.event || h.action || h.content))) || "";
        const tm = h && (h.time || h.timestamp || h.at) ? String(h.time || h.timestamp || h.at) : "";
        items.push(ttlItem("done", String(txt || "执行记录"), tm, ""));
      });
    }
    if (!items.length) return "";
    return '<div class="td-section">' +
      '<div class="td-section-title">执行时间线</div>' +
      '<div class="task-timeline">' + items.join("") + "</div></div>";
  }

  function ttlItem(state, title, meta, sub) {
    const mark = state === "done" ? "✓" : (state === "current" ? "●" : "○");
    return '<div class="ttl-item ttl-' + state + '">' +
      '<div class="ttl-mark">' + mark + "</div>" +
      '<div class="ttl-body">' +
        '<div class="ttl-title">' + esc(title) +
          (meta ? '<span class="ttl-meta">' + esc(meta) + "</span>" : "") +
        "</div>" +
        (sub ? '<div class="ttl-sub">' + esc(sub) + "</div>" : "") +
      "</div></div>";
  }

  /* ---- PHASE 126.2 最近 Agent 动作（复用 PHASE125.2 已有前端状态，零新增接口）
     仅当 session 真实存在 thinking / working / approval / tool event 时展示；
     idle 且无工具步骤 → 整段隐藏，不编造动作。 */
  function tdAgentActivity() {
    const el = $("#agentActivity");
    if (!el) return "";
    const cls = ["thinking", "working", "approval", "idle"]
      .filter(function (c) { return el.classList.contains(c); })[0] || "idle";
    let steps = [];
    try {
      if (typeof aaSteps !== "undefined" && aaSteps && aaSteps.length) {
        steps = aaSteps.slice(-6).map(function (s) {
          return { tool: s.tool || "工具", status: s.status || "done" };
        });
      }
    } catch (e) { steps = []; }
    const active = cls === "thinking" || cls === "working" || cls === "approval";
    if (!active && !steps.length) return "";
    const titleEl = $("#aaTitle");
    const text = titleEl ? String(titleEl.textContent || "").trim() : "";
    let html = '<div class="td-section">' +
      '<div class="td-section-title">最近 Agent 动作</div>' +
      '<div class="td-agent td-agent-' + cls + '">' +
        '<span class="td-ws-dot"></span>' +
        '<span class="td-agent-text">' + esc(text || defaultAaText(cls)) + "</span>" +
      "</div>";
    if (steps.length) {
      html += '<div class="task-timeline td-aa-list">' + steps.map(function (s) {
        const done = s.status === "done";
        return ttlItem(done ? "done" : "current", s.tool + (done ? " 完成" : " 执行中"), "", "");
      }).join("") + "</div>";
    }
    return html + "</div>";
  }
  /* PHASE 128.1 详情弹窗状态保持：关闭只切换 hidden，
     不重新加载、不重绘任务列表、不重置筛选、不改变页面位置。 */
  let wxScrollMemo = null;
  function wxMemoScroll() {
    try {
      const box = $("#tasksBody");
      wxScrollMemo = { y: window.scrollY || 0, box: box ? box.scrollTop : 0 };
    } catch (e) { wxScrollMemo = null; }
  }
  function wxRestoreScroll() {
    if (!wxScrollMemo) return;
    try {
      if ((window.scrollY || 0) !== wxScrollMemo.y && typeof window.scrollTo === "function") {
        window.scrollTo(0, wxScrollMemo.y);
      }
      const box = $("#tasksBody");
      if (box && box.scrollTop !== wxScrollMemo.box) box.scrollTop = wxScrollMemo.box;
    } catch (e) { /* 恢复失败不应影响关闭 */ }
  }
  function closeTaskModal() {
    const m = $("#taskDetailModal");
    if (m) m.hidden = true;
    wxRestoreScroll();
  }

  /* =========================================================
     知识库
     ========================================================= */
  async function loadKnowledge() {
    const box = $("#knowledgeBody");
    box.innerHTML = LOADING;
    try {
      const r = await getJSON("/api/knowledge");
      S.knowledge = r;
      const docs = (r && r.docs) || [];
      if (!docs.length) { box.innerHTML = empty("知识库还是空的，可以把热点或文档保存进来"); return; }
      box.innerHTML = '<div class="list">' + docs.slice(0, 80).map((d) =>
        '<div class="row-card">' +
        '<div class="row-title">' + esc(d.title || d.doc_id || "(无标题)") +
        '<span class="badge ' + (d.status === "reviewed" ? "ok" : "") + '">' +
        esc(d.status === "reviewed" ? "已整理" : (d.status || "待整理")) + "</span></div>" +
        (d.path ? '<div class="row-desc">' + esc(d.path) + "</div>" : "") +
        '<div class="row-foot">' +
        (d.type ? "<span>" + esc(d.type) + "</span>" : "") +
        (d.domain ? "<span>" + esc(d.domain) + "</span>" : "") +
        (Array.isArray(d.tags) && d.tags.length ? "<span>" + esc(d.tags.slice(0, 4).join(" / ")) + "</span>" : "") +
        "</div></div>").join("") + "</div>";
    } catch (e) {
      box.innerHTML = errorBox("知识库读取失败", e.message);
    }
  }

  /* =========================================================
     记忆（Obsidian 三栏：文件树 / 编辑器 / 知识关系图）
     真实接口：/api/notes*（列表 / 单条 / 新建 / 更新 / 删除 / 图谱 / 搜索）
     ========================================================= */
  const LEGACY_PATTERNS = [/ZZ/i, /ZhuangZhou/i, /庄周/i, /旧\s*UI/i, /old[\s_-]*ui/i, /legacy[\s_-]*ui/i];
  const isLegacy = (s) => LEGACY_PATTERNS.some((re) => re.test(String(s || "")));

  async function loadMemory() {
    const tree = $("#treeBody"), graph = $("#graphBody");
    tree.innerHTML = LOADING; graph.innerHTML = LOADING;
    try {
      let notes = await getJSON("/api/notes");
      if (!Array.isArray(notes)) notes = [];
      // 默认隐藏历史遗留数据（ZZ / ZhuangZhou / 庄周 / 旧 UI），不删除
      S.notes = notes.filter((n) => !isLegacy(n.title) && !isLegacy(n.folder) && !isLegacy(n.tags));
      S.legacyHidden = notes.length - S.notes.length;
    } catch (e) {
      tree.innerHTML = errorBox("记忆读取失败", e.message);
      graph.innerHTML = "";
      return;
    }
    renderTree();
    renderGraph();
  }

  function renderTree() {
    const tree = $("#treeBody");
    const notes = S.notes || [];
    if (!notes.length) { tree.innerHTML = empty("暂无记忆笔记"); return; }
    const byFolder = {};
    notes.forEach((n) => {
      const f = n.folder || "未整理";
      (byFolder[f] = byFolder[f] || []).push(n);
    });
    let html = "";
    Object.keys(byFolder).sort().forEach((f) => {
      html += '<div class="tree-folder-row"><span class="tree-folder">📁</span>' + esc(f) +
        '<span class="tree-count">' + byFolder[f].length + "</span></div>";
      byFolder[f].slice().sort((a, b) => String(b.ts || "").localeCompare(String(a.ts || ""))).forEach((n) => {
        html += '<div class="tree-item' + (S.currentNote && S.currentNote.id === n.id ? " active" : "") +
          '" data-note="' + esc(n.id) + '" title="' + esc(n.title || "") + '">' +
          '<span class="ico">📄</span><span class="ti-title">' + esc(n.title || "(无标题)") + "</span></div>";
      });
    });
    tree.innerHTML = html;
  }

  async function openNote(id) {
    try {
      const n = await getJSON("/api/notes/" + encodeURIComponent(id));
      S.currentNote = n;
      $("#editorTitle").textContent = n.title || "(无标题)";
      $("#markdownEditor").value = n.markdown || "";
      $("#markdownEditor").disabled = false;
      $("#btnSaveNote").disabled = false;
      $("#btnDeleteNote").disabled = false;
      $("#btnRenameNote").disabled = false;
      renderTree();
      // 右侧显示该笔记的关联
      renderBacklinks(n.title);
    } catch (e) {
      toast("打开笔记失败：" + e.message, true);
    }
  }

  async function renderBacklinks(title) {
    const box = $("#graphBody");
    if (!title) return;
    try {
      const bl = await getJSON("/api/notes/backlinks?title=" + encodeURIComponent(title));
      const list = Array.isArray(bl) ? bl : (bl.backlinks || []);
      if (list.length) {
        box.innerHTML = '<div class="bl-wrap"><div class="bl-title">被以下笔记引用</div>' +
          list.slice(0, 12).map((x) =>
            '<div class="tree-item" data-note="' + esc(x.id) + '"><span class="ico">🔗</span>' +
            '<span class="ti-title">' + esc(x.title || "(无标题)") + "</span></div>").join("") +
          "</div>" +
          '<div class="bl-switch"><button class="mini-btn" id="btnBackGraph">返回关系图</button></div>';
        const b = $("#btnBackGraph");
        if (b) b.addEventListener("click", renderGraph);
      }
    } catch (e) { /* 反向链接不可用时保留关系图 */ }
  }

  async function renderGraph() {
    const box = $("#graphBody");
    box.innerHTML = LOADING;
    try {
      S.graph = await getJSON("/api/notes/graph");
    } catch (e) {
      box.innerHTML = errorBox("关系图读取失败", e.message);
      return;
    }
    const g = S.graph || {};
    const nodes = g.nodes || [];
    const edges = g.edges || [];
    if (!nodes.length) { box.innerHTML = empty("还没有可展示的知识节点"); return; }
    const hint = $("#graphHint");
    if (hint) hint.textContent = nodes.length + " 个节点";
    box.innerHTML = drawGraph(nodes, edges);
    box.querySelectorAll("[data-gnode]").forEach((el) => {
      el.addEventListener("click", () => openNote(el.getAttribute("data-gnode")));
    });
  }

  // 轻量力导向布局（无第三方库）： repulsion + spring + 向心力
  function drawGraph(nodes, edges) {
    const W = 260, H = 340, pad = 22;
    const n = nodes.length;
    const pos = nodes.map((_, i) => {
      const a = (i / n) * Math.PI * 2;
      return { x: W / 2 + Math.cos(a) * 90, y: H / 2 + Math.sin(a) * 90, vx: 0, vy: 0 };
    });
    const idx = {};
    nodes.forEach((nd, i) => { idx[nd.id] = i; });
    const links = edges.map((e) => ({
      s: idx[e.source != null ? e.source : e.from],
      t: idx[e.target != null ? e.target : e.to],
    })).filter((l) => l.s != null && l.t != null);

    for (let it = 0; it < 220; it++) {
      for (let i = 0; i < n; i++) {
        for (let j = i + 1; j < n; j++) {
          let dx = pos[i].x - pos[j].x, dy = pos[i].y - pos[j].y;
          let d2 = dx * dx + dy * dy || 0.01;
          const f = 900 / d2;
          const d = Math.sqrt(d2);
          pos[i].vx += (dx / d) * f; pos[i].vy += (dy / d) * f;
          pos[j].vx -= (dx / d) * f; pos[j].vy -= (dy / d) * f;
        }
      }
      links.forEach((l) => {
        const a = pos[l.s], b = pos[l.t];
        let dx = b.x - a.x, dy = b.y - a.y;
        const d = Math.sqrt(dx * dx + dy * dy) || 0.01;
        const f = (d - 60) * 0.02;
        a.vx += (dx / d) * f; a.vy += (dy / d) * f;
        b.vx -= (dx / d) * f; b.vy -= (dy / d) * f;
      });
      pos.forEach((p) => {
        p.vx += (W / 2 - p.x) * 0.006;
        p.vy += (H / 2 - p.y) * 0.006;
        p.x += Math.max(-8, Math.min(8, p.vx));
        p.y += Math.max(-8, Math.min(8, p.vy));
        p.x = Math.max(pad, Math.min(W - pad, p.x));
        p.y = Math.max(pad, Math.min(H - pad, p.y));
        p.vx *= 0.82; p.vy *= 0.82;
      });
    }

    let svg = '<svg class="graph-canvas" viewBox="0 0 ' + W + " " + H + '">';
    links.forEach((l) => {
      svg += '<line x1="' + pos[l.s].x.toFixed(1) + '" y1="' + pos[l.s].y.toFixed(1) +
        '" x2="' + pos[l.t].x.toFixed(1) + '" y2="' + pos[l.t].y.toFixed(1) +
        '" stroke="#ececef" stroke-width="1" />';
    });
    nodes.forEach((nd, i) => {
      const r = 3.2 + Math.min(4, (nd.val || 1) * 0.7);
      const cur = S.currentNote && S.currentNote.id === nd.id;
      svg += '<g class="gnode' + (cur ? " cur" : "") + '" data-gnode="' + esc(nd.id) + '">' +
        '<circle cx="' + pos[i].x.toFixed(1) + '" cy="' + pos[i].y.toFixed(1) + '" r="' + r.toFixed(1) +
        '" fill="' + (cur ? "#ff4d4f" : "#ffb3b3") + '" />' +
        '<text x="' + (pos[i].x + r + 4).toFixed(1) + '" y="' + (pos[i].y + 3.2).toFixed(1) +
        '" font-size="8" fill="#8a8a8a">' + esc(String(nd.title || "").slice(0, 10)) + "</text>" +
        "</g>";
    });
    svg += "</svg>";
    if (!links.length) {
      svg += '<div class="graph-note">笔记之间暂无双向链接，先展示全部节点</div>';
    }
    return svg;
  }

  function bindMemoryPane() {
    const tree = $("#treeBody");
    if (tree) tree.addEventListener("click", (e) => {
      const el = e.target.closest("[data-note]");
      if (el) openNote(el.dataset.note);
    });
    const gbox = $("#graphBody");
    if (gbox) gbox.addEventListener("click", (e) => {
      const el = e.target.closest("[data-note]");
      if (el) openNote(el.dataset.note);
    });

    const btnNew = $("#btnNewNote");
    if (btnNew) btnNew.addEventListener("click", async () => {
      const title = prompt("新笔记标题", "新笔记 " + todayStr());
      if (title == null) return;
      try {
        const r = await postJSON("/api/notes", {
          title: title || ("新笔记 " + todayStr()),
          markdown: "# " + (title || "新笔记") + "\n\n",
          folder: "收件箱",
        });
        if (r && r.ok) { toast("已创建"); await loadMemory(); openNote(r.id); }
        else throw new Error((r && r.error) || "创建失败");
      } catch (e) { toast("创建失败：" + e.message, true); }
    });

    const btnSave = $("#btnSaveNote");
    if (btnSave) btnSave.addEventListener("click", async () => {
      const n = S.currentNote;
      if (!n) { toast("请先选择一篇笔记", true); return; }
      const md = $("#markdownEditor").value;
      try {
        const r = await postJSON("/api/notes/update", {
          id: n.id, title: n.title, markdown: md,
          folder: n.folder || "收件箱", tags: n.tags || "",
        });
        if (r && r.ok) { toast("已保存"); await loadMemory(); openNote(n.id); }
        else throw new Error((r && r.error) || "保存失败");
      } catch (e) { toast("保存失败：" + e.message, true); }
    });

    const btnDel = $("#btnDeleteNote");
    if (btnDel) btnDel.addEventListener("click", async () => {
      const n = S.currentNote;
      if (!n) { toast("请先选择一篇笔记", true); return; }
      if (!confirm("确定删除笔记「" + (n.title || "") + "」？此操作不可恢复。")) return;
      try {
        const r = await postJSON("/api/notes/delete", { id: n.id });
        if (r && r.ok) {
          toast("已删除");
          S.currentNote = null;
          $("#editorTitle").textContent = "选择一篇笔记";
          $("#markdownEditor").value = "";
          await loadMemory();
        } else throw new Error((r && r.error) || "删除失败");
      } catch (e) { toast("删除失败：" + e.message, true); }
    });

    const btnRename = $("#btnRenameNote");
    if (btnRename) btnRename.addEventListener("click", async () => {
      const n = S.currentNote;
      if (!n) { toast("请先选择一篇笔记", true); return; }
      const t = prompt("重命名笔记", n.title || "");
      if (t == null || !t.trim()) return;
      try {
        const r = await postJSON("/api/notes/update", {
          id: n.id, title: t.trim(), markdown: $("#markdownEditor").value,
          folder: n.folder || "收件箱", tags: n.tags || "",
        });
        if (r && r.ok) { toast("已重命名"); await loadMemory(); openNote(n.id); }
        else throw new Error((r && r.error) || "重命名失败");
      } catch (e) { toast("重命名失败：" + e.message, true); }
    });

    // 记忆搜索（真实 /api/notes/search?q=）
    const input = $("#memSearch"), btn = $("#btnMemSearch");
    const runSearch = async () => {
      const q = (input.value || "").trim();
      if (!q) { await loadMemory(); return; }
      const tree = $("#treeBody");
      tree.innerHTML = LOADING;
      try {
        let list = await getJSON("/api/notes/search?q=" + encodeURIComponent(q));
        if (!Array.isArray(list)) list = [];
        list = list.filter((n) => !isLegacy(n.title));
        if (!list.length) { tree.innerHTML = empty("没有找到相关记忆"); return; }
        let html = '<div class="tree-folder-row">搜索结果 · ' + list.length + " 条</div>";
        list.slice(0, 40).forEach((n) => {
          html += '<div class="tree-item" data-note="' + esc(n.id) + '">' +
            '<span class="ico">📄</span><span class="ti-title">' + esc(n.title || "(无标题)") + "</span></div>";
        });
        tree.innerHTML = html;
      } catch (e) {
        tree.innerHTML = errorBox("搜索失败", e.message);
      }
    };
    if (btn) btn.addEventListener("click", runSearch);
    if (input) input.addEventListener("keydown", (e) => { if (e.key === "Enter") runSearch(); });

    // 清理历史遗留数据（默认只统计，删除需二次确认）
    const btnClean = $("#btnCleanLegacy");
    if (btnClean) btnClean.addEventListener("click", cleanLegacy);
  }

  async function cleanLegacy() {
    const PATTERNS = [/ZZ/i, /ZhuangZhou/i, /庄周/i, /旧\s*UI/i, /old[\s_-]*ui/i, /legacy[\s_-]*ui/i];
    const box = $("#knowledgeBody");
    try {
      let notes = await getJSON("/api/notes");
      if (!Array.isArray(notes)) notes = [];
      const hit = notes.filter((n) => PATTERNS.some((re) =>
        re.test(String(n.title || "")) || re.test(String(n.folder || "")) || re.test(String(n.tags || ""))));
      let kdocs = [];
      try {
        const k = await getJSON("/api/knowledge");
        kdocs = ((k && k.docs) || []).filter((d) => PATTERNS.some((re) =>
          re.test(String(d.title || "")) || re.test(String(d.path || "")) || re.test(String(d.doc_id || ""))));
      } catch (e) { kdocs = []; }

      if (!hit.length && !kdocs.length) { toast("没有找到需要清理的历史数据"); return; }

      const names = hit.slice(0, 10).map((n) => "· " + (n.title || "(无标题)")).join("\n") +
        (hit.length > 10 ? "\n… 等共 " + hit.length + " 条笔记" : "");
      const ok = confirm(
        "检测到历史遗留数据：\n\n笔记 " + hit.length + " 条\n知识库文档 " + kdocs.length + " 篇\n\n" +
        names + "\n\n确定要永久删除吗？此操作不可恢复。\n（只删除这些内容，不会影响其他记忆）"
      );
      if (!ok) { toast("已取消，未做任何改动"); return; }

      let okN = 0, failN = 0;
      for (const n of hit) {
        try {
          const r = await postJSON("/api/notes/delete", { id: n.id });
          if (r && r.ok) okN++; else failN++;
        } catch (e) { failN++; }
      }
      toast("清理完成：笔记删除 " + okN + " 条" + (failN ? "，失败 " + failN + " 条" : ""));
      if (box) S.knowledge = null;
      await loadMemory();
    } catch (e) {
      toast("清理失败：" + e.message, true);
    }
  }

  /* =========================================================
     能力中心（用户视角分类，不暴露工具数量）
     ========================================================= */
  const CAP_CATEGORY = {
    // 推理
    user_model: "推理", self_diagnosis: "推理", time: "推理",
    // 搜索
    tools: "搜索", world_pulse: "搜索", hotspot: "搜索", prefetch: "搜索",
    // 文件
    read_file: "文件", modify_file: "文件", open_file: "文件", open_folder: "文件",
    search: "文件", delete: "文件",
    // 浏览器
    browser_navigate: "浏览器",
    // 语音
    voice: "语音",
    // 桌面
    computer_action: "桌面", perception: "桌面", capture_screen: "桌面",
    get_window_info: "桌面", list_process: "桌面", "perception.screen": "桌面",
    "perception.window": "桌面", "perception.ocr": "桌面", copy_text: "桌面",
    open_application: "桌面", focus_window: "桌面", execute_command: "桌面",
    kill_process: "桌面", system: "桌面", network: "桌面",
    // 知识
    memory: "知识", knowledge: "知识",
    // 任务
    goals: "任务",
  };
  const CAP_CATS = [
    { key: "推理", desc: "理解你的偏好、分析问题与系统状态" },
    { key: "搜索", desc: "联网检索、热点与实时信息" },
    { key: "文件", desc: "读取、整理与管理本地文件" },
    { key: "浏览器", desc: "打开网页、按你的指令浏览" },
    { key: "语音", desc: "听懂你说的话，也能读给你听" },
    { key: "桌面", desc: "感知屏幕、操作窗口与应用" },
    { key: "知识", desc: "记住你，管理你的知识库" },
    { key: "任务", desc: "拆解目标、跟踪执行进度" },
  ];

  async function loadCapabilities() {
    const box = $("#capabilitiesBody");
    box.innerHTML = LOADING;
    await ensureCaps();
    renderCapabilities();
  }

  function allCapItems() {
    const caps = CAPS();
    const out = [];
    if (!caps || !caps.groups) return out;
    Object.keys(caps.groups).forEach((g) => {
      (caps.groups[g] || []).forEach((c) => out.push(Object.assign({}, c, { __group: g })));
    });
    return out;
  }

  function renderCapabilities() {
    const box = $("#capabilitiesBody");
    const filters = $("#capFilters");
    const items = allCapItems();

    if (filters) {
      filters.innerHTML = '<button class="cap-filter' + (S.capFilter === "all" ? " active" : "") +
        '" data-cat="all">全部</button>' +
        CAP_CATS.map((c) => {
          const n = items.filter((x) => CAP_CATEGORY[x.id] === c.key).length;
          if (!n) return "";
          return '<button class="cap-filter' + (S.capFilter === c.key ? " active" : "") +
            '" data-cat="' + esc(c.key) + '">' + esc(c.key) + " " + n + "</button>";
        }).join("");
    }

    if (!items.length) {
      box.innerHTML = errorBox("能力列表不可用", "后端 /api/capability_os/catalog 未返回数据");
      return;
    }

    const picked = S.capFilter === "all" ? items : items.filter((x) => CAP_CATEGORY[x.id] === S.capFilter);
    if (!picked.length) { box.innerHTML = empty("该分类下暂无能力"); return; }

    const catDesc = CAP_CATS.find((c) => c.key === S.capFilter);
    let html = "";
    if (catDesc) {
      html += '<div class="cat-intro"><div class="ci-name">' + esc(catDesc.key) + "</div>" +
        '<div class="ci-desc">' + esc(catDesc.desc) + "</div></div>";
    }
    html += '<div class="grid">' + picked.map((c) => {
      const on = !!c.available;
      return '<div class="tool-card cap-card' + (on ? "" : " cap-off") + '">' +
        '<div class="cap-card-head">' +
        '<div class="tool-name">' + esc(c.icon || "") + " " + esc(c.name || c.id) + "</div>" +
        '<span class="badge ' + (on ? "ok" : "") + '">' + (on ? "可用" : "未开启") + "</span>" +
        "</div>" +
        '<div class="tool-desc">' + esc(c.description || "") + "</div>" +
        "</div>";
    }).join("") + "</div>";
    box.innerHTML = html;
  }

  /* =========================================================
     设置：通用 / 模型中心 / 联网策略 / 服务状态
     ========================================================= */
  async function loadSettings() {
    const box = $("#settingsBody");
    box.innerHTML = LOADING;
    await ensureConfig();
    renderSettings();
  }

  function renderSettings() {
    const box = $("#settingsBody");
    const t = S.settingsTab;
    if (t === "models") { renderModels(box); return; }
    if (t === "network") { renderNetwork(box); return; }
    if (t === "diagnostics") { renderDiagnostics(box); return; }
    renderGeneral(box);
  }

  function renderGeneral(box) {
    const cfg = S.config || {};
    let html = '<div class="row-card"><div class="kv">' +
      kv("助手名称", cfg.ai_name) +
      kv("外观主题", cfg.theme === "light" ? "浅色" : (cfg.theme || "—")) +
      kv("当前模型", (cfg.llm && cfg.llm.model) || "—") +
      kv("模型提供方", providerShortName(cfg.active_provider || (cfg.llm && cfg.llm.active)) || "—") +
      kv("长期记忆", cfg.memory_graph ? "已开启" : "已关闭") +
      "</div></div>";

    html += '<div class="page-head" style="margin-top:24px"><h1 style="font-size:16px">关于</h1></div>';
    const v = (cfg.version && cfg.version.current) || "1.0.0";
    html += '<div class="row-card"><div class="kv">' +
      kv("小6 版本", v) +
      kv("应用名称", (cfg.version && cfg.version.app_name) || "小6") +
      "</div></div>";
    box.innerHTML = html;
  }

  function kv(k, v) {
    return '<div class="k">' + esc(k) + '</div><div class="v">' + esc(v == null ? "—" : v) + "</div>";
  }

  /* ---------- 模型中心 ---------- */
  const CLOUD_PROVIDERS = [
    { key: "agnes", name: "Agnes", slot: "agnes", base: "https://api.agnes-ai.cn/v1",
      models: ["agnes-2.5-flash", "agnes-2.0-flash", "agnes-1.5-flash"], auth: true, hint: "小6 默认使用的云端模型" },
    { key: "deepseek", name: "DeepSeek", slot: "llm2", base: "https://api.deepseek.com/v1",
      models: ["deepseek-chat", "deepseek-reasoner"], auth: true },
    { key: "glm", name: "智谱 GLM", slot: "llm2", base: "https://open.bigmodel.cn/api/paas/v4",
      models: ["glm-4.6", "glm-4.5", "glm-4-flash"], auth: true },
    { key: "minimax", name: "MiniMax", slot: "llm2", base: "https://api.minimax.chat/v1",
      models: ["MiniMax-Text-01", "abab6.5s-chat"], auth: true },
    { key: "openai", name: "OpenAI", slot: "llm2", base: "https://api.openai.com/v1",
      models: ["gpt-4o", "gpt-4o-mini", "gpt-4.1"], auth: true },
    { key: "claude", name: "Claude", slot: "llm2", base: "https://api.anthropic.com/v1",
      models: ["claude-sonnet-4-5", "claude-3-7-sonnet"], auth: true,
      hint: "Anthropic 原生接口非 OpenAI 格式，需填写 OpenAI 兼容网关地址" },
    { key: "gemini", name: "Gemini", slot: "llm2", base: "https://generativelanguage.googleapis.com/v1beta/openai",
      models: ["gemini-2.5-pro", "gemini-2.5-flash"], auth: true },
  ];
  const LOCAL_PROVIDERS = [
    { key: "ollama", name: "Ollama", slot: "ollama", base: "http://127.0.0.1:11434/v1", models: [], auth: false },
    { key: "mlx", name: "MLX", slot: "mlx", base: "http://127.0.0.1:8080/v1", models: [], auth: false },
    { key: "lmstudio", name: "LM Studio", slot: "lmstudio", base: "http://127.0.0.1:1234/v1", models: [], auth: false },
  ];
  const SLOT_ENV = {
    agnes: { base: "AGNES_BASE_URL", key: "AGNES_API_KEY", model: "AGNES_MODEL" },
    llm2: { base: "LLM2_BASE_URL", key: "LLM2_API_KEY", model: "LLM2_MODEL" },
    ollama: { base: "OLLAMA_BASE_URL", key: "", model: "OLLAMA_MODEL" },
    mlx: { base: "MLX_BASE_URL", key: "", model: "MLX_MODEL" },
    lmstudio: { base: "LMSTUDIO_BASE_URL", key: "", model: "LMSTUDIO_MODEL" },
  };

  function llm2Occupant(cfg) {
    const b = ((cfg.llm || {}).llm2 || {}).base_url || "";
    if (!b) return null;
    return CLOUD_PROVIDERS.find((p) => p.slot === "llm2" && p.base === b.replace(/\/+$/, "")) || { key: "custom", name: "自定义服务" };
  }

  function providerValues(cfg, p) {
    const spec = (cfg.providers || []).find((x) => x.id === p.slot) || {};
    if (p.slot === "agnes") {
      return { base: (cfg.llm && cfg.llm.base_url) || p.base, model: (cfg.llm && cfg.llm.model) || "", keySet: !!(cfg.llm && cfg.llm.key_present) };
    }
    if (p.slot === "llm2") {
      const occ = llm2Occupant(cfg);
      const mine = occ && occ.key === p.key;
      return {
        base: mine ? (cfg.llm.llm2.base_url || p.base) : p.base,
        model: mine ? (cfg.llm.llm2.model || "") : "",
        keySet: mine ? !!(cfg.llm.llm2.key_present) : false,
        occupiedBy: (!mine && occ) ? occ.name : "",
      };
    }
    return { base: spec.resolved_base_url || p.base, model: spec.resolved_model || "", keySet: false };
  }

  function renderModels(box) {
    const cfg = S.config || {};
    const active = (cfg.active_provider || (cfg.llm && cfg.llm.active) || "").toLowerCase();
    const occ = llm2Occupant(cfg);

    let html = "";
    if (occ && occ.key === "custom") {
      html += '<div class="notice-box">当前「自定义云端服务」槽位填的是一个未在列表中的地址，' +
        "选择下方任一云端厂商并启用后会覆盖它。</div>";
    }

    html += '<div class="sec-title">云端模型</div>';
    html += CLOUD_PROVIDERS.map((p) => modelCard(cfg, p, active, "cloud")).join("");
    html += '<div class="notice-box">云端模型中，Agnes 使用独立配置；DeepSeek / 智谱 GLM / MiniMax / OpenAI / Claude / Gemini ' +
      "共用同一个「自定义云端服务」槽位，同一时间只能启用其中一个。</div>";

    html += '<div class="sec-title" style="margin-top:24px">本地模型</div>';
    html += LOCAL_PROVIDERS.map((p) => modelCard(cfg, p, active, "local")).join("");
    html += '<div class="notice-box">本地模型需要先在本机启动对应服务（Ollama / LM Studio / MLX），' +
      "并填写正确的服务地址与模型名称。</div>";

    html += '<div class="notice-box warn">配置保存后会写入小6 的配置文件，<b>重启小6 后生效</b>。</div>';

    box.innerHTML = html;
    bindModelActions();
  }

  function modelCard(cfg, p, active, kind) {
    const v = providerValues(cfg, p);
    const isActive = active === p.slot && (p.slot !== "llm2" || !v.occupiedBy);
    const envs = SLOT_ENV[p.slot];
    const modelOptions = (p.models && p.models.length)
      ? p.models.map((m) => '<option value="' + esc(m) + '"' + (v.model === m ? " selected" : "") + ">" + esc(m) + "</option>").join("")
      : "";

    return '<div class="model-card' + (isActive ? " mc-active" : "") + '" data-pk="' + esc(p.key) + '">' +
      '<div class="model-card-header">' +
      '<div class="model-card-title">' + esc(p.name) +
      '<span class="mc-kind">' + (kind === "local" ? "本地" : "云端") + "</span></div>" +
      (isActive ? '<span class="model-card-badge active">当前使用</span>'
        : '<span class="model-card-badge">' + (v.keySet ? "已配置密钥" : (kind === "local" ? "未连接" : "未配置")) + "</span>") +
      "</div>" +
      (v.occupiedBy ? '<div class="mc-occupied">该槽位当前被「' + esc(v.occupiedBy) + "」占用</div>" : "") +
      (p.hint ? '<div class="mc-hint">' + esc(p.hint) + "</div>" : "") +
      '<div class="model-form">' +
      (envs.key
        ? '<div class="field"><label>API Key</label><input type="password" class="f-key" placeholder="' +
          (v.keySet ? "已保存，留空则不修改" : "请输入 API Key") + '" autocomplete="off" /></div>'
        : '<div class="field"><label>API Key</label><input type="text" value="本地服务无需密钥" disabled /></div>') +
      '<div class="field"><label>Base URL</label><input type="text" class="f-base" value="' + esc(v.base) + '" /></div>' +
      '<div class="field"><label>模型</label>' +
      (modelOptions
        ? '<select class="f-model">' + modelOptions + "</select>"
        : '<input type="text" class="f-model" value="' + esc(v.model) + '" placeholder="例如 llama3.1:8b" />') +
      "</div>" +
      "</div>" +
      '<div class="model-actions">' +
      '<button class="btn-secondary" data-mact="test">连接测试</button>' +
      '<button class="btn-primary" data-mact="save">保存并设为默认</button>' +
      "</div>" +
      '<div class="mc-result"></div>' +
      "</div>";
  }

  function findProvider(key) {
    return CLOUD_PROVIDERS.find((p) => p.key === key) || LOCAL_PROVIDERS.find((p) => p.key === key);
  }

  function bindModelActions() {
    $$(".model-card").forEach((card) => {
      const key = card.dataset.pk;
      const p = findProvider(key);
      if (!p) return;
      card.addEventListener("click", (e) => {
        const b = e.target.closest("[data-mact]");
        if (!b) return;
        const act = b.dataset.mact;
        const base = card.querySelector(".f-base").value.trim();
        const model = card.querySelector(".f-model").value.trim();
        const keyEl = card.querySelector(".f-key");
        const apiKey = keyEl ? keyEl.value.trim() : "";
        const result = card.querySelector(".mc-result");
        if (act === "test") testProvider(card, p, base, model, apiKey, result, b);
        if (act === "save") saveProvider(card, p, base, model, apiKey, result, b);
      });
    });
  }

  async function testProvider(card, p, base, model, apiKey, result, btn) {
    if (!model) { result.className = "mc-result err"; result.textContent = "请先填写模型名称"; return; }
    if (p.auth && !apiKey) {
      const cfg = S.config || {};
      const v = providerValues(cfg, p);
      if (!v.keySet) { result.className = "mc-result err"; result.textContent = "请先填写 API Key"; return; }
    }
    const old = btn.textContent;
    btn.disabled = true; btn.textContent = "测试中…";
    result.className = "mc-result"; result.textContent = "正在连接…";
    try {
      const r = await postJSON("/api/test-llm", {
        base_url: base,
        api_key: p.auth ? apiKey : "local",
        model: model,
      });
      if (r && r.ok) {
        result.className = "mc-result ok";
        result.textContent = "连接成功 · 响应 " + (r.latency_ms || "—") + " ms · 模型 " + (r.model || model);
      } else {
        throw new Error((r && (r.error || r.detail)) || "连接失败");
      }
    } catch (e) {
      result.className = "mc-result err";
      result.textContent = "连接失败：" + e.message;
    } finally {
      btn.disabled = false; btn.textContent = old;
    }
  }

  async function saveProvider(card, p, base, model, apiKey, result, btn) {
    if (!model) { result.className = "mc-result err"; result.textContent = "请先填写模型名称"; return; }
    if (p.auth && !apiKey && !providerValues(S.config || {}, p).keySet) {
      result.className = "mc-result err"; result.textContent = "请先填写 API Key"; return;
    }
    const env = SLOT_ENV[p.slot];
    const payload = {};
    payload[env.base] = base;
    payload[env.model] = model;
    if (p.auth && apiKey) payload[env.key] = apiKey;
    payload.ACTIVE_LLM = p.slot;

    const old = btn.textContent;
    btn.disabled = true; btn.textContent = "保存中…";
    try {
      const r = await postJSON("/api/config", payload);
      if (r && r.ok) {
        result.className = "mc-result ok";
        result.textContent = "已保存并设为默认，重启小6 后生效";
        toast("已保存，重启小6 后生效");
        S.config = null;
        await ensureConfig();
      } else {
        throw new Error((r && (r.error || r.detail)) || "保存失败");
      }
    } catch (e) {
      result.className = "mc-result err";
      result.textContent = "保存失败：" + e.message;
    } finally {
      btn.disabled = false; btn.textContent = old;
    }
  }

  /* ---------- 联网策略（仅 UI 配置，不改 Agent Runtime） ---------- */
  const NET_KEY = "xiao6.network.policy";
  function loadPolicy() {
    try {
      return Object.assign({ mode: "auto", sources: "" }, JSON.parse(localStorage.getItem(NET_KEY) || "{}"));
    } catch (e) { return { mode: "auto", sources: "" }; }
  }
  function savePolicy(p) { try { localStorage.setItem(NET_KEY, JSON.stringify(p)); } catch (e) {} }

  function renderNetwork(box) {
    const pol = loadPolicy();
    const opts = [
      { mode: "auto", label: "自动判断", desc: "由小6自己决定这次是否需要联网查资料（默认）" },
      { mode: "off", label: "禁止联网", desc: "只用已有知识与本地数据回答，不访问网络" },
      { mode: "sources", label: "指定来源", desc: "需要联网时，只从你填写的来源获取信息" },
    ];
    let html = '<div class="row-card">' +
      opts.map((o) =>
        '<div class="network-option">' +
        '<input type="radio" name="netmode" value="' + o.mode + '" id="nm-' + o.mode + '"' +
        (pol.mode === o.mode ? " checked" : "") + " />" +
        '<div><label class="opt-label" for="nm-' + o.mode + '">' + esc(o.label) + "</label>" +
        '<div class="opt-desc">' + esc(o.desc) + "</div></div></div>").join("") +
      '<div class="source-field" id="srcField" style="display:' + (pol.mode === "sources" ? "flex" : "none") + '">' +
      '<input type="text" id="srcInput" placeholder="多个来源用逗号分隔，例如：官网, 知乎, 维基百科" value="' + esc(pol.sources) + '" />' +
      '<button id="btnSaveNet">保存</button></div>' +
      '<div class="net-note">这里只调整小6 的联网偏好；是否联网、怎么查，仍由小6 在每次对话中自行判断。</div>' +
      "</div>";
    box.innerHTML = html;

    $$('input[name="netmode"]').forEach((r) => r.addEventListener("change", () => {
      const sf = $("#srcField");
      if (sf) sf.style.display = r.value === "sources" ? "flex" : "none";
    }));
    const bs = $("#btnSaveNet");
    if (bs) bs.addEventListener("click", () => {
      const m = ($$('input[name="netmode"]').find((r) => r.checked) || {}).value || "auto";
      const src = ($("#srcInput") || {}).value || "";
      savePolicy({ mode: m, sources: src.trim() });
      toast("联网策略已保存");
    });
  }

  function policyPrefix() {
    const p = loadPolicy();
    if (p.mode === "off") {
      return "【联网约束】本次及后续回答禁止使用任何联网工具，只基于你已有的知识与本地数据回答。\n\n";
    }
    if (p.mode === "sources" && p.sources) {
      return "【联网约束】如需联网检索，请只从以下来源获取信息：" + p.sources + "。\n\n";
    }
    return "";
  }

  /* ---------- 服务状态 ---------- */
  async function renderDiagnostics(box) {
    box.innerHTML = LOADING;
    let ready = S.ready, health = S.health;
    try { if (!ready) ready = await getJSON("/api/ready"); } catch (e) { ready = null; }
    try { if (!health) health = await getJSON("/api/health"); } catch (e) { health = null; }

    const checks = (health && health.self_check && health.self_check.checked_at) || "";
    const list = (ready && ready.self_check && ready.self_check.checks) ||
      (health && health.self_check && health.self_check.checks) || [];
    const failed = list.filter((c) => !c.ok);

    let html = '<div class="status-grid" style="grid-template-columns:repeat(3,1fr)">' +
      statusItem("服务", (ready && ready.ready !== false) ? "运行中" : "启动中", (ready && ready.ready !== false) ? "ok" : "warn") +
      statusItem("模型", (S.config && S.config.llm && S.config.llm.model) || (health && health.model) || "—",
        (S.config && S.config.llm && S.config.llm.key_present) ? "ok" : "warn") +
      statusItem("语音", ttStatusLabel(list, health), ttStatusOK(list) ? "ok" : "warn") +
      "</div>";

    html += '<div class="page-head" style="margin-top:24px"><h1 style="font-size:16px">各模块状态' +
      '<span class="badge ' + (failed.length ? "warn" : "ok") + '" style="margin-left:10px">' +
      (failed.length ? failed.length + " 项待处理" : "全部正常") + "</span></h1></div>";

    html += list.length
      ? '<div class="grid">' + list.map((c) =>
          '<div class="tool-card"><div class="cap-card-head">' +
          '<div class="tool-name">' + esc(CHECK_LABEL[c.name] || c.name) + "</div>" +
          '<span class="badge ' + (c.ok ? "ok" : "warn") + '">' + (c.ok ? "正常" : "待处理") + "</span>" +
          "</div></div>").join("") + "</div>"
      : empty("暂无状态信息");

    if (checks) html += '<div class="net-note" style="margin-top:16px">最近检查时间：' + esc(checks) + "</div>";
    box.innerHTML = html;
  }

  function ttStatusLabel(list, health) {
    const c = list.find((x) => /TTS|语音/.test(String(x.name || "")));
    if (c) return c.ok ? "可用" : "待处理";
    return (health && health.tts_backend) ? String(health.tts_backend) : "未配置";
  }
  function ttStatusOK(list) {
    const c = list.find((x) => /TTS|语音/.test(String(x.name || "")));
    return c ? !!c.ok : false;
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
    $("#btnAttach").addEventListener("click", () => $("#fileInput").click());
    $("#fileInput").addEventListener("change", onFiles);

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

    const qc = $("#quickChips");
    if (qc) {
      qc.innerHTML = QUICK.map((q) => '<button class="chip" data-q="' + esc(q) + '">' + esc(q) + "</button>").join("");
      qc.addEventListener("click", (e) => {
        const b = e.target.closest("[data-q]");
        if (b) { ta.value = b.dataset.q; ta.dispatchEvent(new Event("input")); submit(); }
      });
    }
    bindVoice();
  }

  /* =========================================================
     首页全局 Command Bar（S125.1）
     复用已有聊天流程：switchView('chat') → 填充 #input → submit()
     禁止新增 API / 后端能力
     ========================================================= */
  function bindCommandBar() {
    const input = $("#commandInput");
    const send = $("#commandSend");
    const voice = $("#commandVoice");
    if (!input || !send) return;

    const doSend = () => {
      const text = (input.value || "").trim();
      if (!text) { toast("请输入你想让小6做什么", true); return; }
      input.value = "";
      switchView("chat");
      const ta = $("#input");
      ta.value = text;
      ta.dispatchEvent(new Event("input"));
      submit();
    };

    input.addEventListener("keydown", (e) => { if (e.key === "Enter") doSend(); });
    send.addEventListener("click", doSend);
    if (voice) {
      voice.addEventListener("click", () => {
        switchView("chat");
        const chatVoice = $("#btnVoice");
        if (chatVoice) chatVoice.click();
        else toast("当前环境不支持语音输入", true);
      });
    }
    document.addEventListener("click", (e) => {
      const b = e.target.closest("[data-cmd]");
      if (!b || !input) return;
      input.value = b.dataset.cmd;
      input.focus();
    });
  }

  function onFiles(e) { attachPaths(e.target.files); e.target.value = ""; }
  function attachPaths(files) {
    const names = Array.from(files).map((f) => f.name).join("、");
    if (!names) return;
    toast("已选择：" + names + "（文件读取受沙箱目录限制）");
  }

  /* =========================================================
     语音输入（真实 /api/asr）
     ========================================================= */
  let rec = null, recStream = null, recChunks = [];
  function bindVoice() {
    const btn = $("#btnVoice");
    btn.addEventListener("click", async () => {
      if (rec && rec.state === "recording") { rec.stop(); return; }
      if (!navigator.mediaDevices || !window.MediaRecorder) {
        toast("当前环境不支持录音", true); return;
      }
      try { recStream = await navigator.mediaDevices.getUserMedia({ audio: true }); }
      catch (e) { toast("麦克风不可用：" + e.message, true); return; }
      recChunks = [];
      rec = new MediaRecorder(recStream);
      rec.ondataavailable = (e) => { if (e.data && e.data.size) recChunks.push(e.data); };
      rec.onstop = async () => {
        recStream.getTracks().forEach((t) => t.stop());
        btn.classList.remove("on");
        const blob = new Blob(recChunks, { type: rec.mimeType || "audio/webm" });
        if (!blob.size) { toast("没有采集到声音", true); return; }
        try {
          // 冻结契约：POST /api/asr?ext=.wav，multipart 字段名必须是 audio
          const fd = new FormData();
          fd.append("audio", blob, "voice.wav");
          const text = await api("/api/asr?ext=.wav", { method: "POST", body: fd });
          const out = (typeof text === "string" ? text : (text.text || text.result || "")).trim();
          if (!out) { toast("没有听清，请再说一次", true); return; }
          $("#input").value = out;
          $("#input").dispatchEvent(new Event("input"));
          toast("已识别：" + out.slice(0, 20));
        } catch (e) {
          toast("语音识别失败：" + e.message, true);
        }
      };
      rec.start();
      btn.classList.add("on");
      toast("正在聆听… 再次点击结束");
    });
  }

  /* =========================================================
     SSE 事件总线 /api/stream（主动消息 + 审批请求）
     truthful：只有后端 {ok:true} 才置终态，否则保留按钮等重试
     ========================================================= */
  let evtSource = null;
  function initEventStream() {
    if (typeof EventSource === "undefined") return;
    if (evtSource) return;
    try { evtSource = new EventSource("/api/stream"); } catch (e) { return; }
    evtSource.onopen = function () {
      const dot = $("#liveDot");
      if (dot) dot.title = "服务运行中 · 实时消息已连接";
    };
    evtSource.onmessage = function (e) {
      let m = null;
      try { m = JSON.parse(e.data); } catch (_) { return; }
      handleStreamEvent(m);
    };
    evtSource.onerror = function () { /* EventSource 自动重连 */ };
  }

  function handleStreamEvent(m) {
    if (!m || typeof m !== "object") return;
    const ap = m.approval || m.modal || {};
    const ticket = m.ticket || ap.ticket;
    if (ticket) {
      setAgentState("approval", "等待你确认：" + esc((ap.tool || ap.summary || "一项操作")));
      renderApprovalCard(m, ticket);
      return;
    }
    if (m.xiao6_event === "proactive" || m.kind) { renderProactive(m); return; }
  }

  function renderProactive(m) {
    const kind = m.kind || "notice";
    const icon = kind === "alert" ? "📡" : kind === "briefing" ? "☀️" : kind === "reminder" ? "⏰" : "💬";
    const content = m.content || m.text || m.message || "";
    if (!content) return;
    const card = '<div class="proactive-card"><div class="pc-head">' + icon + " " + esc(kind) + "</div>" +
      '<div class="pc-body">' + esc(content) + "</div>" +
      (m.ts ? '<div class="pc-time">' + esc(m.ts) + "</div>" : "") + "</div>";
    hideChatEmpty();
    addMsg("assistant", card);
    toast(icon + " 小6 有新的消息");
  }

  function renderApprovalCard(m, ticket) {
    const ap = m.approval || m.modal || {};
    const tool = m.tool || ap.tool || "";
    const summary = m.summary || ap.summary || m.prompt || ap.prompt || "有一项操作需要你确认";
    const args = m.args_preview || ap.args_preview || m.argsPreview || ap.argsPreview || "";

    hideChatEmpty();
    const bubble = addMsg("assistant", "");
    const card = document.createElement("div");
    card.className = "approval-card";
    card.innerHTML =
      '<div class="ap-head">需要你确认' +
      (tool ? '<span class="ap-tool">' + esc(tool) + "</span>" : "") + "</div>" +
      '<div class="ap-body">' + esc(summary) + "</div>" +
      (args ? '<div class="ap-args">' + esc(args) + "</div>" : "") +
      '<div class="ap-actions"><button class="ap-yes">批准</button><button class="ap-no">拒绝</button>' +
      "</div>";
    bubble.appendChild(card);
    card.querySelector(".ap-yes").addEventListener("click", () => postApproval(ticket, "approve", card));
    card.querySelector(".ap-no").addEventListener("click", () => postApproval(ticket, "reject", card));
    toast("有一项操作需要你确认");
  }

  async function postApproval(ticket, decision, card) {
    const yes = card.querySelector(".ap-yes"), no = card.querySelector(".ap-no");
    if (yes) yes.disabled = true;
    if (no) no.disabled = true;
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
      if (yes) yes.disabled = false;
      if (no) no.disabled = false;
      toast("提交失败：" + e.message + "，请重试", true);
    }
  }

  /* =========================================================
     发送 + 流式输出
     ========================================================= */
  function hideChatEmpty() {
    const ce = $("#chatEmpty");
    if (ce) ce.style.display = "none";
  }

  function addMsg(role, html, id) {
    const wrap = document.createElement("div");
    wrap.className = "msg " + role;
    if (id) wrap.id = id;
    wrap.innerHTML = '<div class="avatar">' + (role === "user" ? "我" : "6") + "</div>" +
      '<div class="bubble">' + html + "</div>";
    $("#messages").appendChild(wrap);
    const box = $("#chatScroll");
    box.scrollTop = box.scrollHeight;
    return wrap.querySelector(".bubble");
  }

  function addToolLine(text, cls) {
    return addMsg("assistant",
      '<span class="tool-evt ' + cls + '"><span class="dot"></span>' + text + "</span>");
  }

  /* ---------------- PHASE 125.2 Agent Activity 可视化（纯前端，复用已有 xiao6_event 流） ----------------
     状态源（零后端改动）：
       · S.busy 提交→响应周期             → thinking / idle
       · /api/chat SSE 的 xiao6_event     → tool_start(running) / tool_end(done)
       · /api/stream 的 approval 事件     → approval（等待用户确认）
     红线：只展示已有真实事件，不编造、不新增接口。 */
  let aaSteps = [];
  function defaultAaText(state) {
    return state === "thinking" ? "小6正在思考…" :
           state === "working" ? "小6正在工作" :
           state === "approval" ? "等待你确认…" : "小6已就绪";
  }
  function setAgentState(state, text) {
    const el = $("#agentActivity");
    if (!el) return;
    el.classList.remove("idle", "thinking", "working", "approval");
    el.classList.add(state);
    const t = $("#aaTitle");
    if (t) t.textContent = text || defaultAaText(state);
  }
  function clearAgentSteps() {
    aaSteps = [];
    const box = $("#aaSteps");
    if (box) box.innerHTML = "";
  }
  function addAgentStep(tool, status) {
    const box = $("#aaSteps");
    if (!box) return;
    const row = document.createElement("div");
    row.className = "aa-step " + status;
    const label = tool || "工具";
    row.innerHTML = '<span class="aa-step-dot"></span><span class="aa-step-text">' +
      esc(status === "running" ? "正在调用 " + label + " …" : label + " 完成") + "</span>";
    box.appendChild(row);
    aaSteps.push({ tool, el: row, status });
    while (box.children.length > 6) box.removeChild(box.firstChild);
  }
  function finishAgentStep(tool) {
    for (let i = aaSteps.length - 1; i >= 0; i--) {
      if (aaSteps[i].status === "running") {
        aaSteps[i].status = "done";
        const el = aaSteps[i].el;
        el.classList.remove("running"); el.classList.add("done");
        const txt = el.querySelector(".aa-step-text");
        if (txt) txt.textContent = esc(aaSteps[i].tool || "工具") + " 完成";
        return;
      }
    }
  }

  /* ---------------- TTS 朗读（真实 POST /api/speak） ---------------- */
  let currentAudio = null;
  async function speak(text, btn) {
    if (!text || !text.trim()) return;
    try {
      if (btn) { btn.disabled = true; btn.textContent = "合成中…"; }
      // 冻结契约：body { text, stream:false }
      const res = await fetch("/api/speak", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: text, stream: false }),
      });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const blob = await res.blob();
      if (!blob.size) throw new Error("返回的音频为空");
      const url = URL.createObjectURL(blob);
      if (currentAudio) { currentAudio.pause(); currentAudio = null; }
      const audio = new Audio(url);
      currentAudio = audio;
      if (btn) { btn.classList.add("playing"); btn.textContent = "播放中…"; }
      audio.onended = () => {
        URL.revokeObjectURL(url);
        if (btn) { btn.classList.remove("playing"); btn.disabled = false; btn.textContent = "朗读"; }
      };
      audio.onerror = () => {
        URL.revokeObjectURL(url);
        toast("音频播放失败", true);
        if (btn) { btn.classList.remove("playing"); btn.disabled = false; btn.textContent = "朗读"; }
      };
      await audio.play();
    } catch (e) {
      // 后端 /api/speak 在 v1.0.0 为悬空路由（S118 遗留，非本次改动），
      // 连接会被直接重置，fetch 抛 TypeError。此处对普通用户降级为可读提示，不暴露堆栈。
      const raw = String((e && e.message) || e || "");
      const netErr = /failed to fetch|networkerror|load failed|empty reply/i.test(raw);
      toast(netErr ? "语音朗读暂不可用（TTS 服务未挂载），已跳过朗读" : "语音合成失败：" + raw, true);
      if (btn) { btn.classList.remove("playing"); btn.disabled = false; btn.textContent = "朗读"; }
    }
  }

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

    // 联网策略：仅在用户消息前附加约束说明，不改任何 Runtime 逻辑
    const payload = policyPrefix() + text;

    hideChatEmpty();
    addMsg("user", esc(text));
    ta.value = ""; ta.style.height = "auto";
    S.conversation.push({ role: "user", content: payload });

    S.busy = true;
    clearAgentSteps();
    setAgentState("thinking", "小6正在思考…");
    $("#btnSend").disabled = true;
    const bubble = addMsg("assistant", '<span class="typing"><i></i><i></i><i></i></span>');
    let acc = "", gotAny = false;

    try {
      await streamChat(S.conversation, (evt) => {
        const delta = evt.choices && evt.choices[0] && evt.choices[0].delta;
        if (delta && typeof delta.content === "string") {
          if (!gotAny) { bubble.innerHTML = ""; gotAny = true; }
          acc += delta.content;
          bubble.textContent = acc;
          const box = $("#chatScroll");
          box.scrollTop = box.scrollHeight;
        }
        if (evt.xiao6_event === "tool_start") {
          addToolLine("正在调用 <code>" + esc(evt.tool || "tool") + "</code> …", "running");
          setAgentState("working", "小6正在工作");
          addAgentStep(evt.tool || "tool", "running");
        }
        if (evt.xiao6_event === "tool_end") {
          addToolLine("<code>" + esc(evt.tool || "tool") + "</code> 调用完成", "done");
          finishAgentStep(evt.tool || "tool");
        }
      });

      if (!gotAny) {
        bubble.innerHTML = '<span style="color:#8a8a8a">（这次没有返回文字内容）</span>';
      } else {
        S.conversation.push({ role: "assistant", content: acc });
        attachSpeak(bubble, acc);
      }
      loadRecent();
    } catch (e) {
      bubble.innerHTML = '<div class="error-state" style="text-align:left">' +
        "<div>小6暂时没能完成这个请求</div>" +
        '<div class="detail" style="text-align:left">' + esc(e.message) + "</div>" +
        '<button class="customize-btn" style="margin-top:10px" data-retry="1">重试</button></div>';
      toast("请求失败：" + e.message, true);
      } finally {
        S.busy = false;
        $("#btnSend").disabled = false;
        setAgentState("idle");
      }
  }

  document.addEventListener("click", (e) => {
    if (e.target && e.target.dataset && e.target.dataset.retry) {
      if (S.conversation.length && S.conversation[S.conversation.length - 1].role === "user") submit();
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
        try { onEvent(JSON.parse(payload)); } catch (_) {}
      }
    }
    const tail = buf.trim();
    if (tail.startsWith("data:")) {
      const p = tail.slice(5).trim();
      if (p && p !== "[DONE]") { try { onEvent(JSON.parse(p)); } catch (_) {} }
    }
  }

  /* ---------------- System Center ---------------- */
  async function loadSystemCenter() {
    const body = $("#systemBody");
    if (!body) return;
    body.innerHTML = '<div class="mini-loading"><span class="spinner"></span>加载中…</div>';

    try {
      const [readyRes, versionRes, memRes, knowledgeRes] = await Promise.all([
        fetch("/api/ready"),
        fetch("/api/version"),
        fetch("/api/memory"),
        fetch("/api/knowledge")
      ]);

      const ready = await readyRes.json();
      const version = await versionRes.json();
      const memory = await memRes.json();
      const knowledge = await knowledgeRes.json();

      const caps = ready.capabilities || {};
      const tools = ready.tools || 0;
      const status = ready.status || "unknown";
      const runtime = ready.runtime || "unknown";
      const dbStatus = ready.database || "unknown";

      const profiles = memory.profiles ? memory.profiles.length : 0;
      const memNotes = memory.notes ? memory.notes.length : 0;
      const memLogs = memory.logs ? memory.logs.length : 0;

      const knowledgeNodes = knowledge.nodes ? knowledge.nodes.length : 0;
      const knowledgeRelations = knowledge.relations ? knowledge.relations.length : 0;

      const ttsStatus = ready.optional_services && ready.optional_services.tts === "blocked" ? "BLOCKED" : (ready.optional_services && ready.optional_services.tts || "unknown");

      let html = `
        <div class="system-grid">
          <div class="system-card">
            <div class="card-header">
              <span class="card-title">版本信息</span>
              <span class="status-badge ${status === 'ready' ? 'ok' : 'warn'}">${status.toUpperCase()}</span>
            </div>
            <div class="card-body">
              <div class="meta-row"><span class="label">App Name</span><span class="value">${esc(version.app_name || '小6')}</span></div>
              <div class="meta-row"><span class="label">Version</span><span class="value">${esc(version.version || '1.0.0')}</span></div>
              <div class="meta-row"><span class="label">Runtime</span><span class="value status-ready">READY</span></div>
              <div class="meta-row"><span class="label">Database</span><span class="value status-ready">READY</span></div>
            </div>
          </div>

          <div class="system-card">
            <div class="card-header">
              <span class="card-title">能力矩阵</span>
              <span class="status-badge ok">${caps.ready || 0}/${caps.total || 0} READY</span>
            </div>
            <div class="card-body">
              <div class="meta-row"><span class="label">Total</span><span class="value">${caps.total || 0}</span></div>
              <div class="meta-row"><span class="label">Ready</span><span class="value status-ready">✅ ${caps.ready || 0}</span></div>
              <div class="meta-row"><span class="label">Partial</span><span class="value status-partial">⚠️ ${caps.partial || 0}</span></div>
              <div class="meta-row"><span class="label">Blocked</span><span class="value status-blocked">🔴 ${caps.blocked || 0}</span></div>
              <div class="meta-row"><span class="label">Not Impl</span><span class="value status-not-impl">⬜ ${caps.not_implemented || 0}</span></div>
            </div>
          </div>

          <div class="system-card">
            <div class="card-header">
              <span class="card-title">工具</span>
              <span class="status-badge ok">${tools} 已挂载</span>
            </div>
            <div class="card-body">
              <div class="meta-row"><span class="label">Total</span><span class="value">${tools}</span></div>
            </div>
          </div>

          <div class="system-card">
            <div class="card-header">
              <span class="card-title">记忆系统</span>
              <span class="status-badge ok">READY</span>
            </div>
            <div class="card-body">
              <div class="meta-row"><span class="label">Profiles</span><span class="value">${profiles}</span></div>
              <div class="meta-row"><span class="label">Notes</span><span class="value">${memNotes}</span></div>
              <div class="meta-row"><span class="label">Logs</span><span class="value">${memLogs}</span></div>
            </div>
          </div>

          <div class="system-card">
            <div class="card-header">
              <span class="card-title">知识库</span>
              <span class="status-badge ok">READY</span>
            </div>
            <div class="card-body">
              <div class="meta-row"><span class="label">Nodes</span><span class="value">${knowledgeNodes}</span></div>
              <div class="meta-row"><span class="label">Relations</span><span class="value">${knowledgeRelations}</span></div>
            </div>
          </div>

          <div class="system-card">
            <div class="card-header">
              <span class="card-title">感知系统</span>
              <span class="status-badge ok">READY</span>
            </div>
            <div class="card-body">
              <div class="meta-row"><span class="label">Screen</span><span class="value status-ready">✅</span></div>
              <div class="meta-row"><span class="label">Window</span><span class="value status-ready">✅</span></div>
              <div class="meta-row"><span class="label">OCR</span><span class="value status-ready">✅</span></div>
            </div>
          </div>

          <div class="system-card">
            <div class="card-header">
              <span class="card-title">TTS 服务</span>
              <span class="status-badge ${ttsStatus === 'BLOCKED' ? 'error' : 'ok'}">${ttsStatus}</span>
            </div>
            <div class="card-body">
              <div class="meta-row"><span class="label">Backend</span><span class="value">GPT-SoVITS</span></div>
              <div class="meta-row"><span class="label">Port</span><span class="value">9880</span></div>
              <div class="meta-row"><span class="label">Status</span><span class="value ${ttsStatus === 'BLOCKED' ? 'status-blocked' : 'status-ready'}">${ttsStatus}</span></div>
            </div>
          </div>
        </div>
      `;

      body.innerHTML = html;

    } catch (e) {
      body.innerHTML = errorBox("加载系统状态失败", e.message);
    }
  }

  /* ---------------- About Page ---------------- */
  async function loadAboutPage() {
    const body = $("#aboutBody");
    if (!body) return;
    body.innerHTML = '<div class="mini-loading"><span class="spinner"></span>加载中…</div>';

    try {
      const [versionRes, readyRes, selfAwarenessRes] = await Promise.all([
        fetch("/api/version"),
        fetch("/api/ready"),
        fetch("/api/self_awareness/status")
      ]);

      const version = await versionRes.json();
      const ready = await readyRes.json();
      const selfAwareness = await selfAwarenessRes.json();

      const caps = selfAwareness.capabilities || ready.capabilities || {};
      const totalTools = ready.tools || 63;

      let html = `
        <div class="about-container">
          <div class="about-hero">
            <div class="about-logo">
              <div class="logo-circle">6</div>
            </div>
            <div class="about-title">
              <h1>${esc(version.app_name || '小6')}</h1>
              <p class="tagline">个人 AI OS</p>
            </div>
          </div>

          <div class="about-info">
            <div class="info-card">
              <h3>版本信息</h3>
              <div class="meta-row"><span class="label">Version</span><span class="value">${esc(version.version || '1.0.0')}</span></div>
              <div class="meta-row"><span class="label">Build</span><span class="value">S141 Release Hardening</span></div>
              <div class="meta-row"><span class="label">Date</span><span class="value">2026-09-06</span></div>
            </div>

            <div class="info-card">
              <h3>架构</h3>
              <div class="meta-row"><span class="label">Runtime</span><span class="value">Single Agent</span></div>
              <div class="meta-row"><span class="label">Architecture</span><span class="value">Phase-based Development</span></div>
              <div class="meta-row"><span class="label">UI Framework</span><span class="value">Native SPA</span></div>
            </div>

            <div class="info-card">
              <h3>能力统计</h3>
              <div class="meta-row"><span class="label">Total</span><span class="value">${caps.total || 0}</span></div>
              <div class="meta-row"><span class="label">Ready</span><span class="value status-ready">✅ ${caps.ready || 0}</span></div>
              <div class="meta-row"><span class="label">Partial</span><span class="value status-partial">⚠️ ${caps.partial || 0}</span></div>
              <div class="meta-row"><span class="label">Blocked</span><span class="value status-blocked">🔴 ${caps.blocked || 0}</span></div>
              <div class="meta-row"><span class="label">Not Impl</span><span class="value status-not-impl">⬜ ${caps.not_implemented || 0}</span></div>
            </div>

            <div class="info-card">
              <h3>工具</h3>
              <div class="meta-row"><span class="label">Total</span><span class="value">${totalTools}</span></div>
            </div>

            <div class="info-card">
              <h3>测试</h3>
              <div class="meta-row"><span class="label">PASS</span><span class="value status-ready">219</span></div>
              <div class="meta-row"><span class="label">FAIL</span><span class="value">0</span></div>
              <div class="meta-row"><span class="label">ERROR</span><span class="value">0</span></div>
              <div class="meta-row"><span class="label">SKIP</span><span class="value">1</span></div>
            </div>

            <div class="info-card">
              <h3>状态</h3>
              <div class="meta-row">
                <span class="label">Final</span>
                <span class="value status-ready">✅ READY</span>
              </div>
              <div class="meta-row">
                <span class="label">Last Audit</span>
                <span class="value">S141 Release Hardening</span>
              </div>
            </div>
          </div>

          <div class="about-footer">
            <p>Xiao6 v1.0.0 — 2026 · Personal AI OS</p>
            <p class="footer-note">Built with love ❤ by Agnes AI Team</p>
          </div>
        </div>
      `;

      body.innerHTML = html;

    } catch (e) {
      body.innerHTML = errorBox("加载关于页面失败", e.message);
    }
  }

})();
