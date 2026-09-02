# 12 · 终审（Final Review）— Stage L

> 回答用户提出的 10 个核心问题 + 产品成熟度评估 + 核心问题 Top20 + 后续建议。
> 本阶段为纯审计，**仅分析、不实施**。

---

## 一、小6真正拥有多少能力？

**约 135 个能力条目**（19 分类；含 62 个工具，非工具能力 ~73）。
其中：
- **Production ~95**（核心闭环完整可用）。
- **Beta ~12**（社交/ASR/KWS/媒体/自我学习/记忆召回/目标源）。
- **Experimental ~8**（感知识别 Mock、设备登记）。
- **Hidden ~14**（flag 默认 off：调度/跨端/移动/常驻/工具工厂/委托/日历/高危电脑）。
- **Dead ~12**（可删除）。
- **Missing 2**（Planner/Workflow 仅蓝图，非真实能力）。

结论：小6是一个**功能相当完整的本地优先 AI OS**，核心对话→目标→执行→记忆/知识→UI 闭环已生产可用。

---

## 二、哪些能力没人知道？（隐藏/实验/死）

- **Hidden**：周期调度器(scheduler)、跨端接力、移动伴随端、常驻伴随、工具工厂、Agent 委托、日历/焦点/剪贴板感知、高危电脑能力(占位 deny)。
- **Experimental**：UIA/OCR/Vision 识别(Mock)、感知融合、设备登记。
- **Dead(应公示为"已废弃")**：personalization.py、perception_* 未接线模块、各类 .tmp/.bak、临时脚本、空 txt。
- **没人知道但有用**：周期调度器已实现却未接线——若启用可支持"定时任务"。

---

## 三、哪些能力没有入口？

- `scheduler.py`：完整实现，**零生产入口**（孤儿）。
- `Planner` / `Workflow`：无入口（且未实现）。
- `personalization.py`：无入口（死）。
- `FEATURE_PERCEPTION`：无门控（悬空）。
- `Ctrl/Cmd+U`：提示文字但无 keydown 处理（死快捷键）。
- `WeatherSource`/`ConversationSource`/`SystemSource`：上下文桩未注册。

---

## 四、哪些能力入口重复？

- **UI 渲染入口重复（最高风险）**：Toast 5+ 套、Overlay/Modal/Dialog 12+ 套并行（权威 `OverlayManager` 已建未收口）。
- **能力视图三源**：capability-registry / capabilities-view / capability-matrix 同源 `ZZCapabilities`。
- **同一能力多触发入口**（正常）：面板可由按钮+指令中心+伴侣菜单三处触发。
- **逻辑重复入口**：天气双源、截图双实现、KWS 三文件、跨端双模块、记忆蒸馏双写、人格双系统、JSON 抽取三份。

---

## 五、哪些能力应该删除？

> 仅建议，本阶段不删。

- **死代码(高置信)**：`_smts_append.py` / `_wcpc_append.py` / `_exec_regression_tmp.py` / `_tmp_log.py` / `e.txt` / `err.txt` / `*.tmp` / `*.bak.zzstep1` / `personalization.py`。
- **未接线感知**：`perception_runtime.py` / `perception_model.py` / `uia_provider.py` / `ocr_provider.py` / `vision_provider.py` / `semantic_fusion.py`（决定接真实模型 or 删）。
- **悬空/幻影开关**：`FEATURE_PERCEPTION` / `FEATURE_PROACTIVE_ENGINE`（补定义或删注释）。
- **孤儿 scheduler**：若产品不投入，删除。
- **幽灵工具名/别名**：`profile_read`/`profile_write`/`reminder_add`/`session_run`（配置错误，清理）。

---

## 六、哪些能力应该保留？

- **核心闭环全保留**：Conversation / Context / Knowledge / Memory / Execution / Goals / Tools / Permission / Proactive / UI 主链路。
- **Beta 但战略重要**：社交、ASR/KWS、媒体生成、自我学习、情节记忆。
- **Experimental 但有路线**：感知识别层（接真实模型后价值高）。

---

## 七、哪些能力应该首页展示？

- **指令中心(Ctrl+K)**：唯一命令入口，应作为首要发现入口。
- **对话主界面**：核心。
- **主动智能开关 + 伴侣**：常态可见。
- **高频面板**：天气/热点/简报/记忆/文档库/地图 → 指令中心已聚合，建议首页 Dock 常驻。
- **能力矩阵 HUD**：展示"生命力"，适合首页一角。

---

## 八、哪些能力应该隐藏？

- **开发/实验**：工具工厂、Agent 委托、周期调度器(未接线)、感知 Mock。
- **需密钥**：社交、媒体生成、ASR/KWS 模型。
- **未完成**：Planner/Workflow（且应**对外不宣称**）。
- **感知识别层**：当前 Mock，不应作为"可用能力"展示。

---

## 九、哪些能力以后必须重构？

