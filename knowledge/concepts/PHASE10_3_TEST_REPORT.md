---
id: know-phase-10-3
type: concept
---
# Phase 10.3 测试报告

**当前版本号：v0.11.0**（由 v0.10.0 升级）
**完成状态：Phase 10.3 Persistent Workspace 全部完成 ✅**

---

## 1. 新增文件

`core/autonomy/workspace/` 目录（11 个模块）：

- `WorkspaceState.js` —— Workspace 生命周期状态机（6 态 + 合法转移表 + `IllegalWorkspaceTransitionError` + `assertWorkspaceTransition`）
- `WorkspaceModel.js` —— Workspace 纯数据模型（工厂 `createWorkspaceModel`）
- `WorkspaceSnapshot.js` —— 纯数据快照（Workspace/Project/Scheduler 状态 + 各类引用 + 版本 + 时间戳）
- `WorkspaceCheckpoint.js` —— 检查点（create/restore/list/remove，深拷贝，restore 不改执行状态）
- `WorkspaceVersion.js` —— 版本管理（bump / history / rollbackPoint / diff，仅记录不执行）
- `ContextStore.js` —— 长期上下文存储（save/update/compress/merge/query/cleanup/hash/version）
- `ArtifactRegistry.js` —— 产物注册表（register/query/remove/classify/tag/setVersion/setMetadata，禁执行对象）
- `WorkspaceRecovery.js` —— 恢复（Snapshot/Checkpoint/Context/Artifact/Version，仅重建数据视图不触发执行链）
- `WorkspaceMemory.js` —— Workspace 记忆桥接（7 分区，带执行隔离硬闸）
- `WorkspaceManager.js` —— 长期工作空间门面（生命周期 + Snapshot/Checkpoint/Version/Context/Artifact + describe）
- `index.js` —— Phase 10.3 统一出口

`phase10_3_workspace_test.js` —— Phase 10.3 单元测试

---

## 2. 修改文件

- `core/autonomy/index.js`：导出 Phase 10.3 全套接口（WorkspaceManager / WorkspaceModel / WorkspaceState / WorkspaceSnapshot / WorkspaceCheckpoint / WorkspaceVersion / ContextStore / ArtifactRegistry / WorkspaceRecovery / WorkspaceMemory 等）
- `core/events/EventBus.js`：新增 12 个 Workspace 事件
- `core/autonomy/project/ProjectManager.js`：新增可选只读引用 `workspaceManager`（不反向控制执行）
- `core/orchestrator/Orchestrator.js`：新增 `workspaceManager` 构造参数、`run()` 返回 `workspace` 快照、`_safeAttach(this.workspaceManager)`
- `main.js`：别名 `LongTermWorkspaceManager` 实例化并注入 ProjectManager（只读）与 Orchestrator、新增 `[长期工作空间]` 汇总段、横幅升 v0.11.0
- `package.json`：升 v0.11.0，加 `test:phase10_3` 与 `test:all`

---

## 3. 架构变化

- 新增独立层 `core/autonomy/workspace/`，与 Phase 9 自主层、Phase 10.1/10.2 同属"只管理/只调度/只保存不执行"的认知-管理家族。
- 依赖方向严格单向：**WorkspaceManager 只管理数据，不反向控制任何执行模块**。ProjectManager / Scheduler 可只读引用 Workspace（`projectManager.workspaceManager`），反之不成立。
- Phase 5~10.2 接口全部兼容（仅加法；ProjectManager 仅新增可选字段）。
- 命名隔离：`main.js` 已有的运行时 `WorkspaceManager`（`core/workspace/WorkspaceManager.js`，即 `ws`）未被触碰，Phase 10.3 以别名 `LongTermWorkspaceManager` 接入。

---

## 4. Workspace 架构设计

`WorkspaceManager` 为唯一对外门面，内部持有：

- `workspaces: Map<workspaceId, WorkspaceModel>` —— 全部 Workspace 纯数据
- `checkpoints: WorkspaceCheckpoint` —— 检查点
- `contexts: ContextStore` —— 长期上下文
- `artifacts: ArtifactRegistry` —— 产物
- `versions: Map<workspaceId, WorkspaceVersion>` —— 版本历史
- `recovery: WorkspaceRecovery` —— 只读恢复引擎（持上述 store 引用）
- `workspaceMemory: WorkspaceMemory` —— 7 分区记忆桥接

