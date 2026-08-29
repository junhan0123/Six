const { chromium } = require('playwright');

const EXE = 'C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1148/chrome-win/chrome.exe';
const URL = 'http://localhost:8010/xiao6-space/index.html';

(async () => {
  const browser = await chromium.launch({ executablePath: EXE, headless: true, args: ['--no-proxy-server', '--disable-gpu'] });
  const page = await browser.newPage();
  const api = [];
  page.on('request', r => { const u = r.url(); if (u.includes('/api/stream') || u.includes('/api/agent/state') || u.includes('/api/chat')) api.push(u); });
  await page.goto(URL, { waitUntil: 'load', timeout: 30000 });
  await page.waitForTimeout(6000);
  let dot = 'NO_DOT';
  try { dot = await page.$eval('#rtStreamDot', el => el.getAttribute('data-state')); } catch (e) {}
  console.log('PROBE_DOT_STATE=' + dot);
  console.log('PROBE_API_REQS=' + JSON.stringify(api));
  await browser.close();
})().catch(e => { console.error('PROBE_ERR', e); process.exit(1); });
