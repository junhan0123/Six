#!/usr/bin/env python3
"""庄周 · 主动智能（D 期）：TICK 心跳 + 预判注入 + 主动推送（SSE）

Phase 3：心跳由固定 15s 升级为动态间隔（对齐参考实现 consciousness-loop 简化版）：
- 有到期提醒 → 立即（0s）
- 命中限流(429) → 锁定 10 分钟
- 启动唤醒期 → 前 N 次 10s 紧凑探索
- 否则 → 可配置基础间隔（默认 30s，比 15s 省资源且单用户足够）
"""

import json
import os
import re
import threading
import time
from datetime import datetime

from db import db_conn
import config as _config
# Phase 9 B1/B2/B3：薄决策层 + 通知策略（无副作用 / 无第二 Runtime）
import proactive_config as _pc
import proactive_engine as _pe

SUBSCRIBERS: list = []  # 当前在线的 SSE 订阅者（每个是一个 queue.Queue）
SUBSCRIBERS_LOCK = threading.Lock()
TICK_BASE_INTERVAL = int(os.environ.get("TICK_INTERVAL", "30"))  # 基础心跳间隔（秒），可配置
TICK_AWAKENING = int(os.environ.get("TICK_AWAKENING", "10"))  # 启动后探索 tick 次数
TICK_ADAPTIVE = os.environ.get("TICK_ADAPTIVE", "true").lower() in ("1", "true", "yes")  # 自适应心跳开关
_RATE_LIMIT_SECONDS = 600  # 429 后锁定时长（秒）
_RATE_LIMIT_UNTIL = 0  # 限流锁（时间戳）
_WEEK = "一二三四五六日"

# ── Phase D-3：哨兵 + 抢占插队（对齐参考实现 600s abort + 优先级队列插队）──
TICK_SENTINEL_GRACE = int(os.environ.get("TICK_SENTINEL_GRACE", "60"))  # 单轮最长允许耗时（秒），超时判定卡死
_TICK_ROUND_START = 0.0          # 当前 tick 轮开始时间戳（0 表示空闲）
_TICK_STUCK = False              # 哨兵是否已判定卡死
_TICK_SENTINEL_STARTED = False
_TICK_WAKE = threading.Event()   # 抢占插队：立即唤醒主循环
_TICK_QUEUE = []                 # 抢占插队的即时任务队列 [{"kind": "hotspot"|"weather"|"all"|...}]
_TICK_QUEUE_LOCK = threading.Lock()

# ── Phase D-2：自主行为调度（舆情 / 天气 / 异常检测）──
# 行为按各自间隔触发；TICK 主循环仍保持 30s 紧凑心跳（到期提醒即时响应），
# 网络取数仅在各自间隔到期时进行，避免空转刷屏与无谓请求。
HOTSPOT_INTERVAL = int(os.environ.get("TICK_HOTSPOT_INTERVAL", "300"))   # 舆情扫描：5 分钟
WEATHER_INTERVAL = int(os.environ.get("TICK_WEATHER_INTERVAL", "900"))   # 天气更新：15 分钟

_PLAT_LABELS = {"douyin": "抖音", "xiaohongshu": "小红书", "wechat": "微信热点", "weibo": "微博"}


def _plat_label(p):
    return _PLAT_LABELS.get(p, p or "")


def _meta_get(key, default=None):
    """读 meta 表（键不存在返回 default），异常静默兜底。"""
    try:
        conn = db_conn()
        row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        conn.close()
        return row[0] if row else default
    except Exception:
        return default


