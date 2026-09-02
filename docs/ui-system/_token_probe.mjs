/**
 * Formal UI System v1.0 — Section 2 令牌分叉实测探针
 * 目的：用真实浏览器验证 styles.css body[data-theme] 与 ui2.css [data-theme] 的令牌冲突
 *       是否造成实际渲染破坏（--glow 类型冲突 / light 主题分叉）。
 * 纪律：只读 + 临时 DOM 探针，不写入任何项目源码。
 */
import { writeFileSync, mkdirSync } from 'node:fs';
import { setTimeout as sleep } from 'node:timers/promises';

const BASE = process.env.ZZ_BASE || 'http://127.0.0.1:8000';
const OUT = 'G:/xiao6/docs/ui-system';
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
const { targetInfos } = await send('Target.getTargets');
let page = targetInfos.find(t => t.type === 'page');
if (!page) { const t = await send('Target.createTarget', { url: 'about:blank' }); page = { targetId: t.targetId }; }
const { sessionId } = await send('Target.attachToTarget', { targetId: page.targetId, flatten: true });
const S = (m, p) => send(m, p, sessionId);
await S('Page.enable');
await S('Runtime.enable');

async function evalJs(expr) {
  const r = await S('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.text + ' :: ' + expr.slice(0, 100));
  return r.result?.value;
}

await S('Emulation.setDeviceMetricsOverride', { width: 1920, height: 1080, deviceScaleFactor: 1, mobile: false });
await S('Page.navigate', { url: BASE + '/index.html' });
for (let i = 0; i < 60; i++) {
  const st = await evalJs('document.readyState').catch(() => null);
  if (st === 'complete') break;
  await sleep(200);
}
await sleep(1500);
await evalJs(`try{ localStorage.setItem('xiao6_onboarded','1'); }catch(e){} try{ var o=document.getElementById('onbOverlay'); if(o) o.remove(); }catch(e){} 'ok'`);

const THEMES = ['dark', 'quantum', 'midnight', 'dark-cyan', 'dark-green', 'dark-purple', 'dark-amber', 'dark-rose', 'light'];
const rows = [];

for (const t of THEMES) {
  await evalJs(`document.body.setAttribute('data-theme', ${JSON.stringify(t)}); 'ok'`);
  await sleep(160);
  const r = await evalJs(`(() => {
    const cs = getComputedStyle(document.body);
    const g = cs.getPropertyValue('--glow').trim();

    // 纯净类型测试：ui2.css 的典型用法（把 --glow 当颜色）
    const probe = document.createElement('div');
    probe.id = '__zz_token_probe';
    probe.style.cssText = 'position:absolute;left:-9999px;width:10px;height:10px';
    probe.style.setProperty('box-shadow', '0 6px 18px -6px var(--glow)');
    document.body.appendChild(probe);
    const asColor = getComputedStyle(probe).boxShadow;

    // styles.css 的典型用法（把 --glow 当完整阴影）
    probe.style.setProperty('box-shadow', 'var(--glow)');
    const asShadow = getComputedStyle(probe).boxShadow;
    probe.remove();

    // 真实元件抽样
    const pick = (sel, prop) => {
      const el = document.querySelector(sel);
      if (!el) return null;
      return getComputedStyle(el).getPropertyValue(prop).trim().slice(0, 90);
    };
    return {
      glowRaw: g,
      glowLooksLikeShadow: /^\\s*\\d/.test(g),
      ui2Usage_asColor: asColor,
      ui2Usage_broken: asColor === 'none' || asColor === '',
      stylesUsage_asShadow: asShadow,
      stylesUsage_broken: asShadow === 'none' || asShadow === '',
      lineStrong: cs.getPropertyValue('--line-strong').trim(),
      accent: cs.getPropertyValue('--accent').trim(),
      panelSolid: cs.getPropertyValue('--panel-solid').trim(),
      voidVar: cs.getPropertyValue('--void').trim(),
      navBrandShadow: pick('.os-nav-brand.active', 'box-shadow'),
    };
  })()`);
  rows.push({ theme: t, ...r });
}

console.log('='.repeat(118));
console.log('主题令牌实测：--glow 类型冲突影响面');
console.log('='.repeat(118));
console.log(
  'theme'.padEnd(13) + '| --glow 实际值'.padEnd(38) +
  '| ui2用法(当颜色)'.padEnd(24) + '| styles用法(当阴影)'.padEnd(24) + '| 判定'
);
console.log('-'.repeat(118));
let brokenUi2 = 0, brokenSty = 0;
for (const r of rows) {
  if (r.ui2Usage_broken) brokenUi2++;
  if (r.stylesUsage_broken) brokenSty++;
  const verdict = r.ui2Usage_broken ? '❌ ui2 辉光失效' : (r.stylesUsage_broken ? '⚠️ styles 辉光失效' : '✅ 两者均生效');
  console.log(
    r.theme.padEnd(13) + '| ' + (r.glowRaw || '(空)').slice(0, 35).padEnd(36) +
    '| ' + (r.ui2Usage_broken ? 'BROKEN' : 'ok').padEnd(22) +
    '| ' + (r.stylesUsage_broken ? 'BROKEN' : 'ok').padEnd(22) + '| ' + verdict
  );
}
console.log('-'.repeat(118));
console.log(`ui2.css 用法失效主题数: ${brokenUi2}/9    styles.css 用法失效主题数: ${brokenSty}/9`);

console.log('\n' + '='.repeat(118));
console.log('light 主题分叉实测 + 各主题关键令牌');
console.log('='.repeat(118));
console.log('theme'.padEnd(13) + '| --accent'.padEnd(12) + '| --line-strong'.padEnd(30) + '| --panel-solid'.padEnd(14) + '| --void');
for (const r of rows) {
  console.log(
    r.theme.padEnd(13) + '| ' + (r.accent || '-').padEnd(10) +
    '| ' + (r.lineStrong || '-').slice(0, 27).padEnd(28) +
    '| ' + (r.panelSolid || '-').padEnd(12) + '| ' + (r.voidVar || '-')
  );
}

console.log('\n=== .os-nav-brand.active 实际 box-shadow（ui2.css:401） ===');
for (const r of rows) console.log('  ' + r.theme.padEnd(13) + (r.navBrandShadow ?? '(元素不存在)'));

writeFileSync(OUT + '/_token_probe.json', JSON.stringify({ generatedAt: new Date().toISOString(), rows }, null, 2), 'utf-8');
console.log('\nWROTE _token_probe.json');
ws.close();
process.exit(0);
