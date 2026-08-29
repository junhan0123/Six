# Xiao6 v1.0.0 Independent Audit

> 审计日期：2026-08-28 · 审计方式：独立只读（未修改任何文件、未执行任何修复、未提交 git） · 全部结论基于工作区实际代码与 git 取证

---

## 1. Overall Status

**定位：A. 开发稳定版（未达 Release Candidate）。六维加权 ≈ 3.7/10，不可发布。**

一句话结论：架构骨架（单一 EventBus、PolicyEngine、PermissionGuard 闭环）设计完整且纪律注释良好，但**接线层断裂**——统一执行入口参数契约失效、依赖模块缺失、server_globals 兼容 stub 覆盖了真实安全实现，叠加前端资产缺失与密钥历史泄露，当前版本主链路不可用。

分项报告：

| # | 报告 | 核心结论 |
|---|---|---|
| 1 | TRAE_GIT_AUDIT_REPORT.md | S84-S87 齐全；未提交热修；工程文件/前端未入库；两棵重复树 |
| 2 | TRAE_FRONTEND_AUDIT_REPORT.md | PARTIAL；主资产缺于工作区与历史，可从归档+dangling blobs 恢复 |
| 3 | TRAE_RUNTIME_AUDIT_REPORT.md | P0×3：契约断裂 / policy.py 缺失 / stub 覆盖链 |
| 4 | TRAE_SECURITY_AUDIT_REPORT.md | P0×2：密钥历史泄露 / 边界安全 stub 化 |
| 5 | TRAE_VERSION_AUDIT_REPORT.md | config.py 三处 1.4.0；无 SSOT；package.json/pyproject 缺失 |

---

## 2. Architecture Score

| 维度 | 得分 | 判定 |
|---|---|---|
| Runtime | 3/10 | ❌ |
| Git | 4/10 | ❌ |
| Frontend | 4/10 | ❌ |
| Security | 2/10 | ❌ |
| Version | 4/10 | ❌ |
| Documentation/Test | 5/10 | ⚠️ |
| **加权总分** | **≈3.7/10** | **不可发布** |

设计亮点（值得保留）：EventBus 单例 + 事件名注册校验；PermissionGuard 的 plan→decide→approve→execute→verify 闭环；policy_engine 的 confirm 票据机制；.env 未入库 + 状态探针不回显密钥。

---

## 3. Runtime Status

- ❌ **P0**：`ai_core/execution/api.py:33` 契约为 `context.get("args")`，但全部 5 个调用点（agent_runtime:566 / capability_runtime:181 / reflector:89 / social_inbound:125 / tools:3319）把工具参数当作 context 传入 → **所有工具以空参数执行**
- ❌ **P0**：`agent_runtime.py:551` 依赖 `ai_core.execution.policy` 模块 —— **该模块不存在**；`__init__.py` 内联 `ExecutionPolicy` 类亦无 `get()` 方法 → Goal 工具执行链 ModuleNotFoundError
- ❌ **P0**：HEAD 提交的 server_globals `_is_local_peer = True`（布尔）→ server.py:223 每请求 TypeError；工作区未提交"热修"降级为恒 True（安全回退）
- ❌ 第二执行入口存在：agent_runtime:729、capability_runtime:158、capability_os:259 直调 `execute_tool`（其内部无 Policy）
- ✅ EventBus 仍为唯一总线，无第二 EventBus；但 `_sse_use_eventbus` 被 stub 强制 False，扇出特性实际未启用
- ⚠️ 统一入口 `default_deny` 随 permission_mode 默认为 False，弱于文档声明

## 4. Frontend Status

- **PARTIAL**：工作区缺 index.html / app.js / styles.css / xiao6-space 等主资产；git 历史无完整版本
- ✅ 可恢复：归档目录（_archive/_audit/_verify）+ dangling blobs 提供恢复来源（详见 TRAE_FRONTEND_AUDIT_REPORT.md）
- 结论：UI 层不可启动，产品面缺失

## 5. Security Status

- ❌ **P0**：Agnes 密钥 `sk-RPu6...` 存在于 `S81-FINAL-REPORT.md`，横跨 ≥3 个历史提交（1e24b62 / 2789613 / 93c6194），未轮换、未清洗
- ❌ **P0**：server_globals.py stub（S79.8 minimal compat）经 server.py:188 导入覆盖真实实现：本地校验恒真 / CORS `{"*"}` / `_REMOTE_FORBIDDEN=False` / 脱敏正则=None → **边界安全控制整体失效**
- ✅ `.env` 未被 git 追踪；config 探针只报密钥存在性与长度，不回显值
- ⚠️ S85"凭证锁定"仅阻断后续入库；S86"运行时稳定"实测未达成

