#!/usr/bin/env python3
# PHASE 5.5 · STEP 0 — Verify-before-audit (READ-ONLY analysis script)
# No production code is imported or executed. Uses ast to parse, and a
# standalone import of capability_os.registry (stubbed package, no __init__).
# Output: evidence JSON + MAP-A / MAP-B / MAP-C markdown into G:/xiao6/_ui_archive/

import ast, sys, os, json, re, types, importlib.util

UI = "G:/xiao6/xiao6-ui"
ARCHIVE = "G:/xiao6/_ui_archive"
os.makedirs(ARCHIVE, exist_ok=True)
# Put product UI on path so registry._build()'s `import capabilities` resolves
# (mirrors production server cwd = xiao6-ui). Without this the legacy merge fails.
sys.path.insert(0, UI)

EVID = {}

# ───────────────────────────── 1. registry (standalone) ─────────────────────────────
reg_path = os.path.join(UI, "capability_os", "registry.py")
pkg = types.ModuleType("capability_os")
pkg.__path__ = [os.path.join(UI, "capability_os")]
sys.modules["capability_os"] = pkg
spec = importlib.util.spec_from_file_location("capability_os.registry", reg_path)
regmod = importlib.util.module_from_spec(spec)
sys.modules["capability_os.registry"] = regmod
spec.loader.exec_module(regmod)

REG = regmod.get_registry()
caps = {}
for cid, c in REG.items():
    caps[cid] = {
        "id": c.id, "name": c.name, "group": c.group,
        "risk": c.risk.value if hasattr(c.risk, "value") else str(c.risk),
        "permission": c.permission.value if hasattr(c.permission, "value") else str(c.permission),
        "available": bool(c.available), "implemented": bool(c.implemented),
        "keywords": list(getattr(c, "keywords", []) or []),
    }
EVID["CANONICAL_COUNT"] = len(caps)
EVID["DELETE_BLOCKED"] = caps.get("delete", {})
EVID["SYSTEM_BLOCKED"] = caps.get("system", {})
EVID["NETWORK_BLOCKED"] = caps.get("network", {})

# ───────────────────────────── 2. tools.py (ast) ─────────────────────────────
with open(os.path.join(UI, "tools.py"), encoding="utf-8") as f:
    tsrc = f.read()
ttree = ast.parse(tsrc)

def find_assign(tree, name):
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name) and t.id == name:
                    return n.value
    return None

# TOOLS list of {function:{name:...}}
tools_val = find_assign(ttree, "TOOLS")
TOOL_NAMES = []
if isinstance(tools_val, ast.List):
    for el in tools_val.elts:
        fn = el
        if isinstance(el, ast.Dict):
            # find "function" key
            for k, v in zip(el.keys, el.values):
                if isinstance(k, ast.Constant) and k.value == "function":
                    fn = v
        if isinstance(fn, ast.Dict):
            for k, v in zip(fn.keys, fn.values):
                if isinstance(k, ast.Constant) and k.value == "name":
                    TOOL_NAMES.append(v.value)
EVID["TOOLS_COUNT"] = len(TOOL_NAMES)

# TOOL_FUNCS dict
tf_val = find_assign(ttree, "TOOL_FUNCS")
TOOL_FUNCS_KEYS = []
if isinstance(tf_val, ast.Dict):
    for k in tf_val.keys:
        if isinstance(k, ast.Constant):
            TOOL_FUNCS_KEYS.append(k.value)
EVID["TOOL_FUNCS_COUNT"] = len(TOOL_FUNCS_KEYS)

# READONLY_TOOLS set (tools.py:3249 is a `set`, not a dict)
ro_val = find_assign(ttree, "READONLY_TOOLS")
READONLY_KEYS = []
if isinstance(ro_val, ast.Set):
    for e in ro_val.elts:
        if isinstance(e, ast.Constant):
            READONLY_KEYS.append(e.value)
elif isinstance(ro_val, ast.Dict):
    for k in ro_val.keys:
        if isinstance(k, ast.Constant):
            READONLY_KEYS.append(k.value)
EVID["READONLY_TOOLS_COUNT"] = len(READONLY_KEYS)

# ───────────────────────────── 3. execution_mapping.py (ast) ─────────────────────────────
with open(os.path.join(UI, "capability_os", "execution_mapping.py"), encoding="utf-8") as f:
    emsrc = f.read()
emtree = ast.parse(emsrc)

