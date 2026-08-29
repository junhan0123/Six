# Icon 全量审计报告（ICON_AUDIT_REPORT）

> Xiao6 Icon System Migration Sprint v1.0 · Task A
> 审计范围：xiao6-ui 下全部小6自有 UI 源文件（HTML/JS/CSS），排除 python/ 打包文档、tests/、assets/ 等非 UI 目录。
> 方法：静态扫描（Python 脚本）+ 逐行人工复核分类。仅审计，不改码。

## 1. 总体统计

| 指标 | 数值 |
|------|------|
| 扫描 UI 源文件数 | 72 |
| 文件内 emoji 总出现数（含 AI 内容/状态文案） | 1134 |
| 其中判定为 **UI 图标 emoji** 的出现数 | 71 |
| Inline SVG 总数（4 文件） | 18 |
| `.ic` / `.zz-icon` 类使用次数 | 38（.ic=36, .zz-icon=2） |

## 2. 三类 Icon 体系并存现状（P0 核心病灶）

| 体系 | 载体 | 现状 | 问题 |
|------|------|------|------|
| A. Emoji | 字符串字形（💬⚙️🧠…） | 散落 16 个文件、约 71 处作为 UI 图标 | 无尺寸/颜色统一、主题不继承、可访问性差、跨平台渲染不一致 |
| B. Inline SVG | `<svg class="ic">` 描边图标 | index.html 内联 12 个定义 + app.js/hotspot.js 各 2–3 个 | 已有规范但仅覆盖部分语义，未覆盖 emoji 场景 |
| C. `.zz-icon` | ui2.css:606 填充基线 | 仅 2 处使用，尚未成为主入口 | 上轮落地但未接管，与 `.ic` 并存形成双基 |

**结论**：emoji（A）与 `.ic`（B）混用于同一导航栏（index.html HUD：🌤️📡⋮🧿⚙️ 为 emoji，rail 内 12 个为 `.ic`），`.zz-icon`（C）未接管 → 三体系并存，须收敛为唯一 `.zz-icon` 入口。

## 3. Emoji 作为 UI 图标明细（共 71 处，须迁移）

