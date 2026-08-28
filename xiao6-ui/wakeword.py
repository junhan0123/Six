"""庄周 · 常驻语音唤醒词（P8 常驻语音 · 脚手架，默认关闭）。

设计目标：让庄周在桌面端「常驻聆听」，离线检测到唤醒词（如 hey_jarvis / 贾维斯）
后触发录音→转写→对话闭环，无需手动按键。

依赖（仅在真正开始监听时惰性导入，缺失不致命）：
- openwakeword：离线唤醒词检测        pip install openwakeword
- sounddevice：麦克风音频采集          pip install sounddevice

功能开关：config.FEATURE_ALWAYS_ON_VOICE（默认 False）。
⚠️ 新增该 flag 时须同步 config.ENV_KEYS 白名单 + reload() 的全局/赋值行
（见项目记忆「致命坑」），否则运行时恒 False。本脚手架在 flag 缺失时默认关闭，
确保零依赖也能安全导入、返回状态、不中断主链路。

注意：本模块为脚手架，监听线程的实际音频后端（sounddevice）需在「带麦克风的用户机器」
上安装依赖并验证；此处结构完整、导入安全，但首跑需真机校准阈值。
"""

import os
import threading
import time

import config
from config import HERE
from wakeword_vosk import (
    is_wake as _vosk_is_wake,
    VOSK_MODEL_DIR as _VOSK_MODEL_DIR,
    load_phrases as _vosk_load_phrases,
)

ENABLED = os.environ.get("ZHUANGZHOU_KWS_ENABLED", "true").lower() in ("1", "true", "yes")
DEFAULT_MODEL = "hey_jarvis"  # openwakeword 内置模型别名
THRESHOLD = 0.5  # 检测分数阈值（真机校准）
SAMPLE_RATE = 16000
CHUNK = 1280  # openwakeword 推荐帧长（16k * 0.08s）

_state = {
    "enabled": bool(ENABLED),
    "listening": False,
    "model": DEFAULT_MODEL if ENABLED else None,
    "note": "",
}
_lock = threading.Lock()
_thread = None
_stop = threading.Event()


def _ensure_deps():
    """惰性导入唤醒词 + 音频依赖。返回 (ok, msg)。"""
    try:
        import openwakeword  # noqa: F401
        import sounddevice  # noqa: F401
        return True, "deps ok"
    except Exception as e:  # noqa: BLE001
        return False, f"缺少依赖：{e}（pip install openwakeword sounddevice）"


def is_enabled():
    return bool(_state["enabled"])


def get_status():
    with _lock:
        return dict(_state)


def _listen_loop(detect_callback):
    """监听线程：从麦克风取帧，喂给 openwakeword，超阈值触发回调。"""
    import sounddevice as sd
    from openwakeword.model import Model

    model = Model(wakeword_models=[DEFAULT_MODEL])
    detected = {"cb": detect_callback}

    def _on_detect():
        try:
            if detected["cb"]:
                detected["cb"](detected.get("model", "unknown"))
        except Exception:
            pass

    def _callback(indata, frames, _t, _status):
        if _stop.is_set():
            return
        # indata: float32 一维；转 int16 字节喂给模型
        import numpy as np

        pcm = (np.clip(indata, -1, 1) * 32767).astype("<i2").tobytes()
        preds = model.predict(pcm)
        score = preds.get(DEFAULT_MODEL, 0.0)
        if score >= THRESHOLD:
            _on_detect()

    with sd.RawInputStream(
        samplerate=SAMPLE_RATE,
        blocksize=CHUNK,
        dtype="int16",
        channels=1,
        callback=_callback,
    ):
        while not _stop.is_set():
            time.sleep(0.1)