def _meta_set(key, value):
    """写 meta 表（幂等 upsert），异常静默兜底。"""
    try:
        conn = db_conn()
        conn.execute(
            "INSERT INTO meta(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def _load_ts(key):
    v = _meta_get(key)
    try:
        return float(v) if v else 0.0
    except Exception:
        return 0.0


def _save_ts(key, t):
    _meta_set(key, str(t))


def set_rate_limited(seconds=None):
    """被 llm.py 在命中 429 时调用，临时拉长心跳（避免持续撞限流）。"""
    global _RATE_LIMIT_UNTIL
    _RATE_LIMIT_UNTIL = time.time() + (seconds or _RATE_LIMIT_SECONDS)


def is_rate_limited():
    global _RATE_LIMIT_UNTIL
    if _RATE_LIMIT_UNTIL and time.time() >= _RATE_LIMIT_UNTIL:
        _RATE_LIMIT_UNTIL = 0
        return False
    return _RATE_LIMIT_UNTIL > 0


def mark_user_activity():
    """用户发消息时调用：记录最近活跃时间戳，供自适应心跳调节间隔。"""
    _save_ts("last_user_activity", time.time())


def _has_due_reminder():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = db_conn()
    try:
        n = conn.execute(
            "SELECT COUNT(*) FROM reminders WHERE done=0 AND due_ts IS NOT NULL AND due_ts <= ?",
            (now,),
        ).fetchone()[0]
        return n > 0
    finally:
        conn.close()


_awakening_left = {"n": TICK_AWAKENING}


def _next_interval():
    """动态计算下次心跳间隔（秒）。"""
    if _has_due_reminder():
        return 0  # 有到期提醒立即处理
    if is_rate_limited():
        return _RATE_LIMIT_SECONDS
    if _awakening_left["n"] > 0:
        _awakening_left["n"] -= 1
        return 10  # 唤醒期紧凑探索
    # —— 自适应心跳：依据用户近期活跃度动态调节间隔（省资源 + 及时响应）——
    if TICK_ADAPTIVE:
        idle = time.time() - _load_ts("last_user_activity")
        if idle < 60:
            return 10   # 用户刚活跃：紧凑，便于即时上下文续接
        if idle < 300:
            return 20   # 近期活跃：中等
        # 长时间无互动：回落到基础间隔，避免空转刷屏
    return TICK_BASE_INTERVAL


def _tick_should_abort():
    """哨兵协作标志：单轮是否已被判定卡死。各 scanner 调用以尽早退出本轮。"""
    return _TICK_STUCK


def request_immediate_scan(kind="all"):
    """抢占插队：把一次即时扫描任务插入队列并立即唤醒心跳（对齐参考实现优先级队列插队）。

    kind 取值：hotspot / weather / rules / prefetch / reminders / all
    """
    with _TICK_QUEUE_LOCK:
        _TICK_QUEUE.append({"kind": kind})
    _TICK_WAKE.set()
    print(f"[TICK] 抢占插队请求：{kind}")


def _drain_immediate():
    """取出并清空即时任务队列，返回任务列表。"""
    with _TICK_QUEUE_LOCK:
        items = list(_TICK_QUEUE)
        _TICK_QUEUE.clear()
    return items


def _tick_sentinel():
    """哨兵线程：监测单轮是否卡死，超时则标记并告警。

    Python 无法强杀线程，故采用协作式降级——标记 _TICK_STUCK 后，本轮机扫描会尽快收尾，
    下一轮重置标志恢复正常（对齐参考实现 600s abort 的「单轮卡死强杀」意图）。
    """
    global _TICK_STUCK
    while True:
        try:
            time.sleep(5)
            if _TICK_ROUND_START and not _TICK_STUCK:
                elapsed = time.time() - _TICK_ROUND_START
                if elapsed > TICK_SENTINEL_GRACE:
                    _TICK_STUCK = True
                    print(
                        f"[TICK 哨兵] 警告：单轮已运行 {int(elapsed)}s 超过 {TICK_SENTINEL_GRACE}s 阈值，"
                        f"判定卡死并降级跳过本轮剩余重型扫描"
                    )
                    try:
                        push_proactive("system", "⚠️ 系统自检：TICK 单轮超时，已降级跳过本轮剩余重型扫描，下一轮自动恢复。", importance="critical")
                    except Exception:
                        pass
        except Exception:
            continue


def _run_immediate(kind, now):
    """执行抢占插队的即时扫描。force=True 无视间隔限制。"""
    try:
        if kind in ("reminders", "all"):
            conn = db_conn()
            due = conn.execute(
                "SELECT id,content FROM reminders WHERE done=0 AND due_ts IS NOT NULL AND due_ts <= ?",
                (now.strftime("%Y-%m-%d %H:%M:%S"),),
            ).fetchall()
            for rid, content in due:
                conn.execute("UPDATE reminders SET done=1 WHERE id=?", (rid,))
                push_proactive("reminder", "⏰ 提醒：" + content)
            conn.commit()
            conn.close()
        if kind in ("hotspot", "all"):
            _scan_hotspots(now, force=True)
        if kind in ("weather", "all"):
            _scan_weather(now, force=True)
        if kind in ("rules", "all"):
            _check_rules(now)
        if kind in ("prefetch", "all"):
            _check_prefetch(now)
    except Exception:
        pass


def _use_eventbus():
    try:
        from eventbus import enabled

        return enabled()
    except Exception:
        return False


def _dispatch_sse(event):
    """把一条 SSE 事件推给所有在线连接。

    FEATURE_EVENTBUS=true：经 EventBus 发布（zz.sse 主题统一扇出）；
    false / 异常：回退旧的 SUBSCRIBERS 全局队列直发（兼容性，§1.6）。
    """
    if _use_eventbus():
        try:
            from eventbus import publish_system

            publish_system("proactive", event, source="proactive")
            return
        except Exception as e:
            print(f"[proactive] EventBus 推送失败，回退 SUBSCRIBERS: {e}")
    with SUBSCRIBERS_LOCK:
        for q in SUBSCRIBERS:
            try:
                q.put(event)
            except Exception:
                pass


def push_proactive(kind, content, importance=None):
    """把一条主动消息推送给所有在线客户端，并落库 pending（离线后重看）。

    Phase 9 B2：经 NotificationPolicy 裁决（DND / quiet hours / importance / 类型白名单）。
    - 被抑制（如 DND 开启且非 critical）→ 不落库、不推送（用户已选择免打扰）。
    - critical 永远突破 DND / quiet hours。
    importance 缺省时按 kind 默认映射（见 proactive_config.kind_importance）。
    """
    imp = importance or _pc.kind_importance(kind)
    try:
        if not _pc.policy.should_deliver(kind, imp):
            return
    except Exception:
        pass  # 决议失败不阻断：兜底按可投递处理
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        conn = db_conn()
        conn.execute("INSERT INTO pending_proactive(kind,content,ts,shown) VALUES(?,?,?,0)", (kind, content, ts))
        conn.commit()
        conn.close()
    except Exception:
        pass
    _dispatch_sse({"xiao6_event": "proactive", "kind": kind, "content": content, "ts": ts, "importance": imp})


def flush_pending(ts_queue):
    """新客户端连接时，把尚未展示的 pending 主动消息推给它。"""
    try:
        conn = db_conn()
        rows = conn.execute("SELECT id,kind,content,ts FROM pending_proactive WHERE shown=0 ORDER BY id ASC").fetchall()
        for rid, kind, content, ts in rows:
            ts_queue.put({"xiao6_event": "proactive", "kind": kind, "content": content, "ts": ts})
            conn.execute("UPDATE pending_proactive SET shown=1 WHERE id=?", (rid,))
        conn.commit()
        conn.close()
    except Exception:
        pass


def make_daily_briefing():
    now = datetime.now()
    date = now.strftime("%Y年%m月%d日 星期") + _WEEK[now.weekday()]
    conn = db_conn()
    rem = conn.execute("SELECT COUNT(*) FROM reminders WHERE done=0").fetchone()[0]
    notes = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    conn.close()
    parts = [f"老板早，{date}。"]
    parts.append(f"今天有 {rem} 条待提醒事项。" if rem else "今天没有待提醒事项。")
    if notes:
        parts.append(f"记忆里存了 {notes} 条笔记。")
    # Phase 3：今日到期目标
    try:
        import goals

        today = now.strftime("%Y-%m-%d")
        due_today = [g for g in goals.list_active_goals(limit=20) if g.due_date and g.due_date[:10] == today]
        if due_today:
            parts.append(
                "今日到期目标："
                + "、".join(f"#{g.id} {g.title}（进度 {g.progress}%）" for g in due_today)
                + "。"
            )
    except Exception:
        pass
    parts.append("需要我做什么，随时说。")
    # Phase 4-C V2：今日建议段（停滞 / 临近目标），关闭 Flag 则跳过
    try:
        if getattr(_config, "FEATURE_PROACTIVE_V2", False):
            sugg = collect_today_suggestions()
            if sugg:
                parts.append("今日建议：" + "；".join(sugg))
    except Exception:
        pass
    return "".join(parts)


def tick_loop():
    global _TICK_SENTINEL_STARTED
    if not _TICK_SENTINEL_STARTED:
        _TICK_SENTINEL_STARTED = True
        threading.Thread(target=_tick_sentinel, daemon=True).start()
    while True:
        try:
            interval = _next_interval()
            if interval > 0:
                # 抢占插队：等待期间若被 request_immediate_scan 唤醒则提前结束等待
                _TICK_WAKE.wait(timeout=interval)
            _TICK_WAKE.clear()
            _tick_once()
        except Exception:
            time.sleep(TICK_BASE_INTERVAL)


def _tick_once():
    global _TICK_ROUND_START, _TICK_STUCK
    _TICK_ROUND_START = time.time()  # 哨兵：标记本轮开始
    now = datetime.now()
    conn = db_conn()
    due = conn.execute(
        "SELECT id,content FROM reminders WHERE done=0 AND due_ts IS NOT NULL AND due_ts <= ?",
        (now.strftime("%Y-%m-%d %H:%M:%S"),),
    ).fetchall()
    for rid, content in due:
        if _tick_should_abort():  # 哨兵已判定卡死，尽快收尾
            break
        conn.execute("UPDATE reminders SET done=1 WHERE id=?", (rid,))
        push_proactive("reminder", "⏰ 提醒：" + content)
    conn.commit()
    conn.close()
    # ── 自主行为：舆情扫描 / 天气更新 / 异常检测（按各自间隔触发）──
    if not _tick_should_abort():
        snap = _scan_hotspots(now)
    else:
        snap = None
    if not _tick_should_abort():
        _scan_weather(now)
    if not _tick_should_abort():
        _scan_anomaly(now, snap)
    if not _tick_should_abort():
        _check_rules(now)
    if not _tick_should_abort():
        _check_prefetch(now)
    if not _tick_should_abort():
        _check_goal_deadlines()
    # ── Phase 4-C V2：主动智能增强（目标停滞建议 / 周小结），关闭 Flag 即跳过 ──
    if getattr(_config, "FEATURE_PROACTIVE_V2", False):
        # 引擎激活（非 off）时，停滞目标交由 ProactiveEngine 统一决策，避免与规则通知重复打扰
        _engine_active = _pc.feature_proactive_engine() and _pc.suggestion_mode() != "off"
        if not _engine_active:
            if not _tick_should_abort():
                _check_goal_stalled()
        if not _tick_should_abort():
            _maybe_weekly_review()
    # ── Phase 9 B1/B3：Proactive Engine 扫描（停滞目标信号 → 决策 → 落地）+ LONG_RUNNING 看门狗 ──
    if _pc.feature_proactive_engine():
        if not _tick_should_abort():
            _proactive_scan(now)
        if not _tick_should_abort():
            _check_long_running(now)
    # ── Phase 28：Self Improvement Advisor（默认 OFF，仅观察/分析/建议，绝不自动执行）──
    if getattr(_config, "FEATURE_SELF_IMPROVEMENT", False):
        if not _tick_should_abort():
            _maybe_self_improvement(now)
    # ── 抢占插队的即时任务（用户/工具请求立即扫描）──
    for task in _drain_immediate():
        if _tick_should_abort():
            break
        _run_immediate(task.get("kind", "all"), now)
    _TICK_ROUND_START = 0
    _TICK_STUCK = False


# ── Phase 28：Self Improvement Advisor 心跳挂勾（默认 OFF）──
_SELF_IMPROVE_COOLDOWN = 3600  # 两次自检建议扫描最小间隔（秒），避免空转刷屏


def _maybe_self_improvement(now):
    """Phase 28 挂勾：经 cooldown 后跑一次自我改进建议扫描（仅观察/分析/建议）。

    全程防御式隔离：异常由 run_cycle 内部吞掉，绝不抛到主循环；
    即使 self_improvement 模块缺失也不影响心跳。
    """
    try:
        last = _load_ts("self_improvement_last_scan")
        if time.time() - last < _SELF_IMPROVE_COOLDOWN:
            return
        from self_improvement import run_cycle
        run_cycle()
        _save_ts("self_improvement_last_scan", time.time())
    except Exception as e:
        print(f"[proactive] self_improvement 挂勾失败（已忽略）: {e}")


def _check_prefetch(now):
    """执行到期的预取任务（对齐参考实现预取 runner）。

    从 prefetch_tasks 取 next_run<=now 且启用的任务，逐条取数（落盘预热或推主动消息），
    并更新 last_run/next_run。运行逻辑在 tools._run_prefetch_task（避免循环依赖，这里延迟导入）。
    """
    try:
        conn = db_conn()
        rows = conn.execute(
            "SELECT id,name,source,query,action,interval FROM prefetch_tasks "
            "WHERE enabled=1 AND next_run IS NOT NULL AND next_run <= ?",
            (now.strftime("%Y-%m-%d %H:%M:%S"),),
        ).fetchall()
        conn.close()
        if not rows:
            return
        from tools import _run_prefetch_task

        for r in rows:
            task = {"id": r[0], "name": r[1], "source": r[2], "query": r[3], "action": r[4], "interval": r[5]}
            try:
                _run_prefetch_task(task)
            except Exception:
                continue
    except Exception:
        pass


def _scan_hotspots(now, force=False):
    """每 HOTSPOT_INTERVAL 秒扫描一次舆情热点；内容有变化才推送摘要（避免刷屏）。
    返回当前快照 [{p,t,r,h}] 供异常检测比对；未到期/无数据返回 None。
    force=True 时无视间隔限制，立即扫描（供抢占插队 / 用户主动触发）。"""
    if not force and now.timestamp() - _load_ts("tick_last_hotspot") < HOTSPOT_INTERVAL:
        return None
    _save_ts("tick_last_hotspot", now.timestamp())
    try:
        import hotspots as _hs
        data = _hs.get_hotspots(force=True)
    except Exception:
        return None
    platforms = (data or {}).get("platforms") or {}
    if not platforms:
        return None
    lines = []
    snap = []
    sig_parts = []
    for p, items in platforms.items():
        if not items:
            continue
        label = _hs._platform_label(p) if hasattr(_hs, "_platform_label") else _plat_label(p)
        top = items[:3]
        lines.append("%s：%s" % (label, "、".join(it.get("text", "") for it in top)))
        for it in items[:10]:
            snap.append({"p": p, "t": it.get("text", ""), "r": it.get("rank", 0) or 0, "h": it.get("heat", "")})
        for it in top:
            sig_parts.append("%s|%s" % (p, it.get("text", "")))
    if not lines:
        return None
    sig = "||".join(sig_parts)
    prev_sig = _meta_get("tick_hotspot_sig", "")
    _meta_set("tick_hotspot_sig", sig)
    if sig == prev_sig:
        return snap  # 无变化仍返回快照供异常比对，但不推送摘要
    content = "🌐 舆情扫描更新：\n" + "\n".join(lines)
    push_proactive("hotspot", content)
    return snap


def _scan_weather(now, force=False):
    """每 WEATHER_INTERVAL 秒更新一次天气；内容有变化才推送。
    force=True 时无视间隔限制，立即更新（供抢占插队 / 用户主动触发）。"""
    if not force and now.timestamp() - _load_ts("tick_last_weather") < WEATHER_INTERVAL:
        return
    _save_ts("tick_last_weather", now.timestamp())
    try:
        import geo_weather as _gw
        city = os.environ.get("XIAO6_DEFAULT_CITY") or None
        w = _gw.get_weather(city=city, mode="compact", force=True)
    except Exception:
        return
    card = (w or {}).get("card") or {}
    if not card:
        return
    content = "🌤️ 天气更新：%s %s %s°（最高%s/最低%s）" % (
        card.get("city", ""),
        card.get("condition", ""),
        card.get("temp", ""),
        card.get("high", ""),
        card.get("low", ""),
    )
    if _meta_get("tick_weather_sig", "") == content:
        return
    _meta_set("tick_weather_sig", content)
    push_proactive("weather", content)


def _scan_anomaly(now, snap):
    """异常检测：关键词命中 + 排名突增 / 新晋热榜。对比上一轮快照，按内容去重推送。"""
    if not snap:
        return
    try:
        keywords = json.loads(_meta_get("alert_keywords", "[]") or "[]")
    except Exception:
        keywords = []
    try:
        prev = json.loads(_meta_get("tick_hotspot_prev", "[]") or "[]")
    except Exception:
        prev = []
    prev_by_text = {x.get("t", ""): x for x in prev if x.get("t")}
    # 首轮：prev 为空时仅建立基线快照，不告警，避免一次性洪泛
    if not prev:
        _meta_set("tick_hotspot_prev", json.dumps(snap, ensure_ascii=False))
        return
    alerts = []
    # 1) 用户关键词命中
    for kw in keywords:
        kw = (kw or "").strip()
        if not kw:
            continue
        for x in snap:
            if kw and kw in (x.get("t", "") or ""):
                alerts.append("🔴 关键词「%s」命中%s热榜：%s" % (kw, _plat_label(x.get("p")), x.get("t", "")))
                break
    # 2) 排名突增 / 新晋热榜
    for x in snap:
        t = x.get("t", "")
        if not t:
            continue
        r = x.get("r") or 0
        if t in prev_by_text:
            pr = prev_by_text[t].get("r") or 0
            if pr and r and (pr - r) >= 3:
                alerts.append("🔥 %s热度攀升：%s 升至第 %d 位" % (_plat_label(x.get("p")), t, r))
        else:
            if r and r <= 5:
                alerts.append("🆕 %s新晋热榜：%s 空降第 %d 位" % (_plat_label(x.get("p")), t, r))
    # 去重后推送（避免重复轰炸）
    seen = set()
    uniq = []
    for a in alerts:
        if a not in seen:
            seen.add(a)
            uniq.append(a)
    if uniq:
        content = "📡 检测到 %d 条舆情异动：\n" % len(uniq) + "\n".join(uniq[:5])
        if _meta_get("tick_alert_sig", "") == content:
            _meta_set("tick_hotspot_prev", json.dumps(snap, ensure_ascii=False))
            return
        _meta_set("tick_alert_sig", content)
        push_proactive("alert", content)
    # 无论是否告警，都更新 prev 快照供下一轮比对
    _meta_set("tick_hotspot_prev", json.dumps(snap, ensure_ascii=False))


# ── 自动化规则触发（IFTTT 式）──
# time 规则：每天 trigger_value(HH:MM) 首次命中时触发一次（靠 last_triggered 防 30s 心跳重复）。
# event 规则：本 ticker 不处理（新会话事件由 SSE 连接时另行触发，后续可扩展）。
def _check_goal_deadlines():
    """扫描 24h 内到期且近 7 天无进展的活跃目标，推送一次主动提醒（去重：每目标 24h 一次）。
    避免过度打扰：仅在目标即将到期（≤24h）且长期未推进时提醒。"""
    try:
        from datetime import timedelta

        import goals

        now = datetime.now()
        horizon = now + timedelta(hours=24)
        for g in goals.list_active_goals(limit=20):
            if not g.due_date:
                continue
            # 解析截止日期（支持 YYYY-MM-DD 或 ISO datetime）
            due = None
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                try:
                    due = datetime.strptime(g.due_date[:19] if " " in g.due_date else g.due_date[:10], fmt)
                    break
                except Exception:
                    continue
            if due is None:
                continue
            # 仅「到期前 ≤24h」区间
            if not (now <= due <= horizon):
                continue
            # 近 7 天无进展则不打扰
            try:
                updated = datetime.strptime(g.updated[:19], "%Y-%m-%d %H:%M:%S")
            except Exception:
                updated = now
            if (now - updated) < timedelta(days=7):
                continue
            # 去重：同一目标 24h 内只提醒一次
            last_key = "goal_remind_%d" % g.id
            last = _load_ts(last_key)
            if last and (now.timestamp() - last) < 86400:
                continue
            _save_ts(last_key, now.timestamp())
            push_proactive(
                "goal",
                f"🎯 目标提醒：#{g.id} {g.title} 将在 {g.due_date} 到期（进度 {g.progress}%），"
                f"近期未推进，要现在拆解推进吗？",
            )
    except Exception:
        pass


def _parse_dt(s):
    """宽松解析目标 due_date / updated 时间（支持 YYYY-MM-DD 或 ISO datetime）。"""
    if not s:
        return None
    norm = s[:19] if " " in s else s[:10]
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(norm, fmt)
        except Exception:
            continue
    return None


def collect_today_suggestions():
    """汇总「今日建议」：停滞目标 + 临近到期目标，给出可行动作。供简报与面板复用（异常静默）。"""
    try:
        from datetime import timedelta

        import goals

        now = datetime.now()
        stall_days = int(os.environ.get("PROACTIVE_STALL_DAYS", "5"))
        horizon = now + timedelta(days=3)
        sugg = []
        for g in goals.list_active_goals(limit=20):
            if g.progress >= 100:
                continue
            # 临近到期（≤3 天）且未完成 → 今天就该推进
            due = _parse_dt(g.due_date)
            if due and now <= due <= horizon:
                sugg.append(
                    f"🎯 #{g.id} {g.title} 将在 {g.due_date[:10]} 到期（进度 {g.progress}%），建议今天拆解推进。"
                )
            # 停滞：超 stall_days 天无进展 → 给一个具体下一脚
            updated = _parse_dt(g.updated) or now
            idle_days = (now - updated).days
            if idle_days >= stall_days:
                pending = [s for s in goals._goal_tasks(g.id) if s["status"] != "done"]
                if pending:
                    sugg.append(
                        f"⏸️ #{g.id} {g.title} 已 {idle_days} 天没动静（进度 {g.progress}%），"
                        f"下一脚可先走：「{pending[0]['title']}」。"
                    )
                else:
                    sugg.append(
                        f"⏸️ #{g.id} {g.title} 已 {idle_days} 天没动静（进度 {g.progress}%），"
                        f"要不要我帮你拆成可执行步骤？"
                    )
        return sugg
    except Exception:
        return []


def _check_goal_stalled():
    """扫描停滞目标（超 PROACTIVE_STALL_DAYS 天无进展且未完成），推送一次主动建议。
    每目标冷却 PROACTIVE_STALL_REMIND_DAYS 天，避免反复打扰（异常静默）。"""
    try:
        from datetime import timedelta

        import goals

        now = datetime.now()
        stall_days = int(os.environ.get("PROACTIVE_STALL_DAYS", "5"))
        remind_days = int(os.environ.get("PROACTIVE_STALL_REMIND_DAYS", "3"))
        for g in goals.list_active_goals(limit=20):
            if g.progress >= 100:
                continue
            updated = _parse_dt(g.updated) or now
            if (now - updated).days < stall_days:
                continue
            last_key = "goal_stall_%d" % g.id
            last = _load_ts(last_key)
            if last and (now.timestamp() - last) < remind_days * 86400:
                continue
            _save_ts(last_key, now.timestamp())
            pending = [s for s in goals._goal_tasks(g.id) if s["status"] != "done"]
            action = (
                f"下一脚可先走：「{pending[0]['title']}」"
                if pending
                else "要不要我帮你把目标拆成可执行的步骤？"
            )
            push_proactive(
                "goal",
                f"⏸️ 目标停滞提醒：#{g.id} {g.title} 已经 {(now - updated).days} 天没有推进"
                f"（进度 {g.progress}%），{action}",
            )
    except Exception:
        pass


def _maybe_weekly_review():
    """每周一次（默认周一，PROACTIVE_REVIEW_WEEKDAY）推送本周小结；按 ISO 周去重（异常静默）。"""
    try:
        from datetime import timedelta

        import goals

        now = datetime.now()
        review_weekday = int(os.environ.get("PROACTIVE_REVIEW_WEEKDAY", "0"))  # 0=周一
        if now.weekday() != review_weekday:
            return
        iso_week = now.strftime("%G-W%V")
        if _meta_get("last_weekly_review") == iso_week:
            return
        _meta_set("last_weekly_review", iso_week)
        week_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        conn = db_conn()
        completed = conn.execute(
            "SELECT COUNT(*) FROM goals WHERE status='completed' AND completed_at >= ?", (week_ago,)
        ).fetchone()[0]
        progressed = conn.execute(
            "SELECT COUNT(*) FROM goals WHERE updated >= ? AND status='active'", (week_ago,)
        ).fetchone()[0]
        open_tasks = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE status NOT IN ('done','archived')"
        ).fetchone()[0]
        conn.close()
        parts = [f"📅 本周小结（{iso_week}）："]
        parts.append(
            f"本周达成 {completed} 个目标，{progressed} 个活跃目标有进展；当前还有 {open_tasks} 条待办任务。"
        )
        if completed == 0 and progressed == 0:
            parts.append("这周目标推进偏少，要不要一起过一遍手上的目标，定个节奏？")
        else:
            parts.append("继续保持节奏，需要我帮你复盘某个目标吗？")
        push_proactive("review", "".join(parts))
    except Exception:
        pass


