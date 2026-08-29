# 03 · 技术栈选型：每一层用什么（含中文优化）

下面给的是**2026 年仍活跃、社区大、能跑通**的具体选型。分"通用派"和"中文优先派"，你在中国大陆、做健康场景，**默认走中文优先派**。

---

## 一、感知层

### 唤醒词
| 选项 | 说明 | 推荐 |
|------|------|------|
| **openWakeWord** | 开源、可训练自定义词（如"阿枢"） | ✅ 首选 |
| Porcupine | 准确但闭源/有限免费 | 备选 |

### 语音识别（ASR / STT）
| 选项 | 中文 | 离线 | 推荐 |
|------|------|------|------|
| **FunASR（阿里达摩院）** | ✅ 极佳 | ✅ | ✅ 中文首选 |
| Whisper / faster-whisper | 中 | ✅ | 英文/通用 |
| Vosk | 中 | ✅ | 轻量嵌入式 |

> 实测：中文环境 FunASR 的 Paraformer 模型远胜 Whisper base，且能识别顺滑。

### 视觉（可选）
- 摄像头 + **视觉大模型（VLM）**：Qwen-VL / InternVL（本地 Ollama 可跑）。
- 屏幕理解：截图 → VLM 读懂界面（类似 Open Interpreter）。

---

## 二、认知层（大脑 + 编排）

### 大模型（本地）
| 模型 | 定位 | 显存需求 |
|------|------|---------|
| **Qwen3-8B / 14B** | 中文均衡首选 | 8B~6GB / 14B~10GB |
| **DeepSeek-R1 蒸馏版** | 推理强 | 类似 |
| Llama 3.x | 英文强 | — |

跑起来用 **Ollama**（一键拉模型，提供 HTTP API）。

### 云端兜底（可选）
- 你已有的 **Agnes AI（agnes-2.0-flash）** 可作为高质量云端兜底，走 OpenAI 格式 API。
- 或接通义/DeepSeek 官方 API。

### 编排器
| 选项 | 适合 | 推荐 |
|------|------|------|
| **LangGraph** | 复杂多步、状态机、开发者 | ✅ 主选 |
| n8n | 可视化自动化流程 | 补强 |
| Dify | 低代码 Agent 平台 | 快速原型 |
| AutoGen | 多智能体协作 | 进阶 |

---

## 三、记忆层

| 类型 | 选型 | 说明 |
|------|------|------|
| 向量库 | **Chroma**（轻） / Qdrant（强） / Milvus（海量） | 语义检索长期记忆 |
| 结构化 | **SQLite**（单机） / PostgreSQL（多端同步） | 用户画像、事实 |
| 缓存/会话 | 内存 + Redis（可选） | 短期对话上下文 |
| 框架 | LlamaIndex（RAG  retrieval 强） | 检索增强可选 |

---

## 四、行动层（工具总线 + 自动化）

### MCP 工具总线
- 自写 **MCP Server**（Python `mcp` SDK）暴露你的工具（查日程、控设备、读健康数据）。
- 直接复用社区现成 MCP Server（文件系统、浏览器、GitHub、数据库……）。

### 设备 / 家居自动化
| 选项 | 说明 |
|------|------|
| **Home Assistant** | 开源全屋智能中枢，设备协议最全 |
| n8n | 通用流程自动化，连 API/邮件/日历 |

### 外部能力
- 联网搜索（DuckDuckGo / SearXNG 自托管）
- 日历（CalDAV）、邮件（IMAP/SMTP 或你已有的 Agent 邮箱）

---

## 五、人格层

- **Persona 文件**：`personality.json` + `user_profile.json`（参考 GiraAI 的结构）。
- **主动规则引擎**：用简单调度（cron / 后台线程）定时检查条件触发对话。
- 语气靠 system prompt 调校，无需特殊框架。

---

## 六、交互层

### 语音输出（TTS）
| 选项 | 中文 | 说明 |
|------|------|------|
| **CosyVoice（阿里）** | ✅ 自然、可克隆音色 | ✅ 中文首选 |
| Edge-TTS（微软） | ✅ 免费够用 | 快速起步 |
| GPT-SoVITS | ✅ 克隆"贾维斯嗓音" | 进阶定制 |

### 界面
| 形态 | 技术 | 说明 |
|------|------|------|
| Web 前端 | **React + Tailwind + WebSocket** | 实时聊天、语音波形 |
| 桌面端 | **Tauri（Rust，轻）** / Electron | 常驻悬浮助手 |
| 全屋屏 | 网页投屏到平板/带屏音箱 | Echo Show 风 |
| 移动端 | React Native / 你规划的健康 APP | 后期打通 |

---

## 七、硬件（最小起步 & 进阶）

| 阶段 | 硬件 |
|------|------|
| MVP | 普通电脑 + 麦克风 + 音箱 |
| 常驻助手 | 小主机(如 N100) + USB 麦克风阵列 |
| 全屋 | 平板屏 + Home Assistant + 智能设备 |
| 健康联动 | 智能手表/手环（数据走 MCP 进贾维斯） |

> 显存提示：本地跑 14B 模型建议 ≥12GB 显存；没独显可用 CPU+内存（慢但能跑），或用你已有的云端 API 兜底。

---

## 开源参考项目（站在巨人肩上）

| 项目 | 技术栈 | 可借鉴 |
|------|--------|--------|
| **My-Xiao6** | Ollama + LangChain + pyttsx3 | 唤醒→LLM→TTS 最小闭环 |
| **Edge-Voice-Agent** | Whisper + Llama + Tkinter | 离线、状态机 GUI |
| **xiao6_rs** | Rust + Vosk + Ollama | 高性能、跨平台 |
| **GiraAI** | FastAPI + React 全栈 | 完整前后端 + 文件/网页/系统控制 |
| **Open WebUI** | 视觉化 LLM 界面 | 现成漂亮前端 |
| **Home Assistant / n8n / Dify** | 自动化/编排 | 行动层与低代码 |

**建议**：直接 clone GiraAI 或 My-Xiao6 当脚手架，把英文零件（Whisper/pyttsx3）换成中文零件（FunASR/CosyVoice），再按本方案加记忆和 MCP。

下一页 → `04-roadmap.md` 看分几期做、每期产出什么。
