// PHASE 5.1-HOTFIX-UI-02 — multi-threshold alpha bbox: is the BRIGHT core circular?
const { chromium } = require('playwright');
const TARGET = 'http://127.0.0.1:8010/desktop-avatar/dyna-orb.html';
const EXEC = 'C:\\Users\\Administrator\\AppData\\Local\\ms-playwright\\chromium-1208\\chrome-win64\\chrome.exe';
const OUT = 'G:\\xiao6\\_ui_archive';
const STATES = ['idle','listening','thinking','speaking','executing'];
const THR = [6,14,40,80,120,160,200,230];

async function layeredMeasure(page) {
  return await page.evaluate((thresholds) => {
    const c = document.getElementById('orb-canvas');
    const ctx = c.getContext('2d');
    const w = c.width, h = c.height;
    const dpr = window.devicePixelRatio || 1;
    let img;
    try { img = ctx.getImageData(0,0,w,h).data; } catch (e) { return {err:e.message}; }
    const cx = w/2, cy = h/2;
    const res = { w, h, dpr, cx, cy, scale: Math.round(Math.min(w,h)*0.40), layers: [] };
    for (const TH of thresholds) {
      let minX=w,minY=h,maxX=-1,maxY=-1,cnt=0,sumX=0,sumY=0;
      for (let y=0;y<h;y++) for (let x=0;x<w;x++) {
        const a = img[(y*w+x)*4+3];
        if (a > TH) { if(x<minX)minX=x; if(x>maxX)maxX=x; if(y<minY)minY=y; if(y>maxY)maxY=y; cnt++; sumX+=x; sumY+=y; }
      }
      const bbW = maxX-minX+1, bbH = maxY-minY+1;
      res.layers.push({
        TH, cnt,
        bbW, bbH,
        ratio: (bbW>0&&bbH>0) ? +(bbW/bbH).toFixed(4) : null,
        absDiff: (bbW>=0&&bbH>=0) ? Math.abs(bbH-bbW) : null, // report h-w (positive => taller)
        centroidX: cnt? +(sumX/cnt).toFixed(2) : null,
        centroidY: cnt? +(sumY/cnt).toFixed(2) : null,
        centroidOffsetX: cnt? +((sumX/cnt)-cx).toFixed(2) : null,
        centroidOffsetY: cnt? +((sumY/cnt)-cy).toFixed(2) : null,
      });
    }
    return res;
  }, THR);
}

async function run() {
  const browser = await chromium.launch({ executablePath: EXEC, args:['--no-sandbox','--disable-gpu','--use-gl=swiftshader','--enable-unsafe-swiftshader'] });
  const results = { cases: [] };
  // Real window 213x320, dpr1
  const ctx = await browser.newContext({ viewport: { width: 213, height: 320 }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  await page.goto(TARGET, { waitUntil:'load', timeout:30000 });
  await page.waitForFunction(()=>typeof window.ZZDynaOrb!=='undefined',{timeout:15000}).catch(()=>{});
  await page.waitForTimeout(400);
  for (const st of STATES) {
    await page.evaluate((s)=>{try{window.ZZDynaOrb.setState(s);}catch(e){}}, st);
    await page.waitForTimeout(450);
    results.cases.push({ case: 'real_213x320_dpr1', state: st, layers: await layeredMeasure(page) });
  }
  await ctx.close();
  // Square 256x256 dpr1 for control
  const ctx2 = await browser.newContext({ viewport: { width: 256, height: 256 }, deviceScaleFactor: 1 });
  const page2 = await ctx2.newPage();
  await page2.goto(TARGET, { waitUntil:'load', timeout:30000 });
  await page2.waitForFunction(()=>typeof window.ZZDynaOrb!=='undefined',{timeout:15000}).catch(()=>{});
  await page2.waitForTimeout(400);
  for (const st of STATES) {
    await page2.evaluate((s)=>{try{window.ZZDynaOrb.setState(s);}catch(e){}}, st);
    await page2.waitForTimeout(450);
    results.cases.push({ case: 'square_256x256_dpr1', state: st, layers: await layeredMeasure(page2) });
  }
  await ctx2.close();
  await browser.close();
  require('fs').writeFileSync(`${OUT}/particle_orb_layers.json`, JSON.stringify(results, null, 2));
  console.log('LAYERS_DONE cases='+results.cases.length);
}
run().catch(e=>{console.error(e);process.exit(1);});
