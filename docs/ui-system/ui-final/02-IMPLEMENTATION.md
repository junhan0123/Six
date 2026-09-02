# Xiao6 AI OS · Final (v6) — Phase 2/4 · Implementation Log

> 完整执行：Audit → Design → Implement → Verify（非仅设计）。零后端改动、零新增事件。

## 1. 交付文件清单

```
xiao6-ui/final/
├── index.html                     # 第一屏结构（时间 / AI Core / 状态 / Context Aura / Voice / Intent / Overlay）
├── css/ui-final.css               # 全新设计语言（深色空间·克制留白·8 态 CSS 变量驱动）
├── js/
│   ├── data-adapter.js            # 只读数据适配（fetch + SSE 订阅 agent_state / wakeword_detected）
│   └── boot.js                   # 装配层（快照→状态驱动→上下文→时钟→SSE→周期刷新）
└── components/
    ├── ai-core.js                 # 存在体 8 态（颜色/亮度/粒子/速度/声音/波形）
    ├── voice-core.js              # 耳朵 5 态（wakeword + /api/asr + 浏览器 STT 降级）
    ├── intent-channel.js          # 唯一输入（ZZIntentGateway.dispatch，IME 守卫）
    ├── context-aura.js            # 自然语言三行（正在/记得/理解）+ 供 Overlay 复用的纯函数
    ├── ambient-orbit.js           # 环绕光点（点击原地展开 Overlay）
    ├── world-map.js               # 2D 关系网（SVG，非太阳系）
    └── overlay.js                # Spotlight 能力展开（记忆/知识/任务/世界/关于）
```

设计文档：`docs/ui-system/ui-final/00-AUDIT.md · 01-DESIGN.md · 03-VERIFY.md`

## 2. 组件实现要点

- **AI Core**：核心光体 + 呼吸 + 单细环 + 粒子场 + 思考波形（canvas）+ 结构线（PLANNING）。8 态由 `avatar-state.js META` 注入 `--core-color/-glow/-speed/-bright`，并同步驱动 Web Audio 柔和音（过渡时 ping，受手势+静音约束）。
- **Voice Core**：`idle→listening→thinking→speaking→error`；监听时声波环展开、理解时频率线、回应时填充脉冲。唤醒词命中即进入聆听。
- **Intent Channel**：单行极简输入，回车 → `ZZIntentGateway.dispatch`；语音文字经 `setText` 回填，回车即发；IME 合成期不误提交。
- **Context Aura**：取进展最大目标 + salience 最高记忆 + 知识域中文标签，渲染为自然语言，无卡片无数字；节流 4s。
- **Ambient Orbit**：4 个光点环绕 AI Core，hover 显字，点击原地展开 Overlay。
- **World Understanding Map**：SVG 2D 关系网（小6中心 + 目标/知识/记忆/项目四簇），默认隐藏，⌘4 呼出。
- **Overlay**：居中聚焦面板 + 径向遮罩；⌘1–5 对应记忆/知识/任务/世界/关于；Esc 关闭。

## 3. 如何查看

- 实时预览：在浏览器打开 `http://127.0.0.1:8121/final/index.html`（server.py catch-all 已托管）。
- 快捷键：`⌘1–5` 能力 · `⌘⇧U` 聆听 · `Esc` 关闭 Overlay。
- 首屏即见「小6」存在体（默认 IDLE），1s 内回填真实 runtime 态与上下文。

## 4. 关于「干净 URL」与后端改动

- 用户明确要求 **禁止修改 Backend 逻辑**。本次**未改动 `server.py`**，入口使用既有 catch-all 托管的 `/final/index.html`。
- 如需干净 URL `/final`，可（但不强制）在 `server.py` 的 `do_GET` 中 `/v5` 路由旁加一行（与本 v4/v5 既有模式一致）：
  ```python
  if path in ("/final", "/final/"):
      return self._serve_file("final/index.html")
  ```
  该行仅新增静态托管入口，不改任何业务逻辑；加后需重启 server 进程生效。

## 5. 与 v4/v5 的决裂点（本版不复用其视觉）

- 视觉语言：去玻璃卡片 / 去 Dashboard / 去多 Panel / 去太阳系；改为深色空间 + 留白 + 比例。
- Ambient：由 v5 的横向文字导航 → v6 的环绕光点，更贴合「一个空间」理念。
- 声音：v5 无声 → v6 引入克制的 Web Audio 状态反馈（符合 spec「状态变化须含声音反馈」）。
- Overlay：原生承载「世界理解图」，不再依赖旧 map 组件。
