"""Phase 8 MVP · OCR Provider（文字识别，不负责理解）

抽象 Provider + Mock（零真实 OCR 引擎依赖）。
输入：截图（整屏或 region）；输出：OcrSpan[]（text / bbox / confidence / language）。
低置信不伪造，标记 lowConfidence。
"""
from __future__ import annotations


class OcrSpan:
    """单个文字识别结果。"""
    __slots__ = ("span_id", "text", "bbox", "confidence", "language", "redacted")

    def __init__(self, span_id, text, bbox=None, confidence=1.0, language="zh", redacted=False):
        self.span_id = span_id
        self.text = text
        self.bbox = tuple(bbox) if bbox else None   # (x, y, w, h)
        self.confidence = float(confidence)
        self.language = language
        self.redacted = bool(redacted)              # 命中敏感模式 → 原文已被 •••• 替换

    def to_dict(self):
        return {
            "spanId": self.span_id,
            "text": self.text,
            "bbox": list(self.bbox) if self.bbox else None,
            "confidence": round(self.confidence, 3),
            "language": self.language,
            "lowConfidence": self.confidence < 0.5,
            "redacted": self.redacted,
        }


class OcrResult:
    """一次 OCR 识别的结果集合。"""
    __slots__ = ("spans", "region", "source")

    def __init__(self, spans=None, region=None, source="mock"):
        self.spans = spans if spans is not None else []
        self.region = tuple(region) if region else None
        self.source = source

    def to_dict(self):
        return {
            "spans": [s.to_dict() for s in self.spans],
            "region": list(self.region) if self.region else None,
            "source": self.source,
        }


class OcrProvider:
    """抽象基类：文字识别接口。"""
    name = "abstract"

    def recognize(self, frame, region=None):
        raise NotImplementedError


class MockOcrProvider(OcrProvider):
    """测试用 OCR：确定性合成文本，零真实 OCR 引擎依赖。支持整屏与区域。"""
    name = "mock"

    def __init__(self, spans=None):
        self._spans = spans or [
            OcrSpan("OCR-1", "文件", bbox=(12, 4, 40, 20), confidence=0.98),
            OcrSpan("OCR-2", "编辑", bbox=(60, 4, 40, 20), confidence=0.97),
            OcrSpan("OCR-3", "小6正在记录", bbox=(12, 44, 200, 24), confidence=0.95),
        ]

    def recognize(self, frame, region=None):
        spans = self._spans
        if region:
            rx, ry, rw, rh = region
            spans = [s for s in spans if s.bbox and not (
                s.bbox[0] > rx + rw or s.bbox[0] + s.bbox[2] < rx or
                s.bbox[1] > ry + rh or s.bbox[1] + s.bbox[3] < ry
            )]
        return OcrResult(spans=list(spans), region=region, source=self.name)
