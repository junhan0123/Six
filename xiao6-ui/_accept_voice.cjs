/* PHASE 3.2-R Test I — Voice OS orb load + channel probe (OBSERVE-ONLY).
 * Goal: determine whether a real Voice->Runtime->GUI event path can be exercised.
 * A real voice utterance requires ASR + microphone, which are unavailable in headless
 * Chromium; we instead verify (a) the orb page loads without crashing, (b) it exposes
 * its runtime API, and (c) whether it shares the Runtime /api/stream channel. */
const { chromium } = require('playwright');
const fs = require('fs');
const EXE = 'C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1148/chrome-win/chrome.exe';
const URL = 'http://localhost:8010/desktop-avatar/dyna-orb.html';
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const O = { loaded: false, httpStatus: null, pageErrors: 0, consoleErrors: 0, hasZZDynaOrb: false, orbApi: null, orbStreamCreations: 0, speechRecAvailable: null, notes: [] };
  const browser = await chromium.launch({ executablePath: EXE, headless: true, args: ['--no-proxy-server', '--disable-gpu', '--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream'] });
  const page = await browser.newPage();
  await page.addInitScript(() => {
    window.__v = { esCreations: 0, speechRec: (typeof window.SpeechRecognition !== 'undefined' || typeof window.webkitSpeechRecognition !== 'undefined') };
    try { const R = window.EventSource; if (R) { function W(u, o) { window.__v.esCreations++; return new R(u, o); } W.prototype = R.prototype; window.EventSource = W; } } catch (e) {}
  });
  page.on('pageerror', () => { O.pageErrors++; });
  page.on('console', m => { if (m.type() === 'error') O.consoleErrors++; });
  try {
    const resp = await page.goto(URL, { waitUntil: 'load', timeout: 20000 });
    O.httpStatus = resp ? resp.status() : null;
    O.loaded = true;
  } catch (e) { O.notes.push('goto failed: ' + String(e)); }
  await sleep(8000);
  try {
    const info = await page.evaluate(() => ({
      hasZZDynaOrb: typeof window.ZZDynaOrb !== 'undefined',
      orbApi: (typeof window.ZZDynaOrb !== 'undefined' && window.ZZDynaOrb) ? Object.keys(window.ZZDynaOrb) : null,
      speechRec: window.__v ? window.__v.speechRec : null,
      esCreations: window.__v ? window.__v.esCreations : null,
      title: document.title,
    }));
    O.hasZZDynaOrb = info.hasZZDynaOrb; O.orbApi = info.orbApi; O.speechRecAvailable = info.speechRec; O.orbStreamCreations = info.esCreations;
  } catch (e) { O.notes.push('evaluate failed: ' + String(e)); }
  O.notes.push('No microphone/ASR in headless Chromium -> a real voice utterance cannot be driven. Voice->Runtime->GUI data flow cannot be exercised end-to-end here.');
  fs.writeFileSync('G:/xiao6/xiao6-ui/_accept_voice.json', JSON.stringify(O, null, 2));
  console.log('VOICE_LOADED=' + O.loaded + ' HTTP=' + O.httpStatus + ' ZZDynaOrb=' + O.hasZZDynaOrb + ' SPEECH_REC=' + O.speechRecAvailable + ' ORB_ES=' + O.orbStreamCreations + ' PAGEERR=' + O.pageErrors + ' CONSOLEERR=' + O.consoleErrors);
  await browser.close();
})().catch(e => { console.error('VOICE_FATAL', e); process.exit(2); });
