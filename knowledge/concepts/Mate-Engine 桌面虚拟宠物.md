---
id: know-mate-engine
type: concept
---
# Mate-Engine — 桌面虚拟宠物

## 基本信息

- **GitHub**：shinyflvre/Mate-Engine
- **Stars**：3466 · Forks：290
- **License**：混合协议（GNU AGPL v3 + MateProv2 License）
- **创建时间**：2025-03-20
- **语言**：ShaderLab（Unity 项目）
- **Steam 版**：[Mate Engine](https://store.steampowered.com/app/3625270/MateEngine/)（$3.99，GitHub 永久免费）
- **Linux 移植版**：Marksonthegamer/Mate-Engine-Linux-Port（280 stars）

## 核心定位

免费、轻量、开源的 Desktop Mate 替代品，支持自定义 VRM 虚拟角色和模组。

**为什么诞生**：
- Desktop Mate 收费 $10-25 买一个角色模型，价格堪比 Steam 游戏
- 后期版本禁用了模组和自定义模型
- Mate-Engine 解决了两个问题：**完全免费** + **支持自定义 VRM 角色** + **开源可模组化**

## 核心功能

### 基础交互
- **窗口坐落**：虚拟角色可以坐在窗口边缘
- **任务栏坐落**：可以坐在任务栏上
- **拖拽动画**：拖拽角色时有互动动画
- **待机动画**：空闲状态自动播放
- **头部追踪**：角色眼睛跟随鼠标/屏幕
- **脊柱追踪**
- **眼部追踪**
- **手部动作**
- **触摸区域**：可设置不同触摸部位的反应
- **角色音效**：触摸/互动时有音效

### 高级功能
- **舞蹈动画**：跟随音乐跳舞
- **屏幕保护**
- **粒子效果**
- **后处理**：Bloom / AO
- **Chibi 模式**（Q 版切换）
- **大屏模式**
- **最多同时 9 个角色**
- **角色间舞蹈同步**
- **Minecraft 集成**
- **食物系统**
- **Discord Rich Presence**
- **反作弊安全**（游戏内可用）
- **开机自启**
- **睡眠模式**

### AI 功能
- **AI 对话**：内置 AI 聊天
- **高级 AI 功能**
- **Markdown 支持**
- **AI API 接口**
- 支持接入 Qwen 2.5 1.5b 等模型

### 模组支持
- **自定义 VRM 模型**
- **自定义 Shader**
- **.ME 文件格式**（自定义模组格式）
- **内置 SDK**
- **动画模组**
- **Steam Workshop**（Steam 版专属）
- **事件消息**（拖拽/跳舞/坐任务栏时生成可爱消息）

## 与竞品对比

| 功能 | Desktop Mate | Phase Pal | Mate-Engine |
|------|:---:|:---:|:---:|
| 开源 | ❌ | ❌ | ✅ |
| 模组支持 | ❌ | ❌ | ✅ |
| 自定义 VRM | ❌ | ✅ | ✅ |
| 自定义 Shader | ❌ | ❌ | ✅ |
| 舞蹈动画 | ❌ | ❌ | ✅ |
| 脊柱/眼部追踪 | ❌ | ❌ | ✅ |
| 屏幕保护 | ❌ | ❌ | ✅ |
| Minecraft 集成 | ❌ | ❌ | ✅ |
| 反作弊安全 | ❌ | ❌ | ✅ |
| Steam Workshop | ❌ | ✅ | ✅ |
| AI 对话 | ❌ | ✅ | ✅ |
| 内存占用 | 中等 | 很差 | 很好 |
| CPU/GPU 占用 | 中等 | 好 | 很好 |

## 商业模式

- **GitHub 下载**：完全免费
- **Steam 版**：$3.99（买断制），独占内容：
  - 专属配饰（花环、樱花光环等）
  - 事件消息系统
  - Steam Workshop 支持
  - 自动更新
- **开发目标**：$100（已达成 $239.34）

## 注意事项

1. **Windows 桌面端**（主要平台），Linux 有非官方移植版
2. **Unity 项目**，源码可编译
3. **默认角色**：Yorshka Shop 版权，不可再分发
4. **免费初音未来 VRM** 可下载体验：[booth.pm](https://booth.pm/en/items/3226395)
5. 性能优秀：高质量模型约 200MB 内存占用

## 相关笔记

- [[ToolKnit — 多功能工具箱]]
- AI 工具调研
