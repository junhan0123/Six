/*
 * command-dock.js — Phase 10.1 P7 · Command Dock（统一输入）
 * ----------------------------------------------------------------------------
 * 五种输入：文本 / 语音 / 拖文件 / 截图 / 快捷命令。全部复用既有 handler：
 *   - 文本 → 既有 #input / #btnSend（或 zz:command 事件钩子）
 *   - 语音 → zz:voice-toggle（既有 wakeword/asr 监听）
 *   - 拖文件 → zz:dock-file（file_read 工具）
 *   - 截图 → zz:dock-screenshot（capture_screen 能力）
 *   - 快捷 → command-palette 打开
 * 纪律：仅派发既有事件/调用既有入口；不新建后端线缆、不写状态。
 */
(function (global) {
  'use strict';

  var root = null, inputEl = null, listening = false;

  function sendText(text) {
    if (!text) return;
    var inp = document.getElementById('input');
    var btn = document.getElementById('btnSend');
    if (inp && btn) { inp.value = text; btn.click(); return; }
    // 兜底：派发钩子事件
    global.dispatchEvent(new CustomEvent('zz:command', { detail: { text: text } }));
  }

  // GAP A 收口：Command Dock 作为指向原生 Agent Runtime 的显式权威入口，
  // 复用既有 Intent Gateway 线缆（与 Ctrl+K 同路），不新建后端/事件、不绕过 execute_tool。
  function sendCommand(text) {
    if (!text) return;
    if (global.ZZIntentGateway && typeof global.ZZIntentGateway.dispatch === 'function') {
      global.ZZIntentGateway.dispatch(text);   // → POST /api/agent/intent → run_intent_gateway → submit_goal
      return;
    }
    sendText(text); // 兜底：Intent Gateway 不可用时退回传统聊天路径
  }

  function build() {
    root.innerHTML =
      '<div class="os-dock-bar" id="osDockBar">' +
        '<button type="button" class="os-dock-btn" id="osDockVoice" title="语音"><svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-mic"/></svg></button>' +
        '<input type="text" id="osDockInput" placeholder="向小6下达指令，或拖入文件 / 截图…" />' +
        '<button type="button" class="os-dock-btn" id="osDockFile" title="拖文件到此"><svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-paperclip"/></svg></button>' +
        '<button type="button" class="os-dock-btn" id="osDockShot" title="截图"><svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-camera"/></svg></button>' +
        '<button type="button" class="os-dock-btn" id="osDockQuick" title="快捷命令"><svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-bolt"/></svg></button>' +
        '<button type="button" class="os-dock-btn send" id="osDockSend" title="发送"><svg class="zz-icon stroke" aria-hidden="true"><use href="#zz-send"/></svg></button>' +
      '</div>' +
      '<div class="os-dock-hint">Ctrl/Cmd+U 打开宇宙视图 · ⌘/Ctrl+K 快捷命令 · 支持拖拽文件</div>';
    inputEl = root.querySelector('#osDockInput');
    var bar = root.querySelector('#osDockBar');

    inputEl.addEventListener('keydown', function (e) { if (e.key === 'Enter') { sendCommand(inputEl.value); inputEl.value = ''; } });
    root.querySelector('#osDockSend').addEventListener('click', function () { sendCommand(inputEl.value); inputEl.value = ''; });

    root.querySelector('#osDockVoice').addEventListener('click', function () {
      listening = !listening;
      this.classList.toggle('listening', listening);
      global.dispatchEvent(new CustomEvent('zz:voice-toggle', { detail: { listening: listening } }));
    });

    root.querySelector('#osDockFile').addEventListener('click', function () {
      global.dispatchEvent(new CustomEvent('zz:dock-file', { detail: {} }));
    });

    root.querySelector('#osDockShot').addEventListener('click', function () {
      global.dispatchEvent(new CustomEvent('zz:dock-screenshot', { detail: {} }));
      sendText('截图当前屏幕');
    });

    root.querySelector('#osDockQuick').addEventListener('click', function () {
      if (global.ZZCommandPalette && global.ZZCommandPalette.open) global.ZZCommandPalette.open();
      else global.dispatchEvent(new CustomEvent('zz:command-palette', { detail: {} }));
    });

    // 拖文件
    ['dragenter', 'dragover'].forEach(function (ev) {
      bar.addEventListener(ev, function (e) { e.preventDefault(); root.classList.add('dragover'); });
    });
    ['dragleave', 'drop'].forEach(function (ev) {
      bar.addEventListener(ev, function (e) { e.preventDefault(); root.classList.remove('dragover'); });
    });
    bar.addEventListener('drop', function (e) {
      var files = e.dataTransfer && e.dataTransfer.files;
      if (files && files.length) {
        var names = [];
        for (var i = 0; i < files.length; i++) names.push(files[i].name);
        global.dispatchEvent(new CustomEvent('zz:dock-file', { detail: { files: Array.prototype.slice.call(files).map(function (f) { return { name: f.name, size: f.size }; }) } }));
        sendText('读取文件：' + names.join('、'));
        inputEl.value = '';
      }
    });
  }

  function init(container) {
    root = container;
    if (!root) return;
    build();
  }

  global.CommandDock = { init: init, sendCommand: sendCommand, sendText: sendText };
})(typeof window !== 'undefined' ? window : globalThis);
