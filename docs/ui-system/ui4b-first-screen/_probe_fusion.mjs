/**
 * UI-4B-1 First Screen Fusion —— 像素级融合度量（启用 vs 禁用本层）
 * ---------------------------------------------------------------------------
 * 把"首屏是否真正融合为一个连续 AI OS 空间"从主观描述变成可测的像素事实：
 *
 *   指标 A · World Window（Galaxy 透出）：中央舞台区域的亮度标准差。
 *     - 启用本层：.os-core backdrop-filter:none + 边框透明 → Galaxy 清晰透出
 *       → 中央区域亮度标准差 高（有星空纹理）。
 *     - 禁用本层：.os-core blur(26px) + 不透明边框/卡片 → Galaxy 被糊成一片
 *       → 中央区域亮度标准差 低（糊成均匀面）。
 *     ⇒ 期望：stdDev(ON) > stdDev(OFF)
 *
 *   指标 B · 无矩形硬边：.os-core 顶边水平亮度剖面的单步跳变最大值。
 *     - 启用本层：border-color:transparent + 无 backdrop-filter + 径向渐变平滑
 *       → 剖面无尖锐台阶。
 *     - 禁用本层：1px 实心边框 + 26px 模糊 → 顶边存在硬线条/过渡。
 *     ⇒ 期望：maxStep(ON) < maxStep(OFF)
 *
 * 前置：python -m http.server 8000（cwd=xiao6-ui/） + Chrome --remote-debugging-port=9222
 * 运行：node _probe_fusion.mjs
 * 产出：_probe_fusion.json（含两态截图已写入 shots/fusion_on.png / fusion_off.png）
 */
import { writeFileSync } from 'node:fs';
import { setTimeout as sleep } from 'node:timers/promises';
import { decodePNG, regionStats, hProfile, maxStep, lum } from './_png.mjs';

