# 04 — Privacy & Fallback（Phase 10-B · 隐私边界与回退）

- **阶段**：Phase 10-B · 架构设计
- **关联**：`03_SELECTION.md`；`01_ARCHITECTURE.md` §5；09_LOCAL_FIRST §3/§4/§6
- **纪律**：设计态，零代码。本文件把「隐私即架构」落到 Provider 层。

---

## 1. 隐私分类（修复 G-04）

每个 Provider 在 Registry 中标 `privacy_class`（见 `02_REGISTRY.md`）：

| 类 | 含义 | 数据去向 | 示例 |
|---|---|---|---|
| `local` | 数据不出本机 | 仅设备内推理 | Ollama / LM Studio / MLX |
| `cloud` | 数据发往远程 | 文本+上下文上传远端 API | Agnes / LLM2 |

**UI 义务**：任何 Provider 被选中/生效时，其 `privacy_class` 必须**可见**（状态行 + 切换确认提示）。用户无权「不知情地使用云端」。

---

## 2. 数据流边界（09_LOCAL_FIRST §4 红线）
- 用户数据 / 记忆 / 知识：**默认本地**，云端仅做**计算**，不得成为状态所有者（09_LOCAL_FIRST L4）。
- 即使选云端 Provider，上行内容也**仅限本次请求上下文**（`server.py:1856 build_context_prompt` 注入），不额外外泄持久状态。
- 本地 Provider 全链路无出站（除用户主动探测已知 localhost，D-06）。

---

## 3. 凭据安全（D-07 · 绝对红线）
| 禁止项 | 现状符合度 | Phase 10 保持 |
|---|---|---|
| 前端持有 API Key | 现 `/api/config` 仅回 `key_present: bool`（`server.py:1488`） | ✅ 不变 |
| Key 进 Git | `.env` 应已在 `.gitignore` | ✅ 校验并补全 |
| Key 进日志 | `llm.py` 不打印 Key | ✅ 维持（新增代码同约束） |
| Key 进 SSE | SSE 无 Provider 字段（D-03） | ✅ 不变 |
| Key 进前端缓存 | — | ✅ 禁止 |

> 本地 Provider `auth_required=False` → 无 Key 概念，天然满足。

---

## 4. Fallback 与隐私的交互（D-05 落地）

```
                 primary = 用户所选
                        │
           探测 status = error ?
                        │
        ┌───────────────┴───────────────┐
       是                               否
        │                                │
   是否开启 opt-in fallback？           直接服务 primary
        │
   ┌────┴────┐
  否         是
   │          │
 报错并       secondary 是否同隐私类
 告知用户     / 本地降级？
（不静默）         │
            ┌─────┴─────┐
          同隐私类     降级到本地
          (cloud→cloud) (local→local)
            │            │
            │        ❌ 禁止 local→cloud
            ▼            ▼
      服务 secondary  服务本地 secondary
            │
      UI 标注 served_by（非静默）
```

**铁律**：
1. 任何回退都**必须用户 opt-in**；
2. **禁止** `local → cloud` 静默外发（隐私泄露）；
3. 实际服务的 Provider **必须在 UI 标注**（`served_by`），**无 Silent Cloud Fallback**；
4. 回退不缓存/不携带密钥。

---

## 5. 切换确认 UX（最小实现）
- 用户在 Settings 从 `local` 切到 `cloud`：弹出一次性确认（复用现有 Modal/Toast 通道，**非新事件**），文案：「此 Provider 会将对话内容发送到云端。是否继续？」
- 从 `cloud` 切到 `local`：无需警告（本地更安全），但状态行更新为「本地 · 数据不出本机」。

---

## 6. 已知债务（记录，不在本 Phase 解）
| 债 | 来源 | 处理 |
|---|---|---|
| API Key 明文存 `.env`（非 OS keychain） | G-08；09_LOCAL_FIRST §3 L31 | 记录为已知债；本 Phase 不改 keychain，但确保不扩散、不入 Git |
| 无 `context_limit` 预算 | G-09 | 本地模型 context 由用户配置声明（见 `07_CAPABILITY_MATRIX.md`），不自动推断 |

> 🛑 设计态。隐私与回退的运行时表达在 Phase C 经 `/api/config` 与 Settings 落地。
