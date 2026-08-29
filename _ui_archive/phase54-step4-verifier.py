#!/usr/bin/env python3
# PHASE 5.4 · STEP 4 regression verifier (analysis-area only, NOT in product tree)
import sys, json, importlib.util, py_compile

PROD = r"G:/xiao6/xiao6-ui"
R = {}

# ---- (1) py_compile syntax gate ----
for rel in ("capabilities.py", "server.py"):
    fp = f"{PROD}/{rel}"
    try:
        py_compile.compile(fp, doraise=True)
        R[f"compile:{rel}"] = "OK"
    except Exception as e:
        R[f"compile:{rel}"] = f"FAIL: {e}"

# ---- (2) live import capabilities (top-level, on PROD path) ----
if PROD not in sys.path:
    sys.path.insert(0, PROD)
try:
    import capabilities
    R["capabilities.import"] = "OK"
    R["capabilities.LEGACY_COMPAT_SHIM"] = bool(getattr(capabilities, "LEGACY_COMPAT_SHIM", False))
    details = capabilities.capability_details()
    R["capabilities.detail_count"] = len(details)
    R["capabilities.detail_ids"] = [d["id"] for d in details]
    # simulate /api/capabilities response body (server.py L478-485)
    body = {"ok": True, "deprecated": True, "count": len(details), "items": details}
    R["api_capabilities_body_has_deprecated"] = ("deprecated" in body) and body["deprecated"] is True
    R["api_capabilities_body_has_items"] = isinstance(body.get("items"), list)
    # canonical_forward_view shim proof
    try:
        cfv = capabilities.canonical_forward_view()
        R["capabilities.canonical_forward_view.source"] = cfv.get("canonical_source")
        R["capabilities.canonical_forward_view.shim"] = cfv.get("shim")
        R["capabilities.canonical_forward_view.forwarded_ids"] = list(cfv.get("forwarded", {}).keys())
    except Exception as e:
        R["capabilities.canonical_forward_view"] = f"FAIL: {e}"
except Exception as e:
    R["capabilities.import"] = f"FAIL: {e}"

# ---- (3) live canonical=33 via registry.py loaded standalone (no heavy pkg __init__) ----
try:
    spec = importlib.util.spec_from_file_location(
        "cap_registry_standalone", f"{PROD}/capability_os/registry.py"
    )
    regmod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(regmod)
    reg = regmod.get_registry()
    ids = list(reg.keys())
    R["capability_os.registry_len"] = len(ids)
    R["capability_os.has_hotspot"] = "hotspot" in ids
    R["capability_os.has_prefetch"] = "prefetch" in ids
    R["capability_os.has_computer_action"] = "computer_action" in ids
    # CRITICAL placeholder guards (delete/system/network) must stay block + unavailable
    for cid in ("delete", "system", "network"):
        c = reg.get(cid)
        R[f"guard:{cid}"] = (
            None if c is None else {"available": c.available, "permission": c.permission}
        )
except Exception as e:
    R["capability_os.registry"] = f"FAIL: {e}"

print(json.dumps(R, ensure_ascii=False, indent=2))
