#!/usr/bin/env python3
"""庄周 · OS Bridge —— Phase 15 / 16 / 17 统一接线层

定位（严格约束，读之前先读这一段）：
- 本模块**不是** Runtime，**不持有**业务状态，**不实现**任何能力。
  它只做一件事：把早已存在但从未接线的后端内核，暴露成 HTTP 可调用的薄接口。
- Phase 15 自检：聚合既有健康源（config / lifecycle / asr / TOOLS / capability_registry），
  每次调用现算现取，**不新增状态源**、不缓存、不落盘。
- Phase 16 视觉：直接复用 capture_runtime.CaptureRuntime + capture_provider.RealCaptureProvider，
  沿用既有 SCREEN_CAPTURED 事件；像素只在内存里编码成 PNG dataURL 后返回，**绝不落盘**。
- Phase 17 操作：**唯一**执行入口是 permission_guard.PermissionGuard，
  Agent / 前端 / 本模块都严禁直连 computer_executor。
  安全链路 Intent → Preview → Confirm → Execute → Verify 由 Guard 原样提供，本模块不改一行。

红线自检：
- 不新增 Agent Runtime / 不改 Planner / 不改 Executor 核心 / 不改 EventBus 协议 / 不改 Memory 核心。
- 不新增权限系统、不新增风险分级、不新增验证层 —— 全部委托既有模块。
"""

from __future__ import annotations

import base64
import io
import threading
import time

import config

# ——————————————————————————————————————————————————————————
# Phase 15 · Self Diagnostic（六维自检）
# ——————————————————————————————————————————————————————————

# 维度顺序即前端能力轨道顺序，前后端共用同一份 id。
# 七维与用户要求的 Capability Orbit 一一对应：
#   ai_core 居中（意识核心自身），其余六项环绕。
DIMENSIONS = ("ai_core", "vision", "voice", "memory", "knowledge", "tools", "action")


def _dim(dim_id, label, status, detail, metric=None):
    """统一维度结果结构。status: ok | warn | error | unknown"""
    return {
        "id": dim_id,
        "label": label,
        "status": status,
        "detail": detail,
        "metric": metric,
    }


def _check_ai_core():
    try:
        import config
        from ai_core.lifecycle import lifecycle
        key_ok = bool(config.AGNES_KEY)
        cached = lifecycle.self_check_result or {}
        if not key_ok:
            return _dim("ai_core", "AI Core", "error", "未配置 API Key，无法推理", None)
        if cached.get("ok"):
            return _dim("ai_core", "AI Core", "ok",
                        "%s · %s" % (config.AGNES_PROVIDER, config.AGNES_MODEL),
                        config.AGNES_MODEL)
        # 有 key 但自检未通过 / 尚未自检
        return _dim("ai_core", "AI Core", "warn",
                    "已配置密钥，最近一次自检未通过", config.AGNES_MODEL)
    except Exception as e:
        return _dim("ai_core", "AI Core", "error", "自检异常：%s" % e, None)


def _check_memory():
    try:
        from db import db_conn
        conn = db_conn()
        try:
            n = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        finally:
            conn.close()
        if n > 0:
            return _dim("memory", "记忆", "ok", "%d 条长期记忆" % n, n)
        return _dim("memory", "记忆", "warn", "尚未建立记忆", 0)
    except Exception as e:
        return _dim("memory", "记忆", "error", "记忆库不可读：%s" % e, None)


def _check_knowledge():
    try:
        from db import db_conn
        conn = db_conn()
        try:
            n = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
        finally:
            conn.close()
        if n > 0:
            return _dim("knowledge", "知识", "ok", "%d 篇知识条目" % n, n)
        return _dim("knowledge", "知识", "warn", "知识库为空", 0)
    except Exception as e:
        return _dim("knowledge", "知识", "error", "知识库不可读：%s" % e, None)


def _check_tools():
    try:
        from tools import TOOLS
        n = len(TOOLS)
        if n > 0:
            return _dim("tools", "工具", "ok", "%d 项工具已装载" % n, n)
        return _dim("tools", "工具", "error", "未装载任何工具", 0)
    except Exception as e:
        return _dim("tools", "工具", "error", "工具装载失败：%s" % e, None)


