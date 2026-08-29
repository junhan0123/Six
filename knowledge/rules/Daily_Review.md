---
id: know-doc-b7cc2c2b
type: rule
---
# 每日总结规则

## 执行时间

每天结束前自动整理。

## 整理内容

1. 今天完成事项
2. 重要决策
3. 解决问题
4. 新知识
5. 下一步计划

## 保存位置

`Daily/YYYY-MM-DD.md`

## 文件格式

```markdown
# YYYY-MM-DD 总结

## 完成事项
- ...

## 重要决策
- ...

## 解决问题
- ...

## 新知识
- ...

## 下一步计划
- ...
```

## 触发方式

由 cronjob 每日 23:30 自动执行，通过 session_search 提取当日关键信息。

## 🔗 相关笔记
- Daily_Report
- Knowledge_Management
- Task_Tracking
