# Xiao6 v1.0.0 API Reference

**Base URL**: `http://localhost:8000`  
**Version**: 1.0.0  
**Last Updated**: 2026-09-06  

---

## Version & Health

### GET /api/version

返回应用版本信息。

**Response**:
```json
{
  "ok": true,
  "app_name": "小6",
  "version": "1.0.0",
  "check_url": "https://github.com/AGI-Xiao6/Xiao6/releases/latest"
}
```

### GET /api/health

健康检查。

**Response**:
```json
{
  "status": "alive",
  "ok": true,
  "model": "agnes-2.5-flash",
  "tts_backend": "sovits",
  "tools": ["get_time", "calculator", ...]
}
```

### GET /api/ready

就绪状态检查。

**Response**:
```json
{
  "ok": false,
  "ready": true,
  "status": "degraded",
  "degraded": []
}
```

---

## Intelligence

### GET /api/intelligence/feed

返回统一洞察列表。

**Response**:
```json
{
  "ok": true,
  "feed": [
    {
      "id": "world-risk-...",
      "type": "world",
      "priority": 5,
      "title": "...",
      "score": 0.85,
      "summary": "...",
      "impact": "high",
      "recommendation": "..."
    }
  ],
  "total": 1
}
```

### GET /api/intelligence/foresight

返回趋势预警信号。

**Response**:
```json
{
  "ok": true,
  "signals": [...],
  "warnings": [...]
}
```

### GET /api/intelligence/context

返回关联分析上下文。

**Response**:
```json
{
  "ok": true,
  "contexts": [
    {
      "context_id": "...",
      "topic": "...",
      "entities": [...],
      "relations": [...]
    }
  ]
}
```

### GET /api/intelligence/reasoning

返回推理引擎结果。

**Response**:
```json
{
  "ok": true,
  "reasonings": [
    {
      "reasoning_id": "...",
      "topic": "...",
      "explanation": "...",
      "evidence": [...],
      "confidence": 0.85
    }
  ]
}
```

### GET /api/intelligence/decision

返回决策辅助信息。

**Response**:
```json
{
  "ok": true,
  "decisions": [
    {
      "decision_id": "...",
      "topic": "...",
      "options": [...],
      "factors": [...],
      "confidence": 0.8
    }
  ]
}
```

### GET /api/intelligence/predictions

返回预测账本。

**Response**:
```json
{
  "ok": true,
  "predictions": [],
  "total": 0
}
```

### GET /api/intelligence/learning

返回学习反馈分析。

**Response**:
```json
{
  "ok": true,
  "records": [],
  "sources": [],
  "overall_accuracy": 0.0,
  "total_predictions": 0
}
```

### GET /api/intelligence/center

返回完整 Intelligence Center 快照。

**Response**:
```json
{
  "ok": true,
  "snapshot": {
    "overview": {
      "total_insights": 0,
      "total_signals": 0,
      "total_warnings": 0,
      "total_reasonings": 0,
      "total_decisions": 0,
      "total_predictions": 0
    },
    "insights": [],
    "future_signals": [],
    "warnings": [],
    "reasonings": [],
    "decisions": [],
    "predictions": [],
    "learning": {
      "records": [],
      "sources": []
    },
    "timestamp": "2026-09-06T..."
  }
}
```

---

## Interaction

### GET /api/interaction/status

交互系统状态。

### POST /api/interaction/parse

命令解析。

**Request**:
```json
{
  "command": "查看今天的洞察"
}
```

### GET /api/interaction/activity

活动追踪列表。

---

## Data APIs

### GET /api/memory

记忆管理。

### GET /api/knowledge

知识库查询。

### GET /api/goals

目标列表。

### GET /api/tasks

任务列表。

### GET /api/tools/list

工具列表（63 tools）。

---

## Error Responses

```json
{
  "ok": false,
  "error": "Error message"
}
```

All endpoints return HTTP 200 with structured response body.