#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成本地开发/演示用的【合成样例数据】（写入 data/，不入库）。

所有数据均为虚构，文件名与 index.json 中均带 sample 标记，
不得与真实推送数据混淆（真实数据由数据生产侧脚本生成 index.json）。

用法：python3 tools/gen_sample.py   （在仓库根目录下执行）
输出：data/（index.json + explanations/ + error-images/ + thumbs/ + incoming/crop/ + accum-book/ + plots）
"""
import json
import os
from datetime import datetime, timedelta

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))

FONT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
SAMPLE_MARK = "样例数据 SAMPLE · 非真实"


def font(size):
    return ImageFont.truetype(FONT, size)


def wrap_cjk(draw, text, fnt, max_w):
    """按像素宽度对文本折行（中英混排）。"""
    lines, cur = [], ""
    for ch in text:
        if ch == "\n":
            lines.append(cur)
            cur = ""
            continue
        t = cur + ch
        if draw.textlength(t, font=fnt) <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    return lines


def watermark(draw, w, h, text=SAMPLE_MARK):
    f = font(30)
    tw = draw.textlength(text, font=f)
    draw.text(((w - tw) / 2, h * 0.45), text, font=f, fill=(220, 60, 60, 110))


def gen_question_image(path, qid, subject, question):
    """生成一张'错题归档照片'样式的 JPEG。"""
    w, h = 900, 1200
    img = Image.new("RGB", (w, h), (248, 247, 244))
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([0, 0, w - 1, h - 1], outline=(190, 185, 175), width=3)
    d.rectangle([24, 24, w - 25, 88], fill=(238, 240, 244))
    d.text((40, 38), "第 %d 题 · %s · 初三" % (qid, subject), font=font(34), fill=(40, 50, 70))
    y = 120
    f = font(30)
    for para in question.split("\n"):
        for line in wrap_cjk(d, para, f, w - 90):
            d.text((45, y), line, font=f, fill=(30, 30, 30))
            y += 46
        y += 14
    d.text((60, y + 20), "学生作答：", font=font(28), fill=(150, 40, 40))
    d.line([45, y + 110, w - 60, y + 110], fill=(120, 120, 160), width=2)
    d.line([45, y + 170, w - 60, y + 170], fill=(120, 120, 160), width=2)
    watermark(d, w, h)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, "JPEG", quality=72)


def gen_thumb(src_path, path):
    """从题图生成长边 400px 的 JPEG 缩略图（契约 v1.1 questions[].thumb，手机侧同口径 q≈80）。"""
    img = Image.open(src_path)
    img.thumbnail((400, 400))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, "JPEG", quality=80)


def gen_crop_image(path, session, index, qnum, preview):
    """生成一张'切题产物'样式的 JPEG。"""
    w, h = 760, 560
    img = Image.new("RGB", (w, h), (252, 251, 248))
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([0, 0, w - 1, h - 1], outline=(200, 195, 185), width=2)
    d.text((20, 16), "%s / q%02d%s" % (session, index, " (%s)" % qnum if qnum else ""),
           font=font(24), fill=(90, 95, 110))
    f = font(28)
    y = 90
    note = preview + "（样例截断预览，真实数据仅 16 字符）"
    for line in wrap_cjk(d, note, f, w - 60):
        d.text((30, y), line, font=f, fill=(35, 35, 35))
        y += 42
    d.line([30, y + 60, w - 40, y + 60], fill=(130, 130, 160), width=2)
    watermark(d, w, h, "样例切图 SAMPLE")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, "JPEG", quality=70)


def gen_fig_image(path, kind="chart"):
    """生成一张'题目附图'样式的 JPEG（坐标 + 曲线，纸墨档案风的浅色网格）。

    kind: chart=函数图像 / circuit=示意图（样例只作形态区分，均为合成图）。
    真实附图量级：数百 px（样本实测最小 439px）。
    """
    w, h = 620, 420
    img = Image.new("RGB", (w, h), (253, 252, 250))
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([0, 0, w - 1, h - 1], outline=(200, 195, 185), width=2)
    ox, oy, aw, ah = 90, 340, 470, 260
    for i in range(6):
        gx = ox + aw * i // 5
        d.line([gx, oy - ah, gx, oy], fill=(228, 224, 216), width=1)
    for i in range(6):
        gy = oy - ah * i // 5
        d.line([ox, gy, ox + aw, gy], fill=(228, 224, 216), width=1)
    d.line([ox, oy - ah, ox, oy], fill=(60, 60, 60), width=2)
    d.line([ox, oy, ox + aw, oy], fill=(60, 60, 60), width=2)
    d.text((ox + aw - 30, oy + 10), "U/V", font=font(20), fill=(90, 90, 90))
    d.text((ox - 60, oy - ah - 6), "I/A", font=font(20), fill=(90, 90, 90))
    if kind == "circuit":
        d.rectangle([ox + 60, oy - ah + 40, ox + 190, oy - ah + 130], outline=(50, 60, 90), width=3)
        d.text((ox + 78, oy - ah + 66), "R", font=font(26), fill=(50, 60, 90))
        d.line([ox + 190, oy - ah + 85, ox + 300, oy - ah + 85], fill=(50, 60, 90), width=3)
        d.ellipse([ox + 300, oy - ah + 55, ox + 360, oy - ah + 115], outline=(50, 60, 90), width=3)
    else:
        pts = [(ox + aw * i // 24, oy - ah * (i * i) // (24 * 24) - 8) for i in range(25)]
        d.line(pts, fill=(150, 50, 40), width=3)
    watermark(d, w, h, "样例附图 SAMPLE")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, "JPEG", quality=72)


def gen_tiny_fig_image(path):
    """生成一张'手写笔迹误检'档的极小附图（95×42 原图 px，主会话实测误报形态）。

    前端 FIG_MIN_SIDE=100 过滤器的用例：这张图加载后应被摘除、不展示。
    """
    w, h = 95, 42
    img = Image.new("RGB", (w, h), (250, 249, 246))
    d = ImageDraw.Draw(img, "RGBA")
    d.line([8, 30, 26, 12, 40, 26, 58, 10, 86, 24], fill=(120, 110, 100), width=2)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, "JPEG", quality=70)


def gen_plot_image(path, title):
    """生成一张'绘图产物'样式的 PNG（坐标 + 曲线）。"""
    w, h = 800, 600
    img = Image.new("RGB", (w, h), (255, 255, 255))
    d = ImageDraw.Draw(img)
    d.rectangle([60, 40, w - 40, h - 60], outline=(0, 0, 0), width=2)
    d.line([60, h - 60, w - 40, h - 60], fill=(0, 0, 0), width=2)
    d.line([60, 40, 60, h - 60], fill=(0, 0, 0), width=2)
    pts = []
    for i in range(41):
        x = 60 + (w - 100) * i / 40
        yv = (h - 60) - ((h - 100) * (i / 40) ** 2 * 0.9 + 30 * (i / 40))
        pts.append((x, yv))
    d.line(pts, fill=(30, 90, 200), width=3)
    d.text((70, 50), title + "（样例）", font=font(26), fill=(30, 30, 30))
    d.text((w - 260, h - 40), SAMPLE_MARK, font=font(22), fill=(220, 60, 60))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, "PNG")


def gen_accum_html(path, name, kps, count):
    html = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>%s（样例）</title>
<style>body{font-family:sans-serif;max-width:640px;margin:24px auto;color:#333;background:#f5f7fa}
.banner{background:#fff3cd;border:1px solid #ffe69c;padding:8px 12px;border-radius:6px}
h1{font-size:20px}li{margin:4px 0}</style></head>
<body><div class="banner">⚠️ 合成样例积累本（非真实数据）</div>
<h1>%s</h1><p>收录 %d 道题（样例）</p><ul>%s</ul></body></html>
""" % (name, name, count, "".join("<li>%s</li>" % k for k in kps))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


