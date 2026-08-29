# 02 · 能力分类（Capability Classification）— Stage B

> 建立**统一能力分类法（Taxonomy）**，所有能力必须归类、不得重复归类（一个能力只归属一个主类，跨类依赖在关系图体现）。
> 本分类即小6能力的"目录树"，UI / AI / Prompt / Agent / 文档 以后均依赖此分类。

---

## 分类总表

| 分类(Code) | 中文 | 覆盖范围 | 能力数(估) | 主状态 |
|---|---|---|---|---|
| Conversation | 对话 | CONV-01..04 | 4 | prod |
| Knowledge | 知识 | KNOW-01..08 | 8 | prod |
| Memory | 记忆 | MEM-01..10 | 10 | prod/beta/exp |
| Context | 上下文 | CTX-01..09 | 9 | prod/hidden |
| Execution | 执行内核 | EXEC-01..11 | 11 | prod |
| Tools | 工具 | TOOL-01..62 | 62 | prod |
| Goals | 目标/任务/编排 | GOAL-01..14 | 14 | prod/beta/hidden/missing |
| Computer | 电脑控制 | COMP-01..08 | 8 | prod/hidden |
| Permission | 权限 | PERM-01..03 | 3 | prod |
| Proactive | 主动智能 | PRO-01..05 | 5 | prod |
| Social | 社交 | SOC-01..03 | 3 | beta/exp |
| Perception | 感知 | PERC-01..07 | 7 | prod/exp |
| External | 外部数据 | EXT-01..07 | 7 | prod/hidden/beta |
| CrossDevice | 跨端 | XDEV-01..02 | 2 | exp/hidden |
| Personalization | 个性化 | PERS-01..03 | 3 | prod/dead |
| Settings | 设置 | SET-01..03 | 3 | prod |
| System | 系统/监控 | SYS-01..08 | 8 | prod/hidden |
| UI | 前端/界面 | UI-01..16 | 16 | prod/duplicate |
| Developer | 开发者 | DEV-01..05 | 5 | prod/hidden |

---

## 分类定义与边界（避免歧义）

### 1. Conversation（对话）
自然语言 I/O 与提示词组装。含对话闭环、意图识别、系统提示词、短期记忆压缩。
**不含**：知识/记忆的存储（归 Knowledge/Memory）、执行（归 Execution）。

### 2. Knowledge（知识）
结构化知识库（Obsidian 笔记）的加载/检索/图谱/监听。
**边界**：`knowledge.search` 被 Context 源消费，但能力本身属 Knowledge。

### 3. Memory（记忆）
对话/用户/经验类记忆的存储、蒸馏、召回、审计、笔记、重要日期、历史。
**边界**：与 Knowledge 区分——Memory 偏"关于用户与对话的动态记忆"，Knowledge 偏"静态知识文档"。

### 4. Context（上下文）
把 Memory/Knowledge/UserModel/Episodic/Personality/Goal 等**组装进提示词**的流水线（源 + 5 阶段构建）。
**边界**：Context 是"喂给 LLM 的拼装层"，不持有数据，数据归各源所属分类。

### 5. Execution（执行内核）
Phase 3 新建的**全 OS 唯一执行入口** `Execution.run` 及其簿记组件（Context/Session/Queue/State/Event/Policy/Metrics/Recovery/Reflection）。
**边界**：真正实现在 `tools.execute_tool`；Execution 只路由+簿记，不重复实现。

### 6. Tools（工具）
`TOOLS`/`TOOL_FUNCS` 注册表（62 项）。是 Execution 的"被调用Leaf"。
**边界**：Tool 是能力的最小执行单元；Goal/Computer 通过 Execution 调用 Tool。

### 7. Goals（目标/任务/编排）
目标生命周期、决策门(GDE)、意图网关、Agent 编排状态机、任务执行/持久/恢复、反思。
**边界**：Planner/Workflow 仅为**蓝图概念**，代码无独立模块（标记 missing，不归类到 prod）。
**注意**：Scheduler 实现完整但零接线 → 归入 Goals 但标记 hidden(孤儿)。

### 8. Computer（电脑控制）
对操作系统的最小副作用操作（读文件/截图/枚举/开应用/聚焦/导航）。
**边界**：高危能力（改文件/执行/杀进程/删/系统/网络）仅为占位 deny，标记 hidden。

### 9. Permission（权限）
PolicyEngine + PermissionGuard + 远程白名单。是所有执行/电脑能力的"闸门"，独立成类。

### 10. Proactive（主动智能）
无需用户触发、后台 tick 驱动的扫描/决策/通知。

### 11. Social（社交）
第三方 IM（飞书/Discord/企业微信）的出站/入站/长连。

### 12. Perception（感知）
屏幕/UIA/OCR/Vision/ASR/唤醒词的"观察"能力。纪律红线：**仅观察、绝不控制**。

### 13. External（外部数据）
天气/台风/地图/系统监控/日历/媒体生成等外部 API 适配。

### 14. CrossDevice（跨端）
设备登记/心跳/跨端接力（handoff）。

### 15. Personalization（个性化）
人格(persona/personality)与习惯个性化。
**边界**：`personalization.py`(习惯/意图) 为死代码，单独标记 dead，不计入活跃个性化。

### 16. Settings（设置）
配置读写 API + 前端设置 + Feature Flag 切换。

### 17. System（系统/监控）
健康检查、监控、HUD、Glance、自检、数据导入导出、常驻伴随。

### 18. UI（前端/界面）
页面、指令中心、指令坞、面板、场景卡、执行监视、引导、Toast/Overlay 管理器、各业务面板。
**边界**：UI 是能力的"呈现/触发层"；重复 UI 子系统在 UI-10/UI-11 标记 duplicate。

### 19. Developer（开发者）
能力清单 API、工具审计、模型测试、工具工厂、自检页。供开发者/AI 自检。

---

## 分类原则（后续新增能力必须遵守）

1. **单一主类**：每个能力只归入一个主分类（跨类关系在 07_CAPABILITY_GRAPH 表达）。
2. **Execution 是横切**：所有"执行"都经 Execution 类，但 Goal/Computer/Tool 仍各有主类（Execution 不吞并它们）。
3. **禁止影子分类**：不因为某个 UI 按钮就叫"新能力"——按钮是入口，不是能力；能力须有后端/内核实现。
4. **蓝图≠能力**：Planner/Workflow 目前无实现，不计入 prod 能力，仅在 04 标记 missing。
5. **重复归入原类 + duplicate 标记**：天气双源都归 External，但互为 duplicate。
