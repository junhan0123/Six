/* ═════════════════════════════════════════════════════════════════
   Xiao6 UI-R1 · voice.js — 语音输入 / TTS 播报（Phase 2）
   迁移自 x6-workspace.js：speakText / startVoice / pcmToWav
   冻结契约：POST /api/speak（body {text,stream:false}）、
            POST /api/asr?ext=.wav（multipart 字段名 audio，不得修改）
   ═════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';
  window.Xiao6 = window.Xiao6 || {};

  function $(id) { return document.getElementById(id); }

  // ───────────────────── TTS 播报 ─────────────────────
  function speakText(text) {
    text = String(text || '').replace(/\s+/g, ' ').trim(); if (!text) return;
    fetch('/api/speak', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: text, stream: false }) })
      .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.blob(); })
      .then(function (blob) { var a = new Audio(URL.createObjectURL(blob)); a.onended = function () { URL.revokeObjectURL(a.src); }; a.play().catch(function () {}); })
      .catch(function () { /* 静默 */ });
  }

  // ───────────────────── 语音输入（浏览器麦克风 → /api/asr → 回填发送）─────────────────────
  function startVoice() {
    if (window.electronAPI && typeof window.electronAPI.focusOrb === 'function') { window.electronAPI.focusOrb(); return; }
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) { window.Xiao6.main.toast('当前环境不支持麦克风'); return; }
    window.Xiao6.main.toast('聆听中…说完自动识别');
    navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, sampleRate: 16000 } })
      .then(function (stream) {
        var AC = window.AudioContext || window.webkitAudioContext; var ctx = new AC({ sampleRate: 16000 });
        var src = ctx.createMediaStreamSource(stream); var an = ctx.createAnalyser(); an.fftSize = 2048; src.connect(an);
        var proc = ctx.createScriptProcessor(4096, 1, 1); var chunks = []; var speaking = false; var silent = 0;
        proc.onaudioprocess = function (e) {
          var d = e.inputBuffer.getChannelData(0); var pcm = new Int16Array(d.length);
          for (var i = 0; i < d.length; i++) { var s = Math.max(-1, Math.min(1, d[i])); pcm[i] = s < 0 ? s * 0x8000 : s * 0x7fff; }
          if (speaking) chunks.push(pcm.buffer);
          var rms = 0; for (var j = 0; j < d.length; j++) rms += d[j] * d[j]; rms = Math.sqrt(rms / d.length);
          if (rms > 0.02) { speaking = true; silent = 0; } else if (speaking) { silent++; if (silent > 70) finish(); }
        };
        an.connect(proc); proc.connect(ctx.destination);
        function finish() {
          try { proc.disconnect(); an.disconnect(); src.disconnect(); ctx.close().catch(function () {}); stream.getTracks().forEach(function (t) { t.stop(); }); } catch (e) {}
          if (!chunks.length) { window.Xiao6.main.toast('未检测到语音'); return; }
          var total = 0; chunks.forEach(function (c) { total += c.byteLength; });
          var merged = new Int16Array(total / 2); var off = 0;
          chunks.forEach(function (c) { var a = new Int16Array(c); merged.set(a, off); off += a.length; });
          var wav = pcmToWav(merged, 16000); var blob = new Blob([wav], { type: 'audio/wav' });
          var fd = new FormData(); fd.append('audio', blob, 'u.wav');
          fetch('/api/asr?ext=.wav', { method: 'POST', body: fd, credentials: 'same-origin' }).then(function (r) { return r.json(); }).then(function (d) {
            var t = (d && d.text) || ''; if (t.trim()) { var ci = $('cmdInput'); if (ci) ci.value = t; window.Xiao6.timeline.submitCmd(t); } else window.Xiao6.main.toast('未识别到内容');
          }).catch(function () { window.Xiao6.main.toast('语音识别失败'); });
        }
      }).catch(function () { window.Xiao6.main.toast('无法访问麦克风'); });
  }

  // ───────────────────── PCM → WAV 编码 ─────────────────────
  function pcmToWav(samples, sr) {
    var len = samples.length, buf = new ArrayBuffer(44 + len * 2), v = new DataView(buf);
    function ws(o, s) { for (var i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); }
    ws(0, 'RIFF'); v.setUint32(4, 36 + len * 2, true); ws(8, 'WAVE'); ws(12, 'fmt '); v.setUint32(16, 16, true);
    v.setUint16(20, 1, true); v.setUint16(22, 1, true); v.setUint32(24, sr, true); v.setUint32(28, sr * 2, true);
    v.setUint16(32, 2, true); v.setUint16(34, 16, true); ws(36, 'data'); v.setUint32(40, len * 2, true);
    for (var i = 0; i < len; i++) v.setInt16(44 + i * 2, samples[i], true);
    return new Uint8Array(buf);
  }

  window.Xiao6.voice = { speakText: speakText, startVoice: startVoice };
})();
