# Bug Root Cause Analysis — `GET /api/interaction/activity` HTTP 500

**Hotfix**: Xiao6 v1.0.0 Runtime Hotfix R1
**Reported error**: `HTTP 500` / `{"error": "name 'field' is not defined"}`
**只改动文件**：`xiao6-ui/interaction_activity.py`（及直接相关测试文件）

---

## 1. `field` 变量来源

`field` 是 Python 标准库 `dataclasses` 模块的函数 `dataclasses.field()`，用于为数据类（dataclass）字段配置选项，典型用法是 `field(default_factory=...)` 指定默认值工厂。

在 `xiao6-ui/interaction_activity.py` 中，`field` 被用在 `Activity` 数据类的两个字段上：

- **L33** `timestamp: float = field(default_factory=time.time)`
- **L34** `metadata: Dict[str, Any] = field(default_factory=dict)`

而文件顶部的导入语句（**L19**）为：

```python
from dataclasses import dataclass, asdict
```

**`field` 并未被导入。** 因此当 Python 在模块导入时求值该类体，`field(...)` 会被当作一个未定义的名字 → 抛出 `NameError: name 'field' is not defined`。

---

## 2. 调用链

```
HTTP GET /api/interaction/activity
  └─ server.py do_GET
       ├─ 路径 L425（handler A）或 L1806（handler B）
       └─ try:
            import interaction_activity as ia          # ← 触发模块导入
            manager = ia.get_activity_manager()
            activities = manager.get_activities(limit=20)
            stats = manager.get_stats()
            return _send(200, JSON({ok, activities, stats}))
          except Exception as e:
            return _send(500, {"error": str(e)})        # ← 捕获 NameError
```

关键：`import interaction_activity` 位于 `try` 块内。导入该模块会执行其顶层代码，包括 `class Activity:` 的类体定义。在类体求值到 L33 时因 `field` 未定义而抛 `NameError`，被 `except` 捕获，最终以 `HTTP 500` + `{"error": "name 'field' is not defined"}` 返回。

（两条 handler 路径 L425 / L1806 逻辑完全一致，因此只要修复模块本身，两条路径同时恢复。）

---

## 3. 影响范围

| 维度 | 影响 |
| --- | --- |
| 受影响端点 | `GET /api/interaction/activity`（两个路由路径均 500） |
| 其他导入方 | 任何 `import interaction_activity` 的代码路径都在导入阶段失败（模块根本无法加载） |
| 前端（command_bar.js） | `loadActivities()` / `trackActivity()` 拉取该端点用于右栏「当前状态 / 运行任务」活动面板；当前因 `resp.ok` 为 false 而静默降级，面板恒为「暂无交互活动」 |
| 数据存储 | 无影响。模块为纯内存存储，不写数据库；缺导入错误不造成任何数据损坏或丢失 |
| server.py 架构 / API 路径 / DB 结构 / Agent Runtime 流程 | **不受影响**（错误在模块自身，与这些无关） |

**结论**：这是一个纯粹的「缺失导入」缺陷，修复点唯一且局限在 `interaction_activity.py` 的 import 行；后端契约、前端契约均保持不变。

---

## 4. 前端契约（修复后必须保持兼容）

后端端点返回：

```json
{
  "ok": true,
  "activities": [ { "activity_id", "type", "title", "status", "description", "intent_type", "timestamp", "relative_time" } ],
  "stats": { "total", "active", "completed", "max_activities" }
}
```

前端消费方式（command_bar.js）：
- `loadActivities()`：`fetch(...).ok` 校验 → `data.activities` 渲染每条 `type / title / status / intent_type / relative_time`
- `trackActivity()`：同端点刷新面板

修复后该结构必须**原样稳定返回 HTTP 200**，字段名与含义不变。

---

## 5. 修复方案（概要）

仅改一行：`interaction_activity.py` L19

```diff
- from dataclasses import dataclass, asdict
+ from dataclasses import dataclass, field, asdict
```

`field` 是 `dataclasses` 的标准导出，`default_factory=time.time` 与 `default_factory=dict` 均为正确用法。修复后模块可正常导入，端点恢复 200。

> 详细验证见回归测试与 curl 结果（修复后补充）。
