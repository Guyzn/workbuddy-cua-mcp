# SKILL.md — cua-mcp

## 触发条件

当用户需要以下能力时使用此 skill：
- 截取屏幕截图（全屏或指定区域）
- 控制鼠标（移动、点击、拖拽、滚动）
- 控制键盘（按键、输入文本、组合键）
- 管理窗口（列出、激活）
- 控制 Chrome 浏览器（导航、点击、输入、执行 JS、截图）

## 依赖

- Python 3.9+
- macOS 12+ (Monterey)
- pyobjc-framework-Quartz（截图和控制）
- websockets（浏览器 CDP）
- Chrome 浏览器（用于 browser_dom 工具）

## 安装

```bash
cd ~/.workbuddy/skills/cua-mcp
python3 install.py
```

## 工具

### 1. screenshot — 截图

```
screenshot(x?, y?, width?, height?, return_base64?) → str
```

- 全屏截图：不传 x/y/width/height
- 区域截图：传 x/y/width/height
- return_base64=true 返回 base64 图片，false 保存到文件

### 2. computer — 桌面控制

```
computer_action(action, ...) → str
```

| action | 必填参数 | 说明 |
|--------|----------|------|
| mouse_move | x, y | 移动鼠标 |
| mouse_click | x, y | 点击（可选 button, clicks） |
| mouse_double_click | x, y | 双击 |
| mouse_right_click | x, y | 右键 |
| mouse_drag | start_x, start_y, end_x, end_y | 拖拽 |
| mouse_scroll | x, y, delta | 滚动 |
| key_press | key | 按键 |
| type_text | text | 输入文本 |
| hotkey | keys（列表） | 组合键 |
| get_windows | — | 列出窗口 |
| get_foreground | — | 前台窗口 |
| activate_app | app_name | 激活应用 |

### 3. browser_dom — 浏览器 CDP

```
browser_dom(action, ...) → str
```

| action | 必填参数 | 说明 |
|--------|----------|------|
| navigate | url | 导航到 URL |
| screenshot | — | 页面截图 |
| click | x, y | 坐标点击 |
| type | text | 输入文本 |
| eval | js | 执行 JS |
| list_tabs | — | 列出标签 |
| new_tab | url | 新建标签 |
| scroll | x, y | 滚动 |
| get_dom | — | 获取 DOM |

## 运行纪律（必读）

- **本 server 是 stdio 协议 MCP server，由 WorkBuddy 宿主进程负责拉起/管理。**
- **禁止** 用 `nohup python server.py &` 或任何方式手动后台拉起——stdio server 脱离宿主后宿主永远连不上（报 `Not connected`），还会留下孤儿进程。
- **改了代码后重启方式**：`pkill -f "skills/cua-mcp/server.py"` 清掉残留进程 → 让宿主重连（重开会话或重启 WorkBuddy），宿主会用新代码重新 spawn。
- 验证修复可用直调模块（`python3 -c "from modules.computer_control import ..."`）或 stdio 冒烟脚本（Popen server.py + JSON-RPC initialize + tools/call），两者都不影响宿主管线。
- ⚠️ get_windows 走 osascript：其输出会把嵌套列表**扁平化**且不转义字符串，**禁止** 用 `ast.literal_eval` 解析；必须让 AppleScript 端自做 JSON 转义、每行输出一个 JSON 对象，Python 端逐行 `json.loads`。

## 安全

- 辅助功能权限：首次使用需在系统设置中授权
- 坐标越界：超出屏幕范围的操作会被拒绝
- 紧急停止：Ctrl+C 可中断

## 示例

```python
# 全屏截图
b64 = await screenshot()

# 点击 (500, 300)
await computer_action("mouse_click", x=500, y=300)

# 输入中文
await computer_action("type_text", text="你好世界")

# Cmd+C 复制
await computer_action("hotkey", keys=["cmd", "c"])

# 浏览器导航
await browser_dom("navigate", url="https://www.baidu.com")

# 浏览器点击
await browser_dom("click", x=200, y=400)
```