def _listen_loop_vosk(detect_callback):
    """Vosk 中文短语监听线程：麦克风流 → Vosk 转写 → is_wake 匹配（P8-2）。"""
    import json

    import numpy as np
    import sounddevice as sd
    from vosk import KaldiRecognizer, Model

    if not os.path.isdir(_VOSK_MODEL_DIR):
        print(f"[KWS] Vosk 模型缺失（{_VOSK_MODEL_DIR}），唤醒词已降级关闭；不影响其他功能。")
        return
    model = Model(_VOSK_MODEL_DIR)
    rec = KaldiRecognizer(model, SAMPLE_RATE)
    phrases = _vosk_load_phrases()

    def _on_detect(phrase):
        try:
            if detect_callback:
                detect_callback(phrase)
        except Exception:
            pass

    def _callback(indata, frames, _t, _status):
        if _stop.is_set():
            return
        pcm = (np.clip(indata, -1, 1) * 32767).astype("<i2").tobytes()
        hit = None
        if rec.AcceptWaveform(pcm):
            hit = _vosk_is_wake(json.loads(rec.Result()).get("text", ""), phrases)
        else:
            partial = json.loads(rec.PartialResult()).get("partial", "")
            if partial:
                hit = _vosk_is_wake(partial, phrases)
        if hit:
            _on_detect(hit)

    try:
        with sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            blocksize=CHUNK,
            dtype="int16",
            channels=1,
            callback=_callback,
        ):
            while not _stop.is_set():
                time.sleep(0.1)
    except Exception as _e:
        # 无可用麦克风设备/权限（如服务器环境）→ 优雅降级，不污染日志
        print(f"[KWS] 麦克风不可用，唤醒词暂停监听（{_e}）；接入麦克风后重启生效。")


def _spawn_vosk(detect_callback):
    """持锁上下文中启动 Vosk 监听线程（不重复加锁）。"""
    global _thread
    _stop.clear()
    _thread = threading.Thread(
        target=_listen_loop_vosk, args=(detect_callback,), daemon=True
    )
    _thread.start()
    _state["listening"] = True
    _state["model"] = "vosk-cn"
    _state["note"] = "Vosk 中文短语监听中"


def start_vosk(detect_callback=None):
    """启动 Vosk 中文短语监听（独立入口）。依赖缺失抛异常，由调用方降级。"""
    global _thread
    with _lock:
        if _state["listening"]:
            return dict(_state)
        _spawn_vosk(detect_callback)
        return dict(_state)


def start(detect_callback=None):
    """启动常驻监听。优先 Vosk 中文短语 KWS（开启且可用），否则 openwakeword fallback。"""
    global _thread
    with _lock:
        # 读取配置（而非硬编码 flag）
        _state["enabled"] = os.environ.get("ZHUANGZHOU_KWS_ENABLED", "true").lower() in ("1", "true", "yes")
        if not _state["enabled"]:
            _state["note"] = "ZHUANGZHOU_KWS_ENABLED 未开启"
            return dict(_state)
        if _state["listening"]:
            return dict(_state)
        # P8-2：优先 Vosk 中文短语 KWS
        vosk_on = os.environ.get("ZHUANGZHOU_VOSK_KWS_ENABLED", "true").lower() in ("1", "true", "yes")
        if vosk_on:
            try:
                _spawn_vosk(detect_callback)
                return dict(_state)
            except Exception as e:  # Vosk 缺失/模型不存在 → 回退 openwakeword
                _state["note"] = f"Vosk KWS 不可用，回退 openwakeword：{e}"
        ok, msg = _ensure_deps()
        if not ok:
            _state["note"] = msg
            return dict(_state)
        _stop.clear()
        _thread = threading.Thread(
            target=_listen_loop, args=(detect_callback,), daemon=True
        )
        _thread.start()
        _state["listening"] = True
        _state["model"] = DEFAULT_MODEL
        _state["note"] = "常驻监听中"
        return dict(_state)


def stop():
    """停止常驻监听。"""
    global _thread
    _stop.set()
    with _lock:
        _state["listening"] = False
        _state["note"] = "已停止"
    _thread = None
    return dict(_state)