| # | 文件 | 行 | 字形 | 语义 | 迁移建议 | 风险 |
|---|------|-----|------|------|----------|------|
| 1 | app.js | 191 | ↩ | return | → `.zz-icon #return` | 中 |
| 2 | app.js | 191 | 📥 | download | → `.zz-icon #download` | 中 |
| 3 | app.js | 209 | 📥 | download | → `.zz-icon #download` | 中 |
| 4 | app.js | 411 | ⚙ | gear/settings | → `.zz-icon #gear` | 中 |
| 5 | app.js | 828 | 🔗 | link | → `.zz-icon #link` | 中 |
| 6 | app.js | 843 | 🔊 | volume | → `.zz-icon #volume` | 中 |
| 7 | app.js | 880 | 🔊 | volume | → `.zz-icon #volume` | 中 |
| 8 | app.js | 900 | ⚡ | lightning | → `.zz-icon #lightning` | 中 |
| 9 | app.js | 920 | ⚠ | warning | → `.zz-icon #warning` | 中 |
| 10 | app.js | 966 | 📷 | camera | → `.zz-icon #camera` | 中 |
| 11 | app.js | 1544 | 📅 | calendar | → `.zz-icon #calendar` | 中 |
| 12 | app.js | 1550 | 🔊 | volume | → `.zz-icon #volume` | 中 |
| 13 | app.js | 1573 | 🔥 | fire | → `.zz-icon #fire` | 中 |
| 14 | app.js | 1587 | ✅ | check | → `.zz-icon #check` | 中 |
| 15 | app.js | 1603 | 💡 | idea | → `.zz-icon #idea` | 中 |
| 16 | app.js | 1609 | 💡 | idea | → `.zz-icon #idea` | 中 |
| 17 | app.js | 2096 | ⚠ | warning | → `.zz-icon #warning` | 中 |
| 18 | capabilities-view.js | 64 | 🔍 | search | → `.zz-icon #search` | 中 |
| 19 | capabilities-view.js | 64 | ⚠ | warning | → `.zz-icon #warning` | 中 |
| 20 | capability-matrix.js | 14 | 🧠 | brain | → `.zz-icon #brain` | 中 |
| 21 | capability-matrix.js | 16 | 💾 | save | → `.zz-icon #save` | 中 |
| 22 | capability-matrix.js | 17 | 🤖 | robot | → `.zz-icon #robot` | 中 |
| 23 | capability-matrix.js | 19 | 🌐 | globe | → `.zz-icon #globe` | 中 |
| 24 | command-dock.js | 32 | 📷 | camera | → `.zz-icon #camera` | 中 |
| 25 | command-dock.js | 33 | ⚡ | lightning | → `.zz-icon #lightning` | 中 |
| 26 | command-palette.js | 41 | 📜 | scroll | → `.zz-icon #scroll` | 中 |
| 27 | command-palette.js | 42 | 📅 | calendar | → `.zz-icon #calendar` | 中 |
| 28 | command-palette.js | 44 | 🧠 | brain | → `.zz-icon #brain` | 中 |
| 29 | command-palette.js | 47 | ⚙ | gear/settings | → `.zz-icon #gear` | 中 |
| 30 | command-palette.js | 49 | 🎨 | palette/art | → `.zz-icon #palette` | 中 |
| 31 | command-palette.js | 53 | 🎯 | target | → `.zz-icon #target` | 中 |
| 32 | command-palette.js | 54 | ✅ | check | → `.zz-icon #check` | 中 |
| 33 | command-palette.js | 57 | ⌨ | keyboard | → `.zz-icon #keyboard` | 中 |
| 34 | glance-card.js | 16 | 🎯 | target | → `.zz-icon #target` | 中 |
| 35 | glance-card.js | 17 | 🧠 | brain | → `.zz-icon #brain` | 中 |
| 36 | glance-card.js | 19 | ℹ | info | → `.zz-icon #info` | 中 |
| 37 | hotspot.js | 67 | 🔊 | volume | → `.zz-icon #volume` | 中 |
| 38 | hotspot.js | 75 | ⚠ | warning | → `.zz-icon #warning` | 中 |
| 39 | hotspot.js | 81 | ⚠ | warning | → `.zz-icon #warning` | 中 |
| 40 | hotspot.js | 89 | 🔥 | fire | → `.zz-icon #fire` | 中 |
| 41 | hotspot.js | 212 | 🌐 | globe | → `.zz-icon #globe` | 中 |
| 42 | hotspot.js | 577 | 🔥 | fire | → `.zz-icon #fire` | 中 |
| 43 | hotspot.js | 826 | 🌐 | globe | → `.zz-icon #globe` | 中 |
| 44 | index.html | 71 | 💬 | chat | → `.zz-icon #chat` | 中 |
| 45 | index.html | 116 | 💬 | chat | → `.zz-icon #chat` | 中 |
| 46 | index.html | 146 | 📝 | edit/list | → `.zz-icon #edit` | 中 |
| 47 | index.html | 148 | 💡 | idea | → `.zz-icon #idea` | 中 |
| 48 | index.html | 149 | 🧠 | brain | → `.zz-icon #brain` | 中 |
| 49 | index.html | 150 | 📅 | calendar | → `.zz-icon #calendar` | 中 |
| 50 | index.html | 208 | 📜 | scroll | → `.zz-icon #scroll` | 中 |
| 51 | index.html | 214 | ⚙ | gear/settings | → `.zz-icon #gear` | 中 |
| 52 | index.html | 334 | 🧠 | brain | → `.zz-icon #brain` | 中 |
| 53 | index.html | 393 | ⚙ | gear/settings | → `.zz-icon #gear` | 中 |
| 54 | index.html | 790 | 📍 | pin | → `.zz-icon #pin` | 中 |
| 55 | index.html | 837 | 🧠 | brain | → `.zz-icon #brain` | 中 |
| 56 | index.html | 872 | 💾 | save | → `.zz-icon #save` | 中 |
| 57 | index.html | 876 | 📥 | download | → `.zz-icon #download` | 中 |
| 58 | index.html | 884 | ♻ | recycle | → `.zz-icon #recycle` | 中 |
| 59 | index.html | 1162 | ✨ | sparkle | → `.zz-icon #sparkle` | 中 |
| 60 | memory-query.js | 29 | 🔍 | search | → `.zz-icon #search` | 中 |
| 61 | memory.js | 132 | ▶ | play | → `.zz-icon #play` | 中 |
| 62 | memory.js | 133 | 📁 | folder | → `.zz-icon #folder` | 中 |
| 63 | memory.js | 145 | 📄 | file | → `.zz-icon #file` | 中 |
| 64 | memory.js | 502 | 👤 | user | → `.zz-icon #user` | 中 |
| 65 | scene.js | 32 | 📊 | chart | → `.zz-icon #chart` | 中 |
| 66 | scene.js | 55 | ▶ | play | → `.zz-icon #play` | 中 |
| 67 | tasks.js | 123 | 📜 | scroll | → `.zz-icon #scroll` | 中 |
| 68 | terminal-stream.js | 10 | 📜 | scroll | → `.zz-icon #scroll` | 中 |
| 69 | userprofile.js | 123 | 🧠 | brain | → `.zz-icon #brain` | 中 |
| 70 | weather-modal-preview.html | 70 | 🔊 | volume | → `.zz-icon #volume` | 中 |
| 71 | weather.js | 103 | 📍 | pin | → `.zz-icon #pin` | 中 |