def _check_voice():
    """语音 = 听（ASR）+ 说（TTS）。任一不可用即降级为 warn。"""
    asr_ok, asr_name = False, "未启用"
    try:
        from asr import status as asr_status
        st = asr_status() or {}
        asr_ok = bool(st.get("enabled"))
        asr_name = st.get("provider") or "未启用"
    except Exception:
        pass

    tts_backend, tts_ok = "unknown", False
    try:
        import config
        tts_backend = getattr(config, "TTS_BACKEND", "edge") or "edge"
        if tts_backend == "sovits":
            # 只探端口存活，不做真实合成（自检必须快且无副作用）
            import socket
            url = getattr(config, "GPT_SOVITS_URL", "") or "http://127.0.0.1:9880"
            host, port = _split_hostport(url)
            s = socket.socket()
            s.settimeout(0.6)
            try:
                s.connect((host, port))
                tts_ok = True
            except Exception:
                tts_ok = False
            finally:
                s.close()
        else:
            tts_ok = True  # edge-tts 走网络，视为可用（真实失败时有系统合成兜底）
    except Exception:
        pass

    detail = "听：%s · 说：%s%s" % (
        asr_name if asr_ok else "浏览器兜底",
        tts_backend,
        "" if tts_ok else "（不可达）",
    )
    if asr_ok and tts_ok:
        return _dim("voice", "语音", "ok", detail, tts_backend)
    if tts_ok or asr_ok:
        return _dim("voice", "语音", "warn", detail, tts_backend)
    return _dim("voice", "语音", "error", detail, tts_backend)


def _split_hostport(url, default_port=9880):
    try:
        raw = url.split("//", 1)[-1].split("/", 1)[0]
        if ":" in raw:
            h, p = raw.rsplit(":", 1)
            return h, int(p)
        return raw, default_port
    except Exception:
        return "127.0.0.1", default_port


def _check_vision():
    """视觉 = 看得见（截图后端 + 至少一块显示器）。"""
    backend = None
    try:
        import mss  # noqa: F401
        backend = "mss"
    except Exception:
        try:
            from PIL import ImageGrab  # noqa: F401
            backend = "Pillow"
        except Exception:
            backend = None
    if not backend:
        return _dim("vision", "视觉", "error", "截图后端缺失（需 mss 或 Pillow）", 0)
    try:
        from PIL import Image  # noqa: F401
    except Exception:
        return _dim("vision", "视觉", "warn", "可截屏但缺 Pillow，无法编码图片", 0)
    try:
        from capture_provider import RealCaptureProvider
        ds = RealCaptureProvider().list_displays()
        n = len(ds)
        if not n:
            return _dim("vision", "视觉", "warn", "未检测到显示器", 0)
        primary = ds[0]
        return _dim("vision", "视觉", "ok",
                    "%s · %d×%d · %d 块屏" % (backend, primary.width, primary.height, n), n)
    except Exception as e:
        return _dim("vision", "视觉", "warn", "显示器枚举失败：%s" % e, 0)


def _check_action():
    """行动 = 动得了（已实现且风险可控的电脑能力）。"""
    impl, blocked = [], []
    try:
        from capability_os.registry import get_registry, GROUP_COMPUTER_ACTION
        for k, v in get_registry().items():
            if v.group != GROUP_COMPUTER_ACTION:
                continue
            if getattr(v, "implemented", True) and v.risk in ("LOW", "MEDIUM"):
                impl.append(k)
            else:
                blocked.append(k)
    except Exception as e:
        return _dim("action", "行动", "error", "能力注册表不可读：%s" % e, 0)

    n = len(impl)
    if not n:
        return _dim("action", "行动", "error", "无可执行能力", 0)
    return _dim("action", "行动", "ok",
                "%d 项可执行 · %d 项高危已封禁" % (n, len(blocked)), n)


_CHECKS = {
    "ai_core": _check_ai_core,
    "vision": _check_vision,
    "voice": _check_voice,
    "memory": _check_memory,
    "knowledge": _check_knowledge,
    "tools": _check_tools,
    "action": _check_action,
}

# 短缓存：自检含 socket 探测与 DB 计数，前端 30s 快照 + 手动刷新可能连打，
# 8 秒内复用同一结果。这是缓存，不是状态源 —— 过期即重算，无任何持久化。
_sc_cache = {"at": 0.0, "data": None}
_sc_lock = threading.Lock()
_SC_TTL = 8.0


