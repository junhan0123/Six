/**
 * Formal UI System v1.0 — GUI 验收截图（Chrome DevTools Protocol）
 * 目标：四模式 × 关键视图 × 9 主题 的真实 GUI 证据。
 * 纪律：只读取与截图，不写入项目任何源码。
 */
import { writeFileSync, mkdirSync } from 'node:fs';
import { setTimeout as sleep } from 'node:timers/promises';

const BASE = process.env.ZZ_BASE || 'http://127.0.0.1:8000';
const OUT = 'G:/xiao6/docs/ui-consolidation/shots-formal';
mkdirSync(OUT, { recursive: true });

const res = await fetch('http://127.0.0.1:9222/json/version');
const { webSocketDebuggerUrl } = await res.json();
const ws = new WebSocket(webSocketDebuggerUrl);
await new Promise(r => ws.addEventListener('open', r, { once: true }));

let id = 0;
const pending = new Map();
ws.addEventListener('message', (ev) => {
  const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
});
function send(method, params = {}, sessionId) {
  const _id = ++id;
  return new Promise((resolve, reject) => {
    pending.set(_id, (m) => m.error ? reject(new Error(method + ': ' + JSON.stringify(m.error))) : resolve(m.result));
    ws.send(JSON.stringify({ id: _id, method, params, sessionId }));
  });
}

// 附着到第一个 page target
const { targetInfos } = await send('Target.getTargets');
let page = targetInfos.find(t => t.type === 'page');
if (!page) {
  const t = await send('Target.createTarget', { url: 'about:blank' });
  page = { targetId: t.targetId };
}
const { sessionId } = await send('Target.attachToTarget', { targetId: page.targetId, flatten: true });
const S = (m, p) => send(m, p, sessionId);

await S('Page.enable');
await S('Runtime.enable');

const errors = [];
ws.addEventListener('message', (ev) => {
  const m = JSON.parse(ev.data);
  if (m.method === 'Runtime.exceptionThrown') {
    errors.push(m.params?.exceptionDetails?.exception?.description
      || m.params?.exceptionDetails?.text || 'unknown');
  }
});

