#!/usr/bin/env python3
"""Response Builder — 响应构建器。

职责：
- 构建标准化的 API 响应
- 输出符合 Interaction Protocol 的响应

约束：
- 不修改现有 API
- 只读操作
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any


@dataclass
class ResponseMessage:
    """响应消息。"""
    message_type: str  # "info", "success", "warning", "error"
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InteractionResponse:
    """交互响应。"""
    ok: bool
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=datetime.now().timestamp)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "message": self.message,
            "data": self.data,
            "errors": self.errors,
            "warnings": self.warnings,
            "meta": self.meta,
            "timestamp": self.timestamp
        }


class ResponseBuilder:
    """响应构建器。"""

    @staticmethod
    def success(message: str, data: Optional[Dict[str, Any]] = None) -> InteractionResponse:
        """构建成功响应。"""
        return InteractionResponse(
            ok=True,
            message=message,
            data=data or {}
        )

    @staticmethod
    def error(message: str, errors: Optional[List[str]] = None) -> InteractionResponse:
        """构建错误响应。"""
        return InteractionResponse(
            ok=False,
            message=message,
            errors=errors or [message]
        )

    @staticmethod
    def warning(message: str, data: Optional[Dict[str, Any]] = None) -> InteractionResponse:
        """构建警告响应。"""
        return InteractionResponse(
            ok=True,
            message=message,
            data=data or {},
            warnings=[message]
        )

    @staticmethod
    def parse_result(command: Dict[str, Any], intent: Dict[str, Any]) -> InteractionResponse:
        """构建解析结果响应。"""
        return InteractionResponse(
            ok=True,
            message="解析成功",
            data={
                "command": command,
                "intent": intent
            }
        )


# 便捷函数
def build_response(**kwargs) -> InteractionResponse:
    """便捷响应构建。"""
    ok = kwargs.pop("ok", True)
    message = kwargs.pop("message", "")
    data = kwargs.pop("data", {})
    errors = kwargs.pop("errors", [])
    warnings = kwargs.pop("warnings", [])
    
    return InteractionResponse(
        ok=ok,
        message=message,
        data=data,
        errors=errors,
        warnings=warnings
    )