---
id: know-bitchat-mesh
type: concept
---
# Bitchat — 去中心化蓝牙 Mesh 聊天应用

> **归档日期：** 2026-08-11
> **来源：** https://github.com/permissionlesstech/bitchat
> **标签：** #去中心化 #蓝牙Mesh #隐私 #Nostr #开源

## 项目信息

- **仓库：** [permissionlesstech/bitchat](https://github.com/permissionlesstech/bitchat)（iOS 版）
- **Android 版：** [permissionlesstech/bitchat-android](https://github.com/permissionlesstech/bitchat-android)
- **创始人：** Jack Dorsey（Twitter 联合创始人）
- **发布时间：** 2025 年 7 月
- **许可证：** 公有领域（Public Domain）

## 是什么

Bitchat 是一个**去中心化的点对点聊天应用**，由 Jack Dorsey 推出。它专注于隐私和抗审查，无需账户、电话号码或中心化服务器。

## 核心特性

### 1. 双传输架构
- **本地：** 蓝牙低功耗（BLE）Mesh 网络，设备间消息跳跃传递
- **全球：** Nostr 协议，通过互联网实现全球通信

### 2. 离线通信
- 无需蜂窝服务、Wi-Fi 或互联网
- 设备间通过蓝牙 Mesh 传递消息
- 网络恢复后自动投递

### 3. 隐私优先
- 端到端加密
- 无需注册账户
- 无需电话号码
- 无需追踪、无广告

### 4. 技术栈
- **iOS：** Swift
- **Android：** Kotlin
- **协议：** BLE Mesh + Nostr
- **状态：** TestFlight / Google Play 可用

## 和我们有什么关系

### 与小6项目

Bitchat 是**去中心化通信应用**，与小6项目（AI 智能指挥中枢）定位不同：

| 维度 | Bitchat | 小6项目 |
|------|---------|---------|
| 定位 | 去中心化聊天 | AI 智能指挥中枢 |
| 通信 | BLE Mesh + Nostr | 中心化 Web 服务 |
| 隐私 | 无账户、端到端加密 | 账户系统、权限管理 |
| 技术 | Swift/Kotlin + Nostr | Vue3/React + Python |

### 潜在应用场景

1. **小6项目的通信模块**
   - Nostr 协议可作为小6项目的备用通信方案
   - 去中心化思路可用于小6的分布式部署

2. **Hermes 的离线通信**
   - 蓝牙 Mesh 通信思路可参考
   - 离线消息队列 + 自动投递机制

### 局限性

- **移动应用**：不是 Web 服务，与小6的 Web 架构不匹配
- **通信协议**：功能范围有限，非 AI 平台
- **Swift/Kotlin 技术栈**：与小6的 Python 后端不匹配

## 相关笔记

- 小6项目-AI智能指挥中枢 — 小6项目架构
- Multica-AI编码代理团队管理平台 — AI 代理团队管理
- Orca-并行AI编码代理编排器 — 并行代理编排器
- SmartAdmin-后台管理模板 — 后台管理模板
- HeyClicky-跨平台AI光标伴侣 — 跨平台 AI 光标伴侣
- Harness-AI代理基础设施框架 — AI 代理基础设施框架
