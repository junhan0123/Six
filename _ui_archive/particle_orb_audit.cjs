// PHASE 5.1-HOTFIX-UI-02 — Desktop Particle Voice Orb real Chromium audit
// Renders the REAL served orb (http://127.0.0.1:8010/desktop-avatar/dyna-orb.html)
// at the real Electron window dims (213x320) + multiple DPR + a square viewport,
// measures canvas backing geometry + pixel bounding box of the particle cloud,
// and captures screenshots per state. NO code change; measurement only.
const { chromium } = require('playwright');

const TARGET = 'http://127.0.0.1:8010/desktop-avatar/dyna-orb.html';
const EXEC = 'C:\\Users\\Administrator\\AppData\\Local\\ms-playwright\\chromium-1208\\chrome-win64\\chrome.exe';
const OUT = 'G:\\xiao6\\_ui_archive';

const STATES = ['idle', 'listening', 'thinking', 'speaking', 'executing'];
const REAL_W = 213, REAL_H = 320;

async function measureInPage(page) {
  return await page.evaluate(() => {
    const c = document.getElementById('orb-canvas');
    if (!c) return { err: 'no canvas' };
    const ctx = c.getContext('2d');
    const w = c.width, h = c.height;
    const dpr = window.devicePixelRatio || 1;
    let img = null;
    try { img = ctx.getImageData(0, 0, w, h).data; } catch (e) { return { err: 'getImageData failed: ' + e.message, w, h, dpr }; }
    // alpha-thresholded particle bounding box
    const TH = 14;
    let minX = w, minY = h, maxX = -1, maxY = -1, cnt = 0;
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const a = img[(y * w + x) * 4 + 3];
        if (a > TH) {
          if (x < minX) minX = x; if (x > maxX) maxX = x;
          if (y < minY) minY = y; if (y > maxY) maxY = y;
          cnt++;
        }
      }
    }
    const bbW = maxX - minX + 1, bbH = maxY - minY + 1;
    const ratio = (bbW > 0 && bbH > 0) ? bbW / bbH : null;
    return {
      backingW: w, backingH: h, dpr,
      cssW: Math.round(w / dpr), cssH: Math.round(h / dpr),
      cx: Math.round(w / 2), cy: Math.round(h / 2),
      scale: Math.round(Math.min(w, h) * 0.40),
      particleCount: cnt,
      bbMinX: minX, bbMinY: minY, bbMaxX: maxX, bbMaxY: maxY,
      bbW, bbH,
      absDiff: (bbW >= 0 && bbH >= 0) ? Math.abs(bbW - bbH) : null,
      ratio,
      hasZZDynaOrb: typeof window.ZZDynaOrb !== 'undefined',
    };
  });
}

async function run() {
  const results = { target: TARGET, cases: [] };
  const browser = await chromium.launch({
    executablePath: EXEC,
    args: ['--no-sandbox', '--disable-gpu', '--use-gl=swiftshader', '--enable-unsafe-swiftshader'],
  });

  // Case 1: real window dims 213x320, dpr 1/2/3
  for (const dpr of [1, 2, 3]) {
    const ctx = await browser.newContext({
      viewport: { width: REAL_W, height: REAL_H },
      deviceScaleFactor: dpr,
      // transparent so the orb frame is visible like the real desktop window
      hasTouch: false,
    });
    const page = await ctx.newPage();
    await page.goto(TARGET, { waitUntil: 'load', timeout: 30000 });
    // wait for orb API + a few animation frames
    await page.waitForFunction(() => typeof window.ZZDynaOrb !== 'undefined', { timeout: 15000 }).catch(() => {});
    await page.waitForTimeout(400);
    const caseObj = { case: `real_213x320_dpr${dpr}`, viewport: { w: REAL_W, h: REAL_H }, dpr, perState: {} };
    for (const st of STATES) {
      await page.evaluate((s) => { try { window.ZZDynaOrb && window.ZZDynaOrb.setState(s); } catch (e) {} }, st);
      await page.waitForTimeout(450); // let particles settle
      const m = await measureInPage(page);
      caseObj.perState[st] = m;
      // screenshot this state
      await page.screenshot({ path: `${OUT}/DESKTOP-PARTICLE-ORB-${st.toUpperCase()}.png` });
    }
    // full-window screenshot (transparent) at idle
    await page.evaluate(() => { try { window.ZZDynaOrb.setState('idle'); } catch (e) {} });
    await page.waitForTimeout(300);
    await page.screenshot({ path: `${OUT}/DESKTOP-PARTICLE-ORB-FULL.png` });
    results.cases.push(caseObj);
    await ctx.close();
  }

  // Case 2: square viewport 256x256 dpr1 — prove circularity independent of window aspect
  {
    const ctx = await browser.newContext({ viewport: { width: 256, height: 256 }, deviceScaleFactor: 1 });
    const page = await ctx.newPage();
    await page.goto(TARGET, { waitUntil: 'load', timeout: 30000 });
    await page.waitForFunction(() => typeof window.ZZDynaOrb !== 'undefined', { timeout: 15000 }).catch(() => {});
    await page.waitForTimeout(400);
    const caseObj = { case: 'square_256x256_dpr1', viewport: { w: 256, h: 256 }, dpr: 1, perState: {} };
    for (const st of STATES) {
      await page.evaluate((s) => { try { window.ZZDynaOrb.setState(s); } catch (e) {} }, st);
      await page.waitForTimeout(450);
      caseObj.perState[st] = await measureInPage(page);
    }
    results.cases.push(caseObj);
    await ctx.close();
  }

  // Case 3: real window dims but forced NON-UNIFORM dpr simulation removed (skip; dpr is single scalar).
  await browser.close();

  const fs = require('fs');
  fs.writeFileSync(`${OUT}/particle_orb_audit.json`, JSON.stringify(results, null, 2));
  console.log('AUDIT_DONE cases=' + results.cases.length);
}

run().catch((e) => { console.error('FATAL', e); process.exit(1); });
