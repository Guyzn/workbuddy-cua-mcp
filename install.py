#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cua-mcp 安装脚本
==============
自动完成：
1. 检查 Python 版本
2. 创建虚拟环境（可选）
3. 安装依赖
4. 配置 WorkBuddy MCP（生成 mcp.json）
"""

import json
import os
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
VENV_DIR = SKILL_DIR / ".venv"
MCP_JSON = Path.home() / ".workbuddy" / "mcp.json"


def run(cmd, **kwargs):
    print(f"  $ {cmd}")
    return subprocess.run(cmd, shell=True, **kwargs)


def main():
    print("=" * 60)
    print("  cua-mcp macOS 安装")
    print("=" * 60)

    # 1. Python 版本检查
    if sys.version_info < (3, 9):
        print("[ERROR] 需要 Python 3.9+")
        sys.exit(1)

    # 2. 创建虚拟环境
    if not VENV_DIR.exists():
        print("\n[1/4] 创建虚拟环境...")
        run(f"{sys.executable} -m venv {VENV_DIR}")
    else:
        print("\n[1/4] 虚拟环境已存在，跳过")

    # 3. 安装依赖
    print("\n[2/4] 安装依赖...")
    pip = VENV_DIR / "bin" / "pip"
    run(f"{pip} install --upgrade pip")
    run(f"{pip} install -r {SKILL_DIR / 'requirements.txt'}")

    # 4. 配置 MCP
    print("\n[3/4] 配置 WorkBuddy MCP...")
    python_path = VENV_DIR / "bin" / "python"
    server_path = SKILL_DIR / "server.py"

    mcp_config = {}
    if MCP_JSON.exists():
        try:
            mcp_config = json.loads(MCP_JSON.read_text())
        except Exception:
            pass

    mcp_config["mcpServers"] = mcp_config.get("mcpServers", {})
    mcp_config["mcpServers"]["cua-mcp"] = {
        "command": str(python_path),
        "args": [str(server_path)],
    }

    MCP_JSON.parent.mkdir(parents=True, exist_ok=True)
    MCP_JSON.write_text(json.dumps(mcp_config, indent=2, ensure_ascii=False))
    print(f"  已写入 {MCP_JSON}")

    # 5. 完成
    print("\n[4/4] 安装完成！")
    print(f"""
使用方法：
  1. 手动启动：{python_path} {server_path}
  2. 或通过 mcp.json 自动加载（重启 WorkBuddy 后生效）

环境变量（可选）：
  BROWSER_DEBUG_PORT  Chrome 调试端口（默认 9225）
  CHROME_PATH        Chrome 路径（默认 /Applications/Google Chrome.app/...）
  BROWSER_AUTOLAUNCH 无调试端口时自动拉起 Chrome（默认 true）
  BROWSER_HEADLESS   无头模式（默认 false，macOS 推荐有头）

注意：首次使用截图/控制时，macOS 会弹出权限提示，
      请到 系统设置 → 隐私与安全性 → 辅助功能 中授权。
""")


if __name__ == "__main__":
    main()
