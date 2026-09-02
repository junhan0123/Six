/**
 * UI-5C-1 · 验证 Command Dock 作为唯一 Intent Entry 可真实驱动聊天
 * 流程：进入 chat-mode → 在 #osDockInput 输入文本 → 点击发送 → 截图观察 #messages
 */
import { writeFileSync, mkdirSync } from 'node:fs';
import { setTimeout as sleep } from 'node:timers/promises';

const BASE = process.env.ZZ_BASE || 'http://127.0.0.1:8000';
const ROOT = 'G:/xiao6/docs/ui-system/ui5c1-conversation-core-integration';
const OUT = `${ROOT}/shots-after`;
mkdirSync(OUT, { recursive: true });

const res = await fetch('http://127.0.0.1:9222/json/version');
const { webSocketDebuggerUrl } = await res.json();
const ws = new WebSocket(webSocketDebuggerUrl);
await new Promise(r => ws.addEventListener('open', r, { once: true }));

let id = 0;
const pending = new Map();
const errors = [];
ws.addEventListener('message', (ev) => {
  const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
  if (m.method === 'Runtime.exceptionThrown') errors.push(m.params?.exceptionDetails?.text || 'unknown');
});
function send(method, params = {}, sessionId) {
  const _id = ++id;
  return new Promise((resolve, reject) => {
    pending.set(_id, (m) => m.error ? reject(new Error(method + ': ' + JSON.stringify(m.error))) : resolve(m.result));
    ws.send(JSON.stringify({ id: _id, method, params, sessionId }));
  });
}

const { targetInfos } = await send('Target.getTargets');
let page = targetInfos.find(t => t.type === 'page');
if (!page) { const t = await send('Target.createTarget', { url: 'about:blank' }); page = { targetId: t.targetId }; }
const { sessionId } = await send('Target.attachToTarget', { targetId: page.targetId, flatten: true });
const S = (m, p) => send(m, p, sessionId);
await S('Page.enable'); await S('Runtime.enable'); await S('Network.clearBrowserCache');

async function evalJs(expr) {
  const r = await S('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.text + ' :: ' + expr.slice(0, 100));
  return r.result?.value;
}
async function goto(url) {
  await S('Page.navigate', { url });
  for (let i = 0; i < 60; i++) { if (await evalJs('document.readyState').catch(()=>null) === 'complete') break; await sleep(200); }
  await sleep(1500);
}
async function shot(name) {
  const { data } = await S('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
  writeFileSync(`${OUT}/${name}.png`, Buffer.from(data, 'base64'));
  console.log('  shot ->', name);
}

await S('Emulation.setDeviceMetricsOverride', { width: 1600, height: 900, deviceScaleFactor: 1, mobile: false });
await goto(BASE + '/index.html');
await evalJs(`try{localStorage.setItem('xiao6_onboarded','1');}catch(e){} try{var o=document.getElementById('onbOverlay'); if(o) o.remove();}catch(e){} 'ok'`);
await sleep(700);

// 进入 conversation
await evalJs(`try{ openChat(); }catch(e){ document.body.classList.add('chat-mode'); } 'ok'`);
await sleep(800);
await shot('04-1600x900-conversation-empty');

// 等待 Command Dock 初始化
for (let i = 0; i < 30; i++) {
  const has = await evalJs(`!!document.getElementById('osDockInput')`);
  if (has) break;
  await sleep(300);
}
const before = await evalJs(`document.getElementById('messages').children.length`);
console.log('  messages before send:', before);

// 通过 Command Dock 发送：聚焦、输入、点击
await evalJs(`
  const inp = document.getElementById('osDockInput');
  if (!inp) throw new Error('osDockInput not found');
  inp.focus(); inp.value = '进入 Conversation';
  inp.dispatchEvent(new Event('input', { bubbles: true }));
  'ok'
`);
await sleep(200);
await evalJs(`try{ document.getElementById('osDockSend').click(); }catch(e){ console.error(e); } 'ok'`);
await sleep(2500); // 等回复
await shot('05-1600x900-conversation-after-send');
const after = await evalJs(`(() => {
  const msgs = document.getElementById('messages');
  return { count: msgs ? msgs.children.length : 0, lastText: msgs && msgs.lastElementChild ? msgs.lastElementChild.textContent.slice(0,120) : 'n/a',
           chatHistoryH: document.getElementById('chatHistory').getBoundingClientRect().height,
           chatHistoryOp: getComputedStyle(document.getElementById('chatHistory')).opacity };
})()`);
console.log('  messages after send:', after.count, 'historyH:', after.chatHistoryH, 'historyOp:', after.chatHistoryOp, 'last:', after.lastText);

writeFileSync(`${ROOT}/_send_test.json`, JSON.stringify({ before, after, errors: errors.slice(0,10) }, null, 2), 'utf-8');
console.log('\n=== send test 完成 === 异常:', errors.length);
ws.close(); process.exit(0);
