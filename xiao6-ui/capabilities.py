#!/usr/bin/env python3
"""庄周 · 能力注册表（参考实现 capability-registry 轻量对齐，Phase 5）

⚠️ DEPRECATED 兼容层（Phase 40）：本文件为「上下文注入能力」来源，仍被
   capability_os.registry._build() 合并进单一声明真相源，也被 server.py
   /api/capabilities 直接消费。自 Phase 40 起，能力声明单一真相源是
   capability_os.registry；本文件保留只为不破坏现有注入链路与端点。

只搬「声明式注册表的壳」：把每个领域能力收敛为一个单元（触发词 + 上下文块 + 可选预喂），
未来新增能力只需注册一行，无需散落多处。不搬 api-slot / tool-factory 重型机制
（探索结论：那是为解决参考实现历史碎片化才做的，庄周范围不需要）。

当前注册：hotspot（热点上下文）、prefetch（天气/新闻预取背景）、computer_action（手）。
这都是对已验证注入链路的「统一视图」，不改动 build_context_prefix 的既有调用。
"""
CAPABILITIES = {}


def _register(cap):
    CAPABILITIES[cap["id"]] = cap
    return cap


# ---- 热点能力 ----
def _hotspot_block(message):
    try:
        import hotspots

        return hotspots.build_hotspot_context(message or "")
    except Exception:
        return ""


_register(
    {
        "id": "hotspot",
        "label": "热点上下文",
        "icon": "📡",
        "group": "上下文增强",
        "description": "实时聚合抖音 / 微博 / 微信 / 小红书等多平台热榜，当对话涉及热点话题时自动注入最新榜单上下文，让回答紧跟时事。",
        "how": "命中热点触发词（或热点面板打开）时，汇总各平台当前热榜，作为系统上下文注入模型；不命中则不打扰，零额外开销。",
        "triggers": ["热搜", "热点", "榜单", "新闻", "热榜", "微博", "抖音", "知乎", "头条", "微信", "小红书"],
        "build_context": _hotspot_block,
    }
)


# ---- 预取背景能力（天气/新闻，模型醒来即用）----
def _prefetch_block(message):
    try:
        import prefetch

        return prefetch.format_prefetched_items(prefetch.get_valid_prefetch())
    except Exception:
        return ""


_register(
    {
        "id": "prefetch",
        "label": "预取背景（天气/新闻）",
        "icon": "🌤️",
        "group": "上下文增强",
        "description": "后台定时预取天气与科技新闻，模型「醒来」即可直接引用，无需等待实时抓取，对话更顺滑。",
        "how": "后台每 30 分钟预取一次天气与科技新闻并缓存；每次对话自动把「仍有效」的预取条目拼进系统上下文，过期自动跳过。",
        "triggers": [],  # 无触发词：有有效预取即注入
        "build_context": _prefetch_block,
    }
)


# ---- 电脑操作能力（Phase 21 "Hand"）—— 让庄周自知拥有「手」----
def _computer_action_block(message):
    # 仅在对话涉及操作电脑/打开/文件/屏幕时给出能力说明；关闭开关则零注入
    try:
        import config
        if not getattr(config, "FEATURE_COMPUTER_ACTION", True):
            return ""
    except Exception:
        return ""
    triggers = ["打开", "文件夹", "目录", "文件", "记事本", "搜索", "查找",
                "操作电脑", "复制", "屏幕", "项目目录"]
    msg = message or ""
    if msg and not any(t in msg for t in triggers):
        return ""
    try:
        from computer_action import get_capabilities
        caps = get_capabilities()
    except Exception:
        return ""
    if not caps:
        return ""
    names = "、".join(c.get("label", c["id"]) for c in caps)
    return ("【我的电脑操作能力】在你的授权下，我可以：" + names +
            "（仅打开/观察/读取类操作；删除、改系统设置等危险操作已禁用）。")


_register(
    {
        "id": "computer_action",
        "label": "电脑操作（手）",
        "icon": "🖐️",
        "group": "电脑能力",
        "description": "安全电脑操作层：在你的授权下打开应用/文件夹/文件、搜索文件、复制文本。所有动作经白名单与权限闸门，删除/改设置/自动发消息等危险操作被禁止。",
        "how": "当你说「打开项目目录」「搜索某文件」「复制这段文字」等意图时，我会先观察屏幕、规划动作、请求确认（如需要）、执行、再验证结果，并在状态中展示观察/规划/执行/验证四态。",
        "triggers": ["打开", "文件夹", "目录", "文件", "记事本", "搜索", "查找",
                     "操作电脑", "复制", "屏幕", "项目目录"],
        "build_context": _computer_action_block,
    }
)


def active_capability_blocks(message=""):
    """返回当前应注入的上下文块列表（按能力单元）。

    各能力的 build_context 内部自带门控（hotspot 的 panel_active/matches、
    prefetch 的过期过滤），这里只收集非空块，不做重复触发词过滤。
    """
    blocks = []
    for cap in CAPABILITIES.values():
        try:
            block = cap["build_context"](message)
        except Exception:
            block = ""
        if block:
            blocks.append(block)
    return blocks


def capability_summary():
    """能力清单（供状态页 / 调试查看）。"""
    return [{"id": c["id"], "label": c["label"], "triggers": c.get("triggers", [])} for c in CAPABILITIES.values()]


def capability_details(probe_message=""):
    """能力清单（含图标 / 描述 / 触发词 / 实时激活状态），供能力视图渲染。

    active 表示当前上下文下该能力是否会真正注入：对各能力的 build_context
    做一次探测，非空即为激活。探测失败不抛错，降级为未激活。
    """
    out = []
    for cap in CAPABILITIES.values():
        try:
            block = cap["build_context"](probe_message or "")
        except Exception:
            block = ""
        out.append(
            {
                "id": cap["id"],
                "label": cap["label"],
                "icon": cap.get("icon", "🧩"),
                "group": cap.get("group", "其他"),
                "description": cap.get("description", ""),
                "how": cap.get("how", ""),
                "triggers": cap.get("triggers", []),
                "active": bool(block and block.strip()),
            }
        )
    return out