def selfcheck(force=False):
    """七维启动自检。现算现取，不落盘、不新增状态源。"""
    now = time.time()
    if not force and _sc_cache["data"] and (now - _sc_cache["at"]) < _SC_TTL:
        cached = dict(_sc_cache["data"])
        cached["cached"] = True
        return cached
    t0 = time.time()
    dims = []
    for d in DIMENSIONS:
        try:
            dims.append(_CHECKS[d]())
        except Exception as e:
            dims.append(_dim(d, d, "error", "自检异常：%s" % e, None))

    n_err = sum(1 for d in dims if d["status"] == "error")
    n_warn = sum(1 for d in dims if d["status"] == "warn")
    overall = "error" if n_err else ("warn" if n_warn else "ok")
    out = {
        "ok": overall != "error",
        "overall": overall,
        "dimensions": dims,
        "summary": {"total": len(dims), "ok": len(dims) - n_err - n_warn,
                    "warn": n_warn, "error": n_err},
        "elapsed_ms": round((time.time() - t0) * 1000, 1),
        "ts": time.time(),
        "cached": False,
    }
    with _sc_lock:
        _sc_cache["at"] = time.time()
        _sc_cache["data"] = out
    return out


# ——————————————————————————————————————————————————————————
# Phase 16 · Vision（截图 → PNG dataURL，内存进出，绝不落盘）
# ——————————————————————————————————————————————————————————

_capture_runtime = None
_capture_lock = threading.Lock()


def _get_capture_runtime():
    """惰性构造既有 CaptureRuntime（注入 Real Provider）。不新建第二套采集系统。"""
    global _capture_runtime
    if _capture_runtime is not None:
        return _capture_runtime
    with _capture_lock:
        if _capture_runtime is None:
            from capture_runtime import CaptureRuntime
            from capture_provider import RealCaptureProvider
            _capture_runtime = CaptureRuntime(RealCaptureProvider())
    return _capture_runtime


def vision_displays():
    try:
        from capture_provider import RealCaptureProvider
        ds = RealCaptureProvider().list_displays()
        return {"ok": True, "displays": [
            {"id": d.display_id, "name": d.name, "width": d.width,
             "height": d.height, "primary": d.is_primary} for d in ds
        ]}
    except Exception as e:
        return {"ok": False, "error": str(e), "displays": []}


