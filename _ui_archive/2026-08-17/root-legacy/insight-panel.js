/*
 * insight-panel.js — Phase 10.1 P8 · Insight（接入 Phase 9 主动智能）
 * ----------------------------------------------------------------------------
 * Phase 10.2 任务四：主动建议升级为「真正可点击执行的 Notification」，不再是静默增长日志。
 *
 * 数据：ZZSSE 系统事件 proactive(kind,content,importance) + proactive_result(goal_id,title,status)。
 * 后端 proactive.py 真实产出；本模块仅展示 + 提供「执行」入口，不自造建议、不自判
 * （与 companion.onProactiveMessage 同纪律）。
 *
 * 纪律（最高约束）：
 *   - 仅订阅 ZZSSE.onMessage；不写状态、不建事件总线、不新增 API / Runtime。
 *   - 「执行」复用既有聊天通道：填充 #input 并触发 #btnSend（send()），绝不直连后端新接口。
 *   - 后端 NotificationPolicy 已完成 DND / quiet hours / importance 裁决；到达此处的消息即“可投递”。
 */
(function (global) {
  'use strict';

  var host = null;
  var MAX = 6; // 同屏最多通知数，超出丢弃最旧

  // 经既有聊天通道执行建议（禁新 API / 禁新 Runtime）
  function executeSuggestion(content) {
    var input = document.getElementById('input');
    var btn = document.getElementById('btnSend');
    if (input && btn) {
      input.value = content || '';
      btn.click(); // 触发既有 send()：真实执行路径，无新增能力
    }
  }

  function dismiss(el) {
    if (!el) return;
    if (el._t) clearTimeout(el._t);
    el.classList.add('pt-leaving');
    setTimeout(function () { if (el.parentNode) el.parentNode.removeChild(el); }, 280);
  }

  function addToast(opts) {
    if (!host) return;
    var importance = opts.importance || 'normal';
    var el = document.createElement('div');
    el.className = 'proactive-toast imp-' + importance;

    // 头部：类型 + 优先级 + 关闭
    var head = document.createElement('div');
    head.className = 'pt-head';
    var kind = document.createElement('span');
    kind.className = 'pt-kind';
    kind.textContent = opts.kind || '建议';
    var imp = document.createElement('span');
    imp.className = 'pt-imp';
    imp.textContent = (importance === 'critical') ? '紧急' : (importance === 'high' ? '高优先' : '提示');
    var close = document.createElement('button');
    close.className = 'pt-close';
    close.type = 'button';
    close.setAttribute('aria-label', '关闭');
    close.textContent = '×';
    close.addEventListener('click', function () { dismiss(el); });
    head.appendChild(kind);
    head.appendChild(imp);
    head.appendChild(close);

    // 正文
    var body = document.createElement('div');
    body.className = 'pt-body';
    body.textContent = opts.content || '（空）';

    el.appendChild(head);
    el.appendChild(body);

    // 动作区：可执行的建议提供「执行 / 忽略」；告警类仅信息提示，无执行按钮
    if (opts.executable) {
      var actions = document.createElement('div');
      actions.className = 'pt-actions';
      var ignore = document.createElement('button');
      ignore.className = 'pt-dismiss';
      ignore.type = 'button';
      ignore.textContent = '忽略';
      ignore.addEventListener('click', function () { dismiss(el); });
      var exec = document.createElement('button');
      exec.className = 'pt-exec';
      exec.type = 'button';
      exec.textContent = '执行';
      exec.addEventListener('click', function () {
        executeSuggestion(opts.content);
        dismiss(el);
      });
      actions.appendChild(ignore);
      actions.appendChild(exec);
      el.appendChild(actions);
      // 自动消失：紧急常驻（需手动关闭）；其余 12s
      if (importance !== 'critical') el._t = setTimeout(function () { dismiss(el); }, 12000);
    } else {
      el._t = setTimeout(function () { dismiss(el); }, 8000);
    }

    host.insertBefore(el, host.firstChild);
    while (host.children.length > MAX) {
      var last = host.lastChild;
      if (last && last._t) clearTimeout(last._t);
      if (last && last.parentNode) last.parentNode.removeChild(last);
    }
  }

  function onMessage(raw) {
    var m;
    try { m = (typeof raw === 'string') ? JSON.parse(raw) : raw; } catch (e) { return; }
    if (!m || !m.xiao6_event) return;
    if (m.xiao6_event === 'proactive') {
      // 告警类（error/alert/anomaly）仅提示，不提供“执行”（非指令）
      var kind = m.kind || '建议';
      var executable = !(kind === 'error' || kind === 'alert' || kind === 'anomaly');
      addToast({
        kind: kind,
        content: m.content,
        importance: m.importance,
        executable: executable,
      });
    } else if (m.xiao6_event === 'proactive_result') {
      if (m.action === 'CREATE_GOAL') {
        addToast({
          kind: '目标',
          content: '已主动创建目标：' + (m.title || m.goal_id || ''),
          importance: 'normal',
          executable: false,
        });
      }
    }
  }

  function init(container) {
    host = container;
    if (!host) return;
    // 通知承载体（替代旧增长日志 os-insight-list）：真 Notification，可点击执行
    host.innerHTML = '<div class="proactive-toast-host" id="proactiveToastHost"></div>';
    host = host.querySelector('#proactiveToastHost');
    if (global.ZZSSE && global.ZZSSE.onMessage) global.ZZSSE.onMessage(onMessage);
  }

  global.InsightPanel = { init: init };
})(typeof window !== 'undefined' ? window : globalThis);
