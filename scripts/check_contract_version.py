#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""契约版本一致性检查。

从 study_web_contract.md 头部的版本块读出「当前契约版本」，与前端 app.js
顶部声明的期望契约版本（CONTRACT_VERSION / CONTRACT_COMPAT_VERSIONS）比对：

  1. 期望版本必须与契约当前版本一致；
  2. 契约当前版本必须在前端的兼容版本列表里（否则前端会误报「数据契约版本不匹配」）。

本地与 CI 均可跑：

    python3 scripts/check_contract_version.py

退出码：一致 0；任一不一致 1（并打印差异）。
"""
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
CONTRACT = os.path.join(ROOT, "study_web_contract.md")
APPJS = os.path.join(ROOT, "app.js")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def contract_version(text):
    m = re.search(r"当前契约版本[：:]\s*\*{0,2}\s*v(\d+(?:\.\d+)*)", text)
    if not m:
        raise SystemExit("未在 study_web_contract.md 找到「当前契约版本：vX.Y」声明")
    return "v" + m.group(1)


def app_declarations(text):
    m = re.search(r"CONTRACT_VERSION\s*=\s*['\"]([^'\"]+)['\"]", text)
    if not m:
        raise SystemExit("未在 app.js 找到 CONTRACT_VERSION 声明")
    expected = m.group(1)

    m2 = re.search(r"CONTRACT_COMPAT_VERSIONS\s*=\s*\[([^\]]*)\]", text)
    compat = re.findall(r"['\"]([^'\"]+)['\"]", m2.group(1)) if m2 else [expected]
    return expected, compat


def main():
    doc = read(CONTRACT)
    js = read(APPJS)

    doc_ver = contract_version(doc)
    expected, compat = app_declarations(js)

    problems = []
    if expected != doc_ver:
        problems.append("app.js 期望契约版本 %s 与契约当前版本 %s 不一致" % (expected, doc_ver))
    if doc_ver not in compat:
        problems.append("契约当前版本 %s 不在 app.js 兼容列表 %s 内（前端会误报版本不匹配）" % (doc_ver, compat))

    if problems:
        for p in problems:
            print("FAIL " + p)
        return 1

    print("PASS 契约版本一致：契约 %s / app.js 期望 %s / 兼容列表 %s" % (doc_ver, expected, compat))
    return 0


if __name__ == "__main__":
    sys.exit(main())
