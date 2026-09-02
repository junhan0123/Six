# Task G · 版本一致性报告（VERSION_CONSISTENCY_REPORT）

> Sprint：Xiao6 UI Foundation Unification Sprint v1.0
> 目标：Version / About / README / 窗口标题 / Package / Build 单一版本号。

## 1. P0 来源

UI/UX Polish Sprint v1.0 审计报告 — **S-03「版本号不一致」**。

## 2. 审计发现（实证 file:line）

| 位置 | 值 | 说明 |
|------|-----|------|
| `config.py:149` | `APP_VERSION = "1.4.0"` | 后端权威版本（API `/api/version` 返回） |
| `index.html:903` | `id="settingsVersion">v1.0.0` | 设置页「关于」硬编码 |
| `index.html:1035` | `id="settingsUpdateVersion">v1.0.0` | 设置页「更新」硬编码 |
| `settings.js:721` | `'v' + (d.version \|\| '1.0.0')` | 版本回退值（但 catch 却用 `v1.4.0`，自相矛盾） |
| `settings.js:969` | `'v' + (d.version \|\| '1.0.0')` | 更新页版本回退值 |

矛盾点：用户静态可见 `v1.0.0`，后端返回 `1.4.0`，且 `settings.js:721` 的 try 分支回退 `1.0.0` 与 catch 分支 `1.4.0` 互相打架。

## 3. 执行（仅常量 / 文案）

| 文件 | 行 | 改动 |
|------|-----|------|
| `index.html` | 903 | `settingsVersion` 硬编码 → `v1.4.0` |
| `index.html` | 1035 | `settingsUpdateVersion` 硬编码 → `v1.4.0` |
| `settings.js` | 721 | 回退值 `'1.0.0'` → `'1.4.0'` |
| `settings.js` | 969 | 回退值 `'1.0.0'` → `'1.4.0'` |

统一为与后端权威 `config.py:149` 一致的 **1.4.0**。

## 4. 纪律合规

- ✅ 仅修改版本常量 / 文案；未改动 `/api/version` 接口或 `config.py` 权威源。
- ✅ 未引入新版本变量；未改构建 / 打包逻辑。
- ✅ 未新增功能。

## 5. 验证

```
grep "v1\.0\.0" index.html        →  无匹配（静态残留已清除）
grep "d.version || '1.4.0'" settings.js  →  721 / 969 均更新
```

## 6. 状态

✅ **P0 关闭** — 全站可见版本号统一为 `1.4.0`，与后端权威源一致。
