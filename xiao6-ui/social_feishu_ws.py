#!/usr/bin/env python3
"""庄周 · 飞书长连接(stream) 接收（可选，需独立依赖，仅显式开启）

为什么需要：飞书官方事件订阅默认要求公网回调 URL；但其「长连接」模式
（WebSocket stream）无需公网 IP，本地 agent 直连即可收消息——非常适合本机部署。

使用前提（用户需在 .env 显式配置并安装依赖）：
- FEISHU_WS_ENABLED=true
- FEISHU_APP_ID / FEISHU_APP_SECRET（取 tenant_access_token）
- FEISHU_WS_URL：开发者后台「事件订阅 > 长连接」给出的 WebSocket 地址
  （不同租户/版本略有差异，故交由用户显式填写，避免硬编码错误地址）
- 可选 FEISHU_ENCRYPT_KEY：若开启了「加密」则需用它做 AES 解密
- pip install websocket-client pycryptodome

安全：本模块不执行任何外部代码；仅把解析出的消息交给 social_inbound.handle_inbound。
若依赖缺失或未开启，模块静默不可用，绝不影响主链路。
"""

import json
import os
import threading

from config import FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_WS_ENABLED, FEISHU_WS_URL


def _get_tenant_token():
    import urllib.request

    body = json.dumps({"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}).encode("utf-8")
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        data=body, headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        d = json.loads(resp.read().decode("utf-8", "replace"))
    return d.get("tenant_access_token")


def _decrypt_event(raw, encrypt_key):
    """若有加密 key，用 AES/ECB/PKCS7 解密飞书事件体；否则原样返回。"""
    if not encrypt_key:
        return raw
    try:
        from Crypto.Cipher import AES
        import base64

        key = encrypt_key.encode("utf-8")
        cipher = AES.new(key, AES.MODE_ECB)
        pad = len(raw) % 4
        if pad:
            raw += "=" * (4 - pad)
        decrypted = cipher.decrypt(base64.b64decode(raw))
        # 去掉 PKCS7 填充
        pad_len = decrypted[-1]
        return decrypted[:-pad_len].decode("utf-8", "replace")
    except Exception as e:
        print(f"[飞书WS] 解密失败：{e}")
        return raw


def _on_message(raw_text):
    """解析一帧 WS 消息，必要时解密，提取文本消息并转交入站处理。"""
    try:
        frame = json.loads(raw_text)
        t = frame.get("type")
        if t == "challenge":
            # 飞书长连接握手：回显 challenge
            return {"type": "challenge", "challenge": frame.get("challenge")}
        if t == "ping":
            return {"type": "pong", "ping": frame.get("ping")}
        if t == "message":
            payload = frame.get("data") or {}
            event = payload.get("event") or {}
            msg = event.get("message") or {}
            if msg.get("message_type") != "text":
                return None
            # 提取纯文本（飞书 text 内容带尾随换行）
            content = (msg.get("content") or "{}")
            try:
                text = json.loads(content).get("text", "").strip()
            except Exception:
                text = content.strip()
            sender = msg.get("sender", {}).get("sender_id", {}).get("open_id") or msg.get("chat_id") or "feishu_user"
            if text:
                import social_inbound as _si

                threading.Thread(target=lambda: _si.handle_inbound("feishu", sender, text), daemon=True).start()
        return None
    except Exception as e:
        print(f"[飞书WS] 消息解析异常：{e}")
        return None


def start_feishu_ws():
    """后台线程：连接飞书长连接并持续接收。仅在依赖就绪且已开启时调用。"""
    try:
        import websocket  # websocket-client
    except ImportError:
        print("[飞书WS] 未安装 websocket-client，跳过长连接接收（pip install websocket-client pycryptodome）")
        return
    if FEISHU_WS_ENABLED not in ("1", "true", "yes"):
        return
    if not (FEISHU_APP_ID and FEISHU_APP_SECRET and FEISHU_WS_URL):
        print("[飞书WS] 缺少 FEISHU_APP_ID/SECRET 或 FEISHU_WS_URL，跳过")
        return

    encrypt_key = os.environ.get("FEISHU_ENCRYPT_KEY", "")
    ws_url = FEISHU_WS_URL

    def _run():
        try:
            ws = websocket.create_connection(ws_url, timeout=30)
            print("[飞书WS] 长连接已建立")
            while True:
                raw = ws.recv()
                if not raw:
                    continue
                resp = _on_message(raw)
                if resp:
                    ws.send(json.dumps(resp))
        except Exception as e:
            print(f"[飞书WS] 连接异常（后台线程退出，不重试以免刷屏）：{e}")

    threading.Thread(target=_run, daemon=True).start()
    print("[飞书WS] 后台接收线程已启动（如依赖/配置就绪）")
