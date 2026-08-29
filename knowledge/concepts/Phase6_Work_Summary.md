---
id: know-phase-6
type: concept
---
# Phase 6 工作总结：认知层交付

**版本**：v0.5.0 → **v0.6.0** · **日期**：2026-07-07 · **状态**：✅ 完成，等待下一阶段指令

---

## 一句话

Phase 5 让系统**会干活**，Phase 6 让系统**知道自己在干什么、干得怎么样**。

---

## 交付内容

### 六大模块

| # | 模块 | 目录 | 核心能力 |
|---|---|---|---|
| 1 | Agent Runtime State Machine | `core/agent_runtime/` | 9 态状态机 + 迁移白名单 + 任务级隔离 |
| 2 | Observation Layer | `core/observation/` | 文件 / 工作区 / 进程三类感官 |
| 3 | Tool Capability Registry | `core/tool_registry/` | 按能力发现工具，消灭硬编码 |
| 4 | Agent Message Protocol | `core/agent_message/` | request / response / notification |
| 5 | Evaluator Agent | `agents/evaluator/` | success / warning / failed 三态判定 |
| 6 | Secrets Manager | `core/secrets/` | 加密存储 + 代理隔离 + 全程审计 |

### Task 系统升级

新增 `verification_status` / `verified_by` / `retry_count` / `max_retry` / `history`，
任务状态机扩展为 `pending → running → verifying → completed | failed`，失败自动打回 `pending` 重跑。

### 认知闭环（Orchestrator）

```
执行 → [EXECUTING] → Evaluator 验证 → [VERIFYING]
   success/warning → completed [COMPLETED]
   failed → 有预算 → [FAILED] → [RECOVERING] → 回 pending 重跑
          → 无预算 → failed
```

---

## 测试结果

| 套件 | 断言 | 结果 |
|---|---|---|
| Phase 6 认知层 | 73 | ✅ 全通过 |
| Phase 5 回归 | 34 | ✅ 全通过 |
| 端到端（8 任务） | — | ✅ 8/8 completed & verified |
| **合计** | **107** | ✅ **全绿** |

```bash
npm run test:phase6   # Phase 6 验收
npm run test:all      # Phase 5 + Phase 6
```

---

## 过程中修掉的 3 个真实缺陷

1. **`ProcessAdapter.isRunning()` 吞异常** —— 沙箱禁止 `spawn ps` 时，
   `.catch(() => [])` 把"探测失败"误判成"进程没在跑"。可观测性系统里最危险的一类 bug。
   改为异常上抛 + Observer 侧降级 + `data.via` 标注来源。
2. **`WorkerAgent` 对轻量 task 对象崩溃** —— `task.artifacts.push()` 假设 task 必来自 TaskManager，
   改为防御性初始化。
3. **状态机漏了 `IDLE → VERIFYING`** —— 迁移表按"执行型 Agent"设计，
   没考虑 Evaluator 这类工作本身就是验证的 Agent。

---

## 关键设计取舍

| 决策 | 为什么 |
|---|---|
| 快照差分而非 `fs.watch` | 三平台事件语义不一致，差分行为确定可测 |
| `node --check` 而非真执行 | 只解析语法，零副作用、零安全风险 |
| Evaluator 经 MessageRouter 调用 | 否则"禁止直接调用"的规矩在编排器自身就破了 |
| 重试 = 打回 pending | 复用 DAG 就绪调度，零新增调度分支 |
| Provider 不提供 `get()` | 记审计挡不住明文扩散，不给返回值才是真隔离 |

---

## 本阶段刻意未做

❌ UI / 可视化面板　❌ Computer Vision 点击操作　❌ 大量业务 Agent　❌ 远程密钥后端（Vault/KMS）

---

## 文档

- `docs/Phase6_Architecture.md` —— 架构说明（模块详解、事件表、文件清单、取舍记录）
- `docs/Phase6_Test_Report.md` —— 测试报告（6 项验收逐条结果、缺陷复盘）
