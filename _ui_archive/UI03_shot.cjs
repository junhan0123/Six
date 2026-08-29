const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  const prefix = process.env.OUT_PREFIX || 'OUT';
  const states = (process.env.STATES || 'idle,listening,thinking,speaking,executing').split(',');
  const dpr = parseInt(process.env.DPR || '2', 10);
  const chromePath = 'C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1208/chrome-win64/chrome.exe';
  const url = 'http://127.0.0.1:8010/desktop-avatar/dyna-orb.html';
  const outDir = 'G:/xiao6/_ui_archive';

  const browser = await chromium.launch({
    executablePath: chromePath,
    args: ['--no-sandbox', '--disable-gpu', '--use-gl=swiftshader', '--enable-unsafe-swiftshader'],
  });
  const context = await browser.newContext({
    viewport: { width: 213, height: 320 },
    deviceScaleFactor: dpr,
    bypassCSP: true,
  });
  const page = await context.newPage();
  // Block voice script so the orb stays under our explicit setState control (pure dyna-orb.js experiment)
  await page.route('**/dyna-orb-voice.js', route =>
    route.fulfill({ status: 200, contentType: 'application/javascript', body: '/* blocked for UI-03 experiment */' })
  );

  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push('PAGEERR:' + e.message));

  await page.goto(url, { waitUntil: 'load', timeout: 30000 });
  await page.waitForFunction(() => window.ZZDynaOrb && typeof window.ZZDynaOrb.setState === 'function', { timeout: 15000 });
  await page.waitForTimeout(900); // initial render frames

  for (const st of states) {
    await page.evaluate(s => { try { window.ZZDynaOrb.setState(s); } catch (e) {} }, st);
    await page.waitForTimeout(1500); // allow per-state lerp + animation to settle
    const fname = `${outDir}/${prefix}-${st.toUpperCase()}.png`;
    await page.screenshot({ path: fname, omitBackground: true });
    const sz = fs.statSync(fname);
    console.log('SHOT', st, '->', fname, sz.size, 'bytes');
  }

  await page.evaluate(() => { try { window.ZZDynaOrb.setState('idle'); } catch (e) {} });
  await page.waitForTimeout(900);
  const full = `${outDir}/${prefix}-FULL.png`;
  await page.screenshot({ path: full });
  console.log('SHOT FULL ->', full);

  console.log('CONSOLE_ERRORS:', JSON.stringify(errors.slice(0, 12)));
  try { await browser.close(); } catch (_) {}
  process.exit(0);
})().catch(e => { console.error('FATAL', e); try { process.exit(1); } catch (_) {} });
