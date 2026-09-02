# Task A · 品牌统一报告（BRAND_UNIFICATION_REPORT）

> Sprint：Xiao6 UI Foundation Unification Sprint v1.0
> 模式：Audit → Plan → Execute → Verify → Report
> 语言：简体中文（代码/类名保持英文）

## 1. P0 来源

UI/UX Polish Sprint v1.0 审计报告 — **V-19 / S-03「品牌三表述」**。
同一产品在三个界面位置使用了互不相同的品牌表述，造成身份认知分裂。

## 2. 审计发现（实证 file:line）

| 位置 | 原文 | 表述 |
|------|------|------|
| `index.html:6` `<title>` | `小6 · 智能指挥中枢` | 智能指挥中枢 |
| `index.html:64` HUD `os-brand` | `小6 · <b>AI OS</b>` | AI OS |
| `index.html:1116` onboarding `onb-sub` | `本地 AI 副驾 · 隐私优先 · 离线可用` | 本地 AI 副驾 |
| `app.js:2232` 档案副标题 | `智能副驾 · 本地档案` | 智能副驾 |
| `app.js:2236` / `2280` 档案 tagline | `个人 AI 副驾 · 本地优先 · 多模态认知` | 个人 AI 副驾 |
| `app.js:2281` 档案简介 | `我是小6，你的本地个人 AI 副驾。` | 本地个人 AI 副驾（已一致） |

## 3. 统一决策

采用单一规范表述 **「本地个人 AI 副驾」**，依据：
- `pyproject.toml:8` 官方描述 = `小6 · 本地个人 AI 副驾`
- `config.py:528` 系统提示词 = `个人智能副驾`（与 AI 人设一致）

即：产品名 = **小6**；品类描述 = **本地个人 AI 副驾**。

## 4. 执行（仅界面文案，零逻辑改动）

| 文件 | 行 | 改动 |
|------|-----|------|
| `index.html` | 6 | title → `小6 · 本地个人 AI 副驾` |
| `index.html` | 64 | `小6 · <b>本地个人 AI 副驾</b>` |
| `index.html` | 1116 | `本地个人 AI 副驾 · 隐私优先 · 离线可用` |
| `app.js` | 2232 | `本地个人 AI 副驾 · 本地档案` |
| `app.js` | 2236 | `本地个人 AI 副驾 · 本地优先 · 多模态认知` |
| `app.js` | 2280 | `本地个人 AI 副驾 · 本地优先 · 多模态认知` |

## 5. 纪律合规

- ✅ 仅修改界面可见文案，未触碰任何业务逻辑 / Runtime / Memory / EventBus / Tool。
- ✅ `config.py` 系统提示词（AI 人设）保持 `个人智能副驾` 不变（与规范同源，非 UI 品牌串）。
- ✅ `e2e_test.py:86` 测试语料（`您的智能副驾`）不动（测试数据，非 UI）。
- ✅ 未新增功能、未顺手优化、未扩大范围。

## 6. 验证

```
grep "智能指挥中枢|>AI OS<" index.html  →  无匹配（已清除）
```

## 7. 状态

✅ **P0 关闭** — 品牌唯一表达已确立。
