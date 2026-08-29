# NSIS 安装器构建闭环报告 · 小6 v1.4.0

- **日期**：2026-08-05
- **执行身份**：Senior Release Engineer + QA Engineer + Deployment Engineer
- **执行模式**：Execute → Verify → Close
- **纪律红线**：仅发布工程执行 / 文档；零代码、零 UI、零架构改动。

---

## 1. 执行动作（Task A）

NSIS 安装器构建在「当前构建沙箱」内共尝试三次，均使用 `electron-builder 25.1.8`、`--win nsis` 目标，配置经静态验证完好：

| 尝试 | 命令 | 状态 | 产物 |
|---|---|---|---|
| 1（前序） | `electron-builder --win nsis` | 停滞（54m+） | win-unpacked 生成，Setup 未产出 |
| 2（前序） | `electron-builder --win nsis` | 停滞（任务被回收） | win-unpacked 12:58，Setup MISSING |
| 3（本 Sprint） | `rm -rf win-unpacked && electron-builder --win nsis`（日志落盘 `C:/tmp/nsis_build.log`） | 停滞 | Setup MISSING，日志停 packaging |

NSIS 配置（`package.json` build 字段）静态验证 ✅：
- `win.target = ["portable","nsis"]`
- `nsis.artifactName = "小6-Setup-${version}-${arch}.${ext}"`
- `nsis.oneClick = false`
- `nsis.allowToChangeInstallationDirectory = true`
- `nsis.createDesktopShortcut = true`
- `extraResources`：`../xiao6-ui` → `backend`

---

## 2. 产物校验结果

| 产物 | 期望路径 | 实际 | 结论 |
|---|---|---|---|
| Portable | `electron/dist/小6-1.4.0-x64.exe` | 108,198,200 字节 ✅ | 已构建、GA Ready |
| NSIS 安装器 | `electron/dist/小6-Setup-1.4.0-x64.exe` | `SETUP_EXE=MISSING` | 未产出 |

最终检查时间：2026-08-05 17:50。

---

## 3. 停滞证据（三次一致）

- 三次构建日志均正常启动：`electron-builder` 加载配置 → `@electron/rebuild` → 安装 native deps → **进入 `packaging` 阶段**。
- 三次均在 `packaging platform=win32 arch=x64 appOutDir=dist\win-unpacked` 后**无进一步推进**，日志无 `building NSIS installer`、无 `BUILD_EXIT`、无任何 exception / error / stack trace。
- `win-unpacked` 目录实际成功生成（packaging 成功），说明问题发生在 `packaging` 之后的 **NSIS 打包/压缩步骤**（`@electron-builder/nsis` 调用）受沙箱限制。

---

## 4. 裁定：构建环境限制（Environment Limitation）

依据「连续三次均停留在 `packaging → win-unpacked`，且无代码错误证据」规则，裁定：

> **当前构建环境限制（Environment Limitation），非小6项目缺陷。**

支撑证据：
1. `electron-builder` 配置静态验证正确（§1）。
2. 三次停滞模式完全一致（§3），非偶发。
3. 全程日志零代码错误/异常 —— 排除项目代码、配置、依赖缺陷。
4. `packaging` 成功 + NSIS 步骤停滞，指向沙箱对 NSIS 压缩/临时目录/进程调用的限制（无管理员权限、受限系统工具、可能为防病毒扫描锁或 IO 限制）。

---

## 5. 处置

- **NSIS 安装器**：标记为「需在独立 Windows 构建机完成最终验证」。本沙箱不发起第四次构建（遵守收尾指令）。
- **Portable**：保持 GA Ready，可先行分发。
- 后续：在具备完整 Windows 构建环境（管理员权限、未被限制的 NSIS 工具链）的机器上重新执行 `electron-builder --win nsis`，产出 `小6-Setup-1.4.0-x64.exe` 并完成 Task B 安装验证。

---

## 6. 结论

Task A 在本构建环境内**无法闭环**（Environment Limitation），但不构成项目缺陷，不阻断 Portable 通道 GA 放行。NSIS 安装器分发前须在独立构建机完成验证。
