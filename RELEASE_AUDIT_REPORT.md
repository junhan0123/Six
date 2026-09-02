# Xiao6 v1.0.0 Release Audit Report · v2（含 UI 专项）

> 审计日期：2026-08-28（第二轮） · 性质：只读审计（未修改任何代码） · 基准：tag `v1.0.0-rc1` + 工作区现状
>
> 与上轮相比的重大变化：R8-P0~P4 与 R8-UI 已入库并打 **tag v1.0.0-rc1**（93e2a6b）；launcher_config.json 已补齐；版本改为 SSOT 读取。但同时工作区出现 **181 个未提交变更**（ZhuangZhou→Xiao6 品牌清扫 + Trust Layer 观测点 + 全新 xiao6-space UI），再次形成"tag 与工作区脱节"。

---

## 一、上轮发现修复验证

| 上轮编号 | 结论 | 本轮验证 |
|---|---|---|
| P0-1 Agnes 密钥未轮换 | **仍开放** | `.env` 仍为泄露史同一密钥 `sk-RPu6...ZWB4L` |
| P0-2 R8 未提交 | **已修复** | 93e2a6b 入库 + tag v1.0.0-rc1 |
| P0-3 launcher_config.json 缺失 | **已修复** | 文件存在，start.ps1 可读 |
| P1-1 `_serve_file` 路径穿越 | **仍开放且扩大** | 防护未加；新路由 `/xiao6-space` 再增 2 个入口（见 N-1） |
| P1-2 版本未统一 | **大部分修复** | `config.py:217 APP_VERSION = _read_version()`（SSOT 读根 VERSION）；但 package.json / pyproject.toml 仍缺失 |
| P1-3 重复树 | **仍开放** | `release/` 与 `xiao6-ui/xiao6-ui/` 均仍在；另发现 `server_backup.py`（server.py 全量副本，已跟踪且被修改） |
| P1-4 ok 判定前缀匹配 | **仍开放** | api.py 未提交 diff 仅新增 TOOL_RISK_CHECKED 观测，判定逻辑未动 |
| P1-5 CSRF | **仍开放** | `_read_json` 仍不校验 Content-Type |

---

## 二、UI 专项审计（本轮新增）

审计范围：`xiao6-space/`（新 UI-R1 三栏壳，9 JS + 7 CSS）、`zz-space/`（R8 恢复的现行入口）、`index.html`（入口重定向）、`xiao6-desktop/pet/`（Electron 桌宠）。UI 所用 20 个后端端点逐一比对 server.py 路由，**全部存在**。

### 质量合格项（值得肯定）

- **XSS 纪律完整**：所有已加载 JS 统一 `esc()` 转义；timeline.js 流式 Markdown 渲染器先 esc 后内联（code/table/inline 均覆盖），链接 href 经转义防属性注入（timeline.js:57-78）；approval/intent/risk 卡片均 esc（approval.js:30、timeline.js:116-121、agent-panel.js 全部）
- **架构纪律好**：api.js 唯一网络层（`/api/` 字符串集中）、EventSource 冻结契约、state.js 单一状态实例 + 订阅制、审批 ticket 全链路（uuid4 不可猜 → policy_engine.request_approval 挂起 Event → POST /api/agent/approval 唤醒，policy_engine.py:257-300）端到端闭环、无 Goal 上下文默认拒绝（:260-261）
- **pet.html 资源全本地**（lottie/robot json 均本地，无远程加载）

### UI 新发现

### N-1 · P1 `_serve_file` 路径穿越（旧 P1-1，入口扩大）

- **位置**：`server.py:757-764`（无 realpath/".." 校验）；新增入口 `server.py:728-729`（do_GET）、`:781-782`（do_HEAD）：`_serve_file("xiao6-space" + path[len("/xiao6-space"):])`
- **影响**：raw 请求 `GET /xiao6-space/../xiao6-ui/.env` → 拼接后为 `xiao6-space/../xiao6-ui/.env` → 读取含 API Key 的 .env。两个新入口与旧入口同一缺陷
- **建议**：`_serve_file` 内统一 `os.path.realpath` 后校验前缀必须位于服务根内；四处入口（/static/、任意路径、/xiao6-space×2）自动收口

