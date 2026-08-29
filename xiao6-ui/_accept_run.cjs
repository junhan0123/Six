/* PHASE 3.2-R — REAL BROWSER ACCEPTANCE (VERIFY ONLY)
 * Drives a REAL headless Chromium (Playwright). No DOM shim, no mock EventSource/fetch/SSE.
 * Instruments the browser at runtime ONLY to OBSERVE (constructor counter + message logger);
 * the real EventSource/fetch/SSE behavior is preserved. Does NOT modify any production file.
 */
const { chromium } = require('playwright');
const fs = require('fs');

const EXE = 'C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1148/chrome-win/chrome.exe';
const URL = 'http://localhost:8010/xiao6-space/index.html';
const EVID_PATH = 'G:/xiao6/xiao6-ui/_accept_evidence.json';

const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const EVID = { meta: {}, tests: {}, network: { stream: [], agentState: [], chat: [], speak: [] }, console: [], pageErrors: [], esLog: [], esMessages: [], esCloses: [] };
  EVID.meta.startedAt = new Date().toISOString();

  const browser = await chromium.launch({ executablePath: EXE, headless: true, args: ['--no-proxy-server', '--disable-gpu'] });
  const page = await browser.newPage();
  await page.setViewportSize({ width: 1280, height: 900 });

  // ---- runtime instrumentation (OBSERVE ONLY) ----
  await page.addInitScript(() => {
    window.__esLog = []; window.__esMessages = []; window.__esCloses = [];
    const RealES = window.EventSource;
    function WrappedEventSource(url, opts) {
      const inst = new RealES(url, opts);
      const ts = Date.now();
      window.__esLog.push({ url, ts, stack: (new Error()).stack });
      inst.addEventListener('message', e => { try { window.__esMessages.push({ url, ts: Date.now(), data: e.data }); } catch (_) {} });
      const realClose = inst.close.bind(inst);
      inst.close = function () { window.__esCloses.push(Date.now()); return realClose(); };
      return inst;
    }
    WrappedEventSource.prototype = RealES.prototype;
    WrappedEventSource.CONNECTING = RealES.CONNECTING;
    WrappedEventSource.OPEN = RealES.OPEN;
    WrappedEventSource.CLOSED = RealES.CLOSED;
    window.EventSource = WrappedEventSource;
  });

  page.on('console', m => { const t = m.type(); const x = m.text(); EVID.console.push({ t, x: x.slice(0, 300) }); });
  page.on('pageerror', e => EVID.pageErrors.push(String(e).slice(0, 400)));
  const track = (kind, r) => {
    const u = r.url();
    if (u.endsWith('/api/stream')) EVID.network.stream.push({ ts: Date.now(), method: r.method() });
    else if (u.endsWith('/api/agent/state')) EVID.network.agentState.push({ ts: Date.now() });
    else if (u.includes('/api/chat')) EVID.network.chat.push({ ts: Date.now(), method: r.method() });
    else if (u.includes('/api/speak')) EVID.network.speak.push({ ts: Date.now() });
  };
  page.on('request', r => track('req', r));

  const dotState = () => page.evaluate(() => { const d = document.getElementById('rtStreamDot'); return d ? d.getAttribute('data-state') : 'NO_DOT'; });
  const rtText = () => page.evaluate(() => { const b = document.querySelector('#runtimeState b'); return b ? b.textContent : 'NO_RT'; });
  const overlayOpen = () => page.evaluate(() => { const o = document.getElementById('overlay'); return o && o.getAttribute('aria-hidden') === 'false'; });
  const overlayInfo = () => page.evaluate(() => {
    const o = document.getElementById('overlay');
    if (!o || o.getAttribute('aria-hidden') !== 'false') return null;
    const title = (document.getElementById('overlayTitle') || {}).textContent || '';
    const body = (document.getElementById('overlayBody') || {}).innerHTML || '';
    const forbidden = /three\.min|lottie|galaxy/i.test(body);
    const secondModal = document.querySelectorAll('[role="dialog"]').length > 1;
    return { title, bodyLen: body.length, forbiddenWord: forbidden, secondModal };
  });
  const closeOverlay = () => page.keyboard.press('Escape').catch(() => {});
  const nodeCount = () => page.evaluate(() => document.getElementsByTagName('*').length);

  const sendChat = async (text) => {
    // ensure conversation view is active (cmdInput lives there)
    await page.evaluate(() => {
      if (document.body.dataset.view !== 'conversation') {
        const btn = document.querySelector('.zz-nav-btn[data-nav="conversation"]');
        if (btn) btn.click(); else { const o = document.getElementById('orbBtn'); if (o) o.click(); }
      }
    });
    await page.waitForSelector('#cmdInput:visible', { timeout: 10000 });
    await page.fill('#cmdInput', text);
    await page.press('#cmdInput', 'Enter');
  };

  // ================= TEST A — EventSource connect =================
  EVID.tests.A = { steps: [] };
  await page.goto(URL, { waitUntil: 'load', timeout: 30000 });
  // sample dot transitions
  const dotSamples = [];
  for (let i = 0; i < 14; i++) { dotSamples.push(await dotState()); await sleep(500); }
  EVID.tests.A.dotSamples = dotSamples;
  EVID.tests.A.finalDot = await dotState();
  EVID.tests.A.esCreations = (await page.evaluate(() => window.__esLog.length));
  EVID.tests.A.streamRequests = EVID.network.stream.length;
  // compute max concurrent EventSource
  const timeline = [];
  (await page.evaluate(() => window.__esLog)).forEach(e => timeline.push({ t: e.ts, d: 1 }));
  (await page.evaluate(() => window.__esCloses)).forEach(t => timeline.push({ t, d: -1 }));
  timeline.sort((a, b) => a.t - b.t);
  let cur = 0, maxc = 0;
  for (const e of timeline) { cur += e.d; if (cur > maxc) maxc = cur; }
  EVID.tests.A.maxConcurrentES = maxc;
  EVID.tests.A.pass = (EVID.tests.A.finalDot === 'connected' && EVID.tests.A.esCreations === 1 && EVID.tests.A.streamRequests >= 1 && maxc <= 1);

  // ================= TEST B / C — agent_state / hud_state on /api/stream =================
  EVID.tests.B = { agentStateSeen: [], guiUpdatedWithin1s: null };
  EVID.tests.C = { hudStateSeen: [] };
  // baseline
  const beforeText = await rtText();
  const bStart = Date.now();
  await sendChat('你好小6，请做个简单的自我介绍。');
  // monitor esMessages for agent_state/hud_state for ~12s
  let guiChangedAt = null;
  for (let i = 0; i < 24; i++) {
    const msgs = await page.evaluate(() => window.__esMessages.map(m => ({ ts: m.ts, data: m.data })));
    for (const m of msgs) {
      let p; try { p = JSON.parse(m.data); } catch (_) { continue; }
      const ev = p.xiao6_event || p.event;
      if (ev === 'agent_state') { EVID.tests.B.agentStateSeen.push({ ts: m.ts, state: (p.payload && p.payload.state) || (p.state) }); }
      if (ev === 'hud_state') { EVID.tests.C.hudStateSeen.push({ ts: m.ts, state: (p.payload && p.payload.state) || p.state }); }
    }
    const nowText = await rtText();
    if (guiChangedAt === null && nowText !== beforeText && EVID.tests.B.agentStateSeen.length) guiChangedAt = Date.now() - bStart;
    await sleep(500);
  }
  EVID.tests.B.guiUpdatedWithin1s = (guiChangedAt !== null && guiChangedAt <= 1000);
  EVID.tests.B.pass = EVID.tests.B.agentStateSeen.length > 0; // real-time observed if event arrived
  EVID.tests.C.pass = EVID.tests.C.hudStateSeen.length > 0;
  await closeOverlay(); await sleep(400);

  // ================= TEST D — Panel/Modal/Scene via chat SSE =================
  EVID.tests.D = { attempts: [], pass: true };
  const dPrompts = [
    { tag: 'modal-weather', text: '北京今天天气怎么样？' },
    { tag: 'modal-hotspots', text: '今天有什么热点新闻？' },
    { tag: 'panel-video', text: '播放一个关于太空的短片' },
    { tag: 'panel-map', text: '帮我查一下上海的地图' },
    { tag: 'panel-memory', text: '打开记忆审计面板' },
    { tag: 'panel-review', text: '帮我审视这段话：小6真棒' }
  ];
  for (const p of dPrompts) {
    const rec = { tag: p.tag, text: p.text };
    await sendChat(p.text);
    let info = null;
    try { await page.waitForFunction(() => { const o = document.getElementById('overlay'); return o && o.getAttribute('aria-hidden') === 'false'; }, { timeout: 20000 }); info = await overlayInfo(); }
    catch (_) { info = await overlayInfo(); }
    rec.overlay = info;
    rec.speakDuring = (await page.evaluate(() => window.__esLog)) && EVID.network.speak.length; // speak count so far
    EVID.tests.D.attempts.push(rec);
    if (info) {
      if (info.forbiddenWord) EVID.tests.D.pass = false;
      if (info.secondModal) EVID.tests.D.pass = false;
    }
    await closeOverlay(); await sleep(600);
  }
  EVID.tests.D.speakCountTotal = EVID.network.speak.length;

  // ================= TEST E — Duplicate guard (tool/INTENT on /api/stream) =================
  EVID.tests.E = { sawChatDomainOnStream: [], toolNodesBefore: null, toolNodesAfter: null, pass: true };
  EVID.tests.E.toolNodesBefore = await page.evaluate(() => document.querySelectorAll('.zz-tool-node, [data-toolnode]').length);
  await sendChat('帮我查一下今天北京天气，并看看有什么热点话题。');
  for (let i = 0; i < 24; i++) {
    const msgs = await page.evaluate(() => window.__esMessages.map(m => m.data));
    for (const d of msgs) {
      let p; try { p = JSON.parse(d); } catch (_) { continue; }
      const ev = p.xiao6_event || p.event;
      if (['tool_started', 'tool_finished', 'execution_started', 'execution_completed', 'MEMORY_RETRIEVED', 'CONTEXT_BUILT', 'INTENT_RECEIVED', 'INTENT_ANALYZING', 'INTENT_CLASSIFIED', 'INTENT_REJECTED', 'tool_start', 'tool_end', 'panel', 'modal', 'scene'].includes(ev)) {
        if (!EVID.tests.E.sawChatDomainOnStream.includes(ev)) EVID.tests.E.sawChatDomainOnStream.push(ev);
      }
    }
    await sleep(500);
  }
  EVID.tests.E.toolNodesAfter = await page.evaluate(() => document.querySelectorAll('.zz-tool-node, [data-toolnode]').length);
  EVID.tests.E.pass = (EVID.tests.E.sawChatDomainOnStream.length > 0 && EVID.pageErrors.length === 0 && EVID.tests.E.toolNodesAfter <= EVID.tests.E.toolNodesBefore + 0); // no duplicate tool nodes
  await closeOverlay(); await sleep(400);

  // ================= TEST F — Reconnect / backoff =================
  EVID.tests.F = { blockSamples: [], backoffIntervals: [], maxConcurrentDuringBlock: 0, recovered: false, errorStorm: false };
  await page.route('**/api/stream', r => r.abort());
  const fStart = Date.now();
  let fPrevCreations = (await page.evaluate(() => window.__esLog.length));
  const creationTs = [(await page.evaluate(() => window.__esLog)).map(e => e.ts)];
  for (let i = 0; i < 30; i++) {
    const ds = await dotState();
    const cre = await page.evaluate(() => window.__esLog.length);
    EVID.tests.F.blockSamples.push({ t: Date.now() - fStart, dot: ds, esCreations: cre });
    await sleep(1000);
  }
  // compute backoff intervals from creation timestamps during block
  const allCre = await page.evaluate(() => window.__esLog.map(e => e.ts));
  const blockCre = allCre.slice(fPrevCreations);
  EVID.tests.F.backoffIntervals = blockCre.slice(1).map((t, i) => t - blockCre[i]);
  // max concurrent during block
  const tl2 = [];
  (await page.evaluate(() => window.__esLog)).forEach(e => tl2.push({ t: e.ts, d: 1 }));
  (await page.evaluate(() => window.__esCloses)).forEach(t => tl2.push({ t, d: -1 }));
  tl2.sort((a, b) => a.t - b.t);
  let c2 = 0, m2 = 0; for (const e of tl2) { c2 += e.d; if (c2 > m2) m2 = c2; }
  EVID.tests.F.maxConcurrentDuringBlock = m2;
  EVID.tests.F.errorStorm = EVID.console.filter(c => c.t === 'error').length > 20;
  // restore
  await page.unroute('**/api/stream');
  let recovered = false;
  for (let i = 0; i < 20; i++) { if (await dotState() === 'connected') { recovered = true; break; } await sleep(1000); }
  EVID.tests.F.recovered = recovered;
  EVID.tests.F.pass = (EVID.tests.F.maxConcurrentDuringBlock <= 1 && recovered && !EVID.tests.F.errorStorm);

  // ================= TEST G — Page visibility guard =================
  EVID.tests.G = { hiddenTextDuring: null, textAfterRestore: null, changedWhileHidden: false, caughtUpAfter: false };
  await page.evaluate(() => {
    Object.defineProperty(document, 'hidden', { configurable: true, get: () => true });
    Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'hidden' });
    document.dispatchEvent(new Event('visibilitychange'));
  });
  const gBefore = await rtText();
  await sendChat('现在帮我记一件事：明天上午十点开会。');
  await sleep(6000);
  const gDuring = await rtText();
  EVID.tests.G.changedWhileHidden = (gDuring !== gBefore);
  EVID.tests.G.hiddenTextDuring = gDuring;
  await page.evaluate(() => {
    Object.defineProperty(document, 'hidden', { configurable: true, get: () => false });
    Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'visible' });
    document.dispatchEvent(new Event('visibilitychange'));
  });
  await sleep(9000); // allow poll/event to catch up
  const gAfter = await rtText();
  EVID.tests.G.textAfterRestore = gAfter;
  EVID.tests.G.caughtUpAfter = (gAfter !== gDuring) || (gAfter === gBefore);
  EVID.tests.G.pass = (!EVID.tests.G.changedWhileHidden); // guard held while hidden
  await closeOverlay(); await sleep(400);

  // ================= TEST H — Reconciliation (8s polling) =================
  EVID.tests.H = { intervals: [], pass: true };
  const polls = (await page.evaluate(() => window.__EVID_POLLS || null));
  // recompute from captured network agentState timestamps
  const aTs = EVID.network.agentState.map(x => x.ts).sort((a, b) => a - b);
  const intervals = [];
  for (let i = 1; i < aTs.length; i++) intervals.push(aTs[i] - aTs[i - 1]);
  EVID.tests.H.intervals = intervals;
  EVID.tests.H.pollCount = aTs.length;
  EVID.tests.H.pass = intervals.filter(iv => iv >= 6000 && iv <= 11000).length >= 1 && EVID.tests.A.maxConcurrentES <= 1;

  EVID.meta.endedAt = new Date().toISOString();
  EVID.meta.finalDot = await dotState();
  EVID.meta.domNodes = await nodeCount();
  EVID.meta.esCreationsTotal = await page.evaluate(() => window.__esLog.length);

  fs.writeFileSync(EVID_PATH, JSON.stringify(EVID, null, 2));
  console.log('ACCEPT_EVIDENCE_WRITTEN=' + EVID_PATH);
  console.log('A.pass=' + EVID.tests.A.pass + ' dot=' + EVID.tests.A.finalDot + ' esCreations=' + EVID.tests.A.esCreations + ' maxConcurrent=' + EVID.tests.A.maxConcurrentES);
  console.log('B.agentStateSeen=' + EVID.tests.B.agentStateSeen.length + ' C.hudSeen=' + EVID.tests.C.hudStateSeen.length);
  console.log('D.pass=' + EVID.tests.D.pass + ' attempts=' + EVID.tests.D.attempts.length + ' speakTotal=' + EVID.tests.D.speakCountTotal);
  console.log('E.sawChatDomain=' + JSON.stringify(EVID.tests.E.sawChatDomainOnStream) + ' toolBefore=' + EVID.tests.E.toolNodesBefore + ' toolAfter=' + EVID.tests.E.toolNodesAfter);
  console.log('F.pass=' + EVID.tests.F.pass + ' recovered=' + EVID.tests.F.recovered + ' maxConcBlock=' + EVID.tests.F.maxConcurrentDuringBlock + ' backoff=' + JSON.stringify(EVID.tests.F.backoffIntervals));
  console.log('G.pass=' + EVID.tests.G.pass + ' changedWhileHidden=' + EVID.tests.G.changedWhileHidden + ' caughtUp=' + EVID.tests.G.caughtUpAfter);
  console.log('H.pass=' + EVID.tests.H.pass + ' pollCount=' + EVID.tests.H.pollCount + ' intervals=' + JSON.stringify(EVID.tests.H.intervals.slice(0, 6)));
  console.log('pageErrors=' + EVID.pageErrors.length + ' consoleErrors=' + EVID.console.filter(c => c.t === 'error').length);
  await browser.close();
})().catch(e => { console.error('ACCEPT_FATAL', e); process.exit(2); });
