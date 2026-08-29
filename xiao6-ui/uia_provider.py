"""Phase 8 MVP · UI Automation Provider（UIA 优先，仅观察）

抽象 Provider + Mock（零真实桌面 / UIA / accessibility 依赖）。
产出结构化 UI 树（Element / Role / Tree / Accessibility / Focus / Window Mapping）。
禁止：任何控制 / 点击 / 输入 / 执行器调用。只观察。
"""
from __future__ import annotations


class UiElement:
    """单个控件实例（UIA 元素）。"""

    __slots__ = ("element_id", "name", "automation_id", "role",
                 "value", "state", "bbox", "parent_id", "window_id", "children")

    def __init__(self, element_id, role, name="", automation_id="",
                 value="", state="normal", bbox=None, parent_id=None,
                 window_id=None, children=None):
        self.element_id = element_id
        self.role = role
        self.name = name
        self.automation_id = automation_id
        self.value = value
        self.state = state                  # enabled/disabled/checked/readonly/normal
        self.bbox = tuple(bbox) if bbox else None   # (x, y, w, h)
        self.parent_id = parent_id
        self.window_id = window_id
        self.children = children if children is not None else []

    def to_dict(self):
        return {
            "elementId": self.element_id,
            "name": self.name,
            "automationId": self.automation_id,
            "role": self.role,
            "value": self.value,
            "state": self.state,
            "bbox": list(self.bbox) if self.bbox else None,
            "parentId": self.parent_id,
            "windowId": self.window_id,
            "children": [c.to_dict() for c in self.children],
        }


class UITree:
    """从桌面根到叶的层级结构 + 焦点元素引用。"""

    __slots__ = ("root", "focused_element_id", "window_ids")

    def __init__(self, root, focused_element_id=None, window_ids=None):
        self.root = root                    # UiElement（桌面根）
        self.focused_element_id = focused_element_id
        self.window_ids = window_ids if window_ids is not None else []

    def to_dict(self):
        return {
            "root": self.root.to_dict() if self.root else None,
            "focusedElementId": self.focused_element_id,
            "windowIds": self.window_ids,
        }

    def find(self, element_id):
        """深度优先查找元素（按 element_id）。"""
        def walk(e):
            if e is None:
                return None
            if e.element_id == element_id:
                return e
            for c in e.children:
                r = walk(c)
                if r:
                    return r
            return None
        return walk(self.root)


class UiProvider:
    """抽象基类：UI 理解接口（仅观察）。"""
    name = "abstract"

    def list_windows(self):
        raise NotImplementedError

    def tree(self, root_window_id=None):
        raise NotImplementedError

    def focused_element(self):
        raise NotImplementedError


class MockUiProvider(UiProvider):
    """测试用 UIA：确定性合成 UI 树，零真实桌面 / UIA 依赖。"""
    name = "mock"

    def __init__(self, focused_window_id="WINDOW-NOTEPAD"):
        self._focused_window_id = focused_window_id

    def list_windows(self):
        return [
            {"windowId": "WINDOW-NOTEPAD", "title": "无标题 - 记事本", "role": "window"},
            {"windowId": "WINDOW-EXPLORER", "title": "文件资源管理器", "role": "window"},
        ]

    def tree(self, root_window_id=None):
        desktop = UiElement("DESKTOP", "desktop")
        notepad = UiElement("WINDOW-NOTEPAD", "window", name="无标题 - 记事本",
                            window_id="WINDOW-NOTEPAD", parent_id="DESKTOP",
                            bbox=(0, 0, 1920, 1080))
        menu = UiElement("ELEM-NOTEPAD-MENU", "menu", name="菜单栏",
                         parent_id="WINDOW-NOTEPAD", window_id="WINDOW-NOTEPAD",
                         bbox=(0, 0, 1920, 30))
        edit = UiElement("ELEM-NOTEPAD-EDIT", "edit", name="文本编辑区",
                         automation_id="15", value="小6正在记录", state="enabled",
                         parent_id="WINDOW-NOTEPAD", window_id="WINDOW-NOTEPAD",
                         bbox=(10, 40, 1900, 1000))
        notepad.children = [menu, edit]
        explorer = UiElement("WINDOW-EXPLORER", "window", name="文件资源管理器",
                             window_id="WINDOW-EXPLORER", parent_id="DESKTOP",
                             bbox=(200, 200, 800, 600))
        desktop.children = [notepad, explorer]
        return UITree(desktop, focused_element_id=self._focused_window_id,
                      window_ids=["WINDOW-NOTEPAD", "WINDOW-EXPLORER"])

    def focused_element(self):
        t = self.tree()
        return t.find(self._focused_window_id)
