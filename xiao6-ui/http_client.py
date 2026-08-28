#!/usr/bin/env python3
"""庄周 · 通用 HTTP JSON 客户端（TLS 自签降级，无第三方依赖）"""

import json
import ssl
import urllib.request

HOTSPOT_UA = "Mozilla/5.0 (compatible; ZhuangZhou/1.0)"


def http_get_json(url, headers=None, timeout=10):
    def _try(ctx=None):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": HOTSPOT_UA,
                    "Accept": "application/json,text/plain,*/*",
                    **(headers or {}),
                },
            )
            # 强制绕过环境变量 HTTPS_PROXY/HTTP_PROXY，避免后台环境注入死代理
            # （如 Clash 未运行时指向 127.0.0.1:7890 会导致 WinError 10061 并拖慢）。
            handlers = [urllib.request.ProxyHandler({})]
            if ctx is not None:
                handlers.append(urllib.request.HTTPSHandler(context=ctx))
            opener = urllib.request.build_opener(*handlers)
            with opener.open(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8", "replace"))
        except Exception as e:
            print(f"[http] GET 失败 {url}: {e}")
            return None

    # 先正常校验；遇 TLS 拦截代理的自签证书则降级为不校验重试
    return _try(None) or _try(ssl._create_unverified_context())
