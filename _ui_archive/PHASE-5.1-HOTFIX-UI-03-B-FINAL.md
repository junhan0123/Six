# PHASE 5.1-HOTFIX-UI-03-B · DESKTOP PARTICLE VOICE ORB · OPTION B FINAL IMPLEMENTATION

- 项目：小6 Xiao6 v1.4.0
- 任务类型：IMPLEMENTATION → REAL RUNTIME VERIFICATION → FREEZE
- 实施对象：`G:\xiao6\xiao6-ui\desktop-avatar\dyna-orb.js`
- 实施内容：OPTION B — BALANCED LIGHTING（2 行视觉参数）
- 日期：2026-08-18

---

## 1. 最终状态

```
PHASE 5.1-HOTFIX-UI-03-B
COMPLETE / VERIFIED / FROZEN

Desktop Particle Voice Orb visual fullness correction = COMPLETE
Geometry   = VERIFIED (ratio 保持 ≈ 1.000，正圆无损)
Lighting   = B BALANCED (alpha 下限 + dotR 双参数)
IDLE       = VERIFIED (cov 9.78% vs 9.18%, ratio 1.000)
LISTENING  = VERIFIED
THINKING   = VERIFIED
SPEAKING   = VERIFIED
ERROR      = VERIFIED (无 JS error，状态正常)
DONE       = VERIFIED (无 JS error，状态正常)
Red Lines  = VERIFIED (0 个禁止文件改动)
Diff       = CLEAN (仅 2 行视觉参数变更)
```

任务随即 **STOP**，未跨任何边界、未开启下一 hotfix、未触碰 DOM Voice Orb 与 executing spinner。

---

## 2. VERIFY-BEFORE-CHANGE 证据

| 检查项 | 结果 |
|---|---|
| 重新读取真实源码 `dyna-orb.js` | ✅ 已 Read（L125–160） |
| 修改前确认仍为 BASELINE | ✅ 修改前 hash `5b1a1b10a1abbf31` == UI-03 基线拷贝 `5b1a1b10a1abbf31` |
| 修改前基线快照 | ✅ `PHASE-5.1-HOTFIX-UI-03-B-BASELINE.dyna-orb.js`（hash `5b1a1b10a1abbf31`） |
| 原参数核验 | ✅ L141 `alpha = 0.25 + depth*0.75`；L142 `dotR = 0.6 + depth*0.8 + amp*2` |
| B 目标值来源 | ✅ 交叉核对 UI-03 报告 §3 表 B 行 + §5 量化 B 行（非记忆猜测） |
| 端口 8010 | ✅ 返回 200，服务可用且从磁盘实时serving（验证见 §4） |

---

## 3. 修改内容（最小 diff）

仅 `dyna-orb.js` 两行数值变化，无重排 / 无重构 / 无 rotX 改动：

```diff
  (line 141)  var alpha = 0.25 + depth * 0.75;   →   var alpha = 0.45 + depth * 0.55;
  (line 142)  var dotR  = 0.6  + depth * 0.8  + animState.amp * 2.0;
                                                   →   var dotR  = 0.8  + depth * 0.5  + animState.amp * 2.0;
```

对照 UI-03 基线快照（`diff`）输出：

```
141,142c141,142
<       var alpha = 0.25 + depth * 0.75;
<       var dotR = 0.6 + depth * 0.8 + animState.amp * 2.0;
---
>       var alpha = 0.45 + depth * 0.55;
>       var dotR = 0.8 + depth * 0.5 + animState.amp * 2.0;
```

`rotX: 0.22`（L63 / L113）**保持不动**；`drawSpinner()`（L155 `R=scale*1.5`）未改；几何投影数学、canvas、DPR、状态机、颜色体系全部未动。

---

## 4. REAL RUNTIME VERIFY（真实 Chromium + 像素测量）

- 方法：复用 `UI03_shot.cjs`（Playwright chromium-1208，`omitBackground:true` 透明 RGBA）+ `UI03B_measure.cjs`（手写 PNG 解码，alpha 通道 ATH_LO=8 / ATH_HI=48）。
- 背板：426×640（CSS 213×320 @ dpr2），期望球心 ≈ (213, 320)。
- 服务：`http://127.0.0.1:8010/desktop-avatar/dyna-orb.html` 从磁盘实时提供（落地后 IDLE 覆盖由 9.18%→9.78% 即证）。
- 控制台错误：**0**（`CONSOLE_ERRORS: []`）。

### 4.1 测量结果与前后对比

| 状态 | ratio(实测) | ratio(预期区间) | cov%(B实测) | cov%(B预期) | cov%(基线) | Δcov | dx | dy |
|---|---|---|---|---|---|---|---|---|
| IDLE | **1.000** | ≈1.000 | 9.78 | 9.81 | 9.18 | **+6.5%** | -0.8 | -0.7 |
| LISTENING | 1.0059 | ≈1.006 | 10.99 | 11.06 | 10.37 | +5.9% | 0.2 | -3.4 |
| THINKING | 1.0173 | ≈1.017 | 13.72 | 13.75 | 12.92 | +6.2% | 1.6 | -1.7 |
| SPEAKING | 1.0208 | ≈1.021 | 11.70 | 11.70 | 11.03 | +6.1% | -2.0 | -1.5 |
| ERROR | 0.9884 | — | 12.04 | — | 11.22 | +7.3% | -5.3 | -2.6 |
| DONE | 1.0089 | — | 11.95 | — | 11.40 | +4.8% | -3.7 | 2.0 |

