"""只读诊断：复现 electron/fullscreen-presence.js 的全屏判定逻辑。
不修改任何产品代码/配置，仅读取当前前台窗口与显示器矩形并输出判定结果。
"""
import ctypes
import ctypes.wintypes as wt

u = ctypes.windll.user32


class RECT(ctypes.Structure):
    _fields_ = [("L", ctypes.c_long), ("T", ctypes.c_long),
                ("R", ctypes.c_long), ("B", ctypes.c_long)]


class MONITORINFO(ctypes.Structure):
    _fields_ = [("cb", ctypes.c_ulong), ("rcMonitor", RECT),
                ("rcWork", RECT), ("dwFlags", ctypes.c_ulong)]


def probe(label):
    h = u.GetForegroundWindow()
    if not h:
        print(label, "-> no foreground window")
        return
    pid = wt.DWORD()
    u.GetWindowThreadProcessId(h, ctypes.byref(pid))
    title = ctypes.create_unicode_buffer(300)
    u.GetWindowTextW(h, title, 300)
    r = RECT()
    u.GetWindowRect(h, ctypes.byref(r))
    m = u.MonitorFromWindow(h, 2)
    mi = MONITORINFO()
    mi.cb = ctypes.sizeof(mi)
    u.GetMonitorInfoW(m, ctypes.byref(mi))
    mw = mi.rcMonitor.R - mi.rcMonitor.L
    mh = mi.rcMonitor.B - mi.rcMonitor.T
    ww = r.R - r.L
    wh = r.B - r.T
    workw = mi.rcWork.R - mi.rcWork.L
    workh = mi.rcWork.B - mi.rcWork.T
    verdict = "FULLSCREEN" if (ww >= mw - 8 and wh >= mh - 8) else "WINDOWED"
    print(label)
    print("  foreground pid=%d title=%r" % (pid.value, title.value))
    print("  window  rect = %dx%d at (%d,%d)" % (ww, wh, r.L, r.T))
    print("  monitor rect = %dx%d   workArea = %dx%d" % (mw, mh, workw, workh))
    print("  VERDICT = %s   (threshold: w>=%d and h>=%d)" % (verdict, mw - 8, mh - 8))
    print("  taskbar reserved? monitorH-workH = %d" % (mh - workh))


print("=== probe as DPI-unaware process (same as default powershell.exe) ===")
probe("probe#1")
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
    print()
    print("=== probe after enabling PER-MONITOR DPI awareness ===")
    probe("probe#2")
except Exception as exc:
    print("dpi awareness switch failed: %r" % (exc,))
