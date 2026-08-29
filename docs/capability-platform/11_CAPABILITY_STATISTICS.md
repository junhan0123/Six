# 11 · 能力统计（Capability Statistics）— Stage K

> 全部**自动统计**（基于 01 清单 + 06 死代码审计 + config 扫描）。
> 统计口径：以 `01_CAPABILITY_INVENTORY.md` 的条目为基准；工具按 62 计。

---

## 一、总量统计

| 指标 | 数量 | 来源/说明 |
|---|---|---|
| **能力条目总数** | **~135** | 19 分类合计（含 62 工具） |
| 非工具能力 | ~73 | 135 − 62 |
| API 路由 | ~73 | server.py(do_GET/do_POST) |
| 工具(TOOL_FUNCS) | 62 | tools.py(基础55+Goal5+Knowledge2) |
| DOMAIN 事件 | 71 | eventbus.DOMAIN_EVENT_NAMES |
| SYSTEM 事件 | 22 | eventbus.SYSTEM_EVENT_NAMES(含 Phase3 加 8) |
| 上下文源 | 8 | context/(3 为未注册桩) |
| 页面/视图 | 5 | index/companion/mobile/selfcheck/weather-preview |
| 指令中心命令 | ~30 | command-palette.js |
| 键盘快捷键 | ~8 | 含 1 死快捷键(Ctrl+U) |
| 菜单(主) | 1 | companion #quickMenu |
| Dock | 1 | command-dock |

---

## 二、按分类计数

| 分类 | 数量 |
|---|---|
| Conversation | 4 |
| Knowledge | 8 |
| Memory | 10 |
| Context | 9 |
| Execution | 11 |
| Tools | 62 |
| Goals | 14 |
| Computer | 8 |
| Permission | 3 |
| Proactive | 5 |
| Social | 3 |
| Perception | 7 |
| External | 7 |
| CrossDevice | 2 |
| Personalization | 3 |
| Settings | 3 |
| System | 8 |
| UI | 16 |
| Developer | 5 |

---

## 三、生命周期分布

| 生命周期 | 数量(估) | 占比 |
|---|---|---|
| Production | ~95 | ~70% |
| Beta | ~12 | ~9% |
| Experimental | ~8 | ~6% |
| Hidden | ~14 | ~10% |
| Internal | ~3 | ~2% |
| Deprecated | 0 | 0% |
| Legacy(fallback) | ~2 | ~1.5% |
| Dead | ~12 | ~9% |
| Missing(蓝图) | 2(Planner/Workflow) | — |

> 注：部分能力跨多标签(如 Hidden 同时是 Beta)；此处按主标签计，有重叠。

---

## 四、Feature Flag 统计

| 类型 | 数量 | 说明 |
|---|---|---|
| `FEATURE_*` 开关 | ~27 | config.py 实际消费(~25) + 幻影1(FEATURE_PROACTIVE_ENGINE) + 悬空1(FEATURE_PERCEPTION) |
| 运行时默认开启 | ~20 | 绝大多数 env 默认 "true" |
| 运行时默认关闭 | ~7 | AVATAR_SCENE/ALWAYS_ON/CROSS_DEVICE/MOBILE_COMPANION/CALENDAR_SENSE/APP_FOCUS/CLIPBOARD_SENSE/MEMORY_DISTILL |
| 非 FEATURE 配置项 | ~20 | AGENT_RUNTIME_AUTO / AGENT_POLICY_DEFAULT / SANDBOX_* / REMOTE_* / FEISHU_WS_ENABLED / XIAO6_KWS_ENABLED 等 |
| 声明默认≠运行时默认 | 全量 | config.py 常量多为 False，reload 翻 true（一致性风险） |

---

## 五、重复/死代码统计

| 指标 | 数量 |
|---|---|
| 重复能力组 | 11 (D1–D11) |
| Toast 系统 | 5+ 套 |
| Overlay/Modal/Dialog 管理器 | 12+ 套 |
| 能力视图数据源 | 3 源 |
| 死代码文件 | ~12 |
| 孤儿模块(未接线) | scheduler / perception_*(6) / personalization |
| 悬空/幻影开关 | 2 |
| 幽灵工具名/别名 | LOW_RISK_TOOLS 3 + session_run 1 |

---

## 六、外部依赖统计

| 类型 | 项 |
|---|---|
| LLM | Agnes(agnes-2.0-flash) |
| 语音 | FunASR / edge-tts / vosk / openwakeword(本地) |
| 外部 API | Open-Meteo / wttr.in / ip-api / nmc.cn(台风) / MiniMax(媒体) |
| 桌面 | Windows(Outlook COM / ReadDirectoryChangesW / nvidia-smi) |
| 社交 | 飞书 / Discord / 企业微信(密钥) |

---

## 七、质量信号

| 信号 | 值 |
|---|---|
| 唯一执行入口 | 1 (EXEC-01) ✅ |
| 唯一事件总线 | 1 (eventbus) ✅ |
| 唯一权限系统 | 1 (PolicyEngine+PermissionGuard) ✅ |
| 第二 Runtime | 0 ✅ |
| 重复 UI 子系统 | 多(高优先级待收口) ⚠ |
| 死代码 | ~12(可清理) ⚠ |
| 架构缺口 | Planner/Workflow 缺失、Electron 不存在、感知 Mock |

---

## 八、统计脚本备注

本统计为**人工聚合 + grep 校验**（审计阶段禁止新增脚本运行于生产）。关键校验：
- API 数：`grep -n "def do_GET\|def do_POST"` + 路由字符串统计 ≈ 73。
- 工具数：`grep -c` TOOLS/TOOL_FUNCS = 62。
- 事件数：eventbus.DOMAIN_EVENT_NAMES(71) / SYSTEM_EVENT_NAMES(22)。
- 死代码：grep import/call 确认无引用者（见 06）。
- Electron：grep `require('electron')`/BrowserWindow/ipcMain = 0。

> 统计口径透明，供 Review 复核。如需精确数字，可后续在开发 Phase 用脚本重算（不在本审计范围）。
