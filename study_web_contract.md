# 初中学习资产查阅端 · 数据契约 v1.5（2026-11-24）

> 本文件定义「学迹」前端消费的 `index.json` 数据结构与契约版本规则。
> 前端（`app.js`）与数据生产侧（负责生成 `index.json` 的同步脚本）都以此文件为唯一权威。
> 本副本面向开源读者：所有部署环境、服务器路径、域名均为占位符或泛化描述。

## 契约版本块

- **当前契约版本：v1.5**，生效日期 2026-11-24，对应 `index.json` schema：v1.4 全部字段不变，新增可选字段 `crop_sessions[].problems[]` 的 `figure_attached` / `figure_bbox` / `figure_files` 三键（见「crop_sessions problems 附图字段」节）。v1.4 → v1.5 为小版本：只加可选字段，消费方对字段缺失一律降级容忍。
- **`index.json` 必须带 `contract_version` 字段**（字符串，如 `"v1.5"`），与本节声明一致。字段缺失的 index.json 视为契约版本化之前的数据：前端按旧数据容忍、不报警；下次同步即带上该字段。
- **bump 规则**（改契约前先升版本，再动数据生产侧脚本与前端，两处各自声明目标契约版本）：
  - **小版本（v1.0 → v1.1）**：只新增可选字段（消费方缺失时可降级）。必须写进「同步规则」并同步两端；前端对新字段缺失要有兜底。
  - **大版本（v1.x → v2.0）**：删除字段、改字段名、改字段语义或改过滤规则。**必须附迁移步骤**（旧数据怎么办、生产侧与前端的切换顺序、回滚方式），并先在 CHANGELOG 加条目再动手。
  - 修订已上线的字段语义（如单位、口径、排除规则）一律按大版本处理，不允许「静默改」。
- **两端声明**：数据生产侧同步脚本的契约版本常量与前端 `app.js` 的期望版本，都必须与本文件头部一致；不一致时前端会显示「数据契约版本不匹配」提示条。一致性可用 `scripts/check_contract_version.py` 自动校验（CI 每次构建都会跑）。

## 架构

- 数据生产侧（手机 / 本地脚本）生成 `index.json` 与 `data/` 下的图片、讲解 md，增量推送到静态托管环境（任意 Web 服务器、对象存储 + CDN 均可）。
- 前端：纯静态 HTML/JS，读 `data/index.json` + 图片文件；无后端、无数据库。
- `index.json` 由数据生产侧每次运行全量重建后随推（数据量小：百题量级 + 讲解 + 会话 + 绘图，JSON 通常 < 1MB）。

## 模块范围

1. **讲解查阅**：题目列表（筛选：科目 / 有无讲解 / 知识点客户端过滤 / 关键词客户端过滤）；题目详情：题图 + OCR 全文 + 讲解 md 渲染 + v1/v2 版本切换。
2. **切题库**：按日期浏览切题会话 → 会话内题目网格 → 单题大图；标注该题是否已入错题本及 id。

明确不做（后续轮次）：知识点树、复习路径、积累本回链、绘图库、服务端检索。

## 同步规则（数据生产侧职责）

- 触发方式由生产侧自定（轮询 / 手动 / 定时均可），有增量才推。
- 增量判定与传输粒度自定（按文件 / 按目录均可），但须保证：**index.json 引用的文件必须都在推送目标里**，缺了前端会显示「图片缺失」降位框（设计内容错容忍，不是崩溃）。
- 每次推送建议写 `manifest.json`（时间 / 文件数 / 字节数 / 耗时 / 增量水位），便于对账。
- `index.json` 只收「未软删且非测试」的题目行；切题会话排除测试目录；绘图只收 `plot_output_{epoch}.png` 形态的产物（排除固定名与手工命名散件）。

## index.json schema（v1.5）

