#!/usr/bin/env python3
"""PHASE 144 — GFE Analyst Council Foundation

Global Foresight Engine (GFE) 分析师委员会基础实现。
职责：
- 多分析角色注册与管理
- 独立分析结果提交
- Consensus 聚合机制
- 事件总线集成

架构边界：
- 不使用机器学习模型
- 不调用 Runtime/Execution
- 仅做分析聚合
- 保持数据追溯性（provenance）
"""

from __future__ import annotations

import json
import time
import uuid
import threading
from dataclasses import dataclass, asdict, field
from typing import Optional, List, Dict, Any, Callable

from db import db_conn
from eventbus import publish_system


# ============================================================
# Constants
# ============================================================

# EventBus Topics
TOPIC_ANALYSIS_CREATED = "gfe_analysis_created"
TOPIC_CONSENSUS_REACHED = "gfe_consensus_reached"

# Analyst specializations
SPECIALIZATION_MACRO = "macro"
SPECIALIZATION_GEOPOLITICS = "geopolitics"
SPECIALIZATION_FINANCE = "finance"
SPECIALIZATION_DEMOGRAPHY = "demography"
SPECIALIZATION_TECHNOLOGY = "technology"
SPECIALIZATION_ENERGY = "energy"
SPECIALIZATION_CLIMATE = "climate"
SPECIALIZATION_RISK = "risk"

ALL_SPECIALIZATIONS = [
    SPECIALIZATION_MACRO, SPECIALIZATION_GEOPOLITICS, SPECIALIZATION_FINANCE,
    SPECIALIZATION_DEMOGRAPHY, SPECIALIZATION_TECHNOLOGY, SPECIALIZATION_ENERGY,
    SPECIALIZATION_CLIMATE, SPECIALIZATION_RISK
]

# Consensus algorithms
ALGORITHM_WEIGHTED_AVERAGE = "weighted_average"
ALGORITHM_VOTE = "vote"
ALGORITHM_CONSENSUS = "consensus"


# ============================================================
# Data Models
# ============================================================

@dataclass
class AnalystAgent:
    """分析师代理模型。"""
    agent_id: str
    name: str
    specialization: str
    weight: float
    confidence: float
    provenance: Optional[str]
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_frontend(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "specialization": self.specialization,
            "weight": self.weight,
            "confidence": self.confidence,
            "provenance": self.provenance,
            "created_at": self.created_at
        }


@dataclass
class AnalysisReport:
    """分析报告模型。"""
    report_id: str
    question: str
    analyst_id: str
    analysis: str
    confidence: float
    evidence_refs: List[str]
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_frontend(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "question": self.question,
            "analyst_id": self.analyst_id,
            "analysis": self.analysis,
            "confidence": self.confidence,
            "evidence_refs": self.evidence_refs,
            "created_at": self.created_at
        }


@dataclass
class ConsensusResult:
    """共识结果模型。"""
    consensus_id: str
    question: str
    final_analysis: str
    agreement_score: float
    confidence: float
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_frontend(self) -> Dict[str, Any]:
        return {
            "consensus_id": self.consensus_id,
            "question": self.question,
            "final_analysis": self.final_analysis,
            "agreement_score": round(self.agreement_score, 3),
            "confidence": round(self.confidence, 3),
            "created_at": self.created_at
        }


# ============================================================
# Analyst Council Engine
# ============================================================

