#!/usr/bin/env python3
"""小6 · 定位 & 天气（全部免 key）"""

import json
import os
import threading
import time

from concurrent.futures import ThreadPoolExecutor, as_completed

from config import GEO_FILE
from http_client import http_get_json

try:
    import zhconv
    def _to_zhcn(s):
        return zhconv.convert(s, 'zh-cn') if s else s
except Exception:  # zhconv 未安装时退化为原样返回（不影响主流程）
    def _to_zhcn(s):
        return s

_cache_lock = threading.Lock()  # 保护下方全局缓存的并发读写
_geo_cache = None
GEO_TTL = 6 * 3600

# 常见城市中英文/拼音 -> 中文映射（解决 wttr.in 音译碎片问题，避免依赖被墙的 nominatim）
_CITY_EN2ZH = {
    "beijing": "北京", "shanghai": "上海", "guangzhou": "广州", "shenzhen": "深圳",
    "chengdu": "成都", "hangzhou": "杭州", "wuhan": "武汉", "xian": "西安", "xi'an": "西安",
    "nanjing": "南京", "chongqing": "重庆", "tianjin": "天津", "suzhou": "苏州",
    "zhengzhou": "郑州", "yenchuang": "郑州", "cheng": "郑州",  # wttr.in 对郑州坐标的常见音译
    "changsha": "长沙", "qingdao": "青岛", "dalian": "大连", "xiamen": "厦门",
    "kunming": "昆明", "harbin": "哈尔滨", "shenyang": "沈阳", "jinan": "济南",
    "fuzhou": "福州", "hefei": "合肥", "nanchang": "南昌", "guiyang": "贵阳",
    "lanzhou": "兰州", "taiyuan": "太原", "shijiazhuang": "石家庄", "haikou": "海口",
    "nanning": "南宁", "urumqi": "乌鲁木齐", "lasa": "拉萨", "yinchuan": "银川",
    "xining": "西宁", "huhehaote": "呼和浩特", "hohhot": "呼和浩特",
    "hong kong": "中国香港", "macao": "中国澳门", "macau": "中国澳门", "taipei": "中国台北",
    "tokyo": "东京", "new york": "纽约", "london": "伦敦", "paris": "巴黎",
    "sydney": "悉尼", "singapore": "新加坡", "seoul": "首尔", "bangkok": "曼谷",
}


def _city_zh(name):
    """把英文/拼音/音译城市名尽量转成中文；无法识别时保留原样。"""
    if not name:
        return name
    key = name.strip().lower().rstrip(",.")
    return _CITY_EN2ZH.get(key) or name


# wttr.in 未提供中文天气描述时（它常回退英文），本地映射到中文
_WX_EN2ZH = {
    "Clear": "晴",
    "Sunny": "晴",
    "Partly cloudy": "局部多云",
    "Cloudy": "多云",
    "Overcast": "阴",
    "Mist": "薄雾",
    "Fog": "雾",
    "Patchy rain possible": "可能有零星小雨",
    "Patchy rain nearby": "附近有零星小雨",
    "Light rain": "小雨",
    "Light rain shower": "小阵雨",
    "Light drizzle": "毛毛雨",
    "Moderate rain": "中雨",
    "Moderate rain at times": "间歇性中雨",
    "Heavy rain": "大雨",
    "Heavy rain at times": "间歇性大雨",
    "Torrential rain": "暴雨",
    "Thundery outbreaks possible": "可能有雷阵雨",
    "Thundery outbreaks in nearby": "附近有雷暴",
    "Patchy light rain": "零星小雨",
    "Patchy light drizzle": "零星毛毛雨",
    "Light snow": "小雪",
    "Moderate snow": "中雪",
    "Heavy snow": "大雪",
    "Blizzard": "暴风雪",
    "Patchy snow possible": "可能有零星小雪",
    "Freezing drizzle": "冻毛毛雨",
    "Ice pellets": "冰粒",
    "Hail": "冰雹",
    "Moderate or heavy rain shower": "中到大阵雨",
    "Thunderstorm": "雷暴",
    "Patchy light rain with thunder": "伴有雷声的零星小雨",
    "Blowing snow": "风吹雪",
    "Patchy sleet possible": "可能有零星雨夹雪",
    "Sleet": "雨夹雪",
}


