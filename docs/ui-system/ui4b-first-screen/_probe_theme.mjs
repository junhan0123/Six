/**
 * UI-4B-1 · 9 主题兼容抽查（只读）
 * 本层所有颜色均由 color-mix() 从 --bg / --surface / --border / --presence-color 派生，
 * 理论上主题无关。此探针用真实渲染证实：9 主题下 World Window 与 Dock 均不塌陷。
 */
import { writeFileSync } from 'node:fs';
import { setTimeout as sleep } from 'node:timers/promises';
const BASE = process.env.ZZ_BASE || 'http://127.0.0.1:8000';
const OUT = new URL('./', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');

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
const evalJs = async expr => {
  const r = await S('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.text);
  return r.result?.value;
};

await S('Emulation.setDeviceMetricsOverride', { width: 1600, height: 900, deviceScaleFactor: 1, mobile: false });
await S('Page.navigate', { url: BASE + '/index.html' });
for (let i = 0; i < 80; i++) { if (await evalJs('document.readyState').catch(() => null) === 'complete') break; await sleep(200); }
await sleep(2000);
await evalJs(`try{localStorage.setItem('xiao6_onboarded','1')}catch(e){};document.querySelectorAll('.onb-overlay,#onbOverlay').forEach(o=>o.remove());'ok'`);

const THEMES = ['dark', 'quantum', 'midnight', 'dark-cyan', 'dark-green', 'dark-purple', 'dark-amber', 'dark-rose', 'light'];
const out = { generatedAt: new Date().toISOString(), themes: {} };

for (const t of THEMES) {
  await evalJs(`document.documentElement.setAttribute('data-theme','${t}');document.body.setAttribute('data-theme','${t}');'ok'`);
  await sleep(320);
  out.themes[t] = await evalJs(`(()=>{
    const core=document.querySelector('.os-core'), bar=document.querySelector('.os-dock .os-dock-bar'),
          hero=document.querySelector('.os-hero-title'), nav=document.querySelector('.os-nav');
    const g=getComputedStyle;
    return {
      bg: g(document.body).getPropertyValue('--bg').trim(),
      text: g(document.body).getPropertyValue('--text').trim(),
      coreBf: core?g(core).backdropFilter:'(none)',
      coreBorderAlpha: core?g(core).borderTopColor:'(none)',
      coreHasGradient: core? g(core).backgroundImage.includes('radial-gradient') : false,
      heroTextShadow: hero? g(hero).textShadow.slice(0,70) : '(none)',
      heroColor: hero? g(hero).color : '(none)',
      barBf: bar?g(bar).backdropFilter:'(MISSING BAR)',
      barBorder: bar?g(bar).borderTopColor:'(MISSING BAR)',
      navBf: nav?g(nav).backdropFilter:'(none)',
      canvasFilter: g(document.getElementById('solarCanvas')).filter,
      canScrollX: Math.max(0, document.documentElement.scrollWidth-document.documentElement.clientWidth)
    };})()`);
  if (t === 'light' || t === 'dark-cyan') {
    const { data } = await S('Page.captureScreenshot', { format: 'png' });
    writeFileSync(`${OUT}shots/theme_${t}.png`, Buffer.from(data, 'base64'));
  }
}
writeFileSync(`${OUT}_probe_theme.json`, JSON.stringify(out, null, 2));
console.log('[theme-probe] done');
ws.close();