def _check_rules(now):
    conn = db_conn()
    try:
        rows = conn.execute(
            "SELECT id,name,trigger_type,trigger_value,action_type,action_value,last_triggered "
            "FROM rules WHERE enabled=1"
        ).fetchall()
        for rid, name, tt, tv, at, av, last in rows:
            if tt == "time" and re.match(r"^\d{1,2}:\d{2}$", tv or ""):
                if now.strftime("%H:%M") == tv and (
                    not last or not last.startswith(now.strftime("%Y-%m-%d"))
                ):
                    _fire_rule(rid, name, at, av, now, conn)
    finally:
        conn.close()


def _fire_rule(rid, name, at, av, now, conn):
    ts = now.strftime("%Y-%m-%d %H:%M:%S")
    if at == "notify":
        push_proactive("rule", av or ("规则「%s」触发了" % name))
    elif at == "open_panel":
        # 前端收到 rule_panel 后自动打开对应面板
        push_proactive("rule_panel", av or "hotspot")
    else:
        # 未知 action 降级为通知，避免静默丢失
        push_proactive("rule", "规则「%s」触发（动作类型 %s 暂不支持）" % (name, at))
    try:
        conn.execute("UPDATE rules SET last_triggered=? WHERE id=?", (ts, rid))
        conn.commit()
    except Exception:
        pass


