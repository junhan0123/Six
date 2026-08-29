# PHASE 5.1-HOTFIX STEP 5：TTS 真实运行时验证
# 1) 库层 edge_tts.Communicate 能否产出真实 MP3 bytes
# 2) POST /api/speak（stream=false 整段 blob 与默认流式）status / Content-Type / Content-Length / 实际 bytes
import asyncio
import json
import os
import urllib.request

print("=" * 72)
print("[1] 库层验证：edge_tts.Communicate")
print("=" * 72)
try:
    import edge_tts

    print("edge_tts version:", getattr(edge_tts, "__version__", "n/a"))

    async def _synth():
        buf = bytearray()
        com = edge_tts.Communicate("代理热修完成，语音链路验证。", "zh-CN-YunxiNeural", rate="+0%")
        async for chunk in com.stream():
            if chunk["type"] == "audio":
                buf.extend(chunk["data"])
        return bytes(buf)

    audio = asyncio.run(_synth())
    print("LIB BYTES:", len(audio), "MAGIC:", audio[:4])
    print("LIB VERDICT:", "PASS (真实 MP3 帧头)" if len(audio) > 1000 and audio[:2] in (b"\xff\xf3", b"\xff\xfb", b"\xff\xf2", b"ID3"[:2]) else "CHECK")
except Exception as e:
    print("LIB FAIL:", repr(e))

# 本进程访问本机 server 强制直连（避免继承代理干扰测量）
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def probe_speak(label, payload, timeout=120):
    print("=" * 72)
    print(f"[2] 端点验证：POST /api/speak  ({label})")
    print("=" * 72)
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "http://127.0.0.1:8010/api/speak",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        r = opener.open(req, timeout=timeout)
        status = r.status
        ct = r.headers.get("Content-Type")
        cl = r.headers.get("Content-Length")
        te = r.headers.get("Transfer-Encoding")
        data = r.read()
        print("HTTP status      :", status)
        print("Content-Type     :", ct)
        print("Content-Length   :", cl)
        print("Transfer-Encoding:", te)
        print("实际 bytes        :", len(data))
        print("MAGIC            :", data[:4])
        ok = status == 200 and len(data) > 1000 and (data[:2] in (b"\xff\xf3", b"\xff\xfb", b"\xff\xf2") or data[:3] == b"ID3")
        print("VERDICT          :", "PASS — 真实 MP3 音频" if ok else "FAIL — 非预期输出")
        return ok
    except Exception as e:
        print("REQUEST FAIL:", repr(e))
        return False


r1 = probe_speak("stream=false 整段 blob", {"text": "代理热修完成，整段合成验证。", "stream": False})
r2 = probe_speak("默认流式（chunked）", {"text": "代理热修完成，流式合成验证。"})

print("=" * 72)
print(f"SPEAK ENDPOINT: blob={'PASS' if r1 else 'FAIL'}  stream={'PASS' if r2 else 'FAIL'}")
print("=" * 72)
