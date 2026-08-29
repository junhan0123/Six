import sys, types, importlib.util, traceback
PROD = r"G:/xiao6/xiao6-ui"
sys.path.insert(0, PROD)

# Stub a minimal capability_os package so registry loads under its REAL name
# (capability_os.registry) without executing the heavy package __init__.py
# (which would pull matcher/router/composer — irrelevant to canonical count).
pkg = types.ModuleType("capability_os")
pkg.__path__ = [f"{PROD}/capability_os"]
pkg.__package__ = "capability_os"
sys.modules["capability_os"] = pkg

spec = importlib.util.spec_from_file_location(
    "capability_os.registry", f"{PROD}/capability_os/registry.py"
)
regmod = importlib.util.module_from_spec(spec)
sys.modules["capability_os.registry"] = regmod
spec.loader.exec_module(regmod)

try:
    reg = regmod.get_registry()
    print("REGISTRY_LEN", len(reg))
    ids = list(reg.keys())
    print("HAS_HOTSPOT", "hotspot" in ids)
    print("HAS_PREFETCH", "prefetch" in ids)
    print("HAS_COMPUTER_ACTION", "computer_action" in ids)
    for cid in ("delete", "system", "network"):
        c = reg.get(cid)
        print("GUARD_" + cid, None if c is None else (c.available, c.permission))
    # also confirm shim forward maps to real canonical entries
    import capabilities
    fwd = capabilities.canonical_forward_view()
    for cid, val in fwd.get("forwarded", {}).items():
        print("FWD_" + cid, "canonical_ok" if isinstance(val, dict) else "MISSING_IN_CANONICAL")
except Exception:
    traceback.print_exc()
