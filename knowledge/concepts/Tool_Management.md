---
id: know-agent
type: concept
---
# Agent 工具管理系统

## 工具分类

### 文件操作
- read_file：读取文件内容
- write_file：写入文件内容
- patch：目标编辑
- search_files：搜索文件内容
- session_search：搜索历史会话

### 代码编辑
- execute_code：执行 Python 代码

### 终端
- terminal：执行 Shell 命令

### 搜索
- web_search：网络搜索
- web_extract：网页内容提取
- mcp__fetch__fetch：URL 抓取

### 知识库
- memory：持久化记忆
- skill_manage：技能管理
- skill_view：查看技能
- skills_list：列出技能

### 自动化
- computer_use：桌面自动化
- delegate_task：子任务委派
- cronjob：定时任务

### 媒体
- image_generate：图片生成
- text_to_speech：语音合成
- vision_analyze：图片分析

### 其他
- clarify：向用户提问
- todo：任务列表管理

## 使用规则

### 自动执行（低风险）
- 读取文件
- 搜索文件
- 搜索会话
- 生成报告
- 整理资料

### 需要确认（高风险）
- 删除文件
- 修改系统配置
- 上传数据
- 支付操作

### 工具选择原则
1. 优先使用专用工具（如 read_file 优于 cat）
2. 优先使用批量操作
3. 优先使用并行调用
4. 工具失败不超过3次

## 工具记录

每个工具记录：
- 输入参数
- 输出格式
- 使用条件
- 已知风险

## 🔗 相关笔记
- Tool_Usage_Guide
- Task_Tracking
- Task_Planning
