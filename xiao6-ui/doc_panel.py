"""庄周 · 文档面板（本地文档浏览与阅读，纯标准库实现）。

用途：浏览 XIAO6_DOC_DIR 指向的本地文档目录，并提供单文档正文读取。
零外部依赖；对 PDF 采用优雅降级——未安装 PyPDF2 时只返回元信息，绝不抛异常。
路径经过严格校验，杜绝目录穿越（".." / 绝对路径）攻击。
"""

import os
from datetime import datetime

# 文档根目录：默认与脚本同级的 docs/，可用环境变量 XIAO6_DOC_DIR 覆盖。
BASE = os.path.dirname(os.path.abspath(__file__))
DOC_DIR_PATH = os.path.join(BASE, os.environ.get("XIAO6_DOC_DIR", "docs"))
os.makedirs(DOC_DIR_PATH, exist_ok=True)

# 允许阅读的扩展名。
ALLOWED_EXT = {".md", ".txt", ".json", ".pdf", ".csv", ".log"}

# 纯文本类扩展名（直接按 UTF-8 读取正文）。
TEXT_EXT = {".md", ".txt", ".csv", ".log", ".json"}


def _iso(ts):
    """把时间戳转为 ISO 字符串；失败兜底为空串。"""
    try:
        return datetime.fromtimestamp(ts).isoformat()
    except Exception:
        return ""


def _safe_join(name):
    """把文档名安全拼接到文档目录并返回绝对路径。

    校验规则：
      - 拒绝含 ".." 的路径；
      - 拒绝绝对路径或 /、\\ 开头；
      - 归一化后必须仍位于 DOC_DIR_PATH 之下。
    不合法返回 None。
    """
    if not name:
        return None
    if ".." in name.replace("\\", "/").split("/"):
        return None
    if os.path.isabs(name):
        return None
    if name.startswith("/") or name.startswith("\\"):
        return None
    # 归一化并解析为绝对路径
    try:
        cand = os.path.normpath(os.path.join(DOC_DIR_PATH, name))
    except Exception:
        return None
    # 确保结果严格位于文档目录内（防穿越）
    try:
        common = os.path.commonpath([DOC_DIR_PATH, cand])
    except Exception:
        return None
    if common != os.path.normpath(DOC_DIR_PATH):
        return None
    return cand


def list_docs():
    """遍历文档目录（仅一层），返回允许扩展名文件清单。

    每项：{"name": 相对路径, "size": 字节, "mtime": ISO, "ext": 扩展名}。
    按修改时间倒序排列。
    """
    docs = []
    try:
        for entry in os.listdir(DOC_DIR_PATH):
            full = os.path.join(DOC_DIR_PATH, entry)
            if not os.path.isfile(full):
                continue
            ext = os.path.splitext(entry)[1].lower()
            if ext not in ALLOWED_EXT:
                continue
            try:
                st = os.stat(full)
            except Exception:
                continue
            docs.append(
                {
                    "name": entry,
                    "size": st.st_size,
                    "mtime": _iso(st.st_mtime),
                    "ext": ext,
                }
            )
    except Exception:
        return []
    docs.sort(key=lambda d: d.get("mtime", ""), reverse=True)
    return docs


def read_doc(name):
    """读取单个文档正文或元信息。

    安全校验失败返回 {"error": "非法路径"}；
    文本类扩展名直接返回正文；
    PDF 在缺库时返回元信息与降级说明；
    不支持的格式返回 {"error": "不支持的格式"}。
    """
    path = _safe_join(name)
    if path is None:
        return {"error": "非法路径"}
    if not os.path.isfile(path):
        return {"error": "文件不存在"}

    ext = os.path.splitext(path)[1].lower()

    if ext in TEXT_EXT:
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except Exception as e:
            return {"error": f"读取失败：{e}"}
        return {"name": name, "ext": ext, "content": text}

    if ext == ".pdf":
        try:
            st = os.stat(path)
            size = st.st_size
            mtime = _iso(st.st_mtime)
        except Exception:
            size, mtime = 0, ""
        try:
            import PyPDF2  # 仅在使用 PDF 时尝试导入

            text = _extract_pdf(PyPDF2, path)
            return {"name": name, "ext": "pdf", "content": text}
        except ImportError:
            return {
                "name": name,
                "ext": "pdf",
                "content": "",
                "note": "后端未安装 PDF 解析库，暂返回元信息",
                "meta": {"size": size, "mtime": mtime},
            }
        except Exception:
            # 已安装但仍解析失败：同样降级，避免中断主链路
            return {
                "name": name,
                "ext": "pdf",
                "content": "",
                "note": "PDF 解析失败，暂返回元信息",
                "meta": {"size": size, "mtime": mtime},
            }

    return {"error": "不支持的格式"}


def _extract_pdf(PyPDF2, path):
    """用 PyPDF2 抽取 PDF 文本（尽力而为，逐页容错）。"""
    parts = []
    try:
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                try:
                    parts.append(page.extract_text() or "")
                except Exception:
                    parts.append("")
    except Exception:
        pass
    return "\n".join(parts)


def build_doc_payload(action, data):
    """为面板构造统一返回结构。

    action == "list"：{"view": "list", "docs": [...]}；
    action == "doc"：{"view": "doc", "doc": {...}}；
    其余：原样透传 data。
    """
    if action == "list":
        return {"view": "list", "docs": data.get("docs", [])}
    if action == "doc":
        return {"view": "doc", "doc": data.get("doc", {})}
    return data


if __name__ == "__main__":
    # 简单的本地自测入口（不依赖任何外部服务）。
    docs = list_docs()
    print(build_doc_payload("list", {"docs": docs}))
