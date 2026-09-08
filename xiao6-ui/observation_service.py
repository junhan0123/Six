#!/usr/bin/env python3
"""PHASE 129 — Observation Service (完整重写版)

只读观察层。监听 EventBus 任务事件，分析状态，产生 Observations。
不修改 Runtime，不自动执行。

设计原则：
1. 纯函数分析：输入 → 分析 → 输出 Observation
2. 规则可解释：每个 Observation 有明确的 reason
3. 边界安全：null/undefined/异常数据不崩溃
4. 零副作用：只读，不写数据库，不改 Runtime
"""

from __future__ import annotations

import time
import threading
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List
from datetime import datetime

# ============================================================
# Constants
# ============================================================

HEALTH_GOOD = "GOOD"
HEALTH_WARNING = "WARNING"
HEALTH_STALE = "STALE"
HEALTH_FAILED = "FAILED"

RUNNING_STATUSES = {"open", "running", "in_progress", "active", "pending"}
DONE_STATUSES = {"done", "completed", "finished", "success"}
FAILED_STATUSES = {"failed", "error", "failure"}

# 分析阈值
STALE_WARNING_HOURS = 24
STALE_STALE_HOURS = 72

# Event Bus Topics
TOPIC_TASK_LIFECYCLE = "xiao6.task.lifecycle"
TOPIC_GOAL_LIFECYCLE = "xiao6.goal.lifecycle"


# ============================================================
# Observation Data Model
# ============================================================

@dataclass
class Observation:
    """单条观察记录。"""
    obs_id: str
    timestamp: float
    source: str          # 来源：event / manual / system
    event_type: Optional[str] = None
    goal_id: Optional[int] = None
    task_id: Optional[str] = None
    
    # 分析结果
    health_status: str = HEALTH_GOOD
    health_reason: str = ""
    
    # 风险信号
    risk_level: str = "none"      # none / low / medium / high
    risk_signal: str = ""
    
    # 建议动作（只读建议，不执行）
    suggested_action: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_frontend(self) -> Dict[str, Any]:
        """序列化到前端格式。"""
        return {
            "id": self.obs_id,
            "timestamp": self.timestamp,
            "source": self.source,
            "event_type": self.event_type,
            "health": {
                "status": self.health_status,
                "reason": self.health_reason
            },
            "risk": {
                "level": self.risk_level,
                "signal": self.risk_signal
            },
            "suggestion": self.suggested_action
        }


# ============================================================
# Health Analyzer
# ============================================================

class HealthAnalyzer:
    """任务健康度分析器（纯函数）。"""
    
    @staticmethod
    def analyze(task: Dict[str, Any]) -> Dict[str, str]:
        """
        分析任务健康度。
        
        Returns:
            {"status": str, "reason": str}
        """
        if not task or not task.get("id"):
            return {"status": HEALTH_GOOD, "reason": ""}
        
        status = str(task.get("status", "")).lower()
        updated = task.get("updated") or task.get("updated_at")
        
        # 失败任务
        if any(s in status for s in FAILED_STATUSES):
            return {"status": HEALTH_FAILED, "reason": "任务失败需要处理"}
        
        # 已完成任务
        if any(s in status for s in DONE_STATUSES):
            return {"status": HEALTH_GOOD, "reason": "任务正常完成"}
        
        # 运行中任务：检查是否停滞
        if any(s in status for s in RUNNING_STATUSES):
            if updated:
                hours_since = _hours_since(updated)
                current_step = task.get("current_step", 0) or 0
                total_steps = task.get("total_steps", 0) or 0
                has_progress = total_steps > 0 and current_step > 0
                
                if hours_since >= STALE_STALE_HOURS and not has_progress:
                    return {"status": HEALTH_STALE, "reason": f"任务超过{STALE_STALE_HOURS}小时没有进度更新"}
                
                if hours_since >= STALE_WARNING_HOURS and not has_progress:
                    return {"status": HEALTH_WARNING, "reason": f"任务{STALE_WARNING_HOURS}小时无进度更新"}
            
            return {"status": HEALTH_GOOD, "reason": "任务正在正常推进"}
        
        # 等待执行
        return {"status": HEALTH_GOOD, "reason": "任务等待执行"}


def _hours_since(timestamp) -> float:
    """计算距现在的小时数。"""
    try:
        if isinstance(timestamp, (int, float)):
            dt = datetime.fromtimestamp(timestamp)
        else:
            dt = datetime.fromisoformat(str(timestamp))
        diff = datetime.now() - dt
        return diff.total_seconds() / 3600
    except (ValueError, TypeError, OSError):
        return 0


