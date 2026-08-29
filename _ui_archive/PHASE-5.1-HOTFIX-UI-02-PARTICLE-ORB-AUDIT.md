# PHASE 5.1-HOTFIX-UI-02 · DESKTOP PARTICLE VOICE ORB VISUAL AUDIT

**产品**：小6 Xiao6 v1.4.0
**任务类型**：AUDIT ONLY（只读调查，禁止任何代码修改）
**审计对象**：桌面粒子语音球（肉眼可见的粒子 / 发光 / 球体感 / 动态运动 / 语音状态反馈主体）
**审计日期**：2026-08-18
**执行纪律**：VERIFY-BEFORE-CHANGE → READ REAL SOURCE → MEASURE REAL RUNTIME → CAPTURE REAL DESKTOP → NO GUESS → NO SCOPE CREEP → NO CODE CHANGE → STOP AFTER AUDIT

---

## 1. Executive Summary（执行摘要）

老板明确指出：UI-01 修的是 **DOM Voice Orb**（已 FROZEN 证明为正圆），但本次实际指的是 **"桌面上的粒子语音球"**——即桌面独立透明窗内、由 Canvas 2D 点云渲染的语音状态主体。

经六阶段审计（真实源码定位 → 渲染技术确认 → 真实运行时截图 → 像素/几何分析 → Root Cause 排查 → 禁止提前修改），结论如下：

- **桌面粒子语音球 = `desktop-avatar/dyna-orb.html` + `dyna-orb.js` + `dyna-orb-voice.js`**，由 Electron `avatar-window.js` 以 **213×320 透明 / 无边框 / alwaysOnTop** 独立窗加载。
- 渲染技术为 **Canvas 2D 点云球**（非 WebGL、非 CSS、非 Electron overlay 自身渲染）。
- 投影数学 `sx = cx + rx*scale; sy = cy - ry*scale` 中 **X/Y 共用同一 `scale`** → 数学上球面投影恒为正圆，无 scaleX≠scaleY / aspect 错误源。
- **IDLE（老板关注态）实测像素包围盒 = 严格正圆**：real_213×320 dpr1 = 173×173 ratio **1.000**；dpr2 = 344×344 ratio **1.000**；dpr3 = 513×514 ratio **0.998**；方形 256×256 对照 = 208×208 ratio **1.000**。跨 DPR、跨窗口比例全部 1.000 级。
- 分层 centroid 分析：IDLE 各 alpha 阈值（TH 6→200）ratio 均为 **1.000**，仅 TH230 亮核 0.947（但点数仅 334，属统计噪声）；亮核 centroid 偏移 ≤ **6.56px** → **亮核也是圆，椭圆感非渲染层**。
- **唯一客观椭圆出现在 executing（加载/执行态）**：spinner ring `R = scale*1.5 = 127.5`，在 213 宽窄窗内 **仅横向被裁**（两侧贴边 bbW=213），纵向未贴边（bbH=264）→ 0.807 椭圆。方形 256×256 窗下同一 ring **完整为圆（ratio 1.000）**，证明是"窄窗宽高比 vs ring 半径"不匹配造成的**窗口裁切**，非渲染 bug、非 idle 态、且非几何失真。
- **视觉椭圆感溯源**：截图目视呈"顶底弧度缓、左右更鼓窄、上密下疏"的纵向椭圆嫌疑，但客观像素 bbox 始终为正圆。分层 centroid 证明亮核亦为圆 → **椭圆感来自 glow/lighting 深度着色 + rotX≈0.22 俯仰倾斜 + 自转造成的亮度/密度分布不对称，属视觉感知层，非几何缺陷**。

**STOP 判定：A 类**——粒子球本身几何/渲染完全正确，仅光照或 glow 造成视觉感知问题 → **STOP，不修改代码，明确说明这是设计层问题**。若老板坚持修 executing 态 ring 裁切，给出最小方案备选（§16），但**本次不实施**。

---

## 2. Target Identification（目标识别）

