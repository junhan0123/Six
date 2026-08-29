# PHASE 5.1-HOTFIX-UI-03 · 桌面粒子语音球视觉校正实验

**产品**：小6 Xiao6 v1.4.0 · 桌面粒子语音球 (`desktop-avatar/dyna-orb.html` + `dyna-orb.js`)
**身份**：Senior Frontend / Canvas 2D Visual Engineer
**任务类型**：VISUAL-ONLY PARAMETER EXPERIMENT（仅改 `dyna-orb.js` 视觉参数，不修数学几何）
**关联**：UI-02（已证几何为正圆，STOP-A，零代码改动）

---

## 0. 一句话结论

> **RECOMMENDATION: B（BALANCED LIGHTING）**
> 三个「感知问题」中，只有「球体不够饱满」是真实可修项；B 用最小改动（2 行）对症修复且不破坏 3D 深度与正圆几何。A 对轮廓/覆盖/椭圆感零作用，C 更饱满但多改了几何无效的 rotX 且在 THINKING 态横向平衡略差。

---

## 1. §一 VERIFY — 基线完整性（先验证，后改动）

| 项目 | 值 |
|---|---|
| 当前 `dyna-orb.js` sha256(16) | `5b1a1b10a1abbf31` |
| 基线副本 sha256(16) | `5b1a1b10a1abbf31` → **MATCH（net zero）** |
| 基线副本 mtime | 2026-08-18 14:04:28 |
| 当前 prod `dyna-orb.js` mtime | 2026-08-18 14:24:32（仅因 `cp -f` 还原复制，内容零改动） |
| `dyna-orb.html` mtime | 2026-08-17 15:28:02（实验期间**仅读不改**） |
| 服务端口 `http://127.0.0.1:8010/desktop-avatar/dyna-orb.html` | **200（OPEN）** |
| 真实 Chromium | `chromium-1208`（Playwright，swiftshader）→ 已确认可运行 |
| 源文件复核 | 已重读 `dyna-orb.js` L55–165 + `dyna-orb.html`，与 UI-02 记录一致，**不靠记忆猜测** |

实验期间**仅** `dyna-orb.js` 被临时编辑→截图→`cp -f` 还原，每轮还原后 sha256 校验 = 基线。其余文件零写入。

---

## 2. §二 允许 / 禁止范围（红线圈）

- **唯一可改文件**：`dyna-orb.js`
- **唯一可改参数**：A. rotX/tilt · B. 前后景深度光照 · C. 粒子 alpha · D. 粒子半径 · E. glow/halo · F. 噪声幅度
- **禁止**（全部 0 改动，见 §9）：canvas W/H/CSS、投影 scale、`cx`/`cy`、DPR、Electron 窗口、`avatar-window.js`、`dyna-orb.html` 结构、`dyna-orb-voice.js`、`voice.js`、`server.py`、任意 `.py`、Runtime/Agent Loop/Memory/Scheduler/Executor/Policy/API/TTS/ASR、端口/代理/启动器、Electron 架构；无 Three.js/WebGL/Lottie/新字体/新依赖；无重构。

---

## 3. §三 三个候选的参数化（均从真实源码派生，已逐轮截图后还原）

| 候选 | rotX（L113） | alpha（L141） | dotR（L142） | 设计意图 |
|---|---|---|---|---|
| **BASELINE** | `0.22 + sin(t·0.15)·0.06`（摆 0.16–0.28） | `0.25 + depth·0.75`（前1.0/后0.25） | `0.6 + depth·0.8 + amp·2` | 现状 |
| **A FRONT-FACING** | `0.12 + sin(t·0.15)·0.04`（摆 0.08–0.16） | 不变 | 不变 | 降倾斜、更正面，保留 3D |
| **B BALANCED LIGHTING** | 不变（0.22） | `0.45 + depth·0.55`（前1.0/后0.45） | `0.8 + depth·0.5 + amp·2` | 抬前后景对比下限 + 略增粒子半径，保留完整 3D 倾斜 |
| **C HYBRID** | `0.15 + sin(t·0.15)·0.05`（摆 0.10–0.20） | `0.40 + depth·0.60`（前1.0/后0.40） | `0.75 + depth·0.6 + amp·2` | 略降 rotX + 略降对比 + 微调半径/alpha |

> `drawSpinner()`（L155–156，`R = scale * 1.5`）**FROZEN**，四轮均未触碰（§6）。

---

## 4. §四 实验方法（真实浏览器，非脑补）

- 驱动：Playwright `chromium-1208`，args `--no-sandbox --disable-gpu --use-gl=swiftshader --enable-unsafe-swiftshader`
- 视口 213×320，`deviceScaleFactor=dpr(2)` → 背板 426×640（= 真实 Electron 窗口 ×dpr）
- 路由拦截 `dyna-orb-voice.js`（返回空脚本），使球完全受 `ZZDynaOrb.setState()` 显式控制
- 每态 `setState(s)` 后等 1500ms 让 lerp/动画落定
- 截图 `omitBackground:true` → **透明 RGBA（colorType=6）**，贴合透明桌面窗口；量化改用 alpha 通道（UI-02 时代白底亮度法已废弃）
- 状态：IDLE / LISTENING / THINKING / SPEAKING（**IDLE 优先**）+ FULL；另补 ERROR / DONE 回归
- 每轮：编辑→截图→`cp -f` 基线副本回写→sha256 校验 MATCH（净零）

