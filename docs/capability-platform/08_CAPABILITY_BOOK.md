# 08 · 能力书（Capability Book）— Stage H

> **小6以后唯一能力说明书（Single Source of Truth）。**
> 每个能力含：用途 / 入口 / 调用 / 限制 / 权限 / 状态 / 依赖 / 相关能力 / 适用场景。
> 完整字段表见 `01_CAPABILITY_INVENTORY.md`；本文件为"人读版说明书"。
> 格式：`### [ID] 名称` + 字段块。

---

## Conversation

### [CONV-01] 对话闭环
- 用途：自然语言对话 + function-calling 工具调用。
- 入口：`/api/chat`(SSE) → 输入框 #userInput / #btnSend。
- 调用：run_fc_loop → select_tools → LLM → run_one → Execution.run → execute_tool。
- 限制：受远程白名单；依赖 Agnes LLM。
- 权限：继承所调 Tool 的权限。
- 状态：Production。依赖：Execution, Tools, Context。
- 相关：CONV-02, CONV-03, CTX-01。
- 适用：所有聊天场景。

### [CONV-02] 意图识别
- 用途：识别用户意图以裁剪工具集。
- 入口：detect_intents(text)（被 run_fc_loop 调用）。
- 调用：文本分类 → 返回意图标签。
- 限制：启发式，非强制。
- 状态：Production。依赖：Tools(select_tools)。

### [CONV-03] 系统提示词组装
- 用途：拼装注入 LLM 的系统提示（含记忆/人格/知识/目标）。
- 入口：build_system_prompt → context/facade.build_context_prompt。
- 限制：旧路径 memory.build_system_prompt 仍作 fail-safe。
- 状态：Production。依赖：Context(CTX)。

---

## Knowledge

### [KNOW-01] 知识门面（唯一 API）
- 用途：统一访问知识库（负载/检索/解析/校验/归档）。
- 入口：knowledge.load/reload/search/resolve/related/validate/...。
- 调用：→ knowledge_runtime 各模块。
- 限制：**仅关键词检索，无语义/向量**（RAG 已移除）；Local-First。
- 权限：低危。状态：Production。依赖：KNOW-02..07。
- 相关：CTX-07, TOOL-35。适用：知识问答/文档检索。

### [KNOW-03] 关键词检索
- 用途：TF + CJK bigram 关键词召回（top 4）。
- 限制：非语义；命中有限。
- 状态：Production。

### [KNOW-06] 文件监听
- 用途：Obsidian 笔记变更自动重载。
- 限制：仅 Windows(ReadDirectoryChangesW)。
- 状态：Production(Win)。

---

## Memory

### [MEM-01] 短期对话缓冲
- 用途：保留近期对话(summary 压缩，24 轮阈值 40)。
- 状态：Production。

### [MEM-03] 自我学习
- 用途：LLM 萃取反馈/纠错为经验。
- 状态：Beta。限制：graceful 降级。

### [MEM-04] 结构化记忆蒸馏器
- 用途：抽取习惯/偏好/重要事件/关系 → memories 表。
- 限制：`FEATURE_MEMORY_DISTILL` 默认 off。状态：Experimental。
- 相关：MEM-03(双写路径，见 D5)。

### [MEM-05] 记忆召回
- 用途：长期记忆搜索。
- 限制：conversation_memories 表可能不存在，静默降级。状态：Beta。

### [MEM-07] 笔记
- 用途：笔记 CRUD + 图谱。入口：`/api/notes`。状态：Production。

---

## Context

### [CTX-01] 上下文引擎
- 用途：把各"源"组装进提示词。入口：build_context_prompt。状态：Production。
- 源：CTX-03..08（Memory/UserModel/Episodic/Personality/Knowledge/Goal）。
- 限制：默认无限预算(不裁剪 token)。CTX-09 为未注册桩。

---

## Execution

