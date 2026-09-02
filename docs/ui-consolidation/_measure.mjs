/** 真实渲染态测量：面板 / 按钮 / 输入 / 徽章 的视觉一致性量化 */
import { setTimeout as sleep } from 'node:timers/promises';
import { writeFileSync } from 'node:fs';
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
// 打开尽量多的面板，让隐藏组件进入渲染态
await ev(`['osCtxToggle','osNavCap','osNavMem','osNavExec'].forEach(i=>{const e=document.getElementById(i); if(e) e.click();}); 'ok'`);
await sleep(1200);

const R = await ev(`(() => {
  const round = n => Math.round(parseFloat(n) || 0);
  const grp = (label, sel) => {
    const out = {};
    document.querySelectorAll(sel).forEach(el => {
      const cs = getComputedStyle(el);
      if (cs.display === 'none' || cs.visibility === 'hidden') return;
      const r = el.getBoundingClientRect();
      if (r.width < 2 || r.height < 2) return;
      const k = JSON.stringify({
        radius: cs.borderRadius.split(' ')[0],
        border: cs.borderTopWidth + ' ' + cs.borderTopStyle,
        blur: (cs.backdropFilter && cs.backdropFilter !== 'none') ? cs.backdropFilter : '-',
        shadow: cs.boxShadow === 'none' ? '-' : cs.boxShadow.slice(0, 44),
        pad: cs.paddingTop + '/' + cs.paddingLeft,
        font: cs.fontSize + ' ' + cs.fontFamily.split(',')[0].replace(/["']/g,''),
        h: round(r.height)
      });
      out[k] = (out[k] || 0) + 1;
    });
    return { label, sel, variants: Object.keys(out).length,
             rows: Object.entries(out).sort((a,b)=>b[1]-a[1]).slice(0,8).map(([k,c])=>({...JSON.parse(k), n:c})) };
  };
  return {
    panels: grp('Surface/面板',
      '.zz-panel,.zz-panel-card,.os-panel,.settings-card,.cap-card,.scene-card,.hs-list-card,.onb-card,.cp-panel,.mem-card'),
    buttons: grp('Control/按钮',
      'button:not(.os-theme-picker button):not(.onb-theme)'),
    inputs: grp('Control/输入', 'input[type=text],input:not([type]),textarea,select,.onb-input'),
    badges: grp('Information/徽章', '.cp-badge,.zz-badge,.cap-badge,.os-cap-vit,.hs-tag,.mem-tag,.tele-ai')
  };
})()`);

for (const k of Object.keys(R)) {
  const g = R[k];
  console.log('\n' + '='.repeat(78));
  console.log(`【${g.label}】 可见变体数 = ${g.variants}`);
  g.rows.forEach(r => console.log(
    `  x${String(r.n).padEnd(3)} h=${String(r.h).padEnd(4)} r=${String(r.radius).padEnd(8)} bd=${String(r.border).padEnd(12)} pad=${String(r.pad).padEnd(14)} font=${String(r.font).padEnd(18)} blur=${r.blur}`));
}
writeFileSync('G:/xiao6/docs/ui-consolidation/shots-formal/_measure.json', JSON.stringify(R, null, 2), 'utf-8');
ws.close(); process.exit(0);
