#!/usr/bin/env python3
import sys, os, types, importlib.util
UI = "G:/xiao6/xiao6-ui"
reg_path = os.path.join(UI, "capability_os", "registry.py")
pkg = types.ModuleType("capability_os")
pkg.__path__ = [os.path.join(UI, "capability_os")]
sys.modules["capability_os"] = pkg
spec2 = importlib.util.spec_from_file_location("capability_os.registry", reg_path)
rm = importlib.util.module_from_spec(spec2)
sys.modules["capability_os.registry"] = rm
spec2.loader.exec_module(rm)
REG = rm.get_registry()
print("REG len:", len(REG))
print("hotspot in REG:", "hotspot" in REG, "| prefetch in REG:", "prefetch" in REG, "| computer_action in REG:", "computer_action" in REG)
# now import the REAL capabilities module exactly as _build does
import capabilities as caps
print("real capabilities.CAPABILITIES len:", len(caps.CAPABILITIES), "keys:", list(caps.CAPABILITIES.keys()))
# re-run merge logic manually to see
added = []
for cid, meta in caps.CAPABILITIES.items():
    if cid not in REG:
        added.append(cid)
print("would-be-added by merge now:", added)
