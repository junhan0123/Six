# Xiao6 · 智能指挥中枢（界面 v0.1）

一个 **Retro-futuristic HUD 风格** 的个人 AI 助手对话界面，已接入 **Agnes API**（云端大模型 `agnes-2.0-flash`）。
当前阶段：文字对话 + 流式输出 + 核心球状态机 + 遥测面板。语音/工具/主动智能按计划后续接入。

> 界面设计遵循专业 UI 规范：非对称 HUD 网格、玻璃面板、四角括弧、扫描线、Orbitron/Rajdhani/Share Tech Mono 字体、内联 SVG 图标，无 emoji。

---

## 目录结构

```
xiao6-ui/
├── index.html      # 界面结构
├── styles.css      # HUD 视觉样式
├── app.js          # 前端逻辑（流式/SSE + 核心球 + 遥测）
├── server.py       # 本地指挥核心（纯标准库，转发 Agnes，密钥仅存服务端）
├── .env            # ⚠️ 含 API Key，已 gitignore，切勿分享
├── .gitignore
├── start-xiao6.bat # 双击启动脚本（启动核心 + 自动打开浏览器）
└── README.md
```

---

## 运行方式

> 需要 Python 3.10+（当前用 3.13 验证通过）。无需安装任何第三方库。

### 推荐：双击启动（最简单）

直接双击目录里的 **`start-xiao6.bat`**：
- 自动启动 `server.py`
- 自动打开默认浏览器访问 **http://localhost:8000**
- 若核心已在运行，则只打开浏览器

### 备用：终端启动

**1. 确认 `.env` 已配置**（已为你填好 Agnes Key，通常无需改动）：
```env
AGNES_API_KEY=sk-xxxx
AGNES_BASE_URL=https://apihub.agnes-ai.com/v1
AGNES_MODEL=agnes-2.0-flash
```

**2. 启动本地核心**：
```bash
cd G:\Xiao6\xiao6-ui
python server.py
```
看到 `Xiao6 指挥核心已启动 -> http://localhost:8000` 即成功。

**3. 打开界面**：
浏览器访问 **http://localhost:8000**

⚠️ **绝对不能直接双击 `index.html`**，否则浏览器会以 `file://` 协议打开，前端无法连接核心，会显示"核心连接失败"。

---

## 怎么用

- 底部输入框输入指令，**Enter 发送**，Shift+Enter 换行。
- 左侧「快捷能力」/ 中央「提示气泡」可一键发示例问题。
- 右侧「遥测」面板实时显示：核心状态、模型、延迟、Tokens、轮次、人格设定、记忆摘要。
- 顶部「核心在线 / 离线」指示：离线说明 `server.py` 没启动或 Key 有误。
- 麦克风按钮目前为占位（语音阶段接入）。

---

## 自定义

- **换模型**：改 `.env` 的 `AGNES_MODEL`（如 `agnes-2.5-pro-alpha`）。
- **改人格**：`server.py` 里的 `SYSTEM_PROMPT`。
- **换配色/字体**：`styles.css` 顶部 `:root` 变量与 `@import` 字体。
- **换端口**：环境变量 `Xiao6_PORT=9000 python server.py`。

---

## 安全提示

- **Key 只存在服务端 `.env`**，前端永远拿不到，也不会出现在浏览器请求里。
- `.env` 已被 `.gitignore` 忽略，提交代码时不要带上去。
- 当前为本地开发用途，未做鉴权；如要暴露到公网，请自行加一层反向代理鉴权。

---

## 新增能力（Phase 9 环境感知 / Phase 13 多端无感，默认关闭）

以下能力均为 **Windows 专属 / 桌面增强**，默认关闭，需显式在 `.env` 开启。开启后可在「设置 / 功能开关」中瞬时回退。

| 能力 | 开关 | 说明 | 端点 |
| --- | --- | --- | --- |
| 常驻伴随 | `FEATURE_ALWAYS_ON` | 后台轻量心跳常驻，CPU 超 `ALWAYS_ON_CPU_LIMIT(%)` 自动降档 | `GET /api/always-on/status`、`POST /api/always-on/control` |
| 跨端接力 | `FEATURE_CROSS_DEVICE` | 桌面 ↔ 移动 会话无缝交接（防抢占认领） | `GET /api/cross-device/status`、`POST /api/cross-device/relay` |
| 移动伴随端 | `FEATURE_MOBILE_COMPANION` | 移动端轻量简报 + 跨端同步（EventBus `zz.mobile.sync`） | `GET /api/mobile/briefing`、`POST /api/mobile/reminder`、`POST /api/mobile/chat` |
| 日历感知 | `FEATURE_CALENDAR_SENSE` | 读取系统日历（Windows Outlook/COM） | `GET /api/calendar/events`、`GET /api/calendar/next` |
| 应用焦点 | `FEATURE_APP_FOCUS` | 当前前台窗口/应用感知（Windows win32gui） | `GET /api/focus/app`、`POST /api/focus/window` |
| 剪贴板 | `FEATURE_CLIPBOARD_SENSE` | 剪贴板内容监听（Windows win32clipboard，内存历史） | `GET /api/clipboard/history`、`POST /api/clipboard/clear` |

> 所有端点均做 feature-gate：开关关闭时返回 `enabled:false`（POST 返回 404 `disabled`），不影响 `/api/chat` 与 ASR/TTS 主链路。
> 相应模块（always_on / cross_device / mobile / calendar_reader / app_focus / clipboard_monitor）对 Windows 专属依赖做 import 守护，缺失时安全降级、不抛错。

### 性能调优（Phase 4）

所有重负载特性均做 **性能门控 / 默认关闭**，保证常驻主链路（对话 / ASR / TTS）不受拖累：

| 优化项 | 机制 | 收益 |
| --- | --- | --- |
| HUD 光环 | WebGL → Canvas2D → 完全停渲染（<20fps 二级降级，标记 `hud-stopped`） | CPU 峰值可控，主链路优先 |
| KWS 唤醒监听 | 2500ms → 6000ms → 完全暂停（<20fps）三级降频 | 低负载时近乎零占用 |
| 日历感知 | 读取结果 1h TTL 缓存 | 避免重复 COM 轮询 |
| 应用焦点 | 前台窗口 10s 缓存 | 降低 win32gui 轮询 |
| 剪贴板历史 | 内存上限默认 20 条 | 内存有界 |
| 记忆蒸馏 | 对话历史上限 50 条（旧消息压缩） | 内存 / 响应有界 |

默认目标：开启感知类特性时 **CPU < 10%**、常驻内存 **< 150MB**、首 token **< 10s**（`AGNES_REASONING=low`）。
新功能默认关闭，可在「设置 / 功能开关」瞬时回退；特性关闭时端点返回 `enabled:false`（POST 404 `disabled`）。

### 测试

```bash
python tests/run_all.py     # 聚合运行 tests/ 下全部测试（pytest）
```

升级测试（P1 移动 PWA / P2 KWS 精准化 / P3 Skills 完善 / P4 性能调优）新增 30+ 项全部通过；
全量约 215 项，其中 11 项为与升级无关的预存失败（context engine 重构、db shell echo、external asr 依赖缺失），升级相关项全部通过。纯逻辑可测、Windows 专属依赖均有 import 守护。
