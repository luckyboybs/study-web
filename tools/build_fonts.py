#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 assets/fonts/ 下的自托管字体子集（思源宋体 + JetBrains Mono）。

为什么自建这一步
--------------
站点是零构建纯静态，不能引 npm/打包器；又不能裸用系统兜底字体链（中文一旦落回默认
黑体，任何版式都长成同一张脸）。所以把字体在仓库里落成可直接 <link> 的 woff2。

上游来源（外采，非自绘）
--------------
- 思源宋体 Noto Serif SC：npm `@fontsource-variable/noto-serif-sc`
  （Google Fonts / Adobe 思源宋体的 fontsource 分发版，SIL OFL 1.1）
- JetBrains Mono：npm `@fontsource-variable/jetbrains-mono`（SIL OFL 1.1）
两者都是按 unicode-range 切开的子集包，本脚本把子集合并回整字后再按本站字符集裁切。

字符集
-------
  data/ 下现有全部文本（index.json + explanations/*.md + accum-book/*.html）
+ 仓库内静态文案（index.html / app.js / styles.css / README.md / *.md）
+ GB2312 一级字 3755 字（覆盖现代汉语常用字，未来数据基本不会缺字）
+ 标点 / 拉丁 / 希腊 / 数理符号 / 序号（初中数理化要用的 ×÷≈≤≥√∠Δ 等）

缺字时浏览器按 CSS fallback 链回退到系统宋体，不会出现豆腐块。

用法
----
    python3 tools/build_fonts.py            # 重新生成 assets/fonts/*.woff2

依赖：fonttools（pyftsubset / varLib.instancer / merge）
"""
import glob
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
FONTS_DIR = os.path.join(ROOT, "assets", "fonts")
DATA_DIR = os.path.join(ROOT, "data")

SERIF_PKG = "@fontsource-variable/noto-serif-sc"
MONO_PKG = "@fontsource-variable/jetbrains-mono"
MONO_SUBSET = "jetbrains-mono-latin-wght-normal.woff2"

EXTRA_SYMBOLS = """
!"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~
¡¢£¤¥¦§¨©ª«¬®¯°±²³´µ¶·¸¹º»¼½¾¿ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ
ĀāĂăĄąĆćČčĎďĐđĒēĖėĘęĚěĞğĪīİıŁłŇňŌōŘřŚśŞşŠšŤťŪūŮůŰűŲųŸŹźŻżŽž
‘’“”†‡•…‰‹›⁄€™←↑→↓⇐⇒⇑⇓⇔↖↗↘↙
≈≠≡≤≥≦≧≮≯∧∨∩∪∈∋∉∌⊂⊃⊆⊇⊄⊅∀∃∅°′″∫∮√∝∞∵∴∽
∠⊥∥⌒⊙△▽◆◇■□▲▼○●◎★☆
αβγδεζηθικλμνξοπρστυφχψωΑΒΓΔΕΖΗΘΙΚΛΜΝΟΠΡΣΤΥΦΧΩ
ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩⅪⅫ㈠㈡㈢㈣㈤㈥㈦㈧㈨㈩①②③④⑤⑥⑦⑧⑨⑩⑴⑵⑶⑷⑸⑹⑺⑻⑼⑽⒈⒉⒊⒋⒌
㎡℃℉‰£￥
""" + "".join(chr(c) for c in range(0xFF01, 0xFF5F)) \
  + "".join(chr(c) for c in range(0x2E80, 0x2EFF)) + "《》「」『』【】〔〕〖〗"


def run(cmd, cwd=None):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if p.returncode != 0:
        sys.stderr.write(p.stdout + "\n" + p.stderr + "\n")
        raise SystemExit("命令失败: %s" % " ".join(cmd))
    return p.stdout


def fetch_pkg(name, workdir):
    """npm pack 取上游字体包，返回解包后的 files/ 目录。"""
    stem = os.path.basename(name)
    tgz = os.path.join(workdir, stem + ".tgz")
    run(["npm", "pack", name, "--pack-destination", workdir])
    if not os.path.exists(tgz):
        cands = [t for t in glob.glob(os.path.join(workdir, "*.tgz")) if stem in os.path.basename(t)]
        if not cands:
            raise SystemExit("npm pack 没有产出 %s 的包" % name)
        tgz = sorted(cands)[-1]
    out = os.path.join(workdir, "pkg-" + stem)
    os.makedirs(out, exist_ok=True)
    run(["tar", "xzf", tgz, "-C", out])
    return os.path.join(out, "package", "files")


def collect_text():
    chars = set()

    def add(s):
        for ch in str(s or ""):
            chars.add(ord(ch))

    if os.path.isdir(DATA_DIR):
        idx = os.path.join(DATA_DIR, "index.json")
        if os.path.exists(idx):
            add(open(idx, encoding="utf-8").read())
        for f in glob.glob(os.path.join(DATA_DIR, "explanations", "*.md")):
            add(open(f, encoding="utf-8").read())
        for f in glob.glob(os.path.join(DATA_DIR, "accum-book", "*.html")):
            add(open(f, encoding="utf-8").read())

    for f in glob.glob(os.path.join(ROOT, "*.html")) + glob.glob(os.path.join(ROOT, "*.js")) \
            + glob.glob(os.path.join(ROOT, "*.css")) + glob.glob(os.path.join(ROOT, "*.md")):
        if os.path.basename(f) == "ANTI-SLOP-CHECK.md":
            continue
        add(open(f, encoding="utf-8", errors="ignore").read())

    add(EXTRA_SYMBOLS)

    # GB2312 一级字（行 16-55）
    from fontTools.ttLib import TTFont  # noqa: F401  (仅确认 fonttools 可用)
    return chars


def gb2312_level1():
    out = set()
    for cp in range(0x4E00, 0xA000):
        try:
            b = chr(cp).encode("gb2312")
        except Exception:
            continue
        if 0xB0 <= b[0] <= 0xD7:
            out.add(cp)
    return out


def build_serif(workdir):
    files = sorted(glob.glob(os.path.join(fetch_pkg(SERIF_PKG, workdir), "*-wght-normal.woff2")))
    if not files:
        raise SystemExit("没找到思源宋体子集文件")
    print("上游子集数: %d" % len(files))

    from fontTools.ttLib import TTFont
    from fontTools.merge import Merger
    from fontTools.varLib.instancer import instantiateVariableFont

    charset = collect_text() | gb2312_level1()
    text_file = os.path.join(workdir, "charset.txt")
    open(text_file, "w", encoding="utf-8").write("".join(chr(c) for c in sorted(charset)))
    print("字符集大小: %d" % len(charset))

    os.makedirs(FONTS_DIR, exist_ok=True)
    for wght in (400, 600, 700):
        tmp = os.path.join(workdir, "s%d" % wght)
        os.makedirs(tmp, exist_ok=True)
        paths = []
        for i, f in enumerate(files):
            t = TTFont(f)
            instantiateVariableFont(t, {"wght": wght}, inplace=True)
            # 合并器不认 BASE/STAT 里的 VarStore，静态化后这些表也没有意义
            for tag in ("BASE", "STAT", "vhea", "vmtx", "GDEF"):
                if tag in t:
                    del t[tag]
            p = os.path.join(tmp, "%03d.ttf" % i)
            t.save(p)
            paths.append(p)
        merged = Merger().merge(paths)
        merged_ttf = os.path.join(workdir, "NotoSerifSC-%d.ttf" % wght)
        merged.save(merged_ttf)

        out = os.path.join(FONTS_DIR, "noto-serif-sc-%d.woff2" % wght)
        run([
            "pyftsubset", merged_ttf,
            "--text-file=%s" % text_file,
            "--output-file=%s" % out,
            "--flavor=woff2",
            "--layout-features=kern,liga,clig,calt,ccmp,locl,mark,mkmk",
            "--no-hinting", "--desubroutinize",
        ])
        print("  noto-serif-sc-%d.woff2  %d KB" % (wght, os.path.getsize(out) // 1024))


def build_mono(workdir):
    files = fetch_pkg(MONO_PKG, workdir)
    src = os.path.join(files, MONO_SUBSET)
    if not os.path.exists(src):
        raise SystemExit("没找到 JetBrains Mono 子集: %s" % MONO_SUBSET)
    latin = "".join(chr(c) for c in list(range(0x20, 0x7F)) + [0xB0, 0xD7, 0xF7, 0x2013, 0x2014, 0x2018, 0x2019, 0x201C, 0x201D, 0x2026, 0xB7, 0xA0])
    tf = os.path.join(workdir, "mono-charset.txt")
    open(tf, "w", encoding="utf-8").write(latin)
    out = os.path.join(FONTS_DIR, "jetbrains-mono-latin.woff2")
    run([
        "pyftsubset", src,
        "--text-file=%s" % tf,
        "--output-file=%s" % out,
        "--flavor=woff2",
        "--layout-features=kern,liga,calt,zero",
        "--no-hinting", "--desubroutinize",
    ])
    print("  jetbrains-mono-latin.woff2  %d KB" % (os.path.getsize(out) // 1024))


def main():
    if not os.path.isdir(DATA_DIR):
        print("警告: 没有 data/ 目录，字符集只覆盖仓库文案与 GB2312 一级字")
    with tempfile.TemporaryDirectory() as workdir:
        build_serif(workdir)
        build_mono(workdir)
    print("完成 -> %s" % FONTS_DIR)


if __name__ == "__main__":
    main()