### N-2 · P1 xiao6-space 整目录未入库，tag 中不存在

- **位置**：`git ls-files xiao6-ui/xiao6-space` = **0**（20 个文件全部未追踪）；server.py:728 路由本身也在未提交修改中
- **影响**：v1.0.0-rc1 tag 不含新 UI——按 tag 检出/发布时 `/xiao6-space` 路由 404。与"R8 入库"的修复形成对照，**新一轮"工作区与 tag 脱节"正在重演**（本轮未提交变更共 181 项：品牌清扫 + Trust Layer + UI-R1）
- **建议**：将品牌清扫、Trust 观测点、UI-R1 收敛为 rc2 提交并重新打 tag；建立规则：任何"冻结/RC"声明必须以 tag 内容为准

### N-3 · P1 双 UI 并存且新 UI 无入口

- **位置**：`index.html`（重定向 → `/zz-space/index.html`，已入库）；`zz-space/index.html` 仅引用 zz-workspace.js/css，无任何指向 xiao6-space 的链接；`xiao6-space/index.html` 仅能手输 URL 到达
- **影响**：UI-R1（三栏壳 + Agent 面板 + 信任分析 + 审批卡）是产品方向，但用户实际只能到达 zz-space 旧 UI；两套 UI 双倍维护面，事件方言也不同（chat 通道 `tool_start/tool_end` vs `/api/stream` 通道 `tool_started/tool_finished`）
- **建议**：明确单一 canonical UI：要么 index.html 切换指向 xiao6-space 并冻结 zz-space 为 legacy，要么暂停 UI-R1 直至切换决策

### N-4 · P1 Electron 桌宠安全配置违规

- **位置**：`xiao6-desktop/pet/main.js:26-30`：`nodeIntegration: true, contextIsolation: false`
- **影响**：违反 Electron 安全基线。当前 pet.html 全本地资源，风险被"无远程内容"缓解；但一旦后续加入远程表情/公告/更新检查，即升级为渲染进程→Node 全权 RCE
- **建议**：`contextIsolation: true` + `preload.js` 白名单暴露 `ipcRenderer.invoke`；pet.js 仅使用受控 API（当前仅 ipcRenderer，改造量小）

### N-5 · P2 UI 假成功：审批提交失败被吞，卡片仍显示"已批准"

- **位置**：`xiao6-space/js/approval.js:42-43`：`fetch('/api/agent/approval...').catch(function () {})` 后无条件执行 `card.innerHTML = '<div>已批准/已拒绝</div>'`；同款逻辑在 zz-space/js/zz-workspace.js:285-286、653-654
- **影响**：网络断开/后端未收到/ticket 已过期（300s 超时后 resolve 返回 False）时，用户看到"已批准"但执行实际按 timeout=reject 处理——**审批环节的假成功**，与 R8-P2 消灭后端假成功的方向直接冲突
- **建议**：在 .then 中检查响应 `ok/exists`，失败时卡片显示"提交失败 · 请重试"并恢复按钮；顺带处理 resolve() 对已超时 ticket 返回 False 的提示

### N-6 · P2 审批文案品牌残留（用户可见）

- **位置**：`policy_engine.py:273`：`summary or f"庄周请求执行工具 {tool}"` —— 审批卡描述直接展示"庄周"；`asr.py:235` whisper 提示词含"庄周"；另有多处 py 文件 docstring"庄周"（不面向用户，降级 P3）
- **影响**：改名清扫（181 文件）未覆盖 policy_engine.py/asr.py，用户在最高风险交互（工具审批）中看到旧品牌
- **建议**：清扫遗漏清单化（庄周 字样全量 grep），用户可见面优先；"XIAO6_*" 环境变量改名后需同步检查 .env/文档/启动器的一致性

### N-7 · P3 审批超时无 UI 反馈

- **位置**：`policy_engine.py:280-283`（ev.wait(300) 超时 → 返回 "timeout" → 按拒绝处理，无事件发布）；UI 卡片停留在"等待确认"永不更新
- **建议**：超时时 publish 一条 `modal`/`approval_timeout` 事件，前端关闭或置灰对应卡片（按 ticket 匹配）

