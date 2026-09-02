/**
 * F-01 补充验证：排除有意离屏抽屉(.os-side/.settings-panel)后，
 * 扫描是否存在「可见元素越出视口右/左边界」的真实裁切缺陷。
 */
import { setTimeout as sleep } from 'node:timers/promises';
const BASE = 'http://127.0.0.1:8000';
const res = await fetch('http://127.0.0.1:9222/json/version');
const { webSocketDebuggerUrl } = await res.json();
const ws = new WebSocket(webSocketDebuggerUrl);
await new Promise(r => ws.addEventListener('open', r, { once: true }));
let id = 0; const pending = new Map();
ws.addEventListener('message', (ev) => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } });
function send(method, params = {}, sessionId) { const _id = ++id; return new Promise((resolve, reject) => { pending.set(_id, (m) => m.error ? reject(new Error(method + ': ' + JSON.stringify(m.error))) : resolve(m.result)); ws.send(JSON.stringify({ id: _id, method, params, sessionId })); }); }
const { targetInfos } = await send('Target.getTargets');
let page = targetInfos.find(t => t.type === 'page');
if (!page) { const t = await send('Target.createTarget', { url: 'about:blank' }); page = { targetId: t.targetId }; }
const { sessionId } = await send('Target.attachToTarget', { targetId: page.targetId, flatten: true });
const S = (m, p) => send(m, p, sessionId);
await S('Page.enable'); await S('Runtime.enable');
async function evalJs(expr) { const r = await S('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }); if (r.exceptionDetails) throw new Error(r.exceptionDetails.text + ' :: ' + expr.slice(0, 80)); return r.result?.value; }
async function setSize(w, h) { await S('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 1, mobile: false }); }
async function goto(url) { await S('Page.navigate', { url }); for (let i = 0; i < 60; i++) { const st = await evalJs('document.readyState').catch(() => null); if (st === 'complete') break; await sleep(200); } await sleep(1400); }
const KILL_ONB = `try{ localStorage.setItem('xiao6_onboarded','1'); }catch(e){} try{ var o=document.getElementById('onbOverlay'); if(o) o.remove(); }catch(e){} 'ok'`;

const PROBE = `(() => {
  const vw = window.innerWidth, vh = window.innerHeight;
  const off = [];
  document.querySelectorAll('body *').forEach(el => {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || cs.opacity === '0') return;
    const sel = el.tagName.toLowerCase() + (el.id ? '#'+el.id : '') + (el.className && typeof el.className==='string' ? '.'+el.className.trim().split(/\\s+/).slice(0,2).join('.') : '');
    if (/\\bos-side\\b/.test(sel) || /\\bsettings-panel\\b/.test(sel)) return; // 有意离屏
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return;
    if (r.right > vw + 1.5 || r.left < -1.5) {
      if (cs.position === 'fixed' || cs.position === 'absolute') {
        if (parseFloat(cs.opacity) < 0.05) return;
        if (cs.transform && cs.transform !== 'none' && r.left < -50) return;
      }
      off.push({ sel, left: Math.round(r.left), right: Math.round(r.right), w: Math.round(r.width), pos: cs.position, op: cs.opacity });
    }
  });
  return off.slice(0, 16);
})()`;

for (const [tag, w, h] of [['1920x1080',1920,1080],['1440x900',1440,900],['1000x800',1000,800],['720x900',720,900]]) {
  console.log('\\n['+tag+']');
  await setSize(w, h); await goto(BASE + '/index.html'); await evalJs(KILL_ONB); await sleep(600);
  const off = await evalJs(PROBE);
  if (!off.length) console.log('  ✅ 无可见越界元素');
  else { console.log('  ❌ 可见越界 '+off.length+' 个：'); off.forEach(o => console.log('    ', JSON.stringify(o))); }
}
ws.close(); process.exit(0);
