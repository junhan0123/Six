---
id: know-mac-studio-m4-max-ai
type: concept
---
# Mac Studio M4 Max AI服务器方案

## 硬件配置

- **型号：** Mac Studio M4 Max
- **内存：** 64GB 统一内存
- **存储：** 1TB SSD
- **当前状态：** 闲置，计划作为AI服务器使用

## 架构设计

**双模式AI工作流：**

| 模式 | 平台 | 用途 | 优势 |
|------|------|------|------|
| 云端API | Windows机器 | 日常AI任务 | 快速、省事、不占本地资源 |
| 本地服务器 | Mac Studio | ComfyUI生图生视频、AI工具 | 不依赖网络、隐私性好、24小时运行 |

## Mac Studio用途

### 1. ComfyUI生图生视频
- 64GB统一内存，跑FLUX/SDXL毫无压力
- 本地跑ComfyUI，不依赖网络
- 可以批量生图、训练LoRA

### 2. 本地大模型推理
- 64GB内存能跑13B-30B参数模型
- 适合做文本生成、代码辅助

### 3. AI工具服务器
- 24小时运行，随时调用
- 可以做自动化生图、视频处理

## 部署方案

### ComfyUI部署
```bash
# 1. 克隆ComfyUI
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 3. 安装依赖
pip install torch torchvision torchaudio
pip install -r requirements.txt

# 4. 启动服务
python main.py --listen 0.0.0.0
```

### 远程访问
- Windows机器通过局域网访问Mac Studio的ComfyUI
- API地址：`http://Mac-Studio-IP:8188`
- 可以写脚本自动调用

## 优势

1. **不浪费硬件** - Mac Studio当服务器，24小时运行
2. **双模式互补** - 云端API快，本地跑隐私好
3. **灵活调度** - 简单任务用云端，复杂任务本地跑
4. **成本可控** - 不额外花钱，利用现有硬件

## 注意事项

- Mac Studio需要保持开机状态
- 局域网访问需要配置防火墙
- 建议设置自动更新和监控

## 🔗 相关笔记

- [[ComfyUI 本地文生图 + 视频生成]]
- Agnes AI 全模态 API
- See-Through-动漫角色图层分解AI工具
