# 学迹 · 登录页

替换浏览器原生 Basic Auth 弹窗的品牌登录页。纯静态、零构建、移动端优先，
完全沿用主站已确立的纸墨档案视觉语言。

```
login/
├── login.html              登录页本体（内联脚本，无外部 JS 依赖）
├── login.css               样式（自带一套与主站 styles.css 逐值相同的纸墨令牌）
├── footer-logout.html      页脚「退出」片段（HTML + CSS，给主站页脚接入）
├── DESIGN-BRIEF.md         设计说明（决策卡 / 参考合同 / 命题 / 逐区清单）
├── ANTI-SLOP-CHECK.md      反模式账本
├── proof/                  本地验证截图（移动 390×844，2x）
└── tools/
    ├── mock_login_server.py  本地 mock 服务端（真实 POST /login，可切四种返回）
    └── verify_login.py       Playwright 验证（79 项断言 + 截图）
```

## 1. 后端契约（给建后端的代理）

前端严格按此对接，**不要改**：

| 项 | 值 |
| --- | --- |
| 方法 / 路径 | `POST /login` |
| 请求体 | `application/x-www-form-urlencoded`，唯一字段 `password` |
| 成功 | `302` + `Location: /` + `Set-Cookie`（HttpOnly, Secure, SameSite=Lax, Path=/，30 天）→ 前端执行 `location.href = '/'` |
| 失败 | `401` → 前端页内 inline 提示，**不**刷新页面 |
| 网络不可达 | fetch 抛错 → 前端提示「连不上，稍后再试。」 |
| 其他状态码 | `429` / `5xx` 等 → 前端给对应中文提示（已实现，见下） |
| 退出 | `GET /logout` → 服务端清会话，`302` 回 `/login/` |

> 注：浏览器 fetch 默认跟随重定向，网页端对 200/302 无感；**原生客户端（App）不跟随重定向，必须把「3xx + Set-Cookie」判为登录成功**。

前端发出的请求形态（可直接用于写测试）：

```
POST /login HTTP/1.1
Content-Type: application/x-www-form-urlencoded

password=%E4%BD%A0%E7%9A%84%E5%AF%86%E7%A0%81
```

### 无 JS 兜底

`<form>` 自带 `action="/login" method="post" enctype="application/x-www-form-urlencoded"`
且输入框 `name="password"`——**禁用 JavaScript 时原生表单提交同样成立**，
服务端返回什么页面，用户就看到什么页面。

## 2. 前端文案一览（改文案只需改 `login.html`）

| 场景 | 文案 |
| --- | --- |
| 空密码提交 | `先输入密码。` |
| 401 | `密码不对，再试一次。` |
| 429 | `试得太多了，歇一会儿再来。` |
| 其他 4xx/5xx | `服务出错了，稍后再试。` |
| 网络错误 | `连不上，稍后再试。` |
| 提交中 | `正在进入…` |
| 空闲 | `进入` |

## 3. 安全边界

- 页面**不存储密码**：不发到任何第三方、不写 `localStorage` / `sessionStorage` /
  `IndexedDB` / cookie。`localStorage` 全页只写一个键 `xueji-theme`（主题偏好，
  与主站共用同一个键，让日/夜选择跨页面保持一致）。
- 401 后**清空密码框并回焦**，不把失败密码留在输入框里。
- `<meta http-equiv="Cache-Control" content="no-store">`，登录页不进浏览器缓存。
- fetch 带 `cache: 'no-store'`，密码不进磁盘缓存。
- `autocomplete="current-password"`，让浏览器密码管理器正常接管。
- 错误提示不区分"用户不存在"与"密码错"——本系统只有家里人，不泄露任何账号信息。

## 4. 接入主站（两处，都很小）

### 4.1 部署登录页

`login/` 整个目录推到站点根下，使 `https://study.example.com/login/login.html` 可达。
页面里所有资产路径都是**根绝对路径**（`/assets/fonts/…`、`/assets/favicon/…`），
因此放在任何子目录深度都能正确加载；`/assets/**` 必须保持免认证可达
（`deploy/study.example.com.conf` 里已有对应规则）。

建议的 nginx（在既有 `study.example.com.conf` 基础上补，按你的部署自行调整）：

```nginx
location = /login  { return 302 /login/login.html; }
location = /login/ { return 302 /login/login.html; }
location = /logout { proxy_pass http://127.0.0.1:<后端端口>/logout; }
location /login/login.html {
    auth_basic off;                 # 登录页本身不能要认证
}
# 其余 location 保持 auth_basic 或改交由后端校验会话
```

> 若后端改为会话校验，需要把原来 `auth_basic` 的保护位置换成"未登录一律 302 到
> `/login/login.html`"。这一步涉及认证体系迁移，建议与后端代理一起做，
> 并先在目标环境灰度（保留 Basic Auth 作为回退）。
>
> 或者更省事：让 `location /login/` 整段免认证并加
> `index login.html;`，这样 `/login` 与 `/login/` 都会直接落到登录页，不必 302。

### 4.2 页脚「退出」

按 `footer-logout.html` 里的注释操作：在 `index.html` 的 `<footer class="foot">`
内、`</footer>` 之前插入一行 HTML，并把该文件里的 CSS 追加到 `styles.css` 末尾。
只新增 `.foot-logout` 一个类，不影响主站其他样式。

## 5. 本地验证

```bash
# 一条命令：自动起 mock 服务端、跑 79 项断言、出 9 张截图
python3 login/tools/verify_login.py 8902
```

mock 服务端也可以单独起，用浏览器手工看：

```bash
python3 login/tools/mock_login_server.py 8902
# 打开 http://127.0.0.1:8902/login/login.html
```

密码哨兵（在密码框里原样输入即可触发对应分支）：

| 输入 | 服务端行为 |
| --- | --- |
| `mock-only-not-a-real-password` | 200 + 种 cookie，跳 `/` |
| `slow` | 延迟 1.6s 后 200（看 loading 态） |
| 其他任意 | 401 |
| `flood` | 429 |
| `boom` | 500 |
| `drop` | 直接断开连接（真实网络错误） |

> 注：`mock-only-not-a-real-password` 行中 mock 为简化返回 `200`，生产为 `302`，差异仅对原生客户端有意义（网页端 fetch 跟随重定向，无感）——**不要改 mock 本身**（79 项断言建立在现行为上）。

## 6. 已知限制

- 审查是作者隔离自检（`SELF_REVIEW_ONLY`），没有独立 reviewer。
- 后端未实现，`/login` 与 `/logout` 的真实行为由 mock 代替；对接后需在目标环境复测一次。
- 登录页复用主站 `/assets/**`，因此**不能**单独部署到没有主站资产的域名下。
- 主题切换写 `localStorage`（键 `xueji-theme`）——这是全页唯一的本地写入，
  与"不存密码"不冲突，但若你希望登录页完全不落任何本地数据，把
   `login.html` 里 `$themeBtn` 的 click 处理和 `<head>` 的主题脚本去掉即可，
   页面会退化为跟随系统 `prefers-color-scheme`。
- 本 README「成功 200」曾与生产不符并直接导致 App 登录 bug（2026-11-09：App 只认 2xx，把服务端 302 成功响应误判为服务错误），已按生产代码修正；**后端契约的唯一权威是后端源码本身**（部署路径自行记录），文档与其冲突时以代码为准。
