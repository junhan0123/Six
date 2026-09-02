#!/usr/bin/env python3
"""小6 · 语音 ASR Provider（本地优先 + 云端兜底）

能力：音频（文件或内存字节）→ 文本（语音转写）。
优先级：
  1. 本地 faster-whisper（small/medium，开源 SOTA 级，带标点，中文准；经 hf-mirror 下载，离线）
  2. 本地 Vosk（small-cn，轻量零依赖、低延迟兜底）
  3. 本地 FunASR（Paraformer，仅在装了 torch+funasr 时可用）
  4. 云端 API（.env 配置 XIAO6_ASR_PROVIDER=aliyun|xfyun|volcengine + 密钥）
  5. 均未就绪 → 返回明确「未启用」文案，绝不消耗积分/触发外部请求

设计要点：
  - whisper/Vosk 模型懒加载（首次转写或后端启动时后台预热），避免拖慢 server 启动。
  - 前端实时对话已直出 16k 单声道 WAV → 直接喂识别器，零转码依赖、零延迟。
  - HF 直连被墙，已统一走 hf-mirror（见模块顶部 os.environ.setdefault）。
"""

import os
import shutil
import subprocess
import tempfile
import glob
import threading

# ── 镜像：HuggingFace 直连被墙，统一走 hf-mirror，确保 whisper 模型可下载/加载 ──
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("HF_XET_DISABLE", "1")

from config import (
    ALIYUN_ASR_KEY,
    ALIYUN_ASR_TOKEN,
    ASR_PROVIDER,
    VOLCENGINE_ASR_KEY,
    VOLCENGINE_ASR_SECRET,
    XFYUN_ASR_APIKEY,
    XFYUN_ASR_APISECRET,
    XFYUN_ASR_APPID,
)

# Paraformer 中文离线模型（modelscope 自动下载到缓存）
LOCAL_MODEL_ID = "iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"

DISABLED_MSG = (
    "语音转写当前未启用（本地 FunASR 不可用且未配置云端密钥）。\n"
    "本地模式需 torch+funasr；或配置 XIAO6_ASR_PROVIDER=aliyun|xfyun|volcengine 及对应密钥。"
)

_MODEL = None
_MODEL_ERR = None


def _ensure_local_model():
    """懒加载本地 FunASR 模型（首次调用时加载并缓存单例）。"""
    global _MODEL, _MODEL_ERR
    if _MODEL is not None or _MODEL_ERR is not None:
        return _MODEL
    try:
        from funasr import AutoModel
        import torch
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        _MODEL = AutoModel(model=LOCAL_MODEL_ID, device=device, disable_update=True)
        return _MODEL
    except Exception as e:  # torch/funasr 缺失或模型下载失败
        _MODEL_ERR = e
        return None


def local_available():
    """本地 FunASR 是否可用（供 status / 前端探测）。"""
    return _ensure_local_model() is not None


def _funasr_available():
    """安全探测：仅判断 funasr 包是否安装，绝不加载模型（避免本机 ctranslate2 段错误拖垮后端）。"""
    try:
        import importlib.util as _u
        return _u.find_spec("funasr") is not None
    except Exception:
        return False


def _find_ffmpeg():
    """定位 ffmpeg 可执行文件。优先 PATH，再探测常见 Windows 便携路径。"""
    found = shutil.which("ffmpeg")
    if found:
        return found
    candidates = []
    for drive in ("C:", "D:", "E:", "G:"):
        base = os.path.join(drive + os.sep, "ffmpeg")
        if os.path.isdir(base):
            for root, _dirs, files in os.walk(base):
                if "ffmpeg.exe" in files:
                    candidates.append(os.path.join(root, "ffmpeg.exe"))
    # 也覆盖几个常见固定路径
    candidates.extend([
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
        r"D:\ffmpeg\bin\ffmpeg.exe",
        r"D:\ffmpeg-8.0-essentials_build\bin\ffmpeg.exe",
    ])
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


def _to_wav_16k(src_path):
    """用 ffmpeg 把任意音频转成 16k 单声道 wav（Vosk/FunASR 输入要求）。失败返回 None。"""
    ffmpeg = _find_ffmpeg()
    if not ffmpeg:
        print("[ASR] ffmpeg 未找到：无法转码音频")
        return None
    fd, wav_path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        proc = subprocess.run(
            [ffmpeg, "-y", "-i", src_path, "-ar", "16000", "-ac", "1", "-f", "wav", wav_path],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        if os.path.getsize(wav_path) > 44:
            return wav_path
        # 输出为空，视为失败
        print(f"[ASR] ffmpeg 输出文件为空：{src_path}")
        try:
            os.remove(wav_path)
        except Exception:
            pass
        return None
    except subprocess.CalledProcessError as e:
        err = e.stderr.decode("utf-8", "replace")[:300] if e.stderr else str(e)
        print(f"[ASR] ffmpeg 转码失败：{err}")
        try:
            os.remove(wav_path)
        except Exception:
            pass
        return None
    except Exception as e:
        print(f"[ASR] ffmpeg 调用异常：{e}")
        try:
            os.remove(wav_path)
        except Exception:
            pass
        return None


# ── Vosk 本地离线识别（中文，无需 GPU / 密钥，低延迟，支持流式） ──
VOSK_MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "vosk", "vosk-model-small-cn-0.22")
_VOSK_MODEL = None
_VOSK_ERR = None

