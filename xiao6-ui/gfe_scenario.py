#!/usr/bin/env python3
"""PHASE 145 — GFE Scenario Engine Foundation

Global Foresight Engine (GFE) 情景引擎基础实现。
职责：
- 情景创建与管理
- 条件假设定义
- 影响路径计算
- 情景对比分析
- 概率权重支持

架构边界：
- 只读取其他 GFE 模块数据，不修改
- 不调用 Runtime/Execution
- 仅做情景推演
- 保持数据追溯性（provenance）
"""

from __future__ import annotations

import json
import time
import uuid
import threading
from dataclasses import dataclass, asdict, field
from typing import Optional, List, Dict, Any

from db import db_conn
from eventbus import publish_system


# ============================================================
# Constants
# ============================================================

# EventBus Topics
TOPIC_SCENARIO_CREATED = "gfe_scenario_created"
TOPIC_SCENARIO_EVALUATED = "gfe_scenario_evaluated"

# Impact directions
DIRECTION_POSITIVE = "positive"
DIRECTION_NEGATIVE = "negative"
DIRECTION_NEUTRAL = "neutral"

ALL_DIRECTIONS = [DIRECTION_POSITIVE, DIRECTION_NEGATIVE, DIRECTION_NEUTRAL]

# Dimensions
DIMENSION_ECONOMY = "economy"
DIMENSION_FINANCE = "finance"
DIMENSION_INDUSTRIES = "industries"
DIMENSION_TECHNOLOGY = "technology"
DIMENSION_ENERGY = "energy"
DIMENSION_TRADE = "trade"
DIMENSION_SOCIAL = "social"
DIMENSION_DIPLOMACY = "diplomacy"
DIMENSION_MILITARY = "military"

ALL_DIMENSIONS = [
    DIMENSION_ECONOMY, DIMENSION_FINANCE, DIMENSION_INDUSTRIES,
    DIMENSION_TECHNOLOGY, DIMENSION_ENERGY, DIMENSION_TRADE,
    DIMENSION_SOCIAL, DIMENSION_DIPLOMACY, DIMENSION_MILITARY
]


# ============================================================
# Data Models
# ============================================================

@dataclass
class Scenario:
    """情景模型。"""
    scenario_id: str
    question: str
    name: str
    description: Optional[str]
    assumptions: Dict[str, Any]
    probability: float
    confidence: float
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_frontend(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "question": self.question,
            "name": self.name,
            "description": self.description,
            "assumptions": self.assumptions,
            "probability": self.probability,
            "confidence": self.confidence,
            "created_at": self.created_at
        }


@dataclass
class ScenarioImpact:
    """情景影响模型。"""
    impact_id: str
    scenario_id: str
    dimension: str
    direction: str
    strength: float
    reason: Optional[str]
    confidence: float
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_frontend(self) -> Dict[str, Any]:
        return {
            "impact_id": self.impact_id,
            "scenario_id": self.scenario_id,
            "dimension": self.dimension,
            "direction": self.direction,
            "strength": round(self.strength, 3),
            "reason": self.reason,
            "confidence": round(self.confidence, 3),
            "created_at": self.created_at
        }


@dataclass
class ScenarioPath:
    """情景路径模型。"""
    path_id: str
    scenario_id: str
    source_node: str
    target_node: str
    impact_score: float
    time_horizon: Optional[int]
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_frontend(self) -> Dict[str, Any]:
        return {
            "path_id": self.path_id,
            "scenario_id": self.scenario_id,
            "source_node": self.source_node,
            "target_node": self.target_node,
            "impact_score": round(self.impact_score, 3),
            "time_horizon": self.time_horizon,
            "created_at": self.created_at
        }


# ============================================================
# Scenario Engine
# ============================================================

