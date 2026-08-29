# Xiao6 AI OS · Final Interface Reconstruction v6 — Phase 1 · Design

> 身份：Senior Product Designer + AI OS Architect + Frontend System Engineer
> 一句话目标：**打开界面第一眼——「小6在这里」**，而不是「我打开了一个网页应用」。

---

## 0. 设计原则

- **不是聊天软件 / 不是 Dashboard / 不是工具集合** —— 小6是一个持续存在的 AI 副驾。
- 高级感来自 **空间、比例、留白**，不是特效。
- 动画 **克制：100–400ms**；状态切换用颜色+亮度+粒子+速度+声音**同时**变化，而非堆特效。
- 深色空间：纯黑 / 深蓝底；强调色 = `avatar-state.js` 8 态色。禁彩色渐变、玻璃卡片、重阴影。
- 字体：现代无衬线（系统栈）；**数据/时间/数字用等宽**。

---

## 1. 第一屏结构（Presence Space）

垂直居中单列，全部在首屏可见，无滚动：

```
                       ⌜ 时间（等宽·淡）⌝

                ◉  AI Core —— 小6的存在体
          ·记忆 ·知识 ·任务 ·世界  （环绕光点 / Ambient Orbit）

                   小6
              状态文字（呼吸感）

      正在 …   记得 …   理解 …      （Context Aura · 自然语言）

                     🎙  （Voice Core · 小6的耳朵）

        [ 告诉小6你的想法……            → ]   （Intent Channel）
```

- 顶部：**仅时间**（+ 一个极小的在线点，不写「AI OS / Presence Space」自述）。
- 中心：**AI Core** 绝对视觉中心。
- 环绕：**Ambient Orbit** 4 个光点。
- 其下：**小6** 名 + 状态文字 → **Context Aura** 三行自然语言。
- 底部：**Voice Core**（耳朵）+ **Intent Channel**（唯一输入）。

---

## 2. AI Core —— 小6的存在体（8 态）

不是圆球，是一团「有生命的光」。

**构成（CSS/SVG，无 Three.js）：**
1. 核心光体（core）：径向柔光，呼吸缩放。
2. 呼吸系统（breath）：4–6s 缓慢 scale/opacity 循环。
3. 状态变化（state）：8 态驱动 `--core-color / --core-glow / --core-speed / --core-particles`。
4. 声音反馈（sound）：状态切换柔和音（Web Audio 合成，受手势+静音开关约束）。
5. 思考反馈（think）：THINKING/PLANNING 时内部粒子加速、结构线生成。

**8 态视觉差异（颜色来自 `avatar-state.META`，统一来源）：**

| 态 | 颜色 | 亮度 | 粒子 | 速度 | 声音 |
|---|---|---|---|---|---|
| IDLE | `#5fb3c8` | 中 | 少·慢飘 | 慢 | 静 |
| WAITING | `#f0b35e` | 中 | 中·轻脉冲 | 中 | 单次轻提示 |
| THINKING | `#8b9bff` | 高 | 多·内旋 | 快 | 低频嗡 |
| PLANNING | `#c08bff` | 高 | 结构线生成 | 中快 | 阶进音 |
| EXECUTING | `#56d364` | 高亮 | 多·外涌 | 最快 | 上行音 |
| COMPLETED | `#56d3a0` | 稳亮 | 收敛静止 | 慢 | 落定音 |
| ERROR | `#ff6b6b` | 闪 | 抖动 | 乱 | 错误脉冲 |
| OFFLINE | `#8a93a6` | 暗 | 几乎无 | 极慢 | 静 |

状态由 `agent_state` SSE 驱动；首屏默认 IDLE（立即可见），真实态 1s 内回填。

---

## 3. Voice Core —— 小6的耳朵（第一入口之一）

不是按钮、不是小图标；是 AI Core 下方一朵「声波耳」。

