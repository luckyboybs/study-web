# 学迹 · 自测清单

每轮前端 / 数据契约改版后，按本清单逐条过一遍。命令均可直接复制，**全部在本机执行**，不涉及任何真实部署目标。

判定基准：全部通过才算改版完成；任何一条不过，先在 CHANGELOG 对应条目里记下再处理。

> 说明：本清单是原运维回归清单的开源版。原清单里指向真实站点 / 真实服务器的线上验证条目已移除，保留全部可在本地复现的检查。

---

## 1. 样例数据就位

```bash
python3 tools/gen_sample.py          # data/ 不存在时生成；已存在可跳过
ls data/index.json                   # 应存在，且 contract_version 与契约头部一致
```

预期：`data/index.json` 生成成功，`sample: true`，页面会显示「样例数据」横幅。

## 2. 起本地静态服务

```bash
python3 -m http.server 8901          # 保持在另一个终端里跑
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8901/              # 200
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8901/data/index.json   # 200
```

预期：首页与 index.json 均 200。

## 3. 全量功能断言（本地）

```bash
python3 tools/verify.py --no-shots
```

预期：0 FAIL。覆盖路由、筛选、知识点面板、版本切换、切题三级导航、灯箱、主题、
空态、错误态、缺图兜底、无 JS 运行时错误、390px 无横向溢出等全部断言。

截图留档（可选，写入 `proof/`，本地产物）：

```bash
python3 tools/verify.py
```

## 4. 390px 窄屏无横向溢出

已内含在第 3 步的断言里（各路由 `scrollWidth - innerWidth == 0`）。
单独复现某条路由时，用 Playwright / 浏览器 devtools 设 390×844 视口逐条路由走一遍：
`#/`、`#/growth`、`#/teach`、`#/teach/q/<id>`、`#/crop`、`#/crop/s/<session>`、
`#/crop/s/<session>/<i>`、`#/accum`、`#/accum/b/<name>`、`#/kp`、`#/kp/c/<concept>`。

## 5. 契约版本提示条三态

前端判据：`index.json` 的 `contract_version` 在 `CONTRACT_COMPAT_VERSIONS` 内 → 不报警；
不在 → 显示「数据契约版本不匹配」条；字段缺失 / 空值 → 不报警（旧数据容忍）。

本地复现（改样例数据后记得改回来）：

```bash
# 一致（样例数据默认契约版本）：不应出现提示条
# 不一致：把 data/index.json 的 contract_version 改成一个不兼容值（如 "v9.9"）→ 应出现提示条
# 缺失：删掉该字段 → 不应出现提示条
```

## 6. 前端三件套与检查脚本

```bash
# JS 语法
for f in $(git ls-files '*.js'); do node --check "$f" || echo "SYNTAX FAIL: $f"; done

# HTML 本地资源引用
python3 scripts/check_html_refs.py

# 契约版本一致性（契约头部 vs app.js 声明）
python3 scripts/check_contract_version.py

# 占位符残留（真实域名 / IP / 服务器路径等不得出现在源码里）
python3 scripts/check_no_private_info.py
```

预期：四条全部退出码 0、无输出错误。

## 7. 登录页本地验证

```bash
python3 login/tools/verify_login.py 8902
# 或单独起 mock 服务端手工看：python3 login/tools/mock_login_server.py 8902
# 打开 http://127.0.0.1:8902/login/login.html
```

预期：断言全过。密码哨兵：`mock-only-not-a-real-password` 成功路径、`slow` loading 态、其他 401、`flood` 429、
`boom` 500、`drop` 网络错误。

## 8. 字体与 favicon 可达

```bash
curl -s -o /dev/null -w "%{http_code} %{content_type}\n" http://127.0.0.1:8901/assets/fonts/noto-serif-sc-400.woff2
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8901/assets/favicon/favicon-64.png
```

预期：`200 font/woff2` 与 `200`。404 先查文件名是否被 `tools/build_fonts.py` 改过。

## 9. 隐私 / 占位符回归

```bash
python3 scripts/check_no_private_info.py
```

预期：退出码 0、零命中。该脚本扫描源码里是否残留真实域名、服务器 IP、ssh 别名、
本机 / 服务器绝对路径、认证服务与文件关键字等（防回归，CI 每次 push / PR 都会跑，本地也可随时复跑）。

## 10. 提交前自查

- [ ] `data/` 未被 `git add`（`.gitignore` 已覆盖）
- [ ] 无 `*.bak-*` / `*.log` / `proof/` 截图进库
- [ ] 文档与示例配置里的占位符（`<WEB_ROOT>` 等）没有被误替换成真实值，反之亦然
- [ ] CHANGELOG 已加条目（版本号 + 变更描述 + 对应契约版本）