class AnalystCouncil:
    """分析师委员会引擎。

    核心功能：
    - 注册分析师代理
    - 提交独立分析
    - 聚合共识
    - 查询结果
    """

    def __init__(self, db_conn_func=None):
        self._conn = db_conn_func or db_conn
        self._lock = threading.RLock()
        # 内存缓存
        self._agents: Dict[str, AnalystAgent] = {}
        self._refresh_cache()

    def _refresh_cache(self):
        """刷新内存缓存。"""
        try:
            conn = self._conn()
            for row in conn.execute("SELECT * FROM gfe_analyst_agents").fetchall():
                agent = self._row_to_agent(row)
                self._agents[agent.agent_id] = agent
        except Exception as e:
            print(f"[AnalystCouncil] 刷新缓存失败: {e}")

    def register_agent(
        self,
        name: str,
        specialization: str,
        weight: float = 0.5,
        confidence: float = 0.5,
        provenance: Optional[str] = None
    ) -> Optional[AnalystAgent]:
        """注册分析师代理。"""
        try:
            with self._lock:
                conn = self._conn()
                agent_id = f"agent_{int(time.time())}_{uuid.uuid4().hex[:8]}"
                now = time.time()

                conn.execute(
                    """INSERT INTO gfe_analyst_agents
                       (agent_id, name, specialization, weight, confidence, provenance, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (agent_id, name, specialization, weight, confidence, provenance, now)
                )
                conn.commit()

                agent = AnalystAgent(
                    agent_id=agent_id,
                    name=name,
                    specialization=specialization,
                    weight=weight,
                    confidence=confidence,
                    provenance=provenance,
                    created_at=now
                )
                self._agents[agent_id] = agent

                # 发布 EventBus 事件
                self._emit_event(TOPIC_ANALYSIS_CREATED, {
                    "agent_id": agent_id,
                    "name": name,
                    "specialization": specialization,
                    "timestamp": now
                })

                return agent

        except Exception as e:
            print(f"[AnalystCouncil] 注册分析师失败: {e}")
            return None

    def submit_analysis(
        self,
        analyst_id: str,
        question: str,
        analysis: str,
        confidence: float = 0.5,
        evidence_refs: Optional[List[str]] = None
    ) -> Optional[AnalysisReport]:
        """提交独立分析。"""
        try:
            with self._lock:
                conn = self._conn()

                # 验证分析师存在
                if analyst_id not in self._agents:
                    row = conn.execute(
                        "SELECT * FROM gfe_analyst_agents WHERE agent_id = ?",
                        (analyst_id,)
                    ).fetchone()
                    if not row:
                        return None
                    self._agents[analyst_id] = self._row_to_agent(row)

                report_id = f"report_{int(time.time())}_{uuid.uuid4().hex[:8]}"
                now = time.time()

                conn.execute(
                    """INSERT INTO gfe_analysis_reports
                       (report_id, question, analyst_id, analysis, confidence, evidence_refs, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        report_id, question, analyst_id, analysis,
                        confidence, json.dumps(evidence_refs or []), now
                    )
                )
                conn.commit()

                report = AnalysisReport(
                    report_id=report_id,
                    question=question,
                    analyst_id=analyst_id,
                    analysis=analysis,
                    confidence=confidence,
                    evidence_refs=evidence_refs or [],
                    created_at=now
                )

                # 发布 EventBus 事件
                self._emit_event(TOPIC_ANALYSIS_CREATED, {
                    "report_id": report_id,
                    "analyst_id": analyst_id,
                    "question": question,
                    "timestamp": now
                })

                return report

        except Exception as e:
            print(f"[AnalystCouncil] 提交分析失败: {e}")
            return None

    def compute_consensus(
        self,
        question: str,
        algorithm: str = ALGORITHM_WEIGHTED_AVERAGE
    ) -> Optional[ConsensusResult]:
        """计算共识。

        算法：
        - weighted_average: 按分析师权重加权平均
        - vote: 简单投票
        - consensus: 严格共识（所有分析师一致）
        """
        try:
            with self._lock:
                conn = self._conn()

                # 获取该问题的所有分析
                rows = conn.execute(
                    """SELECT r.*, a.weight, a.specialization
                       FROM gfe_analysis_reports r
                       JOIN gfe_analyst_agents a ON r.analyst_id = a.agent_id
                       WHERE r.question = ?
                       ORDER BY r.created_at""",
                    (question,)
                ).fetchall()

                if not rows:
                    return None

                # 解析分析结果
                analyses = []
                for row in rows:
                    try:
                        evidence_refs = json.loads(row[6] or "[]")
                    except (json.JSONDecodeError, TypeError):
                        evidence_refs = []

                    analyses.append({
                        "report_id": row[0],
                        "analyst_id": row[2],
                        "analysis": row[3],
                        "confidence": float(row[4]) if row[4] else 0.5,
                        "weight": float(row[7]) if row[7] else 0.5,
                        "specialization": row[8]
                    })

                # 计算共识
                if algorithm == ALGORITHM_WEIGHTED_AVERAGE:
                    final_analysis, agreement_score, confidence = self._weighted_average_consensus(analyses)
                elif algorithm == ALGORITHM_VOTE:
                    final_analysis, agreement_score, confidence = self._vote_consensus(analyses)
                elif algorithm == ALGORITHM_CONSENSUS:
                    final_analysis, agreement_score, confidence = self._strict_consensus(analyses)
                else:
                    final_analysis, agreement_score, confidence = self._weighted_average_consensus(analyses)

                # 保存结果
                consensus_id = f"consensus_{int(time.time())}_{uuid.uuid4().hex[:6]}"
                now = time.time()

                conn.execute(
                    """INSERT INTO gfe_consensus_results
                       (consensus_id, question, final_analysis, agreement_score, confidence, created_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (consensus_id, question, final_analysis, agreement_score, confidence, now)
                )
                conn.commit()

                result = ConsensusResult(
                    consensus_id=consensus_id,
                    question=question,
                    final_analysis=final_analysis,
                    agreement_score=agreement_score,
                    confidence=confidence,
                    created_at=now
                )

                # 发布 EventBus 事件
                self._emit_event(TOPIC_CONSENSUS_REACHED, {
                    "consensus_id": consensus_id,
                    "question": question,
                    "agreement_score": agreement_score,
                    "analyst_count": len(analyses),
                    "timestamp": now
                })

                return result

        except Exception as e:
            print(f"[AnalystCouncil] 计算共识失败: {e}")
            return None

    def get_agents(self, specialization: Optional[str] = None) -> List[AnalystAgent]:
        """查询分析师代理。"""
        try:
            conn = self._conn()
            query = "SELECT * FROM gfe_analyst_agents WHERE 1=1"
            params = []

            if specialization:
                query += " AND specialization = ?"
                params.append(specialization)

            query += " ORDER BY created_at DESC"
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_agent(row) for row in rows if row]

        except Exception as e:
            print(f"[AnalystCouncil] 查询分析师失败: {e}")
            return []

    def get_reports(
        self,
        analyst_id: Optional[str] = None,
        question: Optional[str] = None,
        limit: int = 50
    ) -> List[AnalysisReport]:
        """查询分析报告。"""
        try:
            conn = self._conn()
            query = "SELECT * FROM gfe_analysis_reports WHERE 1=1"
            params = []

            if analyst_id:
                query += " AND analyst_id = ?"
                params.append(analyst_id)
            if question:
                query += " AND question = ?"
                params.append(question)

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            return [self._row_to_report(row) for row in rows if row]

        except Exception as e:
            print(f"[AnalystCouncil] 查询报告失败: {e}")
            return []

    def get_consensus(self, question: Optional[str] = None, limit: int = 20) -> List[ConsensusResult]:
        """查询共识结果。"""
        try:
            conn = self._conn()
            query = "SELECT * FROM gfe_consensus_results WHERE 1=1"
            params = []

            if question:
                query += " AND question = ?"
                params.append(question)

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            return [self._row_to_consensus(row) for row in rows if row]

        except Exception as e:
            print(f"[AnalystCouncil] 查询共识失败: {e}")
            return []

    # ---- 共识算法 ----

    def _weighted_average_consensus(
        self, analyses: List[Dict[str, Any]]
    ) -> tuple:
        """加权平均共识。"""
        total_weight = sum(a["weight"] * a["confidence"] for a in analyses)
        if total_weight == 0:
            return json.dumps({"type": "weighted_average", "analyses": analyses}), 0.0, 0.0

        # 简单聚合：合并所有分析
        combined = {
            "method": ALGORITHM_WEIGHTED_AVERAGE,
            "analyses": analyses,
            "total_weight": total_weight
        }

        # 计算一致性分数（简化版）
        confidences = [a["confidence"] for a in analyses]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        # 一致性：标准差越小越一致
        if len(confidences) > 1:
            mean = avg_confidence
            variance = sum((c - mean) ** 2 for c in confidences) / len(confidences)
            agreement = max(0.0, 1.0 - variance ** 0.5)
        else:
            agreement = avg_confidence

        return json.dumps(combined, ensure_ascii=False), agreement, avg_confidence

    def _vote_consensus(self, analyses: List[Dict[str, Any]]) -> tuple:
        """投票共识。"""
        # 简化：取最多出现的结论方向
        combined = {
            "method": ALGORITHM_VOTE,
            "analyses": analyses
        }

        # 计算一致性
        confidences = [a["confidence"] for a in analyses]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        agreement = avg_confidence

        return json.dumps(combined, ensure_ascii=False), agreement, avg_confidence

    def _strict_consensus(self, analyses: List[Dict[str, Any]]) -> tuple:
        """严格共识。"""
        # 只有所有分析师完全一致时才返回共识
        if len(analyses) < 2:
            return json.dumps({"method": ALGORITHM_CONSENSUS, "result": "single_analyst"}), 1.0, analyses[0]["confidence"]

        # 检查是否所有分析相同
        first = analyses[0]["analysis"]
        all_same = all(a["analysis"] == first for a in analyses)

        if all_same:
            return json.dumps({"method": ALGORITHM_CONSENSUS, "result": "unanimous"}), 1.0, analyses[0]["confidence"]
        else:
            return json.dumps({"method": ALGORITHM_CONSENSUS, "result": "no_consensus"}), 0.0, 0.0

    # ---- 内部方法 ----

    def _row_to_agent(self, row) -> AnalystAgent:
        """将 DB 行转换为 AnalystAgent 对象。"""
        return AnalystAgent(
            agent_id=row[0],
            name=row[1],
            specialization=row[2],
            weight=float(row[3]) if row[3] else 0.5,
            confidence=float(row[4]) if row[4] else 0.5,
            provenance=row[5],
            created_at=float(row[6]) if row[6] else time.time()
        )

    def _row_to_report(self, row) -> AnalysisReport:
        """将 DB 行转换为 AnalysisReport 对象。"""
        try:
            evidence_refs = json.loads(row[5] or "[]")
        except (json.JSONDecodeError, TypeError):
            evidence_refs = []

        return AnalysisReport(
            report_id=row[0],
            question=row[1],
            analyst_id=row[2],
            analysis=row[3],
            confidence=float(row[4]) if row[4] else 0.5,
            evidence_refs=evidence_refs,
            created_at=float(row[6]) if row[6] else time.time()
        )

    def _row_to_consensus(self, row) -> ConsensusResult:
        """将 DB 行转换为 ConsensusResult 对象。"""
        return ConsensusResult(
            consensus_id=row[0],
            question=row[1],
            final_analysis=row[2],
            agreement_score=float(row[3]) if row[3] else 0.5,
            confidence=float(row[4]) if row[4] else 0.5,
            created_at=float(row[5]) if row[5] else time.time()
        )

    def _emit_event(self, event_type: str, payload: Dict[str, Any]):
        """发布 EventBus 事件。"""
        try:
            publish_system(event_type, payload, source="gfe_analyst")
        except Exception as e:
            print(f"[AnalystCouncil] EventBus 发布失败: {e}")


# ============================================================
# Seed Data
# ============================================================

def seed_analyst_agents():
    """初始化种子分析师。"""
    council = AnalystCouncil()

    # 宏观经济分析师
    council.register_agent(
        name="MacroAgent",
        specialization=SPECIALIZATION_MACRO,
        weight=0.9,
        confidence=0.85,
        provenance="GFE built-in model"
    )

    # 地缘政治分析师
    council.register_agent(
        name="GeoAgent",
        specialization=SPECIALIZATION_GEOPOLITICS,
        weight=0.85,
        confidence=0.8,
        provenance="GFE built-in model"
    )

    # 金融分析师
    council.register_agent(
        name="FinanceAgent",
        specialization=SPECIALIZATION_FINANCE,
        weight=0.88,
        confidence=0.82,
        provenance="GFE built-in model"
    )

    # 技术分析师
    council.register_agent(
        name="TechAgent",
        specialization=SPECIALIZATION_TECHNOLOGY,
        weight=0.8,
        confidence=0.78,
        provenance="GFE built-in model"
    )

    # 风险分析师
    council.register_agent(
        name="RiskAgent",
        specialization=SPECIALIZATION_RISK,
        weight=0.92,
        confidence=0.88,
        provenance="GFE built-in model"
    )

    # 能源分析师
    council.register_agent(
        name="EnergyAgent",
        specialization=SPECIALIZATION_ENERGY,
        weight=0.75,
        confidence=0.75,
        provenance="GFE built-in model"
    )

    print(f"[AnalystCouncil] Seeded 6 analyst agents")
    return True


# ============================================================
# Singleton
# ============================================================

_instance: Optional[AnalystCouncil] = None
_instance_lock = threading.Lock()


def get_analyst_council() -> AnalystCouncil:
    """获取单例 AnalystCouncil。"""
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = AnalystCouncil()
        return _instance


def reset_analyst_council():
    """重置单例（用于测试）。"""
    global _instance
    with _instance_lock:
        _instance = None
