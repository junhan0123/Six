# 10 · 产品路线图（Product Roadmap）

> 依赖：01（愿景 · L0–L5 成熟度）、能力真相（missing/exp/hidden 现实）、Golden State（L0 红线）、02（不可违背原则）
> 红线：仅**冻结未来阶段的排序与边界**；不实现、不改动代码、不承诺突破 L0 红线。

---

## 1. 目的

把用户指定的未来产品方向**按 P0–P3 排序并冻结边界**，使后续阶段有清晰优先级，且不偏离"本地优先个人 AI OS"定位与 Golden State 红线。

> 路线图**不是承诺排期**，而是"优先级与边界冻结"。每个阶段启动前须 Review 批准 + 走能力治理（v1.1/02 CCR）+ AI 预检（v1.1/03）。

---

## 2. 优先级定义

| 级别 | 含义 |
|---|---|
| **P0** | 最高优先；补齐当前主形态核心缺口，不突破红线即可落地 |
| **P1** | 高优先；显著增强 OS 属性，需新能力立项但风险可控 |
| **P2** | 中优先；体验深化，依赖 P0/P1 基础 |
| **P3** | 低优先/远景；探索性，受现实约束（如无 Electron）限制明显 |

---

## 3. 冻结的路线图（按 P0–P3）

### P0 — 当前主形态核心缺口
| 方向 | 说明 | 边界/约束 |
|---|---|---|
| **UI 子系统收口** | Toast(5+)→统一通道、Overlay(12+)→OverlayManager、Esc/焦点集中 | 不新增能力，纯整合（引用 05/06 去重要求） |
| **Feature Flag 一致性** | 声明默认 ≠ 运行时默认问题修复 | 配置层，不增能力 |
| **死代码/孤儿清理** | `personalization.py`/perception_*/scheduler 孤儿处置 | 引用能力真相 06_UNUSED_REPORT |
| **能力补强（已规划项）** | 按 12_FINAL_REVIEW 建议，逐项过 CCR | 每项先 v1.1/02+03 |

### P1 — 显著增强 OS 属性
| 方向 | 说明 | 边界/约束 |
|---|---|---|
| **Planner / Workflow 落地** | 当前仅蓝图（missing）；落地为形式化 Goal/Workflow 生命周期 | 须遵守单一 Runtime（L0）；不建第二执行路径（P11） |
| **AI Companion 深化** | Companion 从浮窗升级为更完整的常驻副驾（人格一致、记忆驱动） | 当前非 Electron；原生常驻需立项（见 P3 Desktop Shell） |
| **Perception 真实化** | UIA/OCR/Vision 从 Mock 接真实；perception_runtime 接入 server | Vision **仍仅观察，绝不控制**（Golden State 红线） |
| **Automation（轻量）** | 在权限/检查点内的多步任务编排（基于 Workflow） | 受 P-THIN/P-SAFE 约束，可撤销、可审计 |

### P2 — 体验深化
| 方向 | 说明 | 边界/约束 |
|---|---|---|
| **Cross Device（跨端）** | 设备登记/心跳/跨端接力（handoff），当前 exp/hidden | Local First；数据可携带，不落云端状态 |
| **Voice（语音）深化** | ASR/TTS 真实接入，语音成为一等交互 | 当前 Mock；须过权限，不绕过文字通道 |
| **Proactive 智能增强** | 更精准的触发与建议（薄主动层内） | 严守 P13，不自我执行 |

### P3 — 远景/探索（受现实约束明显）
| 方向 | 说明 | 边界/约束 |
|---|---|---|
| **Desktop Shell（桌面外壳）** | 原生常驻/托盘/全局快捷键/开机自启 | **需 Electron 立项**（当前不存在）；重大架构决策，须走 Decision 流程（L1）且不破 L0 红线 |
| **Mobile（移动伴随）** | 移动端深化（当前 mobile-app.html PWA 默认 off） | Local First；与 Cross Device 协同 |
| **JARVIS L4/L5（自主执行/智能贾维斯）** | 远景成熟度 | 必须在 P-THIN/P-SAFE/可崩溃恢复框架内，绝不突破 L0 |

---

## 4. 路线图的不可动摇约束

1. 任何阶段不得引入**第二 Runtime / Memory / EventBus / Permission**（L0 红线）。
2. 任何阶段 Vision **仅观察，绝不控制**（L0 红线）。
3. 任何"执行"须经统一执行通道 + 权限闸门（P11/P-SAFE）。
4. Local First 不可妥协；云端仅计算，不持有状态。
5. 诚实：蓝图/Mock/hidden 在推进中须持续标注，不得伪装 production。

---

## 5. 阶段启动纪律

每个路线图阶段启动前：
1. Review 批准该阶段范围。
2. 走 `docs/capability-platform/v1.1/02_CAPABILITY_CHANGE_PROTOCOL.md`（CCR 评审闸门）。
3. 任何 AI 动手前跑 `v1.1/03`（G1–G8 预检），NO-GO 禁止实现。
4. 若涉及不可逆架构决策（如引入 Electron）→ 走 `docs/decisions/` Decision 流程（L1）。

---

## 6. 与现有真相的衔接

- 路线图不重定义能力真相；新能力须在 `01_CAPABILITY_INVENTORY.md` SSOT 登记后再定暴露级别（05）。
- 路线图不重定义执行/知识真相；新执行路径须汇入 `Execution.run`（P11）。
- 路线图不与 Golden State 冲突；冲突以 L0 为准。

---

## 7. 本文向下约束

- 本路线图是未来阶段的**唯一排序真相**；任何阶段提案须引用本文件定优先级。
- Review 批准后，本路线图冻结；变更须走治理变更控制（11 §4）。