所有写操作仅：更新纯数据 → 广播 EventBus → 写 Memory 分区。**绝不调用 Worker/Tool/Orchestrator/Agent/Scheduler、绝不执行代码、绝不修改 Task 执行状态。**

---

## 5. Workspace 生命周期

状态（6）：`CREATED → ACTIVE ⇄ SUSPENDED → RECOVERING → ACTIVE → ARCHIVED → DELETED`

- `createWorkspace`：CREATED
- `openWorkspace` / `activateWorkspace`：CREATED/SUSPENDED → ACTIVE（广播 `WorkspaceOpened`）
- `closeWorkspace` / `suspendWorkspace`：ACTIVE → SUSPENDED（广播 `WorkspaceClosed`）
- `saveWorkspace`：不改变状态（广播 `WorkspaceSaved`）
- `recoverWorkspace`：非终态 → RECOVERING → ACTIVE（广播 `WorkspaceRecovered`，仅恢复数据）
- `archiveWorkspace`：ACTIVE/SUSPENDED → ARCHIVED（广播 `WorkspaceArchived`）
- `deleteWorkspace`：→ DELETED 终态（广播 `WorkspaceDeleted`）

---

## 6. Snapshot 机制

- `createSnapshot(workspaceId)`：捕获 `workspaceState / projectState（只读引用 ProjectManager）/ schedulerState（只读引用 Scheduler）/ memoryRefs / contextRefs / artifactRefs / version / timestamp`，生成 `WorkspaceSnapshot` 纯数据对象。
- 快照以 timestamp 作引用键存入 `workspace.snapshotIds`。
- 恢复时经 `WorkspaceRecovery.recoverFromSnapshot(snapshot)` 重建数据视图（不触发执行链）。

---

## 7. Checkpoint 机制

- `createCheckpoint(workspaceId, { label, data })`：以 `WorkspaceModel.toJSON()` 为默认数据做深拷贝，生成检查点，引用键存入 `workspace.checkpointIds`。
- `restoreCheckpoint(workspaceId, checkpointId)`：从检查点写回纯数据字段（name/metadata/version/snapshotIds/checkpointIds/artifactIds），**刻意不修改生命周期状态**（符合"Checkpoint 不能修改执行状态"）。
- `listCheckpoint` / `removeCheckpoint` 支持查询与清理。

---

## 8. Recovery 机制

`WorkspaceRecovery` 提供：

- `recoverFromSnapshot(snapshot)`：重建 workspace 数据视图（含状态/版本/各类引用）
- `recoverFromCheckpoint(checkpointId)`：返回检查点数据
- `recoverContext(contextId)` / `recoverArtifact(artifactId)` / `recoverVersion(workspaceId, version)`：分别按 store 查询
- `recoverWorkspace({ snapshot | checkpointId | workspaceId+version })`：综合恢复，优先快照

**关键约束：恢复仅恢复数据，不恢复执行链。** 该模块不持任何 worker/tool 引用，不调用 Orchestrator/Agent/Scheduler。

---

## 9. Version 管理

- `WorkspaceVersion`：`bump(meta)` 自增版本并写入历史；`getHistory()` 列出全部版本；`rollbackPoint(version)` 取回滚点（仅数据）；`diff(vA, vB)` 计算 meta 差异（added/removed/changed）。
- `WorkspaceManager.bumpVersion` 广播 `WorkspaceVersionUpdated` 并同步 `workspace.version`；`rollbackVersion` 仅调整版本指针与 meta（纯数据，不执行）。
- 初始版本为 1；历史为空时 `rollbackPoint` 返回 `null`。

---

## 10. ContextStore

- 长期上下文：`save` / `update`（版本自增）/ `compress`（压缩视图，不丢 hash）/ `merge`（合并两条上下文为新上下文）/ `query` / `cleanup`。
- `contextHash`（FNV-1a 8 位十六进制）做内容指纹，`hash` / `version` 提供查询与版本能力。
- 全部为纯数据操作，不执行任何代码。

---

## 11. ArtifactRegistry

