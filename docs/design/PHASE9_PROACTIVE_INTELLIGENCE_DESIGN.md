# Xiao6 Phase 9 — Proactive Intelligence Architecture v1.0

**设计版本**: v1.0  
**设计日期**: 2026-08-04  
**阶段**: Phase 9 — Proactive Intelligence Layer  
**状态**: Design Pending Approval

---

## 一、设计概述

### 1.1 目标

将 Xiao6 从 **Reactive AI Assistant** 升级为 **Proactive AI Operating System**：

- **Reactive**: 等待用户指令 → 执行
- **Proactive**: 感知场景 → 主动建议/行动 → 用户确认/静默执行

### 1.2 核心原则

```
1. 用户控制优先: Proactive 行为必须可被用户控制（静默/确认/关闭）
2. 安全网关不变: 所有主动行动必须经 PermissionGuard
3. 单一来源: 复用 EventBus/AppState/Memory，不新建
4. 可观察性: 所有 Proactive 行为可追溯、可审计
```

---

## 二、架构设计

### 2.1 系统组成

```
┌─────────────────────────────────────────────────────────┐
│                   Proactive Intelligence Layer           │
├─────────────────────────────────────────────────────────┤
│  ProactiveEngine (决策层)                                │
│    ├── SceneDetector (场景检测)                          │
│    ├── RiskEvaluator (风险评估)                          │
│    ├── UserPreference (用户偏好)                         │
│    └── DecisionMaker (决策生成)                          │
├─────────────────────────────────────────────────────────┤
│  Scheduler (调度层)                                      │
│    ├── TimerScheduler (周期任务)                         │
│    ├── EventScheduler (事件驱动)                         │
│    └── DelayScheduler (延迟任务)                         │
├─────────────────────────────────────────────────────────┤
│  ControlPanel (控制层)                                   │
│    ├── SilentMode (静默模式)                             │
│    ├── NotificationPolicy (通知策略)                      │
│    └── AllowList/DenyList (允许/拒绝列表)                  │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              复用现有系统 (不新建)                         │
├─────────────────────────────────────────────────────────┤
│  EventBus (事件总线) → PROACTIVE 事件流                  │
│  PermissionGuard (权限闸门) → 风险评估                    │
│  AgentRuntime (执行器) → 目标执行                        │
│  Memory (记忆系统) → 上下文注入                          │
│  AppState (状态核心) → 状态查询                          │
└─────────────────────────────────────────────────────────┘
```

### 2.2 文件结构

```
xiao6-ui/
├── scheduler.py           ← 新增：周期任务调度
├── proactive_engine.py    ← 新增：主动决策引擎
├── proactive_config.py    ← 新增：用户偏好配置
└── (复用现有文件)
    ├── eventbus.py
    ├── permission_guard.py
    ├── agent_runtime.py
    ├── memory.py
    └── app-state.js (前端)
```

---

## 三、事件流设计

### 3.1 Proactive 事件流

```
用户触发 (或周期触发)
    ↓
ProactiveEngine.detect()
    ↓
SceneDetector.analyze() → 检测场景
    ↓
RiskEvaluator.evaluate() → 评估风险
    ↓
UserPreference.check() → 检查用户偏好
    ↓
DecisionMaker.decide() → 生成决策
    ├── auto → 直接执行
    ├── confirm → 请求用户确认
    └── skip → 跳过
    ↓
PermissionGuard.run() → 权限闸门（复用）
    ↓
AgentRuntime.submit_goal() → 目标执行（复用）
    ↓
EventBus.publish_system("PROACTIVE", ...) → 事件通知
```

### 3.2 事件定义

```javascript
// zz-events.js SYSTEM_EVENTS 新增（预算 ≤10）
SYSTEM_EVENTS: {
    // 已有
    PROACTIVE: 'proactive',
    SCENE: 'scene',
    MEMORY_REMINDER: 'memory_reminder',
    AGENT_STATE: 'agent_state',
    // ...
    
    // Phase 9 新增（预算内）
    PROACTIVE_DECIDED: 'proactive_decided',      // 主动决策结果
    PROACTIVE_EXECUTING: 'proactive_executing',  // 主动执行开始
    PROACTIVE_COMPLETED: 'proactive_completed',  // 主动执行完成
    PROACTIVE_DENIED: 'proactive_denied',        // 主动行为被拒绝
}
```

### 3.3 事件 payload 示例

```python
# PROACTIVE_DECIDED
{
    "proactiveId": "prog_abc123",
    "scene": "low_battery",
    "decision": "confirm",
    "risk": "LOW",
    "suggestion": "建议连接充电器",
    "timestamp": 1234567890
}

# PROACTIVE_EXECUTING
{
    "proactiveId": "prog_abc123",
    "action": "open_application",
    "target": "com.apple.TextEdit",
    "goalId": "goal_xyz789"
}
```

---

## 四、权限模型

### 4.1 Proactive 权限层级

```
风险等级    决策模式          用户控制
─────────────────────────────────────────
LOW         auto            可配置静默/确认
MEDIUM      confirm         必须用户确认
HIGH        deny            禁止主动执行
CRITICAL    deny            禁止主动执行
```

### 4.2 权限决策流程

```
Proactive Engine 决策
    ↓
RiskEvaluator.evaluate(capability)
    ↓
风险等级 = CapabilityRegistry.risk_of(capability)
    ↓
┌─────────────────────────────────────┐
│ 风险等级 == LOW                     │
│   → 检查用户偏好 (silent_mode)      │
│   → silent_mode=True → auto 执行    │
│   → silent_mode=False → confirm     │
├─────────────────────────────────────┤
│ 风险等级 == MEDIUM                  │
│   → 必须 confirm                    │
├─────────────────────────────────────┤
│ 风险等级 == HIGH/CRITICAL           │
│   → 直接 deny                       │
└─────────────────────────────────────┘
    ↓
PermissionGuard.run() (复用)
```

