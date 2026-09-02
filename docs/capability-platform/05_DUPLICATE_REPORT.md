# 05 · 重复能力审计（Duplicate Capability Audit）— Stage E

> 仅**记录**重复，不删除、不修改。所有重复项归原分类并标 `duplicate`。
> 重复危害：维护分歧、行为不一致、体积膨胀、焦点/事件管理混乱。

---

## 重复能力汇总（10 组 + UI 子系统群）

| # | 重复组 | 成员 | 类型 | 风险 | 建议(仅分析) |
|---|---|---|---|---|---|
| D1 | 天气数据源 | `weather.py`(Open-Meteo,供 LLM) / `geo_weather.py`(wttr+open-meteo+ip-api,供扫描/定位) | 逻辑重叠 | 中 | 收敛为单天气适配 |
| D2 | 截图实现 | `capture_provider.RealCaptureProvider`(mss) / `computer_executor._op_capture_screen`(mss/Pillow) | 双路径 | 低 | 统一截图入口 |
| D3 | KWS 链路 | `kws.py`(薄包装 `kws_optimized`) / `kws_optimized.py` / `wakeword.py`(独立 vosk/openwakeword) | 三文件职责近 | 中 | 单 KWS 入口 |
| D4 | 跨端模块 | `devices.py`(登记/心跳) / `cross_device.py`(relay handoff) | 部分重叠 | 中 | 合并或明确边界 |
| D5 | 记忆蒸馏 | `memory._distill_learnings`(→learnings) / `memory_distiller.distill`(→memories) | 双写路径 | 中 | 统一蒸馏 writer |
| D6 | 人格系统 | `persona_engine.py`(稳定基线) / `personality.py`(动态 5 维) | 双系统并存 | 低 | 明确职责(已刻意分层，需文档化) |
| D7 | JSON 抽取助手 | `_extract_json`(goals) / `_extract_tasks_json`(gde) / 近似实现(agent_runtime) | 三份近似 | 中 | 抽公共工具 |
| D8 | Toast 系统 | `OverlayManager.toast`(权威) + `app.js`回退`#toast` + `error-boundary`回退`#zz-error-toast` + `mobile-app`回退`#toast` + `insight-panel`独立`#proactiveToastHost` + `glance-card`(HUD 状态) | 5+ 套 | 高 | 全路由 OverlayManager，删回退 |
| D9 | Overlay/Modal/Dialog | `OverlayManager.open`(权威) + 11 遗留(app modal/briefing/ZZPanel/mic/settings/capabilities/memory/review/command-palette/scene/companion) | 12+ 套 | 高 | 遗留迁移至 OverlayManager，收敛 ESC |
| D10 | 能力视图三源 | `capability-registry.js` / `capabilities-view.js` / `capability-matrix.js`(读 `window.ZZCapabilities`) | 三视图同源 | 中 | 单数据源 + 多视图 |
| D11 | 语义召回范式 | `knowledge_runtime`(已删语义) vs `cognitive/episodic`(embed.py ONNX 语义) | 两套范式并存 | 低 | 明确"知识=关键词、情节=语义"边界 |

---

## UI 重复子系统详述（最高风险）

### Toast（D8）— 至少 5 套
1. **权威**：`overlay-manager.js` `OverlayManager.toast()` → `.zz-toast` / `#zzToastRoot`（Step[3] 统一目标）。
2. `app.js` `toast()` → 调 #1，回退旧 DOM `#toast`。
3. `error-boundary.js` `ZZErrorToast` → 调 #1，回退 `#zz-error-toast`（独立红/琥珀样式，不走统一令牌）。
4. `mobile-app.js` `toast()` → 调 #1，回退 `#toast`。
5. **真正并行重复**：`insight-panel.js` `proactive-toast`（`#proactiveToastHost`）— 独立渲染，未路由 OverlayManager。
+ `glance-card.js` 为独立 HUD 状态卡（并行通知面）。

### Overlay/Modal/Dialog（D9）— 至少 12 套
1. **权威**：`overlay-manager.js` `OverlayManager.open()`（`.zz-overlay`/`.zz-dialog` + 栈 + 中央 ESC）。
2. `app.js` `showModal()`(`.modal-mask/.modal-card`) — 独立，自带 ESC。
3. `app.js` `briefingOverlay`(`.briefing-overlay`) — 独立，无 ESC 绑定。
4. `app.js` `openZZPanel()`(`#zzPanel`) — 独立侧栏，自带 ESC。
5. `settings.js` `settingsOverlay/settingsPanel` — 独立，自带 ESC。
6. `capabilities-view.js` `capOverlay/capPanel` — 独立，自带 ESC。
7. `memory-panel.js` `memory-panel` — 独立(`role=dialog`)，自带 ESC。
8. `review.js` `review-panel` — 独立，自带 ESC。
9. `command-palette.js` `cpOverlay` — 独立 overlay。
10. `app.js` `mic-overlay` — 独立语音浮层。
11. `scene.js` `scene-layer` — 独立卡片面。
12. `companion.js` `quickMenu/notify/cmdBubble/statusBubble` — 伴侣专属。

> 后果：18+ 去中心化 ESC 监听（overlay-manager 注释已证实）；焦点陷阱/inert 全项目 0 处；z-index 令牌曾失效（Overlay Step[1] 已修数值，但提层与焦点收尾未做）。

---

## 其他重复/近似

- **LOW_RISK_TOOLS 幽灵名**：`profile_read`/`profile_write`/`reminder_add` 不匹配真实工具（`profile_get`/`profile_set`/`reminder_set`）→ 自动执行白名单失效部分预期。
- **`_INTENT_TOOLS` 幽灵别名** `session_run`：映射 run_shell/session_state，无对应 intent/工具名，永不被命中。
- **`/api/memory/important-dates`** GET(L301) + POST(L1029) 双层注册（无冲突，仅提示）。

---

## 重复处置原则（仅记录，不实施）

1. **UI 子系统**（D8/D9/D10）优先级最高：Phase 3 已建权威 `OverlayManager`，但遗留未迁移 → 建议后续 Phase 收口（不在本审计范围）。
2. **后端逻辑重复**（D1–D7, D11）：建议抽公共工具 / 单适配，但**禁止在本 Phase 修改**。
3. **幽灵名/别名**：属配置错误，建议清理（不实施）。
