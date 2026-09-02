# Task C — Signing Preparation Report | 小6 GA

> **身份**：Senior Release Engineer + Software Delivery Engineer + QA Lead
> **Sprint**：Xiao6 GA Release Preparation Sprint v1.0
> **执行模式**：Audit → Plan → Execute → Verify → Report
> **日期**：2026-08-05
> **纪律红线**：仅发布工程 / 签名准备文档；**无代码签名证书，不得伪造签名**；无业务 / 架构 / Runtime 改动。

---

## 1. 现状（Audit）

| 项 | 状态 |
|---|---|
| 代码签名证书 | ❌ 当前无证书 |
| `electron/package.json` 签名配置 | ❌ 未配置（无 `win.signingOptions` / `certificateSubjectName` 等） |
| 签名文档 / 流程 | ❌ 缺失（本报告补齐） |
| 产物签名状态 | ⚠️ Portable `小6-1.4.0-x64.exe` 与（待构建的）安装器均**未签名** |
| SmartScreen 风险 | ⚠️ 未签名 → Windows SmartScreen 可能提示「未知发布者」 |

**结论**：当前无法在 GA 中交付已签名产物。本任务产出**完整签名准备文档**，供获取证书后一键接入；**绝不伪造签名**。

## 2. 代码签名准备清单

### 2.1 证书类型（建议）
| 类型 | 特点 | 适用 |
|---|---|---|
| **OV（组织验证）代码签名** | 验证组织身份；需已注册法律实体；SmartScreen 信誉需累积 | 个人 / 小团队首选，成本适中 |
| **EV（扩展验证）代码签名** | 严格审查 + 硬件令牌；**立即获得 SmartScreen 信誉** | 预算充足、追求零拦截 |
| **Azure Trusted Signing**（云签名） | 微软托管，按量计费，免硬件令牌；兼容 electron-builder | 无硬件令牌、CI 友好 |

> 小6当前 `author` 已统一为 `小6`；若以组织实体申请，需确保法律实体名称与证书主体一致（建议后续将 `author`/`copyright` 对齐到该实体，非 GA 阻断）。

### 2.2 electron-builder 签名配置（证书就绪后填入）

在 `electron/package.json` 的 `build.win` 增加（示例，参数以实际证书为准）：

```json
"win": {
  "target": ["portable", "nsis"],
  "icon": "assets/icon.ico",
  "artifactName": "小6-${version}-${arch}.${ext},
  "signingOptions": {
    "certificateSubjectName": "小6",
    "signingHashAlgorithms": ["sha256"],
    "timestampServer": "http://timestamp.digicert.com",
    "rfc3161TimeStampServer": "http://timestamp.digicert.com"
  }
}
```

- Portable 与 NSIS 安装器 **均需签名**（二者均为独立 exe）。
- 建议同时签名**内嵌的 `elevate.exe`**（NSIS 提权用，位于 `resources/`），否则提权场景仍可能触发 SmartScreen。
- 时间戳服务器保证证书过期后签名仍有效。

### 2.3 推荐接入方式（CI / 本地）
- **本地一次性**：设置环境变量 `CSC_LINK`（p12 路径）+ `CSC_KEY_PASSWORD`，运行 `npm run dist`。
- **Azure Trusted Signing**：使用 `electron-builder` + `@electron/azure-sign` 插件，密钥托管云端，CI 中无需暴露 p12。
- **CI 建议**：在隔离构建机执行签名，私钥不入库（`.gitignore` 已忽略 `*.p12` / 密钥）。

### 2.4 SmartScreen 信誉策略
- EV 证书：近乎即时消除 SmartScreen 拦截。
- OV 证书：首次发布后需通过下载量 / 反馈逐步累积信誉（数天至数周）；过渡期在下载页明确指引用户「仍要运行」。
- 无论是否签名，均应在官网 / 发布页提供**校验和（SHA-256）**与**使用说明**，降低用户疑虑。

### 2.5 发布页需补充的内容（GA 当前缺口）
- 下载页醒目提示「未签名，Windows 可能拦截，确认来源后选择仍要运行」。
- 提供 `小6-1.4.0-x64.exe` 与 `小6-Setup-1.4.0-x64.exe` 的 SHA-256。
- （获取证书后）更新本文件为「已签名」状态并移除拦截提示。

## 3. 验证（Verify）

- ✅ 确认无证书、未配置签名、未伪造任何签名（遵守纪律红线）。
- ✅ 产出可执行的签名接入清单（证书类型 / 配置片段 / CI 方式 / SmartScreen 策略）。
- ✅ 不影响任何运行时产物；仅文档 + 预留配置说明。
- ✅ 未改动业务代码 / Runtime / EventBus / Memory。

## 4. 风险与阻断判定

- **SmartScreen 拦截**属于**体验风险**，**非发布阻断**（功能不受影响，用户可手动允许）。
- 若组织合规要求「必须消除 SmartScreen 拦截」，则**获取 EV 证书并签名**为 GA 前置条件（属外部采购，非本仓库可完成）。
- 本 Sprint 不阻断 GA 决策（见 Task G），但建议在 GA 发布公告中如实披露未签名状态。

## 5. 纪律红线遵守声明

- ✅ 仅产出签名准备文档与预留配置说明，属「代码签名准备」允许范围。
- ✅ **未伪造、未生成任何签名**；未修改业务 / 架构 / Runtime / EventBus / Memory。
- ✅ 业务 Bug 仅记录，未修复。

---

**Task C 状态：✅ 完成（准备文档交付；签名待证书到位后执行）。**
