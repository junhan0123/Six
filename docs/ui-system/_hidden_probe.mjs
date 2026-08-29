/**
 * 隐藏机制与焦点陷阱实测（只读）
 * 目的：查清 #app / .rail / .main / .tele 等旧外壳的隐藏方式，
 *      并检测「视觉不可见但仍可 Tab 聚焦」的焦点陷阱（真实可访问性缺陷）。
 */
import { writeFileSync } from 'node:fs';
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
await sleep(1800);
await evalJs(`try{localStorage.setItem('xiao6_onboarded','1')}catch(e){};var o=document.getElementById('onbOverlay');if(o)o.remove();'ok'`);

const R = await evalJs(`(() => {
  const sels = ['#app','.rail','.main','#tele','#zzPanel','#memPanel','#toast','#settingsPanel','.os-side'];
  const how = sels.map(sel => {
    const el = document.querySelector(sel);
    if (!el) return { sel, exists:false };
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    let reason = [];
    if (cs.display === 'none') reason.push('display:none');
    if (cs.visibility === 'hidden') reason.push('visibility:hidden');
    if (parseFloat(cs.opacity) <= 0.01) reason.push('opacity:' + cs.opacity);
    if (el.hasAttribute('hidden')) reason.push('[hidden]');
    if (r.width <= 1 || r.height <= 1) reason.push('zero-size');
    if (r.right <= 0 || r.left >= innerWidth) reason.push('offscreen-x');
    return { sel, exists:true, reason: reason.join(' + ') || '(可见)',
             display: cs.display, visibility: cs.visibility, opacity: cs.opacity,
             transform: cs.transform === 'none' ? 'none' : cs.transform,
             pointerEvents: cs.pointerEvents,
             rect:{x:Math.round(r.x),y:Math.round(r.y),w:Math.round(r.width),h:Math.round(r.height)} };
  });

  // 焦点陷阱：可聚焦但视觉不可见的元素
  const FOCUSABLE = 'a[href],button,input,select,textarea,[tabindex]:not([tabindex="-1"])';
  const all = Array.from(document.querySelectorAll(FOCUSABLE));
  const isRendered = el => {
    // display:none / visibility:hidden 的元素不可聚焦（浏览器保证），故只查 opacity / 离屏
    let n = el, opa = 1;
    while (n && n !== document.documentElement) {
      const cs = getComputedStyle(n);
      if (cs.display === 'none' || cs.visibility === 'hidden') return { rendered:false };
      opa *= parseFloat(cs.opacity);
      n = n.parentElement;
    }
    return { rendered:true, opacity: opa };
  };
  const traps = [];
  for (const el of all) {
    if (el.disabled) continue;
    const st = isRendered(el);
    if (!st.rendered) continue;             // 真隐藏，浏览器已排除出 Tab 序列
    const r = el.getBoundingClientRect();
    const offscreen = r.right <= 0 || r.left >= innerWidth || r.bottom <= 0 || r.top >= innerHeight;
    const invisible = st.opacity <= 0.01;
    if (offscreen || invisible) {
      const owner = el.closest('#app,#osShell,#settingsPanel,#capPanel,#sysPromptPanel,#memPanel,#universeView') || document.body;
      traps.push({
        tag: el.tagName.toLowerCase() + (el.id ? '#'+el.id : ''),
        owner: owner.id ? '#'+owner.id : owner.tagName.toLowerCase(),
        why: invisible ? ('opacity=' + st.opacity.toFixed(2)) : 'offscreen',
        rect: Math.round(r.x)+','+Math.round(r.y)
      });
    }
  }
  const byOwner = {};
  traps.forEach(t => { const k = t.owner + ' / ' + t.why.split('=')[0]; byOwner[k] = (byOwner[k]||0)+1; });
  return { how, focusableTotal: all.length, trapCount: traps.length, byOwner,
           sample: traps.slice(0, 12) };
})()`);

console.log('='.repeat(100));
console.log('隐藏机制实测');
console.log('='.repeat(100));
for (const h of R.how) {
  if (!h.exists) { console.log(`  ${h.sel.padEnd(16)} 不存在`); continue; }
  console.log(`  ${h.sel.padEnd(16)} ${h.reason.padEnd(34)} pe:${h.pointerEvents.padEnd(6)} rect=${h.rect.w}x${h.rect.h}@(${h.rect.x},${h.rect.y})`);
}
console.log('\n' + '='.repeat(100));
console.log('焦点陷阱检测（视觉不可见 / 离屏，但仍在 Tab 序列中）');
console.log('='.repeat(100));
console.log(`  页面可聚焦元素总数: ${R.focusableTotal}`);
console.log(`  焦点陷阱数量:       ${R.trapCount}  ${R.trapCount > 0 ? '❌' : '✅'}`);
if (R.trapCount) {
  console.log('\n  按归属统计:');
  Object.entries(R.byOwner).sort((a,b)=>b[1]-a[1]).forEach(([k,v]) => console.log(`    ${k.padEnd(34)} ${v} 个`));
  console.log('\n  样例:');
  R.sample.forEach(t => console.log(`    ${t.tag.padEnd(26)} owner=${t.owner.padEnd(10)} ${t.why.padEnd(14)} @${t.rect}`));
}
writeFileSync('G:/xiao6/docs/ui-system/_hidden_probe.json', JSON.stringify(R, null, 2), 'utf-8');
console.log('\nWROTE _hidden_probe.json');
ws.close(); process.exit(0);
