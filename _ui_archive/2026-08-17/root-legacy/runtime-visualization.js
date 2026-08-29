/*
 * runtime-visualization.js — 小6 Phase 6 Order 3 / 5 / 6 · 运行时可视化（只读投影渲染）
 * ----------------------------------------------------------------------------
 * 链路：Backend Event → EventBus → SSE → event-bridge.js → AppState(单一写入口) → 本模块(只读渲染)
 * 职责：
 *   - Order 3：把 Goal / Task / Agent / Execution 状态从 AppState 投影到 UI（执行时间线）。
 *   - Order 5：Execution Timeline = User Goal → Planner → Reasoning → Tool → Reflection → Result
 *             （数据来自 AppState.execution + 领域事件投影；对应后端 execution_guard.py + conversation_loop.py 产出的事件）。
 *   - Order 6：Memory Context = 已加载记忆 / 上下文窗口代理 / 记忆来源 / 压缩状态 / World Model 投影
 *             （来自 AppState.memory / knowledge / computer）。
 * 纪律（铁律）：
 *   - 本模块只读 AppState（单一事实来源）；绝不直连后端、绝不调 API、绝不建立第二状态。
 *   - 禁止改变 Runtime / Memory 架构，禁止新增执行引擎 / 记忆；仅消费状态做可视化。
 *   - 数据单向派生自 AppState（readiness §5.2：UI 是订阅者而非生产者）。
 * 结构：纯数据模型函数(getExecutionTimeline / getMemoryContext) + 防御性 DOM 渲染器（仅浏览器）。
 * 可在 Node 中单测纯模型函数（不依赖 window / document / 网络）。
 */
