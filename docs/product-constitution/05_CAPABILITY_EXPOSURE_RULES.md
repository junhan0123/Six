# 05 · 能力暴露规则（Capability Exposure Rules）

> 依赖：能力真相（`02_CAPABILITY_CLASSIFICATION.md` 19 类、`01_CAPABILITY_INVENTORY.md` SSOT）、02（P-HON 诚实）
> 红线：仅规定能力"如何呈现给用户"；不增删能力、不改动代码、不重定义能力真相。

---

## 1. 目的

能力真相已在 `docs/capability-platform/01_CAPABILITY_INVENTORY.md` 建立（唯一 SSOT）。本文件规定这些能力**以何种方式暴露给用户**，使产品体验一致、诚实、可控。

> 能力"存在与否/属哪类/成熟度"由能力 SSOT 决定；本文件只决定"怎么露"。

---

## 2. 五档暴露级别（Exposure Tiers）

| 级别 | 名称 | 含义 | 触发方式 |
|---|---|---|---|
| T0 | **默认展示（Default）** | 高频、低风险、已 production 的核心能力，首屏/常驻可见 | 主窗面板、Dock、指令中心常驻段 |
| T1 | **按需（On-Demand）** | 有用但非高频，用户召唤才出现 | 指令中心（Ctrl/Cmd+K）、Chat 指令、面板按钮 |
| T2 | **自动（Automatic）** | 后台运行、无需用户操作即生效 | Proactive tick、Watcher、启动自检 |
| T3 | **后台（Background）** | 系统/开发者/监控类，普通用户无感 | 系统状态、HUD、Glance、自检页 |
| T4 | **专家模式（Expert）** | 高风险/开发者/高级调试，默认隐藏 | 设置开关、开发者 API、专家面板 |

---

## 3. 分级映射（基于能力分类与成熟度）

> 成熟度来自能力真相：`prod` / `beta` / `exp` / `hidden` / `dead` / `missing`（蓝图）。暴露级别**受成熟度约束**：`missing`/`dead` 不得暴露；`hidden` 仅 T3/T4；`exp` 须标注"实验"。

| 能力分类 | 典型成熟度 | 暴露级别 | 说明 |
|---|---|---|---|
| Conversation | prod | T0 | 对话入口首屏常驻 |
| Knowledge | prod | T0/T1 | 文档库面板（T0）+ 检索指令（T1） |
| Memory | prod/beta/exp | T0/T1 | 记忆网络/长期记忆（T0），部分 beta 实验（T1+标注） |
| Context | prod/hidden | T3 | 拼装层，用户无感（hidden 源不暴露） |
| Execution | prod | T1（出口）/ T4（内核） | 用户触发经 T1；内核簿记 T4 |
| Tools | prod | T1 | 经指令中心/对话调用，不单列 62 项 |
| Goals | prod/missing | T0/T1 | 目标管理 T0；Planner/Workflow `missing` 不暴露 |
| Computer | prod/hidden | T1/T4 | 安全操作 T1；高危占位 deny 仅 T4 标注 |
| Permission | prod | T4 | 权限设置仅专家/设置内 |
| Proactive | prod | T2 | 后台 tick；输出经 T0/T1 提醒 |
| Social | beta/exp | T1/T4 | 第三方 IM 接入（beta）T1，配置 T4 |
| Perception | prod/exp | T3/T4 | 感知全 Mock；仅观察，T3 展示，真实识别未接（T4 规划） |
| External | prod/hidden/beta | T1/T3 | 天气/地图 T1；部分 hidden 源不暴露 |
| CrossDevice | exp/hidden | T4 | 跨端接力实验，默认隐藏 |
| Personalization | prod/dead | T1/T4 | 人格设置 T1；`personalization.py` dead 不暴露 |
| Settings | prod | T1 | 设置面板（`,` 或按钮） |
| System | prod/hidden | T3 | 健康/监控/HUD T3；隐藏源不暴露 |
| UI | prod/duplicate | — | 呈现层本身，非能力；重复子系统须收口（见 10） |
| Developer | prod/hidden | T4 | 能力清单 API/审计页 T4 |

---

## 4. 诚实标注规则（P-HON 落地）

- `beta` 能力：界面标注"Beta"，不承诺稳定。
- `exp` 能力：标注"实验"，且若为 Mock（如 Perception）须注明"模拟数据，未接真实识别"。
- `hidden` 能力：不进入用户可见菜单；仅在专家/开发者模式可见。
- `missing`（蓝图，如 Planner/Workflow）：**严禁**作为可用能力暴露；只能出现在"规划中"说明。
- `dead`（如 `personalization.py`）：完全不暴露、不引用。

---

## 5. 暴露禁令（避免体验噪音）

1. **不堆砌**：不在首屏罗列全部 135 能力；首屏仅 T0 核心（对话/知识/记忆/目标/主动）。
2. **不重复入口噪音**：同一能力可由"按钮+指令中心+伴侣菜单"触发（正常），但 Toast/Overlay **渲染入口**须收口到统一通道（引用 `05_DUPLICATE_REPORT.md` D 系列，见 10 路线图）。
3. **不悄悄暴露高危**：Computer 高危动作（删/杀/执行/网络）即使存在也仅 T4 标注 deny，不得伪装可用。
4. **专家能力不外溢**：T4 能力默认隐藏，开启需明确确认。

---

## 6. 暴露与权限的关系

- 暴露级别 ≠ 权限级别。T0 展示的能力（如"执行任务"）实际动作仍须经 `PermissionGuard`（P-SAFE）。
- 用户可见的"能点"不代表"能无确认执行"；高风险动作无论暴露级别都走权限确认（02 §5）。

---

## 7. 本文向下约束

- 06 交互宪法中每个交互面的"承载哪些能力"须符合本分级。
- 07 信息架构的层级须与本分级一致（T0 在首层，T4 在深层）。
- 09 AI 行为中"主动展示能力"须符合 T2/T3 与诚实标注。
- 任何未来新增能力 → 先过 `v1.1/03` 预检并在 SSOT 定级，再定暴露级别（不反向）。
