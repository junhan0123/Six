# 小6 Xiao6 v1.4.0 — PHASE 3.1 GUI HEALTH REPAIR · FINAL REPORT

> 阶段性质：IMPLEMENT / READ-WRITE（仅 GUI 前端 / Interaction Layer）
> 身份：Senior Frontend Engineer + GUI Runtime Integration Engineer
> 唯一 Runtime：G:\xiao6\xiao6-ui\server.py（http://localhost:8010，全程未改）
> 生成时间：2026-08-18

---

## 1. Status

```
COMPLETE（1 项 Runtime 端环境异常不阻断，已如实记录）
```

- 10 个高级功能死入口：GUI 映射已修复（9 个 Runtime 返回 200；1 个 `/api/user_model` 返回 500，为 Runtime 缺失 `numpy` 依赖导致，非 GUI 映射错误，超出本阶段范围）。
- 4 个 GUI 孤儿文件：已归档并移出活动树。
- 双 Orb：已合并为单一视觉陪伴球（#orbPresence）。
- toolModes/autoSpeak：已实现单一状态源 + 双向同步（并修复此前死掉的「设置开关」交互）。
- 错误态：已补齐，普通用户不再看到空白/原始路径/状态码。

---

## 2. 修改文件

### MODIFIED
| 文件 | 修改点 |
|------|--------|
| `G:\xiao6\xiao6-ui\xiao6-space\js\zz-workspace.js` | ① 新增 `FEATURE_API_MAP` + `featureRoute()`，重写 `openFeature()`（显式映射 + 产品语言错误态）；② 新增 `syncToolUI()` 单一状态源同步；③ 对话头工具按钮点击后改调 `syncToolUI()`；④ 设置 `change` 监听末尾补 `syncToolUI()`；⑤ `init()` 改用 `syncToolUI()` 并新增 `settingsBody` 点击监听（修复此前死的设置开关） |
| `G:\xiao6\xiao6-ui\xiao6-space\index.html` | `#orbBtn` 去「第二球」视觉：移除 `<span class="zz-mini-orb">`，改为纯对话快捷按钮（💬），title/aria-label 改为「对话」 |

### DELETED（先归档，可回退）
归档目录：`G:\xiao6\_ui_archive\2026-08-18\gui\`
- `xiao6-space/js/zz-space.js`
- `xiao6-space/css/zz-space.css`
- `xiao6-space/vendor/three.min.js`
- `xiao6-space/vendor/lottie.min.js`
- `xiao6-space/assets/lottie/`（holographic.json / siri.json）

### UNCHANGED（架构边界守纪）
`server.py`、`server_handlers_*.py`、`agent_runtime.py`、`capability_os/`、`policy_engine.py`、`executor/`、`EventBus`、`Memory`、`Context`、`DB`、`config.py`、`.env`、`electron/`、`G:\xiao6-hub`、`G:\xiao6\deepseek-harness-studio`、`desktop-avatar/dyna-orb.js`、`desktop-avatar/dyna-orb-voice.js`、`/api/stream`、`localStorage['xiao6_sid']`。

---

## 3. 10 个 API 映射（实测）

| Feature | 旧 GUI 拼接路由（修复前） | 真实路由（FEATURE_API_MAP） | Before | After | HTTP 实测 |
|---------|---------------------------|------------------------------|--------|-------|-----------|
| system-prompt | `/api/system/prompt` | `/api/system-prompt` | 404 | 200 | 200 |
| capability-os | `/api/capability/os` | `/api/capability_os/catalog` | 404 | 200 | 200 |
| proactive-agent | `/api/proactive/agent` | `/api/proactive_agent/status` | 404 | 200 | 200 |
| self-awareness | `/api/self/awareness` | `/api/self_awareness/status` | 404 | 200 | 200 |
| user-model | `/api/user/model` | `/api/user_model` | 404 | 200（命中真实 handler） | **500**（Runtime 缺 numpy，见 §8/§10） |
| personal-ai | `/api/personal/ai` | `/api/personal_ai` | 404 | 200 | 200 |
| calendar | `/api/calendar` | `/api/calendar/events` | 404 | 200 | 200 |
| clipboard | `/api/clipboard` | `/api/clipboard/history` | 404 | 200 | 200 |
| conversations | `/api/conversations` | `/api/memory/conversations` | 404 | 200 | 200 |
| important-dates | `/api/important/dates` | `/api/memory/important-dates` | 404 | 200 | 200 |

> 映射依据：`server.py` 真实路由表（L256–L677）。其余带短横的高级功能（`perception-*`、`proactive-status`、`hud-state`、`focus-app`、`episodes` 等）经 `replace(/-/g,'/')` 已能命中真实路由（如 `/api/perception/screen`、`/api/proactive/status`、`/api/hud/state`、`/api/focus/app`、`/api/episodes`），**未受损**，无需纳入映射。
>
> `featureRoute()` 对映射表外 id 保留 `/api/` + 替换短横的兜底，但**不再猜测子路径**，避免再次出现 `feature id ≠ API route`。

---

## 4. Orb

- **Before**：GUI 内存在两个球视觉——顶栏 `#orbBtn .zz-mini-orb`（L70 `setState` 更新）与常驻 `#orbPresence`（L736 点击→`startVoice`）。
- **After**：仅保留 `#orbPresence` 作为唯一视觉陪伴球 + 唯一 Voice 入口。`#orbBtn` 移除 `.zz-mini-orb` 元素，改为普通「对话」快捷按钮（emoji 💬，无球视觉），其原有「切到对话视图」行为保留（且导航区本就有「对话」按钮，功能不丢）。
- **Electron 集成**：`#orbPresence` 点击 → `startVoice()` → `window.electronAPI.focusOrb()`（L305）链路完整保留，未破坏。
- **Voice 回归**：`dyna-orb-voice.js` 未改动；`/desktop-avatar/dyna-orb.html` HTTP 200；`startVoice` 在 Electron 下走 `focusOrb`，浏览器下走 `getUserMedia`→`/api/asr`→`/api/chat`，逻辑未变。

