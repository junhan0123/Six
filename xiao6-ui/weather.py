"""天气 Provider —— 基于 Open-Meteo（免密钥、免注册，纯标准库 urllib 实现）。

设计要点：
  - 零外部依赖：只用 urllib，不引入 requests / 第三方 SDK，符合后端 stdlib-only 原则。
  - 优雅降级：无网络 / 解析失败时返回 {"ok": False, "error": ...}，绝不抛异常中断对话。
  - 结构化结果：get_weather() 返回 dict，既给 LLM 一段文字摘要（format_weather_text），
    也通过 last_weather() 暂存供聊天流 emit 一个 modal 弹窗事件。
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# WMO 天气代码 →（中文描述, emoji）
WMO_CODES = {
    0: ("晴", "☀️"),
    1: ("大部晴朗", "🌤️"),
    2: ("局部多云", "⛅"),
    3: ("阴", "☁️"),
    45: ("有雾", "🌫️"),
    48: ("雾凇", "🌫️"),
    51: ("小毛雨", "🌦️"),
    53: ("毛毛雨", "🌦️"),
    55: ("大毛雨", "🌦️"),
    56: ("冻毛雨", "🌧️"),
    57: ("冻毛雨", "🌧️"),
    61: ("小雨", "🌧️"),
    63: ("中雨", "🌧️"),
    65: ("大雨", "🌧️"),
    66: ("冻雨", "🌧️"),
    67: ("冻雨", "🌧️"),
    71: ("小雪", "🌨️"),
    73: ("中雪", "🌨️"),
    75: ("大雪", "🌨️"),
    77: ("雪粒", "🌨️"),
    80: ("阵雨", "🌦️"),
    81: ("阵雨", "🌦️"),
    82: ("强阵雨", "⛈️"),
    85: ("阵雪", "🌨️"),
    86: ("强阵雪", "🌨️"),
    95: ("雷阵雨", "⛈️"),
    96: ("雷阵雨伴冰雹", "⛈️"),
    99: ("强雷阵雨伴冰雹", "⛈️"),
}

# 每次请求开始清空，避免跨请求串台
_LAST = None


def last_weather():
    """返回最近一次成功获取的天气结构化结果（供聊天流弹窗使用），无则 None。"""
    return _LAST


def _wmo(code):
    return WMO_CODES.get(int(code) if str(code).isdigit() else -1, ("未知", "🌡️"))


def _http_get_json(url, timeout=12):
    req = urllib.request.Request(url, headers={"User-Agent": "Xiao6/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _geocode(city):
    """城市名 → (纬度, 经度, 展示名)。失败返回 None。"""
    q = urllib.parse.urlencode({"name": city, "count": "1", "language": "zh", "format": "json"})
    data = _http_get_json(f"{GEO_URL}?{q}")
    results = data.get("results") or []
    if not results:
        return None
    r = results[0]
    parts = [r.get("name", "")]
    if r.get("admin1") and r.get("admin1") != r.get("name"):
        parts.append(r["admin1"])
    if r.get("country"):
        parts.append(r["country"])
    display = "，".join(p for p in parts if p)
    return r.get("latitude"), r.get("longitude"), display


def get_weather(city=None, days=1, hours=12):
    """获取天气。返回结构化 dict；任何失败都返回 {"ok": False, "error": ...}。"""
    global _LAST
    _LAST = None
    city = (city or "").strip() or "北京"
    try:
        geo = _geocode(city)
        if not geo:
            return {"ok": False, "error": f"找不到城市：{city}"}
        lat, lon, display = geo

        params = urllib.parse.urlencode(
            {
                "latitude": f"{lat:.4f}",
                "longitude": f"{lon:.4f}",
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
                "daily": "weather_code,temperature_2m_max,temperature_2m_min",
                "hourly": "temperature_2m,weather_code",
                "timezone": "auto",
                "forecast_days": str(max(1, min(days, 7))),
            }
        )
        data = _http_get_json(f"{FORECAST_URL}?{params}")

        cur = data.get("current", {})
        c_code = cur.get("weather_code", 0)
        c_text, c_emoji = _wmo(c_code)

        daily = data.get("daily", {})
        d_code = (daily.get("weather_code") or [c_code])[0]
        d_text, d_emoji = _wmo(d_code)

        # 逐小时：从当前时刻往后取 hours 个
        h_times = data.get("hourly", {}).get("time", [])
        h_temps = data.get("hourly", {}).get("temperature_2m", [])
        h_codes = data.get("hourly", {}).get("weather_code", [])
        now_hh = (cur.get("time") or "")[11:13]
        hourly = []
        started = False
        for i, t in enumerate(h_times):
            hh = t[11:13]
            if hh == now_hh:
                started = True
            if not started:
                continue
            if len(hourly) >= hours:
                break
            ct, ce = _wmo(h_codes[i] if i < len(h_codes) else c_code)
            hourly.append(
                {
                    "time": f"{hh}:00",
                    "temp": round(h_temps[i]) if i < len(h_temps) else None,
                    "code": h_codes[i] if i < len(h_codes) else c_code,
                    "text": ct,
                    "emoji": ce,
                }
            )

        result = {
            "ok": True,
            "city": city,
            "resolved_name": display,
            "latitude": lat,
            "longitude": lon,
            "current": {
                "temp": round(cur.get("temperature_2m")),
                "feels_like": (
                    round(cur.get("apparent_temperature")) if cur.get("apparent_temperature") is not None else None
                ),
                "code": c_code,
                "text": c_text,
                "emoji": c_emoji,
                "humidity": cur.get("relative_humidity_2m"),
                "wind": cur.get("wind_speed_10m"),
                "time": cur.get("time"),
            },
            "today": {
                "code": d_code,
                "text": d_text,
                "emoji": d_emoji,
                "temp_max": round(daily.get("temperature_2m_max")[0]) if daily.get("temperature_2m_max") else None,
                "temp_min": round(daily.get("temperature_2m_min")[0]) if daily.get("temperature_2m_min") else None,
            },
            "hourly": hourly,
        }
        result["summary"] = format_weather_text(result)
        _LAST = result
        return result
    except urllib.error.URLError as e:
        return {"ok": False, "error": f"天气网络请求失败：{e.reason if hasattr(e, 'reason') else e}"}
    except Exception as e:
        return {"ok": False, "error": f"天气获取失败：{e}"}


def format_weather_text(d):
    """把结构化天气压成一段给 LLM 的口语化中文摘要。"""
    if not d.get("ok"):
        return d.get("error", "天气获取失败")
    c = d["current"]
    t = d["today"]
    parts = [
        f"{d['resolved_name']}当前{c['text']}，{c['temp']}°C",
    ]
    if c.get("feels_like") is not None:
        parts.append(f"体感{c['feels_like']}°C")
    if c.get("humidity") is not None:
        parts.append(f"湿度{c['humidity']}%")
    if c.get("wind") is not None:
        parts.append(f"风速{c['wind']}km/h")
    if t.get("temp_max") is not None:
        parts.append(f"今日最高{t['temp_max']}°C、最低{t['temp_min']}°C")
    return "，".join(parts) + "。"


if __name__ == "__main__":
    import sys

    q = sys.argv[1] if len(sys.argv) > 1 else "北京"
    print(json.dumps(get_weather(q), ensure_ascii=False, indent=2))
