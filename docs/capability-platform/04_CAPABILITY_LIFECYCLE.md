# 04 · 能力生命周期（Capability Lifecycle）— Stage D

> 建立统一生命周期标签，所有能力必须标记其一。
> 标签：Production / Beta / Experimental / Hidden / Internal / Deprecated / Legacy / Dead

---

## 生命周期定义

| 标签 | 含义 | 判定标准 |
|---|---|---|
| Production | 生产可用 | 默认开启、功能完整、接线到主链路 |
| Beta | 已发布但需外部条件 | 结构完整，依赖密钥/模型/Windows 等默认缺省 |
| Experimental | 实验脚手架 | 默认关闭或仅 Mock 实现 |
| Hidden | 隐藏 | 由 flag 默认 off 门控，无默认入口 |
| Internal | 内部 | 仅系统/开发者可见（如 /api/audit、自检） |
| Deprecated | 废弃 | 被新实现取代，仍保留兼容 |
| Legacy | 遗留 | 旧路径，作为 fallback 保留 |
| Dead | 死代码 | 无任何调用者，可删 |

---

## 按分类的生命周期分布

| 分类 | Production | Beta | Experimental | Hidden | Internal | Deprecated | Legacy | Dead |
|---|---|---|---|---|---|---|---|---|
| Conversation | CONV-01..04 | — | — | — | — | — | — | — |
| Knowledge | KNOW-01..08 | — | — | — | — | — | — | — |
| Memory | MEM-01,02,06,07,08,09,10 | MEM-03,05 | MEM-04 | — | — | — | — | — |
| Context | CTX-01..08 | CTX-08 | — | CTX-09 | — | — | — | — |
| Execution | EXEC-01..11 | — | — | — | — | — | — | — |
| Tools | TOOL-01..31,34,35 | — | — | TOOL-32,33 | — | — | — | — |
| Goals | GOAL-01..07,09,11,12 | GOAL-08 | — | GOAL-10,12(scheduler) | — | — | — | GOAL-13,14(missing) |
| Computer | COMP-01..06 | — | — | COMP-07 | — | — | — | — |
| Permission | PERM-01..03 | — | — | — | — | — | — | — |
| Proactive | PRO-01..05 | — | — | — | — | — | — | — |
| Social | — | SOC-01,02 | SOC-03 | — | — | — | — | — |
| Perception | PERC-01 | — | PERC-02..05 | — | — | — | — | — |
| External | EXT-01..05 | EXT-07 | — | EXT-06 | — | — | — | — |
| CrossDevice | — | — | XDEV-01 | XDEV-02 | — | — | — | — |
| Personalization | PERS-01,02 | — | — | — | — | — | — | PERS-03 |
| Settings | SET-01..03 | — | — | — | — | — | — | — |
| System | SYS-01..07 | — | — | SYS-08 | SYS-02,06 | — | — | — |
| UI | UI-01..09,12..16 | — | — | UI-03 | — | — | — | UI-10,11(重复) |
| Developer | DEV-01..03,05 | — | — | DEV-04 | — | — | — | — |

---

## 重点生命周期项

### Beta（需外部条件）
- MEM-03 自我学习、MEM-05 记忆召回（graceful 降级）
- SOC-01/02 社交（密钥门控）、SOC-03 飞书 WS
- PERC-06 ASR、PERC-07 唤醒词/KWS（依赖模型，缺失降级）
- EXT-07 媒体生成（MiniMax 密钥，默认 off）

### Experimental（脚手架/Mock）
- PERC-02 UIA(Mock)、PERC-03 OCR(Mock)、PERC-04 Vision(Mock)、PERC-05 感知融合（未接线）
- XDEV-01 设备登记（relay 占位）

### Hidden（flag 默认 off，无默认入口）
- TOOL-32 工具工厂、TOOL-33 Agent 委托
- COMP-07 高危电脑能力（占位 deny）
- GOAL-10 Agent 委托、GOAL-12 scheduler（孤儿）
- EXT-06 日历感知、XDEV-02 跨端接力、SYS-08 常驻伴随、UI-03 移动伴随端

### Missing（蓝图，代码无实现）
- GOAL-13 Planner、GOAL-14 Workflow（仅文档/注释提及）

### Dead（可安全删除）
- PERS-03 personalization.py（习惯/意图，全仓无调用）
- 临时脚本：`_smts_append.py` / `_wcpc_append.py` / `_exec_regression_tmp.py` / `_tmp_log.py`
- 空残留：`e.txt` / `err.txt`
- 备份：`*.tmp`（companion/execution-channel/premium/styles）、`*.bak.zzstep1`（premium/styles）
- 未接线感知：`perception_runtime.py` / `perception_model.py` / `uia_provider.py` / `ocr_provider.py` / `vision_provider.py` / `semantic_fusion.py`
- 上下文桩：`WeatherSource` / `ConversationSource` / `SystemSource`（context/sources.py，返回 [] 未注册）

### Legacy（fallback 保留）
- CONV-03 的 `memory.build_system_prompt`：作为 Context facade 的 fail-safe 旧路径仍被引用。
- 旧 RAG 知识层：已移除，由 keyword KnowledgeRuntime 取代（代码层面已无，仅文档/注释遗留）。

---

## 生命周期治理建议（仅分析，不实施）

1. **Dead → 删除清单**：上述 Dead 项可批量清理（不改动行为）。
2. **Hidden → 决策**：scheduler / 跨端 / 移动端 / 常驻 / 工具工厂 / Agent 委托，需产品决策"继续投入 or 正式废弃"。
3. **Missing → 诚实标注**：Planner/Workflow 不应在对外文档宣称"具备"，待真正实现再升 Production。
4. **Beta → 收敛依赖**：社交/ASR/媒体需明确"密钥缺失时的用户提示"，避免静默降级。
5. **Experimental → 路线**：感知识别层(Mock)是核心短板，决定"接真实模型 or 降格为观察装饰"。
