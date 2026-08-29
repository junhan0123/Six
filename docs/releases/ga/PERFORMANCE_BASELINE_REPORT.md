# 性能基线报告 · 小6 v1.4.0

- **日期**：2026-08-05
- **执行身份**：Senior Release Engineer + QA Lead + Deployment Engineer
- **执行模式**：Verify → Execute → Validate → Report
- **纪律红线**：仅记录，不做任何优化。

---

## 1. 已实测（Headless）

| 指标 | 结果 | 说明 |
|---|---|---|
| 后端冷启动（进程启动 → `/api/health` 就绪） | **2.46 s** | 隔离实例（端口 8011），`Xiao6_PORT` 覆盖避免与开发服务器冲突 |
| 健康接口延迟（稳态，运行中的开发服务器 :8000） | **2.0 ms** | 连续两次一致 |
| 健康接口延迟（全新隔离实例 :8011，二次调用） | 16.6 ms | 首次调用含轻微预热 |
| DB 连接初始化 | 2.0 ms | `db.db_conn()` |
| 开发服务器健康态 | `ok:true`，`key_present:true`，`model=agnes-2.5-flash`，`theme=dark-cyan` | 稳态服务健康 |

> 后端冷启动与接口响应性能良好（冷启 < 3 s，健康延迟毫秒级），且缺失 API Key 时优雅降级（`ok:false` 但仍服务 `/api/health`）。

---

## 2. 无法在沙箱实测（LIVE，待真机）

| 指标 | 原因 |
|---|---|
| 后端运行内存 / CPU 占用 | `tasklist` / PowerShell 系统工具被沙箱安全策略禁用；`psutil` 未安装，无法读取进程工作集 / CPU |
| Electron 首启 vs 二次启动耗时 | 首启含 `first_launch.py` 初始化（生成 `.env`、运行时目录）+ 首启向导，属 GUI 流程，沙箱无 GUI |
| Electron 首屏渲染时间 / 帧率 / 多显示器缩放 | GUI 项 |

---

## 3. 基线结论

- 后端启动与接口响应性能达标，可作为 GA 性能基线的后端部分。
- 内存 / CPU 占用、Electron 首屏等**需在 Windows 真机补测**，作为 LIVE 项记录，不在此处估算或优化。