```json
{
  "contract_version": "v1.5",
  "generated_at": "ISO8601",
  "kp_concepts": [{"name": "二次函数", "subject": "math"}],
  "stats": {"error_book_total": 0, "error_book_active": 0, "explanations": 0, "crop_sessions": 0, "crop_problems": 0, "plots": 0, "review_backlog": 0, "crop_figures": 0},
  "questions": [{"id": 1, "subject": "physics", "grade": "初三", "knowledge_points": ["电荷","电流方向"], "question": "OCR全文", "student_answer": "...", "correct_answer": "...", "mastery": 0, "resolved": 0, "review_count": 0, "created_at": "...", "do_time": "...", "image": "error-images/1.jpg", "thumb": "thumbs/1.jpg", "crop_session": "crop_1700000000000_hw_1001", "crop_epoch": 1700000000000, "kp_concepts": ["电流方向"], "error_type": "concept", "has_explanation": true, "explanation_versions": ["v1","v2"], "trap_id": null, "ocr_verified": 0}],
  "explanations": [{"id": 1, "version": "v1", "file": "explanations/1-v1.md", "generated_at": "...", "model": "...", "word_count": 0, "summary": "≤80字，取自卡点行"}],
  "crop_sessions": [{"session": "crop_1700000000000_hw_1001", "date": "2026-01-01", "source": "incoming/xxx.jpg", "photo_time": "...", "problems": [{"index": 1, "file": "incoming/crop/crop_1700000000000_hw_1001/q01.jpg", "qnum": "Q1", "text_preview": "≤16字符"}]}],
  "plots": [{"file": "plot_output_1700000000.png", "mtime": "...", "question_id": null, "crop_session": null}],
  "accum_books": [{"name": "...", "pdf": "accum-book/....pdf", "html": "...", "knowledge_points": [], "problem_count": 0}]
}
```

过滤规则：`questions` 只收未软删且非测试的行；`crop_sessions` 排除测试目录；`plots` 只收 `plot_output_{epoch}.png`（排除固定名 `plot_output.png` 与手工命名散件）。

`questions[]` 可带可选 `materials` 对象（v1.4 新增；只有产过分层材料的题有该键）。

`crop_sessions[].problems[]` 可带可选 `figure_attached` / `figure_bbox` / `figure_files` 三键（v1.5 新增；只有带附图的题有这些键）。

## 题目身份补强

- 错题表与切题会话的关联列（`crop_session` / `crop_epoch`）透出到 `questions[]`；**迁移后新增的行才有值，旧行缺席属正常**，UI 一律容忍。
- 绘图元数据 `plot_output_{epoch}.json`（epoch/kind/arg/note/generated_at/subject/question_id/crop_session）可合并进 `plots` 条目，其中 `question_id` / `crop_session` 为题级关联，只写「无歧义」的值，拿不准就留 null。

## v1.1 新增字段（全部可选，消费方缺失容忍）

- `questions[].thumb`：缩略图路径（相对 `data/`，如 `thumbs/1.jpg`）。由题图生成长边 400px JPEG，按题目 id 命名；题图缺失或生成失败时字段缺席。
- `questions[].crop_session` / `crop_epoch`：该错题出自的切题会话名与会话目录 epoch。旧行缺席属正常。
- `explanations[].summary`：一句话摘要（≤80 字）。取自讲解 md 的「🎯 卡点」行；md 无该行时字段缺席。

## v1.3 新增字段（可选，消费方缺失容忍）

- `questions[].error_type`：错题归因（自由文本，如 concept/method/calculation/careless 或中文原值）。成长视图「科目与错题结构」区消费；字段缺失时该区整体不渲染。
- `stats.review_backlog`：已到期未复习的题数（`next_review_at <= 今天` 且未解决）。成长视图阶梯当前级的「真实缺口」数字；缺失时该数字不显示。
- `stats.crop_figures`：切题图总张数（契约引用文件口径）。成长视图月度登记行消费；缺失不渲染该列。
- 月度入库/讲解/切题序列、知识覆盖增长、科目分布、做错时段、里程碑——**全部由前端从既有字段派生**（`questions[].created_at` / `do_time` / `knowledge_points`、`explanations[].generated_at`、`crop_sessions[].date`），不需要新字段。
- `mastery` / `resolved` / `review_count` 继续留在契约但**不在任何视图渲染**（复习闭环未运转；成长叙事只建在真实活动数据上）。

## v1.4 新增字段（可选，消费方缺失容忍）

