#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cua-mcp — macOS 原生 Computer Use MCP 服务器
==============================================
三工具设计（参考 Fan-ComputerUse，适配 macOS）：
  1. screenshot  — 全屏/区域截图
  2. computer    — 鼠标/键盘/窗口控制
  3. browser_dom — Chrome CDP 浏览器自动化

底层实现：
  - 截图：Quartz/CoreGraphics（失败回退 screencapture CLI）
  - 控制：Quartz Events + Accessibility API
  - 浏览器：Chrome DevTools Protocol (CDP)

安装：
  1. pip install -r requirements.txt
  2. 在 WorkBuddy 设置中启用 cua-mcp 连接器，或手动配置 mcp.json

使用：
  python server.py
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

# 导入本地模块
sys.path.insert(0, str(Path(__file__).parent))
from modules.screenshot import take_screenshot, screenshot_to_base64
from modules.computer_control import (
    mouse_move,
    mouse_click,
    mouse_double_click,
    mouse_right_click,
    mouse_drag,
    mouse_scroll,
    key_press,
    type_text,
    hotkey,
    get_windows,
    get_foreground,
    activate_app,
)
from modules.browser_dom import (
    browser_navigate,
    browser_screenshot,
    browser_click,
    browser_type,
    browser_eval,
    browser_list_tabs,
    browser_new_tab,
    browser_scroll,
    browser_get_dom,
)

# ─── MCP 服务器 ──────────────────────────────────────────────────────────────
mcp = FastMCP("cua-mcp")

