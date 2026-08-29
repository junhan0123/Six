const { chromium } = require('playwright');
const fs = require('fs');
const DIR = 'G:/xiao6/_ui_archive/shots_p51';
fs.mkdirSync(DIR, { recursive: true });
const BASE = 'http://127.0.0.1:8010';
const URL = BASE + '/xiao6-space/index.html';
const EXE = 'C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1208/chrome-win64/chrome.exe';

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: EXE, args: ['--no-sandbox', '--disable-gpu'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  const fails = [];
  page.on('response', r => { if (r.status() >= 400) fails.push(r.status() + ' ' + r.url()); });
  page.on('requestfailed', r => fails.push('FAIL ' + r.url() + ' ' + (r.failure() && r.failure().errorText)));

  await page.goto(URL, { waitUntil: 'load', timeout: 30000 });
  await page.waitForTimeout(2000);
  await page.screenshot({ path: DIR + '/A_main.png' }); console.log('SAVED A');
  const info = await page.evaluate(() => ({ title: document.title, body: document.body ? document.body.innerText.length : 0, html: document.documentElement.outerHTML.length }));
  await page.waitForTimeout(3000);
  await page.screenshot({ path: DIR + '/B_after_sse.png' }); console.log('SAVED B');
  await page.setViewportSize({ width: 390, height: 844 }); await page.waitForTimeout(1000);
  await page.screenshot({ path: DIR + '/C_mobile.png' }); console.log('SAVED C');
  try { await page.goto(BASE + '/', { waitUntil: 'load', timeout: 15000 }); await page.waitForTimeout(1200); await page.screenshot({ path: DIR + '/D_root.png' }); console.log('SAVED D'); } catch (e) { fails.push('D:' + e.message); }
  await page.goto(URL, { waitUntil: 'load', timeout: 15000 }); await page.waitForTimeout(800);
  await page.screenshot({ path: DIR + '/E_fullpage.png', fullPage: true }); console.log('SAVED E');
  console.log('INFO ' + JSON.stringify(info));
  console.log('FAILS ' + JSON.stringify(fails.slice(0, 25)));
  await browser.close();
  process.exit(0);
})().catch(e => { console.error('SHOT_FAIL', e && e.message); process.exit(2); });
