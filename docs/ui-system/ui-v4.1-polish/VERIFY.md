# UI-v4.1 Product Polish Sprint · Verify & Acceptance

## 一、技术验证

| 项 | 命令/方法 | 结果 |
|---|---|---|
| JS 语法 | `node --check` × 7 | ✅ 7/7 OK |
| CSS 括号平衡 | `{` vs `}` 计数 | ✅ 169 / 169 BALANCED |
| 线上资源 HTTP | curl `/v4/` 等 | ✅ 全 200 |
| 类/id 一致性 | getElementById ↔ HTML id | ✅ PASS（无悬空引用） |
| 旧 UI 隔离 | grep `app.js/main-orb.js/galaxy/three` | ✅ PASS（仅"不加载"注释） |
| 真实数据流通 | `/api/memories·goals·knowledge` | ✅ 记忆 34 / 目标 7 / 知识 45 |
| 新元素已上线 | curl 实时 HTML/CSS | ✅ `orb__sat`/`topbar__pulse`/`sheet__lead`/新 keyframes 均已服务 |

## 二、改动点落地核查（grep 线上资源）

- `orb__sat`、`topbar__pulse`、`topbar__whisper` 出现在 `/v4/` 实时 HTML ✅
- `core-shimmer`、`sat-orbit`、`.orb__sat`、`sheet__lead`、`is-sending`、`send-pop` 出现在 `/v4/ui-v4.css` ✅
- `js/overlay.js` 含 `LEAD` 映射与 `insertAdjacentHTML('beforeend'` ✅
- `js/intent-line.js` 含 `is-sending` 切换 ✅
- `js/boot.js` 已无 `connectionStatus`/`setConnection` 死代码 ✅

## 三、红线核查

| 红线 | 结果 |
|---|---|
| 不重构架构 | ✅ 仅表现层 |
| 不新增功能 | ✅ 无新能力 |
| 不改 Runtime / 后端 | ✅ 仅消费既有接口 |
| 不新增事件 | ✅ `is-sending` 为纯 CSS 类 |
| 不恢复旧导航 / Galaxy | ✅ 隔离确认 |
| 不引入 Dashboard / 卡片墙 | ✅ Context 三句 + Overlay 行式 |
| 不做多页面 | ✅ 单空间 + Overlay |

## 四、最终验收（对照 spec 九条）

| # | 验收标准 | 结论 | 对应打磨 |
|---|---|---|---|
| 1 | 一个界面 | ✅ | 单空间未动 |
| 2 | 一个 AI Core | ✅ | 光核增强：内禀光泽流转 + 环绕粒子 + 八态强度分档 |
| 3 | 一个输入入口 | ✅ | Intent 聚焦柔光 + 发送入场 + 提交微交互 |
| 4 | 无页面切换 | ✅ | Overlay 仍为同空间浮层 |
| 5 | 无 Dashboard | ✅ | 三句语义 + 行式，零数字卡片 |
| 6 | 无太阳系首页 | ✅ | Galaxy 隔离确认 |
| 7 | 无聊天软件感 | ✅ | 顶部去 chrome，品牌仅「小6」+ 活体存在点 |
| 8 | 有未来科技感 | ✅ | shimmer/satellite/环扫/微动效，安静而精密 |
| 9 | 有真实功能连接 | ✅ | 记忆 34 / 目标 7 / 知识 45 实时驱动 |

## 五、第一眼体验（主观目标）

> 打开小6：顶部仅「小6」+ 一枚与整屏同色呼吸的存在点，下方是安静呼吸的光核与「小6 / 在这里，随时开始」，三句他此刻的理解，底部一行意图线。
> 用户感知从「这是一个软件界面」转向「**这是我的 AI**」——顶部不再有标题栏 chrome，光核有了内部流转与环绕生命，Overlay 是小6展开给你看的一面而非菜单。

## 六、已知限制 / 后续可选项

- 环绕粒子与 shimmer 在 `prefers-reduced-motion` 下自动停（全局降级规则已覆盖）。
- World Graph 仅在 ⌘4/世界点唤出，符合"保持隐藏、仅入口"；如需更强"理解世界"叙事可后续单独 sprint。
- 未做跨浏览器像素级回归（环境无 GUI 浏览器）；已用静态 + 线上资源核查覆盖。
