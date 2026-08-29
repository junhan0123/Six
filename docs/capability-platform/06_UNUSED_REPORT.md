# 06 · 未用能力审计（Unused / Dead Code Audit）— Stage F

> 扫描 Dead Code / Unused Feature / Orphan Module / Legacy API / Unused CSS/JS/Tool/Setting/Prompt/Shortcut/Panel/Overlay。
> **仅记录，不得删除**（本阶段纪律红线）。

---

## 一、死代码 / 孤儿文件（确认无调用者）

| 文件/符号 | 类型 | 证据 | 置信度 |
|---|---|---|---|
| `_smts_append.py` | 一次性脚本 | 依赖已删的 `_smts_css.tmp`，全仓无 import | 高 |
| `_wcpc_append.py` | 一次性脚本 | 同上，依赖已删 `_wcpc_css.tmp` | 高 |
| `_exec_regression_tmp.py` | 临时回归脚本 | import tools/ai_core.execution，无引用者 | 高 |
| `_tmp_log.py` | 临时日志脚本 | import db/agent_runtime，无引用者 | 高 |
| `e.txt` (0B) | 空残留 | grep 全仓无读取 | 高 |
| `err.txt` (0B) | 空残留 | 同上 | 高 |
| `companion.css.tmp` / `execution-channel.css.tmp` / `premium.css.tmp` / `styles.css.tmp` | 编辑器/步骤备份 | html/js 无任何 `.tmp` 链接 | 高 |
| `premium.css.bak.zzstep1` / `styles.css.bak.zzstep1` | 步骤快照备份 | 未被 index.html 引用 | 高 |
| `personalization.py` | 孤儿模块 | `record/summary` 全仓无调用（仅 python/Lib/hashlib.py 误命中） | 高 |
| `perception_runtime.py` / `perception_model.py` / `uia_provider.py` / `ocr_provider.py` / `vision_provider.py` / `semantic_fusion.py` | 模块集 | 仅在 `tests/phase8*` 及彼此 import；**未被 server.py 运行时引用** | 中 |
| `WeatherSource` / `ConversationSource` / `SystemSource` | 上下文桩 | context/sources.py，返回 []，未注册进 builder | 高 |

---

## 二、悬空 / 幻影开关（配置层死代码）

| 符号 | 类型 | 说明 | 置信度 |
|---|---|---|---|
| `FEATURE_PERCEPTION` | 悬空开关 | `perception_runtime.py:9` 注释称"生产门控 FEATURE_PERCEPTION"，但 config.py 无此常量、proactive_config 等也无 env 读取 → 真实无门控 | 中 |
| `FEATURE_PROACTIVE_ENGINE` | 幻影开关 | 仅在 `proactive_config.py` 经 env 读取、server.py 经 `getattr(...,True)` 回退；config.py 顶部无 `= bool` 常量定义，仅出现在状态字典 | 中 |

---

## 三、未接线模块（功能完整但无生产入口）

| 模块 | 状态 | 说明 |
|---|---|---|
| `scheduler.py` | 隐藏孤儿 | 提供 `schedule_once/interval/event`、`get_scheduler()` 单例、后台线程、EventBus 发布；全仓除测试外零生产调用；`on_system_event()` 从未注册订阅者 |
| `agent_delegate.py` | 隐藏 | `AGENT_DELEGATE_ENABLED` 默认 off；子进程 `claude.exe -p`，超时 taskkill |
| `planner` / `workflow` | 缺失 | 无独立模块（仅文档/注释蓝图） |
| `cross_device.py` / `devices.py` | 隐藏 | `FEATURE_CROSS_DEVICE`/`FEATURE_MULTI_DEVICE` 默认 off/部分；跨网信令未接 |
| `calendar_reader.py` / `app_focus.py` / `clipboard_monitor.py` | 隐藏 | `FEATURE_CALENDAR_SENSE`/`APP_FOCUS`/`CLIPBOARD_SENSE` 默认 off |
| `always_on.py` | 隐藏 | `FEATURE_ALWAYS_ON` 默认 off |
| `mobile.py` / `mobile-app.*` | 隐藏 | `FEATURE_MOBILE_COMPANION` 默认 off |
| `tool_factory.py` | 隐藏 | `TOOL_FACTORY_ENABLED` 默认 off |

---

## 四、未用/可疑 UI 元素

| 元素 | 说明 |
|---|---|
| `Ctrl/Cmd+U` 快捷键 | command-dock.js 仅提示"打开宇宙视图"，审计文件内无对应 keydown 处理 → 疑似死快捷键 |
| `briefingOverlay` | 独立浮层，无 ESC 绑定（功能可用但缺关闭键） |
| `weather-modal-preview.html` | 开发预览页，非正式入口 |
| `selfcheck.html` | 仅 settings 内引用，非主流程 |

---

## 五、未用的 CSS/JS（部分）

- `companion.css.tmp` / `execution-channel.css.tmp` / `*.bak.zzstep1`：旧版 CSS 备份，无任何链接引用。
- 旧 RAG 知识层代码：已移除（无残留 import，仅文档提及）。

---

## 六、处理建议（仅分析，不实施）

1. **高置信度死文件**（一次性脚本、空残留、`.tmp`/`.bak`、personalization.py）→ 可安全删除，零行为影响。
2. **未接线感知模块**（perception_*）→ 决定"接真实模型 or 正式标记为 Experimental 并降级"。
3. **悬空/幻影开关** → 要么补定义，要么从注释删除，消除误导。
4. **隐藏孤儿**（scheduler/跨端/移动/常驻/工具工厂/委托）→ 产品决策"投入 or 废弃"，废弃则删除。
5. **死快捷键** → 实现或移除提示文字。

> ⚠️ 本阶段**禁止删除/修改**，上述均为"待 Review 决策清单"。
