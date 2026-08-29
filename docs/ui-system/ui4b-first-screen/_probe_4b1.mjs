/**
 * UI-4B-1 First Screen Fusion —— 真实渲染验收探针（只读）
 * ---------------------------------------------------------------------------
 * 用途：在真实 Chromium 渲染下取 computed style 事实，验证 B1–B4 的实现结果，
 *       而不是靠"读 CSS 源码推断"。模型无法读 PNG，故一切判定以结构事实为准，
 *       截图仅作人眼复核归档。
 *
 * 前置：
 *   1) 静态服务：python -m http.server 8000 （cwd = xiao6-ui/）
 *   2) Chrome：--headless=new --remote-debugging-port=9222 --remote-allow-origins=*
 * 运行：node _probe_4b1.mjs
 * 产出：_probe_4b1.json + shots/*.png
 */
import { writeFileSync } from 'node:fs';
import { setTimeout as sleep } from 'node:timers/promises';

const BASE = process.env.ZZ_BASE || 'http://127.0.0.1:8000';
const OUT_DIR = new URL('./', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');

const { webSocketDebuggerUrl } = await (await fetch('http://127.0.0.1:9222/json/version')).json();
const ws = new WebSocket(webSocketDebuggerUrl);
await new Promise(r => ws.addEventListener('open', r, { once: true }));
let id = 0; const pending = new Map();
ws.addEventListener('message', e => {
  const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
});
const send = (method, params = {}, sessionId) => new Promise((res, rej) => {
  const _id = ++id;
  pending.set(_id, m => m.error ? rej(new Error(method + ':' + JSON.stringify(m.error))) : res(m.result));
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

/* ── 采集脚本：全部为只读 getComputedStyle / getBoundingClientRect ────────── */
const COLLECT = `(() => {
  const cs = sel => { const el = document.querySelector(sel); return el ? getComputedStyle(el) : null; };
  const rect = sel => { const el = document.querySelector(sel); if (!el) return null; const r = el.getBoundingClientRect(); return { w: Math.round(r.width), h: Math.round(r.height), x: Math.round(r.x), y: Math.round(r.y) }; };
  const pick = (sel, props) => {
    const s = cs(sel); if (!s) return { _missing: true };
    const o = { _rect: rect(sel) };
    for (const p of props) o[p] = s.getPropertyValue(p);
    return o;
  };
  const bf = sel => { const s = cs(sel); return s ? (s.backdropFilter || s.webkitBackdropFilter || 'none') : null; };

  // 首屏操作层全集（用于 glass-3 唯一性统计）
  const SURFACES = ['.os-nav', '.os-hud', '.os-core', '.os-panel.os-timeline', '.os-panel.os-dock', '.os-dock .os-dock-bar'];
  const glassMap = {};
  for (const sel of SURFACES) glassMap[sel] = bf(sel);
  document.querySelectorAll('.os-side .os-panel').forEach((el, i) => {
    glassMap['.os-side .os-panel[' + i + ']'] = getComputedStyle(el).backdropFilter || 'none';
  });
  const glass3Users = Object.entries(glassMap).filter(([, v]) => v && v.includes('26px')).map(([k]) => k);

  return {
    viewport: { w: innerWidth, h: innerHeight },
    presence: document.body.getAttribute('data-presence'),
    presenceColor: getComputedStyle(document.body).getPropertyValue('--presence-color').trim(),
    theme: document.documentElement.getAttribute('data-theme') || document.body.getAttribute('data-theme'),
    bodyClass: document.body.className,

    // ── B1 · World Window ────────────────────────────────────────────────
    core: pick('.os-core', ['backdrop-filter', 'border-top-color', 'box-shadow', 'background-color', 'background-image', 'isolation', 'overflow']),
    heroTitle: pick('.os-hero-title', ['text-shadow', 'color', 'font-size', 'display']),
    heroDesc: pick('.os-hero-desc', ['display']),
    heroActions: pick('.os-hero-actions', ['display']),

    // ── B2 · World Visibility ────────────────────────────────────────────
    solarCanvas: pick('#solarCanvas', ['filter', 'z-index', 'position', 'display', 'opacity']),
    galaxyVeil: pick('.galaxy-veil', ['opacity', 'z-index', 'pointer-events']),
    nav: pick('.os-nav', ['backdrop-filter', 'background-color', 'border-top-color']),
    hud: pick('.os-hud', ['backdrop-filter', 'background-color', 'border-top-color']),

    // ── B3 · Attention Budget ────────────────────────────────────────────
    glassMap, glass3Users, glass3Count: glass3Users.length,
    timelinePanel: pick('.os-panel.os-timeline', ['backdrop-filter', 'background-color', 'box-shadow']),
    sidePanelCount: document.querySelectorAll('.os-side .os-panel').length,
    sideOpen: document.body.classList.contains('os-context-open'),
    runtimeVizDisplay: (cs('#runtime-viz') || {}).display ?? '(absent)',
    execMonitorDisplay: (cs('#execution-monitor') || {}).display ?? '(absent)',

    // ── B4 · Command Dock ────────────────────────────────────────────────
    dockPanel: pick('.os-panel.os-dock', ['backdrop-filter', 'background-color', 'border-top-color', 'box-shadow', 'padding-top']),
    dockH3: pick('.os-dock > h3', ['font-size', 'opacity', 'color']),
    dockBar: pick('.os-dock .os-dock-bar', ['backdrop-filter', 'border-top-color', 'background-color', 'box-shadow']),
    dockInput: (() => {
      const el = document.querySelector('#osDockInput') || document.querySelector('.os-dock input');
      if (!el) return { _missing: true };
      const r = el.getBoundingClientRect();
      return { tag: el.tagName, id: el.id, disabled: el.disabled, readOnly: el.readOnly,
               w: Math.round(r.width), h: Math.round(r.height), placeholder: el.placeholder || '' };
    })(),
    dockButtons: [...document.querySelectorAll('.os-dock .os-dock-btn')].map(b => ({
      cls: b.className, title: b.title || b.getAttribute('aria-label') || '', disabled: b.disabled
    })),
    dockHint: (document.querySelector('.os-dock .os-dock-hint') || {}).textContent || null,

    // ── 回归 ─────────────────────────────────────────────────────────────
    scrollX: { scrollW: document.documentElement.scrollWidth, clientW: document.documentElement.clientWidth,
               canScrollX: Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth) },
    shellDisplay: (cs('#osShell') || {}).display ?? '(absent)',
    shellVisibility: (cs('#osShell') || {}).visibility ?? '(absent)',
    cssLoaded: [...document.styleSheets].map(s => (s.href || 'inline').split('/').pop()),
    jsErrors: (window.__zzProbeErrors || []).slice(0, 10)
  };
})()`;

const results = { generatedAt: new Date().toISOString(), base: BASE, viewports: {}, scopeGuard: {} };

async function loadAt(w, h, label) {
  await S('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 1, mobile: false });
  await S('Page.navigate', { url: BASE + '/index.html' });
  for (let i = 0; i < 80; i++) {
    if (await evalJs('document.readyState').catch(() => null) === 'complete') break;
    await sleep(200);
  }
  // 捕获运行时错误（静态服务下后端 API 必然 404，只关心是否影响 DOM 构建）
  await evalJs(`window.__zzProbeErrors=window.__zzProbeErrors||[];window.addEventListener('error',e=>window.__zzProbeErrors.push(String(e.message)));'ok'`);
  await sleep(2200);
  // 关闭首启引导，暴露真实首屏
  await evalJs(`try{localStorage.setItem('xiao6_onboarded','1')}catch(e){};document.querySelectorAll('.onb-overlay,#onbOverlay').forEach(o=>o.remove());'ok'`);
  await sleep(500);
  const data = await evalJs(COLLECT);
  const { data: png } = await S('Page.captureScreenshot', { format: 'png' });
  writeFileSync(`${OUT_DIR}shots/${label}.png`, Buffer.from(png, 'base64'));
  return data;
}

for (const [label, w, h] of [['1920x1080', 1920, 1080], ['1440x900', 1440, 900], ['720x1280', 720, 1280]]) {
  results.viewports[label] = await loadAt(w, h, label);
  console.log(`[probe] ${label} collected`);
}

/* ── 作用域护栏验证：chat-mode / universe-mode 下本层必须完全让位 ─────────── */
await S('Emulation.setDeviceMetricsOverride', { width: 1920, height: 1080, deviceScaleFactor: 1, mobile: false });
results.scopeGuard.baseline = await evalJs(`(()=>{const s=getComputedStyle(document.querySelector('.os-core'));
  return { backdropFilter: s.backdropFilter, backgroundImage: s.backgroundImage.slice(0,80), boxShadow: s.boxShadow.slice(0,60) };})()`);
for (const mode of ['chat-mode', 'universe-mode']) {
  await evalJs(`document.body.classList.add('${mode}');'ok'`);
  await sleep(300);
  results.scopeGuard[mode] = await evalJs(`(()=>{const s=getComputedStyle(document.querySelector('.os-core'));
    return { backdropFilter: s.backdropFilter, backgroundImage: s.backgroundImage.slice(0,80), boxShadow: s.boxShadow.slice(0,60),
             shellVisibility: getComputedStyle(document.getElementById('osShell')).visibility,
             shellDisplay: getComputedStyle(document.getElementById('osShell')).display };})()`);
  await evalJs(`document.body.classList.remove('${mode}');'ok'`);
  await sleep(200);
}

/* ── Context 抽屉展开（Secondary #2）验证 ─────────────────────────────────── */
await evalJs(`document.body.classList.add('os-context-open');'ok'`);
await sleep(600);
results.contextOpen = await evalJs(`(()=>{const p=document.querySelector('.os-side .os-panel');const a=document.querySelector('.os-side');
  return { sidePanelShadow: p?getComputedStyle(p).boxShadow:'(none)', sideTransform: a?getComputedStyle(a).transform:'(none)',
           sideOpacity: a?getComputedStyle(a).opacity:'(none)',
           canScrollX: Math.max(0, document.documentElement.scrollWidth-document.documentElement.clientWidth) };})()`);
const { data: png2 } = await S('Page.captureScreenshot', { format: 'png' });
writeFileSync(`${OUT_DIR}shots/1920x1080_context-open.png`, Buffer.from(png2, 'base64'));
await evalJs(`document.body.classList.remove('os-context-open');'ok'`);

/* ── AI Presence 联动验证（B4 关键主张：入口随 AI 状态呼吸）───────────────── */
results.presenceBinding = {};
for (const st of ['IDLE', 'THINKING', 'EXECUTING', 'ERROR']) {
  await evalJs(`document.body.setAttribute('data-presence','${st}');'ok'`);
  await sleep(250);
  results.presenceBinding[st] = await evalJs(`(()=>{const b=document.querySelector('.os-dock .os-dock-bar');const c=document.querySelector('.os-core');
    return { presenceColor: getComputedStyle(document.body).getPropertyValue('--presence-color').trim(),
             dockBarBorder: b?getComputedStyle(b).borderTopColor:'(no bar)',
             coreBgFirstStop: c?(getComputedStyle(c).backgroundImage.match(/rgba?\\([^)]*\\)/)||['(none)'])[0]:'(no core)' };})()`);
}
const { data: png3 } = await S('Page.captureScreenshot', { format: 'png' });
writeFileSync(`${OUT_DIR}shots/1920x1080_presence-ERROR.png`, Buffer.from(png3, 'base64'));

writeFileSync(`${OUT_DIR}_probe_4b1.json`, JSON.stringify(results, null, 2));
console.log('[probe] done -> _probe_4b1.json');
ws.close();
