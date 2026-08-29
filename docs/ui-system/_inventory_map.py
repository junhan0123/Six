# -*- coding: utf-8 -*-
"""把全部 CSS 选择器归类到 UI Element Inventory 的分类桶（只读），并给出文件归属与交互来源。"""
import re, os, json, collections

UI = r"G:\Xiao6\xiao6-ui"
CSS = ["styles.css", "premium.css", "runtime-viz.css", "execution-channel.css", "ui2.css", "companion.css"]

# 分类 → 选择器匹配前缀（基于真实命名空间，不臆造）
CATS = [
    ("App Shell / 布局",        [r"^\.os-shell", r"^\.app\b", r"^\.os-bottom", r"^body", r"^html", r"^\*"]),
    ("HUD / 顶栏",              [r"^\.os-hud", r"^\.hud-", r"^#osHud"]),
    ("Navigation / 导航",       [r"^\.os-nav", r"^\.rail", r"^\.nav-"]),
    ("Galaxy / 星系",           [r"^\.gx-", r"^#universeView", r"^\.galaxy", r"^\.uv-"]),
    ("Avatar / 化身",           [r"^\.avatar", r"^\.orb-", r"^#osCoreCanvas", r"^\.os-core"]),
    ("Command Dock",            [r"^\.os-dock", r"^\.dock\b", r"^\.dock-"]),
    ("Command Palette",         [r"^\.cp-"]),
    ("Settings / 设置",         [r"^\.settings-", r"^#settings"]),
    ("Context Drawer / 抽屉",   [r"^\.os-side", r"^\.tele", r"^\.side-"]),
    ("Capability Matrix",       [r"^\.cap-", r"^\.os-cap", r"^#capPanel"]),
    ("Insight / 洞察",          [r"^\.insight", r"^\.briefing", r"^\.proactive"]),
    ("Execution / 执行",        [r"^\.em-", r"^\.exec", r"^\.ec-", r"^#execution"]),
    ("Runtime Viz",             [r"^\.rv-", r"^#runtime-viz"]),
    ("Workspace",               [r"^\.ws-", r"^\.workspace", r"^\.panel-host"]),
    ("Chat / 对话",             [r"^\.chat-", r"^\.msg", r"^\.bubble", r"^\.conv-", r"^\.quick-"]),
    ("Tasks / 任务",            [r"^\.ts-", r"^\.task", r"^\.zzTask"]),
    ("Goals / 目标",            [r"^\.goal"]),
    ("Memory / 记忆",           [r"^\.mem-", r"^\.memq-", r"^\.memory", r"^#memPanel"]),
    ("Agent / 代理",            [r"^\.agent", r"^\.appr-", r"^\.act-"]),
    ("Profile / 档案",          [r"^\.profile", r"^\.pt-"]),
    ("Notifications / 通知",    [r"^\.notif", r"^\.zz-panel", r"^#zzPanel"]),
    ("Toast",                   [r"^\.toast", r"^#toast"]),
    ("Modal / 模态",            [r"^\.modal", r"^\.overlay", r"^\.sysprompt"]),
    ("Onboarding / 引导",       [r"^\.onb-"]),
    ("Loading / 加载",          [r"^\.load", r"^\.skeleton", r"^\.spinner"]),
    ("Empty / 空态",            [r"^\.empty", r"-empty"]),
    ("Error / 错误",            [r"^\.error", r"^\.err-"]),
    ("Provider Settings",       [r"^\.provider", r"^\.prov-"]),
    ("Theme Selector",          [r"^\.theme-", r"^\.t-[a-z]", r"^\.onb-theme"]),
    ("Buttons / 按钮",          [r"^\.btn", r"^button", r"^\.zz-button"]),
    ("Inputs / 输入",           [r"^\.input", r"^input", r"^textarea", r"^\.term-"]),
    ("Select / 选择器",         [r"^select", r"^\.select"]),
    ("Cards / 卡片",            [r"^\.card", r"^\.glass-card", r"^\.glass-panel"]),
    ("Badges / 徽标",           [r"^\.badge", r"^\.tag\b"]),
    ("Chips / 芯片",            [r"^\.chip"]),
    ("Tabs / 标签页",           [r"^\.tab"]),
    ("Tooltips / 提示",         [r"^\.tip", r"^\.tooltip", r"\[data-tip"]),
    ("Dropdown / 下拉",         [r"^\.dropdown", r"^\.more-", r"^\.menu"]),
    ("Scrollbars / 滚动条",     [r"::-webkit-scrollbar", r"scrollbar"]),
    ("Status / 状态指示",       [r"^\.status", r"^\.is-", r"^\.dot\b", r"^\.sm-", r"^\.sc-"]),
    ("Presence / 存在感",       [r"\[data-presence", r"^\.presence"]),
    ("Mobile / 移动",           [r"^\.mobile", r"^\.m-"]),
    ("Companion / 伴生窗",      [r"^\.cmp-", r"^\.companion"]),
    ("Icons / 图标",            [r"^\.ic\b", r"^\.zz-icon", r"^\.icon"]),
    ("Hotspot / 热点(领域)",    [r"^\.hs-", r"^\.hotspot", r"^#hs-"]),
    ("Weather / 天气(领域)",    [r"^\.wx-", r"^\.weather"]),
    ("Map / 地图(领域)",        [r"^\.map-", r"^\.loc-"]),
    ("Doc / 文档(领域)",        [r"^\.doc-"]),
    ("Scene / 场景(领域)",      [r"^\.scene", r"^\.video-", r"^\.sc-"]),
    ("Mic / 语音(领域)",        [r"^\.mic", r"^\.tts-", r"^\.kws"]),
    ("Review / 复核(领域)",     [r"^\.review", r"^\.learn-"]),
    ("Tools / 工具(领域)",      [r"^\.tool-"]),
]