---

## 5. State（toolModes / autoSpeak）

- **单一状态源**：`toolModes`（think/web/code）与 `autoSpeak` 本就是闭包内单一变量（非 headerState/settingsState 各存一份）。
- **新增 `syncToolUI()`**：以单一源驱动「对话头工具按钮」与「设置开关」两处视觉，任一修改后双向同步。
- **修复死掉的「设置开关」**：原 `.zz-switch` 是 `<span>`，仅有 `body.addEventListener('change',…)` 监听，而 `<span>` 永不触发 `change` → 设置开关此前**完全无法点击切换**（既存缺陷）。本阶段在 `init()` 为 `$('settingsBody')` 增加 `click` 监听，使开关可切换并同步到对话头。
- **验证（代码级）**：
  - 对话头改 → `syncToolUI()` → 设置开关同步；
  - 设置改（点击）→ 更新源变量 → `syncToolUI()` → 对话头同步；
  - 不会出现「设置开 / 对话头关」。

---

## 6. Error Model（高级功能 overlay）

| 情形 | 用户可见文案（产品语言） | 是否暴露内部细节 |
|------|--------------------------|------------------|
| loading | 正在打开能力… | 否 |
| success | JSON 详情（`esc` 转义） | 否 |
| empty | 暂无可显示内容 | 否 |
| 404 | 这个能力暂时无法打开 | 否 |
| 502/503/504 | 小6 Runtime 当前不可用，请稍后再试 | 否 |
| 其他 !ok | 这个能力暂时无法打开 | 否 |
| network error（fetch 抛错） | 小6 Runtime 当前不可用，请稍后再试 | 否 |

- 已**移除**原先在 overlay hint 展示 `/api/xxx` 内部路径的写法（改为「小6能力详情」）。
- 普通用户不会看到 `404`/`500`、原始 `/api/...` 路径或 stack trace；开发者诊断可保留于控制台（本阶段未引入新的开发入口）。

---

## 7. Cleanup（已删除/归档）

归档位置：`G:\xiao6\_ui_archive\2026-08-18\gui\`（同卷 mv，可回退）
- `js/zz-space.js`（82 KB，旧 Galaxy/Space 遗留）
- `css/zz-space.css`（55 KB）
- `vendor/three.min.js`（603 KB，3D 库，无活动引用）
- `vendor/lottie.min.js`（305 KB，动画库，仅旧 lottie 体系使用）
- `assets/lottie/`（holographic.json / siri.json）

删除前已全局 grep 确认 `index.html`、`zz-workspace.js`、`zz-workspace.css`、Electron、launcher、Runtime 均无活动引用（仅 `zz-space.js` 自引用与 `desktop-avatar` 各自独立的 lottie 命中，互不影响）。

---

## 8. Regression

| 项 | 结果 | 说明 |
|----|------|------|
| Chat（普通聊天） | PASS | `/api/chat` 未改；smoke + PHASE 2 实测 SSE 正常 |
| Streaming | PASS | 未触及 SSE 协议 |
| TTS | PASS | `speakText` 未改；`/api/speak` 200 |
| Voice | PASS | `dyna-orb-voice.js` 未改；`#orbPresence`→`startVoice`→`focusOrb` 完整 |
| Approval | PASS | 未触及审批流；`/api/agent/approval` 未改 |
| Capability | PASS | tool_start/tool_end 链路未改 |
| Memory | PASS | Memory 未改 |
| Tasks | PASS | `/api/tasks` 未改 |
| Settings | PASS | 设置开关现已可交互且双向同步 |
| Command Palette | PASS | `openFeature(f.id)` 仍经 `FEATURE_API_MAP` 取真实路由 |