async function evalJs(expr) {
  const r = await S('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.text + ' :: ' + expr.slice(0, 80));
  return r.result?.value;
}

async function setSize(w, h) {
  await S('Emulation.setDeviceMetricsOverride', {
    width: w, height: h, deviceScaleFactor: 1, mobile: false
  });
}

async function goto(url) {
  await S('Page.navigate', { url });
  // 等 load
  for (let i = 0; i < 60; i++) {
    const st = await evalJs('document.readyState').catch(() => null);
    if (st === 'complete') break;
    await sleep(200);
  }
  await sleep(1400); // 等 JS 初始化 / 动画落定
}

async function shot(name) {
  const { data } = await S('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
  writeFileSync(`${OUT}/${name}.png`, Buffer.from(data, 'base64'));
  console.log('  shot ->', name);
}

// 关掉引导浮层（首启会挡住整个界面）
const KILL_ONB = `
  try{ localStorage.setItem('xiao6_onboarded','1'); }catch(e){}
  try{ var o=document.getElementById('onbOverlay'); if(o) o.remove(); }catch(e){}
  'ok'`;

const REPORT = { sizes: [], themes: [], overflow: [], errors: [] };

// ── 探针：检测溢出/重叠/裁切 ───────────────────────────────────────────────
const PROBE = `(() => {
  const h = document.documentElement;
  const before = h.scrollLeft; h.scrollLeft = 9999;
  const canScrollX = Math.max(h.scrollLeft, document.body.scrollLeft); h.scrollLeft = before;
  const out = { docW: h.scrollWidth, winW: window.innerWidth,
                docH: h.scrollHeight, winH: window.innerHeight,
                canScrollX, offenders: [] };
  const vw = window.innerWidth;
  // .os-side 是 Context 抽屉，收起态以 transform 有意停靠在视口外（前序 Sprint 设计），
  // 其子树不计入溢出。真正的判据是 canScrollX（页面能否被横向拖走）。
  const drawer = document.querySelector('.os-side');
  document.querySelectorAll('body *').forEach(el => {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || cs.opacity === '0') return;
    if (drawer && (el === drawer || drawer.contains(el))) return;
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return;
    // 横向溢出视口
    if (r.right > vw + 1.5 || r.left < -1.5) {
      if (cs.position === 'fixed' || cs.position === 'absolute') {
        // 浮层允许在视口外待命（未激活状态），只记录可见的
        if (parseFloat(cs.opacity) < 0.05) return;
        if (cs.transform && cs.transform !== 'none' && r.left < -50) return;
      }
      out.offenders.push({
        sel: el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') +
             (el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\\s+/).slice(0,2).join('.') : ''),
        left: Math.round(r.left), right: Math.round(r.right), w: Math.round(r.width), pos: cs.position
      });
    }
  });
  out.offenders = out.offenders.slice(0, 14);
  return out;
})()`;

// ── 1. 四模式 × 主视图 ─────────────────────────────────────────────────────
const SIZES = [
  ['1920x1080', 1920, 1080, 'Desktop'],
  ['1600x900', 1600, 900, 'Desktop'],
  ['1280x800', 1280, 800, 'Desktop'],
  ['1000x800', 1000, 800, 'Compact'],
  ['720x900', 720, 900, 'Narrow'],
];

for (const [tag, w, h, mode] of SIZES) {
  console.log(`\n[${mode}] ${tag}`);
  await setSize(w, h);
  await goto(BASE + '/index.html');
  await evalJs(KILL_ONB);
  await sleep(600);
  await shot(`10-${tag}-${mode}-home`);
  const probe = await evalJs(PROBE);
  REPORT.sizes.push({ tag, mode, ...probe });
  if (probe.offenders.length) {
    console.log('   ! 溢出候选:', probe.offenders.length);
    probe.offenders.forEach(o => console.log('     ', o.sel, o.left, '->', o.right, `(vw=${w})`));
  }
}

// ── 2. 9 主题一致性（Desktop 1600x900）──────────────────────────────────────
const THEMES = ['dark', 'quantum', 'midnight', 'dark-cyan', 'dark-green',
                'dark-purple', 'dark-amber', 'dark-rose', 'light'];
console.log('\n[Themes] 1600x900');
await setSize(1600, 900);
await goto(BASE + '/index.html');
await evalJs(KILL_ONB);
for (const t of THEMES) {
  // 只写 body[data-theme]（主题的唯一生效入口）。不调用 ZZSettings.set：
  // 其签名为 set(partialObject)，误传 (key,value) 会把字符串展开成 {0:'t',1:'h',...}
  // 污染 localStorage，并在随后 apply 时把主题改回存储值，导致 9 张截图全同。
  await evalJs(`document.body.setAttribute('data-theme','${t}'); '${t}'`);
  await sleep(650);
  await shot(`20-theme-${t}`);
  const v = await evalJs(`(() => {
    const cs = getComputedStyle(document.body);
    const btn = document.querySelector('.os-dock-btn, button');
    return { theme: document.body.getAttribute('data-theme'),
             bg: cs.backgroundColor, color: cs.color,
             accent: cs.getPropertyValue('--accent').trim(),
             presence: cs.getPropertyValue('--presence-color').trim(),
             dataPresence: document.body.getAttribute('data-presence'),
             btnFont: btn ? getComputedStyle(btn).fontFamily.split(',')[0].replace(/["']/g,'') : 'n/a',
             btnSize: btn ? getComputedStyle(btn).fontSize : 'n/a' };
  })()`);
  REPORT.themes.push(v);
  console.log('  ', t, '->', JSON.stringify(v));
}

// ── 3. 关键浮层 / 面板 ─────────────────────────────────────────────────────
console.log('\n[Overlays] 1600x900');
await evalJs(`document.body.setAttribute('data-theme','dark-cyan'); 'ok'`);
await sleep(400);

const OVERLAYS = [
  ['30-command-palette', `try{ ZZCommandPalette && ZZCommandPalette.open && ZZCommandPalette.open(); }catch(e){ 'x' } 'ok'`],
  ['31-settings', `try{ ZZSettings && ZZSettings.open && ZZSettings.open(); }catch(e){} 'ok'`],
  ['32-onboarding', `try{ var o=document.getElementById('onbOverlay'); if(o){o.classList.add('show'); o.style.display='';} else if(window.ZZOnboarding&&ZZOnboarding.start) ZZOnboarding.start(); }catch(e){} 'ok'`],
];
for (const [name, js] of OVERLAYS) {
  await goto(BASE + '/index.html');
  await evalJs(KILL_ONB);
  await sleep(500);
  await evalJs(js);
  await sleep(900);
  await shot(name);
}

REPORT.errors = errors.slice(0, 30);
writeFileSync(`${OUT}/_probe.json`, JSON.stringify(REPORT, null, 2), 'utf-8');
console.log('\n=== 完成，报告写入 _probe.json ===');
console.log('JS 运行时异常数：', errors.length);
errors.slice(0, 10).forEach(e => console.log('  !', String(e).split('\n')[0]));
ws.close();
process.exit(0);
