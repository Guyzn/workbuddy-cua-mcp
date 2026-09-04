# cua-mcp — macOS 原生 Computer Use MCP 工具

> 让 WorkBuddy Agent 拥有 macOS 桌面控制能力：截图、鼠标/键盘操作、窗口管理、Chrome 浏览器自动化。

## 设计参考

- **Fan-ComputerUse** 的三工具 MCP 协议设计（`screenshot` / `computer` / `browser_dom`）
- **yangjia66/workbuddy-computer-use-kit** 的 browser-control CDP 方案

## 工具清单

| 工具 | 描述 | 底层 |
|------|------|------|
| `screenshot` | 全屏/区域截图，返回 base64 或保存文件 | Quartz/CoreGraphics → screencapture CLI 回退 |
| `computer` | 鼠标移动/点击/拖拽/滚动、按键/组合键/输入文本、窗口管理 | Quartz Events + Accessibility API |
| `browser_dom` | Chrome CDP：导航/截图/点击/输入/JS/标签/滚动/DOM | Chrome DevTools Protocol |

## 安装

```bash
cd ~/.workbuddy/skills/cua-mcp
python3 install.py
```

或手动：

```bash
pip install -r requirements.txt
# 然后配置 ~/.workbuddy/mcp.json（install.py 会自动生成）
```

## 权限

首次使用需在 **系统设置 → 隐私与安全性 → 辅助功能** 中授权相关进程。

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `BROWSER_DEBUG_PORT` | 9225 | Chrome CDP 调试端口 |
| `CHROME_PATH` | `/Applications/Google Chrome.app/...` | Chrome 路径 |
| `BROWSER_AUTOLAUNCH` | true | 无调试端口时自动拉起 Chrome |
| `BROWSER_HEADLESS` | false | 无头模式（macOS 推荐有头） |

## 使用示例

```python
# 截图
await screenshot()  # 返回 base64
await screenshot(x=100, y=100, width=800, height=600)  # 区域截图

# 桌面控制
await computer_action("mouse_click", x=500, y=300)
await computer_action("type_text", text="Hello 世界")
await computer_action("hotkey", keys=["cmd", "c"])
await computer_action("get_windows")

# 浏览器
await browser_dom("navigate", url="https://example.com")
await browser_dom("click", x=200, y=400)
await browser_dom("type", text="搜索内容")
```

## 安全机制

- 坐标越界拦截（超出屏幕范围拒绝执行）
- 前台窗口校验（操作前确认目标应用已激活）
- 紧急停止（可通过 `Ctrl+C` 或系统级中断）

## 平台

- ✅ macOS 12+（Monterey 及以上）
- ❌ Windows（参考 yangjia66 / CarlosShao 的方案）
- ❌ Linux
