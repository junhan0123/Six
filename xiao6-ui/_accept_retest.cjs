/* PHASE 3.2-R re-test: F (real offline reconnect/backoff), B/C (real agent goal -> agent_state/hud_state), D secondModal check */
const { chromium } = require('playwright');
const fs = require('fs');
const EXE = 'C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1148/chrome-win/chrome.exe';
const URL = 'http://localhost:8010/xiao6-space/index.html';
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const O = { badResponses: [], consoleErr: [], agentState: [], hudState: [], rtChanges: [], dialogsWhenOverlayOpen: null, F: {} };
  const browser = await chromium.launch({ executablePath: EXE, headless: true, args: ['--no-proxy-server', '--disable-gpu'] });
  const page = await browser.newPage();
  await page.addInitScript(() => {
    window.__stream = []; window.__esLog = []; window.__esCloses = [];
    const R = window.EventSource;
    function W(u, o) { const i = new R(u, o); window.__esLog.push(Date.now()); i.addEventListener('message', e => { try { window.__stream.push({ ts: Date.now(), data: e.data }); } catch (_) {} }); const rc = i.close.bind(i); i.close = function () { window.__esCloses.push(Date.now()); return rc(); }; return i; }
    W.prototype = R.prototype; W.CONNECTING = R.CONNECTING; W.OPEN = R.OPEN; W.CLOSED = R.CLOSED; window.EventSource = W;
  });
  page.on('response', r => { if (r.status() >= 400) O.badResponses.push({ status: r.status(), url: r.url() }); });
  page.on('console', m => { if (m.type() === 'error') O.consoleErr.push(m.text().slice(0, 200)); });
  page.on('pageerror', e => O.consoleErr.push('PAGEERROR: ' + String(e).slice(0, 200)));

  await page.goto(URL, { waitUntil: 'load', timeout: 30000 });
  await page.waitForSelector('#rtStreamDot[data-state="connected"]', { timeout: 15000 }).catch(() => {});

  const rtText = () => page.evaluate(() => { const b = document.querySelector('#runtimeState b'); return b ? b.textContent : '?'; });
  const parseEv = d => { let p; try { p = JSON.parse(d); } catch (_) { return null; } return p.xiao6_event || p.event || null; };

  // ===== B/C: real agent goal -> agent_state/hud_state on /api/stream =====
  const beforeGoal = await rtText();
  const submit = await page.evaluate(async () => {
    try { const r = await fetch('/api/agent/goal', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title: '验收测试目标', description: '请只回复收到' }) }); const j = await r.json().catch(() => ({})); return { status: r.status, body: j }; } catch (e) { return { error: String(e) }; }
  });
  O.goalSubmit = submit;
  const gStart = Date.now();
  let firstAgentTs = null, firstGuiTs = null, lastText = beforeGoal;
  for (let i = 0; i < 40; i++) {
    const msgs = await page.evaluate(() => window.__stream.map(m => m.data));
    for (const d of msgs) {
      const ev = parseEv(d);
      if (ev === 'agent_state') { const t = Date.now() - gStart; if (firstAgentTs === null) firstAgentTs = t; try { const p = JSON.parse(d); O.agentState.push({ ts: t, state: (p.payload && p.payload.state) || p.state }); } catch (_) {} }
      if (ev === 'hud_state') { const t = Date.now() - gStart; try { const p = JSON.parse(d); O.hudState.push({ ts: t, state: (p.payload && p.payload.state) || p.state }); } catch (_) {} }
    }
    const t = await rtText();
    if (t !== lastText) { O.rtChanges.push({ ts: Date.now() - gStart, from: lastText, to: t }); lastText = t; if (firstGuiTs === null && firstAgentTs !== null) firstGuiTs = Date.now() - gStart; }
    await sleep(400);
  }
  O.bFirstAgentArrivalMs = firstAgentTs;
  O.bGuiUpdateMs = firstGuiTs;
  O.bGuiWithin1s = (firstAgentTs !== null && firstGuiTs !== null) ? (firstGuiTs - firstAgentTs <= 1000) : null;

  // ===== D secondModal check: open a modal via real chat, count [role=dialog] =====
  await page.evaluate(() => { const b = document.querySelector('.zz-nav-btn[data-nav="conversation"]'); if (b) b.click(); else { const o = document.getElementById('orbBtn'); if (o) o.click(); } });
  await page.waitForSelector('#cmdInput:visible', { timeout: 10000 }).catch(() => {});
  await page.fill('#cmdInput', '今天有什么热点新闻？');
  await page.press('#cmdInput', 'Enter');
  let opened = false;
  for (let i = 0; i < 40; i++) { const v = await page.evaluate(() => { const o = document.getElementById('overlay'); return o && o.getAttribute('aria-hidden') === 'false'; }); if (v) { opened = true; break; } await sleep(500); }
  if (opened) {
    O.dialogsWhenOverlayOpen = await page.evaluate(() => {
      const els = Array.from(document.querySelectorAll('[role="dialog"]'));
      return { count: els.length, ids: els.map(e => e.id || (e.className || '').toString().slice(0, 30)), overlayCount: document.querySelectorAll('#overlay').length };
    });
  }
  await page.keyboard.press('Escape').catch(() => {});

  // ===== F: REAL offline -> reconnect/backoff =====
  const fStart = Date.now();
  const creBefore = await page.evaluate(() => window.__esLog.length);
  const cloBefore = await page.evaluate(() => window.__esCloses.length);
  await page.context().setOffline(true);
  const fSamples = [];
  for (let i = 0; i < 30; i++) {
    const dot = await page.evaluate(() => { const d = document.getElementById('rtStreamDot'); return d ? d.getAttribute('data-state') : '?'; });
    const cre = await page.evaluate(() => window.__esLog.length);
    const clo = await page.evaluate(() => window.__esCloses.length);
    fSamples.push({ t: Date.now() - fStart, dot, esCreations: cre, esCloses: clo });
    await sleep(1000);
  }
  const creAfter = await page.evaluate(() => window.__esLog.length);
  const cloAfter = await page.evaluate(() => window.__esCloses.length);
  const blockCreations = (await page.evaluate(() => window.__esLog)).slice(creBefore).map(ts => ts);
  // backoff = deltas between creation timestamps during block
  const backoff = blockCreations.slice(1).map((t, i) => t - blockCreations[i]);
  // max concurrent during block
  const tl = [];
  (await page.evaluate(() => window.__esLog)).forEach(t => tl.push({ t, d: 1 }));
  (await page.evaluate(() => window.__esCloses)).forEach(t => tl.push({ t, d: -1 }));
  tl.sort((a, b) => a.t - b.t);
  let cur = 0, mxc = 0; for (const e of tl) { cur += e.d; if (cur > mxc) mxc = cur; }
  // restore
  await page.context().setOffline(false);
  let recovered = false;
  for (let i = 0; i < 20; i++) { if (await page.evaluate(() => { const d = document.getElementById('rtStreamDot'); return d && d.getAttribute('data-state') === 'connected'; })) { recovered = true; break; } await sleep(1000); }
  O.F = { blockSamples: fSamples, blockCreations: blockCreations.length, backoffIntervals: backoff, maxConcurrentDuringBlock: mxc, recovered, dotBeforeOffline: fSamples[0] && fSamples[0].dot, dotEndOffline: fSamples[fSamples.length - 1] && fSamples[fSamples.length - 1].dot };

  fs.writeFileSync('G:/xiao6/xiao6-ui/_accept_retest.json', JSON.stringify(O, null, 2));
  console.log('GOAL_SUBMIT=' + JSON.stringify(O.goalSubmit));
  console.log('AGENT_STATE_COUNT=' + O.agentState.length + ' firstArrivalMs=' + O.bFirstAgentArrivalMs + ' guiUpdateMs=' + O.bGuiUpdateMs + ' within1s=' + O.bGuiWithin1s);
  console.log('AGENT_STATE=' + JSON.stringify(O.agentState.slice(0, 6)));
  console.log('HUD_STATE_COUNT=' + O.hudState.length + ' ' + JSON.stringify(O.hudState.slice(0, 6)));
  console.log('RT_CHANGES=' + JSON.stringify(O.rtChanges.slice(0, 6)));
  console.log('DIALOGS_WHEN_OVERLAY_OPEN=' + JSON.stringify(O.dialogsWhenOverlayOpen));
  console.log('F_backoff=' + JSON.stringify(O.F.backoffIntervals) + ' maxConc=' + O.F.maxConcurrentDuringBlock + ' recovered=' + O.F.recovered + ' endOfflineDot=' + O.F.dotEndOffline);
  console.log('BAD_RESPONSES=' + JSON.stringify([...new Set(O.badResponses.map(b => b.status + ' ' + b.url))].slice(0, 10)));
  console.log('CONSOLE_ERR_COUNT=' + O.consoleErr.length);
  await browser.close();
})().catch(e => { console.error('RETEST_FATAL', e); process.exit(2); });
