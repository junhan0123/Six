# 真机安装测试报告 · 小6 v1.4.0

- **日期**：2026-08-05
- **执行身份**：Senior Release Engineer + QA Engineer + Deployment Engineer
- **执行模式**：Execute → Verify → Close
- **纪律红线**：仅发布工程执行 / 文档；零代码、零 UI、零架构改动。

---

## 1. 必须真实验证项（Task B）

| 项 | 方法 |
|---|---|
| 安装 | 运行 NSIS 安装器 → 选择目录 → 完成 |
| 启动 | 桌面快捷方式 / 开始菜单 → 启动 `小6.exe` |
| 退出 | 正常关闭窗口 / 托盘退出 |
| 卸载 | 控制面板 / 开始菜单卸载项 |
| 二次安装 | 卸载后重新安装 → 确认干净无残留冲突 |

---

## 2. 沙箱可执行性判定

- **前置条件缺失**：NSIS 安装器 `小6-Setup-1.4.0-x64.exe` 在本沙箱未产出（Environment Limitation，见 `NSIS_BUILD_CLOSURE.md`）。
- 因此安装版「安装 / 卸载 / 二次安装」**无法在沙箱执行**，标记 **Blocked by Environment Limitation**。
- 沙箱无 GUI 显示，即便有安装器，「启动 / 退出」的视觉验证亦不可行（标 LIVE）。

---

## 3. Portable 运行可行性（间接证据，已验证）

Portable 包无需安装，其运行可行性由既有证据覆盖：

- **后端启动可达性**：隔离实例冷启 2.46s、健康检查 2.0ms（继承前序实测）✅
- **崩溃恢复**：WAL + 幂等迁移硬崩溃实测 PASSED ✅
- **真实 Electron GUI 验收**：前序 Phase 8.6 以 puppeteer CDP 连接真实 Electron（非无头），12 Case 验收通过并截图 ✅
- 结论：Portable 通道「可启动、可运行、可交互」已由既有真实验证覆盖。

---

## 4. 裁定

- **安装版（NSIS）测试**：Blocked —— 需在独立 Windows 构建机成功产出 Setup.exe 后，于真机执行 §1 五项验证。
- **Portable 通道**：运行可行性已由既有真实证据覆盖，无需额外安装测试。

---

## 5. 结论

Task B 安装版验证因 Environment Limitation 无法在当前环境闭环，标记为待独立构建机产出后补测；Portable 通道运行可行性已由前序真实验收覆盖。不阻断 Portable GA 放行。
