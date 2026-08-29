/**
 * UI-5C-1 · Conversation Core Integration — GUI 验证脚本（Chrome DevTools Protocol）
 * 用法：ZZ_PHASE=before|after node _5c1_shoot.mjs
 * 纪律：只读取 / 截图 / 探针，不写入项目任何源码。
 */
import { writeFileSync, mkdirSync } from 'node:fs';
import { setTimeout as sleep } from 'node:timers/promises';

const BASE = process.env.ZZ_BASE || 'http://127.0.0.1:8000';
const PHASE = process.env.ZZ_PHASE || 'before';
const ROOT = 'G:/xiao6/docs/ui-system/ui5c1-conversation-core-integration';
const OUT = `${ROOT}/shots-${PHASE}`;
mkdirSync(OUT, { recursive: true });

const res = await fetch('http://127.0.0.1:9222/json/version');
const { webSocketDebuggerUrl } = await res.json();
const ws = new WebSocket(webSocketDebuggerUrl);
await new Promise(r => ws.addEventListener('open', r, { once: true }));

let id = 0;
const pending = new Map();
const errors = [];
ws.addEventListener('message', (ev) => {
  const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
  if (m.method === 'Runtime.exceptionThrown') {
    errors.push(m.params?.exceptionDetails?.exception?.description
      || m.params?.exceptionDetails?.text || 'unknown');
  }
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
await S('Network.clearBrowserCache');

async function evalJs(expr) {
  const r = await S('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.text + ' :: ' + expr.slice(0, 100));
  return r.result?.value;
}
const setSize = (w, h) => S('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 1, mobile: false });
async function goto(url) {
  await S('Page.navigate', { url });
  for (let i = 0; i < 60; i++) {
    const st = await evalJs('document.readyState').catch(() => null);
    if (st === 'complete') break;
    await sleep(200);
  }
  await sleep(1500);
}
async function shot(name) {
  const { data } = await S('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
  writeFileSync(`${OUT}/${name}.png`, Buffer.from(data, 'base64'));
  console.log('  shot ->', name);
}
const KILL_ONB = `try{localStorage.setItem('xiao6_onboarded','1');}catch(e){}
  try{var o=document.getElementById('onbOverlay'); if(o) o.remove();}catch(e){} 'ok'`;

// ── 运行时探针：直接读 computedStyle 与命中测试 ────────────────────────────
const PROBE = `(() => {
  const g = (sel) => document.querySelector(sel);
  const info = (sel) => {
    const el = g(sel); if (!el) return { sel, exists: false };
    const cs = getComputedStyle(el); const r = el.getBoundingClientRect();
    return { sel, exists: true, display: cs.display, visibility: cs.visibility,
      opacity: cs.opacity, filter: cs.filter, pointerEvents: cs.pointerEvents,
      zIndex: cs.zIndex, background: cs.backgroundColor, backdrop: cs.backdropFilter,
      maxHeight: cs.maxHeight,
      rect: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) } };
  };
  // 命中测试：某元素中心点最终收到事件的是谁
  const hit = (sel) => {
    const el = g(sel); if (!el) return { sel, exists: false };
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return { sel, exists: true, zeroBox: true };
    const cx = Math.min(Math.max(r.x + r.width / 2, 1), window.innerWidth - 1);
    const cy = Math.min(Math.max(r.y + r.height / 2, 1), window.innerHeight - 1);
    const top = document.elementFromPoint(cx, cy);
    const desc = (n) => n ? n.tagName.toLowerCase() + (n.id ? '#' + n.id : '') +
      (typeof n.className === 'string' && n.className.trim() ? '.' + n.className.trim().split(/\\s+/).slice(0,2).join('.') : '') : 'null';
    return { sel, exists: true, point: [Math.round(cx), Math.round(cy)],
             top: desc(top), reachable: !!(top && (el === top || el.contains(top) || top.contains(el))) };
  };
  return {
    bodyClass: document.body.className,
    osShell: info('#osShell'),
    osDock: info('#osDock'),
    osDockInput: info('#osDockInput'),
    app: info('#app'),
    rail: info('#app .rail'),
    tele: info('#tele'),
    mainArea: info('#mainArea'),
    hudBar: info('#app .hud-bar'),
    chatArea: info('#chatArea'),
    chatHistory: info('#chatHistory'),
    chatDock: info('#chatArea .dock'),
    legacyInput: info('#input'),
    solarCanvas: info('#solarCanvas'),
    galaxyVeil: info('.galaxy-veil'),
    hits: [hit('#osDockInput'), hit('#osDock'), hit('#solarCanvas'), hit('#input')],
    // Command Dock 是否可作为唯一 Intent Entry：其发送路径依赖 #input/#btnSend
    dockRoute: { hasInput: !!document.getElementById('input'), hasSend: !!document.getElementById('btnSend'),
                 hasDockInput: !!document.getElementById('osDockInput'), hasDockSend: !!document.getElementById('osDockSend') }
  };
})()`;

const REPORT = { phase: PHASE, at: new Date().toISOString(), scenes: [], errors: [] };

async function scene(tag, w, h, name, prepJs) {
  await setSize(w, h);
  if (prepJs === null) { await goto(BASE + '/index.html'); await evalJs(KILL_ONB); await sleep(700); }
  else { await evalJs(prepJs); await sleep(1100); }
  await shot(name);
  const p = await evalJs(PROBE);
  REPORT.scenes.push({ scene: name, size: `${w}x${h}`, ...p });
  console.log(`  probe [${name}] body="${p.bodyClass}" osShell.op=${p.osShell.opacity} osShell.pe=${p.osShell.pointerEvents} app.z=${p.app.zIndex} dockHit=${p.hits[0].reachable}`);
  return p;
}

for (const [w, h] of [[1920, 1080], [1600, 900]]) {
  const t = `${w}x${h}`;
  console.log(`\n[${t}]`);
  await scene(t, w, h, `01-${t}-home`, null);
  await scene(t, w, h, `02-${t}-conversation`, `try{ openChat(); }catch(e){ document.body.classList.add('chat-mode'); } 'ok'`);
  await scene(t, w, h, `03-${t}-back-home`, `try{ closeChat(); }catch(e){ document.body.classList.remove('chat-mode'); } 'ok'`);
}

REPORT.errors = errors.slice(0, 30);
writeFileSync(`${ROOT}/_probe_${PHASE}.json`, JSON.stringify(REPORT, null, 2), 'utf-8');
console.log(`\n=== ${PHASE} 完成 → _probe_${PHASE}.json ===  JS 异常数: ${errors.length}`);
errors.slice(0, 8).forEach(e => console.log('  !', String(e).split('\n')[0]));
ws.close();
process.exit(0);
