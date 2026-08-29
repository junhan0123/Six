"""小6 · 台风面板（纯标准库实现）。

数据源：中央气象台 nmc.cn 公开接口（JSONP 包裹，无需密钥、大陆直连）。
返回结构为 typhoon_jsons_list_default(({...}))，内部 typhoonList 是二维数组：
  [id, enname, name(中文), intlid(国际编号), rank, power, desc, status("start"活跃/"stop"停编)]
网络或解析失败时退化为「暂无可解析台风」并在 note 说明，绝不抛异常中断主链路。
"""

import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime

from config import HERE

NMC_LIST = "http://typhoon.nmc.cn/weatherservice/typhoon/jsons/list_default"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
CACHE_FILE = os.path.join(HERE, "data", "typhoon_cache.json")
REFRESH_IDLE_SECONDS = 30 * 60
FETCH_TIMEOUT = 15


def _now():
    return datetime.now()


def _fetch(url, timeout=FETCH_TIMEOUT):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, "replace")


def _strip_jsonp(text, func):
    """从 JSONP 包裹中提取 JSON 字符串（兼容 ((...)) 与 (...) 两种写法）。"""
    m = re.search(re.escape(func) + r"\s*\(\s*\(\s*(.*?)\s*\)\s*\)\s*;?\s*$", text, re.S)
    if not m:
        m = re.search(re.escape(func) + r"\s*\(\s*(.*?)\s*\)\s*;?\s*$", text, re.S)
    if not m:
        return text
    return m.group(1).strip()


def _load_cache():
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return None


def _save_cache(data):
    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass


def get_typhoon(force=False):
    """返回台风面板数据；网络或解析失败时优雅降级。"""
    now = _now()
    cached = _load_cache()
    if cached and not force:
        ts = cached.get("fetched_at")
        try:
            dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
            if (now - dt).total_seconds() < REFRESH_IDLE_SECONDS:
                return cached
        except Exception:
            pass

    result = {
        "ok": True,
        "status": "live",
        "fetched_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "source": NMC_LIST,
        "active": [],
        "recent": [],
        "note": "",
    }
    try:
        raw = _fetch(NMC_LIST)
        payload = _strip_jsonp(raw, "typhoon_jsons_list_default")
        obj = json.loads(payload)
        rows = obj.get("typhoonList") or []
        active, recent = [], []
        for r in rows:
            # r 为长度 8 的数组：[id, enname, name, intlid, rank, power, desc, status]
            if not isinstance(r, (list, tuple)) or len(r) < 8:
                continue
            rec = {
                "id": r[0],
                "enname": r[1],
                "name": r[2],
                "intlid": r[3],
                "rank": r[4],
                "power": r[5],
                "desc": r[6],
                "status": r[7],
            }
            if r[7] == "start":
                active.append(rec)
            else:
                recent.append(rec)
        result["active"] = active
        result["recent"] = recent[:10]
        result["note"] = "" if active else "当前西北太平洋无活跃台风"
    except Exception as e:
        result["ok"] = False
        result["status"] = "unavailable"
        result["error"] = str(e)
        result["note"] = "网络不可达或解析失败，已降级"
        if cached:
            cached["note"] = "（使用上次缓存，实时获取失败）"
            return cached

    _save_cache(result)
    return result
