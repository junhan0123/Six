#!/usr/bin/env python3
"""庄周 · 跨设备协同控制（模块4）脚手架。

本地多设备协同基础：设备注册 / 心跳 / 指令中继。
当前为本地基础实现（同机多实例或局域网设备登记）；跨网络信令 / 中继为后续阶段。
数据存于本地 devices.json，绝不外传。
"""

import json
import os
import threading
import time

_PATH = os.path.join(os.path.dirname(__file__), "devices.json")
_lock = threading.Lock()
_devices = {}


def _load():
    global _devices
    try:
        with open(_PATH, "r", encoding="utf-8") as f:
            _devices = json.load(f)
    except Exception:
        _devices = {}


def _save():
    try:
        with open(_PATH, "w", encoding="utf-8") as f:
            json.dump(_devices, f, ensure_ascii=False)
    except Exception:
        pass


def register(device_id, name=None, meta=None):
    with _lock:
        _load()
        _devices[device_id] = {
            "name": name or device_id,
            "meta": meta or {},
            "last_seen": int(time.time()),
        }
        _save()
    return _devices[device_id]


def heartbeat(device_id):
    with _lock:
        _load()
        if device_id in _devices:
            _devices[device_id]["last_seen"] = int(time.time())
            _save()
    return True


def list_devices():
    with _lock:
        _load()
    now = int(time.time())
    return [
        {
            "id": k,
            "name": v.get("name", k),
            "meta": v.get("meta", {}),
            "last_seen": v.get("last_seen", 0),
            "online": (now - v.get("last_seen", 0)) < 60,
        }
        for k, v in _devices.items()
    ]


def relay(device_id, command):
    # 占位：真实跨设备指令分发（P2P / 信令）后续接入
    return {
        "ok": True,
        "relayed_to": device_id,
        "command": command,
        "note": "中继脚手架就绪，待接入信令通道",
    }
