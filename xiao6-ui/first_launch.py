#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
庄周 · 首次启动初始化（配置初始化 / 目录创建 / Key 检查 / 可选依赖引导）

设计原则（零侵入，不改任何业务逻辑）：
  - 仅准备运行环境：生成 .env、创建运行时目录、检测 Key、可选安装增强依赖。
  - 不修改 server.py / config.py 的业务行为；不触碰 EventBus / Memory / Runtime。
  - 始终以退出码 0 返回（即使有缺失项也不阻断后端启动）；缺失项通过 JSON 状态上报。

被 electron/backend-launcher.js 在拉起 server.py 之前调用一次，
stdout 输出一行 JSON 供主进程解析（例如决定是否弹出 Key 引导）。
"""

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _read_env_value(key):
    """从 .env 读取某个键的值（不依赖业务模块，纯文本解析）。"""
    env_path = os.path.join(HERE, ".env")
    if not os.path.isfile(env_path):
        return ""
    try:
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k.strip() == key:
                    return v.strip().strip('"').strip("'")
    except OSError:
        return ""
    return ""


def ensure_env_file():
    """若 .env 不存在，则从 .env.example 生成；返回是否新建。"""
    env_path = os.path.join(HERE, ".env")
    example_path = os.path.join(HERE, ".env.example")
    if os.path.isfile(env_path):
        return False
    if os.path.isfile(example_path):
        try:
            with open(example_path, encoding="utf-8") as f:
                content = f.read()
            with open(env_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except OSError:
            pass
    # 兜底：写一个最小占位 .env
    try:
        with open(env_path, "w", encoding="utf-8") as f:
            f.write("# 庄周运行时配置（由首次启动自动生成）\nAGNES_API_KEY=\n")
        return True
    except OSError:
        return False


def ensure_dirs():
    """创建运行时目录（沙箱 / 数据 / 日志 / 文档）。返回新建的目录名列表。"""
    created = []
    for name in ("sandbox", "data", "logs", "docs"):
        p = os.path.join(HERE, name)
        if not os.path.isdir(p):
            try:
                os.makedirs(p, exist_ok=True)
                created.append(name)
            except OSError:
                pass
    return created


def key_present():
    """AGNES_API_KEY 是否已配置（非空）。"""
    val = _read_env_value("AGNES_API_KEY")
    if val:
        return True
    # 兼容：环境变量直接注入的情况
    return bool(os.environ.get("AGNES_API_KEY", "").strip())


def maybe_install_asr():
    """
    可选：首次启动安装语音识别重依赖（torch / torchaudio / funasr / modelscope）。
    默认关闭，避免首次启动拉取 ~2GB 体积；用户可在「设置 → 语音」启用时触发，
    或设环境变量 ZHUANGZHOU_INSTALL_ASR=1 在首次启动静默安装。
    失败不阻断启动。
    """
    if os.environ.get("ZHUANGZHOU_INSTALL_ASR", "").lower() not in ("1", "true", "yes"):
        return {"attempted": False}
    req = os.path.join(HERE, "requirements.txt")
    if not os.path.isfile(req):
        return {"attempted": True, "ok": False, "error": "requirements.txt 缺失"}
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", req,
             "--extra-index-url", "https://download.pytorch.org/whl/cu124"],
            capture_output=True, text=True, timeout=1800,
        )
        return {"attempted": True, "ok": proc.returncode == 0,
                "returncode": proc.returncode}
    except Exception as e:  # noqa: BLE001
        return {"attempted": True, "ok": False, "error": str(e)}


def backfill_missing_keys():
    """
    S20 容错：若 .env 已存在但缺少 .env.example 中的某些键，
    仅追加缺失的键（使用 example 中的默认值），绝不覆盖用户已有的键/值。

    设计边界（零侵入）：
      - 只追加缺失键，不改写任何已有行、不重排、不删除注释。
      - 不触碰 server.py / config.py 业务行为。
      - 任何异常都被吞掉并返回空列表，确保首次启动绝不因本函数失败而中断。
    """
    env_path = os.path.join(HERE, ".env")
    example_path = os.path.join(HERE, ".env.example")
    if not os.path.isfile(env_path) or not os.path.isfile(example_path):
        return []
    try:
        # 收集 .env 中已存在的键（非注释、含 '=' 的行）
        present = set()
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#") or "=" not in s:
                    continue
                present.add(s.split("=", 1)[0].strip())

        # 遍历 example，找出缺失键及其默认行
        missing_lines = []
        added = []
        with open(example_path, encoding="utf-8") as ex:
            for line in ex:
                raw = line.rstrip("\n")
                s = raw.strip()
                if not s or s.startswith("#") or "=" not in s:
                    continue
                key = s.split("=", 1)[0].strip()
                if key not in present:
                    missing_lines.append(raw)
                    added.append(key)

        if missing_lines:
            with open(env_path, "a", encoding="utf-8") as out:
                out.write("\n# 以下键由首次启动补齐（默认值，可按需修改）\n")
                out.write("\n".join(missing_lines) + "\n")
        return added
    except OSError:
        return []


def main():
    status = {
        "ok": True,
        "backend_dir": HERE,
        "env_created": ensure_env_file(),
        "keys_backfilled": backfill_missing_keys(),
        "dirs_created": ensure_dirs(),
        "key_present": key_present(),
        "asr": maybe_install_asr(),
    }
    # 单行 JSON，便于主进程按行解析
    sys.stdout.write(json.dumps(status, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    # 致命兜底：任何意外异常都不应阻止电子壳拉起后端。
    # 永远以退出码 0 返回，绝不 RESET 用户已有 .env。
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001
        sys.stdout.write(
            json.dumps({"ok": False, "fatal": "unexpected_error"}, ensure_ascii=False) + "\n"
        )
        sys.exit(0)
