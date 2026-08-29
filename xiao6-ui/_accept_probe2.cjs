const { chromium } = require('playwright');
const fs = require('fs');
const EXE = 'C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1148/chrome-win/chrome.exe';
const URL = 'http://localhost:8010/xiao6-space/index.html';
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const out = { streamEvents: {}, chatSeen: [], overlayTitles: [], errors: [] };
  const browser = await chromium.launch({ executablePath: EXE, headless: true, args: ['--no-proxy-server', '--disable-gpu'] });
  const page = await browser.newPage();
  await page.addInitScript(() => {
    window.__stream = []; window.__chat = []; window.__esLog = [];
    const RealES = window.EventSource;
    function W(url, o) { const i = new RealES(url, o); window.__esLog.push(Date.now()); i.addEventListener('message', e => { try { window.__stream.push({ ts: Date.now(), data: e.data }); } catch (_) {} }); return i; }
    W.prototype = RealES.prototype; W.CONNECTING = RealES.CONNECTING; W.OPEN = RealES.OPEN; W.CLOSED = RealES.CLOSED; window.EventSource = W;
    // also tee the chat SSE by wrapping fetch
    const Rf = window.fetch.bind(window);
    window.fetch = function (u, o) {
      const p = Rf(u, o);
      if (typeof u === 'string' && u.includes('/api/chat')) {
        p.then(async (resp) => { try { const r = resp.clone(); const rd = r.body.getReader(); const dec = new TextDecoder(); let buf = ''; while (true) { const { done, value } = await rd.read(); if (done) break; buf += dec.decode(value, { stream: true }); const parts = buf.split('\n\n'); buf = parts.pop(); for (const pt of parts) { const line = pt.replace(/^data:\s?/, ''); if (line && line !== '[DONE]') { try { window.__chat.push(line); } catch (_) {} } } } } catch (_) {} });
      }
      return p;
    };
  });
  page.on('pageerror', e => out.errors.push(String(e).slice(0, 300)));
  await page.goto(URL, { waitUntil: 'load', timeout: 30000 });
  await page.waitForSelector('#rtStreamDot[data-state="connected"]', { timeout: 15000 }).catch(() => {});

  const classify = (raw) => { let p; try { p = JSON.parse(raw); } catch (_) { return null; } return p.xiao6_event || p.event || null; };

  // send a chat that should trigger tools (weather + hotspots)
  await page.evaluate(() => { const b = document.querySelector('.zz-nav-btn[data-nav="conversation"]'); if (b) b.click(); else { const o = document.getElementById('orbBtn'); if (o) o.click(); } });
  await page.waitForSelector('#cmdInput:visible', { timeout: 10000 });
  await page.fill('#cmdInput', '北京今天天气怎么样？有什么热点新闻？');
  await page.press('#cmdInput', 'Enter');

  // observe 25s: stream events + chat SSE events + overlay titles
  for (let i = 0; i < 50; i++) {
    const oc = await page.evaluate(() => {
      const o = document.getElementById('overlay');
      if (o && o.getAttribute('aria-hidden') === 'false') { const t = (document.getElementById('overlayTitle') || {}).textContent; return t; }
      return null;
    });
    if (oc && !out.overlayTitles.includes(oc)) out.overlayTitles.push(oc);
    await sleep(500);
  }
  const stream = await page.evaluate(() => window.__stream.map(d => d.data));
  const chat = await page.evaluate(() => window.__chat);
  const seenStream = {}; stream.forEach(d => { const ev = classify(d); if (ev) seenStream[ev] = (seenStream[ev] || 0) + 1; });
  const seenChat = {}; chat.forEach(d => { const ev = classify(d); if (ev) seenChat[ev] = (seenChat[ev] || 0) + 1; });
  out.streamEvents = seenStream;
  out.chatSeen = seenChat;
  out.overlayTitlesFinal = out.overlayTitles;
  out.chatRawCount = chat.length;
  out.streamRawCount = stream.length;
  out.errors = out.errors;
  fs.writeFileSync('G:/xiao6/xiao6-ui/_accept_probe2.json', JSON.stringify(out, null, 2));
  console.log('STREAM_EVENTS=' + JSON.stringify(seenStream));
  console.log('CHAT_EVENTS=' + JSON.stringify(seenChat));
  console.log('OVERLAY_TITLES=' + JSON.stringify(out.overlayTitles));
  console.log('chatRaw=' + chat.length + ' streamRaw=' + stream.length + ' errors=' + out.errors.length);
  await browser.close();
})().catch(e => { console.error('PROBE2_FATAL', e); process.exit(2); });