# ============================================================
# Risk Detector
# ============================================================

class RiskDetector:
    """风险信号检测器（纯函数）。"""
    
    @staticmethod
    def detect(task: Dict[str, Any], health: Dict[str, str]) -> Dict[str, str]:
        """
        检测风险信号。
        
        Returns:
            {"level": str, "signal": str}
        """
        if not task:
            return {"level": "none", "signal": ""}
        
        status = str(task.get("status", "")).lower()
        
        # 高风险：失败
        if any(s in status for s in FAILED_STATUSES):
            error = task.get("error") or task.get("note") or ""
            return {
                "level": "high",
                "signal": f"任务失败: {error[:80]}" if error else "任务失败需要处理"
            }
        
        # 中风险：停滞
        if health.get("status") == HEALTH_STALE:
            return {
                "level": "medium",
                "signal": "任务长时间无进度更新"
            }
        
        # 低风险：警告
        if health.get("status") == HEALTH_WARNING:
            return {
                "level": "low",
                "signal": "任务进度可能停滞"
            }
        
        return {"level": "none", "signal": ""}


# ============================================================
# Observation Service
# ============================================================

class ObservationService:
    """观察服务：监听 EventBus，分析任务状态，产生 Observations。"""
    
    def __init__(self, event_bus=None):
        self._bus = event_bus
        self._running = False
        self._thread = None
        self._lock = threading.Lock()
        self._observations: List[Observation] = []
        self._start_time: Optional[float] = None
        self.stats = {
            "started_at": None,
            "observations_generated": 0,
            "events_processed": 0,
            "errors_count": 0
        }
        self._observed_tasks: set = set()  # 已观察的任务ID，避免重复
    
    def start(self):
        """启动观察服务，订阅 EventBus 任务事件。"""
        if self._running:
            return
        self._running = True
        self._start_time = time.time()
        self.stats["started_at"] = datetime.now().isoformat()
        
        # 订阅任务生命周期事件
        try:
            from eventbus import bus
            self._bus = bus
            
            # 订阅 TASK_CREATED / TASK_COMPLETED / TASK_FAILED
            bus.subscribe("xiao6.task.lifecycle", self._on_task_event, async_=True)
            
            print("[Observation Service] 已订阅任务生命周期事件")
        except Exception as e:
            print(f"[Observation Service] 订阅事件失败: {e}")
            self.stats["errors_count"] += 1
        
        print("[Observation Service] 已启动")
    
    def stop(self):
        """停止观察服务。"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
    
    def _on_task_event(self, event):
        """处理任务生命周期事件。"""
        try:
            payload = event.payload or {}
            task_id = payload.get("taskId") or payload.get("task_id")
            goal_id = payload.get("goalId") or payload.get("goal_id")
            event_type = payload.get("eventType") or getattr(event, 'topic', '')
            
            if not task_id:
                return
            
            # 获取任务数据
            task = self._fetch_task(task_id)
            if not task:
                return
            
            # 生成观察
            self._observe_task(task, event_type=event_type, goal_id=goal_id)
            self.stats["events_processed"] += 1
            
        except Exception as e:
            print(f"[Observation Service] 处理任务事件失败: {e}")
            self.stats["errors_count"] += 1
    
    def _fetch_task(self, task_id: str) -> Optional[Dict]:
        """从数据库获取任务数据（只读）。"""
        try:
            from db import db_conn
            conn = db_conn()
            try:
                row = conn.execute(
                    "SELECT id, title, status, note, description, created, updated, "
                    "current_step, total_steps, history, goal_id "
                    "FROM tasks WHERE id = ?",
                    (task_id,)
                ).fetchone()
                if row:
                    return dict(row)
            finally:
                conn.close()
        except Exception as e:
            print(f"[Observation] 获取任务 {task_id} 失败: {e}")
        return None
    
    def _observe_task(self, task: Dict, source: str = "event", 
                      event_type: Optional[str] = None, goal_id: Optional[int] = None):
        """生成并存储观察记录。"""
        # 分析健康度
        health = HealthAnalyzer.analyze(task)
        
        # 检测风险
        risk = RiskDetector.detect(task, health)
        
        # 生成建议
        suggestion = self._generate_suggestion(task, health, risk)
        
        # 创建观察记录
        obs = Observation(
            obs_id=str(len(self._observations) + 1),
            timestamp=time.time(),
            source=source,
            event_type=event_type,
            task_id=str(task.get("id")),
            goal_id=goal_id or task.get("goal_id"),
            health_status=health["status"],
            health_reason=health["reason"],
            risk_level=risk["level"],
            risk_signal=risk["signal"],
            suggested_action=suggestion
        )
        
        # 存储
        self._store_observation(obs)
    
    def _store_observation(self, obs: Observation):
        """存储观察记录（线程安全）。"""
        with self._lock:
            self._observations.append(obs)
            self.stats["observations_generated"] += 1
            
            # 保留最近 100 条
            if len(self._observations) > 100:
                self._observations = self._observations[-100:]
    
    def _generate_suggestion(self, task: Dict, health: Dict, risk: Dict) -> str:
        """生成建议动作（只读建议）。"""
        status = health.get("status", HEALTH_GOOD)
        risk_level = risk.get("level", "none")
        
        if status == HEALTH_FAILED:
            return "建议检查失败原因并重新执行"
        
        if status == HEALTH_STALE:
            return "建议检查任务是否卡住，必要时手动干预"
        
        if status == HEALTH_WARNING:
            return "建议关注任务进度"
        
        if risk_level == "high":
            return "建议立即处理失败任务"
        
        return ""
    
    def get_observations(self, limit: int = 20) -> List[Dict]:
        """获取最近的观察记录。"""
        with self._lock:
            recent = self._observations[-limit:]
            return [o.to_frontend() for o in recent]
    
    def get_stats(self) -> Dict:
        """获取服务统计。"""
        return {
            **self.stats,
            "observation_count": len(self._observations),
            "running": self._running
        }


# ============================================================
# 全局单例
# ============================================================

_instance: Optional[ObservationService] = None
_instance_lock = threading.Lock()


def get_observation_service() -> ObservationService:
    """获取全局 Observation Service 单例。"""
    global _instance
    with _instance_lock:
        if _instance is None:
            from eventbus import bus
            _instance = ObservationService(event_bus=bus)
        return _instance


def init_observation_service():
    """初始化并启动 Observation Service。"""
    service = get_observation_service()
    service.start()
    return service


# ============================================================
# 测试入口
# ============================================================

if __name__ == "__main__":
    print("=== Observation Service 单元测试 ===\n")
    
    # Test 1: Health Analyzer
    print("Test 1: Health Analyzer")
    
    test_cases = [
        ({"id": "1", "status": "completed"}, HEALTH_GOOD),
        ({"id": "2", "status": "running", "updated": datetime.now().isoformat()}, HEALTH_GOOD),
        ({"id": "3", "status": "failed"}, HEALTH_FAILED),
        ({"id": "4", "status": "running", "updated": datetime.now().timestamp() - 80*3600}, HEALTH_STALE),
    ]
    
    for task, expected in test_cases:
        result = HealthAnalyzer.analyze(task)
        status = "PASS" if result["status"] == expected else "FAIL"
        print(f"  {status}: {task.get('status')} -> {result['status']}")
    
    # Test 2: Risk Detector
    print("\nTest 2: Risk Detector")
    
    health_good = {"status": HEALTH_GOOD, "reason": "ok"}
    health_failed = {"status": HEALTH_FAILED, "reason": "failed"}
    health_stale = {"status": HEALTH_STALE, "reason": "stale"}
    
    test_tasks = [
        ({"id": "1", "status": "failed"}, health_failed, "high"),
        ({"id": "2", "status": "running"}, health_good, "none"),
    ]
    
    for task, health, expected_level in test_tasks:
        result = RiskDetector.detect(task, health)
        status = "PASS" if result["level"] == expected_level else "FAIL"
        print(f"  {status}: status={task.get('status')} -> risk={result['level']}")
    
    # Test 3: Service Instantiation
    print("\nTest 3: Service Instantiation")
    
    svc = ObservationService()
    svc.start()
    assert svc._running == True
    assert svc.stats["observations_generated"] == 0
    print("  PASS: service started")
    
    # Test 4: Direct Observation
    print("\nTest 4: Direct Observation Generation")
    
    failed_task = {"id": "99", "status": "failed", "note": "Connection timeout"}
    svc._observe_task(failed_task, source="manual", event_type="TEST")
    obs = svc.get_observations(1)[0]
    assert obs["health"]["status"] == HEALTH_FAILED
    assert obs["risk"]["level"] == "high"
    print("  PASS: failed task generates correct observation")
    
    print("\n=== All Tests Complete ===")
