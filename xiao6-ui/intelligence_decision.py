#!/usr/bin/env python3
"""S148 — Intelligence Decision Support Layer 决策辅助层。

职责：
- 读取已有 Intelligence 模块数据
- 生成决策辅助信息
- 提供风险分析
- 提供收益分析

约束：
- 不修改 AgentRuntime
- 不修改 Planner
- 不修改 Tool Execution
- 不修改 Memory Schema
- 不新建数据库
- 不引入新 AI 模型
- 不自动执行动作
- 不替用户做最终选择
"""

from __future__ import annotations

import time
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

# 内存存储键
DECISION_KEY_PREFIX = "dec_"
OPTION_KEY_PREFIX = "opt_"
RISK_KEY_PREFIX = "risk_"
BENEFIT_KEY_PREFIX = "benefit_"


@dataclass
class Option:
    """选项。"""
    option_id: str
    name: str
    advantages: List[str]
    risks: List[str]
    impact: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "option_id": self.option_id,
            "name": self.name,
            "advantages": self.advantages,
            "risks": self.risks,
            "impact": self.impact,
        }


@dataclass
class Risk:
    """风险。"""
    risk_id: str
    risk: str
    level: str  # high, medium, low
    reason: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_id": self.risk_id,
            "risk": self.risk,
            "level": self.level,
            "reason": self.reason,
        }


@dataclass
class Benefit:
    """收益。"""
    benefit_id: str
    benefit: str
    impact: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "benefit_id": self.benefit_id,
            "benefit": self.benefit,
            "impact": self.impact,
        }


@dataclass
class DecisionSnapshot:
    """决策快照。"""
    topic: str
    summary: str
    options: List[Dict[str, Any]]
    recommended_analysis: str
    confidence: float
    timestamp: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic": self.topic,
            "summary": self.summary,
            "options": self.options,
            "recommended_analysis": self.recommended_analysis,
            "confidence": round(self.confidence, 2),
            "timestamp": self.timestamp,
        }


@dataclass
class DecisionResult:
    """决策结果。"""
    decision_id: str
    topic: str
    options: List[Option]
    factors: List[str]
    risks: List[Risk]
    benefits: List[Benefit]
    confidence: float
    source: str
    timestamp: float
    snapshot: DecisionSnapshot
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "topic": self.topic,
            "options": [o.to_dict() for o in self.options],
            "factors": self.factors,
            "risks": [r.to_dict() for r in self.risks],
            "benefits": [b.to_dict() for b in self.benefits],
            "confidence": round(self.confidence, 2),
            "source": self.source,
            "timestamp": self.timestamp,
            "snapshot": self.snapshot.to_dict(),
        }


