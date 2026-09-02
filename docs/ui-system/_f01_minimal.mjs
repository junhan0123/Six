/**
 * F-01 最小修复面判定（只读探针，不改源文件）
 * 问题：ui2.css 现有两处封锁 —— html{overflow-x:clip} 与 .os-shell{overflow-x:clip}。
 * 目的：判定 html 那条是否冗余（若把 html 退回 hidden 仍 canScrollX=0，则它对本缺陷无贡献）。
 * 手段：运行时用 inline style 覆盖，四档宽度各测一次，测完复原。
 */
import { setTimeout as sleep } from 'node:timers/promises';
const BASE = process.env.ZZ_BASE || 'http://127.0.0.1:8000';

const { webSocketDebuggerUrl } = await (await fetch('http://127.0.0.1:9222/json/version')).json();
const ws = new WebSocket(webSocketDebuggerUrl);
await new Promise(r => ws.addEventListener('open', r, { once: true }));
let id = 0; const pending = new Map();
ws.addEventListener('message', e => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } });
const send = (method, params = {}, sessionId) => new Promise((res, rej) => {
  const _id = ++id; pending.set(_id, m => m.error ? rej(new Error(method + ':' + JSON.stringify(m.error))) : res(m.result));
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

await S('Emulation.setDeviceMetricsOverride', { width: 1920, height: 1080, deviceScaleFactor: 1, mobile: false });
await S('Page.navigate', { url: BASE + '/index.html' });
for (let i = 0; i < 60; i++) { if (await evalJs('document.readyState').catch(() => null) === 'complete') break; await sleep(200); }
await sleep(1500);
await evalJs(`try{localStorage.setItem('xiao6_onboarded','1')}catch(e){};var o=document.getElementById('onbOverlay');if(o)o.remove();'ok'`);

const MEASURE = `(() => {
  const h = document.documentElement, b = document.body;
  const before = h.scrollLeft; h.scrollLeft = 99999;
  const canScrollX = Math.max(h.scrollLeft, b.scrollLeft); h.scrollLeft = before;
  return { canScrollX, htmlScrollWidth: h.scrollWidth, winW: window.innerWidth,
           htmlOverflowX: getComputedStyle(h).overflowX,
           shellOverflowX: getComputedStyle(document.querySelector('.os-shell')).overflowX };
})()`;

const SCEN = [
  ['A 现状（html:clip + shell:clip）', `document.documentElement.style.removeProperty('overflow-x');
     document.querySelector('.os-shell').style.removeProperty('overflow-x'); 'ok'`],
  ['B 仅 shell:clip（html 退回 hidden）', `document.documentElement.style.setProperty('overflow-x','hidden','important');
     document.querySelector('.os-shell').style.removeProperty('overflow-x'); 'ok'`],
  ['C 仅 html:clip（shell 退回 visible）', `document.documentElement.style.removeProperty('overflow-x');
     document.querySelector('.os-shell').style.setProperty('overflow-x','visible','important'); 'ok'`],
  ['D 两者都退回（缺陷复现基线）', `document.documentElement.style.setProperty('overflow-x','hidden','important');
     document.querySelector('.os-shell').style.setProperty('overflow-x','visible','important'); 'ok'`],
];

const WIDTHS = [[1920, 1080], [1440, 900], [1000, 800], [720, 900]];
const results = {};
for (const [label, setup] of SCEN) {
  results[label] = [];
  for (const [w, h] of WIDTHS) {
    await S('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 1, mobile: false });
    await sleep(260);
    await evalJs(setup);
    await sleep(200);
    results[label].push({ w, ...(await evalJs(MEASURE)) });
  }
}
// 复原
await evalJs(`document.documentElement.style.removeProperty('overflow-x');
  document.querySelector('.os-shell').style.removeProperty('overflow-x'); 'ok'`);

console.log('='.repeat(96));
console.log('F-01 最小修复面判定');
console.log('='.repeat(96));
for (const [label, rows] of Object.entries(results)) {
  const worst = Math.max(...rows.map(r => r.canScrollX));
  console.log(`\n${label}   →  最大 canScrollX = ${worst}  ${worst === 0 ? '✅ 无横向滚动' : '❌ 仍可横向拖动'}`);
  for (const r of rows) {
    console.log(`   ${String(r.w).padStart(4)}px  canScrollX=${String(r.canScrollX).padStart(4)}  scrollWidth=${String(r.htmlScrollWidth).padStart(5)}  html:${r.htmlOverflowX.padEnd(7)} shell:${r.shellOverflowX}`);
  }
}
const b = Math.max(...results['B 仅 shell:clip（html 退回 hidden）'].map(r => r.canScrollX));
const c = Math.max(...results['C 仅 html:clip（shell 退回 visible）'].map(r => r.canScrollX));
const d = Math.max(...results['D 两者都退回（缺陷复现基线）'].map(r => r.canScrollX));
console.log('\n' + '='.repeat(96));
console.log('结论：');
console.log(`  · 缺陷基线可复现：${d > 0 ? '是（canScrollX=' + d + '）' : '否 —— 说明还有第三处在生效，需重查'}`);
console.log(`  · .os-shell{clip} 单独充分：${b === 0 ? '是' : '否'}`);
console.log(`  · html{clip} 单独充分：${c === 0 ? '是' : '否'}`);
console.log(`  · html 那条对本缺陷：${b === 0 && c > 0 ? '冗余（无贡献）' : (c === 0 ? '有效' : '需进一步判定')}`);
ws.close(); process.exit(0);
