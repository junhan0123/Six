# Identity Layer Audit Report

**Date**: 2026-08-28  
**Scope**: AI_DISPLAY_NAME → System Prompt → LLM Response chain  
**Issue**: Model自称 "Agnes" 而非 "小6"

---

## 调用链审计

### 1. Config 层
```python
# config.py:330
AI_DISPLAY_NAME = os.environ.get("AI_DISPLAY_NAME", "小6")
```
✅ 默认值正确："小6"

```python
# config.py:54
AI_DISPLAY_NAME: str = ""  # 类型声明
```
✅ 静态类型声明正确

### 2. System Prompt 模板
```python
# config.py:726-756
def get_system_prompt_template():
    return (
        "你是{name}，老板的个人智能副驾。你唯一且固定的名字是「{name}」，"
        "在任何情况下都只自称{name}，绝不使用其他任何名字。"
        ...
    )

SYSTEM_PROMPT = get_system_prompt_template()
```
✅ 模板正确，包含强身份约束："只自称{name}，绝不使用其他任何名字"

### 3. Context 注入
```python
# memory.py:376-391
def build_system_prompt(message=""):
    import config
    name = config.AI_DISPLAY_NAME or "小6"  # ✅ 正确
    base = config.SYSTEM_PROMPT.format(name=name)  # ✅ 正确格式化
    ...
    return persona_block + base + build_context_prefix(message) + build_memory_block()
```
✅ 函数正确

```python
# server_handlers_chat.py:153-156
messages = [
    {"role": "system", "content": config.SYSTEM_PROMPT.format(name=config.AI_DISPLAY_NAME or "庄周")}
] + messages
```
⚠️ 备用值 "庄周" 而非 "小6"（第155行）

```python
# context/facade.py:21-28
def build_context_prompt(user_text=""):
    try:
        import memory
        return memory.build_system_prompt(user_text or "")
    except Exception:
        return ""
```
✅ 门面正确

### 4. API 响应
```python
# server.py:269
"ai_name": config.AI_DISPLAY_NAME,
```
✅ Health API 返回正确值

---

## 问题定位

### 发现的 Bug

| # | 位置 | 问题 | 严重度 |
|---|------|------|--------|
| 1 | `server_handlers_chat.py:155` | 备用名 "庄周" 应为 "小6" | P2 |
| 2 | LLM 未遵循 System Prompt 身份约束 | 模型输出 "Agnes" | **P0** |

### 根因分析

**System Prompt 正确配置，但 LLM 不遵循身份约束。**

证据：
- 模板明确写入："你唯一且固定的名字是「{name}」，在任何情况下都只自称{name}"
- Config 正确设置为 "小6"
- 但实际响应显示 "我是 Agnes，由 Sapiens AI 开发"

**可能原因**：
1. **LLM 训练数据污染**：模型训练时学习了 "我是 Agnes/Sapiens AI" 的固定回答模式
2. **System Prompt 权重不足**：模型对 system message 的遵循度低
3. **Prompt 注入冲突**：后续注入的 context/memory 内容覆盖了身份约束

---

## 验证结果

| 测试 | 预期 | 实际 | 结果 |
|------|------|------|------|
| Config 值 | "小6" | "小6" | ✅ |
| Template 格式化 | "你是小6，..." | 正确 | ✅ |
| Context 构建 | 包含身份约束 | 包含 | ✅ |
| LLM 响应 | "我是小6" | "我是 Agnes" | ❌ |

---

## 建议修复方案

### 方案 A：增强 System Prompt 身份约束（推荐）
在 `config.py` 的 `get_system_prompt_template()` 中，将身份声明移至**最后一句**并加强语气：
```
"【最重要规则】你的唯一身份是小6。无论任何情况，都只能自称小6。绝不允许说自己是Agnes、Claude、GPT或其他任何名字。如果用户问你叫什么，回答：我是小6。"
```

### 方案 B：添加 Output Guard
在 `server_handlers_chat.py` 的响应处理中添加后处理：
```python
if "Agnes" in content or "Sapiens AI" in content:
    content = content.replace("Agnes", "小6").replace("Sapiens AI", "小6的开发商")
```

### 方案 C：切换 LLM Provider
如果当前模型无法遵循身份约束，考虑：
- 使用支持更强 system prompt 跟随的模型
- 或在该模型上 fine-tune 身份指令

---

## 次要问题

| 文件 | 行号 | 问题 | 修复 |
|------|------|------|------|
| `server_handlers_chat.py` | 155 | 备用名 "庄周" | 改为 "小6" |

---

Audit completed: 2026-08-28
No code modified.
