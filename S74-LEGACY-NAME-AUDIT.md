# S74 Legacy Name Audit
## Xiao6 v1.0.0 Legacy Name Classification

---

## Classification Results

### A. Runtime-Critical (保留)

| 名称 | 位置 | 用途 | 分类 |
|------|------|------|------|
| ZHUANGZHOU_KWS_ENABLED | config.py | KWS 唤醒开关 | RUNTIME-CRITICAL |
| ZHUANGZHOU_WAKE_PHRASE | config.py | 唤醒词配置 | RUNTIME-CRITICAL |
| ZHUANGZHOU_KWS_SENSITIVITY | config.py | KWS 敏感度 | RUNTIME-CRITICAL |
| ZHUANGZHOU_VOSK_KWS_ENABLED | config.py | Vosk KWS 开关 | RUNTIME-CRITICAL |
| ZHUANGZHOU_PROXY_URL | config.py | 代理 URL | RUNTIME-CRITICAL |
| ZHUANGZHOU_PORT | env var | 端口配置 | RUNTIME-CRITICAL |
| ZHUANGZHOU_THEME | env var | 主题配置 | RUNTIME-CRITICAL |
| ZHUANGZHOU_MEMORY_GRAPH | env var | 记忆图开关 | RUNTIME-CRITICAL |
| ZHUANGZHOU_DOC_DIR | config.py | 文档目录 | RUNTIME-CRITICAL |
| ZHUANGZHOU_AUTO_REVIEW | config.py | 自动审查开关 | RUNTIME-CRITICAL |
| ZHUANGZHOU_TTS_BACKEND | env var | TTS 后端 | RUNTIME-CRITICAL |
| ZHUANGZHOU_GPT_SOVITS_URL | env var | GPT-SoVITS URL | RUNTIME-CRITICAL |

**结论**: 所有 ZHUANGZHOU_* 环境变量均为运行时关键，不迁移。

---

### B. Compatibility (保留)

| 名称 | 位置 | 用途 | 分类 |
|------|------|------|------|
| ZhuangZhou_TTS_VOICE | env var | TTS 声线 | COMPATIBILITY |
| ZhuangZhou_TTS_RATE | env var | TTS 速率 | COMPATIBILITY |

---

### C. Historical Documentation (保留)

| 名称 | 位置 | 用途 | 分类 |
|------|------|------|------|
| PHASE-S61-FINAL.md | 历史报告 | 包含 8000 端口记录 | HISTORICAL |
| PHASE-S62-FINAL.md | 历史报告 | 包含 8000 端口记录 | HISTORICAL |
| PHASE-S63-FINAL.md | 历史报告 | 包含 8000 端口记录 | HISTORICAL |
| PHASE-S64-PRECHECK.md | 历史报告 | 包含 8000 端口记录 | HISTORICAL |
| S62-PRECHECK-REPORT.md | 历史报告 | 包含 8000 端口记录 | HISTORICAL |

**结论**: 历史报告不改，保留历史事实。

---

### D. Dead Code (不处理)

| 名称 | 位置 | 用途 | 分类 |
|------|------|------|------|
| zhuangzhou_event | agent_runtime.py.migration-bak | 死代码备份 | DEAD CODE |
| ZHUANGZHOU_ASR_PROVIDER | asr.py.migration-bak | 死代码备份 | DEAD CODE |

---

### E. Safe to Remove (不删除)

无。

---

## Migration Summary

| 类别 | 数量 | 处理 |
|------|------|------|
| A. Runtime-Critical | 12 | 保留 |
| B. Compatibility | 2 | 保留 |
| C. Historical Documentation | 5 | 保留 |
| D. Dead Code | 2 | 保留（备份） |
| E. Safe to Remove | 0 | - |

**总计数**: 21 个 legacy name 引用，全部保留。

---

## Notes

1. **不批量 rename**: ZHUANGZHOU_* 作为环境变量名，用户可能已有配置依赖。
2. **历史报告不变**: PHASE-*.md 文件是历史证据，不改版本号。
3. **兼容性优先**: 保留旧名比破坏现有配置更重要。

---

END OF LEGACY NAME AUDIT
