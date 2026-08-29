import urllib.request, json, sys

BASE = "http://127.0.0.1:8010"

def get(u):
    return json.load(urllib.request.urlopen(u, timeout=8))

print("=== /api/capability_foundation ===")
d = get(BASE + "/api/capability_foundation")
print("total", d['total'], "avail", d['available'], "health", d['health_summary'])
watch = ('focus_window', 'browser_navigate', 'user_model', 'delete',
         'kill_process', 'modify_file', 'system', 'network', 'execute_command')
for c in d['capabilities']:
    if c['id'] in watch:
        h = c.get('health', {})
        print("  %-18s -> %-8s | perm=%-8s | risk=%-8s | %s" % (
            c['id'], h.get('status'), c.get('permission'), c.get('risk'),
            str(h.get('reason', ''))[:55]))

print("=== /api/health ===")
h = get(BASE + "/api/health")
print("health.ok =", h.get('ok'))
sc = h.get('self_check', {})
print("self_check.ok =", sc.get('ok'), "| core_ok =", sc.get('core_ok'),
      "| external.ok =", sc.get('external', {}).get('ok'))

print("=== user_model / episodes ===")
print("user_model.ok =", get(BASE + "/api/user_model").get('ok'))
print("episodes.ok   =", get(BASE + "/api/episodes").get('ok'))

print("=== browser scheme guard unit test (webbrowser mocked) ===")
try:
    import sys as _sys
    _sys.path.insert(0, r"G:\xiao6\xiao6-ui")
    import computer_executor as ce
    import webbrowser
    calls = []
    webbrowser.open = lambda u: (calls.append(u) or True)

    class Fake(ce.RealComputerExecutor):
        def _mk(self, ok, **kw):
            return {'ok': ok, 'error': kw.get('error'), 'data': kw.get('data')}

    ex = Fake()
    A = lambda u: type('Act', (), {'parameters': {'url': u}, 'target': None})()
    r_js = ex._op_browser_navigate(A('javascript:alert(1)'), None)
    r_file = ex._op_browser_navigate(A('file:///C:/x'), None)
    r_http = ex._op_browser_navigate(A('https://example.com'), None)
    r_empty = ex._op_browser_navigate(A(''), None)
    print("  javascript: =>", r_js['ok'], "|", r_js.get('error'))
    print("  file://     =>", r_file['ok'], "|", r_file.get('error'))
    print("  https://    =>", r_http['ok'], "| webbrowser.open called with:", calls)
    print("  empty       =>", r_empty['ok'], "|", r_empty.get('error'))
except Exception as e:
    print("  unit test could not run:", repr(e))