class ScenarioEngine:
    """情景引擎。

    核心功能：
    - 创建和管理情景
    - 定义条件假设
    - 计算影响路径
    - 对比多个情景
    - 支持概率权重
    """

    def __init__(self, db_conn_func=None):
        self._conn = db_conn_func or db_conn
        self._lock = threading.RLock()
        # 内存缓存
        self._scenarios: Dict[str, Scenario] = {}
        self._refresh_cache()

    def _refresh_cache(self):
        """刷新内存缓存。"""
        try:
            conn = self._conn()
            for row in conn.execute("SELECT * FROM gfe_scenarios").fetchall():
                scenario = self._row_to_scenario(row)
                self._scenarios[scenario.scenario_id] = scenario
        except Exception as e:
            print(f"[ScenarioEngine] 刷新缓存失败: {e}")

    def create_scenario(
        self,
        question: str,
        name: str,
        description: Optional[str] = None,
        assumptions: Optional[Dict[str, Any]] = None,
        probability: float = 0.5,
        confidence: float = 0.5
    ) -> Optional[Scenario]:
        """创建情景。"""
        try:
            with self._lock:
                conn = self._conn()
                scenario_id = f"scenario_{int(time.time())}_{uuid.uuid4().hex[:8]}"
                now = time.time()

                conn.execute(
                    """INSERT INTO gfe_scenarios
                       (scenario_id, question, name, description, assumptions, probability, confidence, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        scenario_id, question, name, description,
                        json.dumps(assumptions or {}), probability, confidence, now
                    )
                )
                conn.commit()

                scenario = Scenario(
                    scenario_id=scenario_id,
                    question=question,
                    name=name,
                    description=description,
                    assumptions=assumptions or {},
                    probability=probability,
                    confidence=confidence,
                    created_at=now
                )
                self._scenarios[scenario_id] = scenario

                # 发布 EventBus 事件
                self._emit_event(TOPIC_SCENARIO_CREATED, {
                    "scenario_id": scenario_id,
                    "name": name,
                    "question": question,
                    "timestamp": now
                })

                return scenario

        except Exception as e:
            print(f"[ScenarioEngine] 创建情景失败: {e}")
            return None

    def add_impact(
        self,
        scenario_id: str,
        dimension: str,
        direction: str,
        strength: float,
        reason: Optional[str] = None,
        confidence: float = 0.5
    ) -> Optional[ScenarioImpact]:
        """添加情景影响。"""
        try:
            with self._lock:
                conn = self._conn()

                # 验证情景存在
                if scenario_id not in self._scenarios:
                    row = conn.execute(
                        "SELECT * FROM gfe_scenarios WHERE scenario_id = ?",
                        (scenario_id,)
                    ).fetchone()
                    if not row:
                        return None
                    self._scenarios[scenario_id] = self._row_to_scenario(row)

                impact_id = f"impact_{int(time.time())}_{uuid.uuid4().hex[:8]}"
                now = time.time()

                conn.execute(
                    """INSERT INTO gfe_scenario_impacts
                       (impact_id, scenario_id, dimension, direction, strength, reason, confidence, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (impact_id, scenario_id, dimension, direction, strength, reason, confidence, now)
                )
                conn.commit()

                return ScenarioImpact(
                    impact_id=impact_id,
                    scenario_id=scenario_id,
                    dimension=dimension,
                    direction=direction,
                    strength=strength,
                    reason=reason,
                    confidence=confidence,
                    created_at=now
                )

        except Exception as e:
            print(f"[ScenarioEngine] 添加影响失败: {e}")
            return None

    def add_path(
        self,
        scenario_id: str,
        source_node: str,
        target_node: str,
        impact_score: float,
        time_horizon: Optional[int] = None
    ) -> Optional[ScenarioPath]:
        """添加情景路径。"""
        try:
            with self._lock:
                conn = self._conn()

                # 验证情景存在
                if scenario_id not in self._scenarios:
                    return None

                path_id = f"path_{int(time.time())}_{uuid.uuid4().hex[:8]}"
                now = time.time()

                conn.execute(
                    """INSERT INTO gfe_scenario_paths
                       (path_id, scenario_id, source_node, target_node, impact_score, time_horizon, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (path_id, scenario_id, source_node, target_node, impact_score, time_horizon, now)
                )
                conn.commit()

                return ScenarioPath(
                    path_id=path_id,
                    scenario_id=scenario_id,
                    source_node=source_node,
                    target_node=target_node,
                    impact_score=impact_score,
                    time_horizon=time_horizon,
                    created_at=now
                )

        except Exception as e:
            print(f"[ScenarioEngine] 添加路径失败: {e}")
            return None

    def evaluate_scenario(
        self,
        scenario_id: str,
        use_causal_graph: bool = True,
        use_world_state: bool = True
    ) -> Optional[Dict[str, Any]]:
        """评估情景。

        读取其他模块数据进行情景推演。
        """
        try:
            with self._lock:
                conn = self._conn()

                # 获取情景
                scenario = self.get_scenario(scenario_id)
                if not scenario:
                    return None

                result = {
                    "scenario_id": scenario_id,
                    "name": scenario.name,
                    "probability": scenario.probability,
                    "confidence": scenario.confidence,
                    "impacts": [],
                    "paths": [],
                    "overall_score": 0.0
                }

                # 获取该情景的影响
                impacts = self.get_impacts(scenario_id)
                result["impacts"] = [i.to_frontend() for i in impacts]

                # 计算整体得分
                if impacts:
                    total_strength = sum(i.strength * i.confidence for i in impacts)
                    total_weight = sum(i.confidence for i in impacts)
                    result["overall_score"] = total_strength / total_weight if total_weight > 0 else 0.0

                # 如果启用因果图谱，计算影响路径
                if use_causal_graph:
                    paths = self._calculate_impact_paths(scenario_id)
                    result["paths"] = [p.to_frontend() for p in paths]

                # 发布 EventBus 事件
                self._emit_event(TOPIC_SCENARIO_EVALUATED, {
                    "scenario_id": scenario_id,
                    "name": scenario.name,
                    "impact_count": len(impacts),
                    "overall_score": result["overall_score"],
                    "timestamp": time.time()
                })

                return result

        except Exception as e:
            print(f"[ScenarioEngine] 评估情景失败: {e}")
            return None

    def compare_scenarios(
        self,
        scenario_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """对比多个情景。"""
        try:
            results = []
            for scenario_id in scenario_ids:
                eval_result = self.evaluate_scenario(scenario_id)
                if eval_result:
                    results.append(eval_result)

            # 按整体得分排序
            results.sort(key=lambda x: x["overall_score"], reverse=True)
            return results

        except Exception as e:
            print(f"[ScenarioEngine] 对比情景失败: {e}")
            return []

    def get_scenario(self, scenario_id: str) -> Optional[Scenario]:
        """获取单个情景。"""
        if scenario_id in self._scenarios:
            return self._scenarios[scenario_id]

        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM gfe_scenarios WHERE scenario_id = ?",
            (scenario_id,)
        ).fetchone()

        if row:
            scenario = self._row_to_scenario(row)
            self._scenarios[scenario_id] = scenario
            return scenario

        return None

    def get_scenarios(
        self,
        question: Optional[str] = None,
        limit: int = 50
    ) -> List[Scenario]:
        """查询情景。"""
        try:
            conn = self._conn()
            query = "SELECT * FROM gfe_scenarios WHERE 1=1"
            params = []

            if question:
                query += " AND question = ?"
                params.append(question)

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            return [self._row_to_scenario(row) for row in rows if row]

        except Exception as e:
            print(f"[ScenarioEngine] 查询情景失败: {e}")
            return []

    def get_impacts(self, scenario_id: str) -> List[ScenarioImpact]:
        """查询情景影响。"""
        try:
            conn = self._conn()
            rows = conn.execute(
                "SELECT * FROM gfe_scenario_impacts WHERE scenario_id = ? ORDER BY created_at",
                (scenario_id,)
            ).fetchall()
            return [self._row_to_impact(row) for row in rows if row]

        except Exception as e:
            print(f"[ScenarioEngine] 查询影响失败: {e}")
            return []

    def get_paths(self, scenario_id: str) -> List[ScenarioPath]:
        """查询情景路径。"""
        try:
            conn = self._conn()
            rows = conn.execute(
                "SELECT * FROM gfe_scenario_paths WHERE scenario_id = ? ORDER BY created_at",
                (scenario_id,)
            ).fetchall()
            return [self._row_to_path(row) for row in rows if row]

        except Exception as e:
            print(f"[ScenarioEngine] 查询路径失败: {e}")
            return []

    # ---- 内部方法 ----

    def _calculate_impact_paths(self, scenario_id: str) -> List[ScenarioPath]:
        """计算情景影响路径（读取因果图谱）。"""
        try:
            paths = []
            # 这里只读取因果图谱，不修改
            # 实际实现会查询 gfe_causal_edges 表
            return paths
        except Exception as e:
            print(f"[ScenarioEngine] 计算影响路径失败: {e}")
            return []

    def _row_to_scenario(self, row) -> Scenario:
        """将 DB 行转换为 Scenario 对象。"""
        try:
            assumptions = json.loads(row[4] or "{}")
        except (json.JSONDecodeError, TypeError):
            assumptions = {}

        return Scenario(
            scenario_id=row[0],
            question=row[1],
            name=row[2],
            description=row[3],
            assumptions=assumptions,
            probability=float(row[5]) if row[5] else 0.5,
            confidence=float(row[6]) if row[6] else 0.5,
            created_at=float(row[7]) if row[7] else time.time()
        )

    def _row_to_impact(self, row) -> ScenarioImpact:
        """将 DB 行转换为 ScenarioImpact 对象。"""
        return ScenarioImpact(
            impact_id=row[0],
            scenario_id=row[1],
            dimension=row[2],
            direction=row[3],
            strength=float(row[4]) if row[4] else 0.5,
            reason=row[5],
            confidence=float(row[6]) if row[6] else 0.5,
            created_at=float(row[7]) if row[7] else time.time()
        )

    def _row_to_path(self, row) -> ScenarioPath:
        """将 DB 行转换为 ScenarioPath 对象。"""
        return ScenarioPath(
            path_id=row[0],
            scenario_id=row[1],
            source_node=row[2],
            target_node=row[3],
            impact_score=float(row[4]) if row[4] else 0.5,
            time_horizon=int(row[5]) if row[5] else None,
            created_at=float(row[6]) if row[6] else time.time()
        )

    def _emit_event(self, event_type: str, payload: Dict[str, Any]):
        """发布 EventBus 事件。"""
        try:
            publish_system(event_type, payload, source="gfe_scenario")
        except Exception as e:
            print(f"[ScenarioEngine] EventBus 发布失败: {e}")


# ============================================================
# Seed Data
# ============================================================

def seed_scenarios():
    """初始化种子情景。"""
    engine = ScenarioEngine()

    # 情景1：高通胀情景
    s1 = engine.create_scenario(
        question="未来12个月通胀走势如何？",
        name="High Inflation Scenario",
        description="假设能源价格持续上涨，供应链压力持续",
        assumptions={
            "oil_price_change": 0.3,
            "supply_chain_pressure": "high",
            "wage_growth": 0.08
        },
        probability=0.4,
        confidence=0.7
    )

    if s1:
        engine.add_impact(s1.scenario_id, DIMENSION_ECONOMY, DIRECTION_NEGATIVE, 0.8, "通胀侵蚀购买力")
        engine.add_impact(s1.scenario_id, DIMENSION_FINANCE, DIRECTION_NEGATIVE, 0.7, "利率上升压力")
        engine.add_impact(s1.scenario_id, DIMENSION_SOCIAL, DIRECTION_NEGATIVE, 0.6, "民生压力增大")

    # 情景2：技术突破情景
    s2 = engine.create_scenario(
        question="AI技术突破对经济的影响？",
        name="AI Breakthrough Scenario",
        description="假设生成式AI取得重大突破，生产力大幅提升",
        assumptions={
            "ai_productivity_gain": 0.25,
            "automation_rate": 0.4,
            "adoption_speed": "fast"
        },
        probability=0.3,
        confidence=0.6
    )

    if s2:
        engine.add_impact(s2.scenario_id, DIMENSION_TECHNOLOGY, DIRECTION_POSITIVE, 0.9, "技术飞跃")
        engine.add_impact(s2.scenario_id, DIMENSION_ECONOMY, DIRECTION_POSITIVE, 0.7, "生产率提升")
        engine.add_impact(s2.scenario_id, DIMENSION_SOCIAL, DIRECTION_NEGATIVE, 0.5, "就业结构变化")

    # 情景3：地缘冲突情景
    s3 = engine.create_scenario(
        question="地缘冲突对能源安全的影响？",
        name="Geopolitical Conflict Scenario",
        description="假设主要能源产区发生冲突，供应链中断",
        assumptions={
            "conflict_severity": "high",
            "supply_disruption": 0.5,
            "response_speed": "slow"
        },
        probability=0.2,
        confidence=0.65
    )

    if s3:
        engine.add_impact(s3.scenario_id, DIMENSION_ENERGY, DIRECTION_NEGATIVE, 0.9, "供应中断")
        engine.add_impact(s3.scenario_id, DIMENSION_ECONOMY, DIRECTION_NEGATIVE, 0.7, "成本上升")
        engine.add_impact(s3.scenario_id, DIMENSION_DIPLOMACY, DIRECTION_NEGATIVE, 0.8, "关系恶化")

    print(f"[ScenarioEngine] Seeded 3 scenarios")
    return True


# ============================================================
# Singleton
# ============================================================

_instance: Optional[ScenarioEngine] = None
_instance_lock = threading.Lock()


def get_scenario_engine() -> ScenarioEngine:
    """获取单例 ScenarioEngine。"""
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = ScenarioEngine()
        return _instance


def reset_scenario_engine():
    """重置单例（用于测试）。"""
    global _instance
    with _instance_lock:
        _instance = None
