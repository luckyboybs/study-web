#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HTML 本地资源引用检查。

解析 index.html 与 login/login.html，抽出 link/script/img/a 的 href/src 引用，
凡是指向本地文件的（相对路径或根绝对路径）都必须真实存在：

  - 外部资源（http:// / https:// / //）、锚点、mailto:、data: 跳过；
  - 服务端动态路由（/login、/logout 等）跳过；
  - 根绝对路径按仓库根解析，相对路径按 HTML 所在目录解析。

本地与 CI 均可跑：

    python3 scripts/check_html_refs.py

退出码：全部存在 0；有缺失 1。
"""
import os
import sys
from html.parser import HTMLParser

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

TARGETS = ["index.html", os.path.join("login", "login.html")]

# 由服务端/反代处理的动态路由，不是仓库里的文件
DYNAMIC_ROUTES = {"/login", "/logout", "/login/"}

# 只在这些属性里找引用
ATTRS = ("href", "src")


class RefCollector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name in ATTRS and value:
                self.refs.append((tag, name, value.strip()))


def is_remote(ref):
    return (
        ref.startswith(("http://", "https://", "//"))
        or ref.startswith("#")
        or ref.startswith(("mailto:", "tel:", "data:", "javascript:"))
        or ref == ""
    )


def resolve(ref, html_dir):
    if ref in DYNAMIC_ROUTES:
        return None
    if ref.startswith("/"):
        return os.path.join(ROOT, ref.lstrip("/"))
    return os.path.normpath(os.path.join(html_dir, ref))


def main():
    missing = []
    checked = 0

    for rel in TARGETS:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            print("FAIL 目标 HTML 不存在：%s" % rel)
            missing.append(rel)
            continue

        parser = RefCollector()
        with open(path, encoding="utf-8") as f:
            parser.feed(f.read())

        html_dir = os.path.dirname(path)
        for tag, attr, ref in parser.refs:
            if is_remote(ref):
                continue
            target = resolve(ref, html_dir)
            if target is None:
                continue
            checked += 1
            if not os.path.isfile(target):
                print("FAIL %s <%s %s> 引用的本地文件不存在：%s" % (rel, tag, attr, ref))
                missing.append("%s -> %s" % (rel, ref))

    if missing:
        print("共 %d 处本地引用缺失" % len(missing))
        return 1

    print("PASS HTML 本地资源引用全部存在（检查 %d 处）" % checked)
    return 0


if __name__ == "__main__":
    sys.exit(main())