### [EXEC-01] Execution.run（全 OS 唯一执行入口）
- 用途：统一路由所有执行（Goal/Computer/Chat/Social/Proactive）。
- 入口：run(name,args,allowed,context,goal_id,permission,timeout,retry,...)。
- 调用：仅调 execute_tool + 簿记(Context/Session/Queue/State/Event/Policy/Metrics/Recovery/Reflection)。
- 限制：**不重写 execute_tool**；chat 路径默认 NONE(保持现状绕过语义)。
- 权限：委托 PolicyEngine(PERM-01)；GOAL 路径才显式 evaluate。
- 状态：Production(Phase 3 新建)。依赖：EXEC-02, PERM。
- 相关：所有执行方。适用：一切工具/目标/电脑执行。

### [EXEC-07] ExecutionEvent
- 用途：8 个执行事件经 EventBus SYSTEM 通道(不触碰 DOMAIN 红线)。
- 事件：execution_started/updated/completed/cancelled/tool_started/tool_finished/retry_started/retry_finished。

---

## Tools（代表性，全 62 见 01）

### [TOOL-12] kill_process
- 用途：结束进程。限制：高危，`_safe_to_kill` 名校验。状态：Production。

### [TOOL-13] run_shell
- 用途：执行 shell。限制：远程禁；沙箱 SANDBOX_EXEC。状态：Production。

### [TOOL-32] 自定义工具工厂
- 用途：运行时创建工具。限制：`TOOL_FACTORY_ENABLED` 默认 off。状态：Hidden。

### [TOOL-34] 目标工具集
- 用途：set/update/list/delete/plan_goal。限制：FEATURE_GOAL_SYSTEM。状态：Production。

---

## Goals

### [GOAL-04] 目标决策门(GDE)
- 用途：把自然语言判定为建目标/忽略。入口：GoalDecisionEngine.ingest/submit。
- 限制：单例防抖在生产路径失效(每次新建实例)。状态：Production。依赖：GOAL-05。

### [GOAL-06] Agent 编排状态机
- 用途：IDLE→PLANNING→EXECUTING→REFLECTING。状态：Production。依赖：EXEC-01。

### [GOAL-08] 电脑能力闭环
- 用途：经 CapabilityRegistry→PermissionGuard 执行电脑动作。状态：Beta(确认制)。

### [GOAL-09] 反思/经验沉淀
- 用途：目标完成后蒸馏经验→add_knowledge。状态：Production。

### [GOAL-13/14] Planner / Workflow
- 用途：应为独立"怎么做"规划层。状态：**缺失(仅蓝图)**。⚠ 勿对外宣称具备。

### [GOAL-12 scheduler] 周期调度器
- 用途：schedule_once/interval/event。状态：**Hidden(孤儿，零接线)**。

---

## Computer

### [COMP-01] 读文件
- 用途：读取文件内容。限制：沙箱 SANDBOX_ROOT；LOW→auto。状态：Production。

### [COMP-02] 截图
- 用途：内存截图(不落盘)。限制：观察用。状态：Production。

### [COMP-04..06] 开应用/聚焦/导航
- 用途：最小界面副作用。限制：MEDIUM→confirm(需用户确认)。状态：Production。

### [COMP-07] 高危能力
- 用途：改文件/执行/杀进程/删/系统/网络。限制：**仅占位，Guard 直接 deny**。状态：Hidden。

---

## Permission

### [PERM-01] PolicyEngine
- 用途：四级裁决 auto/confirm/session/never；confirm 经 ticket+EventBus 审批卡。
- 状态：Production。相关：PERM-02, EXEC-08。

### [PERM-02] PermissionGuard
- 用途：plan→decide→run 唯一 executor 闸门。状态：Production。

---

## Proactive

### [PRO-01] 主动心跳
- 用途：后台 tick 驱动扫描（到期提醒即时/429 锁定/自适应）。状态：Production。

### [PRO-02] 主动引擎决策
- 用途：IGNORE/SUGGEST/NOTIFY/CREATE_GOAL。状态：Production。

