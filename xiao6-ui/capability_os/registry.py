#!/usr/bin/env python3
"""小6 · 能力操作系统 · 统一能力注册表（Capability Registry）—— Phase 23.1

职责：把散落在 4 处的「能力真相」收口为单一 Capability 模型：
  A. capability_os.registry（本文件）自持电脑能力目录（COND-A4 / CAP-08 D-CAP08-2 内化；原 capability_registry.py 废弃垫片已于 COND-A8 删除）
  B. capabilities.py           —— 上下文注入能力（hotspot/prefetch）
  C. tools.TOOL_FUNCS          —— 事实上的能力执行表（扁平工具）
  D. capability-exposure.js    —— UI 分类（仅参考，不在运行时依赖）

纪律（严格复用，禁新建）：
- 本文件【不执行任何能力】。它只描述「小6拥有哪些能力、各自用途、风险、权限、
  真实入口在哪」。执行一律委托既有入口（os_bridge / tools.execute_tool / 上下文源 /
  self_diagnosis），绝不复制或绕过。
- 不新建权限系统：permission 字段只是对既有 policy_engine / permission_guard 词汇的
  声明性镜像（auto/confirm/block），最终裁决仍由 Guard 做。
- CRITICAL 占位能力（delete/system/network）永久 available=False + permission=block，
  让 matcher/router 在语义层就拒绝，根本不会进入执行路径。

统一 Capability 模型（对齐 Phase 23 规格，并补充 id/group/icon/entry/data_source/keywords
以便自知、匹配、组合、UI 展示）：
  { id, name, description, group, icon, risk, permission, available,
    input, output, entry, data_source, keywords, implemented }
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# —— 风险等级（复用 policy_engine 词汇，不新建）——
class Risk:
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


# —— 权限档（镜像 permission_guard / policy_engine 的四级词汇）——
class Permission:
    AUTO = "auto"        # 自动执行（LOW）
    CONFIRM = "confirm"  # 需用户确认（MEDIUM）
    SESSION = "session"  # 会话级授权
    BLOCK = "block"      # 永久拒绝（CRITICAL 占位）


# —— 10 个产品能力域（与用户审计清单一一对应）——
GROUP_VOICE = "Voice"
GROUP_MEMORY = "Memory"
GROUP_KNOWLEDGE = "Knowledge"
GROUP_GOALS = "Goals"
GROUP_PERCEPTION = "Perception"
GROUP_COMPUTER_ACTION = "Computer Action"
GROUP_TOOLS = "Tools"
GROUP_WORLD_PULSE = "World Pulse"
GROUP_USER_MODEL = "User Model"
GROUP_SELF_DIAGNOSIS = "Self Diagnosis"


@dataclass
class Capability:
    id: str
    name: str
    description: str
    group: str
    icon: str
    risk: str = Risk.LOW
    permission: str = Permission.AUTO
    available: bool = True
    input: str = ""
    output: str = ""
    entry: str = ""           # 真实调用入口（描述性，执行仍走既有路径）
    data_source: str = ""
    keywords: List[str] = field(default_factory=list)
    implemented: bool = True
    target_kind: str = ""      # COND-A5 (CAP08-F5 形状对齐)：内化 target_kind 语义（D-CAP08-2 完成度）

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "group": self.group,
            "icon": self.icon,
            "risk": self.risk,
            "permission": self.permission,
            "available": self.available,
            "input": self.input,
            "output": self.output,
            "entry": self.entry,
            "data_source": self.data_source,
            "keywords": list(self.keywords),
            "implemented": self.implemented,
            "target_kind": self.target_kind,
        }


# —— 能力分组 → 路由相位（observe → understand → execute），见 router.py ——
OBSERVE_GROUPS = {GROUP_PERCEPTION, GROUP_SELF_DIAGNOSIS}
UNDERSTAND_GROUPS = {GROUP_MEMORY, GROUP_KNOWLEDGE, GROUP_USER_MODEL, GROUP_WORLD_PULSE}
EXECUTE_GROUPS = {GROUP_COMPUTER_ACTION, GROUP_TOOLS, GROUP_VOICE, GROUP_GOALS}


# —— 10 个产品级能力定义（关键词用于 matcher，entry 指向真实调用）——
def _product_catalog() -> List[Capability]:
    return [
        Capability(
            id="voice", name="语音", group=GROUP_VOICE, icon="🎙️",
            description="语音识别（ASR）与语音合成（TTS），让小6能听能说。",
            risk=Risk.LOW, permission=Permission.AUTO,
            input="音频 / 文本", output="文本 / 语音",
            entry="asr.transcribe / server._tts_sovits(GPT_SOVITS_URL)",
            data_source="本地 ASR + GPT-SoVITS(~9880)",
            keywords=["语音", "说话", "念", "读出来", "tts", "asr", "听写",
                       "语音输入", "说出来", "播报"],
        ),
        Capability(
            id="memory", name="记忆", group=GROUP_MEMORY, icon="🧠",
            description="短期对话记忆、长期记忆沉淀与重要性召回，让小6记得你。",
            risk=Risk.LOW, permission=Permission.AUTO,
            input="查询 / 新内容", output="记忆块 / 回忆",
            entry="memory.build_memory_block / memory_intelligence.recall",
            data_source="SQLite xiao6.db (memory_summary/learnings/memories)",
            keywords=["记忆", "记得", "之前", "上次", "历史", "总结过去", "我做过",
                       "开发内容", "记一下", "回忆"],
        ),
        Capability(
            id="knowledge", name="知识库", group=GROUP_KNOWLEDGE, icon="📚",
            description="本地知识文档检索与解析，基于 G:/Xiao6/knowledge/*.md。",
            risk=Risk.LOW, permission=Permission.AUTO,
            input="查询", output="相关文档片段",
            entry="knowledge.search / knowledge_runtime.engine",
            data_source="纯文件库 G:/Xiao6/knowledge/*.md",
            keywords=["知识库", "文档", "资料", "根据文档", "查资料", "笔记库",
                       "项目资料", "本地知识"],
        ),
        Capability(
            id="goals", name="目标", group=GROUP_GOALS, icon="🎯",
            description="目标与任务管理，小6据此自主拆解并执行多步任务。",
            risk=Risk.LOW, permission=Permission.AUTO,
            input="目标描述", output="目标/任务树",
            entry="goals.create_goal / goals.plan_goal",
            data_source="SQLite xiao6.db (goals/tasks)",
            keywords=["目标", "计划", "任务清单", "待办", "设定目标", "排个计划",
                       "帮我规划", "每日目标"],
        ),
        Capability(
            id="perception", name="屏幕感知", group=GROUP_PERCEPTION, icon="👁️",
            description="实时观察当前屏幕、前台窗口与可见文字（OCR），只读不落盘。",
            risk=Risk.LOW, permission=Permission.AUTO,
            input="屏幕像素", output="窗口/屏幕状态 + OCR 文本",
            entry="perception.observe / perception.get_state",
            data_source="实时屏幕（仅驻内存，不落盘）",
            keywords=["屏幕", "看到", "当前窗口", "前台", "桌面现在", "现在在做什么",
                       "截图", "窗口是什么", "正在看", "可见", "电脑", "电脑状态",
                       "当前电脑", "看电脑"],
        ),
        Capability(
            id="computer_action", name="电脑操作", group=GROUP_COMPUTER_ACTION, icon="✋",
            description="安全白名单内的电脑操作（打开应用/文件夹/文件、搜索、复制）。",
            risk=Risk.MEDIUM, permission=Permission.CONFIRM,
            input="动作意图", output="执行结果（经 Guard 验证）",
            entry="os_bridge.action_plan / action_execute / action_observe",
            data_source="OS（文件/窗口/剪贴板），白名单 5 动作",
            keywords=["打开", "文件夹", "应用", "文件", "搜索文件", "复制", "项目目录",
                       "启动", "资源管理器", "把窗口"],
        ),
        Capability(
            id="tools", name="工具", group=GROUP_TOOLS, icon="🛠️",
            description="通用本地工具集：查时间、计算、天气、网页搜索、浏览器阅读等。",
            risk=Risk.LOW, permission=Permission.AUTO,
            input="工具参数", output="工具结果",
            entry="tools.execute_tool(TOOL_FUNCS[name])",
            data_source="各异（文件/shell/网络/DB）",
            keywords=["计算", "天气", "网页", "搜索", "笔记", "查一下", "翻译",
                       "汇率", "提醒"],
        ),
        Capability(
            id="world_pulse", name="世界脉动", group=GROUP_WORLD_PULSE, icon="🌐",
            description="实时热点、热榜与新闻预取，让小6紧跟时事。",
            risk=Risk.LOW, permission=Permission.AUTO,
            input="话题", output="热榜/新闻上下文",
            entry="hotspots.build_hotspot_context / prefetch.get_valid_prefetch",
            data_source="外部热点 API + 天气/科技新闻聚合",
            keywords=["热点", "热搜", "新闻", "榜单", "今天发生", "热榜", "微博",
                       "抖音", "头条", "时事"],
        ),
        Capability(
            id="user_model", name="用户画像", group=GROUP_USER_MODEL, icon="🪪",
            description="记住你是谁、你的项目与偏好，带可信度治理。",
            risk=Risk.LOW, permission=Permission.AUTO,
            input="画像查询/更新", output="用户模型块",
            entry="cognitive.user_model.load_user_model / upsert_user_model",
            data_source="SQLite xiao6.db (user_model 单行 JSON)",
            keywords=["我是谁", "我的偏好", "关于我", "用户画像", "我一般", "我喜欢",
                       "我常用", "我的项目"],
        ),
        Capability(
            id="self_diagnosis", name="启动自检", group=GROUP_SELF_DIAGNOSIS, icon="🩺",
            description="启动期与按需体检：检测 7 大子系统健康、给出修复建议。",
            risk=Risk.LOW, permission=Permission.AUTO,
            input="无", output="健康报告 + 修复建议",
            entry="self_diagnosis.run_check / os_bridge.selfcheck",
            data_source="只读探测（DB/ASR/SoVITS socket/Guard 挂载）",
            keywords=["自检", "健康", "状态", "有问题", "诊断", "哪里坏了", "组件",
                       "正常吗", "检查系统", "体检"],
        ),
        # —— 细粒度工具能力（供 test1「现在几点」→ time 精确命中）——
        Capability(
            id="time", name="时间", group=GROUP_TOOLS, icon="🕐",
            description="查询当前日期与时间。",
            risk=Risk.LOW, permission=Permission.AUTO,
            input="无", output="当前时间",
            entry="tools.tool_get_time",
            data_source="本地时钟",
            keywords=["几点", "时间", "现在几点", "几点了", "日期", "今天几号",
                       "星期几", "现在是什么时候"],
        ),
        # —— CRITICAL 占位能力（永久 block，验证危险任务拒绝）——
        Capability(
            id="delete", name="删除", group=GROUP_COMPUTER_ACTION, icon="🗑️",
            description="删除文件/资源（不可逆）。当前未实现且被永久拒绝。",
            risk=Risk.CRITICAL, permission=Permission.BLOCK,
            available=False, implemented=False,
            input="目标", output="——",
            entry="（无，CRITICAL 占位）",
            data_source="——",
            keywords=["删除", "删掉", "清空", "rm", "彻底删除"],
        ),
        Capability(
            id="system", name="系统操作", group=GROUP_COMPUTER_ACTION, icon="⚙️",
            description="系统级变更（重启/配置）。当前未实现且被永久拒绝。",
            risk=Risk.CRITICAL, permission=Permission.BLOCK,
            available=False, implemented=False,
            input="目标", output="——",
            entry="（无，CRITICAL 占位）",
            data_source="——",
            keywords=["重启", "关机", "改配置", "系统设置", "格式化"],
        ),
        Capability(
            id="network", name="网络操作", group=GROUP_COMPUTER_ACTION, icon="📡",
            description="网络级变更（防火墙/代理）。当前未实现且被永久拒绝。",
            risk=Risk.CRITICAL, permission=Permission.BLOCK,
            available=False, implemented=False,
            input="目标", output="——",
            entry="（无，CRITICAL 占位）",
            data_source="——",
            keywords=["防火墙", "代理", "改网络", "断网"],
        ),
    ]


# —— COND-A4 (CAP-08 D-CAP08-2)：内化 20 项电脑能力目录（替代 capability_registry._CAPABILITIES 冻结快照）——
# 字段语义与旧 _build 合并逻辑逐元素一致：permission 由 implemented/risk 推导，group 固定 Computer Action。
# delete/system/network 维持 available=False + permission=BLOCK（CRITICAL 占位，语义层拒绝，与产品目录一致）。
_COMPUTER_ACTION_CAPABILITIES: Dict[str, dict] = {
    # LOW：只读 / 无副作用
    "read_file":       {"label": "读取文件",   "risk": Risk.LOW,      "target_kind": "file",
                        "expected_effect": "返回文件内容预览（不修改）"},
    "capture_screen":   {"label": "截取屏幕",   "risk": Risk.LOW,      "target_kind": "screen",
                        "expected_effect": "返回当前屏幕截图（不修改）"},
    "get_window_info":  {"label": "获取窗口信息", "risk": Risk.LOW,    "target_kind": "window",
                        "expected_effect": "返回指定窗口的几何/状态信息"},
    "list_process":     {"label": "列举进程",   "risk": Risk.LOW,      "target_kind": "process",
                        "expected_effect": "返回当前进程列表（只读）"},
    "perception.screen": {"label": "屏幕感知",  "risk": Risk.LOW,      "target_kind": "screen",
                        "expected_effect": "返回当前屏幕分辨率与显示器信息（只读，不落盘）"},
    "perception.window": {"label": "窗口感知",  "risk": Risk.LOW,      "target_kind": "window",
                        "expected_effect": "返回当前前台窗口与进程信息（只读）"},
    "perception.ocr":    {"label": "屏幕文字识别", "risk": Risk.LOW,   "target_kind": "screen",
                        "expected_effect": "本地 OCR 读取屏幕可见文字（脱敏，不落盘，不送云端）"},
    "open_folder":     {"label": "打开文件夹", "risk": Risk.MEDIUM,   "target_kind": "folder",
                        "expected_effect": "在资源管理器打开指定文件夹（仅切换视图，不修改）"},
    "open_file":       {"label": "打开文件",   "risk": Risk.MEDIUM,   "target_kind": "file",
                        "expected_effect": "用默认程序打开指定文件（只读副作用，不修改）"},
    "search":          {"label": "搜索文件",   "risk": Risk.LOW,      "target_kind": "filesystem",
                        "expected_effect": "在指定根目录检索文件名/内容（只读，不修改）"},
    "copy_text":       {"label": "复制文本",   "risk": Risk.LOW,      "target_kind": "text",
                        "expected_effect": "复制给定文本或文件片段到剪贴板（不修改源）"},
    # MEDIUM：有界面副作用，需确认
    "open_application": {"label": "打开应用",   "risk": Risk.MEDIUM,   "target_kind": "application",
                        "expected_effect": "启动指定应用（会切换焦点/占用资源）"},
    "focus_window":     {"label": "聚焦窗口",   "risk": Risk.MEDIUM,   "target_kind": "window",
                        "expected_effect": "把指定窗口提到前台（会改变用户焦点）"},
    "browser_navigate": {"label": "浏览器导航", "risk": Risk.MEDIUM,   "target_kind": "browser",
                        "expected_effect": "在浏览器打开/跳转 URL（有网络与外显副作用）"},
    # 未实现（仅声明；占位，语义层拒绝）
    "modify_file":      {"label": "修改文件",   "risk": Risk.HIGH,     "target_kind": "file",
                        "expected_effect": "写入/修改文件内容（破坏性）", "implemented": False},
    "execute_command":  {"label": "执行命令",   "risk": Risk.HIGH,     "target_kind": "process",
                        "expected_effect": "运行 shell 命令（高危）", "implemented": False},
    "kill_process":     {"label": "结束进程",   "risk": Risk.HIGH,     "target_kind": "process",
                        "expected_effect": "终止进程（可能丢数据）", "implemented": False},
    "delete":           {"label": "删除",       "risk": Risk.CRITICAL, "target_kind": "any",
                        "expected_effect": "删除文件/资源（不可逆）", "implemented": False},
    "system":           {"label": "系统操作",   "risk": Risk.CRITICAL, "target_kind": "system",
                        "expected_effect": "系统级变更（重启/配置）", "implemented": False},
    "network":          {"label": "网络操作",   "risk": Risk.CRITICAL, "target_kind": "network",
                        "expected_effect": "网络级变更（防火墙/代理）", "implemented": False},
}


def _computer_action_catalog() -> List[Capability]:
    """COND-A4 (D-CAP08-2)：内化电脑能力目录，返回与旧 _build 合并逻辑逐元素一致的 Capability 列表。"""
    out: List[Capability] = []
    for cid, meta in _COMPUTER_ACTION_CAPABILITIES.items():
        implemented = meta.get("implemented", True)
        risk = meta.get("risk", Risk.UNKNOWN)
        perm = Permission.BLOCK if not implemented else (
            Permission.CONFIRM if risk == Risk.MEDIUM else Permission.AUTO)
        out.append(Capability(
            id=cid, name=meta.get("label", cid), group=GROUP_COMPUTER_ACTION,
            icon="✋", description=meta.get("expected_effect", ""),
            risk=risk, permission=perm,
            available=implemented, implemented=implemented,
            entry="os_bridge.action_* (whitelist)",
            data_source="OS", target_kind=meta.get("target_kind", ""),
            keywords=[cid.replace("_", " ")],
        ))
    return out


_REGISTRY: Dict[str, Capability] = {}
_BUILT = False


def _build() -> None:
    """构建统一注册表（幂等，只读聚合现有真相源）。"""
    global _REGISTRY, _BUILT
    if _BUILT:
        return
    for cap in _product_catalog():
        _REGISTRY[cap.id] = cap

    # COND-A4 (D-CAP08-2)：内化电脑能力目录，不再从 capability_registry 合并（垫片 EXIT 路径）。
    # setdefault 保证产品目录中同 id 的 CRITICAL 占位（delete/system/network）优先，语义一致。
    for cap in _computer_action_catalog():
        _REGISTRY.setdefault(cap.id, cap)

    # 复用 B：capabilities.py 的上下文注入能力
    try:
        import capabilities as caps
        for cid, meta in caps.CAPABILITIES.items():
            _REGISTRY.setdefault(cid, Capability(
                id=cid, name=meta.get("label", cid), group=GROUP_WORLD_PULSE,
                icon=meta.get("icon", "🌐"),
                description=meta.get("description", ""),
                risk=Risk.LOW, permission=Permission.AUTO,
                entry="context_injection(" + cid + ")",
                data_source="外部 API/聚合",
                keywords=list(meta.get("triggers", [])),
            ))
    except Exception:
        pass

    _BUILT = True


def get_registry() -> Dict[str, Capability]:
    _build()
    bootstrap_policy_seeds()  # COND-A4 (D-CAP08-3)：首次访问即播种（幂等）
    return _REGISTRY


def get_capability(cap_id: str) -> Optional[Capability]:
    return get_registry().get(cap_id)


def list_capabilities() -> List[Capability]:
    return list(get_registry().values())


def available_capabilities() -> List[Capability]:
    return [c for c in list_capabilities() if c.available]


def get_groups() -> Dict[str, List[Capability]]:
    out: Dict[str, List[Capability]] = {}
    for c in list_capabilities():
        out.setdefault(c.group, []).append(c)
    return out


def register_capability(cap: Capability) -> None:
    """Phase 41 · 动态注册外部 MCP 能力（discovered → map）。

    纪律：这是既有统一注册表的【受控扩展点】，不是第二套注册表。
    仅由 mcp_host 在「服务器已启动 + 工具已发现」后调用，
    绝不改变 Phase 40 既有 33 项产品能力的真相。
    幂等：同 id 覆盖。
    """
    global _BUILT
    _BUILT = True
    _REGISTRY[cap.id] = cap


# —— COND-A4 (CAP-08 D-CAP08-3)：READONLY_TOOLS 种子（原 capability_registry._register_into_policy_engine 职责 relocate 到 canonical）——
# 历史 _LOW_CAPS 9 项（迁移守卫：删垫片前必须逐元素一致，见 CAP-08 §3.3）。
_COMPUTER_ACTION_LOW_SEED = {
    "read_file", "capture_screen", "get_window_info", "list_process",
    "perception.screen", "perception.window", "perception.ocr",
    "search", "copy_text",
}
_SEED_BOOTSTRAPPED = False


def bootstrap_policy_seeds() -> None:
    """COND-A4 (D-CAP08-3)：将 canonical 中 risk==LOW && available==True 的电脑动作能力登记进
    tools.READONLY_TOOLS（auto 种子）。与历史 _LOW_CAPS 9 项逐元素一致（CAP-08 §3.3 迁移守卫）。幂等。

    种子范围限定 GROUP_COMPUTER_ACTION（电脑动作 id），与历史 _LOW_CAPS 严格对应；
    产品能力（voice/memory/.../time）为能力语义 id，非工具/动作执行名，不入 READONLY_TOOLS。
    """
    global _SEED_BOOTSTRAPPED
    if _SEED_BOOTSTRAPPED:
        return
    _build()
    seed = {c.id for c in _REGISTRY.values()
            if c.group == GROUP_COMPUTER_ACTION and c.risk == Risk.LOW and c.available}
    # 迁移守卫：种子集合与历史 _LOW_CAPS 逐元素一致（CAP-08 D-CAP08-3 / §3.3）。
    # 守卫始终执行，差异即显式抛出，CI 可捕获，不静默吞掉。
    assert seed == _COMPUTER_ACTION_LOW_SEED, (
        f"READONLY_TOOLS 种子漂移（CAP-08 守卫失败）: 差异={seed ^ _COMPUTER_ACTION_LOW_SEED}")
    try:
        from tools import READONLY_TOOLS
        READONLY_TOOLS.update(seed)
    except Exception:
        # tools 不可用（纯单测隔离场景）：种子已通过守卫，仅跳过写入，能力仍可被识别
        pass
    _SEED_BOOTSTRAPPED = True


# —— COND-A4 (CAP-08 D-CAP08-4)：只读帮助函数（不新增权限/执行逻辑，全部委托 canonical 真相）——
def is_known(cap_id: str) -> bool:
    """能力是否已知（委托 canonical 真相）。≡ get_capability(cap_id) is not None"""
    return get_capability(cap_id) is not None


def is_implemented(cap_id: str) -> bool:
    c = get_capability(cap_id)
    return bool(getattr(c, "implemented", True)) if c else False


def risk_of(cap_id: str) -> str:
    c = get_capability(cap_id)
    return getattr(c, "risk", Risk.UNKNOWN) if c else Risk.UNKNOWN


# 风险 → Policy Engine 授权层级（复用 policy_engine 词汇；字面值与 AUTO/CONFIRM 对齐，避免顶层循环 import）
RISK_TIER = {"LOW": "auto", "MEDIUM": "confirm"}


def tier_of(cap_id: str) -> str:
    """能力风险映射到的 Policy Engine 层级（复用既有词汇）。"""
    return RISK_TIER.get(risk_of(cap_id), "confirm")
