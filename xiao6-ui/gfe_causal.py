#!/usr/bin/env python3
"""PHASE 143 — GFE Causal Graph Foundation

Global Foresight Engine (GFE) 因果图谱基础实现。
职责：
- 因果节点和边的存储与管理
- 图遍历与路径发现
- 影响路径计算
- 事件总线集成

架构边界：
- 不使用机器学习模型
- 不修改现有执行系统
- 仅做因果关系建模
- 保持数据追溯性（provenance）
"""

from __future__ import annotations

import json
import time
import uuid
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, asdict, field
from typing import Optional, List, Dict, Any, Set, Tuple

from db import db_conn
from eventbus import publish_system


# ============================================================
# Constants
# ============================================================

# EventBus Topics
TOPIC_CAUSAL_NODE_ADDED = "gfe_causal_node_added"
TOPIC_CAUSAL_EDGE_ADDED = "gfe_causal_edge_added"
TOPIC_CAUSAL_PATH_GENERATED = "gfe_causal_path_generated"

# Node categories
CATEGORY_ECONOMY = "economy"
CATEGORY_FINANCE = "finance"
CATEGORY_ENERGY = "energy"
CATEGORY_TECHNOLOGY = "technology"
CATEGORY_INDUSTRIES = "industries"
CATEGORY_TRADE = "trade"
CATEGORY_SOCIAL = "social"
CATEGORY_DIPLOMACY = "diplomacy"
CATEGORY_MILITARY = "military"

ALL_CATEGORIES = [
    CATEGORY_ECONOMY, CATEGORY_FINANCE, CATEGORY_ENERGY,
    CATEGORY_TECHNOLOGY, CATEGORY_INDUSTRIES, CATEGORY_TRADE,
    CATEGORY_SOCIAL, CATEGORY_DIPLOMACY, CATEGORY_MILITARY
]

# Edge relationship types
RELATIONSHIP_CAUSE = "cause"
RELATIONSHIP_CORRELATE = "correlate"
RELATIONSHIP_LEAD_TO = "lead_to"
RELATIONSHIP_DEPEND_ON = "depend_on"
RELATIONSHIP_MODERATE = "moderate"

ALL_RELATIONSHIPS = [
    RELATIONSHIP_CAUSE, RELATIONSHIP_CORRELATE,
    RELATIONSHIP_LEAD_TO, RELATIONSHIP_DEPEND_ON,
    RELATIONSHIP_MODERATE
]


# ============================================================
# Data Models
# ============================================================

@dataclass
class CausalNode:
    """因果节点模型。"""
    node_id: str
    name: str
    category: Optional[str]
    description: Optional[str]
    entity_type: Optional[str]
    provenance: Optional[str]
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_frontend(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "entity_type": self.entity_type,
            "provenance": self.provenance,
            "created_at": self.created_at
        }


@dataclass
class CausalEdge:
    """因果边模型。"""
    edge_id: str
    source_node: str
    target_node: str
    relationship_type: Optional[str]
    strength: float
    confidence: float
    time_delay: Optional[int]
    evidence_refs: List[str]
    provenance: Optional[str]
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_frontend(self) -> Dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "source_node": self.source_node,
            "target_node": self.target_node,
            "relationship_type": self.relationship_type,
            "strength": self.strength,
            "confidence": self.confidence,
            "time_delay": self.time_delay,
            "evidence_refs": self.evidence_refs,
            "provenance": self.provenance,
            "created_at": self.created_at
        }


@dataclass
class CausalPath:
    """因果路径模型。"""
    path_id: str
    start_node: str
    end_node: str
    nodes: List[str]
    edges: List[str]
    total_strength: float
    explanation: Optional[str]
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_frontend(self) -> Dict[str, Any]:
        return {
            "path_id": self.path_id,
            "start_node": self.start_node,
            "end_node": self.end_node,
            "nodes": self.nodes,
            "edges": self.edges,
            "total_strength": round(self.total_strength, 3),
            "explanation": self.explanation,
            "created_at": self.created_at
        }