### [PRO-03] 通知策略
- 用途：DND/quiet/importance 过滤。状态：Production。

---

## Social

### [SOC-01] 社交出站
- 用途：discord/feishu/wechat 推送。限制：密钥门控。状态：Beta。

### [SOC-02] 社交入站
- 用途：/api/social/inbound 跑一轮 Agent 后回发。限制：token+频率限。状态：Beta。

---

## Perception

### [PERC-01] 屏幕采集
- 用途：真实 mss 截图。限制：仅观察。状态：Production。

### [PERC-02..05] UIA/OCR/Vision/Fusion
- 用途：识别层。限制：**全 Mock(确定性合成)**。状态：Experimental(未接线)。

### [PERC-06] ASR
- 用途：语音转写(whisper/vosk/funasr/cloud占位)。限制：依赖模型。状态：Beta。

### [PERC-07] 唤醒词/KWS
- 用途：本地唤醒。限制：XIAO6_KWS_ENABLED；依赖缺失降级。状态：Beta。

---

## External

### [EXT-01] 天气(Open-Meteo)
- 用途：LLM 天气工具。状态：Production。相关：EXT-02(重复 D1)。

### [EXT-02] 定位+天气面板
- 用途：主动扫描/定位块天气。状态：Production。

### [EXT-04] 地图
- 用途：离线坐标 haversine(无瓦片，合规)。状态：Production。

### [EXT-06] 日历感知
- 用途：Outlook COM。限制：FEATURE_CALENDAR_SENSE 默认 off(Win)。状态：Hidden。

---

## CrossDevice

### [XDEV-01] 设备登记
- 用途：devices.json 登记/心跳。状态：Experimental。

### [XDEV-02] 跨端接力
- 用途：会话 handoff(内存 Relay)。限制：FEATURE_CROSS_DEVICE 默认 off。状态：Hidden。

---

## Personalization

### [PERS-01] 稳定人格(persona)
- 用途：tone/style/boundaries/quirks 基线(首提示块)。状态：Production。

### [PERS-02] 动态人格(personality)
- 用途：5 维动态参数。状态：Production。相关：PERS-01(并存，需文档化)。

### [PERS-03] 习惯/意图个性化
- 用途：原拟 habit/intent 个性化。**状态：Dead(全仓无调用)**。

---

## Settings

### [SET-01] 配置读写 API
- 用途：/api/config GET/POST(.env)。状态：Production。

### [SET-03] Feature Flag 切换
- 用途：指令中心/设置切换 FEATURE_*。状态：Production。⚠ 声明默认≠运行时默认。

---

## System

### [SYS-01] 健康检查
- 用途：/api/health /ready /version。状态：Production。

### [SYS-06] 自检测
- 用途：self_check.py 启动自检。状态：Production。

### [SYS-08] 常驻伴随
- 用途：always_on 常驻浮窗。限制：FEATURE_ALWAYS_ON 默认 off。状态：Hidden。

---

## UI

### [UI-04] 指令中心(Ctrl+K)
- 用途：唯一命令入口(~30 命令)。状态：Production(单一，无重复，良好)。

### [UI-10] Toast 系统
- 用途：轻提示。**状态：重复(5+ 套，见 D8)**。

### [UI-11] Overlay/Modal/Dialog
- 用途：浮层/弹窗。**状态：重复(12+ 套，见 D9)**。

### [UI-03] 移动伴随端
- 用途：PWA 三页。限制：FEATURE_MOBILE_COMPANION 默认 off。状态：Hidden。

---

## Developer

### [DEV-01] 能力清单 API
- 用途：/api/capabilities 自检。状态：Production。

### [DEV-04] 工具工厂
- 用途：运行时建工具。限制：TOOL_FACTORY_ENABLED 默认 off。状态：Hidden。

---

> 本"书"与 `01_CAPABILITY_INVENTORY.md` 互为索引：书为人读说明，表为机读字段。任何 UI/AI/Prompt/Agent/文档**以后必须依据此二者**，不得另立能力真相。
