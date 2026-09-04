# Workbuddy Computer Use for Intel Mac

> **这是给 Intel Mac 的。**
> Apple Silicon（M1/M2/M3/M4）的 macOS 已经有原生 Computer Use，不需要这个。如果你在用 M 系列芯片，跳过就好——你们的原生方案更好。

---

# Workbuddy Computer Use for Intel Mac（中英双语）

## 这是什么

一个 MCP 协议服务器，让 WorkBuddy Agent 能控制 macOS 桌面：截图、鼠标、键盘、窗口管理、Chrome 自动化。

简单说就是——给补上 Intel Mac 没有的原生 Computer Use。

An MCP server that gives WorkBuddy Agent macOS desktop control: screenshot, mouse, keyboard, window management, Chrome automation.

In short — it fills the Computer Use gap on Intel Macs.

## 为什么有这个项目

跑 WorkBuddy 的 Intel Mac 用户，没有原生 Computer Use 可用。M 系列芯片的用户别担心，你们已经有更好的方案了。

这个项目把 Fan-ComputerUse 的三工具 MCP 协议设计，加上 yangjia66 的 CDP 浏览器控制方案，专门给 Intel Mac 补上这个能力。

WorkBuddy on Intel Mac lacked Computer Use. Apple Silicon users — you're already covered with something better.

This project stitches together Fan-ComputerUse's three-tool MCP protocol + yangjia66's CDP browser control to fill that gap.

---

## 工具清单

| 工具 | 做什么 | 底层 |
|---|---|---|
| `screenshot` | 全屏/区域截图，返回 base64 或保存文件 | Quartz/CoreGraphics，失败回退 screencapture CLI |
| `computer` | 鼠标移动/点击/拖拽/滚动、按键/组合键/输入文本、窗口管理 | Quartz Events + Accessibility API |
| `browser_dom` | Chrome CDP：导航/截图/点击/输入/JS/标签/滚动/DOM | Chrome DevTools Protocol |

---

## 安装

```bash
git clone https://github.com/Guyzn/workbuddy-cua-mcp.git ~/.workbuddy/skills/cua-mcp
cd ~/.workbuddy/skills/cua-mcp
python3 install.py
```

或者手动：

```bash
pip install -r requirements.txt
# install.py 会自动配置 ~/.workbuddy/mcp.json
```

## 权限

首次使用前，去 **系统设置 → 隐私与安全性 → 辅助功能** 里，把相关进程加进去。

First use requires granting accessibility access in **System Settings → Privacy & Security → Accessibility**.

---

## 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `BROWSER_DEBUG_PORT` | 9225 | Chrome CDP 调试端口 |
| `CHROME_PATH` | `/Applications/Google Chrome.app/...` | Chrome 路径 |
| `BROWSER_AUTOLAUNCH` | true | 没有调试端口时自动拉起 Chrome |
| `BROWSER_HEADLESS` | false | 无头模式（macOS 推荐有头） |

---

## 使用示例

```python
# 截图
await screenshot()  # 全屏，返回 base64
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

---

## 平台

- ✅ **macOS 12+（Monterey 及以上）— Intel Mac**
- ❌ Apple Silicon（原生支持，不需要这个）
- ❌ Windows
- ❌ Linux

---

## 安全

- 坐标越界会拒绝（超出屏幕范围的操作会被拦下）
- 紧急停止（`Ctrl+C` 或系统级中断）

---

## 设计参考

- **Fan-ComputerUse** — 三工具 MCP 协议设计（`screenshot` / `computer` / `browser_dom`）
- **yangjia66/workbuddy-computer-use-kit** — browser-control CDP 方案
