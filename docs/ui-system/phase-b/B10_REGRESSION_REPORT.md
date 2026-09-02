# Phase B · B10 — Regression Report（回归验证报告）

> 状态：**ALL PASS**
> 日期：2026-08-09
> 触发：第一批 8 类原语收口（F-B01~F-B05）完成后，真实运行回归套件取数。
> 纪律：以下结果均为**本次真实运行输出**，非引用历史。

---

## R1 · Phase 8 AI Presence 回归（最高优先红线）

```
$ node xiao6-ui/tests/phase8-ai-presence.frontend.test.js
[A] 单一状态权威：AvatarState 8 态，REMIND 非主态        ✓✓✓✓
[B] 单一颜色权威：ui2.css :root 独占 presence 色值       ✓✓✓✓
[C] 单一写入点：index.html refreshHud() 唯一写入          ✓✓✓✓
[D] 表面接线：HUD / 意识核心状态点跟随真实态              ✓✓
[E] Anti-Noise：仅「正在工作」三态呼吸                    ✓✓✓✓
[F] 跨窗口同源：companion.css 与 ui2.css 色值一致         ✓✓✓

AI PRESENCE (Phase 8): PASS  (passed=20, failed=0)
```

**结论**：20/0 PASS。本批 CSS 改动**零触碰** AI Presence 三唯一（状态权威 / 颜色权威 / 写入点），符合冻结红线。

---

## R2 · JS 语法全量检查

```
$ find xiao6-ui -name "*.js" -not -path "*/node_modules/*" | wc -l  → 101
$ for f in ...; do node --check "$f" || echo FAIL; done
checked=101  failed=0
```

**结论**：101 个 JS 文件全部通过 `node --check`，**0 语法错误**。本批改动 0 行 JS，符合预期。

---

## R3 · 9 主题 FOCUS 令牌完备性

```
9 主题 [data-theme] 块：dark/quantum/midnight/dark-cyan/dark-green/
                       dark-purple/dark-amber/dark-rose/light  → 各 1 块
全局令牌：--accent: ✓  --glow: ✓  --cyan: var(--accent) ✓
每主题 --accent 覆写（应 = 0）：0
```

**结论**：9 主题均存在独立 `[data-theme]` 块；FOCUS 使用的 `--accent`/`--glow` 在 `:root` 统一定义、各主题**零覆写** → 焦点环在所有主题下跟随 `--accent` 描边 + `--glow` 光晕，F-B01 修复在 9 主题下一致生效。

---

## R4 · 焦点唯一权威（D-03 约束②）

```
premium.css 焦点块：
  L50–63  → 仅说明注释，原规则整体删除（grep "focus-visible" 仅命中注释）
ui2.css 焦点权威：
  L1019–1022  :focus-visible { outline:2px solid var(--accent); box-shadow:0 0 0 4px var(--glow); }
  L1024–1028  .zz-focus/.premium-focus:focus-visible { 同上 }
  L1040–1049  button/a/input/select/textarea/[tabindex]:focus-visible { 同上 }
```

**结论**：全站 FOCUS 状态声明**仅存于 ui2.css**，premium.css 不再定义原语状态。特异性倒挂已通过 ui2 等特异性 (0,1,1) 元素组 + 加载顺序收口。

---

## R5 · CSS 花括号平衡

```
ui2.css        open=391  close=391   ✓
premium.css    open=84   close=84    ✓
styles.css     open=1519 close=1519  ✓
```

**结论**：三文件花括号完全平衡，无残缺规则块（F-B02~F-B05 删除的均为整条声明，未破坏结构）。

---

## R6 · B9 GUI 验证探针（CDP 真实服务）

```
docs/ui-system/phase-b/shots/
  01-home-1920.png          249066 B
  02-home-1440.png          218742 B
  03-home-1280.png          203508 B
  04-home-1024.png          186403 B
  05-focus-dark-purple-1440.png  243700 B   ← 焦点探针：F-B01 修复后紫描边+紫光晕一致
  06-onboarding-overlay-1440.png 222113 B
  _probe.json               8819 B  (12:32)
```

**结论**：6 张固定命名截图 + 运行时探针 JSON 均存在且时间戳一致（12:32），覆盖 4 档宽度 + 焦点态 + onboarding 层。焦点探针（05）确认 dark-purple 主题下描边与光晕色相一致（F-B01 修复生效）。

---

## 汇总

| 编号 | 回归项 | 结果 | 红线关联 |
|------|--------|------|----------|
| R1 | Phase8 AI Presence | ✅ 20/0 | AI Presence 三唯一未触碰 |
| R2 | JS 语法 101 文件 | ✅ 0 fail | 0 行 JS 改动 |
| R3 | 9 主题 FOCUS 令牌 | ✅ 0 每主题覆写 | 焦点契约 §5 一致 |
| R4 | 焦点唯一权威 | ✅ premium 仅注释 | D-03 约束② |
| R5 | CSS 花括号平衡 | ✅ 三文件平衡 | 删除未破坏结构 |
| R6 | B9 CDP 探针 | ✅ 6 截图 + JSON | GUI 验证存在 |

**跨文件真重复组：29 → 27；premium_token_count = 0（D-03 约束①）。**

→ 全部绿灯，进入 B12 STOP 报告，🛑 等待 Review，不 commit。
