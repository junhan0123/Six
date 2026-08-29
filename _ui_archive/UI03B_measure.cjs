// UI03B measurement — alpha-based bbox + brightness-bias metrics for the OPTION B FINAL screenshots.
// Reuses the UI-03 decode/analyze logic (PNG colorType=6 RGBA, alpha offset=3).
const fs = require('fs');
const zlib = require('zlib');

function decodePNG(path) {
  const b = fs.readFileSync(path);
  const w = b.readUInt32BE(16), h = b.readUInt32BE(20);
  const colorType = b[25];
  let off = 8, idat = [];
  while (off < b.length) {
    const len = b.readUInt32BE(off);
    const type = b.toString('ascii', off + 4, off + 8);
    if (type === 'IDAT') idat.push(b.slice(off + 8, off + 8 + len));
    if (type === 'IEND') break;
    off += 12 + len;
  }
  const raw = zlib.inflateSync(Buffer.concat(idat));
  const channels = colorType === 6 ? 4 : (colorType === 2 ? 3 : (colorType === 4 ? 2 : 1));
  const stride = w * channels;
  const out = Buffer.alloc(h * stride);
  let prev = Buffer.alloc(stride);
  let p = 0;
  for (let y = 0; y < h; y++) {
    const filter = raw[p++];
    const cur = Buffer.alloc(stride);
    for (let i = 0; i < stride; i++) {
      const xv = raw[p++];
      const a = i >= channels ? cur[i - channels] : 0;
      const bb = prev[i];
      const c = i >= channels ? prev[i - channels] : 0;
      let val;
      switch (filter) {
        case 0: val = xv; break;
        case 1: val = xv + a; break;
        case 2: val = xv + bb; break;
        case 3: val = xv + ((a + bb) >> 1); break;
        case 4: {
          const pa = Math.abs(bb - c), pb = Math.abs(a - c), pc = Math.abs(a + bb - 2 * c);
          const pr = (pa <= pb && pa <= pc) ? a : (pb <= pc ? bb : c);
          val = xv + pr; break;
        }
        default: val = xv;
      }
      cur[i] = val & 0xff;
    }
    cur.copy(out, y * stride);
    prev = cur;
  }
  return { w, h, channels, colorType, data: out };
}

function analyze(path) {
  const { w, h, channels, data } = decodePNG(path);
  const aOff = channels === 4 ? 3 : (channels === 2 ? 1 : -1);
  const ATH_LO = 8, ATH_HI = 48;
  let minX = w, minY = h, maxX = -1, maxY = -1, cnt = 0;
  let sumLX = 0, sumLY = 0, sumL = 0;
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const i = (y * w + x) * channels;
      const al = aOff >= 0 ? data[i + aOff] : 255;
      if (al > ATH_LO) {
        cnt++;
        if (x < minX) minX = x; if (x > maxX) maxX = x;
        if (y < minY) minY = y; if (y > maxY) maxY = y;
      }
      if (al > ATH_HI) {
        const lum = (data[i] + data[i + 1] + data[i + 2]) / 3;
        sumLX += x * lum; sumLY += y * lum; sumL += lum;
      }
    }
  }
  if (cnt === 0) return { cnt: 0 };
  const bbW = maxX - minX + 1, bbH = maxY - minY + 1;
  const cx = (minX + bbW / 2), cy = (minY + bbH / 2);
  const cov = +(100 * cnt / (w * h)).toFixed(2);
  let cx_b = 0, cy_b = 0, dx = 0, dy = 0, topFrac = 0, leftFrac = 0;
  if (sumL > 0) {
    cx_b = sumLX / sumL; cy_b = sumLY / sumL;
    dx = +(cx_b - cx).toFixed(1); dy = +(cy_b - cy).toFixed(1);
    let topL = 0, botL = 0, leftL = 0, rightL = 0;
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const i = (y * w + x) * channels;
        const al = aOff >= 0 ? data[i + aOff] : 255;
        if (al > ATH_HI) {
          const lum = (data[i] + data[i + 1] + data[i + 2]) / 3;
          if (y < cy) topL += lum; else botL += lum;
          if (x < cx) leftL += lum; else rightL += lum;
        }
      }
    }
    topFrac = +(100 * topL / (topL + botL)).toFixed(1);
    leftFrac = +(100 * leftL / (leftL + rightL)).toFixed(1);
  }
  return { cnt, cov, bbW, bbH, ratio: +(bbW / bbH).toFixed(4),
    cx: +cx.toFixed(1), cy: +cy.toFixed(1), cx_b: +cx_b.toFixed(1), cy_b: +cy_b.toFixed(1),
    dx, dy, topFrac, leftFrac };
}

const dir = 'G:/xiao6/_ui_archive';
const prefix = process.env.MEAS_PREFIX || 'DESKTOP-PARTICLE-ORB-UI03B';
const states = ['IDLE', 'LISTENING', 'THINKING', 'SPEAKING', 'ERROR', 'DONE'];

// Expected BASELINE reference (from PHASE-5.1-HOTFIX-UI-03 report, omitBackground RGBA run)
const BASE_REF = {
  IDLE:       { ratio: 1.000, cov: 9.18, dx: -0.6, dy: -1.0 },
  LISTENING:  { ratio: 1.006, cov: 10.37, dx: 0.4, dy: -3.6 },
  THINKING:   { ratio: 1.017, cov: 12.92, dx: 1.4, dy: -1.9 },
  SPEAKING:   { ratio: 1.021, cov: 11.03, dx: 0.0, dy: -1.5 },
  ERROR:      { ratio: 1.000, cov: 11.22 },
  DONE:       { ratio: 1.000, cov: 11.40 },
};
// Expected OPTION B reference
const B_REF = {
  IDLE:       { ratio: 1.000, cov: 9.81, dx: -1.1, dy: -0.5 },
  LISTENING:  { ratio: 1.006, cov: 11.06 },
  THINKING:   { ratio: 1.017, cov: 13.75 },
  SPEAKING:   { ratio: 1.021, cov: 11.70 },
};

console.log('Canvas backing = 426x640 (CSS 213x320 @ dpr2). Expected orb center ~ (213, 320).');
console.log('ATH_LO=8 外轮廓 / ATH_HI=48 实体粒子场 | cov% 含光晕覆盖 | ratio 1.000=正圆\n');
console.log('state'.padEnd(11), 'ratio'.padStart(7), 'cov%'.padStart(7), 'cx'.padStart(6), 'cy'.padStart(6),
  'dx'.padStart(6), 'dy'.padStart(6), 'topF'.padStart(7), 'leftF'.padStart(7), '| B?cov'.padStart(8));
for (const st of states) {
  const f = `${dir}/${prefix}-${st}.png`;
  let r;
  try { r = analyze(f); } catch (e) { console.log(st.padEnd(11), 'ERR:' + e.message); continue; }
  if (r.cnt === 0) { console.log(st.padEnd(11), 'EMPTY'); continue; }
  const bref = B_REF[st] ? B_REF[st].cov : '-';
  const tag = (typeof bref === 'number' && r.cov >= bref - 0.6) ? 'OK' : (bref === '-' ? 'n/a' : 'LOW');
  console.log(
    st.padEnd(11),
    String(r.ratio).padStart(7),
    String(r.cov).padStart(7),
    String(r.cx).padStart(6),
    String(r.cy).padStart(6),
    String(r.dx).padStart(6),
    String(r.dy).padStart(6),
    String(r.topFrac).padStart(7),
    String(r.leftFrac).padStart(7),
    String(bref).padStart(7) + ' ' + tag
  );
}
