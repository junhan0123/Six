/* PHASE 3.2-R Test J — 15-minute real-browser stability monitor (OBSERVE-ONLY).
 * Instruments the live GUI page with non-destructive counters:
 *   - EventSource creations / max concurrent / alive (singleton + reconnect)
 *   - window addEventListener registrations per type (duplicate-listener leak detection)
 *   - console.error + window error/unhandledrejection counts
 *   - DOM node count (unbounded-growth detection)
 *   - runtime-stream data-state over time
 * No behavior is modified; only counts are recorded. */
const { chromium } = require('playwright');
const fs = require('fs');
const EXE = 'C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1148/chrome-win/chrome.exe';
const URL = 'http://localhost:8010/xiao6-space/index.html';
const DURATION = 15 * 60; // seconds
const SAMPLE = 5;         // seconds

const INSTRUMENT = () => {
  window.__tel = {
    esCreations: 0, esMaxConc: 0, esAlive: 0,
    listenerReg: {}, timerCreations: 0,
    consoleErrors: 0, pageErrors: 0,
  };
  try {
    const R = window.EventSource;
    if (R) {
      function W(u, o) {
        window.__tel.esCreations++;
        window.__tel.esAlive++;
        if (window.__tel.esAlive > window.__tel.esMaxConc) window.__tel.esMaxConc = window.__tel.esAlive;
        const i = new R(u, o);
        const rc = i.close.bind(i);
        i.close = function () { try { rc(); } catch (e) {} window.__tel.esAlive = Math.max(0, window.__tel.esAlive - 1); return undefined; };
        return i;
      }
      W.prototype = R.prototype; W.CONNECTING = R.CONNECTING; W.OPEN = R.OPEN; W.CLOSED = R.CLOSED;
      window.EventSource = W;
    }
  } catch (e) {}
  try {
    const origAdd = window.addEventListener.bind(window);
    window.addEventListener = function (type, fn, opt) {
      try { window.__tel.listenerReg[type] = (window.__tel.listenerReg[type] || 0) + 1; } catch (e) {}
      return origAdd(type, fn, opt);
    };
  } catch (e) {}
  try {
    const oST = window.setTimeout, oSI = window.setInterval;
    window.setTimeout = function () { try { window.__tel.timerCreations++; } catch (e) {} return oST.apply(window, arguments); };
    window.setInterval = function () { try { window.__tel.timerCreations++; } catch (e) {} return oSI.apply(window, arguments); };
  } catch (e) {}
  try {
    const oCE = console.error.bind(console);
    console.error = function () { try { window.__tel.consoleErrors++; } catch (e) {} return oCE.apply(console, arguments); };
  } catch (e) {}
  try {
    window.addEventListener('error', function () { try { window.__tel.pageErrors++; } catch (e) {} });
    window.addEventListener('unhandledrejection', function () { try { window.__tel.pageErrors++; } catch (e) {} });
  } catch (e) {}
};

(async () => {
  const samples = [];
  const browser = await chromium.launch({ executablePath: EXE, headless: true, args: ['--no-proxy-server', '--disable-gpu'] });
  const page = await browser.newPage();
  await page.addInitScript(INSTRUMENT);
  const t0 = Date.now();
  await page.goto(URL, { waitUntil: 'load', timeout: 30000 });
  await page.waitForTimeout(3000);
  while ((Date.now() - t0) < DURATION * 1000) {
    const snap = await page.evaluate(() => {
      const t = window.__tel || {};
      return {
        ts: Date.now(),
        esCreations: t.esCreations || 0,
        esMaxConc: t.esMaxConc || 0,
        esAlive: t.esAlive || 0,
        listenerReg: t.listenerReg || {},
        timerCreations: t.timerCreations || 0,
        consoleErrors: t.consoleErrors || 0,
        pageErrors: t.pageErrors || 0,
        domNodes: document.getElementsByTagName('*').length,
        rtStream: document.documentElement.getAttribute('data-rt-stream'),
      };
    }).catch(() => ({ ts: Date.now(), err: true }));
    samples.push(snap);
    await page.waitForTimeout(SAMPLE * 1000);
  }
  const summary = await page.evaluate(() => window.__tel || {}).catch(() => ({}));
  const out = { durationSec: DURATION, sampleSec: SAMPLE, sampleCount: samples.length, samples, summary };
  fs.writeFileSync('G:/xiao6/xiao6-ui/_accept_stability.json', JSON.stringify(out, null, 2));
  await browser.close();
  console.log('STABILITY_DONE samples=' + samples.length);
})().catch(e => { console.error('STABILITY_FATAL', e); process.exit(2); });