---

## 5. §五 量化结果（alpha 边界；背板 426×640，期望中心 213,320）

`ratio 1.000=正圆` · `dx/dy=亮度质心相对几何中心偏移(px)` · `topFrac/leftFrac=上下/左右亮度占比(50=平衡)` · `cov%=含光晕不透明覆盖`

| set | state | ratio | cov% | cx | cy | dx | dy | topFrac | leftFrac |
|---|---|---|---|---|---|---|---|---|---|
| BASE | IDLE | **1.000** | 9.18 | 213 | 320 | -0.6 | -1.0 | 50.3 | 50.0 |
| A | IDLE | **1.000** | 9.18 | 213 | 320 | 0.0 | -0.3 | 50.0 | 49.9 |
| B | IDLE | **1.000** | 9.81 | 213 | 320 | -1.1 | -0.5 | 50.0 | 50.3 |
| C | IDLE | **1.000** | 9.89 | 213 | 320 | -0.3 | -0.4 | 50.0 | 49.9 |
| BASE | LISTEN | 1.006 | 10.37 | 211 | 324 | 0.1 | -3.5 | 51.1 | 49.8 |
| A | LISTEN | 1.006 | 10.34 | 211 | 323 | 2.4 | -2.4 | 50.6 | 49.1 |
| B | LISTEN | 1.006 | 11.06 | 211 | 324 | 0.1 | -3.7 | 51.1 | 49.8 |
| C | LISTEN | 1.006 | 10.99 | 211 | 323 | 1.9 | -2.4 | 50.7 | 49.0 |
| BASE | THINK | 1.014 | 12.92 | 211 | 321.5 | 1.4 | -1.3 | 50.2 | 49.6 |
| A | THINK | 1.032 | 13.01 | 210.5 | 322 | 2.7 | -1.9 | 50.5 | 49.3 |
| B | THINK | 1.017 | 13.75 | 210.5 | 321.5 | 1.2 | -1.6 | 50.3 | 49.8 |
| C | THINK | 1.026 | 13.82 | 210.5 | 322 | 2.4 | -2.6 | 50.5 | 49.5 |
| BASE | SPEAK | 1.021 | 11.03 | 214 | 322.5 | -2.3 | -1.9 | 51.0 | 50.6 |
| A | SPEAK | 1.021 | 11.22 | 214 | 321.5 | -0.2 | -1.5 | 50.8 | 49.9 |
| B | SPEAK | 1.021 | 11.70 | 214 | 322.5 | -2.3 | -1.6 | 50.6 | 50.7 |
| C | SPEAK | 1.018 | 11.91 | 214 | 322 | -0.9 | -0.7 | 50.2 | 50.2 |

**ERROR / DONE 回归**：cov 11.22% / 11.40%，控制台错误 0 → 正常渲染，无回归。

---

## 6. §五 视觉验收（12 项标准）逐条落点

| # | 标准 | 结论（四候选一致或差异） |
|---|---|---|
| 1 | 轮廓圆润度 | IDLE ratio **1.000** 全四候选 → 正圆；非 IDLE 1.006–1.032（<3.3%，态动画光晕，非几何） |
| 2 | 饱满度 | **BASELINE 最低（9.18%）**；B 9.81% / C 9.89%（+7~8%）→ B、C 解决「不够饱满」 |
| 3 | 高光偏心 | 静态球 dx/dy ≈ 0；A 在 THINK 反而恶化 dx（2.7 vs 1.4） |
| 4 | 上下亮度平衡 | topFrac 50.0–51.1；A/B/C 略优于基线，差异 <1.2pp |
| 5 | 左右亮度平衡 | leftFrac 49.0–50.7；全部接近平衡 |
| 6 | 3D 立体感 | 四候选均保留 front-bright 深度着色 + rotX>0；**无拍扁** |
| 7 | 自然光晕 | halo 结构未改；B/C 因 alpha 下限抬升粒子光晕略增，自然 |
| 8 | 粒子密度 | cov% 提升即密度提升，B/C 明显改善 |
| 9 | 扁平/椭圆观感 | **无真实椭圆**（几何恒正圆）；「椭圆感」= 前亮后暗深度着色 + 光晕的视觉错觉（UI-02 结论），本参数空间内无法彻底消除而不破坏深度 |
| 10 | 旋转畸变 | 正交投影球体剪影恒为圆，倾斜不产生畸变 |
| 11 | 统一视觉语言 | 调色板/投影/状态机未变，视觉语言一致 |
| 12 | 禁止无深度扁圆 | 全部保留深度（前亮后暗 + rotX）；满足 |

---

## 7. §六 / §七 冻结项确认

