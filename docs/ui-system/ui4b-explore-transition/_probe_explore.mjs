/**
 * UI-4B-2A Explore Transition Foundation —— 连续性 + 去硬切 验证探针
 * ---------------------------------------------------------------------------
 * 把"Explore State = Attention Redistribution State"从主观描述变成可测事实：
 *
 *   断言 1 · 操作层「连续退后」而非「硬隐藏」：
 *     - 默认 Operation Focus：#osShell visibility:visible / opacity≈1 / 无 blur。
 *     - Explore(zz-explore) / Universe(universe-mode)：
 *         #osShell visibility:VISIBLE（不再 visibility:hidden 硬切）
 *         #opacity ≈ --operation-opacity-explore(.35)（退后而非消失）
 *         filter 含 blur（景深退后）
 *         transitionDuration > 0（连续缓动，非突变）
 *         pointer-events:none（点击穿透到 Galaxy）
 *
 *   断言 2 · #universeView 成为「半透明空间纱」而非不透明页：
 *     - 默认：background 不透明（rgba alpha≈1，= var(--bg) 实底页基线）。
 *     - Explore / Universe：background 半透明（rgba alpha<0.95，color-mix 78%）。
 *
 *   断言 3 · World Layer 上浮：
 *     - .galaxy-veil opacity→0（连续淡出）；.solar-canvas filter brightness→1。
 *
 *   回归：window.__zzErr 长度 0；无横向溢出(scrollWidth<=innerWidth+1)。
 *
 * 前置：python -m http.server 8000（cwd=xiao6-ui/） + Chrome --remote-debugging-port=9222
 * 运行：node _probe_explore.mjs
 * 产出：_probe_explore.json + shots/explore_{default,zz,universe}.png
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

const setBody = (cls, on) => evalJs(`document.body.classList.${on ? 'add' : 'remove'}('${cls}');'ok'`);
const setUvOpen = on => evalJs(`document.getElementById('universeView').classList.${on ? 'add' : 'remove'}('open');'ok'`);
const clearStates = async () => { await setBody('zz-explore', false); await setBody('universe-mode', false); await setUvOpen(false); };

const W = 1920, H = 1080;
await S('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile: false });
await S('Page.navigate', { url: BASE + '/index.html' });
for (let i = 0; i < 80; i++) { if (await evalJs('document.readyState').catch(() => null) === 'complete') break; await sleep(200); }
await evalJs(`window.addEventListener('error',e=>{(window.__zzErr=window.__zzErr||[]).push(String(e.message))});'ok'`);
await sleep(2200);
await evalJs(`try{localStorage.setItem('xiao6_onboarded','1')}catch(e){};document.querySelectorAll('.onb-overlay,#onbOverlay').forEach(o=>o.remove());'ok'`);
await sleep(600);

/* 读取一个状态的「连续过渡事实」 */
const probeState = async (label) => {
  await sleep(1000); // 等 --attention-dur 过渡完成，取终态
  const data = await evalJs(`(()=>{
    const cs = el => getComputedStyle(el);
    const os = document.getElementById('osShell');
    const app = document.getElementById('app');
    const uv = document.getElementById('universeView');
    const veil = document.querySelector('.galaxy-veil');
    const canvas = document.querySelector('.solar-canvas');
    const num = s => parseFloat(s) || 0;
    const bgAlpha = (()=>{ const bg=cs(uv).backgroundColor;
      if(bg.includes('color(')){ const s=bg.lastIndexOf('/'); if(s<0) return 1; const a=parseFloat(bg.slice(s+1, bg.lastIndexOf(')'))); return isNaN(a)?1:a; }
      const open=bg.indexOf('('); const close=bg.lastIndexOf(')'); if(open<0) return 1;
      const parts=bg.slice(open+1,close).split(',').map(x=>parseFloat(x));
      return parts.length>=4?parts[3]:1; })();
    const transDur = cs(os).transitionDuration.split(',').map(num);
    return {
      bodyClasses: document.body.className,
      osShell: {
        visibility: cs(os).visibility,
        opacity: num(cs(os).opacity),
        filter: cs(os).filter,
        transform: cs(os).transform,
        pointerEvents: cs(os).pointerEvents,
        transitionDuration: cs(os).transitionDuration,
        transitionMaxMs: Math.max(0, ...transDur) * (cs(os).transitionDuration.includes('ms')?1:1000),
      },
      app: { visibility: cs(app).visibility, opacity: num(cs(app).opacity), pointerEvents: cs(app).pointerEvents },
      universeView: { backgroundColor: cs(uv).backgroundColor, bgAlpha, backdropFilter: cs(uv).backdropFilter, zIndex: cs(uv).zIndex },
      galaxyVeil: { opacity: num(cs(veil).opacity), transitionDuration: cs(veil).transitionDuration },
      solarCanvas: { filter: canvas ? cs(canvas).filter : null },
      errCount: (window.__zzErr||[]).length,
      scrollW: document.documentElement.scrollWidth,
      innerW: window.innerWidth,
    };
  })()`);
  // 截图证据
  await sleep(400);
  const { data: png } = await S('Page.captureScreenshot', { format: 'png' });
  writeFileSync(`${OUT_DIR}shots/explore_${label}.png`, Buffer.from(png, 'base64'));
  return data;
};

