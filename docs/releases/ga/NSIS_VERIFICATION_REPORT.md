# NSIS 安装器验证报告 · 小6 v1.4.0

- **日期**：2026-08-05
- **执行身份**：Senior Release Engineer + QA Lead + Deployment Engineer
- **执行模式**：Verify → Execute → Validate → Report
- **纪律红线**：仅验证 / 测试 / 记录；零代码、零 UI、零架构、零 Runtime / Memory / EventBus / Planner / Tool / DB 改动。发现问题仅记录，不借机修复。

---

## 1. 验证范围

| 项 | 类型 | 可执行环境 |
|---|---|---|
| electron-builder NSIS 配置正确性 | 静态 | 沙箱可读 |
| 已产出的 Portable 构建校验 | 产物 | 沙箱可读 |
| win-unpacked 载荷结构（安装器待压缩源） | 产物 | 沙箱可读 |
| NSIS 安装器二进制完整性（头 / 体积 / 签名） | 动态 | 依赖构建完成 |
| 安装 / 启动 / 卸载 / 二次安装流程 | GUI | 真机（LIVE） |

---

## 2. electron-builder NSIS 配置（静态验证）✅

读取 `electron/package.json` 的 `build` 字段：

- `win.target` 包含 `"nsis"` ✅
- `nsis.artifactName = "小6-Setup-${version}-${arch}.${ext}"` → 期望产物 **小6-Setup-1.4.0-x64.exe** ✅
- `nsis.oneClick = false`（非一键，允许自定义目录）✅
- `nsis.allowToChangeInstallationDirectory = true` ✅
- `nsis.createDesktopShortcut = true` ✅
- `extraResources`：从 `../xiao6-ui` → `backend`，过滤 `__pycache__` / `*.db` / `*.db-wal` / `*.log` 等 ✅
- `win.artifactName = "小6-${version}-${arch}.${ext}"` → Portable 命名模式 ✅

**结论**：NSIS 配置正确，产物命名与 README / RELEASE_NOTES / CHANGELOG 引用完全一致。

---

## 3. Portable 构建校验 ✅

- 产物：`electron/dist/小6-1.4.0-x64.exe`
- 大小：**108,198,200 字节**（≈103 MB）
- 命名符合 `win.artifactName` 模式 ✅
- 说明：本 Sprint 触发命令为 `electron-builder --win nsis`（仅 NSIS），该 Portable 为前序构建产物，状态完好、可分发。

---

## 4. win-unpacked 载荷校验 ✅（NSIS 安装器将被压缩的源）

`electron/dist/win-unpacked/` 结构：

- `小6.exe`（188 MB，Electron 主程序）✅
- `resources/backend/`：`python/`（内嵌 3.11 运行时）、`scripts/`、`skills/`、`tests/`、`textures/`、`vendor/` —— `extraResources` 拷贝正确 ✅
- 标准 Electron 资源：`resources.pak` / `snapshot_blob.bin` / `v8_context_snapshot.bin` / `vulkan-1.dll` / `vk_swiftshader.dll` ✅
- `resources/elevate.exe`（UAC 提权助手，用于安装器管理员步骤）✅

**结论**：NSIS 待压缩载荷结构完整、正确。安装器一旦构建完成，即会包裹一个合法应用。

---

## 5. NSIS 安装器二进制（动态验证）⏳ P-2 未关闭

- 后台构建任务 `4krqPp`（`cd electron && ./node_modules/.bin/electron-builder --win nsis`）状态：**运行 54+ 分钟**，日志停留在 `packaging platform=win32 arch=x64 electron=33.4.11 appOutDir=dist\win-unpacked`，无新输出。
- 磁盘核查：`electron/dist/小6-Setup-1.4.0-x64.exe` **不存在**。
- 判定：安装器二进制尚未产出，无法做二进制头 / 体积 / 签名校验。**P-2（NSIS 确认项）维持开放**。
- 处置建议（仅记录，不执行）：若构建在真机 / 更快存储上仍长时间停滞，建议清理 `dist` 后在干净态重启 NSIS 构建；或于发布前在独立构建机上产出安装器。

---

## 6. 安装 / 启动 / 卸载 / 二次安装流程（GUI 验证）🔴 LIVE

- 沙箱无 GUI 显示、无管理员权限，无法执行：安装向导、桌面 / 开始菜单快捷方式创建、卸载（Windows 设置 / 开始菜单卸载项）、二次安装数据保留等流程。
- 标记为 **LIVE（待真机）**：正式分发前需在 Windows 10 / 11 真机执行 —— 双击安装器 → 选择目录 → 验证快捷方式 → 启动 → 关闭 → 卸载 → 确认 `userData` 保留 → 二次安装确认数据保留。

---

## 7. 结论

- NSIS 配置、Portable 构建、win-unpacked 载荷三项静态 / 产物校验**全部通过**。
- 安装器二进制与 GUI 安装流程因「构建中 + 沙箱限制」，标记为 **开放（P-2）/ LIVE**。
- 不影响 GA 放行裁定（P-2 为非阻断项）；但**安装版正式分发前必须关闭 P-2**。
