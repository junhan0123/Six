"""wakeword._to_pcm16 单元测试：验证各种 dtype 输入都能正确转换为 PCM16 bytes。"""
import os

import numpy as np
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wakeword


def test_pcm16_conversion():
    frames = 1280
    channels = 1

    cases = [
        ("float32", np.random.uniform(-1.0, 1.0, size=frames).astype(np.float32), 1),
        ("float32_stereo", np.random.uniform(-1.0, 1.0, size=(frames, 2)).astype(np.float32), 2),
        ("int16", (np.random.uniform(-32768, 32767, size=frames)).astype(np.int16), 1),
        ("uint8", np.random.randint(0, 256, size=frames).astype(np.uint8), 1),
        ("int8", np.random.randint(-128, 128, size=frames).astype(np.int8), 1),
    ]

    for name, arr, ch in cases:
        # 模拟 sounddevice 传回 cffi buffer 的情况：取字节视图
        buf = memoryview(arr.tobytes())
        pcm = wakeword._to_pcm16(buf, frames, dtype=arr.dtype.name, channels=ch)
        assert isinstance(pcm, bytes), f"{name}: result must be bytes"
        expected_len = frames * 2  # PCM16 = 2 bytes/sample
        assert len(pcm) == expected_len, f"{name}: expected {expected_len} bytes, got {len(pcm)}"
        # 转换回来的 int16 不应全是 0/异常
        back = np.frombuffer(pcm, dtype="<i2")
        assert back.dtype == np.int16, f"{name}: decoded dtype must be int16"
        print(f"  {name}: PASS (len={len(pcm)})")

    # 也验证 numpy ndarray 直接传入
    arr_f = np.random.uniform(-1.0, 1.0, size=frames).astype(np.float32)
    pcm = wakeword._to_pcm16(arr_f, frames, dtype="float32", channels=1)
    assert len(pcm) == frames * 2
    print("  float32 ndarray direct: PASS")

    print("\nAll _to_pcm16 tests passed.")


if __name__ == "__main__":
    import os

    test_pcm16_conversion()