const results = { generatedAt: new Date().toISOString(), viewport: { w: W, h: H }, scenarios: {} };

// A) 默认 Operation Focus
await clearStates();
results.scenarios.default = await probeState('default');

// B) Explore World Focus（zz-explore，触发器延后到 UI-4，此处手动挂载以验证过渡语言）
await clearStates();
await setBody('zz-explore', true);
results.scenarios.explore = await probeState('zz');

// C) Universe（universe-mode + #universeView.open，= 当前 Ctrl/Cmd+U 真实路径）
await clearStates();
await setBody('universe-mode', true);
await setUvOpen(true);
results.scenarios.universe = await probeState('universe');

await clearStates();

/* ── 断言 ───────────────────────────────────────────────────────────────── */
const approx = (v, t, tol = 0.08) => Math.abs(v - t) <= tol;
const checks = [];
const chk = (name, pass, detail) => checks.push({ name, pass: !!pass, detail });

// A 默认：操作层全显、无 blur、universeView 实底页
chk('A1 默认 #osShell visible', results.scenarios.default.osShell.visibility === 'visible', results.scenarios.default.osShell.visibility);
chk('A2 默认 #osShell opacity≈1', approx(results.scenarios.default.osShell.opacity, 1, 0.02), results.scenarios.default.osShell.opacity);
chk('A3 默认 #osShell 无 blur', !/blur/.test(results.scenarios.default.osShell.filter), results.scenarios.default.osShell.filter);
chk('A4 默认无硬切：opacity=1 非隐藏', results.scenarios.default.osShell.visibility === 'visible' && approx(results.scenarios.default.osShell.opacity, 1, 0.02), 'visibility=' + results.scenarios.default.osShell.visibility + ' opacity=' + results.scenarios.default.osShell.opacity);
chk('A5 默认 #universeView 不透明实底页(alpha≈1)', approx(results.scenarios.default.universeView.bgAlpha, 1, 0.02), results.scenarios.default.universeView.bgAlpha);

// B Explore：连续退后（核心去硬切断言）
const ex = results.scenarios.explore.osShell;
chk('B1 Explore #osShell 不再 visibility:hidden（去硬切）', ex.visibility === 'visible', ex.visibility);
chk('B2 Explore #osShell opacity≈.35（退后非消失）', approx(ex.opacity, 0.35, 0.08), ex.opacity);
chk('B3 Explore #osShell 含 blur（景深退后）', /blur/.test(ex.filter), ex.filter);
chk('B4 Explore #osShell transition>0（连续缓动）', ex.transitionMaxMs > 0, ex.transitionMaxMs + 'ms');
chk('B5 Explore #osShell pointer-events:none（穿透 Galaxy）', ex.pointerEvents === 'none', ex.pointerEvents);
chk('B6 Explore #universeView 半透明纱(alpha<0.95)', results.scenarios.explore.universeView.bgAlpha < 0.95, results.scenarios.explore.universeView.bgAlpha);
chk('B7 Explore .galaxy-veil opacity→0', approx(results.scenarios.explore.galaxyVeil.opacity, 0, 0.02), results.scenarios.explore.galaxyVeil.opacity);
chk('B8 Explore .solar-canvas brightness→1（世界层上浮）', /brightness\(1\)/.test(results.scenarios.explore.solarCanvas.filter || ''), results.scenarios.explore.solarCanvas.filter);

// C Universe：与 Explore 同款去硬切（当前真实路径改善）
const un = results.scenarios.universe.osShell;
chk('C1 Universe #osShell 不再 visibility:hidden', un.visibility === 'visible', un.visibility);
chk('C2 Universe #osShell opacity≈.35', approx(un.opacity, 0.35, 0.08), un.opacity);
chk('C3 Universe #osShell 含 blur', /blur/.test(un.filter), un.filter);
chk('C4 Universe #universeView 半透明纱(alpha<0.95)', results.scenarios.universe.universeView.bgAlpha < 0.95, results.scenarios.universe.universeView.bgAlpha);
chk('C5 Universe .galaxy-veil opacity→0', approx(results.scenarios.universe.galaxyVeil.opacity, 0, 0.02), results.scenarios.universe.galaxyVeil.opacity);

// 回归
chk('R1 无 JS 运行时错误', results.scenarios.universe.errCount === 0, 'errCount=' + results.scenarios.universe.errCount);
chk('R2 无横向溢出', results.scenarios.universe.scrollW <= results.scenarios.universe.innerW + 1, results.scenarios.universe.scrollW + '≤' + results.scenarios.universe.innerW);

const passed = checks.filter(c => c.pass).length;
const failed = checks.length - passed;
results.checks = checks;
results.summary = { total: checks.length, passed, failed, allPass: failed === 0 };

writeFileSync(`${OUT_DIR}_probe_explore.json`, JSON.stringify(results, null, 2));
console.log(`[explore] ${passed}/${checks.length} checks passed. ${failed === 0 ? 'ALL_PASS' : 'HAS_FAIL'}`);
for (const c of checks) console.log(`  ${c.pass ? 'PASS' : 'FAIL'} · ${c.name} (${c.detail})`);
ws.close();
