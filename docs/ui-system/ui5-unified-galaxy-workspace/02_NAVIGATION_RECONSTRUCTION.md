# UI-5 · Navigation Reconstruction — Capability Focus（02_NAVIGATION_RECONSTRUCTION.md）

> 阶段：UI-5 · Design（仅设计，零代码改动）
> 设计原则：④ Navigation = Capability Focus（不切页）
> 输入：00_AUDIT.md 三、Q3（左导航 6 按钮，3/6 整页切换）

---

## 一、当前导航问题（审计 Q3）

左导航脊柱 `index.html:81-92`（brand `home` + 5 `os-nav-btn`），处理器 `index.html:1505-1526`，高亮由 `syncNav()`（index.html:1495-1504）单一推导。

**问题核心**：6 按钮中有 **3/6**（`workspace`/`assistant`/`galaxy`）触发**整页切换式旧页面**，直接造成「像多个产品」的体感：

| 按钮 | data-nav | 当前行为 | 是否换页 |
|---|---|---|---|
| 小6徽标 | home | 回首页（关 chat/universe/settings/palette） | 否 |
| 工作台 | workspace | `closeUniverse(); openChat()` → chat-mode 全页 | **是** |
| 指令中心 | command | `ZZCommandPalette.open()` | 否（浮层） |
| 星图 | galaxy | `closeChat(); openUniverse()` → universe-mode 全页 | **是** |
| 语音助理 | assistant | `closeUniverse(); openChat(); navVoice=true` + `zz:voice-toggle` | **是** |
| 设置 | settings | `ZZSettings.open()` | 否（浮层） |

首屏 Hero 3 芯片（index.html:128-130：对话/指令/星图）与左导航同源，进一步固化「对话=聊天页」「星图=宇宙页」的双页心智。

---

## 二、新导航语义（Navigation = Capability Focus）

> 导航按钮不再「打开一个页面」，而是「在统一空间里调整焦点（Focus）」。空间永远只有一个，按钮只改变哪一层被推到前台、哪一层被推后。

焦点语义映射到**既有 `body` 类体系**（不新增第二套状态，`syncNav` 单一推导）：

| 焦点态 | body 类（推荐） | 含义 |
|---|---|---|
| 默认/世界 | （无特殊类） | World + Operation 同屏 |
| Galaxy Focus | `zz-galaxy-focus` | World 推前，Operation 推后（替代 `universe-mode`） |
| Command Palette | `cp-mode`（既有） | 浮层，不切页 |
| Settings | `settings-open`（既有） | 浮层，不切页 |
| Voice | `zz-voice`（可选中性类） | 派 `zz:voice-toggle`，不切页 |

> **关键**：`universe-mode` 是「换页类」（ui2.css:933-934 会隐藏 osShell/#app），必须废止，改用中性 `zz-galaxy-focus`（仅控制 World/Operation 焦点与 gx-* 显隐，不隐藏任一层）。

---

## 三、六按钮重释（Capability Focus 模型）

| 按钮 | 新焦点行为（目标态） | 不再做的事 |
|---|---|---|
| 小6徽标 `home` | **Defocus / World Reset**：移除所有焦点类，`syncNav` 归 `home` | 不变（本就不换页） |
| 工作台 `workspace` | **Focus Intent Entry**：聚焦 Command Dock（Global AI Intent Entry），必要时展开 Conversation Panel | 不再 `openChat()` 全页切换 |
| 指令中心 `command` | 打开 Command Palette 浮层（`cp-mode`） | 不变 |
| 星图 `galaxy` | **World Focus**：切换 `zz-galaxy-focus`，显隐 `gx-*` 浮在活 Galaxy 上，os-shell 保留 | 不再 `openUniverse()` 换页 |
| 语音助理 `assistant` | 派 `zz:voice-toggle`（启动/停止语音），必要加 `zz-voice` 中性类 | 不再 `openChat()` 换页 |
| 设置 `settings` | 打开 Settings 浮层 | 不变 |

`syncNav()`（index.html:1495-1504）推导逻辑相应更新：把 `universe-mode` 分支改为 `zz-galaxy-focus` → `galaxy`；`chat-mode` 分支因 `chat-mode` 页切换废止而移除（对话进入由 Command Dock 驱动，不再有独立 `chat-mode` 页态）。

---

## 四、Capability Focus 模型（状态推导）

沿用既有纪律（index.html:1486-1504 注释）：**仅切换既有 body 类 / 调用既有入口，不新建状态、不写运行时**。

- 单一真相：当前焦点 = `body` 上唯一激活的「焦点类」（`zz-galaxy-focus` / `cp-mode` / `settings-open` / `zz-voice` 之一或无）。
- 高亮：`syncNav()` 遍历 `[data-nav]`，按焦点类匹配 `active`。
- 互斥：`home` 点击清除所有焦点类（归默认）。
- **不引入** AppState 写操作 / 新 EventBus 事件 / 新全局变量。

---

## 五、键盘 / 快捷键映射（保持既有）

| 快捷键 | 当前 | 目标态 |
|---|---|---|
| Ctrl/⌘+U | toggle `universe-mode` | toggle `zz-galaxy-focus`（Galaxy Focus，不换页） |
| Ctrl/⌘+K | Command Palette（`cp-mode`） | 不变 |
| Ctrl/⌘+, | Settings | 不变 |
| Esc | universe/chat 退出 | 退出当前 Focus（如 `zz-galaxy-focus` 或浮层），无 Focus 时回默认 |

---

## 六、Hero 芯片重释

`index.html:128-130` 三芯片改为与左导航同语义、**不换页**：
- `对话` → Focus Command Dock（意图入口），不再 `data-nav="workspace"` 换页。
- `指令` → Command Palette（不变）。
- `星图` → `zz-galaxy-focus`（World Focus），不再 `data-nav="galaxy"` 换页。

消除「对话=聊天页」「星图=宇宙页」心智，统一为「在空间中聚焦」。

---

## 七、红线符合性

| 红线 | 满足 |
|---|---|
| 不修改 Backend / Agent / AppState / EventBus | ✅ 仅导航 JS 路由 + body 类语义 |
| 不新增事件 | ✅ 复用 `zz:voice-toggle`；新 `zz-galaxy-focus`/`zz-voice` 为 body 类（状态类，非事件） |
| 不新增第二套状态 | ✅ 沿用 body 类 + syncNav 单一推导 |
| 保护 AI Presence 三唯一 | ✅ 只消费 `body[data-presence]` |
| 第一屏 1/5/30s | ✅ 导航不再把用户赶出空间 |

---

> ▣ **STOP — 本阶段为 Design Only，未修改任何代码。等待 Review 与 Implement 放行。**
