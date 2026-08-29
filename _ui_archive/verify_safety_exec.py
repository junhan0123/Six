import sys
ROOT = r"G:/xiao6/xiao6-ui"
sys.path.insert(0, ROOT)
sys.path.insert(0, ROOT + "/computer_action")

out = []
def log(*a):
    s = " ".join(str(x) for x in a)
    out.append(s)
    print(s)

log("=== A. SAFETY GATE: WHITELIST + MEDIUM->CONFIRM ===")
import computer_action.safety as safety
from capability_os.registry import risk_of, is_implemented
for c in ["focus_window", "browser_navigate", "delete", "kill_process", "system",
          "network", "modify_file", "execute_command", "open_application", "copy_text", "search"]:
    try:
        a = safety.is_allowed(c); cf = safety.needs_confirm(c); r = risk_of(c); imp = is_implemented(c)
    except Exception as e:
        a = cf = r = imp = "ERR:" + str(e)
    log(f"  {c:18} allowed={a!s:5} confirm={cf!s:5} risk={r!s:9} impl={imp}")

log("=== B. ASSERT_ALLOWED RED LINE (HIGH/CRITICAL/non-whitelist must reject) ===")
for c in ["delete", "kill_process", "system", "network", "modify_file", "execute_command", "browser_navigate"]:
    try:
        safety.assert_allowed(c); log(f"  {c:18} assert_allowed=PASS(no-raise)  [expected for whitelisted MEDIUM]")
    except safety.SafetyViolation as e:
        log(f"  {c:18} assert_allowed=REJECTED({type(e).__name__})  [red line intact]")

log("=== C. SCHEME DEFENSE: _op_browser_navigate ===")
import computer_executor as ce
import webbrowser
calls = []
webbrowser.open = lambda u: (calls.append(u) or True)
ex = ce.RealComputerExecutor()

class A:
    def __init__(self, cap, params=None):
        self.capability = cap; self.parameters = params; self.target = None

for url, exp in [("javascript:alert(1)", False), ("file:///C:/x", False),
                 ("https://example.com", True), ("http://example.com", True), ("", False)]:
    calls.clear()
    r = ex._op_browser_navigate(A("browser_navigate", {"url": url}), None)
    ok = r["ok"]; status = "OK" if ok == exp else "MISMATCH!!!"
    log(f"  url={url!r:28} ok={ok!s:5} exp={exp!s:5} wb_called={calls} -> {status}")

log("=== D. verify py_compile of changed modules ===")
import py_compile
for f in [ROOT + "/computer_action/safety.py", ROOT + "/computer_executor.py", ROOT + "/self_check.py"]:
    try:
        py_compile.compile(f, doraise=True); log(f"  compile OK: {f}")
    except Exception as e:
        log(f"  compile FAIL: {f} -> {e}")

print("\n---SUMMARY---")
print("\n".join(out))