class DecisionSupportEngine:
    """决策辅助引擎。"""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._decisions: Dict[str, DecisionResult] = {}
        self._next_id = 0
    
    def _next_id_str(self, prefix: str) -> str:
        self._next_id += 1
        return f"{prefix}{int(time.time())}_{self._next_id}"
    
    def analyze_decision(
        self,
        topic: str,
        options: List[Dict[str, Any]],
        factors: List[str],
        source: str = "decision_support",
    ) -> DecisionResult:
        """分析一个决策主题。
        
        参数：
            topic: 决策主题
            options: 选项列表，每项包含 name/advantages/risks/impact
            factors: 影响因素列表
            source: 数据来源
        """
        with self._lock:
            decision_id = self._next_id_str(DECISION_KEY_PREFIX)
            now = time.time()
            
            # 构建选项
            parsed_options = []
            for opt in options:
                opt_id = self._next_id_str(OPTION_KEY_PREFIX)
                parsed_options.append(Option(
                    option_id=opt_id,
                    name=opt.get("name", ""),
                    advantages=opt.get("advantages", []),
                    risks=opt.get("risks", []),
                    impact=opt.get("impact", ""),
                ))
            
            # 构建风险和收益
            all_risks = []
            all_benefits = []
            risk_id_counter = 0
            benefit_id_counter = 0
            
            for opt in parsed_options:
                for risk_text in opt.risks:
                    risk_id_counter += 1
                    all_risks.append(Risk(
                        risk_id=f"{RISK_KEY_PREFIX}{risk_id_counter}",
                        risk=risk_text,
                        level=self._assess_risk_level(risk_text),
                        reason=f"来自选项: {opt.name}",
                    ))
                
                for adv_text in opt.advantages:
                    benefit_id_counter += 1
                    all_benefits.append(Benefit(
                        benefit_id=f"{BENEFIT_KEY_PREFIX}{benefit_id_counter}",
                        benefit=adv_text,
                        impact=f"提升 {opt.name} 的可行性",
                    ))
            
            # 生成快照
            snapshot = DecisionSnapshot(
                topic=topic,
                summary=f"针对 '{topic}' 的分析，共 {len(parsed_options)} 个选项",
                options=[o.to_dict() for o in parsed_options],
                recommended_analysis=self._generate_analysis(
                    topic, parsed_options, factors
                ),
                confidence=round(0.7 + len(factors) * 0.05, 2),
                timestamp=now,
            )
            
            result = DecisionResult(
                decision_id=decision_id,
                topic=topic,
                options=parsed_options,
                factors=factors,
                risks=all_risks,
                benefits=all_benefits,
                confidence=snapshot.confidence,
                source=source,
                timestamp=now,
                snapshot=snapshot,
            )
            
            self._decisions[decision_id] = result
            return result
    
    def _assess_risk_level(self, risk_text: str) -> str:
        """简单风险评估。"""
        if not risk_text:
            return "low"
        risk_lower = risk_text.lower()
        high_keywords = ["严重", "高风险", "失败", "损失", "危险"]
        medium_keywords = ["中等", "一般", "注意", "潜在"]
        
        for kw in high_keywords:
            if kw in risk_lower:
                return "high"
        for kw in medium_keywords:
            if kw in risk_lower:
                return "medium"
        return "low"
    
    def _generate_analysis(
        self, topic: str, options: List[Option], factors: List[str]
    ) -> str:
        """生成分析建议。"""
        if not options:
            return "暂无选项可分析。"
        
        # 简单启发式分析
        total_risks = sum(len(o.risks) for o in options)
        total_advantages = sum(len(o.advantages) for o in options)
        
        parts = [f"主题: {topic}", ""]
        
        # 选项对比
        parts.append("选项对比:")
        for i, opt in enumerate(options, 1):
            parts.append(f"  {i}. {opt.name}")
            parts.append(f"     优势: {len(opt.advantages)} 项")
            parts.append(f"     风险: {len(opt.risks)} 项")
        
        # 综合建议
        if total_advantages > total_risks:
            parts.append("")
            parts.append("分析建议: 整体正面，可考虑推进。")
        elif total_risks > total_advantages:
            parts.append("")
            parts.append("分析建议: 风险较高，建议谨慎评估。")
        else:
            parts.append("")
            parts.append("分析建议: 利弊相当，需进一步调研。")
        
        if factors:
            parts.append("")
            parts.append("影响因素:")
            for f in factors[:5]:
                parts.append(f"  - {f}")
        
        return "\n".join(parts)
    
    def get_decision(self, decision_id: str) -> Optional[DecisionResult]:
        """获取单个决策。"""
        return self._decisions.get(decision_id)
    
    def get_all_decisions(self) -> List[Dict[str, Any]]:
        """获取所有决策。"""
        return [d.to_dict() for d in self._decisions.values()]
    
    def get_count(self) -> int:
        """获取决策数量。"""
        return len(self._decisions)
    
    def get_status(self) -> Dict[str, Any]:
        """获取引擎状态。"""
        return {
            "ok": True,
            "engine": "decision",
            "version": "1.0.0",
            "decisions_count": self.get_count(),
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }


# 单例
_engine: Optional[DecisionSupportEngine] = None
_engine_lock = threading.Lock()


def get_decision_engine() -> DecisionSupportEngine:
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = DecisionSupportEngine()
        return _engine