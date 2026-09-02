/**
 * 最小 PNG 解码器（仅支持 Chrome 截图产出的 8-bit 非隔行 RGB/RGBA）
 * 用途：把「首屏是否已融合」从主观描述变成可测量的像素事实。
 * 无第三方依赖，仅用 node:zlib。
 */
import { inflateSync } from 'node:zlib';

export function decodePNG(buf) {
  if (buf.readUInt32BE(0) !== 0x89504e47) throw new Error('not a png');
  let off = 8, width = 0, height = 0, bitDepth = 0, colorType = 0;
  const idat = [];
  while (off < buf.length) {
    const len = buf.readUInt32BE(off);
    const type = buf.toString('ascii', off + 4, off + 8);
    const data = buf.subarray(off + 8, off + 8 + len);
    if (type === 'IHDR') {
      width = data.readUInt32BE(0); height = data.readUInt32BE(4);
      bitDepth = data[8]; colorType = data[9];
      if (bitDepth !== 8) throw new Error('unsupported bitDepth ' + bitDepth);
      if (data[12] !== 0) throw new Error('interlaced png unsupported');
    } else if (type === 'IDAT') idat.push(data);
    else if (type === 'IEND') break;
    off += 12 + len;
  }
  const bpp = colorType === 6 ? 4 : colorType === 2 ? 3 : (() => { throw new Error('unsupported colorType ' + colorType); })();
  const raw = inflateSync(Buffer.concat(idat));
  const stride = width * bpp;
  const out = Buffer.alloc(height * stride);
  let pos = 0;
  for (let y = 0; y < height; y++) {
    const filter = raw[pos++];
    const line = raw.subarray(pos, pos + stride); pos += stride;
    const cur = out.subarray(y * stride, (y + 1) * stride);
    const prev = y > 0 ? out.subarray((y - 1) * stride, y * stride) : null;
    for (let x = 0; x < stride; x++) {
      const a = x >= bpp ? cur[x - bpp] : 0;
      const b = prev ? prev[x] : 0;
      const c = (prev && x >= bpp) ? prev[x - bpp] : 0;
      let v = line[x];
      switch (filter) {
        case 0: break;
        case 1: v = (v + a) & 255; break;
        case 2: v = (v + b) & 255; break;
        case 3: v = (v + ((a + b) >> 1)) & 255; break;
        case 4: {
          const p = a + b - c, pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c);
          v = (v + (pa <= pb && pa <= pc ? a : pb <= pc ? b : c)) & 255; break;
        }
        default: throw new Error('bad filter ' + filter);
      }
      cur[x] = v;
    }
  }
  return { width, height, bpp, data: out };
}

/** 相对亮度（sRGB 感知加权，0–255） */
export const lum = (img, x, y) => {
  const i = y * img.width * img.bpp + x * img.bpp;
  return 0.2126 * img.data[i] + 0.7152 * img.data[i + 1] + 0.0722 * img.data[i + 2];
};

/** 矩形区域统计：均值 / 标准差（标准差 ≈「有没有星空纹理」） */
export function regionStats(img, x0, y0, w, h) {
  let n = 0, s = 0, s2 = 0, min = 255, max = 0;
  for (let y = y0; y < y0 + h; y++) {
    if (y < 0 || y >= img.height) continue;
    for (let x = x0; x < x0 + w; x++) {
      if (x < 0 || x >= img.width) continue;
      const L = lum(img, x, y);
      n++; s += L; s2 += L * L; if (L < min) min = L; if (L > max) max = L;
    }
  }
  const mean = s / n;
  return { n, mean: +mean.toFixed(3), sd: +Math.sqrt(Math.max(0, s2 / n - mean * mean)).toFixed(3), min: +min.toFixed(1), max: +max.toFixed(1) };
}

/**
 * 水平亮度剖面：在 y 行、[x0,x1) 范围内逐列取「上下 band 行的均值」。
 * 用于检测「卡片硬边」——边框会在剖面上形成尖锐台阶。
 */
export function hProfile(img, y, x0, x1, band = 9) {
  const prof = [];
  for (let x = x0; x < x1; x++) {
    let s = 0, n = 0;
    for (let dy = -band; dy <= band; dy++) {
      const yy = y + dy; if (yy < 0 || yy >= img.height) continue;
      s += lum(img, x, yy); n++;
    }
    prof.push(s / n);
  }
  return prof;
}

/** 剖面上的最大单步跳变（台阶强度）及其位置 */
export function maxStep(prof, x0 = 0) {
  let best = 0, at = -1;
  for (let i = 1; i < prof.length; i++) {
    const d = Math.abs(prof[i] - prof[i - 1]);
    if (d > best) { best = d; at = x0 + i; }
  }
  return { maxStep: +best.toFixed(3), atX: at };
}
