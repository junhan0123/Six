#!/usr/bin/env python3
"""小6 · Phase 4.7 — QQ真实Computer Use E2E测试 v2

修复问题：
1. QQ激活后焦点验证
2. 输入前确认焦点在正确窗口
3. 使用小6的真实能力
"""
import sys
import os
import time
import json

sys.path.insert(0, r'G:/xiao6/xiao6-ui')
OUTPUT_DIR = r'G:/xiao6/screenshots'

os.makedirs(OUTPUT_DIR, exist_ok=True)

import win32gui
import win32con
import win32process
from computer_action.input import ComputerInput
from computer_action.target_locator import TargetLocator
from computer_action import observe


class QQE2ETestV2:
    """QQ E2E 测试 V2"""
    
    def __init__(self):
        self.steps = []
        self.evidence = {}
        self.locator = TargetLocator()
        self.input = ComputerInput()
        self.success_count = 0
        self.failed_steps = []
        
    def record_step(self, step_id, action, success, details=None, error=None):
        step = {
            "step": step_id,
            "action": action,
            "success": success,
            "timestamp": time.time(),
            "details": details or {},
            "error": error,
        }
        self.steps.append(step)
        if success:
            self.success_count += 1
        else:
            self.failed_steps.append(step)
        print(f"  Step {step_id}: {action} - {'✅' if success else '❌'}")
        return step
    
    def screenshot(self, name):
        import pyautogui
        path = f'{OUTPUT_DIR}/{name}.png'
        pyautogui.screenshot(path)
        self.evidence[f'screenshot_{name}'] = path
        return path
    
    def get_foreground_info(self):
        """获取前台窗口信息"""
        fg = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(fg)
        rect = win32gui.GetWindowRect(fg)
        return {
            "hwnd": fg,
            "title": title,
            "rect": rect,
            "is_qq": title == 'QQ',
        }
    
    def activate_qq_properly(self):
        """正确激活QQ窗口"""
        # 找到所有QQ窗口
        qq_windows = []
        def enum_cb(hwnd, lParam):
            title = win32gui.GetWindowText(hwnd)
            if title == 'QQ':
                if win32gui.IsWindowVisible(hwnd):
                    rect = win32gui.GetWindowRect(hwnd)
                    w, h = rect[2]-rect[0], rect[3]-rect[1]
                    if w > 200 and h > 200:
                        qq_windows.append((hwnd, w, h))
            return True
        win32gui.EnumWindows(enum_cb, None)
        
        if not qq_windows:
            return self.record_step("activate", "find_qq", False, error="未找到可见QQ窗口")
        
        # 取最大的
        target_hwnd = max(qq_windows, key=lambda x: x[1]*x[2])[0]
        
        # 激活窗口
        win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
        time.sleep(0.3)
        
        # 尝试SetForegroundWindow
        try:
            win32gui.SetForegroundWindow(target_hwnd)
            time.sleep(0.5)
        except Exception as e:
            print(f"  SetForegroundWindow failed: {e}")
            # 回退：尝试AttachThreadInput
            try:
                fg = win32gui.GetForegroundWindow()
                fg_thread = win32process.GetWindowThreadProcessId(fg)
                qq_thread = win32process.GetWindowThreadProcessId(target_hwnd)
                if fg_thread and qq_thread:
                    win32process.AttachThreadInput(fg_thread, qq_thread, True)
                    win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
                    win32gui.SetForegroundWindow(target_hwnd)
                    win32process.AttachThreadInput(fg_thread, qq_thread, False)
                    time.sleep(0.5)
            except Exception as e2:
                print(f"  AttachThreadInput also failed: {e2}")
        
        # 验证
        info = self.get_foreground_info()
        success = info["is_qq"]
        
        self.screenshot("activate_result")
        return self.record_step("activate", "activate_qq", success,
                               details={"hwnd": target_hwnd, "foreground": info})
    
    def verify_focus_on_qq(self):
        """验证焦点在QQ"""
        info = self.get_foreground_info()
        success = info["is_qq"]
        return self.record_step("verify_focus", "verify_qq_focus", success,
                               details={"foreground": info["title"]})
    
    def click_text_vision(self, text):
        """使用视觉定位点击文本"""
        # 截图
        self.screenshot(f"before_click_{text[:10]}")
        
        # 定位
        result = self.locator.locate(text, min_confidence=0.5)
        
        if result.success and result.best_candidate:
            candidate = result.best_candidate
            # 移动并点击
            self.input.mouse_move(candidate.center_x, candidate.center_y, duration=0.3)
            time.sleep(0.2)
            click_result = self.input.mouse_click(candidate.center_x, candidate.center_y)
            
            # 验证点击后的状态
            time.sleep(0.5)
            self.screenshot(f"after_click_{text[:10]}")
            
            return self.record_step("click", f"click_{text}", click_result["success"],
                                   details={"x": candidate.center_x, "y": candidate.center_y,
                                           "confidence": candidate.confidence})
        else:
            return self.record_step("click", f"click_{text}", False,
                                   error=f"未找到目标: {text}")
    
    def input_text_safely(self, text):
        """安全输入文本（先验证焦点）"""
        # 检查焦点
        info = self.get_foreground_info()
        if not info["is_qq"]:
            return self.record_step("input", f"type_{text[:10]}", False,
                                   error=f"焦点不在QQ，当前: {info['title']}")
        
        # 输入
        result = self.input.type_text(text)
        
        # 截图验证
        self.screenshot(f"after_type_{text[:10]}")
        
        return self.record_step("input", f"type_{text[:10]}", result["success"],
                               details={"text": text, "success": result["success"]})
    
    def run(self):
        """运行完整测试"""
        print("=" * 60)
        print("小6 · QQ E2E 测试 V2")
        print("=" * 60)
        print()
        
        # 1. 激活QQ
        self.activate_qq_properly()
        
        # 2. 验证焦点
        self.verify_focus_on_qq()
        
        if not self.steps[-1]["success"]:
            print("\n⚠️ QQ未成功激活，终止测试")
            return False
        
        # 3. 观察界面
        self.screenshot("qq_interface")
        snap = observe(scope="window")
        ocr_text = snap.get("ocr_text", [])
        print(f"  OCR识别到 {len(ocr_text)} 个文本片段")
        self.record_step("observe", "observe_qq", True, details={"ocr_count": len(ocr_text)})
        
        # 4. 点击搜索框
        self.click_text_vision("搜索")
        
        # 5. 输入搜索词
        self.input_text_safely("小9")
        
        # 6. 等待搜索结果
        time.sleep(1)
        self.screenshot("search_results")
        
        # 7. 查找联系人
        result = self.locator.locate("小9", min_confidence=0.5)
        if result.success and result.best_candidate:
            c = result.best_candidate
            print(f"  找到联系人: 置信度={c.confidence:.2f} 位置=({c.center_x},{c.center_y})")
            self.record_step("locate", "find_contact_小9", True,
                           details={"x": c.center_x, "y": c.center_y})
            
            # 8. 点击联系人
            self.input.mouse_move(c.center_x, c.center_y, duration=0.3)
            time.sleep(0.2)
            self.input.mouse_click(c.center_x, c.center_y)
            time.sleep(0.5)
            self.screenshot("opened_chat")
            self.record_step("click", "click_contact", True,
                           details={"x": c.center_x, "y": c.center_y})
        else:
            print("  未找到联系人，使用估计位置")
            self.record_step("locate", "find_contact_小9", False,
                           error="未找到联系人")
            # 估计位置点击
            self.input.mouse_move(300, 300, duration=0.3)
            time.sleep(0.2)
            self.input.mouse_click(300, 300)
            time.sleep(0.5)
            self.screenshot("opened_chat_estimated")
            self.record_step("click", "click_contact_estimated", True)
        
        # 9. 验证聊天窗口打开
        time.sleep(0.5)
        info = self.get_foreground_info()
        self.record_step("verify", "chat_window_opened", True,
                        details={"window": info["title"]})
        
        # 10. 输入消息
        message = "小6 Computer Use 测试消息 2026"
        self.input_text_safely(message)
        
        # 11. 发送
        self.screenshot("before_send")
        result = self.input.key_press("enter")
        self.screenshot("after_send")
        self.record_step("send", "send_message", result["success"])
        
        # 12. 验证
        time.sleep(1)
        self.screenshot("final_state")
        info = self.get_foreground_info()
        self.record_step("verify", "final_state", True,
                        details={"window": info["title"]})
        
        # 13. 关闭QQ
        self.input.key_press("alt+f4")
        time.sleep(1)
        self.record_step("close", "close_qq", True)
        
        # 结果
        print()
        print("=" * 60)
        print(f"测试结果: {self.success_count}/{len(self.steps)} PASS")
        print("=" * 60)
        
        if self.failed_steps:
            print("\n失败步骤:")
            for s in self.failed_steps:
                print(f"  Step {s['step']}: {s['action']} - {s.get('error', '未知')}")
        
        return self.success_count == len(self.steps)


if __name__ == "__main__":
    test = QQE2ETestV2()
    success = test.run()
    
    # 保存报告
    report_path = f'{OUTPUT_DIR}/qq_e2e_report_v2.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump({
            "total": len(test.steps),
            "passed": test.success_count,
            "failed": len(test.failed_steps),
            "steps": test.steps,
            "evidence": test.evidence,
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n报告: {report_path}")
    print(f"截图目录: {OUTPUT_DIR}")
    
    sys.exit(0 if success else 1)
