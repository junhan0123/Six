#!/usr/bin/env python3
"""庄周 · 社交接收端（入站消息 → 跑一轮 agent → 自动回发）

设计要点：
- 微信/飞书/Discord 入站消息统一经 POST /api/social/inbound（token 门控）进入；
  飞书长连接(stream)接收模块 social_feishu_ws.py 亦复用本模块的 handle_inbound。
- 入站消息落库 social_inbound 表（便于审计/回看），并触发一次「非流式」agent 对话轮；
  最终回复经 social.send 回发给同一 channel + sender。
- 复用与 /api/chat 一致的 function-calling 闭环与意图兜底，但**不推送前端面板**
  （社交渠道只收纯文本回复，避免把地图/文档等卡片往 IM 里塞）。
- 安全：HTTP 层 token 门控（server._handle_social_inbound）；本模块再叠加
  单 sender 频率限制，防刷屏与回声环路。

绝不执行任意外部代码；回发仅使用已注册的本地工具产出文本。
"""

import json
import time
from datetime import datetime

from config import AI_DISPLAY_NAME, SYSTEM_PROMPT
from context import build_context_prompt
from db import db_conn
from tools import run_fc_loop, detect_intents, select_tools
from ai_core.execution import run as _execution_run

# 单 sender 最小处理间隔（秒），防刷屏 / 防回声环路
_RATE_WINDOW = 3.0
_INBOUND_RATE = {}


def _store_inbound(channel, sender, text):
    """落库一条入站消息，返回自增 id（便于后续回填回复）。异常静默兜底。"""
    try:
        conn = db_conn()
        cur = conn.execute(
            "INSERT INTO social_inbound(ts,channel,sender,text,replied) VALUES(?,?,?,?,0)",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), channel, sender, text),
        )
        rid = cur.lastrowid
        conn.commit()
        conn.close()
        return rid
    except Exception:
        return None


def _update_reply(rid, reply, replied):
    if not rid:
        return
    try:
        conn = db_conn()
        conn.execute(
            "UPDATE social_inbound SET replied=?, reply=? WHERE id=?",
            (replied, reply or "", rid),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def list_inbound(limit=50):
    """返回最近的入站消息列表，供设置面板/调试查看。"""
    try:
        conn = db_conn()
        rows = conn.execute(
            "SELECT id,ts,channel,sender,text,replied,reply FROM social_inbound "
            "ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
        return [
            {"id": r[0], "ts": r[1], "channel": r[2], "sender": r[3], "text": r[4],
             "replied": bool(r[5]), "reply": r[6]}
            for r in rows
        ]
    except Exception:
        return []


def handle_inbound(channel, sender, text, temperature=0.7):
    """处理一条入站消息：频率限制 → 入库 → 跑 agent 轮 → 回发。

    返回 (content, error_or_None, sent)。
    - content：agent 生成的回复文本（即使回发失败也会返回，便于调用方/调试查看）；
    - error：agent 轮级别的错误（None 表示正常产出）；
    - sent：是否成功经 social.send 送达对方（未配置通道时为 False）。
    """
    channel = (channel or "").strip().lower()
    sender = (sender or "").strip()
    text = (text or "").strip()
    if not text:
        return "", "空消息"
    if channel not in ("discord", "feishu", "wechat"):
        return "", "不支持的入站 channel：%s" % channel

    # 单 sender 频率限制（防刷/防回声）
    now = time.time()
    last = _INBOUND_RATE.get(sender, 0.0)
    if now - last < _RATE_WINDOW:
        return "", "频率过高，已忽略"
    _INBOUND_RATE[sender] = now

    rid = _store_inbound(channel, sender, text)

    messages = [
        {"role": "system", "content": build_context_prompt(text)},
        {"role": "user", "content": text},
    ]

    def _noop(_obj):
        return None

    try:
        content, called = run_fc_loop(
            messages, _noop, tools=select_tools(text), temperature=temperature
        )
        # 意图兜底（与 /api/chat 一致）：LLM 没主动调的工具，按显式意图补跑
        intents = detect_intents(text)
        missed = [(n, a) for n, a in intents if n not in called]
        if missed:
            tool_results = []
            for n, a in missed:
                res = _execution_run(n, a)
                tool_results.append((n, res))
            if len(tool_results) == 1:
                content = tool_results[0][1]
            else:
                from llm import agnes_completion

                aug = (
                    "用户问题：" + text + "\n\n"
                    + "\n\n".join(f"本地工具「{n}」返回结果：{r}" for n, r in tool_results)
                    + "\n\n请用简洁、口语化的简体中文，把以上结果自然地汇总告诉用户，不要使用 Markdown 或多余格式。"
                )
                try:
                    with agnes_completion(
                        [{"role": "system", "content": build_context_prompt(text)},
                         {"role": "user", "content": aug}],
                        stream=False, timeout=20,
                    ) as resp:
                        d = json.loads(resp.read().decode("utf-8"))
                    content = d.get("choices", [{}])[0].get("message", {}).get("content") or "\n\n".join(
                        r for _, r in tool_results
                    )
                except Exception:
                    content = "\n\n".join(r for _, r in tool_results)
        content = (content or "").strip()
    except Exception as e:
        content = ""
        print(f"[社交接收] agent 轮异常：{e}")

    # 回发（仅当有内容）
    sent = False
    if content:
        try:
            from social import send as social_send

            ok, err = social_send(channel, sender, content)
            if ok:
                sent = True
                _update_reply(rid, content, 1)
            else:
                # 发送失败（如未配置 webhook）不致命：保留生成的回复文本到历史，便于排查
                print(f"[社交接收] 回发失败 channel={channel} sender={sender}: {err}")
                _update_reply(rid, content + "  [回发失败: " + (err or "未配置通道") + "]", 0)
        except Exception as e:
            print(f"[社交接收] 回发异常：{e}")
            _update_reply(rid, content + "  [回发异常: " + str(e) + "]", 0)
    return content, None, sent
