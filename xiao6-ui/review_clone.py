"""庄周 · 成果审视分身（纯标准库，零新增依赖）。

本模块是庄周的一个「自我审视」人格：以批判性视角复核庄周自己产出的回答，
找出事实性错误、逻辑漏洞、表达问题以及可改进点。设计目标：

  1. 纯标准库，不引入任何第三方包；
  2. 通过「懒导入」在真正调用时才 import llm，避免与 tools / server 形成导入环；
  3. 全流程防御式：任何失败都不抛出，而是返回一段可读的降级提示，
     确保审视分身永远不会中断主回答链路。

对外公共 API：
  - REVIEW_SYSTEM_PROMPT : 审视官的系统提示词（严格但建设性）。
  - review_text(text, context="") -> str : 审视一段文本，返回批判要点。
  - auto_review_enabled() -> bool : 是否开启自动审视（读环境变量）。
  - build_review_payload(original, critique) -> dict : 给前端 review 面板的数据。
"""

import os
from datetime import datetime

# 审视官的系统提示词：严格但建设性，要求言之有物、不要复述原回答。
REVIEW_SYSTEM_PROMPT = (
    "你是庄周的分身审视官。请以批判性视角审视下面这段庄周的回答，指出："
    "1)事实性错误；2)逻辑漏洞或自相矛盾；3)表达不清或冗余；4)可改进点。"
    "用要点列出、言之有物；若无问题请明确写『无明显问题』。不要复述原回答。"
)

# 自动审视开关对应的环境变量名；默认关闭。
AUTO_REVIEW_ENV = "XIAO6_AUTO_REVIEW"

# 审视调用的最大 token 上限（尽量压低成本）。agnes_completion 当前版本
# 不一定接受该参数，因此调用处会做防御式降级（见 _call_review_llm）。
REVIEW_MAX_TOKENS = 400
REVIEW_TIMEOUT = 40
REVIEW_TEMPERATURE = 0.3


def _call_review_llm(messages):
    """懒导入 llm 并调用大模型，返回回复文本；任何异常向上抛出由调用方兜底。

    使用 llm.agnes_completion：它直接返回 urllib 响应对象，需要自行解析
    OpenAI 兼容的 JSON（choices[0].message.content）。
    """
    from llm import agnes_completion  # 延迟导入，规避潜在的导入环

    # 优先尝试带 max_tokens（若未来版本支持）；不支持则降级到精简参数集。
    try:
        resp = agnes_completion(
            messages,
            max_tokens=REVIEW_MAX_TOKENS,
            timeout=REVIEW_TIMEOUT,
            temperature=REVIEW_TEMPERATURE,
        )
    except TypeError:
        resp = agnes_completion(
            messages,
            timeout=REVIEW_TIMEOUT,
            temperature=REVIEW_TEMPERATURE,
        )

    import json

    result = json.loads(resp.read().decode("utf-8"))
    if not result.get("choices"):
        raise RuntimeError("响应中没有 choices")
    content = result["choices"][0]["message"]["content"]
    if not content:
        raise RuntimeError("模型返回了空内容")
    return content.strip()


def review_text(text: str, context: str = "") -> str:
    """审视庄周的一段回答，返回批判要点文本。

    text    : 待审视的庄周回答。
    context : 可选上下文（如对话背景），用于让审视更贴合实际。

    任何失败都不会抛出，而是返回『（审视分身暂时不可用：<简短错误>）』，
    保证主链路不被审视功能拖垮。
    """
    text = text or ""
    context = context or ""
    if not text.strip():
        return "（审视分身暂时不可用：待审视内容为空）"

    user_content = "待审视内容：\n" + text
    if context.strip():
        user_content += "\n\n上下文：\n" + context

    messages = [
        {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    try:
        return _call_review_llm(messages)
    except Exception as e:
        # 防御式降级：把错误摘要截断，避免把大段堆栈暴露给用户/前端。
        return "（审视分身暂时不可用：" + str(e)[:80] + "）"


def auto_review_enabled() -> bool:
    """是否开启自动审视。读环境变量 XIAO6_AUTO_REVIEW，默认关闭。

    取值（不区分大小写）为 1/true/yes/on 时视为开启，其余一律视为关闭。
    """
    val = (os.environ.get(AUTO_REVIEW_ENV, "false") or "false").strip().lower()
    return val in ("1", "true", "yes", "on")


def build_review_payload(original: str, critique: str) -> dict:
    """构造给前端 review 面板使用的 payload。

    original : 被审视的原始回答。
    critique : 审视分身给出的批判要点（可能为空或降级提示）。
    返回含原始文本、批判文本与 ISO 时间戳的字典。
    """
    return {
        "original": original or "",
        "critique": critique or "",
        "ts": datetime.now().isoformat(timespec="seconds"),
    }
