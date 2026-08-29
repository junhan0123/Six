#!/usr/bin/env python3
"""小6 · Goal Decision Engine（GDE）v1.0 —— Runtime 前置决策门（Phase 9 Step 1）。

极瘦红线（违反即实现失败）：只决定「要不要创建 Goal」。绝不拆任务 / 调工具 / 审批 / 写记忆。
唯一写出口 Runtime.submit_goal()；唯一读出口 goals.list_active_goals()（只读）。
不 import / 不调用 planner / reflector / tools / sandbox / db 直写。
Step 2 扩约：经 policy_engine.pre_approve_tools 做 per-goal 预批准注册（逻辑封装在类内 _pre_approve，不做权限裁决）。

两级决策：用户输入 → GDE(要不要做·确定性规则+AI辅助) → Runtime(编排) → Planner(怎么做) → Policy(能不能做) → Executor
判定优先级（fast path 零 LLM）：references_prior→E / is_ambiguous→D / !has_action→A / self_contained→B / multi_step→C(high建|mid _ai_judge|low弹窗)
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# 确定性规则词表（纯中文子串匹配，零 LLM）
# ---------------------------------------------------------------------------
LONG_VERBS = [
    "调研", "研究", "整理", "梳理", "写", "撰写", "生成", "起草", "修复", "修正",
    "重构", "优化", "改进", "搭建", "部署", "设计", "计划", "规划", "实现", "开发",
    "制作", "总结", "汇总", "分析", "排版", "归档", "备份", "迁移", "升级", "清理",
]
ONESHOT_VERBS = [
    "打开", "启动", "运行", "查询", "搜索", "查找", "搜", "播放", "计时", "计算",
    "翻译", "设置", "切换", "查看", "显示", "获取", "读", "找", "提醒", "定个闹钟",
    "发消息", "发邮件", "查一下", "搜一下",
]
AMBIGUOUS = [
    "处理一下", "处理", "弄一下", "弄", "搞一下", "搞", "那个事", "这事儿", "这事情",
    "帮我弄", "帮我搞",
]
COMPLEX = [
    "并", "然后", "分步骤", "逐步", "计划", "方案", "报告", "文档", "周报", "月报",
    "年报", "总结", "整个", "全部", "项目", "系统", "流程", "自动化", "一系列", "多个",
    "完整", "梳理成", "整理成", "做成", "对比",
]
# Phase 6 · 长期目标明确信号：命中即判为长任务 C（进入 GoalSystem）
LONG_TERM = [
    "长期", "持续", "坚持", "养成", "每天", "每周", "学习", "练习", "培养", "锻炼", "习惯",
]
PRIOR = [
    "继续", "接着", "恢复", "回到", "刚才", "之前", "上次", "先前", "那个目标",
    "之前的目标", "刚才的目标", "上次的目标", "刚那个",
]


@dataclass
class Decision:
    """GDE 的输出。action 决定调用方如何处置。"""
    action: str            # create | propose | skip | resume | merge
    classification: str    # A | B | C | D | E
    confidence: float
    reason: str
    title: str = ""
    goal_id: Optional[int] = None


class GoalDecisionEngine:
    """极瘦决策引擎。单入口 ingest()。"""

    def __init__(self, mid_threshold: float = 0.45, auto_threshold: float = 0.55,
                 debounce_seconds: float = 30.0):
        # 数值拍板（P9 Step 1 战术方案）：mid 下界 0.45 / auto 0.55 / 防抖 30s
        self.mid_threshold = mid_threshold
        self.auto_threshold = auto_threshold
        self.debounce_seconds = debounce_seconds
        self._recent: dict = {}   # norm_text -> (monotonic_time, last_action)

    # ---- 主入口 ----
    def ingest(self, user_text: str, context: Optional[dict] = None) -> Decision:
        text = (user_text or "").strip()
        title = self._derive_title(text)
        if not text:
            return Decision("skip", "A", 0.0, "空输入", title)

        # 防抖：相同文本窗口内已建过 Goal → 直接跳过，避免重复创建
        key = self._norm(text)
        now = time.monotonic()
        cached = self._recent.get(key)
        if cached and (now - cached[0]) < self.debounce_seconds and cached[1] == "create":
            return Decision("skip", "C", 0.0, "防抖：重复目标已创建", title)

        cls = self._classify(text)

        if cls == "A":
            decision = Decision("skip", "A", 0.0, "普通问答，不建目标", title)
        elif cls == "B":
            decision = Decision("skip", "B", 0.0, "一次性工具调用，直派不建目标", title)
        elif cls == "E":
            gid = self._match_prior_goal(text)
            if gid is not None:
                decision = Decision("resume", "E", 0.9, "恢复已有目标", title, goal_id=gid)
            else:
                decision = Decision("skip", "E", 0.0, "未找到可恢复的已有目标", title)
        elif cls == "D":
            decision = Decision("propose", "D", 0.3, "意图不明确，需澄清确认", title)
        else:  # C 长任务
            decision = self._decide_long_task(text, title)

        self._recent[key] = (now, decision.action)
        return decision

    # ---- C 类：长任务置信度分流 ----
    def _decide_long_task(self, text: str, title: str) -> Decision:
        score = self._score(text)
        if score > self.auto_threshold:
            return Decision("create", "C", score, "长任务，自动建目标", title)
        if score < self.mid_threshold:
            return Decision("propose", "C", score, "置信度低，弹窗确认", title)
        # mid 带 → AI 辅助二次判定（仅此处调 LLM，轻量、失败兜底 propose）
        verdict, conf = self._ai_judge(text)
        if verdict is None:
            return Decision("propose", "C", score, "AI 判定失败，保守弹窗", title)
        if verdict and conf > self.auto_threshold:
            return Decision("create", "C", conf, "AI 判定为长任务", title)
        return Decision("propose", "C", conf, "AI 判定需确认", title)

    # ---- AI 辅助判定（仅 mid 带调用，可 monkeypatch 便于测试）----
    def _ai_judge(self, text: str):
        try:
            import llm
            prompt = (
                "判断用户请求是否是需要多步骤执行的长期任务（值得建立目标自动执行）。"
                '只输出 JSON：{"is_goal": true/false, "confidence": 0.0-1.0}。'
                f"请求：{text}"
            )
            with llm.agnes_completion(
                [{"role": "system", "content": prompt}],
                stream=False, temperature=0.2, reasoning=None,
            ) as resp:
                data = __import__("json").loads(resp.read().decode("utf-8"))
            msg = (data.get("choices") or [{}])[0].get("message", {})
            obj = _extract_json(msg.get("content") or "")
            if obj and "is_goal" in obj:
                return bool(obj["is_goal"]), float(obj.get("confidence", 0.5))
        except Exception:
            pass
        return None, 0.0

    # ---- 确定性分类 ----
    def _classify(self, text: str) -> str:
        # Phase 6 · 长期目标明确信号优先 → C（进入 GoalSystem）
        if any(w in text for w in LONG_TERM):
            return "C"
        if any(w in text for w in PRIOR):
            return "E"
        if any(w in text for w in AMBIGUOUS):
            if any(v in text for v in LONG_VERBS):
                return "C"
            return "D"
        # 疑问句优先判为普通问答（宁可少建，不误建）；除非同时含长动词+复杂度强任务信号
        if self._is_question(text):
            if any(v in text for v in LONG_VERBS) and any(c in text for c in COMPLEX):
                return "C"
            return "A"
        has_long = any(v in text for v in LONG_VERBS)
        has_oneshot = any(v in text for v in ONESHOT_VERBS)
        if not has_long and not has_oneshot:
            return "A"
        if has_oneshot and not has_long and not any(c in text for c in COMPLEX) and len(text) <= 16:
            return "B"
        return "C"

    @staticmethod
    def _is_question(text: str) -> bool:
        if text.endswith(("？", "?")):
            return True
        return any(q in text for q in ("吗", "呢", "怎么", "为什么", "为何",
                                       "什么", "谁", "何时", "哪", "多少", "几个", "多久"))

    def _score(self, text: str) -> float:
        s = 0.5
        if any(v in text for v in LONG_VERBS):
            s += 0.15
        if any(v in text for v in LONG_TERM):
            s += 0.3
        cx = sum(1 for c in COMPLEX if c in text)
        s += min(cx * 0.1, 0.3)
        if len(text) > 12:
            s += 0.1
        if any(v in text for v in ONESHOT_VERBS) and not any(v in text for v in LONG_VERBS):
            s -= 0.2
        return max(0.0, min(1.0, s))

    # ---- 已有目标匹配（E 类）----
    def _match_prior_goal(self, text: str) -> Optional[int]:
        try:
            from goals import list_active_goals
            goals = list_active_goals(limit=10)
            if not goals:
                return None
            m = re.search(r"#(\d+)", text)
            if m:
                gid = int(m.group(1))
                if any(g.id == gid for g in goals):
                    return gid
            return goals[0].id  # 最近活跃目标
        except Exception:
            return None

    # ---- 工具 ----
    @staticmethod
    def _norm(text: str) -> str:
        return re.sub(r"\s+", "", text).lower()

    @staticmethod
    def _derive_title(text: str) -> str:
        t = text.strip()
        for p in ("帮我", "请", "我想", "能不能", "可以", "麻烦", "能否", "帮我弄", "帮我搞"):
            if t.startswith(p):
                t = t[len(p):]
        t = t.strip("，。！？.!? \n\t：:；;，")
        if len(t) > 40:
            t = t[:40]
        return t or text[:40]

    # 透传给 Runtime.submit_goal（唯一写出口）；建 Goal 后 per-goal 预批准（Step 2 扩约）
    def submit(self, decision: Decision, intent_id: Optional[str] = None) -> Optional[int]:
        if decision.action != "create":
            return None
        try:
            from agent_runtime import runtime
            gid = runtime.submit_goal(decision.title, decision.reason, intent_id=intent_id)
            if gid is not None:
                self._pre_approve(gid, decision.title)
            return gid
        except Exception as e:
            print(f"[GDE] submit_goal 失败: {e}")
            return None

    @staticmethod
    def _pre_approve(goal_id, title):
        """根据目标标题推断高置信度工具，预批准到该 Goal（启发式，失败不阻塞）。"""
        try:
            from policy_engine import pre_approve_tools
        except Exception:
            return
        TOOL_HINTS = {
            "文件": {"file_read", "file_write", "file_list"},
            "笔记": {"file_read", "file_write"},
            "搜索": {"web_search"},
            "天气": {"web_fetch"},
            "执行": {"run_shell"},
        }
        for kw, tools in TOOL_HINTS.items():
            if kw in title:
                pre_approve_tools(goal_id, tools)
                break


def _extract_json(text):
    if not text:
        return None
    raw = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", raw, re.S)
    if m:
        raw = m.group(1).strip()
    try:
        return __import__("json").loads(raw)
    except Exception:
        pass
    s, e = raw.find("{"), raw.rfind("}")
    if s >= 0 and e > s:
        try:
            return __import__("json").loads(raw[s:e + 1])
        except Exception:
            return None
    return None


# 进程级单例
engine = GoalDecisionEngine()
