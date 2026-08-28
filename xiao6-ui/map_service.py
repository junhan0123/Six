"""庄周 · 地图服务（本地坐标工具，纯标准库、离线实现）。

合规说明：本模块不调用任何外部地图 API，也不生成地图图片 / 瓦片，
仅做坐标数学计算（两点直线距离）与内置中国主要城市坐标查询，
避免绘制可能存在的边界错误地图。所有坐标采用 WGS-84。

设计：零外部依赖、零密钥；输入异常或查无结果时优雅降级，绝不抛异常
中断主链路（与 worldcup.py / person_card.py 的防御式风格保持一致）。
"""

import math

# 内置中国主要城市坐标表（WGS-84 经纬度：纬度 lat, 经度 lon）
CITIES = {
    "北京": (39.9042, 116.4074),
    "上海": (31.2304, 121.4737),
    "广州": (23.1291, 113.2644),
    "深圳": (22.5431, 114.0579),
    "杭州": (30.2741, 120.1551),
    "成都": (30.5728, 104.0668),
    "武汉": (30.5928, 114.3055),
    "西安": (34.3416, 108.9398),
    "南京": (32.0603, 118.7969),
    "重庆": (29.5630, 106.5516),
    "天津": (39.3434, 117.3616),
    "苏州": (31.2989, 120.5853),
    "长沙": (28.2282, 112.9388),
    "郑州": (34.7466, 113.6254),
    "青岛": (36.0671, 120.3826),
    "沈阳": (41.8057, 123.4315),
    "大连": (38.9140, 121.6147),
    "厦门": (24.4798, 118.0894),
    "昆明": (25.0389, 102.7183),
    "哈尔滨": (45.8038, 126.5349),
    # 额外补充几个主要城市，全部使用 WGS-84
    "济南": (36.6512, 117.1201),
    "合肥": (31.8206, 117.2272),
    "福州": (26.0745, 119.2965),
    "南昌": (28.6829, 115.8579),
    "贵阳": (26.6477, 106.6302),
    "南宁": (22.8170, 108.3665),
    "兰州": (36.0611, 103.8343),
    "太原": (37.8706, 112.5489),
    "石家庄": (38.0428, 114.5149),
    "乌鲁木齐": (43.8256, 87.6168),
}

# 地名后缀，查无精确匹配时尝试去掉
_SUFFIXES = ("市", "省", "特别行政区", "自治区", "地区", "县")

# 用于切分「A 到 B」「A 和 B」等表达的连词
_SEPARATORS = ["到", "至", "和", "跟", "与", "及", "、", "，"]

_EARTH_RADIUS_KM = 6371.0088


def geocode(query):
    """按名称查询城市坐标。

    入参：query 城市名（可含「市」「省」等后缀）。
    返回：{"name": 键, "lat": 纬度, "lon": 经度} 或查无结果时返回 None。
    """
    try:
        q = (query or "").strip()
        if not q:
            return None
        # 1) 精确匹配
        if q in CITIES:
            lat, lon = CITIES[q]
            return {"name": q, "lat": lat, "lon": lon}
        # 2) 去掉常见后缀再匹配
        stripped = q
        for suf in _SUFFIXES:
            if stripped.endswith(suf) and len(stripped) > len(suf):
                stripped = stripped[: -len(suf)]
                break
        if stripped in CITIES:
            lat, lon = CITIES[stripped]
            return {"name": stripped, "lat": lat, "lon": lon}
        # 3) 包含匹配（如「北京市」「上海市区」）
        for k in CITIES:
            if k in q or q in k:
                lat, lon = CITIES[k]
                return {"name": k, "lat": lat, "lon": lon}
    except Exception:
        pass
    return None


def distance_km(a, b):
    """用 haversine 公式计算两点直线距离（公里）。

    入参：a / b 为含 lat、lon 的字典（如 geocode 的返回值）。
    返回：浮点公里数；任一参数缺失时返回 0.0（不抛异常）。
    """
    try:
        if not a or not b:
            return 0.0
        lat1, lon1 = float(a.get("lat")), float(a.get("lon"))
        lat2, lon2 = float(b.get("lat")), float(b.get("lon"))
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        d_phi = math.radians(lat2 - lat1)
        d_lambda = math.radians(lon2 - lon1)
        h = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
        return 2 * _EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(h)))
    except Exception:
        return 0.0


