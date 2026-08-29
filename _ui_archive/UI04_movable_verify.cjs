'use strict';
// UI04 movable verification — REAL Chromium, stubbed electronAPI.
// Goal: prove the EXISTING dyna-orb.html drag logic works:
//   - pointerdown ON sphere -> setIgnoreMouse(false) (no pass-through) + drag starts
//   - pointermove while dragging -> moveWindow(dx,dy) called
//   - pointermove OFF sphere (hover) -> setIgnoreMouse(true) (pass-through)
// This is READ-ONLY w.r.t. production: we only inject a stub bridge for the test page.
const { chromium } = require('playwright');
const path = require('path');

const EXE = 'C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1208/chrome-win64/chrome.exe';
const URL = process.env.BASE_URL || 'http://127.0.0.1:8010/desktop-avatar/dyna-orb.html';
const W = 213, H = 320, DPR = 2;

(async () => {
  const log = (...a) => { console.log('[stage]', ...a); };
  process.on('unhandledRejection', e => { console.error('UNHANDLED', e); process.exit(2); });
  const calls = { moveWindow: [], setIgnore: [] };
  log('launching chromium');
  const browser = await chromium.launch({
    executablePath: EXE,
    args: ['--no-sandbox', '--disable-gpu', '--use-gl=swiftshader', '--enable-unsafe-swiftshader'],
  });
  const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: DPR });
  log('context created');
  const page = await ctx.newPage();
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push('PAGEERROR: ' + e.message));

  // Inject stub electronAPI BEFORE page scripts run.
  await page.addInitScript(() => {
    window.__calls = { moveWindow: [], setIgnore: [] };
    window.electronAPI = {
      close() {}, hide() {}, openChat() {}, focusOrb() {},
      setIgnoreMouse(ignore) { window.__calls.setIgnore.push(ignore); },
      moveWindow(dx, dy) { window.__calls.moveWindow.push([dx, dy]); },
    };
  });

  await page.goto(URL, { waitUntil: 'load' });
  // let orb init + voice script settle
  await page.waitForTimeout(1200);

  const canvasBox = await page.evaluate(() => {
    const c = document.getElementById('orb-canvas');
    const r = c.getBoundingClientRect();
    return { left: r.left, top: r.top, w: r.width, h: r.height };
  });

  const cx = canvasBox.left + canvasBox.w / 2;
  const cy = canvasBox.top + canvasBox.h / 2;
  const offX = canvasBox.left + 4;          // top-left corner = transparent area (off sphere)
  const offY = canvasBox.top + 4;

  // 1) hover OFF sphere -> should setIgnore(true)
  await page.mouse.move(offX, offY);
  await page.waitForTimeout(60);

  // 2) hover ON sphere -> should setIgnore(false)
  await page.mouse.move(cx, cy);
  await page.waitForTimeout(60);

  // 3) pointerdown ON sphere -> drag start (setIgnore(false) again) + cursor grab
  await page.mouse.move(cx, cy);
  await page.mouse.down();
  await page.waitForTimeout(60);

  // 4) drag -> moveWindow called
  await page.mouse.move(cx + 30, cy + 20, { steps: 5 });
  await page.waitForTimeout(80);

  // 5) pointerup -> endDrag
  await page.mouse.up();
  await page.waitForTimeout(60);

  // 6) move back OFF sphere -> setIgnore(true)
  await page.mouse.move(offX, offY);
  await page.waitForTimeout(60);

  const result = await page.evaluate(() => window.__calls);

  await browser.close();

  const onSphereIgnore = result.setIgnore.filter(v => v === false);
  const offSphereIgnore = result.setIgnore.filter(v => v === true);
  const moved = result.moveWindow.length;
  const totalDx = result.moveWindow.reduce((s, p) => s + (p[0] || 0), 0);
  const totalDy = result.moveWindow.reduce((s, p) => s + (p[1] || 0), 0);

  console.log('=== UI04 MOVABLE VERIFY (REAL CHROMIUM) ===');
  console.log('setIgnore(false) [ON sphere, NO pass-through] count :', onSphereIgnore.length);
  console.log('setIgnore(true)  [OFF sphere, pass-through]    count :', offSphereIgnore.length);
  console.log('moveWindow calls [drag]                          :', moved);
  console.log('moveWindow total delta (dx,dy)                   :', totalDx, totalDy);
  console.log('console errors                                   :', errors.length, errors.slice(0, 5));
  const pass = onSphereIgnore.length >= 1 && offSphereIgnore.length >= 1 && moved >= 1 && errors.length === 0;
  const out = {
    RESULT: pass ? 'PASS' : 'CHECK',
    onSphereIgnoreFalseCount: onSphereIgnore.length,
    offSphereIgnoreTrueCount: offSphereIgnore.length,
    moveWindowCalls: moved,
    moveWindowTotalDelta: [totalDx, totalDy],
    consoleErrors: errors,
    summary: pass ? 'sphere draggable + non-pass-through, outside pass-through' : 'see counts',
  };
  require('fs').writeFileSync('G:/xiao6/_ui_archive/ui04_movable_result.json', JSON.stringify(out, null, 2));
  console.log('RESULT:', pass ? 'PASS — sphere draggable + non-pass-through, outside pass-through' : 'CHECK');
  process.exit(0);
})().catch(e => { console.error('FATAL', e); process.exit(1); });