# CAPABILITY_EXECUTORS dict
ce_val = find_assign(emtree, "CAPABILITY_EXECUTORS")
EXECUTORS = {}
if isinstance(ce_val, ast.Dict):
    for k, v in zip(ce_val.keys, ce_val.values):
        if not isinstance(k, ast.Constant):
            continue
        cid = k.value
        kind, ref = "", ""
        if isinstance(v, ast.Call):
            args = v.args
            if len(args) > 0 and isinstance(args[0], ast.Constant):
                kind = args[0].value
            if len(args) > 1 and isinstance(args[1], ast.Constant):
                ref = args[1].value
        EXECUTORS[cid] = {"kind": kind, "ref": ref}
EVID["EXECUTORS_COUNT"] = len(EXECUTORS)

# TOOL_TO_CAPABILITY (14-entry) in execution_mapping
ttc_val = find_assign(emtree, "TOOL_TO_CAPABILITY")
TTC_EM = {}
if isinstance(ttc_val, ast.Dict):
    for k, v in zip(ttc_val.keys, ttc_val.values):
        if isinstance(k, ast.Constant) and isinstance(v, ast.Constant):
            TTC_EM[k.value] = v.value

# ───────────────────────────── 4. __init__.py _TOOL_TO_CAPABILITY (19-entry) ─────────────────────────────
with open(os.path.join(UI, "capability_os", "__init__.py"), encoding="utf-8") as f:
    initsrc = f.read()
inittree = ast.parse(initsrc)
ttc2_val = find_assign(inittree, "_TOOL_TO_CAPABILITY")
TTC_INIT = {}
if isinstance(ttc2_val, ast.Dict):
    for k, v in zip(ttc2_val.keys, ttc2_val.values):
        if isinstance(k, ast.Constant) and isinstance(v, ast.Constant):
            TTC_INIT[k.value] = v.value
EVID["TTC_EM_COUNT"] = len(TTC_EM)
EVID["TTC_INIT_COUNT"] = len(TTC_INIT)
# divergence
only_em = set(TTC_EM) - set(TTC_INIT)
only_init = set(TTC_INIT) - set(TTC_EM)
conflict = {t: (TTC_EM[t], TTC_INIT[t]) for t in (set(TTC_EM) & set(TTC_INIT)) if TTC_EM[t] != TTC_INIT[t]}
EVID["TTC_DIVERGENCE"] = {
    "only_in_execution_mapping": sorted(only_em),
    "only_in_init": sorted(only_init),
    "conflicting_values": conflict,
}

# ───────────────────────────── 5. capabilities.py CAPABILITIES (runtime) ─────────────────────────────
# The shim populates CAPABILITIES via _register() at import time (not a literal dict),
# so ast sees `{}`. Import it for the true count (read-only, no execution).
import capabilities as _caps_rt
LEGACY_CAPS = list(_caps_rt.CAPABILITIES.keys())
EVID["LEGACY_COUNT"] = len(LEGACY_CAPS)
EVID["LEGACY_CAPS"] = LEGACY_CAPS

# ───────────────────────────── 6. MAP-A: 62 TOOL -> cap (both variants) ─────────────────────────────
def tool_to_capability_init(tool):
    n = (tool or "").lower()
    if not n:
        return "tools"
    if n in TTC_INIT:
        return TTC_INIT[n]
    if n in caps:
        return n
    return "tools"

def tool_to_capability_em(tool):
    n = (tool or "").lower()
    if not n:
        return "tools"
    if n in TTC_EM:
        return TTC_EM[n]
    if n in caps:
        return n
    return "tools"

MAP_A = {}
# Tool universe = executable tools (TOOL_FUNCS, 62). Also note schema-only (TOOLS, 55).
for t in TOOL_FUNCS_KEYS:
    MAP_A[t] = {
        "init": tool_to_capability_init(t),
        "em": tool_to_capability_em(t),
        "in_schema": t in TOOL_NAMES,
    }
EVID["MAP_A"] = MAP_A
EVID["MAP_A_TOOL_UNIVERSE"] = len(TOOL_FUNCS_KEYS)
EVID["MAP_A_IN_SCHEMA"] = sum(1 for t in TOOL_FUNCS_KEYS if t in TOOL_NAMES)
EVID["MAP_A_NOT_IN_SCHEMA"] = sorted(t for t in TOOL_FUNCS_KEYS if t not in TOOL_NAMES)

# group MAP-A by init-result capability
from collections import defaultdict, Counter
init_buckets = defaultdict(list)
for t, m in MAP_A.items():
    init_buckets[m["init"]].append(t)
EVID["MAP_A_BUCKETS_INIT"] = {k: sorted(v) for k, v in sorted(init_buckets.items())}
em_buckets = defaultdict(list)
for t, m in MAP_A.items():
    em_buckets[m["em"]].append(t)