# ── Phase 9 B1/B3：薄决策层 enacter + 扫描 + 看门狗 ──────────────────────────
# 注意：_running_since 仅为 LONG_RUNNING 看门狗用的瞬时计时缓存（goal_id → 起始 ts），
# 不是领域状态来源（领域真相在 goals / agent_runtime），不进任何第二 Runtime/State。
_running_since: dict = {}


def _enact_decision(decision, signal):
    """将引擎决策落地（唯一会触发副作用的入口）。

    纪律（Phase 9 红线）：
    - CREATE_GOAL 只经 runtime.submit_goal（带 intent_id 标记），不绕过 Goal System / Policy Guard；
    - NOTIFY/SUGGEST 经 push_proactive（已含 NotificationPolicy 裁决）；
    - IGNORE 不动作。
    所有落地动作都发布 system 事件（proactive_decision / proactive_result）供前端 Companion 可视化。
    """
    try:
        from eventbus import publish_system
    except Exception:
        publish_system = None
    if decision.action == _pe.ACTION_CREATE_GOAL:
        try:
            from agent_runtime import runtime

            gid = runtime.submit_goal(
                decision.title or "主动目标",
                description=decision.description or "",
                intent_id="proactive-engine",
            )
            if publish_system and gid:
                publish_system(
                    "proactive_result",
                    {
                        "action": "CREATE_GOAL",
                        "goal_id": gid,
                        "signal_type": decision.signal_type,
                        "title": decision.title,
                    },
                    source="proactive_engine",
                )
        except Exception as e:
            print(f"[proactive] CREATE_GOAL 落地失败: {e}")
        return
    if decision.action in (_pe.ACTION_NOTIFY, _pe.ACTION_SUGGEST):
        push_proactive(
            decision.signal_type,
            decision.title or decision.description or "",
            importance=decision.importance,
        )
        if publish_system:
            publish_system("proactive_decision", decision.to_dict(), source="proactive_engine")
        return
    # IGNORE：不动作（仍发决策事件供 telemetry）
    if publish_system:
        publish_system("proactive_decision", decision.to_dict(), source="proactive_engine")


