#!/usr/bin/env python3
"""小6 · 工具系统：声明 / 执行 / function-calling 闭环 / 意图兜底"""

import ast
import concurrent.futures
import json
import operator
import os
import re
import shlex
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from db import db_conn

import config
from ai_core.execution import run as _execution_run
from asr import transcribe as asr_transcribe
from config import WEB_SEARCH_ENGINE, WEB_SEARCH_KEY, web_search_credentials, security_policy
from llm import agnes_completion, _urlopen_with_proxy
from media import generate as media_generate
from context import build_context_prompt
from notes import (
    tool_note_list,
    tool_note_save,
    tool_profile_get,
    tool_profile_set,
    tool_reminder_list,
    tool_reminder_set,
)
from sandbox import assert_not_protected, audit_tool, is_dangerous_command, resolve_in_sandbox
from scene import push_scene_event, flush_scene_events
from shell_session import run_in_session, session_state, reset_session
from social import send as social_send
from tasks import (
    tool_complete_task,
    tool_set_task,
    tool_task_list,
    tool_update_task_step,
)

# ---------- 安全沙箱门控（对应参考实现「安全沙箱」设置） ----------
def _tool_disabled(name):
    """返回 (disabled, reason)。被 BLOCKED_TOOLS 禁用、或对应沙箱开关关闭时返回原因。"""
    pol = security_policy()
    if name in pol["blockedTools"]:
        return True, f"工具 {name} 已在安全沙箱中禁用"
    if name in ("file_read", "file_list", "file_write") and not pol["fileSandbox"]:
        return True, "文件沙箱已关闭（fileSandbox=false），文件工具不可用"
    if name == "run_shell" and not pol["execSandbox"]:
        return True, "执行沙箱已关闭（execSandbox=false），run_shell 不可用"
    return False, ""


# ---------- 通用文本后处理 ----------
_THINK_TAG_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_THINK_DASH_RE = re.compile(r"-think-.*?-/think-", re.DOTALL)


def strip_think_tags(text):
    """剔除模型 reasoning 输出中的 <think>...</think> 与截图中见过的 -think-...-/think- 标记。"""
    if not text:
        return text
    text = _THINK_TAG_RE.sub("", text)
    text = _THINK_DASH_RE.sub("", text)
    # 兜底：单独残留的开放/闭合标签
    text = re.sub(r"</?think>|-/?think-", "", text, flags=re.IGNORECASE)
    return text.strip()


