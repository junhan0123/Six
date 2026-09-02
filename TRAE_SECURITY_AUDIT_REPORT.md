# TRAE 安全审计报告

> 审计日期：2026-08-28 · 性质：独立只读审计 · 范围：.env / config.py / server.py / 日志 / Git 历史

---

## 一、配置链验证

目标链路：

```
.env → config.py → Runtime → Agnes API
```

### 实际状态：**链路存在且基本生效，但存在 stub 覆盖隐患**

| 环节 | 证据 | 结论 |
|---|---|---|
| `.env` 存在 | `xiao6-ui/.env` 含 AGNES_API_KEY / BASE_URL / MODEL | ✅ |
| config.load_env | `config.py:207` `load_env()`，`config.py:469` 模块加载时执行 | ✅ ENV 播种正常 |
| 密钥传递 | `config.py:293` `AGNES_KEY = os.environ.get("AGNES_API_KEY", "")` | ✅ 经环境变量中转，非硬编码 |
| Runtime 消费 | server / capability 层经 config 读取 | ✅ |
| ENV 优先级 | `config.py:228` 定义 secrets 集合；`config.py:241-243` 仅上报 present/length（不回显值） | ✅ 状态探针设计正确 |

⚠️ 隐患：`release/config.py:440-441` 与 `xiao6-ui/config.py:440-441` 加载 `.env.local` + `.env`（双文件），顶层 `xiao6-ui/config.py:469` 只加载 `.env` —— **三棵代码树的加载行为不一致**（详见版本/Git 报告中的重复树问题）。

---

## 二、API Key 泄露取证

### 2.1 工作区（当前文件）

- `xiao6-ui/.env` 含真实密钥 `sk-RPu6...`（Agnes）
- ✅ `git ls-files` 确认 **`.env` 未被 git 追踪**（追踪列表中仅有 VERSION、xiao6-desktop/pet/package.json）

### 2.2 Git 历史（❌ 已泄露）

`git grep` 全历史扫描证实：**同一密钥存在于 `S81-FINAL-REPORT.md`，横跨至少 3 个提交**：

```
1e24b62 :S81-FINAL-REPORT.md
2789613 :S81-FINAL-REPORT.md
93c6194 :S81-FINAL-REPORT.md
```

另有 `git log -S "sk-"` 命中：S85（a79d992 Credential configuration lock）、S86（ec6d554）、S83、S81×2 —— 说明多个阶段的报告/文档在提交中携带过密钥字符串。

**结论：密钥已永久进入 git 对象库。即使未来删除文件，历史仍可恢复。S85 的"凭证锁定"仅阻止了后续新增，未清除历史泄露。** → 需要轮换密钥 + 历史清洗（本次审计不执行）。

---

## 三、S85 / S86 修复有效性验证

| 修复项 | 声明 | 实际验证 | 结论 |
|---|---|---|---|
| S85 凭证锁定 | 阻止密钥入库 | `.env` 未追踪 ✅；但历史泄露未清除 ❌ | **部分生效** |
| S86 Runtime stability closure | 运行时稳定 | HEAD 中 `server_globals._is_local_peer = True`（布尔）→ server.py:223 每请求 TypeError 崩溃；参数契约断裂未修 ❌ | **未生效**（详见 Runtime 报告） |

---

## 四、日志脱敏（当前实际状态：❌ 已失效）

server.py:124-129 定义了正确的访问日志脱敏正则（覆盖 token / access_token / secret / password / api_key / apikey）：

```python
_ACCESS_LOG_REDACT_RE = re.compile(r"([?&](?:token|...|apikey)=)[^&\s\"']+", re.IGNORECASE)
```

但 server.py:188 `from server_globals import _ACCESS_LOG_REDACT_RE` 用 **`None`** 覆盖了该正则 → **脱敏实际关闭**。URL 查询串中的凭证会明文进入日志/stderr。

此外 debug 类输出未发现密钥回显（config 状态探针只报长度），该项合格。

---

## 五、网络与访问控制（当前实际状态：❌ 被 stub 清空）

| 控制 | 声明位置 | 实际生效值（server_globals stub 覆盖后） |
|---|---|---|
| 本地来源校验 `_is_local_peer` | server.py:120 真实实现 | **恒 True**（远程请求一律视为本地） |
| 远程禁用工具 `_REMOTE_FORBIDDEN` | server.py:117 相关逻辑 | **False / 空清单** |
| CORS 白名单 `_CORS_ALLOWED_ORIGINS` | server.py `_resolve_cors_origins` | **`{"*"}`** |
| 访问日志脱敏 | server.py:126 | **None（关闭）** |
| 远程会话工具白名单 | tools.py:3992 `execute_tool(allowed=...)` | 该层仍生效 ✅（前提是调用方传了 allowed） |

**结论：除 tools 层的 allowed 白名单外，服务端边界安全控制在当前工作区状态几乎全部被 stub 失效化。**

---

## 六、Electron / 桌面端

- `xiao6-desktop/pet/package.json`：Electron ^31.0.0，main.js 未在本次深审范围（前端报告已覆盖 UI 缺失问题）；未见明显 nodeIntegration 配置读取入口残留在 git 追踪文件中（桌面端主要文件未追踪，无法完整验证 —— 记为 P2 待补审项）。

---

## 七、发现汇总

| 编号 | 级别 | 问题 |
|---|---|---|
| SEC-01 | **P0** | Agnes API Key 泄露于 git 历史（S81-FINAL-REPORT.md，≥3 commits） |
| SEC-02 | **P0** | server_globals stub 覆盖：本地校验恒真 / CORS `*` / 远程限制关闭 |
| SEC-03 | **P1** | 访问日志脱敏正则被 `None` 覆盖，脱敏失效 |
| SEC-04 | **P1** | S86 未达成其"运行时稳定"目标（HEAD 必崩） |
| SEC-05 | **P2** | 三棵代码树 .env 加载行为不一致（.env.local 仅在 release/嵌套树中加载） |

**安全评级：❌ 未达发布基线。** 密钥轮换 + stub 覆盖链修复为发布前置条件。
