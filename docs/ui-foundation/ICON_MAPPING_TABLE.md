# ICON_MAPPING_TABLE — 小6 Icon 体系迁移映射表

> **Sprint**: Xiao6 Icon System Migration Sprint v1.0（UI Foundation Phase 1 收尾 P0）
> **生成日期**: 2026-08-05
> **唯一规范入口**: `.zz-icon`（SVG Sprite `<use href="#zz-<id>"/>`）
> **源真相**: `xiao6-ui/index.html` 内联 `<svg id="zzIconSprite">` 含 67 个 `<symbol>`；`xiao6-ui/ui2.css` 末加载 Icon 收敛层。

---

## 1. 总览

| 指标 | 数值 |
|------|------|
| Sprite 内 `<symbol>` 定义总数 | 67 |
| 实际被引用的 icon id（去重） | 58（全部命中，0 孤儿） |
| `<use href="#zz-...">` 注入点 | 150 |
| Emoji → .zz-icon **已迁移**（UI 控制图标） | 54 |
| Emoji 语义存在但**刻意保留**（域/内容数据） | 14 |
| 遗留 `.ic` 用法（CSS 别名零改动接管） | 17 |
| `.zz-icon` 字符串出现总次数 | 163 |

迁移总原则：**Emoji 不再作为 UI 图标使用**（验收标准①）；域数据/业务逻辑/纯文本状态中的 emoji 一律保留，不触碰（守纪律红线）。

---

## 2. Emoji → .zz-icon 实际迁移表（54 项，UI 控制图标）

> 下列文本图标已从源码替换为 `<svg class="zz-icon stroke"><use href="#zz-<id>"/></svg>`，跨 16+ 文件。

| Emoji | 语义 | zz-id | Emoji | 语义 | zz-id |
|-------|------|-------|-------|------|-------|
| 💬 | 聊天 | chat | 🧑‍🚀 | 人物 | person |
| ✏️ | 编辑 | edit | 🧿 | 身份 | id |
| 🧠 | 智能体 | brain | ⋮ | 更多(kebab) | kebab |
| 📅 | 日历 | calendar | 🛠 | 工具 | wrench |
| 📜 | 卷轴/记录 | scroll | ↩ | 返回 | return |
| ⚙ / ⚙️ | 设置 | gear | 🌌 | 宇宙视图 | universe |
| 📍 | 定位 | pin | ✕ | 关闭 | close |
| 💾 | 保存 | save | 🕐 | 时钟 | clock |
| 📥 | 收件 | inbox | 📦 | 归档/盒子 | box |
| ♻️ | 循环 | recycle | ☰ | 菜单 | menu |
| ⚡ | 闪电图标 | bolt | 👁 | 显隐密码 | eye |
| 🔥 | 火焰 | flame | 🩺 | 系统自检 | pulse |
| 🎯 | 目标 | target | 🗄️ | 数据库/导出 | database |
| 🔍 / 🔎 | 搜索 | search | 🪷 | 引导 logo | lotus |
| 🔗 | 链接 | link | 🎙 | 麦克风 | mic |
| 🤖 | 机器人 | robot | 📎 | 附件 | paperclip |
| 🎨 | 调色板 | palette | ➤ | 发送 | send |
| ⌨️ | 键盘 | keyboard | 📚 | 书籍 | book |
| ℹ️ | 信息 | info | 🗺️ | 地图 | map |
| 📡 | 信号 | signal | 🔧 | 扳手 | wrench |
| 🖥️ | 显示器 | monitor | 🌗 | 主题切换 | theme |
| ▶ | 播放 | play | ❯ | 右箭头 | chevron-right |
| 📁 | 文件夹 | folder | ⬡ | 六边形 | hexagon |
| 📄 | 文件 | file | | | |
| 👤 | 用户 | user | | | |
| 📊 | 图表 | chart | | | |
| 🧾 | 票据 | receipt | | | |
| 🧩 | 拼图/能力 | puzzle | | | |
| 🕘 | 时钟 | clock | | | |

