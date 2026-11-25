# 学迹 · 初中学习资产查阅端

> 拍下来的题、讲过的题，都在这儿找得回来。

「学迹」是一个**纸墨档案风格**的纯静态 Web 前端，用来查阅初中学习资产：错题本、讲解记录、切题会话、积累册与知识点。它面向家庭私有部署——数据由数据生产侧（手机 / 本地脚本）生成并推送到静态托管环境，前端只读不写。

设计语言：宋体排印 + 纸墨配色 + 朱印徽记，移动端优先，深浅双主题，零构建、零依赖。

---

## 功能特性

| 模块 | 路由 | 说明 |
| --- | --- | --- |
| 近况 | `#/` | 数据生成的开篇三句（本周入库 / 做错时段 / 最硬骨头与讲解覆盖）+ 朱印里程碑带 + 最近讲解/切题 |
| 成长 | `#/growth` | 月度学习活动真比例柱图、知识覆盖增长、科目与错题结构、四级学习阶梯（诚实评定）、下一件事 |
| 讲解查阅 | `#/teach` | 题目列表（科目 / 有无讲解 / 知识点多选 / 关键词 / 排序），详情含题图 + OCR 全文 + 讲解 md + v1/v2 版本切换 |
| 切题库 | `#/crop` | 按日期的切题会话 → 会话内题目网格 → 单题大图（题干图 + 附图组合排版） |
| 积累册 | `#/accum` | 按册列表 + iframe 原样嵌入阅读（PDF 次级入口） |
| 知识点 | `#/kp` | 受控概念列表（按科目分组）+ 概念页（该概念下的题目） |

其他特性：

- **hash 路由 + 筛选状态入 URL**：可分享、可后退，列表筛选用 `history.replaceState`，不塞满历史栈。
- **契约版本提示条**：`data/index.json` 的 `contract_version` 与前端期望版本不在兼容列表内时，显示不显眼警告；字段缺失（旧数据）不报警。
- **降级容忍优先**：缺图、缺字段、缺文件一律优雅降位，不摆占位、不破版。
- **自托管字体子集**：思源宋体 400/600/700 + JetBrains Mono（SIL OFL 1.1），已在 `assets/fonts/` 落成 woff2。
- **登录页**（`login/`）：品牌登录页替换浏览器原生 Basic Auth 弹窗，含本地 mock 服务端与 79 项断言。

## 技术栈

- 纯静态：`index.html` + `app.js`（单文件 vanilla JS，IIFE，无框架无依赖）+ `styles.css`
- 无构建、无 npm 运行时依赖、无 CDN、无后端、无数据库
- 数据：`data/index.json`（结构见 [数据契约](study_web_contract.md)）+ `data/` 下的图片与讲解 md
- 工具链（仅开发/验证用，Python 3）：样例数据生成、Playwright 断言、字体子集重建

## 本地运行

```bash
git clone <你的仓库地址> study-web
cd study-web

# 1. 生成本地合成样例数据（只需一次；data/ 已存在则跳过）
python3 tools/gen_sample.py
#    依赖：Pillow（python3 -m pip install Pillow）

# 2. 起静态服务
python3 -m http.server 8901

# 3. 打开
#    http://127.0.0.1:8901/
```

样例数据全部为虚构合成内容，`index.json` 与文件名均带 `sample` 标记，页面会显示「样例数据」横幅；**`data/` 已在 `.gitignore` 中，不会进仓库**。

### 验证（功能断言 + 截图留档）

```bash
# 前置：上面的 http.server 还在跑
python3 tools/verify.py                 # 默认 http://127.0.0.1:8901
python3 tools/verify.py --no-shots      # 只跑断言，不截图
python3 tools/verify.py --base http://127.0.0.1:9999
```

覆盖：路由、搜索/科目/讲解/知识点筛选、知识点抽屉、排序、版本切换、切题三级导航、上一题/下一题、错题本跳转、灯箱、主题切换与记忆、空态、错误态、缺图兜底、390px 无横向溢出、无 JS 运行时错误。截图写入 `proof/`（本地产物，不入库）。

登录页本地验证（自动起 mock 服务端 + 79 项断言 + 截图）：

```bash
python3 login/tools/verify_login.py 8902
# 打开 http://127.0.0.1:8902/login/login.html
```

### 重新生成字体子集

`assets/fonts/` 已提交，正常情况下**不需要**重跑。只有改字符集或换上游版本时才需要：

```bash
python3 tools/build_fonts.py     # 需要 fonttools 与 npm 网络访问
```

## 目录结构