def vision_capture(display_id=None, max_width=1280, fmt="jpeg", quality=82):
    """截取屏幕 → 图片 dataURL。

    - 复用既有 CaptureRuntime（会发布 SCREEN_CAPTURED 事件，沿用既有协议）。
    - 像素仅驻留内存：mss 原始 RGB → Pillow 编码 → base64，全程无临时文件。
    - 默认降采样到 1280 宽：既够视觉模型识别，又避免请求体膨胀。
    - 默认 JPEG q82：实测同一屏幕 PNG 725KB → JPEG 173KB（4.2× 小），
      文字仍清晰可辨，显著降低多模态请求延迟。需要无损时传 fmt="png"。
    """
    try:
        from frame import CaptureRequest
        rt = _get_capture_runtime()
        t0 = time.time()
        frame = rt.capture(CaptureRequest(display_id=display_id) if display_id
                           else CaptureRequest())
        if frame is None:
            return {"ok": False, "error": rt.last_error or "截图失败"}

        m = frame.metadata
        try:
            from PIL import Image
        except Exception as e:
            return {"ok": False, "error": "PNG 编码需要 Pillow：%s" % e}

        img = Image.frombytes("RGB", (m.width, m.height), frame.data)
        w, h = img.size
        if max_width and w > max_width:
            nh = max(1, int(h * (max_width / float(w))))
            img = img.resize((max_width, nh), Image.LANCZOS)

        buf = io.BytesIO()
        use_png = str(fmt).lower() == "png"
        if use_png:
            img.save(buf, format="PNG", optimize=True)
            mime = "image/png"
        else:
            img.save(buf, format="JPEG", quality=int(quality), optimize=True)
            mime = "image/jpeg"
        raw = buf.getvalue()
        data_url = "data:%s;base64,%s" % (mime, base64.b64encode(raw).decode("ascii"))

        return {
            "ok": True,
            "frameId": frame.frame_id,
            "displayId": m.display_id,
            "width": m.width,
            "height": m.height,
            "encodedWidth": img.size[0],
            "encodedHeight": img.size[1],
            "bytes": len(raw),
            "format": "png" if use_png else "jpeg",
            "elapsed_ms": round((time.time() - t0) * 1000, 1),
            "image": data_url,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ——————————————————————————————————————————————————————————
# Phase 17 · Computer Action（唯一入口 = PermissionGuard）
# ——————————————————————————————————————————————————————————

_guard = None
_guard_lock = threading.Lock()

# 已 plan 但未执行的动作（内存，短生命周期）。
# 存在意义只有一个：确保「执行」只能作用于「刚刚预览过并被用户确认」的那个动作，
# 杜绝前端凭空构造一个动作直接要求执行。
_pending = {}
_PENDING_TTL = 300.0


# ——————————————————————————————————————————————————————————
# Phase 18 · Personal Context Engine（只读聚合视图，不落盘不持状态）
# ——————————————————————————————————————————————————————————
#
# 定位（同 Phase 15/16/17 红线约束）：
# - 本模块不是 Runtime，不持有业务状态。
# - PersonalContext 是「视图」不是「系统」：只读聚合 Git 工作区 / goals /
#   memories / profile / memory_summary / learnings / 设备，现算现取，
#   10s 短缓存（缓存≠状态源，过期即重算，无持久化，绝不写库）。
# - 唯一对外落点：context/personal_context_source.py 注册进 SourceRegistry，
#   喂给唯一的 build_context_prompt()；以及 GET /api/personal_context。

import os as _os
import subprocess as _subprocess
from datetime import datetime as _dt

# Git 仓库根（顶层，用于 repo 名 / 分支 / 变更计数）。
_PC_ROOT = _os.environ.get("ZZ_PROJECT_ROOT") or _os.path.dirname(
    _os.path.dirname(_os.path.abspath(__file__))
)
# 活动扫描根：只扫应用自身目录，不扫整个仓库。
# （实测扫全仓库需 ~3.9s，扫本目录 <150ms —— 上下文必须是「瞬时」的，否则拖慢每次对话。）
_PC_SCAN_ROOT = _os.path.dirname(_os.path.abspath(__file__))
# 扫描时排除的目录与后缀。
_PC_IGNORE_DIRS = (".git", "__pycache__", "node_modules", ".workbuddy", ".venv",
                   "_audit", "dist", "build", ".idea", ".vscode", "sandbox")
_PC_SCAN_SUFFIX = (".py", ".js", ".css", ".html", ".ts", ".jsx", ".tsx")
_PC_SCAN_MAX_DEPTH = 3      # 目录深度上限
_PC_SCAN_MAX_FILES = 4000   # 文件数硬上限，防目录异常膨胀时卡死
_PC_TTL = 10.0
_pc_cache = {"at": 0.0, "data": None}
_pc_lock = threading.Lock()
# Git 子进程实测 ~835ms，而仓库名/分支属慢变量（几乎不变）。
# 快变量（mtime 热点，30ms）每次重算，慢变量单独缓存 90s。
# 这样五维冷算从 993ms 降到 ~150ms —— 上下文在每轮对话前构建，延迟必须可忽略。
_PC_GIT_TTL = 90.0
_pc_git_cache = {"at": 0.0, "data": None}


def _safe_db(query, args=(), fetch="all"):
    """极简只读 SQL 助手：表不存在/异常返回 []，隔离单源失败。"""
    try:
        from db import db_conn
        conn = db_conn()
        try:
            cur = conn.execute(query, args)
            return cur.fetchall() if fetch == "all" else cur.fetchone()
        finally:
            conn.close()
    except Exception as e:
        print(f"[personal_context] db 读取忽略: {e}")
        return [] if fetch == "all" else None


def _probe_git(repo_dir=None, timeout=1.5):
    """只读 Git 探针。返回 {ok, repo_name, branch, changed, recent_hot}。

    - repo_name：顶层目录名（如 zhuangzhou-ui）
    - changed：工作区未提交变更数（git status --porcelain 行数）
    - recent_hot：近 24h 内 mtime 热点文件 top5（真实活动信号）
    - 子进程超时 1.5s；无 git / 超时 / 异常 → ok:False，不影响其他维度
    """
    root = repo_dir or _PC_ROOT
    # Windows 上每次 shell=True 都要拉起 cmd.exe（实测 +600ms/次），
    # 故：不用 shell、合并 rev-parse 为一次调用、status 跳过未跟踪文件扫描。
    # 实测 2544ms → ~600ms。
    _flags = 0
    if hasattr(_subprocess, "CREATE_NO_WINDOW"):
        _flags = _subprocess.CREATE_NO_WINDOW  # 不弹控制台黑窗

    def _run(args, to):
        try:
            p = _subprocess.Popen(args, stdout=_subprocess.PIPE,
                                  stderr=_subprocess.PIPE, cwd=root,
                                  shell=False, creationflags=_flags)
        except Exception:
            return ""
        try:
            out, _ = p.communicate(timeout=to)
            return out.decode("utf-8", "ignore").strip()
        except Exception:
            try:
                p.kill()
            except Exception:
                pass
            return ""

    try:
        # —— 慢变量（子进程）：90s 缓存 ——
        now = time.time()
        slow = _pc_git_cache["data"]
        if not slow or (now - _pc_git_cache["at"]) >= _PC_GIT_TTL:
            # 一次调用同时拿到仓库顶层与当前分支
            head = _run(["git", "rev-parse", "--show-toplevel", "--abbrev-ref", "HEAD"],
                        timeout)
            if not head:
                slow = {"ok": False, "error": "not a git repo"}
            else:
                parts = [l.strip() for l in head.splitlines() if l.strip()]
                top = parts[0] if parts else ""
                branch = parts[1] if len(parts) > 1 else "unknown"
                if not top:
                    slow = {"ok": False, "error": "not a git repo"}
                else:
                    # -uno：不递归枚举未跟踪文件（大仓库上这是主要耗时来源）
                    changed_raw = _run(["git", "status", "--porcelain", "-uno"], timeout)
                    changed = len([l for l in changed_raw.splitlines()
                                   if l.strip()]) if changed_raw else 0
                    slow = {
                        "ok": True,
                        "repo_name": _os.path.basename(top.replace("\\", "/").rstrip("/")),
                        "branch": branch,
                        "changed": changed,
                    }
            _pc_git_cache["at"] = time.time()
            _pc_git_cache["data"] = slow

        if not slow.get("ok"):
            return dict(slow)

        # —— 快变量（纯文件系统，~30ms）：每次重算 ——
        out = dict(slow)
        out["recent_hot"] = _scan_recent_files(hours=24, top=5)
        return out
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _scan_recent_files(root=None, hours=24, top=5):
    """取近 N 小时内 mtime 最新的 top 个源码文件（真实活动信号）。

    纯文件系统读，零副作用。深度 ≤3、文件数 ≤4000、排除 .git/node_modules 等，
    保证 <200ms 完成 —— 上下文构建在每次对话前发生，慢一秒就是每句话慢一秒。
    路径统一为正斜杠，便于前端直接展示。
    """
    base = root or _PC_SCAN_ROOT
    cutoff = time.time() - hours * 3600.0
    hits = []
    seen = 0
    try:
        base_depth = base.rstrip("\\/").count(_os.sep)
        for dirpath, dirnames, filenames in _os.walk(base):
            if dirpath.count(_os.sep) - base_depth >= _PC_SCAN_MAX_DEPTH:
                dirnames[:] = []
            dirnames[:] = [d for d in dirnames
                           if d not in _PC_IGNORE_DIRS and not d.startswith(".")]
            for fn in filenames:
                if not fn.lower().endswith(_PC_SCAN_SUFFIX):
                    continue
                seen += 1
                if seen > _PC_SCAN_MAX_FILES:
                    break
                fp = _os.path.join(dirpath, fn)
                try:
                    mt = _os.path.getmtime(fp)
                except OSError:
                    continue
                if mt >= cutoff:
                    rel = _os.path.relpath(fp, base).replace("\\", "/")
                    hits.append((mt, rel))
            if seen > _PC_SCAN_MAX_FILES:
                break
        hits.sort(reverse=True)
        return [rel for _, rel in hits[:top]]
    except Exception as e:
        print(f"[personal_context] 文件扫描忽略: {e}")
        return []


def _derive_project(git, summary_text, profile_project):
    """多路推导当前项目 + 置信度。

    - S1 Git 仓库名（权重 0.45）
    - S2 工作区活跃度 / 热点（权重 0.30）
    - S3 memory_summary 关键词（权重 0.20）
    - S4 profile.项目（权重 0.05，失真则标 stale）
    返回 {project, area, confidence, stale, signal[]}
    """
    signals = []
    repo_name = None
    confidence = 0.0
    stale = False
    hits = 0

    # S1 · Git 仓库名（权重 0.45）
    if git and git.get("ok"):
        repo_name = git.get("repo_name")
        confidence += 0.45
        hits += 1
        signals.append("git:%s" % repo_name)

    # S3 · memory_summary 项目关键词（权重 0.20）
    s3_hit = None
    for k in ("AI OS", "AIOS", "ZhuangZhou", "zhuangzhou", "庄周"):
        if k in (summary_text or ""):
            s3_hit = k
            break
    if s3_hit:
        confidence += 0.20
        hits += 1
        signals.append("summary:%s" % s3_hit)

    # S2 · 工作区活跃度 / mtime 热点（权重 0.30）
    hot = (git or {}).get("recent_hot") or []
    if hot:
        confidence += 0.30
        hits += 1
        signals.append("hot:%s" % hot[0])

    # 项目名合成：仓库名 + 摘要中的产品限定词 → 「ZhuangZhou AI OS」
    project = repo_name
    if repo_name and s3_hit in ("AI OS", "AIOS") and "OS" not in repo_name.upper():
        project = "%s AI OS" % repo_name

    # S4 · profile.项目（权重 0.05）；与高置信信号冲突则标 stale，仅作参考不采纳
    if profile_project:
        if project and profile_project.strip() and profile_project not in project:
            stale = True
            signals.append("profile_stale:%s" % profile_project)
        else:
            confidence += 0.05

    confidence = min(confidence, 0.99)
    # Phase 20.5 · Truth Layer：User Model 高可信项目（L2, conf>=0.9）作为权威真相，
    # 覆盖失真 profile。真相确定后无需 stale 纠偏。
    try:
        from cognitive.user_model import canonical_project
        cproj, cconf = canonical_project()
        if cproj and cconf >= 0.9:
            project = cproj
            confidence = max(confidence, 0.9)
            stale = False
    except Exception:
        pass
    if confidence < 0.3 or not project:
        # 证据不足时如实声明，绝不编造项目名
        return {"project": "（不确定当前项目）", "area": None,
                "confidence": 0.1, "stale": stale, "signal": signals[:4]}
    # 显示名统一：仓库/推导名为 ZhuangZhou / zhuangzhou / zhuangzhou-ui → 对外展示 Six
    if project:
        pl = project.strip().lower()
        if pl in ("zhuangzhou", "zhuangzhou ai os", "zhuangzhou-ui") or pl.startswith("zhuangzhou"):
            project = "Six"
    return {"project": project, "area": "AI OS 研发",
            "confidence": round(confidence, 2), "stale": stale,
            "signal": signals[:4]}


def personal_context(force=False):
    """五维 PersonalContext 聚合（视图，现算现取）。

    返回 identity / focus / activity / environment / attention 五维字典。
    任一维度失败 → 该维返回 {}，整体仍成功（单维隔离）。
    10s 短缓存：是缓存不是状态源，过期即重算，无持久化。
    """
    now = time.time()
    if not force and _pc_cache["data"] and (now - _pc_cache["at"]) < _PC_TTL:
        cached = dict(_pc_cache["data"])
        cached["cached"] = True
        return cached
    try:
        # ----- Identity（慢变量）-----
        prefs, boundaries = [], []
        for row in _safe_db("SELECT key,value FROM profile"):
            k, v = (row[0] or ""), (row[1] or "")
            if k in ("偏好", "习惯", "领域"):
                prefs.append("%s：%s" % (k, v))
            elif k in ("边界", "限制"):
                boundaries.append(v)
        summary_rows = _safe_db(
            "SELECT summary FROM memory_summary ORDER BY updated DESC LIMIT 1")
        summary_text = (summary_rows[0][0] if summary_rows else "") or ""
        if summary_text:
            prefs.append("长期摘要：" + summary_text[:240])
        identity = {
            "name": config.AI_DISPLAY_NAME or "小6",
            "role": "老板的个人 AI 副驾",
            "prefs": prefs[:6],
            "boundaries": boundaries[:4],
        }

        # ----- Focus（快变量，多路推导）-----
        git = _probe_git()
        profile_project = None
        for row in _safe_db("SELECT value FROM profile WHERE key='项目'"):
            profile_project = row[0]
        focus = _derive_project(git, summary_text, profile_project)
        focus["git"] = git if git.get("ok") else {"ok": False}

        # ----- Activity（快变量）-----
        working_files = (git.get("recent_hot") or []) if git.get("ok") else []
        goal_rows = _safe_db(
            "SELECT title,progress,status FROM goals WHERE status='active' "
            "ORDER BY updated DESC LIMIT 3")
        active_goals = [{"title": r[0], "progress": r[1]} for r in goal_rows]
        activity = {
            "working_files": working_files[:5],
            "active_goals": active_goals,
            "active_intent": active_goals[0]["title"] if active_goals else None,
        }

        # ----- Environment（实时，引用既有端点，不外推）-----
        # 设备/环境实时数据由 /api/sysmon /api/devices 提供，此处仅标记已接入。
        environment = {"source": "sysmon+devices+geo+hotspots", "live": True}

        # ----- Attention（实时）-----
        task_rows = _safe_db("SELECT COUNT(*) FROM tasks WHERE status='in_progress'")
        pending = task_rows[0][0] if task_rows else 0
        attention = {
            "active_goal": active_goals[0] if active_goals else None,
            "pending_tasks": pending,
            "goal_progress": active_goals[0]["progress"] if active_goals else None,
        }

        out = {
            "identity": identity,
            "focus": focus,
            "activity": activity,
            "environment": environment,
            "attention": attention,
            "ts": _dt.now().strftime("%Y-%m-%d %H:%M:%S"),
            "cached": False,
        }
        with _pc_lock:
            _pc_cache["at"] = time.time()
            _pc_cache["data"] = out
        return out
    except Exception as e:
        print(f"[personal_context] 聚合失败: {e}")
        return {"identity": {}, "focus": {}, "activity": {},
                "environment": {}, "attention": {}, "error": str(e)}


def _get_guard():
    """构造/复用真实 PermissionGuard（Phase 21 白名单 Hand），并统一为进程级单例。

    修复 G8/R1（关键）：agent_runtime 以 `from permission_guard import guard` 绑定了
    模块级单例对象的**引用**，若此处新建对象再 `permission_guard.guard = 新对象`，
    agent_runtime 的本地引用仍指向旧 Mock。因此本函数**原地修改单例对象**的
    executor / verifier 属性，使 Agent 闭环路径（透传）与生产 REST 路径引用同一
    真实、白名单受限的 Guard。不修改 permission_guard / agent_runtime 核心源码。
    """
    global _guard
    if _guard is not None:
        return _guard
    with _guard_lock:
        if _guard is None:
            import permission_guard
            from computer_action.executor import ComputerExecutor
            from computer_action.verifier import ComputerVerifier
            from computer_action.observer import Observer
            # 复用模块级单例对象（agent_runtime 透传引用的同一对象），原地替换执行器/验证器
            g = permission_guard.guard
            g.executor = ComputerExecutor(timeout=20.0)
            g.verifier = ComputerVerifier(observer=Observer())
            _guard = g
    return _guard


def _sweep_pending():
    now = time.time()
    for k in [k for k, v in _pending.items() if now - v["at"] > _PENDING_TTL]:
        _pending.pop(k, None)


def action_capabilities():
    """Hand 能力目录（仅白名单内，含风险与预期效果），供 UI 渲染与 Planner 参考。"""
    try:
        from capability_os.registry import get_registry
        from computer_action.safety import is_allowed
        items = []
        for cid, c in get_registry().items():
            if not is_allowed(cid):
                continue  # 仅暴露白名单 + 只读辅助能力
            items.append({
                "id": cid,
                "label": c.name,
                "risk": c.risk,
                "targetKind": c.target_kind,
                "expectedEffect": c.description,
                "implemented": c.implemented,
                "executable": c.risk in ("LOW", "MEDIUM"),
            })
        items.sort(key=lambda x: (not x["executable"], x["risk"], x["id"]))
        return {"ok": True, "capabilities": items}
    except Exception as e:
        return {"ok": False, "error": str(e), "capabilities": []}


def action_plan(capability, target="", parameters=None, goal_id=None):
    """Intent → Action Preview。

    只规划与裁决，**绝不执行**。返回给 UI 用于渲染确认卡片。
    """
    _sweep_pending()
    if not capability:
        return {"ok": False, "error": "capability 必填"}
    try:
        from eventbus import publish_domain
        # 四态：观察（规划前先广播"正在观察屏幕"）
        publish_domain("COMPUTER_ACTION_PHASE", {"phase": "observe", "capability": capability, "goalId": goal_id})
        g = _get_guard()
        action = g.plan(capability, target or "", parameters or {}, goal_id=goal_id)
        # decide 只裁决不执行；HIGH/CRITICAL 在此即被拒
        dec = g.decide(action, goal_id=goal_id)
        # 四态：规划（裁决完成，广播"正在规划操作"）
        publish_domain("COMPUTER_ACTION_PHASE", {"phase": "plan", "capability": capability, "goalId": goal_id})
        decision = dec.get("decision")
        _pending[action.actionId] = {"action": action, "at": time.time(),
                                     "decision": decision}
        return {
            "ok": True,
            "actionId": action.actionId,
            "capability": action.capability,
            "label": _label_of(action.capability),
            "target": action.target,
            "parameters": action.parameters,
            "risk": action.risk,
            "expectedEffect": action.expectedEffect,
            "decision": decision,                  # auto | confirm | block | deny
            "reason": dec.get("reason", ""),
            "needConfirm": decision == "confirm",
            "blocked": decision in ("block", "deny"),
        }
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _label_of(cap):
    try:
        from capability_os.registry import get_capability
        c = get_capability(cap)
        return c.name if c is not None else cap
    except Exception:
        return cap


def action_execute(action_id, confirmed=False, goal_id=None):
    """User Confirm → Execute → Verify。

    - 只能执行 `action_plan` 刚刚产出、且仍在 TTL 内的动作（防止绕过预览）。
    - decision=confirm 的动作必须带 confirmed=True（UI 上用户点了确认）才放行；
      这正是既有 Guard 的 auto_approve 语义 —— 确认发生在 UI，不再走后端票据等待。
    - HIGH / CRITICAL 由 Guard + Executor 双层拒绝，本函数不做任何豁免。
    """
    _sweep_pending()
    rec = _pending.get(action_id)
    if not rec:
        return {"ok": False, "error": "动作不存在或预览已过期，请重新规划"}
    action = rec["action"]
    decision = rec.get("decision")

    if decision in ("block", "deny"):
        return {"ok": False, "error": "该动作已被安全策略拒绝", "decision": decision}
    if decision == "confirm" and not confirmed:
        return {"ok": False, "error": "该动作需要用户确认", "needConfirm": True}

    try:
        g = _get_guard()
        from eventbus import publish_domain
        # 四态：执行（广播"正在执行"）
        publish_domain("COMPUTER_ACTION_PHASE", {"phase": "execute", "capability": action.capability, "goalId": goal_id})
        # auto_approve=True 表示确认已在 UI 完成；auto 决策不受影响
        g.run(action, goal_id=goal_id, auto_approve=True)
        # 四态：验证（执行后复核完成，广播"正在确认结果"）
        publish_domain("COMPUTER_ACTION_PHASE", {"phase": "verify", "capability": action.capability, "goalId": goal_id})
        _pending.pop(action_id, None)
        res = action.result or {}
        return {
            "ok": action.status == "done",
            "actionId": action.actionId,
            "capability": action.capability,
            "status": action.status,
            "result": res,
            "verified": action.verified,
            "verificationDetail": action.verificationDetail,
            "durationMs": res.get("duration_ms"),
            "error": res.get("error"),
        }
    except Exception as e:
        _pending.pop(action_id, None)
        return {"ok": False, "error": str(e)}


def action_observe(scope="window"):
    """当前观察快照（只读），供 UI / 四态展示。"""
    try:
        from computer_action.observer import observe
        return observe(scope=scope)
    except Exception as e:
        return {"ok": False, "error": str(e)}
