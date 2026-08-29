#!/usr/bin/env python3
"""庄周 · 媒体生成 Provider（Phase 4 脚手架，env 门控 + 优雅降级）

能力：文生图 / 文生视频 / 文生音乐。
默认：零密钥优先，未配置即返回「未启用」文案，绝不消耗任何积分。
配置后（.env 配 XIAO6_MEDIA_PROVIDER=minimax + MINIMAX_API_KEY[+MINIMAX_GROUP_ID]）
可真实调用 MiniMax；调用失败仍优雅降级，不影响主链路。

支持运行时通过 config.update_env_file() 热重载。
"""

import json
import urllib.error
import urllib.request

import config

DISABLED_MSG = (
    "媒体生成当前未启用（零密钥优先，不消耗你的积分）。\n" "如需启用，在设置 › 媒体能力中配置 MiniMax API Key 即可。"
)


def status():
    """对外状态：仅暴露布尔/provider 名，绝不泄露密钥本身。"""
    enabled = bool(config.MEDIA_PROVIDER and config.MINIMAX_API_KEY)
    return {
        "provider": config.MEDIA_PROVIDER or None,
        "enabled": enabled,
        "supports": ["image", "video", "music"] if enabled else [],
    }


def generate(kind, prompt, **opts):
    """生成媒体。kind ∈ {image, video, music}。

    返回 (url_or_path, None) 成功，或 (None, 降级/错误文案)。
    """
    if not config.MEDIA_PROVIDER or not config.MINIMAX_API_KEY:
        return None, DISABLED_MSG
    if config.MEDIA_PROVIDER != "minimax":
        return None, f"未知媒体 provider：{config.MEDIA_PROVIDER}（当前仅支持 minimax）"
    return _minimax_generate(kind, prompt, opts)


def _minimax_generate(kind, prompt, opts):
    """真实调用 MiniMax（仅当密钥已配置时才会进入本函数）。

    用标准库 urllib 实现，全程 try/except 兜底，任何失败都转成友好文案，绝不抛异常中断主链路。
    """
    try:
        if kind == "image":
            model = opts.get("model", "image-01")
            payload = {
                "model": model,
                "prompt": prompt,
                "aspect_ratio": opts.get("aspect_ratio", "16:9"),
                "response_format": "url",
            }
            url = "https://api.minimax.chat/v1/image_generation"
        elif kind == "video":
            model = opts.get("model", "video-01")
            payload = {
                "model": model,
                "prompt": prompt,
            }
            url = "https://api.minimax.chat/v1/video_generation"
        elif kind == "music":
            model = opts.get("model", "music-01")
            payload = {
                "model": model,
                "lyrics": prompt,
                "title": opts.get("title", "庄周生成曲"),
            }
            url = "https://api.minimax.chat/v1/music_generation"
        else:
            return None, f"不支持的媒体类型：{kind}（可选 image/video/music）"

        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {config.MINIMAX_API_KEY}",
                **({"GroupId": config.MINIMAX_GROUP_ID} if config.MINIMAX_GROUP_ID else {}),
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
        # MiniMax 返回结构：{base_resp:{status_code}, data:{image_list:[{url}]} / ...}
        if data.get("base_resp", {}).get("status_code", 0) != 0:
            return None, f"MiniMax 返回错误：{data.get('base_resp', {})}"
        out = data.get("data", {})
        if kind == "image":
            items = out.get("image_list") or []
            return (items[0].get("url") if items else None), None
        if kind == "video":
            return out.get("video_url"), None
        if kind == "music":
            return out.get("audio_url"), None
        return None, "未知返回结构"
    except urllib.error.HTTPError as e:
        return None, f"媒体生成请求失败（HTTP {e.code}）"
    except Exception as e:
        return None, f"媒体生成失败：{e}"