### N-8 · P3 同名并发工具的状态串扰

- **位置**：`agent-panel.js:206`：`tool_finished` 按 `x.tool === tname` 匹配进行中的项——同名工具并发时全部标记完成/失败
- **建议**：事件携带 execution/tool call id，前端按 id 匹配

### N-9 · P3 命令面板动态端点 404

- **位置**：`palette.js:105`：id 直译为路径——`proactive-agent` → `/api/proactive/agent`（后端实际为 `/api/proactive_agent/...` 下划线，server.py:498 区域）；`self-awareness` → `/api/self/awareness`（无此路由）
- **影响**：对应能力点击后显示"null"/（空）
- **建议**：FEATURE_REGISTRY 显式携带 `endpoint` 字段，禁止字符串拼装

### N-10 · P3 死文件与副本

- `xiao6-space/js/xiao6-workspace.js`（67KB）：index.html **未加载**，内容与 timeline/approval/agent-panel 大面积重复（含同款审批假成功 bug ×2），未来必漂移
- `server_backup.py`：server.py 全量已跟踪副本且被本轮修改同步改动——无任何 import 引用
- **建议**：删除死文件；副本类文件移出仓库或加 CI 重复检测

---

## 三、未闭合旧项（沿用上轮编号与建议）

| 编号 | 级别 | 现状摘要 |
|---|---|---|
| P0-1 | P0 | 密钥仍在用且在 git 历史 3 个提交中；轮换是唯一止血手段 |
| P1-1 | P1 | 穿越未修 + 新入口 ×2（并入 N-1） |
| P1-3 | P1 | release/ + xiao6-ui/xiao6-ui/ + server_backup.py 三处副本 |
| P1-4 | P1 | ok 判定仍靠中文前缀清单 |
| P1-5 | P1 | CSRF 面（本机浏览器 no-cors 可调全部 POST API） |
| P2-1 | P2 | 执行入口异常无堆栈日志 |
| P2-2 | P2 | 207 处 bare except |
| P2-3 | P2 | 终态事件可能双发 |
| P2-4 | P2 | ContextBudget 无锁 |
| 依赖 | P2 | package.json / pyproject.toml 仍缺（依赖无清单锁定） |

---

## 四、Release Readiness 结论（第二轮）

### 六维评分（上轮 5.5 → 本轮）

| 维度 | 上轮 | 本轮 | 说明 |
|---|---|---|---|
| Runtime | 7 | 7 | api.py 仅增观测点，主体稳定；TRUST 观测链验证通过（tool_risk.py 存在、eventbus 注册） |
| Git | 3 | 5 | rc1 tag 建立；但 181 项新变更再度脱节（含整个 UI-R1） |
| Frontend | 7 | 6 | zz-space 已入库且质量合格；但 UI-R1 孤岛、双 UI 并行、审批假成功 UI |
| Security | 5 | 5 | 密钥未轮换、穿越、CSRF 原样；新增 Electron 违规 |
| Version | 4 | 7 | SSOT 落地；余 package.json/pyproject 缺失 + 用户可见"庄周"残留 |
| Doc/Test | 6 | 6 | 无变化 |
| **加权** | **5.5** | **≈6.0** | 工程治理改善，但新欠账（UI-R1 未入库）抵消部分进展 |

### 发布判定

**仍不可发布，较上轮接近一步。** 当前定位：**B→A 之间（开发稳定版后期）**。

阻断顺序建议：
1. **P0-1** 密钥轮换（唯一 P0）
2. **N-2** 将 181 项工作区变更（品牌清扫 + Trust + UI-R1）收敛为 rc2 提交打 tag
3. **N-1** `_serve_file` 加 realpath 白名单（一处修复覆盖 4 个入口）
4. **N-5** 审批假成功修复（UI 层检查响应）
5. **N-3** 决策 canonical UI 并接通入口
6. **P1-4/P1-5/依赖清单** 收口后复评

> 本报告基于 tag v1.0.0-rc1 与工作区实际代码取证，未修改任何文件。
