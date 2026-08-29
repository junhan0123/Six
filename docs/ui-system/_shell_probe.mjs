/**
 * 双外壳共存关系实测（只读探针）
 * index.html 同时存在 #osShell(.os-shell) 与 #app(.app) 两套完整外壳。
 * 判定：是互斥切换、还是同时渲染（后者意味着两套导航/主区/侧栏真实并存）。
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

const REPORT = `(() => {
  const info = (sel) => {
    const el = document.querySelector(sel);
    if (!el) return { sel, exists: false };
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    // 真实可见：非 display:none / visibility:hidden / opacity:0 / 零面积
    const visible = cs.display !== 'none' && cs.visibility !== 'hidden'
      && parseFloat(cs.opacity) > 0.01 && r.width > 1 && r.height > 1;
    return {
      sel, exists: true, visible,
      display: cs.display, opacity: cs.opacity, zIndex: cs.zIndex,
      position: cs.position, pointerEvents: cs.pointerEvents,
      rect: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) },
      area: Math.round(r.width * r.height),
      hiddenAttr: el.hasAttribute('hidden'),
      childCount: el.children.length,
    };
  };
  const shells = ['#osShell', '#app', '#universeView', '.galaxy-veil'].map(info);
  const parts = ['.os-nav', '.os-hud', '.os-core', '.os-side', '.os-bottom',
                 '.rail', '.main', '.tele'].map(info);
  const overlays = ['#settingsOverlay', '#settingsPanel', '#sysPromptOverlay', '#capOverlay',
                    '#memPanel', '#zzPanel', '#toast', '#onbOverlay'].map(info);
  // 顶层元素堆叠：谁在最上面
  const vw = window.innerWidth, vh = window.innerHeight;
  const centerStack = document.elementsFromPoint(vw / 2, vh / 2).slice(0, 6)
    .map(e => e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + (e.className && typeof e.className === 'string' ? '.' + e.className.trim().split(/\\s+/).slice(0,2).join('.') : ''));
  return { shells, parts, overlays, centerStack, vw, vh,
           bodyClass: document.body.className, bodyTheme: document.body.getAttribute('data-theme') };
})()`;

const r = await evalJs(REPORT);

const line = (o) => o.exists
  ? `${o.sel.padEnd(18)} ${(o.visible ? '可见' : '隐藏').padEnd(5)} display:${o.display.padEnd(7)} z:${String(o.zIndex).padEnd(6)} rect=${o.rect.w}x${o.rect.h}@(${o.rect.x},${o.rect.y}) children:${o.childCount}`
  : `${o.sel.padEnd(18)} 不存在`;

console.log('='.repeat(104));
console.log('双外壳共存关系实测 @1920x1080   body.class="' + r.bodyClass + '"  theme=' + r.bodyTheme);
console.log('='.repeat(104));
console.log('\n【外壳级】');
r.shells.forEach(o => console.log('  ' + line(o)));
console.log('\n【外壳内部区块】');
r.parts.forEach(o => console.log('  ' + line(o)));
console.log('\n【Overlay / Panel】');
r.overlays.forEach(o => console.log('  ' + line(o)));
console.log('\n【视口中心命中堆叠（从上到下）】');
r.centerStack.forEach((s, i) => console.log(`  ${i + 1}. ${s}`));

const visShells = r.shells.filter(s => s.exists && s.visible).map(s => s.sel);
const visParts = r.parts.filter(s => s.exists && s.visible).map(s => s.sel);
console.log('\n' + '='.repeat(104));
console.log('判定：同时可见的外壳 = [' + visShells.join(', ') + ']');
console.log('      同时可见的区块 = [' + visParts.join(', ') + ']');
const dualNav = visParts.includes('.os-nav') && visParts.includes('.rail');
const dualMain = visParts.includes('.os-core') && visParts.includes('.main');
const dualSide = visParts.includes('.os-side') && visParts.includes('.tele');
console.log('      双导航并存: ' + (dualNav ? '是 ❌' : '否 ✅')
  + '   双主区并存: ' + (dualMain ? '是 ❌' : '否 ✅')
  + '   双侧栏并存: ' + (dualSide ? '是 ❌' : '否 ✅'));

writeFileSync('G:/xiao6/docs/ui-system/_shell_probe.json', JSON.stringify(r, null, 2), 'utf-8');
console.log('\nWROTE _shell_probe.json');
ws.close(); process.exit(0);
