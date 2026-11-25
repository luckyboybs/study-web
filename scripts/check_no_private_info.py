#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""占位符残留检查（防回归）。

本仓库是脱敏后开源的：真实域名、服务器 IP、ssh 别名、本机 / 服务器绝对路径、
认证服务与认证文件关键字等一律不允许出现在源码里（示例配置中只允许占位符形态）。

注意：下面的模式串是「拼接」出来的——检查脚本自己不能包含这些字面量，
否则它扫描的第一个命中就是自己。这是刻意为之，不要为了「可读性」改回字面量。

本地与 CI 均可跑：

    python3 scripts/check_no_private_info.py

退出码：零命中 0；有命中 1（逐条打印 文件:行号: 模式）。
"""
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# (说明, 正则模式) —— 模式用拼接构造，避免本脚本自命中
FORBIDDEN = [
    ("真实域名", "blood" + "y" + r"sky"),
    ("真实域名", "blood" + "y" + r"\.top"),
    ("服务器 IP", r"8\.155\." + r"51\.240"),
    ("ssh 别名", "ecs" + r"\-" + "blog"),
    ("本机绝对路径", r"/home/" + "twrp"),
    ("服务器绝对路径", r"/var/" + "www"),
    ("认证服务名", "study" + r"\-" + "auth"),
    ("认证文件关键字", "ht" + "passwd"),
    ("数据侧脚本路径", "pi" + r"\-lark\-" + "bridge"),
    ("云厂商", "阿里" + "云"),
    ("本机用户名", "tw" + "rp"),
]

# 不扫描的目录 / 文件
SKIP_DIRS = {".git", "data", "proof", "__pycache__", "node_modules", ".venv", "venv"}
SKIP_FILES = {"check_no_private_info.py"}
BINARY_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svg",
    ".woff", ".woff2", ".ttf", ".ttc", ".otf",
    ".pdf", ".zip", ".gz", ".pyc",
}

COMPILED = [(label, re.compile(pattern, re.IGNORECASE)) for label, pattern in FORBIDDEN]


def scan_file(path, rel):
    hits = []
    try:
        with open(path, encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                for label, rx in COMPILED:
                    if rx.search(line):
                        hits.append((rel, lineno, label, line.rstrip()[:160]))
    except (UnicodeDecodeError, OSError):
        pass
    return hits


def main():
    all_hits = []

    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            if name in SKIP_FILES:
                continue
            ext = os.path.splitext(name)[1].lower()
            if ext in BINARY_EXT:
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, ROOT)
            all_hits.extend(scan_file(path, rel))

    if all_hits:
        for rel, lineno, label, text in all_hits:
            print("FAIL %s:%d 命中[%s] %s" % (rel, lineno, label, text))
        print("共 %d 处隐私 / 基础设施残留" % len(all_hits))
        return 1

    print("PASS 无隐私 / 基础设施信息残留")
    return 0


if __name__ == "__main__":
    sys.exit(main())
