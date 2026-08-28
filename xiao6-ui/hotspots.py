#!/usr/bin/env python3
"""庄周 · 实时热点热榜"""

import concurrent.futures
import os
import re
import threading
import time

from config import HOTDATA_KEY
from http_client import http_get_json

_HOTSPOT_CACHE = {"data": None, "ts": 0.0}
_HOTSPOT_REFRESH_MINUTES = 30
_cache_lock = threading.Lock()  # 并发加固：避免多线程同时触发重复抓取风暴


def _pick_array(data):
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    for key in ("result", "data", "newslist", "list", "items", "hot_list", "hotList"):
        v = data.get(key)
        if isinstance(v, list):
            return v
    for v in data.values():
        if isinstance(v, dict):
            for key in ("list", "items", "hot_list", "hotList", "data"):
                if isinstance(v.get(key), list):
                    return v[key]
    return []


def _fmt_num(v):
    """去掉多余尾零：1.00 -> 1，1.50 -> 1.5，1.25 -> 1.25。"""
    return f"{v:.2f}".rstrip("0").rstrip(".")


def _fmt_heat(v):
    try:
        n = float(v)
    except Exception:
        return str(v or "")
    if n >= 1e8:
        return f"{_fmt_num(n / 1e8)}亿"
    if n >= 1e4:
        return f"{int(n / 1e4)}万"
    return str(int(n))


# ── 地域识别：把热搜文本映射到真实经纬度，供 3D 地球动态打点 ──
# 名称按长度降序匹配，先命中城市再命中省份；覆盖中国省级行政区 + 全球主要城市。
GEO_MAP = {
    # 直辖市 / 特别行政区
    "北京": (39.90, 116.40),
    "上海": (31.23, 121.47),
    "天津": (39.13, 117.20),
    "重庆": (29.56, 106.55),
    "香港": (22.32, 114.17),
    "澳门": (22.20, 113.54),
    "台北": (25.03, 121.57),
    # 主要城市（优先于省份匹配）
    "广州": (23.13, 113.26),
    "深圳": (22.54, 114.06),
    "杭州": (30.27, 120.15),
    "南京": (32.06, 118.80),
    "成都": (30.57, 104.07),
    "武汉": (30.59, 114.30),
    "西安": (34.34, 108.94),
    "苏州": (31.30, 120.62),
    "长沙": (28.23, 112.94),
    "郑州": (34.75, 113.62),
    "沈阳": (41.80, 123.43),
    "长春": (43.90, 125.32),
    "哈尔滨": (45.80, 126.53),
    "济南": (36.65, 117.00),
    "青岛": (36.07, 120.38),
    "石家庄": (38.04, 114.51),
    "太原": (37.87, 112.55),
    "合肥": (31.86, 117.27),
    "福州": (26.07, 119.30),
    "厦门": (24.48, 118.09),
    "南昌": (28.68, 115.86),
    "昆明": (25.04, 102.71),
    "贵阳": (26.65, 106.63),
    "南宁": (22.82, 108.32),
    "海口": (20.04, 110.20),
    "兰州": (36.06, 103.83),
    "西宁": (36.62, 101.78),
    "呼和浩特": (40.84, 111.75),
    "银川": (38.49, 106.23),
    "乌鲁木齐": (43.83, 87.62),
    "拉萨": (29.65, 91.13),
    "大同": (40.09, 113.30),
    "大连": (38.91, 121.61),
    "宁波": (29.87, 121.55),
    "无锡": (31.49, 120.31),
    "温州": (27.99, 120.70),
    "东莞": (23.02, 113.75),
    "佛山": (23.02, 113.12),
    "珠海": (22.27, 113.58),
    "三亚": (18.25, 109.51),
    "桂林": (25.27, 110.29),
    "丽江": (26.87, 100.23),
    # 省份（作为兜底，命中城市则不会到这一层）
    "四川": (30.65, 104.07),
    "广东": (23.40, 113.55),
    "江苏": (32.06, 118.78),
    "浙江": (30.27, 120.15),
    "山东": (36.65, 117.00),
    "河南": (34.75, 113.62),
    "河北": (38.04, 114.51),
    "湖南": (28.23, 112.94),
    "湖北": (30.59, 114.30),
    "福建": (26.07, 119.30),
    "陕西": (34.34, 108.94),
    "云南": (25.04, 102.71),
    "贵州": (26.65, 106.63),
    "广西": (22.82, 108.32),
    "海南": (20.04, 110.20),
    "黑龙江": (45.80, 126.53),
    "吉林": (43.90, 125.32),
    "辽宁": (41.80, 123.43),
    "山西": (37.87, 112.55),
    "安徽": (31.86, 117.27),
    "江西": (28.68, 115.86),
    "甘肃": (36.06, 103.83),
    "青海": (36.62, 101.78),
    "内蒙古": (40.84, 111.75),
    "宁夏": (38.49, 106.23),
    "新疆": (43.83, 87.62),
    "西藏": (29.65, 91.13),
    "台湾": (25.03, 121.57),
    # 全球主要城市
    "纽约": (40.71, -74.01),
    "伦敦": (51.51, -0.13),
    "巴黎": (48.85, 2.35),
    "东京": (35.68, 139.69),
    "首尔": (37.57, 126.98),
    "莫斯科": (55.75, 37.62),
    "华盛顿": (38.91, -77.04),
    "洛杉矶": (34.05, -118.24),
    "旧金山": (37.77, -122.42),
    "柏林": (52.52, 13.40),
    "布鲁塞尔": (50.85, 4.35),
    "日内瓦": (46.20, 6.14),
    "罗马": (41.90, 12.50),
    "悉尼": (-33.87, 151.21),
    "墨尔本": (-37.81, 144.96),
    "新加坡": (1.35, 103.82),
    "曼谷": (13.76, 100.50),
    "新德里": (28.61, 77.21),
    "孟买": (19.08, 72.88),
    "迪拜": (25.20, 55.27),
    "开罗": (30.04, 31.24),
    "圣保罗": (-23.55, -46.63),
    "里约热内卢": (-22.91, -43.17),
    "墨西哥城": (19.43, -99.13),
    "多伦多": (43.65, -79.38),
    "温哥华": (49.28, -123.12),
    "东京都": (35.68, 139.69),
}

_GEO_KEYS = sorted(GEO_MAP.keys(), key=len, reverse=True)


def geo_tag(text):
    """扫描文本，返回首个命中的地域 {region, lat, lon} 或 None。"""
    if not text or not isinstance(text, str):
        return None
    for name in _GEO_KEYS:
        if name in text:
            lat, lon = GEO_MAP[name]
            return {"region": name, "lat": lat, "lon": lon}
    return None


def _search_url(platform, text):
    """为热点条目合成可点击的搜索链接（数据源未提供直链时兜底）。"""
    from urllib.parse import quote

    q = quote(str(text))
    base = {
        "douyin": "https://www.douyin.com/search/%s",
        "xiaohongshu": "https://www.xiaohongshu.com/search_result?keyword=%s",
        "wechat": "https://weixin.sogou.com/weixin?type=2&query=%s",
        "weibo": "https://s.weibo.com/weibo?q=%s",
    }.get(platform)
    return base % q if base else ""


def _normalize(platform, raw, source):
    out = []
    for i, it in enumerate(raw[:50]):
        if not isinstance(it, dict):
            continue
        title = (
            it.get("word")
            or it.get("hotword")
            or it.get("sentence")
            or it.get("title")
            or it.get("name")
            or it.get("keyword")
            or it.get("query")
            or it.get("text")
            or it.get("display_query")
            or ""
        )
        title = str(title).strip()
        if not title:
            continue
        heat = (
            it.get("hot_value")
            or it.get("hotValue")
            or it.get("hotwordnum")
            or it.get("heat")
            or it.get("score")
            or it.get("views")
            or it.get("view_count")
            or it.get("num")
            or ""
        )
        raw_url = it.get("url") or it.get("share_url") or it.get("link") or it.get("jump_url") or ""
        item = {
            "platform": platform,
            "rank": int(it.get("position") or it.get("rank") or it.get("index") or i + 1),
            "text": title,
            "heat": _fmt_heat(heat),
            "trend": "same",
            "isNew": False,
            "url": raw_url or _search_url(platform, title),
            "source": source,
        }
        tag = geo_tag(title)
        if tag:
            item["region"] = tag["region"]
            item["lat"] = tag["lat"]
            item["lon"] = tag["lon"]
        out.append(item)
    return out


def _fetch_with_fallback(platform, attempts):
    """按顺序尝试多个数据源，第一个返回非空即采用；全部失败返回 []。

    attempts: list of (url, source, headers|None)，headers 仅在有 key 时传入。
    """
    last_err = ""
    for url, source, headers in attempts:
        try:
            raw = http_get_json(url, headers=headers) if headers else http_get_json(url)
            items = _normalize(platform, _pick_array(raw), source)
            if items:
                return items
        except Exception as e:
            last_err = str(e)
    if last_err:
        print(f"[hotspots] 平台 {platform} 所有数据源失败：{last_err}")
    return []


def _fetch_douyin():
    # 回退链：haotechs -> xxapi -> tianapi(可选) -> 自定义(可选)
    attempts = [("https://www.haotechs.cn/ljh-wx/api/douyinHot", "haotechs", None)]
    attempts.append(("https://v2.xxapi.cn/api/douyinhot", "xxapi", None))
    tianapi_key = os.environ.get("TIANAPI_KEY", "").strip()
    if tianapi_key:
        attempts.append((f"https://apis.tianapi.com/douyinhot/index?key={tianapi_key}", "tianapi", None))
    custom = os.environ.get("HOTSPOT_DOUYIN_URL", "").strip()
    if custom:
        attempts.append((custom, "custom", None))
    return _fetch_with_fallback("douyin", attempts)


def _fetch_xhs():
    # 回退链：hotdata -> tikhub(可选) -> 自定义(可选)
    attempts = [("https://w-hotdata.aipromptnav.com/api/hot-data/xiaohongshu", "hotdata", {"X-API-Key": HOTDATA_KEY})]
    tikhub = os.environ.get("TIKHUB_TOKEN", os.environ.get("HOTSPOT_TIKHUB_TOKEN", "")).strip()
    if tikhub:
        attempts.append(("https://api.tikhub.io/api/v1/xiaohongshu/web_v2/fetch_hot_list", "tikhub", {"Authorization": f"Bearer {tikhub}"}))
    custom = os.environ.get("HOTSPOT_XHS_URL", os.environ.get("HOTSPOT_XIAOHONGSHU_URL", "")).strip()
    if custom:
        attempts.append((custom, "custom", None))
    return _fetch_with_fallback("xiaohongshu", attempts)


def _fetch_wechat():
    # 回退链：hotdata -> xxapi -> tianapi(可选) -> 自定义(可选)
    attempts = [("https://w-hotdata.aipromptnav.com/api/hot-data/wxhottopic", "hotdata", {"X-API-Key": HOTDATA_KEY})]
    attempts.append(("https://v2.xxapi.cn/api/wxhot", "xxapi", None))
    wechat_key = os.environ.get("TIANAPI_WECHAT_KEY", os.environ.get("TIANAPI_KEY", "")).strip()
    if wechat_key:
        attempts.append((f"https://apis.tianapi.com/wxhottopic/index?key={wechat_key}", "tianapi", None))
    custom = os.environ.get("HOTSPOT_WECHAT_URL", "").strip()
    if custom:
        attempts.append((custom, "custom", None))
    return _fetch_with_fallback("wechat", attempts)


def _fetch_weibo():
    # 回退链：hotdata -> xxapi -> tianapi(可选) -> 自定义(可选)
    attempts = [("https://w-hotdata.aipromptnav.com/api/hot-data/weibohot", "hotdata", {"X-API-Key": HOTDATA_KEY})]
    attempts.append(("https://v2.xxapi.cn/api/weibohot", "xxapi", None))
    weibo_key = os.environ.get("TIANAPI_WEIBO_KEY", os.environ.get("TIANAPI_KEY", "")).strip()
    if weibo_key:
        attempts.append((f"https://apis.tianapi.com/weibohot/index?key={weibo_key}", "tianapi", None))
    custom = os.environ.get("HOTSPOT_WEIBO_URL", "").strip()
    if custom:
        attempts.append((custom, "custom", None))
    return _fetch_with_fallback("weibo", attempts)


def get_hotspots(force=False, viewed=False):
    now = time.time()
    if not force and _HOTSPOT_CACHE["data"] and (now - _HOTSPOT_CACHE["ts"]) < _HOTSPOT_REFRESH_MINUTES * 60:
        return _HOTSPOT_CACHE["data"]
    # 并发加固：加锁 + 双重检查，避免多线程同时触发重复抓取风暴
    with _cache_lock:
        if not force and _HOTSPOT_CACHE["data"] and (now - _HOTSPOT_CACHE["ts"]) < _HOTSPOT_REFRESH_MINUTES * 60:
            return _HOTSPOT_CACHE["data"]
        platforms = {}
        status = {}
        tasks = [
            ("douyin", _fetch_douyin),
            ("xiaohongshu", _fetch_xhs),
            ("wechat", _fetch_wechat),
            ("weibo", _fetch_weibo),
        ]
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            fut_map = {ex.submit(fn): p for p, fn in tasks}
            for f in concurrent.futures.as_completed(fut_map):
                p = fut_map[f]
                try:
                    items = f.result() or []
                except Exception:
                    items = []
                platforms[p] = items[:14]   # 多取余量，前端过滤后仍可保证 Top10
                status[p] = {
                    "ok": bool(items),
                    "count": len(items),
                    "source": items[0]["source"] if items else "unavailable",
                }
        has_any = any(platforms.values())
        if not has_any and _HOTSPOT_CACHE["data"]:
            data = dict(_HOTSPOT_CACHE["data"])
            data["stale"] = True
            return data
        # 地域聚合：按识别出的 region 统计热度分布，供 3D 地球与「区域关注度」联动
        region_map = {}
        total = 0
        for p, items in platforms.items():
            for it in items:
                total += 1
                r = it.get("region")
                if not r:
                    continue
                entry = region_map.setdefault(
                    r, {"region": r, "lat": it.get("lat"), "lon": it.get("lon"), "count": 0, "platforms": {}, "top": []}
                )
                entry["count"] += 1
                entry["platforms"][p] = entry["platforms"].get(p, 0) + 1
                entry["top"].append(it)
        regions = sorted(region_map.values(), key=lambda e: e["count"], reverse=True)
        for e in regions:
            e["pct"] = round(100 * e["count"] / total) if total else 0
            e["top"].sort(key=lambda x: x.get("rank", 99))
            e["top"] = [
                {
                    "text": t.get("text", ""),
                    "platform": t.get("platform", ""),
                    "heat": t.get("heat", ""),
                    "url": t.get("url", ""),
                    "rank": t.get("rank", 0),
                }
                for t in e["top"][:4]
            ]
            e["platforms"] = sorted(e["platforms"].items(), key=lambda kv: kv[1], reverse=True)
        data = {
            "ok": True,
            "fetchedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "stale": False,
            "refreshMinutes": _HOTSPOT_REFRESH_MINUTES,
            "platforms": platforms,
            "status": status,
            "geo": {"total": total, "regions": regions[:12]},
        }
        _HOTSPOT_CACHE["data"] = data
        _HOTSPOT_CACHE["ts"] = now
        return data


# ── 参考实现搬入 (Phase 1-B)：热点上下文 ACI 注入 ──
PLATFORM_ORDER = ["douyin", "xiaohongshu", "wechat", "weibo"]
PLATFORM_LABELS = {"douyin": "抖音", "xiaohongshu": "小红书", "wechat": "微信热点", "weibo": "微博"}

_HOTSPOT_CONTEXT_TTL = 60 * 60  # 秒：用户查看热点大屏后保留上下文注入的时长
_panel_active_until = 0.0


def note_hotspot_panel_viewed():
    """前端打开热点大屏时调用：激活热点上下文注入（保留 TTL 时长）。"""
    global _panel_active_until
    _panel_active_until = time.time() + _HOTSPOT_CONTEXT_TTL


def get_hotspot_panel_state():
    now = time.time()
    return {"active": now < _panel_active_until, "contextTtlSeconds": int(max(0, _panel_active_until - now))}


def _normalize_search_text(text):
    if not text:
        return ""
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", str(text).lower())


def _hotspot_title(item):
    return str(item.get("title") or item.get("text") or item.get("word") or "").strip()


def _platform_label(platform):
    return PLATFORM_LABELS.get(platform, platform or "热点")


def _extract_keywords(title):
    cleaned = re.sub(r"[^\w\u4e00-\u9fff]+", " ", str(title or "")).strip()
    words = set()
    for part in cleaned.split():
        if re.match(r"^[a-zA-Z0-9]{3,}$", part):
            words.add(part.lower())
    compact = cleaned.replace(" ", "")
    for i in range(len(compact)):
        for ln in range(2, 6):
            if i + ln <= len(compact):
                tok = compact[i : i + ln]
                if re.search(r"[\u4e00-\u9fff]", tok):
                    words.add(tok)
    return list(words)[:24]


def _current_hotspot_items(cache, per_platform=20):
    items = []
    platforms = (cache or {}).get("platforms", {})
    for platform in PLATFORM_ORDER:
        lst = platforms.get(platform) or []
        items.extend([it for it in lst if _hotspot_title(it)][:per_platform])
    return items


def _format_hotspot_lines(items):
    lines = []
    for idx, it in enumerate(items):
        rank = it.get("rank") or idx + 1
        heat = f"（热度 {it['heat']}）" if it.get("heat") else ""
        lines.append(f"{_platform_label(it.get('platform'))} {rank}. {_hotspot_title(it)}{heat}")
    return "\n".join(lines)


def _context_platform_blocks(cache, top=10):
    blocks = []
    platforms = (cache or {}).get("platforms", {})
    for platform in PLATFORM_ORDER:
        lst = [it for it in (platforms.get(platform) or []) if _hotspot_title(it)][:top]
        if not lst:
            continue
        source = lst[0].get("source", "hotspot-api")
        blocks.append(f"当前{_platform_label(platform)}热榜（来源：{source}）：\n{_format_hotspot_lines(lst)}")
    return "\n\n".join(blocks)


def match_hotspots(message, items=None):
    """判断用户消息是否提及当前热点，返回命中列表（含匹配项与关键词）。对齐参考实现 matchHotspots。"""
    if items is None:
        items = _current_hotspot_items(get_hotspots(), 20)
    norm_msg = _normalize_search_text(message)
    if not norm_msg:
        return []
    raw = str(message or "")
    matches = []
    for it in items:
        title = _hotspot_title(it)
        norm_title = _normalize_search_text(title)
        if not norm_title:
            continue
        rank = int(it.get("rank") or 0)
        platform = _platform_label(it.get("platform"))
        rank_ref = rank > 0 and (
            re.search(rf"(热搜|热点|榜单|{platform}).{{0,4}}(第\s*{rank}|{rank}\s*(条|名|位))", raw)
            or (rank == 1 and re.search(rf"(热搜|热点|榜单|{platform}).{{0,4}}(第一|榜一|第\s*1|1\s*(条|名|位))", raw))
        )
        direct = (norm_title in norm_msg) or (len(norm_title) >= 4 and norm_msg in norm_title)
        keywords = _extract_keywords(title)
        hit = sum(1 for k in keywords if _normalize_search_text(k) in norm_msg)
        if direct or rank_ref or hit >= 2:
            matches.append({"item": it, "keywords": keywords[:8], "direct": direct, "rank_ref": bool(rank_ref), "hit": hit})
    return matches[:5]


def build_hotspot_context(message=""):
    """【ACI 热点预判注入】把当前热点榜作为背景上下文注入 system prompt。

    仅在以下情况注入：用户查看过热点大屏（panel active TTL 内），或用户消息命中某热点。
    对齐参考实现 buildHotspotRuntimeContext 的注入门控与措辞。
    """
    cache = get_hotspots()
    if not cache or not cache.get("platforms"):
        return ""
    panel_active = time.time() < _panel_active_until
    items = _current_hotspot_items(cache, 20)
    matches = match_hotspots(message, items) if message else []
    if not panel_active and not matches:
        return ""
    blocks = []
    if panel_active or matches:
        bg = _context_platform_blocks(cache, 10)
        if bg:
            blocks.append(bg)
    match_text = ""
    if matches:
        match_text = f"\n\n用户当前消息可能涉及以下近期热点：\n{_format_hotspot_lines([m['item'] for m in matches])}"
    if not blocks and not match_text:
        return ""
    fetched = cache.get("fetchedAt", "未知")
    header = (
        "## 热点上下文\n"
        "来源：热点大屏，由系统自动采集。发送方：SYSTEM。用途：提供当前环境背景，并非用户请求。\n"
        "以下热点仅作背景参考：不要主动总结，不要将其视为用户消息，也不要仅因此上下文主动向用户回复。\n"
        "仅当用户当前问题/任务/话题与某热点直接相关、或热点含紧急风险/重大变化/高优先级信息时，才主动提及。\n"
        f"采集时间：{fetched}"
    )
    return f"{header}\n\n{chr(10).join(blocks)}{match_text}"


def archive_mentioned_hotspots(message):
    """命中热点自动归档记忆（对齐参考实现 persistMentionedHotspot）。

    仅在用户消息命中某热点时写库；按 hotspot_event_<sha1 12> 去重；best-effort 吞错，
    绝不阻塞/影响主对话流程。依赖 match_hotspots（已与参考实现同构）与 db.upsert_memory_by_mem_id。
    """
    try:
        import hashlib

        from db import upsert_memory_by_mem_id

        cache = get_hotspots()
        if not cache or not cache.get("platforms"):
            return []
        items = _current_hotspot_items(cache, 20)
        matches = match_hotspots(message, items)
        if not matches:
            return []
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        archived = []
        for m in matches:
            it = m["item"]
            platform = it.get("platform") or "hotspot"
            title = _hotspot_title(it)
            key = f"{platform}:{_normalize_search_text(title)}"
            h = hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]
            mem_id = f"hotspot_event_{h}"
            concepts = [title, _platform_label(platform)] + (m.get("keywords") or [])
            seen = set()
            uniq = []
            for c in concepts:
                if c not in seen:
                    seen.add(c)
                    uniq.append(c)
            concepts = uniq[:16]
            detail = "\n".join([
                f"Hotspot source: {it.get('source', '')}",
                f"Platform: {_platform_label(platform)}",
                f"Rank: {it.get('rank', '')}",
                f"Heat: {it.get('heat', '')}",
                f"Link: {it.get('url', '')}",
                f"Trigger message excerpt: {str(message)[:120]}",
                "This is an automatically archived hotspot-event fact (archived when the user mentioned a related hotspot).",
            ])
            upsert_memory_by_mem_id(dict(
                mem_id=mem_id,
                event_type="hotspot_event",
                title=f"Hotspot event: {title}",
                content=f"用户提到热点：{title}",
                detail=detail,
                entities=["SYSTEM"],
                concepts=concepts,
                tags=["hotspot", "hotspot_event", f"platform:{platform}", f"source:{it.get('source', '')}"],
                links=[it.get("url")] if it.get("url") else [],
                salience=3,
                source_ref="hotspot_context",
                timestamp=now,
            ))
            archived.append(mem_id)
        return archived
    except Exception:
        return []