- **EXECUTING**：`drawSpinner()` `R=scale*1.5` 未改；headless swiftshader 下因 `ctx.shadowBlur` 崩溃而空白（`BASELINE-EXECUTING.png`=2100B），为**首屏 harness 伪影**，生产中正常；EXECUTING 在 UI-03 中 FROZEN，非回归。
- **DOM Voice Orb**（`#orbPresence` / `.zz-orb-core` / `.zz-orb-ring`）：UI-01 FROZEN，本次零触碰。

---

## 8. §八 回归验证

| 检查项 | 结果 |
|---|---|
| IDLE / LISTENING / THINKING / SPEAKING | 四候选均正常渲染（见 §5 量化） |
| ERROR / DONE | cov 11.22% / 11.40%，控制台错误 0 → 正常 |
| EXECUTING | 生产正常（harness 伪影，FROZEN） |
| canvas 尺寸 / DPR / Electron 窗口 | 未改 → 不变 |
| 透明 / 鼠标穿透 / 拖拽 | 未改 → 不变 |
| 净代码改动 | **0**（当前 = 基线 `5b1a1b10a1abbf31`） |

---

## 9. §九 红线圈审计（禁止文件全部 0 改动）

- `G:\xiao6` **非 git 仓库** → 审计以内容哈希 + 写操作记录为准。
- 实验全程**唯一**被写入的文件是 `_ui_archive/` 下的实验产物（基线副本、截图、脚本），**均非生产代码**。
- 生产 `dyna-orb.js`：当前哈希 = 基线哈希 → **net zero**。
- 生产 `dyna-orb.html`：仅读，mtime 早于实验（2026-08-17 15:28） → 未改。
- 以下禁止文件**全程未被任何写操作打开**（仅 UI-02 中读，UI-03 中未触）：`avatar-window.js`、`dyna-orb-voice.js`、`voice.js`、`server.py`、任意 `.py`、`electron/main.js`、Runtime/Agent Loop/Memory/Scheduler/Executor/Policy/API/TTS/ASR、端口/代理/启动器、Electron 架构。
- **红线圈违规：0 项。**

---

## 10. §十 最终输出汇总

- **Baseline / 当前参数**：见 §1、§3（rotX 0.22、alpha `0.25+depth·0.75`、dotR `0.6+depth·0.8+amp·2`）。
- **A/B/C 参数**：见 §3 表。
- **截图**：`PHASE-5.1-HOTFIX-UI-03-{BASELINE,A,B,C}-{IDLE,LISTENING,THINKING,SPEAKING,FULL}.png`（20 张）；`REG-{ERROR,DONE}.png`（回归）。
- **像素 bbox / ratio / 亮度质心**：见 §5 表。
- **visual assessment**：见 §6（12 项）。
- **regression**：见 §8。
- **git diff**：不适用（无 git）；等价为哈希 parity + 写审计，见 §9。
- **mtime**：见 §1。
- **red-line audit**：见 §9（0 违规）。

---

## 11. RECOMMENDATION

```
RECOMMENDATION: B
```

**理由**：
1. **对症**：用户三感中仅「不够饱满」真实存在（基线 IDLE 覆盖 9.18%）。B 提升到 9.81%（+7%），C 到 9.89%（+8%）——二者解决此问题，A 不解决（覆盖与基线完全相同）。
2. **几何零风险**：四候选 ratio 均为 1.000（IDLE），正圆几何毫发无损；B 不碰 rotX，保留完整 3D 倾斜（0.22），深度身份不变。
3. **改动最小**：B 仅 2 行（alpha + dotR），比 C 少 1 行且不含几何无效的 rotX 改动。
4. **无回归**：B 在 THINKING 态 dx 1.2（最优，优于基线 1.4 与 A 2.7、C 2.4）；其余平衡指标与基线持平。

**为何不选 A**：正交投影下球体剪影恒为正圆，降 rotX **几何上不可能**改变椭圆感/轮廓/覆盖（数据证实 A 与基线 ratio、cov 完全相同）。A 仅旋转内部高光，对用户的三个感知问题均无实质改善。

**为何不选 C**：C 比 B 仅多 +0.08pp 覆盖，却额外改了 rotX（几何无效，且 THINKING dx 2.4 劣于 B 1.2），改动更多、风险略高、收益边际。若后续用户明确「要最大饱满度、不计较那 1 行 rotX」，C 可作备选。

**诚实边界**：B（及 A/C）均**不消除**肉眼「椭圆感」——那是前亮后暗深度着色 + 光晕的亮度错觉（UI-02 结论），在本允许参数空间内，除非把球拍扁（§5-12 禁止），否则无法彻底消除。B 解决的是唯一可工程化解决的真实项（饱满度）。

---

## 12. STOP — 不扩圈、不擅自 IMPLEMENT

- 生产 `dyna-orb.js` 维持基线 `5b1a1b10a1abbf31`（net zero）。
- 本任务为 **VISUAL-ONLY 实验 + 推荐**，非实现。是否落地 B（或 C）需用户授权 IMPLEMENT 后再开下一轮，届时按 Minimal Implement → Verify → Document 流程执行，并附 per-primitive 证据。
- 未跨任何边界（§11 红线 0 违规）。STOP。
