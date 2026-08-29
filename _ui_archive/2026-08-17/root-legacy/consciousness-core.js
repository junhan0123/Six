/*
 * consciousness-core.js — Phase 10.1 P6 · AI Consciousness Core
 * ----------------------------------------------------------------------------
 * 视觉：中央意识核 + 环绕神经节点 + 动态连线（神经网络意象）。禁太阳、禁天文轨道。
 * 数据：仅消费 AvatarState.deriveFromGlobals()（8 态）+ AppState（活跃目标/智能体数）。
 * 纪律：纯 Presentation Layer；不持有状态、不建事件总线/运行时；仅 rAF 渲染。
 */
(function (global) {
  'use strict';

  var TWO_PI = Math.PI * 2;
  var nodes = [];
  var core = null;
  var canvas = null, ctx = null, raf = 0;
  var W = 0, H = 0, DPR = 1;
  var lastStateCheck = 0;
  var mode = 'IDLE';
  var modeColor = '#5fb3c8';
  var energy = 0;        // 0..1 当前活跃度（平滑）
  var energyTarget = 0.25;
  var bloom = 0;         // 完成绽放衰减
  var fracture = 0;      // 异常裂隙衰减
  var rot = 0;
  var reduced = false;
  // Phase 10.2 任务五：性能优化（仅 Presentation Layer）
  var paused = false;        // 页面隐藏时停 rAF
  var destroyed = false;     // 销毁标记
  var lastFrame = 0;
  var FRAME_MS = 33;         // 限帧 ~30fps：draw call 减半，CPU/GPU 占用显著下降

  function pickColor(state) {
    var m = (global.AvatarState && global.AvatarState.META) ? global.AvatarState.META[state] : null;
    return (m && m.color) || '#5fb3c8';
  }

  function readState() {
    var st = (global.AvatarState && global.AvatarState.deriveFromGlobals)
      ? global.AvatarState.deriveFromGlobals() : { state: 'IDLE', color: '#5fb3c8' };
    var newMode = (st && st.state) || 'IDLE';
    modeColor = (st && st.color) || pickColor(newMode);
    if (newMode !== mode) {
      if (newMode === 'COMPLETED') bloom = 1;
      if (newMode === 'ERROR') fracture = 1;
      mode = newMode;
    }
    // 活跃度目标：按状态设能量
    var t = { IDLE: 0.22, WAITING: 0.3, THINKING: 0.62, PLANNING: 0.55,
      EXECUTING: 0.9, COMPLETED: 0.7, ERROR: 0.5, OFFLINE: 0.08 }[mode] || 0.25;
    energyTarget = (mode === 'OFFLINE') ? 0.06 : t;
  }

  function resize() {
    if (!canvas) return;
    var r = canvas.getBoundingClientRect();
    DPR = Math.min(global.devicePixelRatio || 1, 2);
    W = Math.max(1, Math.floor(r.width)); H = Math.max(1, Math.floor(r.height));
    canvas.width = W * DPR; canvas.height = H * DPR;
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
  }

  function build() {
    nodes = [];
    var cx = W / 2, cy = H / 2;
    core = { x: cx, y: cy, r: Math.min(W, H) * 0.07 };
    var n = Math.max(34, Math.min(72, Math.floor((W * H) / 9000)));
    for (var i = 0; i < n; i++) {
      var ang = (i / n) * TWO_PI + Math.random() * 0.4;
      var rad = core.r * (1.6 + Math.random() * 2.4);
      nodes.push({
        baseAng: ang, baseRad: rad,
        ang: ang, rad: rad,
        x: 0, y: 0, phase: Math.random() * TWO_PI,
        sp: 0.2 + Math.random() * 0.5,
        size: 1.2 + Math.random() * 2.2,
        link: []
      });
    }
    // 预连：每个节点连最近的 2~3 个
    for (var a = 0; a < nodes.length; a++) {
      var dists = [];
      for (var b = 0; b < nodes.length; b++) {
        if (a === b) continue;
        var dx = Math.cos(nodes[a].baseAng) * nodes[a].baseRad - Math.cos(nodes[b].baseAng) * nodes[b].baseRad;
        var dy = Math.sin(nodes[a].baseAng) * nodes[a].baseRad - Math.sin(nodes[b].baseAng) * nodes[b].baseRad;
        dists.push({ b: b, d: dx * dx + dy * dy });
      }
      dists.sort(function (p, q) { return p.d - q.d; });
      var k = 2; // 每节点 2 条连线（原 2~3）：减少 ~25% 描边调用，视觉仍密集
      for (var j = 0; j < k; j++) nodes[a].link.push(dists[j].b);
    }
  }

  function hex(c) {
    // #rrggbb → [r,g,b]
    if (c[0] !== '#' || c.length < 7) return [95, 179, 200];
    return [parseInt(c.slice(1, 3), 16), parseInt(c.slice(3, 5), 16), parseInt(c.slice(5, 7), 16)];
  }

  function frame(ts) {
    if (paused || destroyed) { raf = 0; return; } // 页面隐藏/销毁：停 rAF，省 CPU/GPU
    raf = global.requestAnimationFrame(frame);
    if (!ctx) return;
    if (ts - lastFrame < FRAME_MS) return;          // 限帧 ~30fps：draw call 减半
    lastFrame = ts;
    if (ts - lastStateCheck > 350) { readState(); lastStateCheck = ts; }
    energy += (energyTarget - energy) * 0.04;
    bloom *= 0.96; fracture *= 0.95;
    rot += (0.0008 + energy * 0.004) * (mode === 'OFFLINE' ? 0.3 : 1);

    var cx = W / 2, cy = H / 2;
    ctx.clearRect(0, 0, W, H);
    var rgb = hex(modeColor);
    var colorStr = 'rgb(' + rgb[0] + ',' + rgb[1] + ',' + rgb[2] + ')'; // 预计算纯色，配合 globalAlpha 免逐线字符串分配
    var speed = (mode === 'THINKING' || mode === 'EXECUTING') ? 1 : 0.5;

    // 连线（globalAlpha + 纯色：去除每线 rgba() 字符串分配，~180 次/帧 → 0 分配）
    ctx.lineWidth = 1;
    ctx.globalAlpha = 1;
    for (var i = 0; i < nodes.length; i++) {
      var nd = nodes[i];
      nd.ang = nd.baseAng + rot * nd.sp * speed;
      var rad = nd.baseRad * (1 + 0.06 * Math.sin(ts * 0.0006 * nd.sp + nd.phase));
      if (mode === 'PLANNING') rad *= 1.12; // 规划：网络扩张
      if (mode === 'EXECUTING') rad *= 1 + 0.05 * energy;
      nd.x = cx + Math.cos(nd.ang) * rad;
      nd.y = cy + Math.sin(nd.ang) * rad;
      for (var li = 0; li < nd.link.length; li++) {
        var t = nodes[nd.link[li]];
        if (!t) continue;
        var a = 0.05 + energy * 0.28;
        if (mode === 'THINKING') a += 0.06 * (0.5 + 0.5 * Math.sin(ts * 0.004 + nd.phase));
        ctx.globalAlpha = a;
        ctx.strokeStyle = colorStr;
        ctx.beginPath(); ctx.moveTo(nd.x, nd.y); ctx.lineTo(t.x, t.y); ctx.stroke();
      }
    }
    // 节点
    ctx.globalAlpha = 1;
    for (var m = 0; m < nodes.length; m++) {
      var n2 = nodes[m];
      var r = n2.size * (1 + energy * 0.6);
      ctx.globalAlpha = 0.5 + energy * 0.5;
      ctx.fillStyle = colorStr;
      ctx.beginPath(); ctx.arc(n2.x, n2.y, r, 0, TWO_PI); ctx.fill();
    }
    ctx.globalAlpha = 1;
    // 中央核
    var cr = core.r * (1 + 0.08 * Math.sin(ts * 0.0018) + energy * 0.12 + bloom * 0.5);
    var grad = ctx.createRadialGradient(cx, cy, cr * 0.2, cx, cy, cr * 2.4);
    var coreRGB = (mode === 'OFFLINE') ? [120, 130, 150] : rgb;
    grad.addColorStop(0, 'rgba(' + coreRGB[0] + ',' + coreRGB[1] + ',' + coreRGB[2] + ',0.95)');
    grad.addColorStop(0.4, 'rgba(' + coreRGB[0] + ',' + coreRGB[1] + ',' + coreRGB[2] + ',' + (0.25 + energy * 0.3).toFixed(3) + ')');
    grad.addColorStop(1, 'rgba(' + coreRGB[0] + ',' + coreRGB[1] + ',' + coreRGB[2] + ',0)');
    ctx.fillStyle = grad;
    ctx.beginPath(); ctx.arc(cx, cy, cr * 2.4, 0, TWO_PI); ctx.fill();
    // 核心实心点
    ctx.fillStyle = 'rgba(' + Math.min(255, coreRGB[0] + 40) + ',' + Math.min(255, coreRGB[1] + 40) + ',' + Math.min(255, coreRGB[2] + 40) + ',0.95)';
    ctx.beginPath(); ctx.arc(cx, cy, cr * 0.55, 0, TWO_PI); ctx.fill();

    // 异常裂隙（红色闪线）
    if (fracture > 0.02) {
      ctx.strokeStyle = 'rgba(255,107,107,' + (fracture * 0.8).toFixed(3) + ')';
      ctx.lineWidth = 2;
      for (var f = 0; f < 5; f++) {
        var fa = Math.random() * TWO_PI;
        ctx.beginPath(); ctx.moveTo(cx, cy);
        ctx.lineTo(cx + Math.cos(fa) * cr * (2 + Math.random() * 2), cy + Math.sin(fa) * cr * (2 + Math.random() * 2));
        ctx.stroke();
      }
    }
  }

  function init(el) {
    canvas = el;
    if (!canvas || !canvas.getContext) return;
    destroyed = false;
    ctx = canvas.getContext('2d');
    reduced = (global.matchMedia && global.matchMedia('(prefers-reduced-motion: reduce)').matches) ||
      (document.body && document.body.classList.contains('reduced-motion'));
    resize(); build();
    global.addEventListener('resize', function () { resize(); build(); });
    // 页面隐藏即停 rAF（节电/省 CPU）；恢复可见再重启
    document.addEventListener('visibilitychange', function () {
      paused = document.hidden;
      if (!paused && !reduced && !destroyed && !raf) raf = global.requestAnimationFrame(frame);
    });
    readState();
    if (reduced) { drawStatic(); return; }
    raf = global.requestAnimationFrame(frame);
  }

  function drawStatic() {
    // 减少动效：仅画一帧静态
    var cx = W / 2, cy = H / 2, rgb = hex(modeColor);
    ctx.clearRect(0, 0, W, H);
    for (var i = 0; i < nodes.length; i++) {
      var nd = nodes[i]; nd.x = cx + Math.cos(nd.baseAng) * nd.baseRad; nd.y = cy + Math.sin(nd.baseAng) * nd.baseRad;
    }
    for (var a = 0; a < nodes.length; a++) { var n = nodes[a];
      for (var li = 0; li < n.link.length; li++) { var t = nodes[n.link[li]]; if (!t) continue;
        ctx.strokeStyle = 'rgba(' + rgb[0] + ',' + rgb[1] + ',' + rgb[2] + ',0.12)'; ctx.beginPath(); ctx.moveTo(n.x, n.y); ctx.lineTo(t.x, t.y); ctx.stroke(); } }
    ctx.fillStyle = modeColor; ctx.beginPath(); ctx.arc(cx, cy, core.r, 0, TWO_PI); ctx.fill();
  }

  function destroy() { destroyed = true; paused = true; if (raf) global.cancelAnimationFrame(raf); raf = 0; }

  global.ConsciousnessCore = { init: init, destroy: destroy };
})(typeof window !== 'undefined' ? window : globalThis);
