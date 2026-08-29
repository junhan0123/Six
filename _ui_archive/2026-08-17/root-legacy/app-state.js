/*
 * app-state.js — 小6 Phase 6 · 统一前端状态核心 (App State Layer)
 * ----------------------------------------------------------------------------
 * 职责：Goal / Agent / Task / Galaxy Node / Execution 状态的唯一事实来源 (single source of truth)。
 * 纪律（readiness §2 / R3）：组件内部私有状态不得成为事实来源；UI 只经 subscribe() 观察，
 *       只经 applyEvent() 写入。所有写入都来自事件（Backend→Frontend Bridge 或本地合成）。
 * 设计依据：readiness §4（运行时冻结）/ §6（领域对象映射）/ §5（事件契约）。
 * 本文件不依赖 DOM / Three.js / 网络 —— 纯状态机，可在 Node 中单测。
 */
(function (global) {
  'use strict';
  var ZZ = global.ZZ_EVENTS;

  // —— 统一状态树 ——
  var state = {
    goals:       {},                 // goalId  -> Goal
    agents:      {},                 // agentId -> Agent
    tasks:       {},                 // taskId  -> Task
    galaxyNodes: {},                 // nodeId  -> GalaxyNode {id,type,state,interaction,relation,metadata}
    memory:      {},                 // memoryId-> Memory（Order 1 起；Order 4 补全生命周期）
    knowledge:   {},                 // knowledgeId -> Knowledge（Order 4 新增，与 memory 独立）
    intents:     {},                 // intentId -> Intent（Order 5 新增，与 Goal/Agent/Task/Memory 五态独立）
    execution:   { errors: [], lastRun: null, currentMemoryId: null, reflecting: false }, // Order 4 扩展
    workspace:   { currentId: null },
    focus:       { capability: null, id: null },
    // —— Phase 7 Order 1：Computer World Model 子树（只读世界投影；由观测事件经 reducer 写入，
    //     由 ComputerState 纯投影消费。不在此存放任何 OS 真相，真相在 OS，此处仅为带 TTL 的观测缓存）——
    computer: {
      windows: {}, applications: {}, processes: {}, files: {},
      projects: {}, browsers: {}, terminals: {}, devices: {},
      // —— Phase 7 Order 2：Computer Action 生命周期投影（只读派生自 COMPUTER_ACTION_* 事件；
      //     由 Permission Guard 经 applyEvent 写入；不存放任何执行逻辑/OS 真相）——
      actions: {},
      // —— Phase 21：四态相位（观察/规划/执行/验证；AI Core 状态表达用）——
      phase: 'idle',          // idle | observe | plan | execute | verify
      phaseLabel: ''          // 中文标签（"正在观察屏幕" 等）
    }
  };

  var observers = [];

  function now() { return Date.now(); }

  // —— 状态变更广播（同步，订阅者异常不阻断总线）——
  function emit(name, payload) {
    for (var i = 0; i < observers.length; i++) {
      var o = observers[i];
      if (o.type === name || o.type === '*') {
        try { o.fn(payload, name); } catch (e) { /* 隔离订阅者异常 */ }
      }
    }
  }

  // —— Galaxy Node 注册（任务 #4：数据消费能力，非视觉）——
  function upsertNode(id, type, runtimeState, relation, metadata) {
    var prev = state.galaxyNodes[id];
    var node = {
      id: id,
      type: type,
      state: runtimeState,
      interaction: (prev && prev.interaction) || 'idle',
      relation: relation || {},
      metadata: metadata || {}
    };
    state.galaxyNodes[id] = node;
    return node;
  }

  // —— 状态机 reducer：仅第一批 8 事件；其余预留，不在此阶段实现 ——
  var reducers = {};

  reducers[ZZ.EVENTS.GOAL_CREATED] = function (p) {
    if (!p || !p.goalId) return;
    state.goals[p.goalId] = {
      id: p.goalId, title: p.title || '', priority: p.priority || 'normal',
      timeline: p.timeline || null, horizon: p.horizon || null, progress: 0,
      workspaceId: p.workspaceId || state.workspace.currentId,
      scope: p.scope || 'workspace', status: 'Created', createdAt: now()
    };
    upsertNode('goal:' + p.goalId, 'goal', 'Created',
      { workspaceId: state.goals[p.goalId].workspaceId },
      { title: p.title, priority: p.priority, timeline: p.timeline, scope: p.scope,
        horizon: p.horizon, progress: 0 });
    // Order 5：Intent→Goal 关联（仅更新 intents 子对象；不触碰 Goal 自身状态）
    if (p.intentId && state.intents[p.intentId]) {
      state.intents[p.intentId].targetGoal = p.goalId;
      state.intents[p.intentId].status = 'Converted';
      var inode = state.galaxyNodes['intent:' + p.intentId];
      if (inode) { inode.metadata.targetGoal = p.goalId; inode.state = 'Converted'; }
    }
  };

  // GOAL_UPDATED：只合并非状态字段（progress/title/priority/horizon）。
  // 生命周期状态（Created/Started/Running/Completed/Failed）由专属事件独占，
  // 防止后端持久化状态（active/archived）回退已推进的前端生命周期（readiness §6）。
  reducers[ZZ.EVENTS.GOAL_UPDATED] = function (p) {
    var g = p && state.goals[p.goalId];
    if (!g) return;
    if (p.title !== undefined) g.title = p.title;
    if (p.priority !== undefined) g.priority = p.priority;
    if (p.horizon !== undefined) g.horizon = p.horizon;
    if (p.field === 'progress' && p.value !== undefined) g.progress = p.value;
    if (p.progress !== undefined) g.progress = p.progress;
    if (p.status === 'archived') { g.status = 'Archived'; }  // 删除=归档，独立于生命周期
    var node = state.galaxyNodes['goal:' + p.goalId];
    if (node) {
      node.metadata.title = g.title;
      node.metadata.priority = g.priority;
      node.metadata.horizon = g.horizon;
      node.metadata.progress = g.progress;
      if (p.status === 'archived') node.state = 'Dormant';
    }
  };

  reducers[ZZ.EVENTS.GOAL_STARTED] = function (p) {
    var g = p && state.goals[p.goalId];
    if (!g) return;
    g.status = 'Started';
    var node = state.galaxyNodes['goal:' + p.goalId];
    if (node) node.state = 'Started';
  };

  reducers[ZZ.EVENTS.GOAL_RUNNING] = function (p) {
    var g = p && state.goals[p.goalId];
    if (!g) return;
    g.status = 'Running';
    state.execution.currentGoalId = p.goalId;
    var node = state.galaxyNodes['goal:' + p.goalId];
    if (node) node.state = 'Running';
  };

  reducers[ZZ.EVENTS.GOAL_COMPLETED] = function (p) {
    var g = p && state.goals[p.goalId];
    if (!g) return;
    g.status = 'Completed';
    if (p.progress !== undefined) g.progress = p.progress;
    var node = state.galaxyNodes['goal:' + p.goalId];
    if (node) {
      node.state = 'Completed';
      if (p.progress !== undefined) node.metadata.progress = p.progress;
    }
  };

  reducers[ZZ.EVENTS.GOAL_FAILED] = function (p) {
    var g = p && state.goals[p.goalId];
    if (!g) return;
    g.status = 'Failed';
    var node = state.galaxyNodes['goal:' + p.goalId];
    if (node) node.state = 'Error';
  };

  // —— Order 3：Agent 生命周期（Agent = Goal 轨道的卫星；独立子对象，不与 Goal/Task 互覆）——
  reducers[ZZ.EVENTS.AGENT_CREATED] = function (p) {
    if (!p || !p.agentId) return;
    if (!state.agents[p.agentId]) {
      state.agents[p.agentId] = {
        id: p.agentId, name: p.name || '', type: p.type || 'agent',
        goalId: p.goalId || null, status: 'Created', createdAt: now()
      };
    }
    upsertNode('agent:' + p.agentId, 'agent', 'Created',
      { goalId: p.goalId || null }, { name: p.name, type: p.type });
  };

  reducers[ZZ.EVENTS.AGENT_STARTED] = function (p) {
    var a = p && state.agents[p.agentId];
    if (!a) return;
    a.status = 'Started';
    state.execution.currentAgentId = p.agentId;
    var node = state.galaxyNodes['agent:' + p.agentId];
    if (node) node.state = 'Started';
  };

  reducers[ZZ.EVENTS.AGENT_THINKING] = function (p) {
    var a = p && state.agents[p.agentId];
    if (!a) return;
    a.status = 'Thinking';
    var node = state.galaxyNodes['agent:' + p.agentId];
    if (node) node.state = 'Thinking';
  };

  reducers[ZZ.EVENTS.AGENT_WORKING] = function (p) {
    var a = p && state.agents[p.agentId];
    if (!a) return;
    a.status = 'Working';
    var node = state.galaxyNodes['agent:' + p.agentId];
    if (node) node.state = 'Working';
  };

  reducers[ZZ.EVENTS.AGENT_WAITING] = function (p) {
    var a = p && state.agents[p.agentId];
    if (!a) return;
    a.status = 'Waiting';
    var node = state.galaxyNodes['agent:' + p.agentId];
    if (node) node.state = 'Waiting';
  };

  reducers[ZZ.EVENTS.AGENT_COMPLETED] = function (p) {
    var a = p && state.agents[p.agentId];
    if (!a) return;
    a.status = 'Completed';
    var node = state.galaxyNodes['agent:' + p.agentId];
    if (node) node.state = 'Completed';
  };

  reducers[ZZ.EVENTS.AGENT_FAILED] = function (p) {
    var a = p && state.agents[p.agentId];
    if (!a) return;
    a.status = 'Failed';
    if (p.error) a.error = p.error;
    // GAP C 收口：保留 18 类 ERROR_TAXONOMY 的 category/reason，供 UI 真实表达 FAIL CLOSED（不得静默吞错）
    a.errorCategory = p.category || null;
    a.errorReason = p.reason || null;
    a.errorLabel = _categoryLabel(p.category);
    var node = state.galaxyNodes['agent:' + p.agentId];
    if (node) {
      node.state = 'Error';
      if (p.error) node.metadata.error = p.error;
      node.metadata.errorCategory = p.category || null;
      node.metadata.errorReason = p.reason || null;
      node.metadata.errorLabel = _categoryLabel(p.category);
    }
  };

  // —— Order 3：Task 生命周期（Task = Agent 轨道上的节点；独立子对象）——
  reducers[ZZ.EVENTS.TASK_CREATED] = function (p) {
    if (!p || !p.taskId) return;
    if (!state.tasks[p.taskId]) {
      state.tasks[p.taskId] = {
        id: p.taskId, goalId: p.goalId || null, agentId: p.agentId || null,
        title: p.title || '', status: 'Created'
      };
    }
    upsertNode('task:' + p.taskId, 'task', 'Created',
      { goalId: p.goalId || null, agentId: p.agentId || null },
      { title: p.title });
  };

  reducers[ZZ.EVENTS.TASK_STARTED] = function (p) {
    var t = p && state.tasks[p.taskId];
    if (!t) return;
    t.status = 'Started';
    state.execution.currentTaskId = p.taskId;
    var node = state.galaxyNodes['task:' + p.taskId];
    if (node) node.state = 'Started';
  };

  reducers[ZZ.EVENTS.TASK_RUNNING] = function (p) {
    var t = p && state.tasks[p.taskId];
    if (!t) return;
    t.status = 'Running';
    if (p.progress != null) t.progress = p.progress;
    var node = state.galaxyNodes['task:' + p.taskId];
    if (node) {
      node.state = 'Running';
      if (p.progress != null) node.metadata.progress = p.progress;
    }
  };

  reducers[ZZ.EVENTS.TASK_FAILED] = function (p) {
    var t = p && state.tasks[p.taskId];
    if (!t) return;
    t.status = 'Failed';
    if (p.error) t.error = p.error;
    // GAP C 收口：保留 18 类 ERROR_TAXONOMY 的 category/reason，供 UI 真实表达 FAIL CLOSED（不得静默吞错）
    t.errorCategory = p.category || null;
    t.errorReason = p.reason || null;
    t.errorLabel = _categoryLabel(p.category);
    var node = state.galaxyNodes['task:' + p.taskId];
    if (node) {
      node.state = 'Error';
      if (p.error) node.metadata.error = p.error;
      node.metadata.errorCategory = p.category || null;
      node.metadata.errorReason = p.reason || null;
      node.metadata.errorLabel = _categoryLabel(p.category);
    }
  };

  reducers[ZZ.EVENTS.TASK_COMPLETED] = function (p) {
    var t = p && state.tasks[p.taskId];
    if (!t) return;
    t.status = 'Completed';
    var node = state.galaxyNodes['task:' + p.taskId];
    if (node) node.state = 'Completed';
  };

  reducers[ZZ.EVENTS.MEMORY_UPDATED] = function (p) {
    if (!p || !p.memoryId) return;
    state.memory[p.memoryId] = {
      id: p.memoryId, scope: p.scope || 'global',
      kind: p.kind || 'write', createdAt: now()
    };
    upsertNode('memory:' + p.memoryId, 'memory', 'updated',
      { scope: p.scope || 'global' }, { kind: p.kind });
  };

  // —— Order 4：Memory 生命周期（Memory = 独立子对象；与 Goal/Agent/Task 互不覆盖）——
  reducers[ZZ.EVENTS.MEMORY_CREATED] = function (p) {
    if (!p || !p.memoryId) return;
    if (!state.memory[p.memoryId]) {
      state.memory[p.memoryId] = {
        id: p.memoryId, goalId: p.goalId || null, title: p.title || '',
        scope: p.scope || 'agent-reflection', status: 'Created', createdAt: now()
      };
    } else {
      state.memory[p.memoryId].status = 'Created';
    }
    state.execution.currentMemoryId = p.memoryId;
    state.execution.reflecting = true;
    upsertNode('memory:' + p.memoryId, 'memory', 'Created',
      { goalId: p.goalId || null }, { title: p.title });
  };

  reducers[ZZ.EVENTS.MEMORY_STORED] = function (p) {
    if (!p || !p.memoryId) return;
    var m = state.memory[p.memoryId] || (state.memory[p.memoryId] = {
      id: p.memoryId, title: p.title || '', scope: 'knowledge', status: 'Stored', createdAt: now()
    });
    m.status = 'Stored';
    // 反思产出已持久化 → 反思阶段完成（修正 reflecting 卡在 true 的运行时缺陷；非架构变更）。
    state.execution.reflecting = false;
    if (p.title !== undefined) m.title = p.title;
    if (p.knowledgeId !== undefined) m.knowledgeId = p.knowledgeId;
    // Knowledge 子对象（独立）：knowledgeId -> Knowledge
    if (p.knowledgeId !== undefined) {
      state.knowledge[p.knowledgeId] = state.knowledge[p.knowledgeId] || {
        id: p.knowledgeId, memoryId: p.memoryId, title: p.title || '',
        source: p.source || '', scope: 'knowledge', status: 'Stored', createdAt: now()
      };
      state.knowledge[p.knowledgeId].status = 'Stored';
    }
    upsertNode('memory:' + p.memoryId, 'memory', 'Stored',
      { knowledgeId: p.knowledgeId || null }, { title: p.title });
    if (p.knowledgeId !== undefined) {
      upsertNode('knowledge:' + p.knowledgeId, 'knowledge', 'Stored',
        { memoryId: p.memoryId }, { title: p.title, source: p.source });
    }
  };

  reducers[ZZ.EVENTS.MEMORY_LINKED] = function (p) {
    if (!p || !p.knowledgeId) return;
    var k = state.knowledge[p.knowledgeId] || (state.knowledge[p.knowledgeId] = {
      id: p.knowledgeId, memoryId: p.memoryId || null, title: p.title || '',
      source: p.source || '', scope: 'knowledge', status: 'Linked', createdAt: now()
    });
    k.status = 'Linked';
    if (p.memoryId !== undefined && state.memory[p.memoryId]) {
      state.memory[p.memoryId].status = 'Stored';  // 关联建立后，记忆保持 Stored
    }
    upsertNode('knowledge:' + p.knowledgeId, 'knowledge', 'Linked',
      { memoryId: p.memoryId || null }, { title: p.title, source: p.source });
  };

  reducers[ZZ.EVENTS.MEMORY_ARCHIVED] = function (p) {
    if (!p || (!p.memoryId && !p.knowledgeId)) return;
    if (p.memoryId && state.memory[p.memoryId]) state.memory[p.memoryId].status = 'Archived';
    if (p.knowledgeId && state.knowledge[p.knowledgeId]) state.knowledge[p.knowledgeId].status = 'Archived';
    if (p.memoryId) upsertNode('memory:' + p.memoryId, 'memory', 'Dormant', {}, {});
    if (p.knowledgeId) upsertNode('knowledge:' + p.knowledgeId, 'knowledge', 'Dormant', {}, {});
  };

  // REFLECTING：反思阶段入口（仅置执行态标记，不触碰 Goal/Agent/Task）
  reducers[ZZ.EVENTS.REFLECTING] = function (p) {
    state.execution.reflecting = true;
    if (p && p.goalId !== undefined) state.execution.currentGoalId = p.goalId;
  };

  // —— Order 5：Intent Gateway 生命周期（Intent = 独立子对象；与 Goal/Agent/Task/Memory 互不覆盖）——
  // 状态机：Received → Analyzing → Classified →（Accepted | Rejected）→ Converted(→ Goal)
  reducers[ZZ.EVENTS.INTENT_RECEIVED] = function (p) {
    if (!p || !p.intentId) return;
    state.intents[p.intentId] = {
      id: p.intentId, type: 'intent', source: p.source || 'command', status: 'Received',
      confidence: null, targetGoal: null, text: p.text || '', createdAt: now()
    };
    upsertNode('intent:' + p.intentId, 'intent', 'Received', {}, { text: p.text, source: p.source });
  };

  reducers[ZZ.EVENTS.INTENT_ANALYZING] = function (p) {
    var it = p && state.intents[p.intentId];
    if (!it) return;
    it.status = 'Analyzing';
    var node = state.galaxyNodes['intent:' + p.intentId];
    if (node) node.state = 'Analyzing';
  };

  reducers[ZZ.EVENTS.INTENT_CLASSIFIED] = function (p) {
    var it = p && state.intents[p.intentId];
    if (!it) return;
    it.status = 'Classified';
    it.type = p.classification || it.type;     // type 承载 GDE 分类（A/B/C/D/E）
    it.confidence = (p.confidence != null) ? p.confidence : it.confidence;
    it.action = p.action || null;
    it.title = p.title || it.title;
    var node = state.galaxyNodes['intent:' + p.intentId];
    if (node) { node.state = 'Classified'; node.metadata.classification = p.classification; node.metadata.confidence = p.confidence; }
  };

  reducers[ZZ.EVENTS.INTENT_ACCEPTED] = function (p) {
    var it = p && state.intents[p.intentId];
    if (!it) return;
    it.status = 'Accepted';
    if (p.confidence != null) it.confidence = p.confidence;
    if (p.title) it.title = p.title;
    it.needsConfirm = !!p.needsConfirm;
    var node = state.galaxyNodes['intent:' + p.intentId];
    if (node) { node.state = 'Accepted'; if (p.needsConfirm) node.metadata.needsConfirm = true; }
  };

  reducers[ZZ.EVENTS.INTENT_REJECTED] = function (p) {
    var it = p && state.intents[p.intentId];
    if (!it) return;
    it.status = 'Rejected';
    it.reason = p.reason || '';
    var node = state.galaxyNodes['intent:' + p.intentId];
    if (node) node.state = 'Rejected';
  };

  reducers[ZZ.EVENTS.INTENT_CONVERTED_TO_GOAL] = function (p) {
    var it = p && state.intents[p.intentId];
    if (!it) return;
    it.status = 'Converted';
    if (p.goalId != null) it.targetGoal = p.goalId;   // 转换瞬间 goalId 可能暂空，待 GOAL_CREATED 补全
    var node = state.galaxyNodes['intent:' + p.intentId];
    if (node) { node.state = 'Converted'; if (p.goalId != null) node.metadata.targetGoal = p.goalId; }
  };

  reducers[ZZ.EVENTS.ERROR_OCCURRED] = function (p) {
    if (!p) return;
    var entry = {
      sourceType: p.sourceType || 'unknown', sourceId: p.sourceId || null,
      message: p.message || '', severity: p.severity || 'error', ts: now()
    };
    state.execution.errors.push(entry);
    state.execution.lastRun = entry;
    // 节点状态统一使用大写词表（Created/Started/Running/Completed/Failed/Error/Dormant/Archived），
    // 与 galaxy-runtime.mapState / overlay-runtime.steadyLifecycle 一致；type 仍保持 'error'。
    if (p.sourceId) upsertNode('error:' + p.sourceId, 'error', 'Error',
      { sourceType: entry.sourceType, sourceId: p.sourceId },
      { message: p.message, severity: entry.severity });
  };

  reducers[ZZ.EVENTS.STATE_SYNC] = function (p) {
    if (!p || typeof p !== 'object') return;
    ['goals', 'agents', 'tasks', 'galaxyNodes', 'memory', 'knowledge', 'intents', 'workspace', 'focus'].forEach(function (k) {
      if (p[k] && typeof p[k] === 'object') state[k] = p[k];
    });
  };

  // —— Order 7：Focus 联动（点击银河节点 → AppState Focus → Overlay Runtime → Overlay Model）——
  // FOCUS_CHANGED 是 zz-events 合约预留事件（与 eventbus.DOMAIN_EVENT_NAMES 逐字一致），
  // 本 Order 落地其 reducer，使 AppState 成为聚焦态唯一事实来源。聚焦态是 UI 交互态，
  // 非领域生命周期事件；Overlay Runtime 只读 AppState.focus，绝不直接监听 Three.js。
  reducers[ZZ.EVENTS.FOCUS_CHANGED] = function (p) {
    state.focus = {
      capability: (p && p.capability != null) ? p.capability : null,
      id: (p && p.id != null) ? p.id : null
    };
  };

  // —— Phase 7 Order 1：Computer World Model（只读观测；动作能力在 Order 2+）——
  // 纪律：以下 reducer 只把“观测事件”写入 state.computer 投影；绝不调用 OS、绝不动作。
  //       World Model = Observation only（见 Phase 7 Specification §2/§6）。
  //       所有集合键：windows[windowId] / applications[appId] / processes[pid] /
  //       files[path] / projects[projectId] / browsers[browserId] / terminals[termId] / devices[deviceId]。
  var COMP_COLLS = ['windows', 'applications', 'processes', 'files', 'projects', 'browsers', 'terminals', 'devices'];

  reducers[ZZ.EVENTS.COMPUTER_WORLD_SYNC] = function (p) {
    if (!p || !p.world || typeof p.world !== 'object') return;
    var w = p.world;
    COMP_COLLS.forEach(function (coll) {
      var arr = w[coll];
      if (!arr || !Array.isArray(arr)) return;
      arr.forEach(function (item) {
        if (!item || !item.id) return;
        state.computer[coll][item.id] = Object.assign({}, item, { updatedAt: now() });
      });
    });
  };

  reducers[ZZ.EVENTS.WINDOW_OPENED] = function (p) {
    if (!p || !p.windowId) return;
    var prev = state.computer.windows[p.windowId] || {};
    state.computer.windows[p.windowId] = Object.assign({}, prev, {
      id: p.windowId, appId: p.appId || null, title: p.title || '',
      rect: p.rect || null, zOrder: (p.zOrder != null) ? p.zOrder : (prev.zOrder || 0),
      isFocused: false, isMinimized: !!p.isMinimized, isMaximized: !!p.isMaximized,
      role: p.role || 'window', updatedAt: now()
    });
  };
  reducers[ZZ.EVENTS.WINDOW_CLOSED] = function (p) {
    if (!p || !p.windowId) return;
    delete state.computer.windows[p.windowId];
  };
  reducers[ZZ.EVENTS.WINDOW_FOCUSED] = function (p) {
    if (!p || !p.windowId) return;
    for (var id in state.computer.windows) {
      if (Object.prototype.hasOwnProperty.call(state.computer.windows, id)) {
        state.computer.windows[id].isFocused = (id === p.windowId);
      }
    }
    if (state.computer.windows[p.windowId]) state.computer.windows[p.windowId].updatedAt = now();
  };

  reducers[ZZ.EVENTS.APP_LAUNCHED] = function (p) {
    if (!p || !p.appId) return;
    var prev = state.computer.applications[p.appId] || {};
    state.computer.applications[p.appId] = Object.assign({}, prev, {
      id: p.appId, name: p.name || prev.name || '', execPath: p.execPath || prev.execPath || '',
      version: p.version || prev.version || '', pids: p.pids || prev.pids || [],
      state: 'Running', scope: p.scope || prev.scope || 'user', updatedAt: now()
    });
  };
  reducers[ZZ.EVENTS.APP_EXITED] = function (p) {
    if (!p || !p.appId) return;
    var a = state.computer.applications[p.appId];
    if (a) { a.state = 'Exited'; a.updatedAt = now(); }
  };

  reducers[ZZ.EVENTS.PROCESS_SPAWNED] = function (p) {
    if (!p || p.pid == null) return;
    var id = String(p.pid);
    var prev = state.computer.processes[id] || {};
    state.computer.processes[id] = Object.assign({}, prev, {
      pid: p.pid, ppid: (p.ppid != null) ? p.ppid : prev.ppid, name: p.name || prev.name || '',
      cmdline: p.cmdline || prev.cmdline || '', cpu: (p.cpu != null) ? p.cpu : prev.cpu,
      mem: (p.mem != null) ? p.mem : prev.mem, owner: p.owner || prev.owner || '',
      startedAt: (p.startedAt != null) ? p.startedAt : (prev.startedAt || now()),
      cwd: p.cwd || prev.cwd || '', state: 'Running', updatedAt: now()
    });
  };
  reducers[ZZ.EVENTS.PROCESS_TERMINATED] = function (p) {
    if (!p || p.pid == null) return;
    var pr = state.computer.processes[String(p.pid)];
    if (pr) { pr.state = 'Terminated'; pr.updatedAt = now(); }
  };

  reducers[ZZ.EVENTS.FILE_CREATED] = function (p) {
    if (!p || !p.path) return;
    var prev = state.computer.files[p.path] || {};
    state.computer.files[p.path] = Object.assign({}, prev, {
      path: p.path, type: p.type || prev.type || 'file', size: (p.size != null) ? p.size : prev.size,
      mtime: p.mtime || prev.mtime || now(), perms: p.perms || prev.perms || '',
      hash: p.hash || prev.hash || '', updatedAt: now()
    });
  };
  reducers[ZZ.EVENTS.FILE_MODIFIED] = function (p) {
    if (!p || !p.path) return;
    var f = state.computer.files[p.path];
    if (!f) return;
    if (p.size != null) f.size = p.size;
    if (p.mtime) f.mtime = p.mtime;
    if (p.hash) f.hash = p.hash;
    if (p.perms) f.perms = p.perms;
    f.updatedAt = now();
  };
  reducers[ZZ.EVENTS.FILE_DELETED] = function (p) {
    if (!p || !p.path) return;
    delete state.computer.files[p.path];
  };

  reducers[ZZ.EVENTS.PROJECT_DETECTED] = function (p) {
    if (!p || !p.projectId) return;
    var prev = state.computer.projects[p.projectId] || {};
    state.computer.projects[p.projectId] = Object.assign({}, prev, {
      id: p.projectId, rootPath: p.rootPath || prev.rootPath || '',
      type: p.type || prev.type || 'unknown', manifest: p.manifest || prev.manifest || [],
      openFiles: p.openFiles || prev.openFiles || [],
      associatedAppId: (p.associatedAppId != null) ? p.associatedAppId : prev.associatedAppId || null,
      updatedAt: now()
    });
  };
  reducers[ZZ.EVENTS.PROJECT_UPDATED] = function (p) {
    if (!p || !p.projectId) return;
    var pr = state.computer.projects[p.projectId];
    if (!pr) return;
    if (p.rootPath != null) pr.rootPath = p.rootPath;
    if (p.type != null) pr.type = p.type;
    if (p.manifest) pr.manifest = p.manifest;
    if (p.openFiles) pr.openFiles = p.openFiles;
    if (p.associatedAppId != null) pr.associatedAppId = p.associatedAppId;
    pr.updatedAt = now();
  };

  reducers[ZZ.EVENTS.BROWSER_NAVIGATED] = function (p) {
    if (!p || !p.browserId) return;
    var prev = state.computer.browsers[p.browserId] || {};
    var tabs = prev.tabs ? prev.tabs.slice() : [];
    if (p.tab) {
      if (p.tab.id != null) {
        var idx = -1;
        for (var i = 0; i < tabs.length; i++) { if (tabs[i].id === p.tab.id) { idx = i; break; } }
        if (idx >= 0) tabs[idx] = Object.assign({}, tabs[idx], p.tab);
        else tabs.push(Object.assign({ id: p.tab.id }, p.tab));
      } else if (p.tab.url != null && tabs.length) {
        tabs[tabs.length - 1] = Object.assign({}, tabs[tabs.length - 1], p.tab);
      }
    }
    state.computer.browsers[p.browserId] = Object.assign({}, prev, {
      id: p.browserId, kind: p.kind || prev.kind || 'chrome', tabs: tabs,
      activeTab: (p.activeTab != null) ? p.activeTab : (prev.activeTab || (tabs.length ? tabs[tabs.length - 1].id : null)),
      updatedAt: now()
    });
  };
  reducers[ZZ.EVENTS.BROWSER_TAB_OPENED] = function (p) {
    if (!p || !p.browserId || !p.tab) return;
    var b = state.computer.browsers[p.browserId];
    if (!b) return;
    b.tabs = b.tabs || [];
    var tab = Object.assign({ id: p.tab.id || ('tab' + now()) }, p.tab);
    b.tabs.push(tab);
    if (p.tab.active) b.activeTab = tab.id;
    b.updatedAt = now();
  };
  reducers[ZZ.EVENTS.BROWSER_TAB_CLOSED] = function (p) {
    if (!p || !p.browserId || !p.tabId) return;
    var b = state.computer.browsers[p.browserId];
    if (!b || !b.tabs) return;
    b.tabs = b.tabs.filter(function (t) { return t.id !== p.tabId; });
    if (b.activeTab === p.tabId) b.activeTab = b.tabs.length ? b.tabs[b.tabs.length - 1].id : null;
    b.updatedAt = now();
  };

  reducers[ZZ.EVENTS.TERMINAL_SPAWNED] = function (p) {
    if (!p || !p.termId) return;
    var prev = state.computer.terminals[p.termId] || {};
    state.computer.terminals[p.termId] = Object.assign({}, prev, {
      id: p.termId, shell: p.shell || prev.shell || 'cmd', cwd: p.cwd || prev.cwd || '',
      status: p.status || 'Ready', updatedAt: now()
    });
  };
  reducers[ZZ.EVENTS.TERMINAL_EXITED] = function (p) {
    if (!p || !p.termId) return;
    var t = state.computer.terminals[p.termId];
    if (t) { t.status = 'Exited'; t.updatedAt = now(); }
  };

  reducers[ZZ.EVENTS.DEVICE_STATE_CHANGED] = function (p) {
    if (!p || !p.deviceId) return;
    var prev = state.computer.devices[p.deviceId] || {};
    state.computer.devices[p.deviceId] = Object.assign({}, prev, {
      id: p.deviceId, kind: p.kind || prev.kind || 'unknown',
      state: p.state || prev.state || 'unknown',
      capabilities: p.capabilities || prev.capabilities || {}, updatedAt: now()
    });
  };

  // —— Phase 7 Order 2：Computer Action 生命周期（只读投影；动作经 Permission Guard 写入，
  //     由 ComputerState 类投影消费。绝不在 AppState 执行任何 OS 动作 / 直调 executor）——
  //     纪律：AppState 只是动作事件的“事实账本”，执行裁决在后端 Policy Engine，前端只投影。
  function _actionRec(id) {
    if (!id) return null;
    return state.computer.actions[id] || (state.computer.actions[id] = {
      actionId: id, capability: null, target: null, risk: null,
      expectedEffect: null, status: 'planned', permissionDecision: null,
      result: null, decisionReason: null, verified: null, verificationDetail: null,
      createdAt: now()
    });
  }

  reducers[ZZ.EVENTS.COMPUTER_ACTION_PLANNED] = function (p) {
    if (!p || !p.actionId) return;
    var r = _actionRec(p.actionId);
    r.capability = p.capability || r.capability;
    r.target = (p.target != null) ? p.target : r.target;
    r.risk = p.risk || r.risk;
    r.expectedEffect = p.expectedEffect || r.expectedEffect;
    r.status = 'planned';
    r.parameters = p.parameters || r.parameters || null;
    r.goalId = (p.goalId != null) ? p.goalId : r.goalId;
  };

  reducers[ZZ.EVENTS.COMPUTER_ACTION_CALLED] = function (p) {
    if (!p || !p.actionId) return;
    var r = _actionRec(p.actionId);
    if (p.capability != null) r.capability = p.capability;
    if (p.permissionDecision != null) r.permissionDecision = p.permissionDecision;
    r.status = 'called';
  };

  reducers[ZZ.EVENTS.COMPUTER_ACTION_DONE] = function (p) {
    if (!p || !p.actionId) return;
    var r = _actionRec(p.actionId);
    if (p.capability != null) r.capability = p.capability;
    r.status = 'done';
    r.result = (p.result !== undefined) ? p.result : r.result;
  };

  reducers[ZZ.EVENTS.COMPUTER_ACTION_FAILED] = function (p) {
    if (!p || !p.actionId) return;
    var r = _actionRec(p.actionId);
    if (p.capability != null) r.capability = p.capability;
    r.status = 'failed';
    r.result = (p.error !== undefined) ? { error: p.error } : r.result;
  };

  reducers[ZZ.EVENTS.COMPUTER_ACTION_DENIED] = function (p) {
    if (!p || !p.actionId) return;
    var r = _actionRec(p.actionId);
    if (p.capability != null) r.capability = p.capability;
    if (p.risk != null) r.risk = p.risk;
    r.status = 'denied';
    r.decisionReason = p.reason || r.decisionReason;
  };

  // —— Phase 7 Order 3：Verification（执行后复核；只读投影 VERIFIED / UNVERIFIED）——
  reducers[ZZ.EVENTS.COMPUTER_ACTION_VERIFIED] = function (p) {
    if (!p || !p.actionId) return;
    var r = _actionRec(p.actionId);
    if (p.capability != null) r.capability = p.capability;
    r.verified = true;
    r.verificationDetail = p.detail || r.verificationDetail;
    if (r.status === 'done') r.status = 'verified';
  };

  reducers[ZZ.EVENTS.COMPUTER_ACTION_UNVERIFIED] = function (p) {
    if (!p || !p.actionId) return;
    var r = _actionRec(p.actionId);
    if (p.capability != null) r.capability = p.capability;
    r.verified = false;
    r.verificationDetail = p.detail || r.verificationDetail;
    if (r.status === 'done') r.status = 'unverified';
  };

  // —— Phase 21：四态相位（观察/规划/执行/验证），供 AI Core 状态表达 ——
  var _PHASE_LABELS = {
    observe: '正在观察屏幕',
    plan: '正在规划操作',
    execute: '正在执行',
    verify: '正在确认结果'
  };
  reducers[ZZ.EVENTS.COMPUTER_ACTION_PHASE] = function (p) {
    if (!p || !p.phase) return;
    state.computer.phase = p.phase;
    state.computer.phaseLabel = _PHASE_LABELS[p.phase] || '';
  };

  // —— 唯一写入入口 ——
  function applyEvent(name, payload) {
    if (!ZZ || !ZZ.isEvent(name)) {
      // 已登记系统事件（telemetry / 主动推送 / 输入信号）不属于领域状态，由独立 SSE 监听器
      // （app.js / glance-card.js）消费；此处按设计静默忽略，不产生误导性的"非合约"告警。
      if (ZZ && ZZ.isSystemEvent && ZZ.isSystemEvent(name)) return;
      if (typeof console !== 'undefined') console.warn('[AppState] 忽略非合约事件: ' + name);
      return;
    }
    var r = reducers[name];
    if (r) r(payload || {});
    emit(name, payload || {});
    emit('*', { name: name, payload: payload || {} });
  }

  function subscribe(type, fn) {
    var o = { type: type, fn: fn };
    observers.push(o);
    return function () {
      var i = observers.indexOf(o);
      if (i >= 0) observers.splice(i, 1);
    };
  }

  // —— GAP C 收口：18 类 ERROR_TAXONOMY → 中文 UI 标签（单一词汇表，禁第二套错误词汇）——
  function _categoryLabel(cat) {
    var MAP = {
      network: '网络错误', timeout: '超时', permission: '权限拒绝', file: '文件错误',
      not_found: '未找到', tool_missing: '未知工具', skill_error: '技能错误', mcp_error: 'MCP错误',
      computer_error: '电脑动作错误', budget_exhausted: '预算耗尽', depth_exceeded: '深度超限',
      injection_blocked: '注入拦截', policy_blocked: '策略阻断', parse_error: '解析错误',
      serialization: '序列化错误', validation: '校验错误', resource: '资源错误', unknown: '未知错误'
    };
    return (cat && MAP[cat]) ? MAP[cat] : '未知错误';
  }

  var API = {
    state: state,
    applyEvent: applyEvent,
    subscribe: subscribe,
    categoryLabel: _categoryLabel,
    getState: function () { return state; },
    getNode: function (id) { return state.galaxyNodes[id] || null; },
    getGalaxyNodes: function () { return state.galaxyNodes; },
    getGoal: function (id) { return state.goals[id] || null; },
    getAgent: function (id) { return state.agents[id] || null; },
    getTask: function (id) { return state.tasks[id] || null; },
    getMemory: function (id) { return state.memory[id] || null; },
    getKnowledge: function (id) { return state.knowledge[id] || null; },
    getIntent: function (id) { return state.intents[id] || null; },
    // Order 7：聚焦态读取入口（Overlay Runtime 消费）
    getFocus: function () { return state.focus; },
    // Phase 7 Order 1：Computer World Model 读取入口（ComputerState 投影消费）
    getComputer: function () { return state.computer; }
  };

  global.AppState = API;
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
})(typeof window !== 'undefined' ? window : globalThis);
