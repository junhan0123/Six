# 03 · Capability Exposure Map（Sprint 3 落地）

## 1. 设计目标（对应 05 §2 T0–T4 / §3 成熟度诚实标注）

将能力暴露从"散落声明"收口为**单一真相**：由 `capability-registry.js` 的 `ZZCapabilities.allCapabilities()` 派生，经 `capability-exposure.js` 统一分级与诚实标注，**禁虚假"即将上线"**。

## 2. 暴露档位（TIERS，对齐 05 §2）

| Tier | 含义 | 展示 |
|------|------|------|
| T0 | 核心常驻能力（对话/记忆/态势…） | 永久可见 |
| T1 | 高频能力 | 常驻/快捷 |
| T2 | 中频能力 | 命令中心 |
| T3 | 低频能力 | 命令中心/检索 |
| T4 | 实验/长尾 | 检索/显式入口 |

## 3. 成熟度（MATURITY，对齐 05 §3 诚实标注）

| maturity | 标签 | 暴露 |
|----------|------|------|
| prod | （无后缀） | ✅ |
| beta | `beta` | ✅ 标 Beta |
| exp | `exp` | ✅ 标 实验 |
| hidden | — | ❌ 不暴露 |
| dead / missing | — | ❌ 不暴露（无实现/已废弃，禁"即将上线"占位） |

- `HIDDEN_MATURITY = { missing, dead }` → `exposed:false`。
- `classify(spec)` → `{ tier, maturity, exposed, badge, honest, note }`。
- `tag(item)` → 给 UI 能力项附加 `tier/maturity/exposed/badge`。

## 4. `capability-exposure.js` API

| API | 作用 |
|-----|------|
| `TIERS` / `MATURITY` | 档位与成熟度字典（单一来源）。 |
| `CATEGORY_DEFAULTS` | 19 分类默认档位（对齐 05 §3）。 |
| `classify(spec)` | 计算 tier/maturity/exposed/badge/honest/note。 |
| `tag(item)` | 给 UI 项打标。 |
| `computerMap()` | 由 `ZZCapabilities.allCapabilities()` 派生（含 fallback 快照）；`implemented===false` → maturity `missing`。 |

## 5. 诚实标注纪律（红线条码）

- 任何能力若未实现（dead/missing），**不得**以"即将上线 / Coming Soon"伪暴露。
- 实验（exp）必须标 `实验`；Beta 必须标 `Beta`。
- 三处声明重复（command-palette / capabilities-view / settings 过去各自硬编码档位）已消除：统一从 `CapabilityExposure` 读取。

## 6. 集成点

- **Command Palette**：每条命令经 `CapabilityExposure.tag({category, maturity})` 渲染 `T0·beta` 等 badge（`.cp-badge`，样式见 `styles.css`）。
- **capabilities-view**：渲染档位/成熟度时统一 `tag()`，不再自声明。
- **settings**：能力相关开关统一读取，消除重复硬编码。

## 7. 验证点

- ✅ 单一真相：全部档位/成熟度派生自 `capability-registry`，无第二份声明。
- ✅ 诚实：dead/missing 不暴露；exp/beta 带标签。
- ✅ 无"即将上线"占位：扫描 `coming soon / 即将上线 / soon` 应为空（详见 06 红线扫描）。
