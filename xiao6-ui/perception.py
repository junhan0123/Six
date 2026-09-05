#!/usr/bin/env python3
"""Minimal perception module for window information.

Uses win32gui for window observation.
No second perception runtime - only provides window info capability.
"""
from __future__ import annotations

import sys
from typing import Any, Dict, List, Optional


def get_foreground_window() -> Dict[str, Any]:
    """Get information about the foreground window."""
    try:
        import win32gui
        
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return {"ok": False, "error": "No foreground window"}
        
        title = win32gui.GetWindowText(hwnd)
        class_name = win32gui.GetClassName(hwnd)
        
        # Get window rect
        rect = win32gui.GetWindowRect(hwnd)
        
        return {
            "ok": True,
            "hwnd": hwnd,
            "title": title,
            "class_name": class_name,
            "left": rect[0],
            "top": rect[1],
            "right": rect[2],
            "bottom": rect[3],
            "width": rect[2] - rect[0],
            "height": rect[3] - rect[1],
            "visible": win32gui.IsWindowVisible(hwnd),
            "enabled": win32gui.IsWindowEnabled(hwnd),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_all_windows() -> Dict[str, Any]:
    """Get information about all visible windows."""
    try:
        import win32gui
        
        windows = []
        
        def enum_windows(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:  # Only include windows with titles
                    rect = win32gui.GetWindowRect(hwnd)
                    windows.append({
                        "hwnd": hwnd,
                        "title": title,
                        "left": rect[0],
                        "top": rect[1],
                        "width": rect[2] - rect[0],
                        "height": rect[3] - rect[1],
                    })
            return True
        
        win32gui.EnumWindows(enum_windows, None)
        
        return {
            "ok": True,
            "windows": windows,
            "count": len(windows),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def observe(scope: str = "all") -> Dict[str, Any]:
    """Observe windows based on scope.
    
    Args:
        scope: "window" for foreground, "all" for all windows
    """
    if scope == "window":
        return get_foreground_window()
    elif scope == "all":
        return get_all_windows()
    else:
        return {"ok": False, "error": f"Unknown scope: {scope}"}


class ScreenObserver:
    """Screen observer providing screen metadata."""

    def screen_info(self) -> Dict[str, Any]:
        """Get current screen resolution and info."""
        try:
            import win32api
            import win32con

            width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
            height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)

            return {
                "ok": True,
                "width": width,
                "height": height,
                "refresh_rate": self._get_refresh_rate(),
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _get_refresh_rate(self) -> int:
        """Get screen refresh rate in Hz."""
        try:
            import win32api
            import win32con
            mode = win32api.EnumDisplaySettings(None, win32con.ENUM_CURRENT_SETTINGS)
            return mode.VRefresh
        except Exception:
            return 60  # default


class WindowDetector:
    """Window detector providing window information."""

    def active_window(self) -> Dict[str, Any]:
        """Get the active/foreground window."""
        return get_foreground_window()

    def list_windows(self, limit: int = 40) -> Dict[str, Any]:
        """List all visible windows."""
        result = get_all_windows()
        if result.get('ok'):
            windows = result.get('windows', [])
            result['windows'] = windows[:limit]
            result['count'] = len(windows)
        return result


# Module-level singleton
window_detector = WindowDetector()


# Module-level singleton
screen_observer = ScreenObserver()


if __name__ == "__main__":
    # Test
    print("Testing perception module...")

    # Test foreground window
    fg = get_foreground_window()
    print(f"Foreground OK: {fg.get('ok')}")
    if fg.get('ok'):
        print(f"  Title: {fg.get('title')}")
        print(f"  Size: {fg.get('width')}x{fg.get('height')}")

    # Test all windows
    all_win = get_all_windows()
    print(f"All windows OK: {all_win.get('ok')}")
    if all_win.get('ok'):
        print(f"  Total: {all_win.get('count')}")
        for w in all_win.get('windows', [])[:5]:
            print(f"    - {w['title']}: {w['width']}x{w['height']}")

    # Test screen observer
    screen = screen_observer.screen_info()
    print(f"Screen OK: {screen.get('ok')}")
    if screen.get('ok'):
        print(f"  Resolution: {screen.get('width')}x{screen.get('height')}")