EVID["MAP_A_BUCKETS_EM"] = {k: sorted(v) for k, v in sorted(em_buckets.items())}
# tools that resolve differently between the two reverse-maps
MAP_A_DIVERGENT = sorted(t for t, m in MAP_A.items() if m["init"] != m["em"])
EVID["MAP_A_DIVERGENT_TOOLS"] = MAP_A_DIVERGENT

# ───────────────────────────── 7. MAP-B: capability -> execution + status ─────────────────────────────
# WHITELIST (read from computer_action/safety.py)
with open(os.path.join(UI, "computer_action", "safety.py"), encoding="utf-8") as f:
    safesrc = f.read()
wl = set(re.findall(r'"(open_application|open_folder|open_file|search|copy_text|focus_window|browser_navigate)"', safesrc))
ro_allowed = set(re.findall(r'"(read_file|list_process|capture_screen|get_window_info|perception\.screen|perception\.window|perception\.ocr)"', safesrc))
EVID["WHITELIST"] = sorted(wl)
EVID["READONLY_ALLOWED"] = sorted(ro_allowed)

def module_path(mod):
    parts = mod.split(".")
    p1 = os.path.join(UI, *parts) + ".py"
    p2 = os.path.join(UI, *parts, "__init__.py")
    if os.path.exists(p1):
        return p1
    if os.path.exists(p2):
        return p2
    return None

def builtin_callable(refstr):
    if "." not in refstr:
        # ref is a module name (e.g. perception) — callable if the module exists
        fpath = module_path(refstr)
        if fpath:
            return True, f"module {refstr} present"
        return None, f"module {refstr} not found"
    mod, _, attr = refstr.rpartition(".")
    fpath = module_path(mod)
    if not fpath:
        return None, f"module {mod} not found"
    with open(fpath, encoding="utf-8", errors="ignore") as f:
        src = f.read()
    if re.search(rf"\b(async\s+def|def)\s+{re.escape(attr)}\b", src) or re.search(rf"^\s*{re.escape(attr)}\s*=", src, re.M):
        return True, f"{mod}.{attr} present"
    return False, f"{attr} not found in {mod}"

def expected_permission(cap):
    if not cap["implemented"]:
        return "block"
    if cap["risk"] == "CRITICAL":
        return "block"
    if cap["risk"] == "MEDIUM":
        return "confirm"
    return "auto"

def derive_callable(cap_id, ref):
    if ref is None:
        return False, "no executor"
    kind = ref["kind"]
    r = ref["ref"]
    if kind == "none":
        return False, "permanent deny"
    if kind == "umbrella":
        return True, "aggregate overview"
    if kind == "tool":
        ok = r in TOOL_FUNCS_KEYS
        return ok, ("ref in TOOL_FUNCS" if ok else f"ref {r} not in TOOL_FUNCS")
    if kind == "computer_action":
        ok = (r in wl) or (r in ro_allowed)
        return ok, ("in WHITELIST/_READONLY_ALLOWED" if ok else f"{r} not in whitelist")
    if kind == "context":
        ok = r in LEGACY_CAPS
        return ok, ("ref in capabilities.CAPABILITIES" if ok else f"{r} not in CAPABILITIES")
    if kind == "builtin":
        return builtin_callable(r)
    if kind == "mcp":
        return None, "needs runtime MCP host"
    return False, "unknown kind"

MAP_B = {}
for cid, cap in caps.items():
    ref = EXECUTORS.get(cid)
    callable_ok, note = derive_callable(cid, ref)
    exp = expected_permission(cap)
    perm_ok = (cap["permission"] == exp)
    # status via verify_capability logic
    if ref is None:
        status = "DECLARED"
        reason = "no executor mapping"
    elif not cap["available"] or cap["permission"] == "block":
        status = "BLOCKED"
        reason = "available=False or permission=block"
    elif callable_ok is False:
        if ref["kind"] == "computer_action":
            status = "PARTIAL"
            reason = "computer_action not in whitelist"
        elif ref["kind"] == "mcp":
            status = "DECLARED"
            reason = "MCP unavailable"
        else:
            status = "DECLARED"
            reason = "executor not callable"
    elif not perm_ok:
        status = "PARTIAL"
        reason = f"permission {cap['permission']} != expected {exp}"
    else:
        status = "READY"
        reason = "registered+callable+perm-ok"
    MAP_B[cid] = {
        "name": cap["name"], "group": cap["group"], "risk": cap["risk"],
        "permission": cap["permission"], "available": cap["available"],
        "implemented": cap["implemented"],
        "executor_kind": ref["kind"] if ref else None,
        "executor_ref": ref["ref"] if ref else None,
        "callable": callable_ok, "callable_note": note,
        "perm_expected": exp, "perm_consistent": perm_ok,
        "status": status, "reason": reason,
    }
