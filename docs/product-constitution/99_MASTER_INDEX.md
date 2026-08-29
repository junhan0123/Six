# 99 · 总索引（Master Index）

> 小6 AI OS 产品宪法 Phase v1.0 — 13 份文档总索引、关系图、阅读顺序。
> 性质：纯设计 / 纯产品治理 / 零代码改动。

---

## 1. 文档清单（13 份）

| 编号 | 文档 | 对应 Phase | 一句话职责 |
|---|---|---|---|
| 00 | `00_EXECUTIVE_SUMMARY.md` | — | 执行摘要、权威关系、红线复核、状态 |
| 01 | `01_PRODUCT_VISION.md` | Phase 1 | 产品愿景：是什么 / 不是什么 / 成熟维度 / 现实约束 |
| 02 | `02_PRODUCT_PHILOSOPHY.md` | Phase 2 | 产品哲学：为何存在 / 价值 / 原则 / 不可违背 |
| 03 | `03_EXPERIENCE_PRINCIPLES.md` | Phase 3 | 体验六态（主动/等待/安静/提醒/介入/退出）+ 打扰预算 |
| 04 | `04_DAILY_USER_JOURNEY.md` | Phase 4 | 每日九时段 AI 职责（晨/工/会/研/码/写/玩/夜/眠） |
| 05 | `05_CAPABILITY_EXPOSURE_RULES.md` | Phase 5 | 能力五档暴露级别 + 诚实标注 + 分级映射 |
| 06 | `06_INTERACTION_CONSTITUTION.md` | Phase 6 | 12 交互面唯一职责 + 禁止重叠 + 统一通道 |
| 07 | `07_INFORMATION_ARCHITECTURE.md` | Phase 7 | 信息六层架构 + 导航原则 |
| 08 | `08_USER_MENTAL_MODEL.md` | Phase 8 | 用户应/不应如何认知小6 |
| 09 | `09_AI_BEHAVIOUR_CONSTITUTION.md` | Phase 9 | AI 六类行为边界（说/默/问/执行/拒/确认） |
| 10 | `10_PRODUCT_ROADMAP.md` | Phase 10 | 未来九方向 P0–P3 排序冻结 |
| 11 | `11_PRODUCT_GOVERNANCE.md` | 治理 | 治理定位 / 变更控制 / 维护者 / 重审计 |
| 99 | `99_MASTER_INDEX.md` | — | 本索引 |

---

## 2. 阅读顺序（Recommended Reading Order）

1. `00_EXECUTIVE_SUMMARY`（先建立权威关系与纪律）
2. `01_PRODUCT_VISION` → `02_PRODUCT_PHILOSOPHY`（是什么、为何）
3. `03_EXPERIENCE_PRINCIPLES` → `04_DAILY_USER_JOURNEY`（体验与日常）
4. `05_CAPABILITY_EXPOSURE_RULES` → `06_INTERACTION_CONSTITUTION`（能力如何露、怎么交互）
5. `07_INFORMATION_ARCHITECTURE` → `08_USER_MENTAL_MODEL`（信息怎么组织、用户怎么想）
6. `09_AI_BEHAVIOUR_CONSTITUTION`（AI 怎么行为）
7. `10_PRODUCT_ROADMAP`（未来）
8. `11_PRODUCT_GOVERNANCE`（治理）
9. `99_MASTER_INDEX`（回溯）

---

## 3. 真相关系图（Single Source of Truth Map）

```
                    ┌─────────────────────────────────────┐
                    │  Golden State (L0) — 最高权威         │
                    │  docs/frozen/XIAO6_GOLDEN_STATE  │
                    └───────────────────┬─────────────────┘
                                        │ 服从
        ┌───────────────────────────────┼───────────────────────────────┐
        │                               │                               │
┌───────▼──────┐ ┌─────────────────────▼──────┐ ┌─────────────────────▼──────┐
│ Architecture │ │   Capability / Execution /  │ │   本产品宪法 (NEW)          │
│ (L3 架构真相)│ │  Knowledge (技术层真相)     │ │   产品/体验层单一真相源      │
│ ARCHITECTURE│ │  capability-platform/       │ │   docs/product-constitution │
│ _MAP + 01    │ │  execution-platform/        │ │                            │
│              │ │  knowledge-engine/          │ │  引用↑技术真相，不重定义    │
└──────────────┘ └────────────────────────────┘ └─────────────┬──────────────┘
                                                              │ 引用
                                                    ┌─────────▼─────────┐
                                                    │ Design Canon      │
                                                    │ (解释层, 非权威)   │
                                                    │ docs/design/frozen│
                                                    │ PRODUCT_CONSTITUTION│
                                                    │ DOMAIN_MODEL 等   │
                                                    │ → 应视为本宪法     │
                                                    │   解释子文档       │
                                                    └───────────────────┘
```

---

## 4. 与各真相源的对应（引用，不重定义）

| 本宪法章节 | 引用的真相源 |
|---|---|
| 01 §2, §3 | Golden State（L0 定位）、`10_PRODUCT_POSITIONING.md` §4 |
| 01 §6 现实约束 | `03_ENTRY_MAP.md` §十（Electron 不存在）、能力真相（Planner/Workflow missing、Perception Mock） |
| 02 §5 不可违背 | Golden State 红线、架构 P11–P15 |
| 05 暴露级别 | `02_CAPABILITY_CLASSIFICATION.md`（19 类）、`01_CAPABILITY_INVENTORY.md`（SSOT） |
| 06 交互面 | `03_ENTRY_MAP.md`（入口地图）、`05_DUPLICATE_REPORT.md`（Toast/Overlay 重复） |
| 07 信息架构 | `03_ENTRY_MAP.md` §二（5 页面）、`05` 暴露级别 |
| 09 行为边界 | 架构 P13（薄主动层）、Execution Platform（权限闸门） |
| 10 路线图 | 能力真相（missing/exp/hidden）、Golden State 红线 |
| 11 治理 | `GOVERNANCE_AUTHORITY_HIERARCHY.md`、能力治理 v1.1/04 |

---

## 5. 与其他文档的关系（避免第二真相）

- **`docs/ai-os/10_PRODUCT_POSITIONING.md`**：架构系列产品定位声明。本宪法**吸收并升格**其内容为产品层权威；后续以本宪法为准。
- **`docs/design/frozen/PRODUCT_CONSTITUTION.md`**：设计解释层 Design Canon（已冻结）。本宪法是产品意图权威源；该 Canon 应视为其**解释/索引子文档**（待 Review 后经变更控制标注）。
- **`docs/design/frozen/DOMAIN_MODEL.md`**：设计解释层 Domain Model。本宪法引用其 Galaxy 隐喻映射，不重定义。
- **`AI_BOOTSTRAP.md`**：建议 Review 批准后补入"产品宪法现实认知"段（任何 AI 进入即读本宪法）。

---

## 6. 红线复核（Verify 摘要，详见 00 §四）

- ✅ 未新增功能 / 未改代码 / 未进实现阶段。
- ✅ 未改任何冻结/治理文档（Golden State / Design Canon / Governance 保持原状）。
- ✅ 未提交 Git。
- ✅ 无第二权威：本宪法引用技术真相，不重定义；Design Canon 定位为解释子文档。

---

## 7. 状态

🛑 **Product Constitution Phase v1.0 — 13 份文档齐备，Verify 通过，STOP 等 Review。**
