---
id: know-github-3
type: project
---
# GitHub 项目调研笔记

## 调研时间
2026-07-29

---

## 1. usestrix/strix — AI渗透测试工具

**仓库**：https://github.com/usestrix/strix
**许可证**：Apache 2.0
**语言**：Python
**版本**：v1.4.1

### 功能
- 自主AI渗透测试代理，动态运行代码、发现漏洞、验证漏洞
- 多智能体编排，渗透测试团队协作
- 真实漏洞利用验证（可运行PoC，非误报）
- 自动修复和报告生成

### 工具包
- HTTP拦截代理（Caido）
- 浏览器自动化（XSS/CSRF/点击劫持/认证绕过）
- Shell和命令执行
- 自定义漏洞利用运行时（Python沙箱）
- 侦察和OSINT
- SAST + DAST

### 覆盖漏洞
- 访问控制漏洞（IDOR/权限提升/认证绕过）
- 注入攻击（SQL/NoSQL/OS命令/SSTI）
- 服务端漏洞（SSRF/XXE/反序列化/RCE）
- 客户端攻击（XSS/原型污染/CSRF）
- 业务逻辑缺陷
- 认证与会话安全
- 基础设施和云安全
- API安全

### 集成
- GitHub Actions CI/CD
- GitHub/GitLab/Bitbucket/Slack/Jira/Linear

### 部署
```bash
curl -sSL https://strix.ai/install | bash
export STRIX_LLM="openai/gpt-5.4"
export LLM_API_KEY="your-api-key"
strix --target ./app-directory
```

### 和我们关系
可用于扫描自有代码安全，非日常刚需

---

## 2. xbtlin/ai-berkshire — AI价值投资研究框架

**仓库**：https://github.com/xbtlin/ai-berkshire
**许可证**：MIT
**语言**：Python
**提交**：1,333次

### 功能
- 巴菲特/芒格/段永平/李录四大师方法论
- 多Agent对抗分析
- 20个投资技能

### 技能
- 财报审计
- 财务严谨性验证
- 收益投资分析
- 估值分析
- 护城河分析
- 台股FinMind数据源
- 晨星公允价值筛选

### 数据源
- 晨星（Morningstar）：840只股票公允价值
- FinMind（台股）
- Goodinfo（台股）
- MOPS（台股）

### 覆盖市场
- A股、美股、港股、台股

### 工具
- `report_audit.py`：财报数据审计
- `financial_rigor.py`：财务严谨性验证
- `twstock_data.py`：台股FinMind取数

### 和我们关系
老板关注股票投资，可直接接入使用

---

## 3. diegosouzapw/OmniRoute — AI网关

**仓库**：https://github.com/diegosouzapw/OmniRoute
**许可证**：MIT
**语言**：TypeScript/Node.js
**版本**：v3.8.50
**贡献者**：500+
**分叉**：93
**标签**：312

### 功能
- 统一API网关，一个端点接入290+提供商、500+模型
- 支持90+免费提供商

### 支持提供商
- Kimi、Claude、GPT、OpenAI、Gemini、GLM、DeepSeek、MiniMax

### 兼容工具
- Claude Code、Codex、Cursor、OpenCode、Cline、Copilot

### 核心特性
- 配额感知自动回退
- RTK + Caveman压缩（节省15-95%令牌）
- 支持MCP/A2A
- 桌面/PWA应用

### 特色功能
- VNC浏览器会话：无头服务器上的交互式登录
- Langfuse插件集成
- Adobe Firefly图像生成

### 部署
- 支持Docker、Podman
- Electron桌面应用

### 和我们关系
可统一管理多个API Key，自动切换最便宜模型，省令牌费

---

## 4. simplex-chat/simplex-chat — 隐私即时通讯

**仓库**：https://github.com/simplex-chat/simplex-chat
**许可证**：AGPL v3
**版本**：7.0
**提交**：6,389次
**分支**：292
**标签**：368