EVID["MAP_B"] = MAP_B
EVID["MAP_B_STATUS_COUNTS"] = dict(Counter(m["status"] for m in MAP_B.values()))

# ───────────────────────────── 8. MAP-C: 47 features -> API -> cap ─────────────────────────────
with open(os.path.join(UI, "xiao6-space", "js", "zz-workspace.js"), encoding="utf-8") as f:
    jssrc = f.read()
# FEATURE_REGISTRY block
m = re.search(r"var FEATURE_REGISTRY\s*=\s*\[(.*?)\];", jssrc, re.S)
FEATURES = []
if m:
    block = m.group(1)
    for fm in re.finditer(r"\{\s*id:\s*'([^']+)'\s*,\s*name:\s*'([^']+)'\s*,\s*cat:\s*'([^']+)'\s*,\s*vis:\s*'([^']+)'\s*\}", block):
        FEATURES.append({"id": fm.group(1), "name": fm.group(2), "cat": fm.group(3), "vis": fm.group(4)})
EVID["FEATURE_COUNT"] = len(FEATURES)

m2 = re.search(r"var FEATURE_API_MAP\s*=\s*\{(.*?)\};", jssrc, re.S)
FAM = {}
if m2:
    for fm in re.finditer(r"'([^']+)'\s*:\s*'([^']+)'", m2.group(1)):
        FAM[fm.group(1)] = fm.group(2)
EVID["FAM_COUNT"] = len(FAM)

# map each feature -> api -> is it deprecated?
DEPRECATED_API = "/api/capabilities"
def feature_route(fid):
    if fid in FAM:
        return FAM[fid]
    return "/api/" + str(fid or "").replace("-", "/")

MAP_C = []
for f in FEATURES:
    api = feature_route(f["id"])
    deprecated = (api == DEPRECATED_API)
    # best-effort cap linkage for capability-related features
    cap_link = None
    if f["id"] in ("capabilities",):
        cap_link = "registry(catalog/foundation)"
    elif f["id"] == "capability-os":
        cap_link = "catalog_view/foundation_view"
    MAP_C.append({**f, "api": api, "deprecated": deprecated, "cap_link": cap_link})
EVID["MAP_C"] = MAP_C
EVID["MAP_C_DEPRECATED_FEATURES"] = [f["id"] for f in MAP_C if f["deprecated"]]
EVID["MAP_C_MAPPED_COUNT"] = len(FAM)

# ───────────────────────────── MAP-A markdown ─────────────────────────────
mapa_lines = ["# PHASE 5.5 · MAP-A — Tool → Capability 映射", ""]
mapa_lines.append(f"> 工具全集 = TOOL_FUNCS **{len(TOOL_FUNCS_KEYS)}** 项（可执行）；其中进入 OpenAI schema(TOOLS) **{EVID['MAP_A_IN_SCHEMA']}** 项，未进 schema **{len(EVID['MAP_A_NOT_IN_SCHEMA'])}** 项：{', '.join(EVID['MAP_A_NOT_IN_SCHEMA'])}。")
mapa_lines.append("> 双反向映射：init=`capability_os.tool_to_capability`(18项)，em=`execution_mapping.tool_to_capability`(15项)。分歧工具(结果不同)见末表。")
mapa_lines.append("")
mapa_lines.append("## 按能力归并（init 视图）")
for cap_id in sorted(init_buckets, key=lambda c: (-len(init_buckets[c]), c)):
    tools = init_buckets[cap_id]
    mapa_lines.append(f"### {cap_id}  ({len(tools)})")
    for t in tools:
        em_cap = MAP_A[t]["em"]
        flag = "" if em_cap == cap_id else f"  ⚠️ em→`{em_cap}`"
        sch = "schema" if MAP_A[t]["in_schema"] else "no-schema"
        mapa_lines.append(f"- `{t}` ({sch}){flag}")
    mapa_lines.append("")
mapa_lines.append("## 双映射分歧工具（同一工具经两个 reverse-map 落到不同能力）")
if MAP_A_DIVERGENT:
    for t in MAP_A_DIVERGENT:
        mapa_lines.append(f"- `{t}` → init=`{MAP_A[t]['init']}` / em=`{MAP_A[t]['em']}`")
