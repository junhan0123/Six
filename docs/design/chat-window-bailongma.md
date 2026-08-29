# 小6聊天窗口：对齐白龙马交互

## 问题
上一轮把聊天消息流做成了「右侧独立浮窗 hover 滑出」，与白龙马真实交互不符。用户纠正：「不对，参考白龙马」。

## 白龙马真实范式（源自 `src/ui/brain-ui/chat.js`）
- 聊天区（输入坞）本身常驻在主界面；对话历史 `#chat-history` 默认 `max-height:0` 折叠隐藏。
- 鼠标 **enter 聊天区 → 展开历史**；**leave → 延迟收起**。
- `isHoveringChat()` 防抖（鼠标其实还在上面时不误关）、**流式输出期间不收起**、点击聊天区外收起。

## 本次改造（提交 `d181f3e`）
- **index.html**：删除右侧 `#chatPanel` / `#chatTrigger`；把 `#messages` 包回主区并置入 `#chatArea`（内含折叠的 `#chatHistory` + 常驻的底部 `dock` 输入坞）。
- **styles.css**：删除旧浮窗样式；新增 `.chat-area`（卡片容器）+ `.chat-history`（`max-height:0` 折叠 + `0.62s` 过渡，`.open` 展开到 `min(62vh,720px)`）；`dock` 去掉重复边框（由外层 `chat-area` 统一提供）。
- **app.js**：换成白龙马式 hover 逻辑（`chatArea` 的 `mouseenter`/`mouseleave` + `document.pointerdown` 外部收起 + `state.streaming` 流式保护）；`addMessage` 与 `send()` 结束时触发「自动展开，闲置数秒无悬停则收起」。

## 使用方式
Electron 刷新页面即可：平时只见底部输入坞 + 中央语音球；**鼠标移到聊天区（输入框一带）对话历史平滑展开，移开约 0.8s 收起**；对话中或有新消息时自动展开并保持，停下数秒后自动隐藏。

## 缓存版本
- `styles.css?v=20260731e` · `app.js?v=20260731d`
