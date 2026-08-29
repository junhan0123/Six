/*
 * zz-events.js — 小6 Phase 6 · 单一事件名来源 (Single Source of Truth)
 * ----------------------------------------------------------------------------
 * 依据：readiness §5.1（15 个冻结核心事件）+ Order 1 第一批新增 TASK_COMPLETED。
 * 纪律（R1）：事件名必须唯一来源。任何模块禁止定义自己的事件名副本；
 *           后端 eventbus.publish_domain 与前端的 ZZ_EVENTS 必须逐字一致。
 * 本文件不实现任何视觉/网络逻辑，只定义事件名常量 + 校验。
 */
(function (global) {
  'use strict';

  // —— readiness §5.1 冻结的 15 个核心事件 ——
  var EVENTS = {
    GOAL_CREATED:        'GOAL_CREATED',
    GOAL_UPDATED:        'GOAL_UPDATED',
    GOAL_PLANNED:        'GOAL_PLANNED',
    GOAL_STARTED:        'GOAL_STARTED',
    GOAL_RUNNING:        'GOAL_RUNNING',
    GOAL_COMPLETED:      'GOAL_COMPLETED',
    GOAL_FAILED:         'GOAL_FAILED',
    AGENT_CREATED:       'AGENT_CREATED',
    AGENT_STARTED:       'AGENT_STARTED',
    AGENT_THINKING:      'AGENT_THINKING',
    AGENT_WORKING:       'AGENT_WORKING',
    AGENT_WAITING:       'AGENT_WAITING',
    AGENT_COMPLETED:     'AGENT_COMPLETED',
    AGENT_FAILED:        'AGENT_FAILED',
    TASK_CREATED:        'TASK_CREATED',
    TASK_STARTED:        'TASK_STARTED',
    TASK_RUNNING:        'TASK_RUNNING',
    TASK_COMPLETED:      'TASK_COMPLETED',
    TASK_FAILED:         'TASK_FAILED',
    TOOL_CALLED:         'TOOL_CALLED',
    TOOL_DONE:           'TOOL_DONE',
    MEMORY_UPDATED:      'MEMORY_UPDATED',
    MEMORY_CREATED:      'MEMORY_CREATED',
    MEMORY_STORED:       'MEMORY_STORED',
    MEMORY_LINKED:       'MEMORY_LINKED',
    MEMORY_ARCHIVED:     'MEMORY_ARCHIVED',
    // —— Order 5：Intent Gateway 生命周期（User Intent → Goal Decision Engine → Goal）——
    INTENT_RECEIVED:          'INTENT_RECEIVED',
    INTENT_ANALYZING:         'INTENT_ANALYZING',
    INTENT_CLASSIFIED:        'INTENT_CLASSIFIED',
    INTENT_ACCEPTED:          'INTENT_ACCEPTED',
    INTENT_REJECTED:          'INTENT_REJECTED',
    INTENT_CONVERTED_TO_GOAL: 'INTENT_CONVERTED_TO_GOAL',
    NOTIFICATION_RAISED: 'NOTIFICATION_RAISED',
    REFLECTING:          'REFLECTING',
    ERROR_OCCURRED:      'ERROR_OCCURRED',
    WORKSPACE_SWITCHED:  'WORKSPACE_SWITCHED',
    FOCUS_CHANGED:       'FOCUS_CHANGED',
    STATE_SYNC:          'STATE_SYNC',
    // —— Phase 7 Order 1：Computer World Model（只读世界观测事件；动作能力在 Order 2+）——
    COMPUTER_WORLD_SYNC:   'COMPUTER_WORLD_SYNC',
    WINDOW_OPENED:         'WINDOW_OPENED',
    WINDOW_CLOSED:         'WINDOW_CLOSED',
    WINDOW_FOCUSED:        'WINDOW_FOCUSED',
    APP_LAUNCHED:          'APP_LAUNCHED',
    APP_EXITED:            'APP_EXITED',
    PROCESS_SPAWNED:       'PROCESS_SPAWNED',
    PROCESS_TERMINATED:    'PROCESS_TERMINATED',
    FILE_CREATED:          'FILE_CREATED',
    FILE_MODIFIED:         'FILE_MODIFIED',
    FILE_DELETED:          'FILE_DELETED',
    PROJECT_DETECTED:      'PROJECT_DETECTED',
    PROJECT_UPDATED:       'PROJECT_UPDATED',
    BROWSER_NAVIGATED:     'BROWSER_NAVIGATED',
    BROWSER_TAB_OPENED:    'BROWSER_TAB_OPENED',
    BROWSER_TAB_CLOSED:    'BROWSER_TAB_CLOSED',
    TERMINAL_SPAWNED:      'TERMINAL_SPAWNED',
    TERMINAL_EXITED:       'TERMINAL_EXITED',
    DEVICE_STATE_CHANGED:  'DEVICE_STATE_CHANGED',
    // —— Phase 7 Order 2：Computer Action 生命周期（动作能力执行安全层；经 Policy Engine 裁决）——
    COMPUTER_ACTION_PLANNED: 'COMPUTER_ACTION_PLANNED',
    COMPUTER_ACTION_CALLED:  'COMPUTER_ACTION_CALLED',
    COMPUTER_ACTION_DONE:    'COMPUTER_ACTION_DONE',
    COMPUTER_ACTION_FAILED:  'COMPUTER_ACTION_FAILED',
    COMPUTER_ACTION_DENIED:  'COMPUTER_ACTION_DENIED',
    COMPUTER_ACTION_VERIFIED:   'COMPUTER_ACTION_VERIFIED',
    COMPUTER_ACTION_UNVERIFIED: 'COMPUTER_ACTION_UNVERIFIED',
    COMPUTER_ACTION_PHASE:      'COMPUTER_ACTION_PHASE',
    // —— Phase 8 Order 1：Screen Capture Foundation（仅采集，不含任何理解/识别）——
    SCREEN_CAPTURED:      'SCREEN_CAPTURED',
    SCREEN_CAPTURE_FAILED: 'SCREEN_CAPTURE_FAILED',
    // —— Phase 8 MVP：Computer Perception（观察层；Vision 绝不控制）——
    //     注：PERCEPTION_FOCUS_CHANGED 为 UIA accessibility focus，与 Phase 6 既有
    //     FOCUS_CHANGED（银河节点聚焦态）命名不同、互不冲突，均为 DOMAIN 单一来源。
    PERCEPTION_SYNC:         'PERCEPTION_SYNC',
    PERCEPTION_UI_UPDATED:   'PERCEPTION_UI_UPDATED',
    PERCEPTION_OCR_UPDATED:  'PERCEPTION_OCR_UPDATED',
    PERCEPTION_VISION_FACT:  'PERCEPTION_VISION_FACT',
    PERCEPTION_FOCUS_CHANGED: 'PERCEPTION_FOCUS_CHANGED'
  };

  // —— Order 1 第一批新增：TASK_RUNNING 的完成态，补足任务生命周期闭环 ——
  // （已并入上方 EVENTS 常量，保持单一来源）

  // 本阶段（Order 1）必须实现 handler 的 8 个事件
  var BATCH_1 = [
    EVENTS.GOAL_CREATED, EVENTS.GOAL_UPDATED, EVENTS.AGENT_STARTED,
    EVENTS.TASK_RUNNING, EVENTS.TASK_COMPLETED, EVENTS.MEMORY_UPDATED,
    EVENTS.ERROR_OCCURRED, EVENTS.STATE_SYNC
  ];

  // Order 2 第二批：Goal 生命周期完整闭环（Created→Started→Running→Completed/Failed）
  var BATCH_2 = [
    EVENTS.GOAL_STARTED, EVENTS.GOAL_RUNNING,
    EVENTS.GOAL_COMPLETED, EVENTS.GOAL_FAILED
  ];

  // Order 3 第三批：Agent + Task 生命周期（Agent→Satellite，Task→Orbit Node）
  var BATCH_3 = [
    EVENTS.AGENT_CREATED, EVENTS.AGENT_STARTED, EVENTS.AGENT_THINKING,
    EVENTS.AGENT_WORKING, EVENTS.AGENT_WAITING, EVENTS.AGENT_COMPLETED,
    EVENTS.AGENT_FAILED, EVENTS.TASK_CREATED, EVENTS.TASK_STARTED,
    EVENTS.TASK_FAILED
  ];

  // Order 4 第四批：Memory 生命周期（Reflection→Memory→Knowledge 贯通统一状态流）
  // 说明：MEMORY_LINKED 取代预留的 KNOWLEDGE_LINKED（单一来源，禁第二套事件）；
  //       REFLECTING 由预留转为本批实现（反思阶段入口事件）。
  var BATCH_4 = [
    EVENTS.MEMORY_CREATED, EVENTS.MEMORY_STORED, EVENTS.MEMORY_LINKED,
    EVENTS.MEMORY_ARCHIVED, EVENTS.REFLECTING
  ];

  // Order 5 第五批：Intent Gateway 生命周期（Command 输入入口→意图识别→Goal）
  // 链路：INTENT_RECEIVED → INTENT_ANALYZING → INTENT_CLASSIFIED
  //      →（INTENT_ACCEPTED | INTENT_REJECTED）→ INTENT_CONVERTED_TO_GOAL → GOAL_CREATED…
  var BATCH_5 = [
    EVENTS.INTENT_RECEIVED, EVENTS.INTENT_ANALYZING, EVENTS.INTENT_CLASSIFIED,
    EVENTS.INTENT_ACCEPTED, EVENTS.INTENT_REJECTED, EVENTS.INTENT_CONVERTED_TO_GOAL
  ];

  // Phase 7 Order 1：Computer World Model 观测事件（只读世界状态；动作事件在 Order 2+）
  var BATCH_7 = [
    EVENTS.COMPUTER_WORLD_SYNC,
    EVENTS.WINDOW_OPENED, EVENTS.WINDOW_CLOSED, EVENTS.WINDOW_FOCUSED,
    EVENTS.APP_LAUNCHED, EVENTS.APP_EXITED,
    EVENTS.PROCESS_SPAWNED, EVENTS.PROCESS_TERMINATED,
    EVENTS.FILE_CREATED, EVENTS.FILE_MODIFIED, EVENTS.FILE_DELETED,
    EVENTS.PROJECT_DETECTED, EVENTS.PROJECT_UPDATED,
    EVENTS.BROWSER_NAVIGATED,     EVENTS.BROWSER_TAB_OPENED, EVENTS.BROWSER_TAB_CLOSED,
    EVENTS.TERMINAL_SPAWNED, EVENTS.TERMINAL_EXITED,
    EVENTS.DEVICE_STATE_CHANGED
  ];

  // Phase 7 Order 2 + Order 3：Computer Action 生命周期事件（动作能力执行安全层；经 Policy Engine 裁决 + 执行后复核）
  var BATCH_7_ACTION = [
    EVENTS.COMPUTER_ACTION_PLANNED,
    EVENTS.COMPUTER_ACTION_CALLED,
    EVENTS.COMPUTER_ACTION_DONE,
    EVENTS.COMPUTER_ACTION_FAILED,
    EVENTS.COMPUTER_ACTION_DENIED,
    EVENTS.COMPUTER_ACTION_VERIFIED,
    EVENTS.COMPUTER_ACTION_UNVERIFIED,
    EVENTS.COMPUTER_ACTION_PHASE
  ];

  // Phase 8 MVP：Computer Perception 感知事件（观察层；Vision 绝不控制）
  var BATCH_8 = [
    EVENTS.PERCEPTION_SYNC,
    EVENTS.PERCEPTION_UI_UPDATED,
    EVENTS.PERCEPTION_OCR_UPDATED,
    EVENTS.PERCEPTION_VISION_FACT,
    EVENTS.PERCEPTION_FOCUS_CHANGED
  ];

  // 已冻结但本阶段仅作为常量保留、handler 在后续 Order 实现（预留，禁同义事件）
  var RESERVED = [
    EVENTS.GOAL_PLANNED, EVENTS.TOOL_CALLED, EVENTS.TOOL_DONE,
    EVENTS.NOTIFICATION_RAISED, EVENTS.WORKSPACE_SWITCHED, EVENTS.FOCUS_CHANGED
  ];

  // —— Phase 6 Hotfix：系统事件命名空间（与 EVENTS 互斥，单一来源，须与后端 eventbus.SYSTEM_EVENT_NAMES 逐字对齐）——
  // 这些事件由前端独立 SSE 监听器（app.js / glance-card.js）消费，承载 telemetry / 主动推送 /
  // 输入信号 / 工具进度 / 面板控制，不属于领域生命周期状态（不进 AppState）。
  var SYSTEM_EVENTS = {
    PROACTIVE:          'proactive',
    SCENE:              'scene',
    MEMORY_REMINDER:    'memory_reminder',
    AGENT_STATE:        'agent_state',
    MODAL:              'modal',
    WAKEWORD_DETECTED:  'wakeword_detected',
    // —— Phase 8 MVP：Perception telemetry / 主动感知提示（类 scene / agent_state）——
    PERCEPTION_ALERT:   'perception_alert',
    PERCEPTION_HEALTH:  'perception_health'
  };

  function isEvent(name) {
    return Object.prototype.hasOwnProperty.call(EVENTS, name);
  }

  function isSystemEvent(name) {
    for (var k in SYSTEM_EVENTS) {
      if (SYSTEM_EVENTS[k] === name) return true;
    }
    return false;
  }

  var API = {
    EVENTS: EVENTS,
    BATCH_1: BATCH_1,
    BATCH_2: BATCH_2,
    BATCH_3: BATCH_3,
    BATCH_4: BATCH_4,
    BATCH_5: BATCH_5,
    BATCH_7: BATCH_7,
    BATCH_7_ACTION: BATCH_7_ACTION,
    BATCH_8: BATCH_8,
    RESERVED: RESERVED,
    SYSTEM_EVENTS: SYSTEM_EVENTS,
    isEvent: isEvent,
    isSystemEvent: isSystemEvent,
    names: function () { return Object.keys(EVENTS); }
  };

  global.ZZ_EVENTS = API;
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
})(typeof window !== 'undefined' ? window : globalThis);
