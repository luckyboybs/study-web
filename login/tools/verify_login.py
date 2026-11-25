#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""学迹登录页 · 本地验证（Playwright + mock 服务端）。

覆盖：渲染、字体加载、自动聚焦、明文切换、空态、401、429、500、网络错误、
loading 与防重复提交、成功跳转、日夜切换与记忆、长密码不溢版、
localStorage 不落密码、令牌与主站逐值一致、对比度、页脚退出片段。

用法：python3 tools/verify_login.py [端口]
退出码：0 = 全过；1 = 有失败
"""
import os
import re
import subprocess
import sys
import time

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))     # .../study-web/login/tools
LOGIN_DIR = os.path.dirname(HERE)                     # .../study-web/login
ROOT = os.path.dirname(LOGIN_DIR)                     # .../study-web
PROOF = os.path.join(LOGIN_DIR, 'proof')
LOGIN_URL_PATH = '/login/login.html'

PASS, FAIL = [], []


def check(name, cond, extra=''):
    (PASS if cond else FAIL).append(name)
    print('%s %s%s' % ('PASS' if cond else 'FAIL', name,
                       ('  -> ' + str(extra)) if (extra and not cond) else ''))


def lum(rgb):
    def ch(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def parse_rgb(s):
    m = re.findall(r'[\d.]+', s)
    return tuple(int(float(x)) for x in m[:3])


def token_block(path):
    """取 :root { ... } 里的 --xxx: value 行。"""
    txt = open(path, encoding='utf-8').read()
    out = {}
    for m in re.finditer(r'--([a-z0-9-]+)\s*:\s*([^;]+);', txt):
        out[m.group(1)] = m.group(2).strip()
    return out


def find_chrome():
    """与 tools/verify.py 同口径：优先用 playwright 缓存里的 chromium，找不到则交给默认解析。"""
    import glob
    cache = os.path.join(os.path.expanduser('~'), '.cache', 'ms-playwright')
    cands = sorted(glob.glob(os.path.join(cache, 'chromium-*/chrome-linux64/chrome')), reverse=True)
    cands += sorted(glob.glob(os.path.join(cache, 'chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell')), reverse=True)
    return cands[0] if cands else None


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8902
    base = 'http://127.0.0.1:%d' % port
    url = base + LOGIN_URL_PATH

    srv = subprocess.Popen(
        [sys.executable, os.path.join(HERE, 'mock_login_server.py'), str(port)],
        stderr=subprocess.DEVNULL)
    try:
        run(port, base, url)
    finally:
        srv.terminate()
        try:
            srv.wait(timeout=5)
        except Exception:
            srv.kill()

    print('\n===== %d passed, %d failed =====' % (len(PASS), len(FAIL)))
    if FAIL:
        for f in FAIL:
            print('  FAILED:', f)
        sys.exit(1)


def run(port, base, url):
    with sync_playwright() as p:
        exe = find_chrome()
        browser = p.chromium.launch(**( {'executable_path': exe} if exe else {} ))
        page = browser.new_page(viewport={'width': 390, 'height': 844},
                                device_scale_factor=2)

        js_errors = []
        net_logs = []
        page.on('pageerror', lambda e: js_errors.append(str(e)))
        page.on('console', lambda m: net_logs.append(m.text)
                if m.type == 'error' else None)

        # ---------- 1. 渲染（日间） ----------
        page.goto(url, wait_until='networkidle')
        page.wait_for_timeout(300)

        check('页面标题是「学迹 · 登录」', page.title() == '学迹 · 登录', page.title())
        check('h1 是「学迹」', page.locator('h1').inner_text() == '学迹')
        check('副标是「家庭学习档案」',
              page.locator('.login-sub').inner_text() == '家庭学习档案')
        check('引导语是产品语言不是营销话',
              page.locator('.login-note').inner_text() == '家庭私有，只有家里人能进。')
        check('页面没有任何英文装饰眉题',
              not re.search(r'[A-Za-z]{3,}', page.locator('.login-head').inner_text()))
        check('朱红方印加载成功（真图，非占位）',
              page.evaluate(
                  "document.querySelector('.login-seal').naturalWidth") > 100)
        check('输入框 autofocus 已聚焦',
              page.evaluate('document.activeElement.id') == 'pw')
        check('输入框默认 type=password',
              page.get_attribute('#pw', 'type') == 'password')
        check('autocomplete=current-password',
              page.get_attribute('#pw', 'autocomplete') == 'current-password')
        check('表单原生 action=/login method=post（无 JS 也能提交）',
              page.get_attribute('#login-form', 'action') == '/login'
              and page.get_attribute('#login-form', 'method') == 'post')
        check('输入框有可访问标签「密码」',
              page.get_by_label('密码').evaluate('e => e.id') == 'pw')
        check('初始无错误提示', page.locator('#form-msg').inner_text() == '')
        check('提交按钮文字是「进入」', page.locator('#submit-btn').inner_text() == '进入')
        check('提交按钮是朱红（唯一强调色）',
              page.evaluate(
                  "getComputedStyle(document.getElementById('submit-btn')).backgroundColor")
              == 'rgb(156, 43, 31)')

        # 字体
        page.evaluate('document.fonts.ready.then(() => 1)')
        page.wait_for_timeout(200)
        check('思源宋体 400 已加载',
              page.evaluate("document.fonts.check('400 16px \"Noto Serif SC\"')"))
        check('思源宋体 600 已加载',
              page.evaluate("document.fonts.check('600 16px \"Noto Serif SC\"')"))
        check('思源宋体 700 已加载',
              page.evaluate("document.fonts.check('700 16px \"Noto Serif SC\"')"))
        check('正文实际渲染用思源宋体',
              'Noto Serif SC' in page.evaluate(
                  "getComputedStyle(document.body).fontFamily"))

        # 字号地板
        for sel, least in [('.login-note', 14), ('#form-msg', 14),
                           ('.login-foot-line', 14), ('.field-label', 14),
                           ('.login-sub', 13)]:
            fs = page.evaluate(
                "parseFloat(getComputedStyle(document.querySelector('%s')).fontSize)" % sel)
            check('字号地板：%s >= %dpx（实际 %gpx）' % (sel, least, fs), fs >= least)

        page.screenshot(path=os.path.join(PROOF, 'login-01-light.png'), full_page=True)

        # ---------- 2. 明文切换 ----------
        page.fill('#pw', 'test-password-not-real')
        page.click('#pw-toggle')
        check('点「显示」后输入框变 text',
              page.get_attribute('#pw', 'type') == 'text')
        check('按钮文字变成「隐藏」', page.locator('#pw-toggle').inner_text() == '隐藏')
        check('aria-pressed=true', page.get_attribute('#pw-toggle', 'aria-pressed') == 'true')
        check('密码值未被截断', page.input_value('#pw') == 'test-password-not-real')
        page.screenshot(path=os.path.join(PROOF, 'login-04-reveal.png'), full_page=True)
        page.click('#pw-toggle')
        check('再点切回 password', page.get_attribute('#pw', 'type') == 'password')
        check('按钮文字回到「显示」', page.locator('#pw-toggle').inner_text() == '显示')
        check('切回后焦点仍在输入框',
              page.evaluate('document.activeElement.id') == 'pw')

        # ---------- 3. 空态 ----------
        page.fill('#pw', '')
        page.click('#submit-btn')
        check('空密码提交显示「先输入密码。」',
              page.locator('#form-msg').inner_text() == '先输入密码。')
        check('空态设置 aria-invalid',
              page.get_attribute('#pw', 'aria-invalid') == 'true')
        check('空态后焦点回到输入框',
              page.evaluate('document.activeElement.id') == 'pw')
        check('空态不发起任何请求',
              page.evaluate('window.__posts || 0') == 0)
        check('空态后按钮恢复可用', page.locator('#submit-btn').is_enabled())
        page.screenshot(path=os.path.join(PROOF, 'login-09-empty.png'), full_page=True)

        # ---------- 4. 401 ----------
        page.fill('#pw', 'wrong-pw')
        page.click('#submit-btn')
        page.wait_for_selector('#form-msg:not(:empty)')
        check('401 显示「密码不对，再试一次。」',
              page.locator('#form-msg').inner_text() == '密码不对，再试一次。')
        check('401 后清空密码框', page.input_value('#pw') == '')
        check('401 后焦点回到密码框',
              page.evaluate('document.activeElement.id') == 'pw')
        check('401 后按钮恢复可用', page.locator('#submit-btn').is_enabled())
        check('401 后地址没变（没有整页刷新）', page.url == url)
        page.screenshot(path=os.path.join(PROOF, 'login-05-error-401.png'), full_page=True)

        # 输入即清错误
        page.fill('#pw', 'x')
        check('重新输入即清除错误提示', page.locator('#form-msg').inner_text() == '')
        check('重新输入即清除 aria-invalid',
              page.get_attribute('#pw', 'aria-invalid') is None)

        # ---------- 5. 网络错误 ----------
        page.fill('#pw', 'drop')
        page.click('#submit-btn')
        page.wait_for_selector('#form-msg:not(:empty)', timeout=8000)
        check('网络错误显示「连不上，稍后再试。」',
              page.locator('#form-msg').inner_text() == '连不上，稍后再试。')
        check('网络错误后按钮恢复可用', page.locator('#submit-btn').is_enabled())
        page.screenshot(path=os.path.join(PROOF, 'login-06-error-network.png'),
                        full_page=True)

        # ---------- 6. 其他状态码 ----------
        page.fill('#pw', 'boom')
        page.click('#submit-btn')
        page.wait_for_selector('#form-msg:not(:empty)')
        check('500 显示「服务出错了，稍后再试。」',
              page.locator('#form-msg').inner_text() == '服务出错了，稍后再试。')

        page.fill('#pw', 'flood')
        page.click('#submit-btn')
        page.wait_for_selector('#form-msg:not(:empty)')
        check('429 显示「试得太多了，歇一会儿再来。」',
              page.locator('#form-msg').inner_text() == '试得太多了，歇一会儿再来。')

        # ---------- 7. loading + 防重复提交 ----------
        posts = []
        page.on('request', lambda r: posts.append(r.url)
                if r.method == 'POST' else None)
        page.fill('#pw', 'slow')
        page.click('#submit-btn')
        page.wait_for_timeout(250)
        check('提交中按钮禁用（防重复提交）',
              not page.locator('#submit-btn').is_enabled())
        check('提交中按钮文字是「正在进入…」',
              page.locator('#submit-btn').inner_text() == '正在进入…')
        check('提交中表单 aria-busy=true',
              page.get_attribute('#login-form', 'aria-busy') == 'true')
        page.screenshot(path=os.path.join(PROOF, 'login-03-loading.png'), full_page=True)
        # 连点三次，只能有一次请求
        page.locator('#submit-btn').click(force=True, click_count=3)
        page.wait_for_url(base + '/', timeout=15000)
        check('200 后跳转到 /', page.url == base + '/')
        check('跳转后落在主站（标题是主站标题）',
              page.title() == '学迹 · 初中学习档案', page.title())
        check('连点三次只发出 1 次 POST', len(posts) == 1, posts)
        check('跳转后种下了 cookie',
              'xueji_session' in str(page.context.cookies()))

        # ---------- 8. 退出 ----------
        page.goto(base + '/logout')
        page.wait_for_url(base + '/login/login.html', timeout=8000)
        check('GET /logout 回到登录页', page.url == url)
        check('logout 后 cookie 已清',
              'xueji_session' not in str(page.context.cookies()))

        # ---------- 9. 日间 / 夜间 ----------
        page.goto(url)
        check('默认日间', page.get_attribute('html', 'data-theme') == 'light')
        page.click('#theme-btn')
        check('切夜间：data-theme=dark',
              page.get_attribute('html', 'data-theme') == 'dark')
        check('夜间按钮文字变成「日间」',
              page.locator('#theme-btn-label').inner_text() == '日间')
        check('夜间写入 localStorage[xueji-theme]=dark',
              page.evaluate("localStorage.getItem('xueji-theme')") == 'dark')
        page.wait_for_timeout(200)
        page.screenshot(path=os.path.join(PROOF, 'login-02-dark.png'), full_page=True)

        # 夜间对比度
        paper = parse_rgb(page.evaluate(
            "getComputedStyle(document.body).backgroundColor"))
        ink2 = parse_rgb(page.evaluate(
            "getComputedStyle(document.querySelector('.login-note')).color"))
        ink3 = parse_rgb(page.evaluate(
            "getComputedStyle(document.querySelector('.login-foot-meta')).color"))
        seal = parse_rgb(page.evaluate(
            "getComputedStyle(document.querySelector('.submit-btn')).backgroundColor"))
        check('夜间 纸/墨 对比 >= 7:1（实际 %.1f）' % contrast(paper, ink2),
              contrast(paper, ink2) >= 7, contrast(paper, ink2))
        check('夜间 纸/辅助字 对比 >= 4.5:1（实际 %.1f）' % contrast(paper, ink3),
              contrast(paper, ink3) >= 4.5, contrast(paper, ink3))
        check('夜间 朱红按钮 纸字对比 >= 4.5:1（实际 %.1f）' % contrast(seal, paper),
              contrast(seal, paper) >= 4.5, contrast(seal, paper))

        page.reload(wait_until='networkidle')
        check('刷新后仍是夜间（记忆生效）',
              page.get_attribute('html', 'data-theme') == 'dark')
        page.click('#theme-btn')
        check('切回日间', page.get_attribute('html', 'data-theme') == 'light')

        # ---------- 10. 长密码不溢版 ----------
        page.fill('#pw', 'p' * 200)
        page.wait_for_timeout(100)
        check('200 位密码未被截断', len(page.input_value('#pw')) == 200)
        check('长密码不产生横向滚动',
              page.evaluate(
                  'document.documentElement.scrollWidth <= '
                  'document.documentElement.clientWidth'))
        check('输入框本身不溢出面板',
              page.evaluate(
                  "document.getElementById('pw').getBoundingClientRect().right <= "
                  "document.getElementById('login-form').getBoundingClientRect().right"))
        page.screenshot(path=os.path.join(PROOF, 'login-07-long-password.png'),
                        full_page=True)

        # ---------- 11. 安全 ----------
        keys = page.evaluate('Object.keys(localStorage)')
        check('localStorage 只有主题键，没有别的', keys == ['xueji-theme'], keys)
        vals = ' '.join(page.evaluate('Object.values(localStorage)'))
        check('localStorage 不含密码',
              'test-password-not-real' not in vals
              and 'mock-only-not-a-real-password' not in vals)
        check('页面没有任何密码回显到 DOM',
              'test-password-not-real' not in page.content())

        # ---------- 12. Enter 提交 ----------
        page.fill('#pw', 'enter-key')
        page.press('#pw', 'Enter')
        page.wait_for_selector('#form-msg:not(:empty)')
        check('按 Enter 也能提交并得到 401 反馈',
              page.locator('#form-msg').inner_text() == '密码不对，再试一次。')

        # ---------- 13. 令牌与主站逐值一致 ----------
        a = token_block(os.path.join(ROOT, 'styles.css'))
        b = token_block(os.path.join(ROOT, 'login', 'login.css'))
        shared = ['paper', 'surface', 'surface-2', 'ink', 'ink-2', 'ink-3', 'line',
                  'line-2', 'seal', 'seal-ink', 'seal-soft', 'ok', 'scrim',
                  'serif', 'mono', 'r', 't']
        diff = [k for k in shared if a.get(k) != b.get(k)]
        check('login.css 与主站 styles.css 令牌逐值一致（%d 项）' % len(shared),
              not diff, diff)

        # ---------- 14. 页脚退出片段 ----------
        demo = os.path.join(ROOT, 'login', '_footer-demo.html')
        with open(demo, 'w', encoding='utf-8') as f:
            f.write(
                '<!DOCTYPE html><html lang="zh-CN" data-theme="light"><head>'
                '<meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width, initial-scale=1">'
                '<title>退出片段预览</title>'
                '<link rel="icon" href="/assets/favicon/favicon-32.png" sizes="32x32">'
                '<link rel="stylesheet" href="/styles.css">'
                '<style>' + extract_snippet_css() + '</style></head><body>'
                '<header class="topbar"><div class="topbar-row">'
                '<a class="brand" href="#/"><img class="brand-mark" '
                'src="/assets/favicon/favicon-64.png" alt="" width="30" height="30">'
                '<span class="brand-text"><span class="brand-name">学迹</span>'
                '<span class="brand-sub">初中学习档案</span></span></a></div></header>'
                '<main id="app" style="padding:24px 18px">'
                '<p style="font-size:16px;color:var(--ink-2)">'
                '（这里是主站内容区，退出片段只出现在页脚）</p></main>'
                '<footer class="foot">'
                '<p class="foot-line" id="foot-tag">拍下来的题、讲过的题，都在这儿找得回来。</p>'
                '<p class="foot-meta" id="foot-meta">数据更新于 <生成时间> · 契约 v1</p>'
                '<p class="foot-logout"><a href="/logout">退出</a></p>'
                '</footer></body></html>')
        try:
            page.goto(base + '/login/_footer-demo.html', wait_until='networkidle')
            page.wait_for_timeout(200)
            check('退出片段渲染出「退出」链接',
                  page.locator('.foot-logout a').inner_text() == '退出')
            check('退出链接指向 GET /logout',
                  page.get_attribute('.foot-logout a', 'href') == '/logout')
            check('退出链接字号 >= 14px',
                  page.evaluate("parseFloat(getComputedStyle("
                                "document.querySelector('.foot-logout a')).fontSize)") >= 14)
            check('退出链接是页脚最后一行',
                  page.evaluate(
                      "document.querySelector('.foot').lastElementChild"
                      ".classList.contains('foot-logout')"))
            page.screenshot(path=os.path.join(PROOF, 'login-08-logout-snippet.png'),
                            full_page=True)
        finally:
            if os.path.exists(demo):
                os.remove(demo)

        # ---------- 15. 无 JS 错误 ----------
        check('无 JS 运行时错误（pageerror）', not js_errors, js_errors[:3])
        # Chrome 会把失败请求也记成 console error；这里只应出现我们故意触发的三种
        expected_net = ('Failed to load resource: the server responded with a status of 401',
                        'Failed to load resource: net::ERR_EMPTY_RESPONSE',
                        'Failed to load resource: the server responded with a status of 429',
                        'Failed to load resource: the server responded with a status of 500')
        unexpected = [t for t in net_logs if not any(t.startswith(e) for e in expected_net)]
        check('除故意触发的 401 / 429 / 网络错误 / 500 外无其他资源错误',
              not unexpected, unexpected)
        check('故意触发的四种失败都如实出现在了日志里',
              all(any(t.startswith(e) for t in net_logs) for e in expected_net), net_logs)

        browser.close()


def extract_snippet_css():
    txt = open(os.path.join(ROOT, 'login', 'footer-logout.html'), encoding='utf-8').read()
    m = re.search(r'<style>(.*?)</style>', txt, re.S)
    return m.group(1) if m else ''


if __name__ == '__main__':
    os.makedirs(PROOF, exist_ok=True)
    main()
