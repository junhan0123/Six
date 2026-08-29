/* ============================================================
 * execution-channel.js — Phase 6 Order 7 · Execution Channel
 * 纯前端、只读事件、无后端直连。与 runtime-visualization.js 同纪律。
 *
 * 职责：把「执行过程」从「用户对话」中解耦出来，汇聚到独立的
 *       Execution Monitor 面板。不写聊天窗口、不创建新 Runtime/
 *       Memory/EventBus，仅消费既有 tool_start/tool_end 系统事件。
 * ============================================================ */
(() => {
  'use strict';

  // 工具中文名（仅展示用，非业务逻辑；与 app.js TOOL_LABELS 同源口径）
  const TOOL_LABELS = {
    get_time: '查询时间', calculator: '计算', note_save: '记笔记',
    note_list: '翻笔记', profile_set: '记住你', profile_get: '回忆你',
    reminder_set: '设提醒', reminder_list: '看提醒',
    set_task: '记任务', update_task_step: '更新进度', complete_task: '完成任务', task_list: '看任务',
    file_read: '读取文件', file_list: '列文件', file_write: '写文件',
    run_shell: '执行命令', session_run: '会话命令',
    web_fetch: '抓取网页', web_search: '联网搜索',
    media_generate: '生成媒体', social_send: '发消息', asr_transcribe: '语音识别',
    get_weather: '查天气', get_hotspots: '看热点', open_hotspot_panel: '开热点大屏',
    play_video: '放视频', install_software: '安装软件',
  };

  let _id = 0;
  const executions = [];
  let current = null;
  const subs = [];

  function uid() { return 'exec-' + (++_id) + '-' + Date.now().toString(36); }

  function notify() {
    for (const cb of subs) { try { cb(getSnapshot()); } catch (e) { console.warn('[ExecutionChannel]', e); } }
  }

  function getSnapshot() {
    return {
      current: current ? Object.assign({}, current, { steps: current.steps.map(s => Object.assign({}, s)) }) : null,
      history: executions.map(e => Object.assign({}, e, { steps: e.steps.map(s => Object.assign({}, s)) })),
    };
  }

  const ExecutionChannel = {
    /* ── 生命周期（前端推导的边界事件，不新增后端线缆事件） ── */
    startExecution(prompt) {
      if (current && current.status === 'running') {
        // 连续请求：先把上一个收尾，避免 episode 串台
        current.status = 'completed';
        current.completedAt = current.completedAt || Date.now();
      }
      current = {
        id: uid(),
        prompt: typeof prompt === 'string' ? prompt : '',
        status: 'running',
        startedAt: Date.now(),
        completedAt: null,
        steps: [],
      };
      executions.push(current);
      if (executions.length > 50) executions.shift(); // 仅内存，防无限增长
      notify();
      return current.id;
    },
    onToolStart(ev) {
      if (!current || current.status !== 'running') this.startExecution('');
      const tool = (ev && ev.tool) || 'unknown';
      const step = {
        tool,
        label: TOOL_LABELS[tool] || tool,
        args: ev ? ev.args : undefined,
        status: 'running',
        result: undefined,
        startedAt: Date.now(),
        completedAt: null,
      };
      current.steps.push(step);
      notify();
    },
    onToolEnd(ev) {
      if (!current) return;
      const tool = (ev && ev.tool) || 'unknown';
      // 匹配最后一个同名且未完成的 step（多轮同工具也正确）
      for (let i = current.steps.length - 1; i >= 0; i--) {
        const s = current.steps[i];
        if (s.tool === tool && s.status !== 'completed') {
          s.status = 'completed';
          s.result = ev ? ev.result : undefined;
          s.completedAt = Date.now();
          notify();
          return;
        }
      }
      // 异常：未收到 start 就收到 end —— 补一条已完成记录，保证可回溯
      current.steps.push({
        tool, label: TOOL_LABELS[tool] || tool,
        args: undefined, status: 'completed',
        result: ev ? ev.result : undefined,
        startedAt: Date.now(), completedAt: Date.now(),
      });
      notify();
    },
    completeExecution() {
      if (current && current.status === 'running') {
        current.status = 'completed';
        current.completedAt = Date.now();
        notify();
      }
    },
    /* ── 只读快照 / 订阅 ── */
    getExecutions() { return getSnapshot().history; },
    getCurrent() { return getSnapshot().current; },
    subscribe(cb) { if (typeof cb === 'function') subs.push(cb); return () => {
      const i = subs.indexOf(cb); if (i >= 0) subs.splice(i, 1);
    }; },
    /* ── Phase 8：聚焦执行监视（用于 Companion 的“当前任务 / 完成查看”）── */
    focus() {
      this.mount();
      const p = this._panel;
      if (!p) return;
      try { p.scrollIntoView({ block: 'center' }); } catch (_) {}
      const prev = p.style.boxShadow;
      p.style.boxShadow = '0 0 0 3px rgba(86,211,100,0.85)';
      setTimeout(() => { p.style.boxShadow = prev; }, 1200);
    },
    /* ── 渲染：Execution Monitor 面板 ── */
    mount() {
      if (typeof document === 'undefined') return null;
      let panel = document.getElementById('execution-monitor');
      if (panel) return panel;
      panel = document.createElement('div');
      panel.id = 'execution-monitor';
      panel.className = 'exec-monitor';
      panel.innerHTML =
        '<div class="em-bar">' +
          '<span class="em-title"><span class="em-dot"></span>执行监视 · Execution</span>' +
          '<span class="em-count" id="emCount">0</span>' +
        '</div>' +
        '<div class="em-body" id="emBody"></div>';
      (document.body || document.documentElement).appendChild(panel);
      this._panel = panel;
      this._body = panel.querySelector('#emBody');
      this._count = panel.querySelector('#emCount');
      this.subscribe(() => this.render());
      this.render();
      return panel;
    },
    render() {
      if (!this._body) return;
      const snap = getSnapshot();
      const cur = snap.current;
      const steps = cur ? cur.steps : [];
      this._count.textContent = String(steps.length);
      if (!steps.length) {
        this._body.innerHTML = '<div class="em-empty">暂无执行活动</div>';
        return;
      }
      let html = '<div class="em-ep' + (cur.status === 'running' ? ' running' : '') + '">';
      html += '<div class="em-ep-head">' +
                (cur.status === 'running' ? '执行中' : '已完成') +
                (cur.prompt ? ' · ' + escapeHtml(cur.prompt.slice(0, 28)) : '') +
              '</div>';
      for (const s of steps) {
        const ico = s.status === 'running' ? '<span class="em-spin"></span>' : '<span class="em-ok">✓</span>';
        const res = s.result ? escapeHtml(String(s.result).slice(0, 90)) : '';
        html += '<div class="em-step ' + s.status + '">' +
                  '<span class="em-ico">' + ico + '</span>' +
                  '<div class="em-step-main">' +
                    '<div class="em-step-label">' + escapeHtml(s.label) + '</div>' +
                    (res ? '<div class="em-step-res">' + res + '</div>' : '') +
                  '</div>' +
                '</div>';
      }
      html += '</div>';
      this._body.innerHTML = html;
    },
  };

  function escapeHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, c =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }

  if (typeof window !== 'undefined') window.ExecutionChannel = ExecutionChannel;

  /* ── 自挂载（与 runtime-visualization.js 同模式） ── */
  function boot() {
    if (typeof window === 'undefined' || !window.document) return;
    if (document.readyState === 'loading') window.addEventListener('DOMContentLoaded', () => ExecutionChannel.mount());
    else ExecutionChannel.mount();
  }
  boot();

  if (typeof module !== 'undefined' && module.exports) module.exports = ExecutionChannel;
})();