### 4.2 判定

- **饱满度（核心目标）**：IDLE 9.18% → 9.78%（+6.5%），全部活跃态 +5.9%~+6.2%，B > BASELINE 趋势明确成立。
- **几何红线**：IDLE ratio = 1.000（正圆无损）；LISTENING/THINKING/SPEAKING ratio 全部落在 UI-03 预期区间内，无 X/Y 失衡、无新几何失真。
- **亮度质心**：dx/dy 均 < 6px，属动画瞬时帧正常浮动；topFrac/leftFrac ≈ 50/50 平衡。
- **ERROR/DONE 回归**：无 JS exception、状态可正常进入、球体正常显示；覆盖略高于参考是因 B 抬升全局 alpha 下限（任务 §十二已声明不要求精确相等）。
- **结论**：所有验收项通过，无失败项。

---

## 5. 几何红线复核（§十一）

| 红线项 | 状态 |
|---|---|
| scaleX != scaleY | ❌ 未发生（投影 math 未动） |
| canvas aspect 改变 | ❌ 未发生 |
| canvas width/height 改变 | ❌ 未发生 |
| projection 数学改变 | ❌ 未发生 |
| rotX 被修改 | ❌ 保持 0.22 |
| rotY 被修改 | ❌ 未动 |
| DPR 逻辑改变 | ❌ 未动 |

IDLE ratio 1.000、LISTENING 1.0059、THINKING 1.0173、SPEAKING 1.0208 —— 与 UI-03 验收区间一致。

---

## 6. EXECUTING 状态

- `drawSpinner()` `R=scale*1.5` **未改**；`electron/avatar-window.js` `WINDOW_W` **未改**。
- UI-02 已确认 executing spinner 在 213×320 窄窗下横向裁切 ratio≈0.807，属 **KNOWN / FROZEN / OUT OF SCOPE**。
- 本轮**未为 UI-03 顺手修 spinner**，未改 `drawSpinner()`、未改 `WINDOW_W`、未改 `avatar-window.js`。
- harness 中 executing 因 headless swiftshader 不支持 `ctx.shadowBlur` 而空白 —— 为 **harness 环境伪影**，非生产问题；本轮未测 executing（非可靠验证项），标记为 FROZEN。

---

## 7. 红线审计（§十六 / §十七）

G:\xiao6 非 git repository → 以内容 hash + mtime + 写入日志举证。

| 文件 | 结果 |
|---|---|
| `desktop-avatar/dyna-orb.js` | ✅ 唯一变更（仅 B 两参数；当前 hash `8f62061cb1f196e5`） |
| `desktop-avatar/dyna-orb.html` | ✅ hash `40b8404a73ac535b` == UI-03 基线拷贝，未改 |
| `desktop-avatar/dyna-orb-voice.js` | ✅ mtime 早于本任务，未改 |
| `desktop-avatar/voice.js` | ✅ mtime 早于本任务，未改 |
| `electron/avatar-window.js` | ✅ 未写入 |
| `server.py` / 任何 `.py` | ✅ 未写入 |
| Runtime / Agent Loop / Memory / Scheduler / Executor / Policy / API | ✅ 未写入 |
| TTS / ASR / voice routing / port / proxy / launcher | ✅ 未写入 |
| DOM Voice Orb / zz-workspace.css / 其它 UI / 历史 UI | ✅ 未写入 |

`git diff --stat` 等价物（基于基线快照 diff）：**仅 `dyna-orb.js` 1 个文件变更，且 diff 恰为 OPTION B 两行视觉参数**。

---

## 8. 交付物 / 截图清单（`G:\xiao6\_ui_archive\`）

- `DESKTOP-PARTICLE-ORB-UI03B-IDLE.png`
- `DESKTOP-PARTICLE-ORB-UI03B-LISTENING.png`
- `DESKTOP-PARTICLE-ORB-UI03B-THINKING.png`
- `DESKTOP-PARTICLE-ORB-UI03B-SPEAKING.png`
- `DESKTOP-PARTICLE-ORB-UI03B-FULL.png`
- `DESKTOP-PARTICLE-ORB-UI03B-ERROR.png`
- `DESKTOP-PARTICLE-ORB-UI03B-DONE.png`
- `PHASE-5.1-HOTFIX-UI-03-B-BASELINE.dyna-orb.js`（落地前快照）
- `UI03B_measure.cjs`（测量脚本，仅实验产物）
- `PHASE-5.1-HOTFIX-UI-03-B-VIEWER.html`（前后对比查看器）

---

## 9. 诚实边界（与 UI-03 一致）

OPTION B 解决的是唯一可工程化解决的真实项 —— **球体不够饱满**。
「肉眼椭圆感 / 亮度偏心」是**前亮后暗深度着色 + 光晕的亮度错觉**（UI-02 结论），在允许参数空间内除非把球拍扁（禁止）否则无法彻底消除；B 不动 rotX、不动投影，正圆几何与 3D 深度身份完全保留。

---

## 10. STOP

任务完成即停。不继续优化、不提出新 UI 改造、不再调整 orb、不碰 DOM Voice Orb、不碰 executing spinner、不开下一 hotfix。