## 4. 排除项（非 UI 图标，本 Sprint 不处理）

| 文件 | 行 | 字形 | 性质 | 理由 |
|------|-----|------|------|------|
| app.js | 101 | 📷 | 逻辑/域数据 | cleanReply 清洗字符集（AI 输出去 emoji，逻辑非 UI） |
| app.js | 358 | 🌐 | 逻辑/域数据 | AI 内容检测正则（舆情/告警前缀，逻辑非 UI） |
| hotspot.js | 796 | 🌐 | 逻辑/域数据 | AI 内容检测正则（舆情/告警前缀，逻辑非 UI） |
| weather.js | 21 | ☀ | 逻辑/域数据 | 天气语义映射表（'晴':'☀️' 等域数据，非控件） |
| weather-modal-preview.html | 53 | ☀ | 逻辑/域数据 | 天气展示（☀️ 域数据，非控件） |
| weather-modal-preview.html | 62 | ☀ | 逻辑/域数据 | 天气展示（☀️ 域数据，非控件） |
| weather-modal-preview.html | 67 | 🌙 | 逻辑/域数据 | 天气展示（🌙 域数据，非控件） |

> 说明：上述 emoji 位于 `cleanReply` 清洗正则、AI 内容检测正则、天气语义映射表中，属**业务逻辑/域数据**，非界面控件图标。修改将触碰业务逻辑/数据映射（违反纪律红线），故明确排除，记录为观察项。

## 5. Inline SVG 明细（既有 `.ic` 资产，保留并接管）

| 文件 | Inline SVG 数 | 说明 |
|------|---------------|------|
| app.js | 3 | 运行时注入的 `.ic` 图标 |
| hotspot.js | 2 | 运行时注入的 `.ic` 图标 |
| index.html | 12 | 12 个 `.ic` 图标定义（box/plus/layers/volume/frame/image/grid/monitor/mic/send/close/sliders） |
| ui2.css | 1 | 运行时注入的 `.ic` 图标 |

## 6. 重复 Icon / 缺失 Icon 分析

- **重复**：`volume`（🔊）可由既有 `.ic` speaker 接管；`monitor`（🖥️）可由既有 `.ic` monitor 接管；多处 `📅/🧠/🔊` 重复出现，属同语义多实例（正常）。
- **缺失（emoji 语义无现成 `.ic` 覆盖，须新增 `.zz-icon` 定义）**：chat、edit、idea/bulb、brain、calendar、scroll、gear、pin、save、inbox、recycle、sparkle、bolt、warning、camera、flame、check、target、search、link、robot、globe、palette、keyboard、info、signal、play、folder、file、user、chart、receipt、puzzle、clock、person、id、kebab、wrench 等约 38 个语义。

## 7. 按文件分布（UI 图标 emoji）

| 文件 | UI 图标 emoji 数 |
|------|------------------|
| app.js | 17 |
| index.html | 16 |
| command-palette.js | 8 |
| hotspot.js | 7 |
| capability-matrix.js | 4 |
| memory.js | 4 |
| glance-card.js | 3 |
| capabilities-view.js | 2 |
| command-dock.js | 2 |
| scene.js | 2 |
| memory-query.js | 1 |
| tasks.js | 1 |
| terminal-stream.js | 1 |
| userprofile.js | 1 |
| weather-modal-preview.html | 1 |
| weather.js | 1 |

## 8. P1 记录（发现但不处理，待 Review 门控）

- **组件库**：`.ic` 12 个定义散落 index.html 内联，未抽为 symbol 精灵；建议 P1 抽为 `<svg><symbol>` 精灵并全站 `<use>` 引用（本 Sprint 不重构）。
- **Overlay / 快捷键 / 主题 / 引导 / 搜索 / 首页信息架构**：本次审计发现相关 emoji/图标散落，但均属 P1 范围，按纪律仅记录不处理。
- **天气域图标**：weather.js / weather-modal-preview.html 的天气 emoji 为域数据展示，建议 P1 评估天气专用图标组件（非本 Sprint 控件图标迁移范围）。

## 9. 审计结论

小6当前并存 **emoji / inline SVG(`.ic`) / `.zz-icon`** 三套图标表达。P0 须完成：
1. 将 71 处 emoji UI 图标替换为 `.zz-icon` SVG（映射见 ICON_MAPPING_TABLE.md）；
2. 以 `.zz-icon` 为唯一规范（`.ic` 降级为别名），消除双基（见 ICON_USAGE_SPEC.md）；
3. 保留既有 12 个 `.ic` 资产，通过别名零改动接管。

> 交付物：本文件 + ICON_MAPPING_TABLE.md + ICON_USAGE_SPEC.md + 迁移后 ICON_MIGRATION_VERIFY.md + ICON_SYSTEM_FINAL_REPORT.md