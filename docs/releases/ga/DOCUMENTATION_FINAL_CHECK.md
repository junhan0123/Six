# 发布文档最终核对 · 小6 v1.4.0

- **日期**：2026-08-05
- **执行身份**：Senior Release Engineer + QA Lead + Deployment Engineer
- **执行模式**：Verify → Execute → Validate → Report

---

## 1. 版本号一致性（全源 = 1.4.0）✅

| 来源 | 值 |
|---|---|
| `VERSION` 文件 | `1.4.0` |
| git tag | `v1.4.0-当前版本`（含 `1.4.0`） |
| `xiao6-ui/config.py` → `APP_VERSION` | `"1.4.0"` |
| `electron/package.json` → `version` | `1.4.0` |
| `README.md` / `RELEASE_NOTES.md` / `CHANGELOG.md` | `1.4.0` |
| `pyproject.toml` → `version` | `0.1.0`（Python 打包元数据，非用户可见版本，符合预期） |

---

## 2. 许可证一致性 ✅

- `LICENSE` = **MIT**，Copyright (c) 2026 小6
- `README.md` / `RELEASE_NOTES.md` / `CHANGELOG.md` / `THIRD_PARTY_LICENSES.md` 均声明 MIT © 2026 小6 —— 一致。

---

## 3. 产物文件名引用一致性 ✅（安装器二进制待构建）

- `README.md` §安装：Portable `小6-1.4.0-x64.exe`（**已存在** ✅）；Installer `小6-Setup-1.4.0-x64.exe`（引用命名与 `package.json` `nsis.artifactName` 完全一致；二进制构建中 = P-2）。
- `RELEASE_NOTES.md` / `CHANGELOG.md` 引用文件名与 `package.json` artifactName 完全一致。

---

## 4. 文档交叉引用 ✅

- `README.md` 链接 `RELEASE_NOTES.md` / `CHANGELOG.md` / `THIRD_PARTY_LICENSES.md` / `LICENSE` —— 均存在且可达。
- `THIRD_PARTY_LICENSES.md` 引用 `win-unpacked/LICENSE.electron.txt` 等（构建后随 `win-unpacked` 存在）。

---

## 5. 结论

- 发布文档的版本号、许可证、产物文件名引用、交叉链接**全部一致**。
- 唯一开放项：安装器二进制文件名已被文档正确引用，但二进制本身待 NSIS 构建完成（P-2）。
