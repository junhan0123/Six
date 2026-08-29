const { chromium } = require('playwright');
const fs = require('fs');
const DIR = 'G:/xiao6/_ui_archive';
const BASE = 'http://127.0.0.1:8010';
const URL = BASE + '/xiao6-space/index.html';
const EXE = 'C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1208/chrome-win64/chrome.exe';

function measureEl(page, sel) {
  return page.evaluate((s) => {
    const el = document.querySelector(s);
    if (!el) return { sel: s, found: false };
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    return {
      sel: s, found: true,
      rect: { x: Math.round(r.x*100)/100, y: Math.round(r.y*100)/100, w: Math.round(r.width*100)/100, h: Math.round(r.height*100)/100 },
      computed: {
        width: cs.width, height: cs.height,
        borderRadius: cs.borderRadius,
        boxSizing: cs.boxSizing,
        position: cs.position, display: cs.display,
        aspectRatio: cs.aspectRatio,
        transform: cs.transform,
        paddingTop: cs.paddingTop, paddingLeft: cs.paddingLeft,
        borderTopWidth: cs.borderTopWidth, borderLeftWidth: cs.borderLeftWidth,
        marginTop: cs.marginTop, marginLeft: cs.marginLeft,
        alignSelf: cs.alignSelf, justifySelf: cs.justifySelf,
        offsetParent: el.offsetParent ? (el.offsetParent.id || el.offsetParent.className || el.offsetParent.tagName) : null
      }
    };
  }, sel);
}

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: EXE, args: ['--no-sandbox', '--disable-gpu'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 800, deviceScaleFactor: 2 } });
  const fails = [];
  page.on('response', r => { if (r.status() >= 400) fails.push(r.status() + ' ' + r.url()); });
  await page.goto(URL, { waitUntil: 'load', timeout: 30000 });
  await page.waitForSelector('#orbPresence', { timeout: 10000 });
  await page.waitForTimeout(1500);

  const sels = ['#orbPresence', '.zz-orb-presence .zz-orb-core', '.zz-orb-ring', '.zz-orb-core', '.zz-core-disc', '#voiceOrb'];
  const out = { url: URL, states: {} };

  const states = ['idle', 'listening', 'speaking', 'thinking'];
  for (const st of states) {
    await page.evaluate((s) => { const o = document.getElementById('orbPresence'); if (o) o.dataset.state = s; }, st);
    await page.waitForTimeout(400);
    const meas = {};
    for (const s of sels) {
      const m = await measureEl(page, s);
      if (m.found) meas[s] = m;
    }
    out.states[st] = meas;
  }

  // idle screenshot of orb region (tight clip, 2x DPR)
  await page.evaluate(() => { const o = document.getElementById('orbPresence'); if (o) o.dataset.state = 'idle'; });
  await page.waitForTimeout(400);
  const orb = await page.$('#orbPresence');
  if (orb) {
    const box = await orb.boundingBox();
    const pad = 24;
    await page.screenshot({
      path: DIR + '/VOICE-ORB-BEFORE.png',
      clip: { x: Math.max(0, box.x - pad), y: Math.max(0, box.y - pad), width: box.width + pad*2, height: box.height + pad*2 }
    });
    out.orbBox = box;
  }
  // also full page for context
  await page.screenshot({ path: DIR + '/VOICE-ORB-BEFORE-FULL.png', fullPage: false });

  out.fails = fails.slice(0, 20);
  fs.writeFileSync(DIR + '/orb_measure.json', JSON.stringify(out, null, 2));
  console.log('MEASURE_DONE states=' + states.join(','));
  await browser.close();
  process.exit(0);
})().catch(e => { fs.writeFileSync(DIR + '/orb_measure_err.txt', String(e && e.stack || e)); process.exit(2); });
