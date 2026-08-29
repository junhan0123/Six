/* ═══════════════════════════════════════════════════════════════════
   小6 · 粒子语音球（dyna-orb.js）
   采用最早的粒子点阵球基因（voice-orb-simple 的 Fibonacci 采样 + 正弦噪声位移 + 深度着色 + 自转/俯仰）
   整体白色水晶粒子，状态仅以极淡冷色调区分
   状态：idle/listening/recognizing/thinking/processing/executing/speaking/done/error
   接口：window.ZZDynaOrb（与 dyna-orb.html / dyna-orb-voice.js 契约一致）
   ═══════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  // ── 球面采样（Fibonacci） ──
  function fibSphere(n, radius) {
    var pts = [], golden = Math.PI * (3 - Math.sqrt(5));
    for (var i = 0; i < n; i++) {
      var y = 1 - (i / (n - 1)) * 2;
      var r = Math.sqrt(Math.max(0, 1 - y * y));
      var theta = golden * i;
      pts.push({ x: Math.cos(theta) * r * radius, y: y * radius, z: Math.sin(theta) * r * radius });
    }
    return pts;
  }

  var BASE_OUTER = fibSphere(3200, 1.0);   // 外层 3200 点
  var BASE_INNER = fibSphere(1200, 0.88);  // 内层 1200 点（更小半径）

  // ── 正弦噪声（表面起伏） ──
  function sn(x, y, z, t) {
    return (
      Math.sin(x * 2.3 + t * 1.1) * Math.cos(y * 1.9 + t * 0.8) * 0.38 +
      Math.sin(y * 3.1 + t * 1.4) * Math.cos(z * 2.7 + t * 0.6) * 0.30 +
      Math.sin(z * 1.7 + t * 0.9) * Math.cos(x * 3.3 + t * 1.2) * 0.30 +
      Math.sin(x * 5.1 + y * 4.3 + t * 2.1) * 0.14
    );
  }

  function lerp(a, b, k) { return a + (b - a) * k; }
  function lerpArr3(a, b, k) { return [lerp(a[0], b[0], k), lerp(a[1], b[1], k), lerp(a[2], b[2], k)]; }

  // ── 状态配置（白色水晶粒子，状态以极淡冷色区分）──
  // col = [近, 中, 远] 三档色，渲染用 [0]→[2] 做深度渐变
  var STATE_CFG = {
    idle:        { amp: 0.003, spd: 0.10, r: [230, 235, 245], g: [232, 237, 247], b: [238, 243, 250] },
    listening:   { amp: 0.055, spd: 0.75, r: [235, 242, 250], g: [238, 245, 252], b: [245, 250, 255] }, // 纯白
    recognizing: { amp: 0.55,  spd: 4.50, r: [170, 205, 255], g: [190, 220, 255], b: [205, 228, 255] }, // 冰蓝
    thinking:    { amp: 0.16,  spd: 1.15, r: [200, 195, 255], g: [210, 205, 255], b: [220, 215, 255] }, // 淡紫
    processing:  { amp: 0.15,  spd: 1.10, r: [205, 195, 255], g: [212, 202, 255], b: [225, 218, 255] }, // 淡紫
    executing:   { amp: 0.08,  spd: 1.00, r: [255, 255, 255], g: [255, 255, 255], b: [255, 255, 255] }, // 纯白（spinner）
    speaking:    { amp: 0.09,  spd: 1.00, r: [240, 236, 230], g: [245, 242, 238], b: [250, 248, 245] }, // 暖白
    done:        { amp: 0.10,  spd: 1.20, r: [205, 255, 235], g: [215, 255, 240], b: [225, 255, 245] }, // 薄荷白
    error:       { amp: 0.10,  spd: 0.70, r: [255, 205, 205], g: [255, 210, 210], b: [255, 220, 220] }, // 淡红白
  };
  // 兼容别名（驱动脚本可能用到的近似状态名）
  var STATE_ALIAS = {
    recognize: 'recognizing', think: 'thinking', process: 'processing',
    execute: 'executing', speak: 'speaking', ready: 'idle',
  };

  var canvas, ctx, W, H, cx, cy, scale;
  var sk = 'idle';
  var animState = {
    amp: STATE_CFG.idle.amp, spd: STATE_CFG.idle.spd,
    col: [STATE_CFG.idle.r, STATE_CFG.idle.g, STATE_CFG.idle.b],
    t: 0, rotY: 0, rotX: 0.22,
  };
  var rafId = null, running = false;
  var doneTimer = null;
  var externalVol = null;     // 外部注入音量 0-1
  var ringRot = 0;            // 执行中旋转加载环角度

  function resize() {
    var rect = canvas.getBoundingClientRect();
    var dpr = Math.max(1, Math.min(window.devicePixelRatio || 1, 3));
    var nW = Math.max(1, Math.round(rect.width * dpr));
    var nH = Math.max(1, Math.round(rect.height * dpr));
    if (canvas.width !== nW || canvas.height !== nH) { canvas.width = nW; canvas.height = nH; }
    W = nW; H = nH; cx = W / 2; cy = H / 2;
    scale = Math.min(W, H) * 0.40;
  }

  function setStatus(newSk) {
    newSk = String(newSk || 'idle').toLowerCase();
    var renderSk = STATE_CFG[newSk] ? newSk : (STATE_ALIAS[newSk] || 'idle');
    sk = renderSk;
    if (newSk === 'done') {
      if (doneTimer) clearTimeout(doneTimer);
      doneTimer = setTimeout(function () { if (sk === 'done') setStatus('idle'); }, 2400);
    }
  }

  function draw(now) {
    if (!running) return;
    var ts = now || performance.now();
    resize();
    var cfg = STATE_CFG[sk];
    var ls = 0.04;
    animState.amp = lerp(animState.amp, cfg.amp, ls * 8);
    animState.spd = lerp(animState.spd, cfg.spd, ls * 6);
    animState.col = [
      lerpArr3(animState.col[0], cfg.r, ls * 1.5),
      lerpArr3(animState.col[1], cfg.g, ls * 1.5),
      lerpArr3(animState.col[2], cfg.b, ls * 1.5),
    ];

    // 音量驱动：说话/识别时放大振幅 + 加速
    var visualVol = externalVol != null ? externalVol : 0;
    if (visualVol > 0.02) {
      animState.amp = lerp(animState.amp, 0.06 + visualVol * 1.2, 0.4);
      animState.spd = lerp(animState.spd, 0.8 + visualVol * 4.0, 0.2);
    }

    animState.t += 0.016 * animState.spd;
    animState.rotY += 0.008 * (0.5 + animState.spd * 0.4);
    animState.rotX = 0.22 + Math.sin(animState.t * 0.15) * 0.06;

    ctx.clearRect(0, 0, W, H);
    var cY = Math.cos(animState.rotY), sY = Math.sin(animState.rotY);
    var cX = Math.cos(animState.rotX), sX = Math.sin(animState.rotX);

    var project = function (orig) {
      var d = 1.0 + sn(orig.x, orig.y, orig.z, animState.t) * animState.amp;
      var px = orig.x * d, py = orig.y * d, pz = orig.z * d;
      var rx = px * cY + pz * sY;
      var ry0 = py;
      var rz = -px * sY + pz * cY;
      var ry = ry0 * cX - rz * sX;
      var rz2 = ry0 * sX + rz * cX;
      return { sx: cx + rx * scale, sy: cy - ry * scale, z: rz2 };
    };

    var allPts = [];
    for (var i = 0; i < BASE_OUTER.length; i++) allPts.push(project(BASE_OUTER[i]));
    for (var j = 0; j < BASE_INNER.length; j++) allPts.push(project(BASE_INNER[j]));
    allPts.sort(function (a, b) { return a.z - b.z; });

    for (var k = 0; k < allPts.length; k++) {
      var pt = allPts[k];
      var depth = (pt.z + 1.5) / 3.0;
      var r = Math.round(lerp(animState.col[0][0], animState.col[0][2], depth));
      var g = Math.round(lerp(animState.col[1][0], animState.col[1][2], depth));
      var bb = Math.round(lerp(animState.col[2][0], animState.col[2][2], depth));
      var alpha = 0.25 + depth * 0.75;
      var dotR = 0.6 + depth * 0.8 + animState.amp * 2.0;
      ctx.beginPath();
      ctx.arc(pt.sx, pt.sy, dotR, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(' + r + ',' + g + ',' + bb + ',' + alpha.toFixed(2) + ')';
      ctx.fill();
    }

    if (sk === 'executing') drawSpinner();

    rafId = requestAnimationFrame(draw);
  }

  // ── 执行中：外圈旋转加载环（白色 spinner） ──
  function drawSpinner() {
    var R = scale * 1.5;
    var lw = Math.max(2.5, scale * 0.10);
    ringRot += 0.09;
    var sweep = Math.PI * 0.55;
    var start = ringRot;
    ctx.save();
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.arc(cx, cy, R, 0, Math.PI * 2);
    ctx.lineWidth = lw;
    ctx.strokeStyle = 'rgba(255,255,255,0.12)';
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(cx, cy, R, start, start + sweep);
    ctx.lineWidth = lw;
    ctx.strokeStyle = 'rgba(255,255,255,0.95)';
    ctx.shadowColor = 'rgba(255,255,255,0.9)';
    ctx.shadowBlur = Math.max(6, scale * 0.25);
    ctx.stroke();
    ctx.restore();
  }

  // ── 公共接口（与 dyna-orb.html / dyna-orb-voice.js 契约一致） ──
  window.ZZDynaOrb = {
    init: function (el) {
      canvas = el;
      ctx = canvas.getContext('2d');
      resize();
    },
    start: function () { running = true; if (!rafId) rafId = requestAnimationFrame(draw); },
    stop: function () {
      running = false;
      if (rafId) { cancelAnimationFrame(rafId); rafId = null; }
      if (doneTimer) { clearTimeout(doneTimer); doneTimer = null; }
    },
    setState: function (s) { setStatus(s); },
    setVolume: function (v) { externalVol = (v == null ? null : Number(v) || 0); },
    getState: function () { return sk; },
  };
})();
