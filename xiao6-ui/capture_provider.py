#!/usr/bin/env python3
"""Minimal capture provider for screen capture.

Uses PIL + win32gui for Windows screen capture.
No second perception runtime - only provides screenshot capability.
"""
from __future__ import annotations

import sys
from typing import Any, Dict, List, Optional


def get_displays() -> Dict[str, Any]:
    """Get monitor information using win32gui."""
    try:
        import win32gui
        import win32api
        
        displays = []
        
        def enum_monitors(hwnd, extra):
            rect = win32gui.GetWindowRect(hwnd)
            displays.append({
                "hwnd": hwnd,
                "left": rect[0],
                "top": rect[1],
                "right": rect[2],
                "bottom": rect[3],
                "width": rect[2] - rect[0],
                "height": rect[3] - rect[1],
            })
            return True
        
        win32gui.EnumDisplayMonitors(None, None, enum_monitors, None)
        
        if displays:
            return {
                "ok": True,
                "displays": displays,
                "count": len(displays),
            }
        else:
            return {
                "ok": False,
                "error": "No displays found",
                "displays": [],
            }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "displays": [],
        }


def capture_screen(target: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Capture screen using PIL + win32gui.
    
    Args:
        target: Optional dict with 'display_index' to capture specific monitor
    
    Returns:
        Dict with 'ok', 'screenshot' (bytes), 'width', 'height', 'format'
    """
    try:
        from PIL import ImageGrab
        
        # Use PIL's built-in screenshot
        img = ImageGrab.grab()
        
        # Convert to bytes
        import io
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        screenshot_bytes = buffer.getvalue()
        
        return {
            "ok": True,
            "screenshot": screenshot_bytes,
            "width": img.width,
            "height": img.height,
            "format": "png",
            "size_bytes": len(screenshot_bytes),
        }
    except Exception as e:
        import traceback
        return {
            "ok": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "screenshot": None,
        }


def capture_region(
    x: int, y: int, width: int, height: int
) -> Dict[str, Any]:
    """Capture a specific region of the screen."""
    try:
        from PIL import ImageGrab
        
        img = ImageGrab.grab(bbox=(x, y, x + width, y + height))
        
        import io
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        
        return {
            "ok": True,
            "screenshot": buffer.getvalue(),
            "width": width,
            "height": height,
            "format": "png",
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


if __name__ == "__main__":
    # Test
    print("Testing capture_provider...")
    
    # Test displays
    displays = get_displays()
    print(f"Displays OK: {displays.get('ok')}")
    if displays.get('ok'):
        print(f"  Count: {displays.get('count')}")
        for d in displays.get('displays', []):
            print(f"  Display: {d['width']}x{d['height']} at ({d['left']},{d['top']})")
    
    # Test capture
    result = capture_screen()
    print(f"Capture OK: {result.get('ok')}")
    if result.get("ok"):
        print(f"Size: {result.get('size_bytes')} bytes")
        print(f"Dimensions: {result.get('width')}x{result.get('height')}")
    else:
        print(f"Error: {result.get('error')}")