const BASE = process.env.ZZ_BASE || 'http://127.0.0.1:8000';
const OUT_DIR = new URL('./', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');

const { webSocketDebuggerUrl } = await (await fetch('http://127.0.0.1:9222/json/version')).json();
const ws = new WebSocket(webSocketDebuggerUrl);
await new Promise(r => ws.addEventListener('open', r, { once: true }));
let id = 0; const pending = new Map();
ws.addEventListener('message', e => {
  const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
});
const send = (method, params = {}, sessionId) => new Promise((res, rej) => {
  const _id = ++id;
  pending.set(_id, m => m.error ? rej(new Error(method + ':' + JSON.stringify(m.error))) : res(m.result));
  ws.send(JSON.stringify({ id: _id, method, params, sessionId }));
});
const { targetInfos } = await send('Target.getTargets');
const page = targetInfos.find(t => t.type === 'page');
const { sessionId } = await send('Target.attachToTarget', { targetId: page.targetId, flatten: true });
const S = (m, p) => send(m, p, sessionId);
await S('Page.enable'); await S('Runtime.enable');
await S('Network.enable').catch(() => {});
await S('Network.setCacheDisabled', { cacheDisabled: true }).catch(() => {});

const evalJs = async expr => {
  const r = await S('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.text);
  return r.result?.value;
};

const setUi4b = on =>
  evalJs(`(()=>{document.querySelectorAll('link[rel=stylesheet]').forEach(l=>{if(l.href.includes('ui4b-first-screen'))l.disabled=${on ? 'false' : 'true'}});return [...document.styleSheets].filter(s=>s.href&&s.href.includes('ui4b-first-screen')).map(s=>s.disabled);})()`);

const coreRect = () => evalJs(`(()=>{const e=document.querySelector('.os-core');if(!e)return null;const r=e.getBoundingClientRect();return {x:Math.round(r.x),y:Math.round(r.y),w:Math.round(r.width),h:Math.round(r.height)};})()`);

const W = 1920, H = 1080;
await S('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile: false });
await S('Page.navigate', { url: BASE + '/index.html' });
for (let i = 0; i < 80; i++) { if (await evalJs('document.readyState').catch(() => null) === 'complete') break; await sleep(200); }
await evalJs(`window.addEventListener('error',e=>{(window.__zzErr=window.__zzErr||[]).push(String(e.message))});'ok'`);
await sleep(2200);
await evalJs(`try{localStorage.setItem('xiao6_onboarded','1')}catch(e){};document.querySelectorAll('.onb-overlay,#onbOverlay').forEach(o=>o.remove());'ok'`);
await sleep(600);

async function capture(label) {
  await sleep(700); // 等过渡完成
  const rect = await coreRect();
  const { data: png } = await S('Page.captureScreenshot', { format: 'png' });
  writeFileSync(`${OUT_DIR}shots/${label}.png`, Buffer.from(png, 'base64'));
  return rect;
}

// ── ON（启用本层）──
await setUi4b(true);
const rectOn = await capture('fusion_on');
// ── OFF（禁用本层）──
await setUi4b(false);
const rectOff = await capture('fusion_off');
await setUi4b(true);

/* ── 解码 + 度量 ────────────────────────────────────────────────────────── */
const on = decodePNG(await import('node:fs').then(m => m.readFileSync(`${OUT_DIR}shots/fusion_on.png`)));
const off = decodePNG(await import('node:fs').then(m => m.readFileSync(`${OUT_DIR}shots/fusion_off.png`)));

// 中央舞台内框（取 .os-core 内部 40%–60% 区域，排除边缘过渡）
const inner = (rect) => ({
  x0: Math.round(rect.x + rect.w * 0.40),
  y0: Math.round(rect.y + rect.h * 0.40),
  w: Math.round(rect.w * 0.20),
  h: Math.round(rect.h * 0.20),
});
const rOn = inner(rectOn), rOff = inner(rectOff);

const onStats = regionStats(on, rOn.x0, rOn.y0, rOn.w, rOn.h);
const offStats = regionStats(off, rOff.x0, rOff.y0, rOff.w, rOff.h);

// 顶边「硬矩形边」台阶：沿 .os-core 顶边取多列，每列做垂直穿越（band 上行 vs 下行均值之差）。
// 设计要点：1px 实心边框在 ALL 列上连续存在 → 平均后被保留；Galaxy 星点是稀疏点源 → 平均后被稀释。
// 故 avgStep(OFF，有边框) 应 > avgStep(ON，边框透明)。单点 maxStep 会被星点误导（已弃用）。
const vCrossStep = (img, rect, xFrac) => {
  const x = Math.round(rect.x + rect.w * xFrac);
  let above = 0, an = 0, below = 0, bn = 0;
  for (let dy = -6; dy <= -2; dy++) { const yy = rect.y + dy; if (yy < 0 || yy >= img.height) continue; above += lum(img, x, yy); an++; }
  for (let dy = 2; dy <= 6; dy++) { const yy = rect.y + 0 + dy; if (yy < 0 || yy >= img.height) continue; below += lum(img, x, yy); bn++; }
  return Math.abs(above / an - below / bn);
};
const N_COLS = 60;
const stepsOn = [], stepsOff = [];
for (let i = 0; i < N_COLS; i++) {
  const xf = 0.05 + (0.90 * i) / (N_COLS - 1);
  stepsOn.push(vCrossStep(on, rectOn, xf));
  stepsOff.push(vCrossStep(off, rectOff, xf));
}
const mean = a => a.reduce((s, v) => s + v, 0) / a.length;
const avgOn = +mean(stepsOn).toFixed(3), avgOff = +mean(stepsOff).toFixed(3);

const results = {
  generatedAt: new Date().toISOString(),
  viewport: { w: W, h: H },
  rectOn, rectOff,
  centralRegion: { on: rOn, off: rOff },
  metricA_worldWindow: {
    on_stdDev: onStats.sd, off_stdDev: offStats.sd,
    on_mean: onStats.mean, off_mean: offStats.mean,
    conclusion: onStats.sd > offStats.sd ? 'PASS · Galaxy 透出更清晰（stdDev ON > OFF）' : 'FAIL · 反直觉',
  },
  metricB_noHardEdge: {
    on_avgBorderStep: avgOn, off_avgBorderStep: avgOff,
    cols: N_COLS,
    conclusion: avgOn < avgOff ? 'PASS · 顶边无连续硬矩形边（avgStep ON < OFF）' : 'FAIL · 顶边仍存连续硬边',
    note: 'avgStep = 沿顶边 60 列垂直穿越均值差；边框连续→被保留，星点稀疏→被稀释。',
  },
  raw: { onStats, offStats },
};

writeFileSync(`${OUT_DIR}_probe_fusion.json`, JSON.stringify(results, null, 2));
console.log('[fusion] metricA:', results.metricA_worldWindow.conclusion, `(ON ${onStats.sd} vs OFF ${offStats.sd})`);
console.log('[fusion] metricB:', results.metricB_noHardEdge.conclusion, `(ON ${avgOn} vs OFF ${avgOff})`);
ws.close();
