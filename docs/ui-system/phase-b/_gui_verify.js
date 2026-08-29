/* Phase B · B9 — GUI 验证（Chrome Headless + CDP）
 * 只读脚本：启动 headless Chrome，对真实渲染的 index.html 截图 + 抓取 computed style 探针。
 * 不修改任何源码。 */
'use strict';
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const BASE = 'http://127.0.0.1:8099/index.html';
const OUT = path.resolve(__dirname, 'shots');
const PORT = 9333;
fs.mkdirSync(OUT, { recursive: true });

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

async function getJSON(url) {
  const r = await fetch(url);
  return r.json();
}

class CDP {
  constructor(ws) { this.ws = ws; this.id = 0; this.pending = new Map(); this.sessions = new Set();
    ws.addEventListener('message', (ev) => {
      const m = JSON.parse(ev.data);
      if (m.id && this.pending.has(m.id)) { const { res, rej } = this.pending.get(m.id); this.pending.delete(m.id);
        m.error ? rej(new Error(JSON.stringify(m.error))) : res(m.result); }
    });
  }
  send(method, params = {}, sessionId) {
    const id = ++this.id;
    return new Promise((res, rej) => {
      this.pending.set(id, { res, rej });
      this.ws.send(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }));
      setTimeout(() => { if (this.pending.has(id)) { this.pending.delete(id); rej(new Error('timeout ' + method)); } }, 30000);
    });
  }
}