### 功能
- 无需任何用户标识符的即时通讯网络
- 100%私密

### 平台
- iOS、Android、桌面应用、CLI

### 特色
- 机器人API
- ERC1155代币合约（NFT）
- 频道功能
- Web预览

### 和我们关系
纯通讯工具，与业务无关

---

## 5. Robbyant/lingbot-map — 3D重建基础模型

**仓库**：https://github.com/Robbyant/lingbot-map
**许可证**：Apache 2.0
**语言**：Python
**论文**：arXiv 2604.14141

### 功能
- 流式3D重建前馈基础模型
- Geometric Context Transformer架构

### 核心特性
- 统一坐标定位、密集几何线索、长距离漂移校正
- 前馈架构，20 FPS推理（518×378分辨率）
- 支持10000+帧长序列
- Paged KV Cache注意力

### 模型
- `lingbot-map-long`：适合长序列和大场景
- `lingbot-map`：平衡版本（论文基准）
- `lingbot-map-stage1`：第一阶段训练检查点

### 基准数据集
- KITTI、Oxford Spires、VBR、Droid-W、TUM-D
- 7-scenes、ETH3D、Tanks and Temples、NRGBD

### 部署
```bash
conda create -n lingbot-map python=3.10
pip install torch==2.8.0 --index-url https://download.pytorch.org/whl/cu128
pip install -e .
pip install flashinfer-python
python demo.py --model_path /path/to/lingbot-map.pt --image_folder example/courthouse --mask_sky
```

### 和我们关系
Unity游戏场景自动生成潜在应用，非当前刚需

---

## 总结

| 项目 | 类型 | 优先级 | 理由 |
|------|------|--------|------|
| ai-berkshire | 投资研究 | ⭐⭐⭐ | 老板关注股票，可直接使用 |
| OmniRoute | API网关 | ⭐⭐ | 统一管理API，省令牌费 |
| strix | 安全扫描 | ⭐ | 偶尔扫描代码安全 |
| simplex-chat | 通讯 | ❌ | 与业务无关 |
| lingbot-map | 3D重建 | ⭐ | Unity场景生成潜在应用 |

## 6. emilkowalski/skills — taste-frontend（前端设计品味 skill）

**仓库**：https://github.com/emilkowalski/skills
**作者**：Emil Kowalski（Vercel 创始人，Sonner/Vaul 作者）
**Stars**：22.3k+ | **提交**：活跃
**许可证**：Apache 2.0

### 功能
- 反模板化前端设计 skill，专注落地页、作品集、重新设计
- 读取简报 → 推断设计方向 → 输出非模板化界面
- 三大旋钮配置：DESIGN_VARIANCE（1-10）、MOTION_INTENSITY（1-10）、VISUAL_DENSITY（1-10）
- 23 条设计规则，覆盖排版、色彩、布局、交互、内容密度、引用/证言、主题锁定等

### 核心特色
- **设计阅读（Design Read）**：生成代码前先声明页面类型、受众、风格倾向
- **三大旋钮**：VARIANCE（对称→混乱）、MOTION（静态→电影级）、DENSITY（画廊→驾驶舱）
- **真实设计系统映射**：根据简报自动推荐 Fluent UI、Material 3、Carbon、shadcn/ui 等
- **反默认纪律**：禁止 AI 紫渐变、禁止 Inter 作为默认字体、禁止衬线体滥用
- **色彩校准**：禁止 AI 紫/蓝辉光，推荐中性基底+高对比单色点缀
- **布局纪律**：Hero 必须适配首屏、导航单行、Bento 网格节奏、反对重复布局
- **图片策略**：优先 AI 生图 → 真实图片 → 占位符，禁止 div 伪截图
- **内容密度**：每节短标题+短正文+单视觉资产，禁止数据倾倒
- **Pre-Flight 检查**：按钮对比度、CTA 单行、表单可访问性、颜色一致性锁定

