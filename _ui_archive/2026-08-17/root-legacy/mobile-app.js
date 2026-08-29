/* 小6 · 移动伴随端逻辑（P13 前端消费层）
 * 三面板：简报 / 提醒 / 对话；复用 device-client.js 自注册设备；
 * feature 关闭时优雅降级（显示未启用提示，禁用写操作）。
 * 端点契约与 server.py 的 _handle_mobile_* / _handle_cross_device_status 对齐。
 */
(function () {
  "use strict";

  var $ = function (id) { return document.getElementById(id); };

  function show(el) { if (el) el.classList.remove("hidden"); }
  function hide(el) { if (el) el.classList.add("hidden"); }

  var toastTimer = null;
  function toast(msg) {
    // Step[3] 兼容守卫：若主窗 OverlayManager 在场则路由统一 toast；
    // 移动端独立壳默认不加载 overlay-manager.js，故回退旧 show/hide 行为（零范围扩展）。
    if (window.OverlayManager && typeof window.OverlayManager.toast === 'function') {
      window.OverlayManager.toast({ type: 'info', message: msg, legacyDismissMs: 2600 });
      return;
    }
    var t = $("toast");
    if (!t) return;
    t.textContent = msg;
    show(t);
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { hide(t); }, 2600);
  }

  function banner(msg) {
    var b = $("banner");
    if (!b) return;
    b.textContent = msg;
    show(b);
  }

  function isDisabled(res) {
    return res.status === 404 && res.data && res.data.disabled === true;
  }

  async function api(path, opts) {
    try {
      var r = await fetch(path, opts);
      var data = await r.json().catch(function () { return {}; });
      return { ok: r.ok, status: r.status, data: data };
    } catch (e) {
      return { ok: false, status: 0, data: {}, error: String(e) };
    }
  }

  // ---- 简报 ----
  async function loadBriefing() {
    var body = $("briefing-body");
    if (!body) return;
    var res = await api("/api/mobile/briefing", { method: "GET" });
    if (res.status === 404 || (res.data && res.data.enabled === false)) {
      banner("移动伴随端未启用：请在桌面端开启 FEATURE_MOBILE_COMPANION 后刷新。");
      body.innerHTML = "<p class='muted'>功能未启用</p>";
      return;
    }
    if (!res.ok) {
      body.innerHTML = "<p class='muted'>简报加载失败</p>";
      return;
    }
    var b = res.data.briefing || {};
    var html = "";
    if (b.greeting) html += "<p class='greeting'>" + esc(b.greeting) + "</p>";
    if (b.weather && b.weather.temp !== undefined) {
      html += "<p class='weather'>" + esc(String(b.weather.temp)) + "° " + esc(b.weather.desc || "") + "</p>";
    }
    var rems = (b.reminders || []).filter(function (r) { return r && r.content; });
    if (rems.length) {
      html += "<ul class='list'>";
      rems.forEach(function (r) {
        html += "<li>" + esc(r.content) +
          (r.due ? " <span class='muted'>· " + esc(r.due) + "</span>" : "") + "</li>";
      });
      html += "</ul>";
    }
    body.innerHTML = html || "<p class='muted'>今天空空如也</p>";
    renderReminders(rems);
  }

  function renderReminders(rems) {
    var list = $("reminder-list");
    if (!list) return;
    list.innerHTML = "";
    (rems || []).forEach(function (r) {
      if (!r || !r.content) return;
      var li = document.createElement("li");
      li.textContent = r.content + (r.due ? " · " + r.due : "");
      list.appendChild(li);
    });
  }

  // ---- 跨端状态徽标 ----
  async function loadSyncBadge() {
    var badge = $("sync-badge");
    if (!badge) return;
    var res = await api("/api/cross-device/status", { method: "GET" });
    if (res.data && res.data.enabled === true && res.data.total > 0) {
      badge.textContent = "桌面在线";
      show(badge);
    } else {
      hide(badge);
    }
  }

  // ---- 提醒写 ----
  async function submitReminder(content) {
    var res = await api("/api/mobile/reminder", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: content }),
    });
    if (isDisabled(res)) {
      banner("提醒功能未启用：请开启 FEATURE_MOBILE_COMPANION。");
      return;
    }
    if (res.ok && res.data && res.data.ok) {
      toast("已添加提醒");
      var list = $("reminder-list");
      if (list) {
        var li = document.createElement("li");
        li.textContent = content;
        list.appendChild(li);
      }
    } else {
      toast("添加失败");
    }
  }

  // ---- 对话接力 ----
  async function submitChat(message) {
    var log = $("chat-log");
    if (log) {
      var mine = document.createElement("div");
      mine.className = "bubble mine";
      mine.textContent = message;
      log.appendChild(mine);
      log.scrollTop = log.scrollHeight;
    }
    var res = await api("/api/mobile/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: message }),
    });
    if (isDisabled(res)) {
      banner("对话接力未启用：请开启 FEATURE_MOBILE_COMPANION。");
      return;
    }
    var reply = document.createElement("div");
    reply.className = "bubble sys";
    reply.textContent = (res.ok && res.data && res.data.ok)
      ? "已接力到桌面端处理"
      : "接力失败，请重试";
    if (log) { log.appendChild(reply); log.scrollTop = log.scrollHeight; }
  }

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  // ---- 面板切换 ----
  function bindTabs() {
    var tabs = document.querySelectorAll(".tab");
    tabs.forEach(function (tab) {
      tab.addEventListener("click", function () {
        tabs.forEach(function (t) { t.classList.remove("active"); });
        tab.classList.add("active");
        var target = tab.getAttribute("data-target");
        document.querySelectorAll(".panel").forEach(function (p) { hide(p); });
        var panel = $("panel-" + target);
        if (panel) show(panel);
      });
    });
  }

  function registerSW() {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("sw.js").catch(function () { /* 忽略 */ });
    }
  }

  function bindForms() {
    var rf = $("reminder-form");
    if (rf) rf.addEventListener("submit", function (e) {
      e.preventDefault();
      var inp = $("reminder-input");
      var v = (inp.value || "").trim();
      if (!v) return;
      submitReminder(v);
      inp.value = "";
    });
    var cf = $("chat-form");
    if (cf) cf.addEventListener("submit", function (e) {
      e.preventDefault();
      var inp = $("chat-input");
      var v = (inp.value || "").trim();
      if (!v) return;
      submitChat(v);
      inp.value = "";
    });
  }

  function init() {
    bindTabs();
    bindForms();
    registerSW();
    loadBriefing();
    loadSyncBadge();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
