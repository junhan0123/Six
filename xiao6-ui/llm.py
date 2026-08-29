#!/usr/bin/env python3
"""小6 · Agnes / OpenAI 兼容大模型调用（带重试 + 最小间隔，支持动态配置热重载）"""

import json
import threading
import time
import urllib.error
import urllib.request

import config
import provider_registry
import quota

agnes_lock = threading.Lock()
_agnes_last_call = [0.0]
AGNES_MIN_SPACING = 1.0  # 两次调用最小间隔（秒），降低被限流概率


def _urlopen_with_proxy(req, timeout):
    """根据配置使用代理发送请求；未配置代理则直接请求。

    当代理配置存在但连接被拒绝/代理不可用时，会降级尝试一次直连；
    直连使用调用方传入的原始 timeout，不再硬截断为 8 秒，避免 reasoning 模型
    首 token 时间较长时被误超时。

    注意：urllib 默认会沿用环境变量 HTTPS_PROXY/HTTP_PROXY。为让「直连」名副其实，
    兜底与无代理路径都显式使用空 ProxyHandler，强制绕过任何环境变量代理
    （某些后台运行环境会注入指向死代理的 HTTPS_PROXY，导致「直连」也拿到 10061 拒绝）。
    """
    proxy = getattr(config, "XIAO6_PROXY_URL", "") or ""
    if proxy:
        try:
            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler({"http": proxy, "https": proxy})
            )
            return opener.open(req, timeout=timeout)
        except Exception as proxy_err:
            proxy_msg = str(proxy_err)
            # 代理不通时，强制「真·直连」：显式清空环境变量代理。
            # 重建请求，避免代理尝试已部分消费请求体（POST 场景）。
            try:
                no_proxy = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                direct_req = urllib.request.Request(
                    req.full_url,
                    data=req.data,
                    headers=dict(req.headers),
                    method=req.get_method(),
                )
                return no_proxy.open(direct_req, timeout=timeout)
            except Exception as direct_err:
                raise Exception(
                    f"代理 {proxy} 不可用 ({proxy_msg})，直连也失败 ({direct_err})"
                ) from direct_err
    # 未配置代理：同样强制绕过环境变量代理，确保真正直连
    return urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=timeout)


def _reasoning_param():
    """根据当前配置返回思考模式参数。空字符串表示关闭。"""
    r = (config.AGNES_REASONING or "").strip().lower()
    if r in ("low", "medium", "high"):
        return r
    return None


def _cfg(attr, default=""):
    """按属性名从 config 取值（属性名由 Registry 声明，见 DC-06）。"""
    if not attr:
        return default
    return getattr(config, attr, default) or default


def resolve_provider(provider_id=None):
    """Provider Resolver —— **唯一**的「Provider → 可用连接参数」解析实现。

    输入：provider_id（可为 None / 别名 / 大小写混写）
    输出：ProviderBinding(dict)，字段：
        id, label, kind, privacy_class, auth_required, openai_compatible,
        base_url, api_key, model, capabilities, configured

    选择优先级（DC-01：唯一 Selection authority = config.ACTIVE_LLM）：
        显式入参 > config.ACTIVE_LLM > 默认 agnes
    未知取值由 Registry 归一为默认 Provider，保证主链路不中断。

    云端缺省兜底：llm2 未配置 base/model 时沿用 Agnes 值（保持既有行为完全一致）。
    本地缺省兜底：使用 Registry 的 default_base_url（127.0.0.1 白名单内）。
    """
    pid = provider_registry.normalize_provider_id(provider_id or config.ACTIVE_LLM)
    spec = provider_registry.PROVIDER_SPECS[pid]
    attrs = spec["config_attrs"]

    base = _cfg(attrs.get("base"))
    key = _cfg(attrs.get("key"))
    model = _cfg(attrs.get("model"))

    if spec["kind"] == provider_registry.KIND_LOCAL:
        base = base or spec.get("default_base_url", "")
    elif pid != provider_registry.DEFAULT_PROVIDER_ID:
        # 云端第二供应商未填时，沿用主用 Agnes 的 base/model（与旧 _provider_creds 行为一致）
        base = base or config.AGNES_BASE
        model = model or config.AGNES_MODEL

    return {
        "id": spec["id"],
        "label": spec["label"],
        "kind": spec["kind"],
        "privacy_class": spec["privacy_class"],
        "auth_required": spec["auth_required"],
        "openai_compatible": spec["openai_compatible"],
        "base_url": (base or "").rstrip("/"),
        "api_key": key,
        "model": model,
        "capabilities": dict(spec["capabilities"]),
        # configured：连接参数是否齐备（云端还需 key；本地不需要）
        "configured": bool(base) and bool(model) and (bool(key) or not spec["auth_required"]),
    }


