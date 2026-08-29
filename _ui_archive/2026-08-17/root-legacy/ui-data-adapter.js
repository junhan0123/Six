/* =============================================================================
 * ui-data-adapter.js · P0-B Real Data Activation
 * -----------------------------------------------------------------------------
 * 职责：把 REST 快照（只读）投影到首页真实信息模块（NOW / MEMORY / KNOWLEDGE）。
 *
 * 纪律（P0-B 红线）：
 *  - 只读：仅 GET 快照 +（可选）消费既有 SSE 事件；不发起任何写请求。
 *  - 不修改内部状态：本适配器**绝不**调用 AppState 的 set/update/merge 等写入 API，
 *    只把数据写到专用 DOM 容器（#osReadout 的三个 cell）。AppState 仍是 Runtime 的单一事实源。
 *  - 不新增事件契约：不 publish 任何领域事件；仅订阅既有 GOAL_ 与 MEMORY_ 事件以做轻量刷新。
 *  - 不依赖 Agent Runtime / EventBus 内部实现，仅走 HTTP + 既有事件名。
 *
 * 这是 UI v2「UI Data Adapter」层的第一个实例：REST snapshot → UI 展示。
 * ========================================================================== */
(function () {
  "use strict";

  var READOUT = "#osReadout";
  var REFRESH_MS = 30000; // 兜底轮询；既有事件触发时立即刷新，不依赖此间隔
  var timer = null;
  var started = false;

  /* ---------- 工具：安全的文本写入（防 XSS / 防内部状态污染） ---------- */
  function setText(el, text) {
    if (!el) return;
    el.textContent = text == null ? "" : String(text);
  }
  function el(id) {
    return document.querySelector(id);
  }

  /* ---------- 取数：并行拉取三个只读端点 ---------- */
  function getJSON(url) {
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (!r.ok) throw new Error(url + " -> " + r.status);
      return r.json();
    });
  }

  /* ---------- NOW：当前进行中目标 ---------- */
  function renderGoal(goals) {
    var titleEl = el("#osrGoalTitle");
    var metaEl = el("#osrGoalMeta");
    var list = Array.isArray(goals) ? goals : [];
    // 优先展示 active；其次任何未归档目标；都没有则提示
    var active = list.filter(function (g) { return g.status === "active"; });
    var pick = active[0] || list.filter(function (g) { return g.status !== "archived"; })[0];
    if (!pick) {
      setText(titleEl, "暂无进行中目标");
      setText(metaEl, "向小6说一句话即可立目标");
      return;
    }
    setText(titleEl, pick.title || ("目标 #" + pick.id));
    var parts = [];
    if (pick.priority) parts.push(pick.priority);
    if (typeof pick.progress === "number") parts.push("进度 " + pick.progress + "%");
    if (pick.due_date) parts.push("截止 " + pick.due_date);
    setText(metaEl, parts.join(" · "));
  }

  /* ---------- MEMORY：最近记忆摘要 ---------- */
  function renderMemory(mem) {
    var titleEl = el("#osrMemTitle");
    var metaEl = el("#osrMemMeta");
    // /api/memories 返回数组（get_memories）；也可能为空
    var list = Array.isArray(mem) ? mem : [];
    setText(titleEl, list.length ? ("最近记忆 " + list.length + " 条") : "暂无记忆");
    // 取最新一条的摘要/内容预览
    var latest = list[0];
    var preview = "";
    if (latest) {
      preview = latest.summary || latest.content || latest.value || "";
      if (typeof preview === "string" && preview.length > 48) {
        preview = preview.slice(0, 48) + "…";
      }
    }
    setText(metaEl, preview || (list.length ? "已为你长期记忆" : "对话后自动沉淀"));
  }

  /* ---------- KNOWLEDGE：知识库状态 ---------- */
  function renderKnowledge(payload) {
    var titleEl = el("#osrKnoTitle");
    var metaEl = el("#osrKnoMeta");
    // /api/knowledge 返回 { docs:[...], stats:{...} }
    var docs = (payload && payload.docs) || [];
    var stats = (payload && payload.stats) || {};
    var catCount = stats.category_count != null ? stats.category_count
      : (stats.categories ? Object.keys(stats.categories).length : null);
    setText(titleEl, "知识库 " + docs.length + " 篇");
    var meta = [];
    if (catCount != null) meta.push(catCount + " 类");
    if (stats.total != null) meta.push(stats.total + " 节点");
    setText(metaEl, meta.join(" · ") || "本地优先 · 隐私安全");
  }

  /* ---------- P1-2 AI Core Identity：能力摘要（复用同一组快照，无新增数据源） ---------- */
  function renderSummary(goals, mem, knowledge) {
    var g = Array.isArray(goals) ? goals : [];
    var m = Array.isArray(mem) ? mem : [];
    var docs = (knowledge && knowledge.docs) || [];
    setText("#csGoals", String(g.length));
    setText("#csMemory", String(m.length));
    setText("#csKnowledge", String(docs.length));
  }

  /* ---------- 一次性拉取并渲染 ---------- */
  function refresh() {
    var root = el(READOUT);
    if (!root) return;
    Promise.all([
      getJSON("/api/goals?status=active&limit=20").catch(function () { return []; }),
      getJSON("/api/memories?limit=10").catch(function () { return []; }),
      getJSON("/api/knowledge").catch(function () { return { docs: [], stats: {} }; }),
    ]).then(function (res) {
      renderGoal(res[0]);
      renderMemory(res[1]);
      renderKnowledge(res[2]);
      renderSummary(res[0], res[1], res[2]);
      root.setAttribute("data-loaded", "1");
    }).catch(function (e) {
      // 失败时保持上一次渲染，不抛错、不打断首页
      if (window.console) console.warn("[ui-data-adapter] 拉取失败（已忽略）:", e && e.message);
    });
  }

  /* ---------- 既事件驱动（不新增契约）：监听既有 GOAL_ 与 MEMORY_ 事件 ---------- */
  function bindEvents() {
    // zzEvents 是既有事件总线（zz-events.js 单一来源），仅订阅、不发布
    var bus = window.zzEvents || (window.AppState && window.AppState.events);
    if (bus && typeof bus.on === "function") {
      ["GOAL_CREATED", "GOAL_UPDATED", "GOAL_COMPLETED", "GOAL_PLANNED",
       "MEMORY_CREATED", "MEMORY_STORED", "MEMORY_LINKED", "MEMORY_UPDATED"
      ].forEach(function (name) {
        try { bus.on(name, refresh); } catch (e) { /* 忽略未支持事件 */ }
      });
    }
  }

  /* ---------- 启动：DOM 就绪后挂载 ---------- */
  function start() {
    if (started) return;
    var root = el(READOUT);
    if (!root) return; // 首页不存在则跳过（不报错）
    started = true;
    refresh();
    bindEvents();
    // 兜底轮询，确保即使没有事件也能保持真实数据新鲜
    if (REFRESH_MS > 0) timer = setInterval(refresh, REFRESH_MS);
    // 页面重新可见时立即刷新
    document.addEventListener("visibilitychange", function () {
      if (!document.hidden) refresh();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
