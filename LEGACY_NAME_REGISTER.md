# Legacy Name Register
## Xiao6 历史名称审计

---

## Runtime-critical（运行时关键）

| 旧名称 | 当前名称 | 文件 | 是否迁移 | 原因 |
|--------|----------|------|----------|------|
| ZHUANGZHOU_PORT | ZhuangZhou_PORT | config.py | 保留 | 环境变量名，向后兼容 |
| ZHUANGZHOU_PROXY_URL | XIAO6_PROXY_URL + ZHUANGZHOU_PROXY_URL | config.py | 双名并存 | 代理配置兼容 |
| ZHUANGZHOU_WEB_SEARCH_* | ZHUANGZHOU_WEB_SEARCH_* | config.py | 保留 | 搜索配置环境变量 |

---

## Documentation-only（仅文档）

| 旧名称 | 当前名称 | 文件 | 是否迁移 | 原因 |
|--------|----------|------|----------|------|
| zz-agent-runtime | agent_runtime.py 线程名 | agent/agent_runtime.py | 不迁移 | 非关键，保留记录 |
| zz-distill | agent_runtime.py 线程名 | agent/agent_runtime.py | 不迁移 | 非关键，保留记录 |

---

## Historical artifact（历史证据）

| 旧名称 | 当前名称 | 文件 | 是否迁移 | 原因 |
|--------|----------|------|----------|------|
| zz-icon, zz-close, zz-inbox | 前端 CSS 类名 | electron/* | 保留 | 前端资产，保留历史 |
| zhuangzhou-ui/ | xiao6-ui/ | 目录 | 已迁移 | 项目重命名 |
| zhuangzhou.db.bak* | xiao6.db.bak* | data/ | 已迁移 | 数据库重命名 |

---

## Dead code（死代码）

| 旧名称 | 当前名称 | 文件 | 是否迁移 | 原因 |
|--------|----------|------|----------|------|
| zhuangzhou_event | - | agent_runtime.py.migration-bak | 不删除 | 历史记录 |
| ZHUANGZHOU_ASR_PROVIDER | - | asr.py.migration-bak | 不删除 | 历史记录 |

---

## 审计结论

**无需大规模 rename。**

所有 ZHUANGZHOU_* 环境变量名均为用户配置，保留兼容性。

历史目录 zhuangzhou-ui/ 已迁移到 xiao6-ui/，旧路径不活跃。

---

END OF REGISTER
