---
created: 2026-08-03
tags:
  - AI/角色设计
  - 小6
  - Avatar
  - 设计规范
id: know-xiao6-avatar-design-specification-v1-0
type: concept
---
# Xiao6 Avatar Design Specification v1.0

## 1. 角色定位

### 名称

**小6（Xiao6）**

**定位**：

> 一个陪伴用户工作的本地 AI 操作系统化身。

**不是**：

- 宠物
- 女仆
- 虚拟偶像
- 聊天机器人

**是**：

- AI 副驾
- 智能伙伴
- 系统意识体

---

## 2. 核心关键词

### 生成时固定

```
东方哲学
未来科技
AI 意识体
银河
微型智能生命
安静
可靠
高级感
```

### 避免

```
萌宠
幼儿化
过度二次元
赛博朋克暴力风
机器人脸
```

---

## 3. 外观方向

### 推荐方向：「东方未来 AI 精灵」

**参考感觉**：

不是人类。不是机器人。像"银河中的一个智能生命体"。

### 身体比例

```
头 : 身体 = 1 : 1.2
```

**特点**：

- 大头
- 小身体
- 悬浮

**适合**：桌宠窗口

---

## 4. 视觉元素

### 头部

**核心**：智能核心

**设计**：

- 半透明头环
- 微型银河纹路
- 光环

**不要**：

- 猫耳
- 兽耳
- 传统萌元素

### 眼睛

**要求**：有生命感

**颜色**：

- 主：青蓝色
- 辅助：紫色星光

**表现**：像 AI 正在思考

### 身体

**材质**：未来东方服饰

**推荐**：

```
未来道袍 + 科技纹理 + 轻量机械结构
```

**原因**：名字"小6"，保留东方文化

### 胸口

**设计**：AI 核心

**类似**：能源核心

**内部**：银河旋转

---

## 5. 状态动作设计

桌宠必须有状态动画。

### Idle 空闲

**动作**：漂浮、轻微呼吸、星光流动

### Listening 聆听

**动作**：靠近用户、眼睛亮起

### Thinking 思考

**动作**：头微低、银河核心旋转

### Working 执行

**动作**：周围出现数据流、代码粒子

### Success 成功

**动作**：微笑、光环展开

### Error 错误

**动作**：颜色降低、出现提示符号

### Sleep 休眠

**动作**：进入休眠球

---

## 6. 必备素材清单

第一次生成不要只生成一张。

### 基础立绘

```
Front View
Full Body
Transparent Background
```

### 表情（至少 7 种）

```
Normal
Happy
Thinking
Focused
Confused
Error
Sleep
```

### 动作（至少 5 种）

```
Idle
Listening
Thinking
Working
Success
```

### 分层要求（为 Live2D 准备）

```
PSD Layer
├── Head
├── Hair
├── Face
├── Eyes
├── Mouth
├── Body
├── Clothes
├── Effects
└── Core
```

---

## 7. 推荐生成平台

### 第一选择：Midjourney

**适合**：角色设计稿

**优势**：

- 角色一致性强
- 高质量概念设计

**生成**：先做角色设计，不要直接要求动画

### 第二选择：OpenAI 图片生成

**适合**：快速迭代

**优势**：

- 中文理解好
- 修改方便

### 第三选择：专业角色资产

如果以后做 Live2D：

**nizima**：买 Live2D 模型

**BOOTH**：搜索 `Live2D model AI assistant mascot character PSD`

### 第四选择：3D 路线

如果以后想做真正桌面陪伴：

**VRoid Hub**：生成 VRM 模型

---

## 8. 第一版生成 Prompt

可以直接丢给图片模型：

```
Design a mascot avatar for an AI operating system called Xiao6.

A small floating AI lifeform inspired by Chinese philosophy and galaxy.

Style:
premium futuristic oriental sci-fi,
clean anime style,
not childish,
not a robot,
not a pet.

Character:
small intelligent companion,
floating body,
transparent holographic robe,
cyan and purple galaxy energy core,
soft glowing eyes,
subtle cosmic patterns,
calm and wise expression.

Design requirements:
front view,
full body,
transparent background,
character design sheet,
professional game character concept art,
high quality,
consistent silhouette.

Need:
idle pose,
thinking pose,
working pose,
listening pose.
```

---

## 9. 最终形象方向建议

**80% 东方 AI 智者 + 20% 银河生命体**

**不要做**："小助手机器人"

**因为项目定位已经不是 App，而是**：

> Personal AI Operating System

**角色应该像**："操作系统里的意识"

---

## 10. 生成顺序

1. Midjourney / 图片生成 → 定角色
2. 确定三视图
3. PSD 分层
4. Live2D / Sprite 动画
5. Electron 桌宠接入

**不要反过来。先定 IP，再做技术。**

---

## 相关笔记

- 小6 - 项目架构
- 技术决策 - 自研 AI 智能体平台
- [[Dify - 开源 LLM 应用开发平台]]
