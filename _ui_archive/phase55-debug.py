#!/usr/bin/env python3
import ast, sys, os, types, importlib.util, json

UI = "G:/xiao6/xiao6-ui"

with open(os.path.join(UI, "tools.py"), encoding="utf-8") as f:
    ttree = ast.parse(f.read())

def find_assign(tree, name):
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name) and t.id == name:
                    return n.value
    return None

# TOOLS: count list elts, robustly extract function.name
tv = find_assign(ttree, "TOOLS")
print("TOOLS node type:", type(tv).__name__)
names = []
miss = 0
if isinstance(tv, ast.List):
    print("TOOLS elts:", len(tv.elts))
    for el in tv.elts:
        fn = el
        if isinstance(el, ast.Dict):
            for k, v in zip(el.keys, el.values):
                if isinstance(k, ast.Constant) and k.value == "function":
                    fn = v
        if isinstance(fn, ast.Dict):
            got = False
            for k, v in zip(fn.keys, fn.values):
                if isinstance(k, ast.Constant) and k.value == "name":
                    names.append(v.value); got = True
            if not got:
                miss += 1
        else:
            miss += 1
    print("TOOLS extracted names:", len(names), "missed:", miss)
    # check overlap with TOOL_FUNCS
tfv = find_assign(ttree, "TOOL_FUNCS")
tfk = [k.value for k in tfv.keys if isinstance(k, ast.Constant)] if isinstance(tfv, ast.Dict) else []
print("TOOL_FUNCS keys:", len(tfk))
print("TOOLS names not in TOOL_FUNCS:", sorted(set(names) - set(tfk)))
print("TOOL_FUNCS keys not in TOOLS:", sorted(set(tfk) - set(names)))

# READONLY_TOOLS (set)
rv = find_assign(ttree, "READONLY_TOOLS")
print("READONLY_TOOLS node type:", type(rv).__name__)
ro = []
if isinstance(rv, ast.Set):
    ro = [e.value for e in rv.elts if isinstance(e, ast.Constant)]
elif isinstance(rv, ast.Dict):
    ro = [k.value for k in rv.keys if isinstance(k, ast.Constant)]
print("READONLY_TOOLS count:", len(ro))

# capabilities runtime import
spec = importlib.util.spec_from_file_location("capabilities_rt", os.path.join(UI, "capabilities.py"))
cm = importlib.util.module_from_spec(spec)
sys.modules["capabilities_rt"] = cm
spec.loader.exec_module(cm)
print("capabilities CAPABILITIES runtime len:", len(cm.CAPABILITIES), "keys:", list(cm.CAPABILITIES.keys()))

# registry standalone
reg_path = os.path.join(UI, "capability_os", "registry.py")
pkg = types.ModuleType("capability_os")
pkg.__path__ = [os.path.join(UI, "capability_os")]
sys.modules["capability_os"] = pkg
spec2 = importlib.util.spec_from_file_location("capability_os.registry", reg_path)
rm = importlib.util.module_from_spec(spec2)
sys.modules["capability_os.registry"] = rm
spec2.loader.exec_module(rm)
REG = rm.get_registry()
print("registry get_registry len:", len(REG))
print("legacy present:", [c for c in ("hotspot","prefetch","computer_action") if c in REG])
print("registry keys sample (first 40):", sorted(REG.keys())[:40])