# ---------- 工具声明（OpenAI function calling 格式） ----------
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "获取当前日期与时间（可选指定城市，默认本地）。",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string", "description": "城市名，如 北京 / 上海；缺省为本地时间"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "计算数学表达式，如 123*456、(1+2)**3。仅支持 + - * / ** % 和括号。",
            "parameters": {
                "type": "object",
                "properties": {"expr": {"type": "string", "description": "数学表达式"}},
                "required": ["expr"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remember",
            "description": "把一条重要事实/决定/承诺/偏好显式存入长期情节记忆（对应「记住这个」「记一下」）。例如「记住我周三要交报告」「记一下：我不喜欢冗余的 Markdown」。",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "要记住的内容"},
                    "category": {"type": "string", "description": "类别：decision|commitment|project_state|preference|fact|event，默认 fact"},
                    "importance": {"type": "number", "description": "重要度 0~1，默认 0.7"}
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "note_save",
            "description": "保存一条笔记或待办到本地记忆。",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "笔记内容"},
                    "tag": {"type": "string", "description": "可选标签，如 待办/想法/日程"},
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "note_list",
            "description": "列出最近保存的笔记/待办。",
            "parameters": {
                "type": "object",
                "properties": {"limit": {"type": "integer", "description": "返回条数，默认 10"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "memory_search",
            "description": "本地向量语义召回（对齐参考实现本地向量 RAG）：用自然语言提问，按语义相似度检索最相关的笔记/记忆（bge 中文向量模型，理解同义/近义，而非关键词字面匹配）。例如「之前聊过郑州的工厂吗」「关于健康的笔记」时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "语义查询，如「郑州的 iPhone 代工厂」"},
                    "top_k": {"type": "integer", "description": "返回条数，默认 5"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "profile_set",
            "description": "记住关于用户的一条长期事实，例如称呼、偏好、习惯、项目。key 为类别，value 为内容。",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "记忆类别，如 称呼 / 偏好 / 习惯 / 项目"},
                    "value": {"type": "string", "description": "记忆内容"},
                },
                "required": ["key", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "profile_get",
            "description": "回忆关于用户的某条长期记忆；不传 key 则列出全部已记住的信息。",
            "parameters": {
                "type": "object",
                "properties": {"key": {"type": "string", "description": "记忆类别；缺省列出全部"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reminder_set",
            "description": "设置一个提醒/待办，可包含时间（如 明天10:00、30分钟后、立刻）。到时间会主动提醒用户。",
            "parameters": {
                "type": "object",
                "properties": {"content": {"type": "string", "description": "提醒内容，可含时间词"}},
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reminder_list",
            "description": "列出当前未完成的提醒/待办。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_task",
            "description": "创建一条多步任务并跟踪进度（重启后仍在，可续跑）。steps 为步骤清单数组；不传则只记录标题。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "任务标题"},
                    "steps": {"type": "array", "items": {"type": "string"}, "description": "可选：分步计划清单"},
                    "note": {"type": "string", "description": "可选：备注"},
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_task_step",
            "description": "更新任务进度：推进到第几步(current_step)、记录当前步内容(step)、追加备注(note)或改状态(status)。",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "任务 id"},
                    "current_step": {"type": "integer", "description": "已完成/进行到的步序号"},
                    "step": {"type": "string", "description": "当前步骤的简短描述"},
                    "note": {"type": "string", "description": "进度备注"},
                    "status": {"type": "string", "description": "可选：open/running/paused/done/failed"},
                },
                "required": ["task_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "complete_task",
            "description": "完成任务（success 默认 true；false 表示标记失败）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "任务 id"},
                    "success": {"type": "boolean", "description": "是否成功完成，默认 true"},
                    "note": {"type": "string", "description": "可选：完成备注"},
                },
                "required": ["task_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "task_list",
            "description": "列出任务；only_open=true 时只列出未完成的任务。",
            "parameters": {
                "type": "object",
                "properties": {"only_open": {"type": "boolean", "description": "只列未完成，默认 false"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "file_read",
            "description": "读取沙箱内的文件内容。path 为相对沙箱根的路径；可选 start_line/end_line/max_lines 做范围读取。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件相对路径，如 notes/foo.md"},
                    "start_line": {"type": "integer", "description": "起始行（从 1 计），可选"},
                    "end_line": {"type": "integer", "description": "结束行，可选"},
                    "max_lines": {"type": "integer", "description": "最多读取行数，可选"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "file_list",
            "description": "列出沙箱内某目录的内容。path 缺省为沙箱根。",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "目录相对路径，缺省为沙箱根"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "file_write",
            "description": "在沙箱内创建/覆盖写入文件（写入后会读回校验）。path 相对沙箱根。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件相对路径"},
                    "content": {"type": "string", "description": "要写入的文本"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "file_make_dir",
            "description": "在沙箱内创建目录（可递归创建多级目录）。path 为相对沙箱根的路径。",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "要创建的目录相对路径，如 projects/demo"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "file_delete",
            "description": "删除沙箱内的文件或空目录。path 为相对沙箱根的路径。删除前会确认路径在沙箱内且不在受保护列表。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "要删除的文件/目录相对路径"},
                    "recursive": {"type": "boolean", "description": "若删除目录且非空，是否递归删除（默认 false，仅删空目录）"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "file_rename",
            "description": "在沙箱内重命名或移动文件/目录。src 与 dst 均为相对沙箱根的路径。",
            "parameters": {
                "type": "object",
                "properties": {
                    "src": {"type": "string", "description": "原路径"},
                    "dst": {"type": "string", "description": "新路径/新名称"},
                },
                "required": ["src", "dst"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_processes",
            "description": "列出本机正在运行的进程（按内存占用降序）。可选 query 按名称过滤，limit 限制条数。只读。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "按进程名（包含即匹配）过滤，如 chrome"},
                    "limit": {"type": "integer", "description": "返回条数上限（默认 30，最大 200）"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "kill_process",
            "description": "终止本机进程。可传 pid（精确）或 name（按名，会终止所有同名进程）。关键系统进程与小6自身会被拒绝。",
            "parameters": {
                "type": "object",
                "properties": {
                    "pid": {"type": "integer", "description": "要终止的进程 PID（精确）"},
                    "name": {"type": "string", "description": "要终止的进程名（如 notepad.exe），会终止所有同名进程"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "在沙箱内执行一条 shell 命令（cwd 锁死在沙箱根，自动审计）。用于本地脚本/编译/查询等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "要执行的命令"},
                    "cwd": {"type": "string", "description": "可选：沙箱内的子目录作为工作目录"},
                    "session": {
                        "type": "boolean",
                        "description": "是否使用持久 shell 会话（默认 false）。true 时跨命令保持工作目录与环境变量，像真终端一样连续执行（适合 cd 后继续操作、长任务分段跑）。",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "超时秒数（默认 30，最长 180）。会话模式默认 60，适合编译等稍长命令。",
                    },
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "session_state",
            "description": "查看持久 shell 会话的当前状态：平台、就绪情况、已执行命令数、会话目录（含命令内 cd 后的真实目录）。只读。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reset_session",
            "description": "重置持久 shell 会话：终止当前长驻 shell 进程，下条命令会重新拉起一个干净的 shell（cwd 回到沙箱根、环境变量清空）。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "install_software",
            "description": "用 winget 在后台安装软件（Windows）。支持中文软件名（微信/QQ/TIM/VSCode/Chrome 等）或明确的 winget id。会先检索候选、自动选最优，再用界面进度卡实时显示安装进度，装完自动更新。适合「装个微信」「安装 X」这类请求。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "软件名/关键词，如 微信、vscode、chrome"},
                    "package_id": {"type": "string", "description": "可选的明确 winget id，如 Tencent.WeChat；指定后跳过检索直接装"},
                    "silent": {"type": "boolean", "description": "是否静默安装（默认 true，免安装向导点击）。机器范围包仍需 Windows UAC 提权。"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": "抓取指定 URL 的网页文本内容（零密钥，无需任何 API）。返回正文文本（过长会截断）。",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "目标网址"}},
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_read",
            "description": "像浏览器一样「读」一个网页：抓取并清洗成正文可读文本，抽取标题、描述与主体内容（自动识别编码、走代理）。注意：本机无 Chromium，无法渲染 JS 动态内容，纯静态/SSR 页面效果好，SPA 可能读不到动态部分。适合「读一下这个网页 / 看看这个链接讲了什么 / 打开网页」。",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "要读取的网页 URL"},
                    "max_chars": {"type": "integer", "description": "返回正文最大字符数（默认 6000，最大 20000）"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scan_desktop",
            "description": "扫描本机桌面/文档/下载目录，列出文件与文件夹（含大小、修改时间）。让用户/模型了解本机有哪些资料。只读。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "可选：额外要扫描的目录（沙箱内相对路径或绝对路径）"},
                    "limit": {"type": "integer", "description": "每个目录最多列出的条数（默认 50，最大 500）"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scan_installed_software",
            "description": "扫描本机已安装软件（读 Windows 卸载注册表，无需外部依赖），列出软件名与版本。只读。",
            "parameters": {
                "type": "object",
                "properties": {"limit": {"type": "integer", "description": "返回条数上限（默认 60，最大 500）"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "manage_prefetch_task",
            "description": "管理通用预取任务（对齐参考实现 manage_prefetch_task）：让小6按间隔自动取数并缓存或推送。source 可为 weather/hotspot/web；task_action 为 cache(落盘预热) 或 notify(推主动消息)；interval 为秒。TICK 心跳会自动执行到期的启用任务。",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["add", "list", "update", "remove", "run", "run_all"], "description": "操作：add 新增 / list 列出 / update 修改 / remove 删除 / run 立即执行一条 / run_all 执行全部启用"},
                    "id": {"type": "integer", "description": "update/remove/run 时的任务 id"},
                    "name": {"type": "string", "description": "add 时的任务名，或 update 时改名"},
                    "source": {"type": "string", "description": "取数源：weather / hotspot / web（web 时 query 填 URL）"},
                    "query": {"type": "string", "description": "web 源时的目标 URL；weather 源时的城市（可选）"},
                    "task_action": {"type": "string", "description": "执行结果处理：cache(落盘预热) / notify(推主动消息)"},
                    "interval": {"type": "integer", "description": "自动执行间隔秒数（默认 3600）"},
                    "enabled": {"type": "boolean", "description": "是否启用（update 时）"},
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tick_now",
            "description": "抢占插队：立即触发一次 TICK 主动扫描（无需等待下次心跳）。kind 可为 hotspot(舆情热点)/weather(天气)/rules(自动化规则)/prefetch(预取任务)/reminders(到期提醒)/all(全部)。例如用户说「立刻扫描热点」「马上刷新天气」时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "kind": {
                        "type": "string",
                        "enum": ["hotspot", "weather", "rules", "prefetch", "reminders", "all"],
                        "description": "立即执行的扫描类型，默认 all",
                    },
                },
                "required": ["kind"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "实时网络搜索（非预取）。无需密钥即可用 DuckDuckGo 兜底检索；若配置了 XIAO6_WEB_SEARCH_KEY，则走 tavily/serper/brave/jina/searxng 等更高质量源。当用户问到最新资讯、新闻、实时数据或需要联网求证时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"},
                    "limit": {"type": "integer", "description": "返回条数，默认 5"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "media_generate",
            "description": "生成媒体内容：图片/视频/音乐。需配置媒体密钥后启用；未配置时返回启用提示，不消耗任何积分。kind 可选 image/video/music。",
            "parameters": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "description": "媒体类型：image / video / music"},
                    "prompt": {"type": "string", "description": "生成提示词/歌词"},
                    "title": {"type": "string", "description": "仅音乐用：曲名（可选）"},
                    "aspect_ratio": {"type": "string", "description": "仅图片用：如 16:9 / 1:1（可选）"},
                },
                "required": ["kind", "prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "social_send",
            "description": "向社交平台推送消息（Discord / 飞书 / 微信）。统一路由：配置对应平台密钥后启用；未配置时返回启用提示，不触达任何外部账号（零密钥优先，绝不泄漏凭证）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "platform": {"type": "string", "description": "平台：discord / feishu / wechat（微信 ClawBot/企业微信机器人 Webhook）"},
                    "target": {"type": "string", "description": "目标：Discord 频道ID / 飞书 open_id / 微信 touser（可空）"},
                    "text": {"type": "string", "description": "要发送的消息内容"},
                },
                "required": ["platform", "target", "text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "asr_transcribe",
            "description": "语音转写：把音频文件转成文字。需配置 ASR 密钥后启用；未配置时返回启用提示，不消耗任何积分。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "音频文件路径（沙箱内）"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询天气：获取指定城市的当前实况、今日最高/最低温与未来逐小时预报。用户询问天气、气温、温度、出不出太阳、要不要带伞等时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名，如 北京 / 上海 / 杭州；缺省默认北京"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_hotspots",
            "description": "获取实时热点热榜（抖音/小红书/微信/微博）。当用户要求看新闻、热点、实时资讯、更新热榜、刷新热搜、看看今天发生了什么时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "platform": {
                        "type": "string",
                        "description": "平台名：douyin/xiaohongshu/wechat/weibo；缺省返回全部平台",
                    },
                    "force": {"type": "boolean", "description": "是否强制刷新缓存，默认 false"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_hotspot_panel",
            "description": "打开全屏热点面板/大屏。当用户说「打开热点界面/面板/大屏/视图」、「进入热点模式」、「热点大屏」等明确想打开可视化热点面板时调用。不要用于单纯询问热点新闻。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "typhoon_panel",
            "description": "查询台风信息（活跃台风、编号、强度、路径状态）。当用户问「台风」「热带气旋」「台风预警」「台风路径」「现在有几个台风」「台风叫什么」等气象相关问题时调用。数据源：中央气象台 nmc.cn（公开、零密钥）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "force": {"type": "boolean", "description": "是否强制刷新缓存重新抓取，默认 false（30 分钟内复用缓存）"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "person_card",
            "description": "人物卡：保存/查询/列举用户关心的人的结构化档案（身份、关键事实、标签、关系）。当用户说「存一张人物卡」「记一下 XX 是谁」「查 XX 的人物卡」「列出我的人物卡」「人物资料卡」时调用。action=get 查单人（传 name）；action=save 新建/更新（传 name + identity/facts/tags/relation）；action=list 列举全部。",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["get", "save", "list"], "description": "操作类型：get 查单人 / save 新建或更新 / list 列举全部"},
                    "name": {"type": "string", "description": "人物姓名（get/save 时用）"},
                    "identity": {"type": "string", "description": "身份/头衔简介（save 时用）"},
                    "facts": {"type": "array", "items": {"type": "string"}, "description": "关键事实列表（save 时用）"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "标签列表（save 时用）"},
                    "relation": {"type": "string", "description": "与用户的关系（save 时用，可选）"},
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "map_query",
            "description": "地图服务：城市间直线距离、城市坐标、城市列表查询。当用户问「北京到上海多远」「XX 坐标」「XX 在哪」「有哪些城市」「附近城市」等地理问题时调用。离线内置中国主要城市 WGS-84 坐标，不依赖外部地图。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "地理查询语句，如「北京到上海多远」「成都坐标」「有哪些城市」"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_doc_panel",
            "description": "打开文档面板：浏览并阅读本机指定目录下的本地文档（Markdown / 文本 / PDF 元信息）。当用户说「打开文档」「文档面板」「看看我的文档」「读一下 XX 文档」时调用。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_memory_audit",
            "description": "打开记忆审计面板：查看小6各类记忆存储（对话历史、笔记、人物卡等）的统计与抽样，并可按保留天数清理。当用户说「记忆审计」「记忆管理」「看看你记了什么」「清理记忆」时调用。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "review_output",
            "description": "成果审视分身：以批判性视角审视一段回答（事实错误 / 逻辑漏洞 / 表达问题 / 改进点）。当用户说「审视一下」「检查这段回答」「复核」「分身点评」或要求审视上一条回复时调用。text 不传则自动审视最近一条小6回复。",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "要审视的原文；留空则自动取最近一条小6回复"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "play_video",
            "description": "搜索并打开视频播放。当用户想看视频、看剧、看番、看电影、看 B 站/YouTube 视频时调用。可传 url 直接播，或传 query 关键词（如「猫片」「谍战剧」）由小6自动搜 bilibili 并打开全屏播放器。不要用于 AI 生成视频（那是 media_generate）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词，如「猫咪搞笑视频」「谍战剧」"},
                    "url": {"type": "string", "description": "直接给的视频链接（bilibili/youtube 等），优先于 query"},
                    "title": {"type": "string", "description": "视频标题（可选，用于面板展示）"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "manage_rule",
            "description": "管理自动化规则（if-this-then-that）。action=add 创建：trigger_type 填 time（每天定点，trigger_value 填 HH:MM，如 09:00）或 event（trigger_value 填 session_start 表示新开会话时）；action_type 填 notify（到点推送一句话，action_value 是要说的文本）或 open_panel（到点自动打开面板，action_value 填 hotspot/video/memory 之一）。例：每天 9 点打开热点 → {action:add, name:早间热点, trigger_type:time, trigger_value:09:00, action_type:open_panel, action_value:hotspot}。action=list 列出全部规则；action=toggle 切换启用（传 id 与 enabled）；action=delete 删除（传 id）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["add", "list", "toggle", "delete"], "description": "操作类型"},
                    "id": {"type": "integer", "description": "规则 id（toggle/delete 时用）"},
                    "name": {"type": "string", "description": "规则名（add 时用）"},
                    "enabled": {"type": "integer", "description": "1 启用 / 0 禁用（toggle 时用）"},
                    "trigger_type": {"type": "string", "enum": ["time", "event"], "description": "触发类型（add 时用）"},
                    "trigger_value": {"type": "string", "description": "触发器参数：time 填 HH:MM；event 填 session_start"},
                    "action_type": {"type": "string", "enum": ["notify", "open_panel"], "description": "动作类型（add 时用）"},
                    "action_value": {"type": "string", "description": "动作参数：notify 填要说的文本；open_panel 填 hotspot/video/memory"},
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "render_card",
            "description": "声明式往界面挂一张卡片（参考实现 scene 同款）。agent 把界面某处该长什么样「声明」出来，而不是下命令——前端按 id 幂等渲染/更新/移除。kind 可选：text(文本)/weather(天气)/media(图片或视频链接)/choice(选项按钮，点选回传消息)/list(列表)/progress(进度条 0-100)/metric(大数字指标，value+unit+label+delta)/form(输入表单，fields 数组，提交回传消息)/stack|row|col(容器卡，children 嵌套子卡，row 横向)/selfcheck(自检清单，items 每项带 ok)/awakening(唤醒卡，可带按钮)。action 填 set 或 remove。每次只声明一张卡。",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "卡片唯一 id，用于幂等更新/移除（如 weather-now、install-confirm、stats-cpu）"},
                    "kind": {"type": "string", "enum": ["text", "weather", "media", "choice", "list", "progress", "metric", "form", "stack", "row", "col", "selfcheck", "awakening"], "description": "卡片类型"},
                    "action": {"type": "string", "enum": ["set", "remove"], "description": "set=新增或更新；remove=移除该 id"},
                    "title": {"type": "string", "description": "卡片标题"},
                    "body": {"type": "string", "description": "text/weather/awakening 卡的正文，或 choice/list/form 卡的说明文字"},
                    "items": {"type": "array", "items": {"type": "string"}, "description": "list 卡项目数组 / choice 卡选项数组 / selfcheck 卡逐项 {label, ok}"},
                    "media_url": {"type": "string", "description": "media 卡的图片或视频链接"},
                    "media_type": {"type": "string", "description": "media 卡的媒体类型：image / video"},
                    "percent": {"type": "integer", "description": "progress 卡的进度百分比 0-100"},
                    "status": {"type": "string", "description": "progress 卡的进度文字说明"},
                    "value": {"type": "string", "description": "metric 卡的主数值，如 42 / 3.6GHz"},
                    "unit": {"type": "string", "description": "metric 卡的单位，如 °C / MB / %"},
                    "label": {"type": "string", "description": "metric 卡的数值下方说明文字"},
                    "delta": {"type": "string", "description": "metric 卡的变化量，如 +2.3 / -1.1"},
                    "delta_dir": {"type": "string", "description": "metric 卡变化方向：up / down / flat（决定颜色）"},
                    "fields": {"type": "array", "items": {"type": "object", "properties": {"name": {"type": "string"}, "label": {"type": "string"}, "placeholder": {"type": "string"}}}, "description": "form 卡的输入字段数组 {name,label,placeholder}"},
                    "submit_text": {"type": "string", "description": "form 卡提交按钮文字"},
                    "children": {"type": "array", "items": {"type": "object"}, "description": "stack/row/col 容器卡的子卡数组（每张子卡同 render_card 结构，可递归嵌套）"},
                    "summary": {"type": "string", "description": "selfcheck 卡底部的总结文字"},
                    "button_label": {"type": "string", "description": "awakening 卡按钮文字（点击回传该文字作为消息）"},
                },
                "required": ["id", "kind", "action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scan_resources",
            "description": "扫描本机资源并汇总：桌面文件、已装软件（winget）、SSH 主机（~/.ssh/config）、Git 仓库。当用户说「扫描本机」「本机资源」「已装软件有哪些」「我的仓库」「SSH 主机」「桌面有什么」时调用。纯只读，绝不执行任何命令。",
            "parameters": {
                "type": "object",
                "properties": {
                    "scope": {"type": "string", "enum": ["all", "desktop", "software", "ssh", "git"], "description": "扫描范围，默认 all 全扫"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_skills",
            "description": "列出本地可用的 Agent 技能（Skills）清单（名称/描述/触发词）。当用户问「有哪些技能」「技能列表」「你能用什么技能」「列出技能」时调用。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "use_skill",
            "description": "加载并应用一个指定技能：把该技能的说明（SKILL.md 正文）注入上下文供本次回答参考。当用户说「用 XX 技能」「加载技能」「试用示例技能」「调用 XX 技能」时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "技能名称，如「示例技能」"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_custom_tool",
            "description": "创建/更新一个自定义工具（工具工厂/动态 API 槽）：用声明式 JSON 规格定义 name、description、parameters(JSON Schema) 与 strategy（type=http 调白名单域名接口；type=command 沙箱内执行，默认需开启）。绝不接受任意代码。返回创建结果。",
            "parameters": {
                "type": "object",
                "properties": {
                    "spec_json": {"type": "string", "description": "工具规格 JSON 字符串，示例：{\"name\":\"my_api\",\"description\":\"查询X\",\"parameters\":{\"type\":\"object\",\"properties\":{\"q\":{\"type\":\"string\"}},\"required\":[\"q\"]},\"strategy\":{\"type\":\"http\",\"method\":\"GET\",\"url\":\"https://api.x.com/s?q={{q}}\",\"domain_allowlist\":[\"api.x.com\"]}}"}
                },
                "required": ["spec_json"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_custom_tools",
            "description": "列出当前已注册的所有自定义工具（名称/描述/策略类型/创建时间）。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_custom_tool",
            "description": "删除一个已注册的自定义工具（按 name）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "要删除的自定义工具名称"}
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delegate_agent",
            "description": "将一项编程/工程任务委托给本地 Agent（Claude Code）独立执行：启动隔离子进程自动编写/修改代码并返回结果。默认需先确认（confirm=false 仅预览）。适用于「让 agent 帮我写/改/调试 XX」「交给本地 agent 处理」。",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "要委托给本地 Agent 的任务描述"},
                    "confirm": {"type": "boolean", "description": "是否确认执行；false（默认）=仅预览不执行，true=真正启动 Agent"}
                },
                "required": ["task"],
            },
        },
    },
]


# ---------- Phase 3：目标系统工具（Feature Flag 门控）----------
# FEATURE_GOAL_SYSTEM=true（默认）时把 goal 工具追加进 schema；关闭即不注册（用户路径回退 Phase 2）。
try:
    import config as _cfg

    _GOAL_ENABLED = bool(getattr(_cfg, "FEATURE_GOAL_SYSTEM", False))
except Exception:
    _GOAL_ENABLED = False

_GOAL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "set_goal",
            "description": "为用户创建一个中长期目标（Goal）。例如「帮我定个目标：年底前读完 10 本书」「我想做个人网站」。目标可设优先级 / 时间跨度 / 截止日期。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "目标标题，如 搭建个人网站"},
                    "description": {"type": "string", "description": "可选：目标补充描述"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"], "description": "优先级，默认 medium"},
                    "horizon": {"type": "string", "enum": ["short", "medium", "long"], "description": "时间跨度：short 本周 / medium 本月 / long 长期，默认 short"},
                    "due_date": {"type": "string", "description": "可选：截止日期，YYYY-MM-DD 或 ISO datetime"},
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_goal",
            "description": "更新目标的状态 / 进度 / 优先级 / 截止日期等字段。例如「把目标 #3 标记完成」「目标 #1 进度调到 60%」。",
            "parameters": {
                "type": "object",
                "properties": {
                    "goal_id": {"type": "integer", "description": "目标 id"},
                    "status": {"type": "string", "description": "可选：active/paused/completed/archived"},
                    "progress": {"type": "integer", "description": "可选：手动进度 0-100（有子任务时通常由子任务聚合）"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"], "description": "可选：调整优先级"},
                    "due_date": {"type": "string", "description": "可选：调整截止日期"},
                },
                "required": ["goal_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_goals",
            "description": "列出用户的目标。可只列活跃目标；也可按状态 / 时间跨度筛选。",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "可选：按状态筛选 active/paused/completed/archived"},
                    "only_active": {"type": "boolean", "description": "为 true 时只列活跃目标，默认 false"},
                    "limit": {"type": "integer", "description": "返回条数，默认 10"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_goal",
            "description": "删除（归档）一个目标。会二次确认，谨慎使用。",
            "parameters": {
                "type": "object",
                "properties": {"goal_id": {"type": "integer", "description": "目标 id"}},
                "required": ["goal_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "plan_goal",
            "description": "把一个目标拆解为若干可执行子任务（Task），写入任务表并自动关联该目标。适合用户想推进目标、问「怎么拆」「怎么推进」时调用。",
            "parameters": {
                "type": "object",
                "properties": {"goal_id": {"type": "integer", "description": "目标 id"}},
                "required": ["goal_id"],
            },
        },
    },
]

if _GOAL_ENABLED:
    TOOLS += _GOAL_TOOLS


# ---------- P4-B：持久知识库工具（Feature Flag 门控）----------
# FEATURE_KNOWLEDGE_PLATFORM=true（默认）时把知识库工具追加进 schema；关闭即不注册。
try:
    import config as _cfg

    _KNOWLEDGE_ENABLED = bool(getattr(_cfg, "FEATURE_KNOWLEDGE_PLATFORM", False))
except Exception:
    _KNOWLEDGE_ENABLED = False

_KNOWLEDGE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add_knowledge",
            "description": "把一段文本/资料存入本地持久知识库（语义索引，日后相关问题时自动召回）。适合「把这段记到知识库」「保存这份资料」「存下来以后用」。参数：title 标题（可选），text 要入库的正文（必填）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "资料标题（可选，默认取正文前若干字）"},
                    "text": {"type": "string", "description": "要存入知识库的原文内容（必填）"},
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "archive_knowledge",
            "description": "把当前这段对话归档进本地知识库（自动切分+向量化，日后语义召回）。适合「把这次对话存进知识库」「归档本对话」「记住我们聊了什么」。无需参数，自动归档当前会话。",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]

if _KNOWLEDGE_ENABLED:
    TOOLS += _KNOWLEDGE_TOOLS


# ---------- Phase 2.4：意图驱动工具动态裁剪 ----------
# 命中明确意图时，只下发相关工具（省 token、降误调用）；无明确意图则下发全部（保持现状）。
_INTENT_TOOLS = {
    "profile_set": ["profile_set", "profile_get"],
    "profile_get": ["profile_get"],
    "reminder_set": ["reminder_set", "reminder_list"],
    "reminder_list": ["reminder_list"],
    "calculator": ["calculator"],
    "note_save": ["note_save", "note_list"],
    "note_list": ["note_list"],
    "get_time": ["get_time"],
    "set_task": ["set_task", "update_task_step", "complete_task", "task_list"],
    "update_task_step": ["update_task_step", "task_list"],
    "complete_task": ["complete_task", "task_list"],
    "task_list": ["task_list"],
    "file_read": ["file_read", "file_list"],
    "file_list": ["file_list"],
    "file_write": ["file_write", "file_read", "file_list"],
    "file_make_dir": ["file_make_dir", "file_list"],
    "file_delete": ["file_delete", "file_list"],
    "file_rename": ["file_rename", "file_list"],
    "list_processes": ["list_processes"],
    "kill_process": ["kill_process"],
    "run_shell": ["run_shell"],
    "session_run": ["run_shell", "session_state"],
    "install_software": ["install_software"],
    "web_fetch": ["web_fetch"],
    "browser_read": ["browser_read"],
    "scan_desktop": ["scan_desktop"],
    "scan_installed_software": ["scan_installed_software"],
    "manage_prefetch_task": ["manage_prefetch_task"],
    "tick_now": ["tick_now"],
    "memory_search": ["memory_search"],
    "web_search": ["web_search"],
    "media_generate": ["media_generate"],
    "social_send": ["social_send"],
    "asr_transcribe": ["asr_transcribe"],
    "get_weather": ["get_weather"],
    "get_hotspots": ["get_hotspots"],
    "open_hotspot_panel": ["open_hotspot_panel"],
    "typhoon_panel": ["typhoon_panel"],
    "person_card": ["person_card"],
    "map_query": ["map_query"],
    "open_doc_panel": ["open_doc_panel"],
    "open_memory_audit": ["open_memory_audit"],
    "review_output": ["review_output"],
    "play_video": ["play_video", "web_search"],
    "scan_resources": ["scan_resources"],
    "list_skills": ["list_skills"],
    "use_skill": ["use_skill"],
    "list_custom_tools": ["list_custom_tools"],
    "delete_custom_tool": ["delete_custom_tool"],
    "delegate_agent": ["delegate_agent"],
    "remember": ["remember"],
    "set_goal": ["set_goal", "list_goals", "update_goal"],
    "update_goal": ["update_goal", "list_goals"],
    "list_goals": ["list_goals"],
    "delete_goal": ["delete_goal", "list_goals"],
    "plan_goal": ["plan_goal", "list_goals", "set_task", "update_task_step", "task_list"],
}


def _merge_dynamic(base, allowed=None):
    """把工具工厂的动态自定义工具追加进 schema（去重）；若给定 allowed 白名单则仅保留白名单内工具。"""
    try:
        from tool_factory import dynamic_tool_schemas
        dyn = dynamic_tool_schemas()
    except Exception:
        dyn = []
    if not dyn:
        merged = base
    else:
        known = {b["function"]["name"] for b in base}
        merged = base + [d for d in dyn if d["function"]["name"] not in known]
    if allowed is not None:
        allowed_set = set(allowed)
        merged = [m for m in merged if m["function"]["name"] in allowed_set]
    return merged


def select_tools(text, allowed=None):
    """按用户意图动态裁剪要下发给 LLM 的 tool schema（Phase 2.4）。

    命中明确意图 → 只发相关工具；无明确意图（自由聊天）→ 发全部，避免漏调。
    为降低首 token 延迟：纯问候/极短闲聊不发工具，让模型直接回复。
    支持复合意图：一句同时问天气+热点，会同时下发两组工具。
    纯函数（基于 detect_intents 启发式，零密钥、无网络）。
    """
    t = (text or "").strip()
    intents = detect_intents(t)
    if intents:
        allowed = set()
        for name, _ in intents:
            names = _INTENT_TOOLS.get(name)
            if names:
                allowed.update(names)
        if allowed:
            return _merge_dynamic([t for t in TOOLS if t["function"]["name"] in allowed], allowed)
    # 无明确意图时：纯问候 / 闲聊 / 测试类短句不下发工具，避免 23 个 schema 拖慢首 token
    casual = r"^(你好|您好|嗨|哈喽|hello|hi|在吗|在么|在不在|早上好|晚上好|下午好|辛苦|谢|谢谢|多谢|测试|试一下|试下|随便|聊聊|聊下|聊两句|说说|说两句|你好啊|您好啊)[\s!！。，,]*$"
    if re.search(casual, t, re.I):
        return []
    # 兜底启发：无明确意图且文本较短（<=15 字符）的闲聊/测试，也不下发全量工具
    # 包含数字（可能是计算）、明显工具关键词的短句仍保留工具能力
    if len(t) <= 15 and not re.search(r"天气|温度|搜索|查|记|提醒|任务|文件|运行|抓取|画[^\w]|图|视频|音乐|算|计算|\d", t):
        return []
    return _merge_dynamic(TOOLS, allowed)


# ---------- 基础工具实现 ----------
def tool_get_time(args):
    from datetime import datetime

    now = datetime.now()
    city = (args.get("city") or "").strip()
    base = now.strftime("%Y年%m月%d日 %H:%M:%S 星期") + "一二三四五六日"[now.weekday()]
    return f"{city + ' ' if city else '本地 '}时间：{base}"


# 纯 AST 安全求值器：仅允许数字字面量、二元运算(+ - * / ** %)、一元正负号与括号。
# 不调用 eval，从根上杜绝代码执行风险（Phase 1.4 硬化）。
_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def _safe_eval(node):
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("仅支持数字")
    if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
        return _BINOPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.unaryop) in _UNARY:
        return _UNARY[type(node.unaryop)](_safe_eval(node.operand))
    raise ValueError("仅支持数字与 + - * / ** % 及括号")


def tool_calculator(args):
    # Phase 46.2 · 工具基线修复（STEP 1）：白名单式别名归一化 expression→expr。
    # 仅接受 expr / expression 两个键，不静默映射任意 key，不影响其他工具与 execute_tool 透传。
    expr = (args.get("expr") or args.get("expression") or "").strip()
    if not expr:
        return "错误：表达式为空"
    try:
        tree = ast.parse(expr, mode="eval")
        val = _safe_eval(tree)
        return f"{expr} = {val}"
    except Exception as e:
        return f"计算失败：{e}"


# ---------- Phase 3.2：文件 / Shell / Web 工具（全部经沙箱 + 审计） ----------


def tool_file_read(args):
    t0 = time.time()
    try:
        disabled, reason = _tool_disabled("file_read")
        if disabled:
            audit_tool("file_read", args, "disabled", reason, started_at=t0)
            return reason
        raw = args.get("path") or args.get("filename") or args.get("file_path") or ""
        if not raw:
            return "错误：未提供文件路径"
        resolved = resolve_in_sandbox(raw)
        if not os.path.isfile(resolved):
            return f"错误：文件不存在：{raw}"
        with open(resolved, encoding="utf-8", errors="replace") as f:
            content = f.read()
        lines = content.split("\n")
        start = max(1, int(args.get("start_line") or 1))
        if args.get("max_lines") is not None:
            end = min(len(lines), start + max(0, int(args["max_lines"])) - 1)
        elif args.get("end_line") is not None:
            end = min(len(lines), max(start, int(args["end_line"])))
        else:
            end = len(lines)
        selected = [] if (args.get("max_lines") == 0) else lines[start - 1 : end]
        body = "\n".join(selected)
        truncated = end < len(lines) or start > 1
        audit_tool("file_read", args, "ok", f"lines {start}-{end}/{len(lines)}", started_at=t0)
        return f"# 文件：{raw}（共 {len(lines)} 行，显示 {start}-{end} 行{'，已截断' if truncated else ''}）\n\n{body}"
    except Exception as e:
        audit_tool("file_read", args, "error", error=str(e), started_at=t0)
        return f"读取失败：{e}"


def tool_file_list(args):
    t0 = time.time()
    try:
        disabled, reason = _tool_disabled("file_list")
        if disabled:
            audit_tool("file_list", args, "disabled", reason, started_at=t0)
            return reason
        raw = args.get("path") or args.get("dir") or args.get("directory") or "."
        resolved = resolve_in_sandbox(raw)
        if not os.path.isdir(resolved):
            return f"错误：目录不存在：{raw}"
        entries = []
        for name in sorted(os.listdir(resolved)):
            full = os.path.join(resolved, name)
            entries.append(f"[{'目录' if os.path.isdir(full) else '文件'}] {name}")
        disp = "." if raw in (".", "/") else raw.replace("\\", "/")
        audit_tool("file_list", args, "ok", f"{len(entries)} entries", started_at=t0)
        return f"目录（相对路径）：{disp}\n\n" + ("\n".join(entries) or "（空目录）")
    except Exception as e:
        audit_tool("file_list", args, "error", error=str(e), started_at=t0)
        return f"列目录失败：{e}"


def tool_file_write(args):
    t0 = time.time()
    try:
        disabled, reason = _tool_disabled("file_write")
        if disabled:
            audit_tool("file_write", args, "disabled", reason, started_at=t0)
            return reason
        raw = args.get("path") or args.get("filename") or args.get("file_path") or ""
        content = args.get("content")
        if not raw:
            return "错误：未提供文件路径"
        if content is None:
            return "错误：未提供写入内容"
        resolved = resolve_in_sandbox(raw)
        assert_not_protected(resolved)
        os.makedirs(os.path.dirname(resolved) or config.SANDBOX_ROOT, exist_ok=True)
        with open(resolved, "w", encoding="utf-8") as f:
            f.write(content)
        # 读回校验
        with open(resolved, encoding="utf-8") as f:
            verified = f.read()
        ok = verified == content
        status = "ok" if ok else "error"
        audit_tool("file_write", args, status, f"bytes={len(content)} verified={ok}", started_at=t0)
        return f"{'已写入' if ok else '写入后校验失败'}：{raw}（{len(content)} 字符）"
    except Exception as e:
        audit_tool("file_write", args, "error", error=str(e), started_at=t0)
        return f"写入失败：{e}"


def tool_file_make_dir(args):
    t0 = time.time()
    try:
        disabled, reason = _tool_disabled("file_write")
        if disabled:
            audit_tool("file_make_dir", args, "disabled", reason, started_at=t0)
            return reason
        raw = args.get("path") or ""
        if not raw:
            return "错误：未提供目录路径"
        resolved = resolve_in_sandbox(raw)
        assert_not_protected(resolved)
        if os.path.isdir(resolved):
            audit_tool("file_make_dir", args, "ok", f"exists {raw}", started_at=t0)
            return f"目录已存在：{raw}"
        os.makedirs(resolved, exist_ok=True)
        audit_tool("file_make_dir", args, "ok", raw, started_at=t0)
        return f"已创建目录：{raw}"
    except Exception as e:
        audit_tool("file_make_dir", args, "error", error=str(e), started_at=t0)
        return f"创建目录失败：{e}"


def tool_file_delete(args):
    t0 = time.time()
    try:
        disabled, reason = _tool_disabled("file_write")
        if disabled:
            audit_tool("file_delete", args, "disabled", reason, started_at=t0)
            return reason
        raw = args.get("path") or ""
        if not raw:
            return "错误：未提供要删除的路径"
        resolved = resolve_in_sandbox(raw)
        assert_not_protected(resolved)
        if not (os.path.isfile(resolved) or os.path.isdir(resolved)):
            return f"错误：路径不存在：{raw}"
        if os.path.isfile(resolved):
            os.remove(resolved)
            audit_tool("file_delete", args, "ok", f"file {raw}", started_at=t0)
            return f"已删除文件：{raw}"
        recursive = bool(args.get("recursive"))
        if recursive:
            import shutil

            shutil.rmtree(resolved)
            audit_tool("file_delete", args, "ok", f"dir(recursive) {raw}", started_at=t0)
            return f"已递归删除目录：{raw}"
        try:
            os.rmdir(resolved)
            audit_tool("file_delete", args, "ok", f"dir {raw}", started_at=t0)
            return f"已删除空目录：{raw}"
        except OSError:
            return f"目录非空（{raw}）。如需连子内容一起删，请传 recursive=true。"
    except Exception as e:
        audit_tool("file_delete", args, "error", error=str(e), started_at=t0)
        return f"删除失败：{e}"


def tool_file_rename(args):
    t0 = time.time()
    try:
        disabled, reason = _tool_disabled("file_write")
        if disabled:
            audit_tool("file_rename", args, "disabled", reason, started_at=t0)
            return reason
        src = args.get("src") or ""
        dst = args.get("dst") or ""
        if not src or not dst:
            return "错误：需提供 src 与 dst"
        rsrc = resolve_in_sandbox(src)
        rdst = resolve_in_sandbox(dst)
        assert_not_protected(rsrc)
        assert_not_protected(rdst)
        if not (os.path.isfile(rsrc) or os.path.isdir(rsrc)):
            return f"错误：源路径不存在：{src}"
        if os.path.exists(rdst):
            return f"错误：目标已存在：{dst}"
        os.makedirs(os.path.dirname(rdst) or config.SANDBOX_ROOT, exist_ok=True)
        os.rename(rsrc, rdst)
        audit_tool("file_rename", args, "ok", f"{src} -> {dst}", started_at=t0)
        return f"已重命名：{src} → {dst}"
    except Exception as e:
        audit_tool("file_rename", args, "error", error=str(e), started_at=t0)
        return f"重命名失败：{e}"


def _safe_to_kill(name, pid):
    """拒绝杀死关键系统进程与小6自身后端，避免把系统或自己搞挂。"""
    if pid in (0, 4):
        return False, "系统保留进程（PID %s），拒绝操作" % pid
    critical = {
        "system", "smss.exe", "csrss.exe", "wininit.exe", "services.exe",
        "lsass.exe", "winlogon.exe", "registry.exe", "memory compression",
    }
    nm = (name or "").lower().strip()
    if nm in critical:
        return False, "关键系统进程（%s），拒绝终止以防系统崩溃" % name
    try:
        if pid == os.getpid():
            return False, "不能终止小6后端自身进程"
    except Exception:
        pass
    return True, ""


def tool_list_processes(args):
    t0 = time.time()
    try:
        query = (args.get("query") or "").strip().lower()
        limit = max(1, min(int(args.get("limit") or 30), 200))
        rows = []
        try:
            import psutil

            for p in psutil.process_iter(["pid", "name", "memory_info"]):
                try:
                    rows.append((p.info["pid"], p.info["name"], p.info["memory_info"].rss // (1024 * 1024)))
                except Exception:
                    pass
        except Exception:
            out = subprocess.run(
                ["tasklist", "/fo", "csv", "/nh"],
                capture_output=True, text=True, encoding="gbk", errors="replace", timeout=20,
            ).stdout
            import csv as _csv
            from io import StringIO

            for r in _csv.reader(StringIO(out)):
                if len(r) < 5:
                    continue
                name, pid_s, mem = r[0], r[1], r[4]
                mem_mb = 0
                try:
                    mem_mb = int(mem.replace(",", "").replace(" K", "").strip()) // 1024
                except Exception:
                    pass
                try:
                    pid = int(pid_s)
                except Exception:
                    pid = 0
                rows.append((pid, name, mem_mb))
        if query:
            rows = [r for r in rows if query in (r[1] or "").lower()]
        rows.sort(key=lambda x: x[2], reverse=True)
        rows = rows[:limit]
        if not rows:
            return "未找到匹配的进程" + (f"（query={query}）" if query else "")
        lines = [f"{pid:>7}  {mem:>6} MB  {name}" for pid, name, mem in rows]
        header = f"进程列表（共 {len(rows)} 条{'，按内存排序' if not query else f'，匹配「{query}」'}）："
        audit_tool("list_processes", args, "ok", f"{len(rows)} procs", started_at=t0)
        return header + "\n" + "\n".join(lines)
    except Exception as e:
        audit_tool("list_processes", args, "error", error=str(e), started_at=t0)
        return f"列出进程失败：{e}"


def tool_kill_process(args):
    t0 = time.time()
    try:
        disabled, reason = _tool_disabled("kill_process")
        if disabled:
            audit_tool("kill_process", args, "disabled", reason, started_at=t0)
            return reason
        pid = args.get("pid")
        name = (args.get("name") or "").strip()
        if pid is None and not name:
            return "错误：需提供 pid 或 name"
        if pid is not None:
            try:
                pid = int(pid)
            except Exception:
                return "错误：pid 必须为整数"
            pname = ""
            try:
                import psutil

                pname = psutil.Process(pid).name()
            except Exception:
                out = subprocess.run(
                    ["tasklist", "/fo", "csv", "/nh", "/fi", f"PID eq {pid}"],
                    capture_output=True, text=True, encoding="gbk", errors="replace", timeout=15,
                ).stdout
                m = re.search(r'"([^"]+\.exe)"', out)
                if m:
                    pname = m.group(1)
            ok, why = _safe_to_kill(pname, pid)
            if not ok:
                audit_tool("kill_process", args, "blocked", why, started_at=t0)
                return why
            cmd = ["taskkill", "/PID", str(pid), "/F"]
            target = f"PID {pid}"
        else:
            # 按名终止风险高：拒绝解释器/壳类名，避免误杀自身或系统
            nm = name.lower()
            if nm in ("python.exe", "python3.exe", "py.exe", "node.exe", "cmd.exe", "powershell.exe", "explorer.exe"):
                msg = f"拒绝按名终止「{name}」：过于宽泛，可能误杀小6后端或系统。请改用 pid 精确终止。"
                audit_tool("kill_process", args, "blocked", msg, started_at=t0)
                return msg
            ok, why = _safe_to_kill(name, -1)
            if not ok:
                audit_tool("kill_process", args, "blocked", why, started_at=t0)
                return why
            cmd = ["taskkill", "/IM", name, "/F"]
            target = name
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="gbk", errors="replace", timeout=20)
        out = (res.stdout or res.stderr or "").strip()
        if res.returncode == 0:
            audit_tool("kill_process", args, "ok", out[:120], started_at=t0)
            return f"已终止：{target}" + (f"\n{out}" if out else "")
        audit_tool("kill_process", args, "error", out[:200], started_at=t0)
        return f"终止失败（返回码 {res.returncode}）：{out}" if out else f"终止失败（返回码 {res.returncode}）"
    except Exception as e:
        audit_tool("kill_process", args, "error", error=str(e), started_at=t0)
        return f"终止进程异常：{e}"


def tool_run_shell(args):
    t0 = time.time()
    try:
        disabled, reason = _tool_disabled("run_shell")
        if disabled:
            audit_tool("run_shell", args, "disabled", reason, started_at=t0)
            return reason
        command = (args.get("command") or "").strip()
        if not command:
            return "错误：未提供命令"
        if is_dangerous_command(command):
            audit_tool("run_shell", args, "blocked", "dangerous command refused", started_at=t0)
            return "拒绝执行：检测到高危命令（rm -rf /、format、shutdown、mkfs、dd 等）。"
        use_session = bool(args.get("session"))
        timeout = args.get("timeout") or (60 if use_session else 30)
        cwd_rel = args.get("cwd")
        # 默认（无显式 cwd）也解析到沙箱根并建目录；避免 Windows 下 subprocess 用不存在的
        # cwd 触发 WinError 267（目录名称无效）。沙箱化是设计意图，命令一律在沙箱内执行。
        cwd = resolve_in_sandbox(cwd_rel) if cwd_rel else resolve_in_sandbox(".")
        os.makedirs(cwd, exist_ok=True)  # 确保工作目录存在，避免 cwd 无效
        if use_session:
            # —— 持久 shell 会话：跨命令保持 cwd / 环境变量 ——
            res = run_in_session(command, cwd=cwd, timeout=timeout)
            exit_code = res.get("exit", -1)
            out = res.get("stdout", "") or ""
            err = res.get("stderr", "") or ""
            text = (out + (("\n[stderr]\n" + err) if err else "")).strip()
            status = "ok" if exit_code == 0 else "error"
            audit_tool("run_shell", args, status, f"[session] exit={exit_code} out={len(text)}B", started_at=t0)
            tag = "（持久会话）" + ("（降级独立进程）" if res.get("fallback") else "")
            head = text[:4000]
            return f"$ {command}\n[exit {exit_code}]{tag}\n\n{head}" + (
                "\n…(输出过长已截断)" if len(text) > 4000 else ""
            )
        # —— 普通一次性命令 ——
        # Phase 47.2 C-06：默认 shell=False（参数列表）以消除命令注入面；
        # 仅当命令含 shell 元字符（管道/重定向/变量/命令链等）无法安全转为 argv 时，
        # 回退 shell=True（仍受上方 is_dangerous_command 黑名单兜底）。
        _shell_meta_re = re.compile(r"[|&;<>$`*?(){}\[\]!~]|`|\$\(|<<")
        if _shell_meta_re.search(command):
            proc = subprocess.run(
                command, shell=True,
                cwd=cwd or resolve_in_sandbox("."),
                capture_output=True, timeout=timeout,
            )
        else:
            try:
                _argv = shlex.split(command)
            except Exception:
                _argv = None
            if _argv:
                proc = subprocess.run(
                    _argv, shell=False,
                    cwd=cwd or resolve_in_sandbox("."),
                    capture_output=True, timeout=timeout,
                )
            else:
                proc = subprocess.run(
                    command, shell=True,
                    cwd=cwd or resolve_in_sandbox("."),
                    capture_output=True, timeout=timeout,
                )
        out = (proc.stdout or b"").decode("utf-8", "replace")
        err = (proc.stderr or b"").decode("utf-8", "replace")
        text = (out + (("\n[stderr]\n" + err) if err else "")).strip()
        code = proc.returncode
        status = "ok" if code == 0 else "error"
        audit_tool("run_shell", args, status, f"exit={code} out={len(text)}B", started_at=t0)
        head = text[:2000]
        return f"$ {command}\n[exit {code}]（cwd={cwd_rel or '.'}）\n\n{head}" + (
            "\n…(输出过长已截断)" if len(text) > 2000 else ""
        )
    except subprocess.TimeoutExpired:
        audit_tool("run_shell", args, "error", error=f"timeout {timeout}s", started_at=t0)
        return f"执行超时（{timeout}s）"
    except Exception as e:
        audit_tool("run_shell", args, "error", error=str(e), started_at=t0)
        return f"执行失败：{e}"


def tool_session_state(args):
    try:
        return session_state()
    except Exception as e:
        return f"查询持久会话状态失败：{e}"


def tool_reset_session(args):
    try:
        return reset_session()
    except Exception as e:
        return f"重置持久会话失败：{e}"


# ─────────────────────────────────────────────────────────────────────────────
# 本地软件安装（移植自参考实现 software-install，用小6架构重写）
# 流程：探测 winget → 解析候选（中文别名 / 明确 id / 搜索）→ 后台线程跑安装 →
#       用 scene 进度卡实时推给前端（push_scene_event + flush_scene_events）。
# ─────────────────────────────────────────────────────────────────────────────
_WINGET_ALIASES = [
    (r"^(qq|腾讯\s*qq|tencent\s*qq)$", ["Tencent.QQ.NT", "Tencent.QQ"]),
    (r"^(tim|腾讯\s*tim)$", ["Tencent.TIM"]),
    (r"^(wechat|weixin|微信|微信电脑版)$", ["Tencent.WeChat"]),
    (r"^(vscode|vs\s*code|visual\s*studio\s*code)$", ["Microsoft.VisualStudioCode"]),
    (r"^(chrome|谷歌浏览器|谷歌)$", ["Google.Chrome"]),
    (r"^(firefox|火狐|火狐浏览器)$", ["Mozilla.Firefox"]),
    (r"^(python3?|python\s*3)$", ["Python.Python.3.12", "Python.Python.3.11"]),
    (r"^(node|nodejs|node\.js)$", ["OpenJS.NodeJS.LTS"]),
    (r"^(git)$", ["Git.Git"]),
    (r"^(7zip|7-zip)$", ["7zip.7zip"]),
    (r"^(vlc)$", ["VideoLAN.VLC"]),
]


def _looks_like_winget_id(value):
    return bool(re.match(r"^[A-Za-z0-9][A-Za-z0-9_.-]+\.[A-Za-z0-9][A-Za-z0-9_.-]+$", str(value or "").strip()))


def _parse_winget_search(output):
    """解析 `winget search` 输出，返回 [{name, id, version}]（移植自参考实现）。"""
    lines = (output or "").replace("\r", "").split("\n")
    results = []
    in_rows = False
    for line in lines:
        if re.match(r"^-{3,}$", line.replace(" ", "")):
            in_rows = True
            continue
        if not in_rows or re.match(r"^Name\s+Id\s+Version", line, re.I):
            continue
        m = re.match(r"^(.+?)\s{2,}([A-Za-z0-9][A-Za-z0-9_.-]+\.[A-Za-z0-9][A-Za-z0-9_.-]+)\s{2,}(\S+)", line)
        if m:
            results.append({"name": m.group(1).strip(), "id": m.group(2).strip(), "version": m.group(3).strip()})
    return results


def _resolve_winget_candidates(query, package_id):
    ids = []
    if _looks_like_winget_id(package_id):
        ids.append(package_id)
    for pat, aids in _WINGET_ALIASES:
        if re.search(pat, query or "", re.I):
            ids += aids
    if _looks_like_winget_id(query):
        ids.append(query)
    out, seen = [], set()
    for i in ids:
        il = i.lower()
        if il in seen:
            continue
        seen.add(il)
        out.append({"id": i, "name": i})
    if not out and query:
        try:
            sp = subprocess.run(
                ["winget", "search", query, "--source", "winget",
                 "--accept-source-agreements", "--disable-interactivity"],
                capture_output=True, text=True, timeout=45, errors="replace",
            )
            for r in _parse_winget_search(sp.stdout or ""):
                rl = r["id"].lower()
                if rl in seen:
                    continue
                seen.add(rl)
                out.append(r)
        except Exception:
            pass
    return out[:6]


def _emit_install_card(card_id, display, percent, status, done=False, error=False):
    card = {
        "id": card_id,
        "kind": "progress",
        "title": f"安装 {display}",
        "percent": percent,
        "status": status,
        "action": "set",
    }
    if done:
        card["done"] = True
    if error:
        card["error"] = True
    push_scene_event(card)
    flush_scene_events()


def _install_worker(pkg_id, display, silent, card_id):
    """后台线程：跑 winget install，实时推进度卡。"""
    try:
        _emit_install_card(card_id, display, 45, "下载并安装中…")
        args = [
            "winget", "install", "--id", pkg_id, "--exact", "--source", "winget",
            "--accept-package-agreements", "--accept-source-agreements", "--disable-interactivity",
        ]
        if silent:
            args.append("--silent")
        proc = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            encoding="utf-8", errors="replace", bufsize=1,
        )
        pct = 45
        text_parts = []
        for line in proc:
            text_parts.append(line)
            low = line.lower()
            if "downloading" in low:
                pct = max(pct, 60)
            elif "installing" in low or "applying" in low or "verifying" in low:
                pct = max(pct, 80)
            _emit_install_card(card_id, display, pct, line.strip()[:60])
        proc.wait(timeout=300)
        text = "".join(text_parts)
        if proc.returncode == 0 or "successfully installed" in text.lower():
            _emit_install_card(card_id, display, 100, "已安装完成 ✓", done=True)
        elif "already installed" in text.lower() or "no applicable upgrade" in text.lower():
            _emit_install_card(card_id, display, 100, "已经装过了 / 已是最新 ✓", done=True)
        else:
            _emit_install_card(
                card_id, display, 90,
                f"安装失败（退出码 {proc.returncode}）", done=True, error=True,
            )
    except Exception as e:
        _emit_install_card(card_id, display, 90, f"安装异常：{e}", done=True, error=True)


def tool_install_software(args):
    query = (args.get("query") or args.get("name") or "").strip()
    pkg_id = (args.get("package_id") or args.get("id") or "").strip()
    silent = args.get("silent")
    silent = True if silent is None else bool(silent)
    if not query and not pkg_id:
        return "需要告诉我要装什么：给个软件名（query，如 微信）或明确的 winget id（package_id）。"
    # winget 可用性探测
    try:
        v = subprocess.run(["winget", "--version"], capture_output=True, text=True, timeout=15)
        if v.returncode != 0:
            return "本机没装 winget，没法用软件安装能力（Windows 10/11 一般自带，可在微软商店装 App Installer）。"
    except Exception:
        return "本机没装 winget，没法用软件安装能力。"
    candidates = _resolve_winget_candidates(query, pkg_id)
    if not candidates:
        return f"在 winget 里没找到「{query or pkg_id}」的候选包，换个名字或给个 winget id 试试？"
    top = candidates[0]
    display = top.get("name") or top.get("id")
    card_id = "install_" + re.sub(r"[^A-Za-z0-9]", "_", top["id"])[:40]
    # 立即推一张进度卡（检索阶段）
    _emit_install_card(card_id, display, 8, "正在检索 winget 源…")
    # 后台跑安装，不阻塞对话
    threading.Thread(
        target=_install_worker, args=(top["id"], display, silent, card_id), daemon=True
    ).start()
    return (
        f"已在后台开始安装「{display}」（winget id：{top['id']}），"
        f"界面会显示实时进度，装完自动更新。{'（已选最优候选；若想装别的版本，给我具体 winget id 即可）' if len(candidates) > 1 else ''}"
    )


def tool_web_fetch(args):
    t0 = time.time()
    try:
        url = (args.get("url") or args.get("link") or args.get("href") or "").strip()
        if not url:
            return "错误：未提供 URL"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; Xiao6/1.0)"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
            ctype = resp.headers.get("Content-Type", "")
        if "json" in ctype:
            text = data.decode("utf-8", "replace")
        else:
            # 简单去标签，保留可读文本
            raw = data.decode("utf-8", "replace")
            text = re.sub(r"<script[\s\S]*?</script>", "", raw, flags=re.IGNORECASE)
            text = re.sub(r"<style[\s\S]*?</style>", "", text, flags=re.IGNORECASE)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()
        audit_tool("web_fetch", args, "ok", f"{len(text)} chars", started_at=t0)
        return f"# 抓取：{url}\n\n{text[:3000]}" + ("\n…(内容过长已截断)" if len(text) > 3000 else "")
    except Exception as e:
        audit_tool("web_fetch", args, "error", error=str(e), started_at=t0)
        return f"抓取失败：{e}"


# ---------- 服务端「读网页」：清洗为正文（无 Chromium，走静态/SSR 渲染兜底） ----------
def _decode_html(data, ctype):
    """从响应字节里识别编码并解码（优先 Content-Type / <meta charset>，回退 utf-8/gbk）。"""
    cs = None
    m = re.search(rb"charset=([\w-]+)", (ctype or "").encode("utf-8", "replace"))
    if m:
        cs = m.group(1).decode("ascii", "replace").lower()
    if not cs:
        m = re.search(rb'<meta[^>]+charset=["\']?([\w-]+)', data[:4000], re.I)
        if m:
            cs = m.group(1).decode("ascii", "replace").lower()
    if cs in ("utf8",):
        cs = "utf-8"
    for cand in (cs, "utf-8", "gbk", "gb18030"):
        if not cand:
            continue
        try:
            return data.decode(cand)
        except Exception:
            pass
    return data.decode("utf-8", "replace")


def _readable_text(html):
    """从 HTML 抽标题/描述/正文：去脚本样式、剥离导航页脚等样板、折叠空白。"""
    html = re.sub(r"<!--[\s\S]*?-->", "", html, flags=re.I)
    # 先抽标题/描述（它们在 <head> 内，需在剥离 head 前取）
    tm = re.search(r"<title[^>]*>([\s\S]*?)</title>", html, re.I)
    title = re.sub(r"<[^>]+>", "", tm.group(1)).strip() if tm else ""
    desc = ""
    for pat in (
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']description',
        r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)',
    ):
        dm = re.search(pat, html, re.I)
        if dm:
            desc = dm.group(1).strip()
            break
    # 再剥离脚本/样式/样板标签
    html = re.sub(r"<(script|style|noscript|template|svg|head)[\s\S]*?</\1>", "", html, flags=re.I)
    main = None
    mm = re.search(r"<(article|main)[\s\S]*?</\1>", html, re.I)
    if mm:
        main = mm.group(0)
    else:
        bm = re.search(r"<body[\s\S]*?</body>", html, re.I)
        main = bm.group(0) if bm else html
    main = re.sub(r"<(nav|header|footer|aside|form)[\s\S]*?</\1>", "", main, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", main)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&[a-z]+;", " ", text, flags=re.I)
    text = re.sub(r"[ \t\r]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    text = text.strip()
    return title, desc, text


def tool_browser_read(args):
    t0 = time.time()
    try:
        url = (args.get("url") or args.get("link") or "").strip()
        if not url:
            return "错误：未提供 URL"
        if not re.match(r"^https?://", url, re.I):
            return "错误：仅支持 http/https 链接"
        max_chars = max(500, min(int(args.get("max_chars") or 6000), 20000))
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; Xiao6/1.0)"})
        data = None
        ctype = ""
        # 优先走代理（与 LLM 一致），失败再直连
        try:
            with _urlopen_with_proxy(req, 25) as resp:
                data = resp.read()
                ctype = resp.headers.get("Content-Type", "")
        except Exception:
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = resp.read()
                ctype = resp.headers.get("Content-Type", "")
        if data is None:
            return "错误：未能读取响应"
        html = _decode_html(data, ctype)
        title, desc, text = _readable_text(html)
        meta = []
        if title:
            meta.append("标题：" + title)
        if desc:
            meta.append("描述：" + desc)
        body = text[:max_chars]
        truncated = len(text) > max_chars
        head = f"# 网页阅读：{url}"
        if meta:
            head += "\n\n" + "\n".join(meta)
        result = head + f"\n\n（正文约 {len(text)} 字，显示前 {len(body)} 字）\n\n" + body
        if truncated:
            result += "\n…(正文过长已截断，可调大 max_chars)"
        audit_tool("browser_read", args, "ok", f"title={bool(title)} text={len(text)}", started_at=t0)
        return result
    except Exception as e:
        audit_tool("browser_read", args, "error", error=str(e), started_at=t0)
        return f"网页读取失败：{e}"


# ---------- 本机资源感知：桌面扫描 / 已装软件扫描 ----------
def tool_scan_desktop(args):
    t0 = time.time()
    try:
        dirs = []
        home = os.path.expanduser("~")
        for d in ("Desktop", "Documents", "Downloads"):
            p = os.path.join(home, d)
            if os.path.isdir(p):
                dirs.append(p)
        extra = args.get("path")
        if extra:
            rp = resolve_in_sandbox(extra) if not os.path.isabs(extra) else extra
            if os.path.isdir(rp):
                dirs.append(rp)
        limit = max(1, min(int(args.get("limit") or 50), 500))
        out = []
        total = 0
        for d in dirs:
            try:
                entries = []
                for name in sorted(os.listdir(d)):
                    full = os.path.join(d, name)
                    try:
                        st = os.stat(full)
                        is_dir = os.path.isdir(full)
                        size = 0 if is_dir else st.st_size
                        mtime = datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M")
                        entries.append((name, is_dir, size, mtime))
                    except Exception:
                        continue
                entries = entries[:limit]
                lines = []
                for name, is_dir, size, mtime in entries:
                    kind = "📁" if is_dir else "📄"
                    sz = "" if is_dir else "  %dKB" % (size // 1024)
                    lines.append("%s %s%s  · %s" % (kind, name, sz, mtime))
                out.append("## %s\n" % d + ("\n".join(lines) or "（空）"))
                total += len(entries)
            except Exception as e:
                out.append("## %s\n（无法读取：%s）" % (d, e))
        result = "桌面/文档/下载扫描结果：\n\n" + "\n\n".join(out)
        audit_tool("scan_desktop", args, "ok", "%d entries" % total, started_at=t0)
        return result
    except Exception as e:
        audit_tool("scan_desktop", args, "error", error=str(e), started_at=t0)
        return f"桌面扫描失败：{e}"


def tool_scan_installed_software(args):
    t0 = time.time()
    try:
        limit = max(1, min(int(args.get("limit") or 60), 500))
        items = []
        try:
            import winreg

            roots = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            ]
            seen = set()
            for hkey, sub in roots:
                try:
                    with winreg.OpenKey(hkey, sub) as k:
                        for i in range(winreg.QueryInfoKey(k)[0]):
                            kname = winreg.EnumKey(k, i)
                            try:
                                with winreg.OpenKey(k, kname) as sk:
                                    dn = winreg.QueryValueEx(sk, "DisplayName")[0]
                            except Exception:
                                continue
                            dn = (dn or "").strip()
                            if not dn or dn in seen:
                                continue
                            seen.add(dn)
                            ver = ""
                            try:
                                ver = winreg.QueryValueEx(sk, "DisplayVersion")[0]
                            except Exception:
                                pass
                            items.append(dn + (("  (%s)" % ver) if ver else ""))
                except Exception:
                    continue
        except ImportError:
            items = ["（非 Windows 平台，暂不支持注册表扫描）"]
        except Exception as e:
            items = ["扫描失败：%s" % e]
        items = items[:limit]
        result = ("已安装软件（共 %d 项）：\n\n" % len(items) + "\n".join("• " + it for it in items)) if items else "未检测到已安装软件。"
        audit_tool("scan_installed_software", args, "ok", "%d items" % len(items), started_at=t0)
        return result
    except Exception as e:
        audit_tool("scan_installed_software", args, "error", error=str(e), started_at=t0)
        return f"软件扫描失败：{e}"


# ---------- 通用预取任务（对齐参考实现 manage_prefetch_task） ----------
def _run_prefetch_task(task):
    """执行一条预取任务：按 source 取数，按 task_action 落盘或推送。返回结果文本。"""
    from datetime import datetime as _dt

    now = _dt.now()
    source = (task.get("source") or "web").strip().lower()
    query = (task.get("query") or "").strip()
    action = (task.get("task_action") or task.get("action") or "cache").strip().lower()
    content = ""
    try:
        if source == "hotspot":
            import hotspots as _hs

            data = _hs.get_hotspots(force=True)
            pls = (data or {}).get("platforms") or {}
            lines = []
            for p, its in pls.items():
                if not its:
                    continue
                lbl = _hs._platform_label(p) if hasattr(_hs, "_platform_label") else p
                lines.append("%s：" % lbl + "、".join(it.get("text", "") for it in its[:3]))
            content = "舆情预取：\n" + "\n".join(lines)
        elif source == "weather":
            import geo_weather as _gw

            w = _gw.get_weather(city=(query or None), mode="compact", force=True)
            card = (w or {}).get("card") or {}
            content = "天气预取：%s %s %s°（最高%s/最低%s）" % (
                card.get("city", ""), card.get("condition", ""), card.get("temp", ""),
                card.get("high", ""), card.get("low", ""))
        elif source in ("web", "url"):
            import urllib.request as _ur

            req = _ur.Request(query, headers={"User-Agent": "Mozilla/5.0 (compatible; Xiao6/1.0)"})
            try:
                with _urlopen_with_proxy(req, 25) as resp:
                    data = resp.read()
                    ctype = resp.headers.get("Content-Type", "")
            except Exception:
                with _ur.urlopen(req, timeout=25) as resp:
                    data = resp.read()
                    ctype = resp.headers.get("Content-Type", "")
            html = _decode_html(data, ctype)
            _, _, text = _readable_text(html)
            content = text[:4000]
        else:
            content = "（未知预取源：%s）" % source
    except Exception as e:
        content = "（预取执行失败：%s）" % e
    if action == "notify" and content:
        try:
            import proactive as _pa

            _pa.push_proactive("prefetch", "🔄 预取更新：「%s」\n%s" % (task.get("name", ""), content[:500]))
        except Exception:
            pass
    elif action == "cache" and content:
        try:
            conn = db_conn()
            exp = now.timestamp() + (task.get("interval") or 3600)
            conn.execute(
                "INSERT INTO prefetch_cache(source,content,fetched_at,expires_at,tags) VALUES(?,?,?,?,?) "
                "ON CONFLICT(source) DO UPDATE SET content=excluded.content,fetched_at=excluded.fetched_at,expires_at=excluded.expires_at",
                (task.get("name", source), content, now.strftime("%Y-%m-%d %H:%M:%S"),
                 _dt.fromtimestamp(exp).strftime("%Y-%m-%d %H:%M:%S"), "[]"),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass
    try:
        conn = db_conn()
        nxt = now.timestamp() + (task.get("interval") or 3600)
        conn.execute(
            "UPDATE prefetch_tasks SET last_run=?, next_run=? WHERE id=?",
            (now.strftime("%Y-%m-%d %H:%M:%S"), _dt.fromtimestamp(nxt).strftime("%Y-%m-%d %H:%M:%S"), task["id"]),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass
    return content


def tool_manage_prefetch_task(args):
    t0 = time.time()
    try:
        from datetime import datetime as _dt

        action = (args.get("action") or "list").strip().lower()
        conn = db_conn()
        now = _dt.now()
        if action == "add":
            name = (args.get("name") or "").strip()
            if not name:
                conn.close()
                return "错误：add 需要 name"
            source = (args.get("source") or "web").strip().lower()
            interval = max(60, int(args.get("interval") or 3600))
            task_action = (args.get("task_action") or "cache").strip().lower() or "cache"
            iv = now.timestamp() + interval
            conn.execute(
                "INSERT INTO prefetch_tasks(name,source,query,action,interval,enabled,created,next_run) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (name, source, (args.get("query") or "").strip(), task_action, interval, 1,
                 now.strftime("%Y-%m-%d %H:%M:%S"), _dt.fromtimestamp(iv).strftime("%Y-%m-%d %H:%M:%S")),
            )
            conn.commit(); conn.close()
            audit_tool("manage_prefetch_task", args, "ok", "add %s" % name, started_at=t0)
            return "已添加预取任务：%s（源=%s，间隔=%ds，动作=%s）" % (name, source, interval, task_action)
        if action == "list":
            rows = conn.execute(
                "SELECT id,name,source,query,action,interval,enabled,last_run,next_run FROM prefetch_tasks ORDER BY id"
            ).fetchall()
            conn.close()
            if not rows:
                return "当前没有预取任务。用 action=add 创建，例如每天预取天气或舆情。"
            lines = []
            for r in rows:
                lines.append("#%d %s | 源=%s | 动作=%s | 间隔=%ds | 启用=%s | 上次=%s | 下次=%s" % (
                    r[0], r[1], r[2], r[4], r[5], "是" if r[6] else "否", r[7] or "从未", r[8] or "-"))
            return "预取任务列表：\n" + "\n".join(lines)
        if action in ("update", "remove", "run"):
            tid = int(args.get("id") or 0)
            if not tid:
                conn.close()
                return "错误：需要 id"
            row = conn.execute(
                "SELECT id,name,source,query,action,interval,enabled FROM prefetch_tasks WHERE id=?", (tid,)
            ).fetchone()
            if not row:
                conn.close()
                return "错误：预取任务 #%d 不存在" % tid
            if action == "remove":
                conn.execute("DELETE FROM prefetch_tasks WHERE id=?", (tid,))
                conn.commit(); conn.close()
                audit_tool("manage_prefetch_task", args, "ok", "remove %d" % tid, started_at=t0)
                return "已删除预取任务 #%d" % tid
            if action == "update":
                if args.get("name") is not None:
                    conn.execute("UPDATE prefetch_tasks SET name=? WHERE id=?", (args["name"], tid))
                if args.get("source") is not None:
                    conn.execute("UPDATE prefetch_tasks SET source=? WHERE id=?", (args["source"], tid))
                if args.get("query") is not None:
                    conn.execute("UPDATE prefetch_tasks SET query=? WHERE id=?", (args["query"], tid))
                if args.get("task_action") is not None:
                    conn.execute("UPDATE prefetch_tasks SET action=? WHERE id=?", (args["task_action"], tid))
                if args.get("interval") is not None:
                    iv = max(60, int(args["interval"]))
                    conn.execute("UPDATE prefetch_tasks SET interval=?, next_run=? WHERE id=?",
                                 (iv, _dt.fromtimestamp(now.timestamp() + iv).strftime("%Y-%m-%d %H:%M:%S"), tid))
                if args.get("enabled") is not None:
                    conn.execute("UPDATE prefetch_tasks SET enabled=? WHERE id=?", (1 if args["enabled"] else 0, tid))
                conn.commit(); conn.close()
                audit_tool("manage_prefetch_task", args, "ok", "update %d" % tid, started_at=t0)
                return "已更新预取任务 #%d" % tid
            if action == "run":
                task = {"id": row[0], "name": row[1], "source": row[2], "query": row[3], "action": row[4], "interval": row[5]}
                conn.close()
                content = _run_prefetch_task(task)
                audit_tool("manage_prefetch_task", args, "ok", "run %d" % tid, started_at=t0)
                return "已立即执行预取任务 #%d：\n\n" % tid + (content[:1500] or "（无内容）")
        if action == "run_all":
            rows = conn.execute(
                "SELECT id,name,source,query,action,interval FROM prefetch_tasks WHERE enabled=1"
            ).fetchall()
            conn.close()
            if not rows:
                return "没有启用的预取任务。"
            done = 0
            for r in rows:
                task = {"id": r[0], "name": r[1], "source": r[2], "query": r[3], "action": r[4], "interval": r[5]}
                try:
                    _run_prefetch_task(task); done += 1
                except Exception:
                    pass
            audit_tool("manage_prefetch_task", args, "ok", "run_all %d" % done, started_at=t0)
            return "已执行 %d 条启用的预取任务。" % done
        conn.close()
        return "错误：未知 action（add/list/update/remove/run/run_all）"
    except Exception as e:
        audit_tool("manage_prefetch_task", args, "error", error=str(e), started_at=t0)
        return f"预取任务管理失败：{e}"


# ---------- 抢占插队：立即触发 TICK 主动扫描 ----------
def tool_tick_now(args):
    """立即触发一次 TICK 主动扫描（抢占插队，对齐参考实现优先级队列插队）。"""
    t0 = time.time()
    try:
        import proactive

        kind = (args.get("kind") or "all").strip().lower()
        if kind not in ("hotspot", "weather", "rules", "prefetch", "reminders", "all"):
            kind = "all"
        proactive.request_immediate_scan(kind)
        audit_tool("tick_now", args, "ok", "kind=%s" % kind, started_at=t0)
        label = {
            "hotspot": "舆情热点",
            "weather": "天气",
            "rules": "自动化规则",
            "prefetch": "预取任务",
            "reminders": "到期提醒",
            "all": "全部主动扫描",
        }.get(kind, kind)
        return "已插队，小6将立即执行%s（通常几秒内完成）。" % label
    except Exception as e:
        audit_tool("tick_now", args, "error", error=str(e), started_at=t0)
        return f"立即扫描触发失败：{e}"


# ---------- 本地向量语义召回（对齐参考实现本地向量 RAG） ----------
def tool_memory_search(args):
    """用自然语言做语义检索，召回最相关的笔记/记忆。"""
    t0 = time.time()
    try:
        from embed import memory_search, model_ready

        q = (args.get("query") or "").strip()
        if not q:
            return "错误：查询为空"
        if not model_ready():
            return "语义检索模型尚未就绪（缺少 bge ONNX 模型）。"
        top_k = int(args.get("top_k") or 5)
        results = memory_search(q, top_k=max(1, min(top_k, 10)))
        audit_tool("memory_search", args, "ok", "hits=%d" % len(results), started_at=t0)
        if not results:
            return "没有找到语义相关的记忆。"
        lines = []
        for i, r in enumerate(results, 1):
            scope = "笔记" if r["scope"] == "note" else "记忆"
            lines.append("【%d·%s·%.2f】%s" % (i, scope, r["score"], r["text"][:200]))
        return "语义召回结果：\n" + "\n".join(lines)
    except Exception as e:
        audit_tool("memory_search", args, "error", error=str(e), started_at=t0)
        return f"语义检索失败：{e}"


def _ddg_search(query, limit):
    """免密钥实时搜索兜底：抓取 DuckDuckGo HTML 结果页并解析标题/链接/摘要。"""
    url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    )
    with _urlopen_with_proxy(req, 20) as resp:
        html = resp.read().decode("utf-8", "replace")
    items = []
    for m in re.finditer(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.S):
        href = m.group(1)
        title = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        real = href
        um = re.search(r"uddg=([^&]+)", href)
        if um:
            real = urllib.parse.unquote(um.group(1))
        snippet = ""
        chunk = html[m.end(): m.end() + 800]
        sm = re.search(r'class="result__snippet"[^>]*>(.*?)</a>', chunk, re.S)
        if not sm:
            sm = re.search(r'class="result__snippet"[^>]*>(.*?)</td>', chunk, re.S)
        if sm:
            snippet = re.sub(r"<[^>]+>", "", sm.group(1)).strip()
        items.append({"title": title, "url": real, "content": snippet})
        if len(items) >= limit:
            break
    return items


def _bing_search(query, limit):
    """免密钥兜底（Bing）：全球可达，解析 b_algo 结果块。"""
    url = "https://www.bing.com/search?q=" + urllib.parse.quote(query)
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    )
    with _urlopen_with_proxy(req, 20) as resp:
        html = resp.read().decode("utf-8", "replace")
    items = []
    for m in re.finditer(r'<li class="b_algo"[^>]*>(.*?)</li>', html, re.S):
        block = m.group(1)
        am = re.search(r'<h[23][^>]*>.*?<a[^>]*href="(https?://[^"]+)"', block, re.S)
        if not am:
            am = re.search(r'<a[^>]*href="(https?://[^"]+)"', block)
        if not am:
            continue
        href = am.group(1)
        ta = re.search(r'<a[^>]*href="%s"[^>]*>(.*?)</a>' % re.escape(href), block, re.S)
        title = re.sub(r"<[^>]+>", "", ta.group(1)).strip() if ta else href
        sm = re.search(r"<p[^>]*>(.*?)</p>", block, re.S)
        snippet = re.sub(r"<[^>]+>", "", sm.group(1)).strip() if sm else ""
        items.append({"title": title, "url": href, "content": snippet})
        if len(items) >= limit:
            break
    return items


def _baidu_search(query, limit):
    """免密钥兜底（Baidu）：国内可达，解析搜索结果块。"""
    url = "https://www.baidu.com/s?wd=" + urllib.parse.quote(query)
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    )
    with _urlopen_with_proxy(req, 20) as resp:
        html = resp.read().decode("utf-8", "replace")
    items = []
    for m in re.finditer(r'<div class="result[^"]*"[^>]*>(.*?)</div>\s*</div>', html, re.S):
        block = m.group(1)
        am = re.search(r'<h3[^>]*>.*?<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', block, re.S)
        if not am:
            continue
        href = am.group(1)
        title = re.sub(r"<[^>]+>", "", am.group(2)).strip()
        sm = re.search(r'class="content-right_.*?">(.*?)</span>|<div class="c-abstract[^"]*">(.*?)</div>', block, re.S)
        snippet = re.sub(r"<[^>]+>", "", (sm.group(1) or sm.group(2) or "")).strip()
        if title:
            items.append({"title": title, "url": href, "content": snippet})
        if len(items) >= limit:
            break
    return items


def _keyless_search(query, limit):
    """免密钥实时搜索聚合：依次尝试 Bing → Baidu → DuckDuckGo，返回首个成功的结果。"""
    for fn in (_bing_search, _baidu_search, _ddg_search):
        try:
            items = fn(query, limit)
            if items:
                return items
        except Exception:
            continue
    return []


def tool_remember(args):
    """把一条重要事实/决定/承诺显式存入情节记忆（"记住这个"）。"""
    t0 = time.time()
    content = (args.get("content") or "").strip()
    if not content:
        return "错误：要记住的内容为空"
    category = (args.get("category") or "fact").strip()
    try:
        importance = float(args.get("importance") or 0.7)
    except Exception:
        importance = 0.7
    importance = max(0.0, min(1.0, importance))
    try:
        from cognitive.episodic import add_episode

        eid = add_episode(content[:40], content, category, importance)
        audit_tool("remember", args, "ok", "eid=%s" % eid, started_at=t0)
        return "已记住：「%s」（类别 %s）。" % (content[:40], category)
    except Exception as e:
        audit_tool("remember", args, "error", error=str(e), started_at=t0)
        return f"记忆失败：{e}"


def tool_add_knowledge(args):
    """P4-B：把一段文本存入本地持久知识库（切分 + 本地向量化）。"""
    t0 = time.time()
    text = (args.get("text") or "").strip()
    if not text:
        return "错误：要存入知识库的文本为空"
    title = (args.get("title") or text[:40]).strip()[:120]
    try:
        import knowledge

        # Order 4：透传 memory_id，使 MEMORY_CREATED 与 MEMORY_STORED/LINKED 共享同一 id（单一来源）
        memory_id = args.get("memory_id")
        doc_id = knowledge.ingest_document(title, text, source="chat_tool", memory_id=memory_id)
        if not doc_id:
            return "存入失败：嵌入模型未就绪或文本无法切分（请确认本地 embedding 模型已下载）。"
        audit_tool("add_knowledge", args, "ok", "doc=%s" % doc_id, started_at=t0)
        return "已存入知识库：「%s」（文档ID %s，已切分语义索引，日后相关问题会自动召回）。" % (title, doc_id)
    except Exception as e:
        audit_tool("add_knowledge", args, "error", error=str(e), started_at=t0)
        return f"存入知识库失败：{e}"


def tool_archive_knowledge(args):
    """P4-B：把当前会话归档进本地知识库。"""
    t0 = time.time()
    session = globals().get("_current_session") or "default"
    goal_id = globals().get("_current_goal_id")
    mode = globals().get("_current_mode") or "smart"
    try:
        import knowledge

        doc_id = knowledge.archive_conversation(session)
        if not doc_id:
            return "归档失败：当前会话没有聊天记录或嵌入模型未就绪。"
        audit_tool("archive_knowledge", args, "ok", "doc=%s session=%s" % (doc_id, session), started_at=t0)
        return "已把当前对话归档进知识库（文档ID %s），日后相关问题会自动语义召回。" % doc_id
    except Exception as e:
        audit_tool("archive_knowledge", args, "error", error=str(e), started_at=t0)
        return f"归档失败：{e}"


def tool_web_search(args):
    t0 = time.time()
    try:
        query = (args.get("query") or args.get("q") or "").strip()
        if not query:
            return "错误：未提供搜索关键词"
        # 引擎解析：优先参数里的 engine，否则用全局设置
        engine = (args.get("engine") or WEB_SEARCH_ENGINE or "tavily").lower()
        key, engine = web_search_credentials(engine)
        limit = max(1, min(10, int(args.get("limit") or 5)))
        # 免密钥兜底：未配置任何搜索密钥时，用 Bing/Baidu/DuckDuckGo 实时检索（不消耗积分）
        if not key:
            try:
                items = _keyless_search(query, limit)
                lines = []
                for it in items[:limit]:
                    lines.append(
                        f"- {it.get('title', '')}\n  {it.get('url', '')}\n  {str(it.get('content', '')[:200])}"
                    )
                audit_tool("web_search", args, "ok", f"keyless {len(items)} results", started_at=t0)
                return f"# 实时搜索：{query}\n\n" + ("\n".join(lines) or "（无结果）")
            except Exception as e:
                audit_tool("web_search", args, "error", error=str(e), started_at=t0)
                return f"实时搜索（免密钥兜底）失败：{e}"
        items = []
        try:
            if engine == "tavily":
                body = json.dumps({"api_key": key, "query": query, "max_results": limit}).encode("utf-8")
                req = urllib.request.Request(
                    "https://api.tavily.com/search",
                    data=body,
                    headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=20) as resp:
                    payload = json.loads(resp.read().decode("utf-8", "replace"))
                items = payload.get("results") or []
            elif engine == "serper":
                req = urllib.request.Request(
                    f"https://google.serper.dev/search?q={urllib.parse.quote(query)}&num={limit}",
                    headers={"X-API-KEY": key, "Accept": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=20) as resp:
                    payload = json.loads(resp.read().decode("utf-8", "replace"))
                items = payload.get("organic_results") or []
            elif engine == "brave":
                req = urllib.request.Request(
                    f"https://api.search.brave.com/res/v1/web/search?q={urllib.parse.quote(query)}&count={limit}",
                    headers={"Accept": "application/json", "X-Subscription-Token": key},
                )
                with urllib.request.urlopen(req, timeout=20) as resp:
                    payload = json.loads(resp.read().decode("utf-8", "replace"))
                items = payload.get("web", {}).get("results") or []
            elif engine == "jina":
                # Jina Reader：把一个 URL 转成正文；这里用作搜索网关（s.jina.ai）
                req = urllib.request.Request(
                    f"https://s.jina.ai/{urllib.parse.quote(query)}",
                    headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=20) as resp:
                    text = resp.read().decode("utf-8", "replace")
                items = [{"title": query, "url": "", "content": text[:800]}]
            elif engine == "searxng":
                # 自建 SearXNG 实例
                req = urllib.request.Request(
                    f"{key.rstrip('/')}/search?q={urllib.parse.quote(query)}&format=json",
                    headers={"Accept": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=20) as resp:
                    payload = json.loads(resp.read().decode("utf-8", "replace"))
                items = payload.get("results") or []
            else:
                # 兜底：通用 GET + X-API-KEY（ddg 等）
                req = urllib.request.Request(
                    f"https://api.{engine}.com/search?q={urllib.parse.quote(query)}&num={limit}",
                    headers={"X-API-KEY": key, "Accept": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=20) as resp:
                    payload = json.loads(resp.read().decode("utf-8", "replace"))
                items = payload.get("organic_results") or payload.get("webPages", {}).get("value") or []
        except Exception:
            items = []
        lines = []
        for it in items[:limit]:
            if isinstance(it, dict):
                lines.append(
                    f"- {it.get('title', '')}\n  {it.get('url', it.get('link', ''))}\n  {str(it.get('content', it.get('snippet', ''))[:200])}"
                )
            else:
                lines.append(f"- {it}")
        audit_tool("web_search", args, "ok", f"{len(items)} results", started_at=t0)
        return f"# 搜索：{query}\n\n" + ("\n".join(lines) or "（无结果）")
    except Exception as e:
        audit_tool("web_search", args, "error", error=str(e), started_at=t0)
        return f"搜索失败：{e}"


# ---------- Phase 4：外部接口工具（媒体/社交/ASR，全部 env 门控 + 优雅降级） ----------


def tool_media_generate(args):
    t0 = time.time()
    kind = (args.get("kind") or "").strip().lower()
    prompt = (args.get("prompt") or "").strip()
    if not kind or not prompt:
        return "错误：media_generate 需要 kind（image/video/music）与 prompt"
    opts = {}
    if args.get("title"):
        opts["title"] = args["title"]
    if args.get("aspect_ratio"):
        opts["aspect_ratio"] = args["aspect_ratio"]
    url, err = media_generate(kind, prompt, **opts)
    if err:
        # 未启用 / 失败：审计为 disabled 或 error，绝不阻断主链路
        audit_tool("media_generate", args, "disabled" if "未启用" in err else "error", err[:120], started_at=t0)
        return f"媒体生成（{kind}）：{err}"
    audit_tool("media_generate", args, "ok", f"{kind} -> {url}", started_at=t0)
    return f"媒体生成成功（{kind}）：{url}"


def tool_social_send(args):
    t0 = time.time()
    platform = (args.get("platform") or "").strip().lower()
    target = (args.get("target") or "").strip()
    text = (args.get("text") or "").strip()
    # 微信 webhook 接收方已在 webhook 中，允许 target 为空；其余平台需 target
    target_required = platform not in ("wechat",)
    if not platform or not text or (target_required and not target):
        return "错误：social_send 需要 platform / text" + (" / target" if target_required else "")
    ok, err = social_send(platform, target, text)
    if not ok:
        audit_tool(
            "social_send", args, "disabled" if "未启用" in (err or "") else "error", (err or "")[:120], started_at=t0
        )
        return f"社交推送（{platform}）：{err}"
    audit_tool("social_send", args, "ok", f"{platform} -> {target}", started_at=t0)
    return f"已向 {platform} 推送消息。"


def tool_asr_transcribe(args):
    t0 = time.time()
    path = (args.get("path") or "").strip()
    if not path:
        return "错误：asr_transcribe 需要 path（音频文件路径）"
    # 经沙箱约束（与文件工具一致），防止越界读取
    try:
        resolved = resolve_in_sandbox(path)
    except Exception as e:
        audit_tool("asr_transcribe", args, "error", f"sandbox: {e}", started_at=t0)
        return f"路径不合规：{e}"
    text, err = asr_transcribe(resolved)
    if err:
        audit_tool("asr_transcribe", args, "disabled" if "未启用" in err else "error", err[:120], started_at=t0)
        return f"语音转写：{err}"
    audit_tool("asr_transcribe", args, "ok", f"{len(text or '')} chars", started_at=t0)
    return f"# 语音转写结果\n\n{text}"


def tool_weather(args):
    """查询天气：返回给 LLM 的文字摘要；结构化结果已由 weather.get_weather 暂存，供弹窗读取。"""
    from weather import get_weather

    city = (args.get("city") or "").strip() or None
    d = get_weather(city)
    if not d.get("ok"):
        return f"# 天气获取失败\n\n{d.get('error', '未知错误')}"
    return d.get("summary", "天气获取成功，但无摘要。")


def tool_hotspots(args):
    """获取实时热点热榜：强制刷新缓存，返回给 LLM 的紧凑摘要（默认每平台 Top3，适合聊天回复）。"""
    from hotspots import get_hotspots

    platform = (args.get("platform") or "").strip() or None
    force = bool(args.get("force", True))  # 聊天触发默认强制刷新
    limit = max(1, min(10, int(args.get("limit") or 3)))  # 每平台条数，默认 3
    d = get_hotspots(force=force)
    if not d.get("ok"):
        return f"# 热点获取失败\n\n{d.get('error', '未知错误')}"
    platforms = d.get("platforms", {})
    if platform:
        items = platforms.get(platform, [])
        lines = [f"{i + 1}. {it['text']}（热 {it['heat']}）" for i, it in enumerate(items[:limit])]
        return (
            f"# {PLATFORM_LABELS.get(platform, platform)} 实时热榜\n\n"
            + "\n".join(lines)
            + f"\n\n更新时间：{d.get('fetchedAt')}"
        )
    # 全部平台摘要
    parts = []
    for key, label in PLATFORM_LABELS.items():
        items = platforms.get(key, [])
        if not items:
            continue
        top = items[:limit]
        parts.append(f"## {label}\n" + "\n".join(f"{i + 1}. {it['text']}（{it['heat']}）" for i, it in enumerate(top)))
    return "# 实时热点热榜\n\n" + "\n\n".join(parts) + f"\n\n更新时间：{d.get('fetchedAt')}"


def tool_open_hotspot_panel(args):
    """打开全屏热点面板：返回给 LLM 的提示文本，前端会同步收到 panel 事件并打开热点大屏。"""
    return "好嘞，热点大屏这就给你拉开～"


def tool_typhoon_panel(args):
    """查询台风信息：抓取中央气象台活跃/近期台风，返回给 LLM 的紧凑文字摘要（供聊天回复）。"""
    from typhoon import get_typhoon

    force = bool(args.get("force", False))
    d = get_typhoon(force=force)
    if not d.get("ok"):
        return f"# 台风信息获取失败\n\n{d.get('error', '未知错误')}"
    active = d.get("active") or []
    if not active:
        recent = d.get("recent") or []
        tail = ""
        if recent:
            tail = "\n\n近期（已停编）：" + "、".join(
                f"{r.get('name', '?')}({r.get('intlid', '?')})" for r in recent[:5]
            )
        return (
            "# 台风信息\n\n"
            + (d.get("note") or "当前西北太平洋无活跃台风。")
            + tail
            + f"\n\n数据源：{d.get('source', '')}\n更新时间：{d.get('fetched_at', '')}"
        )
    lines = [
        f"{i + 1}. {t.get('name', '?')}（{t.get('enname', '?')} / 编号 {t.get('intlid', '?')}）"
        for i, t in enumerate(active[:15])
    ]
    return (
        "# 台风信息（活跃）\n\n"
        + "\n".join(lines)
        + f"\n\n（共 {len(active)} 个活跃台风）\n数据源：{d.get('source', '')}\n更新时间：{d.get('fetched_at', '')}"
    )


def tool_person_card(args):
    """人物卡：本地结构化人物档案的保存/查询/列举（零外部依赖）。"""
    from person_card import get_card, list_cards, save_card, format_card

    action = (args.get("action") or "").strip().lower()
    if action == "list":
        cards = list_cards()
        if not cards:
            return "你还没有保存任何人物卡。想记一个人就说「存一张人物卡：张三，身份 XX，事实 XX」。"
        lines = [f"# 我的人物卡（共 {len(cards)} 张）\n"]
        for c in cards:
            lines.append(f"• {c.get('name', '?')} — {c.get('identity', '')}")
        return "\n".join(lines)
    if action == "save":
        name = (args.get("name") or "").strip()
        if not name:
            return "没存成：save 操作需要传 name（人物姓名）。"
        card = save_card(
            name,
            identity=(args.get("identity") or "").strip(),
            facts=args.get("facts") or [],
            tags=args.get("tags") or [],
            relation=(args.get("relation") or "").strip(),
        )
        if not card:
            return "没存成：name 不能为空。"
        return "人物卡已保存/更新 ✅\n\n" + format_card(card)
    # 默认 get
    name = (args.get("name") or "").strip()
    if not name:
        return "查人物卡需要传 name（人物姓名）。"
    card = get_card(name)
    if not card:
        return f"没有找到「{name}」的人物卡。想新建就说「存一张人物卡：{name}，身份 …」。"
    return format_card(card)


# —— 视频播放：把「看视频」意图转化为前端全屏播放面板 ——
_PENDING_VIDEO = None  # (url, title)，供 server 在工具执行后读取并发 panel 事件

def set_pending_video(url, title=""):
    global _PENDING_VIDEO
    _PENDING_VIDEO = {"url": url, "title": title or ""}

def get_pending_video():
    return _PENDING_VIDEO

def clear_pending_video():
    global _PENDING_VIDEO
    _PENDING_VIDEO = None


# ── 新面板暂存（供 server 在工具执行后读取并发 panel 事件）──
_PENDING_MAP = None
_PENDING_REVIEW = None


def get_pending_map():
    return _PENDING_MAP


def clear_pending_map():
    global _PENDING_MAP
    _PENDING_MAP = None


def get_pending_review():
    return _PENDING_REVIEW


def clear_pending_review():
    global _PENDING_REVIEW
    _PENDING_REVIEW = None


def _last_assistant_turn(limit=1):
    """取最近一条小6(xiao6)回复文本，供审视分身默认审视。"""
    try:
        from db import db_conn
        conn = db_conn()
        rows = conn.execute(
            "SELECT content FROM chat_log WHERE role=? ORDER BY id DESC LIMIT ?",
            ("xiao6", limit),
        ).fetchall()
        conn.close()
        if rows:
            return (rows[0][0] or "").strip()
    except Exception:
        pass
    return ""


def tool_map_query(args):
    """地图服务：解析距离/坐标/城市列表查询，返回文字摘要并暂存面板数据。"""
    from map_service import map_query as _mq
    q = (args.get("query") or "").strip()
    if not q:
        return "想查什么地理信息？比如「北京到上海多远」「成都坐标」「有哪些城市」。"
    text, payload = _mq(q)
    global _PENDING_MAP
    _PENDING_MAP = payload
    return text


def tool_open_doc_panel(args):
    """打开文档面板（前端拉取列表）。"""
    return "文档面板这就给你拉开～"


def tool_open_memory_audit(args):
    """打开记忆审计面板（前端拉取统计）。"""
    return "记忆审计面板已打开，来看看我都记了些什么～"


def tool_scan_resources(args):
    """扫描本机资源（桌面/已装软件/SSH 主机/Git 仓库）并汇总摘要。"""
    from resource_scan import scan_resources, format_scan

    scope = (args.get("scope") or "all").strip().lower()
    if scope not in ("all", "desktop", "software", "ssh", "git"):
        scope = "all"
    try:
        results = scan_resources(scope)
        return format_scan(results)
    except Exception as e:
        return "本机资源扫描失败：%s" % e


def tool_list_skills(args):
    """列出本地可用技能清单。"""
    from skills import list_skills

    try:
        items = list_skills()
    except Exception as e:
        return "技能列表加载失败：%s" % e
    if not items:
        return "当前没有已安装的本地技能（在 skills/ 目录放入带 SKILL.md 的技能即可）。"
    lines = ["本地可用技能 %d 个：" % len(items)]
    for it in items:
        triggers = "、".join(it.get("trigger") or [])
        lines.append("· %s —— %s（触发词：%s）" % (it.get("name"), it.get("description"), triggers))
    return "\n".join(lines)


def tool_use_skill(args):
    """加载并应用一个指定技能，把正文注入上下文。"""
    from skills import retrieve_skill, list_skills

    name = (args.get("name") or "").strip()
    if not name:
        return "请告诉我技能名称，例如「示例技能」。"
    try:
        sk = retrieve_skill(name)
        if not sk:
            # 精确未命中 → 模糊匹配（名称包含 / 触发词包含）
            q = name.replace("技能", "").strip()
            for it in list_skills():
                nm = it.get("name", "")
                trg = " ".join(it.get("trigger") or [])
                if (q and q in nm) or (q and q in trg) or (nm and nm in name):
                    sk = retrieve_skill(nm)
                    break
    except Exception as e:
        return "技能加载失败：%s" % e
    if not sk:
        return "找不到名为「%s」的技能。可先用 list_skills 查看可用技能。" % name
    body = (sk.get("body") or "").strip()
    triggers = "、".join(sk.get("trigger") or [])
    head = "【已加载技能：%s】\n描述：%s\n触发词：%s\n--- 技能说明如下，请据此作答 ---" % (
        sk.get("name"), sk.get("description"), triggers)
    return (head + "\n\n" + body) if body else head


def tool_review_output(args):
    """成果审视分身：审视指定文本（或最近一条小6回复），返回提示并暂存面板数据。"""
    from review_clone import review_text
    text = (args.get("text") or "").strip()
    if not text:
        text = _last_assistant_turn()
    if not text:
        return "没有可审视的内容——先聊点什么，或把要审视的文字直接发给我。"
    critique = review_text(text)
    global _PENDING_REVIEW
    _PENDING_REVIEW = {"original": text, "critique": critique}
    return "审视分身已就位，点评稍后在面板呈现～"

# 从文本/链接里抓第一个可播的视频地址（B 站 / YouTube / 腾讯）
_VIDEO_URL_RE = re.compile(
    r"https?://(?:www\.)?(?:"
    r"bilibili\.com/video/(?P<bili>BV[0-9A-Za-z]+)"
    r"|youtube\.com/watch\?v=(?P<yt>[0-9A-Za-z_-]+)"
    r"|youtu\.be/(?P<ytb>[0-9A-Za-z_-]+)"
    r"|v\.qq\.com/x/cover/[0-9a-z]+/(?P<qq>[0-9A-Za-z]+\.html)"
    r")",
    re.I,
)

def _extract_first_video_url(text):
    if not text:
        return None
    m = _VIDEO_URL_RE.search(text)
    if not m:
        return None
    if m.group("bili"):
        return {"url": "https://www.bilibili.com/video/" + m.group("bili"), "title": ""}
    if m.group("yt"):
        return {"url": "https://www.youtube.com/watch?v=" + m.group("yt"), "title": ""}
    if m.group("ytb"):
        return {"url": "https://youtu.be/" + m.group("ytb"), "title": ""}
    if m.group("qq"):
        return {"url": m.group(0), "title": ""}
    return None

def tool_play_video(args):
    """搜索并打开视频：给定关键词或链接，搜出 bilibili/YouTube 视频交给前端全屏播放。"""
    url = (args.get("url") or "").strip()
    title = (args.get("title") or "").strip()
    q = (args.get("query") or args.get("q") or "").strip()
    # 直接给了链接：能播就直接用
    if url and re.match(r"^https?://", url, re.I):
        found = _extract_first_video_url(url) or {"url": url, "title": title}
        set_pending_video(found["url"], found.get("title") or title)
        return f"这就给你放：{title or found['url']}"
    # 否则按关键词搜（优先 bilibili）
    if not q:
        return "没听懂要看啥，给个关键词或视频链接呗～"
    search_q = q if ("bilibili" in q.lower() or "b站" in q) else "bilibili " + q
    try:
        raw = tool_web_search({"query": search_q, "limit": 5})
    except Exception as e:
        return f"视频搜索没成：{e}"
    found = _extract_first_video_url(raw)
    if not found:
        return f"没搜到「{q}」相关的视频，换个说法再试试？"
    set_pending_video(found["url"], found.get("title") or q)
    return f"找到啦：{found.get('title') or q}，马上开播～"


PLATFORM_LABELS = {
    "douyin": "抖音",
    "xiaohongshu": "小红书",
    "wechat": "微信",
    "weibo": "微博",
}


def _rule_desc(name, tt, tv, at, av):
    trig = "每天 %s" % tv if tt == "time" else ("新开会话时" if tv == "session_start" else tv)
    act = ("推送：「%s」" % av) if at == "notify" else ("打开 %s 面板" % av)
    return "触发：%s；动作：%s。" % (trig, act)


def tool_manage_rule(args):
    """自动化规则管理（单入口，action=add/list/toggle/delete）。"""
    action = (args.get("action") or "").strip().lower()
    if action == "list":
        conn = db_conn()
        rows = conn.execute(
            "SELECT id,name,trigger_type,trigger_value,action_type,action_value,enabled FROM rules ORDER BY id"
        ).fetchall()
        conn.close()
        if not rows:
            return "现在还没有任何自动化规则。想设一个就说「帮我建个规则：每天 9 点打开热点」之类的。"
        lines = []
        for rid, name, tt, tv, at, av, en in rows:
            lines.append("• [%d] %s %s — %s" % (rid, "✅" if en else "⏸", name, _rule_desc(name, tt, tv, at, av)))
        return "现有 %d 条自动化规则：\n%s" % (len(rows), "\n".join(lines))
    if action == "add":
        name = (args.get("name") or "").strip() or "未命名规则"
        tt = (args.get("trigger_type") or "").strip().lower()
        tv = (args.get("trigger_value") or "").strip()
        at = (args.get("action_type") or "").strip().lower()
        av = (args.get("action_value") or "").strip()
        if tt not in ("time", "event"):
            return "规则没建成：trigger_type 只能是 time 或 event。"
        if at not in ("notify", "open_panel"):
            return "规则没建成：action_type 目前支持 notify 或 open_panel。"
        if tt == "time" and not re.match(r"^\d{1,2}:\d{2}$", tv):
            return "规则没建成：time 触发需要 trigger_value 填 HH:MM，比如 09:00。"
        if at == "open_panel" and av not in ("hotspot", "video", "memory"):
            return "规则没建成：open_panel 的 action_value 只能是 hotspot / video / memory 之一。"
        conn = db_conn()
        conn.execute(
            "INSERT INTO rules(name,trigger_type,trigger_value,action_type,action_value,enabled,created) VALUES(?,?,?,?,?,1,?)",
            (name, tt, tv, at, av, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        conn.commit()
        conn.close()
        return "规则「%s」建好了。%s" % (name, _rule_desc(name, tt, tv, at, av))
    if action == "toggle":
        rid = int(args.get("id") or 0)
        en = int(args.get("enabled") if args.get("enabled") is not None else 1)
        if not rid:
            return "toggle 需要传规则 id。"
        conn = db_conn()
        cur = conn.execute("UPDATE rules SET enabled=? WHERE id=?", (1 if en else 0, rid))
        conn.commit()
        conn.close()
        if cur.rowcount == 0:
            return "没找到 id=%d 的规则。" % rid
        return "规则 %d 已%s。" % (rid, "启用" if en else "停用")
    if action == "delete":
        rid = int(args.get("id") or 0)
        if not rid:
            return "delete 需要传规则 id。"
        conn = db_conn()
        cur = conn.execute("DELETE FROM rules WHERE id=?", (rid,))
        conn.commit()
        conn.close()
        if cur.rowcount == 0:
            return "没找到 id=%d 的规则。" % rid
        return "规则 %d 已删除。" % rid
    return "action 只能是 add / list / toggle / delete。"


# —— 声明式场景卡片：让 agent 往界面「声明」一张卡（参考实现 scene 同款）——
_VALID_KINDS = ("text", "weather", "media", "choice", "list", "progress",
                 "metric", "form", "stack", "row", "col", "selfcheck", "awakening")


def tool_render_card(args):
    """声明式场景卡片：agent 声明界面某处此刻该长什么样，前端按 id 幂等渲染/移除。

    action=set 新增/更新（按 id 幂等）；action=remove 移除该 id。
    后台任务（如软件安装）也可直接调用 scene.push_scene_event + scene.flush_scene_events 实时推送。
    """
    import scene

    cid = (args.get("id") or "").strip()
    if not cid:
        return "render_card 需要 id（卡片唯一标识）。"
    action = (args.get("action") or "set").strip().lower()
    if action not in ("set", "remove"):
        return "action 只能是 set 或 remove。"
    if action == "remove":
        scene.push_scene_event({"id": cid, "kind": "any", "action": "remove"})
        return "卡片 %s 已移除。" % cid
    kind = (args.get("kind") or "").strip().lower()
    if kind not in _VALID_KINDS:
        return "kind 只能是 text / weather / media / choice / list / progress / metric / form / stack / row / col / selfcheck / awakening 之一。"
    card = {
        "id": cid,
        "kind": kind,
        "action": "set",
        "title": (args.get("title") or "").strip(),
        "body": (args.get("body") or "").strip(),
    }
    if kind in ("list", "choice"):
        items = args.get("items") or []
        if isinstance(items, str):
            items = [items]
        card["items"] = [str(x) for x in items]
    elif kind == "media":
        card["media_url"] = (args.get("media_url") or "").strip()
        card["media_type"] = (args.get("media_type") or "image").strip().lower()
    elif kind == "progress":
        try:
            card["percent"] = int(args.get("percent") or 0)
        except Exception:
            card["percent"] = 0
        card["status"] = (args.get("status") or "").strip()
    elif kind == "metric":
        card["value"] = str(args.get("value") or "")
        card["unit"] = (args.get("unit") or "").strip()
        card["label"] = (args.get("label") or "").strip()
        card["delta"] = (args.get("delta") or "").strip()
        card["delta_dir"] = (args.get("delta_dir") or "flat").strip().lower()
    elif kind == "form":
        fields = args.get("fields") or []
        if isinstance(fields, str):
            fields = [fields]
        norm = []
        for f in fields:
            if isinstance(f, dict):
                norm.append({
                    "name": str(f.get("name") or "field"),
                    "label": str(f.get("label") or f.get("name") or ""),
                    "placeholder": str(f.get("placeholder") or ""),
                })
            else:
                norm.append({"name": str(f), "label": str(f), "placeholder": ""})
        card["fields"] = norm
        card["submit_text"] = (args.get("submit_text") or "提交").strip()
    elif kind in ("stack", "row", "col"):
        children = args.get("children") or []
        if isinstance(children, dict):
            children = [children]
        card["children"] = children
    elif kind == "selfcheck":
        items = args.get("items") or []
        norm = []
        for it in items:
            if isinstance(it, dict):
                norm.append({"label": str(it.get("label") or ""), "ok": bool(it.get("ok"))})
            else:
                norm.append({"label": str(it), "ok": True})
        card["items"] = norm
        card["summary"] = (args.get("summary") or "").strip()
    elif kind == "awakening":
        card["button_label"] = (args.get("button_label") or "").strip()
    scene.push_scene_event(card)
    return "卡片「%s」已声明（%s）。" % ((card.get("title") or cid), kind)


# ---------- Phase C：工具工厂管理工具 ----------
def tool_create_custom_tool(args):
    spec_raw = (args.get("spec_json") or "").strip()
    if not spec_raw:
        return "错误：未提供 spec_json（工具规格 JSON 字符串）"
    try:
        spec = json.loads(spec_raw)
    except Exception as e:
        return f"规格 JSON 解析失败：{e}"
    try:
        from tool_factory import save_custom_tool
        name = save_custom_tool(spec)
    except ValueError as e:
        return f"规格校验未通过：{e}"
    except Exception as e:
        return f"保存失败：{e}"
    return (f"已创建/更新自定义工具：{name}（strategy={spec.get('strategy', {}).get('type')}）。"
            f"启用后（TOOL_FACTORY_ENABLED=true）即会自动注入可用工具列表。")


def tool_list_custom_tools(args):
    try:
        from tool_factory import list_custom_tools, enabled
        items = list_custom_tools()
    except Exception as e:
        return f"查询失败：{e}"
    if not items:
        return "当前没有任何自定义工具（工具工厂为空）。"
    lines = [f"自定义工具共 {len(items)} 个（工厂启用={enabled()}）："]
    for it in items:
        lines.append(f"- {it['name']}  [{it['strategy']}]  {it['description']}  (创建于 {it['created']})")
    return "\n".join(lines)


def tool_delete_custom_tool(args):
    name = (args.get("name") or "").strip()
    if not name:
        return "错误：未提供要删除的工具 name"
    try:
        from tool_factory import delete_custom_tool, get_custom_tool
        if not get_custom_tool(name):
            return f"未找到自定义工具：{name}"
        delete_custom_tool(name)
    except Exception as e:
        return f"删除失败：{e}"
    return f"已删除自定义工具：{name}"


def tool_delegate_agent(args):
    task = (args.get("task") or "").strip()
    confirm = bool(args.get("confirm", False))
    try:
        from agent_delegate import delegate
        return delegate(task, confirm=confirm)
    except Exception as e:
        return f"委托执行失败：{e}"


# ---------- Phase 3：目标系统工具实现 ----------
def tool_set_goal(args):
    title = (args.get("title") or "").strip()
    if not title:
        return "错误：目标标题不能为空"
    try:
        import goals

        g = goals.create_goal(
            title=title,
            description=args.get("description") or "",
            priority=args.get("priority", "medium"),
            horizon=args.get("horizon", "short"),
            due_date=args.get("due_date"),
        )
        if not g:
            return "创建目标失败"
        return (
            f"已创建目标 #{g.id}：{g.title}（优先级 {g.priority}，跨度 {g.horizon}"
            + (f"，截止 {g.due_date}" if g.due_date else "")
            + "）"
        )
    except Exception as e:
        return f"创建目标失败：{e}"


def tool_update_goal(args):
    try:
        gid = int(args.get("goal_id"))
    except (TypeError, ValueError):
        return "错误：goal_id 必须是数字"
    fields = {}
    for k in ("status", "priority", "horizon", "due_date", "title", "description"):
        if args.get(k) is not None:
            fields[k] = args.get(k)
    if args.get("progress") is not None:
        try:
            fields["progress"] = int(args.get("progress"))
        except (TypeError, ValueError):
            pass
    if not fields:
        return "错误：没有提供要更新的字段"
    try:
        import goals

        g = goals.update_goal(gid, **fields)
        if not g:
            return f"错误：找不到目标 #{gid}"
        return f"已更新目标 #{g.id}（{g.title}）：状态 {g.status}，进度 {g.progress}%"
    except Exception as e:
        return f"更新目标失败：{e}"


def tool_list_goals(args):
    try:
        import goals

        only_active = bool(args.get("only_active", False))
        status = "active" if only_active else None
        if args.get("status"):
            status = args.get("status")
        limit = int(args.get("limit", 10))
        gs = goals.list_goals(status=status, limit=limit)
        if not gs:
            return "当前没有目标。"
        lines = []
        for g in gs:
            due = f" 截止 {g.due_date}" if g.due_date else ""
            lines.append(
                f"  - #{g.id} [{g.status}] {g.title}（进度 {g.progress}%，{g.priority}{due}）"
            )
        return "目标列表：\n" + "\n".join(lines)
    except Exception as e:
        return f"列出目标失败：{e}"


def tool_delete_goal(args):
    try:
        gid = int(args.get("goal_id"))
    except (TypeError, ValueError):
        return "错误：goal_id 必须是数字"
    try:
        import goals

        ok = goals.delete_goal(gid)
        if not ok:
            return f"错误：找不到目标 #{gid}"
        return f"已归档（删除）目标 #{gid}。"
    except Exception as e:
        return f"删除目标失败：{e}"


def tool_plan_goal(args):
    try:
        gid = int(args.get("goal_id"))
    except (TypeError, ValueError):
        return "错误：goal_id 必须是数字"
    if gid <= 0:
        return "请先指定要拆解的目标（用 #id 或先调用 list_goals 查看）。"
    try:
        import goals

        ids = goals.plan_goal(gid)
        if not ids:
            return f"目标 #{gid} 拆解未完成（可能 LLM 调用失败或无需拆解）。"
        return (
            f"已将目标 #{gid} 拆解为 {len(ids)} 个子任务"
            f"（task_id：{', '.join('#' + str(i) for i in ids)}）。"
        )
    except Exception as e:
        return f"拆解目标失败：{e}"


TOOL_FUNCS = {
    "get_time": tool_get_time,
    "calculator": tool_calculator,
    "note_save": tool_note_save,
    "note_list": tool_note_list,
    "profile_set": tool_profile_set,
    "profile_get": tool_profile_get,
    "reminder_set": tool_reminder_set,
    "reminder_list": tool_reminder_list,
    "set_task": tool_set_task,
    "update_task_step": tool_update_task_step,
    "complete_task": tool_complete_task,
    "task_list": tool_task_list,
    "file_read": tool_file_read,
    "file_list": tool_file_list,
    "file_write": tool_file_write,
    "file_make_dir": tool_file_make_dir,
    "file_delete": tool_file_delete,
    "file_rename": tool_file_rename,
    "list_processes": tool_list_processes,
    "kill_process": tool_kill_process,
    "run_shell": tool_run_shell,
    "session_state": tool_session_state,
    "reset_session": tool_reset_session,
    "install_software": tool_install_software,
    "web_fetch": tool_web_fetch,
    "browser_read": tool_browser_read,
    "scan_desktop": tool_scan_desktop,
    "scan_installed_software": tool_scan_installed_software,
    "manage_prefetch_task": tool_manage_prefetch_task,
    "tick_now": tool_tick_now,
    "memory_search": tool_memory_search,
    "web_search": tool_web_search,
    "media_generate": tool_media_generate,
    "social_send": tool_social_send,
    "asr_transcribe": tool_asr_transcribe,
    "get_weather": tool_weather,
    "get_hotspots": tool_hotspots,
    "open_hotspot_panel": tool_open_hotspot_panel,
    "typhoon_panel": tool_typhoon_panel,
    "person_card": tool_person_card,
    "map_query": tool_map_query,
    "open_doc_panel": tool_open_doc_panel,
    "open_memory_audit": tool_open_memory_audit,
    "review_output": tool_review_output,
    "remember": tool_remember,
    "play_video": tool_play_video,
    "manage_rule": tool_manage_rule,
    "render_card": tool_render_card,
    "scan_resources": tool_scan_resources,
    "list_skills": tool_list_skills,
    "use_skill": tool_use_skill,
    "create_custom_tool": tool_create_custom_tool,
    "list_custom_tools": tool_list_custom_tools,
    "delete_custom_tool": tool_delete_custom_tool,
    "delegate_agent": tool_delegate_agent,
    "set_goal": tool_set_goal,
    "update_goal": tool_update_goal,
    "list_goals": tool_list_goals,
    "delete_goal": tool_delete_goal,
    "plan_goal": tool_plan_goal,
    "add_knowledge": tool_add_knowledge,
    "archive_knowledge": tool_archive_knowledge,
}

# 只读工具可并行执行；写操作顺序执行
READONLY_TOOLS = {
    "get_time",
    "calculator",
    "note_list",
    "profile_get",
    "reminder_list",
    "task_list",
    "file_read",
    "file_list",
    "list_processes",
    "web_fetch",
    "browser_read",
    "scan_desktop",
    "scan_installed_software",
    "web_search",
    "get_weather",
    "get_hotspots",
    "render_card",
    "session_state",
    "typhoon_panel",
    "map_query",
    "open_doc_panel",
    "open_memory_audit",
    "review_output",
    "scan_resources",
    "list_skills",
    "use_skill",
    "list_custom_tools",
    "list_goals",
}

# P10-4：低危工具白名单 — 无 Goal 上下文也自动执行（人工维护，不含高危/危险命令）
# 是 READONLY_TOOLS 的超集：额外纳入「写但安全」的目标/笔记/提醒/档案类工具。
LOW_RISK_TOOLS = {
    "get_time", "calculator", "note_save", "note_list", "memory_search",
    "profile_read", "profile_write", "reminder_add", "reminder_list",
    "file_read", "file_list", "set_goal", "update_goal", "list_goals",
    "list_skills", "use_skill", "add_knowledge", "list_processes",
    "scan_desktop", "scan_installed_software", "scan_resources",
}


def execute_tool_calls(tool_calls, allowed=None, mode="smart", goal_id=None):
    """执行一批 tool_calls，返回 (tool_messages, events)。"""
    prepared = []
    for tc in tool_calls or []:
        fn = tc.get("function", {}) if isinstance(tc, dict) else {}
        name = fn.get("name", "")
        raw = fn.get("arguments", "{}") or "{}"
        try:
            args = json.loads(raw) if isinstance(raw, str) else (raw or {})
        except Exception:
            args = {}
        prepared.append({"id": tc.get("id", ""), "name": name, "args": args})
    readonly, writes = [], []
    for p in prepared:
        (readonly if p["name"] in READONLY_TOOLS else writes).append(p)
    tool_msgs, events = [], []

    def run_one(p):
        try:
            from capability_runtime import execute as _cap_execute
            _res = _cap_execute(p["name"], p["args"], allowed=allowed, mode=mode, goal_id=goal_id)
            return p, _res.to_tool_message()
        except Exception:
            return p, str(_execution_run(p["name"], {"args": p["args"]}, allowed=allowed, mode=mode, goal_id=goal_id))

    if readonly:
        for p in readonly:
            events.append(("start", p["name"], p["args"]))
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(readonly), 5)) as ex:
            futs = {ex.submit(run_one, p): p for p in readonly}
            for f in futs:
                p, res = f.result()
                tool_msgs.append({"role": "tool", "tool_call_id": p["id"], "content": res})
                events.append(("end", p["name"], res))
    for p in writes:
        events.append(("start", p["name"], p["args"]))
        _, res = run_one(p)
        tool_msgs.append({"role": "tool", "tool_call_id": p["id"], "content": res})
        events.append(("end", p["name"], res))
    return tool_msgs, events


def _fc_fallback(messages, emit):
    """Agnes 主调用失败时的兜底：剥离工具上下文，用最近一条 user 文本直接再问一次。
    成功返回文本，失败返回 None（由调用方决定最终文案）。"""
    try:
        user_text = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                c = m.get("content")
                if isinstance(c, str) and c.strip():
                    user_text = c
                    break
        if not user_text:
            return None
        fb_msgs = [
            {"role": "system", "content": build_context_prompt(user_text)},
            {"role": "user", "content": user_text},
        ]
        with agnes_completion(fb_msgs, tools=[], stream=False, timeout=60) as resp:
            d = json.loads(resp.read().decode("utf-8"))
        return (d.get("choices") or [{}])[0].get("message", {}).get("content") or None
    except Exception as e:
        emit({"error": f"兜底调用也失败：{e}"})
        return None


def run_fc_loop(messages, emit, tools=None, temperature=0.7, reasoning=None, allowed=None, mode="smart", goal_id=None):
    """真正的 function calling 闭环：LLM 自主决定调工具 → 本地执行 → 回填 → 再问 LLM，支持多轮。
    返回 (最终自然语言回复文本, 本轮实际调用的工具名集合)。
    tools：可下发的工具 schema（默认全量 TOOLS）；Phase 2.4 由 select_tools 按意图裁剪后传入。
    mode: smart|expert，传递给 execution layer 用于 policy 上下文。"""
    MAX_ROUNDS = 5
    called = set()
    effective_tools = tools if tools is not None else TOOLS
    for _ in range(MAX_ROUNDS):
        try:
            import urllib.error

            with agnes_completion(
                messages, tools=effective_tools, stream=False, timeout=90, temperature=temperature, reasoning=reasoning
            ) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            emit({"error": f"核心调用失败（HTTP {e.code}）"})
            fb = _fc_fallback(messages, emit)
            return (fb if fb else "（抱歉，核心暂时无法响应）"), called
        except Exception as e:
            emit({"error": f"核心调用失败：{e}"})
            fb = _fc_fallback(messages, emit)
            return (fb if fb else "（抱歉，核心暂时无法响应）"), called
        msg = (data.get("choices") or [{}])[0].get("message", {})
        content = msg.get("content") or ""
        tool_calls = msg.get("tool_calls") or []
        for tc in tool_calls:
            fn = tc.get("function", {}) if isinstance(tc, dict) else {}
            called.add(fn.get("name", ""))
        assistant_msg = {"role": "assistant", "content": content or None}
        if tool_calls:
            assistant_msg["tool_calls"] = tool_calls
        messages.append(assistant_msg)
        if not tool_calls:
            return content, called  # 无工具调用 = 最终自然语言回复
        tool_msgs, events = execute_tool_calls(tool_calls, allowed, mode=mode, goal_id=goal_id)
        for kind, name, payload in events:
            if kind == "start":
                emit({"xiao6_event": "tool_start", "tool": name, "args": payload})
            else:
                emit({"xiao6_event": "tool_end", "tool": name, "result": payload})
        messages.extend(tool_msgs)
    # 超出轮次保护：基于已有上下文强制收尾，不再给工具
    try:
        with agnes_completion(messages, tools=[], stream=False, timeout=90, temperature=temperature) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return (data.get("choices") or [{}])[0].get("message", {}).get("content") or "（抱歉，处理超时）", called
    except Exception as e:
        emit({"error": f"收尾调用失败：{e}"})
        fb = _fc_fallback(messages, emit)
        return (fb if fb else "（抱歉，处理超时）"), called


def detect_intent(text):
    """服务端兜底意图路由：当 Agnes 未走 function calling 时，按关键词直接命中工具。"""
    t = (text or "").strip()
    # —— 先处理「询问类」意图，避免被下方「告知类」正则误吞（如"你记得我叫什么"）——
    if re.search(r"你记得我?叫什么|我的称呼|我叫什么|你记得我的名字", t):
        return ("profile_get", {"key": "称呼"})
    if re.search(r"我的偏好|你记得我的偏好|我的习惯|你记得我的习惯", t):
        return ("profile_get", {"key": "偏好"})
    # —— 长期记忆：用户主动告知事实（放在最前，避免被笔记分支抢走）——
    m = re.search(r"(?:我叫|我的名字是|记住我叫|叫我)\s*([\u4e00-\u9fa5A-Za-z0-9_]{1,12})", t)
    if m:
        return ("profile_set", {"key": "称呼", "value": m.group(1)})
    m = re.search(r"(?:我喜欢|我偏好|我的偏好是|记一下我的偏好[:：]?)\s*([^\s].+)", t)
    if m:
        return ("profile_set", {"key": "偏好", "value": m.group(1).strip(" 。，,、；;")})
    # —— 主动智能（D 期）：提醒 ——
    if re.search(r"提醒我|设个提醒|提醒一下|定时提醒|设个闹钟|备忘提醒", t):
        content = re.sub(r"^(.*?)(提醒我|设个提醒|提醒一下|定时提醒|设个闹钟|备忘提醒)\s*[:：]?", "", t).strip(
            " 。，,、"
        )
        if content:
            return ("reminder_set", {"content": content})
    if re.search(r"我的提醒|待提醒|有哪些提醒|提醒列表|待办提醒|查看提醒", t):
        return ("reminder_list", {})
    # —— 天气（必须先于时间意图：含天气关键词归天气，避免被"今天"等时间正则吞掉）——
    # 城市提取：取天气关键词前的 2~6 个汉字（排除时间词，避免"北京今天"这类误吞）
    m = re.search(
        r"([\u4e00-\u9fa5]{2,6}?)(?:的)?\s*(天气|气温|温度|多少度|几度|冷不冷|热不冷|出不出?太阳|下不下?雨|要不要带伞|适合出门吗)",
        t,
    )
    if m:
        city = re.sub(r"(今天|现在|本地|这里|这儿|当前)", "", m.group(1))
        return ("get_weather", {"city": city.strip()})
    if re.search(
        r"天气怎么样|今日天气|今天的天气|气温如何|温度多少|外面(热|冷|下雨|晴)|(下|落)雨(了|吗|没)|带伞吗|要不要带伞", t
    ):
        city = (re.search(r"([\u4e00-\u9fa5]{2,6})\s*(?:天气|气温|温度)", t) or [None, ""])[1] or ""
        city = re.sub(r"(今天|现在|本地|这里|这儿|当前)", "", city)
        return ("get_weather", {"city": city.strip()})
    if re.search(r"几点|时间|日期|星期|周几|今天|现在|几号|农历", t):
        return ("get_time", {})
    if re.search(r"记一下|记笔记|记个|记着|保存|备忘|记个笔记", t):
        content = re.sub(r"^(.*?)(记一下|记笔记|记个|记着|保存|备忘|记个笔记)\s*[:：]?", "", t).strip(" 。，,、")
        if content:
            # 带时间表达 → 视为定时提醒（而非普通笔记）
            if re.search(
                r"明天|后天|大后天|下周|星期|周[一二三四五六日]|今天|现在|立刻|马上|\d{1,2}\s*[:：]\d{2}|\d+\s*(秒|分钟|小时|天|日)|\d{1,2}\s*点",
                content,
            ):
                return ("reminder_set", {"content": content})
            return ("note_save", {"content": content})
    if re.search(r"笔记|待办|记了|查笔记|我记|备忘", t):
        return ("note_list", {})
    if re.search(r"我的任务|有哪些任务|任务列表|未完成任务|待办任务|看看任务|任务进展", t):
        return ("task_list", {"only_open": True})
    # —— Phase 3.2：文件 / Shell / Web 兜底意图 ——
    m = re.search(r"读取?文件[：:]?\s*([^\s，,。]+)", t)
    if m:
        return ("file_read", {"path": m.group(1)})
    if re.search(r"读(一下|取)?文件|查看文件|打开文件|文件内容", t):
        return ("file_read", {"path": (re.search(r"([\w./\-]+\.\w+)", t) or [None, ""])[1] or ""})
    if re.search(r"列(出|个)?目录|看看目录|沙箱(里|内)?有(什么|哪些)|目录里有", t):
        return ("file_list", {})
    if re.search(r"写(入|个|一下)?文件|保存(到)?文件|创建文件|新建文件", t):
        return (
            "file_write",
            {
                "path": (re.search(r"([\w./\-]+\.\w+)", t) or [None, ""])[1] or "note.txt",
                "content": re.sub(r"^.*?(写|保存|创建|新建)文件[：:]?\s*", "", t).strip(" 。，,、"),
            },
        )
    # 持久 shell 会话：用户明确要求"在会话里 / 连续 / 分步"执行 → 走 session=True
    if re.search(r"在会话里|在会话|持久会话|保持会话|连续执行|连续跑|分步(执行|跑|做)|用会话|会话模式|会话里|shell 会话", t):
        cmd = re.sub(
            r"^.*?(在会话里|在会话|持久会话|保持会话|连续执行|连续跑|分步(执行|跑|做)?|用会话|会话模式|会话里|shell 会话)[：:]?\s*",
            "",
            t,
        ).strip(" 。，,、")
        cmd = re.sub(r"^(运行|执行|跑一下|输入)?\s*", "", cmd).strip(" 。，,、")
        if cmd:
            return ("session_run", {"command": cmd, "session": True})
    if re.search(r"运行命令|执行命令|跑一下命令|命令行|在终端|shell|cmd", t):
        return ("run_shell", {"command": re.sub(r"^.*?(运行|执行|跑一下)?命令(行)?[：:]?\s*", "", t).strip(" 。，,、")})
    # 本地软件安装：安装 / 装一下 / 装个 + 软件名或 winget id
    if re.search(r"安装|装一下|装个|下载安装|安裝", t):
        name = re.sub(r"^.*?(安装|装一下|装个|下载安装|安裝)[：:]?\s*", "", t).strip(" 。，,、")
        name = re.sub(r"^(一下|个|这款|这个|软件|个软件)?\s*", "", name).strip(" 。，,、")
        if name:
            if _looks_like_winget_id(name):
                return ("install_software", {"package_id": name})
            return ("install_software", {"query": name})
    if re.search(r"抓取|打开网页|访问网址|读取网页|抓一下|网页内容|这个链接", t):
        return ("web_fetch", {"url": (re.search(r"(https?://\S+)", t) or [None, ""])[1] or ""})
    if re.search(r"搜索|搜一下|查一下网|上网搜|搜網|百度|google", t):
        return (
            "web_search",
            {
                "query": re.sub(r"^(.*?)(搜索|搜一下|查一下网|上网搜|搜網|百度|google)\s*[:：]?", "", t).strip(
                    " 。，,、"
                )
            },
        )
    # —— Phase 4：外部接口兜底意图（媒体 / 社交 / 语音）——
    # —— Phase 4：外部接口兜底意图（媒体 / 社交 / 语音）——
    # 媒体：触发词 + 媒体名词即可，中间允许有修饰词
    if re.search(r"(生成|画|绘制|文生图|AI 作画|AI 生图|做个|来张).{0,20}?(图|图片|图像|插画)", t) or re.search(
        r"文生图|AI 作画|AI 生图", t
    ):
        return (
            "media_generate",
            {
                "kind": "image",
                "prompt": re.sub(r"^(.*?)(生成|画|绘制|文生图|AI 作画|AI 生图|做个|来张)\s*", "", t).strip(" 。，,、"),
            },
        )
    if re.search(r"(生成|做|制作|文生视频|AI 生成视频).{0,20}?(视频|短片|影片)", t) or re.search(
        r"文生视频|AI 生成视频", t
    ):
        return (
            "media_generate",
            {
                "kind": "video",
                "prompt": re.sub(r"^(.*?)(生成|做|制作|文生视频|AI 生成视频)\s*", "", t).strip(" 。，,、"),
            },
        )
    if re.search(r"(生成|写|创作|文生音乐|AI 作曲).{0,20}?(歌|音乐|曲|旋律)", t) or re.search(r"文生音乐|AI 作曲", t):
        return (
            "media_generate",
            {"kind": "music", "prompt": re.sub(r"^(.*?)(生成|写|创作|文生音乐|AI 作曲)\s*", "", t).strip(" 。，,、")},
        )
    # 社交：允许「发 到 discord」「推送 给 飞书」等带空格写法
    if re.search(
        r"发\s*(到|给)?\s*(discord|Discord|飞书|feishu|飞书群)|推送\s*(到|给)?\s*(discord|Discord|飞书|feishu)", t
    ):
        return (
            "social_send",
            {
                "platform": (
                    "wechat"
                    if re.search(r"微信|wechat|企业微信", t)
                    else "discord"
                    if re.search(r"discord|Discord", t)
                    else "feishu"
                ),
                "target": "",
                "text": "",
            },
        )
    if re.search(r"语音转写|转写|听写|语音识别|把\s*(这段|这个)?\s*(音频|录音|语音)\s*转成?文字|音频转文字", t):
        return (
            "asr_transcribe",
            {"path": (re.search(r"([\w./\-]+\.(wav|mp3|m4a|ogg|flac))", t) or [None, ""])[1] or ""},
        )
    if re.search(r"算|计算|乘以|乘|除|×|÷", t) and re.search(r"\d", t):
        expr = (
            t.replace("乘以", "*")
            .replace("乘", "*")
            .replace("除以", "/")
            .replace("除", "/")
            .replace("加上", "+")
            .replace("加", "+")
            .replace("减去", "-")
            .replace("减", "-")
            .replace("×", "*")
            .replace("÷", "/")
        )
        expr = re.sub(r"[^0-9\+\-\*\/\(\)\.\%\s]", "", expr).strip()
        if re.search(r"[\*\+\-\/]", expr):
            return ("calculator", {"expr": expr})
    return None


def _first_path(s):
    """从文本里抠出第一个像路径的 token：引号优先，其次带扩展名/含分隔符的路径。"""
    m = re.search(r"[\"']([^\"']+)[\"']", s)
    if m:
        return m.group(1).strip()
    m = re.search(r"([A-Za-z0-9_\u4e00-\u9fa5\-./\\]+\.[A-Za-z0-9]+)", s)
    if m:
        return m.group(1).strip()
    m = re.search(r"([A-Za-z0-9_\u4e00-\u9fa5\-./\\]+)", s)
    return m.group(1).strip() if m else ""


def detect_intents(text):
    """服务端兜底意图路由（支持复合意图）。

    返回 [(tool_name, args), ...]，例如一句"北京天气怎么样，再更新下热点"会同时命中
    get_weather 与 get_hotspots。未命中则返回空列表。
    """
    t = (text or "").strip()
    if not t:
        return []
    intents = []
    seen = set()

    def add(name, args):
        if name not in seen:
            seen.add(name)
            intents.append((name, args))

    # —— 天气（独立意图，可与热点并存）——
    m = re.search(
        r"([\u4e00-\u9fa5]{2,6}?)(?:的)?\s*(天气|气温|温度|多少度|几度|冷不冷|热不冷|出不出?太阳|下不下?雨|要不要带伞|适合出门吗)",
        t,
    )
    if m:
        city = re.sub(r"(今天|现在|本地|这里|这儿|当前)", "", m.group(1)).strip()
        add("get_weather", {"city": city})
    elif re.search(
        r"天气怎么样|今日天气|今天的天气|气温如何|温度多少|外面(热|冷|下雨|晴)|(下|落)雨(了|吗|没)|带伞吗|要不要带伞", t
    ):
        city = (re.search(r"([\u4e00-\u9fa5]{2,6})\s*(?:天气|气温|温度)", t) or [None, ""])[1] or ""
        city = re.sub(r"(今天|现在|本地|这里|这儿|当前)", "", city).strip()
        add("get_weather", {"city": city})

    # —— 打开热点大屏（优先于普通热点查询）——
    if re.search(
        r"打开.*热点(界面|面板|大屏|模式|视图)|进入.*热点|热点大屏|热点面板|热点模式|hotspot\s*panel",
        t,
        re.IGNORECASE,
    ):
        add("open_hotspot_panel", {})

    # —— 看视频（搜索 + 打开播放面板；区别于「文生视频 media_generate」）——
    want_video = (
        re.search(r"(bilibili|B站|youtube|油管)", t, re.I)
        or (
            re.search(r"看|播放|放个|来个|搜个|想看|整一个|点开", t)
            and re.search(r"视频|影片|剧|番|电影|clip", t, re.I)
        )
    )
    if want_video:
        q = re.sub(r"(看|播放|来个|找个|搜个|想看|给我放|放一下|整一个|点开|打开)[个一下]?\s*", "", t, flags=re.I)
        q = re.sub(r"(的视频|视频|影片|剧|番剧|番|电影|clip|bilibili|B站|YouTube|youtube|油管)\b", "", q, flags=re.I)
        q = q.strip(" 的了个下，,。、 ")
        add("play_video", {"query": q or "热门"})

    # —— 地图服务（独立意图）——
    if "map_query" not in seen and re.search(
        r"地图|距离|多远|坐标|在哪|位置|附近城市|有哪些城市|城市列表|经纬度", t
    ):
        q = re.sub(r"(查一下|查询|看看|帮我|我想知道|多少|是)?\s*", "", t)
        q = q.strip(" ？?。，,、")
        add("map_query", {"query": q or t})

    # —— 文档面板（独立意图）——
    if "open_doc_panel" not in seen and re.search(
        r"打开文档|文档面板|看看文档|读一下.*文档|我的文档|浏览文档|文档列表", t
    ):
        add("open_doc_panel", {})

    # —— 记忆审计（独立意图）——
    if "open_memory_audit" not in seen and re.search(
        r"记忆审计|记忆管理|记忆面板|看看你记了什么|清理记忆|记忆清理|审计记忆", t
    ):
        add("open_memory_audit", {})

    # —— 成果审视分身（独立意图）——
    if "review_output" not in seen and re.search(
        r"审视|复核|分身点评|点评一下|审查一下|挑刺|帮我审", t
    ):
        add("review_output", {"text": ""})

    # —— 本机资源扫描（独立意图）——
    if "scan_resources" not in seen and re.search(
        r"扫描本机|本机资源|已装软件|装了什么软件|我的仓库|ssh 主机|ssh配置|桌面有什么|桌面文件|本机扫描|扫描我的电脑", t, re.I
    ):
        scope = "all"
        if re.search(r"桌面", t):
            scope = "desktop"
        elif re.search(r"软件|装了", t):
            scope = "software"
        elif re.search(r"ssh|主机", t):
            scope = "ssh"
        elif re.search(r"仓库|git", t, re.I):
            scope = "git"
        add("scan_resources", {"scope": scope})

    # —— 本地技能（独立意图）——
    if "list_skills" not in seen and re.search(
        r"有哪些技能|技能列表|有什么技能|能用什么技能|列出技能|技能清单|本地技能", t
    ):
        add("list_skills", {})
    if "use_skill" not in seen and re.search(
        r"(用|调用|加载|试用|使用|应用).{0,8}?技能", t
    ):
        m = re.search(r"(?:用|调用|加载|试用|使用|应用).{0,8}?([\w一-龥]+?)\s*技能", t)
        name = m.group(1) if m else ""
        add("use_skill", {"name": name})

    # —— 自动化规则：创建类意图优先走 manage_rule（不与 reminder / 热点冲突）——
    if "manage_rule" not in seen and re.search(
        r"新建规则|设置规则|加个?规则|建个?规则|自动化规则|定时任务|自动化|每天.*(打开|播放|播报|提醒|说|做)|定时.*(打开|播放|做)",
        t,
    ):
        add("manage_rule", {"action": "add"})

    # —— 抢占插队：用户要求「立即 / 马上 / 立刻」触发主动扫描时，路由到 tick_now ——
    if "tick_now" not in seen and re.search(
        r"立刻扫描|马上扫描|立即扫描|马上刷新|立刻刷新|立即刷新|扫描一下(热点|天气)|刷新一下(天气|热点)|立刻(扫描|刷新)|马上(扫描|刷新)|触发扫描|立即执行扫描|主动扫描一下",
        t,
    ):
        kind = "all"
        if re.search(r"热点|舆情|热榜", t):
            kind = "hotspot"
        elif re.search(r"天气", t):
            kind = "weather"
        elif re.search(r"规则|自动化", t):
            kind = "rules"
        elif re.search(r"预取", t):
            kind = "prefetch"
        elif re.search(r"提醒", t):
            kind = "reminders"
        add("tick_now", {"kind": kind})

    # —— 本地向量语义召回：用户用自然语言问「之前聊过 X 吗」「关于 X 的笔记」时路由 ——
    if "memory_search" not in seen and re.search(
        r"语义搜索|语义检索|向量检索|语义召回|按意思找|找相关|相关记忆|相关笔记|之前聊过|之前说过|关于.+的笔记|类似.+的笔记|记不记得.*说过",
        t,
    ):
        q = re.sub(
            r"^(.*?)(语义搜索|语义检索|向量检索|语义召回|按意思找|找相关|相关记忆|相关笔记|之前聊过|之前说过|关于|类似|记不记得.*说过)\s*[:：]?",
            "",
            t,
        ).strip(" 。，,、？?")
        add("memory_search", {"query": q or t})

    # —— 声明式场景卡片：用户明确要求「挂卡 / 渲染卡片 / 确认卡 / 进度卡」时，
    #     服务端兜底路由到 render_card（模型 FC 对该工具不稳，用意图路由保底）。
    #     推断 kind 与可选字段，让卡片真正出现在界面上。 ——
    if "render_card" not in seen and re.search(
        r"挂一张?卡|挂卡|渲染卡片|渲染卡|声明卡片|界面卡片|确认卡|进度卡|可视化卡片|展示卡片|render\s*card|scene\s*卡|来张卡|出张卡",
        t,
        re.I,
    ):
        kind = "text"
        if re.search(r"确认|选|是否|要不要|安装", t):
            kind = "choice"
        elif re.search(r"进度|百分比|\d+\s*%", t):
            kind = "progress"
        elif re.search(r"列表|罗列|清单|条目", t):
            kind = "list"
        elif re.search(r"图片|图像|视频|图\s|video|image", t):
            kind = "media"
        elif re.search(r"天气卡|天气面板", t):
            kind = "weather"
        elif re.search(r"指标|统计|数据|数值|大数字|仪表", t):
            kind = "metric"
        elif re.search(r"自检|诊断|体检|检查项|状态检查|健康度", t):
            kind = "selfcheck"
        elif re.search(r"唤醒|苏醒|早安|开机|上线|启动", t):
            kind = "awakening"
        args = {"action": "set", "kind": kind, "id": "declared-" + kind, "title": "小6卡片", "body": t}
        # choice：从「」或【】里抓选项
        if kind == "choice":
            opts = re.findall(r"[「【]([^」】]+)[」】]", t)
            if opts:
                args["items"] = opts
        # progress：抓百分比
        if kind == "progress":
            m = re.search(r"(\d+)\s*%", t)
            if m:
                args["percent"] = int(m.group(1))
        add("render_card", args)

    # —— 台风（独立意图，可与天气/热点并存）——
    if "typhoon_panel" not in seen and re.search(
        r"台风|热带气旋|台风预警|台风路径|台风消息|几个台风|台风叫什么|台风编号",
        t,
    ):
        add("typhoon_panel", {"force": False})

    # —— 人物卡（本地结构化人物档案；仅显式关键词触发，避免与「介绍某人」闲聊冲突）——
    if "person_card" not in seen and re.search(
        r"人物卡|人物资料卡|人物简介卡|人物档案|存.*人物卡|记.*人物卡|查.*人物卡|列出.*人物卡|我的人物卡",
        t,
    ):
        add("person_card", {})

    # —— 热点（独立意图，可与天气并存；已命中「打开面板」则不再走文字热榜）——
    if "open_hotspot_panel" not in seen and "manage_rule" not in seen and re.search(
        r"热点|热榜|热搜|新闻|资讯|今天发生了什么|新鲜事|实时新闻|更新.*榜|刷新.*榜|看看.*热搜|看一下热点|看热点",
        t,
    ):
        add("get_hotspots", {"force": True})

    # —— 网页阅读：读网页/看链接内容（独立意图）——
    if "browser_read" not in seen and re.search(
        r"读一下.*(网页|链接|页面|网址|文章)|看看.*(网页|链接|页面).*讲|打开网页|阅读.*(网页|文章|链接)|这个链接.*内容|网页正文|抓取.*网页",
        t,
        re.I,
    ):
        m = re.search(r"https?://[^\s，。、,）+）\]]+", t)
        add("browser_read", {"url": (m.group(0) if m else "")})

    # —— 本机资源感知：桌面扫描 / 已装软件扫描（独立意图）——
    if "scan_desktop" not in seen and re.search(r"扫描桌面|桌面有(什么|啥)|桌面文件|看看桌面|桌面上?(的)?文件|列出桌面", t):
        add("scan_desktop", {})
    elif "scan_installed_software" not in seen and re.search(r"已装软件|安装了?哪些软件|装了什么软件|软件列表|已安装程序|本机软件|电脑上?装了", t):
        add("scan_installed_software", {})
    elif "manage_prefetch_task" not in seen and re.search(r"预取任务|添加预取|创建预取|定时预取|自动预取", t):
        add("manage_prefetch_task", {"action": "add"})

    # —— 兜底单一意图（避免与已识别意图重复）——

    # —— 文件操作：删除 / 新建目录 / 重命名（独立意图，可与其它并存）——
    if "file_delete" not in seen and re.search(
        r"删除文件|删掉文件|删文件|移除文件|删除这个文件|删除目录|删除文件夹|删掉目录|删掉文件夹|删除这个目录", t
    ):
        clean = re.sub(
            r"删除文件|删掉文件|删文件|移除文件|删除这个文件|删除目录|删除文件夹|删掉目录|删掉文件夹|删除这个目录", "", t
        )
        add("file_delete", {"path": _first_path(clean)})
    elif "file_make_dir" not in seen and re.search(
        r"新建(文件夹|目录)|创建一个?(文件夹|目录)|建个?(文件夹|目录)|创建目录|创建文件夹|mkdir", t
    ):
        clean = re.sub(r"新建(文件夹|目录)|创建一个?(文件夹|目录)|建个?(文件夹|目录)|创建目录|创建文件夹|mkdir", "", t)
        add("file_make_dir", {"path": _first_path(clean)})
    elif "file_rename" not in seen and re.search(r"重命名|改名为|改名成|把.+移动|移动(到|文件)", t):
        mb = re.search(r"把\s*([^\s，。、,]+)\s*(?:重命名[成为]?|改名[成为]?|移动(?:到)?)\s*([^\s，。、,]+)", t)
        if mb:
            src, dst = mb.group(1), mb.group(2)
        else:
            toks = re.findall(
                r"([A-Za-z0-9_\u4e00-\u9fa5\-./\\]+\.[A-Za-z0-9]+|[A-Za-z0-9_\u4e00-\u9fa5\-./\\]+)", t
            )
            src = toks[0] if toks else ""
            dst = toks[1] if len(toks) > 1 else ""
        add("file_rename", {"src": src.strip(" \"'"), "dst": dst.strip(" \"'")})

    # —— 进程管理：列出 / 终止进程（独立意图）——
    if "list_processes" not in seen and re.search(
        r"查看进程|列出进程|进程列表|运行的进程|有什么进程|哪些进程在跑|什么进程|进程占用|任务管理器|进程情况", t
    ):
        qm = re.search(r"(?:叫|名为|名称是|叫\s*)([A-Za-z0-9_\-]+\.exe|[A-Za-z0-9_\-]+)", t)
        add("list_processes", {"query": (qm.group(1) if qm else "")})
    elif "kill_process" not in seen and re.search(
        r"杀掉进程|结束进程|终止进程|kill\s*进程|杀进程|停掉进程|杀掉程序|结束程序|关掉进程|强关进程", t, re.I
    ):
        pidm = re.search(r"pid\s*[是为:：]?\s*(\d+)", t, re.I)
        if pidm:
            add("kill_process", {"pid": int(pidm.group(1))})
        else:
            nm = re.search(r"([A-Za-z0-9_\-]+\.exe)", t)
            add("kill_process", {"name": (nm.group(1) if nm else "")})

    # —— 工具工厂：列出 / 删除自定义工具（独立意图）——
    if re.search(r"列出(我的|已创建|定义|注册)?工具|我(创建|定义|注册)了?哪些工具|有哪些自定义工具|工具列表|我的工具|工具工厂", t):
        add("list_custom_tools", {})
    elif re.search(r"删除(一个|个|我的)?工具|移除(一个|个|我的)?工具|删掉工具|删掉(这个|那个)?工具", t):
        nm = re.search(r"工具[名叫为]?\s*([A-Za-z_][A-Za-z0-9_]{1,40})", t)
        add("delete_custom_tool", {"name": (nm.group(1) if nm else "")})

    # —— 本地 Agent 委托（独立意图）——
    if re.search(r"委托(给|本地)?\s*(agent|Agent|claude|Claude)|让\s*(agent|Claude|本地\s*agent)\s*(帮我|处理|写|改|调试|做)?|交给\s*(本地\s*)?agent", t):
        task = re.sub(
            r"^(.*?)(委托(给|本地)?\s*(agent|Agent|claude|Claude)|让\s*(agent|Claude|本地\s*agent)\s*(帮我|处理|写|改|调试|做)?|交给\s*(本地\s*)?agent)\s*[:：]?",
            "", t,
        ).strip(" 。，,、")
        add("delegate_agent", {"task": task, "confirm": False})

    # —— 显式记忆：用户要求「记住这个 / 记一下 / 记着」时，路由到 remember 工具 ——
    if "remember" not in seen and re.search(
        r"记住(这个|一下|这条|这件事|它)?[:：]?|记一下[:：]?|记着[:：]?|记到记忆(里)?|存到记忆|帮我记(住|下)?",
        t,
    ):
        c = re.sub(
            r"^(.*?)(记住(这个|一下|这条|这件事|它)?|记一下|记着|记到记忆(里)?|存到记忆|帮我记(住|下)?)[:：]?\s*",
            "",
            t,
        ).strip(" 。，,、？?")
        add("remember", {"content": c or t, "category": "fact", "importance": 0.7})

    # —— Phase 3：目标系统意图（Feature Flag 门控）——
    if _GOAL_ENABLED:
        _gid_m = re.search(r"#\s*(\d+)", t)
        # 创建目标：定个目标 / 规划 X / 立 flag
        if (
            re.search(
                r"定(个|一个)?\s*目标|设(个|一个)?\s*目标|帮我规划|规划一下|立个?\s*flag|定个?\s*flag|给我(设|定|建)个?\s*目标",
                t,
            )
            and "set_goal" not in seen
        ):
            title = re.sub(
                r"^(.*?)(定(个|一个)?\s*目标|设(个|一个)?\s*目标|帮我规划|规划一下|立个?\s*flag|定个?\s*flag|给我(设|定|建)个?\s*目标|目标)\s*[:：]?",
                "",
                t,
            ).strip(" 。，,、")
            add("set_goal", {"title": title or t})
        # 询问目标 / 进度
        elif (
            re.search(
                r"我(有|的)?\s*什么目标|有哪些目标|目标列表|我的目标|查看目标|看看目标|目标.*进度|进度.*目标|目标规划",
                t,
            )
            and "list_goals" not in seen
        ):
            add("list_goals", {"only_active": True})
        # 拆解目标：含 #id 时直接定位；含「这个目标/那个目标」时取最近活跃目标；否则先列目标让用户选
        if (
            re.search(
                r"拆(成|解|分|一下|出|开|步骤)|怎么推进|如何推进|怎么达成|如何达成|怎么实现|分步(推进|做)|推进一下",
                t,
            )
            and "plan_goal" not in seen
        ):
            if _gid_m:
                add("plan_goal", {"goal_id": int(_gid_m.group(1))})
            elif re.search(r"(这个|那个|当前|最近)\s*目标", t):
                try:
                    import goals as _goals

                    recent = _goals.list_active_goals(limit=1)
                    if recent:
                        add("plan_goal", {"goal_id": recent[0].id})
                    else:
                        add("list_goals", {"only_active": True})
                except Exception:
                    add("list_goals", {"only_active": True})
            else:
                add("list_goals", {"only_active": True})
        # 完成 / 放弃目标
        if (
            re.search(
                r"完成(了)?\s*(这个|那个)?\s*目标|目标(算)?\s*完成(了)?|放弃(这个|那个)?\s*目标|取消(这个|那个)?\s*目标|目标.*放弃|目标.*取消",
                t,
            )
            and "update_goal" not in seen
        ):
            _target_gid = None
            if _gid_m:
                _target_gid = int(_gid_m.group(1))
            elif re.search(r"(这个|那个|当前|最近)\s*目标", t):
                try:
                    import goals as _goals

                    recent = _goals.list_active_goals(limit=1)
                    if recent:
                        _target_gid = recent[0].id
                except Exception:
                    pass
            if _target_gid:
                _new_status = "completed"
                if re.search(r"放弃|取消", t):
                    _new_status = "archived"
                add("update_goal", {"goal_id": _target_gid, "status": _new_status})
            else:
                add("list_goals", {"only_active": True})

    # —— P4-B 持久知识库：归档当前对话 / 把资料存进知识库（独立意图，兜底 LLM 未调用）——
    if "archive_knowledge" not in seen and re.search(
        r"归档(这|当前|本|这次)?(段|个)?\s*对话|把(这|当前|本|这次)?(段|个)?\s*对话(存|记|归档)|记住我们(聊|说)|把(这次|这段)?\s*(聊天|对话).*(存|记)|记进知识库|存进知识库|存到知识库|记到知识库",
        t,
    ):
        add("archive_knowledge", {})
    elif "add_knowledge" not in seen and re.search(
        r"(把|将|给)\s*(这段|这份|这堆|这些|下面|以下)?\s*(.+?)\s*(存|记|放|加)\s*(进|入|到|进)?\s*知识库",
        t,
    ):
        mt = re.search(r"(把|将|给)\s*(?:这段|这份|这堆|这些|下面|以下)?\s*(.+?)\s*(?:存|记|放|加)\s*(?:进|入|到|进)?\s*知识库", t)
        text = mt.group(2).strip() if mt else ""
        if text:
            add("add_knowledge", {"text": text})

    # —— 兜底单一意图（避免与已识别意图重复）——
    primary = detect_intent(t)
    if primary and primary[0] not in seen:
        add(primary[0], primary[1])

    return intents


def execute_tool(name, args, allowed=None):
    # 远程会话白名单：未列入白名单的工具（含动态自定义工具）一律拒绝
    if allowed is not None and name not in allowed:
        return f"工具 {name} 在远程会话中不可用（受白名单限制）"
    fn = TOOL_FUNCS.get(name)
    if fn:
        try:
            return str(fn(args or {}))
        except Exception as e:
            # R8-P2：失败串携带异常类名，供上层 ERROR_TAXONOMY 恢复异常类型语义
            #（消费者匹配前缀/子串「工具执行失败」不受影响）
            return f"工具执行失败：{type(e).__name__}: {e}"
    # 自定义工具（工具工厂 / 动态 API 槽）
    try:
        from tool_factory import execute_custom_tool, get_custom_tool
        if get_custom_tool(name):
            return execute_custom_tool(name, args or {})
    except Exception as e:
        return f"自定义工具执行失败：{type(e).__name__}: {e}"
    # Phase 41 · 外部 MCP 能力（external.mcp.*）：单一执行链
    # tools.execute_tool → capability_os.execute_capability → mcp_host.MCPExecutor
    # → MCP Host → MCP Server → 结果；权限经 policy_engine。不复制、不绕过。
    if name.startswith("external.mcp."):
        try:
            from capability_os import execute_capability
            return execute_capability(name, args)
        except Exception as e:
            return f"外部 MCP 能力执行失败：{type(e).__name__}: {e}"
    # Phase C · G1 · 原生 Skill 句柄（skill:<name>）：单一执行链
    # tools.execute_tool → skills.execute_skill（取 body 指令包）→ Agent 经 TOOL_FUNCS 完成动作；
    # 复用既有执行内核，不新建第二执行器（§七 SECOND-SYSTEM GUARD）。
    if name.startswith("skill:"):
        from skills import execute_skill
        sname = name[len("skill:"):]
        res = execute_skill(sname, args)
        if res is None:
            return f"未知技能：{sname}"   # FAIL CLOSED
        return str(res)
    return f"未知工具：{name}"