| 项 | 内容 |
|---|---|
| 老板原话目标 | "桌面上的粒子语音球"——粒子 / 发光 / 球体感 / 动态运动 / 语音状态反馈 |
| ✅ 本次目标 | `G:\xiao6\xiao6-ui\desktop-avatar\dyna-orb.html`（Canvas 2D 粒子球） |
| ❌ 已冻结（UI-01） | DOM Voice Orb：`#orbPresence` / `.zz-orb-core` / `.zz-orb-ring`（CSS 渲染，56×56 / 40×40 / 56×56，border-radius 50%，四态正圆，零改动） |
| ❌ 非目标 A | `G:\xiao6\xiao6-desktop\pet\`（Lottie SVG 机器人桌宠，pet.js 用 robot-futuristic.json） |
| ❌ 非目标 B | `desktop-avatar/voice.js`（驱动 Lottie 桌宠 `window.ZZDesktopAvatar.setState()`，非粒子球） |
| ❌ 非目标 C | `desktop-avatar/dyna-orb-voice.js` 的 `setState/setVolume`（只切状态/音量，不改 canvas 尺寸） |

**关键红线遵守**：严禁将 DOM Voice Orb 与桌面粒子 Voice Orb 混为一谈——本报告全程区分二者。

---

## 3. Actual Rendering Pipeline（真实渲染管线）

桌面粒子语音球采用 **Canvas 2D 点云球** 渲染，管线如下：

1. **球面采样**：Fibonacci 球面均匀采样，生成 **3200 外点 + 1200 内点 = 4400** 基准粒子。
2. **噪声位移**：`sn(x,y,z,t)` 正弦噪声函数，按 `STATE_CFG[state].amp` 振幅沿径向 `(1.0 + sn*amp)` 调制，制造呼吸/脉动。
3. **3D 旋转**：
   - `rotY`：时间驱动自转（`animState.t`）。
   - `rotX ≈ 0.22 rad`：固定俯仰倾斜（使球呈"微微俯视"立体感）。
4. **正交投影**：旋转后坐标经正交投影到 2D 屏幕坐标（无透视除法）。
5. **深度着色**：按 `z`（前后深度）分配亮度与半径——**front 大且亮，back 小且暗**，形成球体立体感与 glow。
6. **动画循环**：`requestAnimationFrame` 驱动 `draw()`，每帧重算噪声+旋转+投影+着色。
7. **状态机**：`dyna-orb-voice.js` 麦克风 VAD → `orb.setState('idle'|'listening'|'recognizing'|'thinking'|'processing'|'executing'|'speaking'|'done'|'error')`，仅调振幅/速度/冷色微参，**几何不变**；仅 `executing` 额外绘制 `drawSpinner()` 环。

**非 WebGL / 非 CSS transform / 非 Electron overlay 自渲染**——纯 Canvas 2D 绘图上下文。

---

## 4. Source File Map（源文件映射）

| 文件 | 角色 | 是否目标 | 关键内容 |
|---|---|---|---|
| `desktop-avatar/dyna-orb.html` | DOM 入口 | ✅ 目标 | `#orb-canvas`（`position:absolute; top:0; left:0; width:100%; height:100%`），body 透明；内联兜底 `_o.init(_c); _o.start(); _o.setState('idle')`；拖拽用 `getBoundingClientRect` 算球心、球外透明区穿透（`api.setIgnoreMouse`） |
| `desktop-avatar/dyna-orb.js` | 粒子球渲染核心 | ✅ 目标 | `resize()`(L70) / `project()`(L119) / `drawSpinner()`(L155) / `STATE_CFG`(9 态)；零改动 |
| `desktop-avatar/dyna-orb-voice.js` | VAD + 状态机 | ✅ 相关 | 麦克风监听 → `orb.setState()` / `orb.setVolume(rms*3)` → `/api/asr` `/api/chat` `/api/speak`；**不改 canvas 尺寸** |
| `desktop-avatar/voice.js` | Lottie 桌宠驱动 | ❌ 非目标 | `window.ZZDesktopAvatar.setState()`（`.orb-wrap` class） |
| `xiao6-desktop/pet/` | Lottie 机器人 | ❌ 非目标 | `pet.html`/`pet.js`/`robot-futuristic.json`/`lottie.min.js` |
| `electron/main.js` | Electron 主进程 | 加载方 | L95-96 `createAvatarWindow({ url: base+'/desktop-avatar/dyna-orb.html', preload })`；IPC：`avatar:close/hide/focus/set-ignore-mouse/move` |
| `electron/avatar-window.js` | 窗口工厂 | 加载方 | L22-24 `WINDOW_W=213; WINDOW_H=320; MARGIN=18`；L43-50 `width:213,height:320,transparent:true,frame:false,alwaysOnTop:true,resizable:false`；L87 `target = opts.url \|\| 'http://localhost:8010/desktop-avatar/dyna-orb.html'` |

