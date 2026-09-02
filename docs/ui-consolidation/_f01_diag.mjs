/**
 * F-01 深度诊断：定位真正撑大横向滚动区的元素，并实测 clip 行为。
 * 纪律：只读取与探针，不写入项目任何源码。
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

const DIAG = `(() => {
  const h = document.documentElement, b = document.body;
  const out = { vw: window.innerWidth, htmlOverflowX: getComputedStyle(h).overflowX, htmlScrollW: h.scrollWidth, htmlClientW: h.clientWidth, bodyOverflowX: getComputedStyle(b).overflowX, bodyScrollW: b.scrollWidth };
  // 设置前的 scrollLeft 基线
  const baseHtml = h.scrollLeft, baseBody = b.scrollLeft, baseWin = window.scrollX;
  // 强制程序化滚动
  h.scrollLeft = 99999; b.scrollLeft = 99999; window.scrollTo(99999,0);
  out.afterSet = { htmlSL: h.scrollLeft, bodySL: b.scrollLeft, winX: window.scrollX };
  // 复位
  h.scrollLeft = baseHtml; b.scrollLeft = baseBody; window.scrollTo(baseWin,0);
  // 找出真正越界的可见元素（含 fixed/absolute）
  const vw = window.innerWidth;
  const off = [];
  document.querySelectorAll('body *').forEach(el => {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') return;
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return;
    if (r.right > vw + 2 || r.left < -2) {
      off.push({ sel: (el.tagName.toLowerCase()) + (el.id ? '#'+el.id : '') + (el.className && typeof el.className==='string' ? '.'+el.className.trim().split(/\\s+/).slice(0,2).join('.') : ''), left: Math.round(r.left), right: Math.round(r.right), w: Math.round(r.width), pos: cs.position, transform: cs.transform === 'none' ? 'none' : cs.transform, parent: el.parentElement ? el.parentElement.tagName.toLowerCase() + (el.parentElement.id?'#'+el.parentElement.id:'') : 'null' });
    }
  });
  out.offenders = off.slice(0, 20);
  return out;
})()`;

console.log('=== F-01 深度诊断 (1920x1080) ===');
await setSize(1920, 1080);
await goto(BASE + '/index.html');
await evalJs(KILL_ONB);
await sleep(600);
const d = await evalJs(DIAG);
console.log(JSON.stringify(d, null, 2));
ws.close();
process.exit(0);
