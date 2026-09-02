# 小6 v2 后续开发计划（Phase 5 收尾 + 前瞻）

> 制定时间：2026-08-01
> 制定人：Senior Developer（高级开发工程师）
> 当前代码基线：`f45beef`（P5-1 功能开关面板 + P5-2 每日简报「今日建议」渲染）

---

## 一、当前状态

- **已落地**：Phase 1–5 主体功能——Context Engine、世界模型、人格源、目标系统（Goal+Task）、沉浸视觉（Three.js 粒子/玻璃拟态）、知识增强（向量 RAG）、主动智能 V2（停滞提醒/周小结/今日建议）、多端同步（设备注册）。
- **代码工作树**：干净。仅余运行数据缓存（`geo-weather.json` / `habits.json` / `devices.json`），非源码、不纳入提交。
- **运行后端**：仍跑旧代码，需你从桌面双击 `F:\桌面\start-xiao6.bat` 重启 Electron（端口 8000）加载新能力。

---

## 二、本轮侦查发现的真实缺口（3 项）

| # | 缺口 | 证据 | 影响 |
|---|------|------|------|
| G1 | **SSE 双连接 + 简报可能双推** | `app.js:1597` 与 `main-cognitive.js:145` 各自开一个 `/api/stream`；后端 `_handle_stream`（server.py:1688）支持多连接，但两连接几乎同时建立时 `last_briefing_date` 去重存在竞态 | 每日简报可能推两次；长连接/队列资源重复 |
| G2 | **前端无全局错误兜底** | 全仓无 `window.onerror` / `unhandledrejection` | 单点未捕获异常可整页失效，排查困难 |
| G3 | **/api/health 缺 Phase 4 能力状态** | health（server.py:178）调 `run_self_check`（self_check.py），未反映 4 个 FEATURE flag 与知识库/设备状态 | 运维/自检看不到新能力开闭，排障盲 |

---

## 三、Phase 5：体验打磨与可控性收尾（进行中）

### P5-3 健壮性收尾（建议下一轮直接做）

#### 5-3-1 · SSE 统一为单例管理器 ⭐ 优先级最高
- **方案**
  - 新建 `sse-manager.js`：全局单例 `EventSource('/api/stream')`，指数退避重连（1s→2s→4s→…≤30s），通过 `CustomEvent('zz:sse')` 向各模块广播；暴露连接状态（`connecting`/`open`/`reconnecting`）。
  - `app.js`（`connectProactive`）、`main-cognitive.js`（`connectSSE`）改为**订阅该单例**，不再各自开流。
  - 后端 `_handle_stream` 的 briefing 去重加锁（先写 `last_briefing_date` 再判断，或用 `SUBSCRIBERS_LOCK` 串行化首推），根治双推。
  - 顶部加细连接状态指示（与语音球态联动，可选）。
- **验收**：模拟后端重启 → 前端 3s 内自动重连、状态可见、简报只推一次、事件不丢。

#### 5-3-2 · 前端全局错误兜底
- **方案**：根 `app.js` 顶部加 `window.onerror` + `unhandledrejection` 捕获 → 非阻塞提示条（含「重试」）+ 控制台详细堆栈；语音/球态等关键模块异常隔离，避免单点拖垮整页。
- **验收**：人为抛错不导致整页白；错误有可见反馈且可继续操作。

#### 5-3-3 · /api/health 补 Phase 4 能力状态
- **方案**：`self_check.py` 增加 4 个 FEATURE flag 检测（`premium_ui` / `knowledge_rag` / `proactive_v2` / `multi_device`）+ 知识索引条数 / 已注册设备数；`/api/health` 响应透出。
- **验收**：`GET /api/health?refresh=1` 能反映各新能力开闭与资源量。

### P5-4 真机走查打磨（需你重启 Electron 后按反馈修）
- 地球旋转 / 语音球交互手感
- 热点面板交互（含已修的扫描线）
- 主题切换无闪烁（`body[data-theme]`）
- 简报 `suggestions` 实机渲染
- 我出**观察清单**，你走查后报点，我定点修（不提前大改，避免无真机验证的盲动）。

---

## 四、前瞻路线（待你拍板是否纳入本期）

- **Phase 6 · 白龙马能力搬运收尾**：审计白龙马 v1 未搬能力（rules / scene / persistent-shell / software-install / video + 7 架构缺口：KWS / 审视 / 地图 / 文档 / 记忆审计 / 多 LLM / 自适应心跳），逐项落地或显式弃用。
- **Phase 7 · 部署与打包**：Electron 打包脚本、启动健壮性、离线 / 自更新。

---

## 五、执行纪律（沿用）
- 纯本地 git，确认后再提交；小步提交、不推翻 Phase 1–3 架构。
- FEATURE flag 门控新增能力，默认开、可瞬切。
- 前端改动后 **bump `index.html` 的 `?.js?v=` / `?.css?v=`**，重启 Electron + Ctrl+F5 强刷才生效。
- 真机验证：改完请你重启后端走查，我据反馈定点修。

---

## 六、建议执行顺序
1. **下一轮**：P5-3（5-3-1 → 5-3-2 → 5-3-3），一次性提交。
2. **你重启走查**：验证 P5-1/P5-2/P5-3，反馈 → P5-4 定点修。
3. **视情况**：启动 Phase 6 或 Phase 7（你拍板）。