def gen_accum_pdf(path, name):
    img = Image.new("RGB", (1240, 1754), (255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((80, 80), name + "（合成样例 PDF）", font=font(40), fill=(30, 30, 30))
    d.text((80, 160), SAMPLE_MARK, font=font(30), fill=(220, 60, 60))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, "PDF")


# ---------------------------------------------------------------- 题目 ----
# (id, subject, kps, question, student, correct, has_v2, do_time)
QUESTIONS = [
    (7, "physics", ["电荷", "电流方向", "验电器"],
     "A 带电、B 不带电，用金属棒连接时电流方向 A->B。形成电流的原因是什么？",
     "答：A。", "C. 因为A的正电荷转移到了B", True, "2026-09-05 12:28:22"),
    (12, "math", ["一元一次方程·移项·变号"],
     "解方程：3(x-2) = x + 4，求 x。",
     "x = 5", "x = 5", False, "2026-09-12 20:11:03"),
    (15, "math", ["根的判别式", "根与系数关系"],
     "已知一元二次方程 x² - 5x + 6 = 0，判断根的情况并求两根之和。",
     "有两个不相等的实数根，和是5", "Δ=1>0，两根为 2 和 3，和=5，积=6", True, "2026-09-18 21:40:12"),
    (23, "chemistry", ["酸碱中和反应", "pH"],
     "向稀盐酸中滴加氢氧化钠溶液，pH 随加入量如何变化？",
     "一直变大", "逐渐变大，恰好中和时等于7，过量后大于7", False, "2026-09-22 19:02:41"),
    (31, "physics", ["比热容", "Q=cmΔt 公式变形"],
     "质量相同的水和煤油，吸收相同热量，升高的温度谁大？为什么？",
     "水升得高", "煤油升得高；c_煤油<c_水，由 Q=cmΔt 得 Δt=Q/(cm)", True, "2026-10-02 15:33:20"),
    (42, "math", ["二次函数的应用", "二次函数与一元二次方程的关系"],
     "抛物线 y = x² - 4x + 3 与 x 轴交于哪两点？",
     "(1,0) 和 (3,0)", "(1,0) 和 (3,0)", True, "2026-10-02 21:15:55"),
    (58, "physics", ["串并联电路中电压的规律"],
     "串联电路中各用电器两端电压之和与总电压的关系？",
     "", "等于总电压（U=U1+U2+…）", False, "2026-10-08 20:44:31"),
    (63, "chemistry", ["质量守恒定律", "化学方程式配平"],
     "配平：__Fe + __O₂ → __Fe₃O₄",
     "3Fe + 2O₂ = Fe₃O₄", "3Fe + 2O₂ → Fe₃O₄", False, "2026-10-11 19:20:09"),
    (77, "math", ["与比热容无关的现象判断", "比热容"],
     "（样例：跨科目标签）下列现象中与比热容无关的是？",
     "D", "D。海边昼夜温差小与比热容有关", False, "2026-10-15 21:03:47"),
    (88, "math", ["解一元一次方程", "去括号与移项"],
     "解方程：2(2x - 1) = 3(x + 1) - 1。",
     "x = 2", "x = 2", True, "2026-10-18 20:31:12"),
    (95, "physics", ["欧姆定律", "滑动变阻器"],
     "串联电路中滑动变阻器阻值变大时，电流表示数如何变？",
     "变小", "变小；I = U/R，R 增大则 I 减小", False, "2026-10-21 21:22:05"),
    (102, "math", ["等腰三角形的性质·三线合一", "直角三角形·两锐角互余"],
     "等腰三角形顶角为 40°，求底角的度数。",
     "70°", "70°；(180°-40°)/2", True, "2026-10-24 20:58:33"),
    (110, "chemistry", ["金属活动性顺序"],
     "把铁片放入硫酸铜溶液中，观察到的现象？",
     "铁片变红", "铁片表面有红色固体析出，溶液由蓝变浅绿", False, "2026-10-24 21:30:41"),
    (121, "math", ["乘法公式", "完全平方公式"],
     "计算：(a + 2)²。",
     "a² + 4a + 4", "a² + 4a + 4", False, "2026-10-24 22:05:18"),
]

EXPLAIN_IDS = {7, 12, 15, 31, 42, 63, 88, 95, 102, 110}

# 契约 v1.3 两态样例：只有这些题带 error_type（归因标签），其余题该字段缺席
# （模拟手机侧逐题归因未全覆盖）。取值用英文枚举，与契约 v1.3 注释一致；
# 概念 5/12 < 一半，用于覆盖成长视图「错得最多的是概念」之外的条件分支。
ERROR_TYPE_OF = {
    12: "method",
    15: "concept",
    23: "calculation",
    42: "concept",
    58: "misreading",
    63: "method",
    88: "method",
    95: "concept",
    102: "concept",
    110: "concept",
    121: "calculation",
}

# 契约 v1.3 样例：stats.review_backlog（对象形态，含快照日与当天到期数；
# 同步脚本若给标量题数，前端同样消费）与 stats.crop_figures（切图总张数，按张计）。
# overdue 11 / 总题数 14 > 一半 → 成长视图阶梯当前级评为「让复习转起来」。
SAMPLE_REVIEW_BACKLOG = {
    "snapshot_date": "2026-11-04",
    "overdue": 11,
    "due_today": 2,
    "future": 1,
    "resolved": 0,
}
SAMPLE_CROP_FIGURES = 38  # v1.6.0 口径含附图：7 crops.json + 22 题干图 + 9 张本地存在的附图（tiny 误报图被前端过滤不计展示；missing 引用未落盘不计入口径）

# 契约 v1.1 两态样例：只有这些题生成 thumb（其余题该字段缺席，UI 回退纯文字行）
THUMB_IDS = {7, 12, 15, 31, 42, 102, 110, 121}

# 契约 v1.2 两态样例：受控概念词表（覆盖三科目，含 0 题概念以验证「只列有题」）
# 与 questions[].kp_concepts（受控概念名数组）；未列出的题该字段缺席（模拟旧数据/未归一）。
KP_CONCEPTS = [
    ("一元一次方程", "math"), ("移项", "math"), ("根的判别式", "math"),
    ("韦达定理", "math"), ("二次函数", "math"), ("乘法公式", "math"), ("等腰三角形", "math"),
    ("电荷", "physics"), ("电流方向", "physics"), ("验电器", "physics"), ("比热容", "physics"),
    ("串联电路", "physics"), ("欧姆定律", "physics"), ("滑动变阻器", "physics"),
    ("酸碱中和反应", "chemistry"), ("pH", "chemistry"), ("质量守恒定律", "chemistry"),
    ("化学方程式配平", "chemistry"), ("金属活动性顺序", "chemistry"),
]
KP_OF = {
    7: ["电荷", "电流方向", "验电器"],
    12: ["一元一次方程", "移项"],
    15: ["根的判别式", "韦达定理"],
    31: ["比热容"],
    42: ["二次函数"],
    58: ["串联电路"],
    63: ["质量守恒定律", "化学方程式配平"],
    88: ["一元一次方程", "移项"],
    110: ["金属活动性顺序"],
    121: ["乘法公式"],
}

# 契约 v1.1：explanations[].summary 取自讲解 md 的「🎯 卡点」行（≤80 字）。
# 键为 (qid, version)；列出的 md 写卡点行、index.json 带 summary，
# 未列出的 md 不写卡点行、summary 字段缺席（两态样例）。
KADIAN = {
    (7, "v1"): "金属里移动的是自由电子，而电流方向规定为正电荷定向移动的方向，所以是 A→B 而不是 B→A。",
    (7, "v2"): "先分清「电子移动方向」与「电流方向」这两个概念，再按正电荷方向表述，顺序走对不反。",
    (15, "v1"): "Δ=b²−4ac=1>0 判定两根不相等；再由两根之和 = −b/a = 5 直接得答案，不必解出根。",
    (15, "v2"): "判根只看 Δ 的符号；求和与积用韦达定理 x₁+x₂=−b/a、x₁x₂=c/a，别急着把根解出来。",
    (31, "v1"): "Q、m 相同则 Δt 与 c 成反比：煤油比热容小，升温更高。直觉认为「水升温高」正好相反。",
    (31, "v2"): "由 Q=cmΔt 变形得 Δt=Q/(cm)，c 越小 Δt 越大；先写公式再代数比大小，避免口算翻车。",
    (42, "v1"): "与 x 轴交点令 y=0：x²−4x+3=0 的根是 1 和 3，交点写作 (1,0)、(3,0)，纵坐标是 0。",
    (63, "v1"): "配平靠原子守恒：Fe 配 3、O₂ 配 2，两边氧原子各 4 个；记「3 铁 2 氧气 4 氧原子」。",
    (88, "v1"): "去括号时 3(x+1) 用分配律得 3x+3，移项要变号；两处逐项检查，是这类方程唯一的易错点。",
    (102, "v1"): "等腰三角形两底角相等，顶角 40° 时底角 = (180°−40°)÷2 = 70°；别把顶角当成底角去除。",
    (102, "v2"): "先求底角再验算：70°+70°+40°=180°，内角和守恒；重讲时强调「底角 = (180°−顶角)÷2」。",
    (110, "v1"): "铁比铜活泼，铁表面析出红色铜、溶液由蓝变浅绿；观察题要写全「固体+溶液」两个现象。",
}

SUBJECT_CN = {"math": "数学", "physics": "物理", "chemistry": "化学"}


def build_questions():
    out = []
    for (qid, subj, kps, question, stu, corr, has_v2, do_time) in QUESTIONS:
        versions = []
        if qid in EXPLAIN_IDS:
            versions = ["v1", "v2"] if has_v2 else ["v1"]
        created = (datetime.strptime(do_time, "%Y-%m-%d %H:%M:%S") + timedelta(minutes=3)).strftime("%Y-%m-%d %H:%M:%S")
        trap = None
        if qid == 15:
            trap = "trap-math-discriminant-check"
        elif qid == 31:
            trap = "trap-physics-heat-formula"
        entry = {
            "id": qid,
            "subject": subj,
            "grade": "初三",
            "knowledge_points": kps,
            "question": question,
            "student_answer": stu,
            "correct_answer": corr,
            "mastery": 1 if qid in (15, 102) else 0,
            "resolved": 0,
            "review_count": 1 if qid in (7, 102) else 0,
            "created_at": created,
            "do_time": do_time,
            "image": "error-images/%d.jpg" % qid,
            "has_explanation": bool(versions),
            "explanation_versions": versions,
            "trap_id": trap,
            "ocr_verified": 1 if qid == 102 else 0,
        }
        img_path = os.path.join(ROOT, "error-images", "%d.jpg" % qid)
        gen_question_image(img_path, qid, SUBJECT_CN[subj], question)
        if qid in THUMB_IDS:
            entry["thumb"] = "thumbs/%d.jpg" % qid
            gen_thumb(img_path, os.path.join(ROOT, entry["thumb"]))
        if qid in CROP_REF:
            entry["crop_session"] = CROP_REF[qid]
            entry["crop_epoch"] = int(CROP_REF[qid].split("_")[1])
        if qid in KP_OF:
            entry["kp_concepts"] = list(KP_OF[qid])
        if qid in ERROR_TYPE_OF:
            entry["error_type"] = ERROR_TYPE_OF[qid]
        out.append(entry)
    return out


def build_explanations(questions):
    out = []
    for q in questions:
        qid, subj = q["id"], q["subject"]
        if not q["explanation_versions"]:
            continue
        kp_line = " / ".join(q["knowledge_points"])
        kp0 = q["knowledge_points"][0]
        for ver in q["explanation_versions"]:
            fname = "%d-%s.md" % (qid, ver)
            gen_at = q["created_at"].replace(" ", "T") + "Z"
            wc = 637 if ver == "v1" else 712
            kd = KADIAN.get((qid, ver))
            kadian_block = "🎯 卡点\n%s\n\n" % kd if kd else ""
            if ver == "v1":
                body = """<!-- 条目 id: {id} | 版本: v1 | 生成时间: {gen} | 模型: step-3.7-flash -->
<!-- 📎 转录未校验(ocr_verified=0, confidence="models_divergent_or_degraded") -->
# 第 {id} 题 · {subj} · {kp}
{kadian_block}
🧠 思路
1. 先把题目条件逐条列出来，明确已知与所求；
2. 回忆与 {kp0} 直接相关的定义/公式；
3. 用定义或公式搭一座从条件到结论的桥。

✍️ 分步
**Step1** 整理条件：把题目中的数值与关系写到草稿纸上；
**Step2** 选择工具：涉及 {kp0}，优先使用课本原始表述；
**Step3** 代入验证：把结果代回原条件检查是否自洽。

💡 知识点
- {kp0}
- 相关：{kp}

⚠️ 易错点
- 易错：只看数值大小，不看过程的方向性；
- 易错：单位不统一就代入公式。

**元信息**：id={id} · 学科={subj} · 年级=初三 · 版本=v1 · 字数={wc} · 耗时=51.1s
""".format(id=qid, subj=subj, kp=kp_line, kp0=kp0, gen=gen_at, wc=wc, kadian_block=kadian_block)
            else:
                body = """<!-- 条目 id: {id} | 版本: v2 | 生成时间: {gen} | 模型: step-3.7-flash -->
<!-- ✅ 转录已校验(ocr_verified=1, confidence="both_models_consistent") -->
# 第 {id} 题 · {subj} · {kp}（重讲版）
{kadian_block}
🧠 思路
1. 先问：结论反过来的命题是什么？
2. 举一个反例或正例验证反向命题；
3. 回到原题，用"正向+反向"双重确认答案。

✍️ 分步
**Step1** 写出原命题与逆命题；
**Step2** 用具体数值验证逆命题是否恒成立；
**Step3** 给出规范表达，并标注适用条件。

💡 知识点
- {kp0}
- 方法层：逆命题验证法适用于判断类选择题

⚠️ 易错点
- 易错：把"有时成立"当成"恒成立"；
- 易错：反例不完整，只验证了一种情况。

**元信息**：id={id} · 学科={subj} · 年级=初三 · 版本=v2 · 字数={wc} · 耗时=63.8s
""".format(id=qid, subj=subj, kp=kp_line, kp0=kp0, gen=gen_at, wc=wc, kadian_block=kadian_block)
            path = os.path.join(ROOT, "explanations", fname)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(body)
            entry = {
                "id": qid,
                "version": ver,
                "file": "explanations/%s" % fname,
                "generated_at": gen_at,
                "model": "step-3.7-flash",
                "word_count": wc,
            }
            if kd:
                entry["summary"] = kd
            out.append(entry)
    return out


# ------------------------------------------------------------ 切题会话 ----
# (session, date, source, photo_time, [(file_base, qnum, text_preview, error_book_id)])
#   error_book_id: 整数=已收录 / "NULL"=契约 null（显示"关联未标注"）/ None=字段缺失（不显示状态）
CROP_SESSIONS = [
    ("crop_1791710984244_hw_1005", "2026-10-05", "incoming/1791710984244-img_v3_hw1005.jpg", "2026-10-05 19:12:04",
     [("q01", "Q3", "在“比较不同物质吸热的情况", 31), ("q02", "Q4", "如图所示的电路中，闭合开关", None), ("q03", "Q5", "下列说法正确的是（ ", None)]),
    ("crop_1791805221000_hw_1008", "2026-10-08", "incoming/1791805221000-img_v3_hw1008.jpg", "2026-10-08 20:35:41",
     [("q01", "", "解方程：3(x-2)=x+4，求x的", 12), ("q02", "Q7", "已知抛物线的顶点坐标为(", 42), ("q03", "Q8", "求证：三角形全等的条件", None)]),
    ("crop_1791958400000_hw_1012", "2026-10-12", "incoming/1791958400000-img_v3_hw1012.jpg", "2026-10-12 21:02:19",
     [("q01", "Q2", "向稀盐酸中滴加氢氧化钠溶液", 23), ("q02", "Q3", "配平化学方程式：Fe+O2", 63)]),
    ("crop_1792121900000_hw_1015", "2026-10-15", "incoming/1792121900000-img_v3_hw1015.jpg", "2026-10-15 19:47:52",
     [("q01", "Q9", "串联电路中电压的分配规律", 58), ("q02", "Q10", "滑动变阻器的接法如下图所", 95), ("q03", "Q11", "关于欧姆定律，下列说法错", None), ("q04", "Q12", "在“测定小灯泡电功率", None)]),
    ("crop_1792294800000_hw_1019", "2026-10-19", "incoming/1792294800000-img_v3_hw1019.jpg", "2026-10-19 20:55:10",
     [("q01", "Q1", "把铁片放入硫酸铜溶液中", 110), ("q02", "Q2", "金属活动性顺序由强到弱排", None)]),
    ("crop_1792381200000_hw_1021", "2026-10-21", "incoming/1792381200000-img_v3_hw1021.jpg", "2026-10-21 21:18:33",
     [("q01", "Q5", "等腰三角形顶角为40度", 102), ("q02", "Q6", "直角三角形两锐角的关系是", None), ("q03", "Q7", "计算：(a+2)的完全平方", 121)]),
    ("crop_1792467600000_hw_1024", "2026-10-24", "incoming/1792467600000-img_v3_hw1024.jpg", "2026-10-24 22:11:26",
     [("q01", "Q3", "用金属棒连接带电体A与不带", 7), ("q02", "Q4", "验电器的工作原理是利用了", "NULL"), ("q03", "Q5", "电流方向的规定是下列哪一", None), ("q04", "Q6", "如图，电源电压保持不变", None), ("q05", "Q7", "请在方框中画出电路图", None)]),
]


# 契约 v1.1 两态样例：部分题带 crop_session/crop_epoch（出自的切题会话；旧行缺席属正常）。
# 从 CROP_SESSIONS 的 error_book_id 标注反推，epoch 取会话名里的毫秒时间戳。
CROP_REF = {}
for (_sess_n, _date, _src, _pt, _probs) in CROP_SESSIONS:
    for (_f, _q, _t, _eb) in _probs:
        if isinstance(_eb, int):
            CROP_REF[_eb] = _sess_n


# 切题附图两态样例（v1.6.0）：crops.json 的 problems[] 条目在有附图时多三个键——
#   figure_attached: true / figure_bbox: [x1,y1,x2,y2]（原图 px）/ figure_files: ["qNN-figK.jpg", ...]
# 无附图题三个键都不存在（回归对照）。形态覆盖：
#   "chart"/"circuit"：真实量级附图（数百 px）
#   "tiny"：手写误报档极小图（95×42），前端 FIG_MIN_SIDE 过滤用例
#   "missing"：只引用不落盘，前端加载失败降位用例
CROP_FIGS = {
    ("crop_1791710984244_hw_1005", 1): ["chart"],
    ("crop_1791710984244_hw_1005", 2): ["circuit"],
    ("crop_1791805221000_hw_1008", 2): ["chart"],
    ("crop_1791958400000_hw_1012", 1): ["chart"],
    ("crop_1792121900000_hw_1015", 1): ["missing"],
    ("crop_1792121900000_hw_1015", 2): ["circuit"],
    ("crop_1792294800000_hw_1019", 1): ["tiny"],
    ("crop_1792381200000_hw_1021", 1): ["chart"],
    ("crop_1792467600000_hw_1024", 4): ["circuit", "chart"],
    ("crop_1792467600000_hw_1024", 5): ["circuit"],
}


def build_crop_sessions():
    out = []
    for (sess, date, source, ptime, probs) in CROP_SESSIONS:
        problems = []
        for i, (fbase, qnum, preview, eb_id) in enumerate(probs, 1):
            fname = "%s.jpg" % fbase
            gen_crop_image(os.path.join(ROOT, "incoming", "crop", sess, fname), sess, i, qnum, preview)
            p = {
                "index": i,
                "file": "incoming/crop/%s/%s" % (sess, fname),
                "qnum": qnum,
                "text_preview": preview,
            }
            if eb_id == "NULL":
                # 契约里的 null：字段存在但无值 -> 前端显示"关联未标注"
                p["error_book_id"] = None
            elif eb_id is not None:
                p["error_book_id"] = eb_id
            fig_spec = CROP_FIGS.get((sess, i))
            if fig_spec:
                fig_files = []
                for k, kind in enumerate(fig_spec, 1):
                    fig_name = "%s-fig%d.jpg" % (fbase, k)
                    if kind == "missing":
                        pass  # 引用但不落盘：前端加载失败降位用例
                    elif kind == "tiny":
                        gen_tiny_fig_image(os.path.join(ROOT, "incoming", "crop", sess, fig_name))
                    else:
                        gen_fig_image(os.path.join(ROOT, "incoming", "crop", sess, fig_name), kind)
                    fig_files.append(fig_name)
                p["figure_attached"] = True
                p["figure_bbox"] = [90, 150, 610, 470]
                p["figure_files"] = fig_files
            problems.append(p)
        crops = {
            "session": sess,
            "source": source,
            "photo_time": ptime,
            "anchors_source": "sample",
            "problems": [
                dict({"index": p["index"], "file": p["file"], "qnum": p["qnum"],
                      "text": p["text_preview"],
                      "bbox": [10 + 40 * i, 10 + 40 * i, 700, 500],
                      "poly": [[10, 10], [700, 10], [700, 500], [10, 500]]},
                     **{k: p[k] for k in ("figure_attached", "figure_bbox", "figure_files") if k in p})
                for i, p in enumerate(problems)
            ],
        }
        cpath = os.path.join(ROOT, "incoming", "crop", sess, "crops.json")
        os.makedirs(os.path.dirname(cpath), exist_ok=True)
        with open(cpath, "w", encoding="utf-8") as f:
            json.dump(crops, f, ensure_ascii=False, indent=1)
        out.append({
            "session": sess,
            "date": date,
            "source": source,
            "photo_time": ptime,
            "problems": problems,
        })
    return out


def build_plots():
    out = []
    specs = [
        (1792380000001, "二次函数 y=x²-4x+3 图象", "2026-10-21 20:10:01"),
        (1792468000002, "滑动变阻器伏安特性曲线", "2026-10-24 21:02:02"),
        (1792490000003, "比热容实验温度-时间图", "2026-10-24 22:30:03"),
    ]
    for epoch, title, mtime in specs:
        fname = "plot_output_%d.png" % epoch
        gen_plot_image(os.path.join(ROOT, fname), title)
        out.append({"file": fname, "mtime": mtime})
    return out


def build_accum_books():
    out = []
    specs = [
        ("样例积累册 2026-10-08 · 数学",
         ["一元一次方程·移项·变号", "解一元一次方程", "去括号与移项", "乘法公式", "完全平方公式"], 6),
        ("样例积累册 2026-10-15 · 物理",
         ["电荷", "电流方向", "验电器", "欧姆定律", "滑动变阻器"], 5),
        ("样例积累册 2026-10-21 · 化学",
         ["酸碱中和反应", "pH", "质量守恒定律", "化学方程式配平", "金属活动性顺序"], 4),
        ("样例积累册 2026-10-24 · 二次函数专项",
         ["二次函数的应用", "二次函数与一元二次方程的关系"], 2),
    ]
    for i, (name, kps, cnt) in enumerate(specs, 1):
        html = "accum-book/sample-book-%d.html" % i
        pdf = "accum-book/sample-book-%d.pdf" % i
        gen_accum_html(os.path.join(ROOT, html), name, kps, cnt)
        gen_accum_pdf(os.path.join(ROOT, pdf), name)
        out.append({"name": name, "pdf": pdf, "html": html,
                    "knowledge_points": kps, "problem_count": cnt})
    return out


def main():
    os.makedirs(ROOT, exist_ok=True)
    questions = build_questions()
    explanations = build_explanations(questions)
    crop_sessions = build_crop_sessions()
    plots = build_plots()
    accum_books = build_accum_books()

    index = {
        "contract_version": "v1.4",
        "generated_at": datetime.now().isoformat(),
        "kp_concepts": [{"name": n, "subject": s} for (n, s) in KP_CONCEPTS],
        "sample": True,
        "sample_notice": "本 index.json 为 study-web 合成样例数据（gen_sample.py 生成），"
                         "仅用于开发联调与站点占位；手机侧推送脚本首次运行后将被真实数据覆盖。",
        "stats": {
            "error_book_total": len(questions),
            "error_book_active": len(questions),
            "explanations": len(explanations),
            "crop_sessions": len(crop_sessions),
            "crop_problems": sum(len(s["problems"]) for s in crop_sessions),
            "plots": len(plots),
            "review_backlog": dict(SAMPLE_REVIEW_BACKLOG),
            "crop_figures": SAMPLE_CROP_FIGURES,
        },
        "questions": questions,
        "explanations": explanations,
        "crop_sessions": crop_sessions,
        "plots": plots,
        "accum_books": accum_books,
    }
    path = os.path.join(ROOT, "index.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
    print("written:", path)
    print("questions=%d (thumb %d, kp_concepts %d, error_type %d) explanations=%d (summary %d) "
          "crop_sessions=%d crop_problems=%d plots=%d accum=%d kp_vocab=%d "
          "review_backlog=%s crop_figures=%d"
          % (len(questions), sum(1 for q in questions if "thumb" in q),
             sum(1 for q in questions if "kp_concepts" in q),
             sum(1 for q in questions if "error_type" in q),
             len(explanations), sum(1 for e in explanations if "summary" in e),
             len(crop_sessions),
             index["stats"]["crop_problems"], len(plots), len(accum_books),
             len(index["kp_concepts"]),
             json.dumps(index["stats"]["review_backlog"], ensure_ascii=False),
             index["stats"]["crop_figures"]))


if __name__ == "__main__":
    main()