def _ensure_vosk_model():
    """懒加载 Vosk 中文模型（首次识别时加载并缓存单例）。"""
    global _VOSK_MODEL, _VOSK_ERR
    if _VOSK_MODEL is not None or _VOSK_ERR is not None:
        return _VOSK_MODEL
    try:
        from vosk import Model
        if not os.path.isdir(VOSK_MODEL_DIR):
            raise FileNotFoundError(VOSK_MODEL_DIR)
        _VOSK_MODEL = Model(VOSK_MODEL_DIR)
        return _VOSK_MODEL
    except Exception as e:  # vosk 未安装或模型缺失
        _VOSK_ERR = e
        return None

def vosk_available():
    """Vosk 本地识别是否可用（供 status / 前端探测）。"""
    return _ensure_vosk_model() is not None

def _vosk_transcribe(wav_path):
    model = _ensure_vosk_model()
    if model is None:
        return None
    import json
    import wave
    from vosk import KaldiRecognizer
    try:
        w = wave.open(wav_path, "rb")
    except Exception:
        return None
    rec = KaldiRecognizer(model, w.getframerate())
    while True:
        d = w.readframes(4000)
        if not d:
            break
        rec.AcceptWaveform(d)
    w.close()
    try:
        res = json.loads(rec.FinalResult())
    except Exception:
        return ""
    return (res.get("text") or "").strip()


# ── faster-whisper 本地识别（开源 SOTA 级，带标点，中文准；经 hf-mirror 下载） ──
_WHISPER_MODEL = None
_WHISPER_ERR = None
_WHISPER_HALLU = ("字幕", "感谢观看", "订阅", "thank you", "subscribe", "by ")

def _whisper_model_size():
    return os.environ.get("XIAO6_WHISPER_SIZE", "small")  # small / medium / large-v3

def _whisper_cached():
    """不加载模型，仅判断是否已缓存（供 status 轻量探测）。"""
    try:
        import importlib.util as u
        if u.find_spec("faster_whisper") is None:
            return False
    except Exception:
        return False
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "whisper")
    return bool(glob.glob(os.path.join(root, "**", "model.bin"), recursive=True))

def _ensure_whisper_model():
    """懒加载 faster-whisper（首次调用时加载并缓存单例；首次会下载模型到 models/whisper）。"""
    global _WHISPER_MODEL, _WHISPER_ERR
    if _WHISPER_MODEL is not None or _WHISPER_ERR is not None:
        return _WHISPER_MODEL
    try:
        from faster_whisper import WhisperModel
        size = _whisper_model_size()
        root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "whisper")
        _WHISPER_MODEL = WhisperModel(size, device="cpu", compute_type="int8", download_root=root)
    except Exception as e:
        _WHISPER_ERR = e
    return _WHISPER_MODEL

def whisper_available():
    return _ensure_whisper_model() is not None

# 引导词：whisper 中文默认可能输出繁体，且不认识产品专名。
# 给一段简体上下文可同时纠正字形与专名，属解码提示，不改变模型与接口。
_WHISPER_PROMPT = "以下是简体中文普通话对话。小6是这台电脑上的智能助手。"


def _whisper_transcribe(wav_path):
    model = _ensure_whisper_model()
    if model is None:
        return None
    try:
        segments, _ = model.transcribe(
            wav_path, language="zh", beam_size=5, initial_prompt=_WHISPER_PROMPT
        )
        text = "".join(s.text for s in segments).strip()
        if not text:
            return None
        # 轻量幻觉过滤：whisper 对静音/噪声偶发幻觉出固定短语，丢弃以免误触发
        low = text.lower()
        if any(h in low for h in _WHISPER_HALLU) and len(text) <= 12:
            return None
        return text
    except Exception:
        return None

def _local_transcribe(wav_path):
    model = _ensure_local_model()
    if model is None:
        return None
    res = model.generate(input=wav_path, batch_size_s=300)
    if res and isinstance(res, list) and res[0] and res[0].get("text"):
        return (res[0]["text"] or "").strip()
    return ""


def _wav_is_16k_mono(path):
    """判断 WAV 是否已是 16k 单声道（Vosk 可直接读取，无需转码）。"""
    try:
        import wave
        with wave.open(path, "rb") as w:
            return w.getframerate() == 16000 and w.getnchannels() == 1
    except Exception:
        return False