```
study-web/
├── index.html                页面壳（头部/导航/主区/页脚/灯箱）+ 主题引导脚本
├── app.js                    路由、渲染、markdown 渲染、状态、交互（无依赖）
├── styles.css                设计系统（纸墨配色 / 宋体排印 / 组件 / 响应式 / 动效）
├── assets/
│   ├── fonts/                自托管字体子集（思源宋体 400/600/700 + JetBrains Mono）
│   └── favicon/              由「学」字栅格化的朱印（180/64/32/16）
├── login/                    品牌登录页（login.html + login.css + 页脚退出片段 + mock/验证脚本）
├── deploy/                   nginx 配置示例（占位符，部署时替换）
├── tools/
│   ├── gen_sample.py         生成本地合成样例数据 → data/
│   ├── verify.py             功能断言 + 截图（Playwright）
│   └── build_fonts.py        重新生成 assets/fonts/ 下的字体子集
├── scripts/                  CI 检查脚本（HTML 引用 / 契约版本 / 占位符残留）
├── .github/workflows/ci.yml  GitHub Actions：构建与基础检查
├── study_web_contract.md     数据契约（index.json schema 与契约版本规则）
├── CHANGELOG.md              版本变更记录（版本号 + 变更描述）
├── TESTING.md                自测清单（改版后逐条过）
├── DESIGN-BRIEF.md           设计说明（决策底稿）
├── ANTI-SLOP-CHECK.md        反模式自检账本
└── data/                     【本地生成，不入库】样例数据 / 真实推送数据
```

## 数据契约

`study_web_contract.md` 是 `index.json` 的**唯一权威**：字段定义、可选性、过滤规则、契约版本 bump 规则都在里面。要点：

- `index.json` 必须带 `contract_version` 字段（当前 **v1.5**），前端期望版本在 `app.js` 顶部的 `CONTRACT_VERSION` / `CONTRACT_COMPAT_VERSIONS` 声明。
- 小版本只加可选字段（消费方缺失时降级容忍）；大版本（删字段/改语义）必须附迁移步骤。
- 需要新字段时**先在契约里定稿**，再动数据生产侧与前端，不要顺手改。

CI 会跑 `scripts/check_contract_version.py`：从契约头部版本块读出契约版本，与 `app.js` 声明的期望版本比对，不一致则构建失败。

## 部署

前端是纯静态文件，任何静态托管都能用（nginx / Caddy / 对象存储 + CDN / GitHub Pages 等）。仓库内的 `deploy/` 是一份 **nginx 示例**，其中 `<WEB_ROOT>`、`<AUTH_USER_FILE>`、`<CERT_DIR>` 等均为占位符，部署时替换为你自己的值。

最小部署集：`index.html` + `app.js` + `styles.css` + `assets/`（字体与 favicon 必须一起，否则回退系统字体）。数据目录 `data/` 由数据生产侧另行推送。

要点备忘：

1. `assets/` 必须一起部署；`assets/fonts/` 建议长缓存（文件名稳定，内容不变）。
2. `data/index.json` 建议禁缓存（同步后刷新即见）。
3. 讲解 md 建议以纯文本下发（部分服务器默认按 octet-stream 处理 `.md`）。
4. 认证方式自选：Basic Auth、反代 + 会话校验、或内网裸奔均可；本仓库不含任何认证实现细节，`login/` 只提供页面与本地 mock。
5. **部署前把示例配置里的占位符全部替换掉**，并确认 `data/` 没有被一起提交（CI 的占位符残留检查会盯住域名/IP 之类的真实基础设施信息）。

## CI

`.github/workflows/ci.yml` 只做**构建与基础检查**（无部署、无隐私扫描之外的额外步骤）：

1. `node --check` 对所有 JS 文件做语法检查；
2. `scripts/check_html_refs.py` 校验 `index.html` / `login/login.html` 引用的本地资源文件都存在；
3. `scripts/check_contract_version.py` 校验契约版本与前端声明一致；
4. `scripts/check_no_private_info.py` 扫描真实域名/IP/服务器路径等占位符残留（防回归）。

本地一键复跑：

```bash
python3 scripts/check_html_refs.py
python3 scripts/check_contract_version.py
python3 scripts/check_no_private_info.py
for f in $(git ls-files '*.js'); do node --check "$f"; done
```

## 隐私说明

本仓库是**脱敏后**的开源版本：

- 不含任何真实学生数据：`data/`（index.json、错题图片、讲解、积累册、切题产物）整体不入库，由 `tools/gen_sample.py` 本地生成合成样例。
- 不含任何真实基础设施信息：域名、服务器 IP、ssh 别名、部署路径、认证参数在文档与示例配置中一律是占位符。
- CI 的占位符残留检查会在每次构建时扫描这些模式，防止真实信息被重新引入。

## License

[MIT](LICENSE) © 2026 bloody

自托管字体为 SIL OFL 1.1 授权（见 `tools/build_fonts.py` 头部说明）。
