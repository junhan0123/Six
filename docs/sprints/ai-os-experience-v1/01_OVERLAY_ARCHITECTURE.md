# 01 · Overlay Architecture（Sprint 1 落地）

## 1. 设计目标（对应 06 §统一通道 / 03_ENTRY_MAP §Overlay 重复）

消灭全站 ~12+ 散落浮层与 ~18 处去中心化 ESC 监听，建立**唯一浮层栈** `OverlayManager`，由它统一掌管：

- 打开栈（stack）与多实例 z-index 递增
- 中央 ESC（capture 阶段，仅栈非空时拦截，仅关栈顶）
- 焦点保存 / 恢复（委托 FocusManager）
- 关闭顺序（栈顶优先，多开顺序关）

## 2. 核心 API（`overlay-manager.js`）

| API | 作用 |
|-----|------|
| `OverlayManager.track(id, opts)` | 外部浮层登记：`{ el, dialog, onClose, type, trap, autofocus, backgroundInert, keepZIndex }`。面板保留自身 DOM，仅把 ESC/焦点/栈/z-index 交给 Manager。 |
| `OverlayManager.untrack(id)` | 注销（幂等）。 |
| `OverlayManager.close(id)` | 外部浮层：调用 `onClose()`（不移除 DOM）+ 弹栈 + 恢复焦点。 |
| `OverlayManager.closeTop()` | 关闭栈顶。 |
| `OverlayManager.isOpen(id)` | 是否在栈中。 |
| `OverlayManager.getStack()` | 调试：`[{id, type, external}]`。 |
| `OverlayManager.OverlayType` | `MODAL / PANEL / DIALOG / COMMAND / MENU / NOTIFICATION` 枚举（单一来源）。 |
| `OverlayManager.toast(...)` | 统一 Toast（Step[3]，令牌驱动，非本 Sprint 范围但同文件）。 |

### z-index 单一来源

- `BASE_Z` 运行时读取 CSS 令牌 `--z-dialog-mask`（Step[1]），避免第二套数值。
- 普通浮层：`el.style.zIndex = BASE_Z + stack.length * Z_STEP`（每深一层 +1）。
- `keepZIndex: true`：保留面板自身高位（如 `modal-mask` 9000、`command-palette` 90），不被降级。

## 3. 中央 ESC 模型

```
onKeydown(e):
  if e.key != 'Escape' return
  if stack.length == 0 return          // 休眠：零键盘影响，遗留 ESC 照常
  top = stack[stack.length-1]
  if top.opts.onEsc === false return   // 允许特定浮层禁用 ESC
  e.preventDefault(); e.stopPropagation()   // 阻止遗留监听误触
  close(top.id)                          // 仅关栈顶
```

- 监听器在 `track` 时 `ensureEsc()`（capture 注册一次），栈空时 `releaseEsc()`（休眠）。
- `stopPropagation` 保证：当浮层打开时，遗留 ESC 监听（universe / solar-system / weather 输入级）不会误触；universe 与 solar-system 另加"浮层优先"守卫。

## 4. 迁移模式（既有面板统一接入）

```js
function open() {
  overlay.classList.add('show'); panel.classList.add('open');
  if (window.OverlayManager) window.OverlayManager.track('id', {
    el: panel, onClose: closeImpl,
    type: window.OverlayManager.OverlayType.PANEL,
    trap: false, autofocus: false   // 保持原无陷阱/无自动抢焦点行为
  });
}
function closeImpl() { overlay.classList.remove('show'); panel.classList.remove('open'); }
function close() {
  if (window.OverlayManager && window.OverlayManager.isOpen('id'))
    window.OverlayManager.close('id'); else closeImpl();
}
// 删除原 document.addEventListener('keydown', Escape) 监听
```

高位浮层（`modal-mask` / `command-palette`）用 `trap:true, keepZIndex:true` + `type: MODAL/COMMAND`。

## 5. 已接入浮层清单（共 20 个外部浮层 + 中央 Toast）

| id | 文件 | type | keepZ | 说明 |
|----|------|------|-------|------|
| capabilities-view | capabilities-view.js | PANEL | — | 能力清单 |
| modal-mask | app.js | MODAL | ✅ | 强制聚焦确认/详情 |
| briefing | app.js | PANEL | — | 晨起简报 |
| zz-panel | app.js | PANEL | — | 右侧信息面板 |
| command-palette | command-palette.js | COMMAND | ✅ | AI OS 命令中心 |
| companion-bubble | companion.js | MENU | ✅ | AI 建议气泡 |
| companion-menu | companion.js | MENU | ✅ | 伴侣菜单（已收口为 AI 项） |
| companion-cmdBubble | companion.js | MENU | ✅ | 就地下达指令 |
| doc | doc.js | PANEL | — | 文档 |
| hotspot | hotspot.js | PANEL | — | 热点模式 |
| hotspot-region | hotspot.js | DIALOG | — | 地域弹窗（嵌套，栈顶优先） |
| map | map.js | PANEL | — | 态势地图 |
| memory-panel | memory-panel.js | PANEL | — | AI 记忆面板 |
| jz-memory | memory.js | PANEL | — | 笔记图谱（原 id `memory`，因与 memory-panel 冲突改名 `jz-memory`） |
| memory-query | memory-query.js | PANEL | — | 记忆检索 |
| review | review.js | PANEL | — | 复盘 |
| settings | settings.js | PANEL | — | 设置 |
| sysprompt | sysprompt.js | PANEL | — | 系统提示词 |
| zz-task | tasks.js | PANEL | — | 科技感任务弹窗 |
| video | video.js | PANEL | — | 视频 |

## 6. 验证点

- ✅ 多开顺序关：栈后进先出，ESC 连续按依次关栈顶。
- ✅ ESC 只关栈顶：中央 `close(stack[len-1].id)`。
- ✅ 焦点返回：每个 `track` 保存 `document.activeElement`，`close` 时恢复。
- ✅ 嵌套浮层：`hotspot`(PANEL) 之下 `hotspot-region`(DIALOG) 后开 → ESC 先关 region 再关 hotspot。
- ✅ id 冲突修复：`memory`(memory-panel) 与 `jz-memory`(memory.js) 已区分。
