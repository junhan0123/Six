/*
 * computer-action.js — 小6 Phase 7 Order 2 · ComputerAction 数据模型（前端）
 * 与后端 computer_action.ComputerAction 字段契约严格一致。
 * 纯数据，不含 OS / 网络调用。
 */
(function (global) {
  'use strict';
  var ZZCap = global.ZZCapabilities;

  function ComputerAction(capability, target, parameters, opts) {
    opts = opts || {};
    if (!capability) throw new Error('capability 必填');
    var cap = ZZCap ? ZZCap.getCapability(capability) : null;
    if (!cap) throw new Error('未知能力（未注册到 Capability Registry）: ' + capability);
    this.actionId = opts.actionId || ('ca_' + Math.random().toString(36).slice(2) + Date.now().toString(36));
    this.capability = capability;
    this.target = target || '';
    this.parameters = parameters || {};
    this.risk = opts.risk || cap.risk;
    this.expectedEffect = opts.expectedEffect || cap.expected_effect || '';
    this.permissionDecision = opts.permissionDecision || null; // auto|confirm|block|deny
    this.result = (opts.result !== undefined) ? opts.result : null;
    this.goalId = opts.goalId || null;
    this.status = opts.status || 'planned'; // planned|called|done|failed|denied|verified|unverified
    this.decisionReason = opts.decisionReason || null;
    this.verified = (opts.verified !== undefined) ? opts.verified : null;     // true|false|null
    this.verificationDetail = (opts.verificationDetail !== undefined) ? opts.verificationDetail : null;
    this.createdAt = opts.createdAt || Date.now();
  }

  ComputerAction.prototype.toDict = function () {
    return {
      actionId: this.actionId, capability: this.capability, target: this.target,
      parameters: this.parameters, risk: this.risk, expectedEffect: this.expectedEffect,
      permissionDecision: this.permissionDecision, result: this.result, goalId: this.goalId,
      status: this.status, decisionReason: this.decisionReason,
      verified: this.verified, verificationDetail: this.verificationDetail,
      createdAt: this.createdAt
    };
  };

  ComputerAction.fromDict = function (d) {
    var a = new ComputerAction(d.capability, d.target, d.parameters, {
      actionId: d.actionId, risk: d.risk, expectedEffect: d.expectedEffect,
      permissionDecision: d.permissionDecision, result: d.result, goalId: d.goalId, status: d.status,
      verified: d.verified, verificationDetail: d.verificationDetail
    });
    a.decisionReason = d.decisionReason || null;
    a.createdAt = d.createdAt || a.createdAt;
    return a;
  };

  global.ZZComputerAction = ComputerAction;
  if (typeof module !== 'undefined' && module.exports) module.exports = ComputerAction;
})(typeof window !== 'undefined' ? window : globalThis);
