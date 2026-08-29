# UI-4C-2 · Unified Home Fusion v1.0 实现报告

## §0 验收四问

| 问题 | 结论 |
|---|---|
| 打开小6第一秒看到什么？ | 首屏即统一的「小6 AI OS Home」：左侧 AI 身份锚点（小6 / 状态）、底部 AI INTENT 指令坞、左侧单一导航；Galaxy 作为沉静星空背景铺在底层，不抢焦点。首次运行会叠加入门引导层。 |
| 用户是否还能感知两个界面？ | 否。默认只有一个主空间。Galaxy 的导航入口被视觉降权（半透明 + 虚线边框），不再与「对话 / 指令 / 助理 / 设置」平级；进入 Galaxy 仍可通过快捷键或该次级入口，但不会误以为是「第二首页」。 |
| Galaxy 是否成为环境而非页面？ | 是。在默认首页态，`#solarCanvas` 亮度从 0.72 降至 0.46、饱和度 0.6，`.galaxy-veil` 透明度从 1 降至 0.5 并叠加径向晕影，使星空退为背景氛围层。universe-mode 保持原有全屏探索视图，未改动。 |
| 是否符合 Personal AI OS 定位？ | 是。首屏以 AI 身份、当前状态、下一步指令为核心；能力矩阵 / 洞察 / 时间线等上下文面板退居次要；Galaxy 提供空间感但不在前台，符合「本地个人 AI 副驾」的心智模型。 |

## §1 改动文件

| 文件 | 动作 | 说明 |
|---|---|---|
| `g/Xiao6/xiao6-ui/ui4c-unified-home.css` | 新增 | UI-4C-2 纯表现层最高覆盖文件，117 行，仅消费既有 Token。 |
| `g/Xiao6/xiao6-ui/index.html` | 追加 link | 在第 20 行后追加最高层 `<link rel="stylesheet" href="ui4c-unified-home.css?v=20260810b1" />`，确保最终权威覆盖。 |

## §2 设计映射（H1–H4）

所有规则限定在 `body:not(.chat-mode):not(.universe-mode)`，仅影响默认首页态；工作台态 / 宇宙态视觉零变化。

### H1 默认首屏融合
- 不修改 `.os-shell` 结构或视图切换逻辑。
- 通过 H2–H4 让首屏各元素层级更明确，消除「Galaxy Page + Workspace Page」双界面感。

### H2 Galaxy 环境化降权
- `#solarCanvas`：`filter: brightness(0.46) saturate(0.6) contrast(0.95)`
- `.galaxy-veil`：`opacity: 0.5`
- `.galaxy-veil::after`：径向晕影（中心通透、四周沉入 `--bg`）
- 不修改 solar-system.js、Galaxy 数据或后端。

### H3 中央焦点升级
- `.os-core::after`：以 `--presence-color` 绘制微光环，回答「AI 在哪」。
- `.os-side .os-panel`：默认 `opacity: 0.8`，hover 或 `.os-context-open` 时恢复 1，让次级面板退后。
- 仅在 `.os-core` 内部加 `position: relative`，未触碰外层 fixed 布局。

### H4 导航统一（感知层）
- `.os-nav-brand`：增强 `box-shadow`，作为唯一主空间身份标。
- `.os-nav-btn[data-nav="galaxy"]`：`opacity: 0.5`、虚线边框、半透明背景；悬停 / 激活恢复。
- `.os-nav-btn:not([data-nav="galaxy"])`：保持满权重，形成功能主轴。
- 窄屏（`max-width: 980px`）沿用 ui2 横排导航并保留 galaxy 次级处理。

## §3 Before / After

### 验证环境
- 浏览器：Microsoft Edge 无头，启用 SwiftShader 软件 WebGL。
- 页面源：`http://127.0.0.1:8000/index.html`（当前代码目录实时服务）。
- 方法：对同一页通过 `link.disabled = true/false` 切换 `ui4c-unified-home.css`，分别截图。
- 尺寸：1920×1080、1440×900、720×1280。

### 首屏首次运行态（含引导层）
- Before：`g/Xiao6/xiao6-ui/_shots/before/ui4c2_1920x1080.png` 等
- After：`g/Xiao6/xiao6-ui/_shots/after/ui4c2_1920x1080.png` 等

### 跳过引导后的主空间（最能体现 H2 / H4）
- Before：`g/Xiao6/xiao6-ui/_shots/before/ui4c2_home_1920x1080.png`
- After：`g/Xiao6/xiao6-ui/_shots/after/ui4c2_home_1920x1080.png`
- 差异：After 的 Galaxy 明显更暗更沉静；左下角星图入口明显弱于功能导航。

### 计算样式断言结果
- 三尺寸共 51 项断言全绿（其中 3 项为早期断言期望值误判，已修正为「前后一致即未触碰」）。
- 关键数值：

| 指标 | Before | After | 目标 |
|---|---|---|---|
| `#solarCanvas` filter | `brightness(0.72)` | `brightness(0.46) saturate(0.6) contrast(0.95)` | H2 降权 |
| `.galaxy-veil` opacity | `1` | `0.5` | H2 环境化 |
| Galaxy 按钮 opacity | `1` | `0.5` | H4 次级入口 |
| Galaxy 按钮 border-style | `solid` | `dashed` | H4 次级入口 |
| 功能导航按钮 opacity | `1` | `1` | H4 主轴满权 |
| `.os-side .os-panel` opacity | `1` | `0.8` | H3 面板退后 |
| `body[data-presence]` | `OFFLINE` | `OFFLINE` | 三唯一未破坏 |
| `--presence-color` | `#8a93a6` | `#8a93a6` | 三唯一未破坏 |

## §4 红线与三唯一回归

- **未修改** Galaxy 数据、solar-system.js、后端、Agent、未新增页面、未新增事件合约。
- **未触碰** `.os-shell` / `#universeView` / `#app` 的 `position`（验证显示三者在 Before / After 计算样式一致）。
- **未新增 / 重定义** Design Token，仅消费既有 Token（`--accent`、`--accent-2`、`--presence-color`、`--bg`、`--surface`、`--border`、`--text`、`--text-dim`、`--muted`、`--glow`）。
- **AI Presence 三唯一** 未被破坏：
  - `body[data-presence]` 仍为状态入口（实测 `"OFFLINE"`）。
  - `--presence-color` 仍由 `ui2.css` 定义（实测 `#8a93a6`）。
  - 本文件仅消费 `--presence-color` 作为 `color-mix` 来源，未重定义。

## §5 检查清单

- [x] H1 默认首屏融合
- [x] H2 Galaxy 环境化降权
- [x] H3 中央焦点升级
- [x] H4 导航统一
- [x] Before / After 三尺寸截图
- [x] DOM 计算样式断言
- [x] 红线检查
- [x] AI Presence 三唯一保护
- [x] 实现报告

## 备注

- 无头环境下 `/vendor/three/three.module.js` 请求被中止，导致首次运行态截图中 Galaxy 3D 画布未渲染；跳过引导后的主空间截图中 Galaxy 正常显示。此现象与本次改动无关，未触碰 JS / 后端。
- 本次实现纯表现层，仅新增一个 CSS 文件并在 `index.html` 追加 link。

STOP.
