# -*- coding: utf-8 -*-
"""server.py 拆分出的 chat 域 Handler mixin（由拆分脚本生成，勿手改）。"""
import asyncio
import io
import json
import os
import queue
import re
import sys
import threading
import time
import urllib.request
from urllib.error import HTTPError
from urllib.parse import parse_qs

import capabilities
import config
import data_manager
from asr import status as asr_status, transcribe_bytes
from config import CONTENT, PORT
from db import db_conn, get_memory_graph, save_turn
from focus import capture_foci
from geo_weather import get_geo, get_weather, reverse_geocode
from hotspots import get_hotspots
from llm import _urlopen_with_proxy, agnes_completion, resolve_provider
import provider_registry
from media import status as media_status
from memory import compress_memory
from context import build_context_prompt
from notes import (create_note, extract_daily_note, extract_persons, extract_profile, get_all_tags, get_backlinks,
                   get_graph, get_note, get_notes, parse_md_links, parse_md_tags, search_notes)
from prefetch import start_prefetch_scheduler
from proactive import SUBSCRIBERS, SUBSCRIBERS_LOCK, flush_pending, make_daily_briefing, tick_loop
from self_check import run_self_check
from social import status as social_status
from sysmon import get_logs, get_sysmon
from tasks import recover_tasks
import agent_runtime
from ai_core.lifecycle import lifecycle
from ai_core.execution import run as _execution_run
from tools import TOOL_FUNCS, TOOLS, detect_intents, select_tools, get_pending_video, clear_pending_video, strip_think_tags
from wakeword import get_status as wakeword_status, start as wakeword_start, stop as wakeword_stop

from server_globals import *
from server_globals import _PROVIDER_PROBE_CACHE, _is_local_peer, _sse_put, _sse_use_eventbus, _proactive_dnd_state, _remote_allowed_tools, _hotspot_modal_payload, _resolve_cors_origins, _ACCESS_LOG_REDACT_RE, _REMOTE_FORBIDDEN, _CORS_ALLOWED_ORIGINS, BRIEFING_LOCK


