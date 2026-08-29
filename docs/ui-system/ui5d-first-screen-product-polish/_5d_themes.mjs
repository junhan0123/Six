/**
 * UI-5D · 9 主题横滚回归（Chrome DevTools Protocol）
 * 纪律：只读取 / 探针，不写入源码。
 */
import { writeFileSync, mkdirSync } from 'node:fs';
import { setTimeout as sleep } from 'node:timers/promises';

const BASE = process.env.ZZ_BASE || 'http://127.0.0.1:8000';
const ROOT = 'G:/xiao6/docs/ui-system/ui5d-first-screen-product-polish';
const OUT = `${ROOT}/shots-themes`;
mkdirSync(OUT, { recursive: true });

const res = await fetch('http://127.0.0.1:9222/json/version');
const { webSocketDebuggerUrl } = await res.json();
const ws = new WebSocket(webSocketDebuggerUrl);
await new Promise(r => ws.addEventListener('open', r, { once: true }));
let id = 0; const pending = new Map(); const errors = [];
ws.addEventListener('message', (ev) => { const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
  if (m.method === 'Runtime.exceptionThrown') errors.push(m.params?.exceptionDetails?.text || 'unknown'); });
function send(method, params = {}, sessionId) { const _id = ++id;
  return new Promise((resolve, reject) => { pending.set(_id, (m) => m.error ? reject(new Error(JSON.stringify(m.error))) : resolve(m.result));
    ws.send(JSON.stringify({ id: _id, method, params, sessionId })); }); }
const { targetInfos } = await send('Target.getTargets');
let page = targetInfos.find(t => t.type === 'page') || (await send('Target.createTarget', { url: 'about:blank' }));
const { sessionId } = await send('Target.attachToTarget', { targetId: page.targetId, flatten: true });
const S = (m, p) => send(m, p, sessionId);
await S('Page.enable'); await S('Runtime.enable'); await S('Network.clearBrowserCache');
async function evalJs(e) { const r = await S('Runtime.evaluate', { expression: e, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.text); return r.result?.value; }
const setSize = (w, h) => S('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 1, mobile: false });
async function goto(u) { await S('Page.navigate', { url: u });
  for (let i=0;i<60;i++){ if ((await evalJs('document.readyState').catch(()=>null))==='complete') break; await sleep(200);} await sleep(1200); }
async function shot(n){ const { data } = await S('Page.captureScreenshot', { format:'png', captureBeyondViewport:false });
  writeFileSync(`${OUT}/${n}.png`, Buffer.from(data,'base64')); }

const THEMES = ['dark','quantum','midnight','dark-cyan','dark-green','dark-purple','dark-amber','dark-rose','light'];
const REP = { at: new Date().toISOString(), themes: [], errors: [] };
await setSize(1920, 1080);
for (const t of THEMES) {
  await goto(BASE + '/index.html');
  await evalJs(`try{localStorage.setItem('xiao6_onboarded','1');}catch(e){} try{var o=document.getElementById('onbOverlay');if(o)o.remove();}catch(e){} 'ok'`);
  // 切换主题（点击色板按钮，触发既有 theme handler）
  await evalJs(`try{ document.querySelector('.os-theme-picker button[data-theme="${t}"]').click(); }catch(e){} 'ok'`);
  await sleep(900);
  const m = await evalJs(`(() => {
    const de = document.documentElement, b = document.body;
    const sw = de.scrollWidth, iw = window.innerWidth;
    const pc = getComputedStyle(b).getPropertyValue('--presence-color').trim();
    const bg = getComputedStyle(b).getPropertyValue('--bg').trim();
    const shell = document.querySelector('#osShell'); const sr = shell ? shell.getBoundingClientRect() : null;
    const navLabel = getComputedStyle(document.querySelector('.os-nav-btn[data-nav="workspace"]'),'::after').content.replace(/^["']|["']$/g,'');
    return { scrollW: sw, innerW: iw, horizOverflow: sw > iw + 1, presenceColor: pc, bg,
             shellW: sr ? Math.round(sr.width) : 0, navLabel };
  })()`);
  await shot(`theme-${t}`);
  m.theme = t; REP.themes.push(m);
  console.log(`  theme ${t.padEnd(10)} horizOverflow=${m.horizOverflow} scrollW=${m.scrollW}/${m.innerW} navLabel="${m.navLabel}" bg=${m.bg}`);
}
REP.errors = errors.slice(0,20);
writeFileSync(`${ROOT}/_probe_themes.json`, JSON.stringify(REP, null, 2), 'utf-8');
const bad = REP.themes.filter(t => t.horizOverflow);
console.log(`\n=== 9 主题横滚回归完成 === 异常:${errors.length} 横滚主题:${bad.length}`);
bad.forEach(b => console.log('  OVERFLOW:', b.theme));
ws.close(); process.exit(0);
