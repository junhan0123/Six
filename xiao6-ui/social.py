#!/usr/bin/env python3
"""小6 · 社交扩展 Provider（Phase 4 脚手架，env 门控 + 优雅降级）

能力：Discord / 飞书 消息推送。
默认：零密钥优先，未配置即返回「未启用」文案，绝不消耗任何积分/触发外部请求。
配置后（.env 配 DISCORD_BOT_TOKEN 或 FEISHU_APP_ID/APP_SECRET）可真实推送；
调用失败仍优雅降级，不影响主链路。
"""

import json
import os
import urllib.error
import urllib.request

from config import DISCORD_BOT_TOKEN, FEISHU_APP_ID, FEISHU_APP_SECRET

WECHAT_WEBHOOK_URL = os.environ.get("WECHAT_WEBHOOK_URL", "")

DISABLED_MSG = (
    "社交推送当前未启用（零密钥优先，不触达任何外部账号）。\n"
    "如需启用：Discord 配 DISCORD_BOT_TOKEN；飞书配 FEISHU_APP_ID + FEISHU_APP_SECRET；"
    "微信配 WECHAT_WEBHOOK_URL（ClawBot/企业微信机器人 Webhook）。"
)


def status():
    """对外状态：仅暴露布尔，绝不泄露密钥本身。"""
    return {
        "discord": bool(DISCORD_BOT_TOKEN),
        "feishu": bool(FEISHU_APP_ID and FEISHU_APP_SECRET),
        "wechat": bool(WECHAT_WEBHOOK_URL),
    }


def send(platform, target, text):
    """向指定平台推送消息。platform ∈ {discord, feishu, wechat}。

    返回 (True, None) 成功，或 (False, 降级/错误文案)。
    """
    if platform == "discord":
        if not DISCORD_BOT_TOKEN:
            return False, DISABLED_MSG
        return _discord_send(target, text)
    if platform == "feishu":
        if not (FEISHU_APP_ID and FEISHU_APP_SECRET):
            return False, DISABLED_MSG
        return _feishu_send(target, text)
    if platform == "wechat":
        if not WECHAT_WEBHOOK_URL:
            return False, DISABLED_MSG
        return _wechat_send(target, text)
    return False, f"不支持的社交平台：{platform}（可选 discord / feishu / wechat）"


def _discord_send(channel_id, text):
    try:
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
        body = json.dumps({"content": text}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
        return (data.get("id") is not None), None
    except urllib.error.HTTPError as e:
        return False, f"Discord 推送失败（HTTP {e.code}）"
    except Exception as e:
        return False, f"Discord 推送失败：{e}"


def _feishu_send(open_id, text):
    try:
        # 1) 取 tenant_access_token
        token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        token_body = json.dumps({"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}).encode("utf-8")
        req = urllib.request.Request(
            token_url, data=token_body, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            token_data = json.loads(resp.read().decode("utf-8", "replace"))
        access_token = token_data.get("tenant_access_token")
        if not access_token:
            return False, f"飞书获取 token 失败：{token_data}"
        # 2) 发消息
        msg_url = "https://open.feishu.cn/open-apis/im/v1/messages"
        payload = {
            "receive_id": open_id,
            "msg_type": "text",
            "content": json.dumps({"text": text}, ensure_ascii=False),
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            msg_url,
            data=body,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
        return (data.get("code", 0) == 0), (None if data.get("code", 0) == 0 else f"飞书推送失败：{data}")
    except urllib.error.HTTPError as e:
        return False, f"飞书推送失败（HTTP {e.code}）"
    except Exception as e:
        return False, f"飞书推送失败：{e}"


def _wechat_send(target, text):
    """微信推送（ClawBot / 企业微信机器人 Webhook 风格）：POST 文本到配置的 webhook。

    target 可留空（webhook 已含接收方）；部分网关支持在 body 带 touser/toparty。
    """
    try:
        payload = {"msgtype": "text", "text": {"content": text}}
        if target:
            payload["text"]["touser"] = target
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            WECHAT_WEBHOOK_URL,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
        # 企业微信：errcode==0 成功；ClawBot 网关可能返回不同结构，宽松判定
        ok = data.get("errcode", 0) == 0 if isinstance(data, dict) else True
        return ok, (None if ok else f"微信推送失败：{data}")
    except urllib.error.HTTPError as e:
        return False, f"微信推送失败（HTTP {e.code}）"
    except Exception as e:
        return False, f"微信推送失败：{e}"
