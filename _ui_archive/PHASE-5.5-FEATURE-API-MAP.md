# PHASE 5.5 · MAP-C — Feature → API → Capability 映射

> FEATURE_REGISTRY = **47** 项；FEATURE_API_MAP 显式映射 **10** 项；其余走 heuristic `featureRoute`。
> ⚠️ 唯一命中 deprecated `/api/capabilities` 的特性：`capabilities`（id，vis=default，命令面板入口）。`capability-os` 正确指向 `/api/capability_os/catalog`。

| feature id | name | cat | vis | API 路由 | deprecated? | cap 关联 |
|---|---|---|---|---|---|---|
| start-all | 启动小6 | E | hidden | `/api/start/all` |  |  |
| web-ui | 对话界面 | A | default | `/api/web/ui` |  |  |
| avatar-ui | 数字人界面 | C | hidden | `/api/avatar/ui` |  |  |
| open-project | 打开项目目录 | C | hidden | `/api/open/project` |  |  |
| health | 后端健康 | D | hidden | `/api/health` |  |  |
| ready | 就绪状态 | D | hidden | `/api/ready` |  |  |
| boot-state | 启动状态机 | D | hidden | `/api/boot/state` |  |  |
| sysmon | 系统监控 | D | hidden | `/api/sysmon` |  |  |
| logs | 后端日志 | D | hidden | `/api/logs` |  |  |
| selfcheck | 启动自检 | D | hidden | `/api/selfcheck` |  |  |
| capabilities | 能力目录 | A | default | `/api/capabilities` | 🚫 YES | registry(catalog/foundation) |
| capability-os | Capability OS | B | advanced | `/api/capability_os/catalog` |  | catalog_view/foundation_view |
| version | 版本信息 | D | hidden | `/api/version` |  |  |
| asr-status | 语音识别状态 | D | advanced | `/api/asr/status` |  |  |
| wakeword | 唤醒词状态 | D | advanced | `/api/wakeword` |  |  |
| system-prompt | 系统提示词 | B | advanced | `/api/system-prompt` |  |  |
| memory | 记忆中心 | A | default | `/api/memory` |  |  |
| conversations | 对话历史 | A | default | `/api/memory/conversations` |  |  |
| important-dates | 重要日期 | A | default | `/api/memory/important-dates` |  |  |
| notes | 笔记 | A | default | `/api/notes` |  |  |
| knowledge | 知识库 | A | default | `/api/knowledge` |  |  |
| user-model | 用户画像 | B | advanced | `/api/user_model` |  |  |
| personal-ai | Personal AI 画像 | B | advanced | `/api/personal_ai` |  |  |
| episodes | 情节记忆 | B | advanced | `/api/episodes` |  |  |
| tasks | 任务列表 | A | default | `/api/tasks` |  |  |
| goals | 目标列表 | A | default | `/api/goals` |  |  |
| weather | 天气 | A | default | `/api/weather` |  |  |
| hotspots | 热点 | A | default | `/api/hotspots` |  |  |
| geo | 定位与天气 | A | default | `/api/geo` |  |  |
| briefing | 每日简报 | A | default | `/api/briefing` |  |  |
| calendar | 日历事件 | A | conditional | `/api/calendar/events` |  |  |
| perception-status | 感知状态 | B | advanced | `/api/perception/status` |  |  |
| perception-screen | 屏幕信息 | B | advanced | `/api/perception/screen` |  |  |
| perception-window | 活动窗口 | B | advanced | `/api/perception/window` |  |  |
| perception-ocr | 屏幕 OCR | B | advanced | `/api/perception/ocr` |  |  |
| perception-describe | 屏幕描述 | B | advanced | `/api/perception/describe` |  |  |
| proactive-status | 主动智能状态 | B | advanced | `/api/proactive/status` |  |  |
| proactive-agent | Proactive Agent | B | advanced | `/api/proactive_agent/status` |  |  |
| self-awareness | 自我认知 | B | advanced | `/api/self_awareness/status` |  |  |
| agent-state | Agent 状态 | A | default | `/api/agent/state` |  |  |
| hud-state | HUD 状态 | B | advanced | `/api/hud/state` |  |  |
| focus-app | 应用焦点 | A | conditional | `/api/focus/app` |  |  |
| clipboard | 剪贴板历史 | A | conditional | `/api/clipboard/history` |  |  |
| export-data | 数据导出 | C | hidden | `/api/export/data` |  |  |
| open-config | 打开配置目录 | C | hidden | `/api/open/config` |  |  |
| open-docs | 打开文档目录 | C | hidden | `/api/open/docs` |  |  |
| github | GitHub 仓库 | C | hidden | `/api/github` |  |  |