- **位置**：AI Core 下方，紧贴存在体。
- **5 态**：等待 → 监听 → 理解 → 回应 → 异常。
- **视觉**：监听=声波环展开；理解=频率线波动；回应=柔和填充脉冲；异常=红抖。
- **复用**：`wakeword_detected` SSE（唤醒→进入监听）、`/api/asr`（后端转写，降级用）、浏览器 `SpeechRecognition(zh-CN)` 兜底、`/api/agent/intent`（识别文字落点）。
- **静音/手势**：首次用户手势后 `AudioContext.resume()`；提供全局静音开关。

---

## 4. Intent Channel —— 不是聊天框

- 极简单行输入，占底部，placeholder：`告诉小6你的想法……`。
- 提交 → `ZZIntentGateway.dispatch(text)`；**不出现聊天窗口**。
- 语音识别文字回填此行（`setText`），回车即发。
- IME 合成期（`compositionstart/end`）不误提交。

---

## 5. Context Aura —— 自然语言上下文

三行，无卡片/无数字：

- **正在**：取进展最大的目标 `title` + 中文进度词（刚开了个头/才起步/正在推进/…）。
- **记得**：取 salience 最高记忆原文（去机器前缀），`<em>` 强调。
- **理解**：知识 docs 的 domain 中文标签（概念/项目/架构/…），「你的世界包含 …」。

数据源：`/api/goals` `/api/memories` `/api/knowledge`。渲染节流（≥4s 不重渲，避免跳动）。

---

## 6. Ambient Orbit —— 环绕光点

AI Core 四周 4 个发光小点：**记忆 / 知识 / 任务 / 世界**（+可选「关于」）。
- hover / 激活显标签；点击 → 原地展开 Overlay（非页面跳转）。
- 不离开首页；Overlay 关闭即回主屏。

---

## 7. World Understanding Map —— 轻量 2D 关系网

- 形式：SVG 2D 关系网（**非太阳系/星球**）。
- 节点：项目 / 知识 / 记忆 / 目标；边：语义关联。
- 表达：**「小6如何理解你的世界」**。
- 数据：`/api/memories/graph` + `/api/goals` + `/api/knowledge` + `/api/memories`。
- **默认隐藏**，⌘4 快捷呼出，或点 Ambient「世界」。

---

## 8. Overlay —— Spotlight 式能力展开

居中聚焦面板 + 径向遮罩；按类型注入内容：
- ⌘1 记忆 / ⌘2 知识 / ⌘3 任务 / ⌘4 世界（理解图）/ ⌘5 关于。
- 就地展开，Esc 关闭，焦点管理。

---

## 9. 快捷键

| 键 | 作用 |
|---|---|
| ⌘1 / ⌘2 / ⌘3 / ⌘4 / ⌘5 | 记忆 / 知识 / 任务 / 世界 / 关于 Overlay |
| ⌘⇧U | 唤起/收起聆听 |
| Esc | 关闭 Overlay |

---

## 10. 目录结构

```
xiao6-ui/final/
  index.html
  css/ui-final.css
  js/
    data-adapter.js     # 只读数据适配（fetch + SSE 订阅）
    boot.js             # 装配：快照→状态驱动→上下文→时钟→SSE
  components/
    ai-core.js          # 存在体 8 态
    voice-core.js       # 耳朵 5 态
    intent-channel.js   # 唯一输入
    context-aura.js     # 自然语言三行
    ambient-orbit.js    # 环绕光点
    world-map.js        # 2D 关系网
    overlay.js          # Spotlight 面板
```

---

## 11. 验收（最终目标）

- 打开第一眼：**看到小6**（AI Core 立即在场）。
- 3s：知道这是 **AI**（状态/呼吸/身份）。
- 10s：知道可以**说话**（耳朵 + 输入框）。
- 30s：知道它**记得什么、正在做什么**（Context Aura + Ambient）。
- 60s：愿意**长期使用**（克制、干净、可信）。