def _split_places(query):
    """尽力从查询句中切分出起止两地名，返回 (A, B) 或 (None, None)。"""
    try:
        text = (query or "").strip()
        for sep in _SEPARATORS:
            if sep in text:
                parts = text.split(sep, 1)
                a = parts[0].strip()
                b = parts[1].strip()
                # 去掉 b 中可能残留的动词（多远 / 距离 等）
                for noise in ("多远", "距离", "隔多远", "有多远", "多少公里", "几公里"):
                    if b.endswith(noise):
                        b = b[: -len(noise)].strip()
                if a and b:
                    return a, b
    except Exception:
        pass
    return None, None


def map_query(query):
    """解析地图类自然语言查询，返回 (文本回复, 结构化 payload)。

    支持三类意图：
      - 城市间直线距离：「A到B多远/距离/隔多远」
      - 单点位置：「A坐标/在哪/位置/经纬度」
      - 城市列表：「附近城市/有哪些城市/城市列表」
    其它情况返回友好的空结果提示。
    """
    try:
        q = (query or "").strip()
        if not q:
            return ("请输入要查询的城市或两地距离，例如「北京到上海多远」。", {"type": "empty"})

        # 1) 城市列表
        if any(k in q for k in ("城市列表", "有哪些城市", "附近城市", "城市有哪些", "支持的城市")):
            names = list(CITIES.keys())
            return (
                f"目前支持 {len(names)} 个中国主要城市的坐标查询与城市间直线距离计算，例如："
                + "、".join(names[:12])
                + " 等。",
                {"type": "citylist", "cities": names},
            )

        # 2) 两地距离
        a_name, b_name = _split_places(q)
        dist_keywords = ("多远", "距离", "隔多远", "有多远", "公里", "千米")
        if a_name and b_name and any(k in q for k in dist_keywords):
            a = geocode(a_name)
            b = geocode(b_name)
            if a and b:
                km = distance_km(a, b)
                payload = {
                    "type": "distance",
                    "from": {"name": a["name"], "lat": a["lat"], "lon": a["lon"]},
                    "to": {"name": b["name"], "lat": b["lat"], "lon": b["lon"]},
                    "km": round(km, 1),
                }
                return (f"{a['name']} 到 {b['name']} 直线距离约 {km:.0f} km", payload)
            # 有一地查不到，降级提示
            miss = a_name if not a else b_name
            return (
                f"暂未收录「{miss}」的坐标；目前支持中国主要城市坐标查询与城市间直线距离计算。",
                {"type": "empty", "missing": miss},
            )

        # 3) 单点位置
        loc_keywords = ("坐标", "在哪", "位置", "经纬度", "位于")
        if any(k in q for k in loc_keywords):
            place = q
            for k in loc_keywords:
                place = place.replace(k, "")
            place = place.strip("的吗？? ，。、")
            point = geocode(place)
            if point:
                payload = {
                    "type": "location",
                    "point": {"name": point["name"], "lat": point["lat"], "lon": point["lon"]},
                }
                return (
                    f"{point['name']} 的坐标约为：纬度 {point['lat']}，经度 {point['lon']}（WGS-84）。",
                    payload,
                )
            return (
                f"暂未收录「{place}」的坐标；目前支持中国主要城市坐标查询与城市间直线距离计算。",
                {"type": "empty", "missing": place},
            )

        # 4) 兜底
    except Exception:
        pass
    return (
        "暂未收录该地点；目前支持中国主要城市坐标查询与城市间直线距离计算。",
        {"type": "empty"},
    )


def build_map_payload(query):
    """便捷封装：直接返回 map_query 的结构化 payload（忽略文本）。"""
    try:
        _, payload = map_query(query)
        return payload
    except Exception:
        return {"type": "empty"}