def _wx_zh(en):
    if not en:
        return ""
    en = en.strip()
    if en in _WX_EN2ZH:
        return _WX_EN2ZH[en]
    # 含 "showers" / "rain" 等组合时尽量兜底
    for k, v in _WX_EN2ZH.items():
        if k.lower() in en.lower():
            return v
    return en  # 实在没映射就保留原文


def _collect_geo():
    ip = http_get_json(
        "http://ip-api.com/json/?fields=status,city,regionName,country,countryCode,lat,lon,timezone,query,isp"
    )
    if not ip or ip.get("status") != "success":
        return None
    city_en = ip.get("city") or ""
    loc = {
        "lat": ip.get("lat"),
        "lon": ip.get("lon"),
        "city": city_en,
        "city_zh": _city_zh(city_en),
        "region": ip.get("regionName"),
        "country": ip.get("country"),
        "countryCode": (ip.get("countryCode") or "").upper(),
        "timezone": ip.get("timezone"),
        "ip": ip.get("query"),
        "isp": ip.get("isp"),
    }
    # 精细地址（可选，失败不影响主流程；nominatim 在国内常被墙，仅 3s 短超时）
    try:
        nom = http_get_json(
            "https://nominatim.openstreetmap.org/reverse?lat=%s&lon=%s&format=json&accept-language=zh"
            % (loc["lat"], loc["lon"]),
            timeout=3,
        )
        if nom and nom.get("address"):
            a = nom["address"]
            loc["district"] = a.get("suburb") or a.get("district") or a.get("county")
            loc["display_name"] = nom.get("display_name")
            # 若 nominatim 返回中文城市名，优先用它
            zh = a.get("city") or a.get("town") or a.get("village") or a.get("county")
            if not zh and nom.get("display_name"):
                zh = nom["display_name"].split(",")[0].strip()
            if zh:
                loc["city_zh"] = zh
    except Exception:
        pass
    # 天气
    weather = None
    try:
        w = http_get_json("https://wttr.in/%s,%s?format=j1&lang=zh" % (loc["lat"], loc["lon"]), timeout=12)
        if w and w.get("current_condition"):
            cur = w["current_condition"][0]
            weather = {
                "temp": cur.get("temp_C"),
                "feels_like": cur.get("FeelsLikeC"),
                "humidity": cur.get("humidity"),
                "condition": _wx_zh(
                    (cur.get("lang_zh") or [{}])[0].get("value") or (cur.get("weatherDesc") or [{}])[0].get("value", "")
                ),
                "wind_kmh": cur.get("windspeedKmph"),
                "wind_dir": cur.get("winddir16Point"),
            }
    except Exception:
        pass
    return {"location": loc, "weather": weather, "collected_at": time.strftime("%Y-%m-%d %H:%M:%S")}


def _geo_cache_fresh(cache):
    """检查内存/文件缓存是否在 TTL 内。"""
    if not cache:
        return False
    collected_at = cache.get("collected_at")
    if not collected_at:
        return False
    try:
        ts = time.mktime(time.strptime(collected_at, "%Y-%m-%d %H:%M:%S"))
        return time.time() - ts < GEO_TTL
    except Exception:
        return False