(async () => {
  const userDir = path.join(require('os').tmpdir(), 'zz-phaseb-profile');
  const chrome = spawn(CHROME, [
    '--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${userDir}`,
    '--disable-gpu', '--hide-scrollbars', '--no-first-run', '--no-default-browser-check',
    '--disable-extensions', '--force-device-scale-factor=1', 'about:blank'
  ], { stdio: 'ignore' });

  let version = null;
  for (let i = 0; i < 40; i++) { try { version = await getJSON(`http://127.0.0.1:${PORT}/json/version`); break; } catch { await sleep(250); } }
  if (!version) { console.error('CHROME LAUNCH FAILED'); chrome.kill(); process.exit(1); }
  console.log('chrome:', version['Browser']);

  const ws = new WebSocket(version.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.addEventListener('open', res); ws.addEventListener('error', rej); });
  const cdp = new CDP(ws);

  const { targetId } = await cdp.send('Target.createTarget', { url: 'about:blank' });
  const { sessionId } = await cdp.send('Target.attachToTarget', { targetId, flatten: true });
  const S = sessionId;
  await cdp.send('Page.enable', {}, S);
  await cdp.send('Runtime.enable', {}, S);

  async function go(url, w, h) {
    await cdp.send('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 1, mobile: false }, S);
    await cdp.send('Page.navigate', { url }, S);
    await sleep(2600);
  }
  async function evaluate(expr) {
    const r = await cdp.send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }, S);
    if (r.exceptionDetails) return { __error: r.exceptionDetails.text };
    return r.result.value;
  }
  async function shot(name) {
    const { data } = await cdp.send('Page.captureScreenshot', { format: 'png' }, S);
    fs.writeFileSync(path.join(OUT, name), Buffer.from(data, 'base64'));
    console.log('  shot ->', name);
  }

  const probe = {};

  // ── 01–04：四档宽度首页 ────────────────────────────────
  const widths = [[1920, 1080, '01-home-1920.png'], [1440, 900, '02-home-1440.png'],
                  [1280, 800, '03-home-1280.png'], [1024, 768, '04-home-1024.png']];
  for (const [w, h, name] of widths) {
    await go(BASE, w, h);
    await shot(name);
    probe[name] = await evaluate(`(()=>{
      const de=document.documentElement, b=document.body;
      return { canScrollX: de.scrollWidth>de.clientWidth, theme: b.getAttribute('data-theme')||'(none)',
               presence: b.getAttribute('data-presence')||'(none)',
               accent: getComputedStyle(b).getPropertyValue('--accent').trim(),
               glow: getComputedStyle(b).getPropertyValue('--glow').trim() };
    })()`);
  }

  // ── 原语 computed style 基线（在任何主题切换之前，避免残留污染）──────
  await go(BASE, 1440, 900);
  probe['primitive_computed_clean'] = await evaluate(`(()=>{
    const pick=(sel)=>{ const els=[...document.querySelectorAll(sel)]; if(!els.length) return {missing:sel};
      const el=els[0], cs=getComputedStyle(el);
      return { matched: els.length, cls: (el.className||'').toString().slice(0,60),
               theme_chain: (()=>{let n=el,c=[];while(n&&n!==document.documentElement){if(n.getAttribute&&n.getAttribute('data-theme'))c.push(n.tagName+'='+n.getAttribute('data-theme'));n=n.parentElement;}return c.join(' < ')||'(inherit body)';})(),
               backgroundImage: cs.backgroundImage.slice(0,84), backgroundColor: cs.backgroundColor,
               width: cs.width, padding: cs.padding, borderRadius: cs.borderRadius,
               backdropFilter: cs.backdropFilter, borderTop: cs.borderTopWidth+' '+cs.borderTopStyle+' '+cs.borderTopColor };
    };
    return { bodyTheme: document.body.getAttribute('data-theme'),
             '.glass-panel': pick('.glass-panel'), '.onb-card': pick('.onb-card'),
             '.onb-overlay': pick('.onb-overlay'), '.btn-new': pick('.btn-new'),
             '.zz-icon': pick('.zz-icon') };
  })()`);

  // ── 05：焦点环跨主题探针（F-B01 核心证据）────────────────
  await go(BASE, 1440, 900);
  probe['focus_ring_by_theme'] = await evaluate(`(()=>{
    const THEMES=['dark-cyan','dark-purple','dark-green','dark-amber','dark-rose','light','quantum','midnight','dark'];
    // 隔离测量：注入无类名的裸原语，排除组件自有 focus 规则干扰，直接检验 Primitive 契约
    const box=document.createElement('div');
    box.id='__phaseb_probe__';
    box.style.cssText='position:fixed;left:24px;bottom:24px;z-index:2147483647;display:flex;gap:12px;';
    box.innerHTML='<button id="__pb_btn">probe button</button><input id="__pb_inp" value="probe input"><a id="__pb_a" href="#" tabindex="0">probe link</a>';
    document.body.appendChild(box);
    const els={ button:'__pb_btn', input:'__pb_inp', a:'__pb_a' };
    const out={};
    for(const t of THEMES){
      document.body.setAttribute('data-theme',t);
      const bs=getComputedStyle(document.body);
      const rec={ accent: bs.getPropertyValue('--accent').trim(), glow: bs.getPropertyValue('--glow').trim() };
      for(const [k,id] of Object.entries(els)){
        const el=document.getElementById(id);
        el.focus();
        const cs=getComputedStyle(el);
        rec[k]={ outline: cs.outlineWidth+' '+cs.outlineStyle+' '+cs.outlineColor, boxShadow: cs.boxShadow };
      }
      out[t]=rec;
    }
    document.body.setAttribute('data-theme','dark-purple');
    document.getElementById('__pb_btn').focus();
    return out;
  })()`);
  await shot('05-focus-dark-purple-1440.png');

  // ── 06：引导卡 / 玻璃面板（F-B02/03/04 零视觉变化证据）──
  probe['primitive_computed'] = await evaluate(`(()=>{
    document.body.setAttribute('data-theme','dark-cyan');
    const pick=(sel)=>{ const el=document.querySelector(sel); if(!el) return {missing:sel};
      const cs=getComputedStyle(el);
      return { backgroundImage: cs.backgroundImage.slice(0,90), backgroundColor: cs.backgroundColor,
               width: cs.width, padding: cs.padding, borderRadius: cs.borderRadius,
               backdropFilter: cs.backdropFilter, border: cs.borderTopWidth+' '+cs.borderTopStyle+' '+cs.borderTopColor };
    };
    return { '.glass-panel': pick('.glass-panel'), '.onb-card': pick('.onb-card'),
             '.onb-overlay': pick('.onb-overlay'), '.btn-new': pick('.btn-new') };
  })()`);
  await evaluate(`(()=>{ const o=document.querySelector('.onb-overlay'); if(o){o.hidden=false;o.classList.add('show');} return 1; })()`);
  await sleep(500);
  await shot('06-onboarding-overlay-1440.png');

  fs.writeFileSync(path.join(OUT, '_probe.json'), JSON.stringify(probe, null, 2), 'utf-8');
  console.log('\n=== PROBE ===');
  console.log(JSON.stringify(probe, null, 2));

  ws.close(); chrome.kill();
  await sleep(400);
  process.exit(0);
})().catch(e => { console.error('FATAL', e); process.exit(1); });