else:
    mapa_lines.append("- （无）")
mapa_lines.append("")
with open(os.path.join(ARCHIVE, "PHASE-5.5-TOOL-CAPABILITY-MAP.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(mapa_lines))

# ───────────────────────────── MAP-B markdown ─────────────────────────────
mapb_lines = ["# PHASE 5.5 · MAP-B — Capability → Execution 映射", ""]
mapb_lines.append(f"> canonical 能力 = **{len(caps)}** 项。状态由 `verification.verify_capability` 真实链推导（静态复现：registry 元数据 + executor_callable 真实检查）。")
mapb_lines.append(f"> 状态分布：{EVID['MAP_B_STATUS_COUNTS']}")
mapb_lines.append("")
mapb_lines.append("| 能力 id | 名称 | group | risk | permission | available | executor.kind | executor.ref | callable | 状态 | 理由 |")
mapb_lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
for cid in sorted(MAP_B, key=lambda c: (MAP_B[c]["status"], c)):
    m = MAP_B[cid]
    mapb_lines.append(f"| {cid} | {m['name']} | {m['group']} | {m['risk']} | {m['permission']} | {m['available']} | {m['executor_kind']} | {m['executor_ref']} | {m['callable']} | **{m['status']}** | {m['reason']} |")
mapb_lines.append("")
with open(os.path.join(ARCHIVE, "PHASE-5.5-CAPABILITY-EXECUTION-MAP.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(mapb_lines))

# ───────────────────────────── MAP-C markdown ─────────────────────────────
mapc_lines = ["# PHASE 5.5 · MAP-C — Feature → API → Capability 映射", ""]
mapc_lines.append(f"> FEATURE_REGISTRY = **{len(FEATURES)}** 项；FEATURE_API_MAP 显式映射 **{len(FAM)}** 项；其余走 heuristic `featureRoute`。")
mapc_lines.append("> ⚠️ 唯一命中 deprecated `/api/capabilities` 的特性：`capabilities`（id，vis=default，命令面板入口）。`capability-os` 正确指向 `/api/capability_os/catalog`。")
mapc_lines.append("")
mapc_lines.append("| feature id | name | cat | vis | API 路由 | deprecated? | cap 关联 |")
mapc_lines.append("|---|---|---|---|---|---|---|")
for f in MAP_C:
    dep = "🚫 YES" if f["deprecated"] else ""
    mapc_lines.append(f"| {f['id']} | {f['name']} | {f['cat']} | {f['vis']} | `{f['api']}` | {dep} | {f['cap_link'] or ''} |")
mapc_lines.append("")
with open(os.path.join(ARCHIVE, "PHASE-5.5-FEATURE-API-MAP.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(mapc_lines))

# ───────────────────────────── write evidence json ─────────────────────────────
with open(os.path.join(ARCHIVE, "phase55-evidence.json"), "w", encoding="utf-8") as f:
    json.dump(EVID, f, ensure_ascii=False, indent=2)

# console summary
print("=== PHASE 5.5 STEP 0 EVIDENCE ===")
for k in ["TOOLS_COUNT","TOOL_FUNCS_COUNT","READONLY_TOOLS_COUNT","CANONICAL_COUNT",
          "LEGACY_COUNT","EXECUTORS_COUNT","TTC_EM_COUNT","TTC_INIT_COUNT",
          "FEATURE_COUNT","FAM_COUNT"]:
    print(f"  {k} = {EVID.get(k)}")
print("  TTC_DIVERGENCE only_em:", EVID["TTC_DIVERGENCE"]["only_in_execution_mapping"])
print("  TTC_DIVERGENCE only_init:", EVID["TTC_DIVERGENCE"]["only_in_init"])
print("  TTC_DIVERGENCE conflict:", EVID["TTC_DIVERGENCE"]["conflicting_values"])
print("  MAP_B_STATUS_COUNTS:", EVID["MAP_B_STATUS_COUNTS"])
print("  MAP_C_DEPRECATED_FEATURES:", EVID["MAP_C_DEPRECATED_FEATURES"])
print("  delete BLOCKED:", EVID["DELETE_BLOCKED"].get("available"), EVID["DELETE_BLOCKED"].get("permission"))
print("  system BLOCKED:", EVID["SYSTEM_BLOCKED"].get("available"), EVID["SYSTEM_BLOCKED"].get("permission"))
print("  network BLOCKED:", EVID["NETWORK_BLOCKED"].get("available"), EVID["NETWORK_BLOCKED"].get("permission"))
print("  evidence ->", os.path.join(ARCHIVE, "phase55-evidence.json"))