- **静态审计**：`node --check xiao6-space/js/zz-workspace.js` → `JS_SYNTAX_OK`；删除后重新 grep `zz-space|lottie|three.min` 于活动 `xiao6-space` 代码 → **0 命中**。
- **Smoke（全部 200）**：`/`、`/xiao6-space/index.html`、`/api/health`、`/api/ready`、`/api/agent/state`、`/api/asr/status`、`/desktop-avatar/dyna-orb.html`、`/gui/chat.html`。
- **唯一非 GUI 阻断项**：`/api/user_model` 返回 500，响应体 `{"ok": false, "error": "No module named 'numpy'"}`，属 Runtime Python 环境缺失依赖，非 GUI 回归缺陷（见 §10）。

---

## 9. Git diff / 变更范围

- 本环境未使用 git 管理该目录，以文件清单核对变更范围：
  - 仅 `xiao6-space/js/zz-workspace.js` 与 `xiao6-space/index.html` 被修改；
  - `xiao6-space/js/zz-space.js`、`css/zz-space.css`、`vendor/three.min.js`、`vendor/lottie.min.js`、`assets/lottie/` 移出活动树（归档）；
  - `G:\xiao6\xiao6-ui\server.py` 及所有 `server_handlers_*.py` **未被读取以外的任何写入**；
  - 未产生第二 GUI、第二 Runtime、第二 Voice。

---

## 10. Architecture Guard（架构守护）

| 项 | 状态 |
|----|------|
| Runtime (server.py) | 未修改 ✅ |
| Runtime EventBus 发布逻辑 | 未修改 ✅ |
| `/api/stream` 协议 | 未修改 ✅（本阶段按 §九明确不实现） |
| Memory / Context | 未修改 ✅ |
| Capability Runtime / Policy / Executor | 未修改 ✅ |
| DB schema / 数据 | 未修改 ✅ |
| DSH / Xiao6Hub | 未修改 ✅ |
| Voice Orb (dyna-orb.js / dyna-orb-voice.js) | 未修改 ✅ |
| Session 机制 (`localStorage['xiao6_sid']`) | 未修改 ✅ |
| `featureRoute` 兜底 | 仅兜底，不猜测子路径 ✅ |

**已知 Runtime 端异常（超出本阶段范围，不伪造成功）**：
`GET /api/user_model` → 500 `No module named 'numpy'`。GUI 映射已正确指向真实端点 `/api/user_model`（旧 `/api/user/model` 仍 404 可作佐证），该 500 由 Runtime 运行环境缺 `numpy` 引起，需由 Runtime/依赖侧修复，不在 PHASE 3.1 禁止修改范围内。

---

## 11. 下一阶段建议

**仅建议 PHASE 3.2 — GUI Runtime Event Stream + Panel Integration**（本阶段不实现）：

- 目标：GUI 订阅 `EventSource('/api/stream')`，消费 Runtime 发布的 `panel` / `agent_state` / `hud_state` / `scene` / `proactive` 事件，实现 Voice↔GUI 实时协同（当前 GUI 仅每 8s 轮询 `/api/agent/state`，实时性缺失）。
- 允许范围：GUI/Interaction Layer（`zz-workspace.js`）；新增 `/api/stream` 消费与轻量节流（debounce + 仅更新可见视图）。
- 禁止范围（与 PHASE 3.1 一致）：改 Runtime 发布协议、改 server.py、改 Voice Orb、改 Memory/Policy/Capability、创建第二 Runtime/GUI/Voice。
- 验收：Runtime 发布 `panel` 事件时 GUI 即时渲染对应面板；Agent 状态变更 ≤1s 内反映于 GUI；无刷屏/无内存泄漏。

---

# FINAL VERDICT

```
PHASE 3.1 = COMPLETE
GUI 死链修复      = PASS（10 入口映射修复，9×200；1×500 为 Runtime 端，已记录不阻断）
孤儿清理          = PASS（4 文件 + lottie 资源归档移出，0 活动引用）
双 Orb 合并       = PASS（唯一 #orbPresence；Electron focusOrb 保留）
状态单一源        = PASS（syncToolUI + 设置开关可交互 + 双向同步）
错误态            = PASS（loading/success/empty/404/5xx/network 产品语言）
架构守护          = PASS（Runtime/Memory/DSH/Voice/Session 均未改）
```

**STOP** — 本阶段结束。未进入 PHASE 3.2，未重做 GUI 视觉，未修改 Runtime，等待老板审核。