# 截图存储目录
SHOTS_DIR = Path(__file__).parent / "shots"
SHOTS_DIR.mkdir(exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
# 工具 1: screenshot — 截图
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
async def screenshot(
    x: Optional[int] = None,
    y: Optional[int] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    return_base64: bool = True,
) -> str:
    """
    截取屏幕截图。
    
    参数:
        x, y: 截图区域左上角坐标（不传则全屏）
        width, height: 截图区域宽高（不传则全屏）
        return_base64: 是否返回 base64 图片（默认 true）
    
    返回:
        base64 图片数据 URI 或保存路径
    """
    try:
        data = await take_screenshot(x, y, width, height)
        if return_base64:
            return screenshot_to_base64(data)
        # 保存到文件
        path = SHOTS_DIR / f"screenshot_{time.strftime('%Y%m%d_%H%M%S')}.png"
        path.write_bytes(data)
        return f"截图已保存：{path}"
    except Exception as e:
        return f"截图失败：{str(e)}"


# ═══════════════════════════════════════════════════════════════════════════════
# 工具 2: computer — 桌面控制（鼠标/键盘/窗口）
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
async def computer_action(
    action: str,
    x: Optional[int] = None,
    y: Optional[int] = None,
    button: str = "left",
    clicks: int = 1,
    start_x: Optional[int] = None,
    start_y: Optional[int] = None,
    end_x: Optional[int] = None,
    end_y: Optional[int] = None,
    delta: int = 0,
    horizontal: bool = False,
    key: str = "",
    text: str = "",
    keys: Optional[list] = None,
    app_name: str = "",
) -> str:
    """
    执行桌面控制操作（鼠标/键盘/窗口）。
    
    参数:
        action: 操作类型
            - mouse_move: 移动鼠标（需 x, y）
            - mouse_click: 点击鼠标（需 x, y；可选 button, clicks）
            - mouse_double_click: 双击（需 x, y）
            - mouse_right_click: 右键点击（需 x, y）
            - mouse_drag: 拖拽（需 start_x, start_y, end_x, end_y）
            - mouse_scroll: 滚动（需 x, y, delta；可选 horizontal）
            - key_press: 按键（需 key，如 "cmd", "enter", "delete"）
            - type_text: 输入文本（需 text）
            - hotkey: 组合键（需 keys 列表，如 ["cmd", "c"]）
            - get_windows: 列出所有窗口
            - get_foreground: 获取前台窗口
            - activate_app: 激活应用（需 app_name）
        x, y: 鼠标坐标
        button: 鼠标按钮（left/right/middle）
        clicks: 点击次数
        start_x, start_y, end_x, end_y: 拖拽起止坐标
        delta: 滚动量（正上负下）
        horizontal: 是否水平滚动
        key: 按键名称
        text: 要输入的文本
        keys: 组合键列表
        app_name: 应用名称
    
    返回:
        操作结果描述
    """
    try:
        if action == "mouse_move":
            if x is None or y is None:
                return "错误：mouse_move 需要 x, y 参数"
            return await mouse_move(x, y)

        elif action == "mouse_click":
            if x is None or y is None:
                return "错误：mouse_click 需要 x, y 参数"
            return await mouse_click(x, y, button, clicks)

        elif action == "mouse_double_click":
            if x is None or y is None:
                return "错误：mouse_double_click 需要 x, y 参数"
            return await mouse_double_click(x, y)

        elif action == "mouse_right_click":
            if x is None or y is None:
                return "错误：mouse_right_click 需要 x, y 参数"
            return await mouse_right_click(x, y)

        elif action == "mouse_drag":
            if any(v is None for v in [start_x, start_y, end_x, end_y]):
                return "错误：mouse_drag 需要 start_x, start_y, end_x, end_y 参数"
            return await mouse_drag(start_x, start_y, end_x, end_y)

        elif action == "mouse_scroll":
            if x is None or y is None:
                return "错误：mouse_scroll 需要 x, y 参数"
            return await mouse_scroll(x, y, delta, horizontal)

        elif action == "key_press":
            if not key:
                return "错误：key_press 需要 key 参数"
            return await key_press(key)

        elif action == "type_text":
            if not text:
                return "错误：type_text 需要 text 参数"
            return await type_text(text)

        elif action == "hotkey":
            if not keys:
                return "错误：hotkey 需要 keys 参数（列表）"
            return await hotkey(*keys)

        elif action == "get_windows":
            windows = await get_windows()
            return json.dumps(windows[:50], ensure_ascii=False, indent=2)

        elif action == "get_foreground":
            fg = await get_foreground()
            if fg is None:
                return "错误：获取前台窗口失败（可能缺少辅助功能权限）"
            return json.dumps(fg, ensure_ascii=False, indent=2)

        elif action == "activate_app":
            if not app_name:
                return "错误：activate_app 需要 app_name 参数"
            return await activate_app(app_name)

        else:
            return f"错误：未知操作 '{action}'"

    except Exception as e:
        return f"操作失败：{str(e)}"


# ═══════════════════════════════════════════════════════════════════════════════
# 工具 3: browser_dom — 浏览器 CDP 控制
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
async def browser_dom(
    action: str,
    url: str = "",
    x: Optional[int] = None,
    y: Optional[int] = None,
    text: str = "",
    js: str = "",
    delta_x: int = 0,
    delta_y: int = -300,
) -> str:
    """
    通过 CDP 控制 Chrome 浏览器。
    
    参数:
        action: 操作类型
            - navigate: 导航到 URL（需 url）
            - screenshot: 页面截图
            - click: 坐标点击（需 x, y）
            - type: 输入文本（需 text）
            - eval: 执行 JavaScript（需 js）
            - list_tabs: 列出标签页
            - new_tab: 新建标签页（需 url）
            - scroll: 滚动页面（需 x, y；可选 delta_x, delta_y）
            - get_dom: 获取页面 DOM
        url: 网址
        x, y: 视口坐标
        text: 输入文本
        js: JavaScript 代码
        delta_x, delta_y: 滚动量
    
    返回:
        操作结果描述
    """
    try:
        if action == "navigate":
            if not url:
                return "错误：navigate 需要 url 参数"
            return await browser_navigate(url)

        elif action == "screenshot":
            return await browser_screenshot()

        elif action == "click":
            if x is None or y is None:
                return "错误：click 需要 x, y 参数"
            return await browser_click(x, y)

        elif action == "type":
            if not text:
                return "错误：type 需要 text 参数"
            return await browser_type(text)

        elif action == "eval":
            if not js:
                return "错误：eval 需要 js 参数"
            return await browser_eval(js)

        elif action == "list_tabs":
            return await browser_list_tabs()

        elif action == "new_tab":
            return await browser_new_tab(url)

        elif action == "scroll":
            if x is None or y is None:
                return "错误：scroll 需要 x, y 参数"
            return await browser_scroll(x, y, delta_x, delta_y)

        elif action == "get_dom":
            return await browser_get_dom()

        else:
            return f"错误：未知操作 '{action}'"

    except Exception as e:
        return f"浏览器操作失败：{str(e)}"


# ─── 入口 ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
