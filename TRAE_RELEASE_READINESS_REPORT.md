# TRAE Release Readiness 评估报告

> 审计日期：2026-08-28 · 评估对象：Xiao6 v1.0.0 · 依据：本次七项独立审计的实际取证

---

## 一、定位结论

```
A. 开发稳定版   ← 当前真实定位
B. Release Candidate   ← 未达到
C. 正式发布版   ← 未达到
```

**当前为 A（开发稳定版），且属于"A 中的不稳定态"——存在 3 项 P0 运行时/安全阻断项，甚至不能保证主链路可用。**

距 B（RC）的硬性差距：P0 清零 + 版本统一 + 前端资产归位。在此之前不应打 RC 标签。

---

## 二、六维评分

评分口径：0-10，≥8 视为达标，6-7 视为带条件通过，<6 不通过。

| 维度 | 得分 | 判定 | 依据 |
|---|---|---|---|
| **Runtime** | **3/10** | ❌ | 统一执行入口参数契约断裂（5/5 调用点传参全丢）；`ai_core/execution/policy.py` 缺失导致 Goal 工具链 ModuleNotFoundError；3 处 execute_tool 直调绕过 Policy；HEAD 版本 server 每请求必崩（_is_local_peer bool）。架构骨架（EventBus 单例、PermissionGuard 闭环、PolicyEngine）设计良好但接线断裂 |
| **Git** | **4/10** | ❌ | S84-S87 四个里程碑提交齐全 ✅；但工作区含未提交热修（server_globals.py），核心工程文件（package.json / pyproject.toml / 前端资产）未追踪或缺失，`release/` 与 `xiao6-ui/xiao6-ui/` 两棵完整重复树入库，密钥泄露历史未清洗 |
| **Frontend** | **4/10** | ❌ | 状态 PARTIAL：工作区缺 index.html / app.js / styles.css 等主资产；git 历史无完整副本（LOST 于历史），但归档目录与 dangling blobs 提供恢复来源。无 UI 即无可交付产品面 |
| **Security** | **2/10** | ❌ | Agnes 密钥泄露于 git 历史 ≥3 commits（未轮换）；server_globals stub 把本地校验/CORS/远程限制/日志脱敏四项边界控制全部失效化；.env 本身未追踪（唯一亮点） |
| **Version** | **4/10** | ❌ | VERSION/AI_BOOTSTRAP/桌面端 = 1.0.0 ✅；config.py 三处 = 1.4.0 ❌；无 SSOT；package.json/pyproject.toml 缺失 |
| **Documentation + Test** | **5/10** | ⚠️ | S 阶段文档齐全（S81-FINAL-REPORT 等贯穿全程，流程可追溯 ✅）；但文档即泄露源之一（密钥入档）；无自动化测试证据，"E2E validation"仅为人工阶段性声明，与本次实测结果（链路断裂）互相矛盾 |

**加权总分：约 3.7 / 10 —— 不可发布。**

---

## 三、各维度到 RC 的门槛条件

| 维度 | 进入 RC 的最低门槛 |
|---|---|
| Runtime | 修复 api.py 契约（调用方传 `context={"args":...}` 或入口改签名）；补齐/对齐 `ai_core.execution.policy` 模块；Skill 直调路径纳入 Policy；stub 覆盖链解除 |
| Git | 未提交热修收敛为正式提交；删除两棵重复树或明确其为构建产物；核心工程文件入库 |
| Frontend | 从归档/dangling blobs 恢复主资产并入库；UI 可启动、可与 server 联通 |
| Security | 轮换 Agnes 密钥；历史清洗或至少立即废止旧钥；server_globals 真实实现回归；脱敏正则恢复 |
| Version | config.py 1.4.0 → 读 VERSION 单源；补 package.json/pyproject.toml（1.0.0） |
| Doc/Test | 建立最小冒烟测试（server 启动 + 一次工具调用 + 一次 Goal 执行），使"E2E 完成"类声明可复现 |

---

## 四、风险矩阵（Top 5）

| # | 风险 | 概率 | 影响 | 级别 |
|---|---|---|---|---|
| 1 | 密钥已公开泄露于历史（若仓库被共享/推送） | 已发生 | 凭证盗用、账单损失 | P0 |
| 2 | 远程访问边界全开（恒 local + CORS * + 空禁用清单） | 已发生 | 未授权远程执行工具 | P0 |
| 3 | Goal 执行链 ModuleNotFoundError | 已发生 | 核心功能不可用 | P0 |
| 4 | 重复代码树（release/、xiao6-ui/xiao6-ui/）与主树漂移 | 高 | 修复不同步、行为不一致 | P1 |
| 5 | 工具以空参数执行（契约断裂） | 已发生 | 静默错误结果、难以排查 | P0 |

---

## 五、建议下一阶段（顺序）

1. **P0 止血**（安全 + 运行时，二者都阻塞一切）
2. 前端资产恢复
3. 版本 SSOT 统一
4. 重复树清理 + Git 卫生
5. 最小测试基线 → 复评 → 打 RC 标签

（详见 TRAE_FINAL_AUDIT_REPORT.md §10）
