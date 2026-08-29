import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
EnumWindows = user32.EnumWindows
EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
GetWindowTextLength = user32.GetWindowTextLengthW
GetWindowText = user32.GetWindowTextW
GetClassName = user32.GetClassNameW
IsWindowVisible = user32.IsWindowVisible
GetWindowRect = user32.GetWindowRect

results = []

def enum_cb(hwnd, lparam):
    length = GetWindowTextLength(hwnd)
    title = ""
    if length > 0:
        buf = ctypes.create_unicode_buffer(length + 1)
        GetWindowText(hwnd, buf, length + 1)
        title = buf.value
    cls = ctypes.create_unicode_buffer(256)
    GetClassName(hwnd, cls, 256)
    clsname = cls.value
    if 'Chrome' in clsname or '小6' in title or '语音' in title or 'Xiao6' in title:
        rect = wintypes.RECT()
        GetWindowRect(hwnd, ctypes.byref(rect))
        visible = bool(IsWindowVisible(hwnd))
        results.append((hwnd, clsname, title, visible,
                        (rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top)))
    return True

EnumWindows(EnumWindowsProc(enum_cb), 0)

if not results:
    print("RESULT: NO_RELEVANT_WINDOW")
else:
    for hwnd, clsname, title, visible, (x, y, w, h) in results:
        print(f"HWND={hwnd} CLS={clsname} VIS={visible} title='{title}' rect=({x},{y},{w}x{h})")
    orb = [r for r in results if '语音' in r[2] or '语音球' in r[2]]
    if orb:
        print("ORB_VISIBLE=" + str(orb[0][3]))
        print("RESULT: " + ("ORB_SHOWN_OK" if orb[0][3] else "ORB_HIDDEN"))
    else:
        print("RESULT: ORB_NOT_FOUND_AMONG_ELECTRON_WINDOWS")
