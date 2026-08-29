"""回归测试：模拟原始 wakeword.py line 130 的溢出场景，确认新版不再报错。"""
import os
import sys

import numpy as np
import sounddevice as sd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wakeword

SAMPLE_RATE = 16000
CHUNK = 1280

errors_old = []
errors_new = []
callback_count = 0
stop_event = object()


class Stopper:
    def __init__(self):
        self.e = False
    def is_set(self):
        return self.e

stopper = Stopper()


def old_callback(indata, frames, _t, _status):
    global callback_count
    try:
        pcm = (np.clip(indata, -1, 1) * 32767).astype("<i2").tobytes()
    except Exception as exc:
        errors_old.append(str(exc))


def new_callback(indata, frames, _t, _status):
    global callback_count
    try:
        pcm = wakeword._to_pcm16(indata, frames, dtype="int16", channels=1)
        callback_count += 1
    except Exception as exc:
        errors_new.append(str(exc))


print("Testing OLD callback (should reproduce OverflowError)...")
try:
    with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=CHUNK, dtype="int16", channels=1, callback=old_callback):
        import time
        time.sleep(0.5)
except Exception as exc:
    print(f"  Stream error: {exc}")
print(f"  Old callback errors: {errors_old[:3]}")

print("\nTesting NEW callback (should be clean)...")
try:
    with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=CHUNK, dtype="int16", channels=1, callback=new_callback):
        import time
        time.sleep(0.5)
except Exception as exc:
    print(f"  Stream error: {exc}")
print(f"  New callback errors: {errors_new}")
print(f"  New callback success count: {callback_count}")

if errors_old and not errors_new:
    print("\nRegression test PASSED: old code fails, new code succeeds.")
else:
    print("\nRegression test result: old fails =", bool(errors_old), ", new fails =", bool(errors_new))