### 安装
已在 `~/.hermes/skills/taste-frontend/` 安装（已有，内容完整 1206 行）

### 和我们关系
已有 skill，覆盖创意审美方向，配合 impeccable 使用

---

## 7. pbakaus/impeccable — 无可挑剔前端设计 skill

**仓库**：https://github.com/pbakaus/impeccable
**作者**：Paul Bakaus（Google Chrome 团队成员）
**Stars**：23k+ | **提交**：1261 次 | **版本**：4.0.3
**许可证**：Apache 2.0

### 功能
- 23 个设计命令，覆盖创建、评估、润色、简化、加固、系统六大类
- 支持 Claude Code、Codex、Cursor、Gemini、Grok、Kiro 等几乎所有 AI 编程工具
- 四种模式：Persuade（说服）、Operate（操作）、Read（阅读）、Experience（体验）

### 命令分类

**Build（构建）：**
- `craft [feature]`：新工作请求（已弃用，用 shape 替代）
- `shape [feature]`：写代码前规划 UX/UI
- `init`：在 PRODUCT.md 中捕获产品上下文
- `document`：从现有项目代码生成 DESIGN.md
- `extract [target]`：提取可复用 token 和组件到设计系统

**Evaluate（评估）：**
- `critique [target]`：启发式评分的 UX 设计评审
- `audit [target]`：技术质量检查（可访问性、性能、响应式）

**Refine（润色）：**
- `polish [target]`：发货前的最终质量检查
- `bolder [target]`：放大安全或平淡的设计
- `quieter [target]`：降低侵略性或过度刺激的设计
- `distill [target]`：剥离到本质，移除复杂度
- `harden [target]`：生产就绪：错误处理、i18n、边界情况
- `onboard [target]`：设计首次运行流程、空状态、激活

**Enhance（增强）：**
- `animate [target]`：添加有目的的动画和动效
- `colorize [target]`：为单色 UI 添加战略性色彩
- `typeset [target]`：改进排版层级和字体
- `layout [target]`：修复间距、节奏和视觉层级
- `delight [target]`：添加个性和令人难忘的细节
- `overdrive [target]`：突破常规极限

**Fix（修复）：**
- `clarify [target]`：改进 UX 文案、标签和错误消息
- `adapt [target]`：适配不同设备和屏幕尺寸
- `optimize [target]`：诊断和修复 UI 性能

**Iterate（迭代）：**
- `live`：视觉变体模式，在浏览器中选择元素生成替代方案

### 核心原则
- **Go all out**：不犹豫、不 shortcuts，交付必须完整
- **Dream big and bold**：独特、美丽、出色、高度启发性
- **Verify in bounded passes**：构建完整 → 一次性检查（桌面+移动）→ 批量修复 → 最多一轮确认 → 停止打磨

### 安装
已在 `~/.hermes/skills/impeccable/` 安装（克隆自 GitHub，SKILL.md 已创建）

### 和我们关系
与 taste-frontend 互补：taste-frontend 偏创意审美，impeccable 覆盖设计全流程，Chrome 团队出品

---

## 总结（更新）

| 项目 | 类型 | 优先级 | 理由 |
|------|------|--------|------|
| ai-berkshire | 投资研究 | ⭐⭐⭐ | 老板关注股票，可直接使用 |
| OmniRoute | API网关 | ⭐⭐ | 统一管理API，省令牌费 |
| taste-frontend | 前端设计 | ⭐⭐ | 创意审美方向（已安装） |
| impeccable | 前端设计 | ⭐⭐ | 设计全流程（已安装） |
| strix | 安全扫描 | ⭐ | 偶尔扫描代码安全 |
| lingbot-map | 3D重建 | ⭐ | Unity场景生成潜在应用 |
| simplex-chat | 通讯 | ❌ | 与业务无关 |

## 🔗 相关笔记
- 系统能力清单
- VibeVoice调研报告
- taste-frontend skill 使用指南
- impeccable skill 使用指南