def get_geo(force=False):
    """返回 {location, weather}；优先缓存，超时或强制时重新采集。"""
    global _geo_cache
    if _geo_cache and not force and _geo_cache_fresh(_geo_cache):
        return _geo_cache
    data = None
    if os.path.exists(GEO_FILE):
        try:
            with open(GEO_FILE, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = None
    if data and not force:
        # 文件缓存同样检查 TTL，避免 city_zh 等字段永久停留在旧值
        collected_at = data.get("collected_at")
        if collected_at:
            try:
                ts = time.mktime(time.strptime(collected_at, "%Y-%m-%d %H:%M:%S"))
                if time.time() - ts < GEO_TTL:
                    with _cache_lock:
                        _geo_cache = data
                    return data
            except Exception:
                pass
    fresh = _collect_geo()
    if fresh:
        with _cache_lock:
            _geo_cache = fresh
        try:
            with open(GEO_FILE, "w", encoding="utf-8") as f:
                json.dump(fresh, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        return fresh
    return data or {"location": None, "weather": None}


def reverse_geocode(lat, lon):
    """坐标→中文地名（浏览器实时定位的反查）。优先 BigDataCloud（免费、含中文 locality），回退 wttr.in。"""
    lat = _to_float(lat)
    lon = _to_float(lon)
    if lat is None or lon is None:
        return None
    result = {"lat": lat, "lon": lon, "city": None, "district": None,
              "region": None, "country": None, "display": None, "weather": None}
    # 1) BigDataCloud 反向地理编码（无需 key，localityLanguage=zh 返回中文）
    try:
        d = http_get_json(
            "https://api.bigdatacloud.net/data/reverse-geocode-client"
            "?latitude=%s&longitude=%s&localityLanguage=zh" % (lat, lon),
            timeout=6,
        )
        if d:
            province = (d.get("principalSubdivision") or "").strip()
            city = (d.get("city") or "").strip()
            locality = (d.get("locality") or "").strip()
            country = (d.get("countryName") or "").strip()
            result["region"] = _to_zhcn(province) or None
            result["city"] = _to_zhcn(city) or (_to_zhcn(locality) or None)
            result["district"] = _to_zhcn(locality) or None
            result["country"] = _to_zhcn(country) or None
            # 组装展示名：去重、按 省·市·县 顺序（繁→简归一）
            parts = []
            seen = set()
            for p in (province, city, locality):
                p = _to_zhcn(p.strip()) if p else ""
                if p and p not in seen:
                    seen.add(p)
                    parts.append(p)
            if not parts and country:
                parts = [_to_zhcn(country)]
            result["display"] = "·".join(parts) if parts else None
    except Exception:
        pass
    # 2) 回退：wttr.in 最近区域 + 实时天气（国内可达，单次请求复用）
    try:
        w = http_get_json("https://wttr.in/%s,%s?format=j1&lang=zh" % (lat, lon), timeout=10)
        if w:
            if not result["display"] and w.get("nearest_area"):
                a = w["nearest_area"][0]
                area = (((a.get("areaName") or [{}])[0] or {}).get("value")) or ""
                region = (((a.get("region") or [{}])[0] or {}).get("value")) or ""
                city_zh = _city_zh(area) or area
                result["city"] = result["city"] or (city_zh or None)
                result["region"] = result["region"] or (region or None)
                parts = [p for p in (region, city_zh) if p]
                result["display"] = "·".join(parts) if parts else (city_zh or None)
            if w.get("current_condition"):
                cur = w["current_condition"][0]
                result["weather"] = {
                    "temp": cur.get("temp_C"),
                    "condition": _wx_zh(
                        (cur.get("lang_zh") or [{}])[0].get("value")
                        or (cur.get("weatherDesc") or [{}])[0].get("value", "")
                    ),
                }
    except Exception:
        pass
    if not result["display"]:
        return None
    return result


def build_geo_block():
    """注入 system prompt 的定位信息块。"""
    g = _geo_cache or {}
    loc = g.get("location")
    if not loc or loc.get("lat") is None:
        return ""
    parts = []
    place = "，".join(filter(None, [loc.get("district"), loc.get("city"), loc.get("region"), loc.get("country")]))
    if place:
        parts.append("位置：" + place)
    if loc.get("lat") is not None:
        parts.append("坐标：%s, %s" % (loc["lat"], loc["lon"]))
    if loc.get("timezone"):
        parts.append("时区：" + loc["timezone"])
    w = g.get("weather")
    if w and w.get("condition"):
        parts.append("天气：%s %s°C（体感 %s°C）" % (w["condition"], w.get("temp"), w.get("feels_like")))
    if not parts:
        return ""
    return "\n【定位信息】\n" + "\n".join("  - " + p for p in parts) + "\n"


# ---------- 天气面板数据（Python 后端代理） ----------
_WEATHER_REFRESH_MINUTES = 30
_WEATHER_CACHE = {"data": None, "ts": 0, "key": ""}


def _to_int(v):
    try:
        if v is None or v == "":
            return None
        return int(float(v))
    except Exception:
        return None


def _to_float(v):
    try:
        if v is None or v == "":
            return None
        return float(v)
    except Exception:
        return None


def _weather_code_zh(code):
    try:
        n = int(code)
    except Exception:
        n = 0
    if n in (0, 1):
        return "晴"
    if n == 2:
        return "多云"
    if n == 3:
        return "阴"
    if n in (45, 48):
        return "雾"
    if n in (51, 53, 55):
        return "细雨"
    if n in (56, 57, 66, 67):
        return "冻雨"
    if n in (61, 80):
        return "小雨"
    if n in (63, 81):
        return "中雨"
    if n in (65, 82):
        return "大雨"
    if n in (71, 77, 85):
        return "小雪"
    if n == 73:
        return "中雪"
    if n in (75, 86):
        return "大雪"
    if n == 95:
        return "雷暴"
    if n in (96, 99):
        return "雷雨"
    return "多云"


def _day_label(date_str, index, mode="compact"):
    if index == 0:
        return "今天"
    if index == 1:
        return "明天"
    if index == 2 and mode == "compact":
        return "后天"
    try:
        wd = time.strptime(date_str, "%Y-%m-%d").tm_wday
        return ["周日", "周一", "周二", "周三", "周四", "周五", "周六"][wd]
    except Exception:
        return date_str or ""


def get_weather(city=None, mode=None, force=False):
    """返回天气面板数据：{ card, forecast[] }。"""
    import re
    import urllib.parse

    global _WEATHER_CACHE
    _COORD_RE = re.compile(r"^\s*-?\d+(\.\d+)?\s*,\s*-?\d+(\.\d+)?\s*$")
    # 保存用户前端显式输入的城市名（非坐标串）。后续不能让它被 IP 定位缓存的中文名覆盖。
    explicit_city = city.strip() if (city and not _COORD_RE.match(city)) else None
    now = time.time()
    g = get_geo()
    loc = (g or {}).get("location") or {}
    # 查询 key：自动定位用 IP 库英文城市或坐标；手动/坐标传入时保持原值
    if not city:
        city = loc.get("city") or (
            "%s,%s" % (loc.get("lat"), loc.get("lon")) if loc.get("lat") is not None else None
        )
    if not city:
        city = "Beijing"
    if mode is None:
        mode = "compact"
    # 中文显示名：优先用定位缓存中的中文名，其次用本地映射表翻译 wttr 返回的区域名
    zh_city = loc.get("city_zh") or loc.get("district")
    key = "%s:%s" % (mode, city)

    with _cache_lock:
        if not force and _WEATHER_CACHE["key"] == key and _WEATHER_CACHE["data"]:
            if now - _WEATHER_CACHE["ts"] < _WEATHER_REFRESH_MINUTES * 60:
                return _WEATHER_CACHE["data"]

    # 坐标形式（lat,lon）必须原样拼进 URL，quote 会把逗号转义成 %2C 导致 wttr.in 退化为 IP 定位
    query_lat = _to_float(loc.get("lat"))
    query_lon = _to_float(loc.get("lon"))
    if _COORD_RE.match(city):
        wttr_url = "https://wttr.in/%s?format=j1&lang=zh" % city
        parts = [p.strip() for p in city.split(",")]
        query_lat = _to_float(parts[0]) or query_lat
        query_lon = _to_float(parts[1]) or query_lon
    else:
        wttr_url = "https://wttr.in/%s?format=j1&lang=zh" % urllib.parse.quote(city)

    # 用户显式指定城市名时，必须先拉 wttr 拿到真实坐标与区域名，再用该坐标拉 open-meteo。
    # 否则 IP 定位缓存的坐标/中文名会覆盖用户选择（如设置"民权县"却显示"郑州"）。
    results = {}
    if explicit_city:
        data = http_get_json(wttr_url, timeout=8)
        if not data or not data.get("current_condition"):
            if _WEATHER_CACHE["data"]:
                d = dict(_WEATHER_CACHE["data"])
                d["stale"] = True
                return d
            return {
                "ok": False,
                "error": "weather fetch failed",
                "city": city,
                "refreshMinutes": _WEATHER_REFRESH_MINUTES,
                "card": None,
                "forecast": [],
            }
        area = (data.get("nearest_area") or [{}])[0]
        area_name = (((area.get("areaName") or [{}])[0] or {}).get("value")) if area else None
        # wttr 返回的坐标通常比 IP 定位更贴近用户指定的城市
        query_lat = _to_float(area.get("latitude") if area else None) or query_lat
        query_lon = _to_float(area.get("longitude") if area else None) or query_lon
        # 显示名必须优先使用用户指定的城市名，不能被 IP 定位缓存覆盖
        display_city = _city_zh(explicit_city) or explicit_city
        results["wttr"] = data
    else:
        display_city = zh_city or _city_zh(area_name) or _city_zh(city) or area_name or city

    # open-meteo（空气质量/逐小时/7天预报）
    om_urls = {}
    if query_lat is not None and query_lon is not None:
        om_urls["aq"] = (
            "https://air-quality-api.open-meteo.com/v1/air-quality"
            "?latitude=%s&longitude=%s&current=us_aqi,pm2_5"
            "&hourly=pm2_5&timezone=auto" % (query_lat, query_lon)
        )
        om_urls["hourly"] = (
            "https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s"
            "&hourly=temperature_2m&forecast_days=1&timezone=auto" % (query_lat, query_lon)
        )
        # 统一拉取 7 天 daily；compact 与 week 仅切片长度不同，避免两家 provider 预报不一致
        om_urls["daily"] = (
            "https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s"
            "&daily=weather_code,temperature_2m_max,temperature_2m_min"
            "&forecast_days=7&timezone=auto" % (query_lat, query_lon)
        )

    if explicit_city:
        if om_urls:
            with ThreadPoolExecutor(max_workers=3) as pool:
                future_to_key = {
                    pool.submit(http_get_json, u, timeout=5): k
                    for k, u in om_urls.items()
                }
                for fut in as_completed(future_to_key):
                    key = future_to_key[fut]
                    try:
                        results[key] = fut.result()
                    except Exception:
                        results[key] = None
    else:
        all_urls = {"wttr": wttr_url, **om_urls}
        with ThreadPoolExecutor(max_workers=4) as pool:
            future_to_key = {
                pool.submit(http_get_json, u, timeout=(8 if k == "wttr" else 5)): k
                for k, u in all_urls.items()
            }
            for fut in as_completed(future_to_key):
                key = future_to_key[fut]
                try:
                    results[key] = fut.result()
                except Exception:
                    results[key] = None

        data = results.get("wttr")
        if not data or not data.get("current_condition"):
            if _WEATHER_CACHE["data"]:
                d = dict(_WEATHER_CACHE["data"])
                d["stale"] = True
                return d
            return {
                "ok": False,
                "error": "weather fetch failed",
                "city": city,
                "refreshMinutes": _WEATHER_REFRESH_MINUTES,
                "card": None,
                "forecast": [],
            }
        area = (data.get("nearest_area") or [{}])[0]
        area_name = (((area.get("areaName") or [{}])[0] or {}).get("value")) if area else None
        display_city = zh_city or _city_zh(area_name) or _city_zh(city) or area_name or city

    cur = data["current_condition"][0]
    desc = _wx_zh(
        ((cur.get("lang_zh") or [{}])[0] or {}).get("value") or (cur.get("weatherDesc") or [{}])[0].get("value", "")
    )
    temp = _to_int(cur.get("temp_C"))
    feels = _to_int(cur.get("FeelsLikeC"))
    humidity = _to_int(cur.get("humidity"))
    wind_kmh = _to_int(cur.get("windspeedKmph"))
    wind_dir = cur.get("winddir16Point") or ""
    vis = _to_int(cur.get("visibility"))
    today = (data.get("weather") or [{}])[0]
    high = _to_int(today.get("maxtempC"))
    low = _to_int(today.get("mintempC"))

    # 坐标优先 wttr 解析，回退传入/定位坐标
    lat = _to_float(area.get("latitude") if area else None) or query_lat
    lon = _to_float(area.get("longitude") if area else None) or query_lon

    aq = results.get("aq")
    om_hourly = results.get("hourly")
    daily_data = results.get("daily")
    aqi = None
    pm25 = None
    hourly_temps = []
    if aq and aq.get("current"):
        aqi = _to_int(aq["current"].get("us_aqi"))
        pm25 = _to_int(aq["current"].get("pm2_5"))
    if om_hourly:
        hod = om_hourly.get("hourly") or {}
        htimes = hod.get("time") or []
        htemps = hod.get("temperature_2m") or []
        for i in range(min(24, len(htimes))):
            hh = htimes[i].split("T")[-1] if "T" in htimes[i] else htimes[i]
            hourly_temps.append({"t": hh[:5], "temp": _to_int(htemps[i])})

    # 统一 forecast 源：优先 open-meteo daily（ compact 取 3 天，week 取 7 天）
    forecast = []
    if daily_data:
        daily = daily_data.get("daily") or {}
        times = daily.get("time") or []
        codes = daily.get("weather_code") or []
        hi = daily.get("temperature_2m_max") or []
        lo = daily.get("temperature_2m_min") or []
        limit = 3 if mode == "compact" else 7
        for i in range(min(limit, len(times))):
            forecast.append(
                {
                    "day": _day_label(times[i], i, mode),
                    "condition": _weather_code_zh(codes[i] if i < len(codes) else 0),
                    "high": _to_int(hi[i] if i < len(hi) else None),
                    "low": _to_int(lo[i] if i < len(lo) else None),
                }
            )

    # open-meteo 不可达/无数据：回退到 wttr.in 自带的多天数据
    if not forecast:
        try:
            limit = 3 if mode == "compact" else 7
            for i, d in enumerate((data.get("weather") or [])[:limit]):
                h4 = (d.get("hourly") or [{}])[4] or {}
                c = _wx_zh(
                    (h4.get("lang_zh", [{}])[0].get("value") if h4.get("lang_zh") else None)
                    or h4.get("weatherDesc", [{}])[0].get("value", "")
                )
                forecast.append(
                    {
                        "day": _day_label(d.get("date", ""), i, mode),
                        "condition": c,
                        "high": _to_int(d.get("maxtempC")),
                        "low": _to_int(d.get("mintempC")),
                    }
                )
        except Exception:
            pass

    # 统一左侧当前卡片与今日预报：open-meteo 可用时，让大卡片的条件/高低温与 forecast[0]（今天）一致，
    # 避免同一面板里"当前晴、今天雷雨"的左右互搏。当前温度/体感/湿度/风/能见度等仍保留 wttr.in 实况。
    if forecast:
        today_f = forecast[0]
        if today_f.get("condition"):
            desc = today_f["condition"]
        if today_f.get("high") is not None:
            high = today_f["high"]
        if today_f.get("low") is not None:
            low = today_f["low"]

    # 生活指数（基于已有字段简单推导）
    rain = any(k in desc for k in ("雨", "雪", "雷", "雹", "雾"))
    if temp >= 28:
        cloth = "炎热 · 短袖清凉"
    elif temp >= 20:
        cloth = "舒适 · 短袖为主"
    elif temp >= 10:
        cloth = "微凉 · 长袖外套"
    elif temp >= 0:
        cloth = "寒冷 · 厚外套"
    else:
        cloth = "严寒 · 羽绒保暖"
    sport = "不宜室外" if rain else "适宜运动"
    carwash = "不宜洗车" if rain else "适宜洗车"
    life_index = [
        {"name": "穿衣", "val": cloth},
        {"name": "运动", "val": sport},
        {"name": "洗车", "val": carwash},
    ]

    card = {
        "variant": "week" if mode == "week" and len(forecast) >= 7 else "compact",
        "city": display_city,
        "temp": temp,
        "condition": desc,
        "feel": feels,
        "high": high,
        "low": low,
        "humidity": humidity,
        "wind": ("%s %s km/h" % (wind_dir, wind_kmh)) if wind_dir else ("%s km/h" % wind_kmh),
        "visibility": vis,
        "wind_dir": wind_dir,
        "wind_kmh": wind_kmh,
        "aqi": aqi,
        "pm25": pm25,
        "hourly": hourly_temps,
        "lifeIndex": life_index,
    }
    result = {
        "ok": True,
        "fetchedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "stale": False,
        "refreshMinutes": _WEATHER_REFRESH_MINUTES,
        "city": display_city,
        "mode": mode,
        "weekLimited": (mode == "week" and len(forecast) < 7),
        "card": card,
        "forecast": forecast,
    }
    with _cache_lock:
        _WEATHER_CACHE["data"] = result
        _WEATHER_CACHE["ts"] = now
        _WEATHER_CACHE["key"] = key
    return result