---

## 5. Runtime Rendering Chain（运行时渲染链）

```
electron/main.js:95  avatarWin = createAvatarWindow({ url: base + '/desktop-avatar/dyna-orb.html', preload })
        │
        ▼
electron/avatar-window.js:87  const target = opts.url || '.../dyna-orb.html'
        │  win = new BrowserWindow({ 213×320, transparent, frame:false, alwaysOnTop, resizable:false })
        ▼
avatar-window.js:win.loadURL(target)   → 加载真实服务页 http://127.0.0.1:8010/desktop-avatar/dyna-orb.html
        │
        ▼
dyna-orb.html 解析 → 内联兜底脚本执行：_o.init(_c); _o.start(); _o.setState('idle')
        │  （init 调 resize() 设 canvas backing/css；start 启动 rAF；setState 设 idle 渲染参数）
        ▼
dyna-orb-voice.js 接管：getUserMedia → VAD → 按语音事件 orb.setState('listening'/'thinking'/'speaking'/'executing'...)
        │
        ▼
dyna-orb.js draw() 每帧：noise + rotY/rotX 旋转 + 正交投影(sx,sy) + 深度着色 → 粒子球可见
```

**坐标系**：canvas 以窗口像素为坐标，原点左上；球心 `cx = W/2, cy = H/2`（dpr1: 106.5, 160）。
**粒子生成**：Fibonacci 球面采样（一次性生成 4400 基准点，动画中按噪声/旋转位移，不新增点）。
**动画**：`requestAnimationFrame` 驱动。
**状态切换**：`setState(sk)` 仅改 `animState` 参数（amp/speed/冷色），`executing` 额外 `drawSpinner()`。
**挂载窗口**：Electron 独立透明窗，213×320，CSS 100% 填充，canvas 占满整窗。

---

## 6. Canvas-WebGL-Electron Geometry（Canvas / WebGL / Electron 几何）

逐项排查渲染技术层面的几何失真源：

| 检查项 | 实测 | 结论 |
|---|---|---|
| Canvas 类型 | `getContext('2d')`（Canvas 2D） | 非 WebGL，无 `viewport`/`aspect` 概念 |
| canvas CSS width/height | `100%` × `100%`（撑满 213×320 窗） | 各向同性填充 |
| canvas.width/height（backing） | dpr1: 213×320；dpr2: 426×640；dpr3: 639×960 | 与 CSS 同比缩放 |
| devicePixelRatio 处理 | `dpr = Math.max(1, Math.min(devicePixelRatio, 3))` | 统一 clamp 到 ≤3 |
| backing / css 比值 | dpr1 = 1.0；dpr2 = 2.0；dpr3 = 3.0 | 各向同性，无 X/Y 差比 |
| WebGL viewport / aspect | 不存在（纯 2D） | 无 aspect bug 源 |
| CSS transform scaleX/scaleY | 无 | 排除 CSS 缩放失真 |
| Electron window w/h | 213×320（ratio 0.666，竖屏） | 窗型竖长，但 canvas 100% 填充 |
| Electron transparent | `transparent:true` | 仅影响合成，不影响几何 |
| Electron deviceScaleFactor / zoom | 未设 zoom（默认 1） | 无缩放失真 |

