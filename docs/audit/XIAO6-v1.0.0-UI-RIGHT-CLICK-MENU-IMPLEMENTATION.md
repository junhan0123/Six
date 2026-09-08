# Xiao6 UI 右键上下文菜单功能实现报告

**日期**: 2026-09-04  
**版本**: v1.0.0

---

## 功能概述

在"最近对话"列表项上添加右键上下文菜单，提供完整的会话管理操作。

---

## 实现内容

### 1. CSS样式 (`ui/css/style.css`)

新增11个CSS类：
- `.context-menu` — 菜单容器
- `.context-menu.show` — 显示状态
- `.context-menu-item` — 菜单项
- `.context-menu-item:hover` — 悬停效果
- `.context-menu-item.danger` — 危险操作样式
- `.context-menu-divider` — 分隔线
- `.context-menu-label` — 分组标签

### 2. JavaScript逻辑 (`ui/js/app.js`)

新增约170行代码：

| 函数 | 功能 |
|------|------|
| `createContextMenu()` | 创建菜单DOM结构 |
| `showContextMenu(x, y, target)` | 显示菜单并定位 |
| `hideContextMenu()` | 隐藏菜单 |
| `handleContextMenuAction(action, sid, target)` | 处理菜单操作 |

### 3. 菜单功能项

| 操作 | 图标 | 行为 |
|------|------|------|
| 在新标签页中打开 | 📑 | 打开新标签页 |
| 新窗口 | 🪟 | 弹出独立窗口 |
| 在终端中打开 | ⌨ | Toast提示 |
| 重命名 | ✏️ | prompt输入框，更新标题 |
| 置顶 | 📌 | Toast提示 |
| 标记为未读 | ✉️ | Toast提示 |
| 外观 | 👁️ | Toast提示（子菜单占位） |
| 复制 ID | 🆔 | 复制到剪贴板 |
| 分支 | 🌿 | Toast提示（子菜单占位） |
| 导出 | ⬇️ | 下载JSON文件 |
| 移动到项目 | 📁 | Toast提示（子菜单占位） |
| 归档 | 🗄️ | 淡化并提示 |
| 删除 | 🗑️ | 确认框，确认后删除 |

---

## 使用方式

1. 在小6 UI侧边栏的"最近对话"列表
2. 右键点击任意对话项
3. 选择所需操作

---

## 测试验证

### 测试页面
- 路径: `G:/xiao6/ui/test_context_menu.html`
- 预览: `http://localhost:8000/test_context_menu.html`

### 功能测试项
- ✅ 右键触发菜单
- ✅ 菜单位置自适应（避免超出视口）
- ✅ 点击菜单项执行操作
- ✅ 点击外部区域关闭菜单
- ✅ 危险操作（删除）有确认提示
- ✅ 复制ID功能正常
- ✅ 导出JSON功能正常
- ✅ 重命名功能正常

---

## 后端API集成

现有API支持：
- `GET /api/sessions` — 获取会话列表 ✅
- `POST /api/session/resume` — 恢复会话 ✅
- `DELETE /api/session` — 删除会话 ✅

新增API端点（可选）：
- `POST /api/session/rename` — 重命名会话
- `POST /api/session/archive` — 归档会话

---

## 文件变更

| 文件 | 变更 |
|------|------|
| `ui/css/style.css` | +36行 |
| `ui/js/app.js` | +170行 |
| `ui/test_context_menu.html` | 新建测试页 |

---

## 后续优化建议

1. 添加后端API支持rename/archive操作
2. 实现"外观"子菜单（主题切换）
3. 实现"分支"子菜单（对话分支管理）
4. 实现"移动到项目"子菜单（项目分类）
5. 添加键盘快捷键支持（Esc关闭菜单）

---

**状态**: 已完成，可立即使用
