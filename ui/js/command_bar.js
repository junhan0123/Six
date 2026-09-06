/* =========================================================
   Xiao6 Command Bar & Interaction Status — S144.2
   接入 /api/interaction/parse 与 /api/interaction/activity
   红线：仅前端展示，不修改 Runtime / Planner / Tool Execution
   ========================================================= */
(function () {
  "use strict";

  /* ---------------- 状态机 ---------------- */
  const STATE_IDLE = "idle";
  const STATE_THINKING = "thinking";
  const STATE_UNDERSTANDING = "understanding";
  const STATE_READY = "ready";

  let _currentState = STATE_IDLE;
  let _currentIntent = null;

  /* ---------------- DOM 元素 ---------------- */
  function getCommandBar() {
    return document.getElementById("commandBar");
  }
  function getCommandInput() {
    return document.getElementById("commandInput");
  }
  function getCommandSend() {
    return document.getElementById("commandSend");
  }
  function getCommandStatus() {
    return document.getElementById("commandStatus");
  }
  function getCommandIntent() {
    return document.getElementById("commandIntent");
  }

  /* ---------------- 状态显示 ---------------- */
  function updateCommandStatus(state, intent) {
    const statusEl = getCommandStatus();
    const intentEl = getCommandIntent();
    if (!statusEl) return;

    _currentState = state;
    _currentIntent = intent;

    const labels = {
      [STATE_IDLE]: "输入指令，让小6帮你...",
      [STATE_THINKING]: "小6正在理解...",
      [STATE_UNDERSTANDING]: "识别意图...",
      [STATE_READY]: "准备执行"
    };
    statusEl.textContent = labels[state] || state;
    statusEl.className = "command-status " + state;

    if (intentEl) {
      intentEl.textContent = intent ? ("意图：" + intent) : "";
    }
  }

  /* ---------------- 解析请求 ---------------- */
  async function parseInteraction(text) {
    const input = getCommandInput();
    const sendBtn = getCommandSend();
    if (!text || !text.trim()) return null;

    // 设置状态
    updateCommandStatus(STATE_THINKING);
    if (sendBtn) sendBtn.disabled = true;
    if (input) input.disabled = true;

    try {
      // 第一步：发送到交互层
      updateCommandStatus(STATE_UNDERSTANDING);
      
      const resp = await fetch("/api/interaction/parse", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: text.trim() })
      });

      if (!resp.ok) {
        throw new Error("HTTP " + resp.status);
      }

      const data = await resp.json();
      
      // 提取意图信息
      let intentType = "chat";
      if (data.data && data.data.intent) {
        intentType = data.data.intent.intent_type || "chat";
      }

      updateCommandStatus(STATE_READY, intentType);
      
      // 记录活动
      trackActivity("parse", text.trim(), intentType, data);
      
      return data;

    } catch (err) {
      console.error("[CommandBar] 解析失败:", err);
      updateCommandStatus(STATE_IDLE);
      showToast("解析失败，请重试", true);
      return null;
    } finally {
      if (sendBtn) sendBtn.disabled = false;
      if (input) input.disabled = false;
    }
  }

  /* ---------------- 活动追踪 ---------------- */
  function trackActivity(type, text, intent, data) {
    fetch("/api/interaction/activity")
      .then(r => r.json())
      .then(result => {
        // 刷新活动列表
        renderActivityPanel(result.activities || []);
      })
      .catch(err => console.error("[CommandBar] 活动记录失败:", err));
  }

  /* ---------------- 渲染活动面板 ---------------- */
  function renderActivityPanel(activities) {
    const panel = document.getElementById("activityPanel");
    if (!panel) return;

    if (!activities || activities.length === 0) {
      panel.innerHTML = '<div class="activity-empty">暂无交互活动</div>';
      return;
    }

    const html = activities.map(act => {
      const icons = {
        "parse": "🔍",
        "intent": "🎯",
        "analysis": "📊",
        "command": "⚡"
      };
      const icon = icons[act.type] || "•";
      const statusCls = act.status === "completed" ? "done" : (act.status === "running" ? "run" : "");
      return `<div class="activity-item ${statusCls}">
        <span class="activity-icon">${icon}</span>
        <div class="activity-content">
          <div class="activity-title">${escapeHtml(act.title)}</div>
          <div class="activity-meta">${act.intent_type || act.type} · ${act.relative_time || ""}</div>
        </div>
      </div>`;
    }).join("");

    panel.innerHTML = html;
  }

  /* ---------------- 加载活动列表 ---------------- */
  async function loadActivities() {
    try {
      const resp = await fetch("/api/interaction/activity");
      if (!resp.ok) return;
      const data = await resp.json();
      renderActivityPanel(data.activities || []);
    } catch (err) {
      console.error("[CommandBar] 加载活动失败:", err);
    }
  }

  /* ---------------- 绑定事件 ---------------- */
  function bindCommandBar() {
    const input = getCommandInput();
    const send = getCommandSend();
    if (!input || !send) return;

    // 回车发送
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        const text = input.value.trim();
        if (text) {
          parseInteraction(text);
          input.value = "";
        }
      }
    });

    // 点击发送
    send.addEventListener("click", () => {
      const text = input.value.trim();
      if (text) {
        parseInteraction(text);
        input.value = "";
      }
    });

    // 定期刷新活动列表
    loadActivities();
    setInterval(loadActivities, 30000); // 每30秒刷新
  }

  /* ---------------- 工具函数 ---------------- */
  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text || "";
    return div.innerHTML;
  }

  function showToast(msg, isErr) {
    const t = document.getElementById("toast");
    if (!t) return;
    t.textContent = msg;
    t.className = "toast show" + (isErr ? " err" : "");
    setTimeout(() => { t.className = "toast"; }, isErr ? 4200 : 2400);
  }

  /* ---------------- 初始化 ---------------- */
  function init() {
    // 等待 DOM 加载
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", bindCommandBar);
    } else {
      bindCommandBar();
    }
  }

  // 导出
  window.Xiao6CommandBar = {
    init: init,
    parse: parseInteraction,
    updateStatus: updateCommandStatus,
    loadActivities: loadActivities
  };

  // 自动初始化
  init();
})();