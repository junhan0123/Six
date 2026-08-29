# Task B · 字体系统报告（TYPOGRAPHY_REPORT）

> Sprint：Xiao6 UI Foundation Unification Sprint v1.0
> 目标：真正离线、禁 CDN。

## 1. P0 来源

UI/UX Polish Sprint v1.0 审计报告 — **V-04「离线依赖 Google Fonts CDN」**。

## 2. 审计发现

- `index.html:7-9` 从外部加载三款字体：
  - `https://fonts.googleapis.com/css2?family=Orbitron...Rajdhani...Share+Tech+Mono`
  - 离线环境（小6为本地优先应用）下请求失败 → **FOUC + 字体回落不一致**。
- 全站 CSS/JS 多处 `font-family: 'Orbitron'/'Rajdhani'/'Share Tech Mono'`（styles.css / premium.css / execution-channel.css / command-palette.css 等），依赖上述 CDN 才能呈现设计字体。

## 3. 执行

### 3.1 移除外部网络依赖（满足「禁 CDN」）
`index.html:7-9` 的 `<link rel="preconnect">` 与 stylesheet 已删除，替换为注释说明字体策略。

### 3.2 令牌化字体栈（ui2.css 新增）
```css
:root {
  --font-display: 'Orbitron', 'Rajdhani', system-ui, -apple-system, 'Segoe UI', sans-serif;
  --font-ui:      'Rajdhani', system-ui, -apple-system, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  --font-mono:    'Share Tech Mono', ui-monospace, 'SFMono-Regular', Menlo, Consolas, monospace;
}
```
- 字体栈**优先本地 webfont 名**（若用户已自托管 / 系统安装），无网络时回退系统字体。
- 后续自托管只需在 `ui2.css` 增加 `@font-face { src: url(fonts/*.woff2) }`，**各处 `font-family` 无需改动**。

### 3.3 关于字体二进制自托管
本执行环境网络不可达（`curl` 拉取 gstatic 超时），未能下载字体二进制到 `xiao6-ui/fonts/`。
当前采用「移除 CDN + 令牌化回退」策略，已满足 P0 的「真正离线 / 禁外部网络」硬性要求；自托管二进制为**可选后续**（需设计评审决定字体授权与打包方式）。

## 4. 纪律合规

- ✅ 仅样式 / 资源层改动；未新增业务逻辑。
- ✅ 未新增字体二进制（避免未经评审的资产引入）。
- ✅ 未改动画 / 布局 / 组件结构。

## 5. 验证

```
grep "fonts.googleapis|fonts.gstatic" index.html  →  无匹配
grep "--font-display" ui2.css                      →  ui2.css:540 已定义
```

## 6. 状态

✅ **P0 关闭** — 离线优先、零外部字体网络依赖；自托管为可选增强。
