---
id: know-smartadmin
type: concept
---
# SmartAdmin — 后台管理模板/快速开发平台

> **归档日期：** 2026-08-11
> **来源：** https://github.com/1024-lab/smart-admin
> **标签：** #后台管理 #快速开发 #Java #Vue3 #Admin

## 项目信息

- **仓库：** [1024-lab/smart-admin](https://github.com/1024-lab/smart-admin)
- **定位：** 国内首个以「高质量代码」为核心的快速开发平台
- **技术栈：** SpringBoot 2/3 + Sa-Token + MyBatis-Plus + Vue3 + Ant Design Vue
- **安全：** 满足国家三级等保要求

## 是什么

SmartAdmin 是一个**后台管理系统的快速开发平台**，提供完整的前后端代码模板，用于快速搭建企业级后台管理系统。

## 核心特性

### 1. 安全体系
- 双因子登录
- 密码加密、复杂度要求
- 登录错误次数锁定
- 接口国产加解密
- 数据脱敏
- 满足国家三级等保要求

### 2. 技术架构
- **后端：** Java 8 + SpringBoot 2.X / Java 17 + SpringBoot 3.X（双版本）
- **前端：** Vue3 + Vite5 + Ant Design Vue 4.x（JS + TypeScript 双版本）
- **移动端：** Uni-App + Uni-UI
- **数据库：** 支持国产（达梦、金仓、OceanBase、GaussDB 等）+ 主流（MySQL、PostgreSQL、Oracle 等）

### 3. 功能模块
- 系统功能：员工、部门、角色、权限、菜单、水印、文件管理
- 日志监控：服务器心跳日志、登录日志、操作日志
- OA 办公：公司信息、通知公告
- 代码生成：基于表的配置、在线预览代码
- 数据变更记录：基于 git diff 插件
- 在线文档：右侧帮助文档

## 和我们有什么关系

### 与小6项目

SmartAdmin 是**传统后台管理系统模板**，与小6项目（AI 智能指挥中枢）定位不同：

| 维度 | SmartAdmin | 小6项目 |
|------|-----------|---------|
| 定位 | 后台管理模板 | AI 智能指挥中枢 |
| 技术 | SpringBoot + Vue3 | Vue3/React + Python |
| 核心 | CRUD + 权限 | AI 对话 + 能力模块 |
| 特点 | 快速开发、安全合规 | 赛博朋克风格、自主行动 |

### 潜在应用场景

1. **小6项目的管理后台**
   - SmartAdmin 可作为小6项目的后台管理前端参考
   - 权限管理、日志监控等功能可借鉴

2. **小6项目的部署监控**
   - 如果需要监控多个小6实例，SmartAdmin 的监控模块可参考

### 局限性

- **不是 AI 项目**：与 AI 代理、智能系统无关
- **Java 技术栈**：与小6项目的 Python 后端不匹配
- **传统 CRUD**：不涉及 AI 能力集成

## 相关笔记

- 小6项目-AI智能指挥中枢 — 小6项目架构
- Multica-AI编码代理团队管理平台 — AI 代理团队管理
- Orca-并行AI编码代理编排器 — 并行代理编排器
