/*
 * capability-registry.js — 小6 Phase 7 Order 2 · 电脑能力注册表（前端镜像）
 * 与后端 capability_registry.py 严格对齐：声明能力目录 + 风险 → Policy Engine 层级映射。
 * 纪律：前端只做“规划/校验/预览”，权威裁决在后端 Policy Engine；本文件不含任何 OS 调用。
 */
(function (global) {
  'use strict';

  var AUTO = 'auto', CONFIRM = 'confirm';
  // 风险 → Policy Engine 层级（复用既有词汇，不新建风险系统）
  var RISK_TIER = { LOW: AUTO, MEDIUM: CONFIRM };

  var CAPS = {
    // LOW：只读 / 无副作用
    read_file:       { id: 'read_file',       label: '读取文件',   risk: 'LOW',      target_kind: 'file',       expected_effect: '返回文件内容预览（不修改）' },
    capture_screen:   { id: 'capture_screen',   label: '截取屏幕',   risk: 'LOW',      target_kind: 'screen',     expected_effect: '返回当前屏幕截图（不修改）' },
    get_window_info:  { id: 'get_window_info',  label: '获取窗口信息', risk: 'LOW',    target_kind: 'window',     expected_effect: '返回指定窗口的几何/状态信息' },
    list_process:     { id: 'list_process',     label: '列举进程',   risk: 'LOW',      target_kind: 'process',    expected_effect: '返回当前进程列表（只读）' },
    // MEDIUM：有界面副作用，需确认
    open_application: { id: 'open_application', label: '打开应用',   risk: 'MEDIUM',   target_kind: 'application', expected_effect: '启动指定应用（会切换焦点/占用资源）' },
    focus_window:     { id: 'focus_window',     label: '聚焦窗口',   risk: 'MEDIUM',   target_kind: 'window',     expected_effect: '把指定窗口提到前台（会改变用户焦点）' },
    browser_navigate: { id: 'browser_navigate', label: '浏览器导航', risk: 'MEDIUM',   target_kind: 'browser',    expected_effect: '在浏览器打开/跳转 URL（有网络与外显副作用）' },
    // 未实现（仅声明占位，Order 3+）
    modify_file:      { id: 'modify_file',      label: '修改文件',   risk: 'HIGH',     target_kind: 'file',       expected_effect: '写入/修改文件内容（破坏性）', implemented: false },
    execute_command:  { id: 'execute_command',  label: '执行命令',   risk: 'HIGH',     target_kind: 'process',    expected_effect: '运行 shell 命令（高危）', implemented: false },
    kill_process:     { id: 'kill_process',     label: '结束进程',   risk: 'HIGH',     target_kind: 'process',    expected_effect: '终止进程（可能丢数据）', implemented: false },
    delete:           { id: 'delete',           label: '删除',       risk: 'CRITICAL', target_kind: 'any',       expected_effect: '删除文件/资源（不可逆）', implemented: false },
    system:           { id: 'system',           label: '系统操作',   risk: 'CRITICAL', target_kind: 'system',     expected_effect: '系统级变更（重启/配置）', implemented: false },
    network:          { id: 'network',          label: '网络操作',   risk: 'CRITICAL', target_kind: 'network',    expected_effect: '网络级变更（防火墙/代理）', implemented: false }
  };

  function getCapability(id) { return CAPS[id] || null; }
  function isKnown(id) { return Object.prototype.hasOwnProperty.call(CAPS, id); }
  function isImplemented(id) { var c = CAPS[id]; return !!(c && c.implemented !== false); }
  function riskOf(id) { var c = CAPS[id]; return c ? c.risk : 'UNKNOWN'; }
  function tierOf(id) { return RISK_TIER[riskOf(id)] || CONFIRM; }
  function allCapabilities() { return Object.keys(CAPS).map(function (k) { return CAPS[k]; }); }
  function implementedCapabilities() { return Object.keys(CAPS).filter(isImplemented); }
  function lowCapabilities() { return Object.keys(CAPS).filter(function (k) { return CAPS[k].risk === 'LOW'; }); }
  function mediumCapabilities() { return Object.keys(CAPS).filter(function (k) { return CAPS[k].risk === 'MEDIUM'; }); }

  var API = {
    RISK_TIER: RISK_TIER,
    getCapability: getCapability,
    isKnown: isKnown,
    isImplemented: isImplemented,
    riskOf: riskOf,
    tierOf: tierOf,
    allCapabilities: allCapabilities,
    implementedCapabilities: implementedCapabilities,
    lowCapabilities: lowCapabilities,
    mediumCapabilities: mediumCapabilities
  };
  global.ZZCapabilities = API;
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
})(typeof window !== 'undefined' ? window : globalThis);
