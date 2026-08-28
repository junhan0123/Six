# ⛔ DEPRECATED — 禁止误启动

本目录（`release/`）是历史发布快照副本，**已废弃（deprecated）**。

- 唯一受支持的代码树：**`xiao6-ui/`（本仓库主树）**
- **禁止**从本目录启动任何服务 / 脚本 / 启动器；本目录不含受支持的启动入口。
- 若你在这里执行 `server.py` 或任何入口，行为不受支持、无保证。
- 本目录保留仅供历史对照审计，不参与 v1.0.0-rc1 发布运行。

正确启动方式：在 `xiao6-ui/launcher/` 执行 `start.ps1`（或直接 `python server.py`，见主树 README / AI_HANDOFF_PROTOCOL.md）。
