# Task C — First Launch Report | 小6 Beta Packaging Sprint v1.0

> **身份**：Senior Release Engineer + Deployment Engineer
> **日期**：2026-08-05
> **纪律红线**：仅首次启动流程 / 配置初始化；禁止改业务逻辑 / Runtime / Memory / EventBus。

---

## 0. 摘要（TL;DR）

| 维度 | 结论 |
|---|---|
| 首次启动脚本 | ✅ `xiao6-ui/first_launch.py`（纯标准库，零业务侵入，退出码恒 0） |
| 初始化 | ✅ 生成 `.env`（基于 `.env.example`）/ 创建 `sandbox data logs docs` / 检测 Key |
| Key 引导 | ✅ `main.js` 检测 `key_present=false` → 弹独立 BrowserWindow 向导 |
| Key 持久化 | ✅ 向导提交 → IPC `firstlaunch:submit-key` → POST `/api/config` → `config.update_env_file()` |
| 可选 ASR | ✅ `maybe_install_asr()` 默认关，设 `XIAO6_INSTALL_ASR=1` 静默装 |

---

## 1. 设计原则（零侵入）

`first_launch.py` 顶部注释明确：**不修改 `server.py`/`config.py` 业务行为；不触碰 EventBus / Memory / Runtime；始终退出码 0**（缺失项通过 JSON 上报，不阻断后端启动）。

这与纪律红线一致 —— 本 Sprint 仅做「配置初始化 / 首次启动流程」，未改动任何业务代码路径。

---

## 2. 首次启动流程（backend-launcher.js 编排）

```
Electron 启动
  └─ launchBackend(onFirstLaunch)
       ├─ resolveBackendDir()           # resources/backend
       ├─ runFirstLaunch(dir)           # 新增：运行 first_launch.py
       │    └─ 解析单行 JSON → firstLaunch{ok, env_created, dirs_created, key_present, asr}
       ├─ onFirstLaunch(firstLaunch)    # main.js 存 firstLaunchInfo
       └─ 拉起 server.py（SSE 就绪）
  └─ 后端就绪后：if (!firstLaunchInfo.key_present) openFirstLaunchWizard()
```

`backend-launcher.js` 变更：
- 新增 `runFirstLaunch(backendDir)`：用打包内 `python/python.exe`（或系统 python）运行 `first_launch.py`，解析单行 JSON，失败返回 `null`（不阻断）。
- `launchBackend` 三个 return（成功/可恢复失败/硬性失败）及 `CONNECTED` 均携带 `firstLaunch` 字段，保证 `main.js` 总能拿到首启状态。

---

## 3. Key 引导向导

- 新增 `electron/firstlaunch.html`：premium 风格引导窗（输入 AGNES_API_KEY + 「保存并继续」/「稍后再说」），回车提交。
- 新增 `electron/firstlaunch-preload.js`：隔离 `contextBridge`，暴露白名单 `window.firstLaunch.submitKey(key)` / `.skip()`。
- `main.js` 新增：
  - 状态 `firstLaunchInfo` / `firstLaunchWizard`。
  - IPC `firstlaunch:submit-key`：POST `/api/config` 写 `AGNES_API_KEY`，成功则 `closeFirstLaunchWizard()`。
  - IPC `firstlaunch:skip`：关闭向导（保留无 Key 状态，用户后续在设置填）。
  - `openFirstLaunchWizard()`：480×340 BrowserWindow，仅当 `!key_present` 弹出。

> 后端 `/api/config` + `update_env_file()` 已确认存在（`server.py:257`/`config.py:480`），Key 流真实可用，非占位。

---

## 4. 验证（无头模拟，见 Task D）

`first_launch.py` 在干净 backend 目录运行，输出：

```json
{"ok": true, "env_created": true, "dirs_created": ["sandbox","data","logs","docs"], "key_present": false, "asr": {"attempted": false}}
```

→ 触发向导。二次运行 `env_created:false, dirs_created:[]` → 幂等配置持久。

---

## 5. 已知限制

- 向导窗渲染 / 提交回写的实际 GUI 交互未在本无头环境重跑（Phase 8.6 已验证 Electron 启动+IPC 机制）。逻辑与接线均已静态核验。

---

## 6. 结论

✅ Task C 完成。首次启动流程覆盖初始化、目录创建、Key 检查与引导、可选 ASR，且全程零业务侵入、退出码恒 0 不阻断启动。