### 4.3 用户控制配置

```python
# proactive_config.py
class ProactiveConfig:
    def __init__(self):
        # 静默模式：低风险提示用户但不等待确认
        self.silent_mode: bool = False
        
        # 通知策略
        self.notification_policy: str = "important"  # "always" | "important" | "none"
        
        # 确认阈值：高于此风险等级必须确认
        self.confirm_threshold: str = "MEDIUM"  # "LOW" | "MEDIUM" | "HIGH"
        
        # 允许/拒绝列表（精确匹配能力名）
        self.allow_list: list = []  # 空 = 全部允许
        self.deny_list: list = ["delete", "system", "network"]  # 默认拒绝高危
        
        # 检测频率（秒）
        self.check_interval: int = 60  # 每 60 秒检测一次
```

---

## 五、主动任务生命周期

### 5.1 生命周期状态

```
SCENED → EVALUATING → DECIDED → (auto|confirm|skip)
                              ↓
                        EXECUTING → COMPLETED / DENIED / FAILED
```

### 5.2 状态机定义

```python
# proactive_engine.py
class ProactiveTask:
    def __init__(self, task_id, scene, risk, suggestion):
        self.task_id = task_id
        self.scene = scene
        self.risk = risk
        self.suggestion = suggestion
        self.status = "SCENED"  # SCENED → EVALUATING → DECIDED → EXECUTING → COMPLETED
        self.decision = None    # auto | confirm | skip
        self.goal_id = None     # 关联的 Goal ID
        self.created_at = time.time()
```

### 5.3 生命周期事件

```python
# 状态转变事件
SCENED            → 场景检测到
EVALUATING        → 开始风险评估
DECIDED           → 决策生成完成
EXECUTING         → 开始执行（经 PermissionGuard）
COMPLETED         → 执行完成
DENIED            → 被拒绝（风险过高/用户拒绝/在拒绝列表）
FAILED            → 执行失败
```

---

## 六、Scheduler 设计

### 6.1 接口定义

```python
# scheduler.py
class Scheduler:
    """周期任务调度器"""
    
    def __init__(self):
        self._timers = {}  # task_id → Timer
        self._lock = threading.Lock()
    
    def schedule_once(self, delay_seconds, callback, task_id=None):
        """延迟执行一次"""
        ...
    
    def schedule_interval(self, interval_seconds, callback, task_id=None):
        """周期执行"""
        ...
    
    def cancel(self, task_id):
        """取消任务"""
        ...
    
    def shutdown(self):
        """关闭所有任务"""
        ...
```

### 6.2 Proactive 调度集成

```python
# proactive_engine.py
class ProactiveEngine:
    def __init__(self, scheduler: Scheduler):
        self.scheduler = scheduler
        self._check_task_id = None
    
    def start(self):
        """启动主动检测循环"""
        self._check_task_id = self.scheduler.schedule_interval(
            interval_seconds=60,  # 可配置
            callback=self._periodic_check,
            task_id="proactive_check"
        )
    
    def stop(self):
        """停止主动检测"""
        if self._check_task_id:
            self.scheduler.cancel(self._check_task_id)
```

---

## 七、Risk Analysis

### 7.1 风险场景

| 场景 | 风险 | 缓解措施 |
|------|------|----------|
| 误触发主动行动 | 中 | 用户确认机制 + 可配置阈值 |
| 高频检测影响性能 | 低 | 可调间隔 + 防抖 |
| 权限绕过 | 高 | 强制 PermissionGuard |
| 记忆污染 | 中 | 隔离 Proactive 上下文 |
| 用户疲劳 | 中 | 静默模式 + 通知频率限制 |

### 7.2 防御策略

```
1. 默认 deny 高危操作
2. 所有 Proactive 行动记录审计日志
3. 用户可随时关闭 Proactive 功能
4. 执行前必须经 PermissionGuard
5. 检测间隔可调（默认 60s）
```

---

## 八、实施计划

### 8.1 Order 分解

| Order | 内容 | 依赖 | 工作量 |
|-------|------|------|--------|
| Order 1 | Scheduler 实现 | 无 | 小 |
| Order 2 | ProactiveEngine 核心 | Order 1 | 中 |
| Order 3 | ProactiveConfig 配置 | 无 | 小 |
| Order 4 | 前端事件订阅 | Order 2 | 小 |
| Order 5 | 测试覆盖 | Order 1-4 | 中 |

### 8.2 预算控制

```
新增事件: 4 个 (PROACTIVE_DECIDED, PROACTIVE_EXECUTING, PROACTIVE_COMPLETED, PROACTIVE_DENIED)
新增文件: 3 个 (scheduler.py, proactive_engine.py, proactive_config.py)
新增代码: ~500 行
复用系统: EventBus, PermissionGuard, AgentRuntime, Memory, AppState
```

---

## 九、设计确认

### 9.1 检查清单

- [ ] 无第二 EventBus/Memory/Runtime/Permission
- [ ] 所有 Proactive 行动经 PermissionGuard
- [ ] 用户可控制静默/确认/关闭
- [ ] 高危操作默认 deny
- [ ] 事件预算可控（≤10 新增）
- [ ] 测试覆盖完整

### 9.2 待用户确认

1. **设计是否满足需求？**
2. **Order 分解是否合理？**
3. **风险缓解是否充分？**
4. **是否可以开始 Order 1 实现？**

---

**设计人**: Agnes  
**设计日期**: 2026-08-04 20:50  
**状态**: ⏸ 等待 Review 批准
