#!/usr/bin/env python3
"""庄周 · ai_core —— AI OS 核心包（Phase B 抽离，Extract Never Rewrite）。

本包按 Phase B 规划逐步收纳 AI Core 子系统：lifecycle / context / execution /
capability / health / metrics / recovery / logging。每个模块仅抽离既有逻辑、保持行为
完全一致，不重写、不新增状态/功能/优化、不触碰业务/网络/权限/事件契约。

红线（冻结）：
- 单一 Runtime / 单一状态写入口 / 单一 EventBus / 单一 Permission。
- 本包是对 server.py 中既有 AI Core 逻辑的「搬迁」，不是新实现。

注意：本 __init__ 不重新导出子模块内的同名单例，以免 `ai_core.lifecycle` 子模块名被
单例实例遮蔽（shadowing）。请始终用 `from ai_core.<module> import <name>` 形式引用。
"""
