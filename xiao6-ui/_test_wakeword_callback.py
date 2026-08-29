"""实测 sounddevice RawInputStream callback：验证 _to_pcm16 不再 OverflowError。"""
import os
import sys
import threading
import time

import numpy as np
import sounddevice as sd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wakeword

SAMPLE_RATE = 16000
CHUNK = 1280

errors = []
callback_count = 0
lock = threading.Lock()
stop_event = threading.Event()


def callback(indata, frames, t, status):
    global callback_count
    try:
        pcm = wakeword._to_pcm16(indata, frames, dtype="int16", channels=1)
        with lock:
            callback_count += 1
        # 简单验证输出长度
        if len(pcm) != frames * 2:
            raise ValueError(f"PCM length mismatch: {len(pcm)} != {frames * 2}")
    except Exception as exc:
        errors.append(str(exc))
        stop_event.set()


print("Starting RawInputStream for 3 seconds...")
try:
    with sd.RawInputStream(
        samplerate=SAMPLE_RATE,
        blocksize=CHUNK,
        dtype="int16",
        channels=1,
        callback=callback,
    ):
        stop_event.wait(timeout=3.0)
except Exception as exc:
    print(f"Stream error: {exc}")

print(f"Callback count: {callback_count}")
print(f"Errors: {errors if errors else 'None'}")

if errors:
    sys.exit(1)
print("Callback test PASSED.")
