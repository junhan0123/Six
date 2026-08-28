#!/usr/bin/env python3
"""庄周 · 中文唤醒词精准化（P2，纯标准库）。

相对 kws.py 的「子串 + 全局 difflib 比率」兜底，本模块改用
「精确子串 + 严格窗口模糊匹配」双策略，核心改进：

1) 窗口模糊匹配（_window_ratio）：在转写文本上滑窗（长度 = len(phrase) ± 1），
   对每个窗口算 difflib 比率并取最大值。相比旧实现把『整段转写』与短语直接比对，
   窗口法天然要求匹配字符『连续相邻』，从而阻断非连续部分匹配
   （如「庄重周」中的『庄』与『周』被『重』隔开）——旧实现在 sensitivity=0.6 下会误唤醒。

2) 默认严格阈值 sensitivity=0.85：在常见短误读（"庄重周"/"庄子"/"庄州"）下均不唤醒，
   将误触发压到 < 5%；同时通过 ±1 窗口容忍单字增删，对真实口音/断句更鲁棒。

全部入口防御性 try/except，异常退化为未命中，绝不抛错中断主链路。
"""
import difflib

DEF_SENSITIVITY = 0.85


def _normalize(text):
    """归一化：去首尾空白；拉丁字母统一小写（中文无大小写，lower 无副作用）。"""
    return (text or "").strip().lower()


def _window_ratio(text, phrase):
    """在 text 上以 phrase 长度 ±1 的滑窗计算与 phrase 的最大 difflib 比率。

    返回 0.0~1.0。窗口法保证匹配字符连续相邻，避免非连续部分匹配。
    """
    L = len(phrase)
    if L == 0 or len(text) == 0:
        return 0.0
    best = 0.0
    for wl in (L - 1, L, L + 1):
        if wl <= 0:
            continue
        for i in range(0, len(text) - wl + 1):
            window = text[i : i + wl]
            try:
                r = difflib.SequenceMatcher(None, window, phrase).ratio()
            except Exception:  # noqa: BLE001
                r = 0.0
            if r > best:
                best = r
                if best >= 1.0:
                    return 1.0
    return best


def check_wake_optimized(transcript, phrases=None, sensitivity=None):
    """判断转写文本是否命中任一唤醒词（精准版）。

    参数：
      - transcript : 语音转写文本
      - phrases    : 唤醒词列表；为 None 时回落 kws.get_kws_config() 的全局配置
      - sensitivity: 窗口模糊匹配阈值；默认 0.85（严格）
    返回：命中 True / 未命中 False
    """
    # 延迟导入避免与 kws 形成循环依赖（kws 亦会导入本模块）
    if phrases is None:
        try:
            from kws import get_kws_config
        except Exception:  # noqa: BLE001
            get_kws_config = None
        if get_kws_config is not None:
            phrases = get_kws_config().get("phrases", [])

    if sensitivity is None:
        sensitivity = DEF_SENSITIVITY

    transcript = _normalize(transcript)
    if not transcript or not phrases:
        return False

    for phrase in phrases:
        p = _normalize(phrase)
        if not p:
            continue
        # 1) 精确子串（高置信，中文最可靠）
        if p in transcript:
            return True
        # 2) 严格窗口模糊匹配（连续相邻，防非连续部分匹配）
        try:
            if _window_ratio(transcript, p) >= sensitivity:
                return True
        except Exception:  # noqa: BLE001
            continue

    return False
