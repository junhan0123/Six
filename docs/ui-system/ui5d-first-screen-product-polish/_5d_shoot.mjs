/**
 * UI-5D · First Screen Product Polish — GUI 验证脚本（Chrome DevTools Protocol）
 * 用法：
 *   ZZ_PHASE=before node _5d_shoot.mjs   （自动剥离 ui5d 样式，作为 UI-4D-1 基线）
 *   ZZ_PHASE=after  node _5d_shoot.mjs   （含 ui5d 样式，当前实现态）
 * 纪律：只读取 / 截图 / 探针，不写入项目任何源码。
 */
import { writeFileSync, mkdirSync } from 'node:fs';
import { setTimeout as sleep } from 'node:timers/promises';

const BASE = process.env.ZZ_BASE || 'http://127.0.0.1:8000';
const PHASE = process.env.ZZ_PHASE || 'after';
const ROOT = 'G:/xiao6/docs/ui-system/ui5d-first-screen-product-polish';
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
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.text + ' :: ' + expr.slice(0, 120));
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
// before 阶段：剥离 ui5d 样式，回到 UI-4D-1 基线
const STRIP_UI5D = `try{var l=document.querySelector('link[href*="ui5d-first-screen-polish"]'); if(l) l.remove();}catch(e){} 'ok'`;

const PROBE = `(() => {
  const g = (sel) => document.querySelector(sel);
  const info = (sel) => {
    const el = g(sel); if (!el) return { sel, exists: false };
    const cs = getComputedStyle(el); const r = el.getBoundingClientRect();
    return { sel, exists: true, display: cs.display, visibility: cs.visibility,
      opacity: cs.opacity, filter: cs.filter, transform: cs.transform,
      pointerEvents: cs.pointerEvents, zIndex: cs.zIndex,
      fontSize: cs.fontSize, width: cs.width, height: cs.height,
      background: cs.backgroundColor, boxShadow: cs.boxShadow, borderColor: cs.borderColor,
      rect: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) } };
  };
  const afterContent = (sel) => {
    const el = g(sel); if (!el) return null;
    const c = getComputedStyle(el, '::after').content;
    return c && c !== 'none' ? c.replace(/^["']|["']$/g, '') : '';
  };
  // D3-b：聚焦输入条，读取 .os-dock-bar 聚焦态 box-shadow / border-color
  let dockBarFocus = null;
  const di = g('#osDockInput');
  if (di) { try { di.focus(); } catch(e){} }
  const bar = g('.os-dock-bar');
  if (bar) {
    const bcs = getComputedStyle(bar);
    dockBarFocus = { boxShadow: bcs.boxShadow, borderColor: bcs.borderColor };
  }
  if (di) { try { di.blur(); } catch(e){} }
  // D3-c：非发送工具按钮背景
  const toolBtn = g('.os-dock .os-dock-btn:not(.send)');
  const toolBg = toolBtn ? getComputedStyle(toolBtn).backgroundColor : null;
  // D1-b：主题选择 opacity + 按钮宽
  const tp = g('.os-theme-picker');
  const tpOpacity = tp ? getComputedStyle(tp).opacity : null;
  const tpBtn = g('.os-theme-picker button');
  const tpBtnW = tpBtn ? getComputedStyle(tpBtn).width : null;
  // D2：导航能力标签
  const navLabels = {};
  ['workspace','command','galaxy','assistant','settings'].forEach(n => {
    navLabels[n] = afterContent('.os-nav-btn[data-nav="'+n+'"]');
  });
  navLabels.brand = afterContent('.os-nav-brand');
  const navBtnCount = document.querySelectorAll('.os-nav-btn').length;
  // presence
  const presence = document.body.getAttribute('data-presence') || '';
  const presenceColor = getComputedStyle(document.body).getPropertyValue('--presence-color').trim();
  return {
    bodyClass: document.body.className,
    presence, presenceColor,
    osBrand: info('.os-hud .os-brand'),
    osState: info('.os-hud .os-state'),
    osClock: info('.os-hud .os-clock'),
    themePickerOpacity: tpOpacity, themePickerBtnW: tpBtnW,
    navBtnCount, navLabels,
    dockBarFocus, toolBtnBg: toolBg,
    osShell: info('#osShell'),
    app: info('#app'),
    solarCanvas: info('#solarCanvas'),
    galaxyVeil: info('.galaxy-veil'),
    osDock: info('#osDock')
  };
})()`;

const REPORT = { phase: PHASE, at: new Date().toISOString(), scenes: [], errors: [] };

async function scene(tag, w, h, name, prepJs) {
  await setSize(w, h);
  await goto(BASE + '/index.html');
  await evalJs(KILL_ONB);
  if (PHASE === 'before') await evalJs(STRIP_UI5D);
  if (prepJs) { await evalJs(prepJs); await sleep(1100); }
  else { await sleep(700); }
  await shot(name);
  const p = await evalJs(PROBE);
  REPORT.scenes.push({ scene: name, size: `${w}x${h}`, ...p });
  console.log(`  probe [${name}] presence=${p.presence} brand.op=${p.osBrand.opacity} brand.fs=${p.osBrand.fontSize} tpOp=${p.themePickerOpacity} tpBtnW=${p.themePickerBtnW} solar.f=${p.solarCanvas.filter}`);
  return p;
}

// 场景定义
const OPEN_CHAT = `try{ if(typeof openChat==='function') openChat(); else document.body.classList.add('chat-mode'); }catch(e){ document.body.classList.add('chat-mode'); } 'ok'`;
const OPEN_EXPLORE = `try{ if(typeof openUniverse==='function') openUniverse(); else document.body.classList.add('universe-mode'); }catch(e){ document.body.classList.add('universe-mode'); } 'ok'`;

console.log(`\n[UI-5D verify · PHASE=${PHASE}]`);
await scene('home-1920', 1920, 1080, `01-home-1920`, null);
await scene('home-1440', 1440, 900, `02-home-1440`, null);
await scene('home-720', 720, 900, `03-home-720`, null);
await scene('conversation-1920', 1920, 1080, `04-conversation-1920`, OPEN_CHAT);
await scene('explore-1920', 1920, 1080, `05-explore-1920`, OPEN_EXPLORE);

REPORT.errors = errors.slice(0, 30);
writeFileSync(`${ROOT}/_probe_${PHASE}.json`, JSON.stringify(REPORT, null, 2), 'utf-8');
console.log(`\n=== ${PHASE} 完成 → _probe_${PHASE}.json ===  JS 异常数: ${errors.length}`);
errors.slice(0, 8).forEach(e => console.log('  !', String(e).split('\n')[0]));
ws.close();
process.exit(0);