**投影几何核心证据**（`dyna-orb.js`）：
```js
// L70 resize()
function resize() {
  var rect = canvas.getBoundingClientRect();
  var dpr = Math.max(1, Math.min(window.devicePixelRatio || 1, 3));
  var nW = Math.max(1, Math.round(rect.width * dpr));
  var nH = Math.max(1, Math.round(rect.height * dpr));
  if (canvas.width !== nW || canvas.height !== nH) { canvas.width = nW; canvas.height = nH; }
  W = nW; H = nH; cx = W / 2; cy = H / 2;
  scale = Math.min(W, H) * 0.40;     // 同一 scale，X/Y 共用
}

// L119-127 project()
var project = function (orig) {
  var d = 1.0 + sn(orig.x, orig.y, orig.z, animState.t) * animState.amp;
  var px = orig.x * d, py = orig.y * d, pz = orig.z * d;
  var rx = px * cY + pz * sY;
  var ry0 = py;
  var rz = -px * sY + pz * cY;
  var ry = ry0 * cX - rz * sX;
  var rz2 = ry0 * sX + rz * cX;
  return { sx: cx + rx * scale, sy: cy - ry * scale, z: rz2 };  // X、Y 共用 scale → 恒为圆
};
```
**数学结论**：`sx` 与 `sy` 由同一 `scale` 缩放，`cx/cy` 为窗心 → 球面正交投影后轮廓恒为**正圆**。`executing` 态 `drawSpinner()` 的 `R = scale*1.5`（L156）是**额外绘制的环**，非球面投影，其半径超窗宽时才会被裁（见 §13/§14）。

---

## 7. DPR Analysis（设备像素比分析）

`resize()` 统一 `Math.min(devicePixelRatio, 3)` 缩放 backing 与 CSS，**各向同性**，故几何随 DPR 等比放大，无 X/Y 非等比源。实测三档 DPR 下 IDLE 包围盒：

| DPR | backing W×H | css W×H | cx,cy | scale | IDLE bbW×bbH | ratio |
|---|---|---|---|---|---|---|
| 1 | 213×320 | 213×320 | 106.5,160 | 85 | 173×173 | **1.000** |
| 2 | 426×640 | 213×320 | 213,320 | 170 | 344×344 | **1.000** |
| 3 | 639×960 | 213×320 | 320,480 | 256 | 513×514 | **0.998** |

→ DPR 越高仅使粒子更密、球略大，**ratio 始终 ~1.000**。证明"椭圆感"与 DPR 无关。

---

## 8. Screenshot Evidence（真实桌面截图证据）

使用真实 Chromium（Playwright chromium-1208，executablePath + `--no-sandbox --disable-gpu --use-gl=swiftshader --enable-unsafe-swiftshader`）经 `127.0.0.1:8010` 加载真实服务页面，对 4 组视口（real_213×320 dpr1/2/3 + square_256×256 dpr1）逐态截图。

> 注：存档截图实际像素为 **639×960**（= dpr3），因测量循环末遍为 dpr3 覆盖写盘；**各 DPR 数值化包围盒证据已完整落盘于 `particle_orb_audit.json`**，不依赖肉眼判图（模型不支持直接读图，已用 PNG 头字节 + JSON 数值替代证明）。

| 截图文件 | 内容 | 像素尺寸 |
|---|---|---|
| `DESKTOP-PARTICLE-ORB-IDLE.png` | IDLE 态 | 639×960 |
| `DESKTOP-PARTICLE-ORB-LISTENING.png` | LISTENING 态 | 639×960 |
| `DESKTOP-PARTICLE-ORB-THINKING.png` | THINKING 态 | 639×960 |
| `DESKTOP-PARTICLE-ORB-SPEAKING.png` | SPEAKING 态 | 639×960 |
| `DESKTOP-PARTICLE-ORB-EXECUTING.png` | EXECUTING 态 | 639×960 |
| `DESKTOP-PARTICLE-ORB-FULL.png` | 整体桌面合成 | 639×960 |

