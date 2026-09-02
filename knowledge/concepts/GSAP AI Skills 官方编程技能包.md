---
id: know-gsap-ai-skills-greensock-ai
type: concept
---
# GSAP AI Skills — GreenSock 官方 AI 编程技能包

## 📌 项目概述

**GSAP AI Skills** 是 GreenSock（GSAP 动画引擎的开发商）官方发布的 AI 编程技能包。它教导 AI 编码代理（Agent）如何正确使用 GSAP，涵盖核心 API、时间轴、ScrollTrigger、插件、React/Vue/Svelte 集成、性能优化等。

### 基本信息

- **仓库**: https://github.com/greensock/gsap-skills
- **Stars**: 12,752+（截至 2026-07-31）
- **Forks**: 752
- **协议**: MIT
- **创建时间**: 2026-03-04
- **开发商**: GreenSock（Webflow 旗下）
- **格式**: Agent Skills（兼容 Cursor、Claude Code、Codex、Copilot、Windsurf、Gemini Antigravity 等 40+ 代理）

## 🔑 核心要点

### GSAP 现在完全免费

Webflow 收购 GSAP 后，所有 formerly Club GSAP 插件（**SplitText**、**MorphSVG** 等）全部免费开源，包括商业用途。只需从公共 `gsap` npm 包安装，无需 Club 会员、无需 `.npmrc` 认证、无需私有仓库。

### 安装方式

```bash
# 通用安装（推荐，兼容 40+ 代理）
npx skills add https://github.com/greensock/gsap-skills

# Claude Code 专用
/plugin marketplace add greensock/gsap-skills

# Cursor 专用
# Settings → Rules → Add Rule → Remote Rule (Github) → greensock/gsap-skills
```

## 📚 技能模块（8 个）

| 技能 | 覆盖内容 |
|------|----------|
| **gsap-core** | 核心 API：`gsap.to()` / `from()` / `fromTo()`、缓动、时长、交错、默认值 |
| **gsap-timeline** | 时间轴：序列、position 参数、标签、嵌套、播放控制 |
| **gsap-scrolltrigger** | ScrollTrigger：滚动驱动动画、固定(pinning)、scrub、触发器、刷新与清理 |
| **gsap-plugins** | 插件：ScrollToPlugin、ScrollSmoother、Flip、Draggable、Inertia、Observer、SplitText、ScrambleText、SVG/物理插件、CustomEase、EasePack、GSDevTools 等 |
| **gsap-utils** | 工具函数：clamp、mapRange、normalize、interpolate、random、snap、toArray、selector、wrap、pipe |
| **gsap-react** | React：useGSAP hook、refs、`gsap.context()`、清理、SSR |
| **gsap-performance** | 性能：transform 替代 layout 属性、will-change、批量操作、ScrollTrigger 优化 |
| **gsap-frameworks** | Vue、Svelte 等：生命周期、选择器作用域、卸载时清理 |

## 💡 典型使用模式

```javascript
// 1. 导入和插件注册（应用初始化时一次）
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
gsap.registerPlugin(ScrollTrigger);

// 2. 单个动画 — 优先使用 transform 别名和 autoAlpha
gsap.to(".box", { x: 100, autoAlpha: 1, duration: 0.6, ease: "power2.inOut" });

// 3. 时间轴序列 — 优先于链式 delay
const tl = gsap.timeline({ defaults: { duration: 0.5, ease: "power2" } });
tl.to(".a", { x: 100 })
  .to(".b", { y: 50 }, "+=0.2")
  .to(".c", { opacity: 0 }, "-=0.1");

// 4. ScrollTrigger — 绑定到时间轴或顶层 tween
const tl2 = gsap.timeline({
  scrollTrigger: {
    trigger: ".section",
    start: "top center",
    end: "bottom center",
    scrub: true
  }
});
tl2.to(".panel", { x: 100 })
   .to(".panel", { rotation: 5, duration: 0.7 });
// DOM/布局变更后: ScrollTrigger.refresh();

// 5. React: useGSAP + scope + cleanup
// useGSAP(() => { gsap.to(ref.current, { x: 100 }); }, { scope: containerRef });
```

## 🎯 适用场景

1. **网页动画开发** — GSAP 是业界事实标准的 JS 动画库
2. **滚动驱动动画** — ScrollTrigger 是滚动动画的最佳方案
3. **React/Vue/Svelte 集成** — 官方提供的框架适配技能
4. **AI 辅助开发** — 安装技能包后，AI 代理能生成正确的 GSAP 代码
5. **性能敏感项目** — gsap-performance 技能确保使用最佳实践

## 🔗 相关笔记

- PPT Master AI 原生 PowerPoint 生成
- [[CRMEB 开源商城系统调研报告]]
- World Monitor 贾维斯系统免费复刻攻略
- Mate-Engine 桌面虚拟宠物
- ToolKnit 多功能工具箱
