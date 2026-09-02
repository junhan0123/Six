import { setTimeout as sleep } from 'node:timers/promises';
const BASE='http://127.0.0.1:8000';
const res=await fetch('http://127.0.0.1:9222/json/version');
const {webSocketDebuggerUrl}=await res.json();
const ws=new WebSocket(webSocketDebuggerUrl);
await new Promise(r=>ws.addEventListener('open',r,{once:true}));
let id=0;const pending=new Map();
ws.addEventListener('message',(ev)=>{const m=JSON.parse(ev.data);if(m.id&&pending.has(m.id)){pending.get(m.id)(m);pending.delete(m.id);}});
function send(method,params={},sid){const _id=++id;return new Promise((res,rej)=>{pending.set(_id,(m)=>m.error?rej(new Error(method+': '+JSON.stringify(m.error))):res(m.result));ws.send(JSON.stringify({id:_id,method,params,sid}));});}
const {targetInfos}=await send('Target.getTargets');
let page=targetInfos.find(t=>t.type==='page');
if(!page){const t=await send('Target.createTarget',{url:'about:blank'});page={targetId:t.targetId};}
const {sessionId}=await send('Target.attachToTarget',{targetId:page.targetId,flatten:true});
const S=(m,p)=>send(m,p,sessionId);
await S('Page.enable');await S('Runtime.enable');
async function ev(e){const r=await S('Runtime.evaluate',{expression:e,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw new Error(r.exceptionDetails.text);return r.result?.value;}
async function setSize(w,h){await S('Emulation.setDeviceMetricsOverride',{width:w,height:h,deviceScaleFactor:1,mobile:false});}
async function goto(u){await S('Page.navigate',{url:u});for(let i=0;i<60;i++){const s=await ev('document.readyState').catch(()=>null);if(s==='complete')break;await sleep(200);}await sleep(1400);}
const KILL='try{localStorage.setItem("xiao6_onboarded","1");}catch(e){}try{var o=document.getElementById("onbOverlay");if(o)o.remove();}catch(e){}"ok"';
await setSize(1920,1080);await goto(BASE+'/index.html');await ev(KILL);await sleep(600);
// 打开 Context 抽屉
await ev(`try{ document.body.classList.add('os-context-open'); document.querySelector('.os-side')?.style.setProperty('transform','none'); }catch(e){}"ok"`);
await sleep(800);
const r=await ev(`(()=>{const el=document.querySelector('.os-side');const cs=getComputedStyle(el);const b=el.getBoundingClientRect();return{display:cs.display,opacity:cs.opacity,transform:cs.transform,left:Math.round(b.left),right:Math.round(b.right),top:Math.round(b.top),bottom:Math.round(b.bottom),vw:window.innerWidth,visibleInViewport:(b.left>=0&&b.right<=window.innerWidth)};})()`);
console.log('Context 抽屉打开态：',JSON.stringify(r,null,2));
console.log(r.visibleInViewport?'✅ 抽屉在视口内正常显示，clip 未误裁':'❌ 抽屉被裁切/越界');
ws.close();process.exit(0);
