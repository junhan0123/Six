import ctypes, sys

user32 = ctypes.windll.user32
GWL_STYLE = -16
WS_VISIBLE = 0x10000000

hwnd = int(sys.argv[1]) if len(sys.argv) > 1 else 330050
style = user32.GetWindowLongW(hwnd, GWL_STYLE)
visible_style = bool(style & WS_VISIBLE)
print(f"HWND={hwnd} STYLE=0x{style & 0xFFFFFFFF:08X} WS_VISIBLE_BIT={visible_style}")
print("CONCLUSION: " + ("show()_was_called_window_has_visible_style" if visible_style else "show()_NOT_called_window_hidden"))
