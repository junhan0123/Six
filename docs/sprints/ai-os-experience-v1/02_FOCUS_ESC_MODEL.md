# 02 · Focus & ESC Model（Sprint 2 落地）

## 1. 设计目标（对应 06 §2 Keyboard 集中焦点管理 / 03 §2.6 退出态焦点恢复）

- 全站**单一键盘捕获监听**：`KeyboardManager`（快捷键）+ `OverlayManager`（ESC）。
- 焦点陷阱只在浮层打开时激活；关闭后**焦点恢复到打开前的元素**。
- 浮层打开时背景不可聚焦（可选 `backgroundInert`，默认关以防误伤嵌套面板）。
- 键盘全程可操作（Tab 循环、Enter 触发、方向键导航）。

## 2. FocusManager（`focus-manager.js`，经典脚本，`window.FocusManager`）

| API | 作用 |
|-----|------|
| `trap(container, opts)` | 聚焦入容器；`opts.focusFirst`(默认 true) 移焦点；`opts.backgroundInert`(默认 false) 置背景 inert；注册 capture `keydown` 做 Tab 循环。 |
| `release()` | 注销监听 + `clearBackgroundInert()`。 |
| `isTrapping()` / `current()` | 状态查询（供 OverlayManager 释放时校验）。 |

### backgroundInert 祖先链感知（安全设计）

为避免全局 `inert` 误伤整个应用（尤其浮层可能嵌套在统一包装层内）：
1. 沿 `container.parentElement` 向上到 `body`，对每层**兄弟节点** `setInert(true)`。
2. 对 `body.children` 中非容器祖先者 `setInert(true)`。
3. 仅释放时精确 `clearBackgroundInert()`（记录被置 inert 的集合，仅恢复那些）。

> 默认 `backgroundInert: false`（opt-in）。当前所有外部面板 `track` 均传 `trap:false`，因此默认只做 **Tab 循环 + 焦点恢复**，不置 inert —— 满足"背景不可聚焦"的可操作底线，且零误伤风险。

### FOCUSABLE 选择器

`a[href]` / `button` / `input` / `select` / `textarea` / `[tabindex]` / `[contenteditable]`。

## 3. KeyboardManager（`keyboard-manager.js`，经典脚本，`window.KeyboardManager`）

| API | 作用 |
|-----|------|
| `registerShortcut(combo, fn, opts)` | `combo` 归一化（mod/alt/shift+key）；`priority` 排序；单例 capture `dispatch`。 |
| `registerCommand(fn)` | `registerShortcut('mod+k', fn, { id:'command-palette', priority:1000 })` —— **最高优先级**。 |
| `start()` / `unregister()` | 生命周期。 |

- 单一 `document.addEventListener('keydown', dispatch, true)`。
- Command Palette（`mod+k` / `Ctrl+K`）优先级 1000，高于一切，保证"命令中心"随时可呼起。

## 4. ESC 统一通道（与 OverlayManager 协同）

- 中央 ESC 在 `overlay-manager.js` capture 阶段：栈非空 → 关栈顶并 `stopPropagation`；栈空 → 休眠。
- `command-palette.js` 内部 ESC 直接 `return`（交中央处理）。
- `weather.js`(line 219) 的 ESC 为**输入级**（隐藏城市建议框），保留。
- `index.html` universe / `solar-system.js` 的 ESC 加"浮层优先"守卫：`if (OverlayManager.getStack().length) return;`。

## 5. 焦点恢复链路

```
track(id):
  returnFocus = document.activeElement        // 保存打开者
  applyFocus(entry):
     trap:true → FocusManager.trap(container)   // 陷阱+可选inert
     else if autofocus!=false → focusDialog(container)
close(id):
  releaseFocus(entry)                           // FocusManager.release（若当前陷阱匹配）
  onClose()                                     // 外部：视觉关闭
  stack.splice
  if returnFocus && document.contains(returnFocus) returnFocus.focus()  // 恢复
```

## 6. 可操作性与优先级验证点

- ✅ 单一键盘捕获监听（无重复 `keydown` 快捷键散落；既有全局快捷键仍走 `app.js` 旧监听，列为后续可迁 KeyboardManager 的改进项，超出本 Sprint ESC 范围）。
- ✅ Command Palette 最高优先级（`mod+k` 即时呼起，不被其他快捷键拦截）。
- ✅ Tab 在浮层内循环；ESC 关栈顶；关闭后焦点回打开者。
- ✅ 背景不可聚焦（默认 Tab 循环兜底；opt-in inert 待后续按需开启）。
