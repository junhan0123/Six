import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
EnumWindows = user32.EnumWindows
EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
GetWindowTextLength = user32.GetWindowTextLengthW
GetWindowText = user32.GetWindowTextW
IsWindowVisible = user32.IsWindowVisible
GetWindowRect = user32.GetWindowRect

results = []

def enum_cb(hwnd, lparam):
    length = GetWindowTextLength(hwnd)
    if length > 0:
        buf = ctypes.create_unicode_buffer(length + 1)
        GetWindowText(hwnd, buf, length + 1)
        title = buf.value
        if '小6' in title or 'Xiao6' in title:
            rect = wintypes.RECT()
            GetWindowRect(hwnd, ctypes.byref(rect))
            visible = bool(IsWindowVisible(hwnd))
            results.append((hwnd, title, visible,
                            (rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top)))
    return True

EnumWindows(EnumWindowsProc(enum_cb), 0)

if not results:
    print("RESULT: NO_XIAO6_WINDOW")
else:
    for hwnd, title, visible, (x, y, w, h) in results:
        print(f"HWND={hwnd} VISIBLE={visible} title='{title}' rect=({x},{y},{w}x{h})")
    orb = [r for r in results if '语音球' in r[1]]
    if orb:
        v = orb[0][2]
        print("ORB_VISIBLE=" + str(v))
        print("RESULT: " + ("ORB_SHOWN" if v else "ORB_HIDDEN_FROZEN_RISK"))
    else:
        print("RESULT: ORB_WINDOW_NOT_FOUND")
