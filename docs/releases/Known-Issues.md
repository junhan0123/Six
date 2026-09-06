# Xiao6 v1.0.0 Known Issues

**Document Version**: 1.0.0  
**Last Updated**: 2026-09-06  

---

## Critical

### TTS Not Available

**Severity**: High  
**Status**: External Dependency Blocked  

GPT-SoVITS 语音合成服务未运行。

**影响**：
- 语音输入不可用
- 语音输出不可用
- TTS API 返回连接超时

**解决方案**：
启动 GPT-SoVITS 服务：
```bash
# 默认端口 9880
http://127.0.0.1:9880
```

**配置**：
- `TTS_BACKEND=sovits`
- `GPT_SOVITS_URL=http://127.0.0.1:9880`

---

## Medium

### In-Memory Only Storage

**Severity**: Medium  
**Status**: By Design  

Intelligence 模块使用内存存储，重启后数据丢失。

**影响**：
- 预测记录不持久化
- 学习数据不跨重启保留
- 洞察历史不保留

**设计决策**：
遵循 Architecture Freeze 约束，不引入额外数据库。

---

## Low

### External Service Dependencies

**Severity**: Low  
**Status**: Monitored  

部分外部 API 不稳定：
- Agnes API: HTTP 404（内部配置问题）
- 抖音热点源: HTTP 502/404
- 天气源 Open-Meteo: 正常

---

## Out of Scope (Frozen)

以下功能在 v1.0.0 中已冻结，不在 release scope：

- Browser 自动化（NOT_IMPL）
- Multi-Agent 协作
- Forecast Market
- Country Simulator
- Black Swan Engine

---

## Notes

所有标记为 Known Issues 的项目均不影响核心功能使用。
TTS 问题不影响文本对话能力。