- `questions[].materials`（可选对象）：该题**分层材料**的指针。来源为错题表的材料列 JSON，构建 index 时**一律转成相对 `data/` 的路径**；无材料、字段为空、JSON 解析失败或空对象 → **该键整体缺席**（不写 null 对象）。
- 键口径（按数据实际有无透出，缺哪个键就缺席哪个）：
  - `annotated_image`：原题标注图（PNG）；
  - `student_version`：学生极简版（md）；
  - `parent_version`：家长推演版（md）；
  - 额外键按数据原样透出（补充图指针等）；
  - 非路径值（各类校验和、归档时间等）**原样透出**，不改写。
- 路径口径与 `image` / `thumb` 一致：**相对 `data/`**；指针文件在数据侧不存在时该键缺席（不编造路径），其余键照常。
- 缺失容忍：无 `materials` 键的题消费方**不渲染该区、不摆占位**；对象内单个键缺失时对应入口不渲染。

## crop_sessions problems 附图字段（v1.5 新增，可选，消费方缺失容忍）

- 来源：生产切图链路对**有附图**的题，在 crops.json `problems[]` 条目写 `figure_attached: true` / `figure_bbox: [x1,y1,x2,y2]`（原图 px，该题全部附图的合并框）/ `figure_files: ["q01-fig1.jpg", ...]`（会话目录内相对文件名），并在同目录落 `qNN-figK.jpg`；**无附图题三项都不写**（不是 false / null / 空串）。
- index.json 透传口径：**逐键判断，仅当源 crops.json 该题条目带此键时才透传**，值原样透出；`figure_files` 保持会话目录内相对文件名，完整路径 = `incoming/crop/<session>/<figure_files[i]>`（与 `problems[].file` 同目录）。
- `figure_files` 为数组，一题可有多张附图（`fig1` / `fig2`…）；**可能为空数组**（附图框 clamp 后退化被跳过时），消费方按空数组处理 = 不渲染附图区。
- 存量过渡数据：早期格式可能只有 `figure_attached` / `figure_bbox` 而无 `figure_files`。**消费方以 `figure_files` 为渲染依据**（缺席或空数组 → 不渲染附图区、不摆占位），不要仅凭 `figure_attached` 渲染。
- 缺失容忍：三键缺席即无附图。前端拼图组合排版（题干图 + 附图）的消费方式由后续轮次定义，本版不约束。
- 同步口径：`qNN-figK.jpg` 随会话目录整目录增量同步（与 `qNN.jpg`、crops.json 同批）；crops.json 是该会话最后落盘的文件（fig jpg 先写、crops.json 后写），见到 crops.json 时附图必已在盘，无竞态。
- verify 口径：期望远端文件数应把 `figure_files` 计入——index.json 引用的文件必须都在远端，缺了要报出来。

## plots[].question_id / crop_session（可选，不 bump 版本）

- `plots[].question_id`（可选）：该绘图关联的错题 id（**题级**，非页级/会话级）。只写「无歧义」的值，拿不准就留 null。
- `plots[].crop_session`（可选）：该题入库时的切题会话名，同 `questions[].crop_session` 口径；无切题会话时为 null。
- 死链不建：测试题与软删题不关联（它们不在 `questions` 里）。
- 消费方（绘图库）按 `question_id` 回链题目详情；`null` / 字段缺失时该图继续留在按时间浏览的绘图库，不报警、不猜测。

## v1.2 新增字段（可选，消费方缺失容忍）

- `kp_concepts`（顶层，可选）：受控概念词表快照 `[{name, subject}]`。唯一权威是数据生产侧维护的课程词表；契约不复制词表内容，只定义透出形态。映射文件或词表缺失时整字段缺席。
- `questions[].kp_concepts`（可选）：该题知识点经别名归一化后的受控概念名数组（`kp_concepts[].name` 的子集）。由别名映射表在构建 index 时派生；题内无可归一标签时字段缺席。原始 `knowledge_points` 字段保持原样（展示层仍用原文，不动）。

## 已知数据缺陷（UI 要容忍，不要「修」数据）

- crops.json 的题干预览只有 16 字符截断 → 切题库不做题干搜索。
- 绘图历史可能被固定名覆盖丢失 → 绘图库只从新数据起。
- 知识点标签以自由文本为主 → 别名归一化是数据侧的事，一期不碰。
- 复习字段未闭环 → 复习路径后续轮次，一期不碰。