def _proactive_scan(now):
    """构建停滞目标信号，经 ProactiveEngine 决策并落地。

    - 仅对「目标停滞」信号启用引擎（其余信号沿用既有规则通知）。
    - 每目标冷却 PROACTIVE_STALL_REMIND_DAYS 天，避免刷屏。
    - 只读 goals，纯决策 + 合法落地（runtime.submit_goal），不直连工具。
    """
    try:
        remind_days = int(os.environ.get("PROACTIVE_STALL_REMIND_DAYS", "3"))
        import goals

        for g in goals.list_active_goals(limit=20):
            if g.progress >= 100:
                continue
            updated = _parse_dt(g.updated) or now
            idle_days = (now - updated).days
            if idle_days < _pc.stall_days():
                continue
            # 冷却：同一目标 N 天内只决策一次
            last_key = "pe_goal_%d" % g.id
            last = _load_ts(last_key)
            if last and (now.timestamp() - last) < remind_days * 86400:
                continue
            _save_ts(last_key, now.timestamp())
            pending = [s for s in goals._goal_tasks(g.id) if s["status"] != "done"]
            next_step = pending[0]["title"] if pending else None
            signal = _pe.signal_goal_stalled(
                goal_id=g.id, title=g.title, idle_days=idle_days,
                next_step=next_step, stall_threshold=_pc.stall_days(),
            )
            decision = _pe.decide(signal)
            if decision.action != _pe.ACTION_IGNORE:
                _enact_decision(decision, signal)
    except Exception:
        pass


