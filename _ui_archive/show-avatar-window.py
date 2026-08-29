"""运维工具（只操作运行时窗口状态，不修改任何产品代码/配置）。

用途：小6桌宠窗口（标题 '小6 · 语音球'）在本机被 fullscreen-presence 探测链路
误判隐藏后，用 Win32 ShowWindow 直接把它显示出来并置顶，便于实机视觉验收。

用法：
    python show-avatar-window.py          # 显示并置顶
    python show-avatar-window.py --status # 仅查询状态，不做任何改动
"""
import ctypes
import ctypes.wintypes as wt
import sys

u = ctypes.windll.user32

SW_SHOW = 5
SW_SHOWNOACTIVATE = 4
HWND_TOPMOST = -1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040

TARGET_TITLE = "小6 · 语音球"

EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)


def find_targets():
    found = []

    def cb(h, _l):
        buf = ctypes.create_unicode_buffer(300)
        u.GetWindowTextW(h, buf, 300)
        if buf.value == TARGET_TITLE:
            found.append(h)
        return True

    u.EnumWindows(EnumWindowsProc(cb), 0)
    return found


def describe(h):
    class RECT(ctypes.Structure):
        _fields_ = [("L", ctypes.c_long), ("T", ctypes.c_long),
                    ("R", ctypes.c_long), ("B", ctypes.c_long)]

    r = RECT()
    u.GetWindowRect(h, ctypes.byref(r))
    vis = bool(u.IsWindowVisible(h))
    pid = wt.DWORD()
    u.GetWindowThreadProcessId(h, ctypes.byref(pid))
    return "hwnd=0x%X pid=%d visible=%s size=%dx%d pos=(%d,%d)" % (
        h, pid.value, vis, r.R - r.L, r.B - r.T, r.L, r.T)


def main():
    status_only = "--status" in sys.argv
    targets = find_targets()
    if not targets:
        print("NOT FOUND: 未找到标题为 %r 的窗口（桌宠可能未启动）" % TARGET_TITLE)
        return 1
    for h in targets:
        print("BEFORE: " + describe(h))
        if status_only:
            continue
        u.ShowWindow(h, SW_SHOWNOACTIVATE)
        u.SetWindowPos(h, HWND_TOPMOST, 0, 0, 0, 0,
                       SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW)
        print("AFTER : " + describe(h))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
