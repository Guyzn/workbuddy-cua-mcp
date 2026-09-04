#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
macOS 原生截图模块 — 使用 Quartz/CoreGraphics
============================================
支持全屏截图和指定区域截图，性能优于 screencapture CLI。
"""

import asyncio
import base64
import os
import tempfile
from pathlib import Path
from typing import Optional

# 优先使用 Quartz（需要 pyobjc），失败回退到 screencapture CLI
try:
    import Quartz
    from Quartz import (
        CGRectMake,
        CGWindowListCreateImage,
        kCGWindowListOptionOnScreenOnly,
        kCGNullWindowID,
        kCGWindowImageDefault,
    )
    HAS_QUARTZ = True
except ImportError:
    HAS_QUARTZ = False


def capture_fullscreen_quartz() -> bytes:
    """使用 Quartz 截取全屏（主显示器），返回 PNG bytes。"""
    main_display_id = Quartz.CGMainDisplayID()
    bounds = Quartz.CGDisplayBounds(main_display_id)
    image = CGWindowListCreateImage(
        bounds,
        kCGWindowListOptionOnScreenOnly,
        kCGNullWindowID,
        kCGWindowImageDefault,
    )
    if not image:
        raise RuntimeError("CGWindowListCreateImage 返回 None")
    return _cgimage_to_png(image)


def capture_region_quartz(x: int, y: int, width: int, height: int) -> bytes:
    """使用 Quartz 截取指定区域，返回 PNG bytes。

    注意：CGWindowListCreateImage 的 CGRect 使用左上角原点坐标系，
    与 CGEvent 鼠标坐标一致，无需翻转。
    """
    rect = CGRectMake(x, y, width, height)
    image = CGWindowListCreateImage(
        rect,
        kCGWindowListOptionOnScreenOnly,
        kCGNullWindowID,
        kCGWindowImageDefault,
    )
    if not image:
        raise RuntimeError("CGWindowListCreateImage 返回 None")
    return _cgimage_to_png(image)


def _cgimage_to_png(image) -> bytes:
    """将 CGImageRef 编码为 PNG bytes。"""
    from Foundation import NSMutableData
    data = NSMutableData.data()
    # CGImageDestinationCreateWithData 直接接受 UTType 字符串，无需 LaunchServices
    dest = Quartz.CGImageDestinationCreateWithData(
        data, "public.png", 1, None
    )
    if not dest:
        raise RuntimeError("CGImageDestinationCreateWithData 失败")
    Quartz.CGImageDestinationAddImage(dest, image, None)
    if not Quartz.CGImageDestinationFinalize(dest):
        raise RuntimeError("CGImageDestinationFinalize 失败")
    return bytes(data)


def capture_fullscreen_cli(path: str) -> bytes:
    """使用 screencapture CLI 截取全屏，返回 PNG bytes。"""
    import subprocess
    subprocess.run(["screencapture", "-x", path], check=True)
    return Path(path).read_bytes()


def capture_region_cli(path: str, x: int, y: int, w: int, h: int) -> bytes:
    """使用 screencapture CLI 截取指定区域。"""
    import subprocess
    subprocess.run(["screencapture", "-x", f"-R{x},{y},{w},{h}", path], check=True)
    return Path(path).read_bytes()


async def take_screenshot(
    x: Optional[int] = None,
    y: Optional[int] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> bytes:
    """
    异步截图。
    如果提供 x/y/width/height 则截取指定区域，否则全屏。
    优先使用 Quartz，失败回退到 screencapture CLI。
    """
    if HAS_QUARTZ:
        loop = asyncio.get_event_loop()
        if x is not None and y is not None and width and height:
            data = await loop.run_in_executor(
                None, capture_region_quartz, x, y, width, height
            )
        else:
            data = await loop.run_in_executor(None, capture_fullscreen_quartz)
        return data
    else:
        loop = asyncio.get_event_loop()
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
            tmp_path = tf.name
        try:
            if x is not None and y is not None and width and height:
                data = await loop.run_in_executor(
                    None, capture_region_cli, tmp_path, x, y, width, height
                )
            else:
                data = await loop.run_in_executor(None, capture_fullscreen_cli, tmp_path)
            return data
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def screenshot_to_base64(data: bytes) -> str:
    """将 PNG bytes 编码为 base64 data URI。"""
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:image/png;base64,{b64}"
