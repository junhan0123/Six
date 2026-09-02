# RC-3 Core Experience Repair - 审计汇总报告

**日期**: 2026-08-28  
**阶段**: RC Maintenance - Core Experience Repair  
**状态**: 审计完成，待修复

---

## 审计概览

| 审计报告 | 路径 | 严重度 |
|---------|------|--------|
| IDENTITY_AUDIT_REPORT.md | `G:\xiao6\xiao6-ui\IDENTITY_AUDIT_REPORT.md` | P0 |
| MEMORY_AUDIT_REPORT.md | `G:\xiao6\xiao6-ui\MEMORY_AUDIT_REPORT.md` | P0 |
| LLM_RELIABILITY_REPORT.md | `G:\xiao6\xiao6-ui\LLM_RELIABILITY_REPORT.md` | P1 |

---

## P0 问题汇总（必须修复）

### 1. AI 身份错误
**现象**: LLM 自称 "Agnes" 而非 "小6"  
**根因**: LLM 未遵循 System Prompt 身份约束（可能训练数据污染）  
**位置**: 
- `config.py:726-756` - System Prompt 模板正确
- `memory.py:376-391` - build_system_prompt() 正确
- `server_handlers_chat.py:155` - 备用名错误（"庄周" 应为 "小6"）

**修复方案**:
1. 增强 System Prompt 身份声明（移至最后、加强语气）
2. 修复 server_handlers_chat.py:155 备用名
3. 或添加 Output Guard 后处理

---

### 2. Memory 系统未工作
**现象**: memories 表为空（0 条记录），`remember` 工具调用返回成功但无持久化  
**根因**: 
- 需进一步验证：DB 路径一致性 / 事务提交 / Content Hash 冲突
- tool_remember → add_episode → memory_adapter → memory.create_memory 链路看似正确

**修复方案**:
1. 添加写入验证日志
2. 检查 DB 路径一致性（所有模块使用相同路径）
3. 添加 Memory 健康检查到 /api/health

---

## P1 问题汇总（建议修复）

### 3. Quota 语法错误
**现象**: quota.py 存在 SyntaxError（leading zero in decimal integer）  
**位置**: `quota.py`（具体行号待确认）  
**影响**: 阻止模块导入，可能导致 LLM 调用失败

**修复方案**:
```python
# 修改前（推测）
LEAD_0_TIME = 01  # ❌ SyntaxError

# 修改后
LEAD_0_TIME = 1  # ✅
```

---

### 4. Retry 不足 + 无 Fallback
**现象**: 429 限流时仅重试 2 次，无降级方案  
**位置**: `llm.py:129-227`  
**影响**: 高频使用时服务不可用

**修复方案**:
1. 增加 retries 从 2 到 4-5
2. 添加 LLM2 作为备用 Provider
3. 实现响应缓存

---

## 修复优先级

| 优先级 | 问题 | 预计工作量 | 阻塞发布？ |
|--------|------|-----------|-----------|
| P0 | AI 身份错误 | 30min | ✅ 是 |
| P0 | Memory 系统失效 | 1-2h | ✅ 是 |
| P1 | Quota 语法错误 | 10min | ⚠️ 建议修 |
| P1 | Retry/Fallback | 2-3h | ❌ 否 |

---

## 下一步行动

### 立即执行（P0）
1. 修复 `server_handlers_chat.py:155` 备用名
2. 增强 System Prompt 身份约束
3. 调试 Memory 写入链路

### 本周执行（P1）
4. 修复 `quota.py` 语法错误
5. 增加 LLM Retry 次数
6. 配置 LLM2 备用 Provider

---

## 交付文件

| 文件 | 完整路径 | 大小 |
|------|---------|------|
| IDENTITY_AUDIT_REPORT.md | `G:\xiao6\xiao6-ui\IDENTITY_AUDIT_REPORT.md` | 2.2KB |
| MEMORY_AUDIT_REPORT.md | `G:\xiao6\xiao6-ui\MEMORY_AUDIT_REPORT.md` | 6.1KB |
| LLM_RELIABILITY_REPORT.md | `G:\xiao6\xiao6-ui\LLM_RELIABILITY_REPORT.md` | 6.1KB |
| RC-3 汇总报告 | `G:\xiao6\xiao6-ui\RC3_AUDIT_SUMMARY.md` | 本文档 |

---

**状态**: 审计完成，等待修复指令  
**禁止**: 未修改任何代码  
**下一步**: 等待用户确认修复方案