# ============================================================
# Causal Graph Engine
# ============================================================

class CausalGraphEngine:
    """因果图谱引擎。

    核心功能：
    - 添加因果节点
    - 添加因果边
    - 图遍历（BFS/DFS）
    - 路径发现
    - 影响路径计算
    """

    def __init__(self, db_conn_func=None):
        self._conn = db_conn_func or db_conn
        self._lock = threading.RLock()
        # 内存图缓存（提高查询性能）
        self._adjacency: Dict[str, List[str]] = defaultdict(list)
        self._reverse_adjacency: Dict[str, List[str]] = defaultdict(list)
        self._nodes: Dict[str, CausalNode] = {}
        self._edges: Dict[str, CausalEdge] = {}
        self._refresh_cache()

    def _refresh_cache(self):
        """刷新内存图缓存。"""
        try:
            conn = self._conn()
            # 加载所有节点
            for row in conn.execute("SELECT * FROM gfe_causal_nodes").fetchall():
                node = self._row_to_node(row)
                self._nodes[node.node_id] = node
            # 加载所有边并构建邻接表
            self._adjacency.clear()
            self._reverse_adjacency.clear()
            for row in conn.execute("SELECT * FROM gfe_causal_edges").fetchall():
                edge = self._row_to_edge(row)
                self._edges[edge.edge_id] = edge
                self._adjacency[edge.source_node].append(edge.target_node)
                self._reverse_adjacency[edge.target_node].append(edge.source_node)
        except Exception as e:
            print(f"[CausalGraph] 刷新缓存失败: {e}")

    def add_node(
        self,
        name: str,
        category: Optional[str] = None,
        description: Optional[str] = None,
        entity_type: Optional[str] = None,
        provenance: Optional[str] = None
    ) -> Optional[CausalNode]:
        """添加因果节点。"""
        try:
            with self._lock:
                conn = self._conn()
                node_id = f"node_{int(time.time())}_{uuid.uuid4().hex[:8]}"
                now = time.time()

                conn.execute(
                    """INSERT INTO gfe_causal_nodes
                       (node_id, name, category, description, entity_type, provenance, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (node_id, name, category, description, entity_type, provenance, now)
                )
                conn.commit()

                node = CausalNode(
                    node_id=node_id,
                    name=name,
                    category=category,
                    description=description,
                    entity_type=entity_type,
                    provenance=provenance,
                    created_at=now
                )
                self._nodes[node_id] = node

                # 发布 EventBus 事件
                self._emit_event(TOPIC_CAUSAL_NODE_ADDED, {
                    "node_id": node_id,
                    "name": name,
                    "category": category,
                    "timestamp": now
                })

                return node

        except Exception as e:
            print(f"[CausalGraph] 添加节点失败: {e}")
            return None

    def add_edge(
        self,
        source_node: str,
        target_node: str,
        relationship_type: Optional[str] = None,
        strength: float = 0.5,
        confidence: float = 0.5,
        time_delay: Optional[int] = None,
        evidence_refs: Optional[List[str]] = None,
        provenance: Optional[str] = None
    ) -> Optional[CausalEdge]:
        """添加因果边。"""
        try:
            with self._lock:
                conn = self._conn()
                edge_id = f"edge_{int(time.time())}_{uuid.uuid4().hex[:8]}"
                now = time.time()

                conn.execute(
                    """INSERT INTO gfe_causal_edges
                       (edge_id, source_node, target_node, relationship_type, strength,
                        confidence, time_delay, evidence_refs, provenance, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        edge_id, source_node, target_node, relationship_type,
                        strength, confidence, time_delay,
                        json.dumps(evidence_refs or []),
                        provenance, now
                    )
                )
                conn.commit()

                edge = CausalEdge(
                    edge_id=edge_id,
                    source_node=source_node,
                    target_node=target_node,
                    relationship_type=relationship_type,
                    strength=strength,
                    confidence=confidence,
                    time_delay=time_delay,
                    evidence_refs=evidence_refs or [],
                    provenance=provenance,
                    created_at=now
                )
                self._edges[edge_id] = edge

                # 更新邻接表
                self._adjacency[source_node].append(target_node)
                self._reverse_adjacency[target_node].append(source_node)

                # 发布 EventBus 事件
                self._emit_event(TOPIC_CAUSAL_EDGE_ADDED, {
                    "edge_id": edge_id,
                    "source_node": source_node,
                    "target_node": target_node,
                    "strength": strength,
                    "timestamp": now
                })

                return edge

        except Exception as e:
            print(f"[CausalGraph] 添加边失败: {e}")
            return None

    def get_nodes(
        self,
        category: Optional[str] = None,
        limit: int = 100
    ) -> List[CausalNode]:
        """查询因果节点。"""
        try:
            conn = self._conn()
            query = "SELECT * FROM gfe_causal_nodes WHERE 1=1"
            params = []

            if category:
                query += " AND category = ?"
                params.append(category)

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            return [self._row_to_node(row) for row in rows if row]

        except Exception as e:
            print(f"[CausalGraph] 查询节点失败: {e}")
            return []

    def get_edges(
        self,
        source_node: Optional[str] = None,
        target_node: Optional[str] = None,
        limit: int = 100
    ) -> List[CausalEdge]:
        """查询因果边。"""
        try:
            conn = self._conn()
            query = "SELECT * FROM gfe_causal_edges WHERE 1=1"
            params = []

            if source_node:
                query += " AND source_node = ?"
                params.append(source_node)
            if target_node:
                query += " AND target_node = ?"
                params.append(target_node)

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            return [self._row_to_edge(row) for row in rows if row]

        except Exception as e:
            print(f"[CausalGraph] 查询边失败: {e}")
            return []

    def find_path(
        self,
        start: str,
        end: str,
        max_depth: int = 10
    ) -> Optional[CausalPath]:
        """使用 BFS 查找从 start 到 end 的路径。"""
        try:
            if start not in self._nodes and start not in self._adjacency:
                # 尝试在数据库中查找
                conn = self._conn()
                row = conn.execute(
                    "SELECT * FROM gfe_causal_nodes WHERE name = ? OR node_id = ?",
                    (start, start)
                ).fetchone()
                if row:
                    self._nodes[start] = self._row_to_node(row)
                else:
                    return None

            if end not in self._nodes and end not in self._adjacency:
                conn = self._conn()
                row = conn.execute(
                    "SELECT * FROM gfe_causal_nodes WHERE name = ? OR node_id = ?",
                    (end, end)
                ).fetchone()
                if row:
                    self._nodes[end] = self._row_to_node(row)
                else:
                    return None

            # BFS 搜索
            queue = deque([(start, [start], [])])
            visited = {start}

            while queue:
                current, path, edge_path = queue.popleft()

                if len(path) > max_depth:
                    continue

                if current == end:
                    path_id = f"path_{int(time.time())}_{uuid.uuid4().hex[:6]}"
                    path_obj = CausalPath(
                        path_id=path_id,
                        start_node=start,
                        end_node=end,
                        nodes=path,
                        edges=edge_path,
                        total_strength=self._calculate_path_strength(path, edge_path),
                        explanation=f"Path from {start} to {end} via {len(path)-1} nodes"
                    )

                    # 发布 EventBus 事件
                    self._emit_event(TOPIC_CAUSAL_PATH_GENERATED, {
                        "path_id": path_id,
                        "start_node": start,
                        "end_node": end,
                        "length": len(path),
                        "strength": path_obj.total_strength,
                        "timestamp": time.time()
                    })

                    return path_obj

                for neighbor in self._adjacency.get(current, []):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        # 查找对应的边
                        edge_id = self._find_edge_id(current, neighbor)
                        queue.append((neighbor, path + [neighbor], edge_path + [edge_id]))

            return None

        except Exception as e:
            print(f"[CausalGraph] 路径查找失败: {e}")
            return None

    def calculate_impact_path(self, node_id: str) -> List[Dict[str, Any]]:
        """计算节点的影响路径（所有可达节点）。"""
        try:
            impacts = []
            visited = set()
            queue = deque([(node_id, 0, [node_id])])

            while queue:
                current, depth, path = queue.popleft()

                if current in visited:
                    continue
                visited.add(current)

                if depth > 0:
                    # 找到一条影响路径
                    edge_ids = []
                    for i in range(len(path) - 1):
                        eid = self._find_edge_id(path[i], path[i + 1])
                        if eid:
                            edge_ids.append(eid)

                    impacts.append({
                        "target_node": current,
                        "depth": depth,
                        "path": path,
                        "edge_count": len(edge_ids)
                    })

                if depth < 10:  # 限制最大深度
                    for neighbor in self._adjacency.get(current, []):
                        if neighbor not in visited:
                            queue.append((neighbor, depth + 1, path + [neighbor]))

            return impacts

        except Exception as e:
            print(f"[CausalGraph] 影响路径计算失败: {e}")
            return []

    def get_node(self, node_id: str) -> Optional[CausalNode]:
        """获取单个节点。"""
        if node_id in self._nodes:
            return self._nodes[node_id]

        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM gfe_causal_nodes WHERE node_id = ?",
            (node_id,)
        ).fetchone()

        if row:
            node = self._row_to_node(row)
            self._nodes[node_id] = node
            return node

        return None

    def get_node_by_name(self, name: str) -> Optional[CausalNode]:
        """通过名称获取节点。"""
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM gfe_causal_nodes WHERE name = ?",
            (name,)
        ).fetchone()

        if row:
            node = self._row_to_node(row)
            self._nodes[node.node_id] = node
            return node

        return None

    # ---- 内部方法 ----

    def _row_to_node(self, row) -> CausalNode:
        """将 DB 行转换为 CausalNode 对象。"""
        return CausalNode(
            node_id=row[0],
            name=row[1],
            category=row[2],
            description=row[3],
            entity_type=row[4],
            provenance=row[5],
            created_at=float(row[6]) if row[6] else time.time()
        )

    def _row_to_edge(self, row) -> CausalEdge:
        """将 DB 行转换为 CausalEdge 对象。"""
        try:
            evidence_refs = json.loads(row[7] or "[]")
        except (json.JSONDecodeError, TypeError):
            evidence_refs = []

        return CausalEdge(
            edge_id=row[0],
            source_node=row[1],
            target_node=row[2],
            relationship_type=row[3],
            strength=float(row[4]) if row[4] else 0.5,
            confidence=float(row[5]) if row[5] else 0.5,
            time_delay=int(row[6]) if row[6] else None,
            evidence_refs=evidence_refs,
            provenance=row[8],
            created_at=float(row[9]) if row[9] else time.time()
        )

    def _find_edge_id(self, source: str, target: str) -> Optional[str]:
        """查找两个节点之间的边 ID。"""
        for edge in self._edges.values():
            if edge.source_node == source and edge.target_node == target:
                return edge.edge_id
        return None

    def _calculate_path_strength(self, nodes: List[str], edges: List[str]) -> float:
        """计算路径总强度。"""
        if not edges:
            return 0.0

        total_strength = 0.0
        edge_count = 0

        for i in range(len(nodes) - 1):
            for edge in self._edges.values():
                if edge.source_node == nodes[i] and edge.target_node == nodes[i + 1]:
                    total_strength += edge.strength
                    edge_count += 1
                    break

        return total_strength / edge_count if edge_count > 0 else 0.0

    def _emit_event(self, event_type: str, payload: Dict[str, Any]):
        """发布 EventBus 事件。"""
        try:
            publish_system(event_type, payload, source="gfe_causal")
        except Exception as e:
            print(f"[CausalGraph] EventBus 发布失败: {e}")


# ============================================================
# Seed Data
# ============================================================

def seed_causal_graph():
    """初始化种子因果图谱。"""
    engine = CausalGraphEngine()

    # === 能源因果链 ===
    # oil_price -> energy_cost -> inflation -> interest_rate -> growth
    engine.add_node("oil_price", CATEGORY_ENERGY, "国际原油价格", "indicator", "IEA, OPEC reports")
    engine.add_node("energy_cost", CATEGORY_ENERGY, "能源成本指数", "indicator", "EIA statistics")
    engine.add_node("inflation", CATEGORY_ECONOMY, "通货膨胀率", "indicator", "BLS, IMF WEO")
    engine.add_node("interest_rate", CATEGORY_FINANCE, "基准利率", "indicator", "Central Bank records")
    engine.add_node("growth", CATEGORY_ECONOMY, "经济增长率", "indicator", "World Bank, IMF")

    engine.add_edge("oil_price", "energy_cost", RELATIONSHIP_CAUSE, 0.85, 0.9, 30, provenance="Energy economics literature")
    engine.add_edge("energy_cost", "inflation", RELATIONSHIP_CAUSE, 0.7, 0.85, 60, provenance="Macroeconomic studies")
    engine.add_edge("inflation", "interest_rate", RELATIONSHIP_CAUSE, 0.75, 0.9, 90, provenance="Monetary theory")
    engine.add_edge("interest_rate", "growth", RELATIONSHIP_CAUSE, 0.6, 0.8, 180, provenance="Central bank models")

    # === 科技因果链 ===
    # chip_supply -> technology_output -> industrial_capacity -> economic_growth
    engine.add_node("chip_supply", CATEGORY_TECHNOLOGY, "芯片供应", "indicator", "Semiconductor Industry Association")
    engine.add_node("technology_output", CATEGORY_TECHNOLOGY, "技术产出", "indicator", "Patent office data")
    engine.add_node("industrial_capacity", CATEGORY_INDUSTRIES, "工业产能", "indicator", "Manufacturing surveys")
    engine.add_node("economic_growth", CATEGORY_ECONOMY, "经济增长", "indicator", "GDP statistics")

    engine.add_edge("chip_supply", "technology_output", RELATIONSHIP_CAUSE, 0.8, 0.85, 90, provenance="Technology economics")
    engine.add_edge("technology_output", "industrial_capacity", RELATIONSHIP_CAUSE, 0.7, 0.8, 180, provenance="Industrial economics")
    engine.add_edge("industrial_capacity", "economic_growth", RELATIONSHIP_CAUSE, 0.75, 0.85, 365, provenance="Growth theory")

    # === 金融因果链 ===
    # interest_rate -> liquidity -> asset_price -> investment
    engine.add_node("liquidity", CATEGORY_FINANCE, "市场流动性", "indicator", "Central bank data")
    engine.add_node("asset_price", CATEGORY_FINANCE, "资产价格", "indicator", "Market indices")
    engine.add_node("investment", CATEGORY_FINANCE, "投资水平", "indicator", "CAPEX statistics")

    engine.add_edge("interest_rate", "liquidity", RELATIONSHIP_CAUSE, 0.8, 0.9, 30, provenance="Monetary economics")
    engine.add_edge("liquidity", "asset_price", RELATIONSHIP_CAUSE, 0.75, 0.85, 60, provenance="Asset pricing theory")
    engine.add_edge("asset_price", "investment", RELATIONSHIP_CAUSE, 0.65, 0.8, 180, provenance="Tobin's Q theory")

    print(f"[CausalGraph] Seeded 12 nodes and 10 edges")
    return True


# ============================================================
# Singleton
# ============================================================

_instance: Optional[CausalGraphEngine] = None
_instance_lock = threading.Lock()


def get_causal_graph_engine() -> CausalGraphEngine:
    """获取单例 CausalGraphEngine。"""
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = CausalGraphEngine()
        return _instance


def reset_causal_graph_engine():
    """重置单例（用于测试）。"""
    global _instance
    with _instance_lock:
        _instance = None