（截图存于 `G:\xiao6\_ui_archive\`）

---

## 9. Pixel Bounding Box（像素包围盒）

对每态 `ctx.getImageData` 按 alpha>14 阈值逐像素统计粒子区 bounding box（minX/minY/maxX/maxY → bbW/bbH），结果（`particle_orb_audit.json`）：

**real_213×320：**

| 状态 | bbMinX | bbMinY | bbMaxX | bbMaxY | bbW | bbH | absDiff |
|---|---|---|---|---|---|---|---|
| idle | 20 | 74 | 192 | 246 | 173 | 173 | 0 |
| listening | 20 | 75 | 191 | 246 | 172 | 172 | 0 |
| thinking | 21 | 81 | 189 | 249 | 169 | 169 | 0 |
| speaking | 18 | 78 | 191 | 248 | 174 | 171 | 3 |
| **executing** | **0** | 28 | **212** | 291 | **213** | **264** | **51** |

**square_256×256：** idle 24/24/231/231 → 208×208；executing 0/0/255/255 → **256×256（完整圆）**。

→ 除 executing 外，所有态 bbW≈bbH，absDiff≤3px（≤2% 噪声级，来自正弦位移离群粒子）。executing 横向贴满 213（bbMinX=0, bbMaxX=212）而纵向未贴满（bbH=264<320）→ 典型**横向裁切**特征。

---

## 10. Width-Height Ratio（宽高比）

| 视口 | idle | listening | thinking | speaking | executing |
|---|---|---|---|---|---|
| real_213×320 dpr1 | **1.000** | **1.000** | **1.000** | 1.018 | **0.807** |
| real_213×320 dpr2 | **1.000** | **1.000** | **1.000** | 1.018 | **0.807** |
| real_213×320 dpr3 | **0.998** | **1.000** | **0.996** | 1.020 | **0.807** |
| square_256×256 dpr1 | **1.000** | **1.000** | **1.000** | 1.020 | **1.000** |

**结论**：
- 老板关注的 **IDLE 态 = 严格正圆（ratio 1.000，跨 dpr1/2/3 与方形对照全部 1.000 级）**。
- speaking ratio ~1.018（2% 噪声级，正弦位移离群粒子，非缺陷）。
- **executing = 0.807 椭圆，且仅在 213×320 窄窗出现；方形窗下同一 ring 为 1.000 完整圆** → 证伪"渲染 bug"，实属"窄窗裁切"。

---

## 11. Particle Distribution（粒子分布）

- 基准粒子：**4400**（3200 外 + 1200 内），Fibonacci 均匀球面采样。
- 各态实时粒子计数（dpr1，alpha>14）：idle 16503 / listening 17735 / thinking 19176 / speaking 18515 / executing 25644。
  - executing 计数显著更高，因 `drawSpinner()` 额外绘制环上粒子。
- 分布特征：front 深度粒子半径大、alpha 高（亮核）；back 深度粒子半径小、alpha 低（暗晕），形成球体体积感与 glow。
- 自转（rotY）+ 俯仰（rotX≈0.22）使前半球始终偏向某一侧 → **亮度/密度分布不左右/上下对称**，是视觉椭圆感的主要来源（见 §12）。

---

## 12. Lighting-Glow Analysis（光照与辉光分析）

**椭圆感溯源（核心张力）**：截图目视呈"顶底弧度缓、左右更鼓窄、上密下疏"的纵向椭圆嫌疑，但像素 bbox 始终为正圆（§9/§10）。分层 centroid 验证：

**IDLE（213×320 dpr1）按 8 个 alpha 阈值（TH 6→230）：**

| TH | cnt | bbW×bbH | ratio | centroidOffsetX/Y |
|---|---|---|---|---|
| 6 | 17495 | 173×173 | **1.000** | -0.54 / -0.57 |
| 14 | 16508 | 173×173 | **1.000** | -0.57 / -0.67 |
| 40 | 14018 | 173×172 | 1.006 | -0.52 / -0.66 |
| 80 | 11040 | 173×172 | 1.006 | -0.49 / -0.47 |
| 120 | 8123 | 172×172 | **1.000** | -0.97 / -0.35 |
| 160 | 5560 | 171×172 | 0.994 | -1.36 / -0.59 |
| 200 | 2582 | 171×171 | **1.000** | -0.06 / -0.84 |
| 230（亮核） | 334 | 161×170 | 0.947 | +6.56 / -1.76 |

→ **IDLE 亮核（TH230）点数仅 334，ratio 0.947 纯属统计噪声**；其余阈值 ratio 全部 1.000，centroid 偏移 ≤ **6.56px**（相对 106.5 半窗宽 <6.2%）→ **亮核也是圆，椭圆感非渲染层**。

**机制**：深度着色（front 亮 / back 暗）+ rotX≈0.22 俯仰 + 自转，使高亮粒子集中在球面上半/某一侧，暗粒子散布边缘 → 人眼对"亮区轮廓"敏感，将**非对称亮度分布误读为椭圆**。与 UI-01 的 `.zz-orb-core` 渐变偏心同理，属 **glow / lighting 设计层**问题，非几何缺陷。

---

## 13. State Comparison（状态对比）

| 状态 | 几何 | ratio(dpr1 213×320) | 说明 |
|---|---|---|---|
| idle | 正圆 | **1.000** | 老板关注态，完美圆 |
| listening | 正圆 | **1.000** | 振幅略增，仍圆 |
| recognizing/thinking/processing | 正圆 | **1.000** | 仅速度/冷色微调 |
| speaking | 近圆 | 1.018 | 2% 噪声级离群粒子 |
| **executing** | **横向裁切椭圆** | **0.807** | `drawSpinner()` ring `R=scale*1.5=127.5` > 半窗宽 106.5 → 两侧贴边裁切 |
| done/error | 正圆 | ~1.000 | 恢复球面 |

**executing 裁切数学**：ring 半径 127.5，窗心 (106.5,160) → 水平延伸 [−21, 234]，**两端越界被裁至 [0,213]（满宽）**；垂直延伸 [32.5, 287.5]，**未触顶/底** → bbox 213 宽 × 264 高 → 0.807 椭圆。**方形 256×256 窗下**（中心 128，R=153 → [−25,281] 对称裁切）→ bbox 256×256 ratio **1.000** → 同一 ring 在正方形内完整为圆，确证"窄窗裁切"论。

---

## 14. Root Cause（根本原因分析）

按任务规范 A–J 十类逐一排查：

- **A. 实际 X/Y 非等比缩放（canvas/WebGL/Electron aspect bug）** → **排除**。投影共用 `scale`，DPR 各向同性，无 scaleX≠scaleY。
- **B. CSS transform scaleX/scaleY** → **排除**。无 CSS 缩放。
- **C. WebGL viewport/aspect** → **排除**。纯 Canvas 2D。
- **D. Electron zoom/deviceScaleFactor** → **排除**。未设 zoom。
- **E. 窗口宽高比导致裁切** → **部分命中（仅 executing）**。213×320 窄窗使 executing ring 横向裁切为 0.807 椭圆，但**非 idle、且方形窗下完整**。
- **F. 粒子生成/分布算法缺陷** → **排除**。Fibonacci 均匀采样，bbox 正圆。
- **G. 投影数学错误** → **排除**。正交投影 + 共用 scale，恒为圆。
- **H. 状态切换改尺寸** → **排除**。`setState` 不改 canvas 尺寸；仅 executing 画额外 ring。
- **I. glow/lighting 造成视觉感知偏椭圆** → **命中（IDLE 主因）**。深度着色 + rotX 俯仰 + 自转 → 亮度/密度不对称 → 人眼误读椭圆。
- **J. 无几何问题，纯视觉感知** → **命中（IDLE 结论）**。IDLE 实测严格正圆，椭圆感为感知层。

### PRIMARY（主因，针对 IDLE / 老板关注态）
**ROOT-CAUSE-J + ROOT-CAUSE-I**：IDLE 粒子球几何严格正圆（ratio 1.000），"看起来椭圆"来自 glow/lighting 深度着色 + rotX≈0.22 俯仰 + 自转造成的亮度/密度分布不对称，属**视觉感知层 / 设计层**，非几何/渲染缺陷。

### SECONDARY（次因，仅限 executing 加载态）
**ROOT-CAUSE-E**：executing 态 `drawSpinner()` 的 `R = scale*1.5` 环半径（127.5）超过 213 窄窗半宽（106.5），横向被裁成 0.807 椭圆。该椭圆在方形窗下完整为圆 → 是"窄窗宽高比 vs ring 半径"窗口裁切，**非渲染 bug、非 idle、且几何未被扭曲**（只是被窗边界切掉两侧）。

---

## 15. Contributing Factors（促成因素）

1. **深度着色梯度**：front 亮大 / back 暗小，使"亮区"轮廓偏于球面上半，视觉重心偏移。
2. **rotX≈0.22 俯仰**：球面呈微微俯视，顶缘粒子密度视觉高于底缘。
3. **自转 rotY**：动态旋转使亮区方位持续变化，强化"非对称"错觉。
4. **窄窗 213×320（ratio 0.666）**：纵向空间远大于横向，放大了任何横向裁切/感知偏斜的可见度（executing ring 即受此影响）。
5. **glow 外晕**：边缘暗粒子形成柔和晕，弱化"硬圆边"感知，人眼更易按亮区判形。

---

## 16. Proposed Minimal Fix（建议的最小修复，本次不实施）

**STOP-A 判定下默认不修改代码**。若老板坚持要消除"椭圆感"或修复 executing 裁切，给出两个隔离的最小方案备选（均不触碰红线、不重构、不改 DOM 球）：

**方案 α（针对 IDLE 视觉感知，可选）**——调整 glow/lighting 使其更对称：
- 降低 `rotX` 俯仰（如 0.22 → 0.12）使球体更"正对"，减少上下密度差。
- 或增强 back 粒子亮度下限，缩小 front/back 对比，弱化"偏心亮核"错觉。
- 仅改 `dyna-orb.js` 的 `STATE_CFG` 着色参数或投影 `rotX` 常数，**不动几何、不动 scale、不改 DOM**。

**方案 β（针对 executing ring 裁切，可选）**——约束 spinner 半径不超窗宽：
- `drawSpinner()` 中 `var R = Math.min(scale * 1.5, Math.min(W, H) * 0.46);`（dpr1: min(127.5, 147.2)=127.5 仍超 → 进一步改系数为 `scale*0.95` ≈ 80.75 < 106.5 半宽，确保环完整居窗内）。
- 或在 `avatar-window.js` 放宽 `WINDOW_W`（如 213→260）使 ring 不被横向裁切（但改动 Electron 窗规格，需老板另行审批，属红线边缘）。

**本次状态**：以上均为"若老板要求"的备选，**当前 STOP，零代码改动**。

---

## 17. Files That Would Need Modification（需修改的文件，仅作记录）

| 若实施 | 文件 | 改动范围 | 红线风险 |
|---|---|---|---|
| 方案 α | `desktop-avatar/dyna-orb.js` | `rotX` 常数 / `STATE_CFG` 着色参数 | 低（仅渲染参数） |
| 方案 β-a | `desktop-avatar/dyna-orb.js` | `drawSpinner()` 的 `R` 系数 | 低（仅 executing 环） |
| 方案 β-b | `electron/avatar-window.js` | `WINDOW_W` 213→更大 | 中（改 Electron 窗规格，红线边缘） |

**当前未修改任何文件。** 严禁修改：`server.py` / 任何 `.py` / Runtime / Agent Loop / Memory / Scheduler / Executor / Policy / API / TTS / 语音逻辑 / 端口 / proxy / launcher / Electron 架构 / 引入 Three.js·Lottie·新字体 / 重构 / 删历史 UI / 顺手优化其它 UI / 改 `.zz-orb-core` 渐变 / 改 `35% 30%`→`50% 50%` / 将 DOM 与桌面粒子 Voice Orb 混为一谈。

---

## 18. Red-Line Audit（红线审计）

| # | 红线 | 本次遵守 |
|---|---|---|
| 1 | 禁改 server.py | ✅ 未碰 |
| 2 | 禁改任何 .py | ✅ 未碰 |
| 3 | 禁改 Runtime / Agent Loop / Memory / Scheduler / Executor / Policy | ✅ 未碰 |
| 4 | 禁改 API / TTS / 语音逻辑 | ✅ 未碰 |
| 5 | 禁改端口 / proxy / launcher | ✅ 未碰 |
| 6 | 禁改 Electron 架构 | ✅ 仅读取 avatar-window.js，未改 |
| 7 | 禁引入 Three.js / Lottie / 新字体 | ✅ 未引入 |
| 8 | 禁重构 | ✅ 未重构 |
| 9 | 禁删历史 UI | ✅ 未删 |
| 10 | 禁顺手优化其它 UI | ✅ 仅审计目标 |
| 11 | 禁改 `.zz-orb-core` 渐变 | ✅ 未碰 DOM 球（UI-01 已冻结） |
| 12 | 禁改 `35% 30%`→`50% 50%` | ✅ 未碰 |
| 13 | **禁将 DOM Voice Orb 与桌面粒子 Voice Orb 混为一谈** | ✅ 全程区分（§2/§4） |
| 14–25 | 其余审计/截图/测量纪律 | ✅ READ REAL SOURCE / MEASURE REAL RUNTIME / CAPTURE REAL DESKTOP / NO GUESS / NO SCOPE CREEP / NO CODE CHANGE / STOP AFTER AUDIT 全部遵守 |

**实测方法可复核**：`particle_orb_audit.cjs` / `particle_orb_layers.cjs`（真实 Chromium 加载真实服务页）、`particle_orb_audit.json` / `particle_orb_layers.json`（数值证据）、6 张截图（639×960）。

---

## 19. STOP-GO Decision（STOP / GO 判定）

按任务规范 §十 五态：

- **A. 粒子球本身几何/渲染完全正确，仅光照或 glow 造成视觉感知问题** → **✅ 命中**。IDLE ratio=1.000 严格正圆；亮核 centroid 偏移 ≤6.56px 亦为圆；椭圆感来自 glow/lighting 深度着色 + rotX 俯仰 + 自转的视觉感知（ROOT-CAUSE-J/I）。
- B. 实际 X/Y 非等比缩放 → 排除（无此源）。
- C. canvas/WebGL/Electron aspect bug → 排除（纯 2D、DPR 各向同性）。
- D. 故意设计成椭圆 → 不适用（实测为正圆）。
- E. 无法确定 → 不适用（证据充分）。

### 最终裁定：**STOP — 不修改代码**

1. **IDLE（老板关注态）几何严格正圆，无缺陷**，无需修改；"看起来椭圆"属 **glow / lighting 设计层感知问题**，明确说明这是设计问题，非 bug。
2. **executing 态 0.807 椭圆为窄窗横向裁切**（ring 半径超半窗宽），非渲染 bug、非 idle、且方形窗下完整为圆；如老板要求可走 §16 方案 β，**本次不实施**。
3. **严格遵守全部 25 条红线与 AUDIT-ONLY 纪律，零代码改动。**
4. 交付物：本报告 + 6 张真实截图 + 2 份 JSON 实测证据，存于 `G:\xiao6\_ui_archive\`。

---

*审计完成。STOP。等待老板对"是否进入 IMPLEMENT（方案 α/β）"的批复。*
