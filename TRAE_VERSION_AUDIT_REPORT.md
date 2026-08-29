# TRAE 版本统一审计报告

> 审计日期：2026-08-28 · 目标版本：**1.0.0**（产品规则：所有版本必须统一为 1.0.0）

---

## 一、版本源逐项核查

| 位置 | 状态 | 值 | 判定 |
|---|---|---|---|
| `G:\xiao6\VERSION` | ✅ 存在（git 追踪） | `1.0.0` | ✅ 合规 |
| `AI_BOOTSTRAP.md` | ✅ 存在 | `1.0.0` | ✅ 合规 |
| `xiao6-desktop/pet/package.json` | ✅ 存在（git 追踪） | `"version": "1.0.0"` | ✅ 合规 |
| `xiao6-ui/config.py:204` | ✅ 存在 | `APP_VERSION: str = "1.4.0"` | ❌ **违规** |
| `xiao6-ui/release/config.py:208` | ✅ 存在 | `APP_VERSION: str = "1.4.0"` | ❌ **违规（重复树）** |
| `xiao6-ui/xiao6-ui/config.py:208` | ✅ 存在 | `APP_VERSION: str = "1.4.0"` | ❌ **违规（重复树）** |
| 根 `package.json` | ❌ **不存在且未被 git 追踪** | — | ❌ 缺失 |
| `pyproject.toml` | ❌ **不存在且未被 git 追踪** | — | ❌ 缺失 |
| `xiao6-ui/package.json` | ❌ **不存在** | — | ❌ 缺失（Python 后端无 Node 包，但 Electron 桌面端依赖清单完整性受损） |
| UI 显示版本 | ⚠️ 前端资产 LOST/PARTIAL（见前端报告） | 无法验证 | ⚠️ 不可验证 |
| 启动信息 | ⚠️ 依赖 `config.APP_VERSION` | 实际会显示 1.4.0 | ❌ 间接违规 |
| README / 文档 | ⚠️ 多份 S 阶段报告存在 | 未发现 1.4.0 之外的声明性版本冲突 | ⚠️ 部分 |

---

## 二、违规详情

### VER-01（P1）：config.py 三处 `APP_VERSION = "1.4.0"`

- 顶层与两棵重复树均为 1.4.0，与 VERSION / AI_BOOTSTRAP.md / 桌面端 package.json 的 **1.0.0 冲突**
- 运行时展示（启动横幅、状态接口、UI About）几乎必然读取 `config.APP_VERSION` → 用户可见版本为 1.4.0
- 该值是"历史版本残留"，违反产品版本规则

### VER-02（P1）：版本声明源碎片化

版本号分散在 ≥4 类文件中，且**没有单一事实来源（SSOT）**：VERSION 文件存在但 config.py 不读取它（config.py:204 为字面量硬编码）。

### VER-03（P2）：`package.json` / `pyproject.toml` 缺失

- 无法以包元数据承载版本与依赖锁
- 与 Git 报告中"核心工程文件未入库"问题同源：项目连"这是什么项目"的机器可读声明都不完整

---

## 三、历史残留扫描

- 未发现 `v1.x`、`0.1.0` 等其他残留值（在已检查的追踪文件范围内）
- `1.4.0` 为唯一且三处重复的违规值

---

## 四、结论

| 维度 | 结论 |
|---|---|
| 目标 1.0.0 统一 | **未达成**（3 处 1.4.0 + 关键版本载体缺失） |
| SSOT | **不存在**（VERSION 无人读取） |
| 修复路径（供后续，不在本次执行） | config.py 改读 VERSION 文件；补 package.json/pyproject.toml 并声明 1.0.0；清除两棵重复树 |

**版本评级：❌ 未达标。**