def _check_long_running(now):
    """LONG_RUNNING 看门狗：对在跑目标计时，超阈值发一次告警（每目标一次，完成/失败清除）。"""
    try:
        threshold = _pc.long_running_minutes() * 60.0
        expired = [gid for gid, start in list(_running_since.items())
                   if (now.timestamp() - start) >= threshold]
        for gid in expired:
            _running_since.pop(gid, None)
            try:
                import goals

                g = goals.get_goal(gid)
                title = g.title if g else f"目标 #{gid}"
            except Exception:
                title = f"目标 #{gid}"
            dec = _pe.decide(_pe.signal_long_running(
                title=title,
                detail=f"已运行超过 {_pc.long_running_minutes()} 分钟",
                payload={"goal_id": gid},
            ))
            _enact_decision(dec, {"type": "long_running", "goal_id": gid})
    except Exception:
        pass


def _on_goal_event(event):
    """消费 zz.goal 事件（领域事件信封）：完成时主动提示复盘。

    信封结构：{"xiao6_event": "GOAL_COMPLETED", "payload": {...}}（见 eventbus.publish_domain）。
    """
    try:
        if event.payload.get("xiao6_event") == "GOAL_COMPLETED":
            payload = event.payload.get("payload", {})
            title = payload.get("title", "目标")
            # 完成即清除看门狗计时
            gid = payload.get("goal_id")
            if gid:
                _running_since.pop(gid, None)
            push_proactive("goal", f"🏆 目标达成：{title} 已完成！要不要我帮你做个复盘小结？")
    except Exception:
        pass


