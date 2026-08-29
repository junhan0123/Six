"""庄周 · 中文短语唤醒词检测（P8-2，Vosk KWS）。

复用 asr.py 已落地的 Vosk 中文模型目录（models/vosk/vosk-model-small-cn-0.22），
仅做关键词检测：把实时麦克风流喂给 Vosk KaldiRecognizer，取 partial/final 文本，
用 is_wake() 做 ±1 字符容错的短语匹配（覆盖 ASR 同音/漏字口误）。
零网络、零密钥。Vosk / sounddevice / numpy 缺失时由 wakeword.py 捕获降级。

注意：VOSK_MODEL_DIR 与 asr.VOSK_MODEL_DIR 保持一致（刻意不复用 asr，避免 KWS 启动时
加载 faster-whisper 等重依赖）。
"""
import itertools
import json
import os

VOSK_MODEL_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "models", "vosk", "vosk-model-small-cn-0.22",
)

# 同音/近形容错候选（覆盖常见 ASR 口误，避免盲目 edit-distance 爆炸）
_HOMOPHONES = {
    "小": ["小", "晓", "筱"],
    "周": ["周", "洲", "舟", "州"],
    "庄": ["庄", "装", "状"],
}

DEFAULT_PHRASES = ["庄周", "小周"]


def load_phrases():
    """读取 XIAO6_WAKE_PHRASE（逗号分隔），空则回退默认。"""
    raw = os.environ.get("XIAO6_WAKE_PHRASE", "庄周,小周") or "庄周,小周"
    out = [p.strip() for p in raw.split(",") if p.strip()]
    return out or list(DEFAULT_PHRASES)


def _norm(text):
    """仅保留 CJK 字符（去空格/标点/数字）。"""
    return "".join(ch for ch in text if "一" <= ch <= "鿿")


def _phrase_variants(phrase):
    """返回 {variant: phrase} 映射，保留每个容错候选的来源短语。

    ±1 容错：同音替换（笛卡尔积，短语短故可控）+ 漏一字（≥3 字才做，避免 2 字删成单字误触发）。
    """
    pn = _norm(phrase)
    if not pn:
        return {}
    m = {pn: phrase}
    opts = [_HOMOPHONES.get(ch, [ch]) for ch in pn]
    for combo in itertools.product(*opts):
        m["".join(combo)] = phrase
    if len(pn) >= 3:
        for i in range(len(pn)):
            m[pn[:i] + pn[i + 1:]] = phrase
    return m


def _variant_to_phrase(phrases):
    out = {}
    for ph in phrases:
        out.update(_phrase_variants(ph))
    return out


def is_wake(transcript, phrases=None):
    """判断转写文本是否命中任一唤醒短语（容错 ±1 字符）。

    transcript: Vosk 输出的中文文本（可含 partial）。
    返回命中的原始短语（如 "庄周"，真值可当 bool 用）或 None（未命中）。
    """
    if not transcript:
        return None
    text = _norm(transcript)
    if not text:
        return None
    phrases = phrases if phrases is not None else load_phrases()
    mapping = _variant_to_phrase(phrases)
    for v, ph in mapping.items():
        if v and v in text:
            return ph
    return None


if __name__ == "__main__":
    # 轻量单测（不依赖麦克风/模型）：验证 is_wake 容错逻辑
    import sys

    def _assert(cond, msg):
        if not cond:
            print(f"FAIL: {msg}")
            sys.exit(1)
        print(f"ok: {msg}")

    # test_vosk_wake_detection
    _assert(is_wake("小周现在几点了") == "小周", "小周 精确触发")
    _assert(is_wake("庄周帮我记一下") == "庄周", "庄周 精确触发")
    _assert(is_wake("今天天气怎么样") is None, "无关词不触发")
    # test_wake_phrase_recognition（同音/漏字容错）
    _assert(is_wake("小洲在吗") == "小周", "同音 小洲→小周")
    _assert(is_wake("晓周打开灯") == "小周", "同音 晓周→小周")
    _assert(is_wake("庄洲设置一个提醒") == "庄周", "同音 庄洲→庄周")
    print("ALL WAKE TESTS PASSED")
