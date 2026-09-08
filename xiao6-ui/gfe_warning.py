#!/usr/bin/env python3
"""PHASE 148 — GFE Early Warning Foundation

Global Foresight Engine (GFE) 预警引擎基础实现。
职责：
- 风险预警规则管理
- 综合风险评估（Events + World States + Causal + Forecasts）
- 预警生成与管理
- 预警历史追踪

架构边界：
- 只读访问其他 GFE 模块数据
- 不修改已有模块
- 不调用 Runtime/Execution
- 仅做风险评估和预警
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
TOPIC_WARNING_CREATED = "gfe_warning_created"
TOPIC_WARNING_UPDATED = "gfe_warning_updated"

# Severity levels
SEVERITY_LOW = 0.3
SEVERITY_MEDIUM = 0.5
SEVERITY_HIGH = 0.7
SEVERITY_CRITICAL = 0.9

# Alert status
STATUS_ACTIVE = "active"
STATUS_ACKNOWLEDGED = "acknowledged"
STATUS_RESOLVED = "resolved"


# ============================================================
# Data Models
# ============================================================

@dataclass
class WarningRule:
    """预警规则模型。"""
    rule_id: str
    name: str
    category: str
    conditions: str  # JSON
    severity: float
    confidence: float
    enabled: int
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_frontend(self) -> Dict[str, Any]:
        conditions = {}
        if self.conditions:
            try:
                conditions = json.loads(self.conditions)
            except json.JSONDecodeError:
                conditions = {}
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "category": self.category,
            "conditions": conditions,
            "severity": round(self.severity, 3),
            "confidence": round(self.confidence, 3),
            "enabled": bool(self.enabled),
            "created_at": self.created_at
        }


@dataclass
class WarningAlert:
    """预警记录模型。"""
    alert_id: str
    country_code: str
    title: str
    description: str
    severity: float
    probability: float
    confidence: float
    trigger_refs: str  # JSON
    status: str
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_frontend(self) -> Dict[str, Any]:
        triggers = []
        if self.trigger_refs:
            try:
                triggers = json.loads(self.trigger_refs)
            except json.JSONDecodeError:
                triggers = []
        return {
            "alert_id": self.alert_id,
            "country_code": self.country_code,
            "title": self.title,
            "description": self.description,
            "severity": round(self.severity, 3),
            "probability": round(self.probability, 3),
            "confidence": round(self.confidence, 3),
            "trigger_refs": triggers,
            "status": self.status,
            "created_at": self.created_at
        }


# ============================================================
# EarlyWarningEngine
# ============================================================

class EarlyWarningEngine:
    """预警引擎。

    核心功能：
    - 预警规则管理
    - 风险评估（综合 Events, World States, Causal Graph, Forecasts）
    - 预警生成
    - 预警状态管理
    """

    def __init__(self):
        self._lock = threading.Lock()

    def create_rule(
        self,
        name: str,
        category: str,
        conditions: Dict[str, Any],
        severity: float = 0.5,
        confidence: float = 0.5,
        enabled: int = 1
    ) -> Optional[WarningRule]:
        """创建预警规则。"""
        try:
            conn = db_conn()
            rule_id = "rule_" + uuid.uuid4().hex[:8]
            conditions_json = json.dumps(conditions, ensure_ascii=False)

            conn.execute(
                """INSERT INTO gfe_warning_rules
                   (rule_id, name, category, conditions, severity, confidence, enabled, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (rule_id, name, category, conditions_json, severity, confidence, enabled, time.time())
            )
            conn.commit()

            rule = WarningRule(
                rule_id=rule_id,
                name=name,
                category=category,
                conditions=conditions_json,
                severity=severity,
                confidence=confidence,
                enabled=enabled
            )

            publish_system(TOPIC_WARNING_CREATED, {
                "rule_id": rule_id,
                "name": name,
                "category": category
            })

            return rule
        except Exception as e:
            print(f"[EarlyWarning] 创建规则失败: {e}")
            return None

    def get_rules(self, category: Optional[str] = None, enabled_only: bool = True) -> List[WarningRule]:
        """查询预警规则。"""
        try:
            conn = db_conn()
            query = "SELECT * FROM gfe_warning_rules WHERE 1=1"
            params = []
            if category:
                query += " AND category = ?"
                params.append(category)
            if enabled_only:
                query += " AND enabled = 1"
            query += " ORDER BY severity DESC, created_at DESC"

            rows = conn.execute(query, params).fetchall()
            return [
                WarningRule(
                    rule_id=r[0], name=r[1], category=r[2], conditions=r[3],
                    severity=r[4], confidence=r[5], enabled=r[6], created_at=r[7]
                )
                for r in rows
            ]
        except Exception as e:
            print(f"[EarlyWarning] 查询规则失败: {e}")
            return []

    def evaluate_risk(self, country_code: str) -> Dict[str, Any]:
        """综合风险评估。

        数据来源（只读）：
        - gfe_events: 事件风险
        - gfe_world_states: 世界状态异常
        - gfe_causal_edges: 因果链传播
        - gfe_forecasts: 预测不确定性
        """
        try:
            conn = db_conn()
            risk_factors = {
                "event_risk": 0.0,
                "state_anomaly": 0.0,
                "causal_propagation": 0.0,
                "forecast_uncertainty": 0.0
            }

            # 1. 事件风险
            event_rows = conn.execute(
                """SELECT severity, confidence FROM gfe_events
                   WHERE country_code = ? AND severity > 0.6
                   ORDER BY created_at DESC LIMIT 5""",
                (country_code,)
            ).fetchall()
            if event_rows:
                avg_event_sev = sum(r[0] for r in event_rows) / len(event_rows)
                avg_event_conf = sum(r[1] for r in event_rows) / len(event_rows)
                risk_factors["event_risk"] = avg_event_sev * avg_event_conf

            # 2. 世界状态异常
            state_rows = conn.execute(
                "SELECT json_each.value FROM gfe_world_states, json_each(gfe_world_states.economy) WHERE country_code = ?",
                (country_code,)
            ).fetchall()
            if state_rows:
                anomalies = sum(1 for r in state_rows if isinstance(r[0], dict) and r[0].get("anomaly", 0) > 0.5)
                risk_factors["state_anomaly"] = min(anomalies / max(len(state_rows), 1), 1.0)

            # 3. 因果链传播
            causal_rows = conn.execute(
                """SELECT strength, confidence FROM gfe_causal_edges
                   WHERE source_node IN (
                       SELECT name FROM gfe_causal_nodes WHERE entity_type = ?
                   )
                   LIMIT 10""",
                (country_code,)
            ).fetchall()
            if causal_rows:
                avg_ca = sum(r[0] * r[1] for r in causal_rows) / len(causal_rows)
                risk_factors["causal_propagation"] = avg_ca

            # 4. 预测不确定性
            forecast_rows = conn.execute(
                """SELECT probability, confidence FROM gfe_forecasts
                   WHERE target LIKE ? AND status = 'active'
                   ORDER BY created_at DESC LIMIT 5""",
                (f"%{country_code}%",)
            ).fetchall()
            if forecast_rows:
                avg_fc_conf = sum(r[1] for r in forecast_rows) / len(forecast_rows)
                avg_fc_prob = sum(r[0] for r in forecast_rows) / len(forecast_rows)
                risk_factors["forecast_uncertainty"] = 1.0 - abs(avg_fc_prob - 0.5) * 2
                risk_factors["forecast_uncertainty"] *= avg_fc_conf

            # 综合风险评分
            weights = {"event_risk": 0.35, "state_anomaly": 0.25, "causal_propagation": 0.25, "forecast_uncertainty": 0.15}
            risk_score = sum(risk_factors[k] * weights[k] for k in weights)

            # 确定风险等级
            if risk_score >= 0.7:
                severity = SEVERITY_CRITICAL
            elif risk_score >= 0.5:
                severity = SEVERITY_HIGH
            elif risk_score >= 0.3:
                severity = SEVERITY_MEDIUM
            else:
                severity = SEVERITY_LOW

            return {
                "country_code": country_code,
                "risk_score": round(risk_score, 3),
                "severity": severity,
                "risk_factors": {k: round(v, 3) for k, v in risk_factors.items()},
                "evaluated_at": time.time()
            }
        except Exception as e:
            print(f"[EarlyWarning] 风险评估失败: {e}")
            return {"country_code": country_code, "error": str(e)}

    def generate_alert(
        self,
        country_code: str,
        title: str,
        description: str,
        severity: float,
        probability: float,
        confidence: float,
        trigger_refs: List[str]
    ) -> Optional[WarningAlert]:
        """生成预警。"""
        try:
            conn = db_conn()
            alert_id = "alert_" + uuid.uuid4().hex[:8]
            trigger_refs_json = json.dumps(trigger_refs, ensure_ascii=False)

            conn.execute(
                """INSERT INTO gfe_warning_alerts
                   (alert_id, country_code, title, description, severity, probability, confidence, trigger_refs, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (alert_id, country_code, title, description, severity, probability, confidence, trigger_refs_json, STATUS_ACTIVE, time.time())
            )
            conn.commit()

            alert = WarningAlert(
                alert_id=alert_id,
                country_code=country_code,
                title=title,
                description=description,
                severity=severity,
                probability=probability,
                confidence=confidence,
                trigger_refs=trigger_refs_json,
                status=STATUS_ACTIVE
            )

            publish_system(TOPIC_WARNING_CREATED, {
                "alert_id": alert_id,
                "country_code": country_code,
                "severity": severity
            })

            return alert
        except Exception as e:
            print(f"[EarlyWarning] 生成预警失败: {e}")
            return None

    def get_alerts(self, country_code: Optional[str] = None, status: Optional[str] = None) -> List[WarningAlert]:
        """查询预警。"""
        try:
            conn = db_conn()
            query = "SELECT * FROM gfe_warning_alerts"
            params = []
            if country_code:
                query += " WHERE country_code = ?"
                params.append(country_code)
            if status:
                query += " AND status = ?"
                params.append(status)
            query += " ORDER BY severity DESC, created_at DESC"

            rows = conn.execute(query, params).fetchall()
            return [
                WarningAlert(
                    alert_id=r[0], country_code=r[1], title=r[2], description=r[3],
                    severity=r[4], probability=r[5], confidence=r[6],
                    trigger_refs=r[7], status=r[8], created_at=r[9]
                )
                for r in rows
            ]
        except Exception as e:
            print(f"[EarlyWarning] 查询预警失败: {e}")
            return []

    def update_alert_status(self, alert_id: str, new_status: str, reason: str = "") -> bool:
        """更新预警状态。"""
        try:
            conn = db_conn()
            # 获取旧状态
            old_row = conn.execute("SELECT status FROM gfe_warning_alerts WHERE alert_id = ?", (alert_id,)).fetchone()
            if not old_row:
                return False

            old_status = old_row[0]
            conn.execute(
                "UPDATE gfe_warning_alerts SET status = ? WHERE alert_id = ?",
                (new_status, alert_id)
            )

            # 记录历史
            history_id = "hist_" + uuid.uuid4().hex[:8]
            conn.execute(
                """INSERT INTO gfe_warning_history
                   (history_id, alert_id, old_status, new_status, reason, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (history_id, alert_id, old_status, new_status, reason, time.time())
            )
            conn.commit()

            publish_system(TOPIC_WARNING_UPDATED, {
                "alert_id": alert_id,
                "old_status": old_status,
                "new_status": new_status
            })

            return True
        except Exception as e:
            print(f"[EarlyWarning] 更新预警状态失败: {e}")
            return False

    def seed_data(self):
        """种子数据。"""
        try:
            conn = db_conn()
            # 检查是否已有数据
            count = conn.execute("SELECT COUNT(*) FROM gfe_warning_rules").fetchone()[0]
            if count > 0:
                return

            # 创建预警规则
            rules = [
                ("高通胀预警", "economy", {"inflation_rate": "> 5%", "duration": "> 3 months"}, 0.8, 0.7),
                ("汇率波动预警", "finance", {"fx_volatility": "> 10%", "direction": "sharp"}, 0.7, 0.6),
                ("能源危机预警", "energy", {"supply_disruption": "> 20%", "price_spike": "> 30%"}, 0.9, 0.8),
                ("地缘政治风险", "geopolitics", {"tension_level": "> high", "duration": "> 1 month"}, 0.85, 0.75),
                ("技术封锁预警", "technology", {"export_control": True, "scope": "critical"}, 0.75, 0.7),
            ]

            for name, cat, cond, sev, conf in rules:
                self.create_rule(name, cat, cond, sev, conf)

            print("[EarlyWarning] Seeded warning rules")
        except Exception as e:
            print(f"[EarlyWarning] 种子数据失败: {e}")


# ============================================================
# Singleton
# ============================================================

_instance: Optional[EarlyWarningEngine] = None
_instance_lock = threading.Lock()


def get_early_warning_engine() -> EarlyWarningEngine:
    """获取预警引擎单例。"""
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = EarlyWarningEngine()
                _instance.seed_data()
    return _instance


# ============================================================
# 前端格式化函数
# ============================================================

def rule_to_frontend(rule: WarningRule) -> Dict[str, Any]:
    """规则转前端格式。"""
    return rule.to_frontend()


def alert_to_frontend(alert: WarningAlert) -> Dict[str, Any]:
    """预警转前端格式。"""
    return alert.to_frontend()
