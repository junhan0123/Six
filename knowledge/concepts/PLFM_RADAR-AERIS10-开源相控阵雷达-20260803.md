---
created: 2026-08-03
tags:
  - 雷达
  - 硬件
  - FPGA
  - 开源硬件
  - 相控阵
id: know-plfm-radar-aeris-10
type: concept
---
# PLFM_RADAR (AERIS-10) - 开源相控阵雷达系统

## 简介

**AERIS-10** 是一个完全开源的低成本 10.5 GHz 相控阵雷达系统，采用脉冲线性调频（PLFM）调制。项目旨在让大学研究者、无人机公司和 SDR 爱好者都能探索相控阵雷达技术。

- **GitHub**: [NawfalMotii79/PLFM_RADAR](https://github.com/NawfalMotii79/PLFM_RADAR)
- **⭐**: 23.3k
- **Forks**: 5.4k
- **License**: MIT（软件）+ CERN-OHL-P（硬件）
- **状态**: Alpha
- **Hackaday**: [项目页面](https://hackaday.io/project/205190-open-source-plfm-radar-up-to-20km-range)

## 核心参数

| 参数 | 值 |
|------|-----|
| 频率 | 10.5 GHz |
| 调制方式 | 脉冲线性调频（PLFM） |
| FPGA | AMD Artix-7 |
| 版本 | AERIS-10N（3km）/ AERIS-10X（20km） |
| 天线阵列 | 8×16 贴片天线 / 32×16 介质填充槽波导 |
| 开源协议 | 软件 MIT / 硬件 CERN-OHL-P |

## 两个版本

### AERIS-10N（Nexus）
- 探测距离：3km
- 天线：8×16 贴片天线阵列
- 适合：入门、实验室、无人机近距离探测

### AERIS-10X（Extended）
- 探测距离：20km
- 天线：32×16 介质填充槽波导阵列
- 适合：远距离探测、安防、科研

## 核心功能

- **波束成形** — 电子控制雷达波束方向
- **脉冲压缩** — 提高距离分辨率
- **多普勒处理** — 速度测量和运动目标检测
- **目标跟踪** — 多目标轨迹追踪
- **GUI 仪表盘** — Tkinter 图形界面实时监控

## 技术架构

### 硬件
- FPGA：AMD Artix-7
- 射频前端：10.5 GHz 相控阵天线
- 数据传输：FT2232H / FT601

### 软件
- 固件：FPGA 逻辑
- GUI：Tkinter 仪表盘（V6.5）
- 仿真：Python（Ruff lint 严格模式）
- 工具：UART 诊断捕获工具

### 仓库结构
```
.github/workflows/          # CI/CD
1_Project_Description/      # 项目描述
2_Functional Diagram/       # 功能框图
3_Power Management/         # 电源管理
4_Schematics and Boards/    # 原理图和 PCB
5_Simulations/              # 仿真
6_Application Notes/        # 应用笔记
7_Components Datasheets/    # 元器件手册
8_Utils/                    # 工具（3D 波导等）
9_Firmware/                 # 固件
docs/                       # 文档
```

## 应用场景

- **无人机避障** — 近距离目标检测
- **安防监控** — 远距离入侵检测
- **学术研究** — 波束成形、信号处理实验
- **SDR 爱好者** — 相控阵技术探索
- **低空经济** — 无人机交通管理

## 与 OSIRIS 对比

| 特性 | OSIRIS | PLFM_RADAR (AERIS-10) |
|------|--------|----------------------|
| 类型 | 软件情报平台 | 硬件雷达系统 |
| 能力 | 信息聚合、态势感知 | 物理目标探测 |
| 部署 | 服务器/容器 | FPGA + 射频硬件 |
| 数据源 | 公开 API、摄像头 | 雷达回波 |
| 探测范围 | 全球 | 3-20km |
| 开源 | 纯软件 | 软件+硬件全开源 |
| 适用 | 安全研究、情报 | 无人机、安防、科研 |

## 部署方式

### 硬件组装
需要采购 AMD Artix-7 FPGA 开发板、射频前端模块、天线阵列，按原理图焊接。

### 软件部署
```bash
git clone https://github.com/NawfalMotii79/PLFM_RADAR.git
cd PLFM_RADAR
# 编译 FPGA 固件
# 运行 GUI 仪表盘
```

## 与我们的关系

- **Mac Studio** — 可运行仿真和数据处理
- **小6项目** — 可集成雷达数据作为物理感知层
- **AI Agent** — 雷达目标数据可作为 Agent 感知输入
- **无人机** — 适合与无人机项目结合

## 🔗 相关笔记
- OSIRIS-开源全球情报平台
- 小6项目 - 能力模块系统
- AGENTS.md