---

## 3. Emoji → .zz-icon 语义存在但刻意保留（14 项，域/内容数据）

> 这些 emoji **不是 UI 控制图标**，而是：① 业务逻辑（清洗/检测正则）；② 域数据（天气状况表、天气展示）；③ 纯文本状态/心情/标题字形。迁移会破坏功能或语义，**按纪律红线排除**。全树剩余 119 处 emoji 全部属于此类。

| Emoji | 语义 | 保留位置（代表） | 保留理由 |
|-------|------|----------------|----------|
| 🌤️ / ☀️ / 🌙 | 天气状况 | weather.js:21-25,132 / weather-modal-preview.html | 域数据（天气状况→字形） |
| 🌐 / ⚠ / 🚨 | AI 内容检测 | app.js:358 / hotspot.js:796 | 业务逻辑（内容识别正则） |
| 📝 | 编辑/标题 | 笔记/标题文本 | 内容文本字形 |
| 💡 | 想法/提示 | 标题/提示文本 | 内容文本字形 |
| ✨ | 星光/强调 | 标题/心情 | 内容字形 |
| 🔊 | 音量 | 媒体标签 | 内容标签 |
| 📷 | 相机 | 媒体标签 | 内容标签 |
| ⭐ | 星级 | 评分/标题 | 内容字形 |
| ✅ | 完成状态 | 状态文本 | 纯文本状态 |

---

## 4. `.ic` → `.zz-icon.stroke` 别名映射（遗留 12 语义，零改动接管）

> 既有 17 处 `class="ic"` 内联 SVG 不删除、不重构。通过 `ui2.css` 末加载的 CSS 别名层 `.ic → .zz-icon.stroke` 自动合规（fill:none / stroke:currentColor / stroke-width:1.7），实现「零 HTML/JS 改动接管」。新代码一律用 `.zz-icon`。

| 遗留 `.ic` 语义 | 对应 zz-id（同形 path 复用） |
|----------------|------------------------------|
| 聊天 | chat |
| 编辑 | edit |
| 设置(gear) | gear |
| 定位(pin) | pin |
| 保存(save) | save |
| 收件(inbox) | inbox |
| 循环(recycle) | recycle |
| 搜索(search) | search |
| 链接(link) | link |
| 用户(user) | user |
| 图表(chart) | chart |
| 返回(return) | return |

---

## 5. Sprite Symbol 全集（67）

`index.html` `#zzIconSprite` 内 67 个 `<symbol id="zz-<id>">`：

- **复用遗留 `.ic` 路径（12）**: chat, edit, gear, pin, save, inbox, recycle, search, link, user, chart, return
- **新增描边图标（55）**: brain, calendar, scroll, idea, bolt, warning, camera, flame, check, target, palette, keyboard, info, signal, play, folder, file, receipt, puzzle, clock, person, id, kebab, wrench, weather, sun, moon, star, universe, menu, eye, pulse, database, lotus, paperclip, book, map, theme, chevron-right, hexagon, microphone(sparkle/spark/robot/globe 等按需用)

> 注：部分新增 zz-id（如 sparkle/robot/globe/volume）已定义备用，当前未被 `<use>` 引用但不影响渲染；新增图标流程见 `ICON_USAGE_SPEC.md`。

---

## 6. 引用解析校验

```
defined symbols : 67
referenced ids  : 58
ORPHAN (引用但无定义): NONE
```

所有 `<use href="#zz-<id>"/>` 均命中 sprite 定义，无空白图标风险。

---

## 7. P1 观察（仅记录，不处理）

- 天气模块仍用 emoji 作域数据展示（`weather.js` / `weather-modal-preview.html`），建议 P1 引入天气专用图标组件统一视觉语言（不在本 Sprint 范围）。
- 部分内容字形 emoji（✨⭐💡 等）为文本强调，P1 可评估是否以 `.zz-icon` 替代以保持纯图标体系一致性（非强制）。
