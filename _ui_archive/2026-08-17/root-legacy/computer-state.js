/*
 * computer-state.js — 小6 Phase 7 Order 1 · Computer World Model 数据投影层（非视觉）
 * ----------------------------------------------------------------------------
 * 职责：把 AppState 的 Computer World Model 子对象投影为可消费的世界状态
 *       {windows, applications, processes, files, projects, browsers, terminals, devices}，
 *       供未来 Overlay（Environment/Info 卡片）/ Agent 运行时消费（Phase 7 Specification §2/§7）。
 * 纪律（严格对齐 galaxy-state.js / readiness §5.2）：
 *   - 本文件绝不触碰 UI / Three.js / WebGL / Overlay；只维护纯数据。
 *   - World Model 是“投影”，不是真相：真相在 OS，本层是带 TTL 的观测缓存派生。
 *   - 数据单向派生自 AppState（AppState 是唯一写入入口；ComputerState 只读）。
 *   - 本层不 emit（不发布任何事件）；它只订阅 AppState 并重建本地投影。
 *   - 观察者只经 onWorldChange() 订阅；外界只经 get*() 读取；无任何 set/apply 写入口
 *     （禁止模块直接修改状态 / 私有事件 / 旁路更新）。
 * 可在 Node 中单测（不依赖 window）。Phase 7 Order 1 不接入真实 Windows API、
 * 不实现任何动作能力，仅建立数据结构 + 投影 + 测试 mock provider。
 */
(function (global) {
  'use strict';
  var AppState = global.AppState;

  // —— 8 个世界集合，顺序即投影标签 ——
  var COLLS = ['windows', 'applications', 'processes', 'files',
               'projects', 'browsers', 'terminals', 'devices'];

  // 本地投影（与 AppState.computer 同构；AppState 变更时整体重拉，保持单向派生）
  var data = {
    windows: {}, applications: {}, processes: {}, files: {},
    projects: {}, browsers: {}, terminals: {}, devices: {}
  };
  var subs = [];

  // 从 AppState 单向拉取（投影，非复制写入逻辑）
  function pull() {
    var src = AppState.getComputer();
    if (!src) return;
    for (var i = 0; i < COLLS.length; i++) {
      var c = COLLS[i];
      if (src[c]) data[c] = src[c];
    }
  }

  function notify(evt) {
    for (var i = 0; i < subs.length; i++) subs[i](data, evt);
  }

  // 订阅 AppState 全事件，保持世界数据同步（只读投影）
  var unsub = AppState.subscribe('*', function (e) { pull(); notify(e); });
  pull();

  function list(coll) {
    var m = data[coll];
    return Object.keys(m).map(function (k) { return m[k]; });
  }

  var API = {
    // —— 整世界快照 ——
    getWorld: function () { return data; },

    // —— 各集合列表投影 ——
    getWindows:      function () { return list('windows'); },
    getApplications: function () { return list('applications'); },
    getProcesses:    function () { return list('processes'); },
    getFiles:        function () { return list('files'); },
    getProjects:     function () { return list('projects'); },
    getBrowsers:     function () { return list('browsers'); },
    getTerminals:    function () { return list('terminals'); },
    getDevices:      function () { return list('devices'); },

    // —— 单实体查询 ——
    getWindow:      function (id) { return data.windows[id] || null; },
    getApplication: function (id) { return data.applications[id] || null; },
    getProcess:     function (id) { return data.processes[String(id)] || null; },
    getFile:        function (path) { return data.files[path] || null; },
    getProject:     function (id) { return data.projects[id] || null; },
    getBrowser:     function (id) { return data.browsers[id] || null; },
    getTerminal:    function (id) { return data.terminals[id] || null; },
    getDevice:      function (id) { return data.devices[id] || null; },

    // —— 派生查询（投影层可承载轻量派生，不触达 OS）——
    getFocusedWindow: function () {
      var ws = data.windows;
      for (var k in ws) {
        if (Object.prototype.hasOwnProperty.call(ws, k) && ws[k].isFocused) return ws[k];
      }
      return null;
    },
    getRunningApplications: function () {
      return list('applications').filter(function (a) { return a.state === 'Running'; });
    },
    getRunningProcesses: function () {
      return list('processes').filter(function (p) { return p.state === 'Running'; });
    },

    // —— 订阅（只读观察；无写入口）——
    onWorldChange: function (cb) {
      subs.push(cb);
      return function () {
        var i = subs.indexOf(cb);
        if (i >= 0) subs.splice(i, 1);
      };
    },

    _unsub: unsub
  };

  global.ComputerState = API;
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
})(typeof window !== 'undefined' ? window : globalThis);
