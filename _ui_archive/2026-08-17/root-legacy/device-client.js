#!/usr/bin/env - 2>/dev/null; true
/*
 * 小6 · 多端 Web 客户端（P4-D R1）
 * 每个打开小6前端的「端」（桌面 Electron / 任意浏览器）在加载时自注册为一个设备，
 * 并持续心跳，使后端 /api/devices 能呈现「多端在线」状态，为多端协同打底。
 * - 设备 ID 持久化在 localStorage，刷新/重开保持稳定身份。
 * - 后端 FEATURE_MULTI_DEVICE=false 时端点返回 404 disabled，本模块自动静默停用。
 * - 非本机访问受 REMOTE_ACCESS_TOKEN 门控（由 server._remote_gate 统一处理）。
 */
(function () {
  "use strict";
  var KEY = "zz_device_id";

  function getDeviceId() {
    var id = null;
    try { id = localStorage.getItem(KEY); } catch (e) { id = null; }
    if (!id) {
      id = "web-" + Math.random().toString(36).slice(2, 10) + Date.now().toString(36);
      try { localStorage.setItem(KEY, id); } catch (e) { /* 隐私模式忽略 */ }
    }
    return id;
  }

  function platformName() {
    var ua = navigator.userAgent || "";
    if (/Electron/i.test(ua)) return "桌面客户端";
    if (/Android/i.test(ua)) return "Android 浏览器";
    if (/iPhone|iPad|iPod/i.test(ua)) return "iOS 浏览器";
    if (/Mac/i.test(ua)) return "Mac 浏览器";
    if (/Windows/i.test(ua)) return "Windows 浏览器";
    if (/Linux/i.test(ua)) return "Linux 浏览器";
    return "Web 客户端";
  }

  function post(payload) {
    return fetch("/api/devices", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  }

  async function register() {
    var id = getDeviceId();
    try {
      var r = await post({
        device_id: id,
        name: platformName(),
        meta: { ua: navigator.userAgent, ts: Date.now() },
      });
      // 404 + disabled => 多端同步未启用，静默停用
      if (r.status === 404) return false;
      return true;
    } catch (e) {
      return false;
    }
  }

  async function heartbeat() {
    try {
      await post({ device_id: getDeviceId(), heartbeat: true });
    } catch (e) { /* 网络抖动忽略 */ }
  }

  window.addEventListener("load", async function () {
    var ok = await register();
    if (!ok) return;
    heartbeat();
    setInterval(heartbeat, 30000);
  });
})();
