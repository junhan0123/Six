/*
 * companion.js — Phase 8 Desktop Companion · 小6交互层 (Interaction Entry)
 * ----------------------------------------------------------------------------
 * 纪律（最高约束，与 Phase 7 一致并升级）：
 *   - 仅 Presentation Layer：消费既有 AppState + ExecutionChannel + ZZSSE，不维护任务真相，
 *     不新建 Runtime / Memory / EventBus / State System。
 *   - 所有“系统动作”经 companion:action IPC 桥（Electron Desktop Layer）转发主窗口既有系统
 *     （Command / Chat / Goal / Execution / Panel），绝非直接调后端 API，绝非第二事件总线。
 *   - 快速指令复用既有 Command Palette（command-palette.js 暴露的 window.ZZCommandPalette.open），
 *     禁止在 Companion 内新增任何命令系统。
 *   - 数据来源真实：Hover 气泡 / 完成通知全部读自 AppState + ExecutionChannel，禁止本地模拟。
 */
(function () {
  'use strict';

  var AvatarState = window.AvatarState;
  var AppState = window.AppState;
  var ExecutionChannel = window.ExecutionChannel;
  var ZZSSE = window.ZZSSE;
  var bridge = window.xiao6; // preload 暴露的本地桥（含 action / setPref / getPrefs / setCompanionVisible）

  var root, avatar, badge, tip, menu, bubble, notify, notifyText, notifyIcon, notifyTimer, notifyAction;
  var cmdBubble, cmdInput, cmdSend;
  var mainVisible = false; // B4：主窗是否可见（用于主动提示去重）
  var sbStatus, sbElapsed, sbTask, sbPhase, ctlPause, ctlDnd;

  var current = null;        // 仅视图渲染缓存（非任务状态副本）
  var prevState = null;      // 用于检测状态跃迁以触发完成/异常通知（S5）
  var tipTimer = null;
  var bubbleTimer = null;
  var bubbleVisible = false;
  var prefs = { paused: false, dnd: false }; // 本地呈现偏好（持久化到 companion.json）
  var notifyKind = 'done';

  // —— Phase 10.2 任务二：桌宠自动隐藏（仅窗口可见性，禁碰任务状态）——
  var autoHidden = false;       // 是否处于 idle 自动隐藏态（瞬态，不持久化）
  var manualHidden = false;     // 用户主动隐藏（S6 按钮 / 右键菜单），不自动回归
  var idleTimer = null;         // idle 计时器
  var hideAnimTimer = null;     // 优雅淡出计时器
  var IDLE_HIDE_MS = 45000;     // 空闲多久后自动隐藏（45s，避免打扰）；可在设置 xiao6_settings_v1.idleHideMs 覆盖
  try {
    var _idleCfg = JSON.parse(localStorage.getItem('xiao6_settings_v1') || '{}').idleHideMs;
    if (_idleCfg && Number(_idleCfg) > 0) IDLE_HIDE_MS = Number(_idleCfg);
  } catch (_e) { /* 保持默认 */ }

  function $(id) { return document.getElementById(id); }

  // —— 小工具 ——
  function progressOf(steps) {
    if (!steps || !steps.length) return 0;
    var done = 0;
    for (var i = 0; i < steps.length; i++) if (steps[i].status === 'completed') done++;
    return Math.round((done / steps.length) * 100);
  }
  function fmtElapsed(ms) {
    if (!ms || ms < 0) ms = 0;
    var s = Math.floor(ms / 1000);
    var m = Math.floor(s / 60);
    s = s % 60;
    return (m < 10 ? '0' + m : m) + ':' + (s < 10 ? '0' + s : s);
  }

  // —— 主渲染（每次都从既有全局重新读取，绝不缓存任务真相）——
  function render() {
    if (!AvatarState) return;
    var res = AvatarState.deriveFromGlobals();
    current = res;

    if (avatar) {
      // A3：经 AvatarRenderer 投影八态 SVG 脸（含降级）；保留 data-state / color 设置
      if (window.AvatarRenderer) {
        window.AvatarRenderer.render(avatar, res.state, res.color);
      } else {
        avatar.setAttribute('data-state', res.state);
        avatar.className = 'avatar avatar--' + res.state.toLowerCase();
        avatar.style.setProperty('--avatar-color', res.color);
      }
    }
    // P4：广播存在色到全 Companion 表面（chrome 跟随状态色，强化"AI 在此"在场感；纯表现，不新增职责）
    if (root) root.style.setProperty('--presence-color', res.color);
    if (badge) badge.textContent = res.label;

    // 状态隐含的操作提示
    var auto = null;
    if (res.state === 'EXECUTING') {
      auto = res.context.tool ? ('执行：' + res.context.tool) : (res.context.prompt || '执行中…');
      if (res.context.progress) auto += ' · ' + res.context.progress + '%';
    } else if (res.state === 'ERROR') {
      auto = '异常：' + (res.context.error || '未知');
    } else if (res.state === 'PLANNING') {
      auto = res.context.goal ? ('规划：' + res.context.goal) : (res.context.intent ? ('规划：' + res.context.intent) : '规划中…');
    } else if (res.state === 'COMPLETED') {
      auto = res.context.prompt ? ('完成：' + res.context.prompt) : '任务已完成';
    } else if (res.state === 'OFFLINE') {
      auto = '后端离线，重连中…';
    }
    if (auto && tip) {
      tip.textContent = auto;
      tip.hidden = false;
    } else if (tip && !tip.dataset.sticky) {
      tip.hidden = true;
    }

    // S4：Hover 气泡随真实状态实时刷新
    if (bubbleVisible) updateBubble();

    // S5：状态跃迁 → 完成 / 异常通知（首帧不触发，避免加载即弹）
    if (prevState === null) {
      prevState = res.state;
    } else if (res.state !== prevState) {
      if (res.state === 'COMPLETED') {
        var cp = (res.context && res.context.prompt) || '任务';
        showNotification('done', '已完成：' + cp);
      } else if (res.state === 'ERROR') {
        var ce = (res.context && res.context.error) || '未知异常';
        showNotification('error', '异常：' + ce);
      }
      prevState = res.state;
    }

    // 桌宠自动隐藏编排：IDLE 空闲计时优雅隐藏；AI 活跃自动回归（仅窗口可见性，禁碰任务状态）
    // 用户主动隐藏（manualHidden）不自动回归，尊重显式 dismiss。
    if (res.state !== 'IDLE') {
      if (autoHidden && !manualHidden) revealFromIdle();
      cancelIdleHide();
    } else {
      armIdleHide();
    }
  }

  // 渲染合并：多处订阅（AppState / ExecutionChannel / ZZSSE）同帧只渲染一次，避免重复 Render
  var renderScheduled = false;
  function scheduleRender() {
    if (renderScheduled) return;
    renderScheduled = true;
    requestAnimationFrame(function () { renderScheduled = false; render(); });
  }

  // —— S4：Hover 状态气泡（数据全部来自 AppState + ExecutionChannel）——
  function updateBubble() {
    if (!bubble || !current) return;
    if (sbStatus) sbStatus.textContent = current.label;

    var cur = (ExecutionChannel && ExecutionChannel.getCurrent) ? ExecutionChannel.getCurrent() : null;
    var prompt = (cur && cur.prompt) ||
      (current.context && (current.context.prompt || current.context.goal || current.context.intent)) || '';
    if (sbTask) sbTask.textContent = prompt || '—';

    var phase = '—';
    if (current.state === 'EXECUTING') {
      if (cur && cur.steps && cur.steps.length) {
        var running = null;
        for (var i = 0; i < cur.steps.length; i++) if (cur.steps[i].status === 'running') { running = cur.steps[i]; break; }
        var last = cur.steps[cur.steps.length - 1];
        phase = (running ? running.label : (last ? last.label : '执行中')) + ' · ' + progressOf(cur.steps) + '%';
      } else {
        phase = (current.context && current.context.tool) || '执行中';
      }
    } else if (current.state === 'PLANNING') {
      phase = (current.context && (current.context.intent || current.context.goal)) || '规划中';
    } else if (current.state === 'THINKING') {
      phase = '思考中';
    } else if (current.state === 'COMPLETED') {
      phase = '已完成';
    } else if (current.state === 'ERROR') {
      phase = (current.context && current.context.error) || '异常';
    } else if (current.state === 'WAITING') {
      phase = '等待指令';
    } else if (current.state === 'OFFLINE') {
      phase = '离线';
    }
    if (sbPhase) sbPhase.textContent = phase;

    if (sbElapsed) {
      if (cur && cur.startedAt && current.state === 'EXECUTING') {
        sbElapsed.textContent = fmtElapsed(Date.now() - cur.startedAt);
      } else if (cur && cur.completedAt && cur.startedAt && current.state === 'COMPLETED') {
        sbElapsed.textContent = fmtElapsed(cur.completedAt - cur.startedAt);
      } else {
        sbElapsed.textContent = '';
      }
    }
  }

  function showBubble() {
    if (!bubble) return;
    if (menu && !menu.hidden) return; // 菜单打开时不抢位（气泡与菜单同处 top:128px）
    bubbleVisible = true;
    bubble.hidden = false;
    updateBubble();
    if (bubbleTimer) clearInterval(bubbleTimer);
    bubbleTimer = setInterval(updateBubble, 250); // 实时刷新耗时 / 阶段
    if (window.OverlayManager) window.OverlayManager.track('companion-bubble', {
      el: bubble, onClose: hideBubble, type: window.OverlayManager.OverlayType.MENU,
      trap: false, autofocus: false, keepZIndex: true
    });
  }
  function hideBubble() {
    if (window.OverlayManager) window.OverlayManager.untrack('companion-bubble');
    bubbleVisible = false;
    if (bubble) bubble.hidden = true;
    if (bubbleTimer) { clearInterval(bubbleTimer); bubbleTimer = null; }
  }

  // —— S5：完成 / 异常通知 ——
  // importance：'critical' 突破 DND（系统级异常/超时）；其余遵守 DND（与后端 NotificationPolicy 保持一致）。
  function showNotification(kind, text, importance, opts) {
    if (!notify) return;
    opts = opts || {};
    // B4：普通遵守 DND；critical 永远突破（后端已裁决可投递的消息，前端仅对 critical 破例）
    if (prefs.dnd && importance !== 'critical') return;
    notifyKind = kind;
    // P4：统一存在色语言——error 珊瑚红 / remind 琥珀 / done 青绿；remind 触发头像温和脉冲环
    var cls = 'companion-notify';
    if (kind === 'error') cls += ' cn-error';
    else if (kind === 'remind') cls += ' cn-remind';
    notify.className = cls;
    if (notifyIcon) notifyIcon.textContent = kind === 'error' ? '!' : (kind === 'remind' ? '»' : '✓');
    if (root) {
      if (kind === 'remind') root.classList.add('companion-root--remind');
      else root.classList.remove('companion-root--remind');
    }
    if (notifyText) notifyText.textContent = text;
    // B3：主动建议（非告警）提供「执行」入口，复用既有聊天执行链路，无新 API
    if (notifyAction) {
      if (opts.executable && opts.execContent) {
        notifyAction.hidden = false;
        notifyAction.onclick = function (e) {
          if (e) e.stopPropagation(); // 阻止冒泡到 notify 自身点击处理
          if (bridge && bridge.action) bridge.action({ type: 'execute-suggestion', content: opts.execContent });
          hideNotification();
        };
      } else {
        notifyAction.hidden = true;
        notifyAction.onclick = null;
      }
    }
    notify.hidden = false;
    if (notifyTimer) clearTimeout(notifyTimer);
    notifyTimer = setTimeout(hideNotification, 6000);
  }
  function hideNotification() {
    if (notify) notify.hidden = true;
    if (root) root.classList.remove('companion-root--remind');
    if (notifyTimer) { clearTimeout(notifyTimer); notifyTimer = null; }
  }

  // —— Phase 9 B4：小6接入主动消息（消费 proactive 通道；小6不自行判断，仅展示）——
  // 后端 NotificationPolicy 已完成 DND / quiet hours / importance 裁决；到达此处的消息即“可投递”。
  // 小6仅负责呈现：critical 突破本地 DND，其余遵守本地 DND（与后端保持同步）。
  function onProactiveMessage(raw) {
    var msg;
    try { msg = typeof raw === 'string' ? JSON.parse(raw) : raw; } catch (_) { return; }
    if (!msg || !msg.xiao6_event) return;

    // B4：主窗可见时，主动提示由主窗 Toast 呈现，Companion 不重复弹（仅在主窗隐藏的常驻表面呈现）
    if ((msg.xiao6_event === 'proactive' || msg.xiao6_event === 'proactive_result') && mainVisible) return;

    if (msg.xiao6_event === 'proactive') {
      var kind = msg.kind || 'goal';
      var content = msg.content || '';
      var imp = msg.importance || 'normal';
      // error / alert / anomaly 走异常样式；其余（建议/目标）走"提醒"样式（P4：remind 态，琥珀 + 头像脉冲）
      var style = (kind === 'error' || kind === 'alert' || kind === 'anomaly') ? 'error' : 'remind';
      // 告警类不可执行；其余（建议/目标）提供「执行」入口（B3）
      var executable = !(kind === 'error' || kind === 'alert' || kind === 'anomaly');
      showNotification(style, content, imp, { executable: executable, execContent: content });
    } else if (msg.xiao6_event === 'proactive_result') {
      // CREATE_GOAL 落地结果：告知用户已主动创建目标（不重复，引擎仅此处产生用户消息）
      if (msg.action === 'CREATE_GOAL') {
        var title = msg.title || ('目标 #' + (msg.goal_id || '?'));
        showNotification('done', '已主动创建目标：' + title);
      }
    }
    // proactive_decision / long_running 为遥测事件，小6仅展示不判断（已由 proactive 通道呈现）。
  }

  // —— B2：DND 权威来源在后端（NotificationPolicy）。经 IPC 桥同步/校准，禁止前端直连后端 API。——
  function syncDndToBackend(enabled) {
    if (bridge && bridge.syncDnd) bridge.syncDnd(enabled);
  }
  function loadDndFromBackend() {
    if (!bridge || !bridge.getDnd) return;
    Promise.resolve(bridge.getDnd())
      .then(function (s) {
        if (s && typeof s.dnd === 'boolean') {
          prefs.dnd = s.dnd; // 后端为权威，前端 DND 对齐
          if (ctlDnd) {
            ctlDnd.classList.toggle('is-on', prefs.dnd);
            ctlDnd.textContent = prefs.dnd ? '勿扰：开' : '勿扰模式';
          }
        }
      })
      .catch(function () {});
  }

  // —— S6：偏好持久化 ——
  function setPref(obj) {
    if (bridge && bridge.setPref) bridge.setPref(obj);
  }
  function applyPrefs(ui) {
    if (!ui) return;
    prefs.paused = !!ui.paused;
    prefs.dnd = !!ui.dnd;
    if (root) root.classList.toggle('companion-root--paused', prefs.paused);
    if (ctlPause) {
      ctlPause.classList.toggle('is-on', prefs.paused);
      ctlPause.textContent = prefs.paused ? '恢复动画' : '暂停动画';
    }
    if (ctlDnd) {
      ctlDnd.classList.toggle('is-on', prefs.dnd);
      ctlDnd.textContent = prefs.dnd ? '勿扰：开' : '勿扰模式';
    }
  }
  function togglePref(key) {
    prefs[key] = !prefs[key];
    applyPrefs({ paused: prefs.paused, dnd: prefs.dnd });
    setPref((key === 'paused') ? { paused: prefs.paused } : { dnd: prefs.dnd });
    if (key === 'dnd') syncDndToBackend(prefs.dnd); // B2：同步后端权威 DND
  }

  // Phase 10.2 任务一：应用主窗口推送的 OS 主题（仅视图层；头像色仍由状态驱动）
  function applyCompanionTheme(t) {
    if (!t) t = 'midnight';
    document.documentElement.setAttribute('data-theme', t);
  }

  // —— 自动隐藏（桌宠体验）：IDLE 空闲计时优雅淡出；AI 活跃自动回归；用户活动立即取消 ——
  // 纪律：仅经既有 companion:set-visible IPC 控制窗口可见性，不触碰任务状态 / AppState / EventBus。
  function cancelIdleHide() {
    if (idleTimer) { clearTimeout(idleTimer); idleTimer = null; }
    autoHidden = false;
    if (root) root.classList.remove('companion-root--hiding');
  }
  function armIdleHide() {
    if (idleTimer) { clearTimeout(idleTimer); idleTimer = null; }
    if (prefs.paused || autoHidden) return; // 暂停动画偏好下不自动隐藏
    idleTimer = setTimeout(function () {
      if (current && current.state === 'IDLE' && !prefs.paused) autoHide();
    }, IDLE_HIDE_MS);
  }
  function requestHide(persist) {
    hideBubble(); hideMenu();
    if (root) root.classList.add('companion-root--hiding');
    if (hideAnimTimer) clearTimeout(hideAnimTimer);
    hideAnimTimer = setTimeout(function () {
      if (bridge && bridge.setCompanionVisible) bridge.setCompanionVisible(false, !!persist);
    }, 480);
  }
  function autoHide() {
    if (autoHidden) return;
    autoHidden = true;
    requestHide(false); // 瞬态：不持久化 hidden，重启仍显示
  }
  function revealFromIdle() {
    if (!autoHidden) return;
    autoHidden = false;
    if (hideAnimTimer) { clearTimeout(hideAnimTimer); hideAnimTimer = null; }
    if (root) root.classList.remove('companion-root--hiding');
    if (bridge && bridge.setCompanionVisible) bridge.setCompanionVisible(true, true);
  }

  function showTip(text, ms) {
    if (!tip) return;
    tip.textContent = text;
    tip.hidden = false;
    tip.dataset.sticky = '1';
    if (tipTimer) clearTimeout(tipTimer);
    tipTimer = setTimeout(function () {
      tip.hidden = true;
      delete tip.dataset.sticky;
    }, ms || 4000);
  }

  function hideMenu() {
    if (window.OverlayManager) window.OverlayManager.untrack('companion-menu');
    if (menu) menu.hidden = true;
    if (bridge && bridge.setClickthrough) bridge.setClickthrough('auto'); // P0-3：关闭菜单恢复自动穿透
  }

  // Beta1.1 P0-1：命令气泡（就地下达指令，复用既有聊天执行链路，无新能力）
  function openCmdBubble() {
    if (!cmdBubble || !cmdInput) return;
    cmdBubble.hidden = false;
    if (window.OverlayManager) window.OverlayManager.track('companion-cmdBubble', {
      el: cmdBubble, onClose: closeCmdBubble, type: window.OverlayManager.OverlayType.MENU,
      trap: false, autofocus: false, keepZIndex: true
    });
    if (bridge && bridge.setClickthrough) bridge.setClickthrough(false); // P0-3：气泡打开期间强制接收
    setTimeout(function () { try { cmdInput.focus(); } catch (_) {} }, 30);
  }
  function closeCmdBubble() {
    if (window.OverlayManager) window.OverlayManager.untrack('companion-cmdBubble');
    if (cmdBubble) cmdBubble.hidden = true;
    if (cmdInput) cmdInput.value = '';
    if (bridge && bridge.setClickthrough) bridge.setClickthrough('auto'); // P0-3：关闭恢复自动穿透
  }
  function sendCmdBubble() {
    if (!cmdInput) return;
    var text = (cmdInput.value || '').trim();
    if (!text) { closeCmdBubble(); return; }
    // 复用既有聊天执行链路（Presentation Layer）：经 IPC 投递主窗 ZZChat.send
    if (bridge && bridge.action) bridge.action({ type: 'execute-suggestion', content: text });
    closeCmdBubble();
  }

  // P2：左键菜单 + 方向自适应（近屏幕下缘则向上展开；水平夹紧视口内）
  function toggleMenu() {
    if (!menu) return;
    if (menu.hidden) {
      menu.hidden = false;
      if (window.OverlayManager) window.OverlayManager.track('companion-menu', {
        el: menu, onClose: hideMenu, type: window.OverlayManager.OverlayType.MENU,
        trap: false, autofocus: false, keepZIndex: true
      });
      if (bridge && bridge.setClickthrough) bridge.setClickthrough(false); // P0-3：菜单打开强制接收鼠标
      var r = avatar ? avatar.getBoundingClientRect() : { left: 0, bottom: 0, top: 0 };
      var mh = menu.offsetHeight || 240;
      var mw = menu.offsetWidth || 168;
      var left = Math.min(Math.max(8, r.left), window.innerWidth - mw - 8);
      var openUp = (r.bottom + mh + 8 > window.innerHeight);
      menu.style.position = 'fixed';
      menu.style.left = left + 'px';
      if (openUp) { menu.style.top = 'auto'; menu.style.bottom = (window.innerHeight - r.top + 8) + 'px'; }
      else { menu.style.top = (r.bottom + 8) + 'px'; menu.style.bottom = 'auto'; }
    } else {
      menu.hidden = true;
      if (bridge && bridge.setClickthrough) bridge.setClickthrough('auto'); // P0-3：关闭恢复自动穿透
    }
  }

  // —— 动作路由：本地控制 vs 系统动作（IPC 桥）——
  function handleAction(action) {
    hideMenu();
    cancelIdleHide(); // 任意动作均为用户活动，取消空闲隐藏计时
    // 本地呈现控制（S6）
    if (action === 'toggle-pause') { togglePref('paused'); return; }
    if (action === 'toggle-dnd') { togglePref('dnd'); return; }
    if (action === 'hide') {
      manualHidden = true;      // 用户主动隐藏：不自动回归，尊重显式 dismiss
      requestHide(true);        // 手动隐藏：优雅淡出 + 持久化 hidden:true
      setPref({ hidden: true });
      return;
    }
    if (action === 'cmd-bubble') { openCmdBubble(); return; } // P0-1：就地下达指令
    // 系统动作：经 companion:action IPC 桥（Electron Desktop Layer），由主窗口转发既有系统
    // Sprint 5 职责收口：已移除 open-main / system-status / memory / project / settings
    // （页面导航 / 非 AI 状态 / 设置入口 不属于 Companion 的 AI 职责面，统一交 Command Palette / 导航脊柱）。
    switch (action) {
      case 'current-task':
      case 'quick-cmd':
        if (bridge && bridge.action) bridge.action({ type: action });
        break;
    }
  }

  function bind() {
    root = $('companionRoot');
    avatar = $('avatar');
    badge = $('statusBadge');
    tip = $('statusTip');
    menu = $('quickMenu');
    bubble = $('statusBubble');
    notify = $('notify');
    notifyText = $('notifyText');
    notifyIcon = $('notifyIcon');
    notifyAction = $('notifyAction');
    cmdBubble = $('cmdBubble');
    cmdInput = $('cmdBubbleInput');
    cmdSend = $('cmdBubbleSend');
    sbStatus = $('sbStatus');
    sbElapsed = $('sbElapsed');
    sbTask = $('sbTask');
    sbPhase = $('sbPhase');
    ctlPause = $('ctlPause');
    ctlDnd = $('ctlDnd');

    // ── Phase 10 P0：鼠标路由（Hover / Left / Double / Right / Drag 四条独立流，互不串）──
    // 设计：仅左键(0)在 Avatar 上发起拖拽/点击；右(2)经 contextmenu 走系统原生右键菜单，不触碰 quickMenu。
    var dragState = { active: false, moved: false, startX: 0, startY: 0, button: 0 };
    var DRAG_THRESHOLD = 6;
    var lastLeftTime = 0;
    var singleClickTimer = null;

    function openMain() { if (bridge && bridge.show) bridge.show(); }

    // 左键：区分单击（切换 quickMenu）与双击（打开主窗）
    function scheduleLeftClick() {
      var now = Date.now();
      if (now - lastLeftTime < 300) {
        if (singleClickTimer) { clearTimeout(singleClickTimer); singleClickTimer = null; }
        lastLeftTime = 0;
        openMain();
      } else {
        lastLeftTime = now;
        singleClickTimer = setTimeout(function () {
          singleClickTimer = null;
          toggleMenu(); // 左键：打开 / 关闭快捷菜单
        }, 280);
      }
    }

    if (avatar) {
      // 按下：仅左键发起拖拽（记录起点 + 指针捕获，保证移出头像仍跟手）
      avatar.addEventListener('pointerdown', function (e) {
        if (e.button !== 0) return; // 右键不发起拖拽（走 contextmenu）
        cancelIdleHide(); // 用户接触桌宠即取消空闲隐藏
        dragState.active = true;
        dragState.moved = false;
        dragState.startX = e.screenX;
        dragState.startY = e.screenY;
        dragState.button = e.button;
        try { avatar.setPointerCapture(e.pointerId); } catch (_) {}
      });
      avatar.addEventListener('pointermove', function (e) {
        if (!dragState.active) return;
        var dx = e.screenX - dragState.startX;
        var dy = e.screenY - dragState.startY;
        if (!dragState.moved && Math.sqrt(dx * dx + dy * dy) > DRAG_THRESHOLD) {
          dragState.moved = true;
          if (bridge && bridge.dragStart) bridge.dragStart(dragState.startX, dragState.startY);
        }
        if (dragState.moved && bridge && bridge.dragMove) bridge.dragMove(e.screenX, e.screenY);
      });
      avatar.addEventListener('pointerup', function (e) {
        if (!dragState.active) return;
        dragState.active = false;
        try { avatar.releasePointerCapture(e.pointerId); } catch (_) {}
        if (dragState.moved) {
          if (bridge && bridge.dragEnd) bridge.dragEnd();
          dragState.moved = false;
          return; // 拖拽完成，不触发点击
        }
        if (e.button === 0) scheduleLeftClick(); // 左键：菜单 / 双击主窗
      });
      avatar.addEventListener('pointercancel', function () {
        dragState.active = false;
        dragState.moved = false;
      });

      // 悬停 → 状态气泡（S4）+ 取消空闲隐藏；拖拽中不收起，保持可读性
      avatar.addEventListener('mouseenter', function () { cancelIdleHide(); showBubble(); });
      avatar.addEventListener('mouseleave', function () { if (!dragState.active) hideBubble(); });
    }

    // 右键 → 系统原生上下文菜单（独立事件流，与 quickMenu 分离；阻止 OS 默认菜单）
    if (root) root.addEventListener('contextmenu', function (e) {
      e.preventDefault();
      if (dragState.moved) return;
      if (bridge && bridge.openContextMenu) bridge.openContextMenu();
    });

    // 点击菜单项
    if (menu) menu.addEventListener('click', function (e) {
      var btn = e.target.closest('button[data-action]');
      if (btn) handleAction(btn.getAttribute('data-action'));
    });

    // Beta1.1 P0-1：命令气泡交互
    if (cmdSend) cmdSend.addEventListener('click', function (e) { e.stopPropagation(); sendCmdBubble(); });
    if (cmdInput) {
      cmdInput.addEventListener('keydown', function (e) { if (e.key === 'Enter') sendCmdBubble(); });
      cmdInput.addEventListener('click', function (e) { e.stopPropagation(); }); // 不触发收菜单逻辑
    }

    // 点击空白处收起菜单
    document.addEventListener('click', function (e) {
      cancelIdleHide(); // 任意点击均为用户活动
      // Root Cause A 修复：原守卫 e.target !== avatar 错误——点击 avatar 内部子元素
      // （halo/ring/core/SVG）时 e.target 并非 avatar 元素本身，导致左键菜单打开即被关闭、
      // 菜单项无法点击（仅展示未执行）。改为 !avatar.contains(e.target) 正确覆盖整个头像区域。
      if (menu && !menu.hidden && !menu.contains(e.target) && !avatar.contains(e.target)) hideMenu();
      // Beta1.1 P0-1：命令气泡打开时点击空白区关闭
      if (cmdBubble && !cmdBubble.hidden && !cmdBubble.contains(e.target)) closeCmdBubble();
    });

    // P2：ESC 关闭菜单 / 气泡 / 命令气泡 —— 已统一交由 OverlayManager 中央通道处理
    // （companion-menu / companion-bubble / companion-cmdBubble 在各自 show 时 track，
    //  ESC 仅关闭栈顶，符合 06 §2 单一键盘通道纪律）。

    // 点击通知 → 查看结果（S5）
    if (notify) notify.addEventListener('click', function () {
      hideNotification();
      if (notifyKind === 'done') {
        if (bridge && bridge.action) bridge.action({ type: 'completion-view' });
      } else if (bridge && bridge.show) {
        bridge.show();
      }
    });

    // 订阅既有状态源（不新建 EventBus，复用 AppState / ExecutionChannel / ZZSSE）
    // 经 scheduleRender 合并同帧多次触发，避免重复 Render（任务五性能优化）
    if (AppState && AppState.subscribe) AppState.subscribe('*', scheduleRender);
    if (ExecutionChannel && ExecutionChannel.subscribe) ExecutionChannel.subscribe(scheduleRender);
    if (ZZSSE && ZZSSE.onState) ZZSSE.onState(function () { scheduleRender(); });

    // Phase 9 B4：订阅 SSE 主动消息（proactive / proactive_result），小6仅展示不判断
    if (ZZSSE && ZZSSE.onMessage) ZZSSE.onMessage(onProactiveMessage);

    // Root Cause B 修复：companion 窗口的 ExecutionChannel 实例需自行订阅 SSE 的
    // tool_start/tool_end——主窗口 app.js 的喂入仅作用于主窗口 window 实例，不跨窗口共享，
    // 导致 companion 窗口 ExecutionChannel 永远为空，Hover 气泡（updateBubble 读
    // ExecutionChannel.getCurrent）只能显示占位。复用既有 ZZSSE 单例 + ExecutionChannel API，
    // 不新建任何 Runtime / EventBus / State System（严格守 Phase 8/9 纪律）。
    if (ZZSSE && ZZSSE.onMessage && ExecutionChannel) {
      ZZSSE.onMessage(function (raw) {
        try {
          var m = (typeof raw === 'string') ? JSON.parse(raw) : raw;
          if (!m || !m.xiao6_event) return;
          if (m.xiao6_event === 'tool_start' && ExecutionChannel.onToolStart) ExecutionChannel.onToolStart(m);
          else if (m.xiao6_event === 'tool_end' && ExecutionChannel.onToolEnd) ExecutionChannel.onToolEnd(m);
        } catch (_) {}
      });
    }

    // 拉取已持久化偏好（companion.json → preload → 此处应用）
    if (bridge && bridge.getPrefs) {
      Promise.resolve(bridge.getPrefs())
        .then(function (s) { applyPrefs(s && s.ui); })
        .catch(function () {});
    }
    // B2：从后端校准权威 DND 状态（NotificationPolicy 单一来源）
    loadDndFromBackend();

    // B4：订阅主窗可见性（主动提示去重：主窗可见时由主窗 Toast 呈现，Companion 不重复弹）
    if (bridge && bridge.onMainVisible) bridge.onMainVisible(function (v) { mainVisible = v; });

    // Phase 10.2 任务一：订阅主窗口主题推送 + 首屏拉取（Presentation-only）
    if (bridge && bridge.onTheme) bridge.onTheme(applyCompanionTheme);
    if (bridge && bridge.getTheme) {
      Promise.resolve(bridge.getTheme()).then(applyCompanionTheme).catch(function () {});
    }

    // 桌宠经托盘/双击被主进程重新显示时，渲染进程不知情；焦点进入即清除淡出态与隐藏标记，恢复常态
    window.addEventListener('focus', function () {
      autoHidden = false;
      manualHidden = false;
      if (root) root.classList.remove('companion-root--hiding');
    });

    render();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bind);
  } else {
    bind();
  }
})();
