#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
macOS 原生桌面控制模块 — 使用 Quartz Events + Accessibility API
============================================================
提供鼠标/键盘/窗口控制能力，无需 pyautogui。

核心能力：
- 鼠标移动、点击、拖拽（支持左/右/中键）
- 键盘输入（支持修饰键：Cmd/Ctrl/Option/Shift）
- 窗口管理（列出/激活/移动/调整大小）
- 滚动事件
"""

import asyncio
import time
from typing import Optional, Tuple, List, Dict, Any

try:
    import Quartz
    from Quartz import (
        CGEventCreateMouseEvent,
        CGEventPost,
        kCGHIDEventTap,
        kCGMouseButtonLeft,
        CGEventCreateScrollWheelEvent,
        CGEventCreateKeyboardEvent,
        CGEventSetFlags,
        CGEventSetIntegerValueField,
        kCGMouseEventClickState,
        kCGEventLeftMouseDown,
        kCGEventLeftMouseUp,
        kCGEventRightMouseDown,
        kCGEventRightMouseUp,
        kCGEventMouseMoved,
        kCGEventLeftMouseDragged,
        kCGEventOtherMouseDragged,
        kCGEventOtherMouseDown,
        kCGEventOtherMouseUp,
        CGWindowListCopyWindowInfo,
        kCGWindowListOptionAll,
        kCGNullWindowID,
        kCGWindowBounds,
        kCGWindowOwnerName,
        kCGWindowName,
        kCGWindowLayer,
        kCGWindowNumber,
        kCGWindowOwnerPID,
        kCGWindowIsOnscreen,
    )
    HAS_QUARTZ = True
except ImportError as e:
    HAS_QUARTZ = False
    print(f"[WARN] Quartz not available, desktop control disabled: {e}")

# macOS 虚拟键码映射表
# 来源：Carbon/HIToolbox/Events.h
KEY_CODES = {
    # 字母
    "a": 0x00, "s": 0x01, "d": 0x02, "f": 0x03, "h": 0x04,
    "g": 0x05, "z": 0x06, "x": 0x07, "c": 0x08, "v": 0x09,
    "b": 0x0b, "q": 0x0c, "w": 0x0d, "e": 0x0e, "r": 0x0f,
    "y": 0x10, "t": 0x11, "1": 0x12, "2": 0x13, "3": 0x14,
    "4": 0x16, "6": 0x17, "5": 0x18, "=": 0x19, "9": 0x1a,
    "7": 0x1c, "-": 0x1d, "8": 0x1e, "0": 0x1f, "]": 0x21,
    "o": 0x22, "u": 0x23, "[": 0x25, "i": 0x26, "p": 0x28,
    "l": 0x2b, "j": 0x2d, "'": 0x2f, "k": 0x32, "\\": 0x34,
    ";": 0x33, ",": 0x37, "/": 0x38, "n": 0x39, "m": 0x3b,
    ".": 0x3c, "`": 0x3a,
    # 数字键（单独）
    "return": 0x24, "enter": 0x24,
    "tab": 0x30,
    "space": 0x31,
    "delete": 0x33, "backspace": 0x33,
    "escape": 0x35, "esc": 0x35,
    "cmd": 0x37, "command": 0x37,
    "shift": 0x38,
    "capslock": 0x39,
    "option": 0x3a, "alt": 0x3a,
    "ctrl": 0x3b, "control": 0x3b,
    "rightshift": 0x3c,
    "rightoption": 0x3d,
    "rightcontrol": 0x3e,
    "fn": 0x3f,
    "f17": 0x40,
    "volumeup": 0x48,
    "volumedown": 0x49,
    "mute": 0x4a,
    "f18": 0x4f,
    "f19": 0x50,
    "f5": 0x60, "f6": 0x61, "f7": 0x62, "f3": 0x63,
    "f8": 0x64, "f9": 0x65, "f11": 0x67, "f13": 0x69,
    "f16": 0x6a, "f14": 0x6b, "f10": 0x6d, "f12": 0x6f,
    "f15": 0x71, "help": 0x72, "home": 0x73,
    "pageup": 0x74, "forwarddelete": 0x75, "f4": 0x76,
    "end": 0x77, "f2": 0x78, "pagedown": 0x79,
    "f1": 0x7a, "left": 0x7b, "right": 0x7c,
    "down": 0x7d, "up": 0x7e,
}

# 修饰键标志
MODIFIER_FLAGS = {
    "cmd": 0x100000,
    "shift": 0x20000,
    "option": 0x80000,
    "control": 0x40000,
    "alt": 0x80000,
}

# 修饰键对应的实体键码（用于 hotkey 真正按下修饰键）
MODIFIER_KEYCODES = {
    "cmd": 0x37,
    "shift": 0x38,
    "option": 0x3A,
    "alt": 0x3A,
    "control": 0x3B,
    "ctrl": 0x3B,
}


class MouseController:
    """鼠标控制器 — 移动、点击、拖拽、滚动。"""

    @staticmethod
    def move(x: int, y: int) -> None:
        """将鼠标移动到屏幕坐标 (x, y)。"""
        if not HAS_QUARTZ:
            raise RuntimeError("Quartz not available")
        event = CGEventCreateMouseEvent(None, kCGEventMouseMoved, (x, y), 0)
        CGEventPost(kCGHIDEventTap, event)

    @staticmethod
    def click(x: int, y: int, button: str = "left", clicks: int = 1) -> None:
        """在 (x, y) 处点击指定按钮。button: left/right/middle。"""
        if not HAS_QUARTZ:
            raise RuntimeError("Quartz not available")

        button_map = {
            "left": kCGMouseButtonLeft,
            "right": Quartz.kCGMouseButtonRight,
            "middle": Quartz.kCGMouseButtonCenter,
        }
        cg_button = button_map.get(button, kCGMouseButtonLeft)

        event_type_down = {
            "left": kCGEventLeftMouseDown,
            "right": kCGEventRightMouseDown,
            "middle": kCGEventOtherMouseDown,
        }
        event_type_up = {
            "left": kCGEventLeftMouseUp,
            "right": kCGEventRightMouseUp,
            "middle": kCGEventOtherMouseUp,
        }

        for i in range(clicks):
            # clickState 必须是 1..N 递增，macOS 才能识别为双击/三击
            down = CGEventCreateMouseEvent(
                None, event_type_down[button], (x, y), cg_button
            )
            CGEventSetIntegerValueField(down, kCGMouseEventClickState, i + 1)
            CGEventPost(kCGHIDEventTap, down)
            time.sleep(0.05)
            up = CGEventCreateMouseEvent(
                None, event_type_up[button], (x, y), cg_button
            )
            CGEventSetIntegerValueField(up, kCGMouseEventClickState, i + 1)
            CGEventPost(kCGHIDEventTap, up)

    @staticmethod
    def double_click(x: int, y: int) -> None:
        """在 (x, y) 处双击。"""
        MouseController.click(x, y, "left", clicks=2)

    @staticmethod
    def right_click(x: int, y: int) -> None:
        """在 (x, y) 处右键点击。"""
        MouseController.click(x, y, "right")

    @staticmethod
    def drag(start_x: int, start_y: int, end_x: int, end_y: int, button: str = "left") -> None:
        """拖拽：从 (start_x, start_y) 到 (end_x, end_y)。"""
        if not HAS_QUARTZ:
            raise RuntimeError("Quartz not available")

        button_map = {
            "left": kCGMouseButtonLeft,
            "right": Quartz.kCGMouseButtonRight,
            "middle": Quartz.kCGMouseButtonCenter,
        }
        cg_button = button_map.get(button, kCGMouseButtonLeft)

        # 按下
        down = CGEventCreateMouseEvent(
            None, kCGEventLeftMouseDown, (start_x, start_y), cg_button
        )
        CGEventPost(kCGHIDEventTap, down)
        time.sleep(0.1)

        # 拖动
        drag_type = kCGEventLeftMouseDragged if button == "left" else kCGEventOtherMouseDragged
        drag = CGEventCreateMouseEvent(None, drag_type, (end_x, end_y), cg_button)
        CGEventPost(kCGHIDEventTap, drag)
        time.sleep(0.1)

        # 释放
        up = CGEventCreateMouseEvent(
            None, kCGEventLeftMouseUp, (end_x, end_y), cg_button
        )
        CGEventPost(kCGHIDEventTap, up)

    @staticmethod
    def scroll(x: int, y: int, delta: int, horizontal: bool = False) -> None:
        """在 (x, y) 处滚动。delta>0 向上，delta<0 向下。"""
        if not HAS_QUARTZ:
            raise RuntimeError("Quartz not available")
        # 使用固定精度滚动
        if horizontal:
            event = CGEventCreateScrollWheelEvent(
                None, 0, 0, delta
            )
        else:
            event = CGEventCreateScrollWheelEvent(
                None, 1, delta, 0
            )
        CGEventPost(kCGHIDEventTap, event)


class KeyboardController:
    """键盘控制器 — 按键、输入文本、组合键。"""

    @staticmethod
    def press_key(key: str) -> None:
        """按下并释放一个键（带修饰键检测）。"""
        modifiers = 0
        parts = key.lower().split("+")
        main_key = parts[-1]

        # 解析修饰键
        for part in parts[:-1]:
            part = part.strip()
            if part in MODIFIER_FLAGS:
                modifiers |= MODIFIER_FLAGS[part]

        code = KEY_CODES.get(main_key)
        if code is None:
            raise ValueError(f"Unknown key: {key}")

        # 按下
        event = CGEventCreateKeyboardEvent(None, code, True)
        if modifiers:
            CGEventSetFlags(event, modifiers)
        CGEventPost(kCGHIDEventTap, event)
        time.sleep(0.05)
        # 释放
        event = CGEventCreateKeyboardEvent(None, code, False)
        if modifiers:
            CGEventSetFlags(event, modifiers)
        CGEventPost(kCGHIDEventTap, event)

    @staticmethod
    def type_text(text: str, modifiers: int = 0) -> None:
        """输入文本（支持中文/Unicode）。使用 CGEventKeyboardSetUnicodeString。"""
        if not HAS_QUARTZ:
            raise RuntimeError("Quartz not available")
        for char in text:
            event = CGEventCreateKeyboardEvent(None, 0, True)
            if modifiers:
                CGEventSetFlags(event, modifiers)
            Quartz.CGEventKeyboardSetUnicodeString(event, len(char), [ord(char)])
            CGEventPost(kCGHIDEventTap, event)
            time.sleep(0.02)
            event = CGEventCreateKeyboardEvent(None, 0, False)
            if modifiers:
                CGEventSetFlags(event, modifiers)
            CGEventPost(kCGHIDEventTap, event)
            time.sleep(0.02)

    @staticmethod
    def hotkey(*keys: str) -> None:
        """发送组合键，如 hotkey("cmd", "c") 复制。修饰键会被真实按下。"""
        codes = []
        flags = 0
        mod_codes = []
        for key in keys:
            key = key.lower().strip()
            if key in MODIFIER_FLAGS:
                flags |= MODIFIER_FLAGS[key]
                mod_codes.append(MODIFIER_KEYCODES[key])
            else:
                code = KEY_CODES.get(key)
                if code is None:
                    raise ValueError(f"Unknown key: {key}")
                codes.append(code)

        if not codes:
            raise ValueError("No regular keys provided")

        # 1) 先按下所有修饰键（实体按下，兼容监听 raw keydown 的应用）
        for code in mod_codes:
            event = CGEventCreateKeyboardEvent(None, code, True)
            CGEventPost(kCGHIDEventTap, event)
            time.sleep(0.02)
        # 2) 按下主键（带修饰 flags）
        for code in codes:
            event = CGEventCreateKeyboardEvent(None, code, True)
            CGEventSetFlags(event, flags)
            CGEventPost(kCGHIDEventTap, event)
            time.sleep(0.02)
        # 3) 释放主键
        for code in codes:
            event = CGEventCreateKeyboardEvent(None, code, False)
            CGEventSetFlags(event, flags)
            CGEventPost(kCGHIDEventTap, event)
            time.sleep(0.02)
        # 4) 反向释放修饰键
        for code in reversed(mod_codes):
            event = CGEventCreateKeyboardEvent(None, code, False)
            CGEventPost(kCGHIDEventTap, event)
            time.sleep(0.02)


class WindowManager:
    """窗口管理器 — 列出、激活、移动窗口。"""

    @staticmethod
    def list_windows() -> List[Dict[str, Any]]:
        """列出所有窗口信息。"""
        if not HAS_QUARTZ:
            raise RuntimeError("Quartz not available")
        windows = CGWindowListCopyWindowInfo(
            kCGWindowListOptionAll, kCGNullWindowID
        )
        result = []
        for w in windows:
            if w.get(kCGWindowLayer, 0) != 0:  # 只取普通窗口层
                continue
            result.append({
                "id": w.get(kCGWindowNumber, 0),
                "title": w.get(kCGWindowName, ""),
                "owner": w.get(kCGWindowOwnerName, ""),
                "pid": w.get(kCGWindowOwnerPID, 0),
                "bounds": w.get(kCGWindowBounds, {}),
                "onscreen": w.get(kCGWindowIsOnscreen, False),
            })
        return result

    @staticmethod
    def get_foreground_window() -> Optional[Dict[str, Any]]:
        """获取当前前台窗口信息（通过 AppleScript）。"""
        import subprocess
        script = '''
        tell application "System Events"
            set frontApp to name of first application process whose frontmost is true
            set frontWindow to ""
            try
                set frontWindow to name of first window of first application process whose frontmost is true
            end try
            return {frontApp, frontWindow}
        end tell
        '''
        try:
            out = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=5
            )
            if out.returncode == 0:
                parts = out.stdout.strip().split(", ")
                return {
                    "app": parts[0] if len(parts) > 0 else "",
                    "window": parts[1] if len(parts) > 1 else "",
                }
        except Exception:
            pass
        return {"app": "", "window": "", "error": "获取前台窗口失败（可能缺少辅助功能权限）"}

    @staticmethod
    def activate_window(app_name: str) -> bool:
        """激活指定应用的窗口（将其置于前台）。"""
        import subprocess
        # 转义双引号和反斜杠，避免注入/破坏 AppleScript
        safe_name = app_name.replace("\\", "\\\\").replace('"', '\\"')
        script = f'''
        tell application "{safe_name}"
            activate
        end tell
        '''
        try:
            out = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=5
            )
            return out.returncode == 0
        except Exception:
            return False


# ─── 便捷函数（异步封装）──────────────────────────────────────────────────────

async def mouse_move(x: int, y: int) -> str:
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, MouseController.move, x, y)
    return f"Mouse moved to ({x}, {y})"


async def mouse_click(x: int, y: int, button: str = "left", clicks: int = 1) -> str:
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, MouseController.click, x, y, button, clicks)
    return f"{button} click at ({x}, {y})" + (f" x{clicks}" if clicks > 1 else "")


async def mouse_double_click(x: int, y: int) -> str:
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, MouseController.double_click, x, y)
    return f"Double clicked at ({x}, {y})"


async def mouse_right_click(x: int, y: int) -> str:
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, MouseController.right_click, x, y)
    return f"Right clicked at ({x}, {y})"


async def mouse_drag(start_x: int, start_y: int, end_x: int, end_y: int) -> str:
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None, MouseController.drag, start_x, start_y, end_x, end_y
    )
    return f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})"


async def mouse_scroll(x: int, y: int, delta: int, horizontal: bool = False) -> str:
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None, MouseController.scroll, x, y, delta, horizontal
    )
    direction = "horizontal" if horizontal else "vertical"
    return f"Scrolled {direction} at ({x}, {y}) delta={delta}"


async def key_press(key: str) -> str:
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, KeyboardController.press_key, key)
    return f"Pressed {key}"


async def type_text(text: str) -> str:
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, KeyboardController.type_text, text)
    return f"Typed: {text}"


async def hotkey(*keys: str) -> str:
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, KeyboardController.hotkey, *keys)
    return f"Hotkey: {'+'.join(keys)}"


async def get_windows() -> list:
    loop = asyncio.get_event_loop()
    windows = await loop.run_in_executor(None, WindowManager.list_windows)
    return windows


async def get_foreground() -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, WindowManager.get_foreground_window)


async def activate_app(app_name: str) -> str:
    loop = asyncio.get_event_loop()
    ok = await loop.run_in_executor(None, WindowManager.activate_window, app_name)
    if ok:
        return f"Activated {app_name}"
    return f"Failed to activate {app_name}"