class ChatMixin:
    def _handle_chat_history(self):
        """GET /api/chat/history?limit=N&session=xxx — 只读对话历史。

        按 session 分组返回最近若干轮对话，供 Memory Archive 展示
        「用户输入摘要 / 小6回应摘要」。只读 chat_log，不写任何数据。
        """
        try:
            qs = parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
            limit = max(1, min(200, int(qs.get("limit", ["100"])[0] or "100")))
            session_q = (qs.get("session") or [""])[0].strip()
            from db import db_conn

            conn = db_conn()
            if session_q:
                rows = conn.execute(
                    "SELECT session, role, content, ts FROM chat_log "
                    "WHERE session=? ORDER BY id DESC LIMIT ?",
                    (session_q, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT session, role, content, ts FROM chat_log "
                    "ORDER BY id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            conn.close()
            # 按 session 分组（时间正序）
            sessions = {}
            for session, role, content, ts in reversed(rows):
                sessions.setdefault(session, []).append(
                    {"role": role, "content": content, "ts": ts}
                )
            data = [
                {"session": s, "turns": turns}
                for s, turns in sessions.items()
            ]
            return self._send(
                200,
                json.dumps(
                    {"ok": True, "count": len(rows), "sessions": data},
                    ensure_ascii=False,
                ),
            )
        except Exception as e:
            return self._send(500, json.dumps({"error": str(e)}))


    def _handle_asr_post(self):
        """POST /api/asr — 接收前端录音字节（webm/opus/wav...），本地 FunASR 转写返回文本。
        请求体为原始音频字节；扩展名可由 ?ext=.webm 指定（默认 .webm）。
        """
        try:
            length = int(self.headers.get("Content-Length", 0) or 0)
        except Exception:
            length = 0
        if not length:
            return self._send(400, json.dumps({"ok": False, "text": "", "error": "空请求体"}, ensure_ascii=False))
        data = self.rfile.read(length)
        while len(data) < length:  # 防御性：分块续读
            chunk = self.rfile.read(length - len(data))
            if not chunk:
                break
            data += chunk
        qs = parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
        ext = qs.get("ext", [""])[0].strip() or ".webm"
        if not ext.startswith("."):
            ext = "." + ext
        text, err = transcribe_bytes(data, ext)
        if err:
            return self._send(200, json.dumps({"ok": False, "text": "", "error": err}, ensure_ascii=False))
        return self._send(200, json.dumps({"ok": True, "text": text or "", "error": None}, ensure_ascii=False))


    def _handle_transcribe_post(self):
        """POST /api/transcribe — 上传音视频文件（任意容器），ffmpeg 抽音频 + FunASR 转写，
        返回字幕文本。扩展名由 ?ext=.mp4 指定（默认 .mp4；音频可为 .mp3/.wav 等）。"""
        try:
            length = int(self.headers.get("Content-Length", 0) or 0)
        except Exception:
            length = 0
        if not length:
            return self._send(400, json.dumps({"ok": False, "text": "", "error": "空请求体"}, ensure_ascii=False))
        data = self.rfile.read(length)
        while len(data) < length:
            chunk = self.rfile.read(length - len(data))
            if not chunk:
                break
            data += chunk
        qs = parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
        ext = qs.get("ext", [""])[0].strip() or ".mp4"
        if not ext.startswith("."):
            ext = "." + ext
        text, err = transcribe_bytes(data, ext)
        if err:
            return self._send(200, json.dumps({"ok": False, "text": "", "error": err}, ensure_ascii=False))
        return self._send(200, json.dumps({"ok": True, "text": text or "", "error": None}, ensure_ascii=False))


    def _handle_chat(self):
        payload = self._read_json()
        if "_error" in payload:
            return self._send(400, json.dumps({"error": payload["_error"]}))
        messages = payload.get("messages", [])
        if not isinstance(messages, list) or not messages:
            return self._send(400, json.dumps({"error": "messages required"}))
        if messages[0].get("role") != "system":
            messages = [
                {"role": "system", "content": config.SYSTEM_PROMPT.format(name=config.AI_DISPLAY_NAME or "小6")}
            ] + messages
        user_text = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_text = m.get("content", "")
                break
        # Phase 6 · Intent Routing：剥离能力标签（【深度思考】【联网搜索】【代码执行】→ metadata）
        # 标签仅作为 metadata 影响模型参数/工具权限，不改变 intent 分类
        from intent_gateway import parse_cap_tags, classify_intent
        user_text, cap_flags = parse_cap_tags(user_text)
        _intent = classify_intent(user_text)
        # Phase 7 · Agent Trust Layer：执行意图报告 + 状态透明化事件（AGENT_INTENT_ANALYZED）
        _intent_tools, _intent_risk, _intent_confirm = [], "SAFE", False
        if _intent in ("execution_task", "knowledge_query"):
            try:
                from tool_risk import max_risk, need_confirmation
                _intent_tools = [n for n, _ in detect_intents(user_text)]
                _intent_risk = max_risk(_intent_tools) if _intent_tools else "SAFE"
                _intent_confirm = need_confirmation(_intent_tools)
            except Exception:
                _intent_tools, _intent_risk, _intent_confirm = [], "SAFE", False
        try:
            from eventbus import publish_domain
            publish_domain("AGENT_INTENT_ANALYZED", {
                "intent": _intent,
                "confidence": 1.0 if _intent_tools else 0.6,
                "goal": user_text[:40],
                "tools": _intent_tools,
                "risk": _intent_risk,
                "need_confirmation": _intent_confirm,
            }, source="intent_gateway")
        except Exception:
            pass
        for m in reversed(messages):
            if m.get("role") == "user" and isinstance(m.get("content"), str):
                m["content"] = user_text
                break
        messages[0]["content"] = build_context_prompt(user_text)

        # 模块2：图像多模态输入 —— 若前端附带图片，转 OpenAI vision content 格式
        images = payload.get("images") or []
        if images and isinstance(images, list):
            for m in reversed(messages):
                if m.get("role") == "user":
                    txt = m.get("content") if isinstance(m.get("content"), str) else (user_text or "")
                    m["content"] = [{"type": "text", "text": txt or ""}] + [
                        {"type": "image_url", "image_url": {"url": img}}
                        for img in images[:4]
                        if isinstance(img, str) and img.startswith("data:")
                    ]
                    break

        # 模块5：个性化学习 —— 记录用户习惯信号（best-effort，绝不阻塞）
        try:
            from personalization import record as _prec
            _prec(user_text)
        except Exception:
            pass
        # 把习惯画像注入系统提示词，使回复随使用习惯优化
        try:
            from personalization import summary as _psum
            ps = _psum()
            if ps:
                messages[0]["content"] = messages[0]["content"] + "\n\n" + ps
        except Exception:
            pass

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.send_header("Access-Control-Allow-Origin", self._cors_origin())
        self.end_headers()

        def emit(obj):
            # RC-4 Output Guard: 强制身份锁定（在写入前拦截）
            if isinstance(obj, dict) and "choices" in obj:
                for choice in obj.get("choices", []):
                    delta = choice.get("delta", {})
                    content = delta.get("content", "")
                    if content and ("Agnes" in content or "Sapiens AI" in content):
                        print(f"[RC-4 GUARD] 拦截到非法身份: {content}")
                        content = content.replace("Agnes", "小6").replace("Sapiens AI", "小6的开发商")
                        obj = {"choices": [{"delta": {"content": content}}]}
                        print(f"[RC-4 GUARD] 替换后: {content}")
            line = "data: " + json.dumps(obj, ensure_ascii=False) + "\n\n"
            self.wfile.write(line.encode("utf-8"))
            self.wfile.flush()
            if isinstance(obj, dict) and "error" in obj:
                print(f"[CHAT ERROR] session={payload.get('session_id', 'default')} error={obj['error']}")

        try:
            session_id = (payload.get("session_id") or "default")[:64]
            # 把当前会话 id 暴露给工具层（供 archive_knowledge 等按会话归档），best-effort
            try:
                import tools as _tools_mod

                _tools_mod._current_session = session_id
            except Exception:
                pass

            # —— Command Intent Gateway（Order 5）：统一意图入口 ——
            # 复用 intent_gateway.run_intent_gateway（内部走 GoalDecisionEngine → submit_goal），
            # 所有 Intent/Goal 生命周期事件经 publish_domain() 单一来源发出（前端 AppState 合约入口）。
            # 默认关闭（FEATURE_GOAL_DECISION=false）；开启且 Runtime 已启动才介入；异常降级为普通聊天。
            pending_proposal = None
            # Phase 6 · 禁自动 Goal：GoalSystem 只能由 long_term_goal 意图进入；
            # casual_chat / knowledge_query / execution_task 一律不触发 Goal 决策链
            if getattr(config, "FEATURE_GOAL_DECISION", False) and _intent == "long_term_goal":
                try:
                    if getattr(agent_runtime.runtime, "_running", False):
                        from intent_gateway import run_intent_gateway
                        _res = run_intent_gateway(user_text, source="chat")
                        if _res.get("action") == "create" and _res.get("goalId"):
                            _content = f"已为你创建目标 #{_res['goalId']}：「{_res['title']}」，我会规划并自动执行。"
                            emit({"choices": [{"delta": {"content": _content}}]})
                            emit("[DONE]")
                            save_turn(session_id, "xiao6", _content)
                            return
                        elif _res.get("action") in ("propose", "resume"):
                            pending_proposal = (
                                f"（我判断「{_res['title']}」是一个值得建立的目标，是否要我创建并自动执行？"
                                "确认后我会开始规划。）"
                            )
                        # skip / rejected → 走正常聊天（Intent 事件已由网关发出）
                except Exception as _gde_err:
                    print(f"[GDE] 决策失败，降级为普通聊天: {_gde_err}")

            save_turn(session_id, "user", user_text)
            # 自我学习：捕获用户显式反馈（「记住…」「别再…」「以后…」）持久化为可纠错的学习经验
            try:
                if getattr(config, "FEATURE_SELF_LEARNING", False):
                    import re
                    from memory import record_learning

                    ut = user_text.strip()
                    if re.search(r"(记住|记着|记得|别再|不要再|以后|下次|从今以后|改掉)", ut):
                        m = re.search(
                            r"(?:记住|记着|记得|别再|不要再|以后|下次|从今以后|改掉)[，,：:：]?\s*(.+)",
                            ut,
                        )
                        content = (m.group(1) if m else ut).strip().rstrip("。.！!？?")
                        if content and len(content) >= 4:
                            ltype = "correction" if re.search(r"(别再|不要再|改掉)", ut) else "feedback"
                            record_learning(content, ltype)
            except Exception:
                pass
            # 记忆压缩 + 自我学习蒸馏（后台线程，best-effort，绝不阻塞回复）
            try:
                import threading
                from memory import compress_memory

                threading.Thread(target=compress_memory, daemon=True).start()
            except Exception:
                pass
            try:
                import proactive as _proactive
                _proactive.mark_user_activity()
            except Exception:
                pass
            capture_foci(user_text)  # Phase 2.3：把用户提到的 URL/实体压入焦点栈
            # 命中热点自动归档记忆（对齐参考实现 persistMentionedHotspot，best-effort 不阻塞）
            try:
                import hotspots as _hs
                _hs.archive_mentioned_hotspots(user_text)
            except Exception:
                pass

            # 清空上一轮暂存的天气结果，避免串台（weather.py 旧缓存，供聊天流弹窗 last_weather）
            try:
                import weather as _wmod

                _wmod._LAST = None
            except Exception:
                pass
            # —— 真正的 function calling 闭环（LLM 自主决策工具 + 多轮）——
            # Phase 2.4：按用户意图动态裁剪工具 schema 后下发，省 token、降误调用
            # Phase C：远程会话收敛工具白名单（默认排除 run_shell/file_write 等高危）
            # P1：可见能力清单以 capability_os.discovery.dispatch_tool_list() 为真相源
            #      （capability_runtime.select_capabilities → 委派既有 select_tools 做延迟裁剪）
            from capability_runtime import select_capabilities as _cap_select, execute as _cap_execute
            temperature = float(payload.get("temperature", 0.7))
            reasoning = payload.get("reasoning", None)
            mode = (payload.get("mode") or "smart").strip().lower()
            if mode not in ("smart", "expert"):
                mode = "smart"
            goal_id = payload.get("goal_id")
            peer = (self.client_address or ("",))[0]
            is_remote = not _is_local_peer(peer)
            remote_allowed = _remote_allowed_tools() if is_remote else None
            if _intent == "casual_chat":
                # Phase 6 · casual_chat 快速路径：不下发工具、跳过兜底意图，LLM 直接回复
                # S89/S90: 统一经过 AgentRuntime（不再绕过）
                content, called = agent_runtime.runtime.run_chat_turn(
                    messages, emit, user_text=user_text, tools=[],
                    temperature=temperature, reasoning=reasoning, allowed=remote_allowed,
                    mode=mode, goal_id=goal_id,
                )
                missed = []
            else:
                # S89/S90: 统一经过 AgentRuntime（不再绕过）
                content, called = agent_runtime.runtime.run_chat_turn(
                    messages, emit, user_text=user_text,
                    tools=_cap_select(user_text, allowed=remote_allowed),
                    temperature=temperature, reasoning=reasoning, allowed=remote_allowed,
                    mode=mode, goal_id=goal_id,
                )

                # —— 兜底强化：用户意图明显该走某工具，但 LLM 本轮没调用它（支持复合意图）
                intents = detect_intents(user_text)
                missed = [(name, args) for name, args in intents if name not in called]
            if missed:
                tool_results = []
                for name, args in missed:
                    # 远程会话同样受白名单约束
                    if remote_allowed is not None and name not in remote_allowed:
                        emit({"xiao6_event": "tool_end", "tool": name,
                              "result": f"工具 {name} 在远程会话中不可用（受白名单限制）"})
                        continue
                    emit({"xiao6_event": "tool_start", "tool": name, "args": args})
                    # P1：统一经 capability_runtime（默认 Chat 能力收敛点）→
                    # capability_os.invoke_capability / execute_tool → ai_core.execution.run（policy 门）
                    _cap_result = _cap_execute(name, args, allowed=remote_allowed, mode=mode, goal_id=goal_id)
                    result = _cap_result.to_tool_message()
                    emit({"xiao6_event": "tool_end", "tool": name, "result": result})
                    tool_results.append((name, result))

                # 热点结果本身已是格式化摘要，直接返回更稳更快，避免 LLM 超时导致连接断开
                if len(tool_results) == 1 and tool_results[0][0] in ("get_hotspots", "open_hotspot_panel"):
                    content = tool_results[0][1]
                else:
                    aug = (
                        "用户问题："
                        + user_text
                        + "\n\n"
                        + "\n\n".join(f"本地工具「{name}」返回结果：{result}" for name, result in tool_results)
                        + "\n\n请用简洁、口语化的简体中文，把以上结果自然地汇总告诉用户，不要使用 Markdown 或多余格式。"
                    )
                    try:
                        with agnes_completion(
                            [{"role": "system", "content": build_context_prompt(user_text)}, {"role": "user", "content": aug}],
                            stream=False,
                            timeout=20,
                        ) as resp:
                            d = json.loads(resp.read().decode("utf-8"))
                        content = d.get("choices", [{}])[0].get("message", {}).get("content") or "\n\n".join(
                            r for _, r in tool_results
                        )
                    except Exception:
                        content = "\n\n".join(r for _, r in tool_results)

            # —— 天气弹窗：若有天气结构化结果，额外推一个 modal 事件，前端独立弹窗展示 ——
            try:
                import weather as _wmod

                wd = _wmod.last_weather()
                if wd and wd.get("ok"):
                    emit({"xiao6_event": "modal", "kind": "weather", "data": wd})
            except Exception:
                pass

            # —— 热点聚合弹窗：命中 get_hotspots 时，额外推一个 modal 事件（前端弹窗卡片）——
            try:
                did_hotspots = ("get_hotspots" in called) or any(n == "get_hotspots" for n, _ in missed)
                if did_hotspots:
                    hs = get_hotspots()
                    emit({"xiao6_event": "modal", "kind": "hotspots", "data": _hotspot_modal_payload(hs)})
            except Exception:
                pass

            # —— 热点面板打开：命中 open_hotspot_panel 时，推 panel 事件让前端切到全屏热点模式 ——
            try:
                did_open_panel = ("open_hotspot_panel" in called) or any(n == "open_hotspot_panel" for n, _ in missed)
                if did_open_panel:
                    emit({"xiao6_event": "panel", "panel": "hotspot"})
            except Exception:
                pass

            # —— 视频播放面板：命中 play_video 且已搜到链接时，推 panel 事件打开全屏播放器 ——
            try:
                did_video = ("play_video" in called) or any(n == "play_video" for n, _ in missed)
                if did_video:
                    pending_vid = get_pending_video()
                    if pending_vid and pending_vid.get("url"):
                        emit({"xiao6_event": "panel", "panel": "video",
                              "url": pending_vid["url"], "title": pending_vid.get("title", "")})
                    clear_pending_video()
            except Exception:
                pass

            # —— 声明式场景卡片：render_card 工具执行后，把卡片声明推送为 scene 事件 ——
            try:
                from scene import drain_scene_events
                for card in drain_scene_events():
                    emit({"xiao6_event": "scene", "card": card})
            except Exception:
                pass

            # —— 新面板：地图 / 文档 / 记忆审计 / 审视分身 ——
            try:
                did_map = ("map_query" in called) or any(n == "map_query" for n, _ in missed)
                if did_map:
                    from tools import get_pending_map, clear_pending_map
                    mp = get_pending_map()
                    clear_pending_map()
                    if mp:
                        emit({"xiao6_event": "panel", "panel": "map", "data": mp})
                did_doc = ("open_doc_panel" in called) or any(n == "open_doc_panel" for n, _ in missed)
                if did_doc:
                    emit({"xiao6_event": "panel", "panel": "doc"})
                did_mem = ("open_memory_audit" in called) or any(n == "open_memory_audit" for n, _ in missed)
                if did_mem:
                    emit({"xiao6_event": "panel", "panel": "memory"})
                did_rev = ("review_output" in called) or any(n == "review_output" for n, _ in missed)
                if did_rev:
                    from tools import get_pending_review, clear_pending_review
                    rp = get_pending_review()
                    clear_pending_review()
                    if rp:
                        emit({"xiao6_event": "panel", "panel": "review", "data": rp})
            except Exception:
                pass

            # 统一剔除模型 reasoning 标签（<think> 或 -think- 变体），避免泄露到用户侧
            content = strip_think_tags(content)

            # —— 自动审视（可选，默认关闭）：对最终回答做一次分身审视并推面板 ——
            try:
                import review_clone as _rc
                if _rc.auto_review_enabled() and content and len(content) <= 4000:
                    critique = _rc.review_text(content[:4000])
                    if critique:
                        emit({"xiao6_event": "panel", "panel": "review", "data": {"original": content, "critique": critique}})
            except Exception:
                pass

            # 推送最终文本（SSE 包装，前端做打字机动画）
            if pending_proposal:
                content = (content or "") + "\n\n" + pending_proposal
            emit({"choices": [{"delta": {"content": content or ""}}]})
            emit("[DONE]")
            save_turn(session_id, "xiao6", content or "")
            # 记忆压缩是 LLM 调用，可能耗时较长，放到后台线程避免阻塞 SSE 连接关闭
            threading.Thread(target=compress_memory, daemon=True).start()
            threading.Thread(target=extract_daily_note, daemon=True).start()
            threading.Thread(target=extract_profile, daemon=True).start()
            threading.Thread(target=extract_persons, daemon=True).start()
            # P1 认知层：后台触发用户模型 + 情节记忆自动抽取
            # （受 Feature Flag 门控；两者皆关则不跑抽取，压缩仍由 compress_memory 兜底；阈值门控、best-effort、不阻塞）
            # 注意：server.py 模块顶部已 import config，此处禁止再 import config，否则会把 config 绑定为 _handle_chat 局部变量，
            #       导致函数开头引用 config.SYSTEM_PROMPT 时抛 UnboundLocalError。
            try:
                if getattr(config, "FEATURE_USER_MODEL", False) or getattr(config, "FEATURE_EPISODIC_MEMORY", False):
                    from cognitive import maybe_extract as _maybe_extract

                    threading.Thread(target=_maybe_extract, daemon=True).start()
            except Exception:
                pass
        except HTTPError as e:
            detail = ""
            try:
                detail = e.read().decode("utf-8", "replace")
            except Exception:
                pass
            emit({"error": f"HTTP {e.code}: {detail or e.reason}"})
        except Exception as e:
            emit({"error": str(e)})


    def _handle_kws(self):
        """POST /api/kws — 接收短音频(16k 单声道 WAV)，转写并判定唤醒词。返回 {wake, transcript}。"""
        try:
            length = int(self.headers.get("Content-Length", 0) or 0)
            body = b""
            while len(body) < length:
                chunk = self.rfile.read(length - len(body))
                if not chunk:
                    break
                body += chunk
            import kws as _kws
            transcript = _kws.transcribe_short(body) if body else ""
            wake = _kws.check_wake(transcript)
            return self._send(
                200,
                json.dumps({"wake": bool(wake), "transcript": transcript}, ensure_ascii=False),
            )
        except Exception as e:
            return self._send(
                500,
                json.dumps({"wake": False, "transcript": "", "error": str(e)}, ensure_ascii=False),
            )


    def _sovits_reachable(self, url, timeout=1.0):
        """快速预检 GPT-SoVITS 服务是否可连，避免不可达时白白等待连接/超时。"""
        import socket
        from urllib.parse import urlparse
        p = urlparse(url)
        host = p.hostname or "localhost"
        port = p.port or (443 if p.scheme == "https" else 80)
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except Exception:
            return False


    def _tts_sovits(self, text):
        """调用本地 GPT-SoVITS GET /tts 合成自定义音色语音，返回 mp3 bytes；失败抛异常。"""
        from urllib.parse import quote
        from urllib.request import Request, urlopen

        base = config.GPT_SOVITS_URL.rstrip("/")
        qs = (
            "text="
            + quote(text)
            + "&ref_audio_path="
            + quote(config.GPT_SOVITS_REF_AUDIO)
            + "&prompt_text="
            + quote(config.GPT_SOVITS_PROMPT_TEXT)
            + "&text_lang=zh&prompt_lang=zh"
        )
        req = Request(base + "/tts?" + qs, headers={"Accept": "audio/mpeg"})
        with urlopen(req, timeout=60) as resp:
            return resp.read()


    def _send_audio(self, audio):
        self.send_response(200)
        self.send_header("Content-Type", "audio/mpeg")
        self.send_header("Content-Length", str(len(audio)))
        self.send_header("Access-Control-Allow-Origin", self._cors_origin())
        self.end_headers()
        self.wfile.write(audio)


    def _tts_sovits(self, text):
        payload = self._read_json()
        if "_error" in payload:
            return self._send(400, json.dumps({"error": payload["_error"]}))
        text = (payload.get("text") or "").strip()
        if not text:
            return self._send(400, json.dumps({"error": "text required"}))
        voice = (payload.get("voice") or "").strip() or config.TTS_VOICE
        rate = (payload.get("rate") or "").strip() or config.TTS_RATE or "+0%"
        import re as _re
        if rate and not _re.match(r'^[\+\-]?\d+(\.\d+)?%$', rate):
            rate = "+0%"  # TTS rate format requires percentage, invalid values fall back to default to avoid 500
        # 前端选了「自定义音色」但后端未启用 GPT-SoVITS 时，回退默认音色，避免无效 voice 报错
        if voice == "__sovits__" and config.TTS_BACKEND != "sovits":
            voice = config.TTS_VOICE
        # 自定义音色（GPT-SoVITS）：仅当显式启用且已配置参考音频时走此路
        if config.TTS_BACKEND == "sovits" and config.GPT_SOVITS_REF_AUDIO and self._sovits_reachable(config.GPT_SOVITS_URL):
            try:
                self._send_audio(self._tts_sovits(text))
                return
            except Exception as e:
                print(f"[TTS] GPT-SoVITS 合成失败：{e}")
                # 不再降级到其他 TTS，直接返回错误
                return self._send(500, json.dumps({"error": f"GPT-SoVITS 不可用: {e}"}))

        # Qwen3-TTS 本地声线（默认声线 Qwen3-TTS-12Hz-1.7B-CustomVoice；
        # 配置参考音频时自动走音色克隆，Base 克隆接口预留）
        if config.TTS_BACKEND == "qwen3":
            try:
                import qwen3_tts
                # 用模块级配置（env 已由 config.reload 同步）
                qwen3_tts.QWEN3_TTS_URL = config.QWEN3_TTS_URL or qwen3_tts.QWEN3_TTS_URL
                qwen3_tts.QWEN3_TTS_MODEL = config.QWEN3_TTS_MODEL or qwen3_tts.QWEN3_TTS_MODEL
                qwen3_tts.QWEN3_TTS_VOICE = config.QWEN3_TTS_VOICE or qwen3_tts.QWEN3_TTS_VOICE
                qwen3_tts.QWEN3_TTS_CLONE_URL = config.QWEN3_TTS_CLONE_URL or qwen3_tts.QWEN3_TTS_CLONE_URL
                qwen3_tts.QWEN3_TTS_REF_AUDIO = config.QWEN3_TTS_REF_AUDIO or qwen3_tts.QWEN3_TTS_REF_AUDIO
                # 前端显式传 __clone__ 或 __sovits__ 声线 → 走克隆；否则用默认声线/默认参考
                if voice in ("__clone__", "__sovits__", "qwen3-clone") or config.QWEN3_TTS_REF_AUDIO:
                    audio = qwen3_tts.synth_clone(text, config.QWEN3_TTS_REF_AUDIO or "")
                else:
                    audio = qwen3_tts.synth_qwen3(
                        text,
                        voice=(voice if voice and voice != "__sovits__" else config.QWEN3_TTS_VOICE),
                        rate=rate,
                    )
                self._send_audio(audio)
                return
            except Exception as e:
                print(f"[TTS] Qwen3-TTS 合成失败：{e}")
                # 不再降级到其他 TTS，直接返回错误
                return self._send(500, json.dumps({"error": f"Qwen3-TTS 不可用: {e}"}))

        # 默认：GPT-SoVITS 未部署，返回错误
        return self._send(503, json.dumps({"error": "TTS 不可用：GPT-SoVITS 未部署"}))


    def _handle_data_export(self):
        """GET /api/data/export — 导出全量用户数据为 JSON 下载。"""
        try:
            data = data_manager.export_data()
            body = json.dumps(data, ensure_ascii=False)
            fname = "xiao6-data-" + time.strftime("%Y%m%d-%H%M%S") + ".json"
            self._send(
                200,
                body,
                ctype="application/json; charset=utf-8",
                headers={"Content-Disposition": f'attachment; filename="{fname}"'},
            )
        except Exception as e:
            self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))


    def _handle_data_import(self):
        """POST /api/data/import — 从备份 JSON 恢复（白名单表 + 关键文件）。"""
        try:
            length = int(self.headers.get("Content-Length", 0) or 0)
            raw = self.rfile.read(length) if length else b""
            if not raw:
                return self._send(400, json.dumps({"error": "空请求体"}))
            payload = json.loads(raw.decode("utf-8"))
            res = data_manager.import_data(payload)
            self._send(200, json.dumps(res, ensure_ascii=False))
        except Exception as e:
            self._send(400, json.dumps({"error": str(e)}, ensure_ascii=False))


    def _handle_stream(self):
        from datetime import datetime
        q = queue.Queue()
        _sse_tokens = []
        if _sse_use_eventbus():
            try:
                from eventbus import bus, TOPIC_SSE, TOPIC_HUD_STATE

                _sse_tokens.append(bus.subscribe(TOPIC_SSE, lambda ev: _sse_put(q, ev.payload)))
                # Phase 11：HUD 状态事件也经 SSE 扇出到前端光环 / glance
                _sse_tokens.append(bus.subscribe(TOPIC_HUD_STATE, lambda ev: _sse_put(q, ev.payload)))
            except Exception as e:
                print(f"[stream] EventBus 订阅失败，回退 SUBSCRIBERS: {e}")
                _sse_tokens = []
        if not _sse_tokens:
            with SUBSCRIBERS_LOCK:
                SUBSCRIBERS.append(q)
        # 1) 离线期间产生的 pending 主动消息，连接即补推
        flush_pending(q)
        # 2) 每日简报：今天还没播报过则推一次。用 BRIEFING_LOCK 串行化，
        #    避免多 SSE 连接 / 远程 Web 客户端多开并发时竞态导致简报双推。
        try:
            with BRIEFING_LOCK:
                today = datetime.now().strftime("%Y-%m-%d")
                conn = db_conn()
                row = conn.execute("SELECT value FROM meta WHERE key='last_briefing_date'").fetchone()
                if not row or row[0] != today:
                    conn.execute(
                        "INSERT INTO meta(key,value) VALUES('last_briefing_date',?) "
                        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                        (today,),
                    )
                    conn.commit()
                    conn.close()
                    q.put(
                        {
                            "xiao6_event": "proactive",
                            "kind": "briefing",
                            "content": make_daily_briefing(),
                            "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        }
                    )
                else:
                    conn.close()
        except Exception:
            pass
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", self._cors_origin())
        self.end_headers()
        try:
            self.wfile.write(b": connected\n\n")
            self.wfile.flush()
            while True:
                try:
                    item = q.get(timeout=20)
                except Exception:
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
                    continue
                self.wfile.write(("data: " + json.dumps(item, ensure_ascii=False) + "\n\n").encode("utf-8"))
                self.wfile.flush()
        except Exception:
            pass
        finally:
            for _tok in _sse_tokens:
                try:
                    from eventbus import bus

                    bus.unsubscribe(_tok)
                except Exception:
                    pass
            else:
                with SUBSCRIBERS_LOCK:
                    if q in SUBSCRIBERS:
                        SUBSCRIBERS.remove(q)


