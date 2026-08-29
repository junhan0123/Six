# AI OS Experience Sprint v1.0 — Sprint Summary

> 身份：Senior Frontend Architect / AI OS Interaction Engineer / Product Experience Implementer
> 任务等级：LONG RUNNING IMPLEMENTATION TASK
> 任务类型：Audit → Plan → Refactor → Integrate → Verify → Document → STOP
> 状态：**实现完成，文档齐备，等待 Review（STOP）**

本 Sprint 将已冻结的 **Product Constitution v1.0** 落地为真实前端 AI OS 体验，仅做 P0 体验统一的五支柱：
1. Overlay 统一　2. Focus / ESC 统一　3. Capability Exposure 统一　4. Command Palette 统一　5. Companion 职责收口

---

## 一、强制预读清单（已读 ✅）

| # | 文档 | 用途 |
|---|------|------|
| 1 | `docs/product-constitution/03_EXPERIENCE_PRINCIPLES.md` | 体验六态 / 打扰预算 / 退出态焦点恢复 |
| 2 | `docs/product-constitution/05_CAPABILITY_EXPOSURE_RULES.md` | T0–T4 暴露档位 + 成熟度诚实标注 |
| 3 | `docs/product-constitution/06_INTERACTION_CONSTITUTION.md` | 12 交互面唯一职责 + 禁止重叠 + 统一通道 |
| 4 | `docs/product-constitution/07_INFORMATION_ARCHITECTURE.md` | 六层 L1–L6 + T↔L 信息架构 |
| 5 | `docs/capability-platform/03_ENTRY_MAP.md` | 18+ 去中心化 ESC + 12+ Overlay 重复 + Command Palette 唯一 |
| 6 | `docs/capability-platform/v1.1/03_AGENT_CAPABILITY_CHECK_PROTOCOL.md` | 八道预检闸门（G2/G3/G6 PASS，仅触发 G8 文档义务） |

## 二、本 Sprint 对应条款映射表

| Sprint | Product Constitution / Capability Platform 条款 | 落地点 |
|--------|--------------------------------------------------|--------|
| **S1 Overlay** | 06 §统一通道（单一 Overlay 入口）；03_ENTRY_MAP §Overlay 重复（12+）；03 §体验六态 | `overlay-manager.js` `track/untrack`；20 个面板统一登记；去中心化 ESC 清零 |
| **S2 Focus/ESC** | 06 §2 Keyboard 集中焦点管理；03 §2.6 退出态焦点恢复 | `focus-manager.js`、`keyboard-manager.js`；ESC 仅关栈顶；焦点保存/恢复 |
| **S3 Capability Exposure** | 05 §2 T0–T4 档位；05 §3 成熟度诚实标注（禁虚假"即将上线"） | `capability-exposure.js` `classify/tag`；command-palette badge；capabilities-view 读取 |
| **S4 Command Palette** | 06 §Command Palette 唯一命令中心；03_ENTRY_MAP §CP 唯一；07 §信息架构 | `command-palette.js` 整合搜索/执行/最近/能力标签/页面跳转；单一开关经 OverlayManager |
| **S5 Companion** | 06 §12 交互面唯一职责；03 §体验六态 | `companion.js`/`companion.html` 移除非 AI 职责（设置/系统状态/页面导航），保留对话/AI 状态/建议/主动提醒/执行反馈 |

## 三、交付物清单

| 类别 | 文件 | 说明 |
|------|------|------|
| 基础设施（新增） | `focus-manager.js` | 焦点陷阱 + 祖先链感知 backgroundInert + 焦点恢复 |
| 基础设施（新增） | `keyboard-manager.js` | 单一 capture 监听 + 优先级；Command Palette 最高优先级（mod+k） |
| 基础设施（新增） | `capability-exposure.js` | T0–T4 + 成熟度诚实标注 + classify/tag + computerMap |
| 基础设施（扩展） | `overlay-manager.js` | 新增 `track/untrack/closeTop/OverlayType`；中央 ESC 仅关栈顶；焦点委托 FocusManager |
| 接入（改造） | `command-palette.js` | 经 OverlayManager 开关；最近命令；能力状态 badge；键盘最高优先级 |
| 接入（改造） | `capabilities-view.js` `doc.js` `map.js` `memory-panel.js` `memory-query.js` `sysprompt.js` `review.js` `video.js` `settings.js` `app.js(modal-mask/zzPanel/briefing)` `tasks.js` `memory.js` `hotspot.js` `companion.js` | 统一 `track` + 删除去中心化 ESC |
| 职责收口 | `companion.js` `companion.html` | 移除 5 个非 AI 菜单项 + handleAction 对应分支 |
| 样式 | `styles.css` | `.cp-badge` T0–T4 / beta / exp 状态标签 |
| 脚本注入 | `index.html` | focus/keyboard/capability/overlay 经典脚本在 module 面板前就绪 |
| 文档 | `docs/sprints/ai-os-experience-v1/00~06` | 7 份 |

## 四、最终 Verify 五清单（✅ 已满足）

- [x] **无新增能力 / Runtime / API / Prompt / DB / 权限模型改动**：仅前端 JS/CSS/HTML + 新增基础设施文件；未触碰 `server.py` / Planner / Workflow / EventBus 协议 / Knowledge / Memory / Tool 行为。
- [x] **Overlay / ESC / Command Palette 入口唯一**：全站仅 `OverlayManager` 一个浮层栈 + 一个中央 ESC（capture）；Command Palette 唯一命令中心（`mod+k`，经 OverlayManager 开关）。
- [x] **Companion 职责唯一**：移除设置入口 / 系统菜单项 / 页面导航 / 非 AI 状态；保留对话 / AI 状态 / AI 建议 / AI 主动提醒 / AI 执行反馈。
- [x] **Capability 展示符合 T0–T4**：`CapabilityExposure` 派生自 `capability-registry`，诚实标注 prod/beta/exp/hidden(dead/missing 不暴露)；Command Palette 命令项带 T 档 + 成熟度 badge。
- [x] **去中心化 ESC 清零**：原 ~18 处 `document.addEventListener('keydown', Escape)` 浮层关闭监听全部移除，仅保留：中央 `overlay-manager.js`、输入级 `weather.js`（隐藏建议，非关浮层）、宇宙视图/3D 焦点两处已加"浮层优先"守卫。

## 五、纪律红线遵守

- ✅ 未引入 Electron / 新框架 / 云同步 / 新业务能力。
- ✅ 未改动产品定位、Runtime、LLM Prompt、权限模型、DB 结构。
- ✅ 复用既有 `OverlayManager`（G2/G3：不建第二 Overlay / 命令系统）。
- ⚠️ v1.1/03 八道预检仅触发 **G8 文档义务**（本目录 7 份即履约）。

## 六、STOP — 等待 Review

本 Sprint 实现与文档均已完成。按纪律，下一步**不得**进入 Galaxy Runtime / Desktop Shell / Planner / Workflow / Perception / Electron / Mobile / Voice。请 Review 后给出下一步指令。

> 注：集成测试 10 项与性能基线已写入 `06_TEST_REPORT.md`。其中交互级验证（多开顺序关、ESC 栈顶、焦点恢复、键盘全可操作）需在浏览器手动跑一遍；本环境无 GUI，已提供测试用例与设计基线，待 Review 时人工确认。
