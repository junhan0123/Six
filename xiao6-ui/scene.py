#!/usr/bin/env python3
"""庄周 · 声明式场景卡片通道（scene）

agent 通过 render_card 工具「声明」界面某处此刻该长什么样，本模块暂存这些声明。
两条推送路径：
1) 聊天流：server.py 在 run_fc_loop 后调用 drain_scene_events() 随本次 SSE 推给前端；
2) 后台任务（如软件安装）：先 push_scene_event() 再调 flush_scene_events() 实时推给所有在线连接。

前端 ZZScene 按 id 幂等渲染 / 更新 / 移除卡片（参考实现 scene.js 同款能力，用庄周架构重写）。
"""

from proactive import SUBSCRIBERS, SUBSCRIBERS_LOCK

# 模块级队列：render_card 工具调用、或后台任务调用时压入，server / flush 取出后清空
_pending_scene_events = []


def push_scene_event(card):
    """压入一张卡片声明（dict：至少含 id，以及 action/kind 等字段）。"""
    global _pending_scene_events
    if not isinstance(card, dict):
        return
    if not card.get("id"):
        return
    _pending_scene_events.append(card)


def drain_scene_events():
    """取出并清空聊天流待推送卡片（server 在工具执行后调用，随请求 SSE 推送）。"""
    global _pending_scene_events
    out = _pending_scene_events
    _pending_scene_events = []
    return out


def _use_eventbus():
    try:
        from eventbus import enabled

        return enabled()
    except Exception:
        return False


def flush_scene_events():
    """把当前暂存卡片实时推给所有在线 SSE 连接（后台任务调用，如软件安装进度）。

    取出的卡片会逐条以 xiao6_event:scene 推给每个订阅者（/api/stream 长连接）。
    若无可推送内容则空操作，安全幂等。
    FEATURE_EVENTBUS=true 经 EventBus 发布；false/异常回退 SUBSCRIBERS 直发（§1.6）。
    """
    global _pending_scene_events
    out = _pending_scene_events
    _pending_scene_events = []
    if not out:
        return
    if _use_eventbus():
        try:
            from eventbus import publish_system

            for card in out:
                publish_system("scene", {"card": card}, source="scene")
            return
        except Exception as e:
            print(f"[scene] EventBus 推送失败，回退 SUBSCRIBERS: {e}")
    with SUBSCRIBERS_LOCK:
        for q in SUBSCRIBERS:
            try:
                for card in out:
                    q.put({"xiao6_event": "scene", "card": card})
            except Exception:
                pass
