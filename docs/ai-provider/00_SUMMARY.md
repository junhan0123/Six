# 00 — Phase 10 总体摘要（Living Document）

- **项目**：Xiao6 AI OS · Phase 10 · AI Provider Integration Foundation v1.0
- **更新**：2026-08-08（Phase B 完成）
- **本文件**：随 Phase 进展更新；当前覆盖 Phase A（审计）+ Phase B（架构设计）。

---

## 1. 一句话定位
为「云端 API + 本地大模型」建立**可选择、可治理、可扩展**的 AI Provider 接入基础；UI 仅为表现层，不反向侵入系统核心。

## 2. 当前进度

| Phase | 内容 | 状态 | 交付物 |
|---|---|---|---|
| A · Reality Audit | 真实审计 AI 请求链、18 问带行号证据 | ✅ 完成 | `10_REALITY_AUDIT.md` |
| B · Architecture Design | 最小 Provider 抽象 + Registry + Selection + Privacy + Capability | ✅ 完成 | `01_ARCHITECTURE` `02_REGISTRY` `03_SELECTION` `04_PRIVACY_AND_FALLBACK` `07_CAPABILITY_MATRIX` |
| C · Minimal Implementation | 后端 Resolver/Registry/Config/探测 + 前端 Settings 扩展 | ⏳ 未开始（待 Design Review） | `05_UI` `06_CONNECTION_TEST` |
| D · Verify | 36 项验证 + 测试矩阵 | ⏳ | `08_VERIFY` |
| E · Docs | 10 份交付文档收口 | ⏳ | 本套文档 |
| F · Git/Memory + STOP | 真实 git diff、更新记忆、🛑 STOP | ⏳ | — |

## 3. 最重要发现（来自审计）
1. 系统**已有未完成双 Provider 骨架**（`ACTIVE_LLM` + `LLM2_*`），缺 UI/文档/状态/隐私表达 → Phase 10 = **完成半成品**。
2. **本地模型路径 = 0**，违反 `09_LOCAL_FIRST §4` → 首要合规缺口（G-01）。
3. `llm._provider_creds` 是天然收口点，改动面可极小（D-01/D-02）。

## 4. 冻结红线（设计全程遵守）
- 不新建第二 Runtime/Memory/EventBus/Permission（Golden State L40）；
- 不新增领域事件（事件合约 71/8 FROZEN，D-03）；
- 不触碰 AI Presence 三唯一（D-04）；
- API Key 绝不下发前端（D-07）；
- 本地端点仅已知 localhost，禁系统扫描（D-06）；
- Fallback 默认 OFF，禁 Silent Cloud Fallback（D-05）。

## 5. Readiness 判定（截至 Phase B）
- **架构设计 Readiness**：🟢 完整、自洽、遵守全部红线。
- **实现 Readiness**：🔴 未开始（Phase C 待 Design Review 通过后启动）。
- **整体 Phase Readiness**：🟡 设计完成，实现未动；Local First 合规缺口已设计修复方案但尚未落地。

## 6. 已知 NOT SUPPORTED（设计态已锁定）
- 真 token 级流式（全部 Provider）：❌ NOT SUPPORTED；
- 系统端口/服务扫描：🔴 FORBIDDEN；
- Silent Cloud Fallback：🔴 FORBIDDEN；
- OS keychain 存 Key：❌ NOT SUPPORTED（本 Phase，记录债 G-08）。

## 7. 下一步
→ 提交 Phase B 架构设计供 Review；Review 通过 → 启动 #696 Phase C 最小实现。

> 🛑 本文件随 Phase 更新。每次 Phase 边界重写本节。
