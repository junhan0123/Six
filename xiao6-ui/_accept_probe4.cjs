/* PHASE 3.2-R Test F — real EventSource error -> exponential backoff -> recovery.
 * Block /api/stream from load so the real EventSource hits a real connection failure,
 * exercises onerror->scheduleReconnect(backoff)->reconnect->onopen->reset, then recovers. */
const { chromium } = require('playwright');
const fs = require('fs');
const EXE = 'C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1148/chrome-win/chrome.exe';
const URL = 'http://localhost:8010/xiao6-space/index.html';
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const O = { creationAbs: [], backoff: [], maxConc: 0, endOfflineDot: null, recovered: false, dotTimeline: [] };
  const browser = await chromium.launch({ executablePath: EXE, headless: true, args: ['--no-proxy-server', '--disable-gpu'] });
  const page = await browser.newPage();
  await page.addInitScript(() => {
    window.__esLog = []; window.__esCloses = [];
    const R = window.EventSource;
    function W(u, o) { const i = new R(u, o); window.__esLog.push(Date.now()); const rc = i.close.bind(i); i.close = function () { window.__esCloses.push(Date.now()); return rc(); }; return i; }
    W.prototype = R.prototype; W.CONNECTING = R.CONNECTING; W.OPEN = R.OPEN; W.CLOSED = R.CLOSED; window.EventSource = W;
  });
  await page.route('**/api/stream', r => r.abort());
  const t0 = Date.now();
  await page.goto(URL, { waitUntil: 'load', timeout: 30000 });
  for (let i = 0; i < 34; i++) {
    const dot = await page.evaluate(() => { const d = document.getElementById('rtStreamDot'); return d ? d.getAttribute('data-state') : '?'; });
    const cre = await page.evaluate(() => window.__esLog.length);
    O.dotTimeline.push({ t: Date.now() - t0, dot, creations: cre });
    await sleep(1000);
  }
  O.creationAbs = (await page.evaluate(() => window.__esLog)).map(ts => ts - t0);
  O.backoff = O.creationAbs.slice(1).map((t, i) => t - O.creationAbs[i]);
  const tl = []; (await page.evaluate(() => window.__esLog)).forEach(t => tl.push({ t, d: 1 })); (await page.evaluate(() => window.__esCloses)).forEach(t => tl.push({ t, d: -1 })); tl.sort((a, b) => a.t - b.t);
  let cur = 0, mxc = 0; for (const e of tl) { cur += e.d; if (cur > mxc) mxc = cur; }
  O.maxConc = mxc;
  O.endOfflineDot = O.dotTimeline[O.dotTimeline.length - 1].dot;
  await page.unroute('**/api/stream');
  let rec = false;
  for (let i = 0; i < 20; i++) { if (await page.evaluate(() => { const d = document.getElementById('rtStreamDot'); return d && d.getAttribute('data-state') === 'connected'; })) { rec = true; break; } await sleep(1000); }
  O.recovered = rec;
  fs.writeFileSync('G:/xiao6/xiao6-ui/_accept_probe4.json', JSON.stringify(O, null, 2));
  console.log('CREATION_ABS=' + JSON.stringify(O.creationAbs));
  console.log('BACKOFF_INTERVALS=' + JSON.stringify(O.backoff));
  console.log('MAX_CONCURRENT=' + O.maxConc + ' END_OFFLINE_DOT=' + O.endOfflineDot + ' RECOVERED=' + O.recovered);
  await browser.close();
})().catch(e => { console.error('PROBE4_FATAL', e); process.exit(2); });
