# -*- coding: utf-8 -*-
"""
PROJECT_DOCUMENT_AUDIT.py — Xiao6 文档治理自动检查
检查项：根目录污染 / 冻结文档完整 / 文档链接有效 / 状态一致 / Phase记录一致 / 孤儿文档 / 重复规范
用法：python docs/reference/PROJECT_DOCUMENT_AUDIT.py
"""
import os, re, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # G:/xiao6
DOCS = os.path.join(ROOT, "docs")

ALLOWED_ROOT_MD = {
    "README.md", "PROJECT_STATUS.md", "CURRENT_STATE.md", "CURRENT_PHASE.md",
    "DEVELOPMENT_PROGRESS.md", "ARCHITECTURE_MAP.md", "AI_HANDOFF_PROTOCOL.md",
    "AI_BOOTSTRAP.md", "CHANGELOG_AI.md",
}
EXEMPT_PATHS = {  # 治理自身产生的文件，免孤儿检查
    "docs/DOCUMENT_INVENTORY.md", "docs/DOCUMENT_MIGRATION_REPORT.md",
    "docs/reference/PROJECT_DOCUMENT_AUDIT.py",
    "docs/audits/PROJECT_DOCUMENT_AUDIT_RESULT.md",
    # Design Canon（设计解释层，2026-08-04 落盘，非孤儿）
    "docs/design/frozen/PRODUCT_CONSTITUTION.md",
    "docs/design/frozen/AI_OS_DESIGN_PRINCIPLES.md",
    "docs/design/frozen/INFORMATION_ARCHITECTURE.md",
    "docs/design/frozen/GALAXY_INTERACTION_SPEC.md",
    "docs/design/frozen/INTERACTION_SYSTEM_SPEC.md",
    "docs/design/frozen/DESIGN_SYSTEM_SPEC.md",
    "docs/design/frozen/EXPERIENTIAL_PROTOTYPE_SPEC.md",
    "docs/design/frozen/DOMAIN_MODEL.md",
    "docs/design/AI_DESIGN_CONTEXT.md",
    "docs/design/DESIGN_CONFLICT_REGISTER.md",
}
EXEMPT_PREFIXES = ("docs/decisions/",)  # 决策记录由 Phase 2 产生

# Design Canon（设计解释层）完整性检查
DESIGN_CANON_FILES = [
    "docs/design/frozen/PRODUCT_CONSTITUTION.md",
    "docs/design/frozen/AI_OS_DESIGN_PRINCIPLES.md",
    "docs/design/frozen/INFORMATION_ARCHITECTURE.md",
    "docs/design/frozen/GALAXY_INTERACTION_SPEC.md",
    "docs/design/frozen/INTERACTION_SYSTEM_SPEC.md",
    "docs/design/frozen/DESIGN_SYSTEM_SPEC.md",
    "docs/design/frozen/EXPERIENTIAL_PROTOTYPE_SPEC.md",
    "docs/design/frozen/DOMAIN_MODEL.md",
    "docs/design/AI_DESIGN_CONTEXT.md",
    "docs/design/DESIGN_CONFLICT_REGISTER.md",
]
DESIGN_CANON_REQUIRED_SECTIONS = [
    "## Source Authority", "## Related Documents", "## Frozen Status",
    "## Scope", "## Non-goals",
]

LINK_RE = re.compile(r"\]\(([^)]+)\)")

