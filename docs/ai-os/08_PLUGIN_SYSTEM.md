# 08 — Plugin / Extension System（插件与扩展系统）

> 依赖：01（分层 L8）、04/05/06（执行通道）、P11（权限门控）
> 红线：所有扩展动作经 PermissionGuard + PolicyEngine；MCP 是协议适配器，不是第二系统。

---

## 1. 设计目标

当前系统存在多类"能力扩展"概念（MCP / Tool / Connector / Plugin / Extension），造成重复抽象与权限分裂。2.0 将它们**收敛为单一 Extension 抽象**：统一注册、统一发现、统一权限门控。MCP 作为"接入外部服务的协议适配器"存在，不另立运行时。

---

## 2. 统一 Extension 抽象

```
Extension
 ├─ id / name / version
 ├─ manifest（能力声明、所需权限 scope）
 ├─ type: tool | connector | mcp-adapter | ui-widget
 ├─ entry（本地代码/配置，无独立进程）
 └─ permissions: [scope.list]   ← 经 PolicyEngine 校验
```

- 任何能力（本地脚本、外部 API 连接器、MCP server 适配器、UI 组件）都实现为 Extension。
- 扩展运行在**主 Runtime 内**（或受控沙箱），不 spawn 独立 Agent 运行时（守 P14）。

---

## 3. Registry（注册与发现）

- 单一 `ExtensionRegistry` 管理所有已安装/已启用扩展。
- 注册时需提交 manifest，声明能力 + 权限 scope；未声明 scope 的动作被拒。
- 发现：模块通过 Registry 查询"谁提供某能力"，不直接引用具体扩展实现。
- 版本与依赖：Registry 解析扩展依赖，冲突时拒绝启用。

---

## 4. Policy Engine 权限门控（核心）

- 扩展的**每一次动作**都经 `PermissionGuard → PolicyEngine`（见 01 §2、04 §3）。
- 权限 scope 在 `goal:approved` / HITL 阶段由用户授予（敏感 scope 显式确认）。
- 扩展无权自决：它"请求"动作，Execution Channel 判定放行/拒绝/需确认。
- 越权动作在 `PermissionGuard` 被拒，记审计（Memory L10 Governance）。

---

## 5. MCP 作为协议适配器

- MCP（Model Context Protocol）是**接入外部工具的协议**，不是独立子系统。
- 一个 `mcp-adapter` 类型 Extension 将远程 MCP server 暴露为本地 Extension 能力。
- MCP server 调用仍经 Execution Channel + PermissionGuard（远程调用也视为"动作"）。
- 不因为引入 MCP 而新增第二 Runtime / EventBus / Memory。

---

## 6. 生命周期

```
 installed ─▶ enabled ─▶ active
    │            │         │
    │         disabled   error(权限/依赖失败)
    │            │
    └───────── uninstalled
```

- 安装/启用须经用户确认；禁用不删数据（Local First）。
- 升级：manifest 变更触发权限重审；降权扩展需用户重新授权。
- 远程连接器（如云 API）的凭据存本地密钥库（见 09），不落明文。

---

## 7. UI 扩展边界

- `ui-widget` 类型扩展仅可向 Surface 注册**受控组件槽位**（如 Dashboard 卡片）。
- UI 扩展不得修改 Galaxy 语义、不得绕过 AppState（经 `applyEvent`）。
- 扩展 UI 与主界面共享 Design Token（见设计系统规范），保持视觉一致。

---

## 8. 接口（事件）

```text
publish(extension:registered  {id, scopes})       ← Registry
publish(extension:action      {id, action})       → Execution Channel
publish(extension:denied      {id, reason})       ← PermissionGuard
subscribe(extension:query      {capability})       → Registry 发现
```

---

## 9. 红线

- 禁止扩展私建执行路径（必经 PermissionGuard）。
- 禁止引入第二 Runtime / EventBus 承载扩展。
- 禁止扩展未声明 scope 即执行动作。
- 禁止 MCP 绕过统一权限门控。

> 目标态设计；实现由 Plugin Sprint 承接，本 Sprint 不写代码。
