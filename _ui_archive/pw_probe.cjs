const fs = require('fs');
const LOG = 'G:/xiao6/_ui_archive/pw_probe.log';
function L(s){ fs.appendFileSync(LOG, s + '\n'); }
fs.writeFileSync(LOG, 'START\n');
try {
  L('before require');
  const p = require('playwright');
  L('REQUIRE_OK keys=' + JSON.stringify(Object.keys(p)));
  L('chromium=' + typeof p.chromium);
  L('before launch');
  (async () => {
    try {
      const browser = await p.chromium.launch({ headless: true, executablePath: 'C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1208/chrome-win64/chrome.exe', args: ['--no-sandbox','--disable-gpu'] });
      L('LAUNCH_OK');
      const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
      await page.goto('http://127.0.0.1:8010/xiao6-space/index.html', { waitUntil: 'load', timeout: 30000 });
      await page.waitForTimeout(1500);
      await page.screenshot({ path: 'G:/xiao6/_ui_archive/shots_p51/A_main.png' });
      L('SHOT_OK');
      const info = await page.evaluate(() => ({ title: document.title, bodyLen: document.body ? document.body.innerText.length : 0 }));
      L('INFO ' + JSON.stringify(info));
      await browser.close();
      L('DONE');
    } catch (e) {
      L('ASYNC_ERR ' + (e && e.stack || e));
    }
  })();
} catch (e) {
  L('REQUIRE_ERR ' + (e && e.stack || e));
}
