# 小6聊天窗口 · 整窗收起（最终方案）

## 为什么改
上一版（d181f3e）只折叠了**对话历史**，但**输入框一直常驻底部**，界面并没有真正"干净"，
不符合你说的"聊天窗口自动隐藏、鼠标放上去显示"。这版按你选的「整窗收起 hover 展开」重做。

## 现在的行为
- **默认**：整个聊天窗口收起，屏幕底部只剩一条细触发条 `💬 对话`（玻璃拟态）。
- **展开**：鼠标移到聊天区任意位置（含触发条），整窗从下方平滑升起，露出历史 + 输入框。
- **收起**：鼠标移开 0.8 秒后自动收回。
- **钉住**：点击底部触发条可固定展开（再点取消）；移动端没 hover 也能用。
- **保护**：流式回复中、或输入框正在聚焦打字时，绝不自动收起；新消息到达 / 回复结束会自动展开，闲置数秒无悬停再收起。

## 实现要点
- DOM：`#chatArea` → `#chatBody`（含 `#chatHistory` + `dock` 输入框） + 常驻 `#chatBar` 触发条。
- CSS：`.chat-body` 默认 `max-height:0;opacity:0;pointer-events:none`，`#chatArea.open .chat-body` 展开到 `min(64vh,760px)`，`0.5s cubic-bezier(.16,1,.3,1)` 缓动。
- JS：`revealChat()` / `scheduleCloseChat()` 配合 `isHoveringChat()`、`isTyping()`、`chatPinned` 三重保护。

## 改动文件 / 提交
- `index.html` `styles.css` `app.js`
- 缓存版本 bump：`styles.css?v=20260731f` / `app.js?v=20260731d`
- 提交 `858749e`
- 纯前端改动，不依赖后端；Electron 硬刷新（Ctrl+Shift+R）即生效。

## 验证
- `node --check app.js` 通过；grep 确认旧浮窗 / 旧折叠类名引用全部清零。
- 注：当前环境 browser-use 未安装、本地静态服务器 IPv6 不匹配，未做浏览器实拍；纯前端 hover/click 折叠逻辑已逐项核对。你刷新页面移鼠标到输入框一带即可实测。
