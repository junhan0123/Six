/** 诊断：① 是否真实产生横向滚动 ② 主题切换为何失效 */
import { setTimeout as sleep } from 'node:timers/promises';
const BASE = 'http://127.0.0.1:8000';
const { webSocketDebuggerUrl } = await (await fetch('http://127.0.0.1:9222/json/version')).json();
const ws = new WebSocket(webSocketDebuggerUrl);
await new Promise(r => ws.addEventListener('open', r, { once: true }));
let id = 0; const pending = new Map();
ws.addEventListener('message', e => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } });
const send = (method, params = {}, sessionId) => new Promise((res, rej) => { const _id = ++id; pending.set(_id, m => m.error ? rej(new Error(JSON.stringify(m.error))) : res(m.result)); ws.send(JSON.stringify({ id: _id, method, params, sessionId })); });
const { targetInfos } = await send('Target.getTargets');
const page = targetInfos.find(t => t.type === 'page');
const { sessionId } = await send('Target.attachToTarget', { targetId: page.targetId, flatten: true });
const S = (m, p) => send(m, p, sessionId);
await S('Page.enable'); await S('Runtime.enable');
const ev = async (expr) => { const r = await S('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }); if (r.exceptionDetails) throw new Error(r.exceptionDetails.text); return r.result?.value; };

await S('Emulation.setDeviceMetricsOverride', { width: 1600, height: 900, deviceScaleFactor: 1, mobile: false });
await S('Page.navigate', { url: BASE + '/index.html' });
for (let i = 0; i < 50; i++) { if (await ev('document.readyState') === 'complete') break; await sleep(200); }
await sleep(1800);
await ev(`try{localStorage.setItem('xiao6_onboarded','1')}catch(e){}; (document.getElementById('onbOverlay')||{remove(){}}).remove(); 'ok'`);
await sleep(500);

console.log('=== ① 横向滚动实测 ===');
console.log(await ev(`(()=>{
  const h=document.documentElement,b=document.body;
  const before=h.scrollLeft;
  h.scrollLeft=9999; b.scrollLeft=9999;
  const after=Math.max(h.scrollLeft,b.scrollLeft);
  h.scrollLeft=before;
  return { htmlOverflowX:getComputedStyle(h).overflowX, bodyOverflowX:getComputedStyle(b).overflowX,
           htmlScrollW:h.scrollWidth, bodyScrollW:b.scrollWidth, winW:innerWidth,
           canScrollRight:after, verdict: after>1 ? '会真实横向滚动(缺陷)' : '不可滚动(安全)' };
})()`));

console.log('\n=== ② .os-side 归属确认 ===');
console.log(await ev(`(()=>{
  const s=document.querySelector('.os-side'); if(!s) return 'no .os-side';
  const r=s.getBoundingClientRect(); const cs=getComputedStyle(s);
  const inner=[...s.querySelectorAll('.os-panel')].map(p=>{const q=p.getBoundingClientRect();return {cls:p.className,x:Math.round(q.x),right:Math.round(q.right)}});
  return { x:Math.round(r.x), right:Math.round(r.right), w:Math.round(r.width), pos:cs.position,
           transform:cs.transform, bodyClass:document.body.className, inner };
})()`));

console.log('\n=== ③ 主题切换链路 ===');
for (const t of ['quantum','light','dark-amber']) {
  const out = await ev(`(()=>{
    document.body.setAttribute('data-theme','${t}');
    const a = document.body.getAttribute('data-theme');
    const csBody = getComputedStyle(document.body);
    return { setTo:'${t}', readBackImmediate:a, bodyBg:csBody.backgroundColor,
             accentFromBody:csBody.getPropertyValue('--accent').trim(),
             accentFromRoot:getComputedStyle(document.documentElement).getPropertyValue('--accent').trim(),
             htmlAttr:document.documentElement.getAttribute('data-theme') };
  })()`);
  console.log(' 立即:', JSON.stringify(out));
  await sleep(900);
  const after = await ev(`(()=>{const cs=getComputedStyle(document.body);return {
    afterDelay:document.body.getAttribute('data-theme'), bodyBg:cs.backgroundColor,
    accent:cs.getPropertyValue('--accent').trim() };})()`);
  console.log(' 900ms后:', JSON.stringify(after), after.afterDelay === t ? '' : '  <<< 被改回了！');
}

console.log('\n=== ④ 谁在改 data-theme（挂观察器后再试）===');
console.log(await ev(`(()=>{
  window.__zzMut=[];
  const mo=new MutationObserver(ms=>{ms.forEach(m=>{ if(m.attributeName==='data-theme')
    window.__zzMut.push({old:m.oldValue,now:document.body.getAttribute('data-theme'),stack:(new Error()).stack.split('\\n').slice(1,4).join(' | ')});});});
  mo.observe(document.body,{attributes:true,attributeOldValue:true,attributeFilter:['data-theme']});
  window.__zzMO=mo; return 'observing';
})()`));
await ev(`document.body.setAttribute('data-theme','light'); 'set'`);
await sleep(1200);
console.log(await ev(`JSON.stringify(window.__zzMut)`));
console.log('最终:', await ev(`document.body.getAttribute('data-theme')`));

console.log('\n=== ⑤ ZZSettings 主题写入 ===');
console.log(await ev(`(()=>{ try{ return { hasZZSettings: !!window.ZZSettings,
  keys: window.ZZSettings? Object.keys(window.ZZSettings).slice(0,20):[],
  cur: window.ZZSettings&&ZZSettings.get? ZZSettings.get('theme'):'n/a',
  ls: localStorage.getItem('zz_settings')?.slice(0,160) }; }catch(e){return String(e)} })()`));
ws.close(); process.exit(0);