(function (global) {
  'use strict';
  var AppState = global.AppState;

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  // —— 纯数据模型：执行时间线 ——
  function _agentsOf(agents, goalId) {
    return Object.keys(agents || {}).filter(function (id) {
      return !goalId || (agents[id] && agents[id].goalId === goalId);
    }).map(function (id) { return agents[id]; });
  }
  function _tasksOf(tasks, goalId) {
    return Object.keys(tasks || {}).filter(function (id) {
      return !goalId || (tasks[id] && tasks[id].goalId === goalId);
    }).map(function (id) { return tasks[id]; });
  }
  function _firstAgentStatus(agents, goalId) {
    var list = _agentsOf(agents, goalId);
    return list.length ? (list[0].status || 'Idle') : 'Idle';
  }
  function _plannerDetail(agents, goalId) {
    var list = _agentsOf(agents, goalId);
    if (!list.length) return '';
    var a = list[0];
    return (a.name || a.id) + ' · ' + (a.status || '');
  }
  function _anyAgent(agents, goalId, status) {
    return _agentsOf(agents, goalId).some(function (a) { return a.status === status; });
  }
  function _toolStatus(tasks, goalId) {
    var list = _tasksOf(tasks, goalId);
    if (!list.length) return 'Idle';
    if (list.some(function (t) { return t.status === 'Running'; })) return 'Active';
    if (list.some(function (t) { return t.status === 'Failed'; })) return 'Error';
    if (list.every(function (t) { return t.status === 'Completed'; })) return 'Done';
    return 'Idle';
  }
  function _toolDetail(tasks, goalId) {
    var list = _tasksOf(tasks, goalId);
    if (!list.length) return '';
    var labelOf = (global.AppState && typeof global.AppState.categoryLabel === 'function')
      ? function (c) { return global.AppState.categoryLabel(c); }
      : function () { return ''; };
    // GAP C 收口：任务失败时附上 18 类 ERROR_TAXONOMY 的中文标签，使 FAIL CLOSED 在 UI 可观察
    return list.map(function (t) {
      var extra = (t.status === 'Failed' && t.errorCategory) ? '（' + labelOf(t.errorCategory) + '）' : '';
      return (t.title || t.id) + '·' + (t.status || '') + extra;
    }).join('；');
  }
  function _hasStoredMemory(memories, goalId) {
    return Object.keys(memories || {}).some(function (id) {
      var m = memories[id];
      return (!goalId || m.goalId === goalId) && (m.status === 'Stored' || m.status === 'Created');
    });
  }

  function getExecutionTimeline(state) {
    state = state || (AppState && AppState.getState && AppState.getState()) || {};
    var exec = state.execution || {};
    var goals = state.goals || {};
    var agents = state.agents || {};
    var tasks = state.tasks || {};
    var memories = state.memory || {};
    var currentGoalId = (exec && exec.currentGoalId != null) ? exec.currentGoalId : null;
    var goal = currentGoalId != null ? goals[currentGoalId] : null;

    var steps = [
      {
        stage: 'user_goal', label: '用户目标 (User Goal)',
        status: goal ? 'Active' : 'Idle',
        detail: goal ? (goal.title || ('#' + currentGoalId)) : '暂无进行中目标'
      },
      {
        stage: 'planner', label: '规划 (Planner)',
        status: _firstAgentStatus(agents, currentGoalId),
        detail: _plannerDetail(agents, currentGoalId)
      },
      {
        stage: 'reasoning', label: '推理 (Reasoning)',
        status: _anyAgent(agents, currentGoalId, 'Thinking') ? 'Active' : (goal ? 'Done' : 'Idle'),
        detail: _anyAgent(agents, currentGoalId, 'Thinking') ? '正在推理…' : ''
      },
      {
        stage: 'tool', label: '工具 (Tool)',
        status: _toolStatus(tasks, currentGoalId),
        detail: _toolDetail(tasks, currentGoalId)
      },
      {
        stage: 'reflection', label: '反思 (Reflection)',
        status: (exec && exec.reflecting) ? 'Active' : (_hasStoredMemory(memories, currentGoalId) ? 'Done' : 'Idle'),
        detail: (exec && exec.reflecting) ? '正在反思 / 沉淀记忆…'
          : (_hasStoredMemory(memories, currentGoalId) ? '已沉淀记忆' : '')
      },
      {
        stage: 'result', label: '结果 (Result)',
        status: goal && goal.status === 'Completed' ? 'Done'
          : (goal && goal.status === 'Failed' ? 'Error' : 'Idle'),
        detail: goal && goal.status === 'Completed' ? ('完成 ' + (goal.progress != null ? goal.progress + '%' : ''))
          : (goal && goal.status === 'Failed' ? '失败' : '')
      }
    ];
    return steps;
  }

  // —— 纯数据模型：记忆上下文 + 世界模型 ——
  function getMemoryContext(state) {
    state = state || (AppState && AppState.getState && AppState.getState()) || {};
    var memory = state.memory || {};
    var knowledge = state.knowledge || {};
    var computer = state.computer || {};

    var memList = Object.keys(memory).map(function (id) {
      var m = memory[id];
      return { id: id, title: m.title || '', scope: m.scope || '', status: m.status || '', createdAt: m.createdAt || null };
    });
    var knowList = Object.keys(knowledge).map(function (id) {
      var k = knowledge[id];
      return { id: id, title: k.title || '', source: k.source || '', status: k.status || '' };
    });

    var wm = computer || {};
    var worldModel = {
      windows: Object.keys(wm.windows || {}).length,
      applications: Object.keys(wm.applications || {}).length,
      processes: Object.keys(wm.processes || {}).length,
      files: Object.keys(wm.files || {}).length,
      projects: Object.keys(wm.projects || {}).length,
      browsers: Object.keys(wm.browsers || {}).length,
      terminals: Object.keys(wm.terminals || {}).length,
      devices: Object.keys(wm.devices || {}).length
    };

    var loadedCount = memList.length + knowList.length;
    return {
      memories: memList,
      knowledge: knowList,
      worldModel: worldModel,
      context: {
        loadedItems: loadedCount,
        note: '上下文窗口以「已加载记忆 + 知识条数」作代理；精确 token 计数 / 压缩状态由后端 memory_distiller 维护，经 MEMORY_STORED / LINKED 事件投影'
      },
      compression: {
        status: 'tracked-by-backend',
        note: '压缩 / 蒸馏状态由 memory_distiller.py 维护；本视图只读，不新增记忆、不改 Memory 架构'
      }
    };
  }

  // —— 防御性 DOM 渲染器（仅浏览器，document 存在时启动）——
  function mount() {
    if (typeof document === 'undefined') return;
    if (!global.AppState || typeof global.AppState.getState !== 'function') return;
    if (document.getElementById('runtime-viz')) return; // 幂等

    var panel = document.createElement('div');
    panel.id = 'runtime-viz';
    // UI Consolidation Sprint：默认折叠。本面板是「开发者视角」运行时细节，
    // 与 OS 首页底部 Execution Timeline（用户视角 5 段自然语言）视觉职责重复。
    // ui2.css 已限定其仅在工作台(chat-mode)出现；此处再降一级默认噪声。
    panel.className = 'runtime-viz glass rv-collapsed';
    panel.setAttribute('role', 'region');
    panel.setAttribute('aria-label', '运行时可视化');
    panel.innerHTML =
      '<div class="rv-bar">' +
        '<span class="rv-title"><span class="rv-dot"></span>运行时可视化</span>' +
        '<button class="rv-toggle" id="rv-toggle" aria-label="折叠/展开">▾</button>' +
      '</div>' +
      '<div class="rv-body" id="rv-body">' +
        '<section class="rv-section">' +
          '<h4 class="rv-h">执行时间线 · Execution Timeline</h4>' +
          '<ol class="rv-timeline" id="rv-timeline"></ol>' +
        '</section>' +
        '<section class="rv-section">' +
          '<h4 class="rv-h">记忆上下文 · Memory Context</h4>' +
          '<div class="rv-mem" id="rv-mem"></div>' +
          '<h4 class="rv-h">世界模型 · World Model</h4>' +
          '<div class="rv-wm" id="rv-wm"></div>' +
        '</section>' +
      '</div>';
    document.body.appendChild(panel);

    var toggle = panel.querySelector('#rv-toggle');
    if (toggle) toggle.addEventListener('click', function () { panel.classList.toggle('rv-collapsed'); });

    function render() {
      var st = global.AppState.getState();
      var tl = getExecutionTimeline(st);
      var tlEl = panel.querySelector('#rv-timeline');
      if (tlEl) {
        tlEl.innerHTML = tl.map(function (s) {
          return '<li class="rv-step rv-' + esc(String(s.status).toLowerCase()) + '">' +
            '<span class="rv-stage">' + esc(s.label) + '</span>' +
            '<span class="rv-st">' + esc(s.status) + '</span>' +
            (s.detail ? '<span class="rv-detail">' + esc(s.detail) + '</span>' : '') +
            '</li>';
        }).join('');
      }
      var mc = getMemoryContext(st);
      var memEl = panel.querySelector('#rv-mem');
      if (memEl) {
        var memHtml = '<div class="rv-count">已加载记忆 <b>' + mc.memories.length + '</b> · 知识 <b>' + mc.knowledge.length + '</b></div>';
        if (mc.memories.length) {
          memHtml += mc.memories.slice(0, 6).map(function (m) {
            return '<div class="rv-mem-item">' + esc(m.title || m.id) + ' <i>' + esc(m.status) + '</i></div>';
          }).join('');
        } else {
          memHtml += '<div class="rv-empty">暂无记忆</div>';
        }
        memEl.innerHTML = memHtml;
      }
      var wmEl = panel.querySelector('#rv-wm');
      if (wmEl) {
        // UI Consolidation Sprint：世界模型只呈现「真实有值」的维度。
        // 此前无条件渲染全部键，长期显示几十个 0，属纯视觉噪声。
        // 纯展示过滤——不修改 getMemoryContext() 的数据本体，不造假数据。
        var wmKeys = Object.keys(mc.worldModel).filter(function (k) {
          var v = mc.worldModel[k];
          return v !== 0 && v !== '0' && v !== null && v !== undefined && v !== '';
        });
        wmEl.innerHTML = wmKeys.length
          ? wmKeys.map(function (k) {
              return '<span class="rv-wm-item">' + esc(k) + ': <b>' + esc(String(mc.worldModel[k])) + '</b></span>';
            }).join('')
          : '<div class="rv-empty">暂无世界模型数据</div>';
      }
    }

    var unsub = global.AppState.subscribe('*', render);
    render();
    panel._rvUnsub = unsub;
  }

  function boot() {
    if (typeof window === 'undefined' || !window.document) return;
    if (document.readyState === 'loading') {
      window.addEventListener('DOMContentLoaded', mount);
    } else {
      mount();
    }
  }

  var API = {
    getExecutionTimeline: getExecutionTimeline,
    getMemoryContext: getMemoryContext,
    mount: mount
  };
  global.RuntimeViz = API;
  if (typeof module !== 'undefined' && module.exports) module.exports = API;

  // 浏览器中自动挂载（head 中加载，待 DOM 就绪后渲染；Node 中跳过）
  boot();
})(typeof window !== 'undefined' ? window : globalThis);
