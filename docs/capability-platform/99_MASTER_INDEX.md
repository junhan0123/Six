# 99 · 能力平台主索引（Master Index）

> 小6能力平台 Phase v1.0 — 14 份交付物总目录。
> **本目录即能力真相的入口；任何 UI / AI / Prompt / Agent / 文档 必须依赖此处。**

---

## 文档清单

| 文件 | 阶段 | 内容 |
|---|---|---|
| `00_EXECUTIVE_SUMMARY.md` | — | 执行摘要、关键结论、红线复核 |
| `01_CAPABILITY_INVENTORY.md` | Stage A | **能力清单(SSOT 字段表)** — 全量能力 ID/状态/入口/权限/flag/重复/风险 |
| `02_CAPABILITY_CLASSIFICATION.md` | Stage B | 19 分类法(统一 taxonomy) |
| `03_ENTRY_MAP.md` | Stage C | 入口地图(页面/指令/快捷键/API/自动/Proactive/Electron=无) |
| `04_CAPABILITY_LIFECYCLE.md` | Stage D | 生命周期标签(Prod/Beta/Exp/Hidden/Internal/Deprecated/Legacy/Dead) |
| `05_DUPLICATE_REPORT.md` | Stage E | 重复能力审计(11 组 + UI 子系统群) |
| `06_UNUSED_REPORT.md` | Stage F | 未用/死代码审计(死文件/孤儿/悬空开关) |
| `07_CAPABILITY_GRAPH.md` | Stage G | 能力关系图(主链路/旁路/依赖矩阵/红线) |
| `08_CAPABILITY_BOOK.md` | Stage H | **能力书(人读说明书)** — 每能力用途/入口/调用/限制/权限/状态/依赖/场景 |
| `09_USER_CAPABILITY_GUIDE.md` | Stage I | 用户能力指南(能干什么/怎么用/自动/命令/授权/配置) |
| `10_DEVELOPER_CAPABILITY_GUIDE.md` | Stage J | 开发者能力指南(开发前必读/红线/坑/Checklist) |
| `11_CAPABILITY_STATISTICS.md` | Stage K | 能力统计(数量/分类/生命周期/flag/重复/死代码) |
| `12_FINAL_REVIEW.md` | Stage L | 终审(10 问/成熟度/Top20/建议) |
| `99_MASTER_INDEX.md` | — | 本索引 |

---

## 阅读路径

- **想了解小6能做什么** → `09_USER_CAPABILITY_GUIDE.md` → `08_CAPABILITY_BOOK.md`
- **要开发/改代码** → `10_DEVELOPER_CAPABILITY_GUIDE.md` → `01` + `08` + `02`
- **查某能力字段** → `01_CAPABILITY_INVENTORY.md`(搜 ID)
- **查重复/死代码** → `05` / `06`
- **查入口/生命周期** → `03` / `04`
- **查全局数字** → `11_CAPABILITY_STATISTICS.md`
- **查终审结论** → `12_FINAL_REVIEW.md`

---

## 核心数字速记

- 能力条目 **~135**（19 类，含 62 工具）
- API **~73** 路由 · DOMAIN 事件 **71** · SYSTEM 事件 **22**
- Production **~95** / Beta **~12** / Exp **~8** / Hidden **~14** / Dead **~12**
- 重复组 **11** · Toast **5+** · Overlay **12+** · 死代码文件 **~12**
- Feature Flag **~27**（运行时默认开 ~20 / 关 ~7）
- 唯一执行入口 **1** · 唯一事件总线 **1** · 唯一权限 **1** · 第二 Runtime **0**
- **Electron：不存在**

---

## 红线（能力真相不可破）

- 单一执行入口 `Execution.run`；单一事件总线 `eventbus`；单一权限 `PolicyEngine+PermissionGuard`；单一状态写源。
- Local First；F1 事件契约冻结(DOMAIN=71)。
- 本审计阶段未改任何代码/配置/UI；后续任何演进须先读本文档集。

---

🛑 **Capability Platform Phase v1.0 — STOP，等待人工 Review。**