def _on_domain_event_for_proactive(event):
    """Phase 9 B3：统一消费领域事件，补 ERROR_OCCURRED 生产者 + LONG_RUNNING 计时。

    - GOAL_RUNNING / AGENT_*：记录看门狗起始 ts。
    - GOAL_FAILED / AGENT_FAILED：发 ERROR_OCCURRED 领域事件 + 高重要度主动通知（critical 突破 DND）。
    - GOAL_COMPLETED / GOAL_FAILED：清除看门狗计时。
    严格单一来源：仅经 eventbus.publish_domain / push_proactive，绝不裸 bus.publish。
    """
    try:
        name = event.payload.get("xiao6_event")
        payload = event.payload.get("payload", {}) or {}
        gid = payload.get("goal_id")
        if name in ("GOAL_RUNNING",):
            if gid:
                _running_since[gid] = time.time()
        elif name in ("GOAL_COMPLETED", "GOAL_FAILED"):
            if gid:
                _running_since.pop(gid, None)
        if name in ("GOAL_FAILED", "AGENT_FAILED"):
            err = payload.get("error") or "执行失败"
            title = payload.get("title") or f"目标 #{gid}" if gid else "执行异常"
            try:
                from eventbus import publish_domain

                publish_domain(
                    "ERROR_OCCURRED",
                    {"goal_id": gid, "title": title, "error": str(err),
                     "source_event": name},
                    source="proactive",
                )
            except Exception:
                pass
            # 高重要度通知；critical 突破 DND（系统级异常应知会用户）
            push_proactive("error", f"❌ 执行异常：{title} —— {err}", importance="critical")
    except Exception:
        pass


try:
    from eventbus import bus as _goal_bus

    _goal_bus.subscribe("zz.goal", _on_goal_event)
    _goal_bus.subscribe("zz.goal", _on_domain_event_for_proactive)
except Exception:
    pass
