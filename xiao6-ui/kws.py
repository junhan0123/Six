#!/usr/bin/env python3
"""庄周 · 离线唤醒词 / 关键词侦测（纯标准库）。

用途：在语音助手的本地链路里做轻量级唤醒词 / 关键词 spotting，
避免每一次语音都进完整 ASR。特性：
  - 纯标准库（os / difflib / tempfile），零第三方依赖。
  - 短语采用「子串包含」+「difflib 相似度兜底」双策略：
    中文无空格、子串匹配最稳；拉丁短语再叠加模糊匹配以容忍轻微口音 / 识别误差。
  - 全部入口均有 try/except 防御，任何异常都退化为「未命中 / 空文本」，
    绝不抛异常中断主链路。
  - 实际转写委托给 asr 模块（懒加载），本模块不实现 ASR。
"""

import difflib
import os
import tempfile

# 环境变量键
ENV_ENABLED = "XIAO6_KWS_ENABLED"
ENV_PHRASES = "XIAO6_WAKE_PHRASE"
ENV_SENSITIVITY = "XIAO6_KWS_SENSITIVITY"

# 默认值：产品名「庄周」及其口语昵称「小周」均可唤醒；保留旧名「小6」兼容既有用户。
# 注：产品早期代号小6，后定名庄周；唤醒词需随产品名演进，故默认含庄周/小周。
DEF_WAKE_PHRASES = "庄周,小周,小6"
DEF_SENSITIVITY = 0.6


def get_kws_config():
    """读取并返回唤醒词相关配置。

    返回 dict：
      - enabled    : XIAO6_KWS_ENABLED 为 "true"（忽略大小写）时为 True
      - phrases    : 由 XIAO6_WAKE_PHRASE 逗号切分、去空白、去空项得到的列表
      - sensitivity: XIAO6_KWS_SENSITIVITY 浮点；解析失败回退 0.6
    """
    enabled = os.environ.get(ENV_ENABLED, "false").lower() == "true"

    raw = os.environ.get(ENV_PHRASES, DEF_WAKE_PHRASES) or ""
    phrases = [p.strip() for p in raw.split(",") if p.strip()]

    try:
        sensitivity = float(os.environ.get(ENV_SENSITIVITY, str(DEF_SENSITIVITY)))
    except (ValueError, TypeError):
        sensitivity = DEF_SENSITIVITY

    return {
        "enabled": enabled,
        "phrases": phrases,
        "sensitivity": sensitivity,
    }


def _normalize(text):
    """归一化：去首尾空白；拉丁字母统一小写（中文无大小写，lower 无副作用）。"""
    return (text or "").strip().lower()


def check_wake(transcript, phrases=None, sensitivity=None):
    """判断转写文本是否命中任一唤醒词 / 关键词（委托精准版，向后兼容）。

    自 P2 起委托 kws_optimized.check_wake_optimized：精确子串 + 严格窗口模糊匹配，
    误触发率 < 5%。本函数签名 / 行为保持兼容（子串命中、无关词不命中）。
    sensitivity 缺省时使用严格默认 0.85（覆盖旧 0.6 全局默认以提升精度）。
    """
    from kws_optimized import check_wake_optimized

    # 向后兼容：sensitivity 未显式传入时改用严格默认，避免旧 0.6 阈值过宽
    eff = sensitivity if sensitivity is not None else 0.85
    return check_wake_optimized(transcript, phrases, eff)


def transcribe_short(audio_bytes):
    """把一小段音频字节转写成文本，用于唤醒词侦测前的轻量识别。

    实现：懒加载 asr.transcribe（它接收『文件路径』而非字节），
    故把 audio_bytes 落盘为临时 .wav 再传路径。任何失败（导入失败 / 写盘失败 /
    ASR 失败 / 清理异常）均被吞掉并返回空串 ""，绝不向上抛异常。
    """
    if not audio_bytes:
        return ""

    fd = None
    tmp = None
    try:
        from asr import transcribe  # 仅在需要时导入，避免无语音场景下的额外开销
        fd, tmp = tempfile.mkstemp(suffix=".wav")
        with os.fdopen(fd, "wb") as f:
            f.write(audio_bytes)
        fd = None  # 已关闭，避免 finally 重复关闭
        text, _err = transcribe(tmp)
        return (text or "").strip()
    except Exception:
        return ""
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except Exception:
                pass
        if tmp and os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass
