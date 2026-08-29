#!/usr/bin/env python3
"""小6 · ACI 预热缓存（参考实现 prefetch 对齐，Phase 2）

后台定时拉取天气/新闻写入 prefetch_cache 表，build_context_prefix 读取注入 system prompt，
模型醒来即用。天气复用 weather.get_weather（open-meteo 免 key），新闻用 HackerNews（免 key）。
全部 best-effort，单项失败不影响其它项与主线。
"""
import json
import os
import threading
import time
import urllib.request

from db import db_conn

_PREFETCH_INTERVAL = int(os.environ.get("PREFETCH_INTERVAL_MIN", "30"))  # 分钟
_WEATHER_CITIES = [c.strip() for c in os.environ.get("PREFETCH_CITIES", "北京").split(",") if c.strip()]
_NEWS_ENABLED = os.environ.get("PREFETCH_NEWS", "1") not in ("0", "false", "False")


def _fetch_hackernews(top=5):
    try:
        req = urllib.request.Request(
            "https://hacker-news.firebaseio.com/v0/topstories.json",
            headers={"User-Agent": "Xiao6/1.0"},
        )
        ids = json.loads(urllib.request.urlopen(req, timeout=10).read())[:top]
        items = []
        for iid in ids:
            try:
                r = urllib.request.Request(
                    f"https://hacker-news.firebaseio.com/v0/item/{iid}.json",
                    headers={"User-Agent": "Xiao6/1.0"},
                )
                it = json.loads(urllib.request.urlopen(r, timeout=10).read())
                if it and it.get("title"):
                    items.append(f"{it['title']}（热度 {it.get('score', '?')}）")
            except Exception:
                continue
        return items
    except Exception:
        return []


def _set_prefetch(source, content, ttl_minutes, tags):
    from datetime import datetime, timedelta

    fetched = time.strftime("%Y-%m-%d %H:%M:%S")
    exp = (datetime.now() + timedelta(minutes=ttl_minutes)).strftime("%Y-%m-%d %H:%M:%S")
    conn = db_conn()
    try:
        conn.execute(
            "INSERT INTO prefetch_cache(source,content,fetched_at,expires_at,tags) VALUES(?,?,?,?,?) "
            "ON CONFLICT(source) DO UPDATE SET content=excluded.content, fetched_at=excluded.fetched_at, "
            "expires_at=excluded.expires_at, tags=excluded.tags",
            (source, content, fetched, exp, json.dumps(tags, ensure_ascii=False)),
        )
        conn.commit()
    finally:
        conn.close()


def run_prefetch():
    """拉取天气 + 新闻写入 prefetch_cache（best-effort，单项失败不影响其他）。返回成功写入的 source 列表。"""
    results = []
    # 天气（复用 weather.get_weather，open-meteo 免 key）
    try:
        import weather

        for city in _WEATHER_CITIES:
            w = weather.get_weather(city, days=1, hours=12)
            if w.get("ok"):
                _set_prefetch(f"weather:{city}", w.get("summary", ""), 60, ["weather", city, "天气"])
                results.append(f"weather:{city}")
    except Exception:
        pass
    # 新闻（HackerNews 免 key）
    if _NEWS_ENABLED:
        try:
            news = _fetch_hackernews(5)
            if news:
                content = "科技热点（HackerNews）：\n" + "\n".join(f"- {t}" for t in news)
                _set_prefetch("news:hackernews", content, 30, ["news", "hackernews", "科技"])
                results.append("news:hackernews")
        except Exception:
            pass
    return results


def get_valid_prefetch():
    """返回所有未过期缓存（expires_at > now）的 list[dict]。"""
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    conn = db_conn()
    try:
        rows = conn.execute(
            "SELECT source,content,fetched_at,tags FROM prefetch_cache WHERE expires_at > ? ORDER BY id",
            (now,),
        ).fetchall()
        out = []
        for source, content, fetched, tags in rows:
            try:
                tg = json.loads(tags) if tags else []
            except Exception:
                tg = []
            out.append({"source": source, "content": content, "fetched_at": fetched, "tags": tg})
        return out
    finally:
        conn.close()


def format_prefetched_items(items):
    """渲染注入文本（对齐参考实现 formatPrefetchedItems）。"""
    if not items:
        return ""
    body = "\n\n".join(
        f"[{it['source']}] (已于 {it['fetched_at']} 预取)\n{it['content']}" for it in items
    )
    return body + "\n\n以上为系统已预取的背景数据，可直接引用，无需再次联网获取。"


def start_prefetch_scheduler(interval_minutes=None):
    """后台线程：每 interval 分钟跑一次 run_prefetch；启动即预热一次。返回线程对象。"""
    interval = interval_minutes or _PREFETCH_INTERVAL

    def loop():
        try:
            run_prefetch()
        except Exception:
            pass
        while True:
            time.sleep(interval * 60)
            try:
                run_prefetch()
            except Exception:
                pass

    t = threading.Thread(target=loop, daemon=True)
    t.start()
    return t
