#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
macOS 原生浏览器 DOM 控制模块 — 基于 Chrome DevTools Protocol (CDP)
============================================================
参考 yangjia66 的 browser-control CDP 方案，适配 macOS。

核心能力：
- 自动拉起带远程调试端口的 Chrome（或使用已登录的浏览器）
- 导航、截图、坐标点击、输入中文、执行 JS
- 标签页管理（列出/新建/关闭/切换）
- 滚动、获取页面 DOM 结构

环境变量：
  BROWSER_DEBUG_PORT  调试端口，默认 9225
  CHROME_PATH         Chrome 可执行文件路径（macOS）
  CHROME_USER_DATA_DIR 专用 profile 目录
  BROWSER_AUTOLAUNCH  true/false，默认 true
  BROWSER_HEADLESS    true/false，默认 false（macOS 推荐有头模式）
"""

import asyncio
import base64
import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Optional, Dict, Any, List

# ─── 配置 ─────────────────────────────────────────────────────────────────────
PORT = int(os.environ.get("BROWSER_DEBUG_PORT", "9225"))

# 浏览器路径自动检测：优先用户指定 → Chrome → Edge → 其他 Chromium
_fallback_paths = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "/Applications/Opera.app/Contents/MacOS/Opera",
    "/Applications/Vivaldi.app/Contents/MacOS/Vivaldi",
]

raw_chrome = os.environ.get("CHROME_PATH", "")
if raw_chrome and Path(raw_chrome).exists():
    CHROME = raw_chrome
else:
    CHROME = next((p for p in _fallback_paths if Path(p).exists()), _fallback_paths[0])

USER_DATA = os.environ.get(
    "CHROME_USER_DATA_DIR",
    str(Path.home() / "Library" / "Application Support" / "workbuddy-browser-profile"),
)
AUTOLAUNCH = os.environ.get("BROWSER_AUTOLAUNCH", "true").lower() == "true"
HEADLESS = os.environ.get("BROWSER_HEADLESS", "false").lower() == "true"

SHOTS_DIR = Path(__file__).resolve().parent.parent / "shots"
SHOTS_DIR.mkdir(exist_ok=True)

# ─── CDP 连接状态 ──────────────────────────────────────────────────────────────
_browser_ws = None
_page_ws_obj = None
_cdp_id = 0
_launch_lock = asyncio.Lock()
_active_target_id: Optional[str] = None  # 当前操作的标签页，new_tab 后自动切换


def _http_json(path: str):
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}{path}", timeout=5) as r:
        return json.loads(r.read())


async def _ensure_browser():
    """确保有带远程调试的 Chrome 在跑；没有则按需拉起。"""
    try:
        _http_json("/json/version")
        return
    except Exception:
        if not AUTOLAUNCH:
            raise RuntimeError(
                f"未检测到带远程调试的 Chrome。请手动启动 "
                f'Chrome --remote-debugging-port={PORT}，'
                "或设置 BROWSER_AUTOLAUNCH=true"
            )
    async with _launch_lock:
        try:
            _http_json("/json/version")
            return
        except Exception:
            pass
        args = [
            CHROME,
            f"--remote-debugging-port={PORT}",
            f"--user-data-dir={USER_DATA}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-background-networking",
        ]
        if HEADLESS:
            args.append("--headless=new")
        subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(30):
            await asyncio.sleep(1)
            try:
                _http_json("/json/version")
                return
            except Exception:
                pass
        raise RuntimeError("自动拉起 Chrome 失败（调试端口未就绪）")


async def _browser_ws_conn():
    global _browser_ws
    if _browser_ws is not None and not _browser_ws.closed:
        return _browser_ws
    info = _http_json("/json/version")
    import websockets
    _browser_ws = await websockets.connect(
        info["webSocketDebuggerUrl"], open_timeout=10, close_timeout=5
    )
    return _browser_ws


async def _cdp(ws, method: str, params=None):
    global _cdp_id
    _cdp_id += 1
    mid = _cdp_id
    await ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
    while True:
        raw = await ws.recv()
        msg = json.loads(raw)
        if msg.get("id") == mid:
            if "error" in msg:
                raise RuntimeError(f"CDP {method} error: {msg['error']}")
            return msg.get("result", {})


async def page_ws():
    """获取（或创建）一个 page 级 WebSocket 连接，指向当前活跃标签页。"""
    global _page_ws_obj, _active_target_id
    await _ensure_browser()
    tabs = _http_json("/json/list")
    pages = {t["id"]: t for t in tabs if t.get("type") == "page"}

    # 已有连接：确认目标页仍然存在，否则重建
    if _page_ws_obj is not None and not _page_ws_obj.closed:
        if _active_target_id in pages:
            return _page_ws_obj
        try:
            await _page_ws_obj.close()
        except Exception:
            pass
        _page_ws_obj = None

    # 选定目标页：优先沿用活跃页，否则取第一个
    if _active_target_id in pages:
        tid = _active_target_id
    elif pages:
        tid = next(iter(pages))
    else:
        bws = await _browser_ws_conn()
        res = await _cdp(bws, "Target.createTarget", {"url": "about:blank"})
        tid = res["targetId"]
    _active_target_id = tid
    import websockets
    url = f"ws://127.0.0.1:{PORT}/devtools/page/{tid}"
    _page_ws_obj = await websockets.connect(url, open_timeout=10, close_timeout=5)
    return _page_ws_obj


# ─── 工具函数 ─────────────────────────────────────────────────────────────────

async def browser_navigate(url: str) -> str:
    """导航到指定 URL，返回页面标题。"""
    ws = await page_ws()
    await _cdp(ws, "Page.enable")
    await _cdp(ws, "Page.navigate", {"url": url})
    try:
        await _cdp(ws, "Page.stopLoading")
    except Exception:
        pass
    await asyncio.sleep(2.0)
    title = await _cdp(
        ws, "Runtime.evaluate", {"expression": "document.title", "returnByValue": True}
    )
    return f"已导航到 {url}，标题：{title.get('result', {}).get('value', '')}"


async def browser_screenshot(path: str = "") -> str:
    """截取当前页面视口，保存为 PNG 并返回文件路径。"""
    ws = await page_ws()
    await _cdp(ws, "Page.enable")
    res = await _cdp(
        ws,
        "Page.captureScreenshot",
        {"format": "png", "captureBeyondViewport": False},
    )
    data = base64.b64decode(res["data"])
    out = Path(path) if path else SHOTS_DIR / f"screenshot_{time.strftime('%Y%m%d_%H%M%S')}.png"
    out = out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    return f"截图已保存：{out}"


async def browser_click(x: int, y: int) -> str:
    """在视口坐标 (x, y) 处点击（左键单击）。"""
    ws = await page_ws()
    await _cdp(
        ws,
        "Input.dispatchMouseEvent",
        {"type": "mousePressed", "x": x, "y": y, "button": "left", "clickCount": 1},
    )
    await _cdp(
        ws,
        "Input.dispatchMouseEvent",
        {"type": "mouseReleased", "x": x, "y": y, "button": "left", "clickCount": 1},
    )
    return f"已在 ({x}, {y}) 点击"


async def browser_type(text: str) -> str:
    """在当前获得焦点的输入框中键入文本（支持中文）。"""
    ws = await page_ws()
    await _cdp(ws, "Input.insertText", {"text": text})
    return f"已输入：{text}"


async def browser_eval(js: str) -> str:
    """在页面上下文执行 JavaScript，返回结果（JSON 字符串）。"""
    ws = await page_ws()
    res = await _cdp(
        ws,
        "Runtime.evaluate",
        {"expression": js, "returnByValue": True, "awaitPromise": True},
    )
    if "exceptionDetails" in res:
        return f"JS 异常：{res['exceptionDetails']}"
    return json.dumps(res.get("result", {}).get("value", None), ensure_ascii=False)


async def browser_list_tabs() -> str:
    """列出当前所有标签页（id / url / title）。"""
    await _ensure_browser()
    tabs = _http_json("/json/list")
    out = []
    for t in tabs:
        if t.get("type") == "page":
            out.append(
                {"id": t.get("id"), "url": t.get("url"), "title": t.get("title")}
            )
    return json.dumps(out, ensure_ascii=False, indent=2)


async def browser_new_tab(url: str = "about:blank") -> str:
    """新建一个标签页并导航到 url，后续操作自动切换到新标签，返回 targetId。"""
    global _page_ws_obj, _active_target_id
    await _ensure_browser()
    bws = await _browser_ws_conn()
    res = await _cdp(bws, "Target.createTarget", {"url": url})
    tid = res.get("targetId")
    # 切换活跃标签：关闭旧 page 连接，下次 page_ws() 重连到新标签
    if _page_ws_obj is not None and not _page_ws_obj.closed:
        try:
            await _page_ws_obj.close()
        except Exception:
            pass
        _page_ws_obj = None
    _active_target_id = tid
    return f"新标签已创建并激活：{tid} -> {url}"


async def browser_scroll(
    x: int, y: int, delta_x: int = 0, delta_y: int = -300
) -> str:
    """在坐标 (x, y) 处滚动滚轮。"""
    ws = await page_ws()
    await _cdp(
        ws,
        "Input.dispatchMouseEvent",
        {"type": "mouseWheel", "x": x, "y": y, "deltaX": delta_x, "deltaY": delta_y},
    )
    return f"已在 ({x}, {y}) 滚动 deltaY={delta_y}"


async def browser_get_dom() -> str:
    """获取当前页面的 DOM 结构（简化 JSON 树）。"""
    ws = await page_ws()
    # 获取 document
    doc = await _cdp(ws, "DOM.getDocument", {"depth": -1, "pierce": True})
    root_id = doc["root"]["nodeId"]
    # 获取 outerHTML
    html = await _cdp(ws, "DOM.getOuterHTML", {"nodeId": root_id})
    return html.get("outerHTML", "")
