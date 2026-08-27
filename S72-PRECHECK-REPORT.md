# S72 PRECHECK REPORT
## Xiao6 v1.0.0 Engineering Baseline Repair

---

## A. 当前工作目录状态

| 项目 | 状态 |
|------|------|
| G:/xiao6 | 无有效 Git 仓库 |
| G:/xiao6/xiao6-ui | 无有效 Git 仓库 |
| G:/xiao6/xiao6-desktop | 需检查 |
| G:/xiao6/xiao6-ui-new | 空 Git 仓库（dead project）|

---

## B. 版本不一致（关键问题）

| 来源 | 当前版本 | 期望 |
|------|---------|------|
| G:/xiao6/VERSION | `1.4.0` | `1.0.0` |
| G:/xiao6/xiao6-ui/VERSION | `v1.0.0` | `1.0.0` |
| docs/releases/ga/* 报告 | `1.4.0` | 保持历史不变 |
| electron/package.json | `1.4.0` | `1.0.0` |
| config.py APP_VERSION | `1.4.0` | `1.0.0` |

**问题**: VERSION 文件内容格式不一致，需要统一为纯 `1.0.0`。

---

## C. Secret 卫生问题

| 位置 | 状态 |
|------|------|
| .env | [REDACTED] 存在，被拦截 |
| .env.local | [REDACTED] 存在 |
| config.py HOTDATA_KEY | 硬编码: [REDACTED] |
| agent_delegate.py | dummy-key (测试用，可接受) |

**已知风险**:
- config.py 第53行: `HOTDATA_KEY = "zIisgRZJLLXgqKCwBirNLegtNNRuL70eBsbHXPxEBWU="`
- config.py 第381行: 默认值同上行

---

## D. server.py 编码

| 检查项 | 结果 |
|--------|------|
| BOM | 无 BOM |
| UTF-8 | OK |
| GBK | FAIL |
| 结论 | 纯 UTF-8，无需转换 |

---

## E. Legacy Name 审计

| 模式 | 出现位置 | 类型 |
|------|---------|------|
| `ZHUANGZHOU_*` | config.py (变量名) | Runtime-critical |
| `zz-agent-runtime` | agent_runtime.py 线程名 | Documentation-only |
| `zz-distill` | agent_runtime.py 线程名 | Documentation-only |
| `zz-icon`, `zz-close`, `zz-inbox` 等 | 前端 CSS/HTML 类名 | Historical artifact |
| `zhuangzhou_event` | agent_runtime.py.migration-bak | Dead code (backup) |
| `ZHUANGZHOU_ASR_PROVIDER` | asr.py.migration-bak | Dead code (backup) |

**分类**:
- A. Runtime-critical: ZHUANGZHOU_KWS_ENABLED 等环境变量名（用户配置，保留）
- B. Documentation-only: 线程名 zz-* （非运行时关键，可改）
- C. Historical artifact: migration-bak 文件（保留不删除）
- D. Dead code: 无活跃死代码

---

## F. Port Baseline

| 来源 | 端口 |
|------|------|
| config.py PORT | 8010 |
| server.py 默认 fallback | 8010 |
| server.py line 222 | `config.PORT` or 8010 |

**结论**: 权威端口 = **8010**

---

## G. 核心能力验证

| Phase | 测试结果 | 状态 |
|-------|---------|------|
| S68 | 28/28 PASS | ✓ |
| S69 | 27/27 PASS | ✓ |
| S70 | 32/32 PASS | ✓ |
| S71 | 41/42 PASS | ✓ (1 设计限制) |

---

## H. xiao6-ui-new 状态

```
G:/xiao6/xiao6-ui-new/
└── .git/
```

**结论**: 空 Git 仓库，无源码，dead project。标记为 DEAD_PROJECT_CANDIDATE。

---

## STOP 条件检查

| 条件 | 状态 |
|------|------|
| 无法确定的真实 Secret | ✗ .env 被拦截，但已知存在 |
| Git 首次建立可能含 Secret | ⚠ 需先清理 .env 再初始化 |
| server.py 编码转换风险 | ✗ 已确认为 UTF-8，安全 |
| 修改可能影响 S68-S71 | ⚠ 需验证 |
| 无法确认权威 runtime | ✗ 已确认端口 8010 |
| 需要大规模移动文件 | ✗ 无需移动 |

**结论**: 可继续，需先处理 Secret 卫生。
