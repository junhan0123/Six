/**
 * F-01 验证：全局横向滚动缺陷修复确认。
 * 纪律：只读取与探针，不写入项目任何源码。
 * 验证点：1920 / 1440 / 1000 / 720 四档下 canScrollX 必须为 0，
 *        且 html.scrollWidth 不应超出 innerWidth（clip 应把离屏抽屉裁切掉）。
 */
import { writeFileSync, mkdirSync } from 'node:fs';
import { setTimeout as sleep } from 'node:timers/promises';

const BASE = process.env.ZZ_BASE || 'http://127.0.0.1:8000';
const OUT = 'G:/xiao6/docs/ui-consolidation/shots-f01';
mkdirSync(OUT, { recursive: true });

const res = await fetch('http://127.0.0.1:9222/json/version');
const { webSocketDebuggerUrl } = await res.json();
const ws = new WebSocket(webSocketDebuggerUrl);
await new Promise(r => ws.addEventListener('open', r, { once: true }));

let id = 0;
const pending = new Map();
ws.addEventListener('message', (ev) => {
  const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
});
function send(method, params = {}, sessionId) {
  const _id = ++id;
  return new Promise((resolve, reject) => {
    pending.set(_id, (m) => m.error ? reject(new Error(method + ': ' + JSON.stringify(m.error))) : resolve(m.result));
    ws.send(JSON.stringify({ id: _id, method, params, sessionId }));
  });
}
const { targetInfos } = await send('Target.getTargets');
let page = targetInfos.find(t => t.type === 'page');
if (!page) { const t = await send('Target.createTarget', { url: 'about:blank' }); page = { targetId: t.targetId }; }
const { sessionId } = await send('Target.attachToTarget', { targetId: page.targetId, flatten: true });
const S = (m, p) => send(m, p, sessionId);
await S('Page.enable');
await S('Runtime.enable');

async function evalJs(expr) {
  const r = await S('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.text + ' :: ' + expr.slice(0, 80));
  return r.result?.value;
}
async function setSize(w, h) {
  await S('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 1, mobile: false });
}
async function goto(url) {
  await S('Page.navigate', { url });
  for (let i = 0; i < 60; i++) {
    const st = await evalJs('document.readyState').catch(() => null);
    if (st === 'complete') break;
    await sleep(200);
  }
  await sleep(1400);
}
const KILL_ONB = `try{ localStorage.setItem('xiao6_onboarded','1'); }catch(e){} try{ var o=document.getElementById('onbOverlay'); if(o) o.remove(); }catch(e){} 'ok'`;

// 探针：真实横向可滚动量。clip 下 scrollLeft 应恒为 0。
const PROBE = `(() => {
  const h = document.documentElement;
  const before = h.scrollLeft;
  h.scrollLeft = 9999;
  const canScrollX = Math.max(h.scrollLeft, document.body.scrollLeft);
  h.scrollLeft = before;
  return {
    htmlScrollWidth: h.scrollWidth,
    htmlClientWidth: h.clientWidth,
    winW: window.innerWidth,
    bodyScrollWidth: document.body.scrollWidth,
    canScrollX,
    overflowX: getComputedStyle(h).overflowX,
    clipActive: getComputedStyle(h).overflowX === 'clip'
  };
})()`;

const SIZES = [
  ['1920x1080', 1920, 1080],
  ['1440x900', 1440, 900],
  ['1000x800', 1000, 800],
  ['720x900', 720, 900],
];

console.log('=== F-01 横向滚动验证 ===');
const REPORT = { f01: [] };
for (const [tag, w, h] of SIZES) {
  console.log(`\n[${tag}]`);
  await setSize(w, h);
  await goto(BASE + '/index.html');
  await evalJs(KILL_ONB);
  await sleep(600);
  const p = await evalJs(PROBE);
  const pass = p.canScrollX === 0 && p.htmlScrollWidth <= p.winW + 1;
  console.log('  ', JSON.stringify(p), pass ? '✅ PASS' : '❌ FAIL');
  REPORT.f01.push({ tag, ...p, pass });
}

const allPass = REPORT.f01.every(r => r.pass);

// ── 抽屉打开态：确认 clip 未误裁、打开时仍不撑出横向滚动 ──────────────────
console.log('\n[Context 抽屉打开态 @1920]');
await setSize(1920, 1080);
await goto(BASE + '/index.html');
await evalJs(KILL_ONB);
await sleep(500);
await evalJs(`try{ document.body.classList.add('os-context-open'); var s=document.querySelector('.os-side'); if(s) s.style.setProperty('transform','none'); }catch(e){}"ok"`);
await sleep(800);
const openState = await evalJs(`(() => {
  const el = document.querySelector('.os-side');
  const cs = getComputedStyle(el);
  const b = el.getBoundingClientRect();
  const h = document.documentElement; const before = h.scrollLeft; h.scrollLeft = 99999; const canScrollX = Math.max(h.scrollLeft, document.body.scrollLeft); h.scrollLeft = before;
  return { display: cs.display, opacity: cs.opacity, left: Math.round(b.left), right: Math.round(b.right), top: Math.round(b.top), bottom: Math.round(b.bottom),
           vw: window.innerWidth, visibleInViewport: (b.left >= 0 && b.right <= window.innerWidth + 1), canScrollX };
})()`);
const openPass = openState.visibleInViewport && openState.canScrollX === 0;
console.log('  ', JSON.stringify(openState), openPass ? '✅ PASS' : '❌ FAIL');
REPORT.contextOpen = { ...openState, pass: openPass };

console.log('\n=== 汇总：', (allPass && openPass) ? '全部通过 ✅' : '存在失败 ❌', '===');
writeFileSync(`${OUT}/_f01_probe.json`, JSON.stringify(REPORT, null, 2), 'utf-8');
ws.close();
process.exit((allPass && openPass) ? 0 : 1);
