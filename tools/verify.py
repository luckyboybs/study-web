#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""study-web 功能与视觉验证（Playwright）。

覆盖：
  1. DOM / 行为断言：路由、筛选、知识点面板、版本切换、切题三级导航、灯箱、主题、空态、错误态
  2. 截图留档：手机视口 390x844 与桌面视口 1280x900，深浅两套，写入 proof/

前置：study-web/ 下已起静态服务（python3 -m http.server 8901）
      且 data/ 样例数据已由 tools/gen_sample.py 生成。

用法：
    python3 tools/verify.py [--base http://127.0.0.1:8901] [--no-shots]
"""
import argparse
import glob
import json
import os
import random
import re
import sys
from datetime import date
from urllib.parse import quote

from playwright.sync_api import sync_playwright

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PROOF = os.path.join(ROOT, "proof")
PASS, FAIL = [], []
SHOTS = []

EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u2B00-\u2BFF]")


def cn_count(n):
    """与 app.js cnCount 同口径：月数口语计数（2 作「两」）。"""
    return "两" if n == 2 else ("零一二三四五六七八九十十一十二"[n] if 0 < n < 13 else str(n))


def check(name, cond, extra=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS " if cond else "FAIL ") + name + ((" | " + str(extra)) if extra else ""), flush=True)


def find_chrome():
    cache = os.path.join(os.path.expanduser("~"), ".cache", "ms-playwright")
    cands = sorted(glob.glob(os.path.join(cache, "chromium-*/chrome-linux64/chrome")), reverse=True)
    cands += sorted(glob.glob(os.path.join(cache, "chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell")), reverse=True)
    return cands[0] if cands else None


def shot(page, name, full=False):
    if not SHOTS:
        return
    path = os.path.join(PROOF, name + ".png")
    page.screenshot(path=path, full_page=full)
    print("  shot -> proof/%s.png" % name, flush=True)


def set_theme(page, mode):
    page.evaluate("t => localStorage.setItem('xueji-theme', t)", mode)
    page.reload(wait_until="networkidle")
    page.wait_for_timeout(250)


def load_index():
    with open(os.path.join(ROOT, "data", "index.json"), encoding="utf-8") as f:
        return json.load(f)


def build_rich_fixture(base):
    """按设计稿实采口径构造的富样例（120 题 / 四个月 / 里程碑 50·100 /
    review_backlog 115 / error_type 65·49·5·1 / 讲解 145 篇）：用于验证
    「已达成里程碑」分支与设计稿数字，并留档截图。
    所有期望值由本函数在 Python 侧重算，不写死。"""
    rnd = random.Random(20261105)
    subs = ["math"] * 55 + ["chemistry"] * 33 + ["physics"] * 32
    rnd.shuffle(subs)
    plan = [("2026-08", 3, 10), ("2026-09", 49, 30), ("2026-10", 58, 31), ("2026-11", 10, 5)]
    questions, qid = [], 1
    for (mk, n, days) in plan:
        for i in range(n):
            day = (i % days) + 1
            created = "%s-%02d %02d:%02d:00" % (mk, day, 18 + (i % 5), (i * 7) % 60)
            q = {
                "id": qid,
                "subject": subs[qid - 1],
                "grade": "初三",
                "knowledge_points": ["kp-%03d" % qid] + (["二次函数"] if qid % 4 == 0 and qid <= 108 else []),
                "question": "富样例第 %d 题（合成数据，仅用于验证与截图）" % qid,
                "student_answer": "答：略。",
                "correct_answer": "正确答案略。",
                "mastery": 0,
                "resolved": 0,
                "review_count": 0,
                "created_at": created,
                "image": "error-images/%d.jpg" % qid,
                "has_explanation": False,
                "explanation_versions": [],
            }
            if qid <= 111:
                q["do_time"] = created[:10] + (" %02d:%02d:00" % (20 + (qid % 3), (qid * 11) % 60)
                                               if qid <= 92 else " 15:%02d:00" % (qid % 60))
            questions.append(q)
            qid += 1
    # error_type：概念 65 / 方法 49 / 计算 5 / 审题 1（设计稿实采口径，全覆盖）
    ets = ["concept"] * 65 + ["method"] * 49 + ["calculation"] * 5 + ["misreading"] * 1
    rnd.shuffle(ets)
    for q, et in zip(questions, ets):
        q["error_type"] = et
    # 讲解覆盖 102 题；讲解文件 145 篇：10-23 27 篇、10-24 102 篇、10-30 16 篇（重讲批次）
    explained = [q["id"] for q in questions[:102]]
    for q in questions:
        if q["id"] in explained:
            q["has_explanation"] = True
            q["explanation_versions"] = ["v1"]
    tail_ids = [110, 102, 42, 121, 31, 15, 12, 7]
    for q in questions:
        if q["id"] in tail_ids:
            q["explanation_versions"] = ["v1", "v2"]
            q["thumb"] = "thumbs/%d.jpg" % q["id"]
    explanations = []
    for i in range(27):
        explanations.append({"id": explained[i % 102], "version": "v1",
                             "file": "explanations/%d-v1.md" % explained[i % 102],
                             "generated_at": "2026-10-23T21:00:00Z", "model": "step-3.7-flash",
                             "word_count": 637})
    for i in range(102):
        explanations.append({"id": explained[i], "version": "v1",
                             "file": "explanations/%d-v1.md" % explained[i],
                             "generated_at": "2026-10-24T20:00:00Z", "model": "step-3.7-flash",
                             "word_count": 637})
    for qid_t in tail_ids:
        for ver in ("v1", "v2"):
            explanations.append({"id": qid_t, "version": ver,
                                 "file": "explanations/%d-%s.md" % (qid_t, ver),
                                 "generated_at": "2026-10-30T21:30:00Z", "model": "step-3.7-flash",
                                 "word_count": 712,
                                 "summary": "富样例重讲解摘要（%d %s）。" % (qid_t, ver)})
    fixture = dict(base)
    fixture.update({
        "contract_version": "v1.3",
        "generated_at": "2026-11-05T20:20:00",
        "sample": True,
        "questions": questions,
        "explanations": explanations,
        "stats": {
            "error_book_total": len(questions),
            "error_book_active": len(questions),
            "explanations": len(explanations),
            "crop_sessions": len(base["crop_sessions"]),
            "crop_problems": sum(len(s["problems"]) for s in base["crop_sessions"]),
            "plots": len(base["plots"]),
            "review_backlog": {"snapshot_date": "2026-11-04", "overdue": 115,
                               "due_today": 2, "future": 3, "resolved": 0},
            "crop_figures": 53,
        },
    })
    return fixture


def derive(idx):
    """与 app.js 同口径的派生基准（期望值不来自被验实现）。"""
    qs = idx["questions"]
    day_cnt = {}
    for q in qs:
        dk = (q.get("created_at") or "")[:10]
        if dk:
            day_cnt[dk] = day_cnt.get(dk, 0) + 1
    anchor = max(day_cnt) if day_cnt else None

    def _off(dk):
        y1, m1, d1 = [int(x) for x in anchor.split("-")]
        y2, m2, d2 = [int(x) for x in dk.split("-")]
        return (date(y1, m1, d1) - date(y2, m2, d2)).days

    week = sum(n for dk, n in day_cnt.items() if _off(dk) <= 6)
    last_week = sum(n for dk, n in day_cnt.items() if 7 <= _off(dk) <= 13)
    hours, with_time = [0] * 24, 0
    for q in qs:
        t = q.get("do_time") or ""
        if len(t) >= 13 and t[10] in "T ":
            with_time += 1
            hours[int(t[11:13])] += 1
    best_from, best_n = 0, -1
    for s in range(22):
        n = hours[s] + hours[s + 1] + hours[s + 2]
        if n > best_n:
            best_n, best_from = n, s
    kp_cnt = {}
    for q in qs:
        for k in (q.get("knowledge_points") or []):
            kp_cnt[k] = kp_cnt.get(k, 0) + 1
    top_kp = sorted(kp_cnt.items(), key=lambda kv: (-kv[1], kv[0]))[0] if kp_cnt else None
    n_expl = sum(1 for q in qs if q.get("has_explanation"))
    month_cnt = {}
    for q in qs:
        mk = (q.get("created_at") or "")[:7]
        if mk:
            month_cnt[mk] = month_cnt.get(mk, 0) + 1
    et_cnt = {}
    for q in qs:
        v = q.get("error_type")
        if v:
            et_cnt[v] = et_cnt.get(v, 0) + 1
    subj_cnt = {}
    for q in qs:
        subj_cnt[q["subject"]] = subj_cnt.get(q["subject"], 0) + 1
    # 成长开篇月数：与 app.js spanMonths 同口径——第一道错题到数据更新日
    # （generated_at，样例每次生成都是「现在」）经历的月数，round(天数/30) 至少 1；
    # 与柱图月份格数（入过库的日历月数）不是一回事，页面两处各说各的。
    span = 0
    if qs:
        qs_sorted = sorted(qs, key=lambda q: q.get("created_at") or "")
        first = (qs_sorted[0].get("created_at") or "")[:10]
        last = (idx.get("generated_at") or "")[:10] or (qs_sorted[-1].get("created_at") or "")[:10]
        if first and last:
            span = max(1, int((date.fromisoformat(last) - date.fromisoformat(first)).days / 30 + 0.5))
    return {"qs": qs, "week": week, "last_week": last_week, "with_time": with_time,
            "best_from": best_from, "best_n": best_n, "top_kp": top_kp, "n_expl": n_expl,
            "month_cnt": month_cnt, "et_cnt": et_cnt, "subj_cnt": subj_cnt,
            "span": span, "total": len(qs)}


def run(base):
    with sync_playwright() as p:
        exe = find_chrome()
        browser = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
        errors = []

        # ---------------- 手机视口 ----------------
        page = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" and "favicon" not in (m.location.get("url") or "") else None)

        # ---- 首页 · 学习近况（v1.5.0 重构） ----
        page.goto(base + "/#/", wait_until="networkidle")
        page.wait_for_selector(".home-tag", timeout=8000)
        idx = load_index()
        D = derive(idx)
        qs, total, n_expl = D["qs"], D["total"], D["n_expl"]

        check("近况开篇第一句：本周入库数与数据一致",
              "这一周" in page.locator(".home-tag").inner_text() and str(D["week"]) in page.locator(".home-tag").inner_text(),
              page.locator(".home-tag").inner_text())
        note1 = page.locator(".home-note").first.inner_text()
        check("近况第二句：做错时段两数与数据一致",
              str(D["with_time"]) in note1 and str(D["best_n"]) in note1, note1)
        check("近况第二句：时段窗取数据里最高的 3 小时连续段",
              "%02d:00 到 %02d:00" % (D["best_from"], D["best_from"] + 3) in note1, note1)
        check("近况第二句：与上周的对比据实生成",
              ("和上周一样稳" in note1) == (D["week"] == D["last_week"]),
              (D["week"], D["last_week"], note1))
        note2 = page.locator(".home-note").nth(1).inner_text()
        check("近况第三句：最硬骨头与讲解覆盖数与数据一致",
              D["top_kp"][0] in note2 and str(D["top_kp"][1]) in note2
              and str(total) in note2 and str(n_expl) in note2, note2)
        check("近况第三句：未讲数可点进筛选态",
              page.locator('.home-note a[href*="expl=no"]').count() == 1
              and str(total - n_expl) in note2, note2)
        check("近况开篇不是数字卡阵（两句叙事 + 无卡片/统计格容器）",
              page.locator(".home-note").count() == 2 and
              page.evaluate("document.querySelectorAll('.home-lead [class*=card], .home-lead [class*=stat], "
                            ".home-lead [class*=kpi], .milestone [class*=card]').length") == 0)
        check("近况六个导航且「近况」为当前项",
              page.locator("#tabs a").count() == 6 and
              page.locator('#tabs a[aria-current="page"]').inner_text() == "近况")
        check("窄屏导航用短标签（六项在 390 下不撑破）",
              [a.inner_text() for a in page.locator("#tabs a").all()]
              == ["近况", "成长", "讲解", "切题", "积累册", "知识点"],
              [a.inner_text() for a in page.locator("#tabs a").all()])
        ms_done = (total // 50) * 50
        if ms_done:
            check("里程碑带盖已达成印（第 %d 道）" % ms_done,
                  page.locator(".milestone-seal").count() == 1,
                  page.locator(".milestone-seal").inner_text())
        else:
            check("里程碑带：未达成第一枚印时不摆空印", page.locator(".milestone-seal").count() == 0)
            check("里程碑带：下一枚印与「还差 N 道」诚实呈现",
                  "第 50 道" in page.locator(".milestone-t").inner_text()
                  and str(50 - total) in page.locator(".milestone-sub").inner_text(),
                  page.locator(".milestone-sub").inner_text())
        gw = page.evaluate("parseFloat(document.querySelector('.gauge i').style.width)")
        check("讲解覆盖 gauge 为真比例", abs(gw - n_expl / total * 100) < 0.15, gw)
        check("gauge 标签给出覆盖数与差额",
              "讲解覆盖" in page.locator(".gauge-label").first.inner_text()
              and str(total - n_expl) in page.locator(".gauge-label").last.inner_text())
        check("首页最近讲解 ≥1 条", page.locator(".home-lead ~ .sec-h").count() >= 1)
        check("最近讲解 3 行、最近切题 2 行（辅助位）",
              page.locator(".rows .row").count() == 3 and page.locator(".sess").count() == 2,
              (page.locator(".rows .row").count(), page.locator(".sess").count()))
        check("首页最近切题有缩略图", page.locator(".sess-thumbs img").count() >= 1)
        check("无讲解数可点击跳到筛选态", page.locator('.home-note a[href*="expl=no"]').count() == 1)
        check("页脚有数据时间", "数据更新于" in page.locator("#foot-meta").inner_text())
        check("390px 首页无横向溢出",
              page.evaluate("document.documentElement.scrollWidth - window.innerWidth") == 0,
              page.evaluate("document.documentElement.scrollWidth - window.innerWidth"))
        check("首页最近讲解首条显示讲解 summary（契约 v1.1）",
              page.locator(".row .row-q").first.inner_text()
              == "铁比铜活泼，铁表面析出红色铜、溶液由蓝变浅绿；观察题要写全「固体+溶液」两个现象。",
              page.locator(".row .row-q").first.inner_text())
        check("首页无 summary 的讲解回退题干",
              page.locator(".row .row-q").nth(2).inner_text().startswith("串联电路中滑动变阻器"),
              page.locator(".row .row-q").nth(2).inner_text())
        check("尾部成长入口为交叉链接",
              page.locator('.crosslink a[href="#/growth"]').count() == 1,
              page.locator(".crosslink").inner_text())
        check("近况页区块「全部」链接都指向真实路由（不摆空链接）",
              page.locator(".sec-more").count() == 2 and
              page.evaluate("Array.from(document.querySelectorAll('.sec-more')).every("
                            "function(a){return (a.getAttribute('href')||'').indexOf('#/') === 0;})"))
        check("近况页不渲染 mastery/resolved/review_count",
              page.evaluate("['mastery','resolved','review_count','掌握度','已解决'].some("
                            "function(w){return document.getElementById('app').innerText.indexOf(w)>=0;})") is False)
        shot(page, "m1-home-light")

        # ---- 主题切换 ----
        page.click("#theme-btn")
        page.wait_for_timeout(120)
        check("切到夜间模式", page.evaluate("document.documentElement.dataset.theme") == "dark")
        check("夜间按钮文案变为日间", page.locator("#theme-btn-label").inner_text() == "日间")
        bg = page.evaluate("getComputedStyle(document.body).backgroundColor")
        check("夜间底色为暖墨而非纯黑", bg == "rgb(22, 19, 15)", bg)
        seal_bg = page.evaluate("getComputedStyle(document.querySelector('.milestone-seal, .seal-mark')).backgroundColor")
        check("夜间朱印/方印仍为朱红系", seal_bg in ("rgb(217, 105, 79)", "rgb(156, 43, 31)"), seal_bg)
        shot(page, "m2-home-dark")
        page.reload(wait_until="networkidle")
        check("刷新后保持夜间（localStorage）", page.evaluate("document.documentElement.dataset.theme") == "dark")
        page.click("#theme-btn")
        page.wait_for_timeout(120)
        check("切回日间模式", page.evaluate("document.documentElement.dataset.theme") == "light")

        # ---- 成长视图（样例数据） ----
        page.goto(base + "/#/growth", wait_until="networkidle")
        page.wait_for_selector(".chart", timeout=8000)
        mlist = sorted(D["month_cnt"])
        check("成长导航为当前项且共 6 项",
              page.locator('#tabs a[aria-current="page"]').inner_text() == "成长" and
              page.locator("#tabs a").count() == 6)
        check("成长开篇：月数与总题数与数据一致",
              page.locator(".home-tag").inner_text()
              == cn_count(D["span"]) + "个月，" + str(total) + " 道错题。",
              page.locator(".home-tag").inner_text())
        check("月度柱图格数 == 有入库月份数",
              page.locator(".chart .col").count() == len(mlist),
              (page.locator(".chart .col").count(), len(mlist)))
        check("柱值标签与当月入库数一致",
              [int(x) for x in page.locator(".chart .val").all_inner_texts()] == [D["month_cnt"][m] for m in mlist],
              page.locator(".chart .val").all_inner_texts())
        hs = page.evaluate("Array.from(document.querySelectorAll('.chart .bar')).map(b => b.getBoundingClientRect().height)")
        mx = max(D["month_cnt"].values())
        if len(hs) == len(mlist) and min(hs) > 0:
            ratios = [round(h / max(hs), 3) for h in hs]
            expect = [round(D["month_cnt"][m] / mx, 3) for m in mlist]
            check("柱高为真比例（对最高月归一）", all(abs(a - b) <= 0.06 for a, b in zip(ratios, expect)),
                  (ratios, expect))
        check("当前月柱为朱红、历史月为墨色",
              page.evaluate("getComputedStyle(document.querySelector('.chart .col.now .bar')).backgroundColor") == "rgb(156, 43, 31)"
              and page.evaluate("getComputedStyle(document.querySelector('.chart .col:not(.now) .bar')).backgroundColor") == "rgb(33, 30, 26)")
        check("月份刻度为等宽字体",
              "JetBrains Mono" in page.evaluate("getComputedStyle(document.querySelector('.mrow-h .m')).fontFamily"))
        check("月度登记行数 == 有入库月份数", page.locator(".mrow").count() == len(mlist),
              (page.locator(".mrow").count(), len(mlist)))
        check("成长页区块标题不摆空「全部」链接（没有可去的「全部」）",
              page.locator(".sec-more").count() == 0 and
              page.evaluate("Array.from(document.querySelectorAll('.sec-h a')).filter("
                            "function(a){return !a.getAttribute('href');}).length") == 0)
        mrow1 = page.locator(".mrow-h .n").first.inner_text()
        check("登记行含收错题与新增知识点（原始标签口径）",
              ("收错题 %d" % D["month_cnt"][mlist[0]]) in mrow1 and "新增知识点" in mrow1, mrow1)
        check("登记行注明原始标签与受控概念两种口径",
              "受控概念" in page.locator(".reg-note").first.inner_text())
        all_tags = set()
        for q in qs:
            for k in (q.get("knowledge_points") or []):
                all_tags.add(k)
        cov_rows = page.locator(".reg").nth(0).locator(".reg-row")
        check("知识覆盖行数 == 月份数", cov_rows.count() == len(mlist), cov_rows.count())
        check("覆盖行累计等于原始标签去重总数",
              str(len(all_tags)) in cov_rows.last.inner_text(), cov_rows.last.inner_text())
        subj_rows = page.locator(".reg").nth(1).locator(".reg-row")
        subj_ns = [re.match(r"^(\d+) (\d+\.\d)%$", t.strip())
                   for t in subj_rows.locator(".n").all_inner_texts()]
        check("科目分布行数与数据一致", subj_rows.count() == len(D["subj_cnt"]),
              (subj_rows.count(), len(D["subj_cnt"])))
        check("科目行计数与百分比与数据一致",
              all(subj_ns) and sorted(int(m.group(1)) for m in subj_ns) == sorted(D["subj_cnt"].values())
              and all(abs(float(m.group(2)) - int(m.group(1)) / total * 100) < 0.06 for m in subj_ns),
              subj_rows.locator(".n").all_inner_texts())
        subj_bars = page.evaluate("Array.from(document.querySelectorAll('.reg')[1]"
                                  ".querySelectorAll('.reg-bar i')).map(b => parseFloat(b.style.width))")
        check("科目发丝条为真比例",
              len(subj_bars) == len(subj_ns) and
              all(abs(w - int(m.group(1)) / total * 100) < 0.06 for w, m in zip(subj_bars, subj_ns)),
              subj_bars)
        if D["et_cnt"]:
            et_rows = page.locator(".reg").nth(2).locator(".reg-row")
            et_ns = [re.match(r"^(\d+) (\d+\.\d)%$", t.strip())
                     for t in et_rows.locator(".n").all_inner_texts()]
            n_et = sum(D["et_cnt"].values())
            check("错题结构行数 == 有归因标签的题数（类型数）",
                  et_rows.count() == len(D["et_cnt"]), (et_rows.count(), len(D["et_cnt"])))
            check("错题类型计数与比例按打了标签的题算",
                  all(et_ns) and sorted(int(m.group(1)) for m in et_ns) == sorted(D["et_cnt"].values())
                  and all(abs(float(m.group(2)) - int(m.group(1)) / n_et * 100) < 0.06 for m in et_ns),
                  et_rows.locator(".n").all_inner_texts())
            et_note = page.locator(".reg-note").nth(1).inner_text()
            if n_et < total:
                check("归因未全覆盖时注明分母口径", ("%d / %d" % (n_et, total)) in et_note, et_note)
            top_et_n = max(D["et_cnt"].values())
            if D["et_cnt"].get("concept", 0) == top_et_n and top_et_n / n_et > 0.5:
                check("一半以上错在概念时给设计稿解读",
                      "一半以上" in et_note and "概念" in et_note, et_note)
            else:
                check("概念未过半时解读据实生成（不套设计稿那句）",
                      "一半以上" not in et_note and "下一份讲解" in et_note, et_note)
        else:
            check("无归因标签时错题结构区整体不渲染", page.locator(".reg").count() == 2)
        check("学习阶梯四级且当前级唯一",
              page.locator(".lstep").count() == 4 and page.locator(".lstep.now").count() == 1)
        check("阶梯当前级 = 让复习转起来（review_backlog>0 且复习极少）",
              page.locator(".lstep.now .lname").inner_text().startswith("让复习转起来")
              and "你在这儿" in page.locator(".lhere").inner_text())
        rb = idx["stats"].get("review_backlog")
        overdue = rb["overdue"] if isinstance(rb, dict) else rb
        l2 = page.locator(".lstep.now .lev").inner_text()
        check("阶梯当前级给出已到期数字（stats.review_backlog）", str(overdue) in l2, l2)
        check("阶梯上两级零假进度（无百分比/勾选/待补充/禁用）",
              page.locator(".lstep:not(.done):not(.now)").count() == 2 and
              page.evaluate("document.querySelectorAll('.lstep [disabled], .lstep[aria-disabled]').length") == 0
              and "待补充" not in page.locator(".ladder").inner_text()
              and "%" not in page.locator(".lstep:not(.done):not(.now) .lev").first.inner_text())
        check("下一件事从最近讲过的题起步并挂去讲解查阅",
              "最近讲过的" in page.locator(".nextstep-p").inner_text()
              and page.locator('.nextstep-a[href="#/teach"]').count() == 1)
        check("下一件事给出已到期与当天到期数", str(overdue) in page.locator(".nextstep").inner_text())
        check("390px 成长视图无横向溢出",
              page.evaluate("document.documentElement.scrollWidth - window.innerWidth") == 0,
              page.evaluate("document.documentElement.scrollWidth - window.innerWidth"))
        new_blocks = "".join(page.locator(".chart, .reg, .ladder, .nextstep, .mrow, .crosslink, .milestone")
                             .all_inner_texts())
        check("新增区块无 emoji（反模式纪律）", not EMOJI.search(new_blocks), EMOJI.search(new_blocks))
        small = page.evaluate("""Array.from(document.querySelectorAll('#app *')).filter(function(e){
            if (!e.textContent.trim() || e.children.length) return false;
            var fs = parseFloat(getComputedStyle(e).fontSize);
            var mono = getComputedStyle(e).fontFamily.indexOf('JetBrains') >= 0;
            if (e.classList.contains('brand-sub')) return false;
            return fs < 14 && !(fs >= 13 && mono);
        }).map(function(e){return (e.className||e.tagName)+':'+getComputedStyle(e).fontSize;})""")
        check("成长页字号地板 14px（13px 仅等宽刻度）", not small, small[:5])
        pills = page.evaluate("Array.from(document.querySelectorAll('body *')).filter("
                              "function(e){return getComputedStyle(e).borderRadius === '999px';}).length")
        check("成长页无胶囊堆（999px 圆角仅主题钮）", pills == 1, pills)
        anims = page.evaluate("""Array.from(document.querySelectorAll('body *'))
            .filter(function(e){return getComputedStyle(e).animationName !== 'none' && !e.closest('[hidden]');})
            .map(function(e){return getComputedStyle(e).animationName;})""")
        check("动效仍只有路由淡入一种（≤2 种）", len(set(anims)) <= 2, anims)
        shot(page, "m18-growth-light")

        # ---- 成长视图 · 夜间 ----
        set_theme(page, "dark")
        page.goto(base + "/#/growth", wait_until="networkidle")
        page.wait_for_selector(".chart", timeout=8000)
        bg = page.evaluate("getComputedStyle(document.body).backgroundColor")
        check("夜间成长页底色为暖墨", bg == "rgb(22, 19, 15)", bg)
        now_bar = page.evaluate("getComputedStyle(document.querySelector('.chart .col.now .bar')).backgroundColor")
        check("夜间当前月柱仍为朱红", now_bar == "rgb(217, 105, 79)", now_bar)
        lmark = page.evaluate("getComputedStyle(document.querySelector('.lstep.now .lmark')).backgroundColor")
        check("夜间阶梯当前级节点为朱红", lmark == "rgb(217, 105, 79)", lmark)
        shot(page, "m19-growth-dark")
        set_theme(page, "light")

        # ---- 讲解查阅 · 列表 ----
        page.goto(base + "/#/teach", wait_until="networkidle")
        page.wait_for_selector(".row", timeout=8000)
        n_all = page.locator(".row").count()
        check("列表渲染全部 14 题", n_all == 14, n_all)
        check("结果行显示题数", page.locator(".result-line b").inner_text() == "14")
        check("科目分段控件含全部与各科", page.locator('.seg-btn[data-f="subject"]').count() >= 4)
        check("列表行是档案条目（无卡片边框）",
              page.evaluate("getComputedStyle(document.querySelector('.row')).borderTopWidth") == "0px")

        # 契约 v1.1：缩略图（thumb 两态）
        with open(os.path.join(ROOT, "data", "index.json"), encoding="utf-8") as f:
            idx = json.load(f)
        n_thumb = sum(1 for q in idx["questions"] if q.get("thumb"))
        n_summary = sum(1 for e in idx["explanations"] if e.get("summary"))
        n_err = sum(1 for q in idx["questions"] if q.get("error_type"))
        st = idx.get("stats") or {}
        check("样例数据契约 v1.4 两态覆盖（thumb/summary/error_type 部分缺席、summary≤80、版本 v1.4）",
              idx.get("contract_version") == "v1.4"
              and 0 < n_thumb < len(idx["questions"])
              and 0 < n_summary < len(idx["explanations"])
              and 0 < n_err < len(idx["questions"])
              and all(len(e["summary"]) <= 80 for e in idx["explanations"] if e.get("summary")),
              (idx.get("contract_version"), n_thumb, n_summary, n_err))
        check("样例 stats 带 v1.3 新字段（review_backlog/crop_figures）",
              isinstance(st.get("review_backlog"), dict) and st["review_backlog"].get("overdue") is not None
              and isinstance(st.get("crop_figures"), int),
              json.dumps({k: st.get(k) for k in ("review_backlog", "crop_figures")}, ensure_ascii=False))
        check("讲解列表缩略图数量与数据一致（部分题有 thumb）",
              page.locator(".row-thumb").count() == n_thumb,
              (page.locator(".row-thumb").count(), n_thumb))
        t0 = page.locator(".row-thumb").first
        check("缩略图 src 指向 thumbs 且 lazy/async",
              (t0.get_attribute("src") or "").startswith("data/thumbs/")
              and t0.get_attribute("loading") == "lazy"
              and t0.get_attribute("decoding") == "async",
              (t0.get_attribute("src"), t0.get_attribute("loading"), t0.get_attribute("decoding")))
        alt0 = t0.get_attribute("alt") or ""
        check("缩略图 alt 用题号", alt0.startswith("题 #") and alt0[3:].isdigit(), alt0)
        form = page.evaluate("(function(){var rows=Array.prototype.slice.call(document.querySelectorAll('.row'));"
                             "return {rows: rows.length,"
                             "thumb: rows.filter(function(r){return r.querySelector('.row-thumb');}).length,"
                             "missing: document.querySelectorAll('.row .img-missing').length,"
                             "stray: rows.filter(function(r){return Array.prototype.some.call("
                             "r.querySelectorAll('img'),function(i){return !i.classList.contains('row-thumb');});})"
                             ".length};})()")
        check("无 thumb 行保持纯文字（无破图/无占位框/无杂图）",
              form["rows"] == n_all and form["thumb"] == n_thumb
              and form["missing"] == 0 and form["stray"] == 0, form)
        check("390px 讲解列表无横向溢出",
              page.evaluate("document.documentElement.scrollWidth - window.innerWidth") == 0,
              page.evaluate("document.documentElement.scrollWidth - window.innerWidth"))
        shot(page, "m13-teach-thumbs")

        page.click('.seg-btn[data-f="subject"][data-v="physics"]')
        page.wait_for_timeout(150)
        check("科目筛选：物理 = 4 题", page.locator(".row").count() == 4, page.locator(".row").count())
        check("筛选写入 hash，可分享/后退", "subject=physics" in page.url)
        check("物理段为选中态", page.locator('.seg-btn[data-v="physics"]').get_attribute("aria-pressed") == "true")
        shot(page, "m3-teach-physics")

        page.click('.seg-btn[data-f="subject"][data-v="all"]')
        page.wait_for_timeout(150)
        page.click('.seg-btn[data-f="expl"][data-v="no"]')
        page.wait_for_timeout(150)
        n_no = page.locator(".row").count()
        check("无讲解筛选生效", n_no == 4, n_no)
        check("无讲解行有未讲标记", page.locator(".row-idx .st.no").count() == n_no)

        # 关键词（先清掉无讲解筛选，避免复合条件把结果数压到 0）
        page.goto(base + "/#/teach", wait_until="networkidle")
        page.wait_for_selector(".row")
        page.fill("#kw-input", "方程")
        page.wait_for_timeout(500)
        check("关键词过滤生效", page.locator(".row").count() >= 1)
        page.fill("#kw-input", "")
        page.wait_for_timeout(500)
        page.click("#reset-all") if page.locator("#reset-all").count() else None
        page.goto(base + "/#/teach", wait_until="networkidle")
        page.wait_for_selector(".row")

        # 排序
        first_new = page.locator(".row").first.locator(".row-idx").inner_text()
        page.click("#sort-toggle")
        page.wait_for_timeout(150)
        first_old = page.locator(".row").first.locator(".row-idx").inner_text()
        check("排序切换改变首条", first_new != first_old, (first_new, first_old))
        page.click("#sort-toggle")
        page.wait_for_timeout(150)

        # 知识点面板
        page.click("#kp-open")
        page.wait_for_selector("#kp-sheet", timeout=4000)
        check("知识点面板打开", page.locator("#kp-sheet").is_visible())
        check("面板是 dialog 且焦点在搜索框",
              page.locator("#kp-sheet").get_attribute("role") == "dialog" and
              page.evaluate("document.activeElement.id") == "kp-search")
        page.fill("#kp-search", "判别式")
        page.wait_for_timeout(200)
        check("面板内搜索过滤", page.locator(".kp-item").count() == 1, page.locator(".kp-item").count())
        page.wait_for_timeout(400)
        shot(page, "m4b-kp-sheet")
        page.click(".kp-item")
        page.wait_for_timeout(120)
        check("知识点可多选（aria-pressed）", page.locator('.kp-item[aria-pressed="true"]').count() == 1)
        page.click("#kp-done")
        page.wait_for_timeout(250)
        check("选完关闭面板并回到结果", page.locator("#kp-sheet").count() == 0)
        check("已选知识点显示为摘要行", "已按" in page.locator(".kp-summary").inner_text())
        check("hash 带 kp 参数", "kp=" in page.url)
        shot(page, "m4-teach-kp-selected")

        # Esc 关闭
        page.click("#kp-open")
        page.wait_for_selector("#kp-sheet")
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)
        check("Esc 关闭知识点面板", page.locator("#kp-sheet").count() == 0)
        page.click("#kp-clear")
        page.wait_for_timeout(200)
        check("清空知识点", page.locator(".kp-summary").count() == 0)

        # 空态
        page.goto(base + "/#/teach?kw=zzz不存在的关键词", wait_until="networkidle")
        page.wait_for_timeout(400)
        check("空态有提示与清空动作", "没有符合条件" in page.locator(".empty").inner_text()
              and page.locator("#reset-all").count() == 1)

        # ---- 题目详情 ----
        page.goto(base + "/#/teach/q/15", wait_until="networkidle")
        page.wait_for_selector(".reading", timeout=8000)
        check("详情页有题图", page.locator("#q-img").count() == 1)
        check("详情页有 OCR 全文", "一元二次方程" in page.locator(".reading").inner_text())
        check("详情头部带年级", "初三" in page.locator(".detail-id").inner_text())
        check("我的答案/正确答案分区", page.locator(".ans-row").count() == 2)
        check("知识点为链接", page.locator(".kp-line a").count() == 2)
        page.wait_for_timeout(600)
        check("讲解 md 渲染（小节 + 档案注记）",
              page.locator(".md .md-h").count() >= 3 and
              page.locator(".md-note").count() == 1)
        check("md 一级标题不重复页面头部", page.locator(".md h1").count() == 0)
        check("版本切换默认 v2", page.locator('.vers button[aria-selected="true"]').inner_text().startswith("v2"))
        check("注记只留版本/体量/provenance（不含已在头部的 id·学科·年级）",
              "字" in page.locator(".md-note").inner_text()
              and "模型" in page.locator(".md-note").inner_text()
              and "学科" not in page.locator(".md-note").inner_text())
        shot(page, "m5-detail-v2", full=True)

        page.click('.vers button[data-v="v1"]')
        page.wait_for_timeout(600)
        check("切到 v1 渲染对应内容", page.locator('.vers button[aria-selected="true"]').inner_text().startswith("v1"))
        check("v1 无重讲标记", "重讲" not in page.locator('.vers button[data-v="v1"]').inner_text())
        check("无 crop_session 的题不出「出自切题」回链",
              page.locator('#app a[href^="#/crop/s/"]').count() == 0)

        # 契约 v1.1：详情页切题回链（有 crop_session 的题）
        page.goto(base + "/#/teach/q/7", wait_until="networkidle")
        page.wait_for_selector(".hint")
        bl = page.locator('.hint a[href="#/crop/s/crop_1792467600000_hw_1024"]')
        check("详情出自切题回链指向原会话（encode 后 href 正确）", bl.count() == 1, bl.count())
        check("390px 题目详情无横向溢出",
              page.evaluate("document.documentElement.scrollWidth - window.innerWidth") == 0,
              page.evaluate("document.documentElement.scrollWidth - window.innerWidth"))
        bl.click()
        page.wait_for_selector(".crop-cell", timeout=8000)
        check("出自切题回链落到会话网格", page.locator(".crop-cell").count() == 5,
              page.locator(".crop-cell").count())

        # 无讲解的题
        page.goto(base + "/#/teach/q/23", wait_until="networkidle")
        page.wait_for_selector(".block")
        check("无讲解题显示空态说明", "还没有讲解记录" in page.locator("#expl-body").inner_text())

        # 灯箱
        page.goto(base + "/#/teach/q/15", wait_until="networkidle")
        page.wait_for_selector("#q-img")
        page.click("#q-img")
        page.wait_for_timeout(200)
        check("点题图开灯箱", page.locator("#lightbox").is_visible())
        check("灯箱有关闭与缩放按钮", page.locator("#lb-close").count() == 1 and page.locator("#lb-zoom").count() == 1)
        shot(page, "m6-lightbox")
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)
        check("Esc 关灯箱", not page.locator("#lightbox").is_visible())

        # 不存在的题
        page.goto(base + "/#/teach/q/99999", wait_until="networkidle")
        check("题目不存在时有明确错误态", "找不到这道题" in page.locator(".err").inner_text())

        # ---- 切题库 ----
        page.goto(base + "/#/crop", wait_until="networkidle")
        page.wait_for_selector(".sess", timeout=8000)
        check("切题库按日期分组", page.locator(".date-h").count() >= 3)
        check("日期组显示题数", "题" in page.locator(".date-h .n").first.inner_text())
        check("会话行有缩略图与题数", page.locator(".sess-thumbs img").count() >= 3)
        check("长 session id 不当标题", "crop_" not in page.locator(".sess-t").first.inner_text())
        shot(page, "m7-crop-dates")
        check("390px 切题日期列表无横向溢出",
              page.evaluate("document.documentElement.scrollWidth - window.innerWidth") == 0,
              page.evaluate("document.documentElement.scrollWidth - window.innerWidth"))

        page.locator(".sess").first.click()
        page.wait_for_selector(".crop-cell", timeout=8000)
        check("会话网格渲染", page.locator(".crop-cell").count() >= 2)
        check("网格标注题号", page.locator(".crop-cell .cc-q").first.inner_text().startswith("Q"))
        # 有标注（含 null=未收录）的格子必须给出状态；没有该字段的格子保持安静，不摆"待确认"
        n_cells = page.locator(".crop-cell").count()
        n_marked = page.locator(".crop-cell .cc-eb").count()
        check("网格只对已标注的切题显示状态（不摆待确认占位）",
              0 < n_marked < n_cells, (n_marked, n_cells))
        check("未收录状态可读", page.locator(".crop-cell .cc-eb.none").count() >= 1)
        shot(page, "m9-crop-grid")
        check("390px 会话网格无横向溢出",
              page.evaluate("document.documentElement.scrollWidth - window.innerWidth") == 0,
              page.evaluate("document.documentElement.scrollWidth - window.innerWidth"))
        page.locator(".crop-cell").first.click()
        page.wait_for_selector("#prob-img", timeout=8000)
        check("单题大图页", page.locator("#prob-img").count() == 1)
        check("大图页有上一题/下一题导航", page.locator(".pnav .btn").count() >= 1)
        check("大图页显示位置", "/" in page.locator(".pnav .pos").inner_text())
        shot(page, "m8-crop-problem")
        check("390px 单题大图无横向溢出",
              page.evaluate("document.documentElement.scrollWidth - window.innerWidth") == 0,
              page.evaluate("document.documentElement.scrollWidth - window.innerWidth"))

        # ---- v1.6.0：切题库「题干 + 附图」组合排版 ----
        # 显式进入样例里带 1 张真实量级附图的题（crop_1791710984244_hw_1005 第 1 题）：
        # 切题库会话按日期倒排（app.js sortedSessions），点击顺序落到的首会话
        # crop_1792467600000_hw_1024 第 1 题没有 figure_* 三键、.prob-figs 永不出现，
        # 沿用点击顺序会让下面的等待必超时——与下面各子用例一样按 URL 导航。
        page.goto(base + "/#/crop/s/crop_1791710984244_hw_1005/1", wait_until="networkidle")
        page.wait_for_selector("#prob-img", timeout=8000)
        page.wait_for_selector(".prob-figs", timeout=8000)
        check("题干图在前、附图区在其后（组合排版顺序）",
              bool(page.evaluate(
                  "document.getElementById('prob-img').compareDocumentPosition("
                  "document.querySelector('.prob-figs')) & Node.DOCUMENT_POSITION_FOLLOWING")))
        check("附图区区头 + 1 张附图",
              page.locator(".prob-figs-h").count() == 1 and page.locator(".prob-fig").count() == 1)
        check("附图标签「附图 1」，src 与题干图同目录",
              page.locator(".prob-fig figcaption").inner_text() == "附图 1"
              and page.locator(".prob-fig img").get_attribute("src")
              == "data/incoming/crop/crop_1791710984244_hw_1005/q01-fig1.jpg",
              page.locator(".prob-fig img").get_attribute("src"))
        check("附图按实际尺寸展示（最小边 >= 100px 过滤阈值口径）",
              page.evaluate("() => { var i=document.querySelector('.prob-fig img');"
                            "return i.complete && Math.min(i.naturalWidth,i.naturalHeight)>=100; }"))
        shot(page, "m24-crop-prob-figs")
        check("390px 单题大图（含附图区）无横向溢出",
              page.evaluate("document.documentElement.scrollWidth - window.innerWidth") == 0,
              page.evaluate("document.documentElement.scrollWidth - window.innerWidth"))
        page.locator(".prob-fig img").click()
        page.wait_for_timeout(200)
        check("点附图开灯箱（与题干大图同一查看交互）", page.locator("#lightbox").is_visible())
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)

        # 无附图题：figure_* 三键都不存在 -> 附图区零渲染（回归硬约束）
        page.goto(base + "/#/crop/s/crop_1791710984244_hw_1005/3", wait_until="networkidle")
        page.wait_for_selector("#prob-img", timeout=8000)
        check("无附图题不出附图区（figure_* 缺席时零渲染）",
              page.locator(".prob-figs").count() == 0 and page.locator(".prob-fig").count() == 0)
        check("无附图题视图其余结构不变（题干图/导航/位置/注记齐全）",
              page.locator("#prob-img").count() == 1 and page.locator(".pnav .btn").count() >= 1
              and "/" in page.locator(".pnav .pos").inner_text()
              and page.locator(".hint").count() >= 1)

        # 多附图题：两张附图按序标注
        page.goto(base + "/#/crop/s/crop_1792467600000_hw_1024/4", wait_until="networkidle")
        page.wait_for_selector(".prob-fig", timeout=8000)
        check("多附图题两张附图按序标注「附图 1」「附图 2」",
              page.locator(".prob-fig").count() == 2
              and page.locator(".prob-fig figcaption").all_inner_texts() == ["附图 1", "附图 2"],
              page.locator(".prob-fig figcaption").all_inner_texts())
        check("390px 多附图无横向溢出",
              page.evaluate("document.documentElement.scrollWidth - window.innerWidth") == 0,
              page.evaluate("document.documentElement.scrollWidth - window.innerWidth"))

        # 极小误报附图（95×42 原图 px）：加载后过滤，附图区整体消失
        page.goto(base + "/#/crop/s/crop_1792294800000_hw_1019/1", wait_until="networkidle")
        page.wait_for_selector("#prob-img", timeout=8000)
        page.wait_for_function("() => !document.querySelector('.prob-figs')", timeout=8000)
        check("极小误报附图（最小边 < 100px）被过滤、附图区整体消失",
              page.locator(".prob-figs").count() == 0 and page.locator(".prob-fig").count() == 0)

        # 附图文件缺失：降位为说明框，不破版
        page.goto(base + "/#/crop/s/crop_1792121900000_hw_1015/1", wait_until="networkidle")
        page.wait_for_selector("#prob-img", timeout=8000)
        page.wait_for_selector(".prob-fig .img-missing", timeout=8000)
        check("附图加载失败降位为说明框（不破版、不留空 figure）",
              page.locator(".prob-fig .img-missing").count() == 1
              and page.locator(".prob-fig img").count() == 0
              and page.locator("#prob-img").count() == 1,
              page.locator(".img-missing").inner_text())
        check("390px 附图降位后无横向溢出",
              page.evaluate("document.documentElement.scrollWidth - window.innerWidth") == 0,
              page.evaluate("document.documentElement.scrollWidth - window.innerWidth"))

        # 上一题/下一题
        page.click(".pnav .btn:has-text('下一题')")
        page.wait_for_timeout(400)
        check("下一题切换图片", page.locator("#prob-img").get_attribute("src") != "")
        check("回到网格链接可用", page.locator('.backlink[href*="#/crop/s/"]').count() == 1)

        # ---- 积累册 ----
        page.goto(base + "/#/accum", wait_until="networkidle")
        page.wait_for_selector(".arow", timeout=8000)
        check("积累册导航为当前项且共 6 项",
              page.locator('#tabs a[aria-current="page"]').inner_text() == "积累册" and
              page.locator("#tabs a").count() == 6)
        check("积累册列表 4 本", page.locator(".arow").count() == 4, page.locator(".arow").count())
        check("列表行有书名/知识点/题数",
              "样例积累册" in page.locator(".arow-t").first.inner_text() and
              page.locator(".arow-meta").first.inner_text().strip() != "" and
              "题" in page.locator(".arow-n").first.inner_text())
        check("列表是发丝线分栏（无卡片边框）",
              page.evaluate("() => { var s=getComputedStyle(document.querySelector('.arow'));"
                            "return s.borderLeftWidth+' '+s.borderTopWidth+' '+s.borderRightWidth; }") == "0px 0px 0px")
        check("390px 积累册列表无横向溢出",
              page.evaluate("document.documentElement.scrollWidth - window.innerWidth") == 0,
              page.evaluate("document.documentElement.scrollWidth - window.innerWidth"))
        shot(page, "m10-accum-list")

        page.locator(".arow").first.click()
        page.wait_for_selector("#book-frame", timeout=8000)
        check("阅读页 iframe 指向书 html",
              "accum-book/sample-book-1.html" in page.locator("#book-frame").get_attribute("src"))
        check("阅读页有返回积累册链接", page.locator('.backlink[href="#/accum"]').count() == 1)
        note_txt = page.locator(".book-note").inner_text()
        check("档案注记含题数与知识点数", "题" in note_txt and "知识点" in note_txt, note_txt)
        check("PDF 为新窗口次级入口",
              page.locator('.book-pdf[target="_blank"][href$=".pdf"]').count() == 1)
        page.wait_for_function(
            "() => { var f = document.getElementById('book-frame');"
            " return f && f.contentDocument && f.contentDocument.readyState === 'complete'; }",
            timeout=8000)
        check("书 html 在 iframe 内加载成功",
              "样例积累册" in page.evaluate("document.getElementById('book-frame').contentDocument.title"))
        page.wait_for_function(
            "() => document.getElementById('book-frame').style.height !== ''", timeout=8000)
        fh = page.evaluate("document.getElementById('book-frame').getBoundingClientRect().height")
        check("iframe 按文档高度撑开", fh > 320, fh)
        check("390px 阅读页无横向溢出",
              page.evaluate("document.documentElement.scrollWidth - window.innerWidth") == 0,
              page.evaluate("document.documentElement.scrollWidth - window.innerWidth"))
        shot(page, "m11-accum-read")

        page.goto(base + "/#/accum/b/%E4%B8%8D%E5%AD%98%E5%9C%A8%E7%9A%84%E5%86%8C%E5%AD%90",
                  wait_until="networkidle")
        page.wait_for_timeout(300)
        check("不存在的书有明确错误态", "找不到这本积累册" in page.locator(".err").inner_text())

        def _accum_empty(route):
            with open(os.path.join(ROOT, "data", "index.json"), encoding="utf-8") as f:
                d = json.load(f)
            d["accum_books"] = []
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps(d, ensure_ascii=False))
        page.route("**/data/index.json", _accum_empty)
        page.goto(base + "/#/accum")
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(400)
        check("accum_books 为空时空态可读", "还没有积累册" in page.locator(".empty").inner_text())
        page.unroute("**/data/index.json")
        page.reload(wait_until="networkidle")
        page.wait_for_selector(".arow")
        set_theme(page, "dark")
        page.locator(".arow").first.click()
        page.wait_for_selector("#book-frame", timeout=8000)
        bg = page.evaluate("getComputedStyle(document.body).backgroundColor")
        check("夜间阅读页底色为暖墨", bg == "rgb(22, 19, 15)", bg)
        bc = page.evaluate("getComputedStyle(document.getElementById('book-frame')).borderTopColor")
        check("夜间书框为暗色发丝线", bc == "rgb(51, 44, 33)", bc)
        shot(page, "m12-accum-read-dark")
        set_theme(page, "light")

        # ---- 知识点 · 受控概念（契约 v1.2） ----
        page.goto(base + "/#/kp", wait_until="networkidle")
        page.wait_for_selector(".krow", timeout=8000)
        check("知识点导航为当前项且共 6 项",
              page.locator('#tabs a[aria-current="page"]').inner_text() == "知识点" and
              page.locator("#tabs a").count() == 6)
        vocab = idx.get("kp_concepts") or []
        kp_cnt = {}
        for q in idx["questions"]:
            for k in (q.get("kp_concepts") or []):
                kp_cnt[k] = kp_cnt.get(k, 0) + 1
        n_vocab = len(vocab)
        n_listed = sum(1 for c in vocab if kp_cnt.get(c["name"], 0) > 0)
        n_qkp = sum(1 for q in idx["questions"] if q.get("kp_concepts"))
        check("样例数据契约 v1.4 概念两态覆盖（词表 19、部分题带 kp_concepts、N>M）",
              idx.get("contract_version") == "v1.4" and n_vocab == 19
              and 0 < n_qkp < len(idx["questions"]) and 0 < n_listed < n_vocab,
              (n_vocab, n_qkp, n_listed))
        lead = page.locator(".kp-lead").inner_text()
        check("词表规模注记诚实呈现（N 个概念其中 M 个有题）",
              page.locator(".kp-lead").count() == 1
              and "受控词表" in lead and str(n_vocab) in lead and str(n_listed) in lead,
              lead)
        groups = [page.locator(".date-h .d").nth(i).inner_text()
                  for i in range(page.locator(".date-h").count())]
        check("概念按数学/物理/化学分组", groups == ["数学", "物理", "化学"], groups)
        check("只列有题概念（行数 = 有题概念数）",
              page.locator(".krow").count() == n_listed,
              (page.locator(".krow").count(), n_listed))
        r12 = page.locator('.krow[href="#/kp/c/' + quote("一元一次方程") + '"]')
        check("概念行计数与编码链接（一元一次方程 2 题）",
              r12.count() == 1 and r12.inner_text().replace("\n", " ").endswith("2 题"),
              r12.inner_text())
        check("零题概念不摆空行（欧姆定律/酸碱中和反应不出现）",
              page.locator('.krow[href="#/kp/c/' + quote("欧姆定律") + '"]').count() == 0 and
              page.locator('.krow[href="#/kp/c/' + quote("酸碱中和反应") + '"]').count() == 0)
        check("题目数为 mono 刻度",
              "JetBrains Mono" in page.evaluate(
                  "getComputedStyle(document.querySelector('.krow-n')).fontFamily") and
              page.locator(".krow-n").first.inner_text().endswith("题"))
        check("概念列表是发丝线分栏（无卡片边框）",
              page.evaluate("() => { var s=getComputedStyle(document.querySelector('.krow'));"
                            "return s.borderLeftWidth+' '+s.borderTopWidth+' '+s.borderRightWidth; }") == "0px 0px 0px")
        check("390px 概念列表无横向溢出",
              page.evaluate("document.documentElement.scrollWidth - window.innerWidth") == 0,
              page.evaluate("document.documentElement.scrollWidth - window.innerWidth"))
        shot(page, "m15-kp-list")

        r12.click()
        page.wait_for_selector(".book-title", timeout=8000)
        check("概念页标题与科目/题数注记",
              page.locator(".book-title").inner_text() == "一元一次方程" and
              "数学" in page.locator(".book-note").inner_text() and
              "2" in page.locator(".book-note").inner_text(),
              page.locator(".book-note").inner_text())
        check("概念页题目列表条数与缩略图两态（2 行 1 thumb）",
              page.locator(".row").count() == 2 and page.locator(".row-thumb").count() == 1,
              (page.locator(".row").count(), page.locator(".row-thumb").count()))
        check("概念页行指向题目详情",
              page.locator('.row[href="#/teach/q/12"]').count() == 1 and
              page.locator('.row[href="#/teach/q/88"]').count() == 1)
        check("390px 概念页无横向溢出",
              page.evaluate("document.documentElement.scrollWidth - window.innerWidth") == 0,
              page.evaluate("document.documentElement.scrollWidth - window.innerWidth"))
        shot(page, "m16-kp-concept")
        page.locator('.backlink[href="#/kp"]').click()
        page.wait_for_selector(".krow", timeout=8000)
        check("概念页返回链接落回概念列表", page.locator(".krow").count() == n_listed)

        page.goto(base + "/#/kp/c/" + quote("不存在的概念"), wait_until="networkidle")
        page.wait_for_timeout(300)
        check("不存在的概念有明确错误态", "找不到这个受控概念" in page.locator(".err").inner_text())
        page.goto(base + "/#/kp/c/" + quote("欧姆定律"), wait_until="networkidle")
        page.wait_for_timeout(300)
        check("零题概念直输 URL 给错误态", "还没有题目归档" in page.locator(".err").inner_text())

        def _kp_absent(route):
            with open(os.path.join(ROOT, "data", "index.json"), encoding="utf-8") as f:
                d = json.load(f)
            d.pop("kp_concepts", None)
            for q in d["questions"]:
                q.pop("kp_concepts", None)
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps(d, ensure_ascii=False))
        page.route("**/data/index.json", _kp_absent)
        page.goto(base + "/#/kp")
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(400)
        check("kp_concepts 缺席时空态可读（不报错）",
              "数据还没有受控概念归档" in page.locator(".empty").inner_text() and
              page.locator(".krow").count() == 0)
        page.unroute("**/data/index.json")
        page.reload(wait_until="networkidle")
        page.wait_for_selector(".krow")

        set_theme(page, "dark")
        page.goto(base + "/#/kp", wait_until="networkidle")
        page.wait_for_selector(".krow", timeout=8000)
        bg = page.evaluate("getComputedStyle(document.body).backgroundColor")
        check("夜间概念列表底色为暖墨", bg == "rgb(22, 19, 15)", bg)
        kbc = page.evaluate("getComputedStyle(document.querySelector('.krow')).borderBottomColor")
        check("夜间概念行发丝线为暗色", kbc == "rgb(51, 44, 33)", kbc)
        shot(page, "m17-kp-dark")
        set_theme(page, "light")

        # ---- 契约 v1.1：夜间模式下的讲解列表缩略图 ----
        set_theme(page, "dark")
        page.goto(base + "/#/teach", wait_until="networkidle")
        page.wait_for_selector(".row-thumb", timeout=8000)
        bg = page.evaluate("getComputedStyle(document.body).backgroundColor")
        check("夜间列表页底色为暖墨", bg == "rgb(22, 19, 15)", bg)
        tbc = page.evaluate("getComputedStyle(document.querySelector('.row-thumb')).borderTopColor")
        check("夜间缩略图边框为暗发丝线", tbc == "rgb(51, 44, 33)", tbc)
        shot(page, "m14-teach-thumbs-dark")
        set_theme(page, "light")

        # ---- v1.3 新字段缺席降级（route 拦截注入，不摆 0、不摆空框） ----
        def _serve(mutate):
            def _handler(route):
                d = load_index()
                mutate(d)
                route.fulfill(status=200, content_type="application/json",
                              body=json.dumps(d, ensure_ascii=False))
            page.route("**/data/index.json", _handler)
            page.goto(base + "/#/growth")
            page.reload(wait_until="networkidle")
            page.wait_for_timeout(400)

        def _restore():
            page.unroute("**/data/index.json")
            page.reload(wait_until="networkidle")
            page.wait_for_selector(".chart", timeout=8000)

        def _drop_error_type(d):
            for q in d["questions"]:
                q.pop("error_type", None)

        _serve(_drop_error_type)
        app_txt = page.locator("#app").inner_text()
        check("error_type 全缺席时错题结构区整体不渲染（不摆 0、不摆空框）",
              page.locator(".reg").count() == 2 and page.locator(".reg-note").count() == 1
              and "下一份讲解" not in app_txt and "一半以上" not in app_txt,
              page.locator(".reg").count())
        _restore()

        def _drop_backlog(d):
            d["stats"].pop("review_backlog", None)

        _serve(_drop_backlog)
        l2absent = page.locator(".lstep").nth(1).locator(".lev").inner_text()
        check("review_backlog 缺席时阶梯缺数字不摆 0、不标「你在这儿」",
              page.locator(".lstep.now").count() == 0 and page.locator(".lhere").count() == 0
              and not re.search(r"\d", l2absent), l2absent)
        np_absent = page.locator(".nextstep-p").inner_text()
        check("review_backlog 缺席时下一件事不摆到期数、仍给起步量",
              "到期未看" not in np_absent and "最近讲过的" in np_absent, np_absent)
        _restore()

        def _drop_figures(d):
            d["stats"].pop("crop_figures", None)

        _serve(_drop_figures)
        check("crop_figures 缺席时登记行不渲染切题列、说明不给张数",
              "切题" not in page.locator(".mrow-h .n").first.inner_text()
              and "切图一共" not in page.locator(".chart-cap").inner_text(),
              page.locator(".chart-cap").inner_text())
        _restore()

        def _drop_all_new(d):
            for q in d["questions"]:
                q.pop("error_type", None)
            d["stats"].pop("review_backlog", None)
            d["stats"].pop("crop_figures", None)

        _serve(_drop_all_new)
        check("新字段全缺席时成长视图其余区块照常渲染（不报错、不白屏）",
              page.locator(".chart .col").count() == len(mlist) and
              page.locator(".reg").count() == 2 and
              page.locator(".lstep").count() == 4 and
              page.locator(".lstep.now").count() == 0 and
              "切题" not in page.locator(".mrow-h .n").first.inner_text())
        _restore()

        def _scalar_backlog(d):
            d["stats"]["review_backlog"] = 115

        _serve(_scalar_backlog)
        l2scalar = page.locator(".lstep.now .lev").inner_text()
        check("review_backlog 退化为标量时仍显示已到期数字（不摆 0、不摆快照）",
              "115" in l2scalar and "快照" not in l2scalar, l2scalar)
        _restore()

        # ---- 富样例（设计稿实采口径）：已达成里程碑 + 四区全量 + 截图留档 ----
        RICH = build_rich_fixture(load_index())
        RD = derive(RICH)

        def _rich(route):
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps(RICH, ensure_ascii=False))

        page.route("**/data/index.json", _rich)
        page.goto(base + "/#/")
        page.reload(wait_until="networkidle")
        page.wait_for_selector(".home-tag", timeout=8000)
        page.wait_for_timeout(300)
        sq = sorted(RD["qs"], key=lambda q: q["created_at"])
        d50, d100 = sq[49]["created_at"][:10], sq[99]["created_at"][:10]
        r_ms_t = page.locator(".milestone-t").inner_text()
        r_ms_s = page.locator(".milestone-sub").inner_text()
        check("富样例里程碑带：朱印「百」+ 第 50/100 道日期 + 下一枚还差 30 道",
              page.locator(".milestone-seal").inner_text().strip() == "百"
              and ("第 100 道错题，" + d100[5:7] + "-" + d100[8:10]) in r_ms_t
              and ("第 50 道是 " + d50[5:7] + "-" + d50[8:10]) in r_ms_s
              and "第 150 道——还差 30 道" in r_ms_s,
              (page.locator(".milestone-seal").inner_text(), r_ms_t, r_ms_s))
        rgw = page.evaluate("parseFloat(document.querySelector('.gauge i').style.width)")
        check("富样例讲解覆盖 gauge = 102/120 真比例", abs(rgw - 102 / 120 * 100) < 0.15, rgw)
        rnote1 = page.locator(".home-note").first.inner_text()
        check("富样例第二句：晚间时段 92/111、20:00 到 23:00",
              "92" in rnote1 and "111" in rnote1 and "20:00 到 23:00" in rnote1
              and "晚上八点到十一点" in rnote1, rnote1)
        rnote2 = page.locator(".home-note").nth(1).inner_text()
        check("富样例第三句：二次函数 27 道 + 覆盖 102/120 + 还差 18 道",
              "二次函数" in rnote2 and "27" in rnote2 and "120" in rnote2
              and "102" in rnote2 and "18" in rnote2, rnote2)
        check("富样例本周入库数与派生一致",
              str(RD["week"]) in page.locator(".home-tag").inner_text(),
              page.locator(".home-tag").inner_text())
        check("富样例成长入口：这三个月是怎么长过来的",
              "这三个月是怎么长过来的" in page.locator(".crosslink").inner_text())
        check("390px 富样例首页无横向溢出",
              page.evaluate("document.documentElement.scrollWidth - window.innerWidth") == 0,
              page.evaluate("document.documentElement.scrollWidth - window.innerWidth"))
        shot(page, "m20-home-rich-light")
        page.click("#theme-btn")
        page.wait_for_timeout(150)
        check("富样例首页夜间底色为暖墨",
              page.evaluate("getComputedStyle(document.body).backgroundColor") == "rgb(22, 19, 15)")
        shot(page, "m21-home-rich-dark")
        page.click("#theme-btn")
        page.wait_for_timeout(150)

        page.goto(base + "/#/growth")
        page.wait_for_selector(".chart", timeout=8000)
        page.wait_for_timeout(300)
        check("富样例成长开篇：三个月，120 道错题",
              page.locator(".home-tag").inner_text() == "三个月，120 道错题。",
              page.locator(".home-tag").inner_text())
        r_month = {}
        for q in RD["qs"]:
            mk = (q.get("created_at") or "")[:7]
            if mk:
                r_month[mk] = r_month.get(mk, 0) + 1
        check("富样例柱图格数 == 有入库月份数（4）",
              page.locator(".chart .col").count() == len(r_month) == 4,
              (page.locator(".chart .col").count(), len(r_month)))
        check("富样例柱值与月度入库一致（3/49/58/10）",
              [int(x) for x in page.locator(".chart .val").all_inner_texts()]
              == [r_month[m] for m in sorted(r_month)],
              page.locator(".chart .val").all_inner_texts())
        check("富样例当前月（11 月）柱为朱红",
              page.evaluate("getComputedStyle(document.querySelector('.chart .col.now .bar')).backgroundColor")
              == "rgb(156, 43, 31)")
        r_subj = {}
        for q in RD["qs"]:
            r_subj[q["subject"]] = r_subj.get(q["subject"], 0) + 1
        r_subj_rows = page.locator(".reg").nth(1).locator(".reg-row")
        check("富样例科目分布 55/33/32 与数据一致",
              r_subj_rows.count() == 3 and
              sorted(int(re.match(r"^(\d+) ", t.strip()).group(1))
                     for t in r_subj_rows.locator(".n").all_inner_texts())
              == sorted(r_subj.values()),
              r_subj_rows.locator(".n").all_inner_texts())
        r_et_rows = page.locator(".reg").nth(2).locator(".reg-row")
        r_et_note = page.locator(".reg-note").nth(1).inner_text()
        check("富样例错题结构 65/49/5/1（四行全覆盖）",
              r_et_rows.count() == 4 and
              [int(re.match(r"^(\d+) ", t.strip()).group(1))
               for t in r_et_rows.locator(".n").all_inner_texts()] == [65, 49, 5, 1],
              r_et_rows.locator(".n").all_inner_texts())
        check("富样例概念过半时给设计稿解读（且不报分母口径）",
              "一半以上的错题错在概念" in r_et_note and "/" not in r_et_note.split("。")[0],
              r_et_note)
        check("富样例阶梯当前级：115 道已到期（11-04 快照）",
              "115" in page.locator(".lstep.now .lev").inner_text()
              and "11-04 快照" in page.locator(".lstep.now .lev").inner_text(),
              page.locator(".lstep.now .lev").inner_text())
        rnp = page.locator(".nextstep-p").inner_text()
        check("富样例下一件事：115 到期 + 当天 2 道 + 最近讲过的 3 道",
              "115" in rnp and "2" in rnp and "最近讲过的 3 道" in rnp, rnp)
        check("富样例知识覆盖累计等于原始标签去重总数",
              str(len({k for q in RD["qs"] for k in (q.get("knowledge_points") or [])}))
              in page.locator(".reg").nth(0).locator(".reg-row").last.inner_text(),
              page.locator(".reg").nth(0).locator(".reg-row").last.inner_text())
        check("390px 富样例成长页无横向溢出",
              page.evaluate("document.documentElement.scrollWidth - window.innerWidth") == 0,
              page.evaluate("document.documentElement.scrollWidth - window.innerWidth"))
        shot(page, "m22-growth-rich-light")
        page.click("#theme-btn")
        page.wait_for_timeout(150)
        check("富样例成长页夜间当前级节点为朱红",
              page.evaluate("getComputedStyle(document.querySelector('.lstep.now .lmark')).backgroundColor")
              == "rgb(217, 105, 79)")
        shot(page, "m23-growth-rich-dark")
        page.click("#theme-btn")
        page.wait_for_timeout(150)
        page.unroute("**/data/index.json")
        page.reload(wait_until="networkidle")
        page.wait_for_selector(".chart", timeout=8000)

        # ---- 390px 全路由 0 横向溢出（汇总，报告取这一项数值） ----
        ovf = []
        for r in ["/", "/#/growth", "/#/teach", "/#/teach/q/15", "/#/crop",
                  "/#/crop/s/crop_1792467600000_hw_1024", "/#/accum", "/#/kp"]:
            page.goto(base + r, wait_until="networkidle")
            page.wait_for_timeout(250)
            n = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
            if n != 0:
                ovf.append((r, n))
        check("390px 全路由 0 横向溢出", not ovf, ovf)

        # ---- prefers-reduced-motion：两种动效全关 ----
        page.emulate_media(reduced_motion="reduce")
        page.goto(base + "/#/growth", wait_until="networkidle")
        page.wait_for_selector(".chart", timeout=8000)
        dur = page.evaluate("getComputedStyle(document.querySelector('.route-in')).animationDuration")
        tab_dur = page.evaluate("getComputedStyle(document.querySelector('#tabs a')).transitionDuration")
        check("prefers-reduced-motion 下动效全关", dur in ("0.001ms", "1e-06s") and tab_dur in ("0.001ms", "1e-06s"),
              (dur, tab_dur))
        page.emulate_media(reduced_motion=None)

        # ---- 桌面视口 ----
        desk = browser.new_page(viewport={"width": 1280, "height": 900}, device_scale_factor=2)
        desk.on("pageerror", lambda e: errors.append(str(e)))
        desk.goto(base + "/#/", wait_until="networkidle")
        desk.wait_for_selector(".home-tag")
        check("桌面首页渲染", desk.locator(".home-tag").is_visible())
        check("桌面宽屏导航用全标签",
              [a.inner_text() for a in desk.locator("#tabs a").all()]
              == ["近况", "成长", "讲解查阅", "切题库", "积累册", "知识点"],
              [a.inner_text() for a in desk.locator("#tabs a").all()])
        shot(desk, "d1-home-light")
        set_theme(desk, "dark")
        check("桌面夜间模式", desk.evaluate("document.documentElement.dataset.theme") == "dark")
        shot(desk, "d2-home-dark")
        desk.goto(base + "/#/growth", wait_until="networkidle")
        desk.wait_for_selector(".chart")
        shot(desk, "d8-growth-light")
        desk.goto(base + "/#/teach", wait_until="networkidle")
        desk.wait_for_selector(".row")
        desk.click("#kp-open")
        desk.wait_for_selector("#kp-sheet")
        desk.wait_for_timeout(400)
        check("遮罩在桌面也会压暗背景",
              desk.evaluate("getComputedStyle(document.getElementById('scrim')).opacity") == "1")
        shot(desk, "d5-kp-sheet")
        desk.keyboard.press("Escape")
        set_theme(desk, "light")
        desk.goto(base + "/#/teach/q/15", wait_until="networkidle")
        desk.wait_for_selector(".md .md-h")
        desk.wait_for_timeout(500)
        shot(desk, "d3-detail")
        desk.goto(base + "/#/crop", wait_until="networkidle")
        desk.wait_for_selector(".sess")
        shot(desk, "d4-crop")
        desk.goto(base + "/#/accum", wait_until="networkidle")
        desk.wait_for_selector(".arow")
        shot(desk, "d6-accum")
        desk.goto(base + "/#/kp", wait_until="networkidle")
        desk.wait_for_selector(".krow")
        shot(desk, "d7-kp")

        # ---- 富样例 · 桌面 ----
        desk.route("**/data/index.json", lambda route: route.fulfill(
            status=200, content_type="application/json",
            body=json.dumps(RICH, ensure_ascii=False)))
        desk.goto(base + "/#/")
        desk.reload(wait_until="networkidle")
        desk.wait_for_selector(".home-tag")
        desk.wait_for_timeout(300)
        shot(desk, "d9-home-rich-light")
        desk.goto(base + "/#/growth")
        desk.wait_for_selector(".chart")
        desk.wait_for_timeout(300)
        shot(desk, "d10-growth-rich-light")
        desk.unroute("**/data/index.json")

        # ---- 字体真的用上了 ----
        page.goto(base + "/#/teach", wait_until="networkidle")
        page.wait_for_selector(".row")
        fam = page.evaluate("getComputedStyle(document.querySelector('.row-q')).fontFamily")
        check("正文字体为自托管思源宋体", "Noto Serif SC" in fam, fam)
        loaded = page.evaluate("document.fonts.check('16px \"Noto Serif SC\"')")
        check("思源宋体已加载", loaded)
        mono = page.evaluate("getComputedStyle(document.querySelector('.row-idx')).fontFamily")
        check("编号用 JetBrains Mono", "JetBrains Mono" in mono, mono)

        # ---- 缺图兜底（单独统计错误，404 是这一项故意造的）----
        errors_before = len(errors)
        page.goto(base + "/#/teach/q/15", wait_until="networkidle")
        page.evaluate("document.getElementById('q-img').src = 'data/error-images/does-not-exist.jpg'")
        page.wait_for_timeout(400)
        check("图片缺失有兜底说明", page.locator(".img-missing").count() == 1)

        new_errors = [e for e in errors[errors_before:] if "404" not in e]
        check("无 JS 运行时错误", not new_errors, new_errors[:3])
        all_errors = [e for e in errors if "404" not in e and "does-not-exist" not in e]
        check("全程无 JS 运行时错误（含近况/成长/降级注入）", not all_errors, all_errors[:3])

        browser.close()

    print("\n===== %d passed, %d failed =====" % (len(PASS), len(FAIL)))
    if FAIL:
        print("失败项：")
        for f in FAIL:
            print("  - " + f)
    return 0 if not FAIL else 1


def main():
    global SHOTS
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8901")
    ap.add_argument("--no-shots", action="store_true")
    a = ap.parse_args()
    if not a.no_shots:
        os.makedirs(PROOF, exist_ok=True)
        SHOTS.append(True)
    sys.exit(run(a.base))


if __name__ == "__main__":
    main()