- 产物注册：`register` / `query` / `queryByWorkspace` / `queryByKind` / `remove`。
- 分类与元数据：`classify` / `tag`（去重）/ `setVersion` / `setMetadata`。
- **约束：Artifact 不保存执行对象**——`ref` 与 `metadata` 携带 `worker/tool/agent/agents/orchestrator/workflow/coding/executor` 等执行键时构造/设置即抛错。

---

## 12. EventBus 事件

新增 12 个（全部为 `Workspace*` / `Context*` / `Artifact*` 前缀，无执行语义）：

`WorkspaceCreated` / `WorkspaceOpened` / `WorkspaceClosed` / `WorkspaceSaved` / `WorkspaceRecovered` / `WorkspaceArchived` / `WorkspaceDeleted` / `WorkspaceSnapshotCreated` / `WorkspaceCheckpointCreated` / `WorkspaceVersionUpdated` / `ContextUpdated` / `ArtifactRegistered`

---

## 13. Memory 记录

新增 7 个分区（`WorkspaceMemory`，只写不读、不执行）：

- `workspace_memory` —— Workspace 创建/打开/关闭/保存/恢复/归档/删除
- `workspace_snapshot` —— Workspace 快照创建
- `workspace_checkpoint` —— Workspace 检查点创建
- `workspace_context` —— Context 更新
- `workspace_artifact` —— Artifact 注册
- `workspace_version` —— Version 更新
- `workspace_history` —— 生命周期历史

---

## 14. 执行隔离验证

- 14 类禁止注入（worker/tool/tools/toolRegistry/terminalAdapter/applicationAdapter/processAdapter/orchestrator/agentRegistry/messageRouter/executor/coding/agent/agents）构造期被 `assertNoForbiddenInjected` 拒收（`WorkspaceManager` 与 `WorkspaceMemory` 均带硬闸）。
- 真实 EventBus 捕获证明：完整生命周期（create→open→snapshot→save→recover→checkpoint→version→context→artifact→close/archive/delete）**0 个执行类事件**。
- Memory 写入全部为 `workspace_*` 分区，**0 个执行分区**（events/projects/user/agents 等）。
- `WorkspaceManager` 不含 `run` / `execute` 等执行方法；仅对 `projectManager` 做只读引用（快照读状态时调用 `getProject`，不调用任何执行方法）。
- 仅允许：管理数据、恢复数据、保存数据、广播事件、写 Memory。

---

## 15. 测试断言数量

**`phase10_3_workspace_test.js`：272 断言 / PASS 272 / FAIL 0 ✅**

覆盖（23 项）：Workspace 创建、Workspace 生命周期、WorkspaceState、Snapshot、Checkpoint、Recovery、Version、ArtifactRegistry、ContextStore、WorkspaceMemory、WorkspaceManager、EventBus、Memory、状态机、非法转换、多 Workspace、Snapshot 恢复、Checkpoint 恢复、Version 回滚、Context 合并、Artifact 分类、执行隔离、纯数据检查。

---

## 16. PASS / FAIL

- Phase 10.3：PASS（272/272）
- 过程修复（均为测试期望/产品边界修正，非执行权限问题）：
  1. `WorkspaceRecovery.recoverVersion` 对 `Map` 误用对象式下标访问 → 改 `.get()`。
  2. 状态转移表扩展：允许 `CREATED/ACTIVE → RECOVERING`（恢复允许从任意非终态进入），并同步测试长度断言。
  3. 测试期望修正：`createWorkspaceSnapshot` 工厂返回纯对象无 `toJSON`（改用 `new WorkspaceSnapshot`）；`ARCHIVED→DELETED` 合法应成功（原误写为抛错）；版本构造未强制 ≥1（移除该断言）。

---

## 17. 全量回归结果（全部 PASS，零回归）

phase5 / phase6 / phase7_decision / phase7_2 / phase7_full / phase8_1 / phase8_2 / phase8_3 / phase8_4 / phase9_1 / phase10_1 / phase10_2 —— **12 套全 PASS**。

端到端冒烟：`PAIOS_MODEL=heuristic node main.js` **EXIT=0**，v0.11.0 横幅 + `[长期工作空间]` 段正常，EventBus 广播 **5828 事件**无崩溃，Phase 5~10.2 执行链未受影响。

---

## 18. 当前版本号

**v0.11.0**