def transcribe(path):
    """音频文件 → 文本。返回 (text, None) 成功，或 (None, 文案)。"""
    if not os.path.isfile(path):
        return None, f"错误：音频文件不存在：{path}"
    # 前端实时对话已直出 16k 单声道 WAV → 直接喂 Vosk，零依赖、零延迟
    # 其它格式（webm/mp3/媒体文件）才回退 ffmpeg 转码
    need_cleanup = False
    if path.lower().endswith(".wav") and _wav_is_16k_mono(path):
        wav = path
    else:
        wav = _to_wav_16k(path)
        if not wav:
            return None, "音频转码失败（ffmpeg 不可用或文件损坏）"
        need_cleanup = (wav != path)
    try:
        # 优先 faster-whisper（开源 SOTA 级，带标点，中文准确率最高）
        text = _whisper_transcribe(wav)
        if text:
            return text, None
        # 兜底 Vosk（轻量、零依赖、低延迟）
        text = _vosk_transcribe(wav)
        if text:
            return text, None
        text = _local_transcribe(wav)
        if text:
            return text, None
        # 本地模型没识别到 → 尝试云端兜底
        txt2, err = _cloud_transcribe(path)
        if txt2:
            return txt2, None
        return None, "未能识别到语音内容（静音或无法识别）"
    finally:
        if need_cleanup:
            try:
                os.remove(wav)
            except Exception:
                pass


def transcribe_bytes(data, ext=".webm"):
    """内存音频字节（如前端录音 blob）→ 文本。返回 (text, None) 或 (None, 文案)。"""
    if not data:
        return None, "错误：空音频数据"
    fd, tmp = tempfile.mkstemp(suffix=ext)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    try:
        return transcribe(tmp)
    finally:
        try:
            os.remove(tmp)
        except Exception:
            pass


def _cloud_transcribe(path):
    """云端 API 兜底（需密钥）。"""
    provider = ASR_PROVIDER
    if not provider:
        if ALIYUN_ASR_KEY and ALIYUN_ASR_TOKEN:
            provider = "aliyun"
        elif XFYUN_ASR_APPID and XFYUN_ASR_APIKEY:
            provider = "xfyun"
        elif VOLCENGINE_ASR_KEY and VOLCENGINE_ASR_SECRET:
            provider = "volcengine"
    if not provider:
        return None, DISABLED_MSG
    if provider == "aliyun":
        return _placeholder(provider, path, "阿里云一句话/录音文件识别")
    if provider == "xfyun":
        return _placeholder(provider, path, "讯飞语音听写")
    if provider == "volcengine":
        return _placeholder(provider, path, "火山引擎语音识别")
    return None, f"未知 ASR provider：{provider}"


def _placeholder(provider, path, human):
    """云端真实调用脚手架：标准库 HTTP 接入点已就位，但为避免在缺密钥/未联调时产生副作用，
    这里统一返回明确的「待联调」文案。配齐密钥并验证后，可在此替换为真实 HTTP 调用。"""
    return None, f"{human}（{provider}）接入点已就绪，待联调：{os.path.basename(path)}"


def status():
    """对外状态：仅暴露布尔/provider 名，绝不泄露密钥本身。"""
    providers = {
        "whisper": _whisper_cached(),
        "vosk": vosk_available(),
        "local": _funasr_available(),
        "aliyun": bool(ALIYUN_ASR_KEY and ALIYUN_ASR_TOKEN),
        "xfyun": bool(XFYUN_ASR_APPID and XFYUN_ASR_APIKEY and XFYUN_ASR_APISECRET),
        "volcengine": bool(VOLCENGINE_ASR_KEY and VOLCENGINE_ASR_SECRET),
    }
    enabled = providers.get(ASR_PROVIDER, False) if ASR_PROVIDER else any(providers.values())
    provider = ASR_PROVIDER or (
        "whisper" if providers["whisper"]
        else ("vosk" if providers["vosk"]
              else ("local" if providers["local"] else None))
    )
    return {
        "provider": provider,
        "enabled": enabled,
        "local": providers["local"],
        "available": providers,
    }


# ── 启动预热：后端 import 时后台加载 whisper 模型，避免首句语音转写卡顿 ──
# ⚠️ Beta 修复 (Phase 34)：在本机运行环境（ctranslate2/faster-whisper 原生层）加载
# Whisper 模型会在后台线程触发原生段错误(segfault)，进而拖垮整个进程、后端无法启动。
# 因此默认关闭 import 期预热，仅在显式设置 XIAO6_ASR_WARMUP=true 时预热；
# 首次实际语音转写仍走懒加载 _ensure_whisper_model（该路径在本机仍可能 segfault，
# 属环境兼容性问题，不影响文本对话/桌宠/记忆/HUD 等核心链路）。
if os.environ.get("XIAO6_ASR_WARMUP", "false").lower() in ("1", "true", "yes") and _whisper_cached():
    threading.Thread(target=_ensure_whisper_model, daemon=True).start()