def _provider_creds(provider=None):
    """按供应商名返回 (base_url, api_key, model, supports_reasoning)。

    ⚠ 兼容外壳：签名与返回结构保持不变，内部**委托** resolve_provider()（DC-04 双出口·单真相）。
    新代码请直接使用 resolve_provider()，可拿到 auth_required / privacy_class / capabilities。
    """
    b = resolve_provider(provider)
    return b["base_url"], b["api_key"], b["model"], b["capabilities"].get("reasoning_effort", True)


def agnes_completion(messages, tools=None, stream=False, timeout=60, retries=2, temperature=0.7, reasoning=None, provider=None, auth_required=None):
    """
    调用 LLM。使用 config 模块当前值，支持运行时修改。
    当 AGNES_REASONING 为 low/medium/high 时，会加入 reasoning_effort 参数（OpenAI / 部分兼容端点支持）。
    reasoning 参数可覆盖配置：传入 True/"medium"/"low"/"high" 开启；传入 None 则读配置。

    auth_required：None = 由 Provider Binding 自动推导（云端 True / 本地 False）；
                   显式 True/False 可覆盖。为 False 时不发送 Authorization 头
                   （本地端点无 Key，发 "Bearer " 空头不诚实且可能被拒）。
    """
    _binding = resolve_provider(provider)
    _base = _binding["base_url"]
    _key = _binding["api_key"]
    _model = _binding["model"]
    if auth_required is None:
        auth_required = _binding["auth_required"]
    body = {
        "model": _model,
        "messages": messages,
        "stream": stream,
        "temperature": temperature,
    }
    if tools is not None:
        body["tools"] = tools
        if tools:
            body["tool_choice"] = "auto"

    if reasoning is None:
        reasoning = _reasoning_param()
    elif reasoning is True:
        reasoning = "medium"
    elif isinstance(reasoning, str):
        reasoning = reasoning.strip().lower()
        if reasoning not in ("low", "medium", "high"):
            reasoning = None
    else:
        reasoning = None
    if reasoning:
        body["reasoning_effort"] = reasoning

    data = json.dumps(body).encode("utf-8")
    last_err = None
    est_tokens = quota.estimate_input_tokens(messages, tools)
    quota.wait_if_needed(est_tokens)  # 配额预判：超 RPM/TPM 则阻塞到窗口释放
    for attempt in range(retries + 1):
        with agnes_lock:
            wait = AGNES_MIN_SPACING - (time.time() - _agnes_last_call[0])
            if wait > 0:
                time.sleep(wait)
            _headers = {
                "Content-Type": "application/json",
                "Accept": "text/event-stream" if stream else "application/json",
            }
            if auth_required:
                _headers["Authorization"] = "Bearer " + _key
            req = urllib.request.Request(
                _base + "/chat/completions",
                data=data,
                headers=_headers,
            )
            try:
                resp = _urlopen_with_proxy(req, timeout=timeout)
                _agnes_last_call[0] = time.time()
                quota.record(est_tokens)  # 配额记账：本轮请求成功
                return resp
            except urllib.error.HTTPError as e:
                _agnes_last_call[0] = time.time()
                last_err = e
                print(
                    f"[LLM HTTPError] provider={provider or config.ACTIVE_LLM} attempt={attempt} code={e.code} reason={e.reason}"
                )
                try:
                    err_body = e.read().decode("utf-8", "replace")[:400]
                    print(f"[LLM HTTPError body] {err_body}")
                    # 如果是因为 reasoning_effort 不被支持，则降级重试一次
                    if "reasoning_effort" in err_body and reasoning:
                        print("[LLM] reasoning_effort 不被当前端点支持，本次请求已移除该参数")
                        body.pop("reasoning_effort", None)
                        data = json.dumps(body).encode("utf-8")
                        reasoning = None
                except Exception:
                    pass
                if e.code == 429:
                    # 命中 429 限流：配额模块做指数退避 + 锁心跳（对齐参考实现 quota.js）
                    backoff = quota.on_429()
                    print(f"[LLM] 命中 429 限流，退避 {backoff:.0f}s 并临时降速心跳")
                if e.code in (401, 429, 500, 502, 503, 504):
                    time.sleep(2**attempt * 2)  # 退避 2s / 4s
                    continue
                raise
            except Exception as e:
                _agnes_last_call[0] = time.time()
                last_err = e
                print(
                    f"[LLM Exception] provider={provider or config.ACTIVE_LLM} attempt={attempt} type={type(e).__name__} msg={e}"
                )
                time.sleep(2**attempt * 2)
                continue
    raise last_err