## 6. Git Status

- ✅ S84 / S85 / S86 / S87 四个里程碑提交完整存在（S87 为纯文档提交）
- ⚠️ 工作区未提交修改：`server_globals.py`（_is_local_peer 布尔→函数热修）等
- ❌ 未追踪/缺失：根与 xiao6-ui 的 package.json、pyproject.toml、前端主资产
- ❌ 两棵完整重复树入库：`xiao6-ui/release/`、`xiao6-ui/xiao6-ui/`（含各自的 config.py / ai_core / capability_os）
- ❌ 密钥泄露于历史（见 §5）

## 7. Version Status

- ✅ 1.0.0：`VERSION`（git 追踪）、`AI_BOOTSTRAP.md`、`xiao6-desktop/pet/package.json`
- ❌ 1.4.0 残留：`config.py:204`、`release/config.py:208`、`xiao6-ui/config.py:208`（三处，且为启动/UI 实际显示源）
- ❌ 无 SSOT：VERSION 文件无人读取；package.json / pyproject.toml 缺失
- ⚠️ UI 显示版本：因前端 LOST 无法直接验证，但按 config.APP_VERSION 推断为 1.4.0

## 8. P0 Issues

| # | 问题 | 位置 |
|---|---|---|
| P0-1 | 统一执行入口参数契约断裂，全部工具以空参数执行 | ai_core/execution/api.py:33 + 5 个调用点 |
| P0-2 | ai_core/execution/policy.py 缺失，Goal 工具链 ModuleNotFoundError；ExecutionPolicy.get() 不存在 | agent_runtime.py:551-553 |
| P0-3 | HEAD 版本 server 每请求 TypeError 崩溃（_is_local_peer 为布尔）；工作区热修降级为恒 local | server_globals.py:9 / server.py:120,188,223 |
| P0-4 | Agnes API Key 泄露于 git 历史 ≥3 commits，未轮换 | S81-FINAL-REPORT.md @ 1e24b62/2789613/93c6194 |
| P0-5 | server_globals stub 覆盖：本地校验恒真、CORS `*`、远程限制关闭、日志脱敏失效 | server_globals.py:9-30 经 server.py:188 |

## 9. P1 Issues

| # | 问题 | 位置 |
|---|---|---|
| P1-1 | Skill/MCP 直调 execute_tool 绕过 Policy（3 处） | agent_runtime.py:729 / capability_runtime.py:158 / capability_os/__init__.py:259 |
| P1-2 | 统一入口 default_deny=False，弱于声明 | api.py:37,64 |
| P1-3 | config.py APP_VERSION=1.4.0 ×3，与 1.0.0 冲突 | 三棵树 config.py |
| P1-4 | 重复代码树入库（release/、xiao6-ui/xiao6-ui/） | xiao6-ui/ 下 |
| P1-5 | 前端主资产缺失（PARTIAL→需恢复） | 工作区 xiao6-ui 静态资源 |
| P1-6 | package.json / pyproject.toml / VERSION 之外的版本载体缺失且未入库 | 根目录、xiao6-ui |
| P1-7 | 三棵树 .env 加载行为不一致（.env.local 仅嵌套树加载） | config.py:469 vs release/config.py:440-441 |

## 10. Recommended Next Phase

**Phase R1（P0 止血，阻塞一切后续）：**
1. 轮换 Agnes 密钥（立即，最高优先）；评估历史清洗（filter-repo/BFG）或至少确认仓库从未外推
2. 解除 server_globals stub 覆盖链：删除 server.py:188 的 stub 导入，让真实实现（:120 local 校验、:126 脱敏正则、CORS 白名单）生效
3. 修复执行契约：调用方统一传 `context={"args": args, ...}` 或将 api.run 改为 `run(task, args, ...)`；补齐 `ai_core/execution/policy.py` 或对齐 agent_runtime 的导入
4. 将工作区热修收敛为正式提交（HEAD 当前不可运行）

**Phase R2（结构修复）：** 恢复前端资产并入库；删除两棵重复树；补 package.json / pyproject.toml；Skill 直调路径纳入 Policy。

**Phase R3（统一与验证）：** config.APP_VERSION 改为读取 VERSION（SSOT=1.0.0）；建立最小冒烟测试（server 启动 + 工具调用 + Goal 执行），复评六维 ≥8 后打 **RC 标签**。

> 本审计未修改任何文件、未执行修复、未提交 git；全部报告（7 份）仅作为审计产物输出于 G:\xiao6 根目录。