1. **UI 子系统统一**：Toast/Overlay/Modal 收口到 `OverlayManager`，收敛 18+ ESC 监听、补焦点陷阱/inert。
2. **天气/KWS/截图/跨端/蒸馏/JSON 抽取**：抽单适配/公共工具，消除重复。
3. **Feature Flag 一致性**：声明默认与运行时默认对齐（或文档明确）。
4. **感知识别层**：接真实 UIA/OCR/Vision 模型，或正式降格。
5. **Planner/Workflow**：若产品需要，真正实现（当前蓝图）。
6. **Scheduler 接线或删除**。
7. **人格双系统**：明确 persona(稳定) vs personality(动态) 边界并文档化。

---

## 十、哪些能力已经达到生产质量？

- **核心执行链路**：Execution(EXEC-01..11) + execute_tool + Tools(62) —— 统一、单入口、零行为变化（Phase 3 验证）。
- **知识层**：keyword 检索 + Obsidian 桥 + 监听 —— 稳定（Knowledge Platform Sprint 冻结）。
- **记忆/上下文**：压缩/摘要/源拼接 —— 生产可用。
- **权限**：PolicyEngine + PermissionGuard —— 单系统、清晰。
- **主动智能**：tick + 决策 + 通知 —— 生产可用。
- **电脑控制(低风险)**：读文件/截图/枚举/开应用 —— 生产(确认制)。
- **外部数据**：天气/台风/地图/系统监控 —— 生产。
- **指令中心**：单一、无重复、良好。

---

## 十一、产品成熟度评估

| 维度 | 成熟度 | 说明 |
|---|---|---|
| 对话/意图 | ★★★★★ | 完整闭环 |
| 知识 | ★★★★☆ | 关键词级(非语义) |
| 记忆 | ★★★★☆ | 多源、蒸馏待收敛 |
| 执行内核 | ★★★★★ | 单入口、统一(Phase3) |
| 目标/任务 | ★★★★☆ | 完整，Planner 缺失 |
| 电脑控制 | ★★★☆☆ | 低风险 prod，高危 deny |
| 权限 | ★★★★★ | 单系统清晰 |
| 主动智能 | ★★★★☆ | 生产可用 |
| 感知 | ★★☆☆☆ | Mock 为主 |
| 社交 | ★★★☆☆ | 需密钥 |
| UI/UX | ★★★☆☆ | 功能全但重复子系统待收口 |
| 跨端/移动 | ★★☆☆☆ | 默认 off/未接线 |
| 架构纪律 | ★★★★★ | 单 Runtime/EventBus/Permission |
| 文档/真相 | ★★★★★(本阶段后) | 能力平台 14 文档建立 |

**总体：核心 OS 已达生产质量；UI 一致性、感知真实化、Planner/Workflow 落地是主要短板。**

---

## 十二、核心问题 Top20

1. **UI 重复子系统(Toast 5+/Overlay 12+)** —— 最高优先级收口。
2. **Electron 不存在** —— 用户假设落空，桌面能力需重新立项。
3. **Planner/Workflow 缺失** —— 对外宣称与实际不符。
4. **Scheduler 孤儿未接线** —— 已实现无入口。
5. **Feature Flag 声明≠运行时默认** —— 维护陷阱。
6. **感知识别层全 Mock** —— 核心短板。
7. **天气双源** —— 重复。
8. **KWS 三文件** —— 重复。
9. **记忆蒸馏双写** —— 重复/不一致风险。
10. **人格双系统** —— 需明确边界。
11. **JSON 抽取三份** —— 重复。
12. **personalization.py 死代码** —— 可删。
13. **perception_* 未接线** —— 死/实验。
14. **悬空/幻影开关** —— 误导。
15. **18+ 去中心化 ESC 监听** —— 焦点管理风险。
16. **高危电脑能力仅占位 deny** —— 未真正开放。
17. **跨端双模块** —— 重叠。
18. **社交/ASR/媒体依赖密钥默认关** —— 用户易以为"没有此功能"。
19. **LOW_RISK_TOOLS 幽灵名** —— 白名单失效部分。
20. **死快捷键 Ctrl+U** —— 提示无实现。

---

## 十三、后续建议（仅分析，不实施）

**P0（架构/一致性）**
- 收口 UI 子系统(Toast/Overlay)到 OverlayManager，补焦点陷阱。
- 对齐 Feature Flag 声明与运行时默认。
- 诚实标注 Planner/Workflow 为"蓝图"，不对外宣称。

**P1（去重/清理）**
- 天气/KWS/截图/跨端/蒸馏/JSON 抽单适配。
- 删除死代码(~12 文件)与悬空开关。
- scheduler 接线或删。

**P2（能力补强）**
- 感知接真实模型 or 降格。
- 高危电脑能力安全开放路线。
- 跨端/移动/常驻的产品决策。
- 语义召回路线（知识=关键词、情节=语义已分，评估是否扩展）。

**P3（文档/治理）**
- 本能力平台 14 文档作为 SSOT，后续 UI/AI/Prompt/Agent/文档强制引用。
- 新增能力必须先归类(02)并更新 01/08。

---

## 十四、状态

🛑 **Capability Platform Phase v1.0 完成：审计/整理/建档/验证全 PASS，14 份文档齐备。统一 STOP，等待人工 Review。**