def parse_sels(f):
    p = os.path.join(UI, f)
    t = re.sub(r"/\*.*?\*/", "", open(p, encoding="utf-8", errors="replace").read(), flags=re.S)
    out = []
    for m in re.finditer(r"([^{}]+)\{[^{}]*\}", t):
        head = m.group(1).strip().split("\n")[-1].strip()
        if head.startswith("@") or not head: continue
        for s in head.split(","):
            s = " ".join(s.split())
            if s: out.append(s)
    return out

file_sels = {f: parse_sels(f) for f in CSS}

# JS 交互来源映射（真实文件存在性校验）
JS_OWNER = {
    "HUD / 顶栏": "app.js", "Navigation / 导航": "app.js / panel-manager.js",
    "Galaxy / 星系": "galaxy-experience.js / galaxy-runtime.js", "Avatar / 化身": "avatar-renderer.js / avatar-state.js",
    "Command Dock": "command-dock.js", "Command Palette": "command-palette.js",
    "Settings / 设置": "settings.js", "Context Drawer / 抽屉": "panel-manager.js",
    "Capability Matrix": "capability-matrix.js / capabilities-view.js", "Insight / 洞察": "insight-panel.js",
    "Execution / 执行": "execution-channel.js / execution-timeline.js", "Runtime Viz": "runtime-visualization.js",
    "Chat / 对话": "app.js", "Tasks / 任务": "tasks.js", "Memory / 记忆": "memory.js / memory-panel.js / memory-query.js",
    "Toast": "app.js", "Modal / 模态": "overlay-manager.js", "Onboarding / 引导": "onboarding.js",
    "Companion / 伴生窗": "companion.js", "Hotspot / 热点(领域)": "hotspot.js", "Weather / 天气(领域)": "weather.js",
    "Map / 地图(领域)": "map.js", "Doc / 文档(领域)": "doc.js", "Scene / 场景(领域)": "scene.js",
    "Mic / 语音(领域)": "kws.js", "Status / 状态指示": "sysmon.js", "Error / 错误": "error-boundary.js",
    "Mobile / 移动": "mobile-app.js",
}
js_exists = {f for f in os.listdir(UI) if f.endswith(".js")}

rows = []
claimed = set()
for name, pats in CATS:
    rx = [re.compile(p) for p in pats]
    per_file = collections.Counter()
    for f, sels in file_sels.items():
        for s in sels:
            if any(r.search(s) for r in rx):
                per_file[f] += 1
                claimed.add((f, s))
    total = sum(per_file.values())
    owners = [f for f in CSS if per_file.get(f)]
    js = JS_OWNER.get(name, "")
    if js:
        miss = [x.strip() for x in js.replace("/", " ").split() if x.endswith(".js") and x not in js_exists]
        if miss: js += "  ⚠缺失:" + ",".join(miss)
    rows.append({"cat": name, "total": total, "files": {f: per_file.get(f, 0) for f in owners},
                 "multiFile": len(owners) > 1, "js": js})

print("=" * 118)
print(f"{'分类':26s}{'规则数':>7} {'样式来源文件（数量）':52s} {'多源':5s} 交互来源")
print("=" * 118)
for r in rows:
    src = " + ".join(f"{f.replace('.css','')}({n})" for f, n in r["files"].items()) or "—"
    print(f"{r['cat']:26s}{r['total']:>7} {src[:52]:52s} {'⚠' if r['multiFile'] else ' ':5s} {r['js']}")

allsel = sum(len(v) for v in file_sels.values())
print("\n" + "=" * 118)
print(f"选择器总数 {allsel}，已归类 {len(claimed)}，未归类 {allsel - len(claimed)}")
print(f"分类数 {len(rows)}，其中多文件来源（需判定是否分叉）{sum(1 for r in rows if r['multiFile'])} 个")

# 未归类样本
unclaimed = []
for f, sels in file_sels.items():
    for s in sels:
        if (f, s) not in claimed: unclaimed.append(f + " :: " + s)
print(f"\n未归类样本（前 40，用于发现遗漏元素）:")
for u in unclaimed[:40]: print("   " + u[:104])

json.dump({"rows": rows, "unclaimed_count": len(unclaimed), "unclaimed_sample": unclaimed[:200]},
          open(r"G:\Xiao6\docs\ui-system\_inventory_map.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("\nWROTE _inventory_map.json")