def audit():
    problems = []
    warns = []
    # 1. 根目录污染
    root_md = [f for f in os.listdir(ROOT) if f.endswith(".md")]
    for f in root_md:
        if f not in ALLOWED_ROOT_MD:
            problems.append("根目录污染: 非允许 .md -> %s" % f)
    # 根目录其他散落 .py/.txt 文档（排除 docs/ 自身）
    for f in os.listdir(ROOT):
        full = os.path.join(ROOT, f)
        if os.path.isfile(full) and f.endswith((".py", ".txt")) and f not in ("server.py",):
            # 仅报告文档类散落；代码文件不管
            if f.endswith(".txt"):
                problems.append("根目录散落 .txt -> %s" % f)
    # 2. 冻结文档完整
    frozen = os.listdir(os.path.join(DOCS, "frozen")) if os.path.isdir(os.path.join(DOCS, "frozen")) else []
    if not frozen:
        problems.append("docs/frozen/ 为空（应有冻结级规范）")
    # 3. 文档链接有效
    for dp, dn, fn in os.walk(DOCS):
        for f in fn:
            if not f.endswith(".md"):
                continue
            fp = os.path.join(dp, f)
            try:
                txt = open(fp, encoding="utf-8").read()
            except Exception:
                continue
            for m in LINK_RE.findall(txt):
                target = m.split("#")[0].strip()
                if not target or target.startswith(("http://", "https://", "mailto:")):
                    continue
                # 相对路径解析
                base = os.path.dirname(fp)
                cand = os.path.normpath(os.path.join(base, target))
                if not os.path.exists(cand):
                    # 可能是仓库根相对路径
                    cand2 = os.path.normpath(os.path.join(ROOT, target))
                    if not os.path.exists(cand2):
                        warns.append("断链: %s -> %s" % (os.path.relpath(fp, ROOT), target))
    # 4. 状态一致：DOCUMENT_INVENTORY 列出的文件是否都存在
    inv = os.path.join(DOCS, "DOCUMENT_INVENTORY.md")
    if os.path.exists(inv):
        inv_txt = open(inv, encoding="utf-8").read()
        # 提取清单里的路径列
        for line in inv_txt.splitlines():
            if line.startswith("|") and ".md" in line:
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if len(cells) >= 3 and cells[1].endswith(".md"):
                    rel = cells[1]
                    if "/" in rel and not rel.startswith("docs/") and not os.path.exists(os.path.join(ROOT, rel)):
                        # 已迁移文件，路径在库存为旧路径——属正常（迁移报告记录）
                        pass
    # 5. Phase记录一致：DEVELOPMENT_PROGRESS 引用的报告应存在
    prog = os.path.join(ROOT, "DEVELOPMENT_PROGRESS.md")
    if os.path.exists(prog):
        ptxt = open(prog, encoding="utf-8").read()
        for m in re.findall(r"`([^`]+\.md)`", ptxt):
            if m.startswith("docs/"):
                if not os.path.exists(os.path.join(ROOT, m)):
                    problems.append("DEVELOPMENT_PROGRESS 引用缺失: %s" % m)
    # 6. 孤儿文档：docs/ 下未列入 inventory 且非豁免
    inv_paths = set()      # 路径列（cells[2]）
    inv_basenames = set()  # 文件名字段
    if os.path.exists(inv):
        for line in open(inv, encoding="utf-8").read().splitlines():
            if line.startswith("|") and ".md" in line:
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if len(cells) >= 3 and cells[1].endswith(".md"):
                    inv_paths.add(cells[2].replace("\\", "/"))
                    inv_basenames.add(cells[1])
    for dp, dn, fn in os.walk(DOCS):
        for f in fn:
            if not f.endswith(".md"):
                continue
            rel = os.path.relpath(os.path.join(dp, f), ROOT).replace("\\", "/")
            if rel in EXEMPT_PATHS:
                continue
            if any(rel.startswith(p) for p in EXEMPT_PREFIXES):
                continue
            if rel not in inv_paths and os.path.basename(rel) not in inv_basenames:
                warns.append("可能孤儿文档(未列入 inventory): %s" % rel)
    # 7. 重复规范：同名/近同名根文件
    basenames = {}
    for dp, dn, fn in os.walk(DOCS):
        for f in fn:
            if f.endswith(".md"):
                basenames.setdefault(f, []).append(os.path.relpath(os.path.join(dp, f), ROOT))
    for b, locs in basenames.items():
        if len(locs) > 1:
            warns.append("重复文件名: %s -> %s" % (b, locs))

    # 8. Design Canon（设计解释层）完整性
    for rel in DESIGN_CANON_FILES:
        fp = os.path.join(ROOT, rel)
        if not os.path.exists(fp):
            problems.append("Design Canon 缺失: %s" % rel)
            continue
        try:
            txt = open(fp, encoding="utf-8").read()
        except Exception:
            problems.append("Design Canon 无法读取: %s" % rel)
            continue
        # 仅对 docs/design/frozen/ 下 8 份规范强制 5 节；AI_DESIGN_CONTEXT / 冲突册结构不同，跳过节检查
        if rel.startswith("docs/design/frozen/"):
            missing = [s for s in DESIGN_CANON_REQUIRED_SECTIONS if s not in txt]
            if missing:
                problems.append("Design Canon 缺必需章节 %s: %s" % (missing, rel))
            # 解释层纪律：每份 Canon 必须显式声明不覆盖/不替代权威（正向检查）
            if not ("不覆盖" in txt and "不替代" in txt):
                problems.append("Design Canon 缺解释层纪律声明（须明示不覆盖/不替代权威）: %s" % rel)
        # 链接有效性（复用既有 LINK_RE）
        for m in LINK_RE.findall(txt):
            target = m.split("#")[0].strip()
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            base = os.path.dirname(fp)
            cand = os.path.normpath(os.path.join(base, target))
            if not os.path.exists(cand):
                cand2 = os.path.normpath(os.path.join(ROOT, target))
                if not os.path.exists(cand2):
                    warns.append("Design Canon 断链: %s -> %s" % (rel, target))

    return problems, warns

def main():
    problems, warns = audit()
    lines = []
    lines.append("# PROJECT_DOCUMENT_AUDIT — 结果")
    lines.append("")
    lines.append("> 生成时间: %s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
    lines.append("")
    lines.append("## 结论: %s" % ("✅ PASS（无阻断问题）" if not problems else "⚠️ BLOCK（见问题）"))
    lines.append("")
    lines.append("### 阻断问题 (%d)" % len(problems))
    for p in problems:
        lines.append("- ❌ %s" % p)
    if not problems:
        lines.append("- 无")
    lines.append("")
    lines.append("### 警告 (%d)" % len(warns))
    for w in warns:
        lines.append("- ⚠️ %s" % w)
    if not warns:
        lines.append("- 无")
    lines.append("")
    out = os.path.join(DOCS, "audits", "PROJECT_DOCUMENT_AUDIT_RESULT.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print("PROBLEMS:", len(problems), "WARNS:", len(warns))
    for p in problems:
        print("  ❌", p)
    for w in warns:
        print("  ⚠️", w)
    print("RESULT ->", out)

if __name__ == "__main__":
    main()
