# 04 · Command Palette Spec（Sprint 4 落地）

## 1. 设计目标（对应 06 §Command Palette 唯一 / 03_ENTRY_MAP §CP 唯一 / 07 §信息架构）

Command Palette 升格为 **AI OS Command Center**：唯一全局命令入口，键盘优先，整合
搜索 / 命令执行 / 最近命令 / 能力搜索 / 页面跳转。

## 2. 唯一开关（与 OverlayManager 协同）

- 打开：`KeyboardManager.registerCommand(() => openCp/closeCp)`（`mod+k`，优先级 1000）。
- 打开后 `OverlayManager.track('command-palette', { el: ov, onClose: closeCpImpl, type: COMMAND, trap:true, keepZIndex:true })`。
- 关闭：经 `OverlayManager.close('command-palette')`（ESC 由中央处理，palette 内 ESC `return`）。
- 单一 `openCp/closeCp` 入口，杜绝多实例。

## 3. 能力

| 能力 | 实现 |
|------|------|
| 全局快捷键 | `mod+k` 最高优先级呼起 |
| 模糊搜索 | 输入即过滤命令 + 能力 |
| 命令执行 | 回车执行选中命令（页面跳转 / 触发能力 / 打开面板） |
| 最近命令 | `RECENT_KEY='zz.cp.recent'` localStorage，最多 5 条；自然语言意图不计入 |
| 能力搜索 | 从 `CapabilityExposure.computerMap()` 派生，带 T 档 + 成熟度 badge |
| 页面跳转 | 各页面/面板入口统一经命令中心 |
| 状态标签 | 每条命令 `category` + `T0..T4 · beta/exp` badge |

### 命令分类（CAT_ORDER）

`recent`（置顶）→ External / System / Proactive / Knowledge / Memory / Settings / Goals / UI。

## 4. badge 渲染

```js
const tag = window.CapabilityExposure.tag({ category, maturity });
// → <span class="cp-badge cp-badge--T0..T4 (--beta/--exp)">T0·beta</span>
```
样式令牌见 `styles.css`（`.cp-badge` 系列：绿/蓝/紫/灰/红 + beta/exp 底色）。

## 5. FEATURE_META

`FEATURE_MULTI_DEVICE: exp`，其余 `prod` —— 诚实标注多设备能力为实验。

## 6. 验证点

- ✅ 唯一命令中心：`mod+k` 单一入口，经 OverlayManager 开关。
- ✅ 键盘优先：全键盘可操作（上下选择、回车执行、ESC 关闭）。
- ✅ 模糊搜索：输入过滤命令 + 能力。
- ✅ 最近命令：localStorage 持久化，5 条上限，自然语言意图排除。
- ✅ 能力状态标签：T0–T4 + beta/exp 诚实展示。
- ✅ 页面跳转：所有面板/页面入口统一经命令中心（不再各自散落快捷键）。